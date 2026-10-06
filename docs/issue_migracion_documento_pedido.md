# Login abortado: `Table 'rnd.documento_pedido' doesn't exist`

Fecha: 2026-10-05

## Síntoma

Al entrar al sistema (`py main.py`, login OK) el arranque moría antes de abrir
el dashboard, con el diálogo de migración en rojo:

```
INFO  - Eliminado índice legacy lugarentrega_cliente_id_nombre de lugares_entrega
INFO  - Creado índice por cliente+nombre+dirección en lugares_entrega
ERROR - peewee.ProgrammingError: (1146, "Table 'rnd.documento_pedido' doesn't exist")
ERROR - Falló la migración de la base de datos
RuntimeError: No se pudieron aplicar las migraciones de la base de datos
```

## Causa raíz

`MigrarVersion()` corre en **cada login** y una de sus operaciones altera una
tabla que el propio arranque nunca garantiza:

```python
# controladores/Migraciones.py
migrator.alter_column_type('documento_pedido', 'cliente_id', IntegerField(null=True))
```

`documento_pedido` y sus dos tablas hijas son **aditivas** (issue #82,
`773a349`) y se creaban solamente al importar pedidos, mediante
`Documentos.asegurar_esquema_documentos()` (`modelos/Documentos.py:125`), que se
llama desde:

- `controladores/ImportacionPedidos.py:472` (flujo de importación)
- `Documentos.referencias_por_hojas` / `actualizar_remito_de_hoja` / `backfill_documentos_legacy`

**Nunca desde el login.** Por eso, en una instalación que todavía no importó
nada, la tabla no existe, MySQL devuelve 1146, y `RealizaMigraciones` aborta
(`1146` no está en el set `IGNORAR = {1060, 1022, 1061, 1091}`, que sólo cubre
"ya aplicado") abortando toda la migración, no sólo esa operación.

La operación se agregó en `781fb7d` (issue #89, "permitir cliente/ruta
pendientes en importación"), que sí era necesaria: el modelo se creó en #82 con
`cliente` **NOT NULL** y #89 (`123cd0c`) lo pasó a `null=True`. El bug es que la
migración asumía que la tabla ya existía en todas las instalaciones, y sólo es
cierto en las que alguna vez importaron.

## Por qué la base quedó en ese estado

Verificado **contra la base real** (`vps-922868-x.dattaweb.com`, base `rnd`,
MySQL 5.6.51, 31 tablas):

| Tabla | Estado |
| --- | --- |
| `cliente`, `rutas_reparto`, `localidades`, `hoja_de_ruta`, `lugares_entrega`, `proveedor`, `pallet` | existen |
| `documento_pedido` | **no existe** |
| `documento_pedido_detalle` | **no existe** |
| `documento_pedido_hoja_ruta` | **no existe** |

`hoja_de_ruta.cliente_id` y `.ruta_id` ya son `int(11) NULL`, así que las otras
dos operaciones del mismo bloque eran no-ops. El único bloqueo era
`documento_pedido`.

## El arreglo

`controladores/Migraciones.py`: llamar `asegurar_esquema_documentos()` **antes**
del bloque de `alter_column_type`.

- `create_tables(..., safe=True)` no toca instalaciones que ya tienen las tablas.
- El modelo ya declara `cliente` nullable, así que en las nuevas el `alter`
  queda como no-op.
- En las viejas que tienen `cliente_id NOT NULL` el `alter` **se sigue
  aplicando**: esa es la razón de existir de la migración de #89, y el fix no
  la elimina.

Se descartó agregar `1146` a `IGNORAR`: silenciaría el error y dejaría la app
igual de rota, pero más difícil de diagnosticar (fallaría después, en
`BandejaPedidos`, con un error que no señala la causa).

## Cómo se verificó

Nuevo `tests/test_migracion_documento_pedido.py`. Corre la migración **real**
(`MigrarVersion` + `playhouse.migrate.migrate` + los DDL que genera peewee) contra
un MySQL simulado. Lo único que se reemplaza es el servidor, porque la falla es
del servidor (1146), no del código.

**Corroborado en las dos direcciones:**

| | código roto (`git stash` del fix) | con el fix |
| --- | --- | --- |
| resultado | 2 failed | 3 passed |
| error | `ProgrammingError(1146, "Table 'rnd.documento_pedido' doesn't exist")` | — |

El test reproduce el error exacto del log de producción, no una excepción
parecida. Suite completa: **285 passed, 1 skipped**.

Además, chequeo read-only sobre la base real: las 7 tablas legacy que la
migración altera existen, y las 3 que faltaban son exactamente las que ahora
crea el fix. Con el fix el login completa.

## Los 2 minutos del primer arranque (y por qué no se repiten)

El primer login con el fix tardó ~2 minutos en el diálogo "Actualizando
sistema". **Es un costo de una sola vez**: fue la creación de las 3 tablas.

Medido sobre la base real, con las tablas ya existentes:

| | tiempo | SQL emitido |
| --- | --- | --- |
| `asegurar_esquema_documentos()` | 0,10 s | 3× `SELECT ... FROM information_schema.tables` |
| DDL (CREATE/ALTER) | — | **ninguno** |

Como `create_tables(safe=True)` no emite DDL cuando la tabla existe, los
próximos logins no toman **ningún metadata lock**. No hay riesgo de que el
diálogo vuelva a colgarse.

**Por qué tardó 2 minutos esa vez.** Las 3 tablas suman 5 foreign keys contra
`proveedor`, `cliente` y `hoja_de_ruta`, así que el `CREATE TABLE` necesita
metadata locks compartidos sobre esas 4 tablas. En ese servidor:

```
lock_wait_timeout        = 31536000   (1 año)  <--.metadata lock / DDL
innodb_lock_wait_timeout = 50                 <-- row locks, NO aplica a DDL
```

`CREATE TABLE` no está acotado por los 50 segundos de `innodb_lock_wait_timeout`,
sino por `lock_wait_timeout`, que está en un año. O sea: si otra conexión del
sistema tenía una transacción abierta sobre `cliente`/`hoja_de_ruta`, el DDL
espera **casi indefinidamente** hasta que esa transacción se libere. Ahí están
los 2 minutos.

## Trampas del diagnóstico (no confiar en la metadata MySQL 5.6)

`information_schema.tables.create_time` dice `2026-10-03 14:52` para las 3 tablas,
y es **falso**: se crearon hoy. La misma consulta dio **31 tablas a las 15:50** y
**34 a las 16:05**. En MySQL 5.6 InnoDB `create_time` no es confiable — para
decidir si algo existe hay que comparar el conteo/`SHOW TABLES`, no la fecha.

Además, `db.execute_sql()` con un `%` literal en el SQL (tipo
`LIKE 'documento_pedido%'`) revienta con
`TypeError: not enough arguments for format string`: pymysql hace
`query % ()` cuando no hay parámetros. Usar `IN (...)` o `%` duplicado.

## Pendientes

- [x] **Aplicar en la base real.** Aplicado: las 3 tablas existen, vacías, con
      `cliente_id int(11) NULL` y los índices del modelo. Login completo.
- [ ] **DDL en el login sin cota de tiempo.** `lock_wait_timeout = 31536000`
      (1 año) en producción. Cualquier migración futura que agregue una tabla
      con FK puede dejar el diálogo "Actualizando sistema" colgado minutos (o
      mucho más). Opciones: correr esas migraciones por script fuera del arranque,
      o setear un `lock_wait_timeout` de sesión bajo antes de cualquier DDL.
- [ ] **El diálogo dice "unos segundos".** El primer arranque con el fix tardó
      ~2 min. El texto debería admitirlo o mostrar el tiempo transcurrido, para
      que una espera larga no parezca un cuelgue.
- [ ] **`IGNORAR` sigue siendo una lista a mano.** `{1060, 1022, 1061, 1091}`
      son "ya aplicado"; 1146 es "no existe la tabla", otra cosa. Si mañana una
      migración apunta a otra tabla ausente, va a volver a abortar el arranque
      con un error poco descriptivo. Vale la pena loguear una línea clara
      ("falta la tabla X, se omite") cuando se opte por ignorar 1146.
- [ ] **Guardas de existencia de tabla antes de alterar.** Alternativa
      estructural: `migrator.alter_column_type(...)` sólo si la tabla está, en
      vez de depender del orden entre pasos.
- [ ] **`backfill_documentos_legacy()` sigue sin ejecutarse solo.** Con esto el
      esquema existe al entrar, pero las hojas de ruta legacy siguen sin
      documento asociado hasta que se corra
      `scripts/migrar_documentos_logisticos.py` a mano.
- [ ] **Deps: peewee 4.1.1 con `playhouse.migrate`.** En peewee 4,
      `field.ddl_datatype(ctx)` devuelve un nodo `SQL`, no un `str`. Sirvió para
      el test, pero si algún día se usa `playhouse.migrate` sobre peewee 4 hay
      que verificar cada rama que arme DDL.
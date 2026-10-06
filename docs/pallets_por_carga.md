# Pallets por carga activa

## Objetivo

La pantalla **Armado de pallets** trabaja sobre una carga operativa concreta. Un pallet no es global ni debe aparecer solamente por estar en estado `ARMADO`.

La carga activa queda identificada por:

- fecha de reparto;
- ruta;
- responsable/chofer;
- equipo/camión.

Esto evita mezclar pallets de repartos diferentes y permite conservar correctamente incluso pallets vacíos recién creados.

## Selección de pallets

El selector principal ya no es un combo desplegable. Los pallets pertenecientes a la carga se muestran como botones/chips numerados `1..N`.

- Un clic cambia inmediatamente el pallet activo.
- El pallet actual queda visualmente resaltado y además se muestra como `PALLET ACTUAL: N`.
- Los botones se distribuyen en cinco columnas para darles buen tamaño operativo.
- El selector crece verticalmente según la cantidad de pallets, evitando ocultarlos detrás de un scroll en el uso normal (por ejemplo, 20 pallets se ven en cuatro filas).
- El tooltip conserva el código técnico completo (`PLT-AAAAMMDD-NNN`).
- La numeración visible es operativa; las operaciones internas siguen usando `pallet.id` y `pallet.codigo`.
- `+ Nuevo pallet` ocupa una fila propia para quedar siempre visible y crea un pallet dentro del contexto activo dejándolo seleccionado.
- La grilla de contenido del pallet se mantiene compacta (máximo 300 px de alto) para priorizar visualmente la selección de pallets.

La jerarquía visual del panel derecho es:

1. contexto de carga;
2. acción `+ Nuevo pallet`;
3. selector completo de pallets;
4. indicador `PALLET ACTUAL: N`;
5. KPI de KG del pallet actual;
6. grilla compacta con el contenido del pallet seleccionado;
7. totales y destinos.

## KPI de KG del pallet actual

El peso total del pallet dejó de ser una línea más del resumen de abajo y pasó a ser un bloque visual propio, justo debajo de `PALLET ACTUAL: N`:

- título fijo `KG ACTUALES`;
- valor en cuerpo grande (`40px`, peso 800) con la unidad `KG` al lado;
- el resumen inferior se mantiene completo (líneas, cantidad, KG y bultos): el KPI no lo reemplaza, lo destaca.

### Límite por pallet

Todavía **no existe configuración de límite** en el sistema. La pantalla ya está preparada para mostrarla cuando exista:

- se lee el parámetro `KG_LIMITE_PALLET` de la tabla de parámetros del sistema;
- si no está cargado, queda vacío o no es positivo, el KPI muestra sólo el KG actual;
- si está cargado, se agrega la línea `Límite: X KG · Exceso Y KG` o `Límite: X KG · Disponible Y KG`;
- el número grande se pinta en rojo (`#B91C1C`) al exceder y en verde (`#15803D`) cuando hay lugar, con los colores que ya usa el tema.

El límite pertenece al pallet actual: sin pallet elegido no se muestra la línea de límite, porque no hay contra qué compararlo.

`limit_kg_pallet()` lee el parámetro con una consulta directa y **no** usa `ParamSist.ObtenerParametro`, porque ese método inserta el parámetro cuando falta: leerlo en cada refresco escribía en la tabla de parámetros en cada arranque.

### El KG no titila al cambiar de chip

La vista recuerda el KG de cada pallet que ya fue cargado. Al volver a un chip con un clic, el KPI muestra de inmediato el último peso conocido de ese pallet en lugar de `0 KG`, mientras el controlador vuelve a consultar la base y confirma el valor.

Al recargar el selector (por ejemplo al crear un pallet nuevo) se descartan los KG de los pallets que ya no están en pantalla, porque esos ids pertenecen a otra carga.

## Persistencia

`Pallet` incorpora los siguientes campos de contexto, todos compatibles con datos existentes porque aceptan `NULL`:

- `fecha_reparto`;
- `ruta_id`;
- `responsable_id`;
- `equipo_id`.

Los pallets nuevos guardan estos datos desde su creación. De esta manera un pallet vacío también pertenece inequívocamente a la carga que lo creó.

La función `pallets_para_carga()` devuelve sólo pallets `ARMADO` que coinciden exactamente con fecha, ruta, responsable y equipo.

## Resolución del contexto en Armado de pallets

Al cargar mercadería, el controlador obtiene las hojas de ruta para la fecha y ruta elegidas y comprueba la combinación `(responsable, equipo)`.

- Si todas las líneas pertenecen a la misma combinación, ése es el contexto activo.
- Si no hay mercadería, no hay contexto de carga y no se crea ningún pallet.
- Si existe más de una combinación de chofer/equipo para esa fecha y ruta, el armado se bloquea como **carga ambigua**. Esto evita que el operador mezcle mercadería de dos camiones o dos choferes en el mismo conjunto de pallets.

La pantalla muestra además una leyenda con el chofer y el equipo de la carga activa.

## Migración de instalaciones existentes

`MigracionBaseDatos` agrega automáticamente las cuatro columnas nuevas a la tabla `pallet`.

Después intenta completar el contexto de pallets legacy:

1. toma los detalles existentes del pallet;
2. obtiene la `HojaDeRuta` de cada detalle;
3. si todos los detalles apuntan al mismo contexto fecha/ruta/chofer/equipo, guarda ese contexto en el pallet;
4. si el pallet está vacío o sus detalles pertenecen a más de un contexto, no inventa datos: queda sin contexto y se registra el caso cuando corresponde.

Un pallet legacy sin contexto no se muestra como pallet de una carga nueva, que es deliberadamente más seguro que asignarlo por fecha de creación o por aproximación.

## Lógica que no cambia

El cambio no modifica el funcionamiento de:

- agregar líneas completas;
- agregar cantidades parciales;
- quitar líneas;
- doble clic para mover mercadería;
- etiqueta y QR;
- totales por pallet y destino;
- confirmación de preparación;
- identificación técnica por `pallet_id` y `codigo`.

No se incorpora en este cambio configuración de Kg/pallet ni creación masiva por cantidad; la referencia visual solicitada se utiliza sólo como guía de jerarquía y ergonomía.

## Pruebas

`tests/test_armado_pallets.py` cubre, entre otros casos:

- carga y selección visual de pallets;
- cambio de pallet mediante clic en un chip;
- 20 pallets distribuidos en cuatro filas de cinco botones;
- actualización del indicador `PALLET ACTUAL: N`;
- límite de altura de la grilla de contenido;
- preservación del pallet seleccionado;
- filtrado por fecha, ruta, chofer y equipo;
- creación automática de un pallet con el contexto correcto al comenzar a paletizar;
- flujo de agregar y quitar mercadería.

Y los casos del KPI de KG:

- el KG se muestra grande como dato principal y el resumen de abajo sigue completo;
- el KPI cambia al cambiar de chip y no queda en `0 KG`;
- el peso se conserva al recargar el selector y se descarta el de otra carga;
- un pallet vacío muestra `0 KG`;
- con límite configurado muestra `Exceso`/`Disponible` y colorea el número;
- sin pallet seleccionado no se muestra línea de límite;
- el controlador pasa el límite configurado al KPI;
- leer el límite no inserta el parámetro en la base.

Los últimos se verificaron además **en las dos direcciones**: con el código de producción anterior los 9 tests nuevos fallan por el motivo esperado (`'ArmadoPalletsView' object has no attribute 'kpi_peso'` e `ImportError` de los helpers nuevos), no por un error ajeno.

## Bitácora

### Peso del pallet actual como KPI

El KG total estaba escondido en el resumen inferior (`Pallet: N líneas · N cant · N KG · N bultos`), una línea de texto chica entre varias. Es el número con el que el operador decide si el pallet se puede cerrar, así que se promovió a KPI del panel derecho.

Archivos:

- `vistas/ArmadoPallets.py`: nuevo widget `KpiPesoPallet`, cache de KG por pallet y `mostrar_totales()` acepta `limite_kg`;
- `utiles/pallets.py`: `formato_kg()`, `limite_kg_configurable()` y `estado_limite_kg()` (puras, sin Qt ni base);
- `controladores/ArmadoPallets.py`: `limite_kg_pallet()` y paso del límite en `refrescar_contenido()`.

### Bug encontrado durante la implementación

La primera versión de la cache de KG vaciaba el diccionario en cada `cargar_pallets()`. Como el controlador recarga el selector al crear o seleccionar otro pallet, volver a un chip ya visitado pintaba **`0 KG` en el momento del clic**, hasta que `mostrar_contenido()` traía el valor correcto.

Se detectó corriendo el flujo real con el controlador conectado, no con los tests: el test de vista pasaba porque escribía los totales de cada pallet en el orden correcto, y el flujo real los escribía en otro.

La corrección fue podar en lugar de vaciar: se conservan los KG de los pallets que siguen en pantalla y se descartan sólo los que ya no están. Queda cubierto por `test_kpi_peso_conserva_el_peso_al_recargar_pallets` y por `test_controlador_actualiza_el_kpi_al_cambiar_de_chip`.

## Pendientes

- [ ] Pantalla o parámetro para configurar `KG_LIMITE_PALLET`. Hoy el KPI ya lee el valor, pero no hay forma de cargarlo desde la interfaz.
- [ ] Decidir si el límite debería variar por tipo de producto o por destino, en lugar de un único valor por pallet.
- [ ] Llevar los colores del KPI al tema (`temas/vogel2026.qss`) en lugar de estilos en línea, como el resto de la pantalla, para que el cambio de tema siga funcionando.
- [ ] Evaluar una barra de progreso contra el límite: con un solo número, el operador tiene que hacer la resta a ojo.

## Referencias

- Issue: #144 — Mejorar selección de pallets y acotar por carga activa.
- PR: #143 — Pallets por carga con selector visual.

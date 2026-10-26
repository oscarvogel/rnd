# Guion de insistencia — Pruebas del demo RND (20/10/2026)

Contexto: el plazo venció el 15/10, el 16/10 Marcela dijo "Mañana se pone al día con esto
Lautaro" y al 20/10 no hay novedades. Objetivo de este documento: el guion de contacto
y las correcciones de contenido que hay que hacer **antes** de mandar, para que la
respuesta llegue y sirva.

---

## 1. Veredicto

**Sí conviene insistir**, pero no repitiendo la pregunta "¿pudieron hacer las pruebas?".

Ese formato no genera obligación: es una consulta de estado, sin fecha, sin responsable
y sin formato de respuesta, y es exactamente por lo que el hilo quedó en el aire dos
veces. Lo que hay que cambiar es el tipo de pedido:

| Lo que no funciona | Lo que funciona |
|---|---|
| "¿Pudieron realizar las pruebas?" (estado) | "¿Me confirman el día?" (compromiso) |
| Sin fecha | Fecha concreta y una consequence |
| Respuesta libre en prosa | Checklist de 8 puntos para devolver |
| "Avísen cualquier cosa" | Ofrecer 15 min de videollamada para destrabar |

El tono tiene que ser de "cerramos esto", no de "me están ignorando". La culpa produce
silencio; la fecha produce movimiento.

---

## 2. Correcciones de contenido (esto es lo importante)

Verificado contra el código de `C:\Programacion\RND` el 20/10/2026.

### 2.1 "Orden de despacho" no existe con ese nombre

No hay ninguna pantalla ni documento llamado "orden de despacho". El despacho es un
**estado de la hoja de ruta**:

```
EN_PREPARACION → LISTA → DESPACHADA
```

Se llega con el botón **"Confirmar salida a reparto"** (pantalla *Validar hoja de ruta*,
`vistas/ValidacionHojaRuta.py:92`) o con **"Continuar a despacho"** (*Ver Hoja de Ruta*,
`vistas/VerHojaRuta.py:180`).

> Si el mensaje pide "generar la orden de despacho", la respuesta va a ser "no existe esa
> opción" y se reporta como bug inexistente. Decir "dejar la hoja en DESPACHADA".

### 2.2 "Hoja de ruta" y "ruta" son dos cosas distintas

- **Ruta** = zona/destino: el demo tiene `CENTRO` y `NORTE`.
- **Hoja de ruta** = el documento que se genera para una fecha + una ruta.

El mensaje original mezcla ambos y genera un error de lectura al tester.

### 2.3 El manual ya cubre el paso de pallets (actualizado el 20/10)

El manual que se mandó el 14/10 **no tenía** el paso de pallets, y el checklist de
*Validar hoja de ruta* tiene un ítem extra, **"Pallets y carga del camión"**
(`utiles/carga_camion.py:63-105`):

| Situación | Resultado en el checklist |
|---|---|
| Sin pallets armados | **Informativo, no bloquea** (queda en verde) |
| Pallets armados + líneas sin asignar | PENDIENTE → frena LISTA y despacho |
| Todo asignado pero pallets sin CARGADO | PENDIENTE → frena LISTA y despacho |

**Resuelto el 20/10:** el manual se actualizó y ahora tiene un capítulo 4 completo
("Armar pallets y validar la carga"), con dos capturas reales y el paso de despacho.
Hay que **re-enviar el PDF actualizado**, no el del 14/10.

Reglas que el manual deja explícitas y que conviene repetir en el mensaje:

- **Confirmar preparación no cambia el estado.** El pallet sigue `ARMADO`. Recién en
  *Validar carga* pasa a `CARGADO`.
- Un pallet `CARGADO` **desaparece** de *Armado de pallets*: no se perdió, sigue en
  *Validar carga* y en el checklist. Es la confusión más probable del tester.
- El checklist se resuelve con **doble clic** sobre el renglón pendiente: RND abre la
  pantalla exacta donde se corrige.
- Para despachar: hoja `LISTA` → **Confirmar salida a reparto** → `DESPACHADA`. Una
  hoja despachada no retrocede automáticamente.

### 2.4 El link es rodante: no hace falta pasar uno nuevo

`scripts/release_demo.ps1:14-15` publica siempre sobre el tag `rnd-demo` con
`gh release upload --clobber`, o sea que la URL **siempre apunta a la última build**:

```
https://github.com/oscarvogel/vogel-releases/releases/download/rnd-demo/setup_rnd_demo.exe
```

Verificado hoy: HTTP 200. No mandar "les paso la última versión" — mandar el mismo link
y aclarar que se actualiza solo.

### 2.5 El demo no toca datos reales

`sistema.demo.ini` → `base = sqlite`, `basedatos = rnd_demo`. Los testers pueden
trabajar tranquilos, pero conviene decirlo: si alguien abre el MySQL de producción, no
está probando el demo.

### 2.6 El demo ya trae todo precargado (baja la fricción)

`demo_seed.py` crea: 4 proveedores demo (Tremblay, Tío Pujio, Detalle de ventas,
Columnas), 4 clientes, 2 rutas (CENTRO/NORTE), 2 choferes (Juan Gómez, Carlos Benítez),
camiones y una hoja en `LISTA` y otra en `EN_PREPARACION`.

Además genera **4 planillas de ejemplo, una por método de importación**
(`demo_seed.py:484-554`):

| Archivo | Proveedor / método |
|---|---|
| `01_tremblay_demo.xlsx` | Proveedor Demo - Tremblay |
| `02_tio_pujio_demo.xlsx` | Proveedor Demo - Tio Pujio |
| `03_detalle_ventas_demo.xlsx` | Proveedor Demo - Detalle Ventas |
| `04_columnas_demo.xlsx` | Proveedor Demo - Columnas |

Están en `C:\Programacion\RND\demo_importaciones\`. **Adjuntarlas al mail**: así el
tester no tiene que buscarlas dentro de la carpeta de instalación (en el build congelado
caen junto al módulo `demo_seed`, adentro de `_internal`).

El importador **no carga el remito** desde el archivo: queda vacío. Por eso el paso
"asociar remito a mano" no es opcional, es obligatorio. El remito se edita en
*Pedidos para organizar* → botón **Editar** (columna *Remito*), y después se ve en
*Ver Hoja de Ruta* (columna *Remito* y campo "Remito:").

---

## 3. Mensaje 1 — WhatsApp (al grupo, para que quede registrado)

```
Buen día, Marcela, Lautaro. Retomo el tema de las pruebas del demo de RND.

Como el plazo era el 15/10 y no tuve novedades, quiero cerrar la coordinación con una
fecha concreta y un formato de respuesta, así no lo dejamos flotando.

El instalador es el mismo link de siempre y siempre apunta a la última versión, así que
no hace falta que les pase nada nuevo:
https://github.com/oscarvogel/vogel-releases/releases/download/rnd-demo/setup_rnd_demo.exe
El manual es el PDF del 14/10, reenviado hoy con el capítulo de pallets incorporado.

Tres aclaraciones para que no se pierdan tiempo:
1. "Orden de despacho" no es un documento: es dejar la hoja en estado DESPACHADA con el
   botón "Confirmar salida a reparto".
2. El circuito a probar es: Importar pedidos → Grabar pedidos → Pedidos para organizar
   (asociar el remito a mano con "Editar" y organizar en una ruta) → Asignar chofer y
   camión → Armar pallets y validar la carga → Validar hoja de ruta ("Marcar LISTA") →
   Confirmar salida a reparto → Imprimir PDF.
3. Pallets: si no arman pallets, el circuito se completa igual y ese ítem del checklist
   queda como informativo. Si arman pallets, el paso 4 del manual los lleva (ojo:
   "Confirmar preparación" no cambia el estado, el pallet pasa a CARGADO recién en
   "Validar carga").

El demo ya viene con clientes, rutas, choferes y camiones cargados, y les adjunto las 4
planillas de ejemplo (una por cada método de importación) para que no tengan que buscar
archivos.

¿Me confirman dos cosas?
a) Quién hace la prueba y hasta qué día. Propongo viernes 23/10 a las 17:00.
b) Si se traban en algo, me avisan y lo resolvemos por videollamada de 15 minutos.

Cuando terminen, me mandan el PDF de la hoja de ruta + un pantallazo de la bandeja con
el remito asociado + la lista de pasos que salieron bien y los que no.

Gracias!
Oscar
```

---

## 4. Mensaje 2 — Mail (a Marcela, cc Lautaro, con el detalle)

**Asunto:** RND Demo — necesitamos cerrar las pruebas del circuito completo (propongo viernes 23/10)

Buen día, Marcela, Lautaro:

Les escribo para retomar las pruebas del demo de RND. El plazo era el 15/10 y no tuve
novedades, así que les propongo una fecha concreta para no dejarlo flotando.

**Qué probar** (el circuito completo, de punta a punta)

1. Instalar la última versión — es la misma URL de siempre y siempre apunta a la última
   build, así que no hace falta pasarles un link nuevo:
   https://github.com/oscarvogel/vogel-releases/releases/download/rnd-demo/setup_rnd_demo.exe
2. Importar pedidos: elegir **Proveedor/origen** y **Fecha reparto** antes de buscar el
   archivo, cargar una de las planillas de ejemplo que les adjunto (una por método de
   importación), revisar la vista previa y **Grabar pedidos**.
3. Pedidos para organizar: con **Editar**, asociar el remito a mano y dejar cliente,
   lugar de entrega y ruta correctos; después marcar las facturas y **Organizar
   seleccionados** con una ruta destino.
4. Asignar chofer y camión: en *Asignar chofer y camión*, **Cargar datos de hoja** y
   **Guardar asignación** (el demo ya tiene choferes y camiones de ejemplo).
5. Armar pallets y validar la carga (opcional, pero ya documentado): si arman pallets,
   el paso 4 del manual los lleva; si no arman, el circuito se completa igual y ese ítem
   del checklist queda como informativo. Ojo con un detalle: "Confirmar preparación" no
   cambia el estado, el pallet pasa a CARGADO recién en "Validar carga".
6. Validar hoja de ruta: **Revisar** el checklist y **Marcar LISTA**.
7. **Confirmar salida a reparto**: la hoja queda en estado DESPACHADA. Ojo con el
   nombre: no hay un documento "orden de despacho", eso es el estado de la hoja.
8. **Imprimir PDF** de la hoja de ruta. Si llega, generan también **Lista para Sergio**.

**Qué NO hace falta hacer**

- No se metan en la base real: el demo corre sobre una base propia (SQLite) y no toca
  MySQL de producción.

**Qué necesito de vuelta** (con esto me alcanza)

- El PDF de la hoja de ruta generada, adjunto al mail.
- Un pantallazo de *Pedidos para organizar* con el remito ya asociado.
- La lista de pasos que hicieron: los que salieron bien y los que no.
- Si algo no los deja seguir: un pantallazo del mensaje de error vale más que una
  descripción, y lo reviso el mismo día.

**Fecha**

¿Me confirman el día? Propongo **viernes 23/10 a las 17:00**. Si se complica, díganme y
lo corremos, pero necesito una fecha cerrada porque ya tengo otros compromisos de la
semana.

Cualquier duda o si se traban en un paso, hacemos una videollamada de 15 minutos con el
que quede. Coordinamos por ahí.

Gracias,
Oscar Vogel

---

## 5. Formato de respuesta que hay que pedirles

Pedir que respondan con esto (en el mail y recordarlo en el WhatsApp). Es lo que
convierte una respuesta en algo accionable:

```
1. Instalador: OK / falla (qué pasa)
2. Importación (qué proveedor y archivo usaste): OK / falla
3. Remito manual en Pedidos para organizar: OK / falla
4. Organizar en ruta: OK / falla
5. Asignar chofer y camión: OK / falla
6. Pallets (armar + validar carga): OK / falla / no lo hice
7. Marcar LISTA: OK / falla
8. Confirmar salida a reparto (DESPACHADA): OK / falla
9. Imprimir PDF: OK / falla
10. Adjunto: PDF de la hoja + pantallazo del remito
11. Tiempo total que te llevó: ___ minutos
```

El punto 11 no es menor: sirve para saber si el circuito es usable o si hay que
recortar pasos.

---

## 6. Pendientes propios (antes de que respondan)

1. **El manual sigue sin commitear.** `docs/manual_usuario_importacion_hoja_ruta.md`
   figura modificado (versión del 20/10, con el capítulo de pallets), y
   `docs/manual_usuario_hoja_ruta.docx` + `docs/manual_hoja_ruta/` están sin trackear.
   El PDF que mandaste al grupo está fuera del control de versiones. Commitearlo.
2. **Reenviar el PDF nuevo**, no el del 14/10: ahora incluye el capítulo 4 (pallets) y
   el paso de despacho, y el recorrido rápido cambió.
3. **Adjuntar las 4 planillas** desde `demo_importaciones\` al mail.
4. **Definir la fecha antes de mandar.** Si no hay compromiso de otra cosa el viernes,
   mandar el mensaje igual: la fecha propuesta es lo que obliga a responder.
5. **Preparar la videollamada de 15 minutos** con un entorno limpio: instalador
   descargado y al menos una de las planillas de ejemplo a mano. Resolver en vivo vale
   más que tres mails.
6. **El seed del demo congela la fecha de sus pedidos** en el día en que se creó la base
   (`get_or_create` por comprobante, `demo_seed.py:349-366`): si la base del demo ya
   existía de una corrida anterior, los pedidos demo quedan con la fecha vieja. Para
   los testers que instalan fresh no hay problema, pero si vas a reusar la base local,
   reseteala (menú DEMO → ResetDemo) antes de la videollamada.
7. **Si reconstruís el manual en otra máquina**: `python-docx` y `reportlab` no están en
   `requirements.txt` (son tooling del manual, no de la app). Los instalé en `.venv` para
   poder reconstruirlo acá.
8. **Regenerar el manual después de tocar el código**: hay tres textos que viven
   separados (el `.md`, `build_manual.py` y `build_pdf.py`) y un test nuevo
   (`test_manual_markdown_docx_y_pdf_estan_alineados`) avisa si se desincronizan.
   Receta: `capturar_manual.py` → `build_manual.py` → `build_pdf.py`.

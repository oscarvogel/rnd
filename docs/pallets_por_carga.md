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
- El pallet actual queda visualmente resaltado.
- Los botones se distribuyen hasta diez por fila.
- El tooltip conserva el código técnico completo (`PLT-AAAAMMDD-NNN`).
- La numeración visible es operativa; las operaciones internas siguen usando `pallet.id` y `pallet.codigo`.
- `Nuevo` crea un pallet dentro del contexto activo y lo deja seleccionado.

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

## Pruebas

`tests/test_armado_pallets.py` cubre, entre otros casos:

- carga y selección visual de pallets;
- cambio de pallet mediante clic en un chip;
- preservación del pallet seleccionado;
- filtrado por fecha, ruta, chofer y equipo;
- creación automática de un pallet con el contexto correcto al comenzar a paletizar;
- flujo de agregar y quitar mercadería.

## Referencias

- Issue: #144 — Mejorar selección de pallets y acotar por carga activa.
- PR: #143 — Pallets por carga con selector visual.

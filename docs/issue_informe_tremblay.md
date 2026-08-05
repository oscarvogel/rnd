## Contexto

Hoy `utiles/importacion_tremblay_excel.py` está atado al layout de `MISIONES-tremblay.xls` (pedido en col A, producto en col G, kilos en col K, etc). El nuevo `docs/informe tremblay.xls` tiene un layout distinto: es un **informe de despacho por cliente** con doble cabecera repetida por bloque. El `__main__` actual apunta a un path muerto (`o:/rnd/documentacion/MISIONES-tremblay.xls`) que ni siquiera existe en el repo.

## Layout del xls nuevo (436 filas, 11 columnas)

- Fila 0 vacía / fila 1 nombre del informe (ej `BONDA JOSE`) — **se descarta**
- Bloque por cliente:
  - Cabecera cliente: `cod_cliente | cliente | lugar_entrega+remito | fecha | pedido | bultos?`
  - Cabecera productos: `CODIGO | DETALLE | <vacías> | ORIGINAL | DESP. | DIF. | KG | TOTAL | COMPROB.`
  - 1..N filas de producto: `cod_producto | detalle | <vacías> | orig | desp | dif | kg | total | comprob`

## Decisiones tomadas

- **Cantidad → `DESP.`** (despachado real). Va a `HojaDeRuta.cantidad`.
- **Comprobante de `HojaDeRuta`**: se mantiene el propio del sistema. El comprobante del xls (que viene por producto) NO pisa ese campo. Se manda a `observaciones` con el formato `"Comprobante Tremblay: XXXXX"` para no perder el dato. Si se prefiere descartar directo, se cambia.
- **Fila "BONDA JOSE"**: se descarta (es cabecera del informe, no dato de cliente).
- **`.venv-build`**: se regenera en este PR. Adicional: revisar `requirements.txt` y agregar lo que falte (al menos `xlrd==2.0.2` ya está).

## Lo que hay que tocar

- Reescribir/parametrizar el parser en `utiles/importacion_tremblay_excel.py` (o nuevo módulo) para este layout con state machine que detecte cabecera-cliente → cabecera-productos → filas-producto.
- Mantener el contrato de salida que espera `ImportacionPedidosController`: columnas `cliente, nombre_cliente, producto, cantidad, kg, bultos, comprobante, observaciones`.
- Cablear desde `seleccionar_archivo()` cuando `empresa_proveedora == "15"` (Tremblay) y se elija un `.xls`.
- Reemplazar el path muerto del `__main__` por el archivo real (`docs/informe tremblay.xls`) o hacerlo parametrizable.
- Test con el archivo real commiteado en `tests/fixtures/`.
- Regenerar `.venv-build` con el Python activo del entorno de desarrollo.

## Out of scope

- Importador PDF Tremblay (`utiles/importacion_tremblay_pdf.py`) — otro formato, otro flujo
- Cambios al modelo `HojaDeRuta`
- Cambios a `ProcesoLista` (las columnas configurables se mantienen igual)

## Acceptance

- Cargar `docs/informe tremblay.xls` desde la UI con Tremblay seleccionado produce una grilla importable y graba `HojaDeRuta` con la misma UX que el importador viejo.
- Test unitario con el archivo commiteado en `tests/fixtures/` cubre al menos 3 clientes con productos.
- El `__main__` corre sin path muerto: `python -m utiles.importacion_tremblay_excel` (o similar) procesa el archivo commiteado y genera el xlsx de salida.
- `pytest tests/` corre con el venv nuevo sin el `ModuleNotFoundError: xlrd` que aparece hoy en este entorno.

## Notas técnicas detectadas durante el relevamiento

- El repo requiere `xlrd==2.0.2` (en `requirements.txt`) pero no está instalado en el Python del entorno de desarrollo. Hay que tenerlo presente al correr tests/parser.
- Hay dos variantes de importador PDF (`utiles/importacion_tremblay_pdf.py` con PyMuPDF y `utiles/importacion_tremblay_pdf - pdfplumber.py`). Quedan fuera de scope pero vale la pena unificar a futuro.

# Guía de uso del sistema RND

**Actualizada:** 07/10/2026

RND organiza pedidos y prepara hojas de ruta para reparto. Esta guía resume las
pantallas de trabajo actuales y las reglas operativas más importantes.

## Ingreso y pantalla principal

1. Abra RND.
2. Ingrese usuario y clave.
3. Use el panel principal para acceder a las funciones disponibles para su
   perfil.

Si una opción no aparece puede depender de permisos.

El Asistente RND se abre/cierra con **F1**. También puede cerrarse con **Esc** o
con la **X**.

## Datos maestros

Antes de operar conviene mantener:

- Clientes.
- Lugares de entrega.
- Proveedores.
- Códigos de cliente por proveedor.
- Rutas de reparto.
- Empleados/choferes.
- Equipos/camiones.
- Tablas auxiliares.

### Clientes y lugares de entrega

Un cliente puede tener varios destinos.

Cada lugar de entrega puede guardar:

- nombre o referencia;
- dirección;
- localidad;
- ruta;
- indicador de principal;
- activo/inactivo;
- observaciones.

No cree clientes duplicados sólo porque el mismo cliente reciba mercadería en
más de un lugar.

Para agregar lugares a un cliente nuevo, primero guarde el cliente.

### Códigos por proveedor

RND puede asociar el código que usa un proveedor con el cliente interno. Esa
relación tiene prioridad al identificar el cliente durante la importación.

### Consolidar clientes

Si existen clientes duplicados, la opción **Consolidar** permite simular primero
la operación y luego reasignar históricos, códigos y lugares al cliente que
quedará activo. Los clientes origen quedan inactivos.

## Proveedores

El proveedor debe existir y tener configurado su método de importación.

Los métodos actuales incluyen, según el caso:

- COLUMNAS;
- TREMBLAY;
- TIO_PUJIO;
- DETALLE_VENTAS.

La configuración del proveedor se utiliza especialmente para validar y
normalizar Excel.

## Importación de pedidos

Abra **Importar pedidos**.

### Formatos admitidos

RND acepta:

- Excel `.xlsx` y `.xls`;
- PDF `.pdf`;
- imágenes `.png`, `.jpg`, `.jpeg`.

PDF e imágenes se procesan con IA y se convierten internamente al formato de
vista previa. No hace falta convertirlos manualmente a Excel.

### Pasos

1. Seleccione **Proveedor / origen**.
2. Seleccione **Fecha reparto**.
3. Presione **Seleccionar archivo**.
4. Si es Excel, seleccione hoja y opcionalmente filas.
5. Presione **Cargar vista previa**.
6. Revise los datos.
7. Marque o desmarque las filas que corresponda.
8. Presione **Grabar pedidos**.
9. Revise el resumen.
10. Continúe al reparto o corrija pendientes.

### Particularidades de PDF/imagen

La extracción por IA se revisa antes de grabar:

- las celdas pueden editarse;
- las filas con **REVISAR IA** quedan desmarcadas;
- el operador decide si corregirlas y habilitarlas.

Si falta la configuración de IA o no se reconocen pedidos, RND muestra el error
sin grabar pedidos.

## Identificación de cliente, lugar y ruta

Al grabar:

1. RND busca primero cliente por código de proveedor.
2. Como respaldo intenta coincidencia exacta por razón social.
3. Para el lugar usa el principal; si no existe y hay un único lugar activo,
   usa ese.
4. Con varios lugares sin principal deja el destino pendiente.
5. La ruta se toma del lugar y, como respaldo, del cliente.

Los casos no resueltos se corrigen en **Pedidos para organizar**.

## Reimportación

RND identifica documentos y líneas para evitar duplicar una línea que ya está
vinculada a una hoja de ruta de la misma fecha.

Si una línea ya existe se informa como **ya existente/reimportada** y se conserva
la hoja de ruta previa.

Ante una interrupción de conexión, revise el resumen y los pedidos existentes
antes de repetir una importación.

## Pedidos para organizar

Esta pantalla agrupa el trabajo por factura/documento.

Una fila puede representar varias líneas de producto.

Funciones principales:

- fecha;
- Priorizar pendientes;
- buscar por factura;
- Editar;
- Productos;
- seleccionar facturas;
- Ruta destino;
- Organizar seleccionados;
- Asignar chofer y camión.

### Editar

Permite corregir:

- cliente;
- lugar de entrega;
- ruta;
- remito;
- observación general.

También permite abrir **Crear / editar clientes y lugares**.

### Productos

Muestra todas las líneas de la factura.

En este flujo sólo es editable **Cantidad a entregar**. Producto, cantidad
original, pendiente, KG, bultos y observaciones quedan como referencia.

La cantidad a entregar no puede ser negativa ni superar la cantidad original.

## Organizar una ruta

1. Seleccione una o más facturas.
2. Elija **Ruta destino**.
3. Presione **Organizar seleccionados**.

RND verifica en la base que todas las líneas hayan quedado con la ruta elegida.
Sólo después habilita **Asignar chofer y camión**.

## Asignar chofer y camión

La pantalla trabaja por fecha+ruta.

**Cargar hoja** carga o recarga esa combinación en la misma pantalla.

No existen filtros de chofer/camión en esta pantalla.

Seleccione un chofer real y un camión real y presione **Guardar asignación**.
Los recursos genéricos representan pendiente.

La asignación se aplica a todos los pedidos de la fecha+ruta y luego se verifica.

Puede continuar con:

- **Ver hoja de ruta ahora**;
- **Validar hoja de ruta**.

## Ver Hoja de Ruta

La pantalla consulta por fecha+ruta y puede sumar filtros opcionales de:

- chofer;
- camión.

Si no aparecen datos, revise los cuatro criterios.

Desde aquí se puede revisar el detalle, utilizar acciones legacy sobre líneas y
**Imprimir PDF**.

## Armado de pallets

La pantalla trabaja sobre una carga concreta: fecha de reparto, ruta, chofer y
camión. Los pallets de otra carga no se mezclan.

1. Seleccione **Fecha de reparto** y **Ruta de reparto**.
2. Presione **Cargar mercadería**.
3. En **Mercadería pendiente de preparar** seleccione una o más líneas y presione
   **Agregar selección al pallet**. **Agregar parcial…** carga una cantidad menor
   al saldo y **Quitar del pallet** saca líneas.
4. Use **+ Nuevo pallet** cuando necesite otro. Los pallets se muestran numerados:
   un clic cambia el pallet activo y el KPI muestra su peso.
5. **Etiqueta / QR** imprime la etiqueta del pallet seleccionado.
6. Presione **Confirmar preparación**.

El panel derecho muestra la composición del pallet activo: contenido, destinos,
totales y el peso actual.

Si hay un límite de peso configurado, el KPI agrega la línea `Límite: X KG ·
Exceso Y KG` o `Límite: X KG · Disponible Y KG`, en rojo o verde. Sin límite
configurado muestra sólo el peso.

### Los dos estados de un pallet

Un pallet puede estar en dos estados, y son distintos:

| Estado | Qué significa | Dónde se cambia |
|---|---|---|
| `ARMADO` | El pallet existe y tiene mercadería en el piso | Al crearlo en esta pantalla |
| `CARGADO` | El pallet fue subido al camión | En **Validar carga** |

**Confirmar preparación no cambia el estado.** Muestra el resumen del pallet y
nada más: el pallet sigue `ARMADO`. Para despachar hace falta el paso siguiente.

## Validar carga del camión

Se abre desde **Validar hoja de ruta**, con el botón **Validar carga**, o con
doble clic sobre el requisito `Carga del camión validada` del checklist.

Ahí se marca cada pallet a medida que se lo sube al camión. Tres formas:

- tildando el ítem de la lista;
- escaneando o escribiendo el código en el campo **Código** y presionando Enter.
  El campo se limpia solo, así que puede seguir escaneando sin usar el mouse;
- con **Marcar todos**, que tilda la lista completa de una vez. Pide confirmación
  con cuántos pallets son.

Presione **Guardar**: los tildados quedan `CARGADO` y los destildados vuelven a
`ARMADO`. Recién al guardar queda registrado quién cargó cada pallet y cuándo.

Presionar **Cancelar** no guarda nada y los pallets conservan su estado.

Tildar un pallet que después se destilda y se guarda lo devuelve a `ARMADO`: por
eso conviene tildar sólo lo que ya está efectivamente en el camión.

> Un pallet que pasa a `CARGADO` deja de aparecer en **Armado de pallets**. No se
> perdió: sigue visible en **Validar carga** y en el checklist.

## Validar hoja de ruta

El checklist exige:

- pedidos;
- fecha;
- ruta;
- único chofer real;
- único camión real;
- cliente;
- lugar de entrega;
- comprobante;
- cantidades mayores que cero.

Si se armaron pallets, se agregan dos requisitos más:

- mercadería asignada a pallets;
- carga del camión validada.

Si nunca se armaron pallets, esos dos requisitos no bloquean nada.

Estados:

- EN_PREPARACION;
- LISTA;
- DESPACHADA.

Una hoja sólo puede pasar a LISTA si el checklist es válido. DESPACHADA requiere
estar previamente LISTA y continuar válida.

Mientras quede un requisito pendiente, **Marcar LISTA** y **Confirmar salida a
reparto** permanecen deshabilitados. Para corregir un requisito puntual, haga
doble clic sobre la fila: RND abre la pantalla donde se resuelve.

## Imprimir hoja de ruta

Para imprimir deben estar completos:

- fecha;
- ruta;
- responsable/chofer;
- equipo/camión;
- pedidos.

La posibilidad de imprimir es independiente del estado LISTA.

## Buenas prácticas

- Seleccione proveedor y fecha antes del archivo.
- Siempre revise la vista previa.
- En PDF/imagen controle especialmente las filas marcadas REVISAR IA.
- Corrija cliente y lugar antes de cerrar el reparto.
- No duplique clientes por destino.
- Organice facturas completas cuando viajen juntas.
- Asigne chofer y camión antes de validar.
- Arme los pallets antes de validar la carga: confirmar preparación no alcanza.
- Tilde en **Validar carga** lo que ya está en el camión, no lo que va a ir.
- Si una consulta aparece vacía, distinga Asignación de Ver Hoja de Ruta:
  Asignación usa fecha+ruta; Ver Hoja puede tener además filtros de recursos.
- Ante una interrupción de importación, revise antes de repetir.

## Problemas frecuentes

### El PDF no importa

RND sí admite PDF. Revise proveedor, fecha, configuración de IA, calidad del
archivo y el mensaje mostrado por el procesamiento.

### La IA extrajo un dato incorrecto

Corrija la celda en la vista previa antes de grabar.

### Asignar chofer y camión muestra Sin pedidos

Revise fecha+ruta y que las facturas hayan sido organizadas en esa ruta.

### Ver Hoja de Ruta aparece vacía

Revise fecha+ruta y limpie o corrija los filtros opcionales de chofer/camión.

### No permite marcar LISTA

Revise el checklist de Validar hoja de ruta.

### Los pallets están armados y el checklist dice que no están validados

Son dos pasos distintos. **Confirmar preparación** no cambia el estado del
pallet: lo deja en `ARMADO`. El pallet pasa a `CARGADO` únicamente al marcarlo
en **Validar carga** y presionar **Guardar**.

Por eso el requisito `Carga del camión validada` sigue en PENDIENTE aunque los
pallets estén completos: falta registrar la carga. Ábrala con el botón **Validar
carga** o con doble clic sobre ese requisito.

### Tildé los pallets y presioné Guardar, pero no cambió nada

Si le aparece así, no es un error del operador: en versiones anteriores el
diálogo se cerraba sin guardar. Fue corregido. Si vuelve a ocurrir, tome nota de
si el checklist se actualizó al cerrar el diálogo, porque eso distingue si el
problema está en la pantalla o en la base.

### No habilita Confirmar salida a reparto

Es el mismo bloqueo del requisito pendiente: mientras el checklist tenga un
requisito en PENDIENTE no se puede marcar LISTA ni despachar. Haga doble clic
sobre la fila pendiente para ir directo a donde se corrige.

### El pallet que marqué como cargado desapareció de Armado de pallets

Es lo esperado: **Armado de pallets** muestra solamente los pallets `ARMADO`. El
pallet no se perdió, sigue en **Validar carga** y en el checklist.

### No permite imprimir

Complete fecha, ruta, chofer y camión y confirme que existan pedidos.

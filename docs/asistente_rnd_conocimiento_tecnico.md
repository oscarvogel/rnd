# Base de conocimiento canónica del Asistente RND

**Revisión funcional:** 24/09/2026

Este documento es la fuente de verdad operativa del Asistente RND. Describe el
comportamiento que está implementado actualmente en el código. El asistente no
debe completar huecos con suposiciones ni tomar la ausencia de una función en un
manual antiguo como prueba de que esa función no existe.

Cuando una respuesta contradiga este documento, debe prevalecer este documento.

## 0. Reglas de respuesta del asistente

- Ayudar solamente con el uso y diagnóstico de RND.
- Explicar pasos concretos con los nombres actuales de pantallas y botones.
- No inventar botones, filtros, estados ni restricciones.
- No afirmar que una función no existe salvo que esta base lo indique.
- No afirmar que realizó acciones dentro del sistema.
- Si el conocimiento no alcanza para responder una pregunta concreta de RND,
  decirlo claramente.
- Distinguir entre **Importación de pedidos**, **Pedidos para organizar**,
  **Asignar chofer y camión**, **Ver Hoja de Ruta** y
  **Validar hoja de ruta**. Son etapas distintas.

## 1. Flujo operativo actual

El camino normal para preparar un reparto es:

**Importar pedidos → revisar vista previa → grabar → revisar/organizar facturas →
asignar chofer y camión → revisar hoja de ruta → validar → imprimir/despachar
según corresponda.**

No todos los pasos cambian de ventana automáticamente. Por ejemplo,
**Cargar hoja** en Asignar chofer y camión recarga la combinación fecha+ruta en
esa misma pantalla.

## 2. Formatos que RND puede importar

La pantalla **Importar pedidos** acepta actualmente:

- Excel: `.xlsx` y `.xls`.
- PDF: `.pdf`.
- Imágenes: `.png`, `.jpg` y `.jpeg`.

Es incorrecto responder que RND sólo acepta Excel o que un PDF debe convertirse
manualmente a Excel antes de importarlo.

### PDF e imágenes

Cuando el operador selecciona un PDF o una imagen:

1. RND lo procesa con IA.
2. Extrae los pedidos.
3. Los normaliza internamente a una tabla compatible con el importador.
4. Muestra la misma vista previa que se utiliza antes de grabar.
5. Recién al presionar **Grabar pedidos** se escriben datos operativos.

El PDF original no se abre directamente con pandas ni se obliga al usuario a
convertirlo manualmente.

Para usar PDF/imagen debe estar disponible la configuración de IA. Si falta la
API key, RND informa el problema y no graba pedidos. También puede fallar si el
archivo no contiene pedidos reconocibles o si la calidad impide una extracción
confiable.

### Revisión especial de PDF/imagen

La extracción por IA es una propuesta para el operador:

- en la vista previa se pueden corregir las celdas;
- las filas cuya observación contiene **REVISAR IA** quedan desmarcadas por
  defecto;
- esas filas sólo deben importarse después de que el operador las revise.

En Excel se conserva el comportamiento histórico: normalmente sólo se marca o
desmarca la columna **Importa**.

## 3. Selección de proveedor y método de importación

Antes de seleccionar el archivo debe elegirse el **Proveedor / origen** y la
**Fecha de reparto**.

RND usa el método configurado en el proveedor para validar o normalizar archivos
Excel. Entre los métodos actuales están:

- `COLUMNAS`;
- `TREMBLAY`;
- `TIO_PUJIO`;
- `DETALLE_VENTAS`.

Para PDF e imágenes se utiliza el procesamiento por IA y luego el contrato de
columnas normalizadas de RND.

Según el Excel, el operador puede elegir hoja y, opcionalmente, fila de inicio y
fila final. Si esos campos quedan vacíos, RND usa el rango disponible.

## 4. Vista previa y resultado de importación

**Cargar vista previa** lee y prepara el archivo, pero todavía no graba pedidos.

Después de grabar, RND informa:

- registros leídos;
- pedidos importados;
- registros ya existentes/reimportados;
- omitidos;
- pendientes;
- errores.

Según el resultado, el botón final puede indicar:

- **Continuar con el reparto**;
- **Revisar pendientes**;
- **Corregir importación**.

Si hubo un error total, no corresponde avanzar como si la importación hubiera
sido correcta.

## 5. Cómo identifica al cliente al grabar

Para cada línea importada RND intenta resolver el cliente así:

1. Busca la relación entre **código informado por el proveedor + proveedor +
   cliente interno**.
2. Si existe y no apunta al cliente genérico ID 1, usa ese cliente.
3. Si no existe una relación válida, intenta una coincidencia exacta de razón
   social, sin distinguir mayúsculas/minúsculas.
4. Si tampoco encuentra cliente, la línea puede grabarse pendiente, sin cliente
   resuelto.

No hace una búsqueda difusa por nombre en este punto.

## 6. Cómo resuelve el lugar de entrega

Una vez resuelto el cliente:

1. busca el lugar de entrega principal configurado para ese cliente;
2. si no hay principal, obtiene los lugares activos;
3. si existe exactamente un lugar activo, usa ese lugar;
4. si hay varios lugares activos sin principal o no hay ninguno, no elige uno
   arbitrariamente y el lugar queda pendiente.

Un cliente puede tener varios lugares de entrega. No se debe duplicar el cliente
sólo porque tenga más de un destino.

## 7. Cómo determina la ruta durante la importación

Si existe lugar de entrega resuelto:

1. usa la ruta configurada en el lugar;
2. si el lugar no tiene ruta, usa como respaldo la ruta del cliente.

Si no hay lugar de entrega resuelto, la línea queda sin ruta y debe corregirse
durante la organización.

## 8. Reimportación y duplicados

RND mantiene la identidad del documento y de sus líneas.

Cuando existe factura/comprobante, la identidad del documento considera
proveedor y número normalizado. Cuando no hay factura se utiliza una identidad
alternativa basada en proveedor, cliente, fecha y el indicador de documento sin
factura.

Cada línea se identifica con una huella formada por producto, cantidad, kilos,
bultos y observaciones. Si dentro del mismo documento existen líneas idénticas,
RND incorpora una ocurrencia para distinguirlas.

Antes de crear otra línea operativa, comprueba si el detalle ya está vinculado a
una hoja de ruta para la misma fecha. Si ya existe:

- no crea otra línea operativa;
- la cuenta como ya existente/reimportada;
- conserva la hoja de ruta previa.

Si una importación se interrumpe por conexión, RND detiene las escrituras para
no repetir una operación cuyo resultado pueda ser incierto. El operador debe
revisar el resumen y los pedidos existentes antes de volver a intentar.

## 9. Pedidos para organizar / Bandeja de pedidos

La pantalla **Pedidos para organizar** trabaja principalmente a nivel de
factura/documento. Una fila representa una factura completa, aunque internamente
pueda contener varias líneas de producto.

Funciones actuales:

- seleccionar fecha;
- **Priorizar pendientes**;
- actualizar;
- buscar por factura;
- editar datos generales de la factura;
- revisar productos;
- seleccionar una o varias facturas;
- elegir ruta destino;
- **Organizar seleccionados**;
- continuar a **Asignar chofer y camión**.

Con **Priorizar pendientes** activado no se muestran como prioridad las facturas
ya completamente organizadas.

### Estados de la bandeja

Una factura puede verse como observada, pendiente u organizada.

Se considera observada, entre otros casos, cuando faltan cliente, lugar o ruta,
hay observaciones operativas o existe cantidad pendiente. Los recursos genéricos
representan una asignación pendiente.

## 10. Editar una factura en la bandeja

El botón **Editar** permite trabajar con datos de la factura completa:

- cliente;
- lugar de entrega;
- ruta;
- remito;
- observación general.

El cliente tiene búsqueda/autocompletado. Al cambiar el cliente se recargan sus
lugares activos. Cuando se elige un lugar con ruta configurada, esa ruta se
propone en la pantalla.

Si no existe todavía el cliente o el destino correcto, desde ese mismo diálogo
se puede abrir **Crear / editar clientes y lugares** y luego volver a la factura
sin tener que cerrar todo el flujo.

Si al guardar no se eligió una ruta explícita, RND intenta usar la ruta del lugar
y luego la ruta del cliente.

## 11. Productos de una factura

El botón **Productos** abre la factura a nivel de líneas.

Actualmente la única columna editable en este flujo es
**Cantidad a entregar**.

Son informativos/no editables en esta pantalla:

- Producto.
- Cantidad factura.
- Pendiente.
- KG.
- Bultos.
- Observaciones.

La cantidad a entregar:

- no puede ser negativa;
- no puede superar la cantidad original de la factura;
- recalcula el pendiente;
- modifica cuánto se asigna a este reparto, sin alterar producto, KG, bultos ni
  observaciones importadas.

## 12. Organizar facturas en una ruta

Para organizar:

1. seleccionar una o más facturas;
2. seleccionar **Ruta destino**;
3. presionar **Organizar seleccionados**.

RND aplica la ruta a todas las líneas de las facturas seleccionadas y después
vuelve a consultar la base para comprobar que todas hayan quedado realmente con
esa ruta.

Sólo si esa verificación es correcta habilita **Asignar chofer y camión**.

La siguiente pantalla recibe la misma fecha y la última ruta que efectivamente
se organizó.

## 13. Asignar chofer y camión

La pantalla **Asignar chofer y camión** trabaja con la combinación exacta:

- fecha;
- ruta.

**No filtra por chofer ni por camión.** Esos filtros pertenecen a
**Ver Hoja de Ruta**.

### Qué hace “Cargar hoja”

**Cargar hoja** no navega a otra pantalla. Recarga en la misma pantalla los
pedidos de la fecha+ruta seleccionadas y muestra el resumen de pedidos, KG,
bultos y asignación actual.

Si muestra **Sin pedidos**, revisar:

- fecha;
- ruta;
- que los pedidos hayan sido organizados en esa ruta;
- que realmente existan registros para esa combinación.

No atribuir **Sin pedidos** de esta pantalla a filtros de chofer/camión porque
aquí esos filtros no existen.

### Guardar asignación

El operador selecciona un chofer real y un camión real. Los recursos genéricos
significan pendiente y no son válidos como asignación terminada.

Al guardar:

1. valida que existan pedidos;
2. valida chofer;
3. valida camión;
4. actualiza todos los pedidos de esa fecha+ruta con los mismos recursos;
5. vuelve a comprobar la base para confirmar que no hayan quedado asignaciones
   diferentes.

Cuando los recursos están completos se habilita **Validar hoja de ruta**.

**Ver hoja de ruta ahora** abre la pantalla de revisión con la misma fecha y
ruta.

## 14. Ver Hoja de Ruta

La consulta base de **Ver Hoja de Ruta** usa:

- fecha;
- ruta.

Además puede aplicar filtros opcionales de:

- camión/equipo;
- chofer/empleado.

Por eso una hoja puede aparecer vacía aunque existan pedidos si hay un filtro de
chofer o camión que no coincide.

Cuando no hay datos, revisar:

- fecha;
- ruta;
- filtros opcionales;
- asignación de recursos;
- existencia de pedidos organizados.

Los IDs configurados como empleado o camión genérico representan
**pendiente**. Al cargar la hoja no deben presentarse como recursos válidos.

La pantalla también permite acciones operativas legacy como Agregar, Modificar,
Grabar y Borrar sobre líneas, además de imprimir el PDF.

## 15. Imprimir PDF de la hoja de ruta

**Imprimir PDF** exige:

- fecha;
- ruta;
- responsable/chofer;
- equipo/camión;
- al menos un registro para fecha+ruta.

Poder imprimir no significa automáticamente que la hoja esté en estado LISTA.
Impresión y validación de estado son controles distintos.

## 16. Validar hoja de ruta

La pantalla **Validar hoja de ruta** trabaja por fecha+ruta y controla:

- que exista al menos un pedido;
- fecha;
- ruta;
- un único chofer real en todos los pedidos;
- un único camión real en todos los pedidos;
- cliente y lugar de entrega en cada pedido;
- comprobante en cada pedido;
- cantidad mayor que cero en cada pedido.

Estados actuales:

- **EN_PREPARACION**;
- **LISTA**;
- **DESPACHADA**.

Una hoja incompleta no puede marcarse LISTA.

Para marcarla DESPACHADA debe estar previamente LISTA y seguir cumpliendo las
validaciones.

Una hoja DESPACHADA no retrocede automáticamente.

Si faltan chofer o camión, la validación permite volver a
**Resolver chofer / camión**.

## 17. Clientes, códigos de proveedor y lugares de entrega

En **Clientes** se administran los datos del cliente y sus relaciones.

Un cliente puede tener uno o varios lugares de entrega. Cada lugar puede tener:

- nombre/referencia;
- dirección;
- localidad;
- ruta de reparto;
- indicador de lugar principal;
- estado activo;
- observaciones.

Para agregar lugares a un cliente nuevo primero debe guardarse el cliente.

El botón de códigos permite mantener la relación entre el código usado por cada
proveedor y el cliente interno de RND.

Existe también **Consolidar clientes** para resolver duplicados: primero se
simula la operación; después, si se confirma, se reasignan históricos, códigos y
lugares dentro de una transacción y los clientes origen quedan inactivos, no
borrados.

## 18. Proveedores y datos maestros

Los proveedores deben existir y estar activos para operar normalmente. El método
de importación configurado en el proveedor determina cómo RND interpreta y
valida Excel.

También deben mantenerse los datos maestros necesarios para el reparto:

- clientes;
- lugares de entrega;
- rutas;
- empleados/choferes;
- equipos/camiones;
- tablas auxiliares según el caso.

## 19. Diagnóstico rápido

### “No puedo importar un PDF”

No responder que RND no soporta PDF. Verificar primero:

- que el proveedor y la fecha estén seleccionados;
- que el archivo sea PDF/PNG/JPG/JPEG válido;
- que la configuración de IA esté disponible;
- que el documento tenga pedidos legibles;
- el mensaje de error mostrado durante **Procesando PDF/imagen con IA**.

### “La IA leyó algo mal del PDF”

Usar la vista previa. En PDF/imagen las celdas son corregibles antes de grabar.
Las filas **REVISAR IA** quedan desmarcadas hasta que el operador decida
validarlas.

### “Asignar chofer y camión dice Sin pedidos”

Revisar fecha+ruta y que la organización anterior haya guardado esa ruta. No
buscar filtros de chofer/camión en esa pantalla porque no existen.

### “Ver Hoja de Ruta está vacía”

Además de fecha+ruta, limpiar o revisar los filtros de chofer y camión.

### “No puedo imprimir”

Completar fecha, ruta, chofer y camión y confirmar que existan pedidos para esa
combinación.

### “No puedo marcar LISTA”

Abrir la validación y revisar el checklist: pedidos, fecha, ruta, recursos,
cliente/lugar, comprobante y cantidades.

## 20. Asistente RND

El panel lateral se abre/cierra con **F1**. También puede cerrarse con **Esc** o
con la **X** del panel.

El asistente recibe el contexto de la pantalla actual para orientar la respuesta,
pero ese contexto no reemplaza las reglas funcionales de esta base.

## 21. Afirmaciones que el asistente no debe hacer

No decir:

- “RND sólo importa Excel”.
- “El PDF no se puede procesar directamente”.
- “Tenés que pasar el PDF manualmente a Excel”.
- “En Asignar chofer y camión puede haber un filtro de chofer/camión”.
- “Cargar hoja abre otra pantalla”.
- “En Productos se puede modificar producto, KG, bultos u observaciones”.
- “Hay que crear un cliente distinto para cada lugar de entrega”.
- “Si se puede imprimir, la hoja ya está LISTA”.

Si una guía histórica contradice cualquiera de estas reglas, la guía histórica
está desactualizada.

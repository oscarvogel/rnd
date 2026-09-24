# Manual de usuario — Importación de pedidos y generación de hoja de ruta

**Actualizado:** 24/09/2026

Este manual describe el flujo operativo actual de RND desde la recepción del
archivo del proveedor hasta la preparación de la hoja de ruta.

Flujo recomendado:

**Importar → revisar vista previa → grabar → organizar facturas → asignar chofer
y camión → revisar hoja → validar → imprimir / despachar**

---

## 1. Antes de empezar

Verifique que estén disponibles:

- proveedor/origen;
- fecha de reparto;
- clientes;
- lugares de entrega;
- rutas;
- choferes/empleados;
- equipos/camiones.

Un cliente puede tener varios lugares de entrega. No duplique clientes sólo por
tener distintos destinos.

---

## 2. Importar pedidos

Abra **Importar pedidos**.

### Paso 1 — Elegir proveedor y fecha

Seleccione:

- **Proveedor / origen**
- **Fecha reparto**

RND usa la configuración del proveedor para preparar el archivo.

### Paso 2 — Seleccionar archivo

Presione **Seleccionar archivo**.

RND acepta:

- Excel: `.xlsx`, `.xls`;
- PDF: `.pdf`;
- imágenes: `.png`, `.jpg`, `.jpeg`.

### Si el archivo es Excel

RND usa el método configurado para ese proveedor. Según el formato puede
normalizarlo antes de mostrarlo.

Puede seleccionar hoja y, si hace falta, indicar fila de inicio y fila final.

### Si el archivo es PDF o imagen

RND procesa el documento con IA, extrae los pedidos y los convierte
internamente al formato de la vista previa.

**No es necesario convertir el PDF manualmente a Excel.**

Si falta la configuración de IA o el archivo no contiene pedidos reconocibles,
RND muestra el error y no graba nada.

---

## 3. Revisar la vista previa

Presione **Cargar vista previa**.

En este momento todavía no se graban pedidos.

Controle:

- cliente;
- comprobante/factura;
- producto;
- cantidad;
- KG;
- bultos;
- observaciones.

### PDF / imagen

Cuando el origen es PDF o imagen:

- las celdas pueden corregirse antes de grabar;
- las filas marcadas **REVISAR IA** quedan desmarcadas por defecto;
- el operador decide si las corrige y habilita.

### Excel

En el flujo Excel se mantiene el comportamiento histórico: normalmente se
marca o desmarca la columna **Importa**.

---

## 4. Grabar pedidos

Cuando la vista previa sea correcta presione **Grabar pedidos**.

RND muestra un resumen con:

- registros leídos;
- importados;
- ya existentes;
- omitidos;
- pendientes;
- errores.

Según el resultado aparecerá una acción como:

- **Continuar con el reparto**;
- **Revisar pendientes**;
- **Corregir importación**.

Si la conexión se interrumpe durante una escritura, RND detiene la importación.
Revise el resumen y los pedidos existentes antes de repetir la operación.

---

## 5. Cómo resuelve cliente, lugar y ruta

Al grabar, RND intenta primero identificar al cliente por el código que usa el
proveedor. Si no existe esa relación, intenta coincidencia exacta por razón
social.

Para el lugar de entrega:

1. usa el lugar principal si existe;
2. si no hay principal y existe un solo lugar activo, usa ese;
3. si hay varios lugares sin principal, deja el lugar pendiente.

Para la ruta:

1. usa la ruta del lugar;
2. si el lugar no tiene ruta, usa la ruta del cliente.

Los casos pendientes se corrigen en la bandeja antes de finalizar el reparto.

---

## 6. Pedidos para organizar

Abra **Pedidos para organizar**.

La pantalla trabaja a nivel de factura/documento: una fila puede representar
varias líneas de producto.

Puede:

- cambiar la fecha;
- activar/desactivar **Priorizar pendientes**;
- buscar por factura;
- **Editar** una factura;
- abrir **Productos**;
- seleccionar facturas;
- elegir **Ruta destino**;
- presionar **Organizar seleccionados**.

### Editar factura

Permite modificar:

- cliente;
- lugar de entrega;
- ruta;
- remito;
- observación general.

Si falta el cliente o el destino, use **Crear / editar clientes y lugares**.

### Productos

Muestra:

- producto;
- cantidad factura;
- cantidad a entregar;
- pendiente;
- KG;
- bultos;
- observaciones.

En esta pantalla **sólo se modifica Cantidad a entregar**.

La cantidad no puede ser negativa ni superar la cantidad original de la factura.

---

## 7. Organizar en una ruta

Seleccione una o más facturas, elija **Ruta destino** y presione
**Organizar seleccionados**.

RND verifica contra la base que todas las líneas hayan quedado con esa ruta.
Sólo entonces habilita **Asignar chofer y camión**.

---

## 8. Asignar chofer y camión

La pantalla trabaja por:

- fecha;
- ruta.

### Cargar hoja

**Cargar hoja** recarga los pedidos de la fecha+ruta en la misma pantalla. No
abre otra ventana.

Si aparece **Sin pedidos**, revise fecha, ruta y que las facturas se hayan
organizado en esa ruta.

Esta pantalla no usa filtros de chofer o camión.

### Guardar asignación

Seleccione:

- chofer/responsable;
- camión/equipo.

Presione **Guardar asignación**.

RND aplica los mismos recursos a todos los pedidos de esa fecha+ruta y luego
verifica que no hayan quedado asignaciones mezcladas.

Puede usar **Ver hoja de ruta ahora** para revisar el resultado o
**Validar hoja de ruta** para continuar con el checklist.

---

## 9. Ver Hoja de Ruta

Seleccione fecha y ruta y presione **Actualizar**.

En esta pantalla sí existen filtros opcionales de:

- camión;
- chofer.

Si la hoja aparece vacía, revise también esos filtros.

Los recursos genéricos significan pendiente y no deben considerarse una
asignación terminada.

---

## 10. Validar hoja de ruta

La validación exige:

- al menos un pedido;
- fecha;
- ruta;
- un único chofer real;
- un único camión real;
- cliente y lugar de entrega;
- comprobante;
- cantidades mayores que cero.

Estados:

- **EN_PREPARACION**
- **LISTA**
- **DESPACHADA**

Una hoja sólo puede pasar a LISTA si cumple el checklist. Para pasar a
DESPACHADA debe estar LISTA y seguir siendo válida.

---

## 11. Imprimir PDF

En **Ver Hoja de Ruta**, **Imprimir PDF** exige:

- fecha;
- ruta;
- chofer;
- camión;
- pedidos para esa combinación.

Poder imprimir no significa por sí mismo que la hoja esté marcada LISTA.

---

## 12. Problemas frecuentes

### “El PDF no importa”

RND sí soporta PDF. Revise:

- proveedor;
- fecha;
- configuración de IA;
- calidad/legibilidad del documento;
- mensaje mostrado durante el procesamiento.

### “La IA leyó mal una fila”

Corrija la vista previa antes de grabar. Las filas **REVISAR IA** quedan
desmarcadas hasta su revisión.

### “Asignar chofer y camión dice Sin pedidos”

Revise fecha+ruta y que la organización anterior haya guardado esa ruta.

### “Ver Hoja de Ruta no muestra nada”

Revise fecha, ruta y también los filtros opcionales de chofer/camión.

### “No puedo marcar LISTA”

Use el checklist de Validar hoja de ruta para identificar el dato faltante.

### “No puedo imprimir”

Complete fecha, ruta, chofer y camión y confirme que existan pedidos.

---

## 13. Asistente RND

El Asistente RND puede abrirse/cerrarse con **F1**. También puede cerrarse con
**Esc** o con la **X**.

Puede preguntarle por el paso siguiente o por un error de la pantalla actual.

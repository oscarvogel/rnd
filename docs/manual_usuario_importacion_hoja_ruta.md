# Manual de usuario — Importación de pedidos y generación de hoja de ruta

## Objetivo

Este documento explica el flujo operativo para un usuario nuevo de RND Logística, desde la importación de pedidos hasta la generación de la hoja de ruta.

Flujo general:

**Importar pedidos → revisar → organizar → asignar chofer y camión → revisar hoja de ruta → imprimir**

---

## 1. Antes de empezar

Verifique que:

- El proveedor/origen de los pedidos exista en el sistema.
- El proveedor tenga configurado su método de importación.
- Los clientes estén cargados.
- Los clientes que tengan más de un destino tengan sus lugares de entrega correctamente definidos.
- Las rutas de reparto estén disponibles.
- Los empleados/choferes estén cargados.
- Los equipos/camiones estén cargados.
- Conozca la fecha de reparto correspondiente a los pedidos.

> **Importante:** cliente y lugar de entrega son conceptos distintos. El cliente identifica a quién se vende y el lugar de entrega indica dónde se entrega. No se debe duplicar un cliente solamente porque tenga más de un destino.

---

# 2. Importación de pedidos

## Paso 1 — Abrir Importación de pedidos

Desde el menú principal ingrese a **Importación de pedidos**.

La ventana se abre maximizada para facilitar la revisión de los datos.

## Paso 2 — Seleccionar proveedor y fecha

Seleccione:

- **Proveedor / origen**
- **Fecha de reparto**

El proveedor es importante porque RND utiliza su configuración para interpretar correctamente el archivo importado.

## Paso 3 — Seleccionar el archivo

Presione **Examinar** y seleccione el archivo Excel recibido.

RND analiza el archivo y, cuando corresponde, lo normaliza utilizando el método de importación configurado para ese proveedor.

## Paso 4 — Seleccionar hoja y rango

Si el Excel contiene varias hojas:

1. Seleccione la hoja correcta.
2. Revise la fila donde se encuentran los encabezados.
3. Si corresponde, indique la fila final del rango a importar.

## Paso 5 — Cargar vista previa

Presione **Cargar vista previa**.

En este momento **todavía no se graban pedidos**.

Revise especialmente:

- Cliente
- Comprobante / factura
- Producto
- Cantidad
- Kilos
- Bultos
- Observaciones

Las filas que no deban importarse pueden desmarcarse.

### Antes de continuar verifique

- [ ] Proveedor correcto
- [ ] Fecha de reparto correcta
- [ ] Comprobante o factura visible
- [ ] Producto correcto
- [ ] Cantidad correcta
- [ ] Cliente identificable
- [ ] No hay filas de títulos, subtotales o datos basura

---

# 3. Grabar los pedidos

## Paso 6 — Grabar pedidos

Cuando la vista previa sea correcta, presione **Grabar pedidos**.

RND procesa únicamente las filas seleccionadas.

Durante este proceso pueden ocurrir distintas situaciones.

### Cliente reconocido

El pedido se incorpora normalmente y queda disponible para organizarlo en el reparto.

### Cliente pendiente de identificar

Si el código del proveedor todavía no está asociado a un cliente interno, RND puede solicitar que se busque o asocie el cliente.

Si no se logra resolver correctamente, el pedido no debe considerarse listo para despacho.

### Error de conexión o formato

Si RND informa una interrupción o error durante la importación, no repita la operación automáticamente.

Primero revise el mensaje para evitar importar dos veces los mismos pedidos.

---

# 4. Organizar pedidos

## Paso 7 — Abrir Bandeja de pedidos

Después de importar, ingrese a **Bandeja de pedidos** / **Organizar pedidos**.

Seleccione la misma fecha utilizada durante la importación.

## Paso 8 — Buscar y seleccionar pedidos

Utilice los filtros disponibles para encontrar los pedidos.

Cuando corresponda, puede buscar por **factura/comprobante** y seleccionar todos los renglones pertenecientes a la misma factura.

Esto evita organizar producto por producto cuando toda la factura debe viajar junta.

## Paso 9 — Revisar cliente y lugar de entrega

Antes de asignar una ruta verifique:

- Cliente correcto
- Lugar de entrega correcto
- Factura/comprobante correcto
- Productos incluidos
- Cantidades correctas

Ejemplo:

Un mismo cliente puede tener:

- Puerto Rico
- San Vicente

En ese caso debe existir **un solo cliente con dos lugares de entrega**, no dos clientes duplicados.

## Paso 10 — Seleccionar ruta de reparto

Seleccione los pedidos que viajarán juntos.

Luego seleccione la ruta destino, por ejemplo:

- Centro
- Norte
- Sur
- Otra ruta configurada

Presione **Organizar selección**.

RND verifica que la ruta haya quedado realmente grabada antes de permitir continuar.

---

# 5. Asignar chofer y camión

## Paso 11 — Continuar a asignación

Después de organizar los pedidos en una ruta, presione **Siguiente**.

RND abre la asignación correspondiente a:

- La misma fecha
- La ruta recién organizada

## Paso 12 — Seleccionar responsable / chofer

Seleccione el empleado responsable del viaje.

No deje el empleado genérico cuando la hoja de ruta ya vaya a utilizarse operativamente.

## Paso 13 — Seleccionar equipo / camión

Seleccione el camión o equipo que realizará el reparto.

No deje el equipo genérico cuando el viaje ya esté definido.

## Paso 14 — Guardar

Grabe la asignación.

Verifique que todos los pedidos correspondientes a la ruta hayan quedado asociados al chofer y al camión correctos.

---

# 6. Revisar la hoja de ruta

## Paso 15 — Abrir Ver Hoja de Ruta

Ingrese a **Ver Hoja de Ruta**.

Seleccione:

- Fecha
- Ruta

## Paso 16 — Cargar y controlar

Revise la grilla completa.

Verifique:

- Cliente
- Factura / comprobante
- Producto
- Cantidad
- Kilos
- Bultos
- Observaciones
- Chofer
- Camión

## Paso 17 — Corregir antes de imprimir

Si detecta un error, corríjalo antes de generar el documento final.

Según el caso puede utilizar:

- **Modificar**
- **Agregar**
- **Borrar**

No entregue una hoja de ruta con datos incorrectos para corregirla después.

---

# 7. Generar la hoja de ruta

## Paso 18 — Imprimir

Cuando estén completos:

- Fecha
- Ruta
- Responsable / chofer
- Equipo / camión

presione **Imprimir**.

RND genera el PDF de la hoja de ruta con los pedidos correspondientes.

---

# 8. Checklist final

Antes de entregar la hoja de ruta confirme:

- [ ] La fecha es correcta.
- [ ] Todos los pedidos que deben viajar están incluidos.
- [ ] Todas las líneas correspondientes a una factura están incluidas.
- [ ] Cada pedido tiene el cliente correcto.
- [ ] Cada pedido tiene el lugar de entrega correcto.
- [ ] La ruta es correcta.
- [ ] El chofer es correcto.
- [ ] El camión/equipo es correcto.
- [ ] Las cantidades son correctas.
- [ ] Los kilos son correctos.
- [ ] Los bultos son correctos.
- [ ] Las observaciones necesarias están visibles.
- [ ] El PDF corresponde a la fecha y ruta revisadas.

---

# 9. Problemas frecuentes

## Elegí el archivo pero no aparecen los datos

Revise:

- Proveedor seleccionado
- Hoja del Excel
- Fila de encabezados
- Formato del archivo

## El producto aparece vacío

No continúe con la organización.

Puede existir una diferencia entre el formato recibido y el método de importación configurado para ese proveedor.

## El cliente no coincide

Resuelva la asociación del cliente antes de cerrar el reparto.

## Falta el lugar de entrega

Asigne o cree el lugar de entrega correspondiente antes de finalizar la hoja de ruta.

## Organicé una factura pero no aparece donde esperaba

Verifique:

- Fecha
- Ruta seleccionada
- Pedidos seleccionados
- Que se haya incluido toda la factura

Luego actualice la bandeja.

## No puedo imprimir la hoja de ruta

Verifique que estén completos:

- Fecha
- Ruta
- Responsable
- Equipo

y que existan pedidos para esa combinación.

---

# Flujo resumido

| Paso | Acción | Resultado esperado |
|---|---|---|
| 1 | Seleccionar proveedor, fecha y archivo | Archivo listo para procesar |
| 2 | Cargar vista previa | Pedidos visibles para revisar |
| 3 | Grabar pedidos | Pedidos incorporados |
| 4 | Revisar cliente y lugar de entrega | Destinos definidos |
| 5 | Seleccionar pedidos/factura y organizar | Pedidos asignados a una ruta |
| 6 | Asignar chofer y camión | Recursos del viaje definidos |
| 7 | Ver Hoja de Ruta | Revisión final |
| 8 | Imprimir | PDF operativo generado |

---

## Regla recomendada para usuarios nuevos

Trabajar siempre en este orden:

**Importar → Revisar → Organizar → Asignar → Revisar nuevamente → Imprimir**

Esto reduce errores y evita que una hoja de ruta llegue a operación con pedidos, destinos o recursos incorrectos.

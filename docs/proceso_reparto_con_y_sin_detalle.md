# RND - Proceso de preparación de reparto con información completa o incompleta

## Objetivo

RND debe permitir preparar un reparto aunque los proveedores no entreguen siempre la información de la misma manera.

Hay dos situaciones normales:

1. el proveedor envía un archivo o documento con todos los artículos;
2. la mercadería llega con una factura o remito, pero sin un informe detallado que pueda importarse.

Los dos casos deben poder terminar en el mismo reparto.

---

## Caso 1 - El proveedor envía el detalle de productos

Este es el proceso más completo.

### 1. Recibir la información

RND puede recibir el detalle desde:

- Excel;
- PDF;
- imagen o documento escaneado procesado con IA;
- otros formatos configurados para el proveedor.

### 2. Revisar lo importado

El sistema identifica:

- proveedor;
- cliente;
- factura o remito;
- lugar de entrega;
- artículos;
- cantidades;
- kg y bultos cuando están disponibles.

Si algún dato no coincide o falta, el operador lo corrige antes de continuar.

### 3. Organizar el reparto

Se asignan:

- ruta;
- cliente correcto;
- lugar de entrega;
- chofer;
- camión.

### 4. Armar pallets

Los artículos pendientes aparecen en la pantalla de armado.

El operador selecciona el pallet y mueve la mercadería que físicamente se está colocando allí.

RND puede controlar:

- qué artículos están en cada pallet;
- cantidades;
- kg;
- bultos;
- saldos todavía no preparados.

### 5. Validar la carga

Cuando los pallets se suben al camión, el operador confirma cuáles fueron cargados.

El sistema evita despachar si quedó mercadería detallada sin preparar o pallets pendientes de cargar.

### 6. Emitir la hoja de ruta

La hoja de ruta indica:

- cliente;
- lugar de entrega;
- pallets;
- factura/remito;
- artículos y cantidades cuando se conocen.

---

## Caso 2 - Llega una factura o remito sin detalle de artículos

Este caso debe ser igual de válido para la operación.

Ejemplo:

La mercadería está en el depósito y debe salir el jueves, pero el proveedor no envió el archivo con los productos. RND dispone de una factura física o un remito.

No es necesario inventar artículos ni cantidades para poder preparar el reparto.

### 1. Incorporar el documento

El operador puede hacerlo de dos maneras.

#### Escanear o fotografiar

Se escanea la factura/remito o se carga una imagen.

La IA intenta reconocer:

- tipo de documento;
- número;
- proveedor;
- cliente;
- domicilio;
- localidad;
- artículos, si se pueden leer.

Si reconoce la factura y el cliente pero no logra identificar con seguridad los artículos, el documento sigue siendo válido.

RND informa:

**Documento reconocido - Sin detalle de artículos**

#### Carga manual rápida

Si no se desea escanear, el operador puede ingresar solamente:

- proveedor;
- factura o remito;
- número;
- cliente;
- lugar de entrega.

Con eso alcanza para incorporar la entrega al reparto.

### 2. Organizar el reparto

El documento aparece junto con el resto de las entregas.

Por ejemplo:

- Cliente A - Factura 12345 - 8 productos
- Cliente B - Remito 88721 - Sin detalle
- Cliente C - Factura 44210 - 12 productos

La leyenda **Sin detalle** es informativa. No significa que la entrega esté mal.

El sistema sólo debe impedir continuar si falta información necesaria para entregar, por ejemplo:

- cliente;
- lugar de entrega;
- documento identificable;
- ruta.

### 3. Mandar el documento al pallet

El operador selecciona el pallet donde físicamente se encuentra esa mercadería.

Ejemplo:

**Pallet 7**

- Factura 12345 - Cliente A - con detalle
- Factura 88721 - Cliente B - sin detalle
- Remito 33008 - Cliente C - sin detalle

RND registra que esos documentos viajan en el pallet 7.

No crea un artículo ficticio "SIN DETALLE" ni una cantidad artificial.

### 4. Validar la carga

Cuando el pallet 7 se carga al camión, se confirma normalmente.

Aunque no se conozcan los artículos de una factura, RND sabe que:

- la entrega existe;
- pertenece al cliente correcto;
- está en una ruta;
- está dentro de un pallet concreto;
- ese pallet fue cargado.

### 5. Emitir la hoja de ruta

La hoja puede mostrar:

**Entrega 03 - Supermercado López**  
Sucursal Eldorado - Av. San Martín 1234

**Pallet 7**

Factura 0004-001254  
- Queso Tybo - 20
- Cremoso - 15

Factura 0004-001255  
**Sin detalle de artículos**

Remito 003882  
**Sin detalle de artículos**

Para el chofer sigue estando claro qué debe entregar y qué documentación acompaña la entrega.

---

## Un mismo reparto puede mezclar ambos casos

No es necesario que todos los proveedores trabajen igual.

En un mismo camión puede haber:

- mercadería importada desde Excel;
- facturas leídas por IA con detalle;
- remitos leídos por IA sin detalle;
- documentos cargados manualmente.

Todos terminan dentro del mismo proceso de organización, pallets, carga y hoja de ruta.

---

## Qué pasa si el detalle llega después

Supongamos:

1. el jueves se incorpora Factura 123 sin artículos;
2. se asigna al Pallet 7;
3. se prepara y organiza el reparto;
4. más tarde llega el Excel del proveedor.

RND debe reconocer que se trata de la misma factura.

El sistema completa sus artículos y conserva:

- el mismo cliente;
- el mismo reparto;
- el mismo pallet;
- la misma factura.

No debe aparecer una segunda entrega duplicada.

---

## Qué información es obligatoria

Para que una entrega pueda salir a reparto se necesita saber, como mínimo:

- a quién se entrega;
- dónde se entrega;
- qué factura/remito/documento la identifica;
- en qué ruta viaja;
- qué chofer y camión realizan el viaje.

Si RND trabaja con pallets, también debe saberse en qué pallet está la entrega y confirmar que ese pallet fue cargado.

El detalle de artículos mejora el control, pero no siempre es un requisito para poder despachar.

---

## Resultado esperado

El objetivo es que el jueves el operador pueda responder con seguridad:

- ¿qué clientes tienen entrega?;
- ¿qué factura o remito corresponde a cada uno?;
- ¿en qué pallet está?;
- ¿en qué camión viaja?;
- ¿qué pallets ya fueron cargados?;
- ¿qué debe entregar el chofer en cada parada?

Cuando hay detalle de productos, RND lo muestra y lo controla.

Cuando no hay detalle, RND trabaja con el documento sin inventar información.

De esta forma la preparación del reparto no queda detenida porque un proveedor no haya enviado su informe de artículos.

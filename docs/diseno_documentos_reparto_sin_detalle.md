# RND - Soporte de documentos de reparto con y sin detalle de artículos

## 1. Objetivo

Extender el circuito logístico de RND para que una factura o remito pueda participar de un reparto aunque no exista detalle confiable de artículos, cantidades, kg o bultos.

El objetivo no es reemplazar el flujo actual. El flujo detallado existente continúa siendo el camino preferido cuando el proveedor entrega información estructurada. La ampliación agrega un segundo camino válido para los casos en los que RND dispone únicamente del documento físico o de sus datos básicos.

Casos soportados:

1. **Documento con detalle**: factura/remito + cliente + destino + líneas de productos.
2. **Documento sin detalle**: factura/remito + cliente + destino, sin líneas de productos confiables.

En ambos casos el documento debe poder:

- formar parte de un reparto;
- asignarse a una ruta;
- asociarse a chofer y equipo;
- asignarse a un pallet;
- aparecer en la hoja de ruta;
- validarse como parte de la carga;
- evitar duplicaciones si posteriormente se completa el detalle.

---

## 2. Estado actual del modelo

El repositorio ya contiene una separación útil entre documento y detalle.

### 2.1 Documento logístico/comercial

`modelos/Documentos.py` define:

- `DocumentoPedido`
- `DocumentoPedidoDetalle`
- `DocumentoPedidoHojaRuta`

`DocumentoPedido` ya almacena información independiente del artículo:

- proveedor;
- cliente;
- fecha;
- número de factura;
- número de remito;
- comprobante de origen;
- origen;
- observaciones.

Esto permite conservar la identidad documental aunque todavía no existan productos.

### 2.2 Línea operativa actual

`modelos/HojaRuta.py` define `HojaDeRuta`.

Actualmente cada registro de `HojaDeRuta` representa, en la práctica, una línea logística con:

- cliente;
- lugar de entrega;
- ruta;
- comprobante;
- producto;
- cantidad;
- kg;
- bultos;
- chofer;
- equipo.

El circuito existente funciona correctamente cuando hay detalle de mercadería, pero convierte la línea de producto en requisito estructural.

### 2.3 Pallets

`modelos/Pallet.py` utiliza:

- `Pallet`
- `PalletDetalle`

`PalletDetalle` referencia obligatoriamente una `HojaDeRuta`. Por lo tanto, hoy no existe una forma limpia de asignar a un pallet una factura/remito que no tenga líneas de artículos.

### 2.4 Validaciones que hoy obligan a tener detalle

Actualmente existen varias reglas que asumen que todo reparto tiene productos:

- `utiles/validacion_hoja_ruta.py` invalida una línea con `cantidad <= 0`;
- `utiles/bandeja_pedidos.py` considera observada una factura con `productos <= 0`;
- `controladores/ValidacionHojaRuta.py` busca errores operativos exigiendo cantidad válida;
- `ArmadoPallets` trabaja únicamente con saldos derivados de `HojaDeRuta`;
- `GeneradorPDFHojaRuta` arma el reporte operativo a partir de `PalletDetalle`;
- `utiles/importacion_pdf_ia.py` descarta un documento reconocido si no encuentra al menos una línea útil de producto.

Estas reglas deben mantenerse para el flujo detallado, pero no deben bloquear el nuevo flujo documental.

---

## 3. Principio de diseño

La ampliación debe separar dos conceptos que hoy están parcialmente mezclados:

**Documento a entregar**  
La factura/remito que físicamente acompaña una entrega y debe viajar en un reparto.

**Detalle de mercadería**  
Las líneas de productos, cantidades, kg y bultos conocidas para ese documento.

Un documento puede existir y viajar sin detalle.

No se debe crear una línea ficticia del tipo:

- producto = "SIN DETALLE";
- cantidad = 1.

Ese atajo contaminaría totales, saldos, validaciones, pallets y posteriores conciliaciones.

---

## 4. Modelo propuesto

### 4.1 Nueva entidad: DocumentoReparto

Agregar una entidad logística que indique que un `DocumentoPedido` participa en un reparto determinado.

Nombre sugerido:

`DocumentoReparto`

Campos mínimos propuestos:

- `id`
- `documento_id` FK a `DocumentoPedido`
- `fecha_reparto`
- `cliente_id`
- `lugar_entrega_id`
- `ruta_id`
- `responsable_id`
- `equipo_id`
- `observaciones`
- `estado` opcional para futuras extensiones

Restricción recomendada:

- evitar que el mismo `DocumentoPedido` se agregue dos veces al mismo reparto.

La entidad expresa:

> "Este documento debe viajar en esta carga."

No expresa productos ni cantidades.

### 4.2 Nueva relación: PalletDocumento

Agregar una relación entre pallet y documento de reparto.

Campos mínimos:

- `id`
- `pallet_id`
- `documento_reparto_id`

Restricción recomendada:

- unicidad `(pallet_id, documento_reparto_id)`.

Esta tabla no reemplaza `PalletDetalle`.

La composición conceptual pasa a ser:

```
Pallet
├── PalletDetalle
│   └── HojaDeRuta
│       └── líneas de productos conocidas
└── PalletDocumento
    └── DocumentoReparto
        └── factura/remito sin detalle o referencia documental
```

### 4.3 Compatibilidad con el modelo actual

El flujo con detalle continúa utilizando:

```
DocumentoPedido
  -> DocumentoPedidoDetalle
  -> DocumentoPedidoHojaRuta
  -> HojaDeRuta
  -> PalletDetalle
```

El flujo sin detalle utilizará:

```
DocumentoPedido
  -> DocumentoReparto
  -> PalletDocumento
```

Cuando un documento tiene detalle, `DocumentoReparto` puede seguir existiendo como identidad logística del documento. Sin embargo, debe definirse una única política de presentación para evitar que el mismo documento aparezca duplicado en el pallet o en el PDF.

Recomendación:

- `DocumentoReparto` representa siempre la participación del documento en el viaje;
- las líneas de `HojaDeRuta` representan el detalle opcional;
- la UI y los reportes agrupan ambos niveles bajo el mismo documento.

---

## 5. Estados funcionales del documento

No es necesario introducir un workflow complejo. Sí conviene derivar un estado informativo.

### COMPLETO

Existe:

- documento;
- cliente;
- lugar de entrega;
- al menos una línea de producto válida.

Puede participar en ruta y pallet.

### SIN_DETALLE

Existe:

- documento;
- cliente;
- lugar de entrega;
- no existe detalle confiable.

También puede participar en ruta y pallet.

### INCOMPLETO

Falta alguno de estos datos operativos mínimos:

- cliente;
- lugar de entrega;
- número/tipo de documento suficiente para identificarlo.

No debe poder marcarse como listo para reparto.

El artículo, cantidad, kg y bultos no son bloqueantes en el estado `SIN_DETALLE`.

---

## 6. Ingreso de documentos

### 6.1 Importación estructurada actual

Cuando Excel/PDF entrega artículos válidos:

1. se obtiene/crea `DocumentoPedido`;
2. se crean `DocumentoPedidoDetalle`;
3. se crean/vinculan las `HojaDeRuta`;
4. se crea/actualiza la participación logística del documento en `DocumentoReparto`;
5. el documento aparece como **Con detalle**.

El flujo actual debe conservar idempotencia y prevención de duplicados.

### 6.2 PDF o imagen procesado con IA

`utiles/importacion_pdf_ia.py` debe dejar de considerar que `items=[]` equivale necesariamente a documento inválido.

La extracción debe separar:

- reconocimiento de cabecera del documento;
- reconocimiento del detalle.

Resultado válido sin líneas:

```json
{
  "documento": {
    "tipo": "FACTURA",
    "numero": "0004-001254",
    "cliente_nombre": "SUPERMERCADO LOPEZ",
    "domicilio": "...",
    "localidad": "ELDORADO"
  },
  "items": []
}
```

Si la cabecera tiene confianza suficiente, el sistema debe permitir continuar como **documento sin detalle**.

La UI debe informar claramente:

> Documento reconocido. No se pudo obtener detalle confiable de artículos. Puede incorporarse igualmente al reparto.

### 6.3 Alta manual rápida

Debe existir una opción operativa para registrar un documento sin escanearlo.

Campos mínimos:

- proveedor;
- tipo: factura/remito/otro;
- número;
- cliente;
- lugar de entrega;
- fecha de reparto;
- observaciones opcionales.

El sistema no debe pedir producto, cantidad, kg ni bultos para este caso.

---

## 7. Bandeja de organización

La bandeja debe trabajar a nivel de documento, no exclusivamente a nivel de línea.

Ejemplo:

| Cliente | Documento | Estado detalle | Lugar | Ruta | Estado |
|---|---|---|---|---|---|
| Cliente A | Fact. 123 | 5 productos | Eldorado | Norte | Listo |
| Cliente B | Rem. 887 | Sin detalle | Montecarlo | Norte | Listo |
| Cliente C | Fact. 450 | Sin detalle | Sin asignar | - | Revisar |

La ausencia de detalle no debe producir estado de error por sí sola.

Debe diferenciarse visualmente:

- **Con detalle**
- **Sin detalle**
- **Revisar datos**

---

## 8. Armado de pallets

La pantalla debe permitir mover al pallet dos tipos de elementos:

### 8.1 Línea detallada

Se conserva el comportamiento existente:

- producto;
- saldo;
- cantidad;
- kg;
- bultos;
- asignación parcial.

Persiste en `PalletDetalle`.

### 8.2 Documento sin detalle

Se muestra como una unidad documental:

- cliente;
- factura/remito;
- lugar;
- indicador "Sin detalle".

Al agregarlo al pallet se crea `PalletDocumento`.

No se inventan cantidades.

### 8.3 Documento con detalle

Visualmente debería agruparse por documento para el operador.

La implementación puede mantener internamente las líneas actuales, pero la interfaz debe permitir entender:

```
Factura 12345 - Cliente A
  5 productos
  Pallet 3
```

y:

```
Factura 88721 - Cliente B
  Sin detalle de artículos
  Pallet 7
```

---

## 9. Validación de carga y despacho

La validación debe dejar de considerar "cantidad > 0" como requisito universal del documento.

Requisitos mínimos comunes:

- existe al menos un documento/entrega;
- fecha válida;
- ruta válida;
- cliente asignado;
- lugar de entrega asignado;
- documento identificable;
- único chofer;
- único equipo.

Para documentos detallados se mantienen las reglas adicionales de saldo y paletización.

Para documentos sin detalle:

- deben estar asignados a un pallet cuando el reparto utiliza control por pallets;
- el pallet debe ser validado como cargado antes de despachar.

`puede_despachar()` deberá contemplar:

1. saldos de `PalletDetalle`;
2. documentos `DocumentoReparto` pendientes de pallet;
3. pallets esperados todavía no marcados como cargados.

---

## 10. Hoja de ruta / PDF operativo

El PDF debe priorizar la operación de entrega.

Estructura recomendada:

```
ENTREGA 03
Cliente: Supermercado López
Lugar: Sucursal Eldorado
Dirección: ...

PALLET 7
Factura 0004-001254
  - Queso Tybo 20
  - Cremoso 15

Factura 0004-001255
  SIN DETALLE DE ARTÍCULOS

Remito 003882
  SIN DETALLE DE ARTÍCULOS
```

La hoja debe poder generarse aunque todas las entregas sean documentales y no exista ningún `PalletDetalle`.

Por lo tanto `GeneradorPDFHojaRuta` no debe depender exclusivamente de `PalletDetalle`.

Se recomienda construir una representación unificada:

```
Entrega
  -> Cliente/Lugar
  -> Pallets
      -> Documentos
          -> líneas opcionales
```

---

## 11. Conversión posterior de "sin detalle" a "con detalle"

Este caso es crítico para evitar duplicados.

Ejemplo:

1. jueves: se registra Factura 123 sin artículos;
2. se asigna a Pallet 7;
3. posteriormente llega Excel/PDF detallado;
4. RND reconoce la misma `DocumentoPedido`;
5. agrega sus líneas;
6. conserva cliente, reparto y pallet existentes;
7. pasa de **Sin detalle** a **Con detalle**.

No debe generarse una segunda factura en la bandeja ni una segunda entrega.

La clave de identidad documental existente debe reutilizarse siempre que sea suficiente. Cuando no lo sea, debe definirse una estrategia de conciliación por proveedor + tipo/número + cliente.

---

## 12. Migración y compatibilidad

La implementación debe ser aditiva.

No se deben eliminar ni reinterpretar registros existentes de:

- `HojaDeRuta`;
- `Pallet`;
- `PalletDetalle`;
- `DocumentoPedidoDetalle`;
- `DocumentoPedidoHojaRuta`.

Las nuevas tablas pueden crearse mediante el mecanismo de migraciones actual y deben contemplarse también en el esquema DEMO/SQLite.

Los repartos históricos continúan utilizando el flujo legacy/detallado.

---

## 13. Áreas de código a modificar

Principales archivos afectados previsibles:

- `modelos/Documentos.py`
  - nuevo modelo de participación en reparto;
  - helpers de alta/consulta/idempotencia.

- `modelos/Pallet.py`
  - relación documento-pallet;
  - composición unificada;
  - validación de documentos pendientes.

- `controladores/Migraciones.py`
  - nuevas tablas/índices.

- esquema DEMO
  - equivalentes SQLite.

- `utiles/importacion_pdf_ia.py`
  - aceptar documento reconocido con `items=[]`;
  - separar confianza de cabecera y detalle.

- `controladores/ImportacionPedidos.py`
  - crear/actualizar participación logística aun sin líneas.

- `controladores/BandejaPedidos.py`
  - incorporar documentos sin `HojaDeRuta`;
  - estado "Sin detalle" no bloqueante.

- `controladores/ArmadoPallets.py`
  - permitir asignar documentos sin detalle.

- `vistas/ArmadoPallets.py`
  - representar líneas y documentos de forma distinguible.

- `utiles/validacion_hoja_ruta.py`
  - requisitos comunes y requisitos de detalle.

- `controladores/ValidacionHojaRuta.py`
  - localizar y resolver documentos incompletos.

- `utiles/Reportes.py`
  - construir hoja de ruta desde una vista unificada de entregas/pallets/documentos.

---

## 14. Tests mínimos requeridos

### Modelo

- crear documento sin detalle;
- agregarlo a un reparto;
- asignarlo a un pallet;
- impedir duplicación en el mismo pallet/reparto;
- completar después el detalle conservando identidad.

### Importación IA

- factura con cabecera + artículos;
- factura con cabecera válida + `items=[]`;
- imagen ilegible sin número/cliente;
- reimportación del mismo documento.

### Bandeja

- documento con detalle aparece como completo;
- documento sin detalle no queda observado únicamente por no tener productos;
- documento sin lugar queda pendiente;
- combinación de ambos tipos en una misma fecha.

### Pallets

- pallet sólo con productos;
- pallet sólo con documentos sin detalle;
- pallet mixto;
- mover/quitar documento;
- validar carga.

### Hoja de ruta

- viaje detallado actual sin regresión;
- viaje sólo documental;
- viaje mixto;
- factura/remito visible;
- ningún "producto ficticio" en el PDF.

### Despacho

- documento sin detalle y sin pallet cuando el control por pallets aplica: bloquea;
- documento sin detalle correctamente paletizado y pallet cargado: permite;
- líneas detalladas con saldo pendiente: sigue bloqueando.

---

## 15. Fuera de alcance inicial

No incluir en la primera implementación:

- stock;
- facturación contable;
- precios;
- conciliación automática con ERP;
- lectura de códigos de barras de productos;
- optimización automática de pallets;
- geocodificación automática;
- prueba de entrega al cliente.

El objetivo es resolver de forma segura la preparación y salida de mercadería cuando la información documental llega incompleta.

---

## 16. Criterio de aceptación funcional

La ampliación se considera correcta cuando RND permite realizar, sin datos ficticios, este escenario:

1. registrar o escanear una factura;
2. identificar cliente y lugar de entrega;
3. conservar sólo el número de factura/remito si no existe detalle;
4. incorporarla al reparto;
5. asignarla a una ruta;
6. asignarla a un pallet;
7. validar que ese pallet subió al camión;
8. emitir una hoja de ruta que indique cliente, lugar, pallet y factura/remito;
9. despachar;
10. completar posteriormente los artículos de esa misma factura sin duplicar el documento.

Ese comportamiento debe convivir con el flujo detallado existente sin regresiones.

# Conocimiento técnico-funcional para el Asistente RND

Este documento describe comportamiento real del código actual de RND. Su objetivo
es permitir que MiniMax responda preguntas de operación y diagnóstico sin inventar
mecanismos internos.

No es un router de intenciones ni una lista de palabras clave. Es contexto
funcional versionado junto con el sistema.

## 1. Cómo identifica al cliente durante la importación

Al grabar cada línea importada, RND intenta resolver el cliente de esta manera:

1. Busca en `codigos_clientes_proveedores` una relación entre:
   - código informado por el proveedor;
   - proveedor seleccionado;
   - cliente interno.
2. Si existe esa relación y el cliente asociado no es el cliente genérico ID 1,
   utiliza ese cliente.
3. Si no existe una relación válida, intenta una coincidencia exacta, sin
   distinguir mayúsculas/minúsculas, entre el nombre recibido y
   `Cliente.razon_social`.
4. Si tampoco encuentra cliente, la línea queda sin cliente resuelto y se
   considera pendiente de corrección.

Por lo tanto, el sistema no hace una búsqueda difusa por nombre en esta etapa.
La relación proveedor+código es la forma más precisa de identificación.

## 2. Cómo resuelve el lugar de entrega

Una vez resuelto el cliente:

1. Busca primero un lugar de entrega marcado como **principal** y **activo** para
   ese cliente.
2. Si existe, ése es el lugar usado automáticamente.
3. Si no hay principal, obtiene todos los lugares activos del cliente.
4. Si hay exactamente un lugar activo, utiliza ese único lugar.
5. Si hay cero lugares activos o hay más de uno sin un principal definido, no
   elige arbitrariamente: el lugar queda sin resolver.

Cuando el lugar queda sin resolver, la importación puede igualmente crear la
línea operativa, pero queda marcada como pendiente para que el operador la
corrija antes de finalizar el reparto.

Esto significa que, si un cliente tiene varios destinos, conviene definir uno
como principal cuando realmente exista un destino habitual. Si no corresponde
tener un principal, el operador deberá elegir el lugar correcto en la bandeja.

## 3. Cómo se determina la ruta al importar

Si el lugar de entrega quedó resuelto:

1. RND usa la ruta configurada en el lugar de entrega.
2. Si ese lugar no tiene ruta propia, usa como respaldo la ruta configurada en
   el cliente.

Si el lugar de entrega no quedó resuelto, la línea se guarda sin ruta.

En la Bandeja de pedidos el operador puede editar la factura completa, elegir
cliente, lugar y ruta. Al seleccionar un lugar que tiene ruta, la pantalla
propone esa ruta. Si al guardar no se eligió una ruta explícita, vuelve a usar
como respaldo la ruta del lugar y luego la ruta del cliente.

## 4. Qué pasa si falta cliente o lugar de entrega

La importación no descarta automáticamente la línea.

La hoja de ruta se crea con los datos disponibles. Si falta cliente o lugar:

- incrementa el contador de pendientes;
- puede quedar sin ruta;
- debe corregirse antes de considerar la hoja lista.

Desde **Bandeja de pedidos / Organizar pedidos**, la edición de factura permite:

- elegir un cliente;
- elegir uno de sus lugares activos;
- elegir la ruta;
- abrir **Crear / editar clientes y lugares** si hace falta mantener esos datos.

## 5. Cómo evita duplicados al reimportar

RND separa el documento original de sus líneas.

### Identidad del documento

Cuando hay número de factura/comprobante, la clave del documento usa:

- proveedor;
- número de factura normalizado.

Cuando no hay factura, usa:

- proveedor;
- cliente;
- fecha;
- indicador SIN_FACTURA.

### Identidad de cada línea

La identidad de una línea utiliza una huella construida con:

- producto;
- cantidad;
- kilos;
- bultos;
- observaciones.

Si dentro del mismo documento hay dos líneas idénticas, RND agrega un número de
ocurrencia para distinguir la primera, segunda, etc.

### Reimportación

Antes de crear otra hoja de ruta, RND verifica si esa línea del documento ya está
vinculada a una hoja de ruta para la misma fecha.

Si ya existe el vínculo:

- no crea otra línea operativa;
- cuenta la fila como reimportada;
- conserva la hoja de ruta existente.

Por eso, ante una importación que se cortó o genera dudas, no es recomendable
repetirla a ciegas: primero conviene revisar el resumen de importación y los
pedidos existentes.

## 6. Cómo funciona Organizar pedidos

La bandeja carga todas las hojas de ruta de la fecha seleccionada y agrupa las
líneas por factura/documento para trabajar a nivel de factura.

Para organizar:

1. Se selecciona una o más facturas.
2. Se selecciona una ruta destino.
3. RND actualiza la ruta en las líneas seleccionadas.
4. Antes de informar éxito vuelve a consultar la base y verifica que todas las
   líneas hayan quedado realmente grabadas con esa ruta.
5. Sólo después habilita continuar a asignación de chofer y camión.

El botón Siguiente abre Asignación de recursos con la misma fecha y con la última
ruta que efectivamente se organizó.

## 7. Cómo funciona Asignar chofer y camión

La pantalla de asignación carga registros cuya combinación coincide exactamente
con:

- fecha seleccionada;
- ruta seleccionada.

Si no existe ningún registro para esa combinación, muestra **Sin pedidos**.

Los valores genéricos configurados para empleado y camión representan
"pendiente", no una asignación válida.

Al guardar una asignación:

1. valida que existan pedidos;
2. valida un chofer real;
3. valida un camión real;
4. actualiza **todos los pedidos de esa fecha+ruta** con el mismo chofer y camión;
5. consulta otra vez la base y comprueba que no hayan quedado líneas con recursos
   distintos.

El botón para continuar a validación sólo se habilita cuando los recursos están
completos.

## 8. Por qué Ver Hoja de Ruta puede aparecer vacía

La consulta base de Ver Hoja de Ruta filtra por:

- fecha;
- ruta.

Además, si el operador tiene cargado un camión o un empleado en los filtros, la
consulta agrega esos filtros.

Por eso una hoja puede verse vacía aunque existan pedidos si:

- se seleccionó otra fecha;
- se seleccionó otra ruta;
- hay un filtro de camión que no coincide;
- hay un filtro de empleado que no coincide;
- los pedidos todavía no fueron organizados en esa ruta.

Cuando no hay registros, la propia pantalla indica revisar fecha, ruta,
asignación de chofer/camión y existencia de pedidos organizados.

## 9. Recursos genéricos en Ver Hoja de Ruta

Los IDs configurados como empleado genérico y camión genérico significan
"pendiente".

Al cargar la hoja:

- no se muestran como si fueran recursos válidos;
- los campos quedan visualmente vacíos;
- las filas con recursos genéricos no se consideran seleccionadas como una
  asignación terminada.

## 10. Requisitos para imprimir la Hoja de Ruta

Antes de imprimir, la pantalla exige:

- fecha;
- ruta;
- responsable/chofer;
- equipo/camión.

Además debe existir al menos una hoja de ruta para esa combinación de fecha y
ruta.

## 11. Validación operativa de una hoja

La validación considera correcta una hoja solamente si cumple todos estos
requisitos:

- tiene al menos un pedido;
- tiene fecha;
- tiene ruta;
- todos los registros tienen un único chofer real y no genérico;
- todos los registros tienen un único camión real y no genérico;
- ningún pedido carece de cliente;
- ningún pedido carece de lugar de entrega;
- ningún pedido carece de comprobante;
- todas las cantidades son mayores que cero.

Una hoja incompleta no puede pasar a estado LISTA.

Para pasar a DESPACHADA primero debe estar LISTA y seguir cumpliendo las
validaciones.

Una hoja DESPACHADA no retrocede automáticamente de estado.

# Guia de uso del sistema RND

Este documento explica el camino recomendado para usar RND en la operacion diaria. Esta pensado para usuarios administrativos, de logistica y responsables de reparto.

## Objetivo del sistema

RND permite organizar pedidos y generar hojas de ruta para reparto. El flujo principal es:

1. Mantener actualizados los datos maestros.
2. Importar pedidos desde archivos de proveedores.
3. Revisar y grabar los pedidos importados.
4. Armar la hoja de ruta por fecha y ruta de reparto.
5. Asignar camion y chofer.
6. Imprimir o guardar el reporte de hoja de ruta.
7. Consultar, corregir o auditar datos cuando sea necesario.

## Ingreso al sistema

1. Abrir RND desde el acceso directo.
2. Ingresar usuario y clave.
3. Al entrar, el sistema muestra la pantalla principal con un panel lateral de opciones.

Si una opcion no aparece o no abre, puede deberse a permisos del usuario. En ese caso se debe consultar con el administrador del sistema.

## Pantalla principal

La pantalla principal se organiza con botones en el panel lateral. Desde ahi se accede a las funciones de trabajo:

- Clientes.
- Proveedores.
- Empleados.
- Equipos.
- Tablas auxiliares.
- Importacion de pedidos.
- Ver hoja de ruta.
- Auditoria y consultas, segun permisos.

El menu puede variar segun el perfil del usuario.

## Camino recomendado antes de operar

Antes de importar pedidos o emitir hojas de ruta, conviene revisar estos datos:

1. Clientes activos.
2. Ruta de reparto asignada a cada cliente.
3. Proveedores activos.
4. Codigos de cliente por proveedor.
5. Choferes o empleados activos.
6. Equipos o camiones activos.
7. Tablas auxiliares necesarias, como rutas de reparto, localidades y tipos.

Si alguno de estos datos falta, la importacion puede quedar incompleta o pedir confirmaciones manuales.

## Gestion de datos maestros

Las pantallas de ABM tienen una forma de uso similar:

1. Entrar a la opcion correspondiente, por ejemplo Clientes, Proveedores, Empleados o Equipos.
2. Usar el campo de busqueda para encontrar registros existentes.
3. Usar Agregar para crear un nuevo registro.
4. Usar Editar para modificar el registro seleccionado.
5. Usar Borrar solo cuando corresponda eliminar el registro.
6. Usar Excel para exportar la grilla cuando se necesite revisar o compartir informacion.
7. Usar Cerrar para volver a la pantalla principal.

En general, los registros dados de baja o inactivos pueden verse marcados con otro color o no estar disponibles para algunas operaciones.

## Clientes

En Clientes se cargan los datos necesarios para identificar y rutear pedidos:

- Razon social.
- Direccion.
- Telefono.
- CUIT.
- Contacto.
- Ruta de reparto.
- Observaciones.
- Estado activo/inactivo.

### Codigos por proveedor

Algunos proveedores informan sus propios codigos de cliente. Para que RND pueda relacionar un pedido importado con el cliente correcto, se debe mantener la relacion entre:

- proveedor,
- codigo informado por el proveedor,
- cliente interno de RND.

Si durante la importacion aparece un cliente sin codigo asociado, el sistema puede pedir buscar el cliente correcto y guardar esa relacion.

## Proveedores

En Proveedores se mantienen las empresas que entregan archivos de pedidos. Para que la importacion funcione correctamente, el proveedor debe estar cargado y activo.

La configuracion de columnas de importacion depende del proveedor. Si falta una columna esperada, el sistema puede mostrar avisos como que no encuentra Cliente, Producto, Comprobante, Cantidad, KG, Bultos u Observaciones.

## Empleados y choferes

En Empleados se administran los datos del personal. Los choferes o responsables activos se usan al asignar una hoja de ruta.

Desde esta pantalla tambien pueden consultarse fichas, vencimientos y datos relacionados, segun las opciones disponibles para el usuario.

## Equipos o camiones

En Equipos se administran los moviles disponibles para reparto. Para asignar una hoja de ruta, el camion debe estar cargado y activo.

Tambien pueden consultarse vencimientos asociados al equipo cuando la opcion este disponible.

## Importacion de pedidos

La importacion es el primer paso operativo para generar hojas de ruta desde archivos externos.

### Pasos

1. Entrar a Importacion de Pedidos.
2. Seleccionar la Fecha reparto.
3. Seleccionar la Empresa Proveedora.
4. Presionar Examinar y elegir el archivo.
5. Seleccionar la hoja del Excel, si el archivo tiene varias hojas.
6. Indicar Fila inicio y Fila fin.
7. Presionar Importar.
8. Revisar la grilla cargada.
9. Marcar o desmarcar la columna Importa segun las filas que se deben grabar.
10. Presionar Grabar.

### Que hace el sistema al grabar

Al grabar, RND intenta:

- identificar el cliente segun el codigo del proveedor;
- buscar o pedir asociacion si el codigo no existe;
- evitar grabar pedidos contra clientes genericos;
- tomar producto, comprobante, cantidad, kilos, bultos y observaciones;
- crear o actualizar registros de hoja de ruta para la fecha indicada;
- asignar inicialmente camion y empleado genericos, hasta que se arme la hoja de ruta definitiva.

### Recomendaciones

- Verificar que la fecha de reparto sea correcta antes de grabar.
- Revisar que la empresa proveedora sea la correcta.
- No grabar filas que no correspondan a pedidos.
- Si el sistema pide asociar un cliente, elegir cuidadosamente el cliente interno correcto.
- Si muchas filas fallan por columnas faltantes, revisar la configuracion de importacion del proveedor antes de continuar.

## Ver y armar hoja de ruta

La pantalla Ver Hoja de Ruta se usa para revisar pedidos importados, asignar recursos y emitir el reporte.

### Cargar una hoja de ruta

1. Entrar a Ver Hoja de Ruta.
2. Seleccionar fecha.
3. Seleccionar ruta de reparto.
4. Opcionalmente seleccionar camion o chofer para filtrar.
5. Presionar Cargar.

El sistema muestra una grilla con:

- seleccion,
- cliente,
- comprobante,
- producto,
- cantidad,
- kilos,
- bultos,
- observaciones.

### Asignar camion y chofer

1. Seleccionar fecha y ruta.
2. Cargar los pedidos.
3. Elegir camion asignado.
4. Elegir chofer responsable.
5. Marcar las filas que se deben asignar.
6. Presionar Grabar.

Al grabar, el sistema reasigna la hoja de ruta de esa fecha y ruta: primero deja los pedidos en valores genericos y luego asigna camion/chofer a las filas marcadas.

### Agregar un pedido manual

1. Presionar Agregar.
2. Elegir cliente.
3. Completar comprobante, producto, cantidad, kilos, bultos y observaciones.
4. Completar chofer y camion si corresponde.
5. Presionar Grabar.

### Modificar un pedido

1. Seleccionar una fila de la grilla.
2. Presionar Modificar.
3. Corregir los datos necesarios.
4. Presionar Grabar.

### Borrar un pedido

1. Seleccionar la fila.
2. Presionar Borrar.
3. Confirmar solo si realmente corresponde eliminar el registro.

## Imprimir hoja de ruta

Para emitir el reporte:

1. Cargar la hoja de ruta.
2. Verificar fecha y ruta.
3. Verificar que el chofer y el camion esten completos.
4. Presionar Imprimir.

El sistema genera un PDF con los pedidos de la fecha y ruta seleccionadas. Si faltan fecha, ruta, responsable o equipo, el sistema muestra una advertencia para completar esos datos.

## Auditoria

El sistema registra cambios importantes sobre algunos datos. Cuando la opcion esta disponible, la auditoria permite revisar modificaciones anteriores de un registro.

Usar auditoria para:

- verificar quien modifico un dato;
- revisar cambios en clientes, empleados u otros registros;
- entender diferencias entre datos anteriores y actuales.

## Buenas practicas de operacion

- Revisar datos maestros antes de importar.
- Mantener clientes activos y con ruta asignada.
- Mantener actualizados los codigos de cliente por proveedor.
- Verificar fecha de reparto antes de presionar Grabar.
- Revisar la grilla antes de importar definitivamente.
- No usar clientes genericos para pedidos reales.
- Asignar camion y chofer antes de imprimir la hoja de ruta.
- Exportar a Excel cuando se necesite control externo.
- Consultar con administracion si una opcion no aparece por permisos.

## Problemas frecuentes

### No aparece una opcion del menu

Puede faltar permiso para el usuario. Consultar con el administrador.

### El archivo no importa

Revisar:

- proveedor seleccionado;
- formato del archivo;
- hoja seleccionada;
- fila inicio y fila fin;
- columnas configuradas para ese proveedor.

### El sistema no encuentra un cliente

Puede faltar la relacion entre codigo de proveedor y cliente interno. Buscar el cliente correcto cuando el sistema lo solicite y guardar la asociacion.

### La hoja de ruta aparece vacia

Revisar:

- fecha seleccionada;
- ruta de reparto;
- si se importaron pedidos para esa fecha;
- si hay filtros de camion o chofer aplicados.

### No permite imprimir

Completar fecha, ruta, chofer responsable y camion asignado.

## Resumen del flujo diario

1. Verificar clientes, proveedores, empleados y equipos.
2. Importar pedidos del proveedor para la fecha de reparto.
3. Corregir o asociar clientes si el sistema lo pide.
4. Grabar los pedidos importados.
5. Abrir Ver Hoja de Ruta.
6. Cargar por fecha y ruta.
7. Asignar chofer y camion.
8. Grabar asignaciones.
9. Imprimir la hoja de ruta.
10. Revisar o corregir pedidos manuales si hace falta.

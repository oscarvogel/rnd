# Documento de Funciones del Sistema de Gestión Forestal

## Introducción

Este documento detalla las funcionalidades del Sistema de Gestión Forestal para FORESTAL PARAGUAY S.A. El sistema está diseñado para optimizar la gestión de la producción forestal, el mantenimiento de equipos y la administración financiera.

## Módulos del Sistema

El sistema se divide en los siguientes módulos principales:

### 1. Módulo de Producción

Este módulo se centra en el registro y análisis de las operaciones de producción forestal.

- **Registro de Producción Diaria:** Permite registrar la producción diaria, el consumo de recursos y la eficiencia operativa.
- **Importación de Pedidos:** Facilita la importación de pedidos de producción desde archivos externos.
    - **Formatos Soportados:** El sistema es capaz de importar datos desde archivos de Microsoft Excel (.xlsx, .xls) y PDF. Incluye un procesamiento especializado para los partes de despacho del proveedor "Tremblay", tanto en formato Excel como PDF.
    - **Selección de Datos:** La interfaz permite al usuario seleccionar el archivo a importar. Para archivos Excel, el sistema detecta y lista todas las hojas disponibles, permitiendo al usuario elegir cuál procesar.
    - **Configuración Flexible:** El usuario puede especificar el número de la fila donde comienzan los encabezados y el rango de filas de datos que desea importar, lo que otorga gran flexibilidad para manejar distintos formatos de archivo.
    - **Previsualización y Grabación:** Los datos seleccionados se cargan en una grilla para su revisión. El usuario puede marcar qué filas desea importar. Al grabar, el sistema procesa cada fila marcada:
        - **Asignación de Clientes:** Utiliza un código de cliente del archivo importado y lo busca en una tabla de mapeo (`CodigoClienteProveedor`) para asignarlo al cliente interno correcto. Si no se encuentra un mapeo, el sistema puede buscar al cliente por su nombre e incluso crear una nueva asociación si el usuario lo confirma. Se evita la importación de pedidos para clientes genéricos.
        - **Creación de Hojas de Ruta:** Por cada pedido válido, se crea o actualiza una entrada en la `HojaDeRuta`, registrando detalles como el producto, cantidad, peso, bultos y observaciones.
        - **Mapeo de Columnas Dinámico:** La correspondencia entre las columnas del archivo (ej. "Cliente", "Producto") y los campos del sistema se configura por proveedor a través del modelo `ProcesoLista`, permitiendo adaptar el proceso de importación a múltiples socios comerciales sin cambiar el código.
- **Visualización de Hoja de Ruta:** Permite a los operarios y supervisores ver, gestionar y organizar las hojas de ruta.
    - **Búsqueda y Filtro:** Los usuarios pueden cargar las hojas de ruta filtrando por fecha y ruta de reparto. Adicionalmente, pueden filtrar los resultados por equipo (camión) y responsable (empleado) asignado.
    - **Visualización en Grilla:** Los pedidos se presentan en una grilla donde el usuario puede ver detalles como cliente, comprobante, producto, cantidad, peso, bultos y observaciones.
    - **Asignación de Recursos:** La interfaz facilita la asignación y reasignación masiva de un empleado y un equipo a todos los pedidos seleccionados de la hoja de ruta. Antes de grabar, el sistema resetea las asignaciones previas para esa fecha y ruta a valores genéricos, garantizando una reasignación limpia.
    - **Gestión de Pedidos (CRUD):**
        - **Agregar:** Permite añadir nuevos pedidos a la hoja de ruta a través de un formulario de alta.
        - **Modificar:** Posibilita la edición de los detalles de un pedido existente.
        - **Borrar:** Permite eliminar un pedido de la hoja de ruta.
    - **Impresión:** Genera un reporte en formato PDF de la hoja de ruta seleccionada, incluyendo los detalles de los pedidos, así como el responsable y el equipo asignados. Este reporte está listo para ser impreso y distribuido.

### 2. Módulo de Mantenimiento

Este módulo gestiona el ciclo de vida y el mantenimiento del equipamiento de la empresa.

- **Gestión de Equipos (ABM):** Alta, baja y modificación de la información de los equipos de la empresa.
- **Planificación de Mantenimiento:** Permite la planificación y seguimiento de mantenimientos preventivos y correctivos para la maquinaria.

### 3. Módulo Administrativo

Este módulo cubre la gestión financiera y de recursos humanos de la empresa.

- **Gestión de Clientes (ABM):** Alta, baja y modificación de clientes.
- **Gestión de Empleados (ABM):** Alta, baja y modificación de empleados.
- **Gestión de Proveedores (ABM):** Alta, baja y modification de proveedores.
- **Control Financiero:** Incluye control de movimientos de caja y conciliaciones bancarias.
- **Generación de Reportes:** Creación de reportes financieros y operativos en formato PDF.
- **Gestión de Tablas Auxiliares (ABM):** Administración de tablas maestras o de configuración del sistema.

### 4. Funciones Generales

Estas funcionalidades son transversales a todo el sistema.

- **Control de Acceso (Login):** Sistema de autenticación para controlar el acceso a las funcionalidades según el rol del usuario.
- **Auditoría de Acciones:** Registro de las acciones importantes realizadas por los usuarios en el sistema para garantizar la trazabilidad.
- **Migraciones de Base de Datos:** Mecanismos para actualizar la estructura de la base de datos de forma controlada.
- **Automatizaciones:** Procesos automáticos para tareas recurrentes.

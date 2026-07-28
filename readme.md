# RND

**Versión preparada:** `2026.7.28.1`

## Descripción
RND es una aplicación de escritorio desarrollada en Python/PyQt5 para gestión operativa, hojas de ruta, clientes, proveedores, equipos, empleados, importación de pedidos y reportes.

El proyecto usa MySQL como base principal y Peewee como ORM.

## Tecnologías Utilizadas
- **Lenguaje de Programación:** Python
- **Framework de Interfaz Gráfica:** PyQt5
- **Base de Datos:** MySQL
- **ORM:** Peewee
- **Infraestructura:** Aplicación de escritorio
- **Instalador:** PyInstaller + Inno Setup

## Instalación
### Prerrequisitos
- Tener instalado [Git](https://git-scm.com/)
- Tener instalado [MySQL](https://www.mysql.com/)
- Tener instalado Python 3.10 x64 y pip
- Tener instalado Inno Setup 6 para generar instaladores

### Clonar el Repositorio
```bash
git clone https://github.com/oscarvogel/rnd.git
cd rnd
```

### Configuración del Entorno
```bash
py -3.10 -m venv .venv-build
.venv-build\Scripts\python.exe -m pip install -r requirements.txt
```

### Configuración de Base de Datos
1. Copiar `.env.example` a `.env`.
2. Completar las credenciales locales necesarias.
3. Configurar `sistema.ini`/`rnd.ini` según el entorno de ejecución.

### Ejecución del Proyecto
```bash
.venv-build\Scripts\python.exe main.py -i . -a sistema.ini
```

## Build del Instalador

El instalador se genera con:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_installer.ps1
```

El resultado queda en:

```text
dist\installer\setup_rnd.exe
```

## Uso
- Ejecutar la aplicación de escritorio.
- Iniciar sesión con credenciales de usuario registrado.
- Trabajar con hojas de ruta, clientes, proveedores, equipos, empleados, reportes e importaciones.

## Documentación

- [Guía operativa para usuarios finales](docs/guia_usuario.md).
- [Preparación y guion del meet del 29/07/2026](docs/meet-2026-07-29.md).

## Contribución
1. Haz un fork del repositorio.
2. Crea una rama con tu nueva funcionalidad (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza commit de los cambios (`git commit -m 'Agregada nueva funcionalidad'`).
4. Sube la rama (`git push origin feature/nueva-funcionalidad`).
5. Abre un Pull Request.

## Seguridad

No subir `.env`, logs, dumps de base, instaladores generados ni documentación operativa con datos reales. Las credenciales deben resolverse por variables de entorno o configuración local ignorada por Git.

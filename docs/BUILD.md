# Build del instalador de RND

Guia paso a paso para compilar RND como ejecutable (.exe) y como instalador
Windows (.exe con Inno Setup) usando el script `scripts/build_installer.ps1`
o los pasos manuales.

## Indice

1. [Pre-requisitos](#pre-requisitos)
2. [Convencion de version](#convencion-de-version)
3. [Build con el script automatico](#build-con-el-script-automatico)
4. [Build manual (paso a paso)](#build-manual-paso-a-paso)
5. [Troubleshooting](#troubleshooting)
6. [Que archivos genera el build](#que-archivos-genera-el-build)
7. [Salida esperada](#salida-esperada)

## Pre-requisitos

- **Python 3.10+ x64** con pip (las dependencias estan fijadas en `requirements.txt`).
- **MySQL** corriendo y accesible desde donde se ejecuta (para el smoke check).
- **Inno Setup 6** (solo para generar el instalador). Descarga: https://jrsoftware.org/isinfo.php.
  Path default que usa el script: `C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe`.
- **Git** (para clonar y, si se commitea, para push).
- **Submodulo pyqt5libs** (es un submódulo git desde el commit `c953e87`):
  ```bash
  git submodule update --init --recursive
  ```

## Convencion de version

Desde agosto 2026, la version sigue el formato **`AAAA.MM.DD.VV`**:

- `AAAA` = anio (4 digitos)
- `MM` = mes (1-2 digitos)
- `DD` = dia (1-2 digitos)
- `VV` = variante del build del dia (1-2 digitos)

Ejemplos:
- `2026.8.5.1` — primer build del 5 de agosto de 2026
- `2026.8.5.2` — segundo build del mismo dia
- `2026.12.31.1` — primer build del ultimo dia del anio

La version se mantiene sincronizada en **dos lugares**:

1. `version.txt` — formato VSVersionInfo para los metadatos del ejecutable
   (Windows muestra esto en Propiedades > Detalles).
2. `installer/RND.iss` — `#define AppVersion` que usa Inno Setup para el
   instalador y los accesos directos.

El script `build_installer.ps1` modifica ambos atomicamente.

## Build con el script automatico

El script hace todo en orden: bump de version -> tests -> PyInstaller ->
smoke check -> Inno Setup. Aborta en el primer paso que falle.

### Uso basico

```powershell
cd O:\\RND
.\\scripts\\build_installer.ps1
```

Te pregunta: `Confirmar bump de 2026.8.5.1 a 2026.8.5.1 ? (s/n)`.
- Si decis **s**, bumpea a la nueva version (default: fecha de hoy + VV=1).
- Si decis **n**, conserva la version actual.

### Parametros

| Parametro        | Default                | Descripcion                                                  |
|------------------|------------------------|--------------------------------------------------------------|
| `-Version`       | fecha de hoy + VV=1    | Version especifica en formato AAAA.MM.DD.VV                  |
| `-Force`         | (no)                   | No pide confirmacion antes de bumpear                        |
| `-SkipTests`     | (no)                   | Salta la corrida de pytest                                   |
| `-SkipInstaller` | (no)                   | Solo compila con PyInstaller, no genera el instalador        |

### Ejemplos

```powershell
# Build completo con confirmacion interactiva
.\\scripts\\build_installer.ps1

# Version explicita, sin confirmacion (util para CI)
.\\scripts\\build_installer.ps1 -Version "2026.8.5.2" -Force

# Re-compilar rapido sin tests ni instalador (para validar cambios pequenos)
.\\scripts\\build_installer.ps1 -SkipTests -SkipInstaller

# Solo PyInstaller (omite Inno Setup, deja el ejecutable en dist/main/)
.\\scripts\\build_installer.ps1 -SkipTests
```

### Flujo interno

1. **Pre-flight checks**: verifica que existan `.venv-build\\Scripts\\python.exe`,
   `main.spec`, `version.txt`, `installer\\RND.iss`.
2. **Bump de version**: lee la version actual del `RND.iss`, calcula la nueva
   (param `-Version` o default hoy+1), parchea `version.txt` (4 lugares:
   `filevers`, `prodvers`, `ProductVersion`, `FileVersion`) y `RND.iss` (1
   lugar: `#define AppVersion`).
3. **Tests** (a menos que `-SkipTests`): corre pytest desde la raiz,
   excluyendo `test_utiles_smtp.py` (que tiene un import preexistente
   roto). Si falla, aborta el build.
4. **PyInstaller**: limpia `dist/` con `cmd /c rmdir /s /q` (tolera mejor
   archivos lockeados en Windows que `Remove-Item`), corre
   `pyinstaller main.spec --noconfirm`. Output: `dist/main/main.exe` y
   `dist/main/_internal/`.
5. **Smoke check**: ejecuta `main.exe --startup-check -i . -a sistema.ini`
   con `QT_QPA_PLATFORM=offscreen` para validar configuracion sin abrir
   la UI. Si falla, lo avisa pero no aborta (el ejecutable quedo igual).
6. **Inno Setup** (a menos que `-SkipInstaller`): corre
   `ISCC.exe installer/RND.iss`. Output: `dist/installer/setup_rnd.exe`.

## Build manual (paso a paso)

Si preferis hacer cada paso a mano (o si el script no funciona en tu
entorno):

### 1) Setup del entorno (una sola vez)

```powershell
cd O:\\RND
py -3.10 -m venv .venv-build
.venv-build\\Scripts\\python.exe -m pip install -r requirements.txt
git submodule update --init --recursive
```

### 2) Configuracion

```powershell
copy .env.example .env
# Editar .env con las credenciales de tu MySQL
```

`sistema.ini` ya viene apuntando a un VPS por default. Para MySQL local,
cambia el `host=` en `sistema.ini`.

### 3) (Opcional) Bumpear la version

Edita a mano `version.txt` y `installer/RND.iss` siguiendo el formato
`AAAA.MM.DD.VV`. Son 5 lugares en total:
- `version.txt`: `filevers`, `prodvers`, `ProductVersion`, `FileVersion`
- `installer/RND.iss`: `#define AppVersion`

### 4) Correr los tests

```powershell
.venv-build\\Scripts\\python.exe -m pytest tests/ -v
```

Debe dar 19/19 (excluyendo `test_utiles_smtp.py` que esta roto
preexistente). Si falla, **no continues al build**.

### 5) Compilar con PyInstaller

```powershell
# Limpiar build anterior (opcional pero recomendado)
cmd /c rmdir /s /q dist

.venv-build\\Scripts\\pyinstaller.exe main.spec
```

Output: `dist\\main\\main.exe` + `dist\\main\\_internal\\` con todas
las DLLs, PyQt5, pandas, etc. (~150-300 MB total).

### 6) Smoke check del ejecutable

```powershell
cd dist\\main
$env:QT_QPA_PLATFORM = "offscreen"
.\\main.exe --startup-check -i . -a sistema.ini
# Esperado: imprime STARTUP_CHECK_OK y la ruta del ini
Remove-Item Env:QT_QPA_PLATFORM
cd ..\..\
```

Si falla, revisar `dist\\main\\sistema.ini` y los paths.

### 7) Generar el instalador con Inno Setup

```powershell
& "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" installer\\RND.iss
```

Output: `dist\\installer\\setup_rnd.exe`.

El instalador:
- Pide admin y se instala en `C:\\RND\\` por default
- Borra carpetas de versiones anteriores (`_internal`, `PyQt5`, `pandas`, etc.)
- Crea acceso directo en escritorio y menu inicio con los parametros
  `-i "{app}" -a "sistema.ini"`
- Ofrece lanzar RND al final

## Troubleshooting

### `PyInstaller failed to execute the script pyi_rth_pymysql.py`

El `rthook_pymysql.py` (runtime hook) tiene dependencias. Verifica que
`pymysql` y `cryptography` esten en el venv:
```powershell
.venv-build\\Scripts\\python.exe -c "import pymysql, cryptography; print('ok')"
```

### `ImportError: No module named 'xlrd'`

El informe Tremblay de los tests requiere `xlrd` para leer `.xls`. Esta
en `requirements.txt` (`xlrd==2.0.2`); reinstalar con `pip install -r
requirements.txt`.

### `No se encontro ISCC.exe en C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe`

Inno Setup no esta en el path default. Instalar desde
https://jrsoftware.org/isinfo.php o ajustar la variable `$Iscc` al inicio
del script.

### `OSError: [WinError 32] El proceso no puede acceder al archivo porque esta siendo utilizado por otro proceso`

El `dist/main/main.exe` esta lockeado (alguien lo abrio o un build
anterior no se cerro). Cerrar cualquier instancia de RND y volver a
correr el script. El `rmdir /s /q` del script deberia limpiar igual, pero
si no funciona, reiniciar la maquina.

### El smoke check falla con `No se pudo leer el ini` o `STARTUP_CHECK_ERROR`

El `sistema.ini` no tiene las claves requeridas (`host`, `basedatos`,
`port`, `icono`, `logo`, `iniciosistema`) o faltan las imagenes en
`imagenes/`. Verificar:
```powershell
Get-Content sistema.ini
Get-ChildItem imagenes\\logo.ico, imagenes\\logo.png
```

### `core.filemode` o warnings de CRLF en git

PowerShell a veces escribe con CRLF en vez de LF. No afecta el build, es
solo ruido en `git status`. El archivo queda bien igual.

## Que archivos genera el build

```
dist/
  main/                  <- PyInstaller output
    main.exe             <- Ejecutable principal (~3-10 MB)
    _internal/           <- Dependencias empaquetadas (~150-300 MB)
      python313.dll
      PyQt5/
      pandas/
      ...
    sistema.ini
    rnd.ini
    imagenes/
    temas/
  installer/             <- Inno Setup output (solo si no se usa -SkipInstaller)
    setup_rnd.exe        <- Instalador Windows (~50-80 MB)
```

## Salida esperada

Despues de un build completo exitoso, deberias ver:

```
>>> Pre-flight checks
  [OK] Venv OK
  [OK] Archivos de build presentes

>>> 1) Bump de version
    Version actual: 2026.8.5.1
    Default (fecha de hoy + VV=1): 2026.8.5.2
    Confirmar bump de 2026.8.5.1 a 2026.8.5.2 ? (s/n): s
  [OK] version.txt -> 2026, 8, 5, 2
  [OK] RND.iss -> AppVersion "2026.8.5.2"

>>> 2) Suite de tests
...
======================= 19 passed, 2 warnings in 10.20s =======================
  [OK] Tests pasaron

>>> 3) PyInstaller (main.spec)
...
  [OK] Ejecutable generado: O:\RND\dist\main\main.exe

>>>    Smoke check (--startup-check)
  [OK] Smoke check OK

>>> 4) Inno Setup (installer/RND.iss)
...
  [OK] Instalador generado: O:\RND\dist\installer\setup_rnd.exe (X.XX MB)

>>> Build completo
  Version final: 2026.8.5.2
  Ejecutable:    O:\RND\dist\main\main.exe
  Instalador:    O:\RND\dist\installer\setup_rnd.exe
```

## Tests excluidos por designo

`tests/test_utiles_smtp.py` esta excluido del build (`--ignore=tests/test_utiles_smtp.py`)
porque tiene un import preexistente roto
(`vendored_pyqt5libs.pyqt5libs.utiles` no existe). Es un issue aparte, no
causado por este script. Si lo arreglas en el futuro, podes quitar el
`--ignore` del script.

## Ver tambien

- `readme.md` — setup inicial y ejecucion del sistema
- `docs/guia_usuario.md` — guia operativa para usuarios finales
- `installer/RND.iss` — script Inno Setup
- `main.spec` — spec de PyInstaller
- `version.txt` — VSVersionInfo

# RND Meet Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Dejar RND actualizado, verificable e instalable para la reunión del 29 de julio de 2026.

**Architecture:** Mantener `pyqt5libs` vendorizada dentro de RND, actualizar solamente sus paquetes de runtime desde `oscarvogel/pyqt5libs@030edce9ca384d259c4c7f2851398918f1e3d8f1` y registrar esa procedencia. Proteger la integración con pruebas de contrato, validar pantallas sin conexiones reales, centralizar la versión de release y reconstruir el instalador reproducible existente.

**Tech Stack:** Python 3.10, PyQt5, unittest, Peewee, PyInstaller, Inno Setup 6, PowerShell.

---

### Task 1: Proteger el contrato de pyqt5libs

**Files:**
- Create: `tests/test_pyqt5libs_integration.py`
- Create: `pyqt5libs/UPSTREAM_COMMIT`
- Modify: `pyqt5libs/libs/**`
- Modify: `pyqt5libs/pyqt5libs/**`

- [x] **Step 1: Escribir la prueba roja de procedencia y módulos nuevos**

Crear una prueba que exija el commit `030edce9ca384d259c4c7f2851398918f1e3d8f1` y que pueda importar `pyqt5libs.pyqt5libs.core.config`.

- [x] **Step 2: Ejecutar la prueba y confirmar el rojo**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_pyqt5libs_integration -v`

Expected: FAIL porque `UPSTREAM_COMMIT` y `pyqt5libs.pyqt5libs.core.config` todavía no existen.

- [x] **Step 3: Agregar una regresión para SMTP_PORT**

La prueba debe ejecutar `envia_correo()` sin red, reemplazando el hilo y el cliente SMTP, y comprobar que `SMTP_PORT=2525` llega al constructor SMTP.

- [x] **Step 4: Actualizar los paquetes vendorizados**

Copiar desde el commit fijado solamente `libs/`, `pyqt5libs/`, `README.md`, `LICENSE` y `.gitignore`. Escribir el SHA completo en `pyqt5libs/UPSTREAM_COMMIT`.

- [x] **Step 5: Ejecutar la prueba y confirmar que detecta la regresión SMTP**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_pyqt5libs_integration -v`

Expected: FAIL porque upstream consulta `SMPT_PORT`.

- [x] **Step 6: Aplicar el cambio mínimo**

Cambiar las dos lecturas de `SMPT_PORT` en `pyqt5libs/pyqt5libs/utiles.py` a `SMTP_PORT`.

- [x] **Step 7: Confirmar verde**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_pyqt5libs_integration -v`

Expected: PASS.

### Task 2: Agregar smoke visual sin base real

**Files:**
- Create: `tools/render_meet_screens.py`
- Create: `tests/test_gui_smoke.py`
- Generate locally: `artifacts/meet-screens/*.png`

- [x] **Step 1: Escribir pruebas rojas del contrato visual**

Exigir cuatro capturas con títulos y controles mínimos: login, clientes, importación de pedidos y hoja de ruta.

- [x] **Step 2: Ejecutar el rojo**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_gui_smoke -v`

Expected: FAIL porque `tools.render_meet_screens` no existe.

- [x] **Step 3: Implementar el renderer seguro**

Crear widgets PyQt5 representativos usando componentes reales de `pyqt5libs`, sin importar controladores ni ejecutar consultas. El script debe fijar `QT_QPA_PLATFORM=offscreen`, guardar PNG y devolver un manifiesto con título, tamaño y controles presentes.

- [x] **Step 4: Confirmar verde y renderizar**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_gui_smoke -v`

Run: `.venv-build\Scripts\python.exe tools\render_meet_screens.py --output artifacts\meet-screens`

Expected: PASS y cuatro PNG no vacíos.

- [x] **Step 5: Inspeccionar visualmente las cuatro capturas**

Revisar las imágenes y corregir desbordes, controles cortados o texto ilegible antes de continuar.

### Task 3: Sincronizar la versión de release

**Files:**
- Modify: `main.py`
- Modify: `version.txt`
- Modify: `installer/RND.iss`
- Modify: `readme.md`
- Modify: `tests/test_packaging_static.py`

- [x] **Step 1: Escribir una prueba roja de versión única**

Exigir `2026.7.28.1` en `main.py`, `version.txt` e `installer/RND.iss`, junto con `RND` como descripción del producto.

- [x] **Step 2: Ejecutar el rojo**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_packaging_static -v`

Expected: FAIL por la versión `2025.9.2.1` y `__version__ = "0.1"`.

- [x] **Step 3: Actualizar metadatos**

Cambiar versión a `2026.7.28.1`, copyright a 2026 y descripción a `RND - Gestión de hojas de ruta`.

- [x] **Step 4: Confirmar verde**

Run: `.venv-build\Scripts\python.exe -m unittest tests.test_packaging_static -v`

Expected: PASS.

### Task 4: Preparar el resumen del meet

**Files:**
- Create: `docs/meet-2026-07-29.md`
- Modify: `readme.md`

- [x] **Step 1: Documentar estado y demostración**

Incluir objetivo, arquitectura, flujo de demostración, alcance validado, limitaciones, riesgos y próximos pasos. No incluir secretos ni datos reales.

- [x] **Step 2: Enlazar el documento**

Agregar el enlace desde `readme.md` bajo una sección de documentación.

- [x] **Step 3: Validar enlaces y ausencia de marcadores**

Run: `rg -n "TBD|TODO|PENDIENTE_DE_COMPLETAR" docs\meet-2026-07-29.md readme.md`

Expected: sin coincidencias.

### Task 5: Reconstruir y validar el instalador

**Files:**
- Generate locally: `dist/main/**`
- Generate locally: `dist/installer/setup_rnd.exe`
- Generate locally: `artifacts/meet-validation.txt`

- [x] **Step 1: Ejecutar la suite completa antes del build**

Run: `.venv-build\Scripts\python.exe -m unittest discover -s tests -v`

Run: `.venv-build\Scripts\python.exe -m pip check`

Run: `.venv-build\Scripts\python.exe -m compileall -q main.py controladores modelos vistas utiles pyqt5libs tools`

Expected: todas las pruebas y verificaciones en verde.

- [x] **Step 2: Construir desde el script oficial**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File .\build_installer.ps1`

Expected: `dist\main\main.exe` y `dist\installer\setup_rnd.exe`.

- [x] **Step 3: Probar el bundle**

Run: `dist\main\main.exe --startup-check -i . -a sistema.ini`

Expected: exit 0 y `STARTUP_CHECK_OK`.

- [x] **Step 4: Instalar silenciosamente en un directorio temporal**

Ejecutar `setup_rnd.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=<directorio-temporal>`, sin usar `C:\RND`.

- [x] **Step 5: Probar la instalación**

Run: `<directorio-temporal>\main.exe --startup-check -i <directorio-temporal> -a sistema.ini`

Expected: exit 0 y `STARTUP_CHECK_OK`.

- [x] **Step 6: Registrar evidencia**

Guardar versión, tamaños, fechas, códigos de salida y SHA-256 del instalador en `artifacts/meet-validation.txt`.

### Task 6: Auditoría y publicación de la rama

**Files:**
- Review: todos los archivos modificados

- [x] **Step 1: Revisar el diff**

Run: `git status -sb`

Run: `git diff --check`

Run: `git diff --stat`

- [x] **Step 2: Repetir la suite completa**

Run: `.venv-build\Scripts\python.exe -m unittest discover -s tests -v`

Expected: todas las pruebas en verde.

- [x] **Step 3: Confirmar higiene**

Verificar que no se trackeen `.env`, credenciales, instaladores, capturas ni documentos operativos generados.

- [ ] **Step 4: Crear commit y publicar**

Commit sugerido: `Prepare RND for July 2026 meet`

Push: `git push -u origin codex/rnd-meet-readiness`

- [ ] **Step 5: Entregar evidencia**

Informar rama, commit, pruebas, instalador, hash, validación instalada, riesgos pendientes y enlace al resumen del meet.

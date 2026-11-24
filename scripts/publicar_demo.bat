@echo off
cd /d "%~dp0.."
echo Generando y publicando RND DEMO... (log en publicar_demo.log)
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0release_demo.ps1' -SkipInstallDependencies *>&1 | Tee-Object -FilePath '%~dp0..\publicar_demo.log'"
echo.
echo Termino. Puede cerrar esta ventana.
pause

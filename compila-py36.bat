@echo off
REM Elimina el directorio dist/main si existe
rd /S /Q dist\main

REM Usa el python del entorno virtual directamente
REM Si matplotlib no se usa, removemos su referencia para evitar errores
h:\venv\pyfe36\scripts\python.exe -m PyInstaller -w --version-file=version.txt --icon=imagenes\LogoS-01.ico --exclude-module matplotlib main.py
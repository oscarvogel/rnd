$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "[RND] Falta .venv. Ejecutá primero .\demo.ps1 para crear el entorno."
    exit 1
}

Write-Host "[RND] Cargando seed La Estancia de Oro en DEMO..."
& $Python (Join-Path $Root "scripts\seed_estancia_oro_demo.py")
exit $LASTEXITCODE

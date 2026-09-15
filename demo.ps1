$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[RND] Creando entorno virtual propio en $Root\.venv..."
    py -3.11 -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[RND] Instalando dependencias..."
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$env:VIRTUAL_ENV = Join-Path $Root ".venv"
$env:PATH = (Join-Path $env:VIRTUAL_ENV "Scripts") + ";" + $env:PATH
$env:PYTHONPATH = $Root

Write-Host "[RND] Python: $VenvPython"
& $VenvPython (Join-Path $Root "demo_main.py")
exit $LASTEXITCODE

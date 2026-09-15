[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstallDependencies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv-build\Scripts\python.exe"
$StateFile = Join-Path $RepoRoot "installer\.demo_build_state"
$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

function Get-DemoBuildVersion {
    param([string]$Path)
    $today = Get-Date -Format "yyyy.MM.dd"
    $counter = 1
    if (Test-Path $Path) {
        try {
            $state = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
            if ("$($state.date)" -eq $today) { $counter = [int]$state.counter + 1 }
        } catch {}
    }
    [pscustomobject]@{date=$today;counter=$counter} |
        ConvertTo-Json -Compress |
        Set-Content -LiteralPath $Path -Encoding UTF8
    return ("{0}.{1:D2}" -f $today, $counter)
}

$VenvBuild = Join-Path $RepoRoot ".venv-build"

function Test-BuildVenv {
    param([string]$PythonExe)
    if (-not (Test-Path $PythonExe)) {
        return $false
    }
    try {
        & $PythonExe -c "import sys; print(sys.executable)" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if (-not (Test-BuildVenv -PythonExe $Python)) {
    if (Test-Path $VenvBuild) {
        Write-Host "Entorno .venv-build invalido; recreando..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvBuild
    } else {
        Write-Host "Creando entorno de build .venv-build..." -ForegroundColor Cyan
    }

    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $PyLauncher) {
        throw "No se encontro el launcher 'py' de Python."
    }

    & py -3.10 -m venv $VenvBuild
    if ($LASTEXITCODE -ne 0 -or -not (Test-BuildVenv -PythonExe $Python)) {
        throw "No se pudo crear un .venv-build valido con Python 3.10."
    }
}

if (-not $Iscc) {
    throw "No se encontro Inno Setup 6. Instalar Inno Setup 6 y volver a ejecutar este mismo comando."
}

$BuildVersion = Get-DemoBuildVersion -Path $StateFile

Push-Location $RepoRoot
try {
    Write-Host "Actualizando submodulos..." -ForegroundColor Cyan
    & git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron actualizar los submodulos." }

    if (-not $SkipInstallDependencies) {
        & $Python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "Fallaron dependencias." }
        & $Python -m pip install pyinstaller
        if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar PyInstaller." }
    }

    if (-not $SkipTests) {
        $env:QT_QPA_PLATFORM = "offscreen"
        & $Python -m pytest --ignore=tests/test_utiles_smtp.py
        if ($LASTEXITCODE -ne 0) { throw "Tests en rojo. No se genera demo." }
    }

    Remove-Item -Recurse -Force "build\RND Demo" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "dist\RND Demo" -ErrorAction SilentlyContinue
    Remove-Item -Force "dist\installer\setup_rnd_demo.exe" -ErrorAction SilentlyContinue

    & $Python -m PyInstaller --noconfirm --clean installer\RND_Demo.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo." }

    & $Iscc "/DMyAppVersion=$BuildVersion" installer\RND_Demo.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo." }

    Write-Host ""
    Write-Host "RND DEMO generado correctamente." -ForegroundColor Green
    Write-Host "Version: $BuildVersion" -ForegroundColor Green
    Write-Host "Instalador: dist\installer\setup_rnd_demo.exe" -ForegroundColor Green
    Write-Host "Login demo: usuario 1 / clave DEMO" -ForegroundColor Yellow
} finally {
    Pop-Location
}

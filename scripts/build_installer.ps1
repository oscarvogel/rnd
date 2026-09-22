<#
.SYNOPSIS
    Compila RND de extremo a extremo: tests + bump de version + PyInstaller + Inno Setup.

.DESCRIPTION
    Flujo:
      1. (Opcional) Bump de la version en version.txt e installer/RND.iss.
      2. Corre la suite de pytest.
      3. Si los tests pasan, corre PyInstaller con main.spec.
      4. Si PyInstaller termina OK, compila el instalador con Inno Setup.

    El script se aborta en el primer paso que falle (no llega a compilar
    si los tests estan rotos, no genera instalador si PyInstaller falla).

.PARAMETER Version
    Version nueva en formato AAAA.MM.DD.VV (ej: 2026.8.5.2).
    Si no se pasa:
      - Si la version actual es del mismo dia que hoy, se incrementa VV
        (ej: 2026.8.6.2 -> 2026.8.6.3).
      - Si es de otro dia, se usa la fecha de hoy con VV=1
        (ej: 2026.8.6.2 -> 2026.8.7.1).

.PARAMETER SkipTests
    Salta la corrida de pytest. Util solo si ya los corriste y queres
    re-compilar rapido.

.PARAMETER SkipInstaller
    Solo corre tests + PyInstaller, no genera el instalador .exe.

.PARAMETER Force
    No pide confirmacion antes de bumpear la version.

.EXAMPLE
    .\scripts\build_installer.ps1
    # Tests + bump autoincrementado + PyInstaller + Inno Setup

.EXAMPLE
    .\scripts\build_installer.ps1 -Version "2025.9.3.0" -SkipTests
    # Bumpea a 2025.9.3.0, salta tests, compila todo

.EXAMPLE
    .\scripts\build_installer.ps1 -SkipInstaller
    # Bump + tests + PyInstaller, no genera el instalador
#>
[CmdletBinding()]
param(
    [string]$Version,
    [switch]$SkipTests,
    [switch]$SkipInstaller,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$WarningPreference = 'Continue'

# Paths
$RepoRoot    = (Resolve-Path "$PSScriptRoot\..").ProviderPath
$VenvPython  = Join-Path $RepoRoot '.venv-build\Scripts\python.exe'
$PyInstaller = Join-Path $RepoRoot '.venv-build\Scripts\pyinstaller.exe'
$VersionFile = Join-Path $RepoRoot 'version.txt'
$GeneratedDir = Join-Path $RepoRoot 'build\generated'
$GeneratedVersionFile = Join-Path $GeneratedDir 'version.txt'
$StateFile = Join-Path $RepoRoot 'installer\.production_build_state'
$IssFile     = Join-Path $RepoRoot 'installer\RND.iss'
$PySpec     = Join-Path $RepoRoot 'main.spec'
$DistDir     = Join-Path $RepoRoot 'dist'
$MainExe     = Join-Path $DistDir 'main\main.exe'
$Installer   = Join-Path $DistDir 'installer\setup_rnd.exe'
$IsccCandidates = @(
    $env:INNO_SETUP_COMPILER,
    'C:\InnoSetup6\ISCC.exe',
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$Iscc = $IsccCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1

# Helpers visuales
function Write-Step    { param($msg) Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK      { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  [X]  $msg" -ForegroundColor Red }
function Get-Version   { param($path) $txt = Get-Content $path -Raw -Encoding UTF8; $m = [regex]::Match($txt, '"(\d+\.\d+\.\d+\.\d+)"'); if ($m.Success) { $m.Groups[1].Value } else { $null } }
function Test-VersionFormat { param($v) $v -match '^\d{4}\.\d{1,2}\.\d{1,2}\.\d{1,2}$' }

function Get-AutomaticBuildVersion {
    param([string]$Path)
    $today = Get-Date -Format 'yyyy.M.d'
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
    return "$today.$counter"
}

function New-GeneratedVersionFile {
    param([string]$Template, [string]$Destination, [string]$BuildVersion)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    $versionTuple = $BuildVersion -replace '\.', ', '
    $v = Get-Content $Template -Raw -Encoding UTF8
    $v = $v -replace 'filevers=\(\d[\d, ]+\)', "filevers=($versionTuple)"
    $v = $v -replace 'prodvers=\(\d[\d, ]+\)', "prodvers=($versionTuple)"
    $v = $v -replace "u'ProductVersion', u'[\d, ]+'", "u'ProductVersion', u'$versionTuple'"
    $v = $v -replace "u'FileVersion', u'[\d, ]+'", "u'FileVersion', u'$versionTuple'"
    [System.IO.File]::WriteAllText($Destination, $v, [System.Text.UTF8Encoding]::new($false))
}

# Verificaciones previas
Write-Step "Pre-flight checks"
if (-not (Test-Path $VenvPython)) { throw "No se encontro el venv: $VenvPython. Correr 'python -m venv .venv-build && pip install -r requirements.txt' primero." }
if (-not (Test-Path $PySpec))     { throw "No se encontro $PySpec" }
if (-not (Test-Path $VersionFile)){ throw "No se encontro $VersionFile" }
if (-not (Test-Path $IssFile))    { throw "No se encontro $IssFile" }
Write-OK "Venv OK"
Write-OK "Archivos de build presentes"

# 1) Version de build (sin modificar archivos trackeados)
Write-Step "1) Version de build"
if (-not $Version) {
    $Version = Get-AutomaticBuildVersion -Path $StateFile
}
if (-not (Test-VersionFormat $Version)) {
    throw "Formato de version invalido: '$Version'. Esperado AAAA.MM.DD.VV (ej: 2026.8.5.1)"
}
New-GeneratedVersionFile -Template $VersionFile -Destination $GeneratedVersionFile -BuildVersion $Version
Write-OK "Version del build: $Version"
Write-OK "Metadata temporal: $GeneratedVersionFile"
Write-OK "version.txt e installer\RND.iss quedan intactos"

# 2) Tests
if (-not $SkipTests) {
    Write-Step "2) Suite de tests"
    Push-Location $RepoRoot
    try {
        & $VenvPython -m pytest tests/ --ignore=tests/test_utiles_smtp.py -v
        if ($LASTEXITCODE -ne 0) { throw "Los tests fallaron (exit code $LASTEXITCODE). Abortando build." }
    } finally {
        Pop-Location
    }
    Write-OK "Tests pasaron"
} else {
    Write-Warn "Tests saltados (-SkipTests)"
}

# 3) PyInstaller
Write-Step "3) PyInstaller (main.spec)"
if (Test-Path $DistDir) {
    Write-Host "    Limpiando dist/ previo..."
    # Remove-Item falla a veces con "directorio no vacio" en Windows
    # cuando hay handles abiertos. Usamos cmd /c rmdir que es mas
    # agresivo y maneja bien archivos lockeados en este momento.
    cmd /c rmdir /s /q $DistDir 2>$null | Out-Null
}
Push-Location $RepoRoot
try {
    $env:RND_VERSION_FILE = $GeneratedVersionFile
    & $PyInstaller $PySpec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo (exit code $LASTEXITCODE). Abortando." }
} finally {
    Remove-Item Env:RND_VERSION_FILE -ErrorAction SilentlyContinue
    Pop-Location
}
if (-not (Test-Path $MainExe)) { throw "PyInstaller termino pero no existe $MainExe" }
Write-OK "Ejecutable generado: $MainExe"

# Smoke check: ejecutar con --startup-check (sin UI)
Write-Step "   Smoke check (--startup-check)"
$env:QT_QPA_PLATFORM = 'offscreen'
Push-Location (Join-Path $DistDir 'main')
try {
    $proc = Start-Process -FilePath '.\main.exe' -ArgumentList '--startup-check','-i','.','-a','sistema.ini' -NoNewWindow -Wait -PassThru -RedirectStandardOutput 'startup_stdout.log' -RedirectStandardError 'startup_stderr.log'
    $stdout = if (Test-Path 'startup_stdout.log') { Get-Content 'startup_stdout.log' -Raw } else { '' }
    $stderr = if (Test-Path 'startup_stderr.log') { Get-Content 'startup_stderr.log' -Raw } else { '' }
    if ($proc.ExitCode -ne 0 -or $stdout -notmatch 'STARTUP_CHECK_OK') {
        Write-Warn "El smoke check fallo (exit=$($proc.ExitCode)). El ejecutable se genero igual, pero revisa la salida."
        Write-Host "stdout: $stdout"
        Write-Host "stderr: $stderr"
    } else {
        Write-OK "Smoke check OK"
    }
} finally {
    Pop-Location
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $DistDir 'main\startup_stdout.log') -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $DistDir 'main\startup_stderr.log') -ErrorAction SilentlyContinue
}

# 4) Inno Setup
if (-not $SkipInstaller) {
    Write-Step "4) Inno Setup (installer/RND.iss)"
    if (-not (Test-Path $Iscc)) {
        throw "No se encontro ISCC.exe en $Iscc. Instalar Inno Setup 6 desde https://jrsoftware.org/isinfo.php"
    }
    Push-Location (Join-Path $RepoRoot 'installer')
    try {
        & $Iscc "/DMyAppVersion=$Version" RND.iss
        if ($LASTEXITCODE -ne 0) { throw "ISCC fallo (exit code $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
    if (-not (Test-Path $Installer)) { throw "ISCC termino pero no existe $Installer" }
    $size = (Get-Item $Installer).Length / 1MB
    Write-OK "Instalador generado: $Installer ($([math]::Round($size, 2)) MB)"
} else {
    Write-Warn "Instalador saltado (-SkipInstaller)"
}

Write-Step "Build completo"
Write-Host "  Version final: $Version"
if (Test-Path $MainExe)     { Write-Host "  Ejecutable:    $MainExe" }
if (Test-Path $Installer)   { Write-Host "  Instalador:    $Installer" }
Write-Host "  Repo:          sin cambios de version generados por el build" -ForegroundColor Green

[CmdletBinding()]
param(
    [switch]$SkipInstallDependencies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot "build_demo_installer.ps1"
$Installer = Join-Path $RepoRoot "dist\installer\setup_rnd_demo.exe"
$ReleaseRepo = "oscarvogel/vogel-releases"
$ReleaseTag = "rnd-demo"
$ReleaseUrl = "https://github.com/$ReleaseRepo/releases/download/$ReleaseTag/setup_rnd_demo.exe"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "No se encontro gh.exe. Instala GitHub CLI y autentica con: gh auth login"
}

Write-Host ""
Write-Host "[1/3] Ejecutando tests y generando instalador DEMO..." -ForegroundColor Cyan
$buildArgs = @{}
if ($SkipInstallDependencies) { $buildArgs["SkipInstallDependencies"] = $true }
& $BuildScript @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Fallo la generacion del instalador DEMO."
}

if (-not (Test-Path $Installer)) {
    throw "No existe el instalador esperado: $Installer"
}

Write-Host ""
Write-Host "[2/3] Verificando release $ReleaseTag..." -ForegroundColor Cyan
& gh release view $ReleaseTag --repo $ReleaseRepo *> $null
if ($LASTEXITCODE -ne 0) {
    throw "No existe la release '$ReleaseTag' en $ReleaseRepo."
}

Write-Host ""
Write-Host "[3/3] Subiendo instalador a Vogel Releases..." -ForegroundColor Cyan
& gh release upload $ReleaseTag $Installer --repo $ReleaseRepo --clobber
if ($LASTEXITCODE -ne 0) {
    throw "Fallo la subida del instalador a Vogel Releases."
}

Write-Host ""
Write-Host "RND DEMO publicado correctamente." -ForegroundColor Green
Write-Host "Archivo: $Installer" -ForegroundColor Green
Write-Host "URL directa:" -ForegroundColor Yellow
Write-Host $ReleaseUrl -ForegroundColor Yellow

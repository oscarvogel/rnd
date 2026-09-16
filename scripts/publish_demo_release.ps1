[CmdletBinding()]
param(
    [string]$Version
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Installer = Join-Path $RepoRoot "dist\installer\setup_rnd_demo.exe"
$StateFile = Join-Path $RepoRoot "installer\.demo_build_state"
$RepoReleases = "oscarvogel/vogel-releases"
$Tag = "rnd-demo"
$AssetName = "RND_Demo_Setup.exe"

if (-not (Test-Path $Installer)) {
    throw "No existe el instalador DEMO: $Installer"
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "No se encontro GitHub CLI (gh)."
}

if (-not $Version) {
    if (Test-Path $StateFile) {
        try {
            $state = Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($state.date -and $state.counter) {
                $Version = ("{0}.{1:D2}" -f $state.date, [int]$state.counter)
            }
        } catch {}
    }
}
if (-not $Version) {
    $Version = Get-Date -Format "yyyy.MM.dd"
}

Write-Host "Publicando RND DEMO $Version en $RepoReleases..." -ForegroundColor Cyan

& gh release view $Tag --repo $RepoReleases *> $null
$ReleaseExists = ($LASTEXITCODE -eq 0)

$Title = "RND DEMO $Version"
$Notes = @"
Instalador DEMO de RND Logística.

Versión: $Version
Entorno: DEMO / SQLite local
Login: usuario 1 / clave DEMO

Este instalador es únicamente para demostración y pruebas. No corresponde a producción.
"@

if (-not $ReleaseExists) {
    & gh release create $Tag --repo $RepoReleases --title $Title --notes $Notes --prerelease
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el release $Tag." }
} else {
    & gh release edit $Tag --repo $RepoReleases --title $Title --notes $Notes --prerelease
    if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar el release $Tag." }
}

& gh release upload $Tag "$Installer#$AssetName" --repo $RepoReleases --clobber
if ($LASTEXITCODE -ne 0) { throw "No se pudo subir el instalador DEMO." }

$Url = "https://github.com/$RepoReleases/releases/download/$Tag/$AssetName"

Write-Host ""
Write-Host "RND DEMO publicado correctamente." -ForegroundColor Green
Write-Host "Version: $Version" -ForegroundColor Green
Write-Host "Descarga: $Url" -ForegroundColor Green

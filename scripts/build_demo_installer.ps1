[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstallDependencies,
    [string]$DemoAiEnvPath = ""
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

function Get-DemoAiConfig {
    param(
        [string]$RepoRoot,
        [string]$ExplicitPath
    )

    $candidates = @()
    if ($ExplicitPath) {
        $candidates += $ExplicitPath
    }
    $candidates += (Join-Path $RepoRoot "demo_ai.secrets.env")
    $candidates += (Join-Path $RepoRoot ".env")

    $source = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $source) {
        throw @"
No se encontro configuracion IA para el DEMO.
Cree $RepoRoot\demo_ai.secrets.env (recomendado) o use el .env local con:
MINIMAX_API_KEY=...
"@
    }

    $allowed = @(
        "MINIMAX_API_KEY",
        "RND_PDF_AI_API_KEY",
        "RND_PDF_AI_URL",
        "RND_PDF_AI_MODEL",
        "RND_PDF_AI_TIMEOUT"
    )

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $source -Encoding UTF8) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*    param([string]$Path)
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

if (-not (Test-Path $Python)) {
    throw "No existe $Python. Crear .venv-build antes de compilar."
}
if (-not $Iscc) {
    throw "No se encontro Inno Setup 6 (ISCC.exe)."
}

$BuildVersion = Get-DemoBuildVersion -Path $StateFile
$DemoAiConfig = Get-DemoAiConfig -RepoRoot $RepoRoot -ExplicitPath $DemoAiEnvPath
$StagedDemoEnv = Join-Path $RepoRoot "dist\RND Demo\.env"

Push-Location $RepoRoot
try {
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

    $DemoIni = Join-Path $RepoRoot "dist\RND Demo\sistema.demo.ini"
    $RndIni = Join-Path $RepoRoot "dist\RND Demo\rnd.ini"
    if (-not (Test-Path $DemoIni)) {
        throw "Build DEMO invalido: falta dist\RND Demo\sistema.demo.ini"
    }
    if (-not (Test-Path $RndIni)) {
        throw "Build DEMO invalido: falta dist\RND Demo\rnd.ini"
    }

    Write-DemoAiEnv -Values $DemoAiConfig.Values -Destination $StagedDemoEnv
    Write-Host "[RND] Configuracion IA DEMO incluida desde $($DemoAiConfig.Source)." -ForegroundColor Cyan
    Write-Host "[RND] Solo se empaquetan variables IA; no se copia el .env completo." -ForegroundColor Cyan

    & $Iscc "/DMyAppVersion=$BuildVersion" installer\RND_Demo.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo." }

    Write-Host ""
    Write-Host "RND DEMO generado correctamente." -ForegroundColor Green
    Write-Host "Version: $BuildVersion" -ForegroundColor Green
    Write-Host "Instalador: dist\installer\setup_rnd_demo.exe" -ForegroundColor Green
    Write-Host "INI demo: dist\RND Demo\sistema.demo.ini" -ForegroundColor Green
    Write-Host "Login demo: usuario 1 / clave DEMO" -ForegroundColor Yellow
} finally {
    # El secreto solo queda dentro del instalador generado; se limpia la copia
    # temporal del staging para no dejarla tirada en dist\RND Demo.
    Remove-Item -Force $StagedDemoEnv -ErrorAction SilentlyContinue
    Pop-Location
}
) {
            $name = $Matches[1]
            if ($allowed -contains $name) {
                $value = $Matches[2].Trim()
                if (
                    ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                    ($value.StartsWith("'") -and $value.EndsWith("'"))
                ) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                if ($value) {
                    $values[$name] = $value
                }
            }
        }
    }

    if (-not $values.ContainsKey("MINIMAX_API_KEY") -and -not $values.ContainsKey("RND_PDF_AI_API_KEY")) {
        throw "La configuracion IA no contiene MINIMAX_API_KEY ni RND_PDF_AI_API_KEY."
    }

    return [pscustomobject]@{
        Source = $source
        Values = $values
    }
}

function Write-DemoAiEnv {
    param(
        [hashtable]$Values,
        [string]$Destination
    )

    $order = @(
        "MINIMAX_API_KEY",
        "RND_PDF_AI_API_KEY",
        "RND_PDF_AI_URL",
        "RND_PDF_AI_MODEL",
        "RND_PDF_AI_TIMEOUT"
    )
    $lines = @(
        "# RND DEMO - configuracion IA incluida por build_demo_installer.ps1"
        "# No editar durante la demostracion."
    )
    foreach ($name in $order) {
        if ($Values.ContainsKey($name)) {
            $lines += ("{0}={1}" -f $name, $Values[$name])
        }
    }
    $lines | Set-Content -LiteralPath $Destination -Encoding UTF8
}

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

if (-not (Test-Path $Python)) {
    throw "No existe $Python. Crear .venv-build antes de compilar."
}
if (-not $Iscc) {
    throw "No se encontro Inno Setup 6 (ISCC.exe)."
}

$BuildVersion = Get-DemoBuildVersion -Path $StateFile

Push-Location $RepoRoot
try {
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

    $DemoIni = Join-Path $RepoRoot "dist\RND Demo\sistema.demo.ini"
    $RndIni = Join-Path $RepoRoot "dist\RND Demo\rnd.ini"
    if (-not (Test-Path $DemoIni)) {
        throw "Build DEMO invalido: falta dist\RND Demo\sistema.demo.ini"
    }
    if (-not (Test-Path $RndIni)) {
        throw "Build DEMO invalido: falta dist\RND Demo\rnd.ini"
    }

    & $Iscc "/DMyAppVersion=$BuildVersion" installer\RND_Demo.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo." }

    Write-Host ""
    Write-Host "RND DEMO generado correctamente." -ForegroundColor Green
    Write-Host "Version: $BuildVersion" -ForegroundColor Green
    Write-Host "Instalador: dist\installer\setup_rnd_demo.exe" -ForegroundColor Green
    Write-Host "INI demo: dist\RND Demo\sistema.demo.ini" -ForegroundColor Green
    Write-Host "Login demo: usuario 1 / clave DEMO" -ForegroundColor Yellow
} finally {
    Pop-Location
}

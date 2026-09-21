$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExecutable = 'python'
$VenvDir = Join-Path $Root '.venv-build'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$InnoCompilerCandidates = @(
    $env:INNO_SETUP_COMPILER,
    'C:\InnoSetup6\ISCC.exe',
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe'
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

$InnoCompiler = $null
foreach ($Candidate in $InnoCompilerCandidates) {
    if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
        $InnoCompiler = [string]$Candidate
        break
    }
}
$RequiredBuildFiles = @(
    'dist\main\main.exe',
    'dist\main\imagenes',
    'dist\main\temas',
    'dist\main\sistema.ini',
    'dist\main\rnd.ini'
)

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Message,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Action
    )

    Write-Host ""
    Write-Host "==> $Message"
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Falló el paso '$Message' con código de salida $LASTEXITCODE."
    }
}

Set-Location $Root

Invoke-Step 'Checking Python x64' {
    & $PythonExecutable -c "import platform, sys; assert platform.architecture()[0] == '64bit', platform.architecture(); print(sys.executable); print(sys.version)"
}

if (-not (Test-Path $VenvPython)) {
    Invoke-Step 'Creating .venv-build' {
        & $PythonExecutable -m venv $VenvDir
    }
}

Invoke-Step 'Upgrading pip tooling' {
    & $VenvPython -m pip install --upgrade pip setuptools wheel
}

Invoke-Step 'Installing project requirements' {
    & $VenvPython -m pip install -r (Join-Path $Root 'requirements.txt')
}

Invoke-Step 'Running compileall smoke check' {
    & $VenvPython -m compileall -q main.py controladores modelos vistas utiles pyqt5libs
}

Invoke-Step 'Building PyInstaller bundle' {
    & $VenvPython -m PyInstaller --clean --noconfirm main.spec
}

Invoke-Step 'Verifying PyInstaller output' {
    foreach ($RelativePath in $RequiredBuildFiles) {
        $Path = Join-Path $Root $RelativePath
        if (-not (Test-Path $Path)) {
            throw "Missing required build output: $RelativePath"
        }
    }
}

Invoke-Step 'Compiling Inno Setup installer' {
    if ([string]::IsNullOrWhiteSpace($InnoCompiler) -or -not (Test-Path -LiteralPath $InnoCompiler -PathType Leaf)) {
        throw "Inno Setup compiler not found. Set INNO_SETUP_COMPILER or install ISCC.exe in a known location."
    }
    Write-Host "Using Inno Setup compiler: $InnoCompiler"
    $InnoArgs = @((Join-Path $Root 'installer\RND.iss'))
    Start-Process -FilePath $InnoCompiler -ArgumentList $InnoArgs -NoNewWindow -Wait
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup fallo con codigo $LASTEXITCODE."
    }
}

Invoke-Step 'Verifying installer output' {
    $Installer = Join-Path $Root 'dist\installer\RND_Setup.exe'
    if (-not (Test-Path $Installer)) {
        throw "Missing installer output: $Installer"
    }
    Get-Item $Installer | Select-Object FullName, Length, LastWriteTime
}

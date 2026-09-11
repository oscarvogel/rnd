$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonLauncher = 'py'
$PythonVersion = '-3.10'
$VenvDir = Join-Path $Root '.venv-build'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$InnoCompiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
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

Invoke-Step 'Checking Python 3.10 x64' {
    & $PythonLauncher $PythonVersion -c "import platform, sys; assert platform.architecture()[0] == '64bit', platform.architecture(); print(sys.version)"
}

if (-not (Test-Path $VenvPython)) {
    Invoke-Step 'Creating .venv-build' {
        & $PythonLauncher $PythonVersion -m venv $VenvDir
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
    if (-not (Test-Path $InnoCompiler)) {
        throw "Inno Setup compiler not found: $InnoCompiler"
    }
    & $InnoCompiler (Join-Path $Root 'installer\RND.iss')
}

Invoke-Step 'Verifying installer output' {
    $Installer = Join-Path $Root 'dist\installer\RND_Setup.exe'
    if (-not (Test-Path $Installer)) {
        throw "Missing installer output: $Installer"
    }
    Get-Item $Installer | Select-Object FullName, Length, LastWriteTime
}

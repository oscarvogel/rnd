[CmdletBinding()]
param(
    [string]$Installer = "",
    [string]$InstallDir = ""
)

$ErrorActionPreference = 'Stop'

# Verificacion del artefacto final, no del codigo.
#
# Buscar cadenas dentro del .exe NO sirve: Inno Setup comprime con lzma2, asi
# que un texto puede estar presente y no ser greppable, o no estar y no
# aparecer. La unica forma concluyente de saber si la clave viaja es instalar
# de verdad y leer el .env que queda en la maquina.
#
# Se instala en una carpeta temporal y en silencio, se lee el .env, se
# comprueba y se borra todo.

# pruebas/ -> rnd-ia/ -> deploy/ -> raiz del repo
$RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $Installer) {
    $Installer = Join-Path $RepoRoot "dist\installer\setup_rnd_demo.exe"
}
if (-not $InstallDir) {
    $InstallDir = Join-Path $env:TEMP ("rnd_demo_verif_" + [guid]::NewGuid().ToString("N").Substring(0,8))
}

if (-not (Test-Path $Installer)) {
    throw "No existe el instalador: $Installer"
}

$tam = [math]::Round((Get-Item $Installer).Length / 1MB, 1)
Write-Host "Instalador: $Installer ($tam MB)" -ForegroundColor Cyan
Write-Host "Se instala en: $InstallDir" -ForegroundColor Cyan

Write-Host ""
Write-Host "Instalando en silencio..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $Installer `
    -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR=`"$InstallDir`"" `
    -PassThru -Wait

if ($proc.ExitCode -ne 0) {
    throw "El instalador termino con codigo $($proc.ExitCode)"
}

$envInstalado = Join-Path $InstallDir ".env"
$fallas = @()

function Comprobar($etiqueta, $esperado, $real) {
    if ($esperado -eq $real) {
        Write-Host ("ok    $etiqueta ($real)") -ForegroundColor Green
    } else {
        Write-Host ("FALLO ${etiqueta}: se esperaba '$esperado' y se obtuvo '$real'") -ForegroundColor Red
        $script:fallas += $etiqueta
    }
}

try {
    Write-Host ""
    Write-Host "=== Contenido del .env instalado ===" -ForegroundColor Cyan

    if (-not (Test-Path $envInstalado)) {
        Write-Host "FALLO: no se instalo ningun .env en $InstallDir" -ForegroundColor Red
        $fallas += "existencia del .env"
        $contenido = ""
    } else {
        $contenido = Get-Content -LiteralPath $envInstalado -Raw -Encoding UTF8
        Write-Host $contenido
    }

    Write-Host ""
    Write-Host "=== Comprobaciones ===" -ForegroundColor Cyan

    Comprobar "existe el .env" "si" $(if ($envInstalado -and (Test-Path $envInstalado)) { "si" } else { "no" })

    # Lo que jamas debe viajar en un instalador publico.
    foreach ($prohibida in @("MINIMAX_API_KEY", "RND_PDF_AI_API_KEY", "GROUP_SUMMARY_AI_API_KEY")) {
        Comprobar "'$prohibida' ausente" "ausente" $(if ($contenido -match [regex]::Escape($prohibida)) { "PRESENTE" } else { "ausente" })
    }

    # Lo que si tiene que viajar para que la IA funcione.
    Comprobar "la URL del proxy viaja" "si" $(if ($contenido -match "vogelconsultoria\.com\.ar/rnd-ia") { "si" } else { "no" })

    # Ni la clave de MySQL ni nada de la base del cliente.
    foreach ($ajena in @("MYSQL_PASSWORD", "RND_DB_PASSWORD", "sk-cp-")) {
        Comprobar "'$ajena' ausente" "ausente" $(if ($contenido -match [regex]::Escape($ajena)) { "PRESENTE" } else { "ausente" })
    }

    Write-Host ""
    Write-Host "=== Archivos sueltos en la instalacion ===" -ForegroundColor Cyan
    $sospechosos = Get-ChildItem -Path $InstallDir -Recurse -File -Include '.env','*.env','*.pem','*.key','*.credential','*.secret' -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName
    if ($sospechosos) {
        foreach ($s in $sospechosos) {
            Write-Host "  presente: $s" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  solo el .env esperado" -ForegroundColor Green
    }
} finally {
    Write-Host ""
    Write-Host "Desinstalando para limpiar accesos directos y registro..." -ForegroundColor DarkGray
    $uninstalador = Get-ChildItem -Path $InstallDir -Filter 'unins*.exe' -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($uninstalador) {
        $u = Start-Process -FilePath $uninstalador.FullName `
            -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART" -PassThru -Wait
        Write-Host "  desinstalador: codigo $($u.ExitCode)"
    }
    Start-Sleep -Seconds 2
    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
    if (Test-Path $InstallDir) {
        Write-Host "  aviso: quedo la carpeta $InstallDir" -ForegroundColor Yellow
    } else {
        Write-Host "  carpeta eliminada" -ForegroundColor DarkGray
    }
}

Write-Host ""
if ($fallas.Count -eq 0) {
    Write-Host "RESULTADO: el instalador es correcto, no lleva credenciales." -ForegroundColor Green
    exit 0
} else {
    Write-Host ("RESULTADO: fallaron -> " + ($fallas -join ", ")) -ForegroundColor Red
    exit 1
}
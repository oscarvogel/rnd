$ErrorActionPreference = 'Stop'

# Verificacion del flujo real de build_demo_installer.ps1, sin correr PyInstaller.
#
# Se extraen las funciones TAL COMO ESTAN en el script con el parser de
# PowerShell y se ejecutan contra un archivo de secretos de prueba. Asi lo que
# se comprueba es el codigo que va a correr el build, no una copia.

$BuildScript = 'C:\Programacion\RND\scripts\build_demo_installer.ps1'

$errores = $null
$tokens  = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($BuildScript, [ref]$tokens, [ref]$errores)
if ($errores.Count -gt 0) { throw "El build script tiene errores de sintaxis." }

foreach ($nombre in @('Get-DemoAiConfig', 'Write-DemoAiEnv')) {
    $fn = $ast.Find({
        param($n)
        $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $nombre
    }, $true)
    if (-not $fn) { throw "No se encontro la funcion $nombre" }
    Invoke-Expression $fn.Extent.Text
}

$RepoRoot = 'C:\Programacion\RND'
$Temporal = Join-Path $env:TEMP 'rnd_demo_ai_verificacion.env'

# Credenciales falsas con la forma de las reales. Si alguna sobrevive al
# filtrado, aparece aca.
@(
    'MINIMAX_API_KEY=eyJhbGciOiJIUzI1NiJ9.clave-falsa-que-no-debe-viajar'
    'RND_PDF_AI_API_KEY=sk-or-v1-clave-falsa-que-no-debe-viajar'
    'RND_PDF_AI_URL=https://vogelconsultoria.com.ar/rnd-ia/proxy.php'
    'RND_PDF_AI_TOKEN=demo-2026'
    'RND_PDF_AI_MODEL=MiniMax-M3'
    'RND_PDF_AI_TIMEOUT=120'
    'MYSQL_PASSWORD=otra-credencial-que-tampoco-debe-viajar'
) | Set-Content -LiteralPath $Temporal -Encoding UTF8

$Destino = Join-Path $env:TEMP 'rnd_demo_env_generado.env'
Remove-Item -Force $Destino -ErrorAction SilentlyContinue

Write-Host '--- 1. Lectura del archivo de secretos ---' -ForegroundColor Cyan
$config = Get-DemoAiConfig -RepoRoot $RepoRoot -ExplicitPath $Temporal
Write-Host ("origen: " + $config.Source)
Write-Host ("claves leidas: " + (($config.Values.Keys | Sort-Object) -join ', '))

Write-Host ''
Write-Host '--- 2. Escritura del .env de la demo ---' -ForegroundColor Cyan
Write-DemoAiEnv -Values $config.Values -Destination $Destino
Write-Host (Get-Content -LiteralPath $Destino -Raw)

Write-Host ''
Write-Host '--- 3. Verificacion ---' -ForegroundColor Cyan
$generado = Get-Content -LiteralPath $Destino -Raw
$prohibidas = @('MINIMAX_API_KEY', 'RND_PDF_AI_API_KEY', 'clave-falsa', 'MYSQL_PASSWORD')
$fallas = @()

foreach ($p in $prohibidas) {
    if ($generado -match [regex]::Escape($p)) {
        Write-Host ("FALLO: aparece '$p' en el .env de la demo") -ForegroundColor Red
        $fallas += $p
    } else {
        Write-Host ("ok: '$p' NO esta en el .env de la demo") -ForegroundColor Green
    }
}

if ($generado -match [regex]::Escape('RND_PDF_AI_URL=https://vogelconsultoria.com.ar/rnd-ia/proxy.php')) {
    Write-Host 'ok: la URL del proxy si viaja' -ForegroundColor Green
} else {
    Write-Host 'FALLO: falta la URL del proxy' -ForegroundColor Red
    $fallas += 'RND_PDF_AI_URL'
}

Write-Host ''
Write-Host '--- 4. Barrera: el build aborta si se le pasa una credencial ---' -ForegroundColor Cyan
try {
    Write-DemoAiEnv -Values @{ MINIMAX_API_KEY = 'inyectada'; RND_PDF_AI_URL = 'https://x' } -Destination (Join-Path $env:TEMP 'rnd_demo_env_barrera.env')
    Write-Host 'FALLO: la barrera no aborto' -ForegroundColor Red
    $fallas += 'barrera'
} catch {
    Write-Host ("ok: abortó -> " + $_.Exception.Message) -ForegroundColor Green
}

Remove-Item -Force $Temporal, $Destino -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $env:TEMP 'rnd_demo_env_barrera.env') -ErrorAction SilentlyContinue

Write-Host ''
if ($fallas.Count -eq 0) {
    Write-Host 'RESULTADO: todas las comprobaciones pasaron.' -ForegroundColor Green
} else {
    Write-Host ("RESULTADO: fallaron -> " + ($fallas -join ', ')) -ForegroundColor Red
    exit 1
}
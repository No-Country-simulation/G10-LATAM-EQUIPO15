param(
    [string]$OciEnvFile = (Join-Path $env:LOCALAPPDATA 'NuevaMente\oci-storage\oci.env'),
    [string]$GeminiEnvFile
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if (-not $GeminiEnvFile) { $GeminiEnvFile = Join-Path $taskRoot 'ia\.env' }
foreach ($taskFile in @($GeminiEnvFile, $OciEnvFile)) {
    if (-not (Test-Path -LiteralPath $taskFile -PathType Leaf)) {
        throw "Falta la configuracion privada: $taskFile. Revisar docs/CONFIGURAR_OBJECT_STORAGE.md."
    }
}
$taskGeminiPath = (Resolve-Path -LiteralPath $GeminiEnvFile).Path
$taskOciPath = (Resolve-Path -LiteralPath $OciEnvFile).Path

Push-Location -LiteralPath $taskRoot
try {
    $taskDockerVersion = & docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw 'Abrir Docker Desktop y esperar a que el motor Linux este listo.'
    }
    $taskArgs = @('compose', '--env-file', $taskGeminiPath, '--env-file', $taskOciPath,
        '-f', 'compose.integration.yaml', '-f', 'compose.oci.credentials.yaml')
    & docker @taskArgs config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'La configuracion de Docker Compose no es valida.' }
    & docker @taskArgs up --build -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Docker no confirmo el arranque de los servicios.' }
    & docker @taskArgs exec -T backend python -c 'from app.core.config import settings; import sys; sys.exit(0 if settings.OCI_STORAGE_ENABLED else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'El backend arranco con OCI desactivado; revisar el archivo OCI de entorno.' }
    $taskAddress = & docker @taskArgs port frontend 8080
    if ($LASTEXITCODE -ne 0 -or -not $taskAddress) { throw 'No se pudo determinar el puerto del frontend.' }
    $taskUrl = 'http://' + (($taskAddress | Select-Object -First 1).Trim())
    $taskResponse = Invoke-WebRequest -UseBasicParsing -Uri $taskUrl -TimeoutSec 10
    if ($taskResponse.StatusCode -ne 200) { throw 'El frontend no respondio correctamente.' }
    Write-Output "NuevaMente disponible: $taskUrl"
    Write-Output 'OCI activado. Una generacion debe mostrar original y JSON guardados en OCI.'
    Write-Output 'Los datos de IA se conservan en el volumen de Docker entre arranques.'
} finally {
    Pop-Location
}

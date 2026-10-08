param(
    [switch]$Gemini,
    [string]$EnvFile = 'ia/.env',
    [string]$ResultsDirectory,
    [string]$DockerContext
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPreviousLocation = Get-Location
$taskProject = 'nuevamente-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$script:taskDockerPrefix = @()
if ($DockerContext) { $script:taskDockerPrefix = @('--context', $DockerContext) }
if (-not $ResultsDirectory) {
    $ResultsDirectory = Join-Path ([IO.Path]::GetTempPath()) $taskProject
}
$taskResults = [IO.Path]::GetFullPath($ResultsDirectory)
New-Item -ItemType Directory -Path $taskResults -Force | Out-Null
$script:taskComposeArgs = @('compose', '-p', $taskProject, '-f', 'compose.tests.yaml')
$taskPreviousArtifacts = $env:TEST_ARTIFACTS_DIR
$taskLiveStarted = $false
$taskExit = 0
$taskStep = 'preparacion'

function Invoke-TestDocker {
    param([string[]]$DockerArgs)
    & docker @script:taskDockerPrefix @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker devolvio codigo $LASTEXITCODE. El ensayo no se considera aprobado." }
}

function Read-Persistence {
    param([string]$Phase, [string]$DocumentId)
    $taskJson = & docker @script:taskDockerPrefix @script:taskComposeArgs exec -T ia-http python /checks/inspect_persistence.py $DocumentId
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo comprobar el volumen de IA.' }
    $taskText = $taskJson -join "`n"
    Set-Content -LiteralPath (Join-Path $taskResults "estado-$Phase.json") -Value $taskText -Encoding UTF8
    return ($taskText | ConvertFrom-Json)
}

function Read-ProviderStages {
    param([string]$Phase)
    # Se conservan solo contadores. No se imprimen ni guardan los logs completos.
    $taskLines = & docker @script:taskDockerPrefix @script:taskComposeArgs logs --no-color ia-http
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron leer las etapas del proveedor.' }
    $taskCounts = @{}
    $taskFailures = @()
    foreach ($taskLine in $taskLines) {
        if ($taskLine -match 'IA proveedor etapa=(\w+) estado=inicio') {
            $taskStage = $Matches[1]
            if (-not $taskCounts.ContainsKey($taskStage)) { $taskCounts[$taskStage] = 0 }
            $taskCounts[$taskStage] += 1
        }
        if ($taskLine -match 'IA proveedor etapa=(\w+) estado=fallo tipo=(\w+) codigo=(\d+|None) categoria=(\w+) segundos=([\d.]+)') {
            $taskFailures += [pscustomobject]@{etapa=$Matches[1];tipo=$Matches[2];codigo=$Matches[3];categoria=$Matches[4];segundos=$Matches[5]}
        }
    }
    $taskCounts | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskResults "etapas-$Phase.json") -Encoding UTF8
    ConvertTo-Json -InputObject $taskFailures | Set-Content -LiteralPath (Join-Path $taskResults "fallos-$Phase.json") -Encoding UTF8
    return $taskCounts
}

function Assert-PersistenceUnchanged {
    param($Before, $After)
    if (($Before.chunk_ids | ConvertTo-Json -Compress) -ne ($After.chunk_ids | ConvertTo-Json -Compress)) {
        throw 'Los ids de vectores cambiaron o se duplicaron.'
    }
    if ($Before.document_record_sha256 -ne $After.document_record_sha256) {
        throw 'El registro del documento cambio durante la reutilizacion.'
    }
    if (($Before.cache_hashes | ConvertTo-Json -Depth 20 -Compress) -ne ($After.cache_hashes | ConvertTo-Json -Depth 20 -Compress)) {
        throw 'La cache cambio durante la reutilizacion.'
    }
}

try {
    Set-Location -LiteralPath $taskRoot
    if (-not $Gemini) {
        $taskStep = 'construccion de imagenes sin proveedores'
        Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + @('build', 'backend-tests', 'ia-tests'))
        foreach ($taskService in @('backend-tests', 'ia-tests')) {
            $taskStep = $taskService
            $taskCommand = @('run', '--rm', '--volume', "${taskResults}:/results", $taskService, 'python', '-m', 'pytest')
            if ($taskService -eq 'backend-tests') {
                $taskCommand += @('tests', '-q', '--tb=short', '-p', 'no:cacheprovider', '--junitxml=/results/backend.xml')
            } else {
                $taskCommand += @('ia/tests', 'nuevamente-ai-core/tests', '-q', '--tb=short', '-p', 'no:cacheprovider', '--timeout=30', '--junitxml=/results/dataia-ai-core.xml')
            }
            Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + $taskCommand)
        }
        Write-Host 'Backend, Data/IA y AI Core: pruebas sin red aprobadas.'
    } else {
        $taskStep = 'archivo local de credenciales; revisar -EnvFile'
        $taskEnvPath = if ([IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $taskRoot $EnvFile }
        if (-not (Test-Path -LiteralPath $taskEnvPath -PathType Leaf)) { throw 'Falta el archivo local de credenciales. Indicar -EnvFile o crear ia/.env.' }
        $env:TEST_ARTIFACTS_DIR = $taskResults
        $script:taskComposeArgs = @('compose', '--env-file', $taskEnvPath, '-p', $taskProject, '-f', 'compose.integration.tests.yaml')
        $taskStep = 'construccion y arranque del entorno Gemini'
        Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + @('build', 'backend', 'ia-http', 'tests'))
        $taskLiveStarted = $true
        Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + @('up', '-d', '--no-build', '--wait', '--wait-timeout', '120', 'backend', 'ia-http'))
        $taskPdf = Join-Path $taskRoot 'nuevamente-ai-core/tests/JWT en OCI.pdf'
        $taskDocumentId = 'doc-' + (Get-FileHash -LiteralPath $taskPdf -Algorithm SHA256).Hash.Substring(0, 16).ToLowerInvariant()
        $taskInitial = Read-Persistence -Phase 'inicial' -DocumentId $taskDocumentId
        if ($taskInitial.vectors -ne 0 -or $taskInitial.document_record -or $taskInitial.document_cache) { throw 'El volumen de ensayo no esta vacio.' }

        $taskStep = 'adaptacion en frio y persistencia inicial'
        Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + @('run', '--rm', '--no-deps', '-e', 'TEST_PHASE=frio', 'tests', 'python', '-m', 'pytest', '/checks/test_gemini.py', '-q', '--tb=short', '-p', 'no:cacheprovider', '--junitxml=/results/gemini-frio.xml'))
        $taskCold = Read-Persistence -Phase 'frio' -DocumentId $taskDocumentId
        $taskColdStages = Read-ProviderStages -Phase 'frio'
        if ($taskCold.vectors -le 0 -or -not $taskCold.document_record -or -not $taskCold.document_cache) { throw 'No se persistieron los vectores, el registro o la cache.' }
        foreach ($taskStage in @('ENRIQUECIMIENTO_DOCUMENTO', 'ENRIQUECIMIENTO_LOTE', 'EMBEDDINGS_DOCUMENTO', 'GENERADOR', 'CRITICO')) {
            if ($taskColdStages[$taskStage] -lt 1) { throw "No hay evidencia de ejecucion de la etapa $taskStage." }
        }
        $taskOldId = & docker @script:taskDockerPrefix @script:taskComposeArgs ps -q ia-http
        if ($LASTEXITCODE -ne 0 -or -not $taskOldId) { throw 'No se pudo identificar el contenedor inicial.' }
        $taskStep = 'recreacion del contenedor y conservacion de datos'
        Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + @('up', '-d', '--no-deps', '--no-build', '--force-recreate', '--wait', '--wait-timeout', '120', 'ia-http'))
        $taskNewId = & docker @script:taskDockerPrefix @script:taskComposeArgs ps -q ia-http
        if ($LASTEXITCODE -ne 0 -or -not $taskNewId -or $taskOldId -eq $taskNewId) { throw 'El contenedor de IA no fue recreado.' }
        $taskRecreated = Read-Persistence -Phase 'recreado' -DocumentId $taskDocumentId
        Assert-PersistenceUnchanged -Before $taskCold -After $taskRecreated

        $taskStep = 'segunda adaptacion y reutilizacion de cache'
        Invoke-TestDocker -DockerArgs ($script:taskComposeArgs + @('run', '--rm', '--no-deps', '-e', 'TEST_PHASE=reutilizado', 'tests', 'python', '-m', 'pytest', '/checks/test_gemini.py', '-q', '--tb=short', '-p', 'no:cacheprovider', '--junitxml=/results/gemini-reutilizado.xml'))
        $taskWarm = Read-Persistence -Phase 'reutilizado' -DocumentId $taskDocumentId
        $taskWarmStages = Read-ProviderStages -Phase 'reutilizado'
        Assert-PersistenceUnchanged -Before $taskCold -After $taskWarm
        foreach ($taskStage in @('ENRIQUECIMIENTO_DOCUMENTO', 'ENRIQUECIMIENTO_LOTE', 'ENRIQUECIMIENTO_FRAGMENTO', 'EMBEDDINGS_DOCUMENTO')) {
            if ($taskWarmStages[$taskStage] -gt 0) { throw "La reutilizacion volvio a ejecutar $taskStage." }
        }
        foreach ($taskStage in @('GENERADOR', 'CRITICO')) {
            if ($taskWarmStages[$taskStage] -lt 1) { throw "La segunda adaptacion no ejecuto $taskStage." }
        }
        [pscustomobject]@{document_id=$taskDocumentId;vectores=$taskWarm.vectors;contenedor_recreado=$true;cache_reutilizada=$true;modelo=$taskWarm.model} |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskResults 'comparacion.json') -Encoding UTF8
        Write-Host 'Backend -> IA -> Gemini: adaptaciones y persistencia aprobadas.'
    }
} catch {
    # No imprimir excepciones o configuración expandida que puedan contener claves.
    Write-Host "El ensayo fallo en: $taskStep. Revisar los resultados locales; no se considera aprobado."
    $taskExit = 1
} finally {
    if ($taskLiveStarted) {
        if ($taskExit -ne 0) {
            try { Read-ProviderStages -Phase 'al-cierre' | Out-Null } catch { Write-Host 'No se pudieron conservar los contadores de fallo.' }
        }
        # Solo el proyecto aleatorio creado por este script: nunca el de trabajo.
        & docker @script:taskDockerPrefix @script:taskComposeArgs down --volumes
        if ($LASTEXITCODE -ne 0) { $taskExit = 1 }
    }
    $env:TEST_ARTIFACTS_DIR = $taskPreviousArtifacts
    Set-Location -LiteralPath $taskPreviousLocation.Path
    Write-Host "Resultados privados: $taskResults"
}
exit $taskExit

param(
    [ValidateSet('Login', 'Validar', 'Revisar', 'Plan', 'Desplegar')]
    [string]$Accion = 'Revisar',
    [string]$SuscripcionId,
    [string[]]$Regiones = @('brazilsouth', 'eastus2', 'centralus', 'westus3'),
    [string]$DirectorioPrivado = (Join-Path $env:LOCALAPPDATA 'NuevaMente\azure'),
    [string]$OciDirectorio = (Join-Path $env:LOCALAPPDATA 'NuevaMente\oci-storage'),
    [string]$GeminiEnvFile
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskState = [IO.Path]::GetFullPath($DirectorioPrivado)
$taskRootPrefix = $taskRoot.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
if ($taskState.Equals($taskRoot, [StringComparison]::OrdinalIgnoreCase) -or
    $taskState.StartsWith($taskRootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'El estado y la sesion Azure deben guardarse fuera del repositorio.'
}
$taskAncestor = $taskState
while ($taskAncestor) {
    if (Test-Path -LiteralPath (Join-Path $taskAncestor '.git')) { throw 'El directorio privado esta dentro de Git.' }
    if ((Test-Path -LiteralPath $taskAncestor) -and
        ((Get-Item -LiteralPath $taskAncestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'El directorio privado contiene un enlace o junction.'
    }
    $taskAncestor = [IO.Path]::GetDirectoryName($taskAncestor)
}
New-Item -ItemType Directory -Path $taskState -Force | Out-Null
$taskAcl = New-Object Security.AccessControl.DirectorySecurity
$taskAcl.SetAccessRuleProtection($true, $false)
$taskSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$taskAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
    $taskSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
[IO.Directory]::SetAccessControl($taskState, $taskAcl)

$taskImage = 'nuevamente-azure-tools:tf1.16.6-az2.91.0'
$taskDockerCheck = & docker version --format '{{.Server.Version}}' 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Abrir Docker Desktop y esperar a que el motor Linux este listo.' }
$taskImageCheck = & docker image ls --quiet $taskImage
if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar la imagen de herramientas.' }
if (-not $taskImageCheck) {
    & docker build -t $taskImage -f (Join-Path $taskRoot 'infra\azure\Dockerfile.tools') (Join-Path $taskRoot 'infra\azure')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la imagen de herramientas Azure.' }
}
$taskRun = @('run', '--rm')
if ($Accion -eq 'Login') { $taskRun += '-it' }
$taskRun += @('--mount', "type=bind,src=$taskState,dst=/state",
    '--mount', ('type=bind,src=' + (Join-Path $taskRoot 'infra\azure') + ',dst=/module,readonly'),
    '--mount', ('type=bind,src=' + (Join-Path $taskRoot 'scripts\azure') + ',dst=/scripts,readonly'))
if ($Accion -eq 'Desplegar') {
    if (-not $GeminiEnvFile) { $GeminiEnvFile = Join-Path $taskRoot 'ia\.env' }
    foreach ($taskFile in @($GeminiEnvFile, (Join-Path $OciDirectorio 'oci.env'),
        (Join-Path $OciDirectorio 'oci\config'), (Join-Path $OciDirectorio 'oci\key.pem'))) {
        if (-not (Test-Path -LiteralPath $taskFile -PathType Leaf)) { throw "Falta la configuracion privada: $taskFile" }
    }
    & python (Join-Path $taskRoot 'scripts\azure\empaquetar.py') $taskRoot (Join-Path $taskState 'aplicacion.tar.gz')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo empaquetar el codigo local.' }
    $taskRun += @('--mount', "type=bind,src=$OciDirectorio,dst=/source-oci,readonly",
        '--mount', ('type=bind,src=' + (Resolve-Path -LiteralPath $GeminiEnvFile).Path + ',dst=/source-gemini.env,readonly'))
}
$taskRun += @($taskImage, $Accion.ToLowerInvariant(), '--regions', ($Regiones -join ','))
if ($SuscripcionId) { $taskRun += @('--subscription', $SuscripcionId) }
& docker @taskRun
if ($LASTEXITCODE -ne 0) { throw "Azure no completo la accion $Accion. El estado privado se conserva para retomar." }

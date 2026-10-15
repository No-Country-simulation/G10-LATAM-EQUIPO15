#!/usr/bin/env python3
"""Configura OCI Object Storage desde Cloud Shell y exporta acceso para Docker.

Solo usa la biblioteca estandar, OCI CLI y OpenSSL disponibles en Cloud Shell.
No cambia Terraform ni los permisos IAM del usuario que ejecuta el script.
"""
import argparse
import base64
import configparser
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile


OPERATIONS = {
    ("iam", "region-subscription", "list"),
    ("iam", "user", "api-key", "list"),
    ("iam", "user", "api-key", "upload"),
    ("os", "ns", "get"),
    ("os", "bucket", "list"),
    ("os", "bucket", "get"),
    ("os", "bucket", "create"),
    ("os", "object", "put"),
    ("os", "object", "get"),
}

WINDOWS_INSTALLER = r'''param(
    [string]$Repositorio = (Get-Location).Path,
    [string]$DirectorioPrivado = (Join-Path $env:LOCALAPPDATA 'NuevaMente\oci-storage'),
    [switch]$Iniciar
)
$ErrorActionPreference = 'Stop'
$taskRepo = (Resolve-Path -LiteralPath $Repositorio).Path
foreach ($taskCompose in @('compose.integration.yaml', 'compose.oci.credentials.yaml')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskRepo $taskCompose))) {
        throw "No se encuentra $taskCompose en $taskRepo. Usar la rama con integracion OCI."
    }
}
$taskSource = Join-Path $PSScriptRoot 'oci'
$taskTarget = [IO.Path]::GetFullPath($DirectorioPrivado)
$taskRepoPrefix = $taskRepo.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
if ($taskTarget.Equals($taskRepo, [StringComparison]::OrdinalIgnoreCase) -or
    $taskTarget.StartsWith($taskRepoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Las credenciales deben estar fuera del repositorio.'
}
# Evitar enlaces/junctions en el destino antes de escribir una clave privada.
$taskAncestor = $taskTarget
while ($taskAncestor) {
    if (Test-Path -LiteralPath (Join-Path $taskAncestor '.git')) {
        throw 'El destino de credenciales esta dentro de un repositorio Git.'
    }
    if (Test-Path -LiteralPath $taskAncestor) {
        if ((Get-Item -LiteralPath $taskAncestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'El destino de credenciales contiene un enlace o junction.'
        }
    }
    $taskAncestor = [IO.Path]::GetDirectoryName($taskAncestor)
}
foreach ($taskFile in @('config', 'key.pem')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskSource $taskFile) -PathType Leaf)) {
        throw "Falta el archivo privado $taskFile en el paquete."
    }
}
$taskKeyTarget = Join-Path $taskTarget 'oci\key.pem'
if (Test-Path -LiteralPath $taskKeyTarget) {
    if ((Get-FileHash -LiteralPath $taskKeyTarget -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath (Join-Path $taskSource 'key.pem') -Algorithm SHA256).Hash) {
        throw 'Ya hay otra clave instalada. No se reemplazara automaticamente.'
    }
}
New-Item -ItemType Directory -Path $taskTarget -Force | Out-Null
$taskSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$taskAcl = New-Object Security.AccessControl.DirectorySecurity
$taskAcl.SetAccessRuleProtection($true, $false)
$taskRule = [Security.AccessControl.FileSystemAccessRule]::new(
    $taskSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$taskAcl.AddAccessRule($taskRule)
# Cambiar solo la DACL; no tocar propietario ni auditoria (no requiere privilegios admin).
[IO.Directory]::SetAccessControl($taskTarget, $taskAcl)
$taskCredentials = Join-Path $taskTarget 'oci'
New-Item -ItemType Directory -Path $taskCredentials -Force | Out-Null
foreach ($taskFile in @('config', 'key.pem')) {
    $taskDestination = Join-Path $taskCredentials $taskFile
    if ((Test-Path -LiteralPath $taskDestination) -and
        ((Get-Item -LiteralPath $taskDestination -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Un archivo del destino es un enlace.'
    }
    Copy-Item -LiteralPath (Join-Path $taskSource $taskFile) -Destination $taskDestination -Force
}
$taskEnvPath = Join-Path $taskTarget 'oci.env'
if ((Test-Path -LiteralPath $taskEnvPath) -and
    ((Get-Item -LiteralPath $taskEnvPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'El archivo de entorno del destino es un enlace.'
}
$taskEnvContent = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'oci.env'))
$taskEnvContent = $taskEnvContent.Replace('@@OCI_CREDENTIALS_DIRECTORY@@', $taskCredentials.Replace('\','/'))
[IO.File]::WriteAllText($taskEnvPath, $taskEnvContent, (New-Object Text.UTF8Encoding($false)))
Write-Output "Configuracion privada instalada: $taskEnvPath"
if ($Iniciar) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskRepo 'ia\.env'))) {
        throw 'Falta ia/.env con la clave de Gemini. OCI ya quedo configurado.'
    }
    Push-Location -LiteralPath $taskRepo
    try {
        $taskArgs = @('compose', '--env-file', 'ia/.env', '--env-file', $taskEnvPath,
            '-f', 'compose.integration.yaml', '-f', 'compose.oci.credentials.yaml')
        & docker @taskArgs config --quiet
        if ($LASTEXITCODE -ne 0) { throw 'Docker Compose no valido la configuracion.' }
        & docker @taskArgs up --build -d --wait
        if ($LASTEXITCODE -ne 0) { throw 'Docker Compose no confirmo el arranque.' }
        Write-Output 'Servicios iniciados. Falta generar contenido y comprobar almacenamiento_oci.status_upload=subido.'
    } finally { Pop-Location }
} else {
    Write-Output 'Para iniciar la aplicacion, repetir este comando agregando -Iniciar.'
}
'''


class SetupError(RuntimeError):
    pass


class OCIError(SetupError):
    def __init__(self, operation, code="NO_DETERMINADO"):
        self.operation, self.code = operation, code
        super().__init__("Fallo en " + " ".join(operation) + ": " + code)


def require(condition, message):
    if not condition:
        raise SetupError(message)


def log(message):
    print(message, flush=True)


def local_error_location(error):
    """Mostrar funcion/linea propias sin imprimir valores, mensajes ni claves."""
    location = "etapa no determinada"
    trace = error.__traceback__
    while trace:
        if trace.tb_frame.f_code.co_filename == __file__:
            location = trace.tb_frame.f_code.co_name + "(), linea " + str(trace.tb_lineno)
        trace = trace.tb_next
    return location


def error_code(stderr):
    # No imprimir mensajes ni argumentos: pueden contener rutas y credenciales.
    try:
        detail, _ = json.JSONDecoder().raw_decode(stderr[stderr.index("{"):])
        code = detail.get("code", "NO_DETERMINADO")
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", code):
            return code
    except (ValueError, AttributeError):
        pass
    return "NO_DETERMINADO"


class CLI:
    def __init__(self, region, config=None):
        self.region, self.config = region, config

    def call(self, operation, *args, result="data"):
        require(operation in OPERATIONS, "Operacion fuera del alcance de Object Storage.")
        command = ["oci", *operation, *map(str, args), "--region", self.region,
                   "--output", "json", "--max-retries", "0", "--connection-timeout", "10",
                   "--read-timeout", "30", "--cli-rc-file", os.devnull]
        if operation == ("os", "bucket", "get"):
            # GetBucket devuelve auto-tiering=null si no se solicita este campo.
            command += ["--fields", "autoTiering"]
        environment = dict(os.environ)
        if self.config:
            # La prueba debe usar la clave exportada, nunca la sesion Cloud Shell.
            environment = {k: v for k, v in environment.items() if not k.startswith("OCI_CLI_")}
            command += ["--auth", "api_key", "--config-file", str(self.config), "--profile", "DEFAULT"]
        try:
            response = subprocess.run(command, capture_output=True, text=True,
                                      timeout=90, env=environment, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OCIError(operation, "RESULTADO_NO_CONFIRMADO") from exc
        if response.returncode:
            raise OCIError(operation, error_code(response.stderr))
        if result == "file":
            return None  # GetObject escribe en --file, no necesariamente en stdout.
        if operation[-1] == "list" and not response.stdout.strip():
            require("Query returned empty result" not in response.stderr,
                    "OCI CLI oculto los datos de una consulta.")
            return []
        try:
            payload = json.loads(response.stdout)
        except ValueError as exc:
            raise OCIError(operation, "JSON_NO_DETERMINADO") from exc
        if result == "headers":
            require(isinstance(payload, dict) and payload.get("etag"),
                    "OCI no confirmo el ETag de la subida.")
            return payload
        require(isinstance(payload, dict) and "data" in payload,
                "OCI no devolvio datos confirmados.")
        return payload["data"]


def write_private(path, value):
    require(not path.is_symlink(), "No escribir archivos privados a traves de enlaces.")
    encoded = value.encode("utf-8") if isinstance(value, str) else value
    temporary = path.with_name(path.name + ".tmp")
    require(not temporary.exists() and not temporary.is_symlink(),
            "Hay un archivo temporal pendiente. Revisarlo antes de continuar.")
    with temporary.open("xb") as stream:
        stream.write(encoded)
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def detect_identity(args):
    parser = configparser.ConfigParser(interpolation=None)
    configured = os.environ.get("OCI_CLI_CONFIG_FILE")
    config_file = Path(configured) if configured else Path.home() / ".oci/config"
    if config_file.is_file():
        parser.read(config_file, encoding="utf-8")
    profile = os.environ.get("OCI_CLI_PROFILE", "DEFAULT")
    values = parser[profile] if parser.has_section(profile) or profile == "DEFAULT" else {}
    tenancy = os.environ.get("OCI_TENANCY") or values.get("tenancy", "")
    user = os.environ.get("OCI_CS_USER_OCID") or values.get("user", "")
    require(re.fullmatch(r"ocid1\.tenancy\.oc1\.\.[A-Za-z0-9_-]+", tenancy),
            "No se detecto la tenancy. Ejecutar desde Cloud Shell de tu cuenta.")
    require(re.fullmatch(r"ocid1\.user\.oc1\.\.[A-Za-z0-9_-]+", user),
            "No se detecto tu usuario OCI. Ejecutar desde Cloud Shell de tu cuenta.")
    compartment = args.compartment or tenancy
    require(re.fullmatch(r"ocid1\.(?:tenancy|compartment)\.oc1\.\.[A-Za-z0-9_-]+", compartment),
            "El compartment no tiene un OCID valido.")
    region = args.region or os.environ.get("OCI_REGION") or values.get("region") or "sa-saopaulo-1"
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", region), "Region no valida.")
    return tenancy, user, compartment, region


def home_region(cli, tenancy, requested):
    regions = cli.call(("iam", "region-subscription", "list"), "--tenancy-id", tenancy, "--all")
    require(isinstance(regions, list) and all(isinstance(r, dict) for r in regions),
            "Regiones de la cuenta NO DETERMINADAS.")
    homes = [r.get("region-name") for r in regions if r.get("is-home-region") is True]
    require(len(homes) == 1 and isinstance(homes[0], str), "Home region NO DETERMINADA.")
    require(not requested or requested == homes[0],
            "Para esta entrega gratuita se requiere la home region: " + homes[0])
    return homes[0]


def validate_bucket(bucket, identity):
    require(isinstance(bucket, dict) and bucket.get("name") == identity["bucket"],
            "La respuesta no corresponde al bucket solicitado.")
    require(bucket.get("compartment-id") == identity["compartment"],
            "El bucket pertenece a otro compartment; no se modificara.")
    require(bucket.get("namespace") == identity["namespace"], "Namespace del bucket inesperado.")
    require(bucket.get("public-access-type") == "NoPublicAccess", "El bucket existente debe ser privado.")
    require(bucket.get("storage-tier") == "Standard", "El bucket existente debe ser Standard.")
    require(bucket.get("auto-tiering") == "Disabled", "El bucket tiene auto-tiering distinto a Disabled.")
    require(bucket.get("versioning") == "Disabled", "El bucket tiene versionado; revisar su consumo antes de usarlo.")
    require(not bucket.get("kms-key-id"), "El bucket usa una clave Vault propia; revisar antes de usarlo.")


def ensure_bucket(cli, identity):
    buckets = cli.call(("os", "bucket", "list"), "--namespace-name", identity["namespace"],
                       "--compartment-id", identity["compartment"], "--all")
    require(isinstance(buckets, list) and all(isinstance(b, dict) for b in buckets),
            "Listado de buckets NO DETERMINADO.")
    if not any(item.get("name") == identity["bucket"] for item in buckets):
        log("Creando bucket privado Standard: " + identity["bucket"])
        cli.call(("os", "bucket", "create"), "--namespace-name", identity["namespace"],
                 "--compartment-id", identity["compartment"], "--name", identity["bucket"],
                 "--public-access-type", "NoPublicAccess", "--storage-tier", "Standard",
                 "--auto-tiering", "Disabled", "--versioning", "Disabled")
    else:
        log("Reutilizando bucket: " + identity["bucket"])
    bucket = cli.call(("os", "bucket", "get"), "--namespace-name", identity["namespace"],
                      "--name", identity["bucket"])
    validate_bucket(bucket, identity)
    return bucket


def openssl(*args):
    try:
        response = subprocess.run(["openssl", *map(str, args)], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError("OpenSSL no termino; no se registro otra clave.") from exc
    require(response.returncode == 0, "OpenSSL no pudo preparar la clave de firma.")
    return response.stdout


def md5_for_oci(content):
    """MD5 identifica la clave OCI y comprueba bytes; no firma ni autentica."""
    try:
        try:
            return hashlib.md5(content, usedforsecurity=False)
        except TypeError:
            # Python anterior a 3.9 puede no ofrecer usedforsecurity.
            return hashlib.md5(content)
    except ValueError as exc:
        raise SetupError("Python no permite el MD5 requerido para la huella/checksum de OCI, "
                         "incluso como uso no criptografico. No se modifico el modo FIPS.") from exc


def prepare_key(directory):
    private, public = directory / "key.pem", directory / "public.pem"
    require(not private.is_symlink() and not public.is_symlink(), "La clave no debe ser un enlace.")
    if not private.exists():
        openssl("genrsa", "-out", private, "2048")
    private.chmod(0o600)
    public_pem = openssl("rsa", "-in", private, "-pubout")
    write_private(public, public_pem)
    der = openssl("rsa", "-in", private, "-pubout", "-outform", "DER")
    digest = md5_for_oci(der).hexdigest()
    return ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))


def ensure_api_key(cli, user, fingerprint, public):
    operation = ("iam", "user", "api-key", "list")
    keys = cli.call(operation, "--user-id", user, "--all")
    require(isinstance(keys, list) and all(isinstance(k, dict) for k in keys),
            "Claves API NO DETERMINADAS.")
    if not any(k.get("fingerprint") == fingerprint for k in keys):
        require(len(keys) < 3, "Tu usuario ya tiene 3 claves API. No se borrara ninguna automaticamente.")
        log("Registrando la clave publica de esta configuracion en tu usuario.")
        cli.call(("iam", "user", "api-key", "upload"), "--user-id", user, "--key-file", public)
    else:
        log("Reutilizando la clave API registrada por este script.")
    for attempt in range(10):
        keys = cli.call(operation, "--user-id", user, "--all")
        require(isinstance(keys, list) and all(isinstance(k, dict) for k in keys),
                "Claves API NO DETERMINADAS.")
        matching = [k for k in keys if k.get("fingerprint") == fingerprint]
        if matching and matching[0].get("lifecycle-state") == "ACTIVE":
            return
        if attempt < 9:
            time.sleep(3)
    raise SetupError("La clave aun no figura ACTIVE. Repetir el mismo comando para retomar.")


def credential_config(identity, fingerprint, key_path):
    return ("[DEFAULT]\nuser=" + identity["user"] + "\ntenancy=" + identity["tenancy"]
            + "\nfingerprint=" + fingerprint + "\nregion=" + identity["region"]
            + "\nkey_file=" + str(key_path) + "\n")


def probe_storage(cli, identity, directory, probe_id):
    require(re.fullmatch(r"[a-f0-9]{32}", probe_id), "Identificador de prueba no valido.")
    arguments = ("--namespace-name", identity["namespace"], "--bucket-name", identity["bucket"])
    source = b"NuevaMente: comprobacion de documento original en OCI.\n"
    document = json.dumps({"tipo": "comprobacion_object_storage", "original_sha256":
                           hashlib.sha256(source).hexdigest()}, sort_keys=True).encode("utf-8")
    result = []
    for filename, content, content_type in (("original.txt", source, "text/plain"),
                                            ("resultado.json", document, "application/json")):
        name = "comprobacion-oci/" + probe_id + "/" + filename
        upload, download = directory / filename, directory / (filename + ".descargado")
        write_private(upload, content)
        expected_md5 = base64.b64encode(md5_for_oci(content).digest()).decode("ascii")
        headers = cli.call(("os", "object", "put"), *arguments, "--name", name, "--file", upload,
                           "--content-type", content_type, "--content-md5", expected_md5,
                           "--no-multipart", "--force", result="headers")
        require(headers.get("opc-content-md5") == expected_md5, "OCI no confirmo el checksum de la subida.")
        # El backend tambien necesita sobrescribir un resultado identico al repetirlo.
        if filename == "original.txt":
            headers = cli.call(("os", "object", "put"), *arguments, "--name", name, "--file", upload,
                               "--content-md5", expected_md5, "--if-match", headers["etag"],
                               "--no-multipart", "--force", result="headers")
            require(headers.get("opc-content-md5") == expected_md5, "Sobrescritura no confirmada.")
        require(not download.is_symlink(), "No descargar a traves de enlaces.")
        if download.exists():
            download.unlink()  # Solo el archivo de prueba local en el directorio privado.
        cli.call(("os", "object", "get"), *arguments, "--name", name, "--file", download,
                 "--if-match", headers["etag"], "--no-multipart", result="file")
        require(download.is_file() and download.read_bytes() == content,
                "El contenido descargado de OCI no coincide con el original.")
        download.chmod(0o600)
        result.append({"objeto": name, "sha256": hashlib.sha256(content).hexdigest()})
    return result


def docker_env(identity):
    return ("OCI_STORAGE_ENABLED=true\nOCI_AUTH_MODE=api_key\nOCI_CONFIG_FILE=/run/secrets/oci/config\n"
            "OCI_CONFIG_PROFILE=DEFAULT\nOCI_HTTP_TIMEOUT_SECONDS=10\nOCI_NAMESPACE=" + identity["namespace"]
            + "\nOCI_BUCKET_NAME=" + identity["bucket"] + "\nOCI_REGION=" + identity["region"]
            + "\nOCI_CREDENTIALS_DIRECTORY=@@OCI_CREDENTIALS_DIRECTORY@@\n")


def export_bundle(directory, identity, fingerprint, evidence):
    credentials = directory / "oci"
    credentials.mkdir(mode=0o700, exist_ok=True)
    require(not credentials.is_symlink(), "El directorio de credenciales no debe ser un enlace.")
    credentials.chmod(0o700)
    write_private(credentials / "key.pem", (directory / "key.pem").read_bytes())
    write_private(credentials / "config", credential_config(identity, fingerprint, "/run/secrets/oci/key.pem"))
    write_private(directory / "oci.env", docker_env(identity))
    write_private(directory / "conectar-docker.ps1", WINDOWS_INSTALLER)
    report = {"estado": "OBJECT_STORAGE_VALIDADO", **identity, "fingerprint": fingerprint,
              "pruebas": evidence, "momento_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "nota": "Validacion por OCI CLI con la clave API. Falta la prueba del backend con Gemini."}
    write_private(directory / "resultado.json", json.dumps(report, ensure_ascii=False, indent=2))
    write_private(directory / "LEEME.md",
                  "# Conexion privada de NuevaMente\n\nEste paquete contiene una clave privada de tu usuario OCI. "
                  "No compartirlo ni subirlo a GitHub. La clave hereda los permisos actuales de ese usuario.\n\n"
                  "En Windows: extraer el ZIP fuera del repositorio. Desde PowerShell en la rama con OCI, "
                  "ejecutar el archivo conectar-docker.ps1 de este paquete; agregar -Iniciar para levantar Docker. "
                  "Instala en %LOCALAPPDATA%/NuevaMente/oci-storage con acceso restringido a tu usuario.\n\n"
                  "OCI_CREDENTIALS_DIRECTORY se completa al ejecutar conectar-docker.ps1. "
                  "El config esta preparado para /run/secrets/oci/key.pem dentro de Docker.\n\n"
                  "Los dos objetos comprobacion-oci/... son evidencia pequena de subida y lectura real. "
                  "No son resultados generados por Gemini. El siguiente paso es validar la aplicacion completa.\n")
    archive = directory / "nuevamente-oci-conexion.zip"
    require(not archive.is_symlink(), "El ZIP de salida no debe ser un enlace.")
    members = ("oci/config", "oci/key.pem", "oci.env", "conectar-docker.ps1", "resultado.json", "LEEME.md")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for member in members:
            bundle.write(directory / member, member)
    archive.chmod(0o600)
    return archive


def configure(args):
    require(os.name == "posix", "Ejecutar este script en OCI Cloud Shell, no en Windows.")
    require(shutil.which("oci") and shutil.which("openssl"), "Falta OCI CLI u OpenSSL. Usar Cloud Shell.")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}", args.bucket), "Nombre de bucket no valido.")
    tenancy, user, compartment, initial_region = detect_identity(args)
    cli = CLI(initial_region)
    region = home_region(cli, tenancy, args.region)
    cli.region = region
    namespace = cli.call(("os", "ns", "get"), "--compartment-id", tenancy)
    require(isinstance(namespace, str) and re.fullmatch(r"[A-Za-z0-9_-]+", namespace), "Namespace NO DETERMINADO.")
    identity = {"tenancy": tenancy, "user": user, "compartment": compartment,
                "region": region, "namespace": namespace, "bucket": args.bucket}
    directory = Path(args.salida).expanduser().absolute()
    require(not any(parent.is_symlink() for parent in (directory, *directory.parents)),
            "La salida privada no debe contener enlaces.")
    require(not any((parent / ".git").exists() for parent in (directory, *directory.parents)),
            "La salida privada debe estar fuera de cualquier repositorio Git.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    import fcntl
    require(not (directory / "ejecucion.lock").is_symlink(), "El archivo de bloqueo no debe ser un enlace.")
    with (directory / "ejecucion.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SetupError("Ya hay otra ejecucion configurando Object Storage.") from exc
        state_path = directory / "estado.json"
        require(not state_path.is_symlink(), "El estado de identidad no debe ser un enlace.")
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            require(isinstance(state, dict), "El archivo de estado no es valido.")
            require(state.get("identidad") == identity, "La salida contiene datos de otra cuenta o bucket.")
            require(not state.get("fingerprint") or (directory / "key.pem").is_file(),
                    "Falta una clave privada ya registrada. Recuperarla antes de repetir.")
        else:
            require(not (directory / "key.pem").exists(), "Existe una clave sin estado de identidad; no reutilizarla a ciegas.")
            state = {"identidad": identity, "prueba_id": uuid.uuid4().hex}
            write_private(state_path, json.dumps(state))
        log("Configurando Object Storage en " + region + ".")
        ensure_bucket(cli, identity)
        log("Preparando la clave API y su huella para OCI.")
        fingerprint = prepare_key(directory)
        require(not state.get("fingerprint") or state["fingerprint"] == fingerprint,
                "La clave privada cambio desde la ejecucion anterior; no registrar otra a ciegas.")
        state["fingerprint"] = fingerprint
        write_private(state_path, json.dumps(state))
        ensure_api_key(cli, user, fingerprint, directory / "public.pem")
        local_config = directory / "config-cloudshell"
        write_private(local_config, credential_config(identity, fingerprint, directory / "key.pem"))
        key_cli = CLI(region, local_config)
        for attempt in range(10):
            try:
                bucket = key_cli.call(("os", "bucket", "get"), "--namespace-name", namespace, "--name", args.bucket)
                validate_bucket(bucket, identity)
                break
            except OCIError as exc:
                if exc.code not in {"NotAuthenticated", "NotAuthorizedOrNotFound"} or attempt == 9:
                    raise
                if attempt == 0:
                    log("Esperando propagacion de la clave API; solo se repiten consultas de lectura.")
                time.sleep(3)
        log("Probando crear, sobrescribir y descargar objetos con la clave API para Docker.")
        evidence = probe_storage(key_cli, identity, directory, state["prueba_id"])
        archive = export_bundle(directory, identity, fingerprint, evidence)
        log("OBJECT_STORAGE_VALIDADO: original y JSON descargados con contenido identico.")
        log("Descargar este ZIP privado desde Actions > Download file:")
        log(str(archive))
        log("El ZIP contiene una clave privada. Guardarlo fuera del repositorio y no compartirlo.")
        return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="nuevamente-contenidos-educativos")
    parser.add_argument("--compartment", help="OCID de destino; por defecto, root de tu cuenta.")
    parser.add_argument("--region", help="Home region de la cuenta; detectada si se omite.")
    parser.add_argument("--salida", default=str(Path.home() / ".nuevamente-object-storage"))
    args = parser.parse_args()
    os.umask(0o077)
    try:
        configure(args)
    except (SetupError, ValueError, OSError, configparser.Error) as exc:
        # Nunca volcar tracebacks/configuracion ni stdout/stderr de comandos con claves.
        if isinstance(exc, SetupError):
            log("DETENIDO: " + str(exc))
        else:
            log("DETENIDO: " + type(exc).__name__ + " en " + local_error_location(exc) + ".")
        log("No se declaro exito. Conservar el directorio privado y repetir para retomar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

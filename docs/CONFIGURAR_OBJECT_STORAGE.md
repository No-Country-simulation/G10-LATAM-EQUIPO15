# Configurar Object Storage para NuevaMente

El configurador prepara el almacenamiento obligatorio sin desplegar una VM.
Se ejecuta una vez en Cloud Shell de la cuenta que aloja el bucket. Después,
el paquete privado que genera configura la conexión del backend desde Docker
en Windows.

## Ejecutar en Cloud Shell

1. Abrir Cloud Shell en la cuenta propia, por ejemplo dgomenfran.
2. Usar **Actions → Upload** para subir scripts/configurar-object-storage.py.
3. Ejecutar:

       python3 configurar-object-storage.py

El script detecta usuario, tenancy, namespace y home region. Usa el compartment
root y el bucket nuevamente-contenidos-educativos por defecto.

Hace lo siguiente:

- Reutiliza el bucket existente o crea uno privado Standard, sin auto-tiering,
  versionado ni clave Vault propia.
- Genera una clave de firma RSA y registra **solo la clave pública** en el usuario
  que ejecuta Cloud Shell. Hereda los permisos actuales de ese usuario;
  no concede permisos de administrador ni modifica políticas IAM.
- Comprueba la conexión **con la nueva clave API**, sin aprovechar las
  credenciales temporales de Cloud Shell: sube un original y un JSON diminutos,
  verifica sobrescritura y descarga ambos para comparar exactamente sus bytes.
- Genera un ZIP privado con la clave, configuración OCI, variables para Compose,
  evidencia de la prueba y un instalador PowerShell.

No cambia el Terraform ni crea redes, VM, grupos dinámicos o enlaces públicos.
No elimina objetos ni claves preexistentes. Los dos objetos de comprobación
quedan en comprobacion-oci/<identificador>/ como evidencia.

Al finalizar debe imprimir **OBJECT_STORAGE_VALIDADO** y una ruta semejante a:

    /home/tu-usuario/.nuevamente-object-storage/nuevamente-oci-conexion.zip

Usar **Actions → Download file** con la ruta exacta que devuelve. El ZIP contiene
una clave privada: guardarlo fuera del repositorio y no enviarlo a otra persona.
Las claves API usan los permisos de su usuario, incluidos permisos amplios si
el usuario es administrador.

## Conectar Docker en Windows

Extraer el ZIP descargado en una carpeta privada fuera del repositorio.
Desde PowerShell, ubicado en la copia de NuevaMente con
compose.oci.credentials.yaml, ejecutar el archivo del paquete:

    powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\ruta\del\paquete\conectar-docker.ps1'

El instalador copia la conexión a
%LOCALAPPDATA%\NuevaMente\oci-storage, restringe su acceso al usuario de
Windows y completa automáticamente OCI_CREDENTIALS_DIRECTORY.
No reemplaza una clave diferente ya instalada. El archivo config utiliza
/run/secrets/oci/key.pem, la ruta de la clave dentro del contenedor.

Para configurar e iniciar la aplicación en el mismo paso, con Docker Desktop
funcionando y ia/.env con la clave Gemini:

    powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\ruta\del\paquete\conectar-docker.ps1' -Iniciar

Si se ejecuta desde otra carpeta, agregar -Repositorio 'C:\ruta\del\proyecto'.
ExecutionPolicy Bypass se aplica solo a ese proceso y no modifica la política
de ejecución permanente de Windows.
Solo el backend recibe las credenciales, montadas en modo de lectura.
No se instala OCI CLI en Windows.

La prueba del configurador acredita acceso a Object Storage. **Todavía hay
que generar contenido con Gemini desde el frontend**, confirmar
almacenamiento_oci.status_upload=subido y descargar los objetos de esa
generación. No confundir los archivos de comprobación con entregables de IA.

## Reanudar y errores

Repetir el mismo comando conserva bucket, clave y nombres de comprobación.
No borrar .nuevamente-object-storage mientras se usa esta conexión.
Si una escritura falla o vence su timeout, el script se detiene sin anunciar
éxito; la siguiente ejecución consulta los recursos antes de continuar.

Un error de autorización al listar buckets o guardar objetos significa que
el usuario no tiene esos permisos. El script no los amplía. Debe ejecutarlo
el usuario autorizado de la cuenta del bucket.
Si el usuario ya tiene tres claves API, se detiene sin borrar ninguna.
También se detiene si el bucket existente es público, de otro compartment,
tiene versionado/auto-tiering o usa una clave Vault propia.

El estado de auto-tiering se consulta expresamente con --fields autoTiering.
Sin ese parámetro, GetBucket puede devolver null para el campo, aunque la
función esté desactivada. El configurador solicita el dato tanto con la sesión
Cloud Shell como con la clave exportada; no interpreta null como Disabled.
Ver [GetBucket y campos opcionales](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/bucket/get.html).

Cloud Shell puede ejecutar Python con modo FIPS, que rechaza MD5 por defecto.
El configurador usa MD5 solo para la huella exigida por OCI y el checksum de
los bytes, indicando usedforsecurity=False. Las firmas y la autenticación
siguen a cargo de la clave RSA y OCI CLI. No modifica el modo FIPS.
Si ocurre otro error local, informa la función y línea del script sin
imprimir el mensaje de la excepción, claves ni configuración privada.
Referencias: [hashlib y usos no criptográficos](https://docs.python.org/3/library/hashlib.html),
[formato de la huella OCI](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm).

Object Storage tiene una franquicia Always Free compartida de 20 GB y
50.000 solicitudes API mensuales. El configurador crea dos objetos diminutos;
no establece un límite duro de consumo para las futuras cargas de la aplicación.

## Validación del script sin acceso a OCI

    python -B -m unittest discover -s scripts/tests -p test_object_storage_setup.py -v

Las pruebas controlan respuestas del proveedor, errores de permisos, timeout,
integridad de descargas, reutilización y el aislamiento de la clave API.
No sustituyen la ejecución real en Cloud Shell.

Referencias: [Cloud Shell y obtención de identidad](https://blogs.oracle.com/autonomous-ai-database/discover-oci-native-credential-values-with-ease-using-cloud-shell),
[registro de la clave pública propia](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/iam/user/api-key/upload.html),
[creación de buckets](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/bucket/create.html),
[subida y checksum](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/object/put.html),
[Always Free](https://www.oracle.com/cloud/free/).

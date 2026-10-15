# Integración con OCI Object Storage

Para preparar el bucket y la conexión local automáticamente, usar
[el configurador de Cloud Shell](CONFIGURAR_OBJECT_STORAGE.md).

El Backend incluye persistencia del documento original y del JSON aprobado por
IA. Está **desactivada por defecto**. El 14 de octubre de 2026 se validó desde
Docker local contra el bucket privado de `dgomenfran` en São Paulo: tres
adaptaciones con Gemini, subidas confirmadas y descargas autenticadas idénticas
al original y al JSON canónico. Ver [demostración y evidencia](DEMO_LOCAL_OCI.md).
Las pruebas offline también usan el SDK real y un transporte HTTP controlado.
El acceso desde otra cuenta o una VM requiere su propia comprobación.

## Comportamiento

Con `OCI_STORAGE_ENABLED=false`, la API conserva su flujo de generación actual.
Con `true`, después de validar la respuesta de IA, hace dos operaciones PutObject:

1. Original, con los mismos bytes: `documentos-fuente/YYYY/MM/hash-nombre.ext`.
2. JSON de los seis campos públicos: `artefactos-generados/YYYY/MM/hash-original-hash-contenido.json`.

El hash del documento y del contenido separa resultados diferentes. Dentro del
mismo mes, repetir exactamente el original, nombre y resultado reutiliza las
mismas claves; se realizan igualmente las dos operaciones de subida. Los nombres
se asignan en Backend, eliminando componentes de ruta del nombre del archivo y
sin usar el `objeto_id` propuesto por IA. No se crean buckets ni URLs públicas/PAR.

La respuesta conserva `almacenamiento_oci.objeto_id` para el JSON y añade
`documento_original_objeto_id` para el original, más `documento_original_subido`.

| `status_upload` | Significado |
|---|---|
| `pendiente` / `listo_para_subida` | Intención indicada por IA; no confirma almacenamiento |
| `subido` | OCI confirmó HTTP 200 para ambas operaciones |
| `parcial` | El original está confirmado; la subida del JSON no se confirmó |
| `error` | No se confirmó la subida del original o falló la configuración |

Una falla de almacenamiento **conserva HTTP 200 y el contenido generado**,
con `codigo_error` y un mensaje local dentro de `almacenamiento_oci`. El Frontend
muestra el estado de almacenamiento junto al resultado. Esta política permite
utilizar la adaptación aun ante un fallo cloud; el estado `exito` describe la
generación, no garantiza persistencia. No hay reintento separado de subida ni
cola duradera: conservar el resultado y coordinar recuperación con Cloud.

Las dos operaciones no son una transacción. Un timeout puede ocurrir después
de que OCI haya recibido un objeto; se informa falta de confirmación y no se
borra ningún objeto como compensación. Solo Backend confirma la persistencia;
rechaza una respuesta de IA que pretenda declarar `subido`, `parcial` o `error`.

La subida es síncrona para devolver un estado confirmado. Esto concreta una
variante de la persistencia dual prevista en ADR-002; la ejecución asíncrona
propuesta allí requiere otra API de seguimiento y queda fuera de esta entrega.

## Configuración

| Variable | Valor predeterminado / uso |
|---|---|
| `OCI_STORAGE_ENABLED` | `false`; acepta `true`, `false`, `1`, `0` |
| `OCI_NAMESPACE` | Namespace real; obligatorio al habilitar |
| `OCI_BUCKET_NAME` | `nuevamente-contenidos-educativos`; debe existir |
| `OCI_AUTH_MODE` | `api_key` o `instance_principal` |
| `OCI_REGION` | Override de región; obligatorio con Instance Principal |
| `OCI_CONFIG_FILE` | `/run/secrets/oci/config`, solo API key |
| `OCI_CONFIG_PROFILE` | `DEFAULT`, solo API key |
| `OCI_HTTP_TIMEOUT_SECONDS` | `10`, mayor que 0 y como máximo 30, por lectura |

El SDK usa 5 segundos de conexión y el timeout configurado de lectura. Ambas
operaciones usan `NoneRetryStrategy`: no hay reintentos automáticos. Se envían
Content-Length y Content-MD5 para que OCI pueda verificar la integridad del cuerpo.
Estos timeouts son de conexión/lectura, no un presupuesto global de pared.
`/health` no consulta OCI ni verifica permisos.

### API key desde Docker local

Cuando Cloud habilite el usuario, guardar en una carpeta privada **fuera del
repositorio** el archivo `config` de OCI y la clave `key.pem`. En ese `config`,
`key_file` debe apuntar a `/run/secrets/oci/key.pem`, que es su ruta dentro del
contenedor. Se requieren los valores reales de user, tenancy, fingerprint y region.
No copiar claves al repositorio ni a la imagen.

Guardar las variables OCI en otro archivo privado, por ejemplo `oci.env`:

```dotenv
OCI_STORAGE_ENABLED=true
OCI_NAMESPACE=namespace-del-equipo
OCI_BUCKET_NAME=nuevamente-contenidos-educativos
OCI_AUTH_MODE=api_key
OCI_REGION=region-del-equipo
OCI_CREDENTIALS_DIRECTORY=C:/ruta/privada/oci
```

Desde la raíz, usando también la clave existente de Gemini:

```powershell
docker compose --env-file ia/.env --env-file 'C:\ruta\privada\oci.env' -f compose.integration.yaml -f compose.oci.credentials.yaml up --build -d --wait
```

El override monta la carpeta privada solo en Backend, en modo de lectura; no
crea la carpeta si falta. El SDK recibe su configuración al realizar la subida.
Un archivo ilegible o inválido se comunica como `OCI_NO_CONFIGURADO`, preservando
la adaptación. No mostrar la configuración expandida ni compartir las claves.

### Instance Principal en una VM OCI

Cloud debe configurar el grupo dinámico y su política para el bucket objetivo.
Usar `OCI_AUTH_MODE=instance_principal`, la región, namespace y bucket; ejecutar
el Compose de integración sin el override de credenciales. El SDK obtiene la
identidad de la instancia; no se monta una clave privada de usuario. Esto solo
se puede comprobar dentro de la VM con permisos adecuados, no en el equipo local.

El Backend no crea grupos, políticas, VM, redes ni buckets. La infraestructura
por código es un frente posterior y debe usar los recursos acordados con Cloud.

## Pruebas y cierre

```powershell
docker compose -f compose.tests.yaml run --build --rm backend-tests
docker compose -f compose.frontend.tests.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.frontend.tests.yaml down
```

Las pruebas de Backend usan claves RSA efímeras del fixture, el SDK y las firmas
reales, con un adaptador HTTP controlado y sin red. Comprueban los bytes, checksums,
el JSON guardado idéntico a la respuesta, errores de permisos, fallo parcial,
timeout, ausencia de reintentos, rutas seguras, configuración y regresión de IA.
Las pruebas web usan Backend real, IA simulada y una red interna sin acceso a OCI.

Para cerrar la validación real, con acceso del equipo: generar desde el navegador,
comprobar `subido`, descargar ambos objetos mediante acceso autenticado y comparar
el hash del original y el JSON con la respuesta. Verificar también un fallo
controlado de permisos en un entorno de pruebas. Las pruebas offline no acreditan
que el bucket, la VM o los permisos estén operativos.

Referencias oficiales: [PutObject y SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/object_storage/client/oci.object_storage.ObjectStorageClient.html#oci.object_storage.ObjectStorageClient.put_object),
[archivo de configuración](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm),
[Instance Principal](https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/callingservicesfrominstances.htm).

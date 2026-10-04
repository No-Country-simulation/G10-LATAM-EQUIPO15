# Backend

API REST de adaptación de contenido educativo construida con FastAPI.

> **Estado actual:** el endpoint principal recibe el documento original y llama al servicio HTTP de IA. La persistencia en OCI sigue pendiente; el campo `almacenamiento_oci` de la respuesta describe lo que devuelve IA y no acredita una subida.

## Requisitos

- Docker Desktop, o Docker Engine con Docker Compose v2.

No es necesario instalar Python ni las dependencias del proyecto en la máquina local.

## Ejecutar Backend e IA juntos

Desde la raíz del repositorio:

Con `GOOGLE_API_KEY` cargada en `ia/.env`:

```powershell
docker compose --env-file ia/.env -f compose.integration.yaml up --build -d
Invoke-RestMethod http://localhost:18002/health
```

Swagger de Backend: <http://localhost:18002/docs>. Los servicios comparten una red Docker; Backend se comunica con `http://ia-http:8001`. IA no publica un puerto del host en esta configuración. Solo el contenedor IA recibe las credenciales de Gemini, y su healthcheck debe pasar antes de arrancar Backend.

La configuración utiliza el puerto `18002` por defecto y lo publica en loopback. Puede cambiarse con `BACKEND_PORT` en el entorno o en `ia/.env`.

## Adaptar un documento

`POST /api/v1/adaptar-contenido` utiliza `multipart/form-data`:

| Campo | Valores |
|---|---|
| `documento_original` | Archivo PDF, MD, Markdown o TXT |
| `perfil_destinatario` | `Junior`, `Senior`, `Ejecutivo` |
| `formato_salida` | `Flashcards`, `Quiz Interactivo`, `Mapa Mental`, `Resumen Ejecutivo` |
| `nicho_sector` | `Fintech`, `Salud`, `E-commerce`, `General` |

Los cuatro campos son obligatorios. El contrato JSON anterior del endpoint mock fue reemplazado. Backend valida los parámetros, extensión, archivo vacío y tamaño; entrega los bytes originales a IA sin extraer ni normalizar el texto. IA realiza la validación técnica, extracción, generación y evaluación de calidad.

```powershell
curl.exe -X POST http://localhost:18002/api/v1/adaptar-contenido `
  -F "documento_original=@nuevamente-ai-core/tests/JWT en OCI.pdf" `
  -F "perfil_destinatario=Junior" `
  -F "formato_salida=Flashcards" `
  -F "nicho_sector=General"
```

La solicitud es síncrona y puede consumir cuota y tardar varios minutos. Backend valida que la respuesta corresponda al perfil, formato y nicho solicitados; conserva los campos adicionales, incluidos Mermaid, distractores, reintentos y evidencia cuando IA los devuelve. No calcula metadatos ni modifica el criterio de fidelidad. El éxito es `200`; un rechazo de calidad continúa siendo un rechazo.

| HTTP | Comportamiento |
|---|---|
| `413` / `415` | Documento demasiado grande / extensión no soportada |
| `422` | Parámetros inválidos, archivo vacío o rechazo de ingesta/calidad por IA |
| `500` | Error interno clasificado por IA |
| `502` | Error de proveedor/procesamiento, respuesta inválida o incompatible |
| `503` | IA no disponible, ocupada, no configurada o proveedor sin disponibilidad/cuota |
| `504` | Timeout comunicado por IA o agotamiento del tiempo de espera de Backend |

Los errores usan `{"detail": {"codigo": "...", "mensaje": "..."}}`. Backend conserva el código y estado de los errores conocidos de IA y utiliza mensajes propios; no retransmite cuerpos arbitrarios ni excepciones del servicio. Para errores de ocupación puede conservar `Retry-After`. No hay reintentos automáticos ni respuesta mock de contingencia. Este catálogo implementado todavía debe formalizarse con el equipo.

## Ejecutar solo Backend

```powershell
docker compose -f backend/compose.yaml up --build -d backend
```

Esta configuración conserva el puerto predeterminado `8000`. Para adaptar documentos necesita `IA_BASE_URL` apuntando a un servicio IA alcanzable desde el contenedor; arrancar solo Backend permite consultar salud y Swagger, pero no levanta IA.

### Usar otro puerto

Si el puerto `8000` está ocupado, se puede cambiar mediante `BACKEND_PORT`.

PowerShell:

```powershell
$env:BACKEND_PORT = "18000"
docker compose -f backend/compose.yaml up --build -d
```

Bash:

```bash
BACKEND_PORT=18000 docker compose -f backend/compose.yaml up --build -d
```

En ese caso, el Backend estará disponible en `http://localhost:18000`.

## Endpoints disponibles

| Endpoint | Descripción |
|---|---|
| `GET /` | Confirma que la API está en ejecución. |
| `GET /health` | Informa el estado de salud del contenedor. |
| `GET /docs` | Abre la documentación interactiva de FastAPI. |
| `POST /api/v1/adaptar-contenido` | Envía el documento original al servicio IA y devuelve su respuesta o error. |

## Consultar logs

```bash
docker compose --env-file ia/.env -f compose.integration.yaml logs -f backend
```

## Detener el servicio

```bash
docker compose --env-file ia/.env -f compose.integration.yaml down
```

## Configuración

| Variable | Valor predeterminado | Propósito |
|---|---|---|
| `BACKEND_PORT` | `8000` | Puerto publicado en la máquina local. |
| `IA_BASE_URL` | `http://ia-http:8001` | URL del servicio IA en la red Docker. |
| `IA_HTTP_TIMEOUT_SECONDS` | `600` | Tiempo de espera de lectura/escritura de la llamada a IA. Conexión: 5 segundos. |
| `IA_MAX_DOCUMENT_BYTES` | `10485760` | Límite de documento (10 MiB), aplicado en ambos servicios al usar Compose. |
| `OCI_BUCKET_NAME` | `nuevamente-contenidos-educativos` | Nombre previsto para el bucket de OCI. |

`compose.integration.yaml` usa `18002` para `BACKEND_PORT`; `backend/compose.yaml` usa `8000`. El proceso Backend recibe el límite como `MAX_DOCUMENT_BYTES`. `/health` verifica el proceso HTTP, sin consultar IA ni Gemini. El límite de documento se aplica después del parser multipart; en un despliegue público también corresponde limitar el cuerpo en el proxy.

El timeout de Backend no cancela una generación que ya comenzó en IA. El pipeline sigue siendo síncrono, con un documento por vez, sin SSE ni persistencia OCI. Los índices Chroma se guardan dentro del contenedor IA y se pierden al eliminarlo.

## Pruebas sin consumir cuota

```powershell
docker compose -f backend/compose.yaml --profile tests build backend-tests
docker compose -f backend/compose.yaml --profile tests run --rm backend-tests
```

Las pruebas se ejecutan sin red y sin claves. Verifican el transporte multipart con un servicio HTTP simulado, conservación de bytes y formatos, validación, errores, timeout y respuestas incompatibles. La prueba entre contenedores reales debe distinguirse de estas pruebas locales; una respuesta `422` del pipeline demuestra el recorrido de rechazo, sin acreditar una adaptación exitosa.

Las credenciales y secretos no deben incluirse en la imagen ni versionarse en el repositorio. El diagnóstico interno de IA tampoco forma parte de esta entrega.

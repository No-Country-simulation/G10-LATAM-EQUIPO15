# Data & IA con Docker

Este entorno permite probar AI Core junto con los módulos Data/IA y ejecutar su servicio HTTP. Requiere Docker Desktop o Docker Engine con Compose; no requiere instalar Python en la máquina local.

## Fuentes utilizadas

- AI Core: `dev-ia`, commit `2af23861ea3462ec79fdd2646ab28abed34a3c3e`, en `nuevamente-ai-core/`.
- Data/IA: `feature/ia-02-03-04-ingestion-chunking-vectorstore`, commit `5ee736e43cb8e8fb1369cb29201bb46fbf96c968`. Se incorporaron únicamente los módulos de `ia/src/dataia/`; posteriormente se hicieron configurables el modelo y el manejo estricto de fallos en el enriquecimiento del documento y de los chunks.

El pipeline entrega los fragmentos con la propiedad `contenido`, que utilizan los agentes. El crítico rechaza una fuente sin términos evaluables y puede utilizar el documento de respaldo si los fragmentos están vacíos.

AI Core importa `src.dataia`, pero los módulos Data/IA importan `dataia`. El contenedor copia estos módulos dentro de `nuevamente-ai-core/src/dataia` y habilita ambas rutas mediante `PYTHONPATH`. Esta disposición permite probar la combinación; la estructura definitiva de paquetes sigue pendiente. Ambos nombres pueden cargar módulos distintos, lo que también afecta el alcance de los mocks de la suite.

## Ejecutar las pruebas

Desde la raíz del repositorio:

```powershell
docker compose -f ia/compose.tests.yaml build ia-tests
docker compose -f ia/compose.tests.yaml run --rm ia-tests
```

La construcción necesita acceso a Internet para descargar la imagen y las dependencias. Las pruebas se ejecutan con la red deshabilitada, sin puertos publicados, volúmenes del host ni credenciales reales. Los archivos `.env` no se incorporan a la imagen.

La suite existente utiliza claves ficticias y un mock de embeddings, pero también contiene pruebas del pipeline que intentan utilizar proveedores externos. Por eso una ejecución sin red puede detectar tanto problemas de integración como dependencias externas sin simular. No representa una validación del procesamiento real con Gemini o Groq.

Cada prueba tiene un límite de 30 segundos. Pytest devuelve código `0` si pasan todas, `1` ante fallos y `2` ante errores de colección/importación. El resultado JUnit se genera dentro del contenedor en `/tmp/ia-tests.xml` y se elimina al usar `--rm`; la salida de terminal contiene el diagnóstico.

## Ejecutar solo comprobaciones locales

Para comprobar perfiles, compilación del grafo, validadores de entrada, sanitización de Mermaid, configuración del proveedor de respaldo y las regresiones del manejo de contexto:

```powershell
docker compose -f ia/compose.tests.yaml run --rm ia-tests python -m pytest tests/test_ai_pipeline.py tests/test_critic_context.py -q --tb=short --timeout=30 -k "not ejecucion_pipeline and not fidelidad"
```

Estas pruebas no acreditan generación real, fidelidad del contenido, disponibilidad de proveedores ni almacenamiento en OCI. En particular, la prueba de respaldo verifica la configuración del objeto, sin provocar una caída real de Gemini.

Estas configuraciones ejecutan pruebas e invocaciones directas. El servicio HTTP se levanta con la configuración independiente descrita a continuación.

## Ejecutar el pipeline con Gemini real

Cargar la clave localmente en `ia/.env` como `GOOGLE_API_KEY`. Ese archivo está ignorado por Git y excluido de la imagen. No mostrar la configuración expandida de Compose, ya que contiene la clave.

```powershell
docker compose -f ia/compose.tests.yaml build ia-tests
docker compose --env-file ia/.env -f ia/compose.real.yaml run --rm ia-real
```

Esta ejecución habilita Internet, consume la cuota del proveedor e invoca el pipeline directamente con `tests/JWT en OCI.pdf`, perfil Junior y formato Flashcards. Utiliza `gemini-3.1-flash-lite`, configurable mediante `GEMINI_MODEL` en `ia/.env`, y el modelo de embeddings configurado en Data/IA. No importa la suite de pytest ni sus mocks. El modo `IA_STRICT_PROVIDERS=1` propaga los errores del enriquecimiento y la ejecución rechaza el borrador de contingencia del generador si Gemini no produce una salida válida. El campo de almacenamiento de la respuesta no acredita una subida real a OCI.

## Servicio HTTP de IA

El servicio expone el pipeline existente mediante FastAPI. La entrada sigue la frontera `multipart/form-data` del [contrato Backend ↔ IA v2.2](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO15/blob/main/docs/CONTRATOS/CONTRATO_BACKEND_IA.md) disponible en `main`. El contrato todavía debe incorporarse a las ramas de implementación; la respuesta HTTP conserva el modelo `AdaptacionContenidoResponse` de AI Core, incluido su campo `almacenamiento_oci`. Ese campo no representa una subida a OCI.

Desde la raíz del repositorio, con `GOOGLE_API_KEY` cargada en `ia/.env`:

```powershell
docker compose --env-file ia/.env -f ia/compose.http.yaml up -d --build ia-http
Invoke-RestMethod http://localhost:18001/health
```

Swagger: <http://localhost:18001/docs>. Endpoint: `POST /api/v1/adaptar-contenido`.

| Campo | Tipo / valores |
|---|---|
| `documento_original` | Archivo PDF, MD, Markdown o TXT |
| `perfil_destinatario` | `Junior`, `Senior`, `Ejecutivo` |
| `formato_salida` | `Flashcards`, `Quiz Interactivo`, `Resumen Ejecutivo`, `Mapa Mental` |
| `nicho_sector` | `Fintech`, `Salud`, `E-commerce`, `General` |

Los cuatro campos son obligatorios. El título se deriva del nombre del archivo. Se preservan sus bytes, se guardan en un directorio temporal independiente y se eliminan al finalizar la solicitud, incluso ante un rechazo del pipeline. IA realiza la extracción y la validación de contenido. El adaptador admite las extensiones documentadas; no toma el MIME declarado por el cliente como prueba del formato real.

Ejemplo desde PowerShell, utilizando el PDF del repositorio:

```powershell
curl.exe -X POST http://localhost:18001/api/v1/adaptar-contenido `
  -F "documento_original=@nuevamente-ai-core/tests/JWT en OCI.pdf" `
  -F "perfil_destinatario=Junior" `
  -F "formato_salida=Flashcards" `
  -F "nicho_sector=General"
```

La adaptación consume cuota de Gemini y puede tardar varios minutos. El servicio requiere credenciales y modo estricto: si falla el generador, propaga el error en lugar de devolver un borrador de prueba. No cambia el algoritmo ni el umbral de fidelidad. `/health` comprueba disponibilidad HTTP; no consulta proveedores ni certifica que una adaptación pueda completarse.

El puerto local es `18001`, configurable con `IA_PORT` en `ia/.env`, y se publica solo en loopback. Dentro de Docker el puerto es `8001`. El límite de documento es 10 MiB, configurable mediante `IA_MAX_DOCUMENT_BYTES`; se verifica al recibir el archivo y durante su copia. El parser multipart puede almacenar el cuerpo antes de esa verificación: para un despliegue público también corresponde limitar el cuerpo en el proxy de entrada.

Se procesa un documento por vez por proceso; otras solicitudes de adaptación reciben `503 IA_OCUPADA` y pueden reintentarse. El contenedor arranca un único worker. La solicitud es síncrona, sin trabajos en segundo plano ni SSE. Chroma almacena los índices dentro del contenedor; se pierden al eliminarlo. La configuración de persistencia definitiva queda pendiente.

### Respuestas del adaptador

El éxito devuelve `200` con la respuesta tipada del pipeline. Los errores tienen esta forma:

```json
{"detail": {"codigo": "CONTEXTO_INSUFICIENTE", "mensaje": "IA rechazó el contenido por no alcanzar su criterio de fidelidad."}}
```

| HTTP | Situación |
|---|---|
| `413` | Documento mayor al límite configurado |
| `415` | Extensión fuera de PDF, Markdown y TXT |
| `422` | Parámetros inválidos, archivo vacío, rechazo de ingesta o rechazo por calidad |
| `500` | Error interno no clasificado |
| `502` | Fallo de proveedor, segmentación/indexación o respuesta incompatible con el esquema |
| `503` | IA ocupada, credenciales/modo estricto faltantes, proveedor no disponible o cuota agotada |
| `504` | El proveedor comunica un timeout |

Este mapeo es el comportamiento del adaptador; el catálogo definitivo de errores debe alinearse con Backend. El pipeline actual convierte algunos fallos de segmentación/indexación en mensajes genéricos, por lo que esos casos se devuelven como `502` aunque su causa original pueda ser una cuota agotada. No se devuelven excepciones crudas, claves ni rutas internas. No hay un timeout global que cancele el pipeline.

### Pruebas HTTP sin consumir cuota

```powershell
docker compose --env-file ia/.env -f ia/compose.http.yaml --profile tests build ia-http-tests
docker compose --env-file ia/.env -f ia/compose.http.yaml --profile tests run --rm ia-http-tests
```

El contenedor de pruebas no recibe las credenciales y ejecuta sin red. La configuración Compose requiere `--env-file ia/.env` porque contiene también el servicio real, pero la clave solo se inyecta en `ia-http`. Las pruebas HTTP sustituyen la llamada al pipeline para verificar el transporte, validación, limpieza de archivos, ocupación, respuestas y errores; otras pruebas verifican la delegación al pipeline y que el generador respete el modo estricto. También se ejecutan las nueve comprobaciones locales anteriores.

```powershell
docker compose --env-file ia/.env -f ia/compose.http.yaml down
```

Este servicio habilita la invocación HTTP de IA. Para levantarlo junto con Backend, usar desde la raíz `docker compose --env-file ia/.env -f compose.integration.yaml up --build -d`. Backend queda en <http://localhost:18002/docs> y llama a IA por la red interna de Docker; esa configuración no publica un puerto adicional para IA. Ver el [README de Backend](../backend/README.md). La persistencia OCI y la aprobación de fidelidad siguen pendientes.

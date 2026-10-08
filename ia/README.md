# Data & IA con Docker

Para ejecutar la suite completa de Backend, Data/IA y AI Core y reproducir la
integración HTTP con Gemini y persistencia, ver [tests/README.md](../tests/README.md).

Este entorno permite probar AI Core junto con los módulos Data/IA y ejecutar su servicio HTTP. Requiere Docker Desktop o Docker Engine con Compose; no requiere instalar Python en la máquina local.

## Fuentes utilizadas

- AI Core: `dev-ia`, commit `d895a1a87424c76699c99b72ee5267126decbef5`, en `nuevamente-ai-core/`. Incluye el juez LLM para fidelidad, recuperación de hasta 15 chunks y la respuesta pública de tres campos.
- Data/IA: base `5ee736e43cb8e8fb1369cb29201bb46fbf96c968` y mejoras Fase A de `feat/dataia-fase-a`, commit `0ebbd155438781e4afcd9b10746c45a8a95835d4`. Se combinan extracción estructural, clasificación por lotes y persistencia con los límites y el manejo estricto de errores del proveedor.

El pipeline entrega los fragmentos con la propiedad `contenido`, que utilizan los agentes. El crítico conserva el juez LLM de IA, rechaza localmente una fuente vacía sin invocar al proveedor y puede utilizar el documento de respaldo si los fragmentos están vacíos.

### Ingestión, chunking y vector store

La versión anterior de estos módulos corresponde al commit `12ee492`. El detalle de los cambios y sus mediciones está en [docs/18_MEJORAS_DATA_IA_FASE_A.md](../docs/18_MEJORAS_DATA_IA_FASE_A.md).

- **Extracción:** los PDF se convierten a Markdown por página con `pymupdf4llm` (títulos, listas y código), ignorando imágenes y gráficos para no perder el texto superpuesto a ellos; las tablas dibujadas con líneas quedan como texto. Si `pymupdf4llm` falla o una página conserva menos del 90 % de las palabras del texto plano, esa página se extrae con PyMuPDF. Los enlaces se reducen a su texto y se eliminan los encabezados y pies repetidos en la mayoría de las páginas. La normalización conserva la indentación y el interior de los bloques de código.
- **Identidad:** `document_id` es `doc-` + los primeros 16 caracteres hexadecimales del SHA-256 del archivo. El mismo archivo produce el mismo id; `ingest_document(ruta, document_name=...)` conserva el nombre original.
- **Chunking:** se segmenta el documento completo, no página por página. Cada chunk registra `page` (inicio), `page_end` (fin) y `section` (título vigente, sin confundir comentarios `#` de código con títulos).
- **Enriquecimiento:** los chunks se clasifican en lotes de `DATAIA_ENRICH_BATCH_SIZE` (15 por defecto) y la caché se indexa por el hash del texto en `DATAIA_CACHE_DIR`.
- **Vector store:** el `chunk_id` es el id del vector. Si el documento ya está indexado con los mismos fragmentos no se recalculan embeddings; si cambió, se reemplazan sus vectores. La metadata pedagógica del documento se guarda en `DATAIA_DOCUMENTS_DIR/<document_id>.json`. `get_document_chunks(document_id)` devuelve todos los chunks en orden y `load_document_record(document_id)` su registro.
- **Persistencia:** Compose HTTP e integración montan el volumen `ia-data` en `/workspace/data` (ChromaDB, registro y cachés). Sobrevive a la recreación del contenedor; `docker compose down -v` elimina también el volumen. Cada proyecto Compose tiene su propio volumen. Esto no implementa Object Storage de OCI.

AI Core y Data/IA utilizan una sola ruta de importación, `dataia.*`. Las imágenes copian el paquete en `/workspace/ia/src/dataia` y lo incluyen en `PYTHONPATH`; no crean una segunda copia bajo `src.dataia`. Los proveedores simulados de las pruebas tienen alcance por prueba.

## Ejecutar las pruebas sin Docker

Con el Python de Anaconda se crea un entorno virtual en la raíz del repositorio (`.venv/`, ignorado por Git) con las mismas dependencias de la imagen:

```powershell
C:\ProgramData\anaconda3\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install -r nuevamente-ai-core/requirements.txt -r ia/requirements-tests.txt -r ia/requirements-http.txt
```

Pruebas de Data/IA (sin red ni proveedores):

```powershell
$env:PYTHONPATH = "ia/src"
.venv\Scripts\python.exe -m pytest ia/tests/test_dataia.py -q
```

Para llamar a Gemini desde esta máquina, Python debe usar el almacén de certificados de Windows: instalar `truststore` en `.venv` y ejecutar `truststore.inject_into_ssl()` antes de crear los clientes. Sin eso, las llamadas fallan con `CERTIFICATE_VERIFY_FAILED`.

Para ejecutar la suite combinada fuera de Docker, usar `PYTHONPATH=ia/src;nuevamente-ai-core` en PowerShell. No se requiere copiar los módulos a otra carpeta.

## Ejecutar las pruebas con Docker

Desde la raíz del repositorio:

```powershell
docker compose -f ia/compose.tests.yaml build ia-tests
docker compose -f ia/compose.tests.yaml run --rm ia-tests
```

La construcción necesita acceso a Internet para descargar la imagen y las dependencias. Las pruebas se ejecutan con la red deshabilitada, sin puertos publicados, volúmenes del host ni credenciales reales. Los archivos `.env` no se incorporan a la imagen.

Las pruebas del pipeline ejecutan ingesta, Chroma y LangGraph con embeddings, generación y juez explícitamente simulados. Los mocks se restauran al finalizar cada prueba. La ejecución sin red verifica la integración local y no representa una validación del procesamiento real con Gemini o Groq.

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

Opcionalmente, `DATAIA_GOOGLE_API_KEY` define una clave propia para ingestión, chunking y embeddings, de modo que esas etapas consuman una cuota separada de la que usa AI Core en la generación. Si no está definida, también usan `GOOGLE_API_KEY`. Ninguna clave se versiona: cada persona configura las suyas en `ia/.env`.

```dotenv
GOOGLE_API_KEY=clave-para-ai-core
DATAIA_GOOGLE_API_KEY=clave-para-data-ia   # opcional
```

```powershell
docker compose -f ia/compose.tests.yaml build ia-tests
docker compose --env-file ia/.env -f ia/compose.real.yaml run --rm ia-real
```

Esta ejecución habilita Internet, consume la cuota del proveedor e invoca el pipeline directamente con `tests/JWT en OCI.pdf`, perfil Junior y formato Flashcards. Utiliza `gemini-3.5-flash-lite`, configurable mediante `GEMINI_MODEL` en `ia/.env`, y el modelo de embeddings configurado en Data/IA. No importa la suite de pytest ni sus mocks. El modo `IA_STRICT_PROVIDERS=1` propaga los errores del enriquecimiento y la ejecución rechaza el borrador de contingencia del generador si Gemini no produce una salida válida. La respuesta actual no incluye información de almacenamiento; la persistencia en OCI sigue pendiente.

## Servicio HTTP de IA

El servicio expone el pipeline existente mediante FastAPI. La entrada sigue la frontera `multipart/form-data` del [contrato Backend ↔ IA v2.2](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO15/blob/main/docs/CONTRATOS/CONTRATO_BACKEND_IA.md) disponible en `main`. El contrato todavía debe incorporarse a las ramas de implementación; la respuesta HTTP conserva el modelo actual `AdaptacionContenidoResponse` de AI Core: `status`, `metadatos` y `contenido_adaptado`. Los scores de calidad se evalúan internamente y la persistencia en OCI sigue pendiente.

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

Se procesa un documento por vez; otras solicitudes de adaptación reciben `503 IA_OCUPADA` y pueden reintentarse. El contenedor arranca un único worker HTTP. Cada adaptación se ejecuta en un proceso hijo supervisado: al agotar el presupuesto total, IA termina ese proceso, libera la ocupación y elimina el archivo temporal antes de responder. La solicitud sigue siendo síncrona, sin trabajos persistentes en segundo plano ni SSE. Chroma, registros y cachés se conservan en el volumen Docker descrito anteriormente; Object Storage y la persistencia definitiva en OCI siguen pendientes.

### Límites de ejecución

| Variable | Predeterminado | Uso |
|---|---|---|
| `IA_PROVIDER_TIMEOUT_SECONDS` | `60` | Timeout de una solicitud al proveedor, para generación, enriquecimiento y embeddings |
| `IA_PROVIDER_MAX_RETRIES` | `1` | Hasta un reintento adicional; admite valores de 0 a 2 |
| `IA_PIPELINE_TIMEOUT_SECONDS` | `480` | Presupuesto total de la adaptación HTTP, incluyendo el arranque del proceso hijo |
| `IA_CALLER_TIMEOUT_SECONDS` | `600` | Tiempo disponible en el cliente; Compose de integración lo toma de `IA_HTTP_TIMEOUT_SECONDS` |

Los tiempos deben ser positivos y finitos. El presupuesto de IA debe ser al menos cinco segundos menor que el del cliente; se recomienda conservar un margen mayor para transporte y cierre del proceso. Una configuración inválida devuelve `503 IA_NO_CONFIGURADA` antes de comenzar a procesar. Los valores se pueden cargar en `ia/.env`; Compose transmite estas opciones sin incorporar ese archivo a la imagen.

`DATAIA_GOOGLE_API_KEY` es opcional: Data/IA usa esa clave si se configura y, de lo contrario, `GOOGLE_API_KEY`. AI Core mantiene sus credenciales. Ambas rutas conservan los límites HTTP del proveedor. Compose también transmite `DATAIA_ENRICH_BATCH_SIZE`, con valor predeterminado `15`. Los lotes y los reintentos individuales registran su etapa sin imprimir el contenido de los fragmentos.

Se fijan `langchain-google-genai==4.4.0` y `google-genai==2.28.0`, versiones con las que se verifica que los límites llegan a las solicitudes del SDK. En esa versión de LangChain, `max_retries` se transforma en intentos totales; la configuración anterior expresa reintentos adicionales y hace la conversión. Embeddings utiliza un cliente SDK con opciones HTTP explícitas porque la versión instalada no aplica su campo `request_options` a `embed_content`.

Los logs registran etapas, duración, tipo de excepción y código original de Google, incluyendo `429` y `503`. El adaptador mantiene su catálogo público de errores. En modo estricto, un fallo del crítico se propaga como fallo del proveedor, sin convertirlo en una puntuación artificial de baja fidelidad. Los mensajes de excepciones, prompts, claves y rutas de documentos no se registran por este manejo de errores. El timeout global detiene el trabajo local pendiente; no revierte solicitudes que ya fueron enviadas a Google.

Para Gemini 3, la fábrica conserva la temperatura predeterminada del modelo, conforme a la [recomendación de Google](https://ai.google.dev/gemini-api/docs/gemini-3#temperature). Gemini 2 mantiene la temperatura solicitada por cada módulo. Este ajuste no modifica los umbrales ni los criterios del crítico.

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
| `504` | Timeout del proveedor o agotamiento del presupuesto total de IA |

Este mapeo es el comportamiento del adaptador; el catálogo definitivo de errores debe alinearse con Backend. En modo estricto, los fallos reconocidos del proveedor conservan su causa durante segmentación e indexación para clasificarlos correctamente. Otros fallos de procesamiento devuelven `502`. No se devuelven excepciones crudas, claves ni rutas internas.

### Pruebas HTTP sin consumir cuota

```powershell
docker compose --env-file ia/.env -f ia/compose.http.yaml --profile tests build ia-http-tests
docker compose --env-file ia/.env -f ia/compose.http.yaml --profile tests run --rm ia-http-tests
```

El contenedor de pruebas no recibe las credenciales y ejecuta sin red. La configuración Compose requiere `--env-file ia/.env` porque contiene también el servicio real, pero la clave solo se inyecta en `ia-http`. Las pruebas HTTP sustituyen la llamada al pipeline para verificar el transporte, validación, limpieza de archivos, ocupación, respuestas y errores; otras pruebas verifican la delegación al pipeline y que el generador respete el modo estricto. También se ejecutan las comprobaciones locales del grafo y las regresiones del contexto del crítico, usando un juez simulado para no consumir cuota.

```powershell
docker compose --env-file ia/.env -f ia/compose.http.yaml down
```

Este servicio habilita la invocación HTTP de IA. Para levantarlo junto con Backend, usar desde la raíz `docker compose --env-file ia/.env -f compose.integration.yaml up --build -d`. Backend queda en <http://localhost:18002/docs> y llama a IA por la red interna de Docker; esa configuración no publica un puerto adicional para IA. Ver el [README de Backend](../backend/README.md). La persistencia OCI y la aprobación de fidelidad siguen pendientes.

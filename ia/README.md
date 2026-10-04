# Pruebas de Data & IA con Docker

Este entorno permite diagnosticar la suite existente de AI Core junto con los módulos Data/IA. Requiere Docker Desktop o Docker Engine con Compose; no requiere instalar Python en la máquina local.

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

Este entorno es de pruebas; todavía no define cómo el Backend invocará IA ni ofrece una API HTTP.

## Ejecutar el pipeline con Gemini real

Cargar la clave localmente en `ia/.env` como `GOOGLE_API_KEY`. Ese archivo está ignorado por Git y excluido de la imagen. No mostrar la configuración expandida de Compose, ya que contiene la clave.

```powershell
docker compose -f ia/compose.tests.yaml build ia-tests
docker compose --env-file ia/.env -f ia/compose.real.yaml run --rm ia-real
```

Esta ejecución habilita Internet, consume la cuota del proveedor e invoca el pipeline directamente con `tests/JWT en OCI.pdf`, perfil Junior y formato Flashcards. Utiliza `gemini-3.1-flash-lite`, configurable mediante `GEMINI_MODEL` en `ia/.env`, y el modelo de embeddings configurado en Data/IA. No importa la suite de pytest ni sus mocks. El modo `IA_STRICT_PROVIDERS=1` propaga los errores del enriquecimiento y la ejecución rechaza el borrador de contingencia del generador si Gemini no produce una salida válida. El campo de almacenamiento de la respuesta no acredita una subida real a OCI.

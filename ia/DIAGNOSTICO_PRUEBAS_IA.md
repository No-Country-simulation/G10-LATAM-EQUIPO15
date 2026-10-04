# Diagnóstico de las pruebas de IA

Verificación local realizada el 3 de octubre de 2026 en `feat/ia-docker-tests`.

## Resultado

El entorno Docker se construyó correctamente y pytest pudo ejecutar las diez pruebas existentes. La suite completa terminó con **7 aprobadas y 3 fallidas**, código de salida `1`, en **103,29 segundos**. Las tres fallidas alcanzaron el límite de 30 segundos durante una llamada a Gemini que la suite no simula.

La ejecución separada de las comprobaciones locales terminó con **6 aprobadas y 4 excluidas**, código de salida `0`, en **3,85 segundos**.

Estos resultados corresponden a una ejecución sin red ni credenciales reales. No prueban la generación real con proveedores externos ni permiten concluir que las etapas posteriores al enriquecimiento funcionen.

## Entorno y procedencia

- AI Core: `origin/dev-ia`, commit `2af23861ea3462ec79fdd2646ab28abed34a3c3e`.
- Data/IA: commit `5ee736e43cb8e8fb1369cb29201bb46fbf96c968` de `feature/ia-02-03-04-ingestion-chunking-vectorstore`.
- En la ejecución inicial se verificó que los diez archivos incorporados en `ia/src/dataia/` tienen los mismos hashes Git que en su rama de origen. En esa ejecución AI Core y sus pruebas conservaron los fuentes de `dev-ia` sin modificaciones.
- Python `3.14.8`; pytest `9.1.1`; pytest-asyncio `1.4.0`.
- LangGraph `1.2.12`; LangChain `1.4.3`; langchain-google-genai `4.4.0`; ChromaDB `1.5.9`; Pydantic `2.13.5`.
- Imagen local: `sha256:4606027c7c4572c156cd8e61ea99f179b694ab041c1ccdd5005b9f766005b12f`, aproximadamente 729 MB decimales, usuario `testuser`.
- Base de esta construcción: `python:3.14-slim`, digest `sha256:0741d101873c12ab927e6f8653feb8862b9bd58771177acb1b885b95141f91b4`.
- `pip check`: `No broken requirements found.`

La configuración declara versiones mínimas y una etiqueta de imagen base; futuras reconstrucciones pueden resolver versiones diferentes. Los valores anteriores describen el entorno verificado, sin constituir un archivo de bloqueo de dependencias.

## Pruebas ejecutadas

| Prueba | Resultado | Qué acredita en esta ejecución |
|---|---|---|
| Perfiles canónicos | Aprobada | Existen Junior, Senior y Ejecutivo en el esquema. |
| Compilación del grafo LangGraph | Aprobada | El grafo se puede construir. |
| Pipeline Junior / Flashcards | Fallida por timeout | Se intentó invocar Gemini durante el enriquecimiento; no llegó a verificar la salida. |
| Pipeline asíncrono Senior / Quiz | Fallida por timeout | Mismo bloqueo antes de generación y telemetría final. |
| Pipeline Ejecutivo / Mapa Mental | Fallida por timeout | Mismo bloqueo antes de generación. |
| Rechazo de XSS | Aprobada | El validador rechaza el ejemplo de entrada de la prueba. |
| Rechazo de prompt injection | Aprobada | El validador rechaza el ejemplo de entrada de la prueba. |
| Sanitización local de Mermaid | Aprobada | Los ejemplos de limpieza y reconstrucción producen los resultados esperados. |
| Configuración de respaldo a Groq | Aprobada | El objeto de configuración tiene respaldo; no se comprobó una conmutación real. |
| Rechazo de contexto irrelevante | Aprobada | La receta se rechaza en la validación técnica de ingestión, antes del agente crítico. |

Se observaron dos advertencias de deprecación en dependencias de ChromaDB y Google GenAI. No impidieron las pruebas locales.

## Causa observada de los tres fallos

Las tres trazas llegan a:

```text
pipeline.py -> ingest_document(...)
ingestion/service.py -> enrich_document_metadata(...)
ingestion/enrichment.py -> structured_llm.invoke(prompt)
Google GenAI -> reintentos de la llamada externa
Failed: Timeout (>30.0s) from pytest-timeout.
```

El mock global de la suite cubre `src.dataia.vectorstore.client.GoogleGenerativeAIEmbeddings`, pero no `ChatGoogleGenerativeAI` del enriquecimiento. Las claves ficticias permiten construir el cliente y la llamada se intenta de todos modos. La red deshabilitada impide que llegue al proveedor.

Por lo tanto, el fallo observado es una dependencia externa sin aislar en estas pruebas. No demuestra por sí solo un defecto en la respuesta de Gemini ni en las etapas del pipeline que no se alcanzaron.

## Aspectos detectados en los fuentes

1. **Rutas de importación diferentes.** AI Core usa `src.dataia`; los módulos Data/IA usan `dataia`. El contenedor admite ambas rutas para diagnosticar la combinación. Se verificó en el contenedor que `src.dataia.vectorstore.client` y `dataia.vectorstore.client` son objetos distintos: compararlos con `is` devuelve `False`. Es necesario acordar un único paquete para que los imports y los mocks se apliquen de forma consistente.
2. **Evaluación especial para pruebas.** El agente crítico devuelve directamente un score de `0.95` cuando encuentra `GEMINI_API_KEY=dummy_gemini_key`, salvo para títulos con `Receta`. Aprobar una prueba con esa condición no acredita fidelidad real del contenido.
3. **Ejecución directa desactualizada.** El bloque `if __name__ == "__main__"` llama a `test_extractor_texto_plano` y `test_chunker_segmentacion_jerarquica`, que no están definidas en el archivo, y anuncia `12/12`. Pytest descubre diez pruebas y evita ese bloque. Se utilizó pytest para esta verificación.

Los tres puntos anteriores se identificaron por revisión de los fuentes y la diferencia entre los objetos importados también se comprobó en el contenedor. El score del agente crítico y el bloque de ejecución directa no fueron ejecutados en esta verificación.

## Siguiente paso

Preparar el aislamiento completo de proveedores para las pruebas sin red: enriquecimiento del documento, enriquecimiento de chunks, embeddings y generación. Primero debe unificarse la ruta de los módulos para que cada mock cubra la llamada correspondiente. Las pruebas deben seguir comprobando contratos, trazabilidad y errores, sin utilizar el score fijo como evidencia de fidelidad.

Después de comprobar el pipeline aislado, ejecutar una prueba real con un documento y credenciales del proveedor configuradas solo para esa ejecución. Recién con esos resultados se podrá definir y verificar la integración con Backend.

Los comandos de construcción y ejecución están en [README.md](README.md).

## Prueba real con Gemini

Después del diagnóstico inicial, el usuario cargó su clave local en `ia/.env` y autorizó probar el documento completo. La clave no se mostró, no se incorporó a la imagen y permanece ignorada por Git. Se ejecutó el pipeline directamente, sin importar los mocks de pytest.

### Fallos encontrados y correcciones locales

1. La primera ejecución avanzó hasta el grafo y produjo `UnboundLocalError` en el agente crítico. El pipeline generaba fragmentos con la propiedad `texto`, pero los agentes consultaban `contenido`. Al unir varios fragmentos vacíos quedaban separadores que impedían utilizar el documento de respaldo. La rama sin términos evaluables asignaba un score de `0.95` y dejaba `observaciones` sin definir.
2. Se corrigieron las rutas síncrona y asíncrona para enviar `contenido`. El crítico elimina separadores vacíos, utiliza el documento de respaldo cuando corresponde y devuelve score `0.0` con una observación de contexto insuficiente cuando no puede evaluar la fuente.
3. Se incorporaron tres pruebas de regresión del contexto vacío, del contexto aportado por fragmentos y del documento de respaldo. Junto con las seis comprobaciones locales anteriores, el resultado fue **9 aprobadas y 4 excluidas**; la última ejecución tardó **3,90 segundos**. Esto no equivale a aprobar las cuatro pruebas de pipeline excluidas.
4. Se deshabilitó el borrador de contingencia del generador para esta ejecución real. Así se pudo observar el error del proveedor que antes quedaba oculto: `gemini-2.5-flash` respondió `404 NOT_FOUND`, indicando que no está disponible para nuevos usuarios.
5. Se consultó la lista de modelos mediante la API con la clave del usuario. `gemini-3.8-flash` fue listado y recomendado en el error, pero durante el procesamiento de los fragmentos respondió `503 UNAVAILABLE` por alta demanda.
6. Se hizo configurable `GEMINI_MODEL` en el enriquecimiento del documento y de los chunks. El modo `IA_STRICT_PROVIDERS=1`, habilitado únicamente en la ejecución real, propaga sus errores en lugar de devolver metadatos de contingencia.
7. Una consulta mínima con `gemini-3.1-flash-lite` respondió `OK`. Se utilizó ese modelo para la siguiente ejecución del PDF completo; queda como valor predeterminado de la configuración local real.

### Resultado observado con el modelo disponible

La ejecución con **Gemini 3.1 Flash Lite** y **Gemini Embedding 001** completó la ingestión con enriquecimiento, el chunking con enriquecimiento, la indexación vectorial, la recuperación de contexto y la generación real de Flashcards para perfil Junior. El modo estricto permaneció activo y no se utilizó el borrador de contingencia.

El pipeline se detuvo al verificar el resultado del grafo:

```text
ValueError: Contexto Insuficiente (Error 422):
El documento carece de información relevante (Score: 0.78 vs Umbral 0.85).
```

El proceso terminó con código `1`. No se devolvió una respuesta final exitosa, no se llegó a la auditoría posterior y no se realizó ninguna subida a OCI. El umbral de `0.85` se mantuvo.

El mensaje menciona un error 422, pero esta prueba invoca una función Python y no un endpoint HTTP; no se verificó una respuesta HTTP 422.

El evaluador utiliza una heurística de coincidencia de palabras entre fuente y borrador, no una evaluación semántica con Gemini. El score observado no demuestra por sí solo que el PDF carezca de información técnica ni que las tarjetas sean incorrectas. Las tarjetas no quedaron exportadas: el contenedor se eliminó al finalizar y la excepción ocurrió antes de imprimir la respuesta.

### Evidencia local

Los registros permanecen en el directorio temporal de Windows:

- `codex-ia-gemini-real-20261003.log`: fallo original del crítico.
- `codex-ia-gemini-real-corregido-20261003.log`: error 404 del modelo antiguo, sin permitir el borrador de contingencia.
- `codex-ia-gemini-real-modelo-disponible-20261003.log`: error 503 de Gemini 3.8 Flash.
- `codex-ia-gemini-real-flash-lite-20261003.log`: rechazo por score `0.78` ante umbral `0.85`.

La imagen posterior a las correcciones es `sha256:766dfa8d7beb482b57022a4f07b14367987b6ea1091a1aec76bc8de3dbce2100`, con las mismas versiones de dependencias del diagnóstico inicial.

### Próxima comprobación

Capturar el borrador y los fragmentos antes del rechazo, compararlos con el PDF y revisar el criterio de fidelidad. Hasta completar esa comparación, no corresponde bajar el umbral ni afirmar que el pipeline ya funciona de extremo a extremo. Toda esta preparación, sus correcciones y los registros siguen locales, sin commits ni push.

## Captura y revisión posteriores

Se instrumentó únicamente la ejecución local para conservar los estados del grafo antes del rechazo. Una nueva ejecución con Gemini 3.1 Flash Lite capturó ocho páginas, cinco fragmentos recuperados y dos borradores: cinco tarjetas con score `0.79` y seis con score `0.80`. El proceso volvió a rechazar el resultado frente al umbral `0.85`, que no se modificó.

El cálculo original se reprodujo exactamente sobre los borradores capturados. En el segundo intento contó 111 coincidencias sobre 285 palabras. Excluyendo claves y delimitadores del diccionario, y normalizando puntuación en fuente y salida, las mismas tarjetas obtienen 136 coincidencias sobre 243 palabras; aplicar la fórmula existente a ese control produce `0.89`. Este control sirve para detectar distorsión del cálculo y no acredita fidelidad semántica ni aprueba las tarjetas.

La revisión encontró contenido técnico respaldado por la fuente y también aspectos que requieren corrección. La tarjeta sobre políticas de fallo generaliza funciones que corresponden a configuraciones específicas y añade una garantía absoluta de privacidad. El contexto recuperado no incluyó las páginas 3 y 4, donde el PDF explica los tipos de política y sus condiciones. También deben precisarse las analogías sobre firma de JWT y OAuth.

La evidencia, las tarjetas originales y la revisión detallada se guardaron fuera del repositorio en `C:/Users/59598/AppData/Local/Temp/codex-ia-evidence-20261003-250f383f/`. El contenedor utilizado se retiró después de copiar y validar la evidencia.

El siguiente trabajo debe corregir el cálculo y revisar el respaldo de afirmaciones y la cobertura del contexto. No basta con normalizar el texto para obtener un score que supere el umbral. El evaluador todavía no recibió esas modificaciones.

# Propuesta de cambios para AI Core y Backend tras la Fase A de Data/IA

**Para:** responsables de `nuevamente-ai-core/` y de `backend/`.
**Estado:** propuesta para revisar. Ningún archivo de `nuevamente-ai-core/` ni de `backend/` fue modificado.
**Contexto:** [18_MEJORAS_DATA_IA_FASE_A.md](18_MEJORAS_DATA_IA_FASE_A.md).

---

## 1. Qué cambia para cada equipo con la Fase A

### Backend: no requiere cambios

El contrato HTTP Backend ↔ IA no cambió: las mismas rutas, campos y errores.

### Archivos compartidos modificados fuera de `ia/`

| Archivo | Cambio | Efecto |
|---|---|---|
| `compose.integration.yaml` | Volumen `ia-data` en `/workspace/data` del servicio `ia-http`. Variable opcional `DATAIA_GOOGLE_API_KEY`. | ChromaDB, el registro de documentos y las cachés sobreviven a los reinicios. Un documento ya procesado no vuelve a consumir cuota. |
| `.gitignore` | Ignora `.chromadb_data/`, `.dataia_documents/`, `.dataia_cache/` e `ia_old/`. | Evita versionar datos generados localmente. |
| `docs/README.md` | Índice con los documentos 18 y 19. | — |

### Credenciales

- `GOOGLE_API_KEY` sigue siendo la clave de AI Core (generación con LangGraph).
- `DATAIA_GOOGLE_API_KEY` (opcional) es una clave propia para ingestión, chunking y embeddings. Si no se define, Data/IA usa `GOOGLE_API_KEY` como antes.
- Ninguna clave se versiona. Cada persona configura las suyas en `ia/.env`, que Git ignora y que queda fuera de la imagen.

### AI Core: funciona sin cambios

Los contratos de Data/IA solo agregaron campos opcionales. `ejecutar_pipeline_adaptacion` sigue funcionando igual. Las propuestas de las secciones 2 y 3 son mejoras, no correcciones obligatorias.

## 2. Problema observado

Ejecución real con Gemini: "JWT en OCI.pdf", perfil Junior, formato Flashcards, `IA_STRICT_PROVIDERS=1`.

| Versión de Data/IA | Resultado |
|---|---|
| Anterior (2 ejecuciones) | 422 "Contexto Insuficiente", score 0,78 y 0,79 (umbral 0,85) |
| Fase A | 422 "Contexto Insuficiente", score 0,78 |

El documento es pertinente, pero el pipeline no entrega contenido. El resultado es igual con las dos versiones de Data/IA, por lo que la causa está en la etapa de generación y evaluación.

## 3. Propuesta B: selección del contexto (`pipeline.py`)

### Situación actual

```python
# nuevamente-ai-core/src/ai/pipeline.py (versión síncrona y asíncrona)
docs_relevantes = vectorstore.similarity_search(query=query_pedagogica, k=5, filter={"document_id": ...})
```

- `similarity_search(k=5)` es un patrón de preguntas y respuestas: devuelve los 5 fragmentos más parecidos a una consulta genérica armada con el título y el formato. Para generar flashcards, un quiz o un resumen se necesita cubrir el documento completo, no 5 fragmentos.
- La `pedagogical_metadata` (conceptos clave, prerrequisitos, resumen) y la metadata por chunk (`tipo_contenido`, `nivel_dificultad`, `section`) no llegan a los agentes.
- `analizador.py` obtiene los `conceptos_clave` de la respuesta tomando palabras de más de 4 letras que empiezan con mayúscula.

### Cambio propuesto

Data/IA ya expone dos funciones de lectura:

```python
from dataia.vectorstore.client import get_document_chunks, load_document_record

chunks = get_document_chunks(vs_res.document_id)      # todos, en orden del documento, con metadata
registro = load_document_record(vs_res.document_id)   # pedagogical_metadata, secciones, etc.
```

Selección según el formato, dentro de un presupuesto de tokens:

| Formato | Chunks a priorizar |
|---|---|
| Flashcards | `tipo_contenido == "definicion"`, luego cobertura por `section` |
| Quiz Interactivo | `afirmacion` y `procedimiento` |
| Guía Paso a Paso | `procedimiento` y `codigo`, en orden del documento |
| Resumen Ejecutivo / Mapa Mental | al menos un chunk por `section`; si el documento entra en el contexto del modelo, el documento completo |

Archivos afectados:

| Archivo | Cambio |
|---|---|
| `nuevamente-ai-core/src/ai/pipeline.py` | Reemplazar `similarity_search` por la selección anterior, en las dos versiones (síncrona y asíncrona). Agregar al estado inicial `conceptos_clave`, `prerequisitos` y `resumen_ejecutivo` del registro. |
| `nuevamente-ai-core/src/ai/agents/analizador.py` | Usar los `conceptos_clave` recibidos en el estado; dejar la heurística de mayúsculas solo como respaldo. |
| `ia/src/ia_http/main.py` o `runner.py` (Data/IA) | Pasar el nombre original del archivo (`ingest_document(ruta, document_name=...)`). Hoy se registra el nombre temporal `documento.pdf`. |

## 4. Propuesta C: el agente crítico

### Situación actual (`agents/critico.py`)

- El score mide **coincidencia léxica**: qué proporción de las palabras de más de 4 letras del borrador aparece en la fuente. No verifica si las afirmaciones son correctas.
- Penaliza lo que piden los propios prompts: las analogías del perfil Junior, los ejemplos del nicho (`creador.py`: *"Adapta todos los ejemplos… al contexto de {nicho}"*) y las claves del JSON (`pista_didactica`, `categoria_dificultad`), porque evalúa `str(items)`.
- Es binario: si la proporción es menor que 0,5, el score queda en 0,82 o menos y se rechaza; si es mayor o igual, queda en 0,86 o más.
- En el reintento envía al generador `list(set(...))[:5]`: 5 palabras arbitrarias de la fuente, como "términos clave no reflejados". El LLM tiende a forzarlas en el contenido.
- Al aprobar, escribe *"No se detectaron alucinaciones"*, algo que la métrica no verifica.
- El prompt Senior (`prompts/perfiles.py`) pide *"máxima coincidencia léxica con la fuente"*: optimiza la métrica, no la calidad.

### Cambio propuesto

1. El generador indica en cada ítem los `chunk_id` que lo respaldan. Basta un campo opcional `fuentes: list[str]` en el esquema del ítem.
2. El crítico verifica cada ítem con un LLM juez, a temperatura 0, contra el texto de esos chunks: respaldado, parcialmente respaldado o no respaldado. Las analogías y los ejemplos de nicho se evalúan como recursos didácticos, no como afirmaciones de la fuente.
3. El score es la proporción de ítems respaldados. La retroalimentación al generador es concreta: *"La tarjeta 3 afirma X; no está en doc-…-chk-0012"*.
4. Se quita la instrucción de "máxima coincidencia léxica" del perfil Senior.

| Archivo | Cambio |
|---|---|
| `nuevamente-ai-core/src/ai/agents/critico.py` | Verificación por ítem con LLM juez; nueva retroalimentación. |
| `nuevamente-ai-core/src/ai/agents/creador.py` | Pedir `fuentes` por ítem; enviar los fragmentos con su `chunk_id`. |
| `nuevamente-ai-core/src/ai/schemas.py` | Campo opcional `fuentes` en los ítems. |
| `nuevamente-ai-core/src/ai/prompts/perfiles.py` | Ajustar la directriz 5 del perfil Senior. |

## 5. Detalle técnico pendiente: dos nombres para el mismo módulo

AI Core importa `src.dataia.*`, mientras que Data/IA se importa internamente como `dataia.*`. El Dockerfile copia el paquete dentro de `nuevamente-ai-core/src/` para que funcionen las dos rutas, pero Python carga **dos módulos distintos** con el mismo código. Consecuencia concreta: el mock de `test_ai_pipeline.py` parchea `src.dataia.vectorstore.client.GoogleGenerativeAIEmbeddings`, mientras el servicio usa `dataia.vectorstore.client`. Por eso las pruebas de extremo a extremo llaman a Gemini real.

Propuesta: que AI Core importe `dataia.*` (ya está en el `PYTHONPATH` de las imágenes) y que los mocks apunten a `dataia.vectorstore.client`.

## 6. Cómo seguir

Si les parecen bien, implementamos B y C en una rama aparte (por ejemplo `feat/ai-core-contexto-critico`) con su propio PR, para que lo revise quien mantiene AI Core. También pueden tomarlas ustedes; con gusto ayudamos con pruebas y mediciones.

Para validar, cualquiera de las dos propuestas se puede medir con la misma ejecución real descrita en el documento 18, §7.

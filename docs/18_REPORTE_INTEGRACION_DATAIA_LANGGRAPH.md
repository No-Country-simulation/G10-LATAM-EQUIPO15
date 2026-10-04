# REPORTE OFICIAL: Integración del Pipeline DataIA y Motor Multi-Agente (LangGraph)

**Fecha de Integración:** 02 de Octubre de 2026  
**Squad:** IA & Datos (Colaboración cruzada Fernando/Data y Marcos/IA)  
**Estado:** Integración Finalizada, Validada y Optimizada para OCI.

---

## 1. Contexto de la Integración

El objetivo crítico de esta fase fue fusionar el trabajo aislado del procesamiento de documentos (Pipeline `dataia` de Fernando) con el cerebro de Inteligencia Artificial (Motor LangGraph). Antes de esta integración, el motor de IA dependía de módulos *legacy* que extraían el texto de forma plana sin persistencia vectorial real.

Se procedió a importar la rama remota `feature/ia-02-03-04-ingestion-chunking-vectorstore` e inyectarla directamente como el núcleo de procesamiento de datos en el archivo orquestador `src/ai/pipeline.py`.

## 2. Arquitectura Resultante (End-to-End)

El flujo ahora es 100% ininterrumpido. Cuando un usuario sube un PDF, el sistema ejecuta de forma asíncrona la siguiente cadena:

1.  **Ingestión (DataIA):** Se invoca `ingest_document(ruta_archivo)`. PyMuPDF extrae el texto, limpia caracteres extraños y emite un veredicto de calidad documental.
2.  **Segmentación Jerárquica (DataIA):** `process_chunks()` toma el texto y lo divide en ventanas lógicas de 800 caracteres con 150 de solapamiento para no romper el contexto pedagógico.
3.  **Persistencia Vectorial (DataIA):** `process_vectorstore()` convierte los chunks en Embeddings usando la API oficial de Google (`models/gemini-embedding-001`) y los guarda en una base de datos local **ChromaDB**.
4.  **Generación y Auditoría (LangGraph):** El motor recupera los fragmentos más relevantes desde ChromaDB y dispara la máquina de estados de 5 nodos:
    *   *Analizador:* Entiende la intención (Flashcards, Quiz, etc.).
    *   *Creador:* Genera el contenido basado estrictamente en el contexto (RAG).
    *   *Crítico (Hermes):* Evalúa la fidelidad fáctica. Si el PDF era una receta de cocina y se pidió un manual de OCI, levanta un **HTTP 422**.
    *   *Ensamblador:* Empaqueta todo en Pydantic V2.

## 3. Optimización Extrema de Payloads (Preparación OCI)

Para garantizar que el Backend consuma la menor cantidad de memoria y ancho de banda al servir los JSON al Frontend (requisito clave en la capa gratuita de OCI), se realizó una purga masiva del esquema de salida.

*   **Se eliminó `AlmacenamientoOCI`:** Responsabilidad trasladada enteramente al Backend.
*   **Se eliminó `EvaluacionCalidad`:** Se borraron scores de auditoría interna y reintentos del payload final público.
*   **Limpieza de Código:** Se eliminó por completo la carpeta `src/legacy/` que contenía extractores obsoletos.

**Resultado:** El JSON entregado por la IA es ahora ultra-ligero, conteniendo únicamente: `status`, `metadatos` (para UI) y `contenido_adaptado`.

## 4. Validación de Resultados (Test Suite)

Se rediseñó la batería de pruebas en `tests/test_ai_pipeline.py` para utilizar archivos temporales reales (`tempfile`) simulando el paso por ChromaDB.

*   **Éxito Total (10/10 Pruebas Pasadas):** El motor superó satisfactoriamente las pruebas de estrés.
*   **Anti-Alucinaciones Confirmado:** Se probó inyectar una "Receta de Tarta" solicitando un Quiz de Tecnología. El Agente Crítico bloqueó la ejecución correctamente arrojando el error `422 Contexto Insuficiente`.
*   **Failover Dinámico:** Se validó la conmutación de caída. Si Gemini se satura (HTTP 429), la generación hace *fallback* inmediato hacia **Groq (Llama 3.3)** sin que el usuario lo note.
*   **Resolución de Bloqueos:** Se solucionaron bloqueos de concurrencia en SQLite (ChromaDB) limpiando el caché local `.chromadb_data/` entre sesiones de pruebas.

## 5. Resolución de Puntos Pendientes del Contrato (MVP v2.1)

Durante esta integración, se tomaron decisiones arquitectónicas clave que **cierran oficialmente** los puntos pendientes del documento `contratos.md`:

*   **Punto 13 / 15 (Evidencia de Grounding y Evaluación de Calidad):** Se cierra con la decisión de **excluir** los scores del JSON final. La validación de fidelidad ocurre internamente. Si falla, el motor devuelve un error 422; si pasa, el Backend puede confiar en que el contenido es fidedigno. Esto ahorra peso en el payload.
*   **Punto 16 (Persistencia OCI):** Se cierra con la **Alternativa C (Responsabilidad Separada)**. IA solo entrega el JSON puro en memoria, y Backend asume la responsabilidad exclusiva de comunicarse con los buckets de OCI (Storage) y persistir los archivos generados.
*   **Punto 24 (codigo_respuesta):** Se decidió eliminarlo del body JSON, delegando el manejo de códigos HTTP enteramente al framework FastAPI del Backend, evitando duplicación de estado.

## 6. Siguientes Pasos (Handoff a Backend)

El motor local ha quedado encapsulado de forma limpia. El próximo y último paso de integración es que el equipo Backend importe la función `ejecutar_pipeline_adaptacion_async` en el router de FastAPI (`src/api/router.py`), reemplace los mocks estáticos actuales, e implemente el validador de tamaño máximo (10MB) en el `UploadFile`.

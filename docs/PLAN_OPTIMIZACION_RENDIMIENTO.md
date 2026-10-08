# 🚀 Plan de Optimización de Rendimiento (AI Core)

**Fase Actual:** MVP - Semana 1
**Objetivo:** Reducir la latencia de "Cold Start" (Arranque en frío) y maximizar el rendimiento bajo concurrencia extrema.

---

## 🛑 Diagnóstico Actual (Baseline)
Según el perfilado con `--durations=0` del 25 de septiembre:
- **Cold Start (Arranque en frío):** ~20.33 segundos. Causado por la carga inicial de los modelos de Embeddings (Sentence-Transformers) en memoria y la indexación inicial de ChromaDB.
- **Warm Start (Caché caliente):** ~2.90 a ~3.01 segundos. Desempeño excelente.
- **Gastos de Orquestación:** 0.05 segundos para compilar LangGraph (Despreciable).

---

## 🛠️ Plan de Optimización a Corto Plazo (Semana 2)

### 1. Mitigación del Cold Start (VectorStore)
*   **Problema:** En el primer request, la carga de los pesos de los embeddings en RAM toma entre 10 y 15 segundos.
*   **Solución:** Mover la inicialización de `VectorStoreService` al ciclo de vida de arranque del servidor (Lifespan events en FastAPI).
*   **Acción Requerida:** Backend debe instanciar la conexión a ChromaDB en el evento `@asynccontextmanager def lifespan(app: FastAPI):` de FastAPI antes de abrir el puerto, pre-calentando la memoria.

### 2. Caché de Respuestas (Semantic Caching)
*   **Problema:** Las peticiones idénticas gastan tokens repetitivos.
*   **Solución:** Implementar `langchain.cache`.
*   **Acción Requerida:** Utilizar un caché semántico en memoria (o Redis en el futuro) para que si el usuario vuelve a pedir "Flashcards de VCN", la respuesta sea de <0.1s desde el caché.

### 3. Conmutación Activa de Agentes (Llamadas Paralelas)
*   **Problema:** Los agentes están orquestados de forma secuencial rígida en `graph.py`.
*   **Solución:** Evaluar qué ramas de generación se pueden ejecutar en paralelo usando `add_conditional_edges` y nodos paralelos de LangGraph.
*   **Acción Requerida:** El Agente Crítico puede ir evaluando el borrador mientras el Ensamblador prepara los metadatos (ahorro de 0.5s por request).

---

## 📈 Plan de Escalabilidad a Mediano Plazo (Nube OCI)
1. **Desacople de Embeddings:** Usar una API externa de embeddings (ej. Google/Groq) en lugar de un modelo Sentence-Transformers local. Esto quita la carga pesada de CPU de nuestro micro-servidor Always Free de Oracle.
2. **Workers Asíncronos (Celery):** Si las peticiones tardan más de 10s sostenidamente, mover la ejecución a una cola de tareas como Celery/RabbitMQ, mientras FastAPI solo devuelve un `task_id` al frontend.

---

*Nota: Este documento será actualizado continuamente. Cada modificación arquitectónica ejecutada debe ser registrada también en el Changelog del archivo `01_DOCUMENTACION_TECNICA_SEMANA_1_MARCOS.md`.*

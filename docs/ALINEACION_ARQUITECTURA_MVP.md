# 🏛️ Documento Maestro: Alineación de Arquitectura MVP (Data & IA)

**Proyecto:** NuevaMente  
**Squad:** IA / Data (Marcos H., Andy M., Fernando F.)  
**Fecha de Resolución:** 26 de Septiembre de 2026  
**Estado:** **APROBADO Y ALINEADO**  

Este documento sintetiza la arquitectura definitiva acordada por el equipo de IA tras integrar los requerimientos técnicos del diseño original (LangGraph) con el rigor pedagógico exigido por las especificaciones del Hackathon (Observaciones F1-F5).

---

## 1. Arquitectura Central (Motor Multi-Agente)
Se ratifica el uso de **LangGraph** como orquestador de agentes autónomos asíncronos en lugar de un flujo RAG lineal simple. 
*   **Justificación:** Permite implementar un ciclo de auditoría interna (LLM-as-a-judge) y reintentos automáticos sin sobrecargar la API de Backend, asegurando salidas 100% validadas contra esquemas Pydantic.
*   **Componentes:** Extractor → Analizador → Creador → Crítico → Ensamblador.

## 2. Decisiones Arquitectónicas y Ajustes Pedagógicos

### 2.1 Query Builder (Resolución de Búsqueda Semántica)
*   **Cambio:** El RAG ya no buscará en ChromaDB por simple similitud vectorial usando texto genérico.
*   **Ajuste:** Se incorpora un paso de traducción donde el parámetro `formato_salida` dicta los términos de búsqueda (Ej: Flashcards buscará vectores asociados a "definiciones", TL;DR buscará "ejecutivo, resumen").
*   **Justificación:** Evita inyectar contexto "basura" al LLM, enfocando la atención del modelo estrictamente en el propósito pedagógico.

### 2.2 Completitud de Metadatos (Contrato JSON)
*   **Cambio:** El JSON final debe devolver obligatoriamente `tiempo_estimado_estudio_minutos` y `conceptos_clave`.
*   **Ajuste (Implementado):** 
    *   En `ensamblador.py`, se programó el cálculo matemático de tiempo basado en la cantidad de items generados (Ej: 3 min por flashcard, 5 min por pregunta de quiz). 
    *   En `analizador.py`, se extraen los conceptos clave del índice documental.
*   **Justificación:** Bloqueo crítico superado. Sin esto, el Backend no cumpliría con el esquema final requerido por los jueces del Hackathon.

### 2.3 Aplicación Estricta de Nicho/Sector
*   **Cambio:** El parámetro `nicho_sector` deja de ser pasivo.
*   **Ajuste (Implementado):** Se modificó el System Prompt en `creador.py` con una instrucción crítica: *"Adapta todos los ejemplos, analogías y la introducción estrictamente al contexto de {nicho_sector}"*.
*   **Justificación:** Aterriza el conocimiento técnico genérico (ej. "Microservicios") a la realidad del usuario final (ej. "Sector Salud: hospitales y clínicas"), un diferencial inmenso para el producto final.

### 2.4 Grounding Explicable (Score de Anclaje)
*   **Cambio:** El `anclaje_fuente_score` deja de ser un número aleatorio generado por el LLM.
*   **Ajuste:** El Agente Crítico operará bajo el patrón *LLM-as-a-judge*, obligado a justificar su calificación citando fragmentos exactos del documento fuente. Si detecta alucinaciones (<0.85 de score), el sistema reinicia el nodo de generación.
*   **Justificación:** Mitigación absoluta de alucinaciones. Aseguramos la fiabilidad técnica del contenido.

### 2.5 Ingesta y Vectorización Básica (Sin sobreingeniería)
*   **Decisión:** Se descarta el uso de *GraphRAG* para el MVP de la Semana 2.
*   **Justificación:** Desplegaremos en la capa Always Free de OCI (Micro-servidor ARM). Mantendremos un chunking de 500 tokens con ChromaDB para garantizar un tiempo de respuesta rápido (~3 segundos por solicitud en *Warm Start*). El *SemanticSplitter* queda en el backlog para post-MVP.

---

## 3. Estado de la Integración (Handover a Backend)
El motor de IA está técnicamente completo. Backend (Diego M.) puede proceder con la creación de los endpoints FastAPI y WebSockets basándose en el documento de contratos ya establecido.

> *Nota: Todos estos acuerdos han sido ya impactados a nivel código en los archivos del core (`ensamblador.py` y `creador.py`) de la rama principal.*

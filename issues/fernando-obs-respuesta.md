# Respuesta a Informe #1 - NuevaMente Data & IA Pipeline

> **A:** Fernando F. (DataIA Squad)  
> **De:** Marcos H. (Tech Lead)  
> **Fecha:** 26 de Septiembre de 2026  
> **Asunto:** Resolución y acuerdos sobre observaciones del RAG Pedagógico  

Fernando, excelente análisis. Tus observaciones arquitectónicas son precisas y apuntan exactamente a las brechas que teníamos entre la implementación inicial del Hackathon y los requerimientos del jurado (JSON final). Tienes todo el "go" para que implementemos estos ajustes. A continuación, el detalle de cómo abordaremos cada punto desde el liderazgo de IA:

---

## 1. Query Builder Pedagógico (F1 - Aprobado)
*   **Tu observación:** El sistema no recibe una "pregunta", recibe un documento y parámetros. Buscar por similitud plana trae contexto genérico.
*   **Resolución:** Totalmente de acuerdo. Implementaremos el **Query Builder**. Antes de ir a ChromaDB, crearemos un paso intermedio (puede ser determinista por velocidad) que traduzca el `formato` a vectores de búsqueda. Si piden "Flashcards", el Query Builder buscará `["definiciones", "conceptos clave", "terminología"]`. Si piden "Guion", buscará `["ejemplos", "secuencia", "fundamentos"]`.

## 2. Inclusión de Metadata Pedagógica (F2 - Aprobado)
*   **Tu observación:** Faltan `conceptos_clave` y `tiempo_estimado_estudio_minutos` en el pipeline.
*   **Resolución:** Es un bloqueo crítico porque rompe el contrato JSON. 
    *   **Tiempo Estimado:** Lo calcularemos matemáticamente en el `ensamblador.py` (ej. 3 min por flashcard, 5 min por pregunta de quiz). 
    *   **Conceptos Clave:** Serán extraídos por el `analizador.py` en la fase de asimilación y pasados directamente al bloque de `metadatos`.

## 3. Uso del parámetro `nicho_sector` (F3 - Aprobado)
*   **Tu observación:** El nicho_sector se recibe pero se desperdicia en la generación.
*   **Resolución:** Se inyectará una regla estricta en el Prompt del Agente Creador: *"Adapta los ejemplos, analogías y la introducción estrictamente al contexto de {nicho_sector}"*. Así garantizamos que un mapa mental de "Microservicios" se explique con metáforas de hospitales si el nicho es Salud.

## 4. Score de Anclaje como Caja Negra (F4 - Aprobado)
*   **Tu observación:** El score del Agente Crítico debe ser explicable, determinista y auditable (LLM-as-a-judge).
*   **Resolución:** Refactorizaremos el `critico.py`. Ahora estará obligado (vía Pydantic) a devolver un JSON con una `justificacion_score` que cite los fragmentos exactos del documento original que respaldan (o desmienten) el contenido generado.

## 5. Ingesta y Chunking (F5 - Acuerdo a Mediano Plazo)
*   **Tu observación:** El particionado debe ser semántico (Parent-Child) y generar metadatos desde la ingesta.
*   **Resolución:** Es la estrategia correcta para producción. Sin embargo, para no romper el MVP (Hito Semana 2), mantendremos el chunking base actual (800/150) asegurando que los manuales oficiales de prueba no superen los límites semánticos. Una vez validada la integración E2E, habilitamos el `SemanticSplitter`.

---

**Siguientes pasos inmediatos:**
Yo me encargo hoy mismo de parchar el cálculo de tiempos (F2) y la inyección del nicho (F3) en los agentes. Queda en tu cancha subir los manuales de JWT y Microservicios crudos a `data/raw/` para poder correr los tests.

¡Gran trabajo asegurando la calidad del Pipeline!

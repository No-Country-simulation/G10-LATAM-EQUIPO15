# ADR-001: Selección de LangGraph sobre Cadenas Monolíticas para Orquestación de Agentes
**Estado:** Aprobado  
**Fecha:** 2026-09-17  
**Autores:** Marcos Gael (AI Engineer) & Squad de IA  
**Alcance:** Arquitectura de Orquestación y Mitigación de Alucinaciones  

---

## 1. Contexto y Problema
La solución requiere transformar manuales técnicos complejos en contenidos educativos diferenciados (Flashcards, Quizzes, Mapas Mentales, Tutoriales y TL;DR) según perfiles de usuario. 

Las implementaciones convencionales basadas en cadenas secuenciales de prompts simples (*prompts monolíticos* o cadenas lineales de LangChain):
1. No permiten bifurcaciones condicionales dinámicas según el formato requerido.
2. Carecen de mecanismos autónomos de verificación de fidelidad técnica, lo que incrementa el riesgo de alucinaciones conceptuales inadmisibles en educación técnica.
3. Si un modelo genera información inexacta, la cadena secuencial falla silenciosamente o propaga el error al usuario final.

---

## 2. Decisión Arquitectónica
Se adopta **LangGraph** (StateGraph) como el motor central de orquestación multi-agente, modelando el flujo de trabajo como una **Máquina de Estados Finitos con Capacidad de Auto-Reflexión y Corrección**.

El grafo implementa los siguientes nodos diferenciados:
1. `RouterNode`: Enrutador que selecciona la estrategia de contextualización y plantilla de prompt según la tupla `(perfil, formato)`.
2. `RetrieverNode`: Recuperador vectorial que extrae los $k=5$ fragmentos de mayor relevancia semántica ($\ge 0.75$).
3. `PedagogicalDraftingNode`: Redactor instruccional que genera la versión adaptada con técnicas *Few-Shot*.
4. `QualityEvaluatorCriticNode`: Agente supervisor que analiza la salida contra los fragmentos de contexto y computa el `anclaje_fuente_score`.
5. `OutputFormattingNode`: Formateador que asegura conformidad estricta con Pydantic V2.

### Bucle de Auto-Corrección y Límite de Convergencia:
* Si `anclaje_fuente_score < 0.85`: El flujo se redirige al redactor con el reporte de discrepancias para reescribir la sección afectada.
* **Garantía de Terminación:** Se fija un límite estricto de máximo 2 reintentos ($\text{iteraciones} \le 2$). Si tras el segundo intento no se alcanza el umbral, se emite el contenido marcando las observaciones en los metadatos de calidad, garantizando respuesta en tiempo acotado ($O(1)$) y previniendo bucles infinitos o consumo excesivo de tokens.

---

## 3. Consecuencias y Trade-offs

### Consecuencias Positivas:
* **Fidelidad Demostrable:** Permite certificar ante el jurado del Hackathon un score matemático de anclaje fáctico ($\ge 0.85$).
* **Modularidad Extensible:** Cada nuevo formato pedagógico (como los Mapas Mentales en Mermaid) se añade como una rama del grafo sin alterar los nodos existentes.
* **Trazabilidad:** Cada estado y transición del grafo puede registrarse para emitir telemetría hacia la interfaz de usuario.

### Consecuencias Negativas / Mitigaciones:
* **Mayor Complejidad que una Cadena Simple:** Mitigado centralizando el código del grafo en `src/ai/agents/graph.py` con pruebas unitarias aisladas en `tests/ai/`.
* **Latencia Adicional en Reintentos:** Mitigado fijando el límite de 2 iteraciones y manteniendo prompts concisos con temperature $\le 0.3$.

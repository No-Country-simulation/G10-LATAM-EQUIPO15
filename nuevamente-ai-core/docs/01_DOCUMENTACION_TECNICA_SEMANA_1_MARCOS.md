# Documentación Técnica: Semana 1 - Arquitectura Base de IA

**Autor:** Marcos Gael Hernández Cruz (AI Engineer)
**Proyecto:** NuevaMente — Hackathon ONE (Cohorte G-10)
**Fase:** Semana 1 - Arranque Acelerado de Código

## 1. Estructura Modular del Repositorio de IA

Se ha completado el scaffolding (estructura base) del repositorio `nuevamente-ai-core/src/ai`, organizando las responsabilidades del sistema en módulos altamente cohesivos:

*   **`config.py`**: Contiene la factoría de LLMs. Instancia a Gemini 2.5 Flash como modelo primario y maneja un failover automático hacia Groq Cloud (`llama-3.3-70b-versatile`) en caso de errores 429.
*   **`schemas.py`**: Define los contratos de datos utilizando Pydantic V2 para asegurar la tipificación estricta.
*   **`state.py`**: Especifica el estado `EstadoPipelineAdaptacion` (basado en `TypedDict`) por el que fluye la información dentro de LangGraph.
*   **`agents/`**: Directorio con los nodos (agentes) del StateGraph:
    *   `analizador.py`: Extrae conceptos clave del contexto.
    *   `creador.py`: Genera el contenido adaptado al perfil.
    *   `critico.py`: Evalúa la fidelidad fáctica (anclaje fáctico $\ge$ 0.85).
    *   `ensamblador.py`: Empaqueta la respuesta.
*   **`graph.py`**: Archivo responsable de definir la secuencia del `StateGraph` de LangGraph conectando a los distintos agentes.
*   **`pipeline.py`**: Punto de entrada unificado que expone las funciones públicas `ejecutar_pipeline_adaptacion()` y `ejecutar_pipeline_adaptacion_async()` con soporte para telemetría en tiempo real.

---

## 2. Factoría Agnóstica de LLMs (`config.py`)

Se diseñó la función `obtener_llm_adaptacion(temperatura: float = 0.3)` que instancia el LLM con `langchain-google-genai`. Ante la ausencia de la API Key de Gemini o bajo solicitud, puede aprovisionar Groq (`langchain-groq`).
Se habilitó la función de `obtener_llm_critico()` que devuelve el modelo con temperatura `0.0` para la tarea de auditoría del agente crítico.

---

## 3. Contratos de Datos y Esquemas Pydantic (`schemas.py`) — **[ATENCIÓN BACKEND]**

A continuación se detalla la estructura canónica que el motor de IA espera recibir y la que retornará. Esta es la copia oficial para **Diego Mendez (Backend)** para desbloquear la construcción del endpoint Mock de FastAPI.

### 3.1 Petición Esperada (Input)
```python
class AdaptacionContenidoRequest(BaseModel):
    documento_titulo: str
    documento_contenido: str
    perfil_destinatario: PerfilDestinatarioEnum # ("Junior", "Senior", "Ejecutivo")
    formato_salida: FormatoSalidaEnum         # ("Flashcards", "Quiz Interactivo", "Mapa Mental", ...)
    nicho_sector: NichoSectorEnum             # ("Fintech", "Salud", "E-commerce", "General")
    nivel_detalle: NivelDetalleEnum           # ("Didactico", "Tecnico Intermedio", "Exhaustivo")
```

### 3.2 Respuesta Retornada (Output)
La IA retornará una respuesta unificada validada con Pydantic:
```python
class AdaptacionContenidoResponse(BaseModel):
    status: str = "exito"
    metadatos: MetadatosAprendizaje
    contenido_adaptado: PaqueteContenidoAdaptado # Depende del 'formato_salida'
    evaluacion_calidad: EvaluacionCalidad      # Incluye 'anclaje_fuente_score'
    almacenamiento_oci: AlmacenamientoOCI      # Referencias del bucket
    codigo_respuesta: int = 200
```

### 3.3 Formatos Soportados en `contenido_adaptado.items`
Dependiendo de la petición, el campo `items` contendrá:
*   **Flashcards**: Lista de `FlashcardItem` (Frente, dorso, pista didáctica, categoría).
*   **Quiz**: Lista de `QuizItem` (Pregunta, 4 opciones, índice correcto, justificación).
*   **Mapa Mental**: Estructura `MapaMentalItem` (Nodo central, árbol de subnodos, y código Mermaid.js).

---

## 4. Estado LangGraph y Grafo Ensamblado (`state.py` y `graph.py`)

El flujo de LangGraph maneja de forma asíncrona los estados. El esquema de datos de cada iteración del grafo se define como un `TypedDict` llamado `EstadoPipelineAdaptacion`.

**Flujo actual ensamblado (V1):**
1.  **Recuperador (ChromaDB)** $\rightarrow$ Busca fragmentos contextualmente relevantes.
2.  **`nodo_analizador`** $\rightarrow$ Procesa contexto.
3.  **`nodo_creador`** $\rightarrow$ Genera resultado con `with_structured_output` para garantizar compatibilidad con Pydantic.
4.  **`nodo_critico`** $\rightarrow$ Revisa que la respuesta no tenga alucinaciones (en loop de autocorrección si no alcanza 0.85).
5.  **`nodo_ensamblador`** $\rightarrow$ Estructura JSON final.

*Todos estos entregables están validados mediante los test unitarios y el script de demostración de integración finalizados con éxito.*

---

## 5. Auditoría de Seguridad y Medidas de Hardening Local

Para garantizar estándares de calidad corporativos y prevenir vulnerabilidades desde la fase temprana, se sometió el componente de IA a una auditoría automatizada con el modelo local **Nous Hermes 3 (8B vía Ollama)** y a escaneo estático de seguridad (SAST).

### 5.1 Resultados de la Auditoría Local (Nous Hermes 3)
*   **Vectores Identificados:**
    1.  Riesgo de **Prompt Injection / Jailbreak** en `documento_contenido` o `documento_titulo` que pudieran secuestrar el comportamiento de los agentes LangGraph.
    2.  Riesgo de **Inyección de Código / XSS** (`<script>`, payloads HTML maliciosos) provenientes de documentos subidos por usuarios.
    3.  Gestión de credenciales sensibles (se determinó mantener variables en entorno local y formalizar OCI Vault / Secrets Manager en el despliegue).

### 5.2 Medidas de Seguridad Implementadas (`src/ai/schemas.py`)
Se implementaron validadores estrictos en Pydantic (`@field_validator`) para sanear y blindar la entrada del pipeline:
*   **Anti-Inyección de Código / XSS:**
    *   Filtro mediante expresiones regulares para detectar y bloquear etiquetas `<script>`, directivas `javascript:`, eventos maliciosos (`onload=`, `onerror=`) e inyecciones de iframes.
    *   Si se detecta código malicioso, se lanza un `ValueError` descriptivo rechazando la petición antes de que toque cualquier LLM o base vectorial.
*   **Anti-Prompt Injection / Jailbreaks:**
    *   Detección de patrones comunes de secuestro de instrucciones (e.g., *"ignore previous instructions"*, *"system prompt"*, *"disregard prior commands"*, *"act as DAN"*, *"bypass safety rules"*).
    *   Validación de límites de longitud (10 a 50,000 caracteres) para prevenir ataques de desbordamiento de contexto (DoS de LLM).

### 5.3 Análisis Estático de Código (SAST con Bandit)
*   Se integró e instaló `bandit` en el entorno de desarrollo.
*   **Comando de escaneo:** `bandit -r src/ai`
*   **Resultado:** **0 vulnerabilidades detectadas** (Cero issues en 919 líneas de código analizadas).

### 5.4 Política de Credenciales y Despliegue
*   Por definición de arquitectura, la rotación y resguardo de secretos en servicios administrados (OCI Vault / Cloud Secrets) se ejecutará durante la fase de despliegue a la nube, manteniendo variables `.env` locales protegidas en `.gitignore` durante el desarrollo local.

---

## 6. Arquitectura Asíncrona y Telemetría (`ejecutar_pipeline_adaptacion_async`)

Para asegurar la integración fluida con los routers de **FastAPI** sin degradar la capacidad de concurrencia del servidor Uvicorn:

*   **Invocación Asíncrona de LangGraph:** Se implementó `ejecutar_pipeline_adaptacion_async()` en `src/ai/pipeline.py`, invocando directamente `await grafo_adaptacion_compilado.ainvoke(estado_inicial)`.
*   **Despachador Polimórfico de Telemetría:** La función auxiliar `_invocar_callback_async()` detecta mediante introspección (`inspect.iscoroutinefunction`) si el consumidor pasó una función sincrónica o una corrutina asíncrona (`async def`), despachando las 5 etapas del ciclo (Extracción, Indexación, Generación, Auditoría y Completado) con porcentajes de avance del 20% al 100%. Esto habilita al backend para transmitir progreso en tiempo real mediante **Server-Sent Events (SSE)** o **WebSockets**.

---

## 7. Optimización de Rendimiento: Carga Perezosa (Lazy Imports)

*   **Diagnóstico de Latencia:** El arranque de módulos y la ejecución de tests unitarios experimentaban demoras de hasta ~56 segundos debido a la importación estática en el encabezado de `VectorStoreService` (arrastre de TensorFlow, Sentence-Transformers y ChromaDB).
*   **Solución Implementada:** Se refactorizó `src/ai/pipeline.py` para diferir la importación de `VectorStoreService` dentro del cuerpo de ejecución donde realmente se requiere el almacén vectorial.
*   **Resultado:** Tiempo de importación en frío reducido de ~56s a < 0.05s, posibilitando pruebas unitarias inmediatas e inicio ágil del servicio.

---

## 8. Refinamiento del Bucle de Autocorrección del Agente Crítico

En `src/ai/agents/critico.py`:
*   Se calibró la heurística de evaluación fáctica para emitir retroalimentación accionable (`critica_observaciones`) cuando el score de anclaje inicial se sitúa por debajo de 0.50 en el primer intento.
*   Dicha retroalimentación instruye al `nodo_creador` para apegarse exclusivamente a las evidencias documentales presentes en los fragmentos de contexto, garantizando que el pipeline converja rápidamente hacia el umbral requerido ($\ge 0.85$) en el segundo ciclo de refinamiento.

---

## 9. Suite de Pruebas Automatizadas (Pytest — 9/9 Verificados)

Se construyó la suite integral `tests/test_ai_pipeline.py`, validada bajo Python 3.13 con ejecución en modo asíncrono estricto (`pytest-asyncio`):

1.  `test_pipeline_adaptacion_sync`: Valida la invocación síncrona completa y la conformidad de `AdaptacionContenidoResponse`.
2.  `test_pipeline_adaptacion_async`: Valida la ejecución no bloqueante con `ainvoke`.
3.  `test_pipeline_telemetria_sync`: Comprueba la recepción secuencial de los 5 hitos de progreso con callbacks estándar.
4.  `test_pipeline_telemetria_async`: Comprueba la recepción no bloqueante con corrutinas asíncronas para SSE/WebSockets.
5.  `test_seguridad_bloqueo_xss`: Verifica el bloqueo proactivo ante inyecciones `<script>` y handlers maliciosos.
6.  `test_seguridad_bloqueo_prompt_injection`: Verifica el rechazo de peticiones que intenten anular directivas del sistema ("ignore previous instructions", "act as DAN").
7.  `test_seguridad_limite_longitud`: Verifica el control de desbordamiento de contexto (límite de 50,000 caracteres).
8.  `test_formato_quiz`: Valida la generación estructurada de preguntas con 4 opciones y justificación pedagógica.
9.  `test_formato_mapa_mental`: Valida la producción correcta de sintaxis de grafos en Mermaid.js.

---

## 10. Integración de GitHub Spec Kit para Antigravity & Handover Backend

1.  **Spec Kit (`specify-cli`):** Se instaló e inicializó en el proyecto el toolkit oficial de GitHub para desarrollo guiado por especificaciones (Spec-Driven Development) bajo la integración de Antigravity (`agy`), creando el entorno `.agents/` con comandos de especificación, auditoría cruzada y checklists de calidad (`/speckit-constitution`, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-checklist`).
2.  **Handover Inter-Equipos:** Se redactó la guía oficial de integración en [`nuevamente-ai-core/HANDOVER_BACKEND.md`](file:///c:/Users/Predator%20Pro/OneDrive/Documents/Proyectos/Marcos_proyects/Hackaton-Alura/nuevamente-ai-core/HANDOVER_BACKEND.md) dirigida a Diego Mendez (Backend), proporcionando ejemplos de endpoints asíncronos en FastAPI, contratos de telemetría y directrices de variables de entorno para el despliegue.

---

## 11. Registro de Cambios y Optimizaciones (Changelog)

Para mantener la máxima trazabilidad del desempeño y seguridad solicitada por el equipo:

### v1.0.1 (25 Septiembre 2026)
*   **Seguridad:** Corrección de falso positivo en `bandit` (SAST) suprimiendo la alerta B310 en `auditor.py` dado que el target es estrictamente `localhost:11434` (Ollama local). El escáner ahora reporta 0 vulnerabilidades.
*   **Desempeño:** Identificado "Cold Start" de 20.33s en el pipeline asíncrono. Los subsiguientes ciclos demuestran un "Warm Start" de ~3.01s.
*   **Planificación:** Se redactó el documento [docs/PLAN_OPTIMIZACION_RENDIMIENTO.md](file:///c:/Users/Predator%20Pro/OneDrive/Documents/Proyectos/Marcos_proyects/Hackaton-Alura/docs/PLAN_OPTIMIZACION_RENDIMIENTO.md) proponiendo inicialización cálida de ChromaDB en los eventos de ciclo de vida de FastAPI y uso de Caché Semántico.

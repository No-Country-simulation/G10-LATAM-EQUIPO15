# PLAN DE TRABAJO TÁCTICO SEMANA A SEMANA: SQUAD DE IA Y DATOS
## Proyecto: NuevaMente — Hackathon ONE (Oracle & Alura Latam, Cohorte G-10)
**Carácter:** Hoja de Ruta Operativa, Asignación Nominal Día a Día y Criterios de Aceptación  
**Líder Técnico de IA:** Marcos Gael Hernández Cruz  
**Fecha de Inicio:** Lunes 21 de Septiembre de 2026 (Semana 1)  
**Hito Límite de Entrega del MVP:** Domingo 11 de Octubre de 2026 (Semana 3)  

---

## 1. Integrantes del Squad de IA y Datos

| Integrante | Rol Oficial en el Squad | Responsabilidades Nucleares | Herramientas Clave |
|---|---|---|---|
| **Marcos Gael Hernández Cruz** | **AI Engineer** | Arquitectura del grafo LangGraph, fábrica agnóstica de LLMs (Gemini/Groq), contratos Pydantic V2, agente crítico de fidelidad fáctica y conector público del pipeline. | Python 3.11+, LangGraph, LangChain, Pydantic V2, Gemini AI Studio, Groq Cloud. |
| **Fernando Falla** | **Data Engineer** | Pipeline de extracción de documentos técnicos (PyMuPDF), algoritmos de chunking semántico jerárquico (800/150) y base de datos vectorial local (ChromaDB). | PyMuPDF (`fitz`), ChromaDB, LangChain Text Splitters, FastEmbed. |
| **Andy Mijail Martinez Solis** | **Data Analyst & Prompt QA** *(Turno Mañana)* | Curaduría de los 3 manuales oficiales en `data/raw/`, diseño de ejemplos Few-Shot de alta pedagogía, auditoría de anclaje fáctico y pruebas de anti-alucinaciones. | Markdown, ChatGPT/Claude (curaduría de prompts), datasets de validación, Pytest. |
| **Jacqueline Rioja** | **PM & Calidad de Datos** | Gestión del tablero Kanban del squad, seguimiento de dependencias inter-squads y supervisión del entorno de desarrollo. | GitHub Projects, GitHub Actions, Git. |

---

## 2. Los 3 Perfiles Canónicos de Destino

Todas las tareas de desarrollo, prompts y datasets deben ceñirse estrictamente a los 3 perfiles oficiales acordados:
1. **Junior:** Audiencia en formación inicial/intermedia. Uso intensivo de analogías del mundo real, explicaciones didácticas guiadas y código procedural comentado sin tecnicismos innecesarios.
2. **Senior:** Líderes técnicos y arquitectos de software. Enfoque riguroso en trade-offs, escalabilidad, resiliencia, patrones de diseño, vectores de seguridad y rendimiento.
3. **Ejecutivo:** Gestores y directores de negocio. Enfoque estratégico en retorno de inversión (ROI), impacto operativo, costos en la nube, métricas de gobernanza y resúmenes ejecutivos (TL;DR).

---

## 3. Plan Táctico Detallado Semana a Semana (Día a Día)

### 🔵 SEMANA 1: ARRANQUE ACELERADO DE CÓDIGO (21 AL 27 SEPTIEMBRE)
> **Meta de la semana:** Tener el pipeline nuclear de IA funcionando en local. Ingesta PyMuPDF $\rightarrow$ Chunking $\rightarrow$ ChromaDB $\rightarrow$ LangGraph básico $\rightarrow$ JSON con Flashcards preliminares.

#### Lunes 21 y Martes 22 de Septiembre (Días 1 y 2): Scaffolding, Factoría y Extracción
* **Marcos Gael (AI Eng):**
  - [x] Crear la estructura modular de directorios en el repositorio de IA (`src/ai/`).
  - [x] Implementar `src/ai/config.py`: factoría desacoplada con `init_chat_model` configurando **Google Gemini 2.5 Flash** (modelo primario) y **Groq Cloud (`llama-3.3-70b-versatile`)** como failover automático ante errores 429.
  - [x] Formalizar `src/ai/schemas.py`: modelos Pydantic V2 canónicos (`PerfilDestinatarioEnum`, `FormatoSalidaEnum`, `AdaptacionContenidoResponse`).
  - [x] Entregar copia de `schemas.py` a Diego Mendez (Backend) para desbloquear el endpoint Mock de FastAPI.
* **Fernando Falla (Data Eng):**
  - [ ] Implementar `src/ai/ingestion/extractor.py` utilizando `pymupdf` (`fitz`).
  - [ ] Programar extracción de texto limpio con metadatos: número de página, delimitación de encabezados (`#`, `##`) y soporte para archivos `.pdf`, `.md` y `.txt`.
  - [ ] Crear script de prueba unitaria para verificar extracción sin pérdida de caracteres.
* **Andy Mijail (Data Analyst / QA):**
  - [ ] Descargar y colocar en `data/raw/` los 3 manuales oficiales de prueba:
    1. `manual-redes-vcn-oracle.pdf` (Oracle Cloud Infrastructure VCN).
    2. `guia-autenticacion-tokens-jwt.md` (Seguridad y Tokens JWT).
    3. `arquitectura-microservicios-cloud.txt` (Patrones Cloud y Microservicios).
  - [ ] Ejecutar el extractor de Fernando sobre los 3 archivos y validar legibilidad.
* **Jacqueline Rioja (PM):**
  - [ ] Crear las tarjetas del sprint 1 en el Kanban de GitHub Projects.
  - [ ] Verificar que todo el squad tenga clonado el repo e instalado `requirements.txt`.

#### Miércoles 23 y Jueves 24 de Septiembre (Días 3 y 4): Chunking, ChromaDB y LangGraph Inicial
* **Fernando Falla (Data Eng):**
  - [ ] Implementar `src/ai/ingestion/chunker.py` con `RecursiveCharacterTextSplitter`.
  - [ ] Configurar separadores: `["\n## ", "\n### ", "\n```", "\n\n", "\n", " "]`, tamaño de 800 tokens y solapamiento de 150 tokens.
  - [ ] Inyectar metadatos en cada fragmento: `[Documento: {doc} | Pág: {pag} | Sección: {sec}]`.
  - [ ] Implementar `src/ai/rag/vectorstore.py`: inicializar ChromaDB persistente local y función `buscar_similares(query, top_k=5)`.
* **Marcos Gael (AI Eng):**
  - [x] Implementar `src/ai/state.py`: TypedDict `EstadoPipelineAdaptacion` con mensajes, contexto recuperado, rol y resultado.
  - [x] Construir `src/ai/agents/analizador.py`: extrae conceptos clave a partir del contexto recuperado.
  - [x] Construir `src/ai/agents/creador.py`: nodo de generación con salida estructurada forzada mediante `with_structured_output(PaqueteContenidoAdaptado)`.
  - [x] Ensamblar `src/ai/graph.py`: StateGraph inicial conectando `nodo_analizador -> nodo_creador`.
* **Andy Mijail (Data Analyst / QA):**
  - [ ] Redactar el banco de directrices y Few-Shot para el perfil **Junior** en formato **Flashcards**: pares de frente (pregunta directa), dorso (definición) y pista analógica didáctica.

#### Viernes 25 y Sábado 26 de Septiembre (Días 5 y 6): Integración Nuclear y Sync Point 1
* **Marcos Gael & Fernando Falla:**
  - [ ] Conectar el recuperador de ChromaDB al grafo de LangGraph.
  - [ ] Crear el script de demostración ejecutable `run_demo_local.py`.
  - [ ] Validar que un PDF de entrada genere un JSON con 5 Flashcards válidas en menos de 10 segundos.
* **Andy Mijail (QA):**
  - [ ] Auditar el JSON generado: verificar que las tarjetas no contengan alucinaciones evidentes y que el lenguaje sea accesible para perfiles junior.
* **Todo el Squad (Sync Point 1 con Backend y Frontend):**
  - [ ] Demostración en vivo al equipo: el script de IA procesa el PDF y devuelve el JSON canónico que coincide 100% con los mocks consumidos por Frontend.

#### Domingo 27 de Septiembre (Día 7): Buffer y Estabilización S1
* Limpieza de código, documentación de funciones y preparación de ramas para Semana 2.

---

### 🟠 SEMANA 2: AGENTE CRÍTICO, PROMPTS POR PERFIL Y MULTIFORMATO (28 SEPTIEMBRE AL 04 OCTUBRE)
> **Meta de la semana:** Cerrar al 100% el motor de IA. Integrar el Agente Crítico de Calidad fáctica ($\ge 0.85$), soporte para los 3 perfiles (Junior, Senior, Ejecutivo) y generación de Mapas Mentales Mermaid y Quizzes.

#### Lunes 28 a Miércoles 30 de Septiembre (Días 8 a 10): Agente Crítico y Bucle de Auto-Corrección
* **Marcos Gael (AI Eng):**
  - [ ] Implementar `src/ai/agents/critico.py`: nodo evaluador en `temperature=0.0` que extrae afirmaciones fácticas y calcula `anclaje_fuente_score = (afirmaciones_sustentadas) / (total_afirmaciones)`.
  - [ ] Programar la compuerta condicional en LangGraph:
    * Si score $\ge 0.85 \rightarrow$ Avanza a `nodo_ensamblador`.
    * Si score $< 0.85$ y reintentos $< 2 \rightarrow$ Regresa a `nodo_creador` inyectando observaciones correctivas.
    * Si alcanza 2 reintentos $\rightarrow$ Avanza adjuntando advertencia de fidelidad.
* **Andy Mijail (Data Analyst / QA):**
  - [ ] Diseñar el dataset de calibración de prompts para el perfil **Senior**: preguntas de juicio arquitectónico, análisis de fallos y justificación de por qué las alternativas falsas son incorrectas (para Quizzes).
  - [ ] Diseñar el dataset de prompts para el perfil **Ejecutivo**: esquemas de retorno de inversión, costos cloud y resúmenes TL;DR.
* **Fernando Falla (Data Eng):**
  - [ ] Optimizar el índice de ChromaDB: implementar filtros por metadatos (filtrar fragmentos por capítulo o sección).

#### Jueves 01 a Sábado 03 de Octubre (Días 11 a 13): Mapas Mentales Mermaid y Suite de Pruebas
* **Marcos Gael (AI Eng):**
  - [ ] Implementar generador de Mapas Mentales jerárquicos con sintaxis **Mermaid.js** (`mindmap`).
  - [ ] Añadir validador sintáctico para garantizar que Mermaid no emita caracteres especiales sin escapar.
  - [ ] Implementar `src/ai/pipeline.py`: función pública `ejecutar_pipeline_adaptacion(doc_titulo, doc_contenido, perfil, formato, nicho)`.
* **Fernando Falla (Data Eng):**
  - [ ] Crear la suite de pruebas unitarias `tests/test_ai_pipeline.py` con `pytest`.
* **Andy Mijail (QA):**
  - [ ] Ejecutar pruebas de cobertura sobre los 3 manuales: medir tiempos de ejecución y registrar métricas de fidelidad.
* **Marcos & Diego Mendez (Sync Point 2 con Backend):**
  - [ ] Conectar FastAPI con la función `ejecutar_pipeline_adaptacion()`. Backend invoca LangGraph directamente sin usar mocks.

#### Domingo 04 de Octubre (Día 14): Cierre de Motor de IA
* Todo el código de IA queda congelado en rama `develop`, listo para la convergencia final.

---

### 🟣 SEMANA 3: CONVERGENCIA E2E Y LÍMITE CRÍTICO DEL MVP (05 AL 11 OCTUBRE)
> **⚠️ HITO CRÍTICO DE ENTREGA:** Integrar el motor de IA de punta a punta con la API de FastAPI, el Stepper de Server-Sent Events (SSE), la persistencia en OCI Object Storage y la interfaz visual de Frontend.

#### Lunes 05 a Miércoles 07 de Octubre (Días 15 a 17): Telemetría SSE y Enlace con Backend
* **Marcos Gael (AI Eng):**
  - [ ] Instrumentar los nodos de LangGraph para emitir callbacks de telemetría por cada transición:
    1. `EXTRACCION` (20%)
    2. `INDEXACION` (40%)
    3. `GENERACION` (60%)
    4. `AUDITORIA` (80%)
    5. `COMPLETADO` (100%)
  - [ ] Asistir a Cristian Cortes en la canalización de estos eventos al endpoint `/stream` de FastAPI.
* **Fernando Falla (Data Eng):**
  - [ ] Optimizar la memoria y latencia de ChromaDB para ejecuciones concurrentes.
* **Andy Mijail (QA):**
  - [ ] Probar subida de documentos con diferentes tamaños (de 1 a 10 MB) y verificar que no ocurran cuellos de botella de memoria.

#### Jueves 08 a Sábado 10 de Octubre (Días 18 a 20): Pruebas E2E y Validación con Frontend
* **Marcos Gael & Andy Mijail (con Karen Gonzalez y Cristian Cortes):**
  - [ ] Probar el flujo completo desde el navegador:
    1. Cargar PDF en zona Drag & Drop.
    2. Seleccionar Rol (**Junior**, **Senior** o **Ejecutivo**) y Formato (**Flashcards**, **Quiz** o **Mapa Mental**).
    3. Observar el Stepper en tiempo real animándose vía SSE.
    4. Interactuar con las tarjetas 3D volteables, resolver el quiz y explorar el mapa Mermaid.
    5. Verificar que el JSON generado y el archivo original se almacenen en OCI Object Storage.
* **🚨 SÁBADO 10 DE OCTUBRE: SYNC POINT 3 — MVP 100% OPERATIVO Y CONVERGIDO.**

#### Domingo 11 de Octubre (Día 21): Certificación del MVP
* Revisión de cumplimiento del PRD y criterios de aceptación del hackathon.

---

### 🟡 SEMANA 4: CERTIFICACIÓN DE CASOS ORACLE, HARDENING Y CODE FREEZE (12 AL 18 OCTUBRE)
> **Meta de la semana:** Certificar formalmente los 3 casos oficiales de evaluación, optimizar tokens/latencia y ejecutar el Code Freeze.

* **Andy Mijail & Marcos Gael:**
  - [ ] Ejecutar y certificar formalmente los 3 Casos Oficiales de Demostración:
    * **Caso 1:** `manual-redes-vcn-oracle.pdf` $\rightarrow$ Perfil **Junior** $\rightarrow$ Flashcards 3D (Score $\ge 0.90$).
    * **Caso 2:** `guia-autenticacion-tokens-jwt.md` $\rightarrow$ Perfil **Senior** $\rightarrow$ Quiz Interactivo con Justificaciones (Score $\ge 0.85$).
    * **Caso 3:** `arquitectura-microservicios-cloud.txt` $\rightarrow$ Perfil **Ejecutivo** $\rightarrow$ Mapa Mental Mermaid + Resumen Ejecutivo (Score $\ge 0.90$).
  - [ ] Generar el reporte de auditoría `AUDITORIA_CALIDAD_3_CASOS.md`.
* **Marcos Gael & Fernando Falla:**
  - [ ] Hardening: asegurar que si Gemini 2.5 Flash devuelve un error 429, Groq tome el control sin que el usuario final note ningún fallo.
  - [ ] Optimización de prompts para reducir consumo de tokens en un 20%.
* **Viernes 17 de Octubre:** **CODE FREEZE.** Cierre definitivo de ramas de código. Cero cambios posteriores.

---

### 🔴 SEMANA 5: PRODUCCIÓN DEL VIDEO PITCH Y ENTREGA FINAL (19 AL 24 OCTUBRE)
> **Meta de la semana:** Apoyar la grabación del Video Pitch, capturar métricas en vivo y entregar formalmente en la plataforma de Alura ONE.

* **Marcos Gael & Andy Mijail:**
  - [ ] Grabar el segmento técnico del Video Pitch (coordinado por Cristian Maida): demostración en pantalla de LangGraph razonando, la auditoría del Agente Crítico y la verificación de persistencia en OCI Object Storage.
* **Fernando Falla & Jacqueline Rioja:**
  - [ ] Validar que el repositorio cumpla con todas las pautas de entrega: README corporativo, licencia, instrucciones de instalación y sin secretos expuestos.
* **Sábado 24 de Octubre:** Envío formal del proyecto al comité de Oracle Next Education.

---

## 4. Matriz de Entregables Técnicos por Integrante de IA

| Integrante | Semana 1 (Arranque) | Semana 2 (Cierre IA) | Semana 3 (MVP E2E) | Semana 4 (Hardening) | Semana 5 (Pitch) |
|---|---|---|---|---|---|
| **Marcos Gael** | `config.py` (LLM Factory), `schemas.py`, StateGraph inicial | `critico.py` (loop de calidad), Mermaid generator, `pipeline.py` | Telemetría SSE conectada a FastAPI, integración E2E | Optimización de tokens, failover Groq probado | Demo en vivo grabada para el Video Pitch |
| **Fernando Falla** | `extractor.py` (PyMuPDF), `chunker.py` (800/150), ChromaDB local | Filtros de metadatos en ChromaDB, `test_ai_pipeline.py` | Optimización de memoria en Vector Store | Pruebas de estrés y documentos irregulares | Documentación de arquitectura de datos |
| **Andy Mijail** | Curaduría de 3 manuales en `data/raw/`, Few-Shot Junior | Datasets Few-Shot Senior y Ejecutivo, validación de fidelidad | Auditoría de respuestas en la UI integrada | Certificación formal de los 3 casos oficiales | Asistencia técnica al guion del pitch |
| **Jacqueline Rioja** | Setup de repositorio, Kanban S1, verificación de entornos | Seguimiento Kanban S2, control de handshakes | Supervisión de DoD del MVP E2E | Aprobación de PRs finales y Code Freeze | Checklist de entrega del jurado de Alura |

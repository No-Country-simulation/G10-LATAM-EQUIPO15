# DOSSIER DE DOCUMENTACIÓN OFICIAL DE INGENIERÍA
## Proyecto: NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo
**Hackathon:** ONE (Oracle Next Education) & Alura Latam — Cohorte G-10  
**Carácter:** Documentación Técnica de Referencia y Plan Maestro de Ejecución

> **Nota de estado:** Este dossier incluye la documentación técnica definitiva del componente de Inteligencia Artificial (AI Core) y Datos.

---

## 1. Estructura del Dossier Documental

La carpeta `docs/` contiene el conjunto exhaustivo de artefactos de ingeniería para arrancar el proyecto y respaldar la presentación ante el jurado calificador de Oracle y Alura:

```text
docs/
├── README.md                                  # Índice general del dossier documental (Este archivo)
├── 01_PRD_PRODUCT_REQUIREMENTS_DOCUMENT.md    # Requisitos de producto, visión, user personas e ISO 25010
├── 02_SISTEMA_DE_DISENO_Y_UI_UX.md           # Tokens, componentes didácticos (Flashcards, Quizzes, Mapas) y Wireframes
├── 03_WBS_Y_DEFINICION_DE_TAREAS.md          # Desglose formal de tareas por squad e integrante con dependencias
├── 04_TIMELINE_EXTENDIDO_Y_HITOS.md           # Cronograma extendido día a día, diagrama de Gantt e hitos de control
├── 05_CONTRATOS_DE_DATOS_Y_SCHEMAS.md         # Modelos Pydantic V2 canónicos para Backend, Frontend y LangGraph
├── 06_ARQUITECTURA_DE_IA_Y_SISTEMA_MULTIAGENTE.md # Pipeline RAG, Chunking, Embeddings y LangGraph Multi-Agente
├── 07_DIAGRAMAS_DE_ARQUITECTURA_Y_FLUJOS.md       # Diagramas C4, Handshake entre Squads, Secuencia E2E y Git
├── 08_BUENAS_PRACTICAS_SKILLS_Y_RESILIENCIA.md   # Auditoría Hermes 3, catálogo de tools, manejo de fallos y rate limit
├── 09_PLAN_MAESTRO_INTEGRADO_IA_BACKEND_CLOUD_FRONTEND.md # Plan maestro integrado E2E y tareas atómicas por squad
├── 10_PLAN_OPERATIVO_SQUAD_IA_Y_DATOS.md          # Plan de ejecución autónomo para el Squad de IA y Datos
├── 11_PLAN_OPERATIVO_SQUAD_BACKEND_Y_CLOUD.md     # Plan de ejecución autónomo para el Squad de Backend y OCI
├── 12_PLAN_OPERATIVO_SQUAD_FRONTEND_Y_UX.md       # Plan de ejecución autónomo para el Squad de Frontend y UX
├── 13_INFORME_FINAL_AI_CORE_SEMANA_1.md       # Informe de finalización del Sprint 1 para IA
├── 14_REPORTE_BENCHMARK_Y_RENDIMIENTO_APIs.md # Reporte de latencia de Groq vs Gemini
├── 15_DOCUMENTACION_FINAL_AI_CORE.md          # Documentación definitiva técnica del motor integrado
├── 18_MEJORAS_DATA_IA_FASE_A.md               # Mejoras de ingestión, chunking y vector store (Data/IA)
├── 19_PROPUESTA_CAMBIOS_AI_CORE.md            # Propuesta de cambios para AI Core y Backend tras la Fase A
├── CHECKLIST_MAESTRO_AVANCES_Y_HITOS.md       # Tablero maestro de seguimiento, fechas, tareas y checklist por área
└── adr/                                       # Architectural Decision Records (Decisiones de Ingeniería)
    ├── 001-seleccion-langgraph-vs-cadenas-monoliticas.md
    ├── 002-persistencia-obligatoria-oci-object-storage-always-free.md
    └── 003-protocolo-hibrido-rest-y-telemetria-sse.md
```

---

## 2. Propósito y Audiencia de Cada Documento

| Documento | Audiencia Primaria | Contenido y Utilidad |
|---|---|---|
| **`01_PRD_PRODUCT_REQUIREMENTS_DOCUMENT.md`** | Todo el Equipo / Evaluadores | Especificación funcional formal (FRs), requerimientos de calidad ISO/IEC 25010 (NFRs) y casos de uso del producto. |
| **`02_SISTEMA_DE_DISENO_Y_UI_UX.md`** | Equipo de Diseño y Frontend | Guía de estilo "Minimalismo Clásico Tecnológico", diseño de tarjetas 3D, quizzes con feedback, mapas mentales Mermaid. |
| **`05_CONTRATOS_DE_DATOS_Y_SCHEMAS.md`** | Backend e IA | Código Python con esquemas Pydantic V2 de entrada, salida y telemetría. |
| **`06_ARQUITECTURA_DE_IA_Y_SISTEMA_MULTIAGENTE.md`** | Equipo de IA | Especificación de PyMuPDF, chunking jerárquico, LangGraph y VectorStore. |
| **`15_DOCUMENTACION_FINAL_AI_CORE.md`** | Frontend, Backend e IA | Documentación definitiva del motor Multi-Agente, failover a Groq y rendimientos esperados. |
| **`18_MEJORAS_DATA_IA_FASE_A.md`** | Equipo de IA y Datos | Diagnóstico del pipeline, cambios en ingestión, chunking y vector store, mediciones antes/después y fases siguientes. |
| **`19_PROPUESTA_CAMBIOS_AI_CORE.md`** | AI Core y Backend | Impacto de la Fase A en otros equipos y propuesta de cambios en selección de contexto y agente crítico. |

---

## 3. Criterio de mantenimiento

La documentación no debe convertirse en una carga adicional para los equipos.

Cada equipo es responsable principalmente de:
- subir y mantener su código;
- mantener la documentación mínima necesaria para instalar, ejecutar y entender su componente;
- registrar decisiones técnicas relevantes cuando afecten la integración con otros equipos.

La documentación transversal del proyecto se mantendrá en esta carpeta.

---

## 4. Guía Rápida para la Presentación en el Hackathon

Para presentar el proyecto ante los evaluadores, la narrativa debe alinearse con los tres activos clave documentados:
1. **Rigor Técnico e Innovación:** Orquestación Multi-Agente con LangGraph, agente crítico de anclaje semántico y generación multimodal (Flashcards, Quizzes, Mapas).
2. **Infraestructura de Nube Gratuita:** Demostración en vivo de persistencia en OCI.
3. **Resiliencia Extrema:** Failover inteligente y dinámico hacia Groq Cloud en caso de saturación.

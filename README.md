# 🧠 NuevaMente - G10 Hackathon

Sistema Inteligente de Adaptación y Generación de Contenido Educativo.
Proyecto desarrollado para el Hackathon ONE G10 / Alura Latam.

## Estructura del repositorio

- `backend/` — Backend, integraciones y despliegue.
- `frontend/` — Interfaz de usuario.
- `nuevamente-ai-core/` — Componente Core de IA y Datos (DataIA Pipeline)
- `docs/` — Documentación técnica, reportes y decisiones arquitectónicas.
- `data/` — Datos y documentos de prueba.

---

## 📑 Índice de Documentación de IA y Datos

Este repositorio almacena la documentación arquitectónica, técnica y de gestión del componente de Inteligencia Artificial (DataIA Pipeline).

### 1. Arquitectura y Decisiones Core
*   [**Alineación de Arquitectura MVP**](docs/ALINEACION_ARQUITECTURA_MVP.md): Documento maestro que detalla el uso del orquestador Multi-Agente (LangGraph).
*   [**Plan de Optimización de Rendimiento**](docs/PLAN_OPTIMIZACION_RENDIMIENTO.md): Diagnóstico de tiempos de respuesta y estrategias técnicas.

### 2. Integración y Contratos Inter-Equipos
*   [**Contratos Backend API**](docs/CONTRATOS_BACKEND_API.md): Especificación estricta de las entradas y salidas (JSON) esperadas.
*   [**Checklist Maestro de Avances y Hitos**](docs/CHECKLIST_MAESTRO_AVANCES_Y_HITOS.md): Tabla de seguimiento general.

### 3. Reportes Finales
*   [**Reporte de Benchmark y Latencia**](docs/14_REPORTE_BENCHMARK_Y_RENDIMIENTO_APIs.md)
*   [**Documentación Definitiva AI Core**](docs/15_DOCUMENTACION_FINAL_AI_CORE.md)

---

## 🛠️ Stack Tecnológico de IA
*   **Orquestación:** LangGraph (StateGraph, Multi-Agente asíncrono).
*   **LLM Engine:** Gemini 2.5 Flash (Base) / Groq Llama 3.3 (Failover).
*   **Vector Store:** ChromaDB (con Embeddings Sentence-Transformers).
*   **Validación:** Pydantic V2 (Esquemas estructurados y prevención de inyecciones prompt/XSS).
*   **Despliegue Objetivo:** OCI Always Free (Oracle Cloud Infrastructure).

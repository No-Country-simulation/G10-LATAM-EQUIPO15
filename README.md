# 🧠 NuevaMente - G10 Hackathon

Sistema Inteligente de Adaptación y Generación de Contenido Educativo.
Proyecto desarrollado para el Hackathon ONE G10 / Alura Latam.

## Estructura del repositorio

- `backend/` — Backend, integraciones y despliegue.
- `frontend/` — Interfaz de usuario.
- `nuevamente-ai-core/` — Orquestación y agentes AI Core.
- `ia/` — Paquete compartido Data/IA y servicio HTTP.
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
*   **LLM Engine:** Gemini configurable; ejecución HTTP estricta con límites y sin borrador simulado de contingencia.
*   **Vector Store:** ChromaDB persistente, embeddings de Google y cachés reutilizables por hash del documento.
*   **Validación:** Pydantic V2 (Esquemas estructurados y prevención de inyecciones prompt/XSS).
*   **Despliegue Objetivo:** OCI Always Free (Oracle Cloud Infrastructure).

## Ejecutar y verificar

Backend y servicio IA (requiere `GOOGLE_API_KEY` en `ia/.env`):

```powershell
docker compose --env-file ia/.env -f compose.integration.yaml up --build -d
```

Backend queda en <http://localhost:18002/docs>. IA usa la red interna y conserva Chroma y cachés en un volumen Docker.

Frontend estático:

```powershell
docker compose -f frontend/compose.yaml up --build -d
```

Frontend queda en <http://localhost:18003>. Su adaptador usa una respuesta de ejemplo; la conexión al Backend real sigue pendiente. OCI Object Storage y despliegue cloud también siguen pendientes.

Para reproducir las suites offline y la prueba real con Gemini, ver [tests/README.md](tests/README.md). La API vigente está documentada en el [contrato Backend ↔ IA v2.3](docs/CONTRATOS/CONTRATO_BACKEND_IA.md). Los planes y reportes anteriores conservan antecedentes; consultar estos documentos operativos para el comportamiento actual.

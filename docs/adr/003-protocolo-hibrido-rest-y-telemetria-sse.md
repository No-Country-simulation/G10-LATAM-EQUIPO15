# ADR-003: Protocolo Híbrido de Entrega (REST Síncrono Canónico + Telemetría Server-Sent Events)
**Estado:** Aprobado  
**Fecha:** 2026-09-17  
**Autores:** Joaquin y Diego (Backend) & Cristian Cortes y Karen Gonzalez (Frontend)  
**Alcance:** Protocolos de Comunicación API, Telemetría en Vivo y Experiencia de Usuario  

---

## 1. Contexto y Problema
El sistema presenta dos requerimientos de interacción concurrentes con características divergentes:
1. **Requisito Evaluativo Oficial del Hackathon:** La documentación del concurso exige un endpoint REST estándar `POST /api/v1/adaptar-contenido` que recibe el payload y responde con el paquete JSON estructurado completo de forma síncrona y predecible para pruebas automáticas o de integración externa.
2. **Requisito de Experiencia de Usuario (UI/UX):** La inferencia de modelos de lenguaje, el chunking vectorial y la persistencia en OCI consumen entre 10 y 20 segundos. Una interfaz con un spinner estático genera incertidumbre en el usuario; se requiere un **Stepper de Estado en Vivo** que informe en tiempo real en qué fase se encuentra el proceso (`EXTRACCION`, `INDEXACION`, `GENERACION`, `AUDITORIA`, `PERSISTENCIA`).

Si se migraba el endpoint oficial a WebSockets o a un esquema asíncrono con `job_id`, se corría el riesgo de incompatibilidad con pruebas automatizadas del jurado de Alura/Oracle.

---

## 2. Decisión Arquitectónica
Se adopta un **Patrón Híbrido de Doble Canal en FastAPI**:

```
[ Cliente de Evaluación / Swagger / Test Scripts ] 
                   │ 
                   ▼ (HTTP POST Estándar)
          POST /api/v1/adaptar-contenido ──► Retorna JSON Canónico Completo (200 OK)

[ Interfaz de Usuario React / Streamlit ]
                   │
                   ▼ (HTTP POST con Server-Sent Events - SSE)
          POST /api/v1/adaptar-contenido/stream ──► Emite Eventos de Fase + Paquete Final
```

### Canales Implementados:
1. **Canal Oficial Canónico (`POST /api/v1/adaptar-contenido`):**
   - Ejecución directa del pipeline completo.
   - Retorna exactamente el esquema canónico exigido en las bases (pág. 4-5 del documento oficial de Oracle ONE).
   - Garantiza 100% de compatibilidad con pruebas con `curl`, Postman o evaluadores automatizados.
2. **Canal de Telemetría Progresiva (`POST /api/v1/adaptar-contenido/stream`):**
   - Implementado mediante **Server-Sent Events (SSE)** con `StreamingResponse` de FastAPI.
   - Emite eventos serializados `event: phase_update` conteniendo el modelo `TelemetriaEstadoResponse` para mover la barra de progreso en la UI.
   - Al finalizar la fase de persistencia en OCI, emite el evento final `event: completion` con el payload JSON completo.

---

## 3. Consecuencias y Trade-offs

### Consecuencias Positivas:
* **Cero Riesgo de Evaluación:** El endpoint oficial exigido por el Hackathon permanece intacto, determinista y conforme a la documentación.
* **Experiencia de Usuario Premium:** La interfaz gráfica ofrece retroalimentación visual continua, eliminando la sensación de latencia o congelamiento.
* **Ligereza Técnica:** Server-Sent Events es nativo en HTTP/1.1 y HTTP/2, requiere menor sobrecarga que WebSockets y no necesita brokers de mensajería externos (Redis / Celery), preservando el principio de ligereza de la arquitectura.

### Consecuencias Negativas / Mitigaciones:
* **Duplicación de Controladores:** Mitigado implementando un servicio central orquestador (`src/backend/services/content_orchestrator.py`) con generador asíncrono (`async generator`), consumido tanto por la versión síncrona como por la de streaming.

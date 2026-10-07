#  CHECKLIST  DE AVANCES, HITOS Y SEGUIMIENTO POR ÁREAS
## Proyecto: NuevaMente — Plataforma Educativa Inteligente
**Hackathon:** ONE (Oracle Next Education) & Alura Latam — Cohorte G-10  
**Tech Lead & Líder de IA:** Marcos Gael Hernández Cruz  
**PM & Coordinadora de Calidad:** Jacqueline Rioja  
**Última Actualización:** 24 de Septiembre de 2026  

---

##  1. Tablero de Control de Avance General

| Área / Squad | Líder / Responsables | Progreso Semana 1 | Estado Actual | Siguiente Hito Crítico |
|---|---|:---:|:---:|---|
|  **IA y Datos** | Marcos H., Fernando F., Andy M., Jacqueline R. | **100%** |  Adelantado / Listo para integrar | Conexión del pipeline async en FastAPI |
|  **Backend & APIs** | Diego M., Cristian C., Alexis P., Joaquín R. | **70%** |  En desarrollo | Reemplazo de Mock por `ejecutar_pipeline_adaptacion_async` |
|  **Cloud & OCI Always Free** | Alexis P., Joaquín R. | **65%** |  En desarrollo | Módulo `oci_service.py` con credenciales de Object Storage |
|  **Frontend & UX/UI** | Karen G., Cristian C. | **60%** |  En desarrollo | Visor de Flashcards 3D y Stepper SSE de 5 fases |
|  **Gestión, QA & Pitch** | Jacqueline R., Andy M., Cristian M. | **80%** |  Al día | Validación cruzada de manuales y tablero Kanban |

---

## 2. Cronograma de Sprints y Fechas Propuestas

* **Semana 1 (21 - 27 Sep 2026):** Arranque Acelerado de Código y Módulos Nucleares.
* **Semana 2 (28 Sep - 04 Oct 2026):** Integración Core (IA + FastAPI + OCI).
* **Semana 3 (05 - 11 Oct 2026):**  **Hito Límite MVP:** Integración E2E, Mapas Mentales y Telemetría.
* **Semana 4 (12 - 18 Oct 2026):** Hardening en Nube OCI, Certificación de 3 Casos Oficiales y Guion Pitch.
* **Semana 5 (19 - 24 Oct 2026):**  **Code Freeze, Grabación de Video y Entrega en Plataforma ONE.**

---

##  3. Checklist Detallado por Semana y Área

###  SEMANA 1 (21 al 27 de Septiembre, 2026) — Scaffolding y Núcleo de Código

####  Squad Inteligencia Artificial & Datos
- [x] **Arquitectura Multi-Agente:** Implementación del StateGraph en LangGraph (`analizador`, `creador`, `critico`, `ensamblador`). *(Resp: Marcos H. | 22/09)*
- [x] **Pipeline Asíncrono no bloqueante:** Función `ejecutar_pipeline_adaptacion_async` con `.ainvoke()` para FastAPI. *(Resp: Marcos H. | 22/09)*
- [x] **Telemetría de 5 Fases:** Callback polimórfico (sync/async) emitiendo de 20% a 100%. *(Resp: Marcos H. | 22/09)*
- [x] **Optimización de Rendimiento:** Lazy imports en `VectorStoreService` (latencia reducida de 56s a <0.05s). *(Resp: Marcos H. | 22/09)*
- [x] **Extracción y Chunking:** Extractor PyMuPDF/Markdown y segmentador jerárquico (800/150). *(Resp: Fernando F. | 23/09)*
- [x] **Seguridad SAST & Sanitización:** 0 vulnerabilidades con Bandit; filtros anti-XSS y anti-Prompt Injection en Pydantic V2. *(Resp: Marcos H. | 22/09)*
- [x] **Suite de Pruebas:** 10/10 tests pasando en verde con Pytest en `tests/test_ai_pipeline.py`. *(Resp: Marcos H. | 25/09)*
- [x] **Herramienta Spec Kit:** Instalación de `specify-cli` con integración `agy` (.agents/) para auditorías SDD y generación de planes. *(Resp: Marcos H. | 25/09)*
- [x] **Auditoría Local con Nous Hermes 3:** Auditor de seguridad y lógica asíncrono vía Ollama sin costo de tokens de API. *(Resp: Marcos H. | 25/09)*
- [x] **Handover Técnico Backend:** Redacción oficial de [`HANDOVER_BACKEND.md`](file:///c:/Users/Predator%20Pro/OneDrive/Documents/Proyectos/Marcos_proyects/Hackaton-Alura/nuevamente-ai-core/HANDOVER_BACKEND.md). *(Resp: Marcos H. | 22/09)*
- [ ] **Curaduría de 3 Manuales Oficiales:** Completar en `data/raw/` (VCN OCI listo; pendientes JWT y Microservicios). *(Resp: Andy M. | Fecha límite: 26/09)*

####  Squad Backend & APIs
- [ ] **Scaffolding FastAPI:** Estructura modular del proyecto en Python/FastAPI. *(Resp: Diego M., Cristian C. | 22/09)*
- [ ] **Contratos Pydantic V2:** Réplica de esquemas de entrada y salida basados en `src/ai/schemas.py`. *(Resp: Diego M. | 23/09)*
- [ ] **Endpoint Mock Activo:** `POST /api/v1/adaptacion` retornando JSON estático para pruebas de Frontend. *(Resp: Diego M. | Fecha límite: 25/09)*
- [ ] **Revisión de Handover de IA:** Confirmar integración de `ejecutar_pipeline_adaptacion_async`. *(Resp: Diego M. | Fecha límite: 25/09)*
- [ ] **Definición de Protocolo de Telemetría:** Decidir entre Server-Sent Events (SSE `/stream`) o WebSockets. *(Resp: Diego M., Cristian C. | Fecha límite: 26/09)*

####  Squad Cloud & OCI Always Free
- [ ] **Verificación de Tenancy:** Tenancy activa de Oracle Cloud Infrastructure en capa gratuita Always Free. *(Resp: Alexis P., Joaquín R. | 21/09)*
- [ ] **Aprovisionamiento de Buckets:** Creación de buckets `nuevamente-raw-sources` y `nuevamente-generated-content`. *(Resp: Alexis P., Joaquín R. | Fecha límite: 25/09)*
- [ ] **Cliente OCI SDK Python:** Implementación de funciones base en `oci_service.py` (upload/download de objetos). *(Resp: Alexis P., Joaquín R. | Fecha límite: 26/09)*
- [ ] **Alarma de Presupuesto ($0.00 USD):** Configuración de Budget Alert en consola OCI para blindaje de coste cero. *(Resp: Alexis P., Joaquín R. | Fecha límite: 27/09)*

####  Squad Frontend & UX/UI
- [ ] **Scaffolding de Aplicación Web:** Configuración del proyecto base y sistema de tokens de diseño. *(Resp: Karen G., Cristian C. | 22/09)*
- [ ] **Zona de Carga (Drag & Drop):** Componente interactivo para subir archivos PDF, Markdown y TXT. *(Resp: Karen G. | Fecha límite: 25/09)*
- [ ] **Selectores Didácticos:** Controles para Perfil (Junior/Senior/Ejecutivo) y Formato (Flashcards/Quiz/Mapa). *(Resp: Cristian C. | Fecha límite: 25/09)*
- [ ] **Consumo de Mock Backend:** Conectar formulario al endpoint mock de Diego para validar flujo visual. *(Resp: Karen G., Cristian C. | Fecha límite: 27/09)*

####  Squad Gestión, QA & Gobernanza
- [x] **Repositorio y Políticas Git:** Rama `main` protegida, flujo `feature/*` y revisiones cruzadas. *(Resp: Jacqueline R. | 21/09)*
- [ ] **Tablero Kanban:** Configuración de columnas (Backlog, En Progreso, En Revisión, Hecho). *(Resp: Jacqueline R. | 22/09)*
- [ ] **Cierre de Sprint 1:** Revisión de DoD (Definition of Done) del Hito 1 (M-1). *(Resp: Jacqueline R. | Fecha límite: 27/09)*

---

###  SEMANA 2 (28 de Septiembre al 04 de Octubre, 2026) — Integración Core y Persistencia

- [ ] **[IA + Back] Integración Real:** Reemplazar el mock de FastAPI invocando `ejecutar_pipeline_adaptacion_async`. *(Resp: Diego M., Marcos H. | Fecha propuesta: 28 - 30 Sep)*
- [ ] **[Back + OCI] Persistencia Dual:** Subida automática del PDF original a `/raw_sources/` y del JSON a `/generated_content/`. *(Resp: Alexis P., Diego M. | Fecha propuesta: 29 Sep - 01 Oct)*
- [ ] **[Front] Tarjetas Flashcards 3D:** Animación fluida de flip 3D (frente con concepto, dorso con explicación y pista). *(Resp: Karen G. | Fecha propuesta: 29 Sep - 02 Oct)*
- [ ] **[Front] Módulo de Quizzes Interactivos:** Selección de opciones con feedback inmediato (verde/rojo) y explicación didáctica. *(Resp: Cristian C. | Fecha propuesta: 30 Sep - 03 Oct)*
- [ ] **[QA] Primera Prueba E2E en Terminal:** Ejecutar el flujo completo con el manual de Redes VCN y validar respuesta. *(Resp: Andy M., Fernando F. | Fecha propuesta: 02 - 04 Oct)*
- [ ] **Hito de Control 2 (M-2):** Pipeline procesa un documento real desde API, genera contenido y persiste en OCI Object Storage.

---

###  SEMANA 3 (05 al 11 de Octubre, 2026) —  HITO LÍMITE DEL MVP (Integración E2E)

- [ ] **[FullStack] Conexión UI a API Real:** Desacople definitivo de mocks; la UI consume directamente el endpoint FastAPI. *(Resp: Karen G., Diego M. | Fecha propuesta: 05 - 07 Oct)*
- [ ] **[Front + Back] Telemetría en Vivo:** Stepper interactivo de 5 fases alimentado por SSE o WebSockets. *(Resp: Cristian C., Diego M. | Fecha propuesta: 06 - 08 Oct)*
- [ ] **[Front + IA] Renderizador de Mapas Mentales:** Visualizador dinámico de sintaxis Mermaid.js con controles de zoom y pan. *(Resp: Cristian C., Marcos H. | Fecha propuesta: 07 - 09 Oct)*
- [ ] **[QA] Auditoría de Fidelidad Fáctica:** Verificación de anclaje $\ge 0.85$ y ausencia de alucinaciones en los 3 manuales. *(Resp: Andy M. | Fecha propuesta: 09 - 11 Oct)*
- [ ] **Hito de Control 3 (M-3):** MVP completo funcionando. Un usuario carga un documento, ve el avance en vivo y estudia en los 3 formatos.

---

###  SEMANA 4 (12 al 18 de Octubre, 2026) — Certificación de Casos, Nube y Pitch

- [ ] **[Cloud] Despliegue en OCI Compute VM (Opcional Always Free):** Contenedor Docker con `docker-compose.yml` en instancia Linux OCI. *(Resp: Alexis P., Joaquín R. | Fecha propuesta: 12 - 14 Oct)*
- [ ] **[QA + IA] Certificación Oficial de los 3 Casos:**
  - [ ] Caso A: Manual VCN en OCI para perfil **Junior** (Flashcards).
  - [ ] Caso B: Manual JWT & Seguridad para perfil **Senior** (Quiz de Arquitectura).
  - [ ] Caso C: Manual Microservicios para perfil **Ejecutivo** (Mapa Mental Mermaid). *(Resp: Andy M., Marcos H. | Fecha propuesta: 13 - 15 Oct)*
- [ ] **[Front] Exportador de Contenidos:** Botones de descarga en JSON, Markdown y SVG del mapa mental. *(Resp: Karen G. | Fecha propuesta: 14 - 16 Oct)*
- [ ] **[Comms] Guion Técnico del Video Pitch:** Redacción del guion segundo a segundo (3 a 4 minutos). *(Resp: Cristian M., Jacqueline R. | Fecha propuesta: 15 - 17 Oct)*
- [ ] **Hito de Control 4 (M-4):** 3 casos oficiales certificados y listos para la grabación de la demo.

---

###  SEMANA 5 (19 al 24 de Octubre, 2026) — Code Freeze y Entrega Final

- [ ] **Code Freeze Riguroso:** Congelamiento de código y fusión final de ramas `develop` $\rightarrow$ `main`. *(Resp: Todo el equipo | Fecha propuesta: 20 Oct)*
- [ ] **Prueba de Instalación en Limpio:** Clonado y ejecución en un entorno virgen siguiendo el `README.md`. *(Resp: Jacqueline R., Andy M. | Fecha propuesta: 21 Oct)*
- [ ] **Grabación y Edición del Video Pitch:** Captura de pantalla de la app en vivo + voz en off + subtítulos. *(Resp: Cristian M., Karen G. | Fecha propuesta: 21 - 22 Oct)*
- [ ] **Revisión de Checklist de Rúbrica Alura ONE:** Validación punto por punto de los requisitos obligatorios del Hackathon. *(Resp: Jacqueline R. | Fecha propuesta: 23 Oct)*
- [ ] **Cierre de Entrega:** Registro formal de repositorio Git y enlace de video en la plataforma del Hackathon ONE. *(Resp: Jacqueline R., Marcos H. | Fecha límite: 24 Oct)*

---

##  4. Bitácora de Dudas y Acuerdos Inter-Equipos

Utiliza esta sección en las reuniones de sincronización para anotar acuerdos clave:

| Fecha | Squad Emisor | Squad Receptor | Pregunta / Bloqueo | Decisión o Acuerdo Alcanzado | Estado |
|---|---|---|---|---|:---:|
| 24/09/2026 | IA | Backend | ¿Cómo se consumirá la telemetría en FastAPI? | Pendiente respuesta de Diego (se recomienda SSE `/stream`) |  Pendiente |
| 24/09/2026 | IA | Data | ¿Cuándo estarán los PDFs de JWT y Microservicios? | Andy y Fernando los subirán a `data/raw/` antes del 26/09 |  En curso |
| 24/09/2026 | IA | Frontend | ¿Soporte nativo de `mermaid.js` para Mapas Mentales? | Confirmar con Cristian Cortés integración de la librería CDN |  Pendiente |
| 24/09/2026 | IA | Cloud | ¿Rutas exactas de los buckets OCI Always Free? | Alexis confirmará nombres exactos en `oci_service.py` |  Pendiente |

# ESTRUCTURA DE DESGLOSE DEL TRABAJO (WBS) Y DEFINICIÓN DE TAREAS
## Proyecto: NuevaMente — Hackathon ONE (Oracle Next Education) & Alura Latam
**Equipo:** Cohorte G-10 (11 Integrantes / 4 Squads)  
**Propósito:** Desglosar formalmente todas las actividades, dependencias técnicas, responsables directos y criterios de aceptación para la ejecución del proyecto.

---

## 1. Matriz General de Desglose de Paquetes de Trabajo

```
1.0 NUEVAMENTE (SISTEMA INTEGRAL)
├── 1.1 Gestión y Gobernanza del Proyecto (Squad Gestión)
├── 1.2 Inteligencia Artificial y RAG (Squad IA)
├── 1.3 Backend y Servicios en la Nube (Squad Backend y OCI)
└── 1.4 Interfaz de Usuario y Experiencia Didáctica (Squad Frontend y UX)
```

---

## 2. Definición Detallada de Tareas por Squad e Integrante

### 2.1 Squad 1: Gestión y Delivery
**Integrantes:** 
* **Jacqueline Rioja:** Project Manager (Líder de Proyecto, Tablero Kanban, Dailies y Apoyo en IA/Data).
* **Cristian Esteban Maida:** *(Pendiente de asignación oficial el 21/09)* — Propuesta Técnica: Director de Comunicación Técnica, Arquitectura README C4, Storytelling y Video Pitch.

| Código | Tarea | Responsable | Entregable / Criterio de Aceptación | Dependencia |
|---|---|---|---|---|
| **GEST-01** | Configuración de Repositorio y Reglas Git | Jacqueline Rioja | Repositorio creado en GitHub, rama `main` protegida, requerimiento de 1 aprobación y `.gitignore` oficial aplicado. | Ninguna |
| **GEST-02** | Tablero Kanban y Sprint Backlog | Jacqueline Rioja | Tablero en GitHub Projects con columnas: *Backlog, To Do, In Progress, Review, Done* y tareas asignadas. | GEST-01 |
| **GEST-03** | Seguimiento Asíncrono Diario (Dailies) | Jacqueline Rioja | Mensaje diario de alineación en canal del equipo identificando avances y bloqueos entre squads. | GEST-02 |
| **GEST-04** | Control de Cambios y Aprobación de PRs | Jacqueline Rioja | Revisión formal y merge hacia `main` de las versiones consolidadas al final de cada sprint. | GEST-01 |
| **COMMS-01** | Arquitectura del `README.md` Principal | Cristian Maida *(propuesta)* | README corporativo con badges, descripción del problema, stack tecnológico y guía de despliegue. | GEST-01 |
| **COMMS-02** | Diagramación de Arquitectura C4 y Flujos | Cristian Maida *(propuesta)* | Diagramas en Mermaid de contexto, contenedores y flujo multi-agente integrados en la documentación. | IA-07, BE-03 |
| **COMMS-03** | Guion y Storyboard del Video Pitch | Cristian Maida *(propuesta)* | Estructura en 5 bloques (Problema, Solución, Demo en Vivo, OCI/LangGraph, Impacto) con tiempos delimitados. | QA-02 |
| **COMMS-04** | Producción, Grabación y Edición del Pitch | Cristian Maida *(propuesta)* | Video en alta definición de 3 a 4 minutos con voz en off, captura de pantalla interactiva y consola de OCI. | COMMS-03, FE-05 |

---

### 2.2 Squad 2: Inteligencia Artificial y Datos (IA / DATA)
**Integrantes:** 
* **Marcos Gael Hernández Cruz:** Ingeniero de IA (AI Engineer / Lead IA)
* **Fernando Falla:** Ingeniero de Datos (Data Engineer)
* **Jacqueline Rioja:** Apoyo en IA y Gestión de Datos
* **Andy Mijail Martinez Solis:** Analista de Datos y Control de Calidad de Prompts . Stack: ChatGPT, Claude Code, Azure, Discord, Google Meet.

| Código | Tarea | Responsable(s) | Dependencia | Entregable | Prioridad |
|---|---|---|---|---|:---:|
| **IA-01** | Ingesta y Normalización Documental | Fernando Falla | Ninguna | Módulo de extracción para PDF (`pymupdf`/`pypdf`), Markdown y TXT con tablas limpias. | **MVP** |
| **IA-02** | Chunking Contextual (800/150) | Fernando Falla | IA-01 | Segmentador semántico con separadores jerárquicos y cabeceras de metadatos. | **MVP** |
| **IA-03** | Vector Store ChromaDB / Embeddings | Fernando Falla | IA-02 | Base de conocimiento vectorial local con búsqueda por similitud de coseno. | **MVP** |
| **IA-04** | Curaduría de Manuales Técnicos Muestra | Andy Mijail / Fernando | Ninguna | 3 manuales técnicos reales limpios en `data/raw/` (VCN OCI, JWT, Microservicios). | **MVP** |
| **IA-05** | Especificación de Schemas Pydantic V2 | Marcos Gael | Ninguna | Archivo canónico `schemas.py` tipado (Flashcards, Quizzes, Mapas, Tutoriales, TL;DR). | **MVP** |
| **IA-06** | Catálogo de System Prompts Especializados | Marcos Gael | IA-05 | Prompts Few-Shot para los 4 perfiles y los 5 formatos didácticos. | **MVP** |
| **IA-07** | Orquestador Multi-Agente con LangGraph | Marcos Gael | IA-03, IA-06 | StateGraph con nodos Router, Retriever, Drafting y Formatter. | **MVP** |
| **IA-08** | Agente Crítico y Bucle de Autocorrección | Marcos Gael | IA-07 | Cálculo de `anclaje_fuente_score` con cota de convergencia ($\le 2$ iteraciones). | **MVP** |
| **IA-09** | Ejemplos Few-Shot con ChatGPT / Claude | Andy Mijail | IA-05 | Banco de preguntas/respuestas de referencia en lenguaje natural para calibrar prompts. | Importante |
| **IA-10** | Generador de Mapas Mentales (Mermaid/D3) | Marcos Gael | IA-07 | Generación determinista de sintaxis jerárquica para React Flow / Markmap. | Importante |
| **IA-11** | Pruebas Funcionales Manuales de Salida | Andy Mijail / Jacqueline | IA-07, BE-02 | Reporte matutino diario de coherencia y fidelidad fáctica contra los manuales. | **MVP** |
| **IA-12** | Registro y Matriz de Casos de Prueba (A, B, C) | Andy Mijail / Jacqueline | IA-04, GEST-02 | Matriz de validación oficial de los 3 escenarios lista para el Pitch y README. | **MVP** |

---

### 2.3 Squad 3: Backend (BE)
**Integrantes:** 
* **Diego Mendez:** Líder de Backend y Arquitectura API
* **Cristian Cortes:** Fullstack / Streaming SSE e Integración
* **Acuerdo de Contingencia:** Coordinación directa con Alexis y Joaquín para persistencia y despliegue OCI.

| Código | Tarea | Responsable(s) | Dependencia | Entregable | Prioridad |
|---|---|---|---|---|:---:|
| **BE-01** | Scaffolding de Proyecto FastAPI y CORS | Diego / Cristian C. | Ninguna | Backend ejecutable con Swagger activo en `/docs` y middlewares. | **MVP** |
| **BE-02** | Endpoint Mock para Desbloqueo de UI | Diego Mendez | IA-05, BE-01 | `POST /api/v1/adaptar-contenido` respondiendo mock JSON en $< 200\text{ms}$. | **MVP** |
| **BE-03** | Integración del Grafo LangGraph | Diego / Cristian C. / Marcos | IA-07, BE-02 | Endpoint real ejecutando el pipeline de IA de forma asíncrona. | **MVP** |
| **BE-04** | Integración con Servicio de Persistencia OCI | Diego / Alexis / Joaquín | OCI-03, BE-03 | Subida dual automática del PDF fuente y del JSON generado a OCI. | **MVP** |
| **BE-05** | Emisión de Telemetría Server-Sent Events (SSE) | Cristian Cortes / Diego | BE-03 | `POST /api/v1/adaptar-contenido/stream` con eventos de fase para el Stepper. | Importante |
| **BE-06** | Pruebas de Integración y Validación de Errores | Diego / Alexis | BE-02, BE-03 | Suite de pruebas API con TestClient de FastAPI validando respuestas 200 y 422. | **MVP** |
| **BE-07** | Contenedorización con Docker / Compose | Alexis Perez / Cristian C. | BE-04 | `Dockerfile` y `docker-compose.yml` listos para ejecución local y nube. | Opcional |

---

### 2.4 Squad 4: Oracle Cloud Infrastructure (OCI)
**Integrantes:** 
* **Alexis Perez:** Especialista OCI
* **Joaquín Rojas Yaccuzzi:** Especialista OCI
* **Acuerdo de Contingencia:** Backend funcionará como respaldo de este squad para mantener el avance continuo del MVP.

| Código | Tarea | Responsable(s) | Dependencia | Entregable | Prioridad |
|---|---|---|---|---|:---:|
| **OCI-01** | Configuración de Tenancy Always Free y Claves | Alexis / Joaquín | Ninguna | Tenancy operativo, usuario de servicio, claves RSA y `.env.example` formalizado. | **MVP** |
| **OCI-02** | Aprovisionamiento de Bucket Object Storage | Alexis / Joaquín | OCI-01 | Bucket `nuevamente-contenidos-educativos` Always Free con carpetas estructuradas. | **MVP** |
| **OCI-03** | Módulo de Upload / Download con OCI SDK Python | Alexis / Joaquín | OCI-01, OCI-02 | Módulo `oci_service.py` con funciones `upload_source()` y `upload_json()`. | **MVP** |
| **OCI-04** | Alerta Presupuestaria OCI Budgets ($0.01 USD) | Alexis / Joaquín | OCI-01 | Regla de alarma en facturación para garantizar $0.00 USD acumulados. | **MVP** |
| **OCI-05** | Preparación de Instancia Linux Always Free | Alexis / Joaquín | Definición Docker | VM Linux configurada en OCI Compute para despliegue opcional de la solución. | Opcional |

---

### 2.5 Squad 5: Frontend y Experiencia de Usuario (FE)
**Responsable Principal:** Karen Macarena González  
**Apoyo:** Cristian Cortes (desde Backend)

| Código | Tarea | Responsable(s) | Dependencia | Entregable | Prioridad |
|---|---|---|---|---|:---:|
| **FE-01** | Scaffolding de UI y Sistema de Diseño | Karen Gonzalez | Ninguna | Aplicación base (React o Streamlit) con tokens de diseño minimalista clásico. | **MVP** |
| **FE-02** | Zona de Carga de Archivos (Drag & Drop) | Karen Gonzalez | FE-01 | Componente interactivo que valida PDF, Markdown o TXT con preview de nombre. | **MVP** |
| **FE-03** | Panel de Filtros (Perfil, Formato, Nicho) | Karen Gonzalez | FE-01 | Selectores tipo tarjeta/píldora para los 4 perfiles y 5 formatos didácticos. | **MVP** |
| **FE-04** | Stepper de Telemetría en Vivo (5 Fases) | Karen Gonzalez | FE-01, BE-05 | Barra de progreso visual que refleja la fase activa de inferencia y OCI. | Importante |
| **FE-05** | Cliente de Conexión con FastAPI | Cristian Cortes / Karen | BE-02, FE-03 | Servicio HTTP que consume endpoint mock/real gestionando estados de carga. | **MVP** |
| **FE-06** | Visor de Tarjetas Interactivas (Flashcards 3D) | Cristian Cortes / Karen | IA-05, FE-05 | Tarjetas volteables en 3D con atajos de teclado, pistas y contador de tarjetas. | **MVP** |
| **FE-07** | Evaluador de Quizzes con Feedback Inmediato | Cristian Cortes / Karen | IA-05, FE-05 | 4 alternativas seleccionables, revelación de acierto/error y justificación técnica. | **MVP** |
| **FE-08** | Visor de Mapas Mentales (Markmap / React Flow) | Cristian Cortes / Karen | IA-10, FE-05 | Lienzo dinámico con ramas colapsables/expandibles y controles de zoom/pan. | Importante |
| **FE-09** | Panel de Auditoría de Calidad y Descargas | Karen Gonzalez / Cristian | BE-04, FE-05 | Visualización de `anclaje_fuente_score`, badge OCI y botones de exportación. | **MVP** |


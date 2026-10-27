# DIAGRAMAS VISUALES DE ARQUITECTURA, FLUJOS Y TRABAJO COLABORATIVO
## Proyecto: NuevaMente — Plataforma Educativa Inteligente
**Propósito:** Proporcionar una representación visual, esquemática y formal de la arquitectura integral, las dependencias entre los 4 squads, la secuencia de ejecución de extremo a extremo (E2E) y la máquina de estados de LangGraph.

---

## 1. Arquitectura General del Sistema (Modelo C4 - Nivel de Contenedores)

Este diagrama representa cómo se comunican las cuatro capas del sistema: el cliente de usuario, la API backend, el motor de Inteligencia Artificial y los servicios en la nube de Oracle.

```mermaid
flowchart TB
    subgraph CLIENTE["1. Capa de Presentación (Frontend & UX)"]
        UI["Interfaz Web React / Streamlit<br><i>Minimalismo Clásico Tecnológico</i>"]
        STEPPER["Componente de Telemetría en Vivo<br><i>Stepper de 5 Fases</i>"]
        CARDS["Visores Didácticos Interactivos<br><i>Flashcards 3D, Quizzes, Mapas Mermaid</i>"]
        UI --> STEPPER
        UI --> CARDS
    end

    subgraph API_GATEWAY["2. Capa de Servicios y Control (Backend)"]
        FASTAPI["Servidor FastAPI REST<br><i>main.py (Puerto 8000)</i>"]
        EP_SYNC["POST /api/v1/adaptar-contenido<br><i>(Endpoint Oficial Canónico)</i>"]
        EP_STREAM["POST /api/v1/adaptar-contenido/stream<br><i>(Server-Sent Events / Telemetría)</i>"]
        SCHEMAS["Contratos Pydantic V2<br><i>schemas.py (Tipado Estricto)</i>"]
        
        FASTAPI --> EP_SYNC
        FASTAPI --> EP_STREAM
        FASTAPI --> SCHEMAS
    end

    subgraph AI_ENGINE["3. Motor de IA y RAG (LangGraph Engine)"]
        EXTRACTOR["Extractor PyMuPDF / Markdown"]
        SPLITTER["RecursiveCharacterSplitter<br><i>(800 tokens / 150 overlap)</i>"]
        CHROMA[("Base de Datos Vectorial<br>ChromaDB (Local)")]
        LANGGRAPH{"Orquestador Multi-Agente<br><b>LangGraph StateGraph</b>"}
        
        EXTRACTOR --> SPLITTER
        SPLITTER --> CHROMA
        CHROMA -.->|Contexto k=5| LANGGRAPH
    end

    subgraph CLOUD_OCI["4. Infraestructura en la Nube (Oracle Cloud Always Free)"]
        OCI_SDK["Cliente Python OCI SDK<br><i>Autenticación RSA Segura</i>"]
        BUCKET_RAW[("OCI Object Storage<br><i>/documentos-fuente/</i>")]
        BUCKET_JSON[("OCI Object Storage<br><i>/artefactos-generados/</i>")]
        BUDGETS["Alerta de Control de Costos<br><i>OCI Budgets: $0.01 USD</i>"]
        
        OCI_SDK --> BUCKET_RAW
        OCI_SDK --> BUCKET_JSON
    end

    subgraph LLM_PROVIDERS["5. Modelos de Lenguaje"]
        GEMINI["Google Gemini 1.5 Flash<br><i>(Nube - Modelo Oficial ONE)</i>"]
        OLLAMA["Ollama Local<br><i>(qwen2.5 / llama3.1 / hermes3)</i>"]
    end

    UI ==>|Petición HTTP / Form-Data| FASTAPI
    FASTAPI ==>|Invocación Asíncrona| LANGGRAPH
    FASTAPI -->|Persistencia Dual| OCI_SDK
    LANGGRAPH <==>|Inferencia y Structured Outputs| GEMINI
    LANGGRAPH <-.->|Ejecución Local Opcional| OLLAMA
    FASTAPI ==>|Eventos SSE / JSON Final| UI
```

---

## 2. Flujo de Colaboración Operativa entre los 4 Squads (Handshake Matrix)

Este diagrama clarifica exactamente qué genera cada squad y qué entrega al siguiente para garantizar que los 11 integrantes trabajen en sincronía y sin bloqueos:

```mermaid
flowchart LR
    subgraph S1["🟢 GESTIÓN Y DELIVERY"]
        JAC["Jacqueline Rioja (PM)<br>• Reglas Git main protegida<br>• Tablero Kanban<br>• Dailies"]
        MAIDA["Cristian Maida (Comms)<br>• README y C4<br>• Guion del Pitch<br>• Video Demo"]
    end

    subgraph S2["🔵 INTELIGENCIA ARTIFICIAL"]
        FER["Fernando Falla (Data)<br>• Extracción PyMuPDF<br>• Chunking 800/150<br>• ChromaDB"]
        MARCOS["Marcos Gael (AI Eng)<br>• LangGraph StateGraph<br>• Prompts 3 perfiles<br>• Agente Crítico"]
        ANDY["Andy Mijail (QA)<br>• 3 Manuales reales<br>• Matriz de Casos A,B,C<br>• Auditoría anclaje"]
    end

    subgraph S3["🟠 BACKEND Y OCI"]
        OCI_T["Alexis & Joaquin (OCI)<br>• Bucket Always Free<br>• oci_service.py<br>• Alarma $0.01"]
        BACK["Diego & Cristian C. (Back)<br>• FastAPI /adaptar-contenido<br>• Mock Server (Sem 1)<br>• Integración LangGraph"]
    end

    subgraph S4["🟣 FRONTEND Y UX"]
        KAREN["Karen Gonzalez (Front)<br>• UI Minimalista<br>• Drag & Drop PDF<br>• Stepper Telemetría"]
        CORTES["Cristian Cortes (FullStack)<br>• Tarjetas Flashcards 3D<br>• Quizzes con Feedback<br>• Mapas Mermaid.js"]
    end

    JAC -.->|Gobernanza y Sprints| S2
    JAC -.->|Gobernanza y Sprints| S3
    JAC -.->|Gobernanza y Sprints| S4

    FER -->|Vector Store + Contexto| MARCOS
    MARCOS -->|Borrador JSON| ANDY
    ANDY -->|Validación Fidelidad| MARCOS
    MARCOS ==>|Contrato Pydantic V2| BACK
    
    OCI_T ==>|Módulo oci_service.py| BACK
    BACK ==>|1. Mock JSON (Sem 1)<br>2. API Real (Sem 2)| CORTES
    
    KAREN -->|Maquetación UI| CORTES
    CORTES ==>|Producto Funcional E2E| MAIDA
    MAIDA -->|Video Pitch y Demo Grabada| JAC
```

---

## 3. Diagrama de Secuencia de Extremo a Extremo (E2E Execution)

Muestra la traza completa desde que un usuario sube un PDF en el navegador hasta que se renderizan las tarjetas/quizzes y se confirma el guardado en Oracle Cloud:

```mermaid
sequenceDiagram
    autonumber
    actor Usuario as Estudiante / Docente
    participant UI as Frontend (React / Streamlit)
    participant API as FastAPI Backend
    participant Ingest as PyMuPDF + Chunking
    participant Vector as ChromaDB Vector Store
    participant Graph as LangGraph Multi-Agente
    participant LLM as Google Gemini 1.5 Flash
    participant OCI as OCI Object Storage Always Free

    Usuario->>UI: 1. Sube PDF + Selecciona Perfil ("Junior") y Formato ("Flashcards")
    UI->>API: 2. POST /api/v1/adaptar-contenido/stream (Multipart Form)
    
    API-->>UI: Evento SSE [1/5]: "Extrayendo y normalizando texto..."
    API->>Ingest: Extrae texto y añade metadatos (pág, sección)
    Ingest-->>API: Fragmentos limpios
    
    API-->>UI: Evento SSE [2/5]: "Indexando fragmentos en base vectorial..."
    API->>Vector: Genera embeddings y almacena chunks (ChromaDB)
    Vector-->>API: Vector Store listo
    
    API-->>UI: Evento SSE [3/5]: "LangGraph redactando contenido contextualizado..."
    API->>Graph: Inicia StateGraph con parámetros del usuario
    Graph->>Graph: Query Builder traduce el 'Formato' a búsqueda semántica (F1)
    Graph->>Vector: Consulta k=5 fragmentos usando la Query Pedagógica
    Vector-->>Graph: Chunks con evidencia
    Graph->>LLM: Invocación con Few-Shot + Role Prompting (Nicho inyectado)
    LLM-->>Graph: Borrador pedagógico preliminar
    
    API-->>UI: Evento SSE [4/5]: "Agente Crítico: Auditando anclaje fáctico..."
    Graph->>Graph: QualityCriticAgent calcula anclaje_fuente_score
    alt Score < 0.85 e iteraciones < 2
        Graph->>LLM: Auto-corrección: reescribir afirmaciones no sustentadas
        LLM-->>Graph: Borrador corregido
    else Score < 0.85 e iteraciones == 2
        Graph-->>API: Error 422 (Contexto Insuficiente / Falla de Grounding)
        API-->>UI: Cierra conexión con HTTP 422
    end
    Graph-->>API: JSON estructurado validado con Pydantic V2
    
    API-->>UI: Evento SSE [5/5]: "Persistiendo en OCI Object Storage..."
    par Guardar Documento Original
        API->>OCI: Sube PDF a /documentos-fuente/
        OCI-->>API: Confirmación upload (HTTP 200)
    and Guardar JSON Generado
        API->>OCI: Sube JSON a /artefactos-generados/
        OCI-->>API: Objeto id: vcn-junior-001.json
    end
    
    API-->>UI: Evento Final: "Completado" + Payload JSON Canónico
    UI->>Usuario: Renderiza Tarjetas 3D interactivas con pistas y badge de OCI verificado
```

---

## 4. Máquina de Estados del Grafo Multi-Agente (LangGraph State Machine)

Detalla el ciclo interno de los agentes, la evaluación del anclaje y el límite matemático de reintentos para garantizar fiabilidad (ISO/IEC 25010):

```mermaid
stateDiagram-v2
    [*] --> IngestionState: Recepción de Solicitud y Parámetros
    
    IngestionState --> RouterState: Parámetros tipados
    note right of RouterState
        RouterAgent selecciona directrices:
        - Perfil (Junior vs Senior vs Ejecutivo)
        - Formato (Flashcards, Quizzes, Mapas)
        - Nicho (Fintech, Salud, General)
    end note

    RouterState --> RetrievalState: Plan de Búsqueda
    note right of RetrievalState
        RetrievalAgent formula consultas semánticas.
        Recupera top-k chunks de ChromaDB (umbral >= 0.75).
    end note

    RetrievalState --> DraftingState: Chunks con Metadatos
    note right of DraftingState
        PedagogicalDraftingAgent genera borrador
        utilizando Few-Shot Prompting.
    end note

    DraftingState --> QualityCriticState: Borrador Generado
    note right of QualityCriticState
        QualityCriticAgent calcula:
        Score = Afirmaciones Justificadas / Total
    end note

    state QualityCriticState <<choice>>
    QualityCriticState --> SelfCorrectionLoop: Score < 0.85 Y reintentos < 2
    QualityCriticState --> OutputFormattingState: Score >= 0.85
    QualityCriticState --> Error422State: Score < 0.85 Y reintentos == 2

    SelfCorrectionLoop --> DraftingState: Reporte de discrepancias fácticas
    note right of SelfCorrectionLoop
        Incrementa contador iteraciones (+1).
        Instruye al redactor a purgar
        afirmaciones no documentadas.
    end note

    note left of Error422State
        Contexto Insuficiente.
        Fallo de Grounding.
    end note

    OutputFormattingState --> OCIPersistenceState: Diccionario Validado
    note right of OutputFormattingState
        OutputFormattingAgent fuerza conformidad
        estricta con Pydantic V2.
    end note

    OCIPersistenceState --> [*]: Paquete Educativo Listo
    Error422State --> [*]: Rechazo (HTTP 422)
```

---

## 5. Estrategia de Ramas Git y Pipeline de Integración Continua (CI/CD)

Muestra cómo se integran las ramas de los 11 desarrolladores de forma segura hacia la rama de producción `main`:

```mermaid
gitGraph
    commit id: "Init Repo" tag: "v0.1.0"
    branch develop
    checkout develop
    commit id: "setup: carpetas base"
    
    branch feat/ia-langgraph
    checkout feat/ia-langgraph
    commit id: "feat(ia): nodos router y retriever"
    commit id: "feat(ia): nodo critico y loop"
    checkout develop
    merge feat/ia-langgraph id: "PR #1 (IA Aprobado)"
    
    branch feat/backend-fastapi
    checkout feat/backend-fastapi
    commit id: "feat(api): mock server endpoint"
    commit id: "feat(oci): servicio oci-sdk"
    checkout develop
    merge feat/backend-fastapi id: "PR #2 (Back Aprobado)"
    
    branch feat/frontend-cards
    checkout feat/frontend-cards
    commit id: "feat(ui): selector y flashcards 3D"
    commit id: "feat(ui): mapas mermaid y stepper"
    checkout develop
    merge feat/frontend-cards id: "PR #3 (Front Aprobado)"
    
    checkout main
    merge develop id: "Release MVP v1.0.0" tag: "v1.0.0"
```

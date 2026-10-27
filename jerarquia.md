graph TD
    %% Nivel 1: Liderazgo Técnico
    TL["<b>TECH LEAD & ARQUITECTO GLOBAL</b><br/>👑 Marcos Gael Hernández Cruz 🇲🇽<br/><i>Dirección técnica integral, estándares y arquitectura de IA</i>"]

    %% Nivel 2: Gestión y Leads de Squads
    PM["<b>PROJECT MANAGEMENT & GOBERNANZA</b><br/>📋 Jacqueline Rioja 🇨🇴<br/><i>Kanban, Dailies, Control de PRs y Calidad</i>"]
    LEAD_IA["<b>SQUAD IA & DATOS</b><br/>🧠 Marcos Gael 🇲🇽 (Lead IA)"]
    LEAD_BE["<b>SQUAD BACKEND</b><br/>⚙️ Diego Mendez 🇨🇱 (Backend Lead)"]
    LEAD_CLOUD["<b>SQUAD CLOUD (OCI)</b><br/>☁️ Alexis Perez 🇦🇷 & Joaquín Rojas 🇦🇷"]
    LEAD_FE["<b>SQUAD FRONTEND & UX</b><br/>🎨 Karen Gonzalez 🇦🇷 (Frontend Lead)"]
    COMMS["<b>COMUNICACIÓN TÉCNICA & PITCH</b><br/>📢 Cristian Esteban Maida 🇨🇱"]

    %% Conexiones de Liderazgo
    TL --> PM
    TL --> LEAD_IA
    TL --> LEAD_BE
    TL --> LEAD_CLOUD
    TL --> LEAD_FE
    TL --> COMMS

    %% Nivel 3: Miembros por Squad
    subgraph S1["Squad IA & Datos"]
        M_MARCOS["Marcos Gael 🇲🇽<br/><i>AI Engineer (LangGraph / Prompts)</i>"]
        M_FERNANDO["Fernando Falla 🇨🇴<br/><i>Data Engineer (PyMuPDF / ChromaDB)</i>"]
        M_ANDY["Andy Mijail Martinez 🇲🇽<br/><i>Data Analyst & Prompt QA</i>"]
        M_JACQ["Jacqueline Rioja 🇨🇴<br/><i>Gobernanza de Datos & Soporte</i>"]
    end

    subgraph S2["Squad Backend & Cloud"]
        M_DIEGO["Diego Mendez 🇨🇱<br/><i>FastAPI, Endpoints, Mocks, CORS</i>"]
        M_CRISTIAN_C["Cristian Cortes 🇦🇷<br/><i>Fullstack, SSE Streaming, API Client</i>"]
        M_ALEXIS["Alexis Perez 🇦🇷<br/><i>DevOps, Docker, OCI Budgets</i>"]
        M_JOAQUIN["Joaquín Rojas Yaccuzzi 🇦🇷<br/><i>OCI Object Storage & Python SDK</i>"]
    end

    subgraph S3["Squad Frontend & UX"]
        M_KAREN["Karen Macarena Gonzalez 🇦🇷<br/><i>UI/UX, Tokens, Stepper, Layout</i>"]
        M_CORTES_FE["Cristian Cortes 🇦🇷<br/><i>Flashcards 3D, Quizzes, Mermaid</i>"]
    end

    subgraph S4["Gestión y Comunicación"]
        M_MAIDA["Cristian Esteban Maida 🇨🇱<br/><i>README C4, Storyboard y Video Pitch</i>"]
        M_JACQ_PM["Jacqueline Rioja 🇨🇴<br/><i>Seguimiento de Sprints y Bloqueos</i>"]
    end

    %% Conexiones hacia miembros
    LEAD_IA --> M_MARCOS
    LEAD_IA --> M_FERNANDO
    LEAD_IA --> M_ANDY
    LEAD_IA --> M_JACQ

    LEAD_BE --> M_DIEGO
    LEAD_BE --> M_CRISTIAN_C
    LEAD_CLOUD --> M_ALEXIS
    LEAD_CLOUD --> M_JOAQUIN

    LEAD_FE --> M_KAREN
    LEAD_FE --> M_CORTES_FE

    COMMS --> M_MAIDA
    PM --> M_JACQ_PM

    %% Estilos
    classDef leadStyle fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef squadStyle fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#e2e8f0;

    class TL,PM,LEAD_IA,LEAD_BE,LEAD_CLOUD,LEAD_FE,COMMS leadStyle;
    class M_MARCOS,M_FERNANDO,M_ANDY,M_JACQ,M_DIEGO,M_CRISTIAN_C,M_ALEXIS,M_JOAQUIN,M_KAREN,M_CORTES_FE,M_MAIDA,M_JACQ_PM squadStyle;
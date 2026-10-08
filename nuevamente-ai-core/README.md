# 🧠 NuevaMente AI Core — Motor Inteligente de Adaptación Educativa
**Hackathon:** ONE (Oracle Next Education) & Alura Latam — Cohorte G-10  
**Squad:** Inteligencia Artificial y Datos  
**Líder de Squad:** Marcos Gael Hernández Cruz  
**Integrantes:** Marcos Gael (AI Eng), Fernando Falla (Data Eng), Andy Mijail (Data Analyst / Prompt QA), Jacqueline Rioja (PM / Calidad)

---

## 📌 Descripción del Proyecto
Este repositorio contiene el **núcleo de inteligencia artificial** de **NuevaMente**. El sistema procesa documentación técnica densa (PDF, Markdown, TXT) y genera de forma autónoma materiales educativos altamente personalizados para tres perfiles de audiencia:
1. **Junior:** Conceptos clave con analogías del mundo real y código procedural sin tecnicismos intimidantes.
2. **Senior:** Arquitectura de software, evaluación de trade-offs, escalabilidad, resiliencia y seguridad.
3. **Ejecutivo:** Visión estratégica, retorno de inversión (ROI), impacto operativo y resúmenes TL;DR.

El pipeline orquesta un sistema multi-agente en **LangGraph** con un bucle de auditoría crítica que garantiza un score de anclaje fáctico $\ge 0.85$, mitigando alucinaciones conceptuales.

---

## 🏗️ Estructura del Repositorio

```text
nuevamente-ai-core/
├── data/
│   ├── raw/                  # Manuales técnicos originales (.pdf, .md, .txt)
│   └── processed/            # Fragmentos limpios y serializados
├── src/
│   ├── ai/
│   │   ├── config.py         # Factoría desacoplada de LLMs (Gemini / Groq)
│   │   ├── schemas.py        # Modelos Pydantic V2 de contratos y validación
│   │   ├── state.py          # Definición del TypedDict del StateGraph
│   │   ├── ingestion/
│   │   │   ├── extractor.py  # Extracción documental con PyMuPDF (fitz)
│   │   │   └── chunker.py    # RecursiveCharacterTextSplitter contextual (800/150)
│   │   ├── rag/
│   │   │   └── vectorstore.py# Almacén vectorial local en ChromaDB
│   │   ├── prompts/
│   │   │   ├── perfiles.py   # Prompts calibrados para Junior, Senior y Ejecutivo
│   │   │   └── formatos.py   # Few-shot templates (Flashcards, Quizzes, Mermaid)
│   │   ├── agents/
│   │   │   ├── analizador.py # Extracción de conceptos clave del contexto
│   │   │   ├── creador.py    # Generación con salida estructurada Pydantic V2
│   │   │   ├── critico.py    # Evaluación fáctica (anclaje_fuente_score >= 0.85)
│   │   │   └── ensamblador.py# Empaquetado final de respuesta
│   │   ├── graph.py          # StateGraph de LangGraph compilado
│   │   └── pipeline.py       # API pública (ejecutar_pipeline_adaptacion / _async)
├── tests/
│   └── test_ai_pipeline.py   # Suite de pruebas automatizadas con Pytest (9 tests)
├── HANDOVER_BACKEND.md       # Guía de integración para FastAPI (telemetría / async)
├── run_demo_local.py         # Demostración interactiva en terminal
├── requirements.txt          # Dependencias fijadas del proyecto
├── .env.example              # Plantilla de configuración de credenciales
└── README.md                 # Este documento
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Prerrequisitos
- Python 3.11 o superior instalado.
- Git instalado.

### 2. Clonar y crear entorno virtual
```bash
# Crear entorno virtual
python -m venv .venv

# Activar en Windows PowerShell:
.venv\Scripts\Activate.ps1

# O en Linux/macOS:
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copia la plantilla `.env.example` a `.env` y añade tus claves de API:
```bash
cp .env.example .env
```
Edita `.env` con tus credenciales de [Google AI Studio](https://aistudio.google.com/) o [Groq Cloud](https://console.groq.com/).

---

## 🧪 Ejecutar Demostración y Pruebas

### Ejecutar Demo en Consola:
```bash
python run_demo_local.py
```

### Ejecutar Suite de Pruebas Unitarias:
```bash
pytest tests/ -v -s
```

---

## 🤝 Contratos de Datos Canónicos

Este módulo expone funciones síncronas y asíncronas optimizadas para FastAPI:

```python
# Modo Asíncrono (Recomendado para FastAPI / Uvicorn)
from src.ai.pipeline import ejecutar_pipeline_adaptacion_async

resultado = await ejecutar_pipeline_adaptacion_async(
    documento_titulo="Introducción a Virtual Cloud Networks (VCN)",
    documento_contenido="Texto extraído del documento...",
    perfil="Junior",       # "Junior", "Senior", "Ejecutivo"
    formato="Flashcards",   # "Flashcards", "Quiz Interactivo", "Resumen Ejecutivo"
    nicho="General",
    nivel_detalle="Didactico",
    callback_telemetria=callback_sse # Opcional: callback sync o async para telemetría
)
```

```python
# Modo Síncrono (Scripts, CLI o tareas en background)
from src.ai.pipeline import ejecutar_pipeline_adaptacion

resultado = ejecutar_pipeline_adaptacion(
    documento_titulo="Introducción a Virtual Cloud Networks (VCN)",
    documento_contenido="Texto extraído del documento...",
    perfil="Junior",
    formato="Flashcards"
)
```

El objeto retornado es un `AdaptacionContenidoResponse` (validado por Pydantic V2) compatible 100% con los esquemas de FastAPI y los componentes de Frontend.

Para la guía de integración detallada con routers de FastAPI y emisión de telemetría por WebSockets / SSE, consulta [HANDOVER_BACKEND.md](HANDOVER_BACKEND.md).

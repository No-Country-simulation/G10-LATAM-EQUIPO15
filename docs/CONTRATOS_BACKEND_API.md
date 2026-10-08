# Contratos de API para Backend (Integración IA)

**Propósito:** Este documento define de forma estricta los contratos (Endpoints, Inputs, Outputs y Telemetría) que el equipo de Backend (FastAPI) debe implementar para integrarse con el motor de Inteligencia Artificial.

---

## 1. Endpoints Principales

El Backend debe exponer los siguientes endpoints bajo el prefijo `/api/v1/`:

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/v1/adaptacion/generar` | Procesa un documento RAW y genera el contenido educativo adaptado. |
| `GET` | `/api/v1/adaptacion/stream` | Endpoint Server-Sent Events (SSE) o WebSocket para emitir el progreso de IA en tiempo real. |

---

## 2. Entradas (Input: Petición del Cliente)

**Mecanismo:** `multipart/form-data`
Para preservar la fidelidad estructural (tablas, títulos, jerarquía), el Backend **NO** debe procesar el texto. Debe enviar el archivo original (RAW) junto con sus metadatos.

### Campos Requeridos (Form Data):

| Campo | Tipo | Obligatorio | Valores Permitidos / Default |
| :--- | :--- | :---: | :--- |
| `document_raw` | Binary/File | Sí | Archivo original (PDF, MD, DOCX, TXT). |
| `document_id` | String | Sí | Identificador único del documento. |
| `document_title` | String | Sí | Título del documento. |
| `document_mime_type`| String | Sí | Ej. `application/pdf`. |
| `request_id` | String | Sí | Identificador de trazabilidad e idempotencia. |
| `profile` | Enum | Sí | `"Junior"`, `"Senior"`, `"Ejecutivo"` |
| `format` | Enum | Sí | `"Flashcards"`, `"Quiz Interactivo"`, `"Resumen Ejecutivo"` |
| `nicho_sector` | Enum | Sí | `"Fintech"`, `"Salud"`, `"E-commerce"`, `"General"` |
| `nivel_detalle` | Enum | No | **Default:** `"Didactico"`. Opciones: `"Tecnico Intermedio"`, `"Exhaustivo"` |

---

## 3. Salidas (Output: Respuesta al Cliente)

El motor de IA devolverá un objeto estructurado. El Backend debe asegurar que la respuesta HTTP retorne este mismo esquema.

### Esquema JSON de Respuesta Exitoso (200 OK):
```json
{
  "contract_version": "2.0",
  "request_id": "req_123",
  "document_id": "doc_456",
  "status": "success",
  "codigo_respuesta": 200,
  "metadatos": {
    "perfil_aplicado": "Junior",
    "formato_generado": "Flashcards",
    "tiempo_estimado_estudio_minutos": 15,
    "conceptos_clave": ["VCN", "Subredes", "Routing"],
    "nicho_contexto": "General"
  },
  "contenido_adaptado": {
    "titulo": "Domina las VCN en OCI",
    "introduccion_contextualizada": "Como desarrollador Junior, entender redes es el primer paso...",
    "items": [
      {
        "frente": "¿Qué es una VCN?",
        "dorso": "Virtual Cloud Network: Tu red privada en la nube de Oracle.",
        "pista_didactica": "Piensa en una VCN como el terreno cercado donde construyes tu casa.",
        "categoria_dificultad": "Básico"
      }
    ]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.95,
    "claridad_pedagogica": "Alta",
    "observaciones": "Aprobado por el Agente Crítico",
    "clasificacion_fidelidad": "Alta"
  }
}
```

> **Responsabilidad de Persistencia OCI:** El motor de IA actúa como función pura. **Backend es el único responsable** de tomar este JSON de respuesta y subirlo al Object Storage de Oracle (OCI) utilizando el `document_id`.

---

## 4. Contrato de Telemetría (Server-Sent Events / Stream)

El Backend debe inyectar un callback para emitir eventos SSE hacia el Frontend.

| Fase | % Progreso Estimado | Acción Ejecutada |
| :--- | :--- | :--- |
| `EXTRACCION` | 20% | Se procesa y limpia el documento original. |
| `INDEXACION` | 40% | El Chunker y VectorStore indexan en ChromaDB. |
| `GENERACION` | 60% | LangGraph orquesta a los agentes (Analizador, Creador, Crítico). |
| `AUDITORIA` | 80% | Hermes 3 verifica vulnerabilidades. |
| `COMPLETADO` | 100% | Retorna el payload JSON final estructurado. |

---

## 5. Catálogo de Errores (Error Handling)

Si ocurre un fallo, el backend debe retornar el código HTTP exacto de esta lista:

| Código HTTP | Motivo (Status) | Acción Sugerida |
| :--- | :--- | :--- |
| **400 Bad Request** | Inyección XSS o Prompt Injection detectada por Pydantic/Hermes. | Rechazar petición automáticamente. |
| **422 Unprocessable** | **Contexto Insuficiente:** El documento no contiene información válida para el formato solicitado (falla de Grounding). | Pedir al usuario que suba un documento más detallado. |
| **500 Internal Error** | Fallo interno en la orquestación de LangGraph. | Reintentar la petición. |
| **503 Service Unav.** | Fallo por agotamiento de cuota (Rate Limits) en Gemini y Groq simultáneamente. | Notificar saturación temporal al cliente. |

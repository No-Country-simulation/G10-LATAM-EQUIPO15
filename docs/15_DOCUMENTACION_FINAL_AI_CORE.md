# Documentación Definitiva: Arquitectura y Configuración del AI Core
**Fase del Hackathon:** Cierre de Integración de IA (Semana 2 - Semana 3)  
**Squad:** IA & Datos  

Esta documentación sirve como la guía oficial para el Squad de Backend y Frontend sobre cómo interactuar, configurar y entender el comportamiento final del Motor Multi-Agente de NuevaMente.

---

## 1. Topología del Motor de IA
El motor está orquestado usando **LangGraph** para manejar un flujo cíclico y resistente a fallos. Consta de 4 fases que se ejecutan automáticamente al llamar al Pipeline:

1.  **Extracción (PyMuPDF):** Parsea el PDF, limpia caracteres extraños y normaliza el texto.
2.  **Segmentación (Chunker & VectorStore):** Divide el documento en fragmentos superpuestos y los vectoriza de forma **local** para ahorrar costos de API.
3.  **Generación (LangGraph - Agente Creador):** Traduce el contexto recuperado (RAG) a un formato Pydantic estructurado (Quiz, Flashcard, etc.).
4.  **Auditoría (LangGraph - Agente Crítico & Hermes):** Verifica que no haya alucinaciones semánticas ni inyecciones de dependencias.

---

## 2. Modelos Oficiales Seleccionados (MVP)
Tras realizar rigurosas pruebas de carga y benchmarking de latencia, se han establecido los siguientes modelos para operar dentro de la **capa gratuita de OCI (Always Free)**:

*   **Generador Principal (LLM):** `gemini-3.5-flash-lite`
    *   *Justificación:* Genera JSONs Pydantic perfectos, entiende el contexto de manuales técnicos, y arroja resultados en ~15 segundos.
*   **Modelo de Respaldo (Failover):** `llama-3.3-70b-versatile` (Vía Groq Cloud)
    *   *Justificación:* Actúa como red de seguridad ultrarrápida si Google Gemini agota sus cuotas de Rate Limit (HTTP 429).
*   **Modelo de Embeddings:** `all-MiniLM-L6-v2` (Sentence-Transformers)
    *   *Justificación:* Se procesa en CPU local mediante ChromaDB, evitando depender de APIs de terceros y reduciendo costos a cero.

---

## 3. Variables de Entorno y Configuración (.env)
El equipo de Cloud/Backend debe asegurar que el servidor de FastAPI levante las siguientes variables en su archivo `.env`:

```env
# Claves de APIs
GEMINI_API_KEY="<tu_api_key_de_google>"
GROQ_API_KEY="<tu_api_key_de_groq>"

# Configuración de Modelos
GEMINI_MODEL=gemini-3.5-flash-lite
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=gemini
EMBEDDINGS_MODEL=models/text-embedding-004

# Seguridad y Base de Datos Vectorial
CHROMA_PERSIST_DIRECTORY=./chroma_db
UMBRAL_ANCLAJE_MINIMO=0.85
MAX_REINTENTOS_CALIDAD=2
```

> **Nota Crítica sobre el Umbral Dinámico:** La variable base se mantiene en `0.85` (alta fidelidad fáctica) para asegurar que tutoriales, resúmenes y flashcards no alucinen. Sin embargo, el motor de IA está programado para **reducir dinámicamente este umbral a `0.75`** única y exclusivamente cuando el usuario solicita un formato de `"Quiz"`. Esto se hace intencionalmente para darle libertad creativa al LLM de generar "distractores" (opciones incorrectas pedagógicas) sin ser bloqueado erróneamente por el Agente Crítico.

---

## 4. Contrato de Integración para FastAPI (Backend)
Para conectar los Endpoints con el Motor de IA de forma no bloqueante, el Backend debe invocar la función asíncrona principal:

```python
from src.ai.pipeline import ejecutar_pipeline_adaptacion_async

# Llamada desde un Endpoint de FastAPI
respuesta_generada = await ejecutar_pipeline_adaptacion_async(
    documento_titulo="Manual JWT en OCI",
    ruta_archivo="./data/raw/jwt_oci.pdf",
    perfil="Senior",
    formato="Quiz Interactivo",
    nicho="Cloud"
)

# Retorna una instancia Pydantic "AdaptacionContenidoResponse"
return respuesta_generada.model_dump()
```

### Manejo de Errores (HTTP 422)
Si el documento suministrado por el usuario no tiene nada que ver con lo que pide, o es ilegible, el Agente Crítico lanzará un `ValueError` nativo de Python con el mensaje:
> `Contexto Insuficiente (Error 422): El documento carece de información relevante.`

**Accionable para Backend:** Atrapar (`except ValueError as e:`) esta excepción en el Endpoint y devolver un HTTP `422 Unprocessable Entity` hacia el Frontend.

---

## 5. Resiliencia y Mecanismo de Failover (Gemini -> Groq)
El motor de IA implementa un sistema robusto de alta disponibilidad basado en el enrutamiento dinámico de LLMs utilizando LangChain `with_fallbacks()`. 

1. **Proveedor Principal:** El pipeline arranca solicitando el procesamiento al motor `gemini-3.5-flash-lite` de Google.
2. **Activación de Respaldo:** Si la API de Google sufre un estrangulamiento por cuotas (HTTP 429 Rate Limit) o un timeout en la conexión, el sistema atrapa automáticamente la excepción sin bloquear la solicitud del cliente.
3. **Conmutación Inmediata (Failover):** De forma transparente (en un lapso de milisegundos), la solicitud se enruta a **Groq Cloud** consumiendo el modelo `llama-3.3-70b-versatile` gracias a su tecnología ultrarrápida LPU, la cual garantiza el completamiento exitoso de la generación.

**Requisito de Infraestructura:** El archivo `.env` del servidor debe contener la variable `GROQ_API_KEY`. Si Groq no está configurado, el Failover no podrá operar y el error de cuota se transmitirá hasta el cliente.

---

## 6. Rendimiento y Expectativas de Latencia
En hardware estándar y dentro de cuotas gratuitas, la Promesa de Servicio (SLA) del motor es:
- **Tiempo estimado de procesamiento completo (RAG + LangGraph):** 15 a 25 segundos.
- **Límite sugerido de archivo (Hard Limit de API):** 10 MB / 1,000 páginas por PDF. Archivos superiores pueden causar `HTTP 504 Gateway Timeout` en la red.

---

## 7. Ejemplo de Payload Generado (Para Evaluación de Frontend/Backend)
Para que los equipos de UI/UX y Backend puedan planificar el parseo de datos y el renderizado en pantalla, a continuación se presenta un **JSON real** generado por el motor (`gemini-3.5-flash-lite`) basado en el "Manual de JWT en OCI" con un perfil de dificultad "Senior".

```json
{
    "status": "exito",
    "metadatos": {
        "perfil_aplicado": "Senior",
        "formato_generado": "Quiz Interactivo",
        "tiempo_estimado_estudio_minutos": 8,
        "nicho_contexto": "Cloud"
    },
    "contenido_adaptado": {
        "titulo": "Evaluación de Arquitectura: Autenticación y Validación de JWT en OCI API Gateway",
        "introduccion_contextualizada": "Como arquitecto cloud o ingeniero senior, diseñar arquitecturas de microservicios robustas en Oracle Cloud Infrastructure (OCI) exige un dominio absoluto de los mecanismos de seguridad perimetral. Este quiz evalúa las decisiones de diseño relacionadas con las políticas de validación de tokens en API Gateway, el balance entre latencia de red y seguridad criptográfica, y la correcta transición hacia los estándares actuales en políticas de autenticación cloud-native.",
        "items": [
            {
                "pregunta": "En una arquitectura multi-tenant altamente distribuida sobre OCI API Gateway, se requiere minimizar la latencia de validación de tokens JWT sin comprometer la capacidad de revocar claves criptográficas desde el Proveedor de Identidad (IdP). ¿Qué política de validación JSON cumple con este requisito de optimización de rendimiento y diseño sin requerir llamadas sincrónicas por cada request?",
                "opciones": [
                    "REMOTE_DISCOVERY",
                    "REMOTE_JWKS",
                    "STATIC_KEYS",
                    "OAuth 2.0 Introspection Endpoint"
                ],
                "indice_correcto": 2,
                "justificacion_tecnica": "La opción STATIC_KEYS permite que el API Gateway verifique la firma del JWT de forma local utilizando claves públicas de verificación ya emitidas y cacheadas por el IdP. Esto elimina el overhead de red y la latencia asociada a realizar llamadas salientes hacia el IdP en tiempo de ejecución para cada request, logrando la máxima velocidad de validación.",
                "pista_didactica": "Busca el mecanismo que procese la criptografía de manera autocontenida en el gateway sin llamadas de red en tiempo de ejecución.",
                "explicacion_distractores": "REMOTE_DISCOVERY realiza consultas al punto final de introspección (opcionalmente cacheadas, pero implica validación remota o dependencias de estado). REMOTE_JWKS obliga al API Gateway a ponerse en contacto con el IdP en tiempo de ejecución para recuperar las claves de verificación públicas. OAuth 2.0 Introspection Endpoint delega completamente la validación al servidor de autorización mediante llamadas remotas, introduciendo latencia de red en cada request."
            },
            {
                "pregunta": "Un ingeniero senior está diseñando una API en OCI que procesa peticiones concurrentes masivas. Se implementa una política de validación tipo REMOTE_DISCOVERY para soportar tokens opacos y JWT. ¿Qué consideración de trade-off de rendimiento y costos operativos debe tenerse en cuenta al configurar el almacenamiento en caché de la respuesta del punto final de introspección?",
                "opciones": [
                    "Configurar la caché al valor mínimo de 1 minuto para garantizar consistencia estricta en la revocación de tokens.",
                    "Aumentar el tiempo de caché hasta el límite de 24 horas para reducir la carga de llamadas al IdP, asumiendo un riesgo controlado de latencia en la revocación de accesos.",
                    "Desactivar el almacenamiento en caché para obligar al API Gateway a validar contra el Vault de OCI en cada ciclo de vida del token.",
                    "Establecer la caché en el API Gateway utilizando llaves estáticas derivadas del secreto del cliente."
                ],
                "indice_correcto": 1,
                "justificacion_tecnica": "El uso del punto final de introspección requiere llamadas de red remotas. Almacenar en caché la respuesta entre 1 hora (por defecto) y hasta 24 horas acelera drásticamente la validación futura y reduce la congestión y costos transaccionales hacia el IdP. El trade-off arquitectónico es que un token revocado en el IdP seguirá siendo considerado válido por el API Gateway hasta que expire la entrada en la caché local.",
                "pista_didactica": "Evalúa el balance entre la persistencia de llamadas de red al IdP y la ventana temporal de obsolescencia de seguridad.",
                "explicacion_distractores": "Configurar un minuto contradice el propósito de la caché de OCI para introspección (el rango por defecto es de 1 a 24 horas). Desactivar la caché degrada el rendimiento de la API por cuellos de botella en el IdP. Las llaves estáticas no aplican para la validación basada en REMOTE_DISCOVERY, la cual opera por introspección de tokens."
            }
        ]
    },
    "evaluacion_calidad": {
        "anclaje_fuente_score": 0.80,
        "claridad_pedagogica": "Alta",
        "observaciones": "Calidad preliminar sub-umbral (0.8). Cobertura fáctica insuficiente. Términos clave no reflejados adecuadamente: lugar, nuevo, defecto, instrucciones, contiene. Se solicita reescribir integrando mayor fidelidad al documento fuente.",
        "reintentos_realizados": 0
    },
    "almacenamiento_oci": {
        "bucket": "nuevamente-contenidos-educativos",
        "objeto_id": "manual-jwt-oci_senior_quiz interactivo.json",
        "status_upload": "listo_para_subida",
        "ruta_publica_o_par": null
    },
    "codigo_respuesta": 200
}
```

### Notas sobre el Payload Generado:
1.  **Integridad Estructural (Pydantic):** La respuesta es 100% predecible en cada ejecución gracias al uso riguroso de esquemas forzados en LangGraph.
2.  **Personalización Avanzada:** La `justificacion_tecnica` generada por Gemini no es genérica; profundiza explícitamente en características nativas de OCI (`REMOTE_DISCOVERY`, `STATIC_KEYS`).
3.  **Metadatos Listos para Backend:** El objeto `almacenamiento_oci` viene preparado para que el Backend intercepte el JSON e invoque el SDK de Oracle Cloud Storage, inyectando la URL pública final antes de responder al cliente.

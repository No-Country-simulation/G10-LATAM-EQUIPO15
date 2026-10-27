# Integración del Core de IA con FastAPI (Handover para Diego)

> **Handover histórico.** La integración consolidada usa Backend → servicio HTTP IA mediante multipart, con proceso supervisado y plazos acotados. Ver [Backend](../backend/README.md) y el [contrato v2.3](../docs/CONTRATOS/CONTRATO_BACKEND_IA.md). El ejemplo de importación directa y sus campos no describen la API pública actual.

¡Hola Diego!

El equipo de IA ha terminado de implementar y probar la versión asíncrona del pipeline de adaptación de contenido educativo. A continuación, te comparto los detalles para que puedas integrar este motor dentro de tus endpoints de FastAPI sin bloquear el event loop principal.

## ¿Qué hay de nuevo?

Hemos creado una nueva función nativamente asíncrona llamada `ejecutar_pipeline_adaptacion_async` en `src/ai/pipeline.py`. Esta función utiliza `.ainvoke()` por debajo para el grafo de LangGraph, asegurando un consumo eficiente de concurrencia.

### Ubicación del código
- **Archivo:** `src/ai/pipeline.py`
- **Función:** `ejecutar_pipeline_adaptacion_async`
- **Modelo de Respuesta:** `AdaptacionContenidoResponse` (definido en `src/ai/schemas.py`)

## Ejemplo de Integración en FastAPI

Puedes consumir el pipeline directamente en tu endpoint de la siguiente manera:

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import asyncio

# Importar el core de IA
from src.ai.pipeline import ejecutar_pipeline_adaptacion_async
from src.ai.schemas import AdaptacionContenidoResponse

router = APIRouter()

# Callback asíncrono para enviar telemetría al cliente (ej. WebSockets / SSE)
async def enviar_telemetria_ws(etapa: str, paso: int, progreso: int, mensaje: str):
    print(f"[{progreso}%] {etapa} (Paso {paso}): {mensaje}")
    # TODO: Aquí puedes emitir mensajes a través de un WebSocket o Server-Sent Events

@router.post("/api/v1/adaptacion", response_model=AdaptacionContenidoResponse)
async def adaptar_contenido_endpoint(
    documento_titulo: str = Form(...),
    perfil: str = Form("Junior"),
    formato: str = Form("Flashcards"),
    nicho: str = Form("General"),
    nivel_detalle: str = Form("Didactico"),
    archivo: UploadFile = File(None),
    documento_contenido: str = Form(None)
):
    # Validar que se reciba archivo o contenido
    if not archivo and not documento_contenido:
        raise HTTPException(status_code=400, detail="Debe proporcionar archivo o documento_contenido.")

    # Guardar el archivo en una ruta temporal si aplica (o puedes pasar documento_contenido)
    ruta_temporal = None
    if archivo:
        ruta_temporal = f"/tmp/{archivo.filename}"
        with open(ruta_temporal, "wb") as f:
            f.write(await archivo.read())
            
    # Ejecutar el motor asíncrono sin bloquear el event loop
    resultado = await ejecutar_pipeline_adaptacion_async(
        documento_titulo=documento_titulo,
        documento_contenido=documento_contenido,
        ruta_archivo=ruta_temporal,
        perfil=perfil,
        formato=formato,
        nicho=nicho,
        nivel_detalle=nivel_detalle,
        callback_telemetria=enviar_telemetria_ws  # <-- Importante para UX fluida
    )
    
    return resultado
```

## Notas Importantes

1. **Callbacks de Telemetría:** El parámetro `callback_telemetria` en `ejecutar_pipeline_adaptacion_async` ahora soporta funciones `async`. Te recomendamos engancharlo a un sistema de *Server-Sent Events (SSE)* o *WebSockets* para que el frontend pueda mostrar la barra de progreso mientras corre el agente.
2. **Dependencias:** Asegúrate de que las variables de entorno para los modelos LLM (ej. `GROQ_API_KEY`, o lo que estés usando para el modelo local de Hermes) estén configuradas en tu entorno de despliegue.
3. **Auditoría (Spec Kit):** Hemos instalado `GitHub Spec Kit` en la raíz del proyecto (`.agents/`). Esto nos ayudará a llevar la auditoría y control de diseño para futuras modificaciones del agente.

Si tienes alguna duda con el modelo de respuesta o la inyección de la telemetría, ¡avísame!

Atentamente,
**Marcos (AI Engineer)**

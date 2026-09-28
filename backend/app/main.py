from fastapi import FastAPI, status
from app.core.config import settings
from app.api.schemas import AdaptacionRequest, AdaptacionResponse
from app.api.mock_data import MOCK_ADAPTACION_RESPONSE

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs"
)

@app.get("/")
def read_root():
    return {"message": "API de NuevaMente en ejecución", "status": "ok"}


# ------------------------------------------------------------------
# Actividad 3 (BE-03): Endpoint Mock para Adaptación de Contenido
# ------------------------------------------------------------------
@app.post(
    f"{settings.API_V1_STR}/adaptar-contenido",
    response_model=AdaptacionResponse,
    status_code=status.HTTP_200_OK,
    summary="Adaptar contenido educativo (Mock)",
    description="Endpoint simulado para permitir pruebas de integración con Frontend."
)
def adaptar_contenido_mock(payload: AdaptacionRequest):
    """
    Recibe la solicitud con el documento y parámetros de adaptación,
    y retorna la estructura de respuesta canónica simulada.
    """
    # En esta fase mock devolvemos el JSON simulado validado contra el esquema
    return MOCK_ADAPTACION_RESPONSE
from fastapi import FastAPI
from app.core.config import settings
from app.api.schemas import AdaptacionRequest, AdaptacionResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",  # Interfaz Swagger UI
)

@app.get("/")
def read_root():
    return {"message": "API de NuevaMente en ejecución", "status": "ok"}

# Endpoint preliminar usando el modelo Pydantic
@app.post(f"{settings.API_V1_STR}/adaptar-contenido", response_model=AdaptacionResponse)
def adaptar_contenido(payload: AdaptacionRequest):
    # lógica del mock
    pass
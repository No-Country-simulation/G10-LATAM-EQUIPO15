from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",  # Interfaz Swagger UI
)

@app.get("/")
def read_root():
    return {"message": "API de NuevaMente en ejecución", "status": "ok"}
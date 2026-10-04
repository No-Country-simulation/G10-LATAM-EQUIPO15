import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "NuevaMente API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    IA_BASE_URL: str = os.getenv("IA_BASE_URL", "http://ia-http:8001")
    IA_HTTP_TIMEOUT_SECONDS: float = float(os.getenv("IA_HTTP_TIMEOUT_SECONDS", "600"))
    MAX_DOCUMENT_BYTES: int = int(os.getenv("MAX_DOCUMENT_BYTES", "10485760"))

    if IA_HTTP_TIMEOUT_SECONDS <= 0 or MAX_DOCUMENT_BYTES <= 0:
        raise ValueError("El timeout y el límite de documento deben ser positivos.")
    
    # OCI Configuration
    OCI_BUCKET_NAME: str = os.getenv("OCI_BUCKET_NAME", "nuevamente-contenidos-educativos")

settings = Settings()

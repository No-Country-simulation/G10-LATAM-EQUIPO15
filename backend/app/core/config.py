import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "NuevaMente API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    IA_BASE_URL: str = os.getenv("IA_BASE_URL", "http://ia-http:8001")
    IA_HTTP_TIMEOUT_SECONDS: float = float(os.getenv("IA_HTTP_TIMEOUT_SECONDS", "600"))
    MAX_DOCUMENT_BYTES: int = int(os.getenv("MAX_DOCUMENT_BYTES", "26214400"))

    if IA_HTTP_TIMEOUT_SECONDS <= 0 or MAX_DOCUMENT_BYTES <= 0:
        raise ValueError("El timeout y el límite de documento deben ser positivos.")
    
    # OCI Configuration
    OCI_BUCKET_NAME: str = os.getenv("OCI_BUCKET_NAME", "nuevamente-contenidos-educativos")
    _OCI_ENABLED_VALUE = os.getenv("OCI_STORAGE_ENABLED", "false").strip().lower()
    if _OCI_ENABLED_VALUE not in {"true", "false", "1", "0"}:
        raise ValueError("OCI_STORAGE_ENABLED debe ser true, false, 1 o 0.")
    OCI_STORAGE_ENABLED: bool = _OCI_ENABLED_VALUE in {"true", "1"}
    OCI_NAMESPACE: str = os.getenv("OCI_NAMESPACE", "").strip()
    OCI_REGION: str = os.getenv("OCI_REGION", "").strip()
    OCI_AUTH_MODE: str = os.getenv("OCI_AUTH_MODE", "api_key").strip()
    OCI_CONFIG_FILE: str = os.getenv("OCI_CONFIG_FILE", "/run/secrets/oci/config")
    OCI_CONFIG_PROFILE: str = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
    OCI_HTTP_TIMEOUT_SECONDS: float = float(os.getenv("OCI_HTTP_TIMEOUT_SECONDS", "10"))
    if OCI_STORAGE_ENABLED:
        if not OCI_NAMESPACE or not OCI_BUCKET_NAME.strip():
            raise ValueError("Para habilitar OCI se requieren namespace y bucket.")
        if OCI_AUTH_MODE not in {"api_key", "instance_principal"}:
            raise ValueError("OCI_AUTH_MODE debe ser api_key o instance_principal.")
        if not 0 < OCI_HTTP_TIMEOUT_SECONDS <= 30:
            raise ValueError("El timeout OCI debe estar entre 0 y 30 segundos.")
        if OCI_AUTH_MODE == "instance_principal" and not OCI_REGION:
            raise ValueError("Instance Principal requiere OCI_REGION.")

settings = Settings()

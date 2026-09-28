import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "NuevaMente API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # OCI Configuration
    OCI_BUCKET_NAME: str = os.getenv("OCI_BUCKET_NAME", "nuevamente-contenidos-educativos")

settings = Settings()
from app.api.schemas import AdaptacionResponse

MOCK_ADAPTACION_RESPONSE = {
    "status": "exito",
    "metadatos": {
        "perfil_aplicado": "Principiante",
        "formato_generado": "Flashcards",
        "tiempo_estimado_estudio_minutos": 5,
        "conceptos_clave": ["VCN", "Subredes", "Internet Gateway", "OCI"]
    },
    "contenido_adaptado": {
        "titulo": "Conceptos Básicos de Redes Virtuales en la Nube (VCN)",
        "introduccion_contextualizada": "Una VCN en Oracle Cloud Infrastructure es el equivalente a una red tradicional dentro de un centro de datos físico, pero totalmente definida por software.",
        "items": [
            {
                "frente": "¿Qué es una VCN?",
                "dorso": "Es una red privada y personalizable configurada en los centros de datos de Oracle Cloud.",
                "pista_didactica": "Piensa en ella como el perímetro de seguridad de tu propia infraestructura."
            },
            {
                "frente": "¿Qué función cumple una Subred (Subnet)?",
                "dorso": "Es una subdivisión de la VCN que permite agrupar e aislar recursos (como servidores o bases de datos).",
                "pista_didactica": "Es como repartir habitaciones dentro de un mismo edificio."
            }
        ]
    },
    "evaluacion_calidad": {
        "anclaje_fuente_score": 0.95,
        "claridad_pedagogica": "Alta - Lenguaje adaptado sin tecnicismos innecesarios.",
        "observaciones": "Respuesta mock para pruebas de integración con Frontend."
    },
    "almacenamiento_oci": {
        "bucket": "nuevamente-contenidos-educativos",
        "objeto_id": "mock_doc_12345.json",
        "status_upload": "simulado"
    }
}
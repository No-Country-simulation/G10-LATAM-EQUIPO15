from typing import List, Optional
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# 1. ESQUEMA DE ENTRADA (Request)
# -------------------------------------------------------------
class AdaptacionRequest(BaseModel):
    documento_titulo: str = Field(..., min_length=3, max_length=150, example="Introduccion a la Arquitectura de Redes VCN en OCI")
    documento_contenido: str = Field(..., min_length=50, example="La Virtual Cloud Network (VCN) es una red privada y personalizable...")
    perfil_destinatario: str = Field(..., example="Principiante")  # Principiante | Desarrollador Junior | Lider Tecnico | Gestor Ejecutivo
    formato_salida: str = Field(..., example="Flashcards")         # Flashcards | Quiz Interactivo | Guia Paso a Paso | Resumen Ejecutivo
    nicho_sector: str = Field("General", example="General")         # Fintech | Salud | E-commerce | General
    nivel_detalle: Optional[str] = Field("Didactico", example="Didactico")


# -------------------------------------------------------------
# 2. ESQUEMAS SECUNDARIOS / COMPONENTES DE SALIDA
# -------------------------------------------------------------
class ElementoDidactico(BaseModel):
    frente: str = Field(..., example="¿Qué es una VCN en Oracle Cloud?")
    dorso: str = Field(..., example="Es tu red virtual privada y personalizada dentro de la nube de Oracle.")
    pista_didactica: Optional[str] = Field(None, example="Piensa en ella como el terreno cercado donde residen tus servidores.")
    opciones: Optional[List[str]] = Field(None, description="Aplica para Quizzes")
    respuesta_correcta_indice: Optional[int] = Field(None, description="Aplica para Quizzes")

class MetadatosContenido(BaseModel):
    perfil_aplicado: str
    formato_generado: str
    tiempo_estimado_estudio_minutos: int
    conceptos_clave: List[str]

class ContenidoAdaptado(BaseModel):
    titulo: str
    introduccion_contextualizada: str
    items: List[ElementoDidactico]

class EvaluacionCalidad(BaseModel):
    anclaje_fuente_score: float = Field(..., ge=0.0, le=1.0)
    claridad_pedagogica: str
    observaciones: Optional[str] = None

class AlmacenamientoOCI(BaseModel):
    bucket: str
    objeto_id: str
    status_upload: str


# -------------------------------------------------------------
# 3. ESQUEMA DE SALIDA PRINCIPAL (Response)
# -------------------------------------------------------------
class AdaptacionResponse(BaseModel):
    status: str = Field("exito", example="exito")
    metadatos: MetadatosContenido
    contenido_adaptado: ContenidoAdaptado
    evaluacion_calidad: EvaluacionCalidad
    almacenamiento_oci: AlmacenamientoOCI
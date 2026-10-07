"""Contrato de transporte compatible con la respuesta actual de AI Core."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PerfilDestinatario(str, Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    EJECUTIVO = "Ejecutivo"


class FormatoSalida(str, Enum):
    FLASHCARDS = "Flashcards"
    QUIZ = "Quiz Interactivo"
    RESUMEN = "Resumen Ejecutivo"
    MAPA = "Mapa Mental"


class NichoSector(str, Enum):
    FINTECH = "Fintech"
    SALUD = "Salud"
    ECOMMERCE = "E-commerce"
    GENERAL = "General"


class ContratoIA(BaseModel):
    # Conserva campos adicionales del proveedor; Backend no genera ni
    # recalcula metadatos pedagógicos o evidencia de calidad.
    model_config = ConfigDict(extra="allow")


class FlashcardItem(ContratoIA):
    frente: str
    dorso: str
    pista_didactica: str | None = None
    categoria_dificultad: str | None = None


class QuizItem(ContratoIA):
    pregunta: str
    opciones: list[str] = Field(min_length=4, max_length=4)
    indice_correcto: int = Field(ge=0, le=3)
    justificacion_tecnica: str
    pista_didactica: str | None = None
    explicacion_distractores: str | None = None


class NodoMapaMental(ContratoIA):
    id: str
    etiqueta: str
    subnodos: list["NodoMapaMental"] = Field(default_factory=list)


class MapaMentalItem(ContratoIA):
    nodo_central: str
    descripcion_general: str
    arbol: list[NodoMapaMental] = Field(default_factory=list)
    codigo_mermaid: str | None = None


class ResumenEjecutivoItem(ContratoIA):
    tldr: str
    puntos_clave: list[str] = Field(default_factory=list)
    impacto_negocio: str
    recomendaciones: list[str] = Field(default_factory=list)


class MetadatosContenido(ContratoIA):
    perfil_aplicado: PerfilDestinatario
    formato_generado: FormatoSalida
    tiempo_estimado_estudio_minutos: int = Field(ge=1, le=180)
    conceptos_clave: list[str] = Field(min_length=1)
    nicho_contexto: NichoSector = NichoSector.GENERAL


class ContenidoAdaptado(ContratoIA):
    titulo: str
    introduccion_contextualizada: str
    items: list[FlashcardItem] | list[QuizItem] | MapaMentalItem | ResumenEjecutivoItem


class AdaptacionResponse(ContratoIA):
    status: Literal["exito", "success"]
    metadatos: MetadatosContenido
    contenido_adaptado: ContenidoAdaptado

    @model_validator(mode="after")
    def validar_formato_contenido(self):
        items = self.contenido_adaptado.items
        formato = self.metadatos.formato_generado
        if formato == FormatoSalida.FLASHCARDS:
            valid = isinstance(items, list) and all(isinstance(item, FlashcardItem) for item in items)
        elif formato == FormatoSalida.QUIZ:
            valid = isinstance(items, list) and all(isinstance(item, QuizItem) for item in items)
        elif formato == FormatoSalida.MAPA:
            valid = isinstance(items, MapaMentalItem)
        else:
            valid = isinstance(items, ResumenEjecutivoItem)
        if not valid:
            raise ValueError("El contenido no corresponde al formato declarado por IA.")
        return self


class ErrorDetail(BaseModel):
    codigo: str
    mensaje: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail

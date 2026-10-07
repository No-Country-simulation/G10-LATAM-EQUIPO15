"""
Nodo 4: Ensamblador y Formateador Final.
Construye y valida el objeto canónico AdaptacionContenidoResponse bajo los esquemas Pydantic V2.
"""

from typing import Any, Dict
from src.ai.state import EstadoPipelineAdaptacion
from src.ai.schemas import (
    AdaptacionContenidoResponse,
    MetadatosAprendizaje,
    PaqueteContenidoAdaptado,
    PerfilDestinatarioEnum,
    FormatoSalidaEnum,
    NichoSectorEnum
)


def nodo_ensamblador(state: EstadoPipelineAdaptacion) -> Dict[str, Any]:
    """
    Construye la respuesta final normalizada lista para ser retornada a Backend / Frontend.
    """
    borrador = state.get("borrador_contenido", {})
    perfil_str = state.get("perfil_destinatario", "Junior")
    formato_str = state.get("formato_salida", "Flashcards")
    nicho_str = state.get("nicho_sector", "General")
    titulo_doc = state.get("documento_titulo", "Documento")

    # Mapear a enums de forma segura
    try:
        perfil_enum = PerfilDestinatarioEnum(perfil_str)
    except ValueError:
        perfil_enum = PerfilDestinatarioEnum.JUNIOR

    # El formato determina la forma de 'items': si no es válido, no se etiqueta erróneamente.
    formato_enum = FormatoSalidaEnum(formato_str)

    try:
        nicho_enum = NichoSectorEnum(nicho_str)
    except ValueError:
        nicho_enum = NichoSectorEnum.GENERAL

    items_raw = borrador.get("items", [])

    # Tiempo estimado calculado sobre el contenido realmente generado.
    if formato_enum == FormatoSalidaEnum.FLASHCARDS:
        tiempo_calculado = len(items_raw) * 2
    elif formato_enum == FormatoSalidaEnum.QUIZ_INTERACTIVO:
        tiempo_calculado = len(items_raw) * 3
    elif formato_enum == FormatoSalidaEnum.GUIA_PASO_A_PASO and isinstance(items_raw, dict):
        tiempo_calculado = 5 + len(items_raw.get("pasos", [])) * 4
    elif formato_enum == FormatoSalidaEnum.MAPA_MENTAL and isinstance(items_raw, dict):
        tiempo_calculado = 3 + len(items_raw.get("arbol", [])) * 2
    else:
        tiempo_calculado = 5
    tiempo_calculado = max(1, min(180, tiempo_calculado))

    metadatos = MetadatosAprendizaje(
        perfil_aplicado=perfil_enum,
        formato_generado=formato_enum,
        tiempo_estimado_estudio_minutos=tiempo_calculado,
        conceptos_clave=state.get("conceptos_clave") or [titulo_doc],
        nicho_contexto=nicho_enum
    )

    if formato_enum == FormatoSalidaEnum.MAPA_MENTAL and isinstance(items_raw, dict):
        from src.ai.utils.mermaid import sanitizar_codigo_mermaid
        nodo_central = items_raw.get("nodo_central", titulo_doc)
        arbol = items_raw.get("arbol", [])
        # Mermaid se deriva siempre del árbol estructurado (fuente única de verdad).
        items_raw["codigo_mermaid"] = sanitizar_codigo_mermaid(
            codigo=None,
            nodo_central=nodo_central,
            arbol=arbol
        )

    paquete_contenido = PaqueteContenidoAdaptado(
        titulo=borrador.get("titulo") or f"{titulo_doc} para {perfil_enum.value}",
        introduccion_contextualizada=borrador.get("introduccion_contextualizada") or "",
        items=items_raw
    )

    respuesta = AdaptacionContenidoResponse(
        status="exito",
        metadatos=metadatos,
        contenido_adaptado=paquete_contenido
    )

    return {
        "paquete_final_json": respuesta.model_dump(),
        "status": "finalizado_exitosamente"
    }

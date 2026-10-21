"""Regresiones de prompts: ninguna instrucción debe empujar a generar contenido sin sustento."""

import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ai.agents.creador import nodo_creador
from src.ai.agents.critico import nodo_critico
from src.ai.prompts.formatos import INSTRUCCIONES_FORMATOS
from src.ai.prompts.perfiles import PROMPTS_SISTEMA_POR_PERFIL
from src.ai.schemas import FormatoSalidaEnum, PerfilDestinatarioEnum


@pytest.mark.parametrize("formato", list(FormatoSalidaEnum))
def test_formatos_no_exigen_cantidades_minimas(formato):
    instrucciones = INSTRUCCIONES_FORMATOS[formato].lower()
    # Un mínimo obliga a rellenar cuando el documento es breve.
    assert not re.search(r"entre \d+ y \d+", instrucciones)
    assert "siempre" not in instrucciones


def test_resumen_permite_omitir_impacto_y_recomendaciones():
    instrucciones = INSTRUCCIONES_FORMATOS[FormatoSalidaEnum.RESUMEN_EJECUTIVO]
    assert "no lo especifica" in instrucciones
    assert "lista vacía" in instrucciones


def test_pistas_son_opcionales():
    assert "Omítela" in INSTRUCCIONES_FORMATOS[FormatoSalidaEnum.FLASHCARDS]
    assert "siempre" not in PROMPTS_SISTEMA_POR_PERFIL[PerfilDestinatarioEnum.JUNIOR]


def test_senior_condiciona_trade_offs_a_la_fuente():
    prompt = PROMPTS_SISTEMA_POR_PERFIL[PerfilDestinatarioEnum.SENIOR]
    assert "trade-offs de rendimiento y costos solo cuando la fuente los mencione" in prompt


def test_creador_prohibe_datos_nuevos_en_ejemplos_de_nicho(monkeypatch):
    prompts = []

    class Estructurado:
        def __init__(self, schema):
            self.schema = schema

        def invoke(self, mensajes):
            prompts.append(mensajes[1].content)
            return self.schema(titulo="T", introduccion_contextualizada="I", items=[{"frente": "JWT", "dorso": "Token firmado."}])

    monkeypatch.setattr("src.ai.agents.creador.obtener_llm_adaptacion",
                        lambda **_: SimpleNamespace(with_structured_output=Estructurado))
    nodo_creador({
        "fragmentos_relevantes": [{"id": "F1", "contenido": "JWT usa firma para verificar integridad."}],
        "formato_salida": "Flashcards", "nicho_sector": "Fintech",
    })
    assert "no puede incluir cifras, porcentajes, normativas" in prompts[0]
    assert "son máximos" in prompts[0]


def _prompt_creador(monkeypatch, fragmentos):
    prompts = []

    class Estructurado:
        def __init__(self, schema):
            self.schema = schema

        def invoke(self, mensajes):
            prompts.append(mensajes[1].content)
            return self.schema(titulo="T", introduccion_contextualizada="I", items=[{"frente": "a", "dorso": "b"}])

    monkeypatch.setattr("src.ai.agents.creador.obtener_llm_adaptacion",
                        lambda **_: SimpleNamespace(with_structured_output=Estructurado))
    nodo_creador({"fragmentos_relevantes": fragmentos, "formato_salida": "Flashcards", "nicho_sector": "General"})
    return prompts[0]


def test_creador_pide_cubrir_todas_las_secciones(monkeypatch):
    prompt = _prompt_creador(monkeypatch, [
        {"id": "F1", "contenido": "1FN: valores atómicos.", "section": "Primera forma normal"},
        {"id": "F2", "contenido": "3FN: sin dependencias transitivas.", "section": "Tercera forma normal"},
    ])
    assert "SECCIONES DEL DOCUMENTO (cúbrelas todas" in prompt
    assert "- Primera forma normal\n- Tercera forma normal" in prompt


def test_creador_sin_titulos_pide_usar_todos_los_fragmentos(monkeypatch):
    prompt = _prompt_creador(monkeypatch, [{"id": "F1", "contenido": "a"}, {"id": "F2", "contenido": "b"}])
    assert "el documento tiene 2 fragmentos" in prompt
    assert "SECCIONES DEL DOCUMENTO" not in _prompt_creador(monkeypatch, [{"id": "F1", "contenido": "a", "section": "S"}])


def test_critico_no_acepta_datos_nuevos_como_didactica(monkeypatch):
    monkeypatch.delenv("UMBRAL_ANCLAJE_MINIMO", raising=False)
    juez = Mock()
    juez.invoke.return_value = SimpleNamespace(anclaje_fuente_score=0.9, critica_observaciones="ok")
    monkeypatch.setattr("src.ai.agents.critico.obtener_llm_critico",
                        lambda: SimpleNamespace(with_structured_output=lambda _schema: juez))
    nodo_critico({
        "fragmentos_relevantes": [{"id": "F1", "contenido": "JWT usa firma para verificar integridad."}],
        "borrador_contenido": {"items": [{"frente": "JWT", "dorso": "Token firmado.", "fuentes": ["F1"]}]},
        "formato_salida": "Flashcards",
    })
    prompt = juez.invoke.call_args.args[0][1].content
    assert "clasifícalo como 'no_respaldada', nunca como 'didactica'" in prompt

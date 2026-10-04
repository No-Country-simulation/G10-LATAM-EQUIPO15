"""Regresiones locales del contexto usado para evaluar fidelidad."""

import pytest

from src.ai.agents.critico import decidir_proximo_paso, nodo_critico


@pytest.fixture(autouse=True)
def evaluacion_real(monkeypatch):
    # Evitar la rama del score fijo habilitada por la suite anterior.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("UMBRAL_ANCLAJE_MINIMO", raising=False)


def test_contexto_vacio_no_se_aprueba_ni_provoca_excepcion():
    state = {
        "fragmentos_relevantes": [{"contenido": ""}, {"contenido": ""}],
        "documento_contenido": "",
        "borrador_contenido": {"items": ["afirmacion inventada sin respaldo"]},
        "contador_intentos": 1,
    }
    resultado = nodo_critico(state)
    assert resultado["anclaje_fuente_score"] == 0.0
    assert "Contexto Insuficiente" in resultado["critica_observaciones"]
    assert decidir_proximo_paso({**state, **resultado}) == "nodo_creador"


def test_fragmentos_con_contenido_permiten_evaluar_el_borrador():
    fuente = "autenticacion seguridad arquitectura microservicios"
    resultado = nodo_critico({
        "fragmentos_relevantes": [{"contenido": fuente}],
        "documento_contenido": "",
        "borrador_contenido": {"items": [fuente]},
    })
    assert resultado["anclaje_fuente_score"] >= 0.85


def test_separadores_vacios_permiten_usar_el_documento_de_respaldo():
    fuente = "autenticacion seguridad arquitectura microservicios"
    resultado = nodo_critico({
        "fragmentos_relevantes": [{"contenido": " "}, {"contenido": " "}],
        "documento_contenido": fuente,
        "borrador_contenido": {"items": [fuente]},
    })
    assert resultado["anclaje_fuente_score"] >= 0.85

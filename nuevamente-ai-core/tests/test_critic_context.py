"""Regresiones locales del contexto usado para evaluar fidelidad."""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from src.ai.agents.critico import decidir_proximo_paso, nodo_critico
from src.ai.agents.critico import EvaluacionFidelidad, VeredictoItem


@pytest.fixture(autouse=True)
def juez_simulado(monkeypatch):
    # Evitar la rama del score fijo habilitada por la suite anterior.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("UMBRAL_ANCLAJE_MINIMO", raising=False)
    juez = Mock()
    juez.invoke.return_value = SimpleNamespace(
        anclaje_fuente_score=0.9,
        critica_observaciones="El contenido está respaldado por la fuente.",
    )
    modelo = Mock()
    modelo.with_structured_output.return_value = juez
    proveedor = Mock(return_value=modelo)
    monkeypatch.setattr("src.ai.config.obtener_llm_adaptacion", proveedor)
    return proveedor, juez


@pytest.mark.parametrize("documento", ["", " \n\t "])
def test_contexto_vacio_no_se_aprueba_ni_provoca_excepcion(documento, juez_simulado):
    state = {
        "fragmentos_relevantes": [{"contenido": ""}, {"contenido": ""}],
        "documento_contenido": documento,
        "borrador_contenido": {"items": ["afirmacion inventada sin respaldo"]},
        "contador_intentos": 1,
    }
    resultado = nodo_critico(state)
    assert resultado["anclaje_fuente_score"] == 0.0
    assert "Contexto Insuficiente" in resultado["critica_observaciones"]
    assert decidir_proximo_paso({**state, **resultado}) == "nodo_creador"
    proveedor, juez = juez_simulado
    proveedor.assert_not_called()
    juez.invoke.assert_not_called()


@pytest.mark.parametrize("estados,score", [
    (["respaldada", "didactica"], 1.0),
    (["respaldada", "no_respaldada", "didactica"], 0.5),
    (["respaldada", "contradicha", "didactica"], 0.0),
    (["didactica"], 0.5),
])
def test_verdicts_determine_score_and_preserve_cited_source(juez_simulado, estados, score):
    _, juez = juez_simulado
    juez.invoke.return_value = EvaluacionFidelidad(
        veredictos=[VeredictoItem(
            item_id_o_nombre=f"Item {i}", afirmacion_analizada="JWT firmado",
            fuente_evaluada="F1", estado=estado,
        ) for i, estado in enumerate(estados)],
        anclaje_fuente_score=0.99,  # Debe prevalecer el cálculo sobre los veredictos.
        critica_observaciones="Revisión por afirmación.",
    )
    result = nodo_critico({
        "fragmentos_relevantes": [{"id": "F1", "contenido": "JWT usa firma para verificar integridad."}],
        "borrador_contenido": {"items": [{"frente": "JWT", "dorso": "Token firmado", "fuentes": ["F1"]}]},
    })
    assert result["anclaje_fuente_score"] == score
    assert all(v["fuente_evaluada"] == "F1" for v in result["veredictos_critico"])
    prompt = juez.invoke.call_args.args[0][1].content
    assert "F1" in prompt
    if "contradicha" in estados:
        assert "CONTRADICCIÓN" in result["critica_observaciones"]


def test_fragmentos_con_contenido_permiten_evaluar_el_borrador(juez_simulado):
    fuente = "autenticacion seguridad arquitectura microservicios"
    resultado = nodo_critico({
        "fragmentos_relevantes": [{"contenido": fuente}],
        "documento_contenido": "",
        "borrador_contenido": {"items": [fuente]},
    })
    assert resultado["anclaje_fuente_score"] >= 0.85
    _, juez = juez_simulado
    juez.invoke.assert_called_once()
    assert fuente in juez.invoke.call_args.args[0][1].content


def test_separadores_vacios_permiten_usar_el_documento_de_respaldo(juez_simulado):
    fuente = "autenticacion seguridad arquitectura microservicios"
    resultado = nodo_critico({
        "fragmentos_relevantes": [{"contenido": " "}, {"contenido": " "}],
        "documento_contenido": fuente,
        "borrador_contenido": {"items": [fuente]},
    })
    assert resultado["anclaje_fuente_score"] >= 0.85
    _, juez = juez_simulado
    assert fuente in juez.invoke.call_args.args[0][1].content


def test_contexto_vacio_se_rechaza_incluso_con_clave_de_pruebas(monkeypatch, juez_simulado):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_gemini_key")
    resultado = nodo_critico({
        "documento_titulo": "JWT en OCI",
        "fragmentos_relevantes": [],
        "documento_contenido": "",
        "borrador_contenido": {"items": ["afirmacion inventada"]},
    })
    assert resultado["anclaje_fuente_score"] == 0.0
    proveedor, _ = juez_simulado
    proveedor.assert_not_called()


def test_juez_rechaza_afirmaciones_sin_respaldo(juez_simulado):
    _, juez = juez_simulado
    juez.invoke.return_value = SimpleNamespace(
        anclaje_fuente_score=0.6,
        critica_observaciones="La fuente no respalda la afirmación sobre cifrado.",
    )
    state = {
        "fragmentos_relevantes": [{"contenido": "JWT describe autenticacion mediante tokens firmados"}],
        "borrador_contenido": {"items": ["JWT siempre cifra el contenido"]},
        "contador_intentos": 1,
    }
    resultado = nodo_critico(state)
    assert resultado["anclaje_fuente_score"] == 0.6
    assert "no respalda" in resultado["critica_observaciones"]
    assert decidir_proximo_paso({**state, **resultado}) == "nodo_creador"

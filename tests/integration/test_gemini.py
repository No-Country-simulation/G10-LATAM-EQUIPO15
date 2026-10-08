"""Comprobaciones de la cadena HTTP real; no importa ni simula el pipeline."""

import json
import os
import time
from pathlib import Path

import httpx
import pytest

if not os.environ.get("TEST_BACKEND_URL") or not os.environ.get("TEST_IA_URL"):
    pytest.skip("Ensayo real opcional: ejecutar scripts/probar-integracion.ps1 -Gemini", allow_module_level=True)

BACKEND = os.environ["TEST_BACKEND_URL"].rstrip("/")
IA = os.environ["TEST_IA_URL"].rstrip("/")
PHASE = os.environ.get("TEST_PHASE", "manual")
FORM = {"perfil_destinatario": "Junior", "formato_salida": "Flashcards", "nicho_sector": "General"}


@pytest.mark.parametrize("url,service", [(BACKEND, "backend"), (IA, "ia")])
def test_http_services_are_healthy(url, service):
    response = httpx.get(f"{url}/health", timeout=5)
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": service}


def test_backend_rejects_noncanonical_profile():
    response = httpx.post(
        f"{BACKEND}/api/v1/adaptar-contenido", timeout=5,
        data={**FORM, "perfil_destinatario": "Principiante"},
        files={"documento_original": ("ejemplo.txt", b"Texto tecnico")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "PARAMETROS_INVALIDOS"


def test_pdf_is_adapted_through_backend_and_real_gemini():
    document = Path("/fixtures/JWT en OCI.pdf")
    started = time.monotonic()
    with document.open("rb") as original:
        response = httpx.post(
            f"{BACKEND}/api/v1/adaptar-contenido",
            data=FORM, files={"documento_original": (document.name, original, "application/pdf")},
            timeout=float(os.environ.get("TEST_HTTP_TIMEOUT_SECONDS", "600")),
        )
    elapsed = round(time.monotonic() - started, 3)
    # Los resultados son privados: no contienen configuración ni credenciales.
    output = Path("/results")
    output.mkdir(exist_ok=True)
    result = {"fase": PHASE, "http_status": response.status_code, "duracion_segundos": elapsed}
    if response.status_code != 200:
        try:
            code = response.json().get("detail", {}).get("codigo")
            if isinstance(code, str) and code.isascii() and all(c.isupper() or c == "_" for c in code):
                result["codigo_publico"] = code
        except (ValueError, AttributeError):
            pass
    (output / f"resultado-{PHASE}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    assert response.status_code == 200, f"La adaptación falló con HTTP {response.status_code}; revisar los reportes locales del ensayo."
    payload = response.json()
    (output / f"respuesta-{PHASE}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    assert set(payload) == {"status", "metadatos", "contenido_adaptado", "evaluacion_calidad", "almacenamiento_oci", "codigo_respuesta"}
    assert payload["status"] == "exito"
    assert payload["codigo_respuesta"] == 200
    assert 0.85 <= payload["evaluacion_calidad"]["anclaje_fuente_score"] <= 1.0
    assert payload["almacenamiento_oci"]["status_upload"] in {"pendiente", "listo_para_subida"}
    assert payload["metadatos"]["perfil_aplicado"] == FORM["perfil_destinatario"]
    assert payload["metadatos"]["formato_generado"] == FORM["formato_salida"]
    content = payload["contenido_adaptado"]
    assert isinstance(content["titulo"], str) and content["titulo"].strip()
    assert isinstance(content["introduccion_contextualizada"], str) and content["introduccion_contextualizada"].strip()
    assert isinstance(content["items"], list) and content["items"]
    for item in content["items"]:
        for field in ("frente", "dorso"):
            assert isinstance(item[field], str) and item[field].strip()

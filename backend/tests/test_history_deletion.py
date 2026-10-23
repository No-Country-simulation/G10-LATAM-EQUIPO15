"""Borrado real de objetos en el transporte OCI controlado; sin credenciales ni red."""
import json

from fastapi.testclient import TestClient
import httpx
import pytest

from app.main import app
from app.services.ia_client import IAClient, get_ia_client
from test_history import generate, history_env, initialize
from test_ia_integration import payload
from test_oci_storage import sdk_factory, signing_key


def paths(result):
    ref = result["historial"]
    path = "/api/v1/documentos/" + ref["documento_id"]
    return path, path + "/adaptaciones/" + ref["adaptacion_id"]


def confirm(client, path):
    response = client.get(path + "/eliminacion")
    assert response.status_code == 200, response.text
    return response.json()


def remove(client, path, summary):
    return client.delete(path, headers={"If-Match": '"' + summary["version"] + '"'})


def test_eliminar_resultado_conserva_original_y_otras_adaptaciones(history_env):
    client, bucket, calls = history_env
    initialize(client)
    first, second = generate(client), generate(client, "Quiz Interactivo")
    path, adaptation = paths(first)
    artifact = first["almacenamiento_oci"]["objeto_id"]
    assert client.delete(adaptation).json() == {"eliminado": True}
    assert client.delete(adaptation).status_code == 200
    assert artifact not in bucket.objects
    assert client.get(adaptation).status_code == 404
    assert client.get(path + "/original").status_code == 200
    assert client.get(paths(second)[1]).status_code == 200
    assert len(client.get(path + "/adaptaciones").json()["adaptaciones"]) == 1
    assert len(calls) == 2


def test_json_compartido_solo_se_borra_con_la_ultima_referencia(history_env):
    client, bucket, _ = history_env
    initialize(client)
    first, second = generate(client), generate(client)
    artifact = first["almacenamiento_oci"]["objeto_id"]
    assert artifact == second["almacenamiento_oci"]["objeto_id"]
    assert client.delete(paths(first)[1]).status_code == 200
    assert artifact in bucket.objects
    assert client.get(paths(second)[1]).status_code == 200
    assert client.delete(paths(second)[1]).status_code == 200
    assert artifact not in bucket.objects
    assert client.get(paths(first)[0] + "/original").status_code == 200


def test_documento_elimina_todas_las_paginas_y_solo_sus_objetos(history_env):
    client, bucket, calls = history_env
    initialize(client)
    result = generate(client)
    path, _ = paths(result)
    original = result["almacenamiento_oci"]["documento_original_objeto_id"]
    catalog = next(k for k in bucket.objects if "/adaptaciones/" in k)
    record = json.loads(bucket.objects[catalog])
    prefix = catalog.rsplit("/", 1)[0] + "/"
    for index in range(25):
        clone = {**record, "id": f"{index:032x}"}
        bucket.objects[prefix + clone["id"] + ".json"] = json.dumps(clone).encode()
    # Una variante antigua del mismo original, de otro mes.
    old_original = original.replace("/2026/", "/2025/")
    bucket.objects[old_original] = bucket.objects[original]
    unrelated = {"historial-archivos-v1/otro/documentos-fuente/original.txt": b"otro navegador",
                 "documentos-fuente/cache-global.txt": b"legacy"}
    bucket.objects.update(unrelated)
    summary = confirm(client, path)
    assert summary["resultados"] == 26
    assert remove(client, path, summary).status_code == 200
    assert remove(client, path, summary).status_code == 200
    assert client.get("/api/v1/documentos").json()["documentos"] == []
    assert client.get(path + "/original").status_code == 404
    assert not any(k.startswith(prefix) for k in bucket.objects)
    assert original not in bucket.objects and old_original not in bucket.objects
    assert all(bucket.objects[k] == value for k, value in unrelated.items())
    assert len(calls) == 1


def test_exige_confirmacion_actual_y_rechaza_historial_ajeno(history_env):
    client, bucket, _ = history_env
    initialize(client)
    path, adaptation = paths(generate(client))
    snapshot = dict(bucket.objects)
    assert client.delete(path).status_code == 428
    assert client.delete(adaptation, headers={"Origin": "https://ajeno.example"}).status_code == 403
    with TestClient(app) as other:
        assert other.get(path + "/eliminacion").status_code == 404
        assert other.delete(adaptation).status_code == 404
        assert other.delete(path, headers={"If-Match": "0" * 64}).status_code == 404
    assert bucket.objects == snapshot
    summary = confirm(client, path)
    generate(client, "Quiz Interactivo")
    snapshot = dict(bucket.objects)
    assert remove(client, path, summary).status_code == 409
    assert bucket.objects == snapshot
    assert confirm(client, path)["resultados"] == 2


@pytest.mark.parametrize("failure", ["original", "artifact", "document", "completion"])
def test_borrado_documento_incompleto_se_puede_retomar(history_env, failure):
    client, bucket, calls = history_env
    initialize(client)
    result = generate(client)
    path, _ = paths(result)
    summary = confirm(client, path)
    keys = {"original": result["almacenamiento_oci"]["documento_original_objeto_id"],
            "artifact": result["almacenamiento_oci"]["objeto_id"],
            "document": next(k for k in bucket.objects if k.startswith("historial-v1/") and "/documentos/" in k)}
    bucket.delete_failure_key = keys.get(failure)
    bucket.fail_completion = failure == "completion"
    response = remove(client, path, summary)
    assert response.status_code == 503, response.text
    assert "private-detail" not in response.text
    listed = client.get("/api/v1/documentos").json()["documentos"]
    assert len(listed) == 1 and listed[0]["eliminacion_pendiente"] is True
    assert client.get(path + "/original").status_code in (404, 409)
    assert confirm(client, path)["version"] == summary["version"]
    bucket.delete_failure_key = None
    bucket.fail_completion = False
    assert remove(client, path, summary).status_code == 200
    assert client.get("/api/v1/documentos").json()["documentos"] == []
    assert not any(k.startswith("historial-archivos-v1/") for k in bucket.objects)
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["artifact", "catalog", "completion"])
def test_borrado_resultado_incompleto_se_puede_retomar(history_env, failure):
    client, bucket, _ = history_env
    initialize(client)
    result = generate(client)
    path, adaptation = paths(result)
    artifact = result["almacenamiento_oci"]["objeto_id"]
    catalog = next(k for k in bucket.objects if "/adaptaciones/" in k)
    bucket.delete_failure_key = artifact if failure == "artifact" else catalog if failure == "catalog" else None
    bucket.fail_completion = failure == "completion"
    assert client.delete(adaptation).status_code == 503
    listed = client.get(path + "/adaptaciones").json()["adaptaciones"]
    assert len(listed) == 1 and listed[0]["eliminacion_pendiente"] is True
    assert confirm(client, path)["resultados"] == 1
    assert client.get(adaptation).status_code == 409
    bucket.delete_failure_key = None
    bucket.fail_completion = False
    assert client.delete(adaptation).status_code == 200
    assert client.delete(adaptation).status_code == 200
    assert client.get(path + "/adaptaciones").json()["adaptaciones"] == []
    assert client.get(path + "/original").status_code == 200


def test_generacion_anterior_no_resucita_documento_eliminado(history_env):
    client, bucket, calls = history_env
    initialize(client)
    path, _ = paths(generate(client))
    summary = confirm(client, path)

    def interrupted(request):
        calls.append(request.read())
        assert remove(client, path, summary).status_code == 200
        data = payload("Flashcards")
        data["metadatos"].update(perfil_aplicado="Junior", nicho_contexto="General")
        return httpx.Response(200, json=data)

    app.dependency_overrides[get_ia_client] = lambda: IAClient("http://ia-fixture", 600, httpx.MockTransport(interrupted))
    response = generate(client)
    assert response["historial"]["status"] == "error"
    assert "eliminó" in response["historial"]["mensaje"]
    assert client.get("/api/v1/documentos").json()["documentos"] == []
    assert not any(k.startswith("historial-archivos-v1/") for k in bucket.objects)
    # Una carga nueva y explícita sí puede reutilizar el mismo contenido.
    def fresh(_request):
        data = payload("Flashcards")
        data["metadatos"].update(perfil_aplicado="Junior", nicho_contexto="General")
        return httpx.Response(200, json=data)
    app.dependency_overrides[get_ia_client] = lambda: IAClient("http://ia-fixture", 600, httpx.MockTransport(fresh))
    generate(client)
    assert len(client.get("/api/v1/documentos").json()["documentos"]) == 1
    assert remove(client, path, summary).status_code == 200
    assert len(client.get("/api/v1/documentos").json()["documentos"]) == 1

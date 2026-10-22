"""Historial completo con el SDK OCI real y un bucket HTTP controlado, sin red."""

from io import BytesIO
import json
from urllib.parse import parse_qs, unquote, urlsplit

from fastapi.testclient import TestClient
import httpx
import pytest
from oci._vendor import requests
from oci._vendor.requests.adapters import BaseAdapter

from app.core.config import settings
from app.main import app
from app.services.browser_identity import COOKIE
from app.services.ia_client import IAClient, get_ia_client
from app.services.oci_service import OCIStorage, get_oci_storage
from test_ia_integration import FORM, payload, post_document
from test_oci_storage import sdk_factory, signing_key


class BucketTransport(BaseAdapter):
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.failure_prefix = None
        self.empty_collections_are_null = False

    def send(self, request, **_kwargs):
        url = urlsplit(request.url)
        key = unquote(url.path.split("/o/", 1)[1]) if "/o/" in url.path else None
        self.calls.append((request.method, key))
        status, data = 200, b"{}"
        if key and self.failure_prefix and key.startswith(self.failure_prefix):
            status, data = 503, b'{"code":"Unavailable","message":"private-detail"}'
        elif request.method == "PUT":
            self.objects[key] = request.body.read() if hasattr(request.body, "read") else request.body
        elif key is not None:
            if key in self.objects:
                data = self.objects[key]
            else:
                status, data = 404, b'{"code":"ObjectNotFound","message":"private-detail"}'
        else:
            query = parse_qs(url.query)
            prefix = query.get("prefix", [""])[0]
            start = query.get("start", [""])[0]
            limit = int(query.get("limit", ["20"])[0])
            names = sorted(k for k in self.objects if k.startswith(prefix) and k >= start)
            objects = [{"name": k, "size": len(self.objects[k])} for k in names[:limit]]
            data = json.dumps({"objects": objects if objects or not self.empty_collections_are_null else None,
                               "nextStartWith": names[limit] if len(names) > limit else None}).encode()
        response = requests.Response()
        response.status_code, response.request, response.url = status, request, request.url
        response.headers = {"content-type": "application/json", "content-length": str(len(data)), "opc-request-id": "fixture"}
        response._content, response.raw = data, BytesIO(data)
        return response

    def close(self):
        pass


@pytest.fixture
def history_env(sdk_factory, monkeypatch):
    bucket, calls = BucketTransport(), []
    monkeypatch.setattr(settings, "HISTORY_ENABLED", True)
    monkeypatch.setattr(settings, "HISTORY_COOKIE_SECURE", False)

    def sdk():
        client, _ = sdk_factory()
        client.base_client.session.mount("https://", bucket)
        return client

    def ia(request):
        body = request.read()
        calls.append(body)
        # Los valores del multipart deben propagarse sin cambios a las respuestas.
        formato = next(f for f in ("Flashcards", "Quiz Interactivo", "Resumen Ejecutivo") if f.encode() in body)
        data = payload(formato)
        data["metadatos"]["perfil_aplicado"] = "Junior"
        data["metadatos"]["nicho_contexto"] = "General"
        return httpx.Response(200, json=data)

    storage = OCIStorage("namespace-fixture", "bucket-fixture", client_factory=sdk)
    app.dependency_overrides[get_oci_storage] = lambda: storage
    app.dependency_overrides[get_ia_client] = lambda: IAClient("http://ia-fixture", 600, httpx.MockTransport(ia))
    with TestClient(app) as client:
        yield client, bucket, calls
    app.dependency_overrides.clear()


def initialize(client):
    response = client.get("/api/v1/documentos")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert "HttpOnly" in response.headers.get("set-cookie", "")
    return response


def generate(client, formato="Flashcards"):
    response = post_document(client, form={**FORM, "perfil_destinatario": "Junior", "nicho_sector": "General", "formato_salida": formato},
                             filename="Mi documento.md", content=b"# JWT\n\nLa firma verifica la integridad del token.")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("formato", ["Flashcards", "Quiz Interactivo", "Resumen Ejecutivo"])
def test_recorrido_completo_recarga_descarga_y_readaptacion(history_env, formato):
    client, bucket, calls = history_env
    assert initialize(client).json()["documentos"] == []
    result = generate(client, formato)
    ref = result["historial"]
    assert ref["status"] == "disponible"
    doc_id, adaptation_id = ref["documento_id"], ref["adaptacion_id"]
    original_cookie = client.cookies.get(COOKIE)
    documents = client.get("/api/v1/documentos").json()["documentos"]
    assert documents[0]["nombre"] == "Mi documento.md"
    assert "objeto_original" not in documents[0]
    assert client.cookies.get(COOKIE) == original_cookie
    url = f"/api/v1/documentos/{doc_id}/adaptaciones"
    records = client.get(url).json()["adaptaciones"]
    assert records[0]["formato_salida"] == formato
    assert "objeto_resultado" not in records[0]
    before = len(calls)
    saved = client.get(url + "/" + adaptation_id)
    assert saved.status_code == 200, saved.text
    assert saved.json()["contenido_adaptado"] == result["contenido_adaptado"]
    downloaded = client.get(url + "/" + adaptation_id + "/descarga")
    assert downloaded.json() == saved.json()
    assert "attachment" in downloaded.headers["content-disposition"]
    original = client.get(f"/api/v1/documentos/{doc_id}/original")
    assert original.content == b"# JWT\n\nLa firma verifica la integridad del token."
    assert original.headers["cache-control"] == "no-store"
    assert len(calls) == before
    adapted = client.post(url, json={"perfil_destinatario": "Junior", "formato_salida": "Resumen Ejecutivo", "nicho_sector": "General"})
    assert adapted.status_code == 200, adapted.text
    assert len(calls) == before + 1
    assert original.content in calls[-1]
    assert adapted.json()["historial"]["documento_id"] == doc_id
    assert len(client.get(url).json()["adaptaciones"]) == 2
    # Las identidades no residen en memoria del proceso ni dependen del TestClient original.
    with TestClient(app) as reopened:
        reopened.cookies.set(COOKIE, original_cookie)
        assert reopened.get("/api/v1/documentos").json()["documentos"] == client.get("/api/v1/documentos").json()["documentos"]


def test_otro_navegador_y_cookie_borrada_no_acceden_a_documentos(history_env):
    client, bucket, calls = history_env
    initialize(client)
    ref = generate(client)["historial"]
    path = f"/api/v1/documentos/{ref['documento_id']}"
    with TestClient(app) as other:
        assert initialize(other).json()["documentos"] == []
        for suffix in ("/original", "/adaptaciones", f"/adaptaciones/{ref['adaptacion_id']}", f"/adaptaciones/{ref['adaptacion_id']}/descarga"):
            response = other.get(path + suffix)
            assert response.status_code == 404, response.text
            assert response.headers["cache-control"] == "no-store"
        assert other.post(path + "/adaptaciones", json={"perfil_destinatario":"Junior", "formato_salida":"Flashcards", "nicho_sector":"General"}).status_code == 404
    client.cookies.clear()
    assert initialize(client).json()["documentos"] == []
    assert len(calls) == 1


def test_inicializacion_y_origin_no_consumen_ia(history_env):
    client, bucket, calls = history_env
    response = post_document(client)
    assert response.status_code == 409 and calls == []
    assert client.cookies.get(COOKIE)
    for origin in ("https://evil.example", "null", "http://["):
        response = client.post("/api/v1/adaptar-contenido", headers={"Origin": origin})
        assert response.status_code == 403
    assert calls == []


def test_no_se_importan_objetos_anteriores(history_env):
    client, bucket, _ = history_env
    bucket.objects["artefactos-generados/2026/10/antiguo.json"] = b"{}"
    assert initialize(client).json()["documentos"] == []


def test_fallo_del_catalogo_no_pierde_resultado_ni_publica_una_adaptacion(history_env):
    client, bucket, _ = history_env
    initialize(client)
    bucket.failure_prefix = "historial-v1/"
    result = generate(client)
    assert result["almacenamiento_oci"]["status_upload"] == "subido"
    assert result["historial"]["status"] == "error"
    assert "private-detail" not in json.dumps(result)
    bucket.failure_prefix = None
    assert client.get("/api/v1/documentos").json()["documentos"] == []


def test_catalogo_parcial_no_inventa_adaptaciones_disponibles(history_env):
    from hashlib import sha256
    client, bucket, _ = history_env
    initialize(client)
    owner = sha256(client.cookies.get(COOKIE).encode()).hexdigest()
    bucket.failure_prefix = f"historial-v1/{owner}/adaptaciones/"
    result = generate(client)
    assert result["historial"]["status"] == "error"
    bucket.failure_prefix = None
    documents = client.get("/api/v1/documentos").json()["documentos"]
    assert len(documents) == 1
    assert client.get(f"/api/v1/documentos/{documents[0]['id']}/adaptaciones").json()["adaptaciones"] == []


def test_paginacion_recupera_todos_los_documentos_sin_repetirlos(history_env):
    client, _, calls = history_env
    initialize(client)
    for i in range(21):
        response = post_document(client, filename=f"manual-{i}.md", content=f"Contenido técnico número {i}".encode(),
                                 form={**FORM, "perfil_destinatario":"Junior", "nicho_sector":"General"})
        assert response.status_code == 200
        assert response.json()["historial"]["status"] == "disponible"
    first = client.get("/api/v1/documentos").json()
    assert len(first["documentos"]) == 20 and first["siguiente"]
    second = client.get("/api/v1/documentos", params={"cursor":first["siguiente"]}).json()
    assert len(second["documentos"]) == 1 and second["siguiente"] is None
    assert len({doc["id"] for doc in first["documentos"] + second["documentos"]}) == 21
    assert len(calls) == 21


def test_cookie_segura_cuando_la_aplicacion_usa_https(history_env):
    with TestClient(app, base_url="https://testserver") as client:
        response = initialize(client)
        assert "; Secure" in response.headers["set-cookie"]
        assert generate(client)["historial"]["status"] == "disponible"


def test_archivo_ausente_o_corrupto_no_se_envia_a_ia(history_env):
    client, bucket, calls = history_env
    initialize(client)
    result = generate(client)
    ref = result["historial"]
    key = result["almacenamiento_oci"]["documento_original_objeto_id"]
    bucket.objects[key] = b"alterado"
    path = f"/api/v1/documentos/{ref['documento_id']}"
    assert client.get(path + "/original").status_code == 502
    response = client.post(path + "/adaptaciones", json={"perfil_destinatario":"Junior", "formato_salida":"Flashcards", "nicho_sector":"General"})
    assert response.status_code == 502 and len(calls) == 1
    del bucket.objects[key]
    assert client.get(path + "/original").status_code == 404


def test_paginacion_no_permite_cambiar_de_propietario(history_env):
    client, _, _ = history_env
    initialize(client)
    assert client.get("/api/v1/documentos", params={"cursor":"historial-v1/otro/documentos/a.json"}).status_code == 422


def test_resubir_mismos_bytes_con_otro_nombre_no_rompe_resultados_anteriores(history_env):
    client, _, calls = history_env
    initialize(client)
    result = generate(client)
    ref = result["historial"]
    response = post_document(client, filename="Otro nombre.md", content=b"# JWT\n\nLa firma verifica la integridad del token.",
                             form={**FORM, "perfil_destinatario":"Junior", "nicho_sector":"General"})
    assert response.status_code == 200
    assert response.json()["historial"]["documento_id"] == ref["documento_id"]
    assert len(client.get('/api/v1/documentos').json()["documentos"]) == 1
    saved = client.get(f"/api/v1/documentos/{ref['documento_id']}/adaptaciones/{ref['adaptacion_id']}")
    assert saved.status_code == 200, saved.text
    assert len(calls) == 2


def test_resultado_alterado_no_se_publica_como_valido(history_env):
    client, bucket, calls = history_env
    initialize(client)
    result = generate(client)
    ref = result["historial"]
    key = result["almacenamiento_oci"]["objeto_id"]
    tampered = json.loads(bucket.objects[key])
    tampered["contenido_adaptado"]["items"][0]["dorso"] = "Texto modificado después de guardar"
    bucket.objects[key] = json.dumps(tampered).encode()
    response = client.get(f"/api/v1/documentos/{ref['documento_id']}/adaptaciones/{ref['adaptacion_id']}")
    assert response.status_code == 502
    assert len(calls) == 1


def test_sin_oci_el_historial_informa_indisponibilidad(monkeypatch):
    app.dependency_overrides[get_oci_storage] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/documentos")
            assert response.status_code == 503
            assert response.json()["detail"]["codigo"] == "HISTORIAL_NO_DISPONIBLE"
            assert response.headers["cache-control"] == "no-store"
            assert client.get("/api/v1/historial/sesion").json() == {"habilitado": False}
    finally:
        app.dependency_overrides.clear()


def test_coleccion_vacia_null_de_oci_es_un_historial_vacio(history_env):
    client, bucket, calls = history_env
    bucket.empty_collections_are_null = True
    assert initialize(client).json()["documentos"] == []
    assert calls == []


def test_preparar_sesion_no_consulta_oci_ni_ia(history_env):
    client, bucket, calls = history_env
    response = client.get('/api/v1/historial/sesion')
    assert response.json() == {"habilitado": True}
    assert client.cookies.get(COOKIE)
    assert bucket.calls == [] and calls == []


def test_mismos_bytes_entre_navegadores_no_comparten_objetos_ni_nombres(history_env):
    from hashlib import sha256
    client, bucket, _ = history_env
    initialize(client)
    first = generate(client)
    first_owner = sha256(client.cookies.get(COOKIE).encode()).hexdigest()
    with TestClient(app) as other:
        initialize(other)
        second = post_document(other, filename='Nombre privado B.md',
            content=b"# JWT\n\nLa firma verifica la integridad del token.",
            form={**FORM, 'perfil_destinatario':'Junior', 'nicho_sector':'General'}).json()
        second_owner = sha256(other.cookies.get(COOKIE).encode()).hexdigest()
    assert first['almacenamiento_oci']['objeto_id'] != second['almacenamiento_oci']['objeto_id']
    for field in ('objeto_id', 'documento_original_objeto_id'):
        assert first['almacenamiento_oci'][field].startswith(f'historial-archivos-v1/{first_owner}/')
        assert second['almacenamiento_oci'][field].startswith(f'historial-archivos-v1/{second_owner}/')
    ref = first['historial']
    url = f"/api/v1/documentos/{ref['documento_id']}/adaptaciones/{ref['adaptacion_id']}"
    opened = client.get(url)
    assert opened.status_code == 200, opened.text
    assert opened.json()['almacenamiento_oci'] == first['almacenamiento_oci']
    # Incluso un manifiesto alterado no puede apuntar a los archivos de otro owner.
    record_key = f"historial-v1/{first_owner}/adaptaciones/{ref['documento_id']}/{ref['adaptacion_id']}.json"
    record = json.loads(bucket.objects[record_key])
    record['objeto_resultado'] = second['almacenamiento_oci']['objeto_id']
    bucket.objects[record_key] = json.dumps(record).encode()
    before = len(bucket.calls)
    assert client.get(url).status_code == 502
    assert ('GET', second['almacenamiento_oci']['objeto_id']) not in bucket.calls[before:]


def test_nombre_largo_conserva_extension_para_readaptar(history_env):
    client, _, calls = history_env
    initialize(client)
    result = post_document(client, filename='a' * 270 + '.markdown', content=b'Contenido tecnico',
                           form={**FORM, 'perfil_destinatario':'Junior', 'nicho_sector':'General'}).json()
    assert result['historial']['status'] == 'disponible'
    doc = client.get('/api/v1/documentos').json()['documentos'][0]
    assert len(doc['nombre']) == 255 and doc['nombre'].endswith('.markdown')
    response = client.post(f"/api/v1/documentos/{doc['id']}/adaptaciones", json={
        'perfil_destinatario':'Junior', 'formato_salida':'Flashcards', 'nicho_sector':'General'})
    assert response.status_code == 200
    assert len(calls) == 2

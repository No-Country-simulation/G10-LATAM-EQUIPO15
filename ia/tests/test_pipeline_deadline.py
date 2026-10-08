"""Verifica el supervisor con procesos reales, sin llamadas externas."""

import multiprocessing
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ia_http import main, runner

PAYLOAD = {
    "status":"exito",
    "metadatos":{"perfil_aplicado":"Junior", "formato_generado":"Flashcards", "tiempo_estimado_estudio_minutos":3,
                 "conceptos_clave":["JWT"], "nicho_contexto":"General"},
    "contenido_adaptado":{"titulo":"JWT", "introduccion_contextualizada":"Tokens técnicos.",
                          "items":[{"frente":"JWT", "dorso":"Token firmado"}]},
    "evaluacion_calidad":{"anclaje_fuente_score":0.9},
    "almacenamiento_oci":{"objeto_id":"jwt.json", "status_upload":"listo_para_subida"},
}


def successful_worker(connection, kwargs):
    connection.send({"result":PAYLOAD})
    connection.close()


def blocked_worker(connection, kwargs):
    Path(kwargs["marker"]).write_text(str(multiprocessing.current_process().pid))
    time.sleep(20)
    Path(kwargs["marker"] + ".finished").write_text("finished")
    connection.send({"result":PAYLOAD})


def interrupted_worker(connection, kwargs):
    connection.close()


def test_spawn_worker_can_return_validated_response():
    result = runner._run_in_process(successful_worker, {}, 20)
    assert result.status == "exito"
    assert result.contenido_adaptado.items[0].dorso == "Token firmado"


@pytest.fixture
def fast_processes(monkeypatch):
    # Docker Linux: fork permite probar el plazo corto sin medir importaciones.
    context = multiprocessing.get_context("fork")
    monkeypatch.setattr(runner.multiprocessing, "get_context", lambda _: context)


def test_global_deadline_terminates_worker_and_next_request_succeeds(tmp_path, fast_processes):
    marker = str(tmp_path / "worker")
    with pytest.raises(runner.PipelineServiceError) as error:
        runner._run_in_process(blocked_worker, {"marker":marker}, 0.3)
    assert (error.value.status_code, error.value.codigo) == (504, "PROVEEDOR_TIMEOUT")
    assert Path(marker).exists()
    pid = int(Path(marker).read_text())
    assert all(p.pid != pid for p in multiprocessing.active_children())
    assert not Path(marker + ".finished").exists()
    assert runner._run_in_process(successful_worker, {}, 3).status == "exito"


def test_interrupted_worker_has_safe_error_and_does_not_hang(fast_processes):
    with pytest.raises(runner.PipelineServiceError) as error:
        runner._run_in_process(interrupted_worker, {}, 3)
    assert (error.value.status_code, error.value.codigo) == (500, "ERROR_INTERNO_IA")


def test_http_deadline_cleans_temp_file_releases_lock_and_accepts_next_request(monkeypatch, tmp_path, fast_processes):
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key_without_network")
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_without_network")
    monkeypatch.setenv("IA_STRICT_PROVIDERS", "1")
    monkeypatch.setenv("IA_PIPELINE_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setattr(runner, "_pipeline_worker", blocked_worker)
    original = runner.run_pipeline_with_deadline
    paths = []

    def observed(**kwargs):
        paths.append(Path(kwargs["ruta_archivo"]))
        return original(**kwargs, marker=str(tmp_path / "http-worker"))

    main.app.dependency_overrides[runner.get_pipeline_runner] = lambda: observed
    try:
        with TestClient(main.app) as client:
            form = {"perfil_destinatario":"Junior", "formato_salida":"Flashcards", "nicho_sector":"General"}
            response = client.post("/api/v1/adaptar-contenido", data=form, files={"documento_original":("jwt.md",b"JWT")})
            assert response.status_code == 504
            assert response.json()["detail"]["codigo"] == "PROVEEDOR_TIMEOUT"
            assert not paths[0].parent.exists()
            assert client.get("/health").status_code == 200
            monkeypatch.setattr(runner, "_pipeline_worker", successful_worker)
            monkeypatch.setenv("IA_PIPELINE_TIMEOUT_SECONDS", "3")
            response = client.post("/api/v1/adaptar-contenido", data=form, files={"documento_original":("jwt.md",b"JWT")})
            assert response.status_code == 200
            assert not paths[1].parent.exists()
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize("value", ["0", "nan", "600", "invalid"])
def test_invalid_deadline_does_not_start_processing(monkeypatch, value):
    monkeypatch.setenv("IA_PIPELINE_TIMEOUT_SECONDS", value)
    with pytest.raises(runner.PipelineServiceError) as error:
        runner.run_pipeline_with_deadline()
    assert (error.value.status_code, error.value.codigo) == (503, "IA_NO_CONFIGURADA")

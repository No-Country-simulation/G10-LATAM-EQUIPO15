"""Servicio IA simulado solo para probar la cadena HTTP, sin proveedores ni red externa."""
import base64
import json
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

observed = []


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_json(self, code, value):
        content = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "healthy", "service": "ia-fixture"})
        elif self.path == "/test/requests":
            self.send_json(200, observed)
        else:
            self.send_json(404, {})

    def do_POST(self):
        if self.path != "/api/v1/adaptar-contenido":
            self.send_json(404, {})
            return
        body = self.rfile.read(int(self.headers["Content-Length"]))
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + body)
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        document = parts.pop("documento_original")
        params = {name: part.get_payload(decode=True).decode() for name, part in parts.items()}
        filename = document.get_filename()
        observed.append({"filename": filename, "bytes_base64": base64.b64encode(document.get_payload(decode=True)).decode(), "params": params})
        if filename == "rechazado.txt":
            self.send_json(422, {"detail": {"codigo": "CONTEXTO_INSUFICIENTE", "mensaje": "Fallo controlado del fixture."}})
            return
        if filename == "ocupado.txt":
            self.send_json(503, {"detail": {"codigo": "IA_OCUPADA", "mensaje": "Fallo controlado del fixture."}})
            return
        items = {
            "Flashcards": [{"frente": "¿Qué verifica una firma JWT?", "dorso": "La integridad del token."}],
            "Quiz Interactivo": [{"pregunta": "¿Qué verifica la firma?", "opciones": ["Integridad", "Cifrado", "Compresión", "Anonimato"],
                                  "indice_correcto": 0, "justificacion_tecnica": "La firma permite detectar cambios."}],
            "Resumen Ejecutivo": {"tldr": "JWT transporta claims firmados.", "puntos_clave": ["Integridad"],
                                  "impacto_negocio": "Autenticación interoperable.", "recomendaciones": ["Validar firmas"]},
        }[params["formato_salida"]]
        self.send_json(200, {
            "status": "exito", "codigo_respuesta": 200,
            "metadatos": {"perfil_aplicado": params["perfil_destinatario"], "formato_generado": params["formato_salida"],
                          "nicho_contexto": params["nicho_sector"], "tiempo_estimado_estudio_minutos": 3, "conceptos_clave": ["JWT"]},
            "contenido_adaptado": {"titulo": "JWT", "introduccion_contextualizada": "Conceptos del documento.", "items": items},
            "evaluacion_calidad": {"anclaje_fuente_score": 0.95, "claridad_pedagogica": "Alta", "reintentos_realizados": 0},
            "almacenamiento_oci": {"objeto_id": "jwt.json", "status_upload": "pendiente"},
        })


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8001), Fixture).serve_forever()

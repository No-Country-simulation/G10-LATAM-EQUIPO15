"""
Evaluación de calidad con un conjunto fijo de documentos cortos (ver README.md).

Ejecuta cada caso con el mismo runner del servicio HTTP (proceso aislado, límite global
y modo estricto) contra los proveedores reales configurados en ia/.env, y mide:
  - cobertura: secciones del documento (títulos, o párrafos si no hay) cuyo contenido aparece
    en la salida, medido por términos propios de cada sección;
  - fragmentos citados: cuántos fragmentos distintos citan los ítems (con un solo fragmento,
    la cita no permite ubicar la información en el documento);
  - ítems generados frente al tamaño del documento;
  - citas válidas: ítems con fuentes que existen entre los fragmentos;
  - cifras y siglas de la salida ausentes en la fuente (posibles datos inventados),
    sin contar las opciones incorrectas ni la explicación de distractores del quiz;
  - puntaje del crítico, reintentos y tiempo.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python.exe tests/calidad/evaluar.py [--casos id1,id2] [--etiqueta texto] [--pausa 0]
    .venv/Scripts/python.exe tests/calidad/evaluar.py --recalcular tests/calidad/resultados/<carpeta>
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = Path(__file__).resolve().parent
DOCUMENTOS = CARPETA / "documentos"
RESULTADOS = CARPETA / "resultados"
DATOS = CARPETA / ".datos"  # cachés de extracción y metadata: excluido de git

# id: (archivo, formato, perfil, nicho, qué ejercita)
CASOS = {
    "fintech": ("fintech_tokenizacion_pagos.md", "Flashcards", "Junior", "Fintech", "Conceptos y diferencias"),
    "salud": ("salud_triaje_urgencias.pdf", "Quiz Interactivo", "Senior", "Salud", "PDF con ligaduras; cifras de tiempos"),
    "marketing": ("marketing_seo_on_page.md", "Resumen Ejecutivo", "Ejecutivo", "E-commerce", "Resumen sin impacto de negocio explícito"),
    "ecommerce": ("ecommerce_ultima_milla.txt", "Quiz Interactivo", "Junior", "E-commerce", "TXT sin títulos"),
    "software": ("software_git_ramas.md", "Flashcards", "Senior", "General", "Bloques de código"),
    "datos": ("datos_normalizacion_sql.md", "Quiz Interactivo", "Senior", "General", "Tabla Markdown"),
    "finanzas": ("finanzas_flujo_caja.md", "Resumen Ejecutivo", "Ejecutivo", "Fintech", "Cifras: no deben inventarse"),
    "legal": ("legal_datos_personales.pdf", "Flashcards", "Junior", "Salud", "PDF; nicho distinto del tema"),
    "educacion": ("educacion_repaso_espaciado.txt", "Flashcards", "Junior", "General", "Documento muy breve"),
    "cloud_en": ("cloud_iam_least_privilege.md", "Flashcards", "Senior", "Fintech", "Fuente en inglés"),
}


def cargar_entorno():
    for linea in (RAIZ / "ia" / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            nombre, valor = linea.split("=", 1)
            os.environ.setdefault(nombre.strip(), valor.strip())
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
    os.environ.update({
        "IA_STRICT_PROVIDERS": "1", "ANONYMIZED_TELEMETRY": "False",
        "CHROMADB_DIR": str(DATOS / "chromadb"), "DATAIA_DOCUMENTS_DIR": str(DATOS / "documents"),
        "DATAIA_CACHE_DIR": str(DATOS / "cache"),
    })
    sys.path[:0] = [str(RAIZ / "nuevamente-ai-core"), str(RAIZ / "ia" / "src")]


def fragmentos_y_fuente(ruta: Path, formato: str):
    """Reconstruye los fragmentos F1..Fn del pipeline (desde caché, sin llamar al proveedor)."""
    from dataia.ingestion.service import ingest_document
    from dataia.chunking.service import process_chunks
    from src.ai.contexto import seleccionar_fragmentos
    from langchain_core.documents import Document

    ingesta = ingest_document(str(ruta), document_name=ruta.name)
    chunks = process_chunks(ingesta).chunks
    documentos = [Document(page_content=c.text, metadata=c.metadata.model_dump()) for c in chunks]
    fragmentos = seleccionar_fragmentos(documentos, formato)
    fuente = " ".join(c.text for c in ingesta.content)
    estructurado = "\n\n".join(c.text for c in ingesta.content)
    return fragmentos, fuente, estructurado


def _plano(texto: str) -> str:
    texto = texto.replace("ﬁ", "fi").replace("ﬂ", "fl").lower()
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def secciones_fuente(texto: str) -> list:
    """Secciones por títulos Markdown (## o más); sin títulos, párrafos de al menos 20 palabras."""
    titulos = list(re.finditer(r"(?m)^#{2,6}\s+(.+)$", texto))
    if titulos:
        return [(t.group(1).strip(), texto[t.end():(titulos[i + 1].start() if i + 1 < len(titulos) else len(texto))])
                for i, t in enumerate(titulos)]
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if len(p.split()) >= 20]
    return [(p[:40] + "…", p) for p in parrafos]


def cobertura_secciones(texto_fuente: str, salida: str) -> tuple:
    """Una sección está cubierta si la salida usa al menos 2 términos (6+ letras) exclusivos de ella."""
    secciones = secciones_fuente(texto_fuente)
    terminos = [set(re.findall(r"[a-zñ]{6,}", _plano(cuerpo))) for _, cuerpo in secciones]
    palabras_salida = set(re.findall(r"[a-zñ]{6,}", _plano(salida)))
    cubiertas = 0
    for i, propios in enumerate(terminos):
        exclusivos = propios - set().union(*(t for j, t in enumerate(terminos) if j != i))
        if len(exclusivos & palabras_salida) >= min(2, len(exclusivos)):
            cubiertas += 1
    return cubiertas, len(secciones)


def textos_verificables(items, formato: str) -> str:
    """Texto de la salida que debe estar respaldado (excluye los distractores del quiz)."""
    if isinstance(items, dict):
        return json.dumps({k: v for k, v in items.items() if k != "fuentes"}, ensure_ascii=False)
    partes = []
    for item in items:
        if "Quiz" in formato:
            opciones = item.get("opciones") or []
            correcta = opciones[item.get("indice_correcto", 0)] if opciones else ""
            partes += [item.get("pregunta", ""), correcta, item.get("justificacion_tecnica", "")]
        else:
            partes += [str(v) for k, v in item.items() if k != "fuentes"]
    return " ".join(p for p in partes if p)


def _variantes_numero(n: str):
    limpio = n.rstrip(".,%")
    return {limpio, limpio.replace(".", ""), limpio.replace(",", ""), limpio.replace(".", ",")}


def medir(respuesta: dict, fragmentos: list, fuente: str, formato: str, texto_estructurado: str = "") -> dict:
    contenido = respuesta["contenido_adaptado"]
    items = contenido["items"]
    lista = [items] if isinstance(items, dict) else items
    seccion_por_id = {f["id"]: (f.get("section") or "General") for f in fragmentos}

    ids_citados, con_fuentes_validas = set(), 0
    for item in lista:
        ids = item.get("fuentes") or []
        if ids and all(i in seccion_por_id for i in ids):
            con_fuentes_validas += 1
        ids_citados.update(i for i in ids if i in seccion_por_id)

    verificable = " ".join([contenido.get("titulo", ""), contenido.get("introduccion_contextualizada", ""),
                            textos_verificables(items, formato)])
    fuente_plana = fuente.replace("ﬁ", "fi").replace("ﬂ", "fl")
    cifras = sorted({n for n in re.findall(r"\d[\d.,]*%?", verificable)
                     if len(n.rstrip(".,%")) >= 2 and not any(v in fuente_plana for v in _variantes_numero(n))})
    siglas = sorted({s for s in re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", verificable) if s not in fuente_plana})

    cubiertas, total_secciones = cobertura_secciones(texto_estructurado or fuente, verificable)
    ev = respuesta["evaluacion_calidad"]
    return {
        "score": ev["anclaje_fuente_score"],
        "reintentos": ev["reintentos_realizados"],
        "items": len(items) if isinstance(items, list) else len(items.get("puntos_clave", [])),
        "secciones_doc": total_secciones,
        "secciones_cubiertas": cubiertas,
        "cobertura": round(cubiertas / total_secciones, 2) if total_secciones else 0.0,
        "fragmentos_doc": len(fragmentos),
        "fragmentos_citados": len(ids_citados),
        "citas_validas": round(con_fuentes_validas / len(lista), 2) if lista else 0.0,
        "cifras_sin_respaldo": cifras,
        "siglas_sin_respaldo": siglas,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--casos", default=",".join(CASOS), help="ids separados por coma")
    parser.add_argument("--etiqueta", default="", help="nombre corto de la corrida, p. ej. 'linea-base'")
    parser.add_argument("--pausa", type=float, default=0, help="segundos entre casos (útil con Groq)")
    parser.add_argument("--recalcular", help="carpeta de resultados: recalcula métricas sin llamar al proveedor")
    args = parser.parse_args()

    cargar_entorno()
    if args.recalcular:
        return recalcular(Path(args.recalcular))
    from ia_http.runner import PipelineServiceError, run_pipeline_with_deadline

    marca = datetime.now().strftime("%Y%m%d-%H%M") + (f"-{args.etiqueta}" if args.etiqueta else "")
    salida = RESULTADOS / marca
    salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for caso_id in [c.strip() for c in args.casos.split(",") if c.strip()]:
        archivo, formato, perfil, nicho, ejercita = CASOS[caso_id]
        ruta = DOCUMENTOS / archivo
        print(f"=== {caso_id}: {archivo} | {formato} | {perfil} | {nicho}", flush=True)
        inicio = time.monotonic()
        fila = {"caso": caso_id, "archivo": archivo, "formato": formato, "perfil": perfil, "nicho": nicho, "ejercita": ejercita}
        try:
            respuesta = run_pipeline_with_deadline(
                documento_titulo=ruta.stem, ruta_archivo=str(ruta), perfil=perfil,
                formato=formato, nicho=nicho, documento_nombre=ruta.name,
            ).model_dump(mode="json")
            fila["segundos"] = round(time.monotonic() - inicio, 1)
            fragmentos, fuente, estructurado = fragmentos_y_fuente(ruta, formato)
            fila["tokens_doc"] = int(len(fuente.split()) * 1.3)
            fila.update(estado="exito", **medir(respuesta, fragmentos, fuente, formato, estructurado))
            (salida / f"{caso_id}.json").write_text(json.dumps(respuesta, ensure_ascii=False, indent=2), encoding="utf-8")
        except PipelineServiceError as error:
            fila.update(estado="error", segundos=round(time.monotonic() - inicio, 1), http=error.status_code, codigo=error.codigo)
        print("RESULTADO", json.dumps(fila, ensure_ascii=False), flush=True)
        filas.append(fila)
        if args.pausa:
            time.sleep(args.pausa)

    (salida / "resumen.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "resumen.md").write_text(reporte(filas, marca), encoding="utf-8")
    print(f"\nReporte: {salida / 'resumen.md'}")


def recalcular(carpeta: Path):
    filas = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    for fila in filas:
        if fila["estado"] != "exito":
            continue
        respuesta = json.loads((carpeta / f"{fila['caso']}.json").read_text(encoding="utf-8"))
        fragmentos, fuente, estructurado = fragmentos_y_fuente(DOCUMENTOS / fila["archivo"], fila["formato"])
        fila.pop("secciones_citadas", None)
        fila.update(medir(respuesta, fragmentos, fuente, fila["formato"], estructurado))
    (carpeta / "resumen.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "resumen.md").write_text(reporte(filas, carpeta.name), encoding="utf-8")
    print(f"Reporte recalculado: {carpeta / 'resumen.md'}")


def reporte(filas, marca) -> str:
    lineas = [
        f"# Evaluación de calidad: {marca}", "",
        "| Caso | Formato | Tokens | Estado | Fidelidad | Reintentos | Ítems | Cobertura de secciones | Fragmentos citados | Citas válidas | Cifras sin respaldo | Siglas sin respaldo | Tiempo |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        if f["estado"] != "exito":
            lineas.append(f"| {f['caso']} | {f['formato']} | — | {f.get('http')} {f.get('codigo')} | — | — | — | — | — | — | — | — | {f['segundos']} s |")
            continue
        lineas.append(
            f"| {f['caso']} | {f['formato']} | {f['tokens_doc']} | éxito | {f['score']} | {f['reintentos']} | {f['items']} | "
            f"{f['secciones_cubiertas']}/{f['secciones_doc']} | {f['fragmentos_citados']}/{f['fragmentos_doc']} | {f['citas_validas']} | {', '.join(f['cifras_sin_respaldo']) or '—'} | "
            f"{', '.join(f['siglas_sin_respaldo']) or '—'} | {f['segundos']} s |"
        )
    exitos = [f for f in filas if f["estado"] == "exito"]
    if exitos:
        promedio = lambda k: round(sum(f[k] for f in exitos) / len(exitos), 2)
        lineas += ["", f"**Éxitos:** {len(exitos)}/{len(filas)} · **Fidelidad media:** {promedio('score')} · "
                       f"**Cobertura media:** {promedio('cobertura')} · **Citas válidas medias:** {promedio('citas_validas')}"]
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    main()

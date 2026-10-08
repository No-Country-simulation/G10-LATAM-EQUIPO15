# Contrato Backend ↔ IA — MVP

Versión 2.3 — 08-10-2026. Referencia de la consolidación; sustituye las propuestas v2.1 y la salida anterior de tres campos.

## Entrada HTTP

Backend recibe y reenvía el documento original sin extraer ni normalizar su texto. Ambos servicios exponen `POST /api/v1/adaptar-contenido` con `multipart/form-data` y cuatro campos obligatorios:

| Campo | Valores |
|---|---|
| `documento_original` | Archivo PDF, Markdown (`.md` / `.markdown`) o TXT |
| `perfil_destinatario` | `Junior`, `Senior`, `Ejecutivo` |
| `formato_salida` | `Flashcards`, `Quiz Interactivo`, `Resumen Ejecutivo` |
| `nicho_sector` | `Fintech`, `Salud`, `E-commerce`, `General` |

`Senior` representa al líder técnico. No se reciben `request_id`, `nivel_detalle` ni DOCX. Mapa Mental quedó fuera del MVP público; la Guía Paso a Paso permanece únicamente como formato interno de AI Core.

## Responsabilidades

Backend valida parámetros, extensión, tamaño y archivo vacío; envía los bytes a IA, valida la respuesta y su correspondencia con los parámetros solicitados, y conserva campos adicionales. No genera metadatos ni calcula calidad.

Data/IA valida el documento, extrae PDF a Markdown, conserva estructura y páginas, realiza chunking y enriquecimiento en lotes, genera embeddings y persiste Chroma, registros y cachés. El identificador es el hash SHA-256 del contenido: repetir un documento reutiliza sus registros y vectores. Existe un único paquete compartido `ia/src/dataia`, importado como `dataia.*`.

AI Core selecciona contexto entre los fragmentos ordenados del documento según formato y presupuesto, incorpora metadata pedagógica, genera con schemas por formato y cita fragmentos. El crítico revisa afirmaciones y distingue hechos de analogías y distractores. El score se calcula a partir de los veredictos; se mantiene un respaldo de score escalar por compatibilidad. El ensamblador calcula tiempo de estudio y devuelve la evaluación.

## Salida y calidad

HTTP 200 devuelve seis campos: `status`, `metadatos`, `contenido_adaptado`, `evaluacion_calidad`, `almacenamiento_oci`, `codigo_respuesta`. Consultar [Schema Response](SCHEMA_RESPONSE.md) y `/openapi.json` de cada servicio.

El umbral predeterminado es 0.85 para Flashcards y Resumen, y como máximo 0.75 para Quiz. Un borrador insuficiente se corrige hasta el máximo configurado; si no alcanza el umbral, se rechaza con 422 `CONTEXTO_INSUFICIENTE`. En modo estricto los fallos de proveedor se propagan, sin contenido ni score simulados.

`almacenamiento_oci.status_upload` es `listo_para_subida` o `pendiente`; describe una intención de almacenamiento. No certifica una subida. Chroma, registros y cachés sobreviven a recrear el contenedor mediante el volumen Docker `ia-data`. OCI Object Storage no está implementado.

## Errores y ejecución

Los errores tienen forma `{"detail":{"codigo":"...","mensaje":"..."}}`; nunca se presentan como contenido exitoso.

| HTTP | Situación |
|---|---|
| 413 | Documento demasiado grande |
| 415 | Extensión no soportada |
| 422 | Parámetros, documento o contexto rechazado |
| 500 | Error interno |
| 502 | Proveedor/procesamiento o respuesta IA inválida |
| 503 | IA ocupada, no configurada, no disponible o proveedor/cuota sin disponibilidad |
| 504 | Timeout del proveedor, pipeline o cliente Backend |

El endpoint es síncrono. IA procesa una adaptación por vez y responde `503 IA_OCUPADA` a solicitudes concurrentes. Un proceso hijo supervisado aplica el plazo total y libera recursos al agotarlo. Se conservan límites por proveedor y reintentos acotados. `/health` solo comprueba disponibilidad HTTP. No se expone SSE ni un sistema de trabajos persistentes.

## Verificación y pendientes

[Pruebas reproducibles](../../tests/README.md): suite offline sin red y ensayo real con Gemini desde Backend, incluyendo una segunda adaptación después de recrear IA con el mismo volumen. Los resultados no sustituyen una revisión general de calidad para todos los documentos y formatos.

Pendientes: conectar Frontend al endpoint real, implementar OCI Object Storage y validar el despliegue cloud. El Frontend publicado mantiene su adaptador de ejemplo. Los documentos de planificación y ADR describen objetivos que pueden exceder esta implementación.

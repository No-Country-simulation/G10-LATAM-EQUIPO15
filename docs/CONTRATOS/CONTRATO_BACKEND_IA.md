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

Data/IA valida el documento, extrae PDF a Markdown, conserva estructura y páginas, realiza chunking y enriquecimiento en lotes paralelos, y persiste fragmentos, registros y cachés. Los embeddings en Chroma son opcionales (`DATAIA_EMBEDDINGS_ENABLED`, desactivado por defecto): la generación lee los fragmentos en orden y no usa búsqueda vectorial. El identificador es el hash SHA-256 del contenido: repetir un documento reutiliza sus registros y cachés. Existe un único paquete compartido `ia/src/dataia`, importado como `dataia.*`.

AI Core selecciona contexto entre los fragmentos ordenados del documento según formato y presupuesto, incorpora metadata pedagógica, genera con schemas por formato y cita fragmentos. El crítico revisa afirmaciones y distingue hechos de analogías y distractores. El score se calcula a partir de los veredictos; se mantiene un respaldo de score escalar por compatibilidad. El ensamblador calcula tiempo de estudio y devuelve la evaluación.

## Salida y calidad

HTTP 200 devuelve seis campos: `status`, `metadatos`, `contenido_adaptado`, `evaluacion_calidad`, `almacenamiento_oci`, `codigo_respuesta`. Consultar [Schema Response](SCHEMA_RESPONSE.md) y `/openapi.json` de cada servicio.

El umbral predeterminado es 0.85 para Flashcards y Resumen, y como máximo 0.75 para Quiz. Un borrador insuficiente se corrige hasta el máximo configurado; si no alcanza el umbral, se rechaza con 422 `CONTEXTO_INSUFICIENTE`. En modo estricto los fallos de proveedor se propagan, sin contenido ni score simulados.

IA solo puede entregar `almacenamiento_oci.status_upload` como `listo_para_subida` o `pendiente`: describe una intención, no certifica una subida. La opción `OCI_STORAGE_ENABLED` del Backend está desactivada por defecto. Al habilitarla, Backend guarda original y JSON y reemplaza el estado por `subido`, `parcial` o `error`, según las confirmaciones del SDK. Añade la clave del original y su confirmación dentro del mismo campo de almacenamiento; los seis campos públicos se conservan. Un fallo OCI conserva HTTP 200 y la adaptación, con un error de almacenamiento explícito. Consultar [Object Storage](../OCI_OBJECT_STORAGE.md) para su política y validación real pendiente. Chroma, registros y cachés sobreviven a recrear el contenedor mediante el volumen Docker `ia-data`.

## Errores y ejecución

Los errores tienen forma `{"detail":{"codigo":"...","mensaje":"..."}}`; nunca se presentan como contenido exitoso.

| HTTP | Situación |
|---|---|
| 413 | Documento demasiado grande en bytes (`DOCUMENTO_DEMASIADO_GRANDE`) o demasiado extenso en páginas/texto (`DOCUMENTO_DEMASIADO_EXTENSO`) |
| 415 | Extensión no soportada |
| 422 | Parámetros, documento o contexto rechazado; contenido rechazado por la auditoría de seguridad (`CONTENIDO_RECHAZADO`) |
| 500 | Error interno |
| 502 | Proveedor/procesamiento o respuesta IA inválida |
| 503 | IA ocupada, no configurada, no disponible o proveedor/cuota sin disponibilidad |
| 504 | Timeout del proveedor, pipeline o cliente Backend |

El error `429` del proveedor se publica como `503 PROVEEDOR_CUOTA_AGOTADA`.
`503 PROVEEDOR_NO_DISPONIBLE` se reserva para indisponibilidad o problemas de
comunicación con el proveedor; no confirma un agotamiento de cuota. Backend
conserva HTTP y código, y publica mensajes propios, sin copiar el texto del SDK.
El Frontend muestra ese mensaje y mantiene las acciones para reintentar o
cambiar documento/configuración. No se atribuye el fallo de cuota al documento
ni se promete un tiempo de restablecimiento. No se añaden reintentos automáticos.
Actualizar IA y Backend conjuntamente: un Backend anterior no reconoce el
nuevo código y lo trataría como una respuesta IA inválida.

El endpoint es síncrono. IA procesa una adaptación por vez y responde `503 IA_OCUPADA` a solicitudes concurrentes. Un proceso hijo supervisado aplica el plazo total y libera recursos al agotarlo. Se conservan límites por proveedor y reintentos acotados. `/health` solo comprueba disponibilidad HTTP. No se expone SSE ni un sistema de trabajos persistentes.

## Verificación y pendientes

[Pruebas reproducibles](../../tests/README.md): suite offline sin red y ensayo real con Gemini desde Backend, incluyendo una segunda adaptación después de recrear IA con el mismo volumen. Los resultados no sustituyen una revisión general de calidad para todos los documentos y formatos.

Frontend conecta el formulario al endpoint real mediante el proxy de Nginx y representa los tres formatos públicos y el estado de almacenamiento; consultar su [README](../../frontend/README.md) y las pruebas del proxy con Backend real e IA simulada en `compose.frontend.tests.yaml`. Pendientes: validar Object Storage contra OCI real, implementar SSE y validar el despliegue cloud. Los documentos de planificación y ADR describen objetivos que pueden exceder esta implementación.

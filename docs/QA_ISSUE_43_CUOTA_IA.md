# Issue #43: error de cuota de IA

Validación local del 20 de octubre de 2026 para el
[issue #43](https://github.com/No-Country-simulation/G10-LATAM-EQUIPO15/issues/43).
Base: `release/consolidacion-mvp` en `a29a5cc`. No se desplegó en Azure.

## Diagnóstico y cambio

El adaptador IA traducía tanto el `429` como el `503` del SDK de Google a
`503 PROVEEDOR_NO_DISPONIBLE`. Backend publicaba el mismo mensaje ambiguo para
ambos. El código original y la etapa sí quedaban en los logs.

Ahora el `429` se traduce a `503 PROVEEDOR_CUOTA_AGOTADA`; la indisponibilidad
conserva `PROVEEDOR_NO_DISPONIBLE`. Backend reconoce ambos códigos y genera el
mensaje público, sin copiar detalles privados del proveedor. El transporte HTTP
del Frontend ya mostraba ese mensaje; se actualizó el título de la sección.

Mensaje de cuota:

> **No pudimos procesar tu documento**
>
> El servicio de IA alcanzó su límite de uso. Intenta nuevamente más tarde.
> Si el problema continúa, contacta al equipo de soporte.

Se conservan HTTP `503`, `role="alert"`, las dos acciones de recuperación y los
logs técnicos. No se añaden reintentos automáticos, cambios de modelo ni cambios
de credenciales. Un `429` no identifica por sí solo qué límite se alcanzó ni
cuándo habrá disponibilidad.

**Despliegue:** actualizar IA y Backend conjuntamente. Un Backend anterior no
reconoce `PROVEEDOR_CUOTA_AGOTADA` y lo trataría como una respuesta IA inválida.

## Pruebas automatizadas

Las regresiones fallaron antes de modificar producción: IA confundía el `429`
con indisponibilidad y Backend rechazaba el nuevo código como respuesta inválida.
Después del cambio se ejecutaron las suites completas correspondientes:

| Suite | Resultado |
| --- | --- |
| IA y AI Core, contenedor sin red ni credenciales reales | 115 aprobadas |
| Backend, contenedor sin red ni credenciales reales | 74 aprobadas |
| Frontend unitario, HTTP y proxy Nginx → Backend → IA simulada | 58 aprobadas |
| Total | **247 aprobadas** |

Cobertura específica: traducción de `429` directo y envuelto, distinción de
`503`, propagación HTTP, mensaje público seguro, ausencia de un nuevo reintento
en Backend, limpieza del archivo temporal, conservación de errores existentes y
de los tres formatos de respuesta exitosa.

La prueba de embeddings provoca un `ClientError(429)` dentro de
`provider_call("EMBEDDINGS_DOCUMENTO")`, ejecuta el adaptador y la ruta HTTP IA,
y comprueba los campos seguros `etapa=EMBEDDINGS_DOCUMENTO`, `etapa=INDEXACION`,
`codigo=429 categoria=cuota`, sin registrar el contenido privado de la excepción.
Es una reproducción controlada; no consulta la cuota real.

## Validación en navegador

Se utilizó `compose.frontend.tests.yaml` con IA simulada y un puerto adicional
solo en `127.0.0.1:18004`. Backend e IA permanecieron en la red interna. Los
archivos eran TXT sintéticos de 72 bytes; no se enviaron documentos a Google ni
a OCI. Los nombres `cuota.txt`, `indisponible.txt` y `rechazado.txt` seleccionan
las respuestas del fixture de pruebas; no intervienen en el servicio IA real.

| Caso | Resultado observado |
| --- | --- |
| Cuota, escritorio 1280 × 900 | Título y mensaje nuevos; ambas acciones visibles |
| Cuota, móvil 375 × 812 | Texto y botones legibles; ancho de documento y viewport de 375 px, sin desbordamiento horizontal |
| Reintentar | Una solicitud inicial y una segunda al pulsar; conserva archivo, perfil Senior, Quiz Interactivo y sector Fintech |
| Cambiar documento o configuración | Vuelve a `IDLE`, limpia el archivo y conserva las opciones seleccionadas |
| Proveedor indisponible | Mensaje de indisponibilidad, sin afirmar agotamiento de cuota |
| Rechazo 422 | Conserva el mensaje de fidelidad; no se transforma en cuota |
| Generación exitosa | Llega a `COMPLETED` y muestra Quiz Interactivo |

La consola mostró los `503` y `422` esperados de estas pruebas; no se observaron
excepciones JavaScript adicionales.

Capturas del mismo error controlado, revisadas visualmente:

- [Escritorio](evidencias/issue-43/cuota-desktop.png).
- [Móvil](evidencias/issue-43/cuota-mobile.png).

Para repetir las pruebas HTTP sin proveedores:

```bash
docker compose -p nuevamente-issue43-check -f compose.frontend.tests.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -p nuevamente-issue43-check -f compose.frontend.tests.yaml down
```

## Revisión separada de cuota por Data/IA

**Cuota disponible, proyecto afectado y momento de restablecimiento:
NO DETERMINADO.** No se accedió al panel de la cuenta ni se consumió cuota para
esta corrección. La mejora del mensaje no restablece el límite del proveedor.

El código de Data/IA toma `DATAIA_GOOGLE_API_KEY` o, si falta, `GOOGLE_API_KEY`.
El modelo de embeddings se configura con `GOOGLE_EMBEDDING_MODEL`; su valor
predeterminado es `models/gemini-embedding-001`.

Para cerrar la revisión operativa, Data/IA debe identificar el proyecto de la
clave utilizada y consultar sus límites activos del modelo en
[Google AI Studio](https://aistudio.google.com/rate-limit?timeRange=last-28-days).
Registrar qué límite se alcanzó (peticiones o tokens por minuto, peticiones por
día u otro informado), sin publicar claves ni el contenido del documento.
Google aplica los límites por proyecto, no por clave: cambiar de clave dentro
del mismo proyecto no aporta una cuota independiente. Véase la
[documentación oficial de límites](https://ai.google.dev/gemini-api/docs/rate-limits).

El código ya evita recalcular embeddings de fragmentos idénticos indexados en
Chroma. Esto puede reducir consumo en reenvíos, pero no permite procesar un
documento nuevo cuando su cuota está agotada. El fallback de generación no
sustituye al proveedor de embeddings. No se añadió un fallback de embeddings:
antes requeriría validar el modelo, dimensiones, colección e indexación.

El mensaje permite reintentar más tarde, pero no promete éxito ni un plazo fijo.
La [guía oficial de errores](https://ai.google.dev/gemini-api/docs/troubleshooting)
recomienda reintentos acotados para errores transitorios; este cambio conserva
los límites de reintento existentes y no activa facturación.

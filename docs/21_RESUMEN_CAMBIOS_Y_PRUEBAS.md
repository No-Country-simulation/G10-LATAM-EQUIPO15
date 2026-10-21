# Resumen de cambios y su justificación según las pruebas

**Período:** 20 y 21 de octubre de 2026
**Alcance:** servicio IA (`ia/`), AI Core (`nuevamente-ai-core/`), Backend, Frontend (Nginx), Compose y documentación.
**Documento relacionado:** [Sustentación de las decisiones](22_SUSTENTACION_DECISIONES_RECURSOS_GRATUITOS.md).

## 1. Punto de partida

El proyecto se ejecutó localmente en un entorno Python 3.14 (`.venv`, creado con `uv`), la misma versión de la imagen Docker del servicio IA.

| Suite | Línea base | Final |
|---|---|---|
| IA + AI Core | 111 pasan | 165 pasan |
| Backend | 72 pasan | 75 pasan |
| Scripts (OCI, Azure) | 37 pasan | 37 pasan |
| **Total** | **220** | **277** |

En las dos mediciones, 3 pruebas de `ia/tests/test_pipeline_deadline.py` no pueden ejecutarse en Windows porque usan `multiprocessing.get_context("fork")`, que solo existe en Linux. En Docker sí se ejecutan.

Las pruebas reales usaron Gemini y Groq con cuentas gratuitas y el mismo runner del servicio HTTP: proceso aislado, límite global de 480 s y modo estricto.

## 2. Cambios por área

### 2.1 Auditor de seguridad

**Problema:** el auditor rechazaba cualquier salida que contuviera `<script>`, `javascript:`, `onerror=`, "system prompt" o "you are now". Un documento legítimo sobre seguridad web o sobre LLM no podía procesarse. Además, ese rechazo no tenía código propio y el usuario recibía un error 500 genérico.

**Cambio:**
- El auditor compara contra el texto fuente: solo rechaza un patrón si **no** aparece en el documento, es decir, si lo introdujo el modelo.
- Nuevo error 422 `CONTENIDO_RECHAZADO` en IA y Backend. El Backend solo acepta códigos que conoce, así que sin este cambio lo convertía en 502.

**Evidencia:**
- 5 pruebas nuevas, entre ellas una de punta a punta con un documento sobre XSS.
- El frontend muestra todo con `textContent`, por lo que un `<script>` dentro de una tarjeta se ve como texto y no se ejecuta.

### 2.2 Prompts que forzaban contenido sin sustento

**Problema:** las instrucciones exigían cantidades mínimas ("entre 4 y 8 tarjetas", "entre 3 y 5 preguntas") y campos que la fuente puede no tener:
- trade-offs de costos en el perfil Senior;
- recomendaciones obligatorias en el resumen;
- pista didáctica siempre presente.

Además, el crítico clasificaba los ejemplos de nicho como "didáctica" aunque trajeran datos inventados.

**Cambio:**
- Las cantidades pasaron a ser máximos: "solo las que la fuente sustente".
- Los campos dependen de que el documento los contenga.
- El creador prohíbe cifras, normativas, productos y empresas ausentes en la fuente dentro de los ejemplos de nicho.
- El crítico marca como `no_respaldada` cualquier dato verificable que aparezca en una analogía o un ejemplo y no esté en la fuente.

**Evidencia:**
- El documento de salud (unos 400 tokens) produjo **3 tarjetas** en lugar de completar artificialmente hasta 4.
- Las 11 generaciones reales exitosas con Gemini obtuvieron fidelidad 1.0.
- 9 pruebas de regresión fijan estas reglas.

### 2.3 Filtro de documentos: de lista de palabras a decisión del modelo

**Problema:** se exigían 3 palabras de una lista fija de informática en español, buscadas como subcadenas. El filtro fallaba en dos sentidos:
- **Demasiado estrecho:** rechazaba documentos técnicos de marketing, salud o en inglés.
- **Demasiado laxo:** el libro de Java pasó por casualidad, porque "red" coincide dentro de "requi*red*" y "oci" dentro de "ass*oci*ate".

**Cambio:** la llamada de enriquecimiento, que ya existía y queda en caché por documento, decide `apto_para_aprendizaje`. Se acepta conocimiento técnico, profesional o formativo de cualquier sector e idioma, y se rechaza el texto sin ese contenido con `DOCUMENTO_NO_APTO`. No agrega llamadas al proveedor.

**Evidencia real:**

| Documento | Antes | Después |
|---|---|---|
| Marketing (embudo de conversión) | Rechazado | Aceptado, fidelidad 1.0 |
| Salud (hipertensión) | Rechazado | Aceptado, fidelidad 1.0 |
| Conversación personal | — | Rechazado con 422 |

### 2.4 Límites de contenido para cuentas gratuitas

**Problema:** el único límite era de 10 MiB en bytes. Un libro de 3.421 páginas (8,6 MB, unos 364.000 tokens) entraba, pasaba más de 2 minutos extrayéndose y luego fallaba. Al mismo tiempo, un PDF pesado por imágenes y con pocas páginas podía quedar afuera.

**Cambio:** tres criterios, cada uno con una función:

| Criterio | Valor | Momento | Función |
|---|---|---|---|
| `IA_MAX_PAGINAS` | 50 | Antes de extraer (inmediato) | Rechazo temprano de PDF extensos |
| `IA_MAX_TOKENS_DOCUMENTO` | 24.000 | Después de extraer, cualquier formato | Determina tiempo y costo |
| `IA_MAX_DOCUMENT_BYTES` | 25 MiB | Al recibir | Solo protege el transporte |

El exceso devuelve 413 `DOCUMENTO_DEMASIADO_EXTENSO`. El límite de texto es igual al presupuesto de contexto, así que **todo documento aceptado llega completo** al generador y al crítico.

**Evidencia:**
- El libro de 3.421 páginas se rechaza en **0,15 s**, contra más de 2 minutos antes.
- Los documentos de prueba tienen entre 7 y 22 páginas y entre 400 y 7.600 tokens: todos quedan dentro del límite.

### 2.5 Cadena de respaldo entre proveedores gratuitos

**Problema:**
- Gemini devolvió 503 (sobrecarga) de forma reiterada durante las pruebas, y un solo fallo cortaba la solicitud.
- El respaldo con Groq existía en el código pero nunca se activaba en Docker, porque Compose no pasaba `GROQ_API_KEY`.
- El modelo de Groq configurado, `llama-3.3-70b-versatile`, ya no existe (404).

**Cambio:** el orden es `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` (cuota propia) → Groq (solo generador y crítico).

| Hallazgo con Groq | Corrección |
|---|---|
| `llama-3.3-70b-versatile` devuelve 404 | Modelos disponibles: `openai/gpt-oss-20b` y `openai/gpt-oss-120b` |
| La salida estructurada por llamada a herramientas falló en los 3 modelos con prompts largos (`tool_use_failed`) | Salida por esquema JSON; funcionó en los 3 |
| `gpt-oss` agotaba la salida razonando antes de terminar el JSON (`json_validate_failed`) | `reasoning_effort="low"` y salida máxima de 2.500 tokens |
| Límite medido: 8.000 tokens por minuto **por modelo** | El generador empieza por `20b` y el crítico por `120b`, para no compartir cuota |
| La cadena mostraba solo el error del principal | Cada modelo que falla se registra (`IA modelo=... estado=fallo`), sin contenido |
| `gpt-oss-20b` como juez emitió 1 veredicto; `gpt-oss-120b`, 12 | El crítico usa `120b` primero |

**Evidencia real, solo Groq, simulando Gemini caído:**

| Documento | Tokens | Antes de los ajustes | Después |
|---|---|---|---|
| Salud | ~400 | Éxito | Éxito, 1.0 |
| Marketing | ~400 | Éxito | Éxito, 1.0 |
| Microservicios | 2.300 | Error 400 | Éxito, 1.0 (el crítico pasó a `20b` por cuota y continuó) |
| JWT | 4.200 | 413 | Éxito, 1.0, 8 tarjetas en 10 s |
| VCN | 7.600 | 413 | 413: supera la capacidad gratuita de Groq |

### 2.6 Rendimiento de la ingesta

| Cambio | Antes | Después |
|---|---|---|
| Embeddings opcionales (`DATAIA_EMBEDDINGS_ENABLED=false`) | Se calculaban y no se usaban: la generación lee los fragmentos en orden | Una llamada y un punto de falla menos por documento nuevo |
| Muestra para la metadata del documento (`DATAIA_ENRICH_MAX_CHARS`) | El libro completo (~450.000 tokens) en una llamada: 429 | 12 tramos repartidos: 18,6 s |
| Caché de extracción por hash del archivo | 75 a 130 s en cada solicitud del libro | 0,5 s en la segunda |
| Clasificación de fragmentos solo cuando el documento no entra en el contexto | ~38 lotes de unos 22 s cada uno | 0 lotes en documentos chicos; 3 a 6 en grandes |
| Clasificación en paralelo y tolerante a fallos | Un 503 en un lote cortaba la solicitud | 7 lotes con 503 y el pipeline siguió |

La clasificación solo ordena prioridades al seleccionar contexto; no es contenido. Por eso usar la clase por defecto ante un fallo no afecta la fidelidad.

### 2.7 Cobertura del documento cuando no entra completo

**Problema:** el presupuesto se llenaba en orden de aparición. Con tres secciones iguales, quedaban **10, 4 y 1** fragmentos.

**Cambio:** se garantiza un fragmento por sección, luego una cuota proporcional al tamaño de cada sección, y el sobrante se reparte por turnos. Resultado en la misma prueba: **5, 5 y 5**.

Con los límites de la sección 2.4 este caso ya no ocurre en uso normal; queda como protección si se sube el límite.

### 2.8 Correcciones menores

- `prerrequisitos`: Data/IA guarda `prerequisitos` y AI Core leía `prerrequisitos`, así que la lista llegaba siempre vacía. La prueba anterior usaba un registro simulado con la clave "correcta" y por eso no lo detectaba; la nueva usa el registro real.
- `nuevamente-ai-core/.env.example`: usaba nombres de variables que el código no lee y una clave de Groq de ejemplo (`tu_clave_groq_aqui`) que activaba un respaldo con credenciales falsas.
- Nuevo `ia/.env.example`, la plantilla que pedía el README.
- `.gitignore`: la regla `*.txt` excluía los `requirements*.txt`.
- Se eliminó código sin uso (`TOP_K_FRAGMENTOS`, `_construir_query_pedagogica`).
- `pyrefly.toml` permite que el editor resuelva los imports entre `backend/`, `nuevamente-ai-core/` e `ia/src/`.

### 2.9 Evaluación de calidad con documentos cortos

Se creó un conjunto fijo de 10 documentos sintéticos ([tests/calidad/](../tests/calidad/README.md)): fintech, salud, marketing, e-commerce, software, datos, finanzas, legal, educación y uno en inglés, en Markdown, TXT y PDF. El script `evaluar.py` mide fidelidad, cobertura de secciones, fragmentos citados y cifras o siglas ausentes en la fuente.

La línea base mostró dos problemas propios de los documentos cortos:

- **Citas sin valor:** cada documento (100 a 400 tokens) quedaba en un único fragmento, porque el chunking corta cada 800 tokens. Todos los ítems citaban `F1` y la referencia no permitía ubicar la información.
- **Secciones omitidas:** por ejemplo, la tercera forma normal en el documento de datos y el objetivo del triaje en el de salud.

**Cambios:**
- El chunking separa cada sección en al menos un fragmento. Sin títulos, agrupa párrafos hasta unos 200 tokens, sin partir bloques de código.
- El creador recibe la lista de secciones con la instrucción de cubrirlas todas.

| Métrica (10 casos) | Línea base | Con secciones |
|---|---|---|
| Éxitos | 10/10 | 10/10 |
| Fidelidad media | 1.0 | 1.0 |
| Reintentos | 1 | 0 |
| Cobertura de secciones (media) | 0,81 | 0,94 |
| Fragmentos distintos citados | 1 por documento | 1 por sección (por ejemplo, 5 de 5) |
| Cifras sin respaldo | 0 | 0 |

De las secciones que figuran como no cubiertas, la de software sí está cubierta: la métrica falla en secciones con pocas palabras propias. La de finanzas es el ejemplo numérico, que el resumen ejecutivo omite sin inventar cifras. Las pruebas de chunking también detectaron un error que se corrigió antes de la evaluación: al enmascarar el código con espacios, se perdía el contenido de los bloques de código.

### 2.10 Issue 43: error de cuota al procesar un PDF

El issue tiene dos partes, resueltas por caminos complementarios:

- **Mensaje al usuario (PR #46, D. Méndez):** distingue la cuota agotada (`PROVEEDOR_CUOTA_AGOTADA`) de la indisponibilidad (`PROVEEDOR_NO_DISPONIBLE`), con un título y un mensaje claros, pruebas del Frontend y evidencia visual en [QA_ISSUE_43_CUOTA_IA.md](QA_ISSUE_43_CUOTA_IA.md). Estos cambios conservan esa solución.
- **Causa técnica (estos cambios):** el 429 ocurría en `EMBEDDINGS_DOCUMENTO`, una etapa que la generación no usa. Con los embeddings desactivados por defecto (sección 2.6), esa llamada ya no se hace. Si Gemini responde 429 o 503 en otra etapa, la cadena de respaldo (sección 2.5) intenta con otro modelo de Gemini y luego con Groq antes de mostrar el error.

## 3. Resultado final con Gemini (camino normal)

| Documento | Formato y perfil | Resultado | Fidelidad | Ítems | Tiempo |
|---|---|---|---|---|---|
| Microservicios | Resumen, Ejecutivo, Fintech | Éxito | 1.0 | 5 | 80,5 s |
| JWT en OCI | Flashcards, Junior, Fintech | Éxito | 1.0 | 6 | 146,6 s |
| VCN y subredes | Quiz, Senior, Salud | Éxito | 1.0 | 5 | 65,5 s |
| Marketing | Quiz, Junior, E-commerce | Éxito | 1.0 | 4 | 56,6 s |
| Salud | Flashcards, Junior, Salud | Éxito | 1.0 | 3 | 124,3 s |
| Conversación personal | Flashcards | Rechazado (422) | — | — | 2,4 s |

Los tiempos del 21 de octubre fueron altos por la lentitud de Gemini: un prompt mínimo tardaba entre 17 y 34 s. El 20 de octubre, los mismos documentos tardaron entre 16 y 52 s.

## 4. Pendientes y limitaciones conocidas

- **Sin validar en Docker:** la prueba del proxy Nginx con el límite de 26 MiB, las 3 pruebas de `fork` y las suites de frontend requieren Docker y Node, que no estaban en la máquina de pruebas.
- **Groq gratuito** cubre como respaldo documentos de hasta unos 4.000 a 5.000 tokens.
- **Un documento a la vez:** una segunda solicitud simultánea recibe 503 `IA_OCUPADA`. Es una decisión pendiente del equipo.
- **Cambio en el modo estricto:** ante un fallo, la clasificación de fragmentos usa la clase por defecto, también en modo estricto, porque no es contenido.
- **Revisión manual pendiente:** en el quiz de VCN aparecen dos cifras (13 y 14) que no están en la fuente. En una corrida anterior, las cifras ajenas resultaron ser distractores.
- **Mejoras pendientes de la evaluación:** normalizar las ligaduras de PDF ("ﬁ"), dar a la metadata un respaldo con Groq para documentos muy cortos y evitar ítems redundantes en documentos muy breves.

# Sustentación de las decisiones: recursos gratuitos y documentos cortos

**Fecha:** 21 de octubre de 2026
**Documento relacionado:** [Resumen de cambios y pruebas](21_RESUMEN_CAMBIOS_Y_PRUEBAS.md), con las mediciones que respaldan cada afirmación.

## 1. Criterio rector

NuevaMente es un proyecto académico. Dos condiciones orientan todas las decisiones de este documento:

1. **Solo recursos gratuitos.** El proyecto no puede generar costos para los estudiantes. Esto ya estaba establecido para el almacenamiento en el [ADR-002](adr/002-persistencia-obligatoria-oci-object-storage-always-free.md) (OCI Object Storage Always Free) y se extiende aquí a los proveedores de IA.
2. **Calidad antes que volumen.** Con recursos limitados, es preferible procesar muy bien documentos cortos que procesar a medias documentos extensos. El objetivo es que cada material generado sea fiel a la fuente y útil para estudiar.

De esas dos condiciones se deriva el alcance definido: **documentos de hasta 50 páginas y 24.000 tokens de texto**, aproximadamente 18.000 palabras.

## 2. Recursos utilizados

| Recurso | Uso | Nivel | Límite relevante |
|---|---|---|---|
| Gemini API (Google AI Studio) | Proveedor principal: metadata, generación y crítico | Gratuito | Cuota por proyecto y por modelo; se observaron 429 y 503 |
| Groq Cloud | Último respaldo de generador y crítico | Gratuito | 8.000 tokens por minuto y 1.000 solicitudes por día **por modelo** (medido en los encabezados de respuesta) |
| ChromaDB | Almacén vectorial local, opcional | Software libre, sin servicio externo | — |
| OCI Object Storage | Original y JSON generados | Always Free (ADR-002) | 10 GB |
| Python, LangGraph, LangChain, PyMuPDF | Pipeline | Software libre | — |

No se usa ningún nivel pago. La cuenta Google AI Pro del equipo no se usó en las pruebas: es una suscripción de la app Gemini y, hasta donde se pudo determinar, no equivale al nivel pago de la API. Si se considerara para la demostración, habría que verificar en AI Studio si el proyecto tiene facturación activa.

## 3. Por qué documentos cortos

### 3.1 Lo que mostró la prueba con un documento extenso

Se probó un libro de 3.421 páginas (unos 364.000 tokens) para conocer los límites reales:

| Etapa | Observación |
|---|---|
| Extracción | 75 a 130 s, más de una cuarta parte del límite de 480 s |
| Metadata del documento | Enviado completo (~450.000 tokens) en una llamada: **429**, límite de tokens por minuto |
| Clasificación de fragmentos | ~38 lotes de unos 22 s cada uno, para usar finalmente unos 30 fragmentos |
| Generación | **503** reiterados: el modelo gratuito estaba sobrecargado |

El libro nunca terminó de punta a punta. Cada mejora resolvió un cuello de botella y apareció el siguiente, siempre por un límite del nivel gratuito. Procesar documentos extensos con estos recursos no es confiable.

### 3.2 Lo que ganan los documentos cortos

- **Fidelidad:** con el límite de 24.000 tokens, igual al presupuesto de contexto, todo documento aceptado llega **completo** al generador y al crítico. No hay selección de fragmentos que pueda omitir información, y el crítico verifica cada afirmación contra la fuente entera.
- **Menos llamadas:** con documentos cortos no hace falta clasificar fragmentos.

  | Llamada | Primera solicitud de un documento | Repeticiones del mismo documento |
  |---|---|---|
  | Metadata y pertinencia | 1 | 0 (caché por hash) |
  | Generador | 1 (2 si el crítico pide corrección) | 1 a 2 |
  | Crítico | 1 (2 si hubo corrección) | 1 a 2 |
  | Clasificación de fragmentos | 0 | 0 |
  | **Total** | **3 a 5** | **2 a 4** |

- **Respaldo viable:** Groq gratuito procesa documentos de hasta unos 4.000 a 5.000 tokens (JWT, 4.200 tokens, pasó). Con documentos largos, el respaldo no podría funcionar.
- **Rechazo inmediato:** un documento fuera de alcance se rechaza en 0,15 s con un mensaje claro (413), en lugar de consumir minutos y cuota antes de fallar.

## 4. Decisiones

### D1. Límites por contenido, no por bytes

**Decisión:** máximo de 50 páginas (se revisa antes de extraer) y de 24.000 tokens de texto extraído (cualquier formato). El límite de 25 MiB queda solo para proteger el transporte.

**Alternativa descartada:** limitar solo por bytes. Un PDF con imágenes puede pesar mucho con poco texto, y uno liviano puede tener cientos de páginas. Lo que determina el tiempo y la cuota es el texto.

**Configuración:** `IA_MAX_PAGINAS`, `IA_MAX_TOKENS_DOCUMENTO`, `IA_MAX_DOCUMENT_BYTES`.

### D2. Documento completo en el contexto, sin búsqueda vectorial ni reranking

**Decisión:** la generación usa todos los fragmentos del documento en su orden original.

**Alternativa descartada:** búsqueda por similitud con reranking. Esos mecanismos sirven para responder una pregunta concreta. Aquí el objetivo es cubrir todo el documento para generar material de estudio, y una búsqueda por similitud deja secciones afuera (ya se había descartado en el [documento 20](20_RESOLUCION_INTEGRAL_ARQUITECTURA_DATA_IA.md)).

### D3. Embeddings opcionales y desactivados por defecto

**Decisión:** `DATAIA_EMBEDDINGS_ENABLED=false`. Los fragmentos se guardan en el registro de cada documento.

**Justificación:** ni la generación ni el crítico usan los embeddings, así que no afectan la calidad ni la fidelidad. Calcularlos solo gastaba cuota y agregaba un punto de falla. Se pueden reactivar si en el futuro se agregan pedidos por tema o búsqueda entre varios documentos.

### D4. Cadena de respaldo solo con proveedores gratuitos

**Decisión:** `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` → Groq.
- Cada modelo de Gemini tiene su propia cuota gratuita.
- Groq interviene solo en generador y crítico. La metadata no puede ir por Groq porque su entrada supera el límite de 8.000 tokens.
- En Groq, generador y crítico empiezan por modelos distintos (`gpt-oss-20b` y `gpt-oss-120b`), porque el límite es por modelo y así no se agotan entre sí en el mismo minuto.
- El crítico empieza por `gpt-oss-120b` porque es el juez más riguroso: 12 veredictos frente a 1 de `gpt-oss-20b` sobre el mismo borrador.

**Alternativa descartada:** Groq como proveedor principal. Fue mucho más rápido (8 a 21 s contra 57 a 147 s de Gemini el 21 de octubre), pero con 8.000 tokens por minuto admite aproximadamente una solicitud por minuto. Para una demostración con varios usuarios, Gemini ofrece más margen.

### D5. No sumar cuentas gratuitas para ampliar cuota

**Decisión:** el sistema permite una clave separada para la ingesta (`DATAIA_GOOGLE_API_KEY`), pero no se recomienda crear cuentas adicionales para sumar cuota.

**Justificación:**
- La cuota de Gemini es por proyecto, así que dos claves del mismo proyecto no suman.
- Crear varias cuentas gratuitas para eludir los límites puede contradecir los términos de uso del proveedor; hay que revisarlos antes de hacerlo.
- Una clave adicional no evita los 503, que son sobrecarga del servicio y no falta de cuota.

### D6. Pertinencia del documento decidida por el modelo

**Decisión:** la llamada de metadata, que ya existía y queda en caché, decide si el documento tiene conocimiento del que generar material de estudio, sin importar el sector o el idioma.

**Justificación:** el proyecto debe atender documentos técnicos de distintos sectores (Fintech, salud, marketing, entre otros). La lista fija de palabras de informática rechazaba documentos válidos y aceptaba otros por coincidencias accidentales. El cambio no agrega llamadas al proveedor, lo que respeta el criterio de recursos gratuitos.

### D7. Calidad: no forzar contenido

**Decisión:**
- Las cantidades del formato son máximos ("hasta 8 tarjetas").
- Los campos opcionales se omiten si la fuente no los sustenta.
- Los ejemplos de nicho no pueden introducir cifras, normativas ni productos.
- El crítico trata esos datos como no respaldados.

**Justificación:** con documentos cortos, exigir mínimos empuja al modelo a rellenar con información inventada. Es preferible una tarjeta fiel a varias con relleno. El documento de salud produjo 3 tarjetas, no 4 forzadas, y todas las generaciones reales mantuvieron fidelidad 1.0.

### D8. Qué fallos cortan la solicitud y cuáles no

**Decisión:**
- **Cortan:** los fallos de generación y del crítico, en modo estricto. Sin ellos no hay contenido verificado, y el sistema nunca entrega contenido simulado.
- **No cortan:** los fallos de tareas auxiliares, como la clasificación de fragmentos, que dejan un valor por defecto.

**Justificación:** con proveedores gratuitos los fallos transitorios son frecuentes. Cortar una solicitud por un dato auxiliar desperdicia la cuota ya consumida sin ganar calidad.

### D9. Un fragmento por sección y cobertura de todo el documento

**Decisión:**
- El chunking separa cada sección del documento en al menos un fragmento. Sin títulos, agrupa párrafos hasta unos 200 tokens.
- El generador recibe la lista de secciones con la instrucción de cubrirlas todas.

**Justificación:** el corte por tamaño (800 tokens) estaba pensado para documentos largos. En los documentos cortos, que son el alcance definido, todo quedaba en un único fragmento: cada ítem citaba `F1` y la cita no ayudaba al estudiante a ubicar la información. Además, sin ver la estructura del documento, el modelo omitía secciones enteras.

**Evidencia:**
- La cobertura de secciones pasó de 0,81 a 0,94.
- Cada ítem cita su sección (por ejemplo, 5 fragmentos distintos en un documento de 5 secciones).
- La fidelidad se mantuvo en 1.0.

**Costo:** ninguna llamada adicional. Solo cambia cómo se organiza el texto que ya se enviaba.

### D10. Calidad medida con un conjunto fijo de documentos

**Decisión:** cada cambio en prompts, modelos o pipeline se evalúa con los mismos 10 documentos sintéticos de distintos sectores y formatos ([tests/calidad/](../tests/calidad/README.md)), comparando contra la corrida anterior.

**Justificación:** sin una referencia fija, una mejora en un documento puede empeorar otro sin que nadie lo note. El conjunto se ejecuta con los proveedores gratuitos reales: unas 30 a 50 llamadas por corrida completa, y menos al repetirla, porque la extracción y la metadata quedan en caché. Las métricas (cobertura, citas, cifras y siglas ausentes en la fuente) son señales para revisar a mano, no un veredicto automático.

## 5. Cómo ampliar el alcance si cambian los recursos

Todas las decisiones son configurables sin cambiar código. Si el proyecto accediera a un nivel pago o a cuotas mayores:

| Variable | Valor actual | Efecto de aumentarla |
|---|---|---|
| `IA_MAX_PAGINAS`, `IA_MAX_TOKENS_DOCUMENTO` | 50 / 24.000 | Admite documentos más extensos |
| `IA_CONTEXTO_PRESUPUESTO_TOKENS` | 24.000 | Envía más texto completo al modelo |
| `DATAIA_ENRICH_CONCURRENCY` | 4 | Clasifica más rápido los documentos grandes |
| `DATAIA_EMBEDDINGS_ENABLED` | false | Habilita búsqueda vectorial para funciones futuras |
| `GEMINI_FALLBACK_MODELS`, `GROQ_MODEL`, `GROQ_CRITIC_MODEL` | Modelos gratuitos | Permite usar otros modelos |

Para documentos que no entran completos, el sistema ya tiene una selección que cubre todas las secciones en proporción a su tamaño, y clasifica solo los fragmentos candidatos.

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sobrecarga de Gemini (503) | Respaldo en otro modelo de Gemini y luego en Groq |
| Cuota diaria agotada (429) | Caché de metadata y extracción por documento; menos llamadas por solicitud |
| Lentitud de Gemini en la demostración | Probar con anticipación; considerar Groq como principal para documentos de hasta ~4.000 tokens |
| Documento fuera de alcance | Rechazo inmediato con mensaje claro (413) |
| Dos usuarios simultáneos | Hoy la segunda solicitud recibe 503 `IA_OCUPADA`; decisión pendiente del equipo |
| Error de cuota al procesar un documento (issue 43) | La etapa que lo provocaba (embeddings) ya no se ejecuta; la cadena de respaldo cubre las demás. El mensaje distingue cuota de indisponibilidad (PR #46) |
| Antivirus que inspecciona HTTPS en la máquina de desarrollo (se observó con AVG) | Python rechaza los certificados; exportar los certificados raíz de Windows y definir `SSL_CERT_FILE` ([tests/calidad/README.md](../tests/calidad/README.md)) |

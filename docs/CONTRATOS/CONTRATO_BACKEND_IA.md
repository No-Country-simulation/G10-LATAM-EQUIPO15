# CONTRATO BACKEND ↔ IA — MVP

**Proyecto:** NuevaMente  
**Squads:** Backend + IA/Data  
**Versión:** 2.0  
**Fecha:** 26-09-2026  
**Estado:** 🟡 Base definida — existen decisiones pendientes que deben cerrarse antes de congelar el contrato.

> Este documento es el input operativo de Backend para implementar la integración con IA.
> Cada punto se clasifica como 🟢 CERRADO, 🟡 VALIDAR o 🔴 PENDIENTE.

---

## 1. Objetivo

Definir con precisión qué recibe IA desde Backend, qué devuelve IA, qué responsabilidades tiene cada equipo y qué decisiones todavía deben cerrarse.

### Regla de cierre

    Decisión documentada
            +
    Implementación verificable
            +
    Prueba de integración
            =
          CERRADO

Una decisión documentada no demuestra por sí sola que el código esté implementado.

---

## 2. Estado ejecutivo

| Área | Estado | Impacto para BE |
|---|---|---|
| Perfiles MVP | 🟢 Cerrado | Puede implementarse |
| Formatos MVP | 🟢 Cerrado | Puede implementarse |
| Nicho/Sector | 🟢 Cerrado conceptualmente | Debe enviarse a IA |
| Nivel de detalle | 🟢 Definido | Debe formar parte del request |
| Query Builder | 🟢 Decidido | Es interno de IA |
| conceptos_clave | 🟢 Definido | BE debe esperar el campo |
| tiempo_estimado_estudio_minutos | 🟢 Definido | BE debe esperar el campo |
| Grounding | 🟢 Decisión / 🟡 Validar implementación | BE consume score y observaciones |
| Schema response | 🟢 Definido conceptualmente | Falta validar contra código |
| Archivo → IA | 🟡 Pendiente | Definir archivo, texto o referencia |
| Persistencia OCI | 🟡 Pendiente | Definir responsabilidad |
| Contexto insuficiente | 🔴 Pendiente | Definir respuesta y código |
| Códigos de error | 🟡 Pendiente | BE necesita catálogo estable |
| Evidencia grounding | 🟡 Pendiente | Definir qué retorna IA |
| Telemetría/SSE | 🟡 No bloqueante | Puede quedar fuera del contrato mínimo |

---

## 3. Responsabilidades

### 3.1 Backend — 🟢 Definido

Backend debe:

1. recibir la solicitud;
2. validar parámetros;
3. validar el archivo;
4. gestionar persistencia cuando corresponda;
5. invocar IA;
6. validar la respuesta de IA;
7. exponer la respuesta a Frontend;
8. manejar errores;
9. respetar la versión contractual.

### 3.2 IA/Data — 🟢 Definido

IA debe:

1. procesar documento;
2. extraer y normalizar;
3. realizar chunking;
4. generar embeddings;
5. recuperar contexto;
6. construir queries pedagógicas;
7. generar contenido;
8. aplicar perfil, formato y nicho;
9. ejecutar grounding;
10. validar la salida;
11. devolver el schema acordado.

### 3.3 Frontera de responsabilidades

Backend NO necesita conocer:

- ChromaDB;
- embeddings;
- prompts;
- LangGraph;
- agentes internos;
- estrategia interna de retrieval.

IA NO debe depender de:

- controladores internos de Backend;
- estructura de BD de Backend;
- lógica de Frontend.

---

# 4. Request

## 4.1 Parámetros funcionales

| Campo | Tipo | MVP | Estado | Descripción |
|---|---|---:|---|---|
| documento_titulo | string | Sí | 🟢 | Título del documento |
| documento_contenido | string | ⚠️ | 🟡 | Texto, solo si se acuerda esta modalidad |
| perfil_destinatario | enum | Sí | 🟢 | Perfil objetivo |
| formato_salida | enum | Sí | 🟢 | Formato solicitado |
| nicho_sector | enum | Sí | 🟢 | Contexto sectorial |
| nivel_detalle | enum | Sí | 🟢 | Profundidad |

Ejemplo conceptual:

    {
      "documento_titulo": "Fundamentos de Microservicios",
      "documento_contenido": "...",
      "perfil_destinatario": "Junior",
      "formato_salida": "Flashcards",
      "nicho_sector": "Salud",
      "nivel_detalle": "Didactico"
    }

---

# 5. 🔴 PUNTO CRÍTICO — ¿Qué recibe exactamente IA?

Aquí existe una diferencia entre los documentos revisados.

### Definición documentada por Marco

Backend recibe el archivo, lo valida y lo guarda en OCI. DataIA recibe el archivo crudo + parámetros.

### Schema Pydantic documentado

Utiliza documento_titulo + documento_contenido, es decir, contenido textual.

Esto afecta directamente el endpoint de Backend.

## Pregunta Q1 — 🔴 Alta

**¿El contrato real será archivo crudo, texto extraído o referencia a OCI?**

### Opción A — Archivo crudo

Backend → multipart/form-data → IA

**Pros:** IA controla extracción y preserva estructura.  
**Contras:** IA debe manejar formatos y multipart.

### Opción B — Texto extraído

Archivo → Backend → extracción → texto + parámetros → IA

**Pros:** contrato IA simple.  
**Contras:** Backend asume extracción y puede perder estructura.

### Opción C — Referencia OCI

Backend → OCI → document_id/object_id → IA

**Pros:** evita transportar archivos grandes.  
**Contras:** IA necesita permisos/acceso a OCI.

### Decisión

🔴 **BE + IA deben escoger una modalidad antes de congelar el request.**

---

# 6. Perfiles MVP

🟢 **CERRADO**

Los tres perfiles acordados son:

| Valor técnico | Significado funcional |
|---|---|
| Junior | Principiante / desarrollador junior |
| Senior | Líder Técnico |
| Ejecutivo | Perfil ejecutivo |

### Definición Q2 — 🟢 CERRADA

**Senior = Líder Técnico.**

Para evitar ambigüedad entre el nombre técnico del enum y el nombre funcional utilizado por el equipo, el contrato mantiene `Senior` como valor técnico y establece `Líder Técnico` como su significado funcional.

| Valor técnico | Nombre funcional |
|---|---|
| `Junior` | Principiante / desarrollador junior |
| `Senior` | Líder Técnico |
| `Ejecutivo` | Perfil ejecutivo |

---

# 7. Formatos MVP

🟢 **CERRADO**

| Valor | Estado |
|---|---|
| Flashcards | 🟢 MVP |
| Quiz Interactivo | 🟢 MVP |
| Resumen Ejecutivo | 🟢 MVP |
| Mapa Mental | 📌 Plus |
| Guia Paso a Paso | 📌 Plus |

Backend no debe implementar los formatos Plus como requisito del MVP.

---

# 8. Nicho / sector

🟢 **DECISIÓN CERRADA**

Valores documentados:

- Fintech
- Salud
- E-commerce
- General

El campo NO es decorativo.

Marco estableció que IA lo utilizará en el prompt del generador para adaptar ejemplos, analogías e introducción.

Ejemplo:

    "nicho_sector": "Salud"

puede producir ejemplos contextualizados en hospitales, clínicas o sistemas sanitarios.

**Responsabilidad BE:** validar y enviar el enum.  
**Responsabilidad IA:** utilizarlo.

---

# 9. Nivel de detalle

🟢 **Definido**

Valores:

- Didactico
- Tecnico Intermedio
- Exhaustivo

La especificación documentada propone Didactico como default.

### Pregunta Q3 — 🟠

¿Será obligatorio o tendrá default?

**Alternativa A — default:** simplifica el request y mantiene compatibilidad.

**Alternativa B — obligatorio:** evita solicitudes ambiguas.

BE necesita esta decisión para cerrar validación del endpoint.

---

# 10. Query Builder

🟢 **DECISIÓN ARQUITECTÓNICA CERRADA**

Backend NO construye queries RAG.

IA incorpora:

    perfil + formato + nicho
            ↓
       Query Builder
            ↓
    queries pedagógicas
            ↓
         Retriever

Ejemplo:

Flashcards → definiciones, conceptos clave, terminología.

Quiz → afirmaciones verificables, diferencias, reglas.

Resumen Ejecutivo → objetivos, hallazgos, conclusiones.

BE no necesita implementar esta lógica.

---

# 11. Metadata de aprendizaje

🟢 **Definida**

La respuesta contempla:

    {
      "perfil_aplicado": "Junior",
      "formato_generado": "Flashcards",
      "tiempo_estimado_estudio_minutos": 5,
      "conceptos_clave": ["VCN", "Subredes", "Internet Gateway"],
      "nicho_contexto": "General"
    }

### conceptos_clave — 🟢

Marco indicó que se extraen durante la fase de análisis.

### tiempo_estimado_estudio_minutos — 🟢

Marco indicó que se calcula matemáticamente durante el ensamblado.

Ejemplo documentado: 3 minutos por flashcard, sujeto a la regla final de implementación.

**BE no debe recalcular estos valores.**

---

# 12. Contenido adaptado

🟢 **Schema conceptual definido**

    contenido_adaptado
    ├── titulo
    ├── introduccion_contextualizada
    └── items

### Flashcards

    {
      "frente": "¿Qué es una VCN?",
      "dorso": "Red virtual privada...",
      "pista_didactica": "Piensa en ella como...",
      "categoria_dificultad": "Básico"
    }

### Quiz

La especificación contempla:

- pregunta;
- 4 opciones;
- indice_correcto;
- justificacion_tecnica;
- pista opcional;
- explicación de distractores;
- referencia de fuente.

### Resumen Ejecutivo

Contempla:

- vision_general;
- puntos_clave_negocio;
- consideraciones_arquitectura;
- recomendaciones_implementacion.

---

# 13. Grounding / fidelidad

🟢 **Decisión arquitectónica cerrada**  
🟡 **Implementación y pruebas pendientes de validar**

Marco estableció:

- anclaje_fuente_score entre 0 y 1;
- evaluación mediante LLM-as-a-judge;
- justificación;
- referencia a fragmentos fuente;
- score inferior a 0.85 → corrección;
- máximo de reintentos según política.

Ejemplo:

    {
      "anclaje_fuente_score": 0.92,
      "claridad_pedagogica": "Alta",
      "observaciones": "La respuesta está respaldada por los fragmentos recuperados."
    }

### Responsabilidad BE

Backend NO calcula el score.

Backend consume:

- score;
- clasificación;
- observaciones;
- estado final.

### Pregunta Q4 — 🔴 Alta

¿Qué evidencia exacta devolverá IA?

**A — score + observaciones**

Pros: payload pequeño.  
Contra: trazabilidad limitada.

**B — score + observaciones + IDs de chunks**

Pros: buena trazabilidad con payload controlado.  
Contra: requiere IDs estables.

**C — score + observaciones + fragmentos**

Pros: máxima trazabilidad.  
Contra: response más grande y repetitivo.

🔴 Esta decisión debe cerrarse.

---

# 14. Contexto insuficiente

🔴 **PENDIENTE**

No debemos declarar este punto cerrado.

Caso:

El usuario solicita información sobre Kubernetes, pero el documento únicamente contiene Docker.

IA no debe inventar información.

### Alternativa A — Error controlado

    {
      "status": "error",
      "codigo_respuesta": "INSUFFICIENT_CONTEXT",
      "observaciones": "No existe evidencia suficiente."
    }

**Pro:** simple para BE.  
**Contra:** no permite contenido parcial.

### Alternativa B — Respuesta parcial

    {
      "status": "partial",
      "contenido_adaptado": {},
      "observaciones": "La evidencia disponible es insuficiente."
    }

**Pro:** mejor UX.  
**Contra:** agrega un estado contractual.

### Alternativa C — Recuperación + salida controlada

    Retriever
       ↓
    contexto insuficiente
       ↓
    nueva búsqueda
       ↓
    si falla → respuesta controlada

**Pro:** aprovecha mejor el RAG.  
**Contra:** mayor tiempo y complejidad.

### Preguntas Q5–Q6 — 🔴 Alta

1. ¿Cuándo se considera insuficiente el contexto?
2. ¿IA puede reintentar retrieval?
3. ¿Cuántos intentos?
4. ¿El resultado final es error o partial?
5. ¿Qué código recibe BE?
6. ¿Frontend mostrará mensaje específico?

---

# 15. Evaluación de calidad

🟢 **Definida conceptualmente**

    evaluacion_calidad
    ├── anclaje_fuente_score
    ├── claridad_pedagogica
    ├── observaciones
    └── clasificacion_fidelidad

### Pregunta Q7 — 🟠

¿claridad_pedagogica y clasificacion_fidelidad serán enums?

Alternativa recomendada para contrato:

    Alta | Media | Baja

Esto facilita validación y evita respuestas arbitrarias.

---

# 16. Persistencia OCI

🟡 **Pendiente de responsabilidad definitiva**

La documentación indica que Backend recibe, valida y guarda el archivo en OCI.

Sin embargo, el response documentado por IA incluye:

    almacenamiento_oci
      ├── bucket
      ├── objeto_id
      └── status_upload

Esto genera una contradicción de responsabilidades.

### Pregunta Q8 — 🔴 Alta

**¿Quién persiste cada artefacto?**

### A — Backend

Backend persiste archivo original y contenido generado.

**Pro:** responsabilidad centralizada.  
**Contra:** Backend conoce más del almacenamiento.

### B — IA

IA persiste el resultado generado.

**Pro:** IA controla ciclo completo.  
**Contra:** aumenta acoplamiento IA ↔ OCI.

### C — Responsabilidad separada

Backend → archivo original  
IA → contenido generado

**Pro:** separación clara.  
**Contra:** dos flujos de persistencia.

🔴 Debe resolverse antes de hacer obligatorio almacenamiento_oci en el response.

---

# 17. Errores

🟡 **Catálogo definitivo pendiente**

Propuesta inicial:

| Caso | Código propuesto | Estado |
|---|---|---|
| Request inválido | INVALID_REQUEST | 🟡 |
| Archivo no soportado | UNSUPPORTED_FILE | 🟡 |
| Archivo corrupto/vacío | INVALID_DOCUMENT | 🟡 |
| Contexto insuficiente | INSUFFICIENT_CONTEXT | 🔴 |
| Grounding insuficiente | LOW_GROUNDING | 🟡 |
| Error IA | AI_PROCESSING_ERROR | 🟡 |
| Error almacenamiento | STORAGE_ERROR | 🟡 |
| Éxito | OK | 🟢 |

> Estos valores son propuesta de trabajo, no contrato definitivo.

---

# 18. Telemetría

🟡 **No debe bloquear el contrato mínimo**

La documentación contempla fases como:

- extracción;
- indexación;
- generación;
- auditoría;
- persistencia;
- completado;
- error.

También contempla SSE.

Para el endpoint MVP, la respuesta final puede ser suficiente si el equipo no ha decidido telemetría como requisito.

**Pregunta Q9 — 🟡:** ¿SSE/telemetría es requisito MVP o backlog?

---

# 19. Versionamiento

🟢 **Regla definida**

Todo cambio incompatible requiere:

1. actualizar schema;
2. actualizar documentación;
3. revisar Backend;
4. revisar IA;
5. prueba de integración;
6. registrar la decisión.

Ejemplo:

    /api/v1/adaptar-contenido

Si se rompe el contrato:

    /api/v2/adaptar-contenido

o se define explícitamente una estrategia de compatibilidad.

---

# 20. Criterios de aceptación para Backend

Antes de marcar el contrato como cerrado:

- [ ] modalidad de envío del documento;
- [x] perfiles MVP;
- [x] formatos MVP;
- [x] nicho;
- [x] nivel de detalle definido;
- [ ] request definitivo;
- [ ] response definitivo validado contra código;
- [ ] catálogo de errores;
- [ ] política de contexto insuficiente;
- [ ] evidencia de grounding;
- [ ] responsabilidad OCI;
- [ ] prueba de integración.

---

# 21. Matriz de preguntas para reunión BE + IA

| ID | Pregunta | Prioridad | Impacta desarrollo BE |
|---|---|---|---|
| Q1 | ¿IA recibe archivo, texto o referencia OCI? | 🔴 Alta | Sí, directamente |
| Q2 | ¿Senior = Líder Técnico? | 🟢 Cerrada | No bloquea; definición funcional confirmada |
| Q3 | ¿nivel_detalle obligatorio o default? | 🟠 Media | Sí, validación |
| Q4 | ¿Qué evidencia devuelve grounding? | 🔴 Alta | Sí, response |
| Q5 | ¿Qué es contexto insuficiente? | 🔴 Alta | Sí, estados |
| Q6 | ¿Cuántos reintentos? | 🟠 Media | Sí, timeout/estado |
| Q7 | ¿Campos de calidad serán enums? | 🟠 Media | Sí, schema |
| Q8 | ¿Quién persiste cada artefacto OCI? | 🔴 Alta | Sí, integración |
| Q9 | ¿SSE es MVP o backlog? | 🟡 Media | Puede impactar endpoint |

---

# 22. Qué puede comenzar Backend ahora

🟢 Puede avanzar sin esperar las preguntas abiertas:

- estructura general del endpoint;
- validación de perfiles;
- validación de formatos MVP;
- validación de nichos;
- validación de nivel de detalle;
- estructura base del response;
- validación de schema;
- manejo de estados;
- catálogo de errores como configuración;
- integración desacoplada con IA.

🔴 No debería congelar todavía:

- formato definitivo del documento enviado a IA;
- persistencia OCI;
- comportamiento ante contexto insuficiente;
- estructura final de evidencia de grounding.

---

# 23. Trazabilidad y estado de cierre

La trazabilidad permite identificar **qué decisión se está siguiendo, a qué área pertenece y cuál es su estado actual**. Esto evita confundir una decisión documentada con una implementación ya validada.

### Estados utilizados

| Estado | Significado |
|---|---|
| 🟢 CERRADO | Decisión definida y sin pendientes funcionales. Si además existe implementación y prueba, puede considerarse cerrado técnicamente. |
| 🟡 DEFINIDO / VALIDAR | La decisión está documentada, pero falta validar implementación, pruebas o algún detalle técnico. |
| 🔴 PENDIENTE | Existe una decisión abierta que puede cambiar el diseño o la implementación. |
| 🔵 BACKLOG / PLUS | No forma parte del MVP actual; queda para una versión posterior. |

### Matriz de trazabilidad

| ID | Área | Documento / GAP | Tema | Estado | Impacta BE | Impacta IA | Impacta ARQ |
|---|---|---|---|---|---|---|---|
| ARQ-02 | Arquitectura | ARQ-02 | Alcance MVP | 🟢 CERRADO | Sí | Sí | Sí |
| GAP-01 | Contrato | GAP-01 | Archivo ↔ IA | 🔴 PENDIENTE | Sí | Sí | Sí |
| GAP-02 | Contrato | GAP-02 | JSON | 🟢 CERRADO | Sí | Sí | Sí |
| GAP-03 | IA | GAP-03 | Contexto / recuperación | 🟡 DEFINIDO / VALIDAR | Sí | Sí | Sí |
| GAP-04 | IA | GAP-04 | RAG / Query Builder | 🟢 CERRADO | No | Sí | Sí |
| GAP-05 | IA | GAP-05 | Contexto insuficiente | 🔴 PENDIENTE | Sí | Sí | Sí |
| GAP-06 | IA | GAP-06 | Nicho / sector | 🟢 CERRADO | Sí | Sí | Sí |
| GAP-07 | IA | GAP-07 | Grounding | 🟡 DEFINIDO / VALIDAR | Sí | Sí | Sí |
| GAP-08 | Contrato | GAP-08 | Schema | 🟢 CERRADO | Sí | Sí | Sí |
| IA-05 | IA | IA-05 | Retriever / Query Builder | 🟡 DEFINIDO / VALIDAR | No | Sí | Sí |
| IA-07 | IA | IA-07 | Validación / grounding | 🟡 DEFINIDO / VALIDAR | Sí | Sí | Sí |
| IA-08 | Integración | IA-08 | Integración + JSON | 🟡 DEFINIDO / VALIDAR | Sí | Sí | Sí |

> **Regla práctica:** 🟢 CERRADO en esta matriz indica que la decisión está cerrada documentalmente. No implica por sí solo que el código y las pruebas de integración estén terminados.

---

# 24. Resumen para Backend

    Request
      ├── documento       ← 🔴 definir modalidad
      ├── perfil          ← 🟢
      ├── formato         ← 🟢
      ├── nicho           ← 🟢
      └── nivel detalle   ← 🟢

             ↓

            IA

             ↓

    Response
      ├── status              ← 🟢 conceptual
      ├── metadatos           ← 🟢
      ├── contenido_adaptado  ← 🟢
      ├── evaluacion_calidad  ← 🟡 validar evidencia
      └── codigo_respuesta    ← 🟡 catálogo pendiente

### Los cinco puntos que pueden cambiar directamente la implementación BE

1. modalidad del documento;
2. responsabilidad OCI;
3. contexto insuficiente;
4. evidencia de grounding;
5. catálogo definitivo de errores.

**Estos cinco puntos deben cerrarse antes de considerar congelado el contrato Backend ↔ IA.**

# Schema de Response — MVP

**Proyecto:** NuevaMente  
**Squads:** Backend + IA/Data  
**Versión:** 2.0  
**Fecha:** 26-09-2026  
**Estado:** 🟡 Propuesta técnica para validación BE + IA

> Este documento define la **estructura técnica del Response** que IA entrega a Backend.
>
> La fuente de verdad funcional y de responsabilidades es `CONTRATO_BACKEND_IA.md`. Este documento detalla la forma del payload, sus campos, tipos, reglas de validación y ejemplos.

---

## 1. Objetivo

Definir de forma concreta cómo debe estructurarse la respuesta generada por IA para que Backend pueda:

- validar el payload;
- distinguir éxito, respuesta parcial y error;
- consumir metadatos de aprendizaje;
- consumir el contenido adaptado;
- consumir la evaluación de calidad;
- manejar errores de forma controlada;
- mantener compatibilidad entre versiones.

El schema **no define la implementación interna de IA**. Backend no necesita conocer prompts, LangGraph, embeddings, Chroma, Retriever ni otros componentes internos.

---

## 2. Relación con el contrato Backend ↔ IA

| Documento | Responsabilidad |
|---|---|
| `CONTRATO_BACKEND_IA.md` | Define el acuerdo funcional, responsabilidades, decisiones y pendientes entre BE e IA |
| `SCHEMA_RESPONSE.md` | Define técnicamente la estructura del Response |
| `GAPS/` | Registra problemas, decisiones y brechas que afectan el contrato |
| `ARQ-02_MATRIZ_ALCANCE_MVP.md` | Define alcance y límites del MVP |

### Regla

> Si cambia un campo, enum, estructura obligatoria o comportamiento contractual del Response, deben revisarse ambos documentos.

---

# 3. Response general

La estructura base propuesta es:

```json
{
  "status": "success",
  "codigo_respuesta": "OK",
  "metadatos": {},
  "contenido_adaptado": {},
  "evaluacion_calidad": {}
}
```

### Campos

| Campo | Tipo | Obligatorio | Estado | Descripción |
|---|---|---:|---|---|
| `status` | string/enum | Sí | 🟡 Validar | Estado general de la operación |
| `codigo_respuesta` | string/enum | Sí | 🟡 Validar | Código estable para Backend |
| `metadatos` | object | Sí en éxito | 🟢 Definido | Información de aprendizaje |
| `contenido_adaptado` | object | Sí en éxito | 🟢 Definido | Contenido generado |
| `evaluacion_calidad` | object | Sí en éxito | 🟡 Validar | Resultado de evaluación y grounding |

> Los estados 🟡 reflejan decisiones que todavía deben validarse con Backend/IA antes de congelar el contrato.

---

# 4. Status

Se propone utilizar:

| Valor | Significado |
|---|---|
| `success` | Operación completada correctamente |
| `partial` | Se generó una respuesta parcial/controlada |
| `error` | La operación no pudo completarse |

### Nota

`partial` todavía depende de la decisión del equipo sobre **contexto insuficiente**. No debe considerarse cerrado hasta resolver GAP-05.

---

# 5. Código de respuesta

Catálogo inicial alineado con el contrato Backend ↔ IA:

| Código | Situación | Estado |
|---|---|---|
| `OK` | Operación exitosa | 🟢 |
| `INVALID_REQUEST` | Request inválido | 🟡 |
| `UNSUPPORTED_FILE` | Archivo no soportado | 🟡 |
| `INVALID_DOCUMENT` | Documento corrupto, vacío o inválido | 🟡 |
| `INSUFFICIENT_CONTEXT` | Evidencia insuficiente para responder | 🔴 GAP-05 |
| `LOW_GROUNDING` | Grounding por debajo del umbral definido | 🟡 GAP-07 |
| `AI_PROCESSING_ERROR` | Error durante procesamiento IA | 🟡 |
| `STORAGE_ERROR` | Error de almacenamiento | 🟡 |

> Estos códigos son propuesta de trabajo hasta que BE + IA aprueben el catálogo definitivo.

---

# 6. Metadatos de aprendizaje

## 6.1 Estructura

```json
{
  "perfil_aplicado": "Junior",
  "formato_generado": "Flashcards",
  "tiempo_estimado_estudio_minutos": 5,
  "conceptos_clave": [
    "VCN",
    "Subredes",
    "Internet Gateway"
  ],
  "nicho_contexto": "General"
}
```

## 6.2 Campos

| Campo | Tipo | Obligatorio | Estado |
|---|---|---:|---|
| `perfil_aplicado` | enum | Sí | 🟢 |
| `formato_generado` | enum | Sí | 🟢 |
| `tiempo_estimado_estudio_minutos` | integer | Sí | 🟢 |
| `conceptos_clave` | array[string] | Sí | 🟢 |
| `nicho_contexto` | enum | Sí | 🟢 |

### Valores contractuales

**Perfil**

- `Junior`
- `Senior` — Líder Técnico
- `Ejecutivo`

**Formato MVP**

- `Flashcards`
- `Quiz Interactivo`
- `Resumen Ejecutivo`
- `Mapa Mental`

**Nicho**

- `Fintech`
- `Salud`
- `E-commerce`
- `General`

**Nivel de detalle**

El `nivel_detalle` pertenece al Request. IA lo utiliza para adaptar la generación, pero no necesariamente debe repetirse en el Response salvo que el contrato definitivo así lo establezca.

---

# 7. Contenido adaptado

## 7.1 Estructura común

```json
{
  "titulo": "Fundamentos de Redes",
  "introduccion_contextualizada": "Introducción adaptada al perfil y contexto.",
  "items": []
}
```

| Campo | Tipo | Obligatorio |
|---|---|---:|
| `titulo` | string | Sí |
| `introduccion_contextualizada` | string | Sí |
| `items` | array/object según formato | Sí |

---

# 8. Flashcards — MVP

## Estructura

```json
{
  "titulo": "Fundamentos de Redes",
  "introduccion_contextualizada": "Conceptos esenciales para comenzar.",
  "items": [
    {
      "frente": "¿Qué es una VCN?",
      "dorso": "Una red virtual privada...",
      "pista_didactica": "Piensa en una red aislada dentro de la nube.",
      "categoria_dificultad": "Básico",
      "identificador": "FC-001"
    }
  ]
}
```

## Campos

| Campo | Tipo | Estado |
|---|---|---|
| `frente` | string | 🟢 |
| `dorso` | string | 🟢 |
| `pista_didactica` | string | 🟢 |
| `categoria_dificultad` | string | 🟡 Validar |
| `identificador` | string | 🟡 Validar |

---

# 9. Quiz Interactivo — MVP

## Estructura

```json
{
  "titulo": "Quiz de Redes",
  "introduccion_contextualizada": "Evalúa los conceptos principales.",
  "items": [
    {
      "pregunta": "¿Qué función cumple una VCN?",
      "opciones": [
        "Opción A",
        "Opción B",
        "Opción C",
        "Opción D"
      ],
      "indice_correcto": 1,
      "justificacion_tecnica": "Explicación de la respuesta correcta.",
      "pista_didactica": "Recuerda el concepto de red virtual.",
      "explicacion_distractores": "Por qué las demás opciones no corresponden.",
      "referencia_fuente": "chunk-001",
      "identificador": "QZ-001"
    }
  ]
}
```

## Campos

| Campo | Tipo | Estado |
|---|---|---|
| `pregunta` | string | 🟢 |
| `opciones` | array[string] | 🟢 |
| `indice_correcto` | integer | 🟢 |
| `justificacion_tecnica` | string | 🟢 |
| `pista_didactica` | string | 🟡 Opcional |
| `explicacion_distractores` | string | 🟡 Opcional |
| `referencia_fuente` | string | 🟡 Validar |
| `identificador` | string | 🟡 Validar |

### Regla

El MVP contempla **4 opciones** por pregunta.

---

# 10. Resumen Ejecutivo — MVP

## Estructura propuesta

```json
{
  "titulo": "Arquitectura de la solución",
  "introduccion_contextualizada": "Síntesis orientada al perfil ejecutivo.",
  "items": {
    "vision_general": "Descripción general.",
    "puntos_clave_negocio": [
      "Punto 1",
      "Punto 2"
    ],
    "consideraciones_arquitectura": [
      "Consideración 1"
    ],
    "recomendaciones_implementacion": [
      "Recomendación 1"
    ]
  }
}
```

| Campo | Tipo | Estado |
|---|---|---|
| `vision_general` | string | 🟢 |
| `puntos_clave_negocio` | array[string] | 🟢 |
| `consideraciones_arquitectura` | array[string] | 🟢 |
| `recomendaciones_implementacion` | array[string] | 🟢 |

---

# 11. Mapa Mental — MVP

El Mapa Mental forma parte ahora del MVP.

## Estructura propuesta

```json
{
  "titulo": "Arquitectura RAG",
  "introduccion_contextualizada": "Mapa conceptual de los componentes principales.",
  "items": {
    "nodo_central": "RAG",
    "descripcion_general": "Sistema de recuperación aumentada por generación.",
    "ramas_principales": [
      {
        "nombre": "Retrieval",
        "descripcion": "Recuperación de información relevante.",
        "subnodos": [
          {
            "nombre": "Retriever",
            "descripcion": "Busca fragmentos relevantes."
          },
          {
            "nombre": "Vector Store",
            "descripcion": "Almacena representaciones vectoriales."
          }
        ]
      }
    ]
  }
}
```

### Estructura conceptual

```text
MapaMental
│
├── nodo_central
├── descripcion_general
└── ramas_principales[]
      │
      └── SubnodoConceptual[]
```

| Campo | Tipo | Estado |
|---|---|---|
| `nodo_central` | string | 🟢 |
| `descripcion_general` | string | 🟢 |
| `ramas_principales` | array | 🟢 |
| `nombre` de rama | string | 🟢 |
| `descripcion` de rama | string | 🟡 Validar |
| `subnodos` | array | 🟢 |
| `nombre` de subnodo | string | 🟢 |
| `descripcion` de subnodo | string | 🟢 |

### Responsabilidades

- **IA:** genera la estructura conceptual.
- **Backend:** valida y transporta el schema.
- **Frontend:** representa visualmente el mapa.

Backend no necesita conocer cómo IA construye internamente el mapa.

---

# 12. Evaluación de calidad

## Estructura

```json
{
  "anclaje_fuente_score": 0.92,
  "claridad_pedagogica": "Alta",
  "observaciones": "La respuesta está respaldada por los fragmentos recuperados.",
  "clasificacion_fidelidad": "Alta"
}
```

| Campo | Tipo | Estado |
|---|---|---|
| `anclaje_fuente_score` | number 0..1 | 🟢 |
| `claridad_pedagogica` | string/enum | 🟡 Validar |
| `observaciones` | string | 🟢 |
| `clasificacion_fidelidad` | string/enum | 🟡 Validar |

### Grounding

La decisión arquitectónica documentada contempla:

- evaluación mediante LLM-as-a-judge;
- score entre 0 y 1;
- umbral de grounding;
- corrección/reintento cuando el score sea inferior al umbral definido;
- referencia a evidencia fuente.

El contrato todavía debe cerrar **qué evidencia exacta devuelve IA**:

1. score + observaciones;
2. score + observaciones + IDs de chunks;
3. score + observaciones + fragmentos fuente.

Por tanto, la estructura definitiva de evidencia queda marcada como 🟡/🔴 según GAP-07.

---

# 13. Contexto insuficiente

El comportamiento ante contexto insuficiente todavía está pendiente de cierre mediante GAP-05.

Ejemplo conceptual:

```json
{
  "status": "error",
  "codigo_respuesta": "INSUFFICIENT_CONTEXT",
  "metadatos": {},
  "contenido_adaptado": null,
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0,
    "observaciones": "No existe evidencia suficiente para responder."
  }
}
```

La estructura definitiva dependerá de la decisión BE + IA sobre:

- criterio de insuficiencia;
- reintentos de retrieval;
- máximo de reintentos;
- `error` vs `partial`;
- comportamiento de Frontend.

---

# 14. Errores y respuestas controladas

Un error contractual debe ser identificable por Backend mediante `status` y `codigo_respuesta`.

### Ejemplo

```json
{
  "status": "error",
  "codigo_respuesta": "INVALID_DOCUMENT",
  "metadatos": null,
  "contenido_adaptado": null,
  "evaluacion_calidad": null
}
```

### Regla

En una respuesta de error no debe enviarse contenido adaptado como si fuera una respuesta exitosa.

La forma definitiva de los payloads de error debe alinearse con el catálogo aprobado por BE + IA.

---

# 15. Ejemplos completos

## 15.1 Success — Flashcards

```json
{
  "status": "success",
  "codigo_respuesta": "OK",
  "metadatos": {
    "perfil_aplicado": "Junior",
    "formato_generado": "Flashcards",
    "tiempo_estimado_estudio_minutos": 5,
    "conceptos_clave": [
      "VCN",
      "Subredes"
    ],
    "nicho_contexto": "General"
  },
  "contenido_adaptado": {
    "titulo": "Fundamentos de Redes",
    "introduccion_contextualizada": "Conceptos esenciales.",
    "items": [
      {
        "frente": "¿Qué es una VCN?",
        "dorso": "Una red virtual privada.",
        "pista_didactica": "Piensa en una red aislada.",
        "categoria_dificultad": "Básico",
        "identificador": "FC-001"
      }
    ]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.92,
    "claridad_pedagogica": "Alta",
    "observaciones": "Contenido respaldado por la fuente.",
    "clasificacion_fidelidad": "Alta"
  }
}
```

## 15.2 Success — Mapa Mental

```json
{
  "status": "success",
  "codigo_respuesta": "OK",
  "metadatos": {
    "perfil_aplicado": "Senior",
    "formato_generado": "Mapa Mental",
    "tiempo_estimado_estudio_minutos": 10,
    "conceptos_clave": [
      "RAG",
      "Retriever",
      "Embeddings"
    ],
    "nicho_contexto": "General"
  },
  "contenido_adaptado": {
    "titulo": "Arquitectura RAG",
    "introduccion_contextualizada": "Vista general de la arquitectura.",
    "items": {
      "nodo_central": "RAG",
      "descripcion_general": "Recuperación aumentada por generación.",
      "ramas_principales": [
        {
          "nombre": "Retrieval",
          "descripcion": "Recuperación de información.",
          "subnodos": [
            {
              "nombre": "Retriever",
              "descripcion": "Busca fragmentos relevantes."
            }
          ]
        }
      ]
    }
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.91,
    "claridad_pedagogica": "Alta",
    "observaciones": "La estructura se encuentra respaldada por la fuente.",
    "clasificacion_fidelidad": "Alta"
  }
}
```

---

# 16. Reglas de validación

Backend debe validar como mínimo:

### Estructura

- Response no nulo.
- Campos obligatorios presentes cuando corresponda.
- Tipos correctos.
- Objetos anidados válidos.

### Enums

- Perfil válido.
- Formato válido.
- Nicho válido.
- Códigos de respuesta válidos una vez aprobado el catálogo.

### Contenido

- Si `status = success`, debe existir contenido adaptado.
- Si `status = error`, no debe tratarse el contenido como exitoso.
- El contenido debe corresponder al `formato_generado`.

### Grounding

- `anclaje_fuente_score` debe estar entre 0 y 1.
- Las reglas definitivas de evidencia quedan pendientes de GAP-07.

---

# 17. Compatibilidad y versionado

Este schema forma parte del contrato de integración.

Cambios compatibles:

- agregar campos opcionales;
- agregar información no obligatoria sin romper consumidores.

Cambios potencialmente incompatibles:

- eliminar campos;
- cambiar tipos;
- renombrar campos;
- cambiar enums;
- cambiar estructuras obligatorias;
- modificar el significado de un campo.

Ante un cambio incompatible:

1. actualizar este documento;
2. actualizar `CONTRATO_BACKEND_IA.md`;
3. revisar Backend;
4. revisar IA;
5. ejecutar prueba de integración;
6. registrar la decisión;
7. actualizar la versión del contrato.

---

# 18. Criterios de aceptación

El schema podrá considerarse **cerrado técnicamente** cuando:

- [x] estructura general definida;
- [x] metadatos definidos;
- [x] Flashcards definido;
- [x] Quiz definido;
- [x] Resumen Ejecutivo definido;
- [x] Mapa Mental incorporado al MVP;
- [ ] catálogo de errores aprobado;
- [ ] comportamiento ante contexto insuficiente aprobado;
- [ ] evidencia de grounding definida;
- [ ] enums de calidad definidos;
- [ ] validación contra implementación IA;
- [ ] prueba de integración BE ↔ IA.

---

# 19. Trazabilidad

| Elemento | Relación | Estado |
|---|---|---|
| ARQ-02 | Alcance de formatos MVP | 🟢 |
| GAP-02 | Contrato JSON | 🟢 |
| GAP-05 | Contexto insuficiente | 🔴 |
| GAP-07 | Grounding / evidencia | 🟡 |
| GAP-08 | Schema de validación | 🟢 |
| IA-08 | Integración + JSON | 🟡 |

> Este documento debe evolucionar junto con el contrato Backend ↔ IA. No debe convertirse en una definición independiente o contradictoria.

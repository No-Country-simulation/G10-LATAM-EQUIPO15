# Schema Response — Backend ↔ IA

Versión 2.3 — 08-10-2026. Referencia: [Contrato Backend ↔ IA](CONTRATO_BACKEND_IA.md). Los schemas ejecutables están en `backend/app/api/schemas.py` y `nuevamente-ai-core/src/ai/schemas.py`; consultar `/openapi.json` para sus restricciones exactas.

## Respuesta exitosa

HTTP 200 devuelve seis campos obligatorios:

| Campo | Contenido |
|---|---|
| `status` | AI Core emite `exito`; Backend también acepta `success` por compatibilidad |
| `metadatos` | Perfil, formato, nicho, conceptos clave y tiempo de estudio |
| `contenido_adaptado` | Título, introducción contextualizada e items tipados por formato |
| `evaluacion_calidad` | Score entre 0 y 1, observaciones, claridad, reintentos y evidencia opcional |
| `almacenamiento_oci` | Bucket, objeto propuesto, estado pendiente de subida y ruta opcional |
| `codigo_respuesta` | Número `200`, no cadena `OK` |

`metadatos` requiere `perfil_aplicado`, `formato_generado`, `tiempo_estimado_estudio_minutos` (1–180) y `conceptos_clave` (lista no vacía). `nicho_contexto` tiene valor predeterminado `General`. Backend exige que perfil, formato y nicho coincidan con la solicitud.

## Items por formato público

| Formato | Tipo y campos |
|---|---|
| Flashcards | Lista: `frente`, `dorso`; pista, dificultad y `fuentes` opcionales |
| Quiz Interactivo | Lista: `pregunta`, cuatro `opciones`, `indice_correcto` 0–3, `justificacion_tecnica`; pista, explicación de distractores y `fuentes` opcionales |
| Resumen Ejecutivo | Objeto: `tldr`, `impacto_negocio`, listas `puntos_clave` y `recomendaciones`; `fuentes` opcional |

Los identificadores `F1`, `F2`, etc. se refieren al contexto seleccionado para la generación. No son enlaces públicos ni sustituyen una exportación de la fuente. Backend conserva los campos adicionales de IA y valida que la estructura corresponda al formato declarado.

Ejemplo ilustrativo (no resultado de una subida a OCI):

```json
{
  "status": "exito",
  "metadatos": {
    "perfil_aplicado": "Junior",
    "formato_generado": "Flashcards",
    "tiempo_estimado_estudio_minutos": 3,
    "conceptos_clave": ["JWT"],
    "nicho_contexto": "General"
  },
  "contenido_adaptado": {
    "titulo": "JWT",
    "introduccion_contextualizada": "Conceptos del documento.",
    "items": [{"frente": "¿Qué verifica la firma?", "dorso": "La integridad del token.", "fuentes": ["F1"]}]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.95,
    "claridad_pedagogica": "Alta",
    "observaciones": "Afirmaciones respaldadas por los fragmentos.",
    "reintentos_realizados": 0,
    "evidencia": ["F1"]
  },
  "almacenamiento_oci": {
    "bucket": "nuevamente-contenidos-educativos",
    "objeto_id": "ejemplo.json",
    "status_upload": "listo_para_subida",
    "ruta_publica_o_par": null
  },
  "codigo_respuesta": 200
}
```

## Respuesta de error

```json
{"detail":{"codigo":"CONTEXTO_INSUFICIENTE","mensaje":"IA rechazó el contenido por no alcanzar su criterio de fidelidad."}}
```

El estado HTTP expresa el fallo; no se devuelve contenido exitoso parcial. Backend rechaza con 502 las respuestas vacías, malformadas, de formato incorrecto, con score fuera de rango o sin los campos obligatorios. No inventa los campos faltantes ni recalcula los valores devueltos por IA.

## Compatibilidad

La restitución de calidad, almacenamiento y código numérico, junto con la retirada pública de Mapa Mental, requiere actualizar consumidores. El request continúa siendo multipart de cuatro campos. Los planes antiguos con DOCX, `request_id`, `nivel_detalle`, `status: error` o código `OK` no describen esta API.

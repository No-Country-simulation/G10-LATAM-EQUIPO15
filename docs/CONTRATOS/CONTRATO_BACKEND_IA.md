# Contrato Backend ↔ IA

## 1. Objetivo

Establecer el contrato mínimo entre Backend e IA para evitar acoplamiento implícito y diferencias de interpretación.

## 2. Request conceptual

```json
{
  "documento": {
    "nombre": "documento.pdf",
    "tipo": "application/pdf",
    "contenido": "<contenido o referencia acordada>"
  },
  "perfil_destinatario": "Junior",
  "formato_salida": "Flashcards",
  "nicho_sector": "General",
  "nivel_detalle": "Didactico"
}
```

Los nombres definitivos deben mantenerse alineados con el schema implementado.

## 3. Response conceptual

```json
{
  "status": "success",
  "metadatos": {},
  "contenido_adaptado": {},
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.0,
    "observaciones": []
  },
  "codigo_respuesta": "OK"
}
```

## 4. Reglas

- Backend no debe depender de detalles internos del RAG.
- IA no debe depender de la implementación interna del Backend.
- Los enums deben ser compartidos y versionados.
- Los errores deben tener códigos determinísticos.
- El schema debe validarse antes de responder.
- Los campos de grounding deben formar parte del contrato cuando el MVP los requiera.

## 5. Responsabilidades

| Área | Responsabilidad |
|---|---|
| Backend | recibir request, validar entrada, gestionar archivo y consumir contrato IA |
| IA/Data | procesar documento, recuperar contexto, generar y validar |
| Backend | exponer response al cliente |
| Ambos | versionar cambios incompatibles |

## 6. Cambios de contrato

Todo cambio incompatible requiere:

1. actualización del schema;
2. actualización de documentación;
3. revisión de consumidores;
4. prueba de integración;
5. registro de la decisión.

## 7. Trazabilidad

Este contrato se relaciona con ARQ-02 y con los GAP de archivo, JSON, grounding y schema.

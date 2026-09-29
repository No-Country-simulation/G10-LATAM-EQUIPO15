# Matriz de GAPs — IA / Data

## Propósito

Registrar los principales GAP identificados durante la alineación de arquitectura y su estado documental.

| GAP | Tema | Estado documental | Evidencia de implementación |
|---|---|---|---|
| GAP-01 | Contrato archivo ↔ IA | Definido | Validar transporte e integración |
| GAP-02 | Contrato JSON | Cerrado | Pendiente de validación |
| GAP-03 | Contexto / recuperación | Parcial | Pendiente |
| GAP-04 | Estrategia RAG / Query Builder | Cerrado | Pendiente de validación |
| GAP-05 | Contexto insuficiente | Pendiente de formalización | Pendiente |
| GAP-06 | Nicho / sector | Cerrado | Pendiente de validación |
| GAP-07 | Grounding / score | Decisión cerrada | Implementación y pruebas pendientes |
| GAP-08 | Schema de validación | Cerrado | Pendiente de validación |

## Regla

**Documentado ≠ implementado.**

Para cerrar definitivamente un GAP se requiere:

```
Decisión documentada
        +
Implementación verificable
        +
Prueba / evidencia
        =
CERRADO
```

## Actualización GAP-01

La frontera funcional de entrada quedó definida:

- Backend entrega el documento original, sin extracción ni tratamiento.
- Backend entrega los parámetros funcionales.
- Data/IA realiza validación inicial, detección de formato, extracción y normalización.
- Formatos inicialmente soportados: PDF, DOCX, Markdown y TXT.

La decisión funcional está cerrada; la implementación y la prueba de integración quedan pendientes de validación.

## Próximo foco

GAP-05 debe contar con una política explícita para determinar qué ocurre cuando el contexto recuperado no es suficiente para responder.

GAP-03 y GAP-07 requieren evidencia técnica antes de considerarse completamente cerrados.

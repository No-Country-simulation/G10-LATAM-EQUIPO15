# DOSSIER DE DOCUMENTACIÓN — NUEVAMENTE

## Proyecto

**NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo**

**Hackathon:** ONE (Oracle Next Education) & Alura Latam — Cohorte G-10

---

## 1. Fuente de verdad técnica

La documentación se organiza en tres niveles:

1. **Arquitectura y alcance:** decisiones que definen qué construimos.
2. **IA / Data y contratos:** cómo funciona el pipeline y cómo se integra con Backend.
3. **GAPs y decisiones:** trazabilidad de problemas, acuerdos y pendientes.

La documentación debe reflejar las decisiones reales del equipo. Los documentos de referencia externos o históricos no sustituyen la evidencia de implementación del repositorio.

---

## 2. Documentos principales

| Documento | Propósito |
|---|---|
| [ARQ-02 — Matriz de Alcance MVP](./ARQ-02_MATRIZ_ALCANCE_MVP.md) | Fuente de verdad del alcance de IA/Data. |
| [Pipeline de IA MVP](./IA/PIPELINE_IA_MVP.md) | Flujo técnico completo de IA. |
| [Estrategia RAG MVP](./IA/ESTRATEGIA_RAG_MVP.md) | Recuperación, Query Builder y contexto. |
| [Grounding y Validación](./IA/GROUNDING_Y_VALIDACION.md) | Fidelidad, score y corrección. |
| [Contrato Backend ↔ IA](./CONTRATOS/CONTRATO_BACKEND_IA.md) | Contrato de integración entre equipos. |
| [Schema Response](./CONTRATOS/SCHEMA_RESPONSE.md) | Estructura y validación de respuesta. |
| [Matriz de GAPs](./GAPS/README_GAPS.md) | Estado y trazabilidad de GAP-01 a GAP-08. |

---

## 3. Criterio de mantenimiento

Cada documento debe indicar:

- objetivo;
- alcance;
- estado;
- decisiones;
- criterios de aceptación;
- dependencias;
- trazabilidad cuando corresponda.

No se deben declarar componentes como implementados únicamente porque estén descritos en documentación.

---

## 4. Regla de cierre

**CERRADO = decisión documentada + implementación verificable + prueba/evidencia.**

Cuando falta implementación o evidencia, el estado debe ser **DECIDIDO / PENDIENTE DE VALIDACIÓN**.

---

## 5. Estructura existente

Además de esta documentación de IA/Data, el repositorio puede incorporar progresivamente:

- PRD;
- arquitectura general;
- WBS;
- timeline;
- ADR;
- documentación Backend;
- documentación Frontend;
- documentación OCI.

Estos documentos deben mantenerse alineados con ARQ-02 y con los contratos de integración.

---

## 6. Hackathon

Proyecto desarrollado para el Hackathon ONE G10 / Alura Latam.

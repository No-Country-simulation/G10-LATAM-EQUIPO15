# Documentación de NuevaMente

La referencia operativa es el código consolidado, los README de ejecución y las pruebas reproducibles. Los planes y ADR registran decisiones y objetivos; no demuestran que un componente está implementado.

## Ejecución y contratos vigentes

- [README del proyecto](../README.md)
- [Backend](../backend/README.md), [Data/IA y servicio HTTP](../ia/README.md), [Frontend](../frontend/README.md)
- [Pruebas reproducibles offline y Gemini](../tests/README.md)
- [Contrato Backend ↔ IA v2.3](CONTRATOS/CONTRATO_BACKEND_IA.md)
- [Schema Response v2.3](CONTRATOS/SCHEMA_RESPONSE.md)

La API pública acepta PDF, Markdown y TXT y devuelve Flashcards, Quiz Interactivo o Resumen Ejecutivo. Calidad y estado pendiente de almacenamiento acompañan la salida. El Frontend envía multipart al Backend mediante Nginx y representa los tres formatos. OCI Object Storage, despliegue cloud y SSE continúan pendientes.

## Arquitectura y seguimiento

- [Matriz de alcance MVP](ARQ-02_MATRIZ_ALCANCE_MVP.md)
- [Pipeline IA](IA/PIPELINE_IA_MVP.md)
- [Estrategia RAG](IA/ESTRATEGIA_RAG_MVP.md)
- [Grounding y validación](IA/GROUNDING_Y_VALIDACION.md)
- [Matriz de GAPs](GAPS/README_GAPS.md)
- [Alineación de arquitectura](ALINEACION_ARQUITECTURA_MVP.md)
- [Checklist maestro](CHECKLIST_MAESTRO_AVANCES_Y_HITOS.md)

Estos documentos conservan antecedentes y propuestas. Ante diferencias de enums, transporte, recuperación o salida, prevalecen los contratos v2.3 y los schemas ejecutables.

## Aportes Data/IA y AI Core

- [Mejoras Fase A](18_MEJORAS_DATA_IA_FASE_A.md): ingesta, chunking, hash, cachés y vector store.
- [Propuesta AI Core](19_PROPUESTA_CAMBIOS_AI_CORE.md): propuestas posteriores a la Fase A.
- [Resolución integral de Marcos](20_RESOLUCION_INTEGRAL_ARQUITECTURA_DATA_IA.md): cambios y pendientes identificados por AI Core.
- [Reporte de integración](18_REPORTE_INTEGRACION_DATAIA_LANGGRAPH.md)
- [Formatos de salida](16_FORMATOS_DE_SALIDA_JSON.md)

## Dossier y planes

Los documentos numerados 01–17 contienen PRD, diseño, WBS, cronograma, contratos iniciales, arquitectura, prácticas, planes por squad, reportes y evaluación. `adr/` conserva las decisiones de orquestación, OCI y telemetría. También hay planes en `plan_squad_ia_data/` y especificaciones en `specs/`.

Para cerrar un pendiente se requiere decisión documentada, implementación verificable y prueba. No presentar como desplegado un objetivo que solo aparece en estos planes.

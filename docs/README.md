# DOSSIER DE DOCUMENTACIÓN — NUEVAMENTE

## Proyecto

**NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo**

**Hackathon:** ONE (Oracle Next Education) & Alura Latam — Cohorte G-10

> **Nota de estado:** Este dossier parte de la documentación técnica propuesta inicialmente por Marco. Los documentos se incorporarán y revisarán progresivamente para alinearlos con las decisiones reales del equipo, el alcance del MVP y la estructura actual del repositorio.

---

## 1. Documentación prevista

La documentación técnica se organizará en los siguientes documentos:

| Documento | Propósito |
|---|---|
| `01_PRD_PRODUCT_REQUIREMENTS_DOCUMENT.md` | Requisitos de producto, visión, perfiles y requisitos funcionales. |
| `02_SISTEMA_DE_DISENO_Y_UI_UX.md` | Lineamientos de diseño, componentes y experiencia de usuario. |
| `03_WBS_Y_DEFINICION_DE_TAREAS.md` | Desglose de trabajo, responsabilidades y dependencias. |
| `04_TIMELINE_EXTENDIDO_Y_HITOS.md` | Cronograma, hitos y puntos de control. |
| `05_CONTRATOS_DE_DATOS_Y_SCHEMAS.md` | Contratos de datos y esquemas de entrada/salida. |
| `06_ARQUITECTURA_DE_IA_Y_SISTEMA_MULTIAGENTE.md` | Arquitectura de IA, RAG, embeddings, LLM y orquestación. |
| `07_DIAGRAMAS_DE_ARQUITECTURA_Y_FLUJOS.md` | Diagramas de arquitectura, flujos e integración. |
| `08_BUENAS_PRACTICAS_SKILLS_Y_RESILIENCIA.md` | Buenas prácticas, manejo de errores y resiliencia. |
| `adr/` | Registros de decisiones arquitectónicas relevantes. |

---

## 2. Criterio de mantenimiento

La documentación no debe convertirse en una carga adicional para los equipos.

Cada equipo es responsable principalmente de:

- subir y mantener su código;
- mantener la documentación mínima necesaria para instalar, ejecutar y entender su componente;
- registrar decisiones técnicas relevantes cuando afecten la integración con otros equipos.

La documentación transversal del proyecto se mantendrá en esta carpeta.

---

## 3. Estado de la documentación

Los documentos propuestos por Marco se consideran **material de referencia inicial** hasta que sean revisados y alineados con las decisiones del equipo.

En particular, antes de considerar una especificación como definitiva se deberán validar:

- alcance real del MVP;
- responsabilidades entre Frontend, Backend e IA/Data;
- contrato entre Backend e IA;
- estrategia de RAG y embeddings;
- proveedor/modelo LLM;
- estrategia de orquestación;
- validación de fidelidad;
- integración con OCI;
- funcionalidades adicionales como telemetría, mapas, flashcards 3D, quiz interactivo y exportaciones.

---

## 4. Referencia del proyecto

El README principal del repositorio se encuentra en la raíz:

`README.md`

Este archivo funciona únicamente como índice de la documentación técnica ubicada en `docs/`.

# Resolución: Frontera de Integración DataIA ↔ Backend

**De:** Marcos Hernández (Líder Squad DataIA)  
**Para:** Fernando y Equipo de Integración (G10 LATAM Equipo 15)  
**Fecha:** 26 de septiembre de 2026  
**Estado:** **APROBADO Y MERGEADO**

---

Fernando, excelente análisis de integración. El nivel de detalle técnico es exactamente lo que necesitamos para asegurar que los contratos de frontera no tengan fisuras durante el Hackathon.

Confirmo que **tu propuesta ha sido aprobada en su totalidad** y la documentación oficial (`docs/CONTRATOS_BACKEND_API.md`) ya ha sido actualizada para reflejar estos acuerdos. 

A continuación, la resolución oficial a los 5 puntos planteados:

### 1. El Principio Fundamental (Manejo de RAWs)
Totalmente alineados. Extraer texto en Backend destruiría la jerarquía (tablas, markdown, títulos) vital para el Agente Analizador. 
**Aprobado:** Backend enviará `multipart/form-data` con el binario crudo. Nuestro `DocumentExtractor` (que ya soporta carga desde archivo) se encargará del parseo y la indexación nativa.

### 2. Decisiones Conjuntas (Cierre de los 5 puntos)

| # | Punto de Duda | Resolución Oficial Adoptada por IA |
| :--- | :--- | :--- |
| 1 | **Contexto insuficiente** | **Error controlado (422).** Si el documento carece de datos para generar (ej. pedir un Quiz Técnico de un PDF que solo tiene 1 párrafo), el Agente Crítico lo vetará y devolveremos un error `422 Unprocessable Entity` por falla de Grounding. No devolveremos JSONs parciales ni alucinaremos contenido. |
| 2 | **Evidencia de grounding** | **Score + Observaciones.** No incluiremos los IDs de chunks en el payload final para no ensuciar la salida del Frontend. El Score (ej. `0.92`) y el veredicto del Crítico son suficientes para el MVP. |
| 3 | **Persistencia OCI** | **Responsabilidad 100% de Backend.** El pipeline de DataIA operará como función pura. Nosotros entregamos el JSON final y es tarea de Backend hacer el upload al Object Storage usando el `document_id`. |
| 4 | **Catálogo de Errores** | **Acordado (4 códigos).** El catálogo estricto será: `400` (Inyecciones/Seguridad), `422` (Contexto Insuficiente/Fallo de Grounding), `500` (Fallo interno del Grafo) y `503` (Caída de LLMs Gemini/Groq). |
| 5 | **Default `nivel_detalle`** | **Se vuelve Opcional.** Si Backend omite este campo, el motor de IA aplicará automáticamente el default `"Didactico"` (ya programado en `pipeline.py`). |

---

**Conclusión:**
La frontera está sellada. Los contratos están firmados en el repositorio. Backend tiene luz verde absoluta para empezar a mockear y conectar los endpoints bajo la estructura `contract_version: "2.0"`.

¡Gran trabajo asegurando estos casos límite! Avanzamos.

# NuevaMente Data & IA Pipeline - Informe #1

> **Versión:** 1.0
> **Fecha:** 2026-09-26
> **Autor:** DataIA (equipo de IA)
> **Estado:** Pendiente cerrar decisiones cerradas para MVP del Hackathon ONE
> **Deadline de sustentación:** 27 de octubre de 2026


El pipeline DataIA: un RAG con propósito pedagógico, no de búsqueda
El planteamiento arquitectónico: El documento Proyecto describe una aplicación que no responde preguntas sobre documentos, sino que transforma documentos en contenidos educativos estructurados para perfiles específicos. Esto implica un cambio de paradigma fundamental: el RAG deja de ser un mecanismo de retrieval para Q&A y se convierte en un mecanismo de fundamentación y selección de material pedagógico.En NuevaMente, el usuario no hace preguntas: selecciona un documento, un perfil y un formato de salida. El sistema debe extraer, sintetizar, reescribir y estructurar el contenido.

Sin embargo, el RAG sigue siendo el mecanismo de anclaje que mitiga las alucinaciones. El requisito de "fidelidad técnica" exige que cada afirmación del contenido generado esté respaldada por un fragmento del documento original. El RAG aquí funciona como una capa de verificación y selección de evidencia, no como un motor de respuestas conversacionales.

## 1. Estrategia de ingesta: del documento crudo a unidades pedagógicas,

La ingesta no puede limitarse a extraer texto y dividirlo mecánicamente. Dado que el objetivo es pedagógico, la ingesta debe producir unidades de conocimiento con metadatos pedagógicos desde el primer paso.

Extracción enriquecida: Para PDFs, además de PyPDF, conviene usar herramientas que preserven la estructura (encabezados, listas, tablas, bloques de código). Para Markdown, el parser debe respetar la jerarquía de títulos. La pérdida de estructura en esta etapa es irrecuperable después.

Generación de metadatos con LLM durante la ingesta, cada chunk debe ser etiquetado automáticamente con:

Resumen del chunk (para filtrado previo a la búsqueda vectorial)

Preguntas hipotéticas que responde (útil para formatos Quiz y Flashcards)

Concepto pedagógico principal (para construir la lista de conceptos_clave que exige el JSON de salida)

Nivel de dificultad estimado (para alinear con el perfil del destinatario)

Prerrequisitos detectados (para los metadatos de aprendizaje)

Esto convierte la vectorización en una búsqueda con filtros pedagógicos, no solo semánticos.


## 2. Estrategia de chunking: semántico, jerárquico y consciente del formato de salida.

El chunking es una de las decisiones más críticas del pipeline. Un chunk mal formado contamina toda la cadena. Para DataIA, propongo una estrategia de chunking en dos capas:


Capa 1 — Chunking estructural/semántico (Parent-Child indexing):

El documento se fragmenta en unidades semánticas coherentes (secciones, subsecciones, bloques temáticos), no por longitud fija. El SemanticSplitter de LlamaIndex detecta cambios de tema mediante similitud de embeddings y corta en fronteras semánticas reales.

Sobre esta base, se aplica Parent-Child indexing: se indexan fragmentos pequeños (párrafos o frases individuales) para la búsqueda vectorial, pero al LLM se le entrega el bloque padre (la sección completa) para que tenga contexto suficiente. Esto es especialmente relevante cuando el perfil es "Principiante" y necesita explicaciones contextualizadas, o cuando el formato es "Guion de Clase" y requiere hilo narrativo.


Capa 2 — Chunking orientado al formato de salida:

Componente pedagógica. Los chunks no son solo unidades de texto; son unidades potenciales de contenido educativo. Para cada formato de salida, se necesitan tipos de chunk diferentes.

Esto no significa generar tres indexaciones separadas. Significa que los metadatos asignados durante la ingesta permiten filtrar el Vector Store según el formato solicitado, recuperando el tipo de chunk más adecuado para cada tarea pedagógica. Para el perfil del destinatario, el filtrado es diferente: se seleccionan chunks cuyo nivel_dificultad coincida con el perfil, y el LLM recibe instrucciones de reescritura de tono y profundidad basadas en el perfil_aplicado.

Tamaño y solapamiento: La evidencia empírica sugiere chunks de 360 tokens con 120 de solapamiento para sistemas con audiencias diferenciadas. Azure recomienda ~512 tokens con 10-15% de solapamiento para embeddings generales. Para Nuevamente DataIA, propongo chunks base de 400-512 tokens con solapamiento del 20%, ajustando según la densidad del documento.


## 3. Estrategia de vectorización: embeddings con conciencia pedagógica,

La vectorización debe capturar no solo similitud semántica, sino relaciones pedagógicas. Esto se logra mediante:

Metadatos enriquecidos en el Vector Store: Cada embedding se almacena junto con sus metadatos pedagógicos (nivel_dificultad, tipo_contenido, concepto_principal, formato_ideal). Esto permite búsquedas filtradas: "recupera chunks de tipo 'definición' con nivel_dificultad ≤ 2 para el perfil Principiante".

GraphRAG como capa complementaria: La documentación disponible en general señala que la búsqueda vectorial es "mala para preguntas globales" y los grafos permiten "razonamiento multi-salto". En DataIA, esto es crítico cuando el formato es "Resumen Ejecutivo (TL;DR)": el LLM necesita conceptos de alto nivel y sus relaciones, no fragmentos aislados. Un Knowledge Graph construido durante la ingesta —donde los nodos son conceptos y las aristas son relaciones pedagógicas (prerrequisito, ejemplo_de, contraste_con)— permite que el agente de resumen navegue por el grafo para construir una narrativa coherente.

Selección del Vector Store: Para el MVP en OCI Always Free, ChromaDB o FAISS son suficientes. Si se opta por el diferencial de GraphRAG, se puede combinar FAISS (para búsqueda vectorial rápida) con un grafo ligero en memoria (NetworkX) o Neo4j Aura Free (fuera de OCI, lo cual debe evaluarse cuidadosamente por los requisitos de la capa Always Free).



## 4. Hallazgos, observaciones y sugerencias

Aquí debo anotar que no he visto con detalle el desarrollo que está haciendo Marcos. Son comentarios respetuosos y constructivos para obtener y entregar el mejor producto posible desde este Squad (con los recursos de los que disponemos), y desde luego para beneficio del equipo. No pretendo para nada decirle a mis compañeros como hacer su trabajo. Dejo enfáticamente claro que doy un gran a todo lo desarrollado por mis compañeros hasta este punto (De hecho, los Issues han sido el gran punto de partida para todo esto).

1  El flujo no tiene un paso de "construcción de query pedagógica"

NuevaMente no recibe una pregunta del usuario. Recibe {documento, perfil, formato, nicho}. Entonces, ¿qué es exactamente lo que se busca en el Vector Store?

Opciones:

(a) Buscar todo (dump completo) → inviable, el contexto explota.

(b) Buscar por similitud con una query fija del tipo "conceptos clave de este documento" → mediocre, recupera lo genérico.

(c) Generar queries específicas por formato: para flashcards, buscar definiciones y relaciones término-definición; para quiz, buscar afirmaciones verificables; para tutorial, buscar secuencias paso a paso. → Esto es lo correcto.

El paso (c) no está en ninguna issue. IA-05 asume que "hay una consulta".  Hay allí una cuestión grande del diseño actual. Sin este paso, la diferenciación por formato va a ser superficial: el mismo contexto entra al LLM y solo cambia el prompt de salida.

Sugerencia: agregar un subcomponente a IA-05 (no obstante si Marcos y la PM me autorizan podría implementarlo como IA-04.5) llamado  "Query Builder Pedagógico" que, dado (documento_indexado, perfil, formato, nicho), construya 1-3 queries especializadas. Esto se puede hacer con un LLM pequeño o con plantillas deterministas.

2 Incluir Metadata pedagógica en IA-03 e IA-04

Con el estado actual, IA-06 tendrá que "adivinar" pedagógicamente desde el prompt. Eso funciona para un MVP, pero es frágil.Se puede agregar una capa de enriquecimiento pedagógico que para cada document_id genere una vez (cacheada) una estructura tipo:

{
  "document_id": "doc-001",
  "conceptos_clave": [...],
  "prerequisitos": [...],
  "niveles_dificultad_por_chunk": {"chunk-1": 2, "chunk-2": 4, ...},
  "tipos_contenido_por_chunk": {"chunk-1": "definicion", "chunk-2": "procedimiento", ...}
}

De hecho, el JSON de ejemplo del Proyecto (página 5) pide explícitamente conceptos_clave y tiempo_estimado_estudio_minutos. Ninguna issue IA explica de dónde salen esos campos. Ese es un gap funcional respecto al enunciado del hackathon.

3 Ninguna issue cubre nicho_sector

El Proyecto y las issues mencionan nicho_sector como parámetro, pero ninguna etapa lo consume. IA-06 §5.5 habla de perfiles y formatos, no de nicho. IA-08 no lo incluye en el JSON conceptual.Es un parámetro pequeño pero el enunciado del hackathon lo pide. Sugiero que IA-06 lo use como instrucción adicional en el prompt ("adapta los ejemplos al contexto de Fintech/Salud/E-commerce") y que IA-08 lo exponga en el JSON de salida.

4 Falta el tiempo_estimado_estudio_minutos

El JSON de salida del Proyecto lo pide. Ninguna issue lo cubre. Es un cálculo trivial (p.ej. #items × minutos_por_item[formato] con un ajuste por perfil), pero debe estar explícito en IA-08 o IA-07. Sin esto, el contrato JSON no cumple con el enunciado.

5 IA-07 tiene anclaje_fuente_score como caja negra

El JSON del Proyecto pide anclaje_fuente_score: 0.98 como salida. Es decir, el score es un entregable visible al usuario/backend, no solo un control interno. Eso significa que su cálculo debe ser:

Determinista (o reproducible)

Explicable (no un "se lo preguntamos al LLM y nos dijo 0.92")

Auditable (idealmente con referencias a los chunks que sustentan cada afirmación)

Sugerencia: implementarlo como NLI (Natural Language Inference) sobre pares (afirmación_generada, chunk_fuente), agregando en un score ponderado. Alternativamente, LLM-as-a-judge con rúbrica estructurada y respuesta JSON forzada. Pero documentar la fórmula en el issue y en el código.

## 5. Acuerdos

Transcribo aquí lo que considero ya está acordado y validado:

- Perfiles MVP (solo 3): Principiante / Junior, Líder Técnico, Ejecutivo.
- Formatos MVP (solo 3): Flashcards, Quiz Interactivo, Resumen Ejecutivo (TL;DR). Mapas mentales y Tutorial quedan como plus.
- Contrato de ingestión: Backend recibe el archivo, lo valida y lo guarda en OCI.
- DataIA recibe el archivo crudo + parámetros.

Espero sus valiosos comentarios.



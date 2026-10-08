# ESPECIFICACIÓN DE SISTEMA DE DISEÑO Y UI/UX
## Proyecto: NuevaMente — Plataforma Educativa Inteligente
**Enfoque de Diseño:** Minimalismo Clásico Tecnológico (Classical Tech Minimalism)  
**Propósito:** Definir los lineamientos visuales, tokens de diseño, arquitectura de componentes interactivos y wireframes para el equipo de Frontend (Karen Gonzalez y Cristian Cortes).

---

## 1. Filosofía de Diseño y Principios Visuales

El diseño de **NuevaMente** se rige por tres pilares fundamentales:
1. **Claridad sobre Ruido:** El contenido educativo es denso por naturaleza. La interfaz debe eliminar distracciones visuales innecesarias, otorgando protagonismo al texto didáctico, jerarquía tipográfica y espacios en blanco equilibrados.
2. **Interactividad Cognitiva:** Los componentes didácticos (tarjetas, quizzes, mapas mentales) deben responder de manera fluida y táctil, proporcionando retroalimentación sensorial inmediata ante cada acción del estudiante.
3. **Transparencia en Tiempo Real:** Los procesos de Inteligencia Artificial y almacenamiento en la nube no deben ser una "caja negra"; el usuario debe visualizar en todo momento en qué fase se encuentra la orquestación.

---

## 2. Sistema de Tokens de Diseño (Design Tokens)

### 2.1 Paleta de Colores Semántica
La identidad visual combina la sobriedad técnica del ecosistema Oracle/Enterprise con acentos modernos de aprendizaje digital:

| Token Semántico | Valor Hex / HSL | Uso Principal |
|---|---|---|
| `--color-bg-canvas` | `#0F172A` (Dark) / `#F8FAFC` (Light) | Fondo general de la aplicación. |
| `--color-surface-card` | `#1E293B` (Dark) / `#FFFFFF` (Light) | Contenedores, tarjetas, modales y paneles. |
| `--color-border-subtle` | `#334155` (Dark) / `#E2E8F0` (Light) | Líneas divisorias, bordes de tarjetas e inputs. |
| `--color-text-primary` | `#F8FAFC` (Dark) / `#0F172A` (Light) | Títulos principales, encabezados y texto destacado. |
| `--color-text-secondary` | `#94A3B8` (Dark) / `#64748B` (Light) | Descripciones, metadatos y etiquetas secundarias. |
| `--color-brand-primary` | `#0284C7` (Sky Blue 600) | Acciones primarias, botones de generación, estados activos. |
| `--color-brand-oracle` | `#C74634` (Oracle Red Accent) | Insignias de OCI Always Free, acentos corporativos. |
| `--color-status-success` | `#10B981` (Emerald 500) | Aciertos en quizzes, anclaje aprobado ($\ge 0.85$), OCI conectado. |
| `--color-status-warning` | `#F59E0B` (Amber 500) | Pistas didácticas, advertencias de fidelidad moderada. |
| `--color-status-error` | `#EF4444` (Rose 500) | Errores de carga, respuestas incorrectas en quizzes. |

### 2.2 Tipografía
* **Familia Tipográfica Primaria:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `sans-serif`.
* **Familia Monoespaciada (Código y Snippets):** `JetBrains Mono`, `Fira Code`, `monospace`.
* **Escala Modular:**
  - `Display / H1`: 28px - 32px (Semibold / Bold) — Título de la aplicación y encabezados de paquetes.
  - `H2`: 20px - 24px (Medium) — Secciones principales (Parámetros, Estudio, Auditoría).
  - `H3`: 16px - 18px (Medium) — Títulos de tarjetas, preguntas de quizzes y ramas de mapas.
  - `Body`: 14px - 15px (Regular) — Textos explicativos, dorsos de flashcards y justificaciones.
  - `Caption`: 12px (Regular / Medium) — Metadatos, etiquetas de OCI, tiempo estimado y pistas.

---

## 3. Especificación de Componentes Interactivos Clave

### 3.1 Stepper de Estado en Tiempo Real (Live Generation Stepper)
Ubicado en la parte central superior durante la ejecución. Reemplaza los spinners genéricos por una barra de telemetría pedagógica de 5 fases:

```
[ 1. Ingesta ✓ ] ─── [ 2. Vector RAG ✓ ] ─── [ 3. LangGraph ⟳ ] ─── [ 4. Crítico OCI ] ─── [ 5. Persistencia ]
```

* **Comportamiento:**
  - Cada nodo completado muestra un check verde (`#10B981`) y una transición de color suave.
  - El nodo activo pulsa con un brillo sutil en azul (`#0284C7`) y un texto descriptivo dinámico:
    - *Fase 1:* "Extrayendo texto y normalizando jerarquías del PDF..."
    - *Fase 2:* "Segmentando 42 fragmentos y calculando embeddings..."
    - *Fase 3:* "LangGraph: Adaptando contenido para perfil Junior en formato Flashcards..."
    - *Fase 4:* "Agente Crítico: Verificando anclaje fáctico (Score actual: 0.94)..."
    - *Fase 5:* "OCI Object Storage: Persistiendo JSON en bucket Always Free..."

---

### 3.2 Visor de Tarjetas Interactivas (Interactive Flashcards Studio)
Componente de estudio diseñado con animación CSS 3D:

* **Mecánica de Interacción:**
  - **Frente (Anverso):** Presenta el concepto o pregunta clave en tipografía destacada.
  - **Dorso (Reverso):** Se revela mediante animación de volteo (`transform: rotateY(180deg)`) al hacer clic o presionar la barra espaciadora (`Space`). Contiene la definición adaptada sin tecnicismos excesivos.
  - **Pista Didáctica (Hint Accordion):** Botón discreto con icono de bombilla (`💡`). Al presionarlo, despliega una analogía pedagógica del mundo real sin revelar la respuesta completa.
  - **Controles de Navegación:** Flechas `[ Anterior ]` y `[ Siguiente ]`, compatibles con teclado (`ArrowLeft` / `ArrowRight`).
  - **Contador de Progreso:** Indicador "Tarjeta 3 de 10" con barra de progreso porcentual.

```
┌─────────────────────────────────────────────────────────────┐
│  TARJETA 03 / 10                           [ Nivel: Básico ]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│         ¿Qué es una Virtual Cloud Network (VCN)?            │
│                                                             │
│                                                             │
│  [💡 Ver Pista Didáctica]                                    │
│  "Piensa en ella como el terreno cercado de tu empresa."    │
├─────────────────────────────────────────────────────────────┤
│  [ ← Anterior ]            (Espacio para Voltear) [ Siguiente → ]│
└─────────────────────────────────────────────────────────────┘
```

---

### 3.3 Evaluador de Quizzes Interactivos con Justificación (Interactive Quiz Studio)
Diseñado para la autoevaluación activa con retroalimentación inmediata:

* **Mecánica de Interacción:**
  - Enunciado claro de la pregunta técnica con indicación de dificultad.
  - Cuatro opciones de respuesta presentadas en tarjetas seleccionables con efecto hover.
  - **Feedback Instantáneo:** Al hacer clic en una opción:
    - La opción seleccionada se colorea en verde (si es correcta) o rojo (si es incorrecta).
    - Si es incorrecta, la opción correcta se ilumina automáticamente en verde.
    - Se despliega de forma animada el panel inferior de **Argumentación Técnica**:
      - *Por qué es correcta:* Explicación formal anclada al manual.
      - *Por qué fallan las demás:* Breve análisis del error en las opciones descartadas.
      - *Referencia fáctica:* Sección y página del documento original.
  - **Puntuación Acumulativa:** Marcador de aciertos en tiempo real (ej. `4/5 Aciertos (80%)`).

---

### 3.4 Visor de Mapas Mentales Jerárquicos (Mindmap Graph Studio)
Componente de representación gráfica del conocimiento interactivo de alto impacto visual:

* **Motores Gráficos Recomendados (Superior a Mermaid):**
  - **Motor Primario (en React/Vite):** **`@xyflow/react` (React Flow)** con layout automático (Dagre / Elkjs). Permite renderizar nodos personalizados tipo tarjeta con sombras suaves, badges de dificultad, minimapa interactivo en la esquina y arrastre libre de nodos por el lienzo.
  - **Motor Alternativo / Ultraligero (en Streamlit o React):** **`Markmap.js` (basado en D3.js)**. Permite renderizar un mapa mental arbóreo animado con curvas bezier de colores por rama y nodos colapsables/expandibles al hacer clic.
  - **Exportación Secundaria:** Se mantiene el bloque **Mermaid.js** (`mindmap`) en el payload JSON para permitir al usuario copiar la sintaxis a Notion u Obsidian con un botón *"Copiar Markdown/Mermaid"*.
* **Jerarquía de Conocimiento:**
  - **Nodo Central (Raíz):** Tema global del documento (ej. `Arquitectura de Redes en OCI`).
  - **Ramas Principales (Nivel 1):** Subredes, Tablas de Enrutamiento, Puertas de Enlace, Listas de Seguridad.
  - **Subramas (Nivel 2):** Propiedades clave, reglas de tráfico, casos de uso.
* **Controles de Navegación del Lienzo:**
  - Botones flotantes de `Zoom In (+)`, `Zoom Out (-)` y `Centrar Vista (⤢)`.
  - Paneo interactivo mediante arrastre del mouse (*drag to pan*).
  - Interactividad en nodos: clic para colapsar/expandir ramas hijas.
  - Botón de exportación: `Descargar Diagrama (.svg / .png)`.

---

### 3.5 Tarjeta de Auditoría de Calidad y Persistencia OCI
Ubicada en el pie del panel de resultados para certificar el cumplimiento técnico:

* Muestra el **Score de Anclaje** con una barra radial o indicador visual (ej. `0.96 / 1.00 - Alta Fidelidad`).
* Muestra el identificador del objeto en OCI: `nuevamente-contenidos-educativos/2026-09/vcn-flashcards-001.json`.
* Indicador de latencia y tiempo de procesamiento total.

---

## 4. Arquitectura de Pantallas y Wireframe Textual

La interfaz se estructura en una vista de **Estudio de Doble Panel (Split Workspace)**:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  🎓 NUEVAMENTE  |  Sistema Inteligente de Adaptación Educativa       [ OCI Always Free: Activo ]│
├────────────────────────────────────────┬────────────────────────────────────────────────────┤
│ PANEL IZQUIERDO: CONFIGURACIÓN         │ PANEL DERECHO: ESPACIO DE APRENDIZAJE              │
│                                        │                                                    │
│ 1. Carga de Documento Técnico          │ [ 1. Ingesta ✓ ] ─ [ 2. RAG ✓ ] ─ [ 3. LangGraph ✓ ]│
│ ┌────────────────────────────────────┐ │                                                    │
│ │   📁 Arrastre su archivo PDF / MD  │ │ ────────────────────────────────────────────────── │
│ │   manual-redes-vcn.pdf (3.4 MB)    │ │ VISTA: TARJETAS INTERACTIVAS (FLASHCARDS)          │
│ └────────────────────────────────────┘ │                                                    │
│                                        │ ┌────────────────────────────────────────────────┐ │
│ 2. Perfil de Audiencia                 │ │                                                │ │
│ (o) Junior (Didáctico & Guiado)        │ │   ¿Qué es una Virtual Cloud Network (VCN)?     │ │
│ ( ) Senior (Arquitectura & Trade-offs) │ │                                                │ │
│ ( ) Ejecutivo (Negocio & ROI)          │ │   [💡 Ver Pista Didáctica]                     │ │
│                                        │ │                                                │ │
│                                        │ └────────────────────────────────────────────────┘ │
│ 3. Formato Pedagógico                  │   [ Anterior ]   Tarjeta 1 de 8   [ Siguiente ]    │
│ [ Tarjetas ] [ Quizzes ] [ Mapa Mental]│                                                    │
│ [ Guía Paso a Paso ] [ Resumen TL;DR ] │ ────────────────────────────────────────────────── │
│                                        │ 🛡️ AUDITORÍA & ORACLE CLOUD:                       │
│ 4. Nicho / Contexto                    │ • Anclaje Fuente: 0.96 (Alta Fidelidad)            │
│ [ General ▼ ]                          │ • Almacenamiento: vcn-flashcards-001.json en OCI   │
│                                        │ • Tiempo de Inferencia: 14.2 segundos              │
│ [ 🚀 GENERAR PAQUETE EDUCATIVO ]       │ [ 📥 Descargar JSON ]  [ 📥 Descargar Markdown ]   │
└────────────────────────────────────────┴────────────────────────────────────────────────────┘
```

---

## 5. Directrices de Implementación para Frontend

* **Si se utiliza React / Vite:**
  - Usar TailwindCSS (o Vanilla CSS con tokens CSS estándar definidos en `:root`).
  - Utilizar `lucide-react` para iconos minimalistas consistentes.
  - Usar `mermaid` vía `mermaid.run()` para el renderizado del mapa mental en un contenedor interactivo.
* **Si se utiliza Streamlit:**
  - Implementar CSS inyectado (`st.markdown("<style>...</style>", unsafe_allow_html=True)`) para estilizar tarjetas con sombra y bordes refinados.
  - Usar `streamlit-card` o componentes HTML interactivos para el volteo de tarjetas y quizzes.
  - Usar `streamlit.components.v1.html` para renderizar el diagrama Mermaid interactivo.

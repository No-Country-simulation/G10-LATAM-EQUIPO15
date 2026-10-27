# ESPECIFICACIÓN TÉCNICA DE CONTRATOS DE DATOS Y ESQUEMAS PYDANTIC V2
## Proyecto: NuevaMente — Plataforma Educativa Inteligente
**Propósito:** Definir formalmente los modelos de datos tipados en Python (Pydantic V2) que gobiernan las interfaces de comunicación entre Frontend, Backend, LangGraph y OCI Object Storage, asegurando 100% de compatibilidad con las especificaciones del Hackathon de Oracle & Alura.

---

## 1. Mapeo de Enums Canónicos

```python
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class PerfilDestinatarioEnum(str, Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    EJECUTIVO = "Ejecutivo"


class FormatoSalidaEnum(str, Enum):
    FLASHCARDS = "Flashcards"
    QUIZ_INTERACTIVO = "Quiz Interactivo"
    MAPA_MENTAL = "Mapa Mental"
    GUIA_PASO_A_PASO = "Guia Paso a Paso"
    RESUMEN_EJECUTIVO = "Resumen Ejecutivo"


class NichoSectorEnum(str, Enum):
    FINTECH = "Fintech"
    SALUD = "Salud"
    ECOMMERCE = "E-commerce"
    GENERAL = "General"


class NivelDetalleEnum(str, Enum):
    DIDACTICO = "Didactico"
    TECNICO_INTERMEDIO = "Tecnico Intermedio"
    EXHAUSTIVO = "Exhaustivo"


class FaseProgresoEnum(str, Enum):
    EXTRACCION = "EXTRACCION"
    INDEXACION = "INDEXACION"
    GENERACION = "GENERACION"
    AUDITORIA = "AUDITORIA"
    PERSISTENCIA = "PERSISTENCIA"
    COMPLETADO = "COMPLETADO"
    ERROR = "ERROR"
```

---

## 2. Modelos Específicos por Formato Didáctico

### 2.1 Tarjetas Interactivas (Flashcards)
```python
class FlashcardItem(BaseModel):
    frente: str = Field(..., description="Concepto, término o pregunta clave")
    dorso: str = Field(..., description="Definición o explicación pedagógica adaptada")
    pista_didactica: str = Field(..., description="Analogía o pista mnemotécnica del mundo real")
    categoria_dificultad: Optional[str] = Field(default="Intermedio", description="Básico | Intermedio | Avanzado")
    identificador: Optional[int] = Field(default=None, description="Identificador correlativo opcional")
```

### 2.2 Quizzes Interactivos
```python
class QuizItem(BaseModel):
    pregunta: str = Field(..., description="Enunciado de la pregunta técnica contextualizada")
    opciones: List[str] = Field(..., min_items=4, max_items=4, description="Lista de 4 alternativas")
    indice_correcto: int = Field(..., ge=0, le=3, description="Índice (0-3) de la opción correcta")
    justificacion_tecnica: str = Field(..., description="Explicación exhaustiva de por qué es la opción válida")
    pista_didactica: Optional[str] = Field(None, description="Pista para orientar al alumno antes de responder")
    explicacion_distractores: Optional[str] = Field(None, description="Análisis de por qué fallan las demás opciones")
    referencia_fuente: Optional[str] = Field(None, description="Sección o página del documento original")
    identificador: Optional[int] = Field(default=None)
```

### 2.3 Mapas Mentales Jerárquicos
```python
class SubnodoConceptual(BaseModel):
    titulo: str = Field(..., description="Subtema o concepto específico")
    detalles: List[str] = Field(default_factory=list, description="Propiedades, reglas o ejemplos clave")


class RamaTematica(BaseModel):
    nombre_rama: str = Field(..., description="Pilar temático o módulo principal")
    subnodos: List[SubnodoConceptual] = Field(default_factory=list, description="Subconceptos derivados")


class MapaMentalContenido(BaseModel):
    nodo_central: str = Field(..., description="Tema central o título del documento técnico")
    descripcion_general: str = Field(..., description="Resumen conceptual del árbol temático")
    ramas_principales: List[RamaTematica] = Field(..., description="Estructura jerárquica de temas")
    codigo_mermaid: str = Field(..., description="Sintaxis formal de Mermaid (mindmap) lista para renderizar")
```

### 2.4 Guía Paso a Paso (Tutorial) y Resumen Ejecutivo (TL;DR)
```python
class PasoTutorial(BaseModel):
    numero: int = Field(..., ge=1, description="Número de paso correlativo")
    titulo: str = Field(..., description="Título de la acción")
    instrucciones: str = Field(..., description="Explicación detallada paso a paso")
    snippet_codigo_o_comando: Optional[str] = Field(None, description="Código fuente o comando CLI aplicable")
    resultado_esperado: str = Field(..., description="Criterio de validación del paso")


class ResumenEjecutivoContenido(BaseModel):
    vision_general: str = Field(..., description="Síntesis estratégica de alto nivel")
    puntos_clave_negocio: List[str] = Field(..., description="Impacto operativo, comercial y de eficiencia")
    consideraciones_arquitectura: List[str] = Field(..., description="Trade-offs, disponibilidad y seguridad")
    recomendaciones_implementacion: List[str] = Field(..., description="Próximos pasos sugeridos")
```

---

## 3. Modelo de Contenedor Didáctico Polimórfico

```python
class PaqueteContenidoAdaptado(BaseModel):
    titulo: str = Field(..., description="Título contextualizado del paquete didáctico")
    introduccion_contextualizada: str = Field(..., description="Analogía de apertura adaptada al perfil seleccionado")
    items: Union[
        List[FlashcardItem],
        List[QuizItem],
        MapaMentalContenido,
        List[PasoTutorial],
        ResumenEjecutivoContenido,
    ] = Field(..., description="Elementos didácticos generados según el formato")
```

---

## 4. Contratos Canónicos de la API REST

### 4.1 Modelo de Solicitud (Request Payload)
```python
class AdaptacionContenidoRequest(BaseModel):
    documento_titulo: str = Field(..., min_length=3, max_length=150, description="Título del documento")
    documento_contenido: str = Field(..., min_length=50, description="Texto extraído del documento técnico")
    perfil_destinatario: PerfilDestinatarioEnum = Field(default=PerfilDestinatarioEnum.JUNIOR)
    formato_salida: FormatoSalidaEnum = Field(default=FormatoSalidaEnum.FLASHCARDS)
    nicho_sector: NichoSectorEnum = Field(default=NichoSectorEnum.GENERAL)
    nivel_detalle: NivelDetalleEnum = Field(default=NivelDetalleEnum.DIDACTICO)
```

### 4.2 Metadatos, Calidad y Almacenamiento OCI
```python
class MetadatosAprendizaje(BaseModel):
    perfil_aplicado: str = Field(..., description="Perfil de audiencia utilizado")
    formato_generado: str = Field(..., description="Formato pedagógico producido")
    tiempo_estimado_estudio_minutos: int = Field(..., ge=1, description="Tiempo de lectura y estudio estimado")
    conceptos_clave: List[str] = Field(..., description="Lista de conceptos técnicos fundamentales cubiertos")
    nicho_contexto: Optional[str] = Field(default="General")


class EvaluacionCalidad(BaseModel):
    anclaje_fuente_score: float = Field(..., ge=0.0, le=1.0, description="Índice de fidelidad fáctica (0.0 a 1.0)")
    claridad_pedagogica: str = Field(..., description="Alta | Media | Baja")
    observaciones: str = Field(..., description="Reporte de fidelidad y adecuación de lenguaje del Agente Crítico")
    clasificacion_fidelidad: Optional[str] = Field(default=None)


class AlmacenamientoOCI(BaseModel):
    bucket: str = Field(default="nuevamente-contenidos-educativos", description="Nombre del bucket en OCI")
    objeto_id: str = Field(..., description="Identificador único del archivo JSON en OCI Object Storage")
    status_upload: str = Field(default="completado", description="Estado de persistencia en la nube")
    region: Optional[str] = Field(default="us-ashburn-1")
    tamano_bytes: Optional[int] = Field(default=None)
```

### 4.3 Modelo de Respuesta Canónica (Response Payload)
```python
class AdaptacionContenidoResponse(BaseModel):
    status: str = Field(default="exito", description="Estado de la respuesta ('exito' | 'error')")
    metadatos: MetadatosAprendizaje
    contenido_adaptado: PaqueteContenidoAdaptado
    evaluacion_calidad: EvaluacionCalidad
    almacenamiento_oci: AlmacenamientoOCI
    codigo_respuesta: Optional[int] = Field(default=200, description="Código de estado HTTP")
```

---

## 5. Modelo de Telemetría y Stepper en Tiempo Real

Para la emisión de eventos de progreso en tiempo real (vía Server-Sent Events o sondeo de estado):

```python
class TelemetriaEstadoResponse(BaseModel):
    fase_actual: FaseProgresoEnum = Field(..., description="Fase activa del pipeline")
    fase_numero: int = Field(..., ge=1, le=5, description="Número correlativo de fase (1 a 5)")
    porcentaje_progreso: int = Field(..., ge=0, le=100, description="Porcentaje acumulado de avance")
    mensaje_descriptivo: str = Field(..., description="Texto dinámico explicativo para el usuario")
    tiempo_transcurrido_segundos: float = Field(default=0.0)
    error_detalle: Optional[str] = Field(default=None)
```

---

## 6. Ejemplo Canónico de Salida JSON (Fiel a la Especificación de Oracle ONE)

A continuación se ilustra el payload exacto retornado por el sistema, demostrando compatibilidad estricta con las bases oficiales:

```json
{
  "status": "exito",
  "metadatos": {
    "perfil_aplicado": "Junior",
    "formato_generado": "Flashcards",
    "tiempo_estimado_estudio_minutos": 5,
    "conceptos_clave": ["VCN", "Subredes", "Internet Gateway", "Security Lists"],
    "nicho_contexto": "General"
  },
  "contenido_adaptado": {
    "titulo": "Dominando Redes en la Nube (VCN) para Desarrollador Junior",
    "introduccion_contextualizada": "Imagina la VCN como tu propio barrio privado y seguro dentro de la nube de Oracle, donde tú decides quién entra y quién sale.",
    "items": [
      {
        "frente": "¿Qué es una VCN en Oracle Cloud?",
        "dorso": "Es tu red virtual privada y personalizada dentro de la nube de Oracle, funcionando como la infraestructura de red de tu empresa.",
        "pista_didactica": "Piensa en ella como el terreno cercado donde residen tus servidores.",
        "categoria_dificultad": "Básico"
      },
      {
        "frente": "¿Para qué sirven las Security Lists (Listas de Seguridad)?",
        "dorso": "Son como guardias virtuales con listas de reglas que definen exactamente qué tipo de tráfico de datos puede entrar o salir de tu red.",
        "pista_didactica": "Reglas de entrada (ingress) y reglas de salida (egress).",
        "categoria_dificultad": "Intermedio"
      }
    ]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.98,
    "claridad_pedagogica": "Alta",
    "observaciones": "Lenguaje adaptado para perfil Junior con analogías claras y sin tecnicismos excesivos."
  },
  "almacenamiento_oci": {
    "bucket": "nuevamente-contenidos-educativos",
    "objeto_id": "contenido-vcn-junior-flashcards-001.json",
    "status_upload": "completado"
  }
}
```

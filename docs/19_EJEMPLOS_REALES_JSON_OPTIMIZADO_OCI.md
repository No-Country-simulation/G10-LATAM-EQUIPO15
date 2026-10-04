# REPORTE DE CONTRATOS Y EJEMPLOS REALES DE SALIDA (Payload Optimizado)

**Versión:** 1.0 (Optimizada para OCI Free Tier)
**Fecha:** 03 de Octubre de 2026
**Uso:** Referencia Oficial para Equipos de Backend y Frontend.

---

## 1. Estructura Base del Payload (Común para todos)

El motor Multi-Agente (LangGraph + DataIA) ahora retorna un payload estandarizado, desprovisto de metadata de telemetría interna pesada. Todo payload tiene exactamente 3 claves principales a nivel raíz:

```json
{
  "status": "exito",
  "metadatos": {
    "perfil_aplicado": "Senior",
    "formato_generado": "Nombre del Formato",
    "tiempo_estimado_estudio_minutos": 15,
    "conceptos_clave": ["Concepto1", "Concepto2"],
    "nicho_contexto": "Fintech"
  },
  "contenido_adaptado": {
    "titulo": "Título Contextualizado",
    "introduccion_contextualizada": "Breve párrafo introductorio.",
    "items": [ 
       // <-- Aquí varía la estructura según el formato solicitado
    ]
  }
}
```

---

## 2. Ejemplos Reales por Formato (Contenido del array `items`)

A continuación, se muestra cómo viene estructurado el array `items` dentro de `contenido_adaptado` dependiendo del formato educativo solicitado.

### A. Quiz Interactivo
Estructura rigurosa con un arreglo de 4 `opciones` exactas, un `indice_correcto` numérico (0-3) para validación rápida en el Frontend, y su justificación.

```json
"items": [
  {
    "pregunta": "¿Por qué es crucial usar RS256 en lugar de HS256 para firmar JWTs en una arquitectura distribuida?",
    "opciones": [
      "Porque RS256 es simétrico y más rápido.",
      "Porque RS256 permite la verificación pública sin compartir la clave privada.",
      "Porque HS256 no soporta claims personalizados.",
      "Porque OCI solo soporta algoritmos de cifrado simétricos."
    ],
    "indice_correcto": 1,
    "justificacion_tecnica": "RS256 utiliza un par de claves. El servicio de autenticación firma con la privada, y los microservicios validan con la pública, asegurando que las credenciales no se comprometan.",
    "pista_didactica": "Piensa en el problema de distribuir la misma clave secreta a cientos de servicios.",
    "explicacion_distractores": null
  }
]
```

### B. Flashcards
Estructura de memorización activa (Anki-style), simple de iterar para carruseles.

```json
"items": [
  {
    "frente": "¿Qué protocolo utiliza OCI para la conexión segura en su API Gateway?",
    "dorso": "Utiliza TLS 1.2 o superior, asegurando encriptación end-to-end entre el cliente y el balanceador de carga."
  },
  {
    "frente": "Diferencia principal entre un Subnet Público y Privado en OCI.",
    "dorso": "Los recursos en un Subnet Público tienen IPs públicas y acceso a Internet directo vía Internet Gateway; los privados requieren un NAT Gateway."
  }
]
```

### C. Mapa Mental
Devuelve la estructura jerárquica y el código Mermaid listo para ser inyectado en un componente de renderizado (Ej. `mermaid.js`).

```json
"items": {
  "nodo_central": "Arquitectura de Microservicios",
  "arbol": {
    "Comunicación": ["REST APIs", "gRPC", "Message Brokers (Kafka)"],
    "Persistencia": ["Bases de Datos por Servicio", "Event Sourcing"],
    "Despliegue": ["Contenedores (Docker)", "Orquestación (Kubernetes)"]
  },
  "codigo_mermaid": "graph TD\n    A[Arquitectura de Microservicios] --> B[Comunicación]\n    B --> B1[REST APIs]\n    B --> B2[gRPC]\n    A --> C[Persistencia]\n    C --> C1[Bases de Datos por Servicio]\n    A --> D[Despliegue]\n    D --> D1[Contenedores]"
}
```

### D. Resumen Ejecutivo
Ideal para perfiles ejecutivos o gerenciales que requieren escanear la información rápidamente. Se divide en secciones lógicas.

```json
"items": [
  {
    "seccion": "Objetivos Estratégicos de la Migración a OCI",
    "puntos_clave": [
      "Reducción del TCO (Total Cost of Ownership) en un 30%.",
      "Garantizar alta disponibilidad multi-región."
    ],
    "parrafo_explicativo": "La migración hacia OCI busca modernizar la infraestructura monolítica actual hacia una arquitectura nativa en la nube, optimizando recursos mediante el modelo Always Free y Pay-As-You-Go."
  },
  {
    "seccion": "Riesgos y Mitigaciones",
    "puntos_clave": [
      "Curva de aprendizaje del equipo de desarrollo.",
      "Tiempo de inactividad durante la sincronización de bases de datos."
    ],
    "parrafo_explicativo": "Para mitigar estos riesgos, se ejecutará una fase de capacitación intensiva en OCI Identity and Access Management y se utilizará OCI GoldenGate para la replicación sin interrupciones."
  }
]
```

### E. Tutorial (Paso a Paso)
Ideal para perfiles Junior/Estudiantes técnicos que requieren seguir una receta.

```json
"items": [
  {
    "paso_numero": 1,
    "titulo_paso": "Configurar el Compartment en OCI",
    "explicacion": "Ingresa a la consola de OCI, navega a Identity & Security > Compartments y crea uno nuevo asignándole las etiquetas correspondientes del proyecto.",
    "codigo_ejemplo": "oci iam compartment create --name 'AppProd' --description 'Entorno de Producción'",
    "advertencia_comun": "Asegúrate de no usar el Root Compartment por motivos de seguridad y menor granularidad en políticas."
  },
  {
    "paso_numero": 2,
    "titulo_paso": "Desplegar la Instancia Compute",
    "explicacion": "Lanza una máquina virtual Always Free de tipo Ampere A1. Selecciona la VCN y Subnet público previamente creados.",
    "codigo_ejemplo": null,
    "advertencia_comun": "Verifica que el Security List asociado permita el tráfico de ingreso en los puertos 80 y 443."
  }
]
```

---
**Nota para el equipo Frontend:** Todos estos campos están fuertemente tipados. El modelo `items` será una lista de objetos, excepto en `Mapa Mental` que retorna un objeto JSON único con el código listo para renderizar. No hay metadata adicional ni campos ocultos, optimizando la renderización y uso de memoria.

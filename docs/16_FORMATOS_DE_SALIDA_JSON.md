#  Catálogo de Formatos de Salida (JSON Payloads)
**Fase:** Cierre de Integración de IA  
**Propósito:** Proveer a los equipos de Frontend y Backend la estructura de datos exacta (esquemas JSON) que devolverá el motor de IA para cada formato de estudio.

Actualmente, el MVP soporta de manera robusta y tipada (vía Pydantic) los siguientes formatos estructurados:
1.  **Quiz Interactivo** (Preguntas de opción múltiple).
2.  **Flashcards** (Tarjetas de memorización activa).

A continuación se presentan ejemplos reales generados por `gemini-3.5-flash-lite` utilizando el manual técnico *"JWT en OCI"*.

---

## 1. Formato: Quiz Interactivo
Estructura diseñada para renderizar cuestionarios de opción múltiple con retroalimentación instantánea.

```json
{
    "status": "exito",
    "metadatos": {
        "perfil_aplicado": "Senior",
        "formato_generado": "Quiz Interactivo",
        "tiempo_estimado_estudio_minutos": 8,
        "nicho_contexto": "Cloud"
    },
    "contenido_adaptado": {
        "titulo": "Evaluación de Arquitectura: Autenticación y Validación de JWT en OCI API Gateway",
        "introduccion_contextualizada": "Como arquitecto cloud o ingeniero senior, diseñar arquitecturas de microservicios robustas en Oracle Cloud Infrastructure (OCI) exige un dominio absoluto de los mecanismos de seguridad perimetral...",
        "items": [
            {
                "pregunta": "En una arquitectura multi-tenant altamente distribuida sobre OCI API Gateway... ¿Qué política de validación cumple con este requisito sin requerir llamadas sincrónicas?",
                "opciones": [
                    "REMOTE_DISCOVERY",
                    "REMOTE_JWKS",
                    "STATIC_KEYS",
                    "OAuth 2.0 Introspection Endpoint"
                ],
                "indice_correcto": 2,
                "justificacion_tecnica": "La opción STATIC_KEYS permite que el API Gateway verifique la firma del JWT de forma local utilizando claves públicas de verificación ya emitidas...",
                "pista_didactica": "Busca el mecanismo que procese la criptografía de manera autocontenida.",
                "explicacion_distractores": "REMOTE_DISCOVERY realiza consultas al punto final de introspección..."
            }
            // ... (Más preguntas del quiz iterando la misma estructura)
        ]
    },
    "almacenamiento_oci": {
        "bucket": "nuevamente-contenidos-educativos",
        "objeto_id": "manual-jwt-oci_senior_quiz interactivo.json",
        "status_upload": "listo_para_subida",
        "ruta_publica_o_par": null
    },
    "codigo_respuesta": 200
}
```

---

## 2. Formato: Flashcards
Estructura diseñada para renderizar componentes de interfaz "Flip Cards" (Frente/Dorso) para aprendizaje espaciado.

```json
{
    "status": "exito",
    "metadatos": {
        "perfil_aplicado": "Senior",
        "formato_generado": "Flashcards",
        "tiempo_estimado_estudio_minutos": 5,
        "nicho_contexto": "General"
    },
    "contenido_adaptado": {
        "titulo": "Flashcards de Arquitectura: Autenticación y Validación JWT en OCI API Gateway",
        "introduccion_contextualizada": "Conjunto de tarjetas de memorización activa optimizadas para arquitectos cloud e ingenieros DevOps...",
        "items": [
            {
                "frente": "¿Cuál es la política recomendada en OCI API Gateway para la validación de nuevos tokens JWT en lugar de la heredada JWT_AUTHENTICATION?",
                "dorso": "Se debe utilizar TOKEN_AUTHENTICATION. Permite validar tanto tokens JWT como non-JWT, utilizar puntos finales de introspección...",
                "pista_didactica": "Piensa en TOKEN_AUTHENTICATION como una pasarela de seguridad universal.",
                "categoria_dificultad": "Intermedio"
            },
            {
                "frente": "¿Cuáles son los tres tipos de políticas de validación soportadas por OCI API Gateway para verificar tokens en tiempo de ejecución?",
                "dorso": "1. REMOTE_DISCOVERY, 2. REMOTE_JWKS, 3. STATIC_KEYS.",
                "pista_didactica": "Recuérdalos por sus alcances de red: Introspección remota, JWKS remoto, y Claves estáticas.",
                "categoria_dificultad": "Avanzado"
            }
            // ... (Más tarjetas iterando la misma estructura)
        ]
    },
    "almacenamiento_oci": {
        "bucket": "nuevamente-contenidos-educativos",
        "objeto_id": "manual-jwt-oci_senior_flashcards.json",
        "status_upload": "listo_para_subida",
        "ruta_publica_o_par": null
    },
    "codigo_respuesta": 200
}
```

### Notas para el Squad:
*   Todos los formatos comparten los nodos de alto nivel: `status`, `metadatos`, `contenido_adaptado`, `almacenamiento_oci` y `codigo_respuesta`.
*   La magia y diferencia radica exclusivamente dentro del nodo `contenido_adaptado.items`. Frontend debe hacer un renderizado condicional (*switch/if*) basado en `metadatos.formato_generado`.

---

## 3. Formato: Mapa Mental
Estructura diseñada para renderizar diagramas interactivos tipo Mindmap.

```json
{
    // ... (metadatos compartidos)
    "contenido_adaptado": {
        "titulo": "...",
        "introduccion_contextualizada": "...",
        "items": {
            "nodo_central": "Mecanismos de Autenticación OCI",
            "descripcion_general": "Diagrama de flujo de seguridad.",
            "arbol": [
                {
                    "id": "nodo-1",
                    "etiqueta": "API Gateway",
                    "subnodos": [
                        { "id": "nodo-1-1", "etiqueta": "Validación JWT", "subnodos": [] }
                    ]
                }
            ],
            "codigo_mermaid": "mindmap \n root((OCI Security))"
        }
    }
}
```

---

## 4. Formato: Guia Paso a Paso (Tutorial)
Estructura diseñada para documentaciones técnicas, laboratorios (Labs) y tutoriales iterativos.

```json
{
    // ... (metadatos compartidos)
    "contenido_adaptado": {
        "titulo": "...",
        "introduccion_contextualizada": "...",
        "items": {
            "prerrequisitos": [
                "Tener acceso a OCI Console",
                "Conocer los fundamentos de JWT"
            ],
            "pasos": [
                {
                    "numero_paso": 1,
                    "titulo_paso": "Configurar IdP",
                    "instrucciones": "Navega a la consola y crea un nuevo dominio de identidad.",
                    "bloque_codigo": null,
                    "resultado_esperado": "Se obtiene la URL JWKS."
                }
            ],
            "resumen_cierre": "Con esto el Gateway validará tokens automáticamente."
        }
    }
}
```

---

## 5. Formato: Resumen Ejecutivo
Estructura diseñada para perfiles de alto nivel (CTOs, Ejecutivos) que necesitan entender el impacto del negocio rápidamente (TL;DR).

```json
{
    // ... (metadatos compartidos)
    "contenido_adaptado": {
        "titulo": "...",
        "introduccion_contextualizada": "...",
        "items": {
            "tldr": "OCI API Gateway unifica la seguridad perimetral mediante JWT...",
            "puntos_clave": [
                "Reducción de latencia con caché local.",
                "Soporte multi-tenant nativo."
            ],
            "impacto_negocio": "Reduce los costos operativos en un 40% al evitar llamadas constantes al IdP.",
            "recomendaciones": [
                "Migrar todas las políticas heredadas a TOKEN_AUTHENTICATION."
            ]
        }
    }
}
```

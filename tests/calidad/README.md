# Evaluación de calidad con documentos cortos

Conjunto fijo de 10 documentos breves para medir la calidad del contenido generado **antes y después de cada cambio** en prompts, modelos o pipeline. Usa los proveedores reales configurados en `ia/.env` y consume cuota gratuita: unas 3 a 5 llamadas por caso la primera vez y 2 a 4 después, porque la extracción y la metadata quedan en caché en `tests/calidad/.datos/`.

## Casos

| Caso | Documento | Formato | Perfil | Nicho | Qué ejercita |
|---|---|---|---|---|---|
| `fintech` | Tokenización de tarjetas (MD) | Flashcards | Junior | Fintech | Conceptos y diferencias |
| `salud` | Triaje en urgencias (PDF) | Quiz | Senior | Salud | PDF con ligaduras; cifras de tiempos |
| `marketing` | SEO on-page (MD) | Resumen | Ejecutivo | E-commerce | Resumen sin impacto de negocio explícito |
| `ecommerce` | Logística de última milla (TXT) | Quiz | Junior | E-commerce | Texto sin títulos |
| `software` | Ramas en Git (MD) | Flashcards | Senior | General | Bloques de código |
| `datos` | Normalización SQL (MD) | Quiz | Senior | General | Tabla Markdown |
| `finanzas` | Flujo de caja (MD) | Resumen | Ejecutivo | Fintech | Cifras que no deben inventarse |
| `legal` | Protección de datos (PDF) | Flashcards | Junior | Salud | Nicho distinto del tema |
| `educacion` | Repaso espaciado (TXT, ~100 palabras) | Flashcards | Junior | General | Documento muy breve |
| `cloud_en` | Least privilege en IAM (MD, inglés) | Flashcards | Senior | Fintech | Fuente en otro idioma |

Los documentos son sintéticos, escritos para esta evaluación, y no contienen datos reales ni confidenciales.

## Ejecución

Desde la raíz del repositorio:

```bash
.venv/Scripts/python.exe tests/calidad/evaluar.py --etiqueta linea-base --pausa 20
.venv/Scripts/python.exe tests/calidad/evaluar.py --casos finanzas,legal --etiqueta prompts-v2
```

Cada corrida crea `tests/calidad/resultados/<fecha>-<etiqueta>/` con `resumen.md`, `resumen.json` y la respuesta completa de cada caso.

Si un antivirus inspecciona HTTPS (por ejemplo, el escudo web de AVG), Python rechaza los certificados con `CERTIFICATE_VERIFY_FAILED`. En ese caso, exportar los certificados raíz de Windows a un archivo PEM y definir `SSL_CERT_FILE` con su ruta antes de ejecutar.

## Métricas

| Métrica | Cómo se calcula | Valor esperado |
|---|---|---|
| Fidelidad | Puntaje del crítico (respaldadas / evaluables) | ≥ 0.85 (≥ 0.75 en Quiz) |
| Reintentos | Correcciones pedidas por el crítico | 0 |
| Ítems | Tarjetas, preguntas o puntos clave | Proporcional al documento; pocos en documentos breves |
| Cobertura | Secciones del documento citadas en las fuentes de los ítems / secciones totales | Cerca de 1 |
| Citas válidas | Ítems con fuentes que existen entre los fragmentos | 1 |
| Cifras sin respaldo | Números de la salida que no aparecen en la fuente, sin contar los distractores del quiz | Ninguna |
| Siglas sin respaldo | Siglas de la salida ausentes en la fuente | Ninguna (revisar a mano: pueden ser traducciones) |

Las cifras y siglas sin respaldo son una señal para revisar a mano, no una prueba de error: el modelo puede escribir "10" como "diez" o traducir una sigla.

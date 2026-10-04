# ADR-002: Persistencia Dual en OCI Object Storage Always Free y Control de Presupuesto
**Estado:** Aprobado  
**Fecha:** 2026-09-17  
**Autores:** Alexis Perez y Joaquín Rojas (OCI Team) & Diego Mendez y Cristian Cortes (Backend)  
**Alcance:** Infraestructura Cloud, Seguridad y Cumplimiento Normativo del Programa ONE  

---

## 1. Contexto y Problema
El reglamento oficial del Hackathon ONE (Oracle Next Education & Alura) establece como **requisito indispensable y evaluable del MVP**:
> *"Persistencia obligatoria de los documentos técnicos originales enviados y los archivos JSON de contenido educativo adaptado generados por el sistema en OCI Object Storage dentro de la capa Always Free de OCI."*

Adicionalmente, debido a la naturaleza social del programa, cualquier configuración errónea que incurra en costos monetarios para los estudiantes viola las directrices de la competencia.

---

## 2. Decisión Arquitectónica

1. **Servicio y Nivel:** Se utiliza exclusivamente **OCI Object Storage** en el tier *Standard*, manteniéndose dentro de la cuota gratuita permanente de **10 GB de almacenamiento mensual** y 50,000 solicitudes API.
2. **Estructura Jerárquica del Bucket:** El bucket `nuevamente-contenidos-educativos` adopta una topología de persistencia dual:
   - `/documentos-fuente/YYYY/MM/hash-nombre-original.ext`: Almacena el binario o texto original subido por el usuario.
   - `/artefactos-generados/YYYY/MM/hash-perfil-formato.json`: Almacena el JSON canónico final con los metadatos y contenido adaptado.
3. **Mecanismo de Autenticación Segura:** El acceso al SDK oficial de OCI (`oci` en Python) se realiza utilizando firmas criptográficas RSA mediante variables de entorno locales (`OCI_USER_OCID`, `OCI_TENANCY_OCID`, `OCI_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`), prohibiendo terminantemente subir credenciales a Git.
4. **Política Preventiva de Presupuesto:** Se implementa una alerta presupuestaria mediante **OCI Budgets** fijada en `$0.01 USD`. Ante cualquier consumo imprevisto, el equipo recibe una alerta inmediata para actuar antes de generar facturación real.

---

## 3. Consecuencias y Trade-offs

### Consecuencias Positivas:
* **Cumplimiento al 100% de la Rúbrica Oficial:** Garantiza la máxima puntuación en el criterio de persistencia en la nube de Oracle.
* **Cero Costes:** Cumplimiento estricto de la política social de Oracle Next Education ($0.00 USD).
* **Trazabilidad y Auditoría:** Cada JSON generado mantiene en sus metadatos el `objeto_id` y `status_upload` verificable en la consola web de Oracle Cloud.

### Consecuencias Negativas / Mitigaciones:
* **Dependencia de Conectividad Cloud:** Si la red o el servicio de OCI experimenta lentitud temporal, podría penalizar el tiempo de respuesta.
* **Mitigación:** La subida se realiza de manera asíncrona tras la validación del JSON, asegurando que la respuesta al cliente no se bloquee indebidamente.

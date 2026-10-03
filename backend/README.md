# Backend

API REST de adaptación de contenido educativo construida con FastAPI.

> **Estado actual:** el endpoint principal devuelve una respuesta simulada para facilitar las pruebas de integración. La conexión con IA y la persistencia en OCI todavía no están implementadas.

## Requisitos

- Docker Desktop, o Docker Engine con Docker Compose v2.

No es necesario instalar Python ni las dependencias del proyecto en la máquina local.

## Ejecutar con Docker Compose

Desde la raíz del repositorio:

```bash
docker compose -f backend/compose.yaml up --build -d
```

El Backend estará disponible en `http://localhost:8000`.

### Usar otro puerto

Si el puerto `8000` está ocupado, se puede cambiar mediante `BACKEND_PORT`.

PowerShell:

```powershell
$env:BACKEND_PORT = "18000"
docker compose -f backend/compose.yaml up --build -d
```

Bash:

```bash
BACKEND_PORT=18000 docker compose -f backend/compose.yaml up --build -d
```

En ese caso, el Backend estará disponible en `http://localhost:18000`.

## Endpoints disponibles

| Endpoint | Descripción |
|---|---|
| `GET /` | Confirma que la API está en ejecución. |
| `GET /health` | Confirma que la API responde; Docker lo utiliza para verificar el contenedor. |
| `GET /docs` | Abre la documentación interactiva de FastAPI. |
| `GET /openapi.json` | Describe los endpoints y esquemas que implementa esta versión. |
| `POST /api/v1/adaptar-contenido` | Devuelve temporalmente una adaptación simulada. |

## Verificar la API

Esta secuencia permite comprobar el arranque del Backend en Docker y probar su API desde Swagger. La versión actual devuelve una respuesta simulada; la validación del flujo real con DATA/IA requiere integrar ese servicio.

### 1. Iniciar y comprobar el servicio

Con Docker en ejecución, abrir PowerShell en la raíz del repositorio y ejecutar:

```powershell
$env:BACKEND_PORT = "18000"
docker compose -f backend/compose.yaml up --build -d --wait --wait-timeout 90
docker compose -f backend/compose.yaml ps
Invoke-RestMethod -Uri "http://localhost:18000/health"
```

El servicio `backend` debe aparecer como `healthy` y `/health` debe responder:

```json
{
  "status": "healthy",
  "service": "backend"
}
```

El puerto `18000` pertenece a la máquina local; el contenedor sigue utilizando `8000`. Si `18000` también está ocupado, elegir otro valor para `BACKEND_PORT` y usarlo en las URLs de esta guía.

### 2. Probar una solicitud desde Swagger

Abrir [Swagger](http://localhost:18000/docs), desplegar `POST /api/v1/adaptar-contenido`, pulsar **Try it out**, reemplazar el cuerpo por este JSON y pulsar **Execute**:

```json
{
  "documento_titulo": "Introduccion a redes virtuales",
  "documento_contenido": "Una red virtual permite conectar y aislar recursos en la nube. Las subredes agrupan servidores y las reglas de seguridad controlan su comunicacion.",
  "perfil_destinatario": "Principiante",
  "formato_salida": "Flashcards",
  "nicho_sector": "General",
  "nivel_detalle": "Didactico"
}
```

El resultado esperado es HTTP `200`, con `status: "exito"` y tarjetas sobre redes VCN. La respuesta es fija: cambiar el documento, el perfil o el formato no genera una adaptación diferente. Tanto la evaluación de calidad como los datos de almacenamiento son simulados; `almacenamiento_oci.status_upload` devuelve `"simulado"` y no se guarda ningún archivo en OCI.

La API implementada recibe `application/json`. Esta versión no ofrece carga de archivos ni implementa todavía el transporte `multipart/form-data` previsto en el contrato Backend–IA. Para comprobar el comportamiento actual, usar los esquemas de Swagger de esta versión.

### 3. Comprobar la validación de entrada

En el mismo endpoint, reemplazar el cuerpo por `{}` y volver a ejecutar. Debe responder HTTP `422`, indicando los campos obligatorios que faltan. También se exige un título de 3 a 150 caracteres y un contenido de al menos 50 caracteres.

### Resultados esperados

| Comprobación | Resultado esperado |
|---|---|
| Arranque con Docker Compose | Servicio `backend` en estado `healthy`. |
| `GET /health` | HTTP `200` y estado `healthy`. |
| Swagger y esquema OpenAPI | Documentación accesible y endpoint de adaptación disponible. |
| Solicitud válida del ejemplo | HTTP `200` y respuesta simulada. |
| Solicitud sin campos obligatorios | HTTP `422` con errores de validación. |

La integración con DATA/IA, la adaptación real del contenido y la persistencia en OCI quedan pendientes. Un `/health` exitoso confirma que este Backend responde, sin verificar esos servicios externos.

## Consultar logs

```bash
docker compose -f backend/compose.yaml logs -f backend
```

## Detener el servicio

```bash
docker compose -f backend/compose.yaml down
```

## Configuración

| Variable | Valor predeterminado | Propósito |
|---|---|---|
| `BACKEND_PORT` | `8000` | Puerto publicado en la máquina local. |
| `OCI_BUCKET_NAME` | `nuevamente-contenidos-educativos` | Nombre previsto para el bucket de OCI. |

Las credenciales y secretos no deben incluirse en la imagen ni versionarse en el repositorio.

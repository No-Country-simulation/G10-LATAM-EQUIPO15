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
| `GET /health` | Informa el estado de salud del contenedor. |
| `GET /docs` | Abre la documentación interactiva de FastAPI. |
| `POST /api/v1/adaptar-contenido` | Devuelve temporalmente una adaptación simulada. |

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

# Frontend de NuevaMente con Docker

La interfaz utiliza HTML, CSS y JavaScript sin compilación. La imagen sirve
los archivos con Nginx; no requiere instalar Node ni Python en el equipo.
La base de la interfaz corresponde a `feature/fe-scaffolding-ui`, commit
`edc02fc`, de Karen González.

## Arranque

Requiere Docker Desktop o Docker Engine con Compose. Desde la raíz del repositorio:

```powershell
docker compose -f frontend/compose.yaml up --build -d --wait
```

Abrir <http://localhost:18003>. El servicio se publica en loopback; dentro del
contenedor escucha en `8080` y corre como el usuario `nginx`, con el sistema de
archivos de la imagen en modo de solo lectura y temporales en `/tmp`.

Para usar otro puerto en PowerShell:

```powershell
$env:FRONTEND_PORT = "18004"
docker compose -f frontend/compose.yaml up --build -d --wait
```

El puerto predeterminado es `18003`. `FRONTEND_PORT` cambia únicamente el puerto
del equipo; no modifica la aplicación.

## Comprobaciones y cierre

```powershell
docker compose -f frontend/compose.yaml ps
curl.exe http://localhost:18003/health
docker compose -f frontend/compose.yaml logs --tail 50 frontend
docker compose -f frontend/compose.yaml down
```

`/health` devuelve `{"status":"healthy","service":"frontend"}` y comprueba
el servidor web. Los archivos inexistentes devuelven `404`.

## Estado del flujo

El formulario muestra carga, procesamiento, resultado y error. La generación
actual espera una latencia simulada y carga `mocks/respuesta-ejemplo.json`;
el resultado visual es una demostración local de flashcards. No requiere claves
ni acceso a Gemini.

La conexión real con Backend está pendiente: hay que enviar el archivo original
como multipart a `/api/v1/adaptar-contenido` y alinear los valores de perfiles y
formatos del formulario con el contrato HTTP. El campo de archivo todavía no
se incorpora a la solicitud de `js/api.js`.

## Archivos Docker

- `Dockerfile`: copia los recursos estáticos y define el healthcheck.
- `nginx.conf`: configura el servidor y el endpoint de salud.
- `compose.yaml`: configura imagen, puerto y ejecución local.
- `.dockerignore`: limita el contexto de construcción a los recursos necesarios.

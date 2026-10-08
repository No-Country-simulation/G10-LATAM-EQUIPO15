# Frontend de NuevaMente con Docker

Interfaz HTML, CSS y JavaScript, servida por Nginx sin compilación. El formulario
envía el documento al Backend real y muestra Flashcards, Quiz Interactivo o
Resumen Ejecutivo. La base visual es `feature/fe-scaffolding-ui`, commit
`edc02fc`, de Karen González.

## Arranque del sistema completo

Requiere Docker con Compose y una clave propia en el archivo privado `ia/.env`:

```dotenv
GOOGLE_API_KEY=tu-clave
```

Desde la raíz del repositorio:

```powershell
docker compose --env-file ia/.env -f compose.integration.yaml up --build -d --wait
```

Abrir <http://localhost:18003>. Backend ofrece Swagger en
<http://localhost:18002/docs>. IA recibe las claves, usa la red interna y conserva
Chroma, registro y cachés en su volumen. El navegador solo contacta al mismo
origen del Frontend: Nginx dirige `/api/` a `backend:8000`, sin configurar CORS
ni incluir direcciones internas o claves en JavaScript.

Para evitar puertos ocupados, antes de levantar el proyecto:

```powershell
$env:FRONTEND_PORT = "18004"
$env:BACKEND_PORT = "18005"
```

En un worktree se puede usar `--env-file 'C:\ruta\privada\ia.env'`. Para ejecutar
varias instancias, asignar también proyectos distintos con `-p nombre`; cada
proyecto tendrá su propio volumen. No publicar el archivo de claves ni la
configuración expandida de Compose.

## Formulario y resultados

Se envía `POST /api/v1/adaptar-contenido` con multipart y cuatro campos:

| Campo | Valores |
|---|---|
| `documento_original` | Archivo PDF, Markdown (`.md`, `.markdown`) o TXT |
| `perfil_destinatario` | `Junior`, `Senior`, `Ejecutivo` |
| `formato_salida` | `Flashcards`, `Quiz Interactivo`, `Resumen Ejecutivo` |
| `nicho_sector` | `General`, `Fintech`, `Salud`, `E-commerce` |

Los bytes originales se conservan; el navegador configura el boundary multipart.
La generación deshabilita el envío y muestra un estado de espera. Puede tardar
varios minutos. No hay reenvíos automáticos ni seguimiento SSE.

- Flashcards permite revelar el dorso y muestra pistas cuando están presentes.
- Quiz permite elegir entre cuatro opciones, comprobar la respuesta y consultar
  su justificación técnica.
- Resumen muestra TL;DR, puntos clave, impacto en el negocio y recomendaciones.

El contenido recibido se inserta como texto. Los errores de Backend aparecen
con su mensaje; los fallos de red, timeout y proxy tienen mensajes propios.
“Reintentar” conserva el archivo y la configuración. “Cambiar documento o
configuración” vuelve al formulario sin borrarlos. “Generar otro contenido”
reinicia el formulario. La evaluación de anclaje es una evaluación de IA y
requiere revisión humana para verificar fidelidad pedagógica.

## Límites y operación

El límite predeterminado de archivo es 10 MiB en Backend/IA. Nginx acepta cuerpos
de hasta 11 MiB para dejar espacio al multipart. Los presupuestos predeterminados
son 480 segundos en IA, 600 en Backend, 650 en el proxy y 660 en el navegador.
Al cambiar los límites de Backend/IA, revisar también `nginx.conf` y `js/api.js`.
Nginx evita reenviar una solicitud a otro upstream automáticamente.

```powershell
docker compose --env-file ia/.env -f compose.integration.yaml ps
curl.exe http://localhost:18003/health
docker compose --env-file ia/.env -f compose.integration.yaml down
```

`/health` comprueba el servidor web, sin contactar a Backend ni Gemini. `down`
conserva el volumen de IA. Los puertos de desarrollo se publican en loopback;
el acceso público y HTTPS corresponden al despliegue de Cloud.

Para servir únicamente los recursos estáticos:

```powershell
docker compose -f frontend/compose.yaml up --build -d --wait
```

La carga del sitio y `/health` funcionan sin Backend; generar contenido exige
un servicio `backend:8000` en la misma red. Para el flujo completo, usar el
Compose de integración. La imagen excluye los tests y el antiguo ejemplo mock.

## Pruebas reproducibles sin claves

Desde la raíz, ejecutar 46 comprobaciones:

```powershell
docker compose -f compose.frontend.tests.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.frontend.tests.yaml down
```

Este proyecto separado no publica puertos ni utiliza claves o volúmenes de la
aplicación. Ejecuta 24 pruebas unitarias y 15 HTTP, más 7 pruebas del recorrido
Nginx → Backend real → IA simulada. Verifica los tres formatos, los bytes y campos
multipart originales, los rechazos antes de contactar a IA, errores 422/503 y
el límite de cuerpo del proxy. La red de ejecución es interna; construir las
imágenes puede necesitar Internet. El primer comando devuelve un código distinto
de cero si falla una prueba; no ejecutar el cierre antes de revisar ese código.

También se pueden ejecutar solo las 39 comprobaciones del Frontend:

```powershell
docker compose -f frontend/compose.tests.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f frontend/compose.tests.yaml down
```

Con Node 24 instalado, las unitarias se ejecutan con
`node --test frontend/tests/unit.test.cjs`. Node se usa únicamente para pruebas.

- `tests/unit.test.cjs`: estados, contrato del cliente, errores y visores con DOM
  controlado, incluidos texto HTML literal y respuestas del Quiz.
- `tests/http.test.cjs`: recursos estáticos, tipos de contenido, salud, opciones
  del formulario y archivos privados/no publicados.
- `tests/proxy.test.cjs`: transporte completo con Backend real.
- `tests/ia_fixture.py`: IA explícitamente simulada, únicamente para estas pruebas.

Estas suites no verifican interacción visual en un navegador ni llaman a Gemini.
El ensayo real Backend → IA está en [tests/README.md](../tests/README.md).
Para comprobar manualmente el recorrido desde el navegador, levantar el sistema
completo, cargar un documento de prueba público, generar, revisar el visor y
volver a empezar. Repetir para los tres formatos; probar también archivo vacío,
extensión inválida y reintento. Cada generación real consume cuota del proveedor.

## Pendientes

OCI Object Storage, despliegue público y SSE siguen pendientes. La integración
actual no promete que el contenido esté guardado en OCI.

# Historial de documentos por navegador

Alcance aprobado el 21-10-2026. Rama `feat/historial-documentos`, desde consolidación;
sin mezclar cambios de IA y sin commits automáticos.

## Resultado esperado

Subir y generar una vez, volver desde el mismo navegador, localizar el documento,
abrir o descargar un resultado sin llamar a IA y solicitar otro formato sin reenviar
el original desde el navegador. Los tres formatos conservan sus vistas actuales.

## Identidad y acceso

Sin login: Backend crea un secreto aleatorio de 256 bits en cookie HttpOnly,
SameSite=Lax, persistente un año. Su hash determina el prefijo privado del catálogo
en OCI. No se acepta un propietario ni una ruta OCI suministrados por el cliente.
Cada consulta resuelve identificadores dentro del prefijo de ese navegador.
Otro navegador, un identificador ajeno o una cookie inválida no permiten leer objetos.
Las operaciones con Origin ajeno se rechazan. API privada sin caché HTTP compartida.
Todas las respuestas privadas usan `Cache-Control: no-store`, incluso descargas y errores.
Frontend prepara la cookie mediante una consulta sin acceso a OCI, antes de enviar solicitudes.
En localhost y HTTPS usa Web Locks para serializar esa preparación entre pestañas.
Si falla la conexión, el siguiente envío explícito vuelve a prepararla, sin repetir el POST.
Una carga
con catálogo habilitado pero sin identidad inicializada se rechaza con 409 antes
de invocar IA; la respuesta establece la cookie para el siguiente intento explícito.
Cookie Secure en HTTPS; en HTTP el token viaja sin protección de transporte y Web Locks
puede no estar disponible. El despliegue público con datos privados debe usar HTTPS.
Con TLS terminado delante de Nginx, definir `HISTORY_COOKIE_SECURE=true` en el entorno
del Compose. Esa opción se propaga a Backend sin depender del esquema interno del proxy.

Los archivos y catálogos permanecen en OCI. Borrar las cookies o cambiar de navegador
pierde el acceso automático, no borra los objetos. No hay recuperación de identidad
ni migración de los objetos antiguos, que no tienen propietario.

## Persistencia y fallos

Se reutiliza la persistencia dual existente del original y del JSON aprobado. Los nuevos
archivos se aíslan por propietario en `historial-archivos-v1/{owner}/`; el JSON también
identifica su referencia de origen para evitar sobrescribir nombres entre documentos.
La persistencia anterior conserva sus rutas cuando el historial está deshabilitado. Solo
después de confirmar ambas subidas se publica el catálogo versionado `historial-v1/`:
un manifiesto por documento y uno por adaptación, con nombre original, fecha,
configuración e identificadores internos. El resultado de una generación sigue
disponible si falla OCI o el catálogo; la interfaz informa que no está confirmado
en el historial. Un manifiesto de documento sin adaptaciones muestra lista vacía.

Se usa OCI sin otra base de datos: un índice SQL sería más flexible para búsquedas,
pero añade respaldo y sincronización para este MVP. Listados paginados y lecturas
acotadas. Original descargado comprobado por SHA-256 y límite de tamaño. JSON
recuperado validado con el contrato existente y la configuración del manifiesto.
No hay reintentos automáticos de generación. Las eliminaciones son explícitas y
requieren confirmación en la interfaz.

## Eliminar documentos y resultados

Cada documento y resultado tiene una papelera visible, con nombre accesible y
superficie de 44 px. El diálogo enfoca Cancelar; Escape cancela. No hay peticiones
DELETE antes de confirmar. Mientras se elimina se bloquean los controles del
historial, se informa el progreso y se evita el doble envío.

Eliminar un resultado conserva el original y los demás resultados. Un JSON
compartido no se elimina mientras otra adaptación lo referencie. Eliminar un
documento incluye todos sus resultados, todas las páginas del catálogo y las
variantes de sus archivos dentro del espacio de este navegador en OCI. No toca
objetos de otros navegadores, archivos antiguos sin propietario ni la caché de IA.
La confirmación muestra el número real de resultados. Si otra pestaña modifica
el catálogo, el servidor rechaza la versión antigua y se debe confirmar de nuevo.

Un registro de operación en `historial-control-v1/{owner}/` permite retomar un
borrado parcial y reconocer solicitudes repetidas. Tras completarse conserva
solo un recibo de control, sin el nombre ni el contenido del documento/resultado.
Un borrado incompleto se muestra con su papelera para reintentar; abrir o reutilizar
esos elementos se bloquea. El elemento se retira de la interfaz al confirmar éxito.
Las generaciones que comenzaron antes de eliminar un documento no lo vuelven a
publicar; volver a cargarlo después es una acción nueva y explícita.

El backend MVP se ejecuta con un único worker, fijado en su Dockerfile. Serializa
la persistencia y las eliminaciones de cada navegador mediante locks en ese
proceso; la generación de IA ocurre fuera del lock. Antes de escalar a varios
procesos o réplicas se requiere coordinación distribuida. Los registros de
operación sí persisten en OCI y permiten retomar después de reiniciar el backend.

## API y Frontend

- GET `/api/v1/documentos`: documentos del navegador, con paginación.
- GET `/api/v1/historial/sesion`: prepara la cookie sin consultar OCI ni invocar IA.
- GET `/api/v1/documentos/{id}/adaptaciones`: resultados de un documento.
- GET `/api/v1/documentos/{id}/original`: descarga del original.
- GET `/api/v1/documentos/{id}/eliminacion`: nombre, cantidad total y versión
  para la confirmación de borrado.
- DELETE `/api/v1/documentos/{id}`: original y resultados del navegador. Exige
  `If-Match` con la versión confirmada; 428 sin confirmación y 409 si cambió.
- DELETE `/api/v1/documentos/{id}/adaptaciones/{adaptacion}`: un resultado;
  conserva las referencias compartidas y permite reintentar la misma solicitud.
- GET `/api/v1/documentos/{id}/adaptaciones/{adaptacion}`: resultado almacenado.
- GET con sufijo `/descarga`: descarga JSON como adjunto.
- POST `/api/v1/documentos/{id}/adaptaciones`: configuración JSON, obtiene el original
  autorizado desde OCI y utiliza el mismo cliente IA y validaciones existentes.

La carga normal registra los documentos nuevos. El navegador ofrece Mis documentos,
estados cargando/vacío/error, Ver resultados, Abrir, Descargar y Usar documento.
Abrir llama solo a OCI y reutiliza el renderer actual, incluido el quiz.
Crear otra adaptación es explícito y puede consumir cuota; no implementa la caché
automática de resultados de BL-11. Las nuevas entradas actualizan la lista.

## Verificación

Pruebas de Backend con SDK OCI y transporte controlado: identidades independientes,
recarga, formatos, descargas exactas, cero llamadas IA al abrir, readaptación con
bytes exactos del original, objetos ausentes/corruptos, fallos parciales y Origin.
Pruebas de Frontend, Nginx y Backend en Docker; recorrido real de navegador con
persistencia controlada y servicios externos simulados. Comprobación adicional
contra OCI real si la configuración local está disponible, sin exponer secretos.
Las aperturas pendientes se invalidan al navegar o empezar una generación; una respuesta
antigua no puede reemplazar el trabajo nuevo. Los tests anteriores deben seguir pasando.
Publicación y despliegue son posteriores.

Resultado de la validación del cambio (cierre 22-10-2026):

- Backend: **95 pruebas aprobadas**, con SDK OCI y transporte controlado, sin red.
- Frontend/HTTP/Nginx: **74 pruebas aprobadas**, incluidas carreras de navegación,
  dos pestañas y recuperación después de un fallo inicial de conexión.
- Punta a punta con **OCI real: 4 pruebas aprobadas**. Los tres formatos permiten
  listar, abrir, descargar y readaptar; otro navegador recibe 404 al pedir un recurso ajeno.
- Navegador real: original descargado idéntico por SHA-256, una llamada adicional
  únicamente al pedir otro formato y los mismos bytes originales enviados a IA.
  Después de reiniciar Backend quedaron disponibles el documento y sus dos resultados.
- Vista revisada en escritorio y a 375 px, sin desbordamiento horizontal.

En todas estas pruebas la IA estuvo simulada para no consumir cuota de Gemini;
la comprobación contra OCI real sí guardó y recuperó objetos nuevos del bucket.

### Validación del borrado (22-10-2026)

- Backend: **109 pruebas aprobadas**, incluido borrado por navegador, JSON con
  referencias compartidas, confirmación desactualizada, 26 resultados paginados,
  fallos parciales y generación en curso durante el borrado.
- Frontend/HTTP/proxy: **84 pruebas aprobadas**, incluidas cancelación, Escape,
  doble clic, errores recuperables y retorno del foco después de eliminar.
- Integración completa: **5 pruebas aprobadas**, incluidos los tres formatos y
  eliminar un resultado o todo el documento sin nuevas llamadas a IA.
- Navegador real a 1410 × 1117 y 375 × 812: papeleras de 44 × 44 px, sin
  desbordamiento horizontal; cancelación sin borrar, confirmación con cantidad
  real, documento conservado al eliminar su último resultado y persistencia
  después de recargar. Sin errores de consola en los recorridos revisados.

Estas **198 pruebas** y los recorridos de borrado usan almacenamiento controlado
y una IA simulada. No borran documentos reales en OCI ni consumen cuota de IA.
El cambio se valida localmente; este registro no acredita un despliegue en AWS.

### Ejecutar las pruebas

Backend sin red ni credenciales:

```powershell
docker compose -f backend/compose.yaml --profile tests run --build --rm backend-tests
```

Regresión de Frontend y proxy, con IA simulada y OCI deshabilitado:

```powershell
docker compose -f compose.frontend.tests.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.frontend.tests.yaml down
```

Historial completo, SDK OCI con bucket HTTP controlado persistente e IA simulada:

```powershell
docker compose -f compose.history.tests.yaml up -d --build --wait frontend
docker compose -f compose.history.tests.yaml run --rm --no-deps tests
docker compose -f compose.history.tests.yaml down
```

La QA de historial publica únicamente `127.0.0.1:18008`. No reemplaza el despliegue
normal ni llama a Gemini. `backend/tests/history_real_server.py` permite una comprobación
optativa con el ZIP OCI privado montado como `/run/secrets/oci-connection.zip`, usando
la misma IA simulada. Ese archivo de QA no se incorpora a la imagen de producción.
No montar el ZIP en Git ni imprimir su contenido. La prueba crea solo documentos nuevos.

### Uso local y despliegue posterior

Conservar la configuración OCI que ya funciona y `HISTORY_ENABLED=true` (predeterminado).
Levantar el Compose de integración con el montaje privado existente. No se necesita
crear otra base de datos ni importar objetos anteriores. Con OCI deshabilitado la carga
y generación normal siguen funcionando; Mis documentos informa que falta almacenamiento.
Después de publicar estos cambios, reconstruir Frontend y Backend con el procedimiento
habitual. Los datos del historial quedan en OCI y sobreviven a la recreación de contenedores.

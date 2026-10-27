# Demostracion local con OCI Object Storage

Validacion real realizada el 14 de octubre de 2026 en Docker local, con Gemini
en modo estricto y el bucket privado `nuevamente-contenidos-educativos` de la
cuenta `dgomenfran`, region `sa-saopaulo-1`.

## Levantar la aplicacion

Abrir Docker Desktop y esperar a que este listo. Desde esta copia del proyecto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/iniciar-local-oci.ps1
```

El iniciador valida los archivos privados, construye las imagenes, espera los
servicios saludables, comprueba que OCI este activado y muestra la URL real.
Los puertos predeterminados son:

- Aplicacion: <http://localhost:18003>.
- Swagger de Backend: <http://localhost:18002/docs>.
- IA: red interna de Docker.

Requiere `ia/.env` con la configuracion de Gemini y
`%LOCALAPPDATA%\NuevaMente\oci-storage\oci.env`, generado por
[el instalador de la conexion OCI](CONFIGURAR_OBJECT_STORAGE.md).
Las credenciales OCI estan fuera del repositorio y se montan solo en Backend.

## Tres ejemplos para presentar

Usar el documento [JWT en OCI.pdf](<../nuevamente-ai-core/tests/JWT en OCI.pdf>),
seleccionar nicho `General` y ejecutar estos casos:

| Caso | Perfil | Formato | Resultado comprobado |
|---|---|---|---|
| 1 | Junior | Flashcards | Generacion y original + JSON guardados en OCI |
| 2 | Senior | Quiz Interactivo | Generacion y original + JSON guardados en OCI |
| 3 | Ejecutivo | Resumen Ejecutivo | Generacion y original + JSON guardados en OCI |

Los tres se ejecutaron mediante el formulario del navegador, Backend real y
Gemini. El documento ya tenia vectores y cache en el volumen de IA: estas
ejecuciones reutilizaron su ingesta. Un documento nuevo debe recorrer tambien
extraccion, enriquecimiento y embeddings y puede tardar varios minutos.

El resultado debe mostrar **Documento original y contenido guardados en OCI**.
La respuesta de Backend debe contener `almacenamiento_oci.status_upload=subido`
y `documento_original_subido=true`.

## Evidencia del almacenamiento

Se descargaron mediante el SDK y autenticacion API key ambos objetos de cada
caso. El original coincidio byte a byte con el PDF y el JSON con la respuesta
validada del Backend, restaurando los tipos del contrato antes de comparar su
serializacion canonica. El navegador representa `1.0` como `1` en JSON.

- SHA-256 del PDF original:
  `ac3757fe5aec7fe92c001c7109f7f0d49ea9dbfe5a2a803537ed1ce19160735b`.
- Bucket: privado, Standard, auto-tiering Disabled.
- El mismo original se reutilizo en los tres casos; cada salida tiene un objeto
  JSON distinto en `artefactos-generados/2026/10/`.
- El original esta en `documentos-fuente/2026/10/`.

Las respuestas, capturas y reportes de descargas estan en la carpeta local
`.gstack/demo-oci-20261014/`, excluida de Git. No contienen claves de acceso.
Son evidencia de estas ejecuciones; futuras generaciones pueden variar.

## Proximo arranque

Volver a ejecutar el mismo iniciador conserva el volumen de IA. No usar
`docker compose down --volumes` sobre el proyecto de trabajo: elimina los
vectores y caches locales. La aplicacion debe tener acceso a Internet para
Gemini y OCI, incluso cuando se ejecuta en el equipo local.

Se recreo el contenedor de IA conservando su volumen y se comprobaron los
nueve vectores del documento, el registro y los hashes de las caches:
permanecieron identicos. El iniciador tambien se ejecuto satisfactoriamente
contra los tres servicios saludables.

Esta evidencia acredita Docker local y OCI Object Storage. Posteriormente se
completo el [despliegue Azure con Terraform](AZURE_TERRAFORM.md), con tres pruebas
desde la URL publica y descargas autenticadas de los objetos OCI de cada caso.

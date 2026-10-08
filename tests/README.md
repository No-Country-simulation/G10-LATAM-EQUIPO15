# Pruebas de Backend, Data/IA y AI Core

Las pruebas existentes están versionadas en `backend/tests`, `ia/tests` y
`nuevamente-ai-core/tests`. Estos comandos reúnen las suites de la integración
consolidada (Fase A y cambios de AI Core) y reproducen también el ensayo real con Gemini. Requieren Docker con
Compose y PowerShell; no requieren instalar Python en el equipo.

## Suite sin proveedores

Desde la raíz del repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/probar-integracion.ps1
```

Se construyen las imágenes de pruebas y se ejecutan, por separado:

| Suite | Alcance |
|---|---|
| Backend | Multipart y bytes originales, validación de entradas y respuesta, errores, timeout y contrato HTTP con IA simulada |
| Data/IA | Extracción de PDF, identidad por hash, chunking, cachés y persistencia real de Chroma entre procesos nuevos |
| HTTP de IA | Archivo temporal, concurrencia, limpieza, errores del proveedor y validación de configuración |
| AI Core | Esquemas, grafo, pipeline local y crítico, con generación y embeddings simulados explícitamente |

Los contenedores ejecutan las pruebas con `network_mode: none`, sin claves ni
volúmenes de datos de la aplicación. La construcción sí necesita Internet si
faltan imágenes o dependencias. El script finaliza con código distinto de cero
ante el primer fallo y guarda reportes JUnit en un directorio nuevo de TEMP.

Para ejecutar las suites manualmente, también desde la raíz:

```powershell
docker compose -f compose.tests.yaml build
docker compose -f compose.tests.yaml run --rm backend-tests
docker compose -f compose.tests.yaml run --rm ia-tests
```

## Ensayo real Backend -> IA -> Gemini

Crear el archivo local `ia/.env` con la clave propia:

```dotenv
GOOGLE_API_KEY=tu-clave
```

Este archivo está ignorado por Git y excluido de las imágenes. Se admiten las
opciones de proveedor documentadas en [ia/README.md](../ia/README.md), incluida
la clave opcional `DATAIA_GOOGLE_API_KEY`. No mostrar la configuración expandida
de Compose ni compartir las claves.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/probar-integracion.ps1 -Gemini
```

Cada ejecución crea un proyecto y volumen de ensayo nuevos, sin publicar puertos
ni tocar los contenedores o volúmenes de trabajo. Realiza estas comprobaciones:

1. Backend e IA responden a `/health` y Backend rechaza un perfil inválido.
2. Envía `nuevamente-ai-core/tests/JWT en OCI.pdf` mediante multipart a Backend,
   con perfil Junior, formato Flashcards y nicho General.
3. Exige HTTP 200, los seis campos públicos, calidad aprobada, almacenamiento pendiente y flashcards con frente y dorso.
   Comprueba que se crearon vectores, registro y caché y que se ejecutaron las
   etapas de enriquecimiento, embeddings, generador y crítico.
4. Recrea el contenedor de IA conservando el volumen; verifica que su id cambió
   y que los ids de vectores y hashes de registro y cachés se conservan.
5. Repite la adaptación. Comprueba que no se repiten enriquecimiento ni embeddings
   de documento, y que generador y crítico sí vuelven a ejecutarse.

El ensayo hace **dos adaptaciones reales**, que consumen cuota y pueden involucrar
reintentos del proveedor. No usa mocks ni acepta el borrador de contingencia:
se ejecuta Gemini en modo estricto. El modelo predeterminado y los timeouts son
los de la integración, configurables en `ia/.env`.

Al terminar, incluso ante un fallo, el script elimina únicamente sus contenedores
y volumen temporales. Los resultados privados permanecen en TEMP: JUnit,
respuestas, tiempos, snapshots, contadores de etapas y categorías de fallo del
proveedor. No se suben a Git ni se guardan los logs completos o las claves.
Que el crítico apruebe no sustituye la revisión humana de fidelidad pedagógica.
Esto no verifica la interacción en Frontend ni almacenamiento en OCI.

## Opciones

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/probar-integracion.ps1 -Gemini -EnvFile 'C:\ruta\privada\ia.env'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/probar-integracion.ps1 -DockerContext desktop-linux
```

`-EnvFile` permite usar un archivo privado existente, útil si se trabaja en un
worktree. `-ResultsDirectory` permite indicar otra carpeta privada para resultados;
elegir una fuera del repositorio. Cada miembro del equipo usa sus propias claves.

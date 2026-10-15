# VM Azure con Terraform y aplicacion validada con OCI

El script usa Docker Desktop para ejecutar Azure CLI 2.91.0 y Terraform 1.16.6.
La VM, red, IP, reglas de acceso, disco y extension de verificacion SSH estan
declarados en `infra/azure/main.tf`. La aplicacion sigue guardando originales y
JSON en OCI Object Storage mediante API key.

## Comprobacion del 14 de octubre de 2026

La cuenta autentico correctamente como `FreeTrial_2014-09-01`, habilitada y con
limite de gasto `On`. Se registraron `Microsoft.Compute` y `Microsoft.Network`.
Se creo `Standard_D2as_v6` en
`brazilsouth`, con 2 vCPU, 8 GB, Ubuntu `24.04.202609040` y disco de 64 GB.
Terraform completo **9 altas, 0 cambios y 0 bajas**. Una reanudacion posterior
confirmo cero cambios y completo la instalacion. Se aplico ademas un ajuste
de la IP publica a 15 minutos de espera, sin reemplazos, para admitir las
generaciones largas del proxy. Las once pruebas del script pasaron.

**Aplicacion publica:** <http://191.237.254.59>.

Frontend, Backend e IA iniciaron saludables en la VM. El Backend confirmo
acceso autenticado al bucket privado `nuevamente-contenidos-educativos`.
Desde un navegador externo se cargo un PDF sintetico nuevo y se completaron
estos tres casos con Gemini, proveedores estrictos y almacenamiento OCI:

| Perfil | Formato | JSON descargado | SHA-256 del JSON |
| --- | --- | ---: | --- |
| Junior | Flashcards | 4971 bytes | `b1b20225fb265e24e79dc247e7de2b951eacb05a033e49f9f783f28e4497de84` |
| Senior | Quiz Interactivo | 5285 bytes | `84a3731622de60c56dfdfd03a2c86b2ea720038d0bec0dd1600a32073b2eb9cc` |
| Ejecutivo | Resumen Ejecutivo | 3132 bytes | `56e68efabe00fe47eaef8c52f3ba173f476b245b929136f6371ebf9dd0a8076f` |

Cada caso devolvio `status_upload=subido` y `documento_original_subido=true`.
Se descargaron el original y cada JSON mediante SDK autenticado y se compararon
byte a byte: seis descargas HTTP 200, un PDF compartido y tres JSON distintos.
El original tiene 4014 bytes y SHA-256
`686696e83ac8086ba5a823a1b594dcf8d0697ce813b545f1eba17ee88b3dc580`.
El cuestionario tambien se probo seleccionando una respuesta y mostrando su
justificacion. No se observaron errores JavaScript en estas ejecuciones.

El PDF se genero para esta prueba desde
[`ejemplos/demo-sintetica-documentos.md`](ejemplos/demo-sintetica-documentos.md),
sin documentos privados. PDF, respuestas, capturas y reportes de descarga estan
en `.gstack/demo-azure-20261014/`, carpeta local excluida de Git y sin claves.
Son evidencia de estas ejecuciones; futuras generaciones pueden variar.
La validacion local anterior se conserva en [DEMO_LOCAL_OCI.md](DEMO_LOCAL_OCI.md).

## Iniciar sesion desde Windows

Desde esta copia del proyecto, en PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/azure.ps1 -Accion Login
```

Seguir la direccion y codigo que muestra Microsoft en la terminal. Completar el
inicio de sesion y el segundo factor en el navegador. La sesion se guarda bajo
`%LOCALAPPDATA%\NuevaMente\azure`, con acceso restringido al usuario de Windows.

## Revisar disponibilidad y preparar el plan

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/azure.ps1 -Accion Revisar
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/azure.ps1 -Accion Plan
```

El primer comando consulta la suscripcion, restricciones de SKU y cuotas
regionales y de familia. No crea recursos. La busqueda inicial incluye
`brazilsouth`, `eastus2`, `centralus` y `westus3`, para perfiles x64 de 2 vCPU y
8 GB. Se pueden cambiar con `-Regiones`. Catalogo y cuota no reservan capacidad.
El catalogo se filtra por region en la API oficial y se recorren todas sus
paginas, para evitar la descarga global lenta de `az vm list-skus`.

El segundo prepara Terraform y muestra el plan. Detecta la IPv4 publica mediante
`https://api.ipify.org` para permitir SSH solo desde esa direccion con `/32`.
Resuelve una version concreta de Ubuntu 24.04 y genera una clave ED25519 privada
fuera del repositorio; Terraform recibe unicamente su parte publica.
En una cuenta nueva registra primero `Microsoft.Compute` y `Microsoft.Network`.
Este paso habilita los proveedores requeridos sin crear la VM; antes del
registro, Azure puede devolver cuotas vacias en `Revisar`.

Ambos exigen una suscripcion habilitada cuya oferta se identifique como
`FreeTrial` y cuyo limite de gasto este `On`. No convierten la cuenta a pago por
uso ni alteran el limite. Si hay varias suscripciones habilitadas, indicar
`-SuscripcionId`.

## Desplegar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/azure.ps1 -Accion Desplegar
```

Esta accion consume credito de la prueba. Ejecuta `init`, `validate`, `plan` y
`apply` del plan guardado; se detiene si el plan incluye eliminar o reemplazar
recursos. Crea un grupo `nuevamente-demo-rg` con una VM Ubuntu 24.04, 2 vCPU,
8 GB, disco Standard SSD de 64 GB, IP publica estatica y red. Abre la aplicacion
por HTTP 80 y restringe SSH 22 a la IPv4 detectada. Backend e IA no se publican
directamente. Es un despliegue HTTP de demostracion; HTTPS requiere una fase
adicional.
La IP permite 15 minutos de inactividad en conexiones entrantes, por encima
de los 650 segundos que permite el proxy durante una generacion.

Cloud-init instala Docker desde el repositorio oficial. Despues el script:

1. Verifica la clave publica SSH de la VM mediante una extension administrada
   por Terraform, leida a traves de Azure. Mantiene `StrictHostKeyChecking=yes`.
2. Empaqueta la copia local, incluyendo cambios sin commit, con los archivos de
   ejecucion no ignorados por Git. Excluye `.env`, claves, caches y pruebas.
3. Transfiere el paquete y comprueba su SHA-256 en la VM.
4. Transfiere por SSH la conexion OCI y Gemini desde sus archivos privados,
   separados del paquete, a `/home/azureuser/.nuevamente-private`.
5. Construye las imagenes y levanta Compose con reinicio automatico y volumen
   persistente para IA. Muestra la URL cuando obtiene HTTP 200 desde Internet.

Usa por defecto la misma conexion OCI instalada para la demostracion local.
`-OciDirectorio` y `-GeminiEnvFile` permiten indicar otras rutas privadas.
Los secretos no se pasan por Terraform, cloud-init, Git ni argumentos de red.

## Estado y reanudacion

El estado, planes, clave SSH, inventario y configuracion elegida se conservan en
`%LOCALAPPDATA%\NuevaMente\azure`, fuera del repositorio y del contenedor de
herramientas. Cerrar la terminal no elimina lo ya creado; volver a ejecutar
`Desplegar` retoma usando ese estado. Conservar y respaldar esta carpeta de
forma privada. Si se interrumpe una operacion Azure aun en curso, consultar su
estado antes de repetirla; el script no fuerza desbloqueos de Terraform.
Una vez desplegada, la VM ejecuta Docker por su cuenta: cerrar Docker Desktop
o apagar la computadora local no detiene la aplicacion en Azure. Esto depende
de que la VM y la suscripcion continuen habilitadas y tengan credito disponible.

La ubicacion, tamano e imagen se conservan despues de preparar el primer plan.
No borrar `deployment.json` ni el estado para cambiar de perfil. El script no
importa ni elimina recursos preexistentes automaticamente. Tampoco realiza
sondeos indefinidos de capacidad.

La VM, el disco y la IP consumen credito mientras corresponda. Al terminar la
entrega se deben eliminar mediante Terraform usando este mismo estado. Una
alerta de presupuesto no sustituye el limite de gasto de la prueba.

## Validacion tecnica

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/azure.ps1 -Accion Validar
python -B -m unittest discover -s scripts/azure/tests -p test_guardas.py -v
```

`Validar` inicializa el proveedor y valida HCL y el script Bash sin iniciar
sesion ni crear recursos. Esto no acredita disponibilidad ni despliegue real.
La comprobacion del inicio de esta guia completo tambien las pruebas reales
de navegador y las descargas OCI; la validacion HCL por si sola no las reemplaza.

Referencias: [Azure CLI en Docker](https://learn.microsoft.com/en-us/cli/azure/run-azure-cli-docker),
[VM Linux mediante Terraform](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-terraform),
[limite de gasto](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit),
[Docker en Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

# Procesamiento de documentos y contenido educativo

Documento sintetico creado para una prueba tecnica. Describe un proyecto
ficticio llamado Aula Nube. No contiene datos personales, claves, informacion
de clientes ni documentos privados. Puede enviarse a los servicios de la demo.

## Objetivo del sistema

Aula Nube transforma documentos tecnicos en materiales educativos para personas
con distintos conocimientos. El sistema recibe un archivo, extrae su texto,
prepara una adaptacion y conserva el documento original junto con el resultado.
La finalidad es ayudar a comprender conceptos; una respuesta generada necesita
revision humana antes de utilizarse como material oficial.

La interfaz ofrece tres perfiles. El perfil principiante necesita definiciones,
ejemplos pequenos y explicaciones graduales. El perfil tecnico conoce conceptos
basicos y busca relaciones, decisiones de diseno y limitaciones. El perfil
ejecutivo necesita entender el objetivo, los beneficios y los riesgos sin entrar
en los detalles de cada biblioteca o comando.

## Entrada y validacion

El ejemplo admite PDF con texto, Markdown y texto plano. Primero se comprueba
que exista un archivo, que su tipo sea admitido y que su tamano respete el limite
configurado. El nombre del archivo no demuestra que su contenido sea valido.
Si el archivo esta vacio o no permite extraer texto, la interfaz debe explicar
el problema para que la persona pueda corregirlo.

El servicio conserva una referencia al documento y calcula una huella de sus
bytes. Esta huella permite comparar copias y detectar si el contenido cambio.
Dos archivos pueden tener el mismo nombre y contenidos diferentes. Por eso,
identificar un documento solo por su nombre puede causar confusiones.

## Extraccion y recuperacion de contexto

La etapa de extraccion obtiene texto legible. Despues se divide el texto en
fragmentos para trabajar con partes de un documento extenso. Los fragmentos
deben conservar su relacion con el documento de origen. Una separacion que
corte una definicion por la mitad puede dificultar su interpretacion.

Un indice vectorial ayuda a recuperar fragmentos relacionados con una consulta.
La similitud permite seleccionar contexto, pero no garantiza que una respuesta
sea correcta. El generador necesita utilizar el contenido recuperado y evitar
presentar como hechos las ideas que no aparecen en el documento.

Si el contexto es insuficiente, el resultado debe reconocer esa limitacion.
Inventar una fecha, una medida o una conclusion para completar una respuesta
reduce la confianza. Una revision adicional puede comprobar si los conceptos
generados coinciden con el texto y si el formato solicitado se respeta.

## Formatos educativos

Las tarjetas de estudio presentan una pregunta breve y su respuesta. Son utiles
para practicar definiciones y relaciones. Cada tarjeta debe tratar una idea
concreta; una tarjeta con cinco preguntas distintas resulta dificil de repasar.

Un cuestionario interactivo presenta preguntas, opciones y explicaciones. Las
opciones incorrectas deben ser plausibles para evaluar comprension. La
justificacion explica por que una opcion es adecuada segun el documento y evita
que la actividad se reduzca a memorizar una letra.

El resumen ejecutivo organiza las ideas principales, sus implicaciones y las
limitaciones relevantes. Debe priorizar lo que ayuda a comprender una decision.
Un resumen breve no debe ocultar una condicion que cambie la conclusion del
documento original.

## Almacenamiento y operacion

En este ejemplo ficticio, el archivo original y el resultado JSON se guardan
como objetos separados en un bucket privado. Cada resultado conserva su
referencia de objeto. El acceso al almacenamiento utiliza credenciales del
servidor; la interfaz del navegador no recibe las claves privadas.

Confirmar una escritura no basta para verificar todo el recorrido. La prueba
descarga ambos objetos mediante un cliente autenticado y compara su contenido
con los datos enviados. Si un servicio externo falla, la aplicacion debe mostrar
el estado real y permitir una accion comprensible, sin declarar un exito que
no pudo comprobar.

La aplicacion puede ejecutarse en contenedores tanto en una computadora como
en una maquina virtual. Los archivos privados de configuracion se mantienen
separados del codigo. Un volumen conserva los datos que necesitan sobrevivir
al reinicio de un contenedor. Tener una copia de seguridad sigue siendo una
responsabilidad distinta de mantener el proceso en ejecucion.

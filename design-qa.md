# QA: eliminar documentos y resultados

Revisión local del 22-10-2026 sobre `release/consolidacion-mvp`.
Alcance: opción 2 elegida por el usuario, papeleras visibles y confirmación
obligatoria; implementación en la rama existente, sin commit ni despliegue.

## Referencia y evidencia

- Source visual truth: `C:\Users\59598\.codex\generated_images\01a10340-0c57-7b42-a8ac-85138bc44be1\exec-28d76009-4e7f-411e-8a69-b8550f473880.png`.
  Raster de 1410 × 1116 px, opción 2. No proporciona una tipografía original
  identificable ni una especificación de densidad CSS.
- Implementación: `http://127.0.0.1:18008/`, sección Mis documentos,
  con almacenamiento e IA controlados para QA.
- Captura de escritorio: `C:\Users\59598\AppData\Local\Temp\nuevamente-borrado-desktop.png`.
  Viewport CSS 1410 × 1117, escala 1; recorte de la sección de 1180 × 1032 px.
- Comparación conjunta: `C:\Users\59598\AppData\Local\Temp\nuevamente-borrado-comparacion.png`.
  Captura del navegador de 1380 × 1200 px con ambas imágenes lado a lado.
  Las vistas completas se normalizaron a 660 px de ancho; debajo aparecen
  recortes de los documentos expandidos, también normalizados al mismo ancho.
  El rótulo de la galería redondea por error la altura de la fuente a 1117;
  la dimensión real comprobada mediante `naturalHeight` es 1116.
- Móvil: `C:\Users\59598\AppData\Local\Temp\nuevamente-borrado-mobile.png`.
  Viewport CSS 375 × 812, escala 1; captura completa de la sección desplazable.
- Confirmación de documento en móvil:
  `C:\Users\59598\AppData\Local\Temp\nuevamente-borrado-confirmar-documento-mobile.png`.
- Confirmación de resultado en escritorio:
  `C:\Users\59598\AppData\Local\Temp\nuevamente-borrado-confirmar-resultado.png`.
- Estado posterior al ajuste de foco:
  `C:\Users\59598\AppData\Local\Temp\nuevamente-borrado-foco-corregido.png`.

Todas las capturas anteriores se abrieron y revisaron. La comparación conjunta
incluye dos documentos y un documento expandido con dos resultados. El orden,
los nombres, los tamaños, las fechas y los títulos pertenecen a los datos de
prueba; no se presentan como una comparación de píxeles con contenido idéntico.

## Superficies revisadas

| Superficie | Resultado |
| --- | --- |
| Tipografía | Se conserva la familia existente DM Sans con sus fallbacks. Título, nombres y metadatos mantienen la jerarquía de la aplicación. No se infiere una coincidencia tipográfica exacta con el raster. Los nombres largos permiten salto de línea. |
| Espacio y estructura | Papelera en la esquina superior derecha del documento y al final de cada resultado. Objetivos de 44 × 44 px. En móvil las acciones se distribuyen en varias líneas sin ocultar controles. No hubo desbordamiento horizontal a 375 px. |
| Color | Rojo semántico para eliminar; violeta para las acciones principales. Se preservan los fondos blancos y azulados de la aplicación existente. La referencia tiene una dominante cálida; se considera una diferencia aceptada para este cambio acotado, sin recolorear toda la interfaz. |
| Imágenes e iconos | Icono real de Heroicons v2.2.0, SVG oficial sin redibujar, con licencia MIT incluida. Se comprobó su carga y tamaño de 20 px. No se sustituyen el logo ni las ilustraciones existentes. |
| Texto | Cada botón tiene nombre accesible específico. El diálogo del documento muestra nombre y total de resultados; el del resultado aclara que el original y los demás se conservan. Cancelar, eliminar, progreso, error recuperable y lista vacía tienen mensajes propios. |

Los recortes ampliados permiten revisar los controles nuevos y su alineación;
no se aprueba la fidelidad únicamente a partir de la vista completa.

## Hallazgos e historial de correcciones

- **P2 corregido — foco después de borrar un resultado.** La primera
  implementación intentaba enfocarlo antes de rehabilitar los botones.
  Se trasladó el retorno del foco al final del desbloqueo. La regresión
  automatizada comprueba ese orden. En navegador real, después de confirmar,
  `document.activeElement.textContent` fue `Ver resultados` y el control estaba
  habilitado. Evidencia posterior: captura `nuevamente-borrado-foco-corregido.png`.
- **Corregido — total con un borrado parcial.** Si el índice de un resultado
  ya se eliminó pero falló el recibo final, ese resultado todavía aparece como
  pendiente. La confirmación del documento ahora lo cuenta. Las pruebas de
  fallos parciales cubren este estado.
- No quedan hallazgos P0/P1/P2 accionables en el alcance revisado.

## Interacciones y validación

- Cancelar y Escape cierran sin enviar DELETE; el diálogo enfoca Cancelar.
- Confirmar un resultado elimina solo ese resultado; el original sigue disponible.
- Eliminar el último resultado mantiene el documento y muestra la lista vacía.
- Eliminar un documento informa la cantidad actual y elimina sus resultados;
  otro documento permanece disponible. La ausencia se conserva al recargar.
- Doble clic no duplica solicitudes; un fallo conserva el elemento y permite
  reintentar. La versión confirmada evita borrar resultados añadidos desde otra
  pestaña sin revisar nuevamente la confirmación.
- Consola revisada: sin errores en los recorridos probados.
- Backend: 109 pruebas; Frontend/HTTP/proxy: 84; integración completa: 5.
  Total: **198 aprobadas**. No se usaron documentos reales de OCI ni cuota de IA.

No hay preguntas de diseño pendientes. Esta revisión no acredita un despliegue
en AWS ni una prueba de borrado contra el bucket real. Antes de escalar Backend
a varios procesos se necesita coordinación distribuida; el MVP fija un worker.

## Checklist de entrega

- [x] Papeleras en documentos y resultados.
- [x] Confirmación explícita y cancelación segura.
- [x] Borrado real por navegador, con referencias compartidas y recuperación parcial.
- [x] Escritorio y móvil revisados con evidencia.
- [x] Pruebas y documentación actualizadas.
- [x] Cambios sin stage, commit, push ni despliegue.

final result: passed

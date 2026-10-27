// El archivo se conserva al reintentar, pero se limpia al iniciar una nueva configuración.
document.addEventListener("DOMContentLoaded", () => {
  // Empezar siempre desde la esquina superior izquierda, evitando restaurar
  // una posición horizontal accidental al recargar la aplicación.
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  UI.render(AppState.current, AppState.data);
  const formulario = document.getElementById("form-configuracion");
  const inputDocumento = document.getElementById("documento");
  const nombreArchivo = document.getElementById("nombre-archivo");
  let documentoGuardado = null;
  if (typeof Historial !== 'undefined') Historial.iniciar();
  document.addEventListener('app:documento-guardado', evento => {
    AppState.reset();
    documentoGuardado = evento.detail;
    inputDocumento.required = false;
    nombreArchivo.textContent = `${documentoGuardado.nombre} · Guardado en tu historial`;
    nombreArchivo.classList.add('has-file');
    document.getElementById('documento-contexto').textContent = 'Usaremos el original guardado. Generar otro material puede consumir cuota de IA.';
  });
  inputDocumento.addEventListener('change', () => {
    documentoGuardado = null;
    inputDocumento.required = true;
    const contexto = document.getElementById('documento-contexto');
    if (contexto) contexto.textContent = 'Tu documento es la fuente para generar el material de estudio.';
  });

  formulario.addEventListener("submit", async evento => {
    evento.preventDefault();
    await enviarFormulario();
  });
  document.getElementById("boton-reintentar").addEventListener("click", enviarFormulario);
  document.getElementById("boton-volver").addEventListener("click", volverAConfiguracion);
  document.getElementById("boton-nuevo").addEventListener("click", volverAConfiguracion);

  function limpiarDocumento() {
    documentoGuardado = null;
    inputDocumento.required = true;
    inputDocumento.value = "";
    nombreArchivo.textContent = "Ningún archivo seleccionado";
    nombreArchivo.classList.remove("has-file");
    const contexto = document.getElementById('documento-contexto');
    if (contexto) contexto.textContent = 'Tu documento es la fuente para generar el material de estudio.';
  }

  function volverAConfiguracion() {
    limpiarDocumento();
    AppState.reset();
    // Evita conservar un desplazamiento horizontal accidental al volver al inicio.
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }

  // Garantiza que la etiqueta visible se sincronice cada vez que el estado
  // vuelve a IDLE, incluso si otra acción restablece el estado de la app.
  document.addEventListener("app:state-changed", evento => {
    if (evento.detail?.state === "IDLE") limpiarDocumento();
  });

  async function enviarFormulario() {
    if (AppState.current === "PROCESSING") return;
    if (!formulario.checkValidity()) {
      formulario.reportValidity();
      return;
    }
    const datos = new FormData(formulario);
    const documento = datos.get("documento_original");
    const configuracion = {
      perfil_destinatario: datos.get("perfil_destinatario"),
      formato_salida: datos.get("formato_salida"),
      nicho_sector: datos.get("nicho_sector"),
    };
    AppState.setState("PROCESSING", { documento, configuracion, resultado: null, error: null });
    try {
      if (typeof Historial !== 'undefined') await Api.inicializarHistorial();
      const onStage = stage => {
        document.dispatchEvent(new CustomEvent("app:processing-stage", { detail: { stage } }));
      };
      const resultado = documentoGuardado
        ? await Api.adaptarGuardado(documentoGuardado.id, configuracion, onStage)
        : await Api.generarContenido(documento, configuracion, onStage);
      // Deja que el navegador pinte la etapa de validación antes de mostrar el resultado.
      // No es un porcentaje de progreso: es una pausa breve para que el cambio de estado sea perceptible.
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      await new Promise(resolve => setTimeout(resolve, 900));
      AppState.setState("COMPLETED", { resultado });
    } catch (error) {
      AppState.setState("ERROR", { error: error.message || "No se pudo completar la adaptación." });
    }
  }
});

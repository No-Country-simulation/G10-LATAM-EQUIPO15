// El archivo se conserva al reintentar, pero se limpia al iniciar una nueva configuración.
document.addEventListener("DOMContentLoaded", () => {
  UI.render(AppState.current, AppState.data);
  const formulario = document.getElementById("form-configuracion");
  const inputDocumento = document.getElementById("documento");
  const nombreArchivo = document.getElementById("nombre-archivo");

  formulario.addEventListener("submit", async evento => {
    evento.preventDefault();
    await enviarFormulario();
  });
  document.getElementById("boton-reintentar").addEventListener("click", enviarFormulario);
  document.getElementById("boton-volver").addEventListener("click", volverAConfiguracion);
  document.getElementById("boton-nuevo").addEventListener("click", volverAConfiguracion);

  function volverAConfiguracion() {
    // Eliminar el archivo anterior del input real y de su etiqueta visible.
    inputDocumento.value = "";
    nombreArchivo.textContent = "Ningún archivo seleccionado";
    nombreArchivo.classList.remove("has-file");
    AppState.reset();
  }

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
      const resultado = await Api.generarContenido(documento, configuracion);
      AppState.setState("COMPLETED", { resultado });
    } catch (error) {
      AppState.setState("ERROR", { error: error.message || "No se pudo completar la adaptación." });
    }
  }
});

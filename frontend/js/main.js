// main.js
// Conecta los eventos del usuario (submit del formulario, botón "reintentar") 
// con el estado de la app y las llamadas a la API.

document.addEventListener("DOMContentLoaded", () => {
  // Pintado inicial: acá mostramos la pantalla de carga (estado IDLE)
  UI.render(AppState.current, AppState.data);

  const formulario = document.getElementById("form-configuracion");
  const botonReintentar = document.getElementById("boton-reintentar");
  const botonNuevo = document.getElementById("boton-nuevo");

  formulario.addEventListener("submit", async (e) => {
    e.preventDefault();
    await enviarFormulario();
  });

  botonReintentar.addEventListener("click", () => enviarFormulario());
  botonNuevo.addEventListener("click", () => AppState.reset());

  async function enviarFormulario() {
    const formData = new FormData(formulario);
    const configuracion = {
      documento_titulo: formData.get("documento_titulo") || "Documento sin título",
      perfil_destinatario: formData.get("perfil_destinatario"),
      formato_salida: formData.get("formato_salida"),
      nicho_sector: formData.get("nicho_sector") || "General",
      nivel_detalle: formData.get("nivel_detalle") || "Didactico",
    };

    AppState.setState("PROCESSING", { configuracion, error: null });

    try {
      const resultado = await Api.generarContenido(configuracion);
      AppState.setState("COMPLETED", { resultado });
    } catch (err) {
      AppState.setState("ERROR", { error: err.message });
    }
  }
});

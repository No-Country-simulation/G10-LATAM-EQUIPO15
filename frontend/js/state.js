// state.js
// Máquina de estados de la app: por dónde va el flujo en cada momento.
// Estados posibles (según se discutió con el equipo para FE-04):
//   IDLE        -> esperando que el usuario cargue un documento
//   SUBMITTED   -> el usuario envió el formulario, esperando respuesta inicial
//   PROCESSING  -> el backend está generando el contenido (acá vive el stepper de Semana 3)
//   COMPLETED   -> hay contenido adaptado para mostrar
//   ERROR       -> algo falló, hay que mostrar un mensaje al respecto

const AppState = {
  current: "IDLE",
  data: {
    documento: null,       // archivo cargado por el usuario
    configuracion: null,   // { perfil_destinatario, formato_salida, nicho_sector }
    resultado: null,       // JSON de respuesta del Backend real
    error: null,
  },

  // Cambia de estado y avisa a quien esté escuchando (ui.js)
  setState(nuevoEstado, payload = {}) {
    this.current = nuevoEstado;
    this.data = { ...this.data, ...payload };
    document.dispatchEvent(
      new CustomEvent("app:state-changed", { detail: { state: this.current, data: this.data } })
    );
  },

  reset() {
    this.setState("IDLE", { documento: null, configuracion: null, resultado: null, error: null });
  },
};

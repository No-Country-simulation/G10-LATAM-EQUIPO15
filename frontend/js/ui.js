// ui.js
// Se encarga de mostrar/ocultar secciones y pintar datos según el estado actual.
// No sabe nada de fetch ni de mocks: solo lee lo que hay en AppState.

const UI = {
  secciones: {
    IDLE: document.getElementById("seccion-carga"),
    SUBMITTED: document.getElementById("seccion-procesando"),
    PROCESSING: document.getElementById("seccion-procesando"),
    COMPLETED: document.getElementById("seccion-resultado"),
    ERROR: document.getElementById("seccion-error"),
  },

  render(state, data) {
    // Oculta todas las secciones y muestra solo la del estado actual
    Object.values(this.secciones).forEach((el) => el && el.classList.add("oculto"));
    const activa = this.secciones[state];
    if (activa) activa.classList.remove("oculto");

    if (state === "COMPLETED" && data.resultado) {
      this.pintarResultado(data.resultado);
    }
    if (state === "ERROR" && data.error) {
      document.getElementById("mensaje-error").textContent = data.error;
    }
  },

  pintarResultado(resultado) {
    const { metadatos, contenido_adaptado } = resultado;

    document.getElementById("resultado-titulo").textContent = contenido_adaptado.titulo;
    document.getElementById("resultado-intro").textContent = contenido_adaptado.introduccion_contextualizada;
    document.getElementById("resultado-tiempo").textContent =
      `Tiempo estimado de estudio: ${metadatos.tiempo_estimado_estudio_minutos} min`;
    document.getElementById("resultado-conceptos").textContent =
      `Conceptos clave: ${metadatos.conceptos_clave.join(", ")}`;

    // Render simple de flashcards (items frente/dorso) — placeholder de maquetación,
    // en FE-03 se decidirá el componente definitivo por formato.
    const contenedor = document.getElementById("resultado-items");
    contenedor.innerHTML = "";
    contenido_adaptado.items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "flashcard";
      card.innerHTML = `
        <p class="flashcard-frente"><strong>${item.frente}</strong></p>
        <p class="flashcard-dorso">${item.dorso}</p>
        <p class="flashcard-pista"><em>${item.pista_didactica}</em></p>
      `;
      contenedor.appendChild(card);
    });
  },
};

// Escucha los cambios de estado y vuelve a pintar la pantalla correspondiente
document.addEventListener("app:state-changed", (e) => {
  UI.render(e.detail.state, e.detail.data);
});

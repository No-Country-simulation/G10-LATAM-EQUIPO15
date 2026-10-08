// Los datos del documento/proveedor se muestran como texto, nunca como HTML.
const UI = {
  secciones: {
    IDLE: document.getElementById("seccion-carga"),
    SUBMITTED: document.getElementById("seccion-procesando"),
    PROCESSING: document.getElementById("seccion-procesando"),
    COMPLETED: document.getElementById("seccion-resultado"),
    ERROR: document.getElementById("seccion-error"),
  },
  render(state, data) {
    Object.values(this.secciones).forEach(elemento => elemento?.classList.add("oculto"));
    this.secciones[state]?.classList.remove("oculto");
    const ocupado = state === "PROCESSING";
    document.getElementById("boton-generar").disabled = ocupado;
    document.getElementById("boton-reintentar").disabled = ocupado;
    document.getElementById("form-configuracion").setAttribute("aria-busy", String(ocupado));
    if (state === "COMPLETED" && data.resultado) this.pintarResultado(data.resultado);
    if (state === "ERROR") document.getElementById("mensaje-error").textContent = data.error;
  },
  elemento(tag, texto, clase) {
    const elemento = document.createElement(tag);
    if (texto !== undefined && texto !== null) elemento.textContent = texto;
    if (clase) elemento.className = clase;
    return elemento;
  },
  pintarResultado(resultado) {
    const { metadatos, contenido_adaptado: contenido } = resultado;
    document.getElementById("resultado-titulo").textContent = contenido.titulo;
    document.getElementById("resultado-intro").textContent = contenido.introduccion_contextualizada;
    document.getElementById("resultado-tiempo").textContent =
      `Tiempo estimado de estudio: ${metadatos.tiempo_estimado_estudio_minutos} min`;
    document.getElementById("resultado-conceptos").textContent =
      `Conceptos clave: ${metadatos.conceptos_clave.join(", ")}`;
    const score = resultado.evaluacion_calidad?.anclaje_fuente_score;
    document.getElementById("resultado-calidad").textContent =
      typeof score === "number" ? `Anclaje a la fuente evaluado por IA: ${Math.round(score * 100)} %` : "";
    const contenedor = document.getElementById("resultado-items");
    contenedor.replaceChildren();
    if (metadatos.formato_generado === "Flashcards") {
      contenido.items.forEach(item => this.flashcard(contenedor, item));
    } else if (metadatos.formato_generado === "Quiz Interactivo") {
      contenido.items.forEach((item, indice) => this.pregunta(contenedor, item, indice));
    } else if (metadatos.formato_generado === "Resumen Ejecutivo") {
      this.resumen(contenedor, contenido.items);
    }
  },
  flashcard(contenedor, item) {
    const tarjeta = this.elemento("article", null, "flashcard");
    tarjeta.append(this.elemento("h3", item.frente, "flashcard-frente"));
    const respuesta = this.elemento("details");
    respuesta.append(this.elemento("summary", "Ver respuesta"));
    respuesta.append(this.elemento("p", item.dorso, "flashcard-dorso"));
    if (item.pista_didactica) respuesta.append(this.elemento("p", item.pista_didactica, "flashcard-pista"));
    tarjeta.append(respuesta);
    contenedor.append(tarjeta);
  },
  pregunta(contenedor, item, indice) {
    const pregunta = this.elemento("fieldset", null, "quiz-pregunta");
    pregunta.append(this.elemento("legend", `${indice + 1}. ${item.pregunta}`));
    const opciones = item.opciones.map((texto, opcion) => {
      const etiqueta = this.elemento("label", null, "quiz-opcion");
      const radio = this.elemento("input");
      radio.type = "radio";
      radio.name = `quiz-pregunta-${indice}`;
      radio.value = String(opcion);
      etiqueta.append(radio, this.elemento("span", texto));
      pregunta.append(etiqueta);
      return radio;
    });
    const comprobar = this.elemento("button", "Comprobar respuesta");
    comprobar.type = "button";
    const feedback = this.elemento("p", null, "quiz-feedback");
    feedback.setAttribute("aria-live", "polite");
    comprobar.addEventListener("click", () => {
      const seleccion = opciones.findIndex(opcion => opcion.checked);
      feedback.className = "quiz-feedback";
      if (seleccion === -1) {
        feedback.textContent = "Elegí una opción antes de comprobar.";
        return;
      }
      const correcta = seleccion === item.indice_correcto;
      feedback.classList.add(correcta ? "respuesta-correcta" : "respuesta-incorrecta");
      feedback.textContent = (correcta ? "Respuesta correcta." : `Respuesta incorrecta. La correcta es: ${item.opciones[item.indice_correcto]}.`)
        + `\n${item.justificacion_tecnica}`
        + (!correcta && item.explicacion_distractores ? `\n${item.explicacion_distractores}` : "");
    });
    pregunta.append(comprobar, feedback);
    contenedor.append(pregunta);
  },
  resumen(contenedor, item) {
    contenedor.append(this.elemento("h3", "Resumen"), this.elemento("p", item.tldr));
    this.lista(contenedor, "Puntos clave", item.puntos_clave);
    contenedor.append(this.elemento("h3", "Impacto en el negocio"), this.elemento("p", item.impacto_negocio));
    this.lista(contenedor, "Recomendaciones", item.recomendaciones);
  },
  lista(contenedor, titulo, valores) {
    if (!valores?.length) return;
    const lista = this.elemento("ul");
    valores.forEach(valor => lista.append(this.elemento("li", valor)));
    contenedor.append(this.elemento("h3", titulo), lista);
  },
};
document.addEventListener("app:state-changed", evento => UI.render(evento.detail.state, evento.detail.data));

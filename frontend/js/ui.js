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
    if (state === "PROCESSING") this.setProcessingStage("sending");
    document.getElementById("boton-generar").disabled = ocupado;
    document.getElementById("boton-reintentar").disabled = ocupado;
    document.getElementById("form-configuracion").setAttribute("aria-busy", String(ocupado));
    if (state === "COMPLETED" && data.resultado) this.pintarResultado(data.resultado);
    if (state === "ERROR") document.getElementById("mensaje-error").textContent = data.error;
  },
  setProcessingStage(stage) {
    const steps = [...document.querySelectorAll("[data-processing-step]")];
    const order = ["sending", "waiting", "validating"];
    const activeIndex = order.indexOf(stage);
    const titles = {
      sending: ["En curso", "Pendiente", "Pendiente"],
      waiting: ["Completado", "En curso", "Pendiente"],
      validating: ["Completado", "Completado", "En curso"],
    };
    steps.forEach((elemento, index) => {
      elemento.classList.remove("is-active", "is-done");
      const icono = elemento.querySelector(".processing-step-icon");
      const estado = elemento.querySelector(".processing-step-status");
      if (index < activeIndex) {
        elemento.classList.add("is-done");
        icono.textContent = "✓";
      } else if (index === activeIndex) {
        elemento.classList.add("is-active");
        icono.textContent = String(index + 1);
      } else {
        icono.textContent = String(index + 1);
      }
      estado.textContent = titles[stage]?.[index] || "Pendiente";
    });
    const titulo = document.getElementById("processing-title");
    const descripcion = document.getElementById("processing-description");
    const textos = {
      sending: ["Estamos enviando tu solicitud", "Estamos preparando el documento y tus preferencias para enviarlos de forma segura."],
      waiting: ["Estamos procesando tu documento", "El servidor está trabajando en la adaptación. Este paso puede tardar varios minutos."],
      validating: ["Estamos validando el material", "Recibimos una respuesta y estamos comprobando que tenga el formato solicitado."],
    };
    if (titulo && textos[stage]) titulo.textContent = textos[stage][0];
    if (descripcion && textos[stage]) descripcion.textContent = textos[stage][1];
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
    const resumenAnterior = document.querySelector(".result-actions .quiz-score");
    resumenAnterior?.remove();
    if (metadatos.formato_generado === "Flashcards") {
      contenido.items.forEach(item => this.flashcard(contenedor, item));
    } else if (metadatos.formato_generado === "Quiz Interactivo") {
      this.quiz(contenedor, contenido.items);
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
  quiz(contenedor, items) {
    const preguntas = items.map((item, indice) => this.pregunta(contenedor, item, indice));
    const acciones = this.elemento("div", null, "quiz-final-actions");
    const finalizar = this.elemento("button", "Finalizar quiz y ver resultado", "button-primary");
    finalizar.type = "button";
    const resumen = this.elemento("section", null, "quiz-score oculto");
    resumen.setAttribute("aria-live", "polite");

    // Diálogo de confirmación: permite revisar las preguntas pendientes o finalizar igualmente.
    const dialogo = this.elemento("dialog", null, "quiz-confirm-dialog");
    dialogo.setAttribute("aria-labelledby", "quiz-confirm-title");
    const contenidoDialogo = this.elemento("div", null, "quiz-confirm-content");
    const iconoAviso = this.elemento("span", "!", "quiz-confirm-icon");
    iconoAviso.setAttribute("aria-hidden", "true");
    const tituloDialogo = this.elemento("h3", "¿Finalizar el quiz?", "quiz-confirm-title");
    tituloDialogo.id = "quiz-confirm-title";
    const mensajeDialogo = this.elemento("p", "", "quiz-confirm-message");
    const accionesDialogo = this.elemento("div", null, "quiz-confirm-actions");
    const revisar = this.elemento("button", "Revisar preguntas", "button-secondary");
    revisar.type = "button";
    const finalizarDeTodosModos = this.elemento("button", "Finalizar de todos modos", "button-primary");
    finalizarDeTodosModos.type = "button";
    accionesDialogo.append(revisar, finalizarDeTodosModos);
    contenidoDialogo.append(iconoAviso, tituloDialogo, mensajeDialogo, accionesDialogo);
    dialogo.append(contenidoDialogo);
    contenedor.append(acciones, resumen, dialogo);

    const pendientes = () => preguntas.filter(p => p.seleccion() === -1);

    const mostrarResultado = () => {
      const respondidas = preguntas.filter(p => p.seleccion() !== -1).length;
      const correctas = preguntas.filter(p => p.seleccion() === p.correcta).length;
      const total = preguntas.length;
      const porcentaje = total ? Math.round((correctas / total) * 100) : 0;
      resumen.replaceChildren();
      resumen.append(
        this.elemento("span", "RESULTADO DEL QUIZ", "section-kicker"),
        this.elemento("h3", `${correctas} de ${total} respuestas correctas`, "quiz-score-title"),
        this.elemento("p", `Puntuación: ${porcentaje} %`, "quiz-score-percent")
      );
      if (respondidas < total) {
        resumen.append(this.elemento("p", `Respondiste ${respondidas} de ${total} preguntas. Las preguntas sin responder cuentan como incorrectas en la puntuación final.`, "quiz-score-note"));
      } else {
        resumen.append(this.elemento("p", "¡Terminaste todas las preguntas! Revisa las justificaciones para reforzar lo aprendido.", "quiz-score-note"));
      }
      const pista = this.elemento("div", null, "quiz-score-track");
      const relleno = this.elemento("span");
      relleno.style.width = `${porcentaje}%`;
      pista.append(relleno);
      resumen.append(pista);
      resumen.classList.remove("oculto");
      document.querySelector(".result-actions")?.prepend(resumen);
      finalizar.disabled = true;
      finalizar.textContent = "Quiz finalizado";
      resumen.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };

    const completar = () => {
      if (dialogo.open) dialogo.close();
      mostrarResultado();
    };

    finalizar.addEventListener("click", () => {
      const faltantes = pendientes();
      if (faltantes.length === 0) {
        completar();
        return;
      }
      mensajeDialogo.textContent = `Has respondido ${preguntas.length - faltantes.length} de ${preguntas.length} preguntas. ${faltantes.length === 1 ? "Te falta responder 1 pregunta." : `Te faltan responder ${faltantes.length} preguntas.`}`;
      revisar.dataset.firstPending = String(preguntas.indexOf(faltantes[0]));
      if (typeof dialogo.showModal === "function") {
        dialogo.showModal();
      } else {
        // Respaldo para navegadores sin soporte de <dialog>.
        if (window.confirm(`${mensajeDialogo.textContent} ¿Deseas finalizar de todos modos? Cancela para revisar las preguntas.`)) completar();
        else {
          faltantes[0].elemento.scrollIntoView({ behavior: "smooth", block: "center" });
          faltantes[0].elemento.querySelector('input[type="radio"]')?.focus({ preventScroll: true });
        }
      }
    });

    revisar.addEventListener("click", () => {
      const indice = Number(revisar.dataset.firstPending);
      const pendiente = preguntas[indice];
      dialogo.close();
      if (pendiente) {
        pendiente.elemento.scrollIntoView({ behavior: "smooth", block: "center" });
        pendiente.elemento.querySelector('input[type="radio"]')?.focus({ preventScroll: true });
      }
    });
    finalizarDeTodosModos.addEventListener("click", completar);
    dialogo.addEventListener("click", evento => {
      if (evento.target === dialogo) dialogo.close();
    });
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
    const seleccion = () => opciones.findIndex(opcion => opcion.checked);
    comprobar.addEventListener("click", () => {
      const elegida = seleccion();
      feedback.className = "quiz-feedback";
      if (elegida === -1) {
        feedback.textContent = "Elegí una opción antes de comprobar.";
        return;
      }
      const correcta = elegida === item.indice_correcto;
      feedback.classList.add(correcta ? "respuesta-correcta" : "respuesta-incorrecta");
      feedback.textContent = (correcta ? "Respuesta correcta." : `Respuesta incorrecta. La correcta es: ${item.opciones[item.indice_correcto]}.`)
        + `\n${item.justificacion_tecnica}`
        + (!correcta && item.explicacion_distractores ? `\n${item.explicacion_distractores}` : "");
    });
    pregunta.append(comprobar, feedback);
    contenedor.append(pregunta);
    return { seleccion, correcta: item.indice_correcto, elemento: pregunta };
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

document.addEventListener("app:processing-stage", evento => UI.setProcessingStage(evento.detail.stage));

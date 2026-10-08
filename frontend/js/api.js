// El navegador usa la API del mismo origen, reenviada por Nginx a Backend.
const Api = {
  async generarContenido(documento, configuracion) {
    if (!documento || documento.size === 0) {
      throw new Error("Seleccioná un documento con contenido.");
    }
    const datos = new FormData();
    datos.append("documento_original", documento, documento.name);
    for (const campo of ["perfil_destinatario", "formato_salida", "nicho_sector"]) {
      datos.append(campo, configuracion[campo]);
    }
    let respuesta;
    try {
      respuesta = await fetch("/api/v1/adaptar-contenido", {
        method: "POST",
        body: datos,
        // IA dispone de 480 s y Backend de 600 s en la configuración predeterminada.
        signal: AbortSignal.timeout(660000),
      });
    } catch (error) {
      if (error.name === "TimeoutError" || error.name === "AbortError") {
        throw new Error("Se agotó el tiempo de espera. Podés reintentar la adaptación.");
      }
      throw new Error("No se pudo conectar con el servidor. Revisá la conexión y reintentá.");
    }
    let resultado;
    try {
      resultado = await respuesta.json();
    } catch {
      if (respuesta.ok) throw new Error("El servidor devolvió una respuesta inválida.");
    }
    if (!respuesta.ok) {
      const mensaje = resultado?.detail?.mensaje;
      throw new Error(typeof mensaje === "string" && mensaje.trim()
        ? mensaje
        : `No se pudo completar la adaptación (HTTP ${respuesta.status}). Podés reintentar.`);
    }
    const metadatos = resultado?.metadatos;
    const contenido = resultado?.contenido_adaptado;
    if (!["exito", "success"].includes(resultado?.status)
      || metadatos?.perfil_aplicado !== configuracion.perfil_destinatario
      || metadatos?.formato_generado !== configuracion.formato_salida
      || metadatos?.nicho_contexto !== configuracion.nicho_sector
      || !Array.isArray(metadatos?.conceptos_clave)
      || typeof contenido?.titulo !== "string"
      || typeof contenido?.introduccion_contextualizada !== "string") {
      throw new Error("La respuesta del servidor no corresponde a la adaptación solicitada.");
    }
    const items = contenido.items;
    const formato = metadatos.formato_generado;
    let valido = false;
    if (formato === "Flashcards") {
      valido = Array.isArray(items) && items.length > 0
        && items.every(item => typeof item.frente === "string" && typeof item.dorso === "string");
    } else if (formato === "Quiz Interactivo") {
      valido = Array.isArray(items) && items.length > 0 && items.every(item =>
        typeof item.pregunta === "string" && Array.isArray(item.opciones)
        && item.opciones.length === 4 && item.opciones.every(opcion => typeof opcion === "string")
        && Number.isInteger(item.indice_correcto) && item.indice_correcto >= 0 && item.indice_correcto < 4
        && typeof item.justificacion_tecnica === "string");
    } else if (formato === "Resumen Ejecutivo") {
      valido = items && typeof items.tldr === "string" && typeof items.impacto_negocio === "string"
        && Array.isArray(items.puntos_clave) && Array.isArray(items.recomendaciones);
    }
    if (!valido) throw new Error("El servidor devolvió contenido incompatible con el formato solicitado.");
    return resultado;
  },
};

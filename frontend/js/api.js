// api.js
// Toda la comunicación con el backend vive acá.
// Usamos un mock local. Cuando Backend tenga el endpoint real,
// solo hay que cambiar el contenido de estas funciones (el resto del FE no se toca).

const Api = {
  // Simula el envío del documento + configuración, y la espera del procesamiento.
  // Cuando exista el endpoint real, esto será un fetch a algo como:
  //   POST /api/generar  { documento_titulo, documento_contenido, perfil_destinatario, formato_salida, nicho_sector, nivel_detalle }
  async generarContenido(configuracion) {
    // --- Simulación de latencia real del pipeline RAG + LLM ---
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // --- MOCK: se debe reemplazar por fetch real cuando Backend esté listo ---
    const respuesta = await fetch("mocks/respuesta-ejemplo.json").then((r) => r.json());

    if (respuesta.status !== "exito") {
      throw new Error(respuesta.mensaje_error || "Ocurrió un error al generar el contenido.");
    }

    return respuesta;

    /* Versión real (a modo de referencia para cuando esté el endpoint):
    const res = await fetch("/api/generar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(configuracion),
    });
    if (!res.ok) throw new Error("Error del servidor al generar el contenido.");
    return res.json();
    */
  },
};

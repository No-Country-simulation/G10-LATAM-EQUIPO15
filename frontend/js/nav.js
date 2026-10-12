// nav.js
// Maneja la navegación entre las "pantallas" del sidebar.
// Es independiente de AppState: AppState solo controla el flujo interno del generador.

const vistas = {
  inicio: document.getElementById("seccion-inicio"),
  generador: document.getElementById("vista-generador"),
  "mis-documentos": document.getElementById("seccion-mis-documentos"),
  historial: document.getElementById("seccion-historial"),
};

function mostrarVista(nombre) {
  Object.values(vistas).forEach(elemento => elemento?.classList.add("oculto"));
  vistas[nombre]?.classList.remove("oculto");

  document.querySelectorAll(".nav-item").forEach(link => {
    link.classList.toggle("activo", link.dataset.vista === nombre);
  });
}

document.querySelectorAll(".nav-item").forEach(link => {
  link.addEventListener("click", evento => {
    evento.preventDefault();
    mostrarVista(link.dataset.vista);
  });
});

document.getElementById("boton-ir-generador")?.addEventListener("click", () => mostrarVista("generador"));

mostrarVista("inicio");
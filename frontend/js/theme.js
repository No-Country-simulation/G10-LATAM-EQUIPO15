// theme.js
// Maneja el cambio entre modo claro y oscuro, y recuerda la preferencia del usuario.

const botonTema = document.getElementById("boton-tema");

function aplicarTema(tema) {
    document.documentElement.setAttribute("data-theme", tema);
    botonTema.textContent = tema === "oscuro" ? "Modo claro" : "Modo oscuro";
    localStorage.setItem("tema", tema);
}

// Al cargar la página: usamos la preferencia guardada, o "claro" por defecto.
const temaGuardado = localStorage.getItem("tema") || "claro";
aplicarTema(temaGuardado);

// Al hacer clic: alternamos entre los dos modos.
botonTema.addEventListener("click", () => {
    const temaActual = document.documentElement.getAttribute("data-theme");
    aplicarTema(temaActual === "oscuro" ? "claro" : "oscuro");
});

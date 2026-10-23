// Estado, API, historial y controlador originales con eventos DOM controlados.
const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');
const { respuesta } = require('./fixtures.cjs');

function interfaz(fetch, { confirmar = () => assert.fail('No debe pedir confirmación en este recorrido') } = {}) {
  const elementos = new Map();
  const handlers = new Map();
  function elemento(id) {
    if (!elementos.has(id)) {
      const clases = new Set();
      elementos.set(id, {
        listeners: {}, textContent: '', disabled: false, value: '', required: true,
        classList: { add: c => clases.add(c), remove: c => clases.delete(c),
          toggle: (c, activo) => activo ? clases.add(c) : clases.delete(c) },
        atributos: {},
        setAttribute(k, v) { this.atributos[k] = v; }, removeAttribute(k) { delete this.atributos[k]; }, scrollIntoView() {},
        focus() { if (!this.disabled) document.activeElement = this; },
        querySelectorAll() { return []; }, querySelector() { return null; }, closest() { return null; },
        remove() { this.removed = true; this.isConnected = false; }, isConnected: true,
        replaceChildren() {}, append() {}, checkValidity: () => true, reportValidity() {},
        addEventListener(tipo, callback) { this.listeners[tipo] = callback; },
      });
    }
    return elementos.get(id);
  }
  const document = {
    getElementById: elemento,
    addEventListener(tipo, callback) {
      if (!handlers.has(tipo)) handlers.set(tipo, []);
      handlers.get(tipo).push(callback);
    },
    dispatchEvent(evento) {
      for (const callback of handlers.get(evento.type) || []) callback(evento);
    },
  };
  class CustomEvent { constructor(type, { detail } = {}) { this.type = type; this.detail = detail; } }
  class FormData {
    constructor(form) {
      this.data = new Map(form ? Object.entries({ documento_original: { name: 'nuevo.md', size: 5 },
        perfil_destinatario: 'Junior', formato_salida: 'Flashcards', nicho_sector: 'General' }) : []);
    }
    append(key, value) { this.data.set(key, value); }
    get(key) { return this.data.get(key); }
  }
  const source = ['state.js', 'api.js', 'history.js', 'main.js']
    .map(name => readFileSync(resolve(__dirname, '../js', name), 'utf8')).join('\n');
  const runtime = runInNewContext(source + '\n({ AppState, Api, Historial });', {
    document, CustomEvent, FormData, fetch, AbortSignal,
    UI: { render() {}, elemento: () => elemento(Symbol()) },
    window: { scrollTo() {}, confirm: confirmar }, requestAnimationFrame: callback => callback(),
    setTimeout: callback => callback(),
  });
  return { ...runtime, elemento, document, iniciar: () => document.dispatchEvent(new CustomEvent('DOMContentLoaded')) };
}
const http = data => ({ ok: true, json: async () => data });
const tick = () => new Promise(resolve => setImmediate(resolve));
const doc = { id: 'doc' };
const adaptation = { id: 'adapt', perfil_destinatario: 'Junior', formato_salida: 'Flashcards', nicho_sector: 'General' };

test('una apertura lenta no reemplaza una nueva generación al cambiar de pantalla', async () => {
  let resolver;
  const gate = new Promise(resolve => { resolver = resolve; });
  const ui = interfaz(async ruta => ruta.includes('/adaptaciones/') ? gate
    : http(ruta.endsWith('/sesion') ? { habilitado:true } : { documentos:[], siguiente:null }));
  ui.iniciar();
  await tick();
  const operation = ui.Historial.abrir(doc, adaptation, ui.elemento('abrir'), ui.elemento('resultados'));
  ui.Historial.crear();
  ui.AppState.setState('PROCESSING', { resultado:null });
  resolver(http(respuesta()));
  await operation;
  assert.equal(ui.AppState.current, 'PROCESSING');
  assert.equal(ui.AppState.data.resultado, null);
  assert.equal(ui.elemento('abrir').disabled, false);
});

test('dos aperturas fuera de orden muestran solo la última elegida', async () => {
  const pendientes = [];
  const ui = interfaz(async ruta => ruta.includes('/adaptaciones/')
    ? new Promise(resolve => pendientes.push(resolve))
    : http(ruta.endsWith('/sesion') ? { habilitado:true } : { documentos:[], siguiente:null }));
  ui.iniciar();
  await tick();
  const first = ui.Historial.abrir(doc, adaptation, ui.elemento('primero'), ui.elemento('resultados'));
  const second = ui.Historial.abrir(doc, adaptation, ui.elemento('segundo'), ui.elemento('resultados'));
  const elegido = respuesta(); elegido.contenido_adaptado.titulo = 'Último elegido';
  pendientes[1](http(elegido)); await second;
  pendientes[0](http(respuesta())); await first;
  assert.equal(ui.AppState.data.resultado.contenido_adaptado.titulo, 'Último elegido');
});

test('si falló la primera conexión, enviar explícitamente prepara de nuevo antes del único POST', async () => {
  const calls = [];
  let sesiones = 0;
  const ui = interfaz(async (ruta, options) => {
    calls.push([ruta, options.method || 'GET']);
    if (ruta.endsWith('/sesion')) {
      if (++sesiones === 1) throw new Error('red interrumpida');
      return http({ habilitado:true });
    }
    return http(ruta.endsWith('/documentos') ? { documentos:[], siguiente:null } : respuesta());
  });
  ui.iniciar();
  await tick();
  await ui.elemento('form-configuracion').listeners.submit({ preventDefault() {} });
  assert.equal(ui.AppState.current, 'COMPLETED', ui.AppState.data.error);
  assert.deepEqual(calls.slice(0, 3), [
    ['/api/v1/historial/sesion', 'GET'], ['/api/v1/historial/sesion', 'GET'], ['/api/v1/adaptar-contenido', 'POST'],
  ]);
  assert.equal(calls.filter(([, method]) => method === 'POST').length, 1);
});

test('sin historial habilitado la generación normal sigue disponible', async () => {
  const ui = interfaz(async ruta => http(ruta.endsWith('/sesion') ? { habilitado:false }
    : ruta.endsWith('/documentos') ? { documentos:[], siguiente:null } : respuesta()));
  ui.iniciar();
  await tick();
  await ui.elemento('form-configuracion').listeners.submit({ preventDefault() {} });
  assert.equal(ui.AppState.current, 'COMPLETED');
});

const documentoBorrable = { id: 'a'.repeat(64), nombre: 'manual.pdf' };
const resumenBorrable = { nombre: 'manual.pdf', resultados: 23, version: 'b'.repeat(64) };
const resultadoBorrable = { id: 'c'.repeat(32), titulo: 'Fundamentos de IA' };

function borrado(fetch, options) {
  const ui = interfaz(fetch, options);
  ui.Historial.panel = ui.elemento('seccion-historial');
  ui.Historial.estado = ui.elemento('historial-estado');
  ui.Historial.documentos = [documentoBorrable];
  return ui;
}

test('cancelar la confirmación del documento no envía DELETE ni lo retira', async () => {
  const calls = [];
  const ui = borrado(async (url, options) => { calls.push([url, options.method]); return http(resumenBorrable); }, {
    confirmar: mensaje => { assert.match(mensaje, /23 resultados/); assert.match(mensaje, /manual.pdf/); return false; },
  });
  const card = ui.elemento('tarjeta');
  await ui.Historial.eliminarDocumento(documentoBorrable, card, ui.elemento('borrar'));
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], undefined);
  assert.equal(card.removed, undefined);
  assert.equal(ui.Historial.documentos.length, 1);
});

test('borrar documento usa el resumen completo, confirma y envía su versión', async () => {
  const calls = [];
  const ui = borrado(async (url, options) => {
    calls.push([url, options]);
    return http(options.method === 'DELETE' ? { eliminado: true } : resumenBorrable);
  }, { confirmar: () => true });
  await ui.Historial.eliminarDocumento(documentoBorrable, ui.elemento('tarjeta'), ui.elemento('borrar'));
  assert.equal(calls.length, 2);
  assert.equal(calls[1][1].method, 'DELETE');
  assert.equal(calls[1][1].headers['If-Match'], '"' + resumenBorrable.version + '"');
  assert.equal(calls[1][1].credentials, 'same-origin');
  assert.equal(ui.Historial.documentos.length, 0);
  assert.equal(ui.elemento('tarjeta').removed, true);
  assert.match(ui.elemento('historial-aviso').textContent, /eliminados/);
});

test('sin confirmación del resultado no hay ninguna petición de borrado', async () => {
  const ui = borrado(async () => assert.fail('No debe contactar el servidor'), { confirmar: () => false });
  await ui.Historial.eliminarResultado(documentoBorrable, resultadoBorrable, ui.elemento('fila'), ui.elemento('borrar'), ui.elemento('resultados'));
  assert.equal(ui.elemento('fila').removed, undefined);
  assert.equal(ui.elemento('borrar').disabled, false);
});

test('borrar resultado conserva el documento y describe qué permanece', async () => {
  const calls = [];
  const ui = borrado(async (url, options) => { calls.push([url, options.method]); return http({ eliminado: true }); }, {
    confirmar: mensaje => { assert.match(mensaje, /documento original y los demás resultados se conservarán/); return true; },
  });
  const fila = ui.elemento('fila');
  const borrar = ui.elemento('borrar');
  const ver = ui.elemento('ver-resultados');
  const tarjeta = ui.elemento('documento');
  const resultados = ui.elemento('resultados');
  ui.Historial.panel.querySelectorAll = selector => selector === 'button' ? [ver, borrar] : [];
  tarjeta.querySelector = () => ver;
  resultados.closest = () => tarjeta;
  fila.remove = () => { fila.removed = true; borrar.isConnected = false; };
  await ui.Historial.eliminarResultado(documentoBorrable, resultadoBorrable, fila, borrar, resultados);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], 'DELETE');
  assert.match(calls[0][0], /\/adaptaciones\//);
  assert.equal(ui.elemento('fila').removed, true);
  assert.equal(ui.Historial.documentos.length, 1);
  assert.equal(ui.document.activeElement, ver, 'El foco vuelve a Ver resultados después de habilitarlo');
});

test('error de borrado conserva el elemento y permite reintentar', async () => {
  let intentos = 0;
  const ui = borrado(async () => ++intentos === 1
    ? { ok: false, json: async () => ({ detail: { mensaje: 'Podés reintentar para continuar', codigo: 'HISTORIAL_NO_DISPONIBLE' } }) }
    : http({ eliminado: true }), { confirmar: () => true });
  const row = ui.elemento('fila');
  const button = ui.elemento('borrar');
  await ui.Historial.eliminarResultado(documentoBorrable, resultadoBorrable, row, button, ui.elemento('resultados'));
  assert.equal(row.removed, undefined);
  assert.equal(button.disabled, false);
  assert.match(ui.elemento('historial-aviso').textContent, /reintentar/);
  await ui.Historial.eliminarResultado(documentoBorrable, resultadoBorrable, row, button, ui.elemento('resultados'));
  assert.equal(row.removed, true);
});

test('dos clics mientras elimina producen un único DELETE', async () => {
  let terminar;
  let calls = 0;
  const pending = new Promise(resolve => { terminar = resolve; });
  const ui = borrado(async () => { calls++; return pending; }, { confirmar: () => true });
  const args = [documentoBorrable, resultadoBorrable, ui.elemento('fila'), ui.elemento('borrar'), ui.elemento('resultados')];
  const first = ui.Historial.eliminarResultado(...args);
  await tick();
  await ui.Historial.eliminarResultado(...args);
  assert.equal(calls, 1);
  assert.equal(ui.elemento('borrar').disabled, true);
  terminar(http({ eliminado: true }));
  await first;
});

test('diálogo nativo enfoca Cancelar y Escape no confirma', async () => {
  const ui = borrado(async () => assert.fail('No debe enviar solicitudes'));
  const dialog = ui.elemento('confirmar-eliminacion');
  dialog.showModal = () => { dialog.open = true; };
  const promise = ui.Historial.confirmar('¿Eliminar documento?', 'Se eliminarán 23 resultados.', 'Eliminar documento');
  assert.equal(dialog.open, true);
  assert.equal(ui.document.activeElement, ui.elemento('eliminacion-cancelar'));
  assert.equal(dialog.returnValue, 'cancelar');
  dialog.listeners.close(); // Escape cierra conservando returnValue=cancelar.
  assert.equal(await promise, false);
});

test('confirmación nativa solo acepta la acción explícita Eliminar', async () => {
  const ui = borrado(async () => assert.fail('No debe enviar solicitudes'));
  const dialog = ui.elemento('confirmar-eliminacion');
  dialog.showModal = () => {};
  const promise = ui.Historial.confirmar('¿Eliminar resultado?', 'Conservará el original.', 'Eliminar resultado');
  dialog.returnValue = 'eliminar';
  dialog.listeners.close();
  assert.equal(await promise, true);
});

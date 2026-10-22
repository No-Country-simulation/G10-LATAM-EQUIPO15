// Estado, API, historial y controlador originales con eventos DOM controlados.
const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');
const { respuesta } = require('./fixtures.cjs');

function interfaz(fetch) {
  const elementos = new Map();
  const handlers = new Map();
  function elemento(id) {
    if (!elementos.has(id)) {
      const clases = new Set();
      elementos.set(id, {
        listeners: {}, textContent: '', disabled: false, value: '', required: true,
        classList: { add: c => clases.add(c), remove: c => clases.delete(c),
          toggle: (c, activo) => activo ? clases.add(c) : clases.delete(c) },
        setAttribute() {}, removeAttribute() {}, scrollIntoView() {},
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
    window: { scrollTo() {} }, requestAnimationFrame: callback => callback(),
    setTimeout: callback => callback(),
  });
  return { ...runtime, elemento, iniciar: () => document.dispatchEvent(new CustomEvent('DOMContentLoaded')) };
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

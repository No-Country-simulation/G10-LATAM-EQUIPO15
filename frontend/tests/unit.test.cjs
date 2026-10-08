const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');

// Ejecuta los scripts originales sin agregar exports ni cambiar la aplicación.
function cargar(nombre, variable, entorno) {
  const fuente = readFileSync(resolve(__dirname, '..', 'js', nombre), 'utf8');
  return runInNewContext(`${fuente}\n${variable};`, entorno, { filename: nombre });
}

function crearEstado() {
  const eventos = [];
  const estado = cargar('state.js', 'AppState', {
    document: { dispatchEvent: (evento) => eventos.push(evento) },
    CustomEvent: class {
      constructor(type, options) { this.type = type; this.detail = options.detail; }
    },
  });
  return { estado, eventos };
}

test('el estado inicial espera un documento y no contiene datos previos', () => {
  const { estado, eventos } = crearEstado();
  assert.equal(estado.current, 'IDLE');
  for (const campo of ['documento', 'configuracion', 'resultado', 'error']) {
    assert.equal(estado.data[campo], null);
  }
  assert.equal(eventos.length, 0);
});

test('el procesamiento conserva el documento y notifica la configuración', () => {
  const { estado, eventos } = crearEstado();
  const documento = { name: 'fuente.txt' };
  const configuracion = { formato_salida: 'Flashcards' };
  estado.setState('SUBMITTED', { documento });
  estado.setState('PROCESSING', { configuracion });
  assert.equal(estado.data.documento, documento);
  assert.equal(estado.data.configuracion, configuracion);
  assert.equal(eventos.length, 2);
  assert.equal(eventos[1].type, 'app:state-changed');
  assert.equal(eventos[1].detail.state, 'PROCESSING');
  assert.equal(eventos[1].detail.data.configuracion, configuracion);
});

test('el estado completado publica el resultado recibido', () => {
  const { estado, eventos } = crearEstado();
  const resultado = { status: 'exito', contenido_adaptado: { items: [] } };
  estado.setState('COMPLETED', { resultado });
  assert.equal(estado.current, 'COMPLETED');
  assert.equal(eventos[0].detail.data.resultado, resultado);
});

test('reset limpia documento, configuración, resultado y error', () => {
  const { estado, eventos } = crearEstado();
  estado.setState('ERROR', {
    documento: { name: 'anterior.pdf' }, configuracion: {},
    resultado: { status: 'exito' }, error: 'Sin conexión',
  });
  estado.reset();
  assert.equal(estado.current, 'IDLE');
  for (const valor of Object.values(estado.data)) assert.equal(valor, null);
  assert.equal(eventos.at(-1).detail.state, 'IDLE');
});

function crearApi(fetch) {
  return cargar('api.js', 'Api', { fetch, setTimeout: (callback) => callback() });
}

test('el cliente entrega el JSON exitoso del mock local', async () => {
  const resultado = JSON.parse(readFileSync(resolve(__dirname, '..', 'mocks', 'respuesta-ejemplo.json'), 'utf8'));
  const llamadas = [];
  const api = crearApi(async (...args) => {
    llamadas.push(args);
    return { json: async () => resultado };
  });
  assert.equal(await api.generarContenido({ formato_salida: 'Flashcards' }), resultado);
  assert.deepEqual(llamadas, [['mocks/respuesta-ejemplo.json']]);
});

test('el cliente espera la latencia simulada antes de pedir el mock', async () => {
  let liberar;
  let demora;
  let solicitudes = 0;
  const api = cargar('api.js', 'Api', {
    setTimeout: (callback, ms) => { liberar = callback; demora = ms; },
    fetch: async () => { solicitudes += 1; return { json: async () => ({ status: 'exito' }) }; },
  });
  const pendiente = api.generarContenido({});
  assert.equal(demora, 1500);
  assert.equal(solicitudes, 0);
  liberar();
  await pendiente;
  assert.equal(solicitudes, 1);
});

test('el cliente comunica el mensaje de una respuesta fallida', async () => {
  const api = crearApi(async () => ({ json: async () => ({ status: 'error', mensaje_error: 'Contexto insuficiente' }) }));
  await assert.rejects(api.generarContenido({}), /Contexto insuficiente/);
});

test('el cliente usa un mensaje comprensible cuando el error no lo incluye', async () => {
  const api = crearApi(async () => ({ json: async () => ({ status: 'error' }) }));
  await assert.rejects(api.generarContenido({}), /Ocurrió un error al generar el contenido/);
});

test('el cliente propaga la falla de red para que el formulario muestre error', async () => {
  const api = crearApi(async () => { throw new Error('Sin conexión'); });
  await assert.rejects(api.generarContenido({}), /Sin conexión/);
});

test('el cliente rechaza una respuesta que no se puede interpretar como JSON', async () => {
  const api = crearApi(async () => ({ json: async () => { throw new SyntaxError('JSON inválido'); } }));
  await assert.rejects(api.generarContenido({}), /JSON inválido/);
});

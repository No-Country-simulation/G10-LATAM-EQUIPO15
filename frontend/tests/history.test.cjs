const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');
const { respuesta } = require('./fixtures.cjs');

function api(fetch, navigator) {
  return runInNewContext(readFileSync(resolve(__dirname, '../js/api.js'), 'utf8') + '\nApi;', { fetch, AbortSignal, FormData, navigator });
}
const config = { perfil_destinatario: 'Junior', formato_salida: 'Flashcards', nicho_sector: 'General' };
const http = datos => ({ ok: true, json: async () => datos });

test('las acciones simultáneas de primera visita comparten una sola inicialización', async () => {
  let llamadas = 0;
  let resolver;
  const gate = new Promise(resolve => { resolver = resolve; });
  const cliente = api(async ruta => { llamadas++; assert.equal(ruta, '/api/v1/historial/sesion'); await gate; return http({ habilitado: true }); });
  const first = cliente.inicializarHistorial();
  const second = cliente.inicializarHistorial();
  assert.equal(first, second);
  resolver();
  await Promise.all([first, second]);
  assert.equal(llamadas, 1);
});

test('readaptar un guardado envía solo configuración y espera la identidad', async () => {
  const calls = [];
  const stages = [];
  const cliente = api(async (ruta, options) => {
    calls.push(ruta);
    if (calls.length === 1) return http({ documentos: [], siguiente: null });
    assert.equal(options.method, 'POST');
    assert.equal(options.credentials, 'same-origin');
    assert.deepEqual(JSON.parse(options.body), config);
    assert.ok(!(options.body instanceof FormData));
    return http(respuesta());
  });
  const result = await cliente.adaptarGuardado('documento-guardado', config, stage => stages.push(stage));
  assert.equal(result.contenido_adaptado.titulo, 'JWT');
  assert.deepEqual(calls, ['/api/v1/historial/sesion', '/api/v1/documentos/documento-guardado/adaptaciones']);
  assert.deepEqual(stages, ['waiting', 'validating']);
});

test('abrir un resultado usa GET y conserva la validación de formato', async () => {
  const cliente = api(async (ruta, options) => {
    assert.equal(ruta, '/api/v1/documentos/doc/adaptaciones/adapt');
    assert.equal(options.method, undefined);
    return http(respuesta());
  });
  const result = await cliente.pedirHistorial('/documentos/doc/adaptaciones/adapt');
  assert.equal(cliente.validarResultado(result, config), result);
  assert.throws(() => cliente.validarResultado(result, { ...config, formato_salida: 'Quiz Interactivo' }), /no corresponde/);
});

test('un historial no disponible informa el error y permite reinicializar sin generación automática', async () => {
  let calls = 0;
  const cliente = api(async () => {
    calls++;
    return { ok: false, json: async () => ({ detail: { mensaje: 'Historial no disponible' } }) };
  });
  await assert.rejects(cliente.inicializarHistorial(), /Historial no disponible/);
  await assert.rejects(cliente.inicializarHistorial(), /Historial no disponible/);
  assert.equal(calls, 2);
});

test('dos pestañas preparan la cookie dentro del mismo Web Lock', async () => {
  let cola = Promise.resolve();
  const navigator = { locks: { request(nombre, operacion) {
    assert.equal(nombre, 'nuevamente-historial-inicio');
    const actual = cola.then(operacion);
    cola = actual.catch(() => {});
    return actual;
  } } };
  let cookie = false;
  let identidades = 0;
  const fetch = async () => {
    const nueva = !cookie;
    if (nueva) identidades++;
    await new Promise(resolve => setImmediate(resolve));
    cookie = true;
    return http({ habilitado: true });
  };
  await Promise.all([api(fetch, navigator).inicializarHistorial(), api(fetch, navigator).inicializarHistorial()]);
  assert.equal(identidades, 1, 'La segunda pestaña debe enviar la cookie ya preparada');
});

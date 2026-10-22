// Frontend Api real → Nginx → Backend → SDK OCI/bucket persistente de QA → IA HTTP simulada.
const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');
const base = process.env.FRONTEND_TEST_URL;
const fixture = process.env.IA_FIXTURE_URL;
const fuente = readFileSync(resolve(__dirname, '../js/api.js'), 'utf8');
const bytes = Buffer.from('# JWT\nLa firma permite verificar la integridad del token.');

function navegador() {
  let cookie = '';
  const request = async (path, options = {}) => {
    const response = await fetch(new URL(path, base), {
      ...options, headers: { ...options.headers, ...(cookie ? { Cookie: cookie } : {}) },
    });
    const value = response.headers.get('set-cookie');
    if (value) cookie = value.split(';')[0];
    return response;
  };
  const api = runInNewContext(fuente + '\nApi;', { fetch: request, AbortSignal, FormData });
  return { api, request };
}
async function llamadas() { return (await (await fetch(fixture + '/test/requests')).json()).length; }

for (const formato of ['Flashcards', 'Quiz Interactivo', 'Resumen Ejecutivo']) {
  test(`Historial de punta a punta: ${formato}, recarga, abrir y descargar sin IA`, async () => {
    const browser = navegador();
    const config = { perfil_destinatario: 'Junior', formato_salida: formato, nicho_sector: 'General' };
    assert.equal((await browser.api.inicializarHistorial()).habilitado, true);
    assert.deepEqual((await (await browser.request('/api/v1/documentos')).json()).documentos, []);
    const before = await llamadas();
    const result = await browser.api.generarContenido(new File([bytes], 'manual-historial.md'), config);
    assert.equal(result.historial.status, 'disponible');
    assert.equal(await llamadas(), before + 1);
    const doc = result.historial.documento_id;
    const path = `/api/v1/documentos/${doc}`;
    const documentos = await (await browser.request('/api/v1/documentos')).json();
    assert.equal(documentos.documentos.length, 1);
    assert.equal(documentos.documentos[0].nombre, 'manual-historial.md');
    const registros = await (await browser.request(path + '/adaptaciones')).json();
    const item = registros.adaptaciones[0];
    assert.equal(item.formato_salida, formato);
    const response = await browser.request(path + '/adaptaciones/' + item.id);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    const opened = browser.api.validarResultado(await response.json(), config);
    assert.deepEqual(opened.contenido_adaptado, result.contenido_adaptado);
    const download = await browser.request(path + '/adaptaciones/' + item.id + '/descarga');
    assert.match(download.headers.get('content-disposition'), /attachment/);
    assert.deepEqual(await download.json(), opened);
    const original = await browser.request(path + '/original');
    assert.deepEqual(Buffer.from(await original.arrayBuffer()), bytes);
    assert.equal(await llamadas(), before + 1, 'Abrir y descargar no deben generar otra vez');
    const next = await browser.api.adaptarGuardado(doc, { ...config, formato_salida: 'Resumen Ejecutivo' });
    assert.equal(next.metadatos.formato_generado, 'Resumen Ejecutivo');
    assert.equal(await llamadas(), before + 2);
    const observed = await (await fetch(fixture + '/test/requests')).json();
    assert.deepEqual(Buffer.from(observed.at(-1).bytes_base64, 'base64'), bytes);
    assert.equal((await (await browser.request(path + '/adaptaciones')).json()).adaptaciones.length, 2);
    const other = navegador();
    await other.api.inicializarHistorial();
    assert.equal((await (await other.request('/api/v1/documentos')).json()).documentos.length, 0);
    assert.equal((await other.request(path + '/original')).status, 404);
    assert.equal((await other.request(path + '/adaptaciones/' + item.id)).status, 404);
    assert.equal(await llamadas(), before + 2);
  });
}

test('Proxy conserva Origin y puerto: permite el propio y rechaza otro antes de IA', async () => {
  const browser = navegador();
  await browser.api.inicializarHistorial();
  const before = await llamadas();
  const own = await browser.request('/api/v1/documentos', { headers: { Origin: base } });
  assert.equal(own.status, 200);
  const other = await browser.request('/api/v1/adaptar-contenido', { method:'POST', headers:{ Origin:'https://otro.example' } });
  assert.equal(other.status, 403);
  assert.equal(await llamadas(), before);
});

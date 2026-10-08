const test = require('node:test');
const assert = require('node:assert/strict');
const base = process.env.FRONTEND_TEST_URL;
const fixture = process.env.IA_FIXTURE_URL;
const bytes = Buffer.from([37, 80, 68, 70, 0, 255, 10]);

async function post(formato, filename = 'manual.pdf', perfil = 'Senior') {
  const data = new FormData();
  data.append('documento_original', new Blob([bytes], { type: 'application/pdf' }), filename);
  data.append('perfil_destinatario', perfil);
  data.append('formato_salida', formato);
  data.append('nicho_sector', 'Salud');
  return fetch(`${base}/api/v1/adaptar-contenido`, { method: 'POST', body: data, signal: AbortSignal.timeout(10000) });
}

for (const formato of ['Flashcards', 'Quiz Interactivo', 'Resumen Ejecutivo']) {
  test(`Proxy → Backend → IA simulada conserva archivo y contrato de ${formato}`, async () => {
    const response = await post(formato);
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.deepEqual(Object.keys(payload).sort(), ['status', 'codigo_respuesta', 'metadatos', 'contenido_adaptado', 'evaluacion_calidad', 'almacenamiento_oci'].sort());
    assert.equal(payload.metadatos.formato_generado, formato);
    const requests = await (await fetch(`${fixture}/test/requests`)).json();
    const last = requests.at(-1);
    assert.equal(last.filename, 'manual.pdf');
    assert.deepEqual(Buffer.from(last.bytes_base64, 'base64'), bytes);
    assert.deepEqual(last.params, { perfil_destinatario: 'Senior', formato_salida: formato, nicho_sector: 'Salud' });
  });
}

test('Proxy conserva el rechazo de parámetros de Backend y no contacta IA', async () => {
  const before = await (await fetch(`${fixture}/test/requests`)).json();
  const response = await post('Flashcards', 'manual.pdf', 'Principiante');
  assert.equal(response.status, 422);
  assert.equal((await response.json()).detail.codigo, 'PARAMETROS_INVALIDOS');
  const after = await (await fetch(`${fixture}/test/requests`)).json();
  assert.equal(after.length, before.length);
});

for (const [filename, status, codigo] of [
  ['rechazado.txt', 422, 'CONTEXTO_INSUFICIENTE'], ['ocupado.txt', 503, 'IA_OCUPADA'],
]) {
  test(`Proxy conserva HTTP ${status} sin reemplazar el fallo con contenido`, async () => {
    const response = await post('Flashcards', filename);
    assert.equal(response.status, status);
    const payload = await response.json();
    assert.equal(payload.detail.codigo, codigo);
    assert.equal(payload.contenido_adaptado, undefined);
  });
}

test('Proxy aplica el límite de cuerpo antes de enviar un documento excesivo', async () => {
  const before = await (await fetch(`${fixture}/test/requests`)).json();
  const response = await fetch(`${base}/api/v1/adaptar-contenido`, {
    method: 'POST', body: new Uint8Array(12 * 1024 * 1024), signal: AbortSignal.timeout(10000),
  });
  assert.equal(response.status, 413);
  const after = await (await fetch(`${fixture}/test/requests`)).json();
  assert.equal(after.length, before.length);
});

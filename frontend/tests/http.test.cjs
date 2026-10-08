const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');

// Sólo se incluye en el comando de integración; las unitarias no requieren servidor.
const base = new URL(process.env.FRONTEND_TEST_URL || 'http://localhost:18003');
const tipos = {
  'index.html': 'text/html',
  'css/styles.css': 'text/css',
  'js/state.js': 'application/javascript',
  'js/api.js': 'application/javascript',
  'js/ui.js': 'application/javascript',
  'js/main.js': 'application/javascript',
  'mocks/respuesta-ejemplo.json': 'application/json',
};

async function pedir(ruta) {
  return fetch(new URL(ruta, base), { signal: AbortSignal.timeout(5000) });
}

for (const [archivo, tipo] of Object.entries(tipos)) {
  test(`HTTP sirve ${archivo} completo y con su tipo de contenido`, async () => {
    const respuesta = await pedir(archivo === 'index.html' ? '/' : `/${archivo}`);
    assert.equal(respuesta.status, 200);
    assert.equal(respuesta.headers.get('content-type').split(';')[0], tipo);
    const recibido = Buffer.from(await respuesta.arrayBuffer());
    const original = readFileSync(resolve(__dirname, '..', archivo));
    assert.deepEqual(recibido, original, `El contenedor debe servir la versión actual de ${archivo}`);
  });
}

test('HTTP /health identifica al Frontend y confirma disponibilidad', async () => {
  const respuesta = await pedir('/health');
  assert.equal(respuesta.status, 200);
  assert.match(respuesta.headers.get('content-type'), /^application\/json/);
  assert.deepEqual(await respuesta.json(), { status: 'healthy', service: 'frontend' });
});

test('HTTP entrega flashcards de ejemplo con contenido utilizable', async () => {
  const respuesta = await pedir('/mocks/respuesta-ejemplo.json');
  assert.equal(respuesta.status, 200);
  const resultado = await respuesta.json();
  assert.equal(resultado.status, 'exito');
  assert.equal(resultado.metadatos.formato_generado, 'Flashcards');
  assert.ok(resultado.contenido_adaptado.items.length > 0);
  for (const item of resultado.contenido_adaptado.items) {
    for (const campo of ['frente', 'dorso', 'pista_didactica']) {
      assert.equal(typeof item[campo], 'string');
      assert.ok(item[campo].trim().length > 0);
    }
  }
});

for (const ruta of ['/archivo-inexistente.js', '/README.md', '/.env', '/tests/unit.test.cjs', '/compose.yaml', '/nginx.conf']) {
  test(`HTTP no publica ${ruta}`, async () => {
    const respuesta = await pedir(ruta);
    assert.equal(respuesta.status, 404);
    await respuesta.arrayBuffer();
  });
}

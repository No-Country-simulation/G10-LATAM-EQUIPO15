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

test('HTTP expone solo los perfiles y formatos aceptados por Backend', async () => {
  const html = await (await pedir('/')).text();
  for (const [id, valores] of Object.entries({
    perfil_destinatario: ['Junior', 'Senior', 'Ejecutivo'],
    formato_salida: ['Flashcards', 'Quiz Interactivo', 'Resumen Ejecutivo'],
  })) {
    const select = html.match(new RegExp(`<select id="${id}"[^>]*>([\\s\\S]*?)</select>`))[1];
    assert.deepEqual([...select.matchAll(/<option value="([^"]+)"/g)].map(m => m[1]), valores);
  }
  assert.match(html, /name="documento_original"/);
});

for (const ruta of ['/archivo-inexistente.js', '/README.md', '/.env', '/tests/unit.test.cjs', '/compose.yaml', '/nginx.conf', '/mocks/respuesta-ejemplo.json']) {
  test(`HTTP no publica ${ruta}`, async () => {
    const respuesta = await pedir(ruta);
    assert.equal(respuesta.status, 404);
    await respuesta.arrayBuffer();
  });
}

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


const { respuesta } = require('./fixtures.cjs');
const configuracion = { perfil_destinatario: 'Junior', formato_salida: 'Flashcards', nicho_sector: 'General' };
const archivo = () => new File([Uint8Array.from([37, 80, 68, 70, 0, 255])], 'manual.pdf', { type: 'application/pdf' });
function crearApi(fetch) {
  return cargar('api.js', 'Api', { fetch, FormData, AbortSignal });
}
function respuestaHttp(data, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => data };
}

test('API envía multipart con bytes originales y solo los cuatro campos públicos', async () => {
  const documento = archivo();
  const resultado = respuesta();
  const llamadas = [];
  const api = crearApi(async (url, opciones) => {
    llamadas.push(url);
    assert.equal(opciones.method, 'POST');
    assert.equal(opciones.headers, undefined, 'El navegador debe generar el boundary multipart');
    assert.ok(opciones.signal instanceof AbortSignal);
    assert.deepEqual([...opciones.body.keys()], ['documento_original', 'perfil_destinatario', 'formato_salida', 'nicho_sector']);
    const enviado = opciones.body.get('documento_original');
    assert.equal(enviado.name, documento.name);
    assert.deepEqual(await enviado.arrayBuffer(), await documento.arrayBuffer());
    for (const [campo, valor] of Object.entries(configuracion)) assert.equal(opciones.body.get(campo), valor);
    return respuestaHttp(resultado);
  });
  assert.equal(await api.generarContenido(documento, { ...configuracion, nivel_detalle: 'Exhaustivo' }), resultado);
  assert.deepEqual(llamadas, ['/api/v1/adaptar-contenido']);
});

for (const formato of ['Flashcards', 'Quiz Interactivo', 'Resumen Ejecutivo']) {
  test(`API acepta la forma contractual de ${formato}`, async () => {
    const resultado = respuesta(formato);
    const api = crearApi(async () => respuestaHttp(resultado));
    assert.equal(await api.generarContenido(archivo(), { ...configuracion, formato_salida: formato }), resultado);
  });
}

for (const documento of [null, new File([], 'vacio.txt')]) {
  test(`API rechaza ${documento ? 'archivo vacío' : 'archivo ausente'} antes de contactar Backend`, async () => {
    const api = crearApi(async () => assert.fail('No debe enviarse un archivo vacío'));
    await assert.rejects(api.generarContenido(documento, configuracion), /Seleccioná un documento/);
  });
}

for (const [status, mensaje] of [[422, 'Contexto insuficiente'], [503, 'Proveedor no disponible'], [504, 'Tiempo agotado']]) {
  test(`API conserva el mensaje de HTTP ${status} y no reintenta automáticamente`, async () => {
    let llamadas = 0;
    const api = crearApi(async () => { llamadas++; return respuestaHttp({ detail: { codigo: 'ERROR', mensaje } }, status); });
    await assert.rejects(api.generarContenido(archivo(), configuracion), error => error.message === mensaje);
    assert.equal(llamadas, 1);
  });
}

test('API comunica un error del proxy sin JSON', async () => {
  const api = crearApi(async () => ({ ok: false, status: 502, json: async () => { throw new SyntaxError('HTML'); } }));
  await assert.rejects(api.generarContenido(archivo(), configuracion), /HTTP 502/);
});

test('API no interpreta un error de negocio con HTTP 200 como éxito', async () => {
  const api = crearApi(async () => respuestaHttp({ status: 'error' }));
  await assert.rejects(api.generarContenido(archivo(), configuracion), /no corresponde/);
});

test('API rechaza contenido de otro formato aunque el transporte tenga HTTP 200', async () => {
  const api = crearApi(async () => respuestaHttp(respuesta('Resumen Ejecutivo')));
  await assert.rejects(api.generarContenido(archivo(), configuracion), /no corresponde/);
});

test('API rechaza opciones de Quiz fuera de la estructura contractual', async () => {
  const resultado = respuesta('Quiz Interactivo');
  resultado.contenido_adaptado.items[0].opciones.pop();
  const api = crearApi(async () => respuestaHttp(resultado));
  await assert.rejects(api.generarContenido(archivo(), { ...configuracion, formato_salida: 'Quiz Interactivo' }), /incompatible/);
});

test('API comunica errores de conexión sin devolver contenido de ejemplo', async () => {
  const api = crearApi(async () => { throw new TypeError('fetch failed'); });
  await assert.rejects(api.generarContenido(archivo(), configuracion), /No se pudo conectar/);
});

test('API comunica el agotamiento del plazo de espera', async () => {
  const api = crearApi(async () => { const error = new Error('timeout'); error.name = 'TimeoutError'; throw error; });
  await assert.rejects(api.generarContenido(archivo(), configuracion), /Se agotó el tiempo/);
});

test('API rechaza una respuesta de éxito que no contiene JSON', async () => {
  const api = crearApi(async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('HTML'); } }));
  await assert.rejects(api.generarContenido(archivo(), configuracion), /respuesta inválida/);
});

// DOM mínimo sin parser HTML: permite comprobar que el texto generado no se ejecuta.
function crearUI() {
  class Elemento {
    constructor(tag) {
      this.tagName = tag; this.children = []; this.texto = ''; this.atributos = {}; this.listeners = {};
      this.classes = new Set();
      this.classList = { add: (...valores) => valores.forEach(v => this.classes.add(v)), remove: v => this.classes.delete(v) };
    }
    set className(valor) { this.classes = new Set(valor.split(' ').filter(Boolean)); }
    get className() { return [...this.classes].join(' '); }
    set textContent(valor) { this.texto = String(valor); this.children = []; }
    get textContent() { return this.texto + this.children.map(hijo => hijo.textContent).join(''); }
    set innerHTML(_valor) { assert.fail('El contenido generado no debe interpretarse como HTML'); }
    append(...hijos) { this.children.push(...hijos); }
    replaceChildren(...hijos) { this.children = hijos; this.texto = ''; }
    setAttribute(nombre, valor) { this.atributos[nombre] = valor; }
    addEventListener(nombre, funcion) { this.listeners[nombre] = funcion; }
  }
  const elementos = new Map();
  const document = {
    getElementById: id => { if (!elementos.has(id)) elementos.set(id, new Elemento('div')); return elementos.get(id); },
    createElement: tag => new Elemento(tag), addEventListener: () => {},
  };
  const ui = cargar('ui.js', 'UI', { document });
  const nodos = raiz => [raiz, ...raiz.children.flatMap(nodos)];
  return { ui, document, nodos };
}

test('UI muestra Flashcards sin interpretar HTML ni exigir pistas opcionales', () => {
  const { ui, document, nodos } = crearUI();
  const resultado = respuesta();
  const ataque = '<img src=x onerror="alert(1)">';
  resultado.contenido_adaptado.titulo = ataque;
  resultado.contenido_adaptado.items[0].dorso = ataque;
  ui.pintarResultado(resultado);
  assert.equal(document.getElementById('resultado-titulo').textContent, ataque);
  const tarjetas = nodos(document.getElementById('resultado-items'));
  assert.equal(tarjetas.filter(n => n.tagName === 'details').length, 1);
  assert.ok(tarjetas.some(n => n.tagName === 'p' && n.textContent === ataque));
  assert.ok(!tarjetas.some(n => n.tagName === 'img'));
});

test('UI permite responder el Quiz y muestra justificación para acierto y error', () => {
  const { ui, document, nodos } = crearUI();
  ui.pintarResultado(respuesta('Quiz Interactivo'));
  const elementos = nodos(document.getElementById('resultado-items'));
  const radios = elementos.filter(n => n.tagName === 'input');
  const boton = elementos.find(n => n.tagName === 'button');
  const feedback = elementos.find(n => n.className === 'quiz-feedback');
  boton.listeners.click();
  assert.match(feedback.textContent, /Elegí una opción/);
  radios[1].checked = true;
  boton.listeners.click();
  assert.match(feedback.textContent, /Respuesta incorrecta/);
  assert.match(feedback.textContent, /detectar cambios/);
  radios[1].checked = false;
  radios[0].checked = true;
  boton.listeners.click();
  assert.match(feedback.textContent, /Respuesta correcta/);
});

test('UI muestra el Resumen como objeto y limpia las tarjetas de una adaptación previa', () => {
  const { ui, document, nodos } = crearUI();
  ui.pintarResultado(respuesta());
  ui.pintarResultado(respuesta('Resumen Ejecutivo'));
  const contenedor = document.getElementById('resultado-items');
  assert.match(contenedor.textContent, /transportar claims firmados/);
  assert.match(contenedor.textContent, /Validar firmas/);
  assert.equal(nodos(contenedor).filter(n => n.tagName === 'article').length, 0);
});

test('UI deshabilita el envío durante el procesamiento y presenta errores como texto', () => {
  const { ui, document } = crearUI();
  ui.render('PROCESSING', {});
  assert.equal(document.getElementById('boton-generar').disabled, true);
  assert.equal(document.getElementById('form-configuracion').atributos['aria-busy'], 'true');
  ui.render('ERROR', { error: '<script>alert(1)</script>' });
  assert.equal(document.getElementById('boton-generar').disabled, false);
  assert.equal(document.getElementById('mensaje-error').textContent, '<script>alert(1)</script>');
});

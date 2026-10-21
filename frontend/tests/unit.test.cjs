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
function crearUI({ dialogoNativo = true, confirmar = () => assert.fail('No debe abrirse una confirmación nativa') } = {}) {
  const nodos = raiz => [raiz, ...raiz.children.flatMap(nodos)];
  class Elemento {
    constructor(tag) {
      this.tagName = tag; this.children = []; this.texto = ''; this.atributos = {}; this.listeners = {};
      this.classes = new Set(); this.style = {}; this.disabled = false; this.parentElement = null;
      this.dataset = {}; this.open = false;
      this.classList = {
        add: (...valores) => valores.forEach(v => this.classes.add(v)),
        remove: (...valores) => valores.forEach(v => this.classes.delete(v)),
        contains: valor => this.classes.has(valor),
      };
      if (tag === 'dialog' && dialogoNativo) {
        this.showModal = () => { this.open = true; };
        this.close = () => { this.open = false; };
      }
    }
    set className(valor) { this.classes = new Set(valor.split(' ').filter(Boolean)); }
    get className() { return [...this.classes].join(' '); }
    set textContent(valor) { this.replaceChildren(); this.texto = String(valor); }
    get textContent() { return this.texto + this.children.map(hijo => hijo.textContent).join(''); }
    set innerHTML(_valor) { assert.fail('El contenido generado no debe interpretarse como HTML'); }
    append(...hijos) { hijos.forEach(hijo => { hijo.remove(); hijo.parentElement = this; this.children.push(hijo); }); }
    prepend(...hijos) { hijos.forEach(hijo => hijo.remove()); hijos.forEach(hijo => { hijo.parentElement = this; }); this.children.unshift(...hijos); }
    remove() {
      if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(hijo => hijo !== this);
      this.parentElement = null;
    }
    replaceChildren(...hijos) { this.children.forEach(hijo => { hijo.parentElement = null; }); this.children = []; this.texto = ''; this.append(...hijos); }
    setAttribute(nombre, valor) { this.atributos[nombre] = valor; }
    removeAttribute(nombre) { delete this.atributos[nombre]; }
    addEventListener(nombre, funcion) { this.listeners[nombre] = funcion; }
    matches(selector) {
      if (selector.startsWith('.')) return this.classes.has(selector.slice(1));
      const atributo = selector.match(/^(\w+)?\[([\w-]+)(?:="([^"]*)")?\]$/);
      if (atributo) {
        const [, tag, nombre, valor] = atributo;
        return (!tag || this.tagName === tag) && (valor === undefined
          ? Object.hasOwn(this.atributos, nombre)
          : String(this[nombre] ?? this.atributos[nombre]) === valor);
      }
      return this.tagName === selector;
    }
    closest(selector) {
      return this.matches(selector) ? this : this.parentElement?.closest(selector) || null;
    }
    querySelectorAll(selector) {
      if (selector.includes(',')) return [...new Set(selector.split(',').flatMap(parte => this.querySelectorAll(parte.trim())))];
      const [primero, ...resto] = selector.split(' ');
      const encontrados = nodos(this).slice(1).filter(nodo => nodo.matches(primero));
      return resto.length ? encontrados.flatMap(nodo => nodo.querySelectorAll(resto.join(' '))) : encontrados;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    scrollIntoView() {}
    focus() { document.activeElement = this; }
  }
  const raiz = new Elemento('main');
  const elementos = new Map();
  const document = {
    getElementById: id => {
      if (!elementos.has(id)) { const elemento = new Elemento('div'); elementos.set(id, elemento); raiz.append(elemento); }
      return elementos.get(id);
    },
    createElement: tag => new Elemento(tag), addEventListener: () => {},
    querySelector: selector => raiz.querySelector(selector),
    querySelectorAll: selector => raiz.querySelectorAll(selector),
  };
  const acciones = new Elemento('div');
  acciones.className = 'result-actions';
  raiz.append(acciones);
  for (const etapa of ['sending', 'waiting', 'validating']) {
    const paso = new Elemento('div');
    paso.setAttribute('data-processing-step', etapa);
    for (const clase of ['processing-step-icon', 'processing-step-status']) {
      const detalle = new Elemento('span'); detalle.className = clase; paso.append(detalle);
    }
    document.getElementById('processing-steps').append(paso);
  }
  const ui = cargar('ui.js', 'UI', { document, window: { confirm: confirmar } });
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

for (const [storage, expected] of [
  [{ status_upload: 'pendiente' }, 'Almacenamiento en OCI pendiente.'],
  [{ status_upload: 'listo_para_subida' }, 'Almacenamiento en OCI pendiente.'],
  [{ status_upload: 'subido', documento_original_subido: true }, 'Documento original y contenido guardados en OCI.'],
  [{ status_upload: 'parcial', documento_original_subido: true }, 'Se guardó el documento original, pero no se confirmó la subida del contenido a OCI. El resultado está disponible.'],
  [{ status_upload: 'error' }, 'No se pudo confirmar el almacenamiento en OCI. El contenido generado está disponible.'],
  [{ status_upload: 'subido', documento_original_subido: false }, 'Almacenamiento en OCI pendiente.'],
]) {
  test(`UI distingue almacenamiento ${storage.status_upload} con original=${storage.documento_original_subido}`, () => {
    const { ui, document } = crearUI();
    const resultado = respuesta();
    resultado.almacenamiento_oci = { ...storage, mensaje: '<img src=x onerror="alert(1)">' };
    ui.pintarResultado(resultado);
    assert.equal(document.getElementById('resultado-almacenamiento').textContent, expected);
    resultado.almacenamiento_oci.status_upload = 'pendiente';
    ui.pintarResultado(resultado);
    assert.equal(document.getElementById('resultado-almacenamiento').textContent, 'Almacenamiento en OCI pendiente.');
  });
}

test('UI permite responder el Quiz y muestra justificación para acierto y error', () => {
  const { ui, document, nodos } = crearUI();
  ui.pintarResultado(respuesta('Quiz Interactivo'));
  const elementos = nodos(document.getElementById('resultado-items'));
  const radios = elementos.filter(n => n.tagName === 'input');
  const boton = elementos.find(n => n.tagName === 'button');
  const feedback = elementos.find(n => n.className === 'quiz-feedback');
  boton.listeners.click();
  assert.match(feedback.textContent, /(?:Elegí|Elige) una opción/);
  radios[1].checked = true;
  boton.listeners.click();
  assert.match(feedback.textContent, /Respuesta incorrecta/);
  assert.match(feedback.textContent, /detectar cambios/);
  assert.ok(feedback.textContent.includes('\nLa firma'), 'La explicación debe usar saltos de línea reales');
  assert.ok(!feedback.textContent.includes('\\n'), 'No debe mostrarse la secuencia literal de escape');
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

test('UI finaliza el Quiz con puntuación fija y bloquea todas las respuestas', () => {
  const { ui, document, nodos } = crearUI();
  const resultado = respuesta('Quiz Interactivo');
  resultado.contenido_adaptado.items.push({ ...resultado.contenido_adaptado.items[0] });
  ui.pintarResultado(resultado);
  const elementos = nodos(document.getElementById('resultado-items'));
  const radios = elementos.filter(n => n.tagName === 'input');
  radios[0].checked = true;
  const comprobar = elementos.find(n => n.tagName === 'button');
  comprobar.listeners.click();
  const finalizar = document.querySelector('.quiz-final-actions').children[0];
  finalizar.listeners.click();
  assert.equal(document.querySelector('dialog').open, true);
  assert.equal(document.querySelector('.quiz-score-percent'), null);
  document.querySelector('.quiz-confirm-actions').children[1].listeners.click();
  assert.equal(document.querySelector('dialog').open, false);
  assert.equal(document.querySelector('.quiz-score-percent').textContent, 'Puntuación: 50 %');
  assert.match(document.querySelector('.quiz-score-note').textContent, /Respondiste 1 de 2/);
  assert.ok(radios.every(radio => radio.disabled));
  assert.ok(finalizar.disabled);
  assert.ok(document.querySelectorAll('.quiz-pregunta button').every(boton => boton.disabled));
  comprobar.listeners.click();
  assert.ok(comprobar.disabled, 'Al finalizar también se bloquea la comprobación individual');
  assert.match(document.querySelector('.quiz-feedback').textContent, /Respuesta correcta/);
  assert.equal(document.querySelectorAll('.result-actions .quiz-score').length, 1);

  ui.pintarResultado(respuesta('Quiz Interactivo'));
  assert.equal(document.querySelectorAll('.result-actions .quiz-score').length, 0);
  assert.ok(nodos(document.getElementById('resultado-items')).filter(n => n.tagName === 'input').every(radio => !radio.disabled));
  const nuevo = nodos(document.getElementById('resultado-items'));
  nuevo.find(n => n.tagName === 'input').checked = true;
  nuevo.find(n => n.tagName === 'button').listeners.click();
  assert.match(document.querySelector('.quiz-feedback').textContent, /Respuesta correcta/,
    'El segundo quiz debe permitir comprobar respuestas después de finalizar el anterior');
  ui.pintarResultado(respuesta('Resumen Ejecutivo'));
  assert.equal(document.querySelectorAll('.quiz-score').length, 0);
});

test('UI permite revisar preguntas pendientes sin finalizar ni perder selecciones', () => {
  const { ui, document, nodos } = crearUI();
  const resultado = respuesta('Quiz Interactivo');
  resultado.contenido_adaptado.items.push({ ...resultado.contenido_adaptado.items[0] });
  ui.pintarResultado(resultado);
  const radios = nodos(document.getElementById('resultado-items')).filter(n => n.tagName === 'input');
  radios[0].checked = true;
  const finalizar = document.querySelector('.quiz-final-actions').children[0];
  finalizar.listeners.click();
  assert.equal(document.querySelector('dialog').open, true);
  assert.match(document.querySelector('.quiz-confirm-message').textContent, /Has respondido 1 de 2/);
  document.querySelector('.quiz-confirm-actions').children[0].listeners.click();
  assert.equal(document.querySelector('dialog').open, false);
  assert.equal(document.activeElement, radios[4]);
  assert.ok(radios[0].checked);
  assert.ok(radios.every(radio => !radio.disabled));
  assert.equal(finalizar.disabled, false);
  assert.equal(document.querySelector('.quiz-score-percent'), null);
});

test('UI finaliza directamente un quiz completo y mantiene el resultado fijo', () => {
  const { ui, document, nodos } = crearUI();
  ui.pintarResultado(respuesta('Quiz Interactivo'));
  nodos(document.getElementById('resultado-items')).find(n => n.tagName === 'input').checked = true;
  const finalizar = document.querySelector('.quiz-final-actions').children[0];
  finalizar.listeners.click();
  assert.equal(document.querySelector('dialog').open, false);
  assert.equal(document.querySelector('.quiz-score-percent').textContent, 'Puntuación: 100 %');
  finalizar.listeners.click();
  assert.equal(document.querySelectorAll('.quiz-score-percent').length, 1);
});

test('UI puede cerrar la confirmación y volver a abrirla sin bloquear el quiz', () => {
  const { ui, document } = crearUI();
  ui.pintarResultado(respuesta('Quiz Interactivo'));
  const finalizar = document.querySelector('.quiz-final-actions').children[0];
  const dialogo = document.querySelector('dialog');
  finalizar.listeners.click();
  dialogo.close(); // Escape usa el cierre nativo del navegador.
  finalizar.listeners.click();
  assert.equal(dialogo.open, true);
  dialogo.listeners.click({ target: dialogo });
  assert.equal(dialogo.open, false);
  assert.equal(finalizar.disabled, false);
  assert.equal(document.querySelector('.quiz-score-percent'), null);
});

test('UI confirma un quiz sin respuestas como cero puntos y bloquea los controles', () => {
  const { ui, document, nodos } = crearUI();
  ui.pintarResultado(respuesta('Quiz Interactivo'));
  document.querySelector('.quiz-final-actions').children[0].listeners.click();
  assert.match(document.querySelector('.quiz-confirm-message').textContent, /Te falta responder 1 pregunta/);
  document.querySelector('.quiz-confirm-actions').children[1].listeners.click();
  assert.equal(document.querySelector('.quiz-score-percent').textContent, 'Puntuación: 0 %');
  assert.ok(document.querySelectorAll('.quiz-pregunta').flatMap(nodos)
    .filter(n => ['input', 'button'].includes(n.tagName)).every(n => n.disabled));
});

for (const aceptar of [true, false]) {
  test(`UI conserva la confirmación sin soporte de dialog: aceptar=${aceptar}`, () => {
    let llamadas = 0;
    const { ui, document, nodos } = crearUI({ dialogoNativo: false, confirmar: mensaje => {
      llamadas++;
      assert.match(mensaje, /Te falta responder 1 pregunta/);
      return aceptar;
    } });
    ui.pintarResultado(respuesta('Quiz Interactivo'));
    const finalizar = document.querySelector('.quiz-final-actions').children[0];
    finalizar.listeners.click();
    assert.equal(llamadas, 1);
    assert.equal(finalizar.disabled, aceptar);
    if (aceptar) assert.equal(document.querySelector('.quiz-score-percent').textContent, 'Puntuación: 0 %');
    else {
      assert.equal(document.querySelector('.quiz-score-percent'), null);
      assert.equal(document.activeElement, nodos(document.getElementById('resultado-items')).find(n => n.tagName === 'input'));
    }
  });
}

test('UI refleja envío, espera y validación sin inventar un porcentaje de progreso', () => {
  const { ui, document } = crearUI();
  const pasos = document.querySelectorAll('[data-processing-step]');
  ui.render('PROCESSING', {});
  assert.ok(pasos[0].classes.has('is-active'));
  ui.setProcessingStage('waiting');
  assert.ok(pasos[0].classes.has('is-done'));
  assert.ok(!pasos[0].classes.has('is-active'));
  assert.ok(pasos[1].classes.has('is-active'));
  assert.equal(pasos[2].querySelector('.processing-step-status').textContent, 'Pendiente');
  ui.setProcessingStage('validating');
  assert.ok(pasos[1].classes.has('is-done'));
  assert.ok(!pasos[1].classes.has('is-active'));
  assert.ok(pasos[2].classes.has('is-active'));
  assert.match(document.getElementById('processing-title').textContent, /validando/);
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

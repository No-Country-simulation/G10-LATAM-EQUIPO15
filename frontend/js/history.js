// Los archivos viven en OCI; la identidad se conserva en una cookie HttpOnly del Backend.
const Historial = {
  documentos: [],
  cursor: null,
  version: 0,
  apertura: 0,
  iniciar() {
    this.panel = document.getElementById('seccion-historial');
    this.lista = document.getElementById('historial-documentos');
    this.estado = document.getElementById('historial-estado');
    this.mas = document.getElementById('historial-mas');
    document.getElementById('boton-historial').addEventListener('click', () => this.mostrar());
    document.getElementById('boton-crear').addEventListener('click', () => this.crear());
    document.getElementById('historial-actualizar').addEventListener('click', () => this.cargar());
    this.mas.addEventListener('click', () => this.cargar(true));
    this.preparacion = Api.inicializarHistorial().then(() => this.cargar()).catch(error => this.error(error));
    document.addEventListener('app:state-changed', evento => {
      if (evento.detail.state === 'COMPLETED' && evento.detail.data.resultado?.historial?.status === 'disponible') {
        // No vuelve a generar: solo actualiza las referencias persistidas.
        this.cargar();
      }
      const ocupado = evento.detail.state === 'PROCESSING';
      if (ocupado || evento.detail.state === 'IDLE') this.apertura++;
      document.getElementById('boton-historial').disabled = ocupado;
      document.getElementById('boton-crear').disabled = ocupado;
    });
  },
  crear() {
    this.apertura++;
    this.panel.classList.add('oculto');
    document.getElementById('workspace').classList.remove('oculto');
    document.getElementById('boton-crear').setAttribute('aria-current', 'page');
    document.getElementById('boton-historial').removeAttribute('aria-current');
  },
  mostrar() {
    if (AppState.current === 'PROCESSING') return;
    this.apertura++;
    document.getElementById('workspace').classList.add('oculto');
    this.panel.classList.remove('oculto');
    document.getElementById('boton-historial').setAttribute('aria-current', 'page');
    document.getElementById('boton-crear').removeAttribute('aria-current');
    this.cargar();
    this.panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  },
  error(error) {
    this.estado.textContent = error.message || 'No se pudo cargar el historial.';
    this.estado.setAttribute('role', 'alert');
  },
  async cargar(ampliar = false) {
    const version = ++this.version;
    this.estado.textContent = 'Cargando tus documentos…';
    this.estado.setAttribute('role', 'status');
    this.mas.disabled = true;
    try {
      await Api.inicializarHistorial();
      const query = ampliar && this.cursor ? '?cursor=' + encodeURIComponent(this.cursor) : '';
      const datos = await Api.pedirHistorial('/documentos' + query);
      if (version === this.version) this.pintarDocumentos(datos, ampliar);
    } catch (error) {
      if (version === this.version) this.error(error);
    } finally {
      if (version === this.version) this.mas.disabled = false;
    }
  },
  pintarDocumentos(datos, ampliar = false) {
    if (!Array.isArray(datos.documentos)) throw new Error('El listado de documentos no es válido.');
    this.documentos = ampliar ? [...this.documentos, ...datos.documentos] : datos.documentos;
    this.cursor = datos.siguiente || null;
    this.lista.replaceChildren();
    this.mas.classList.toggle('oculto', !this.cursor);
    this.estado.textContent = this.documentos.length
      ? `${this.documentos.length} documento(s) en este navegador.`
      : 'Todavía no guardaste documentos. Generá tu primer material para encontrarlo acá.';
    this.estado.setAttribute('role', 'status');
    this.documentos.forEach(doc => {
      const tarjeta = UI.elemento('article', null, 'history-card');
      tarjeta.append(UI.elemento('h3', doc.nombre));
      const fecha = new Date(doc.fecha).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
      tarjeta.append(UI.elemento('p', `${fecha} · ${Math.ceil(doc.tamano_bytes / 1024)} KB`, 'meta'));
      const acciones = UI.elemento('div', null, 'history-actions');
      const ver = UI.elemento('button', 'Ver resultados', 'button-secondary');
      ver.type = 'button';
      const usar = UI.elemento('button', 'Usar documento', 'button-primary');
      usar.type = 'button';
      usar.addEventListener('click', () => {
        this.crear();
        document.dispatchEvent(new CustomEvent('app:documento-guardado', { detail: doc }));
        document.getElementById('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      const original = UI.elemento('a', 'Descargar original', 'history-link');
      original.href = `/api/v1/documentos/${encodeURIComponent(doc.id)}/original`;
      const resultados = UI.elemento('div', null, 'history-results');
      resultados.setAttribute('aria-live', 'polite');
      ver.addEventListener('click', () => this.cargarResultados(doc, resultados, ver));
      acciones.append(ver, usar, original);
      tarjeta.append(acciones, resultados);
      this.lista.append(tarjeta);
    });
  },
  async cargarResultados(doc, contenedor, boton, cursor = null) {
    boton.disabled = true;
    if (!cursor) contenedor.replaceChildren(UI.elemento('p', 'Cargando resultados…', 'meta'));
    try {
      const query = cursor ? '?cursor=' + encodeURIComponent(cursor) : '';
      const datos = await Api.pedirHistorial(`/documentos/${encodeURIComponent(doc.id)}/adaptaciones` + query);
      if (!Array.isArray(datos.adaptaciones)) throw new Error('El listado de resultados no es válido.');
      if (!cursor) contenedor.replaceChildren();
      if (!datos.adaptaciones.length && !cursor) contenedor.append(UI.elemento('p', 'No hay resultados confirmados para este documento.', 'meta'));
      datos.adaptaciones.forEach(adaptacion => {
        const fila = UI.elemento('article', null, 'history-adaptation');
        fila.append(UI.elemento('h4', adaptacion.titulo));
        const fecha = new Date(adaptacion.fecha).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
        fila.append(UI.elemento('p', `${adaptacion.formato_salida} · ${adaptacion.perfil_destinatario} · ${adaptacion.nicho_sector} · ${fecha}`, 'meta'));
        const acciones = UI.elemento('div', null, 'history-actions');
        const abrir = UI.elemento('button', 'Abrir resultado', 'button-secondary');
        abrir.type = 'button';
        abrir.addEventListener('click', () => this.abrir(doc, adaptacion, abrir, contenedor));
        const descargar = UI.elemento('a', 'Descargar JSON', 'history-link');
        descargar.href = `/api/v1/documentos/${encodeURIComponent(doc.id)}/adaptaciones/${encodeURIComponent(adaptacion.id)}/descarga`;
        acciones.append(abrir, descargar);
        fila.append(acciones);
        contenedor.append(fila);
      });
      if (datos.siguiente) {
        const mas = UI.elemento('button', 'Más resultados', 'button-secondary');
        mas.type = 'button';
        mas.addEventListener('click', async () => {
          await this.cargarResultados(doc, contenedor, mas, datos.siguiente);
          mas.remove();
        });
        contenedor.append(mas);
      }
    } catch (error) {
      contenedor.replaceChildren(UI.elemento('p', error.message, 'history-error'));
    } finally { boton.disabled = false; }
  },
  async abrir(doc, adaptacion, boton, contenedor) {
    const apertura = ++this.apertura;
    boton.disabled = true;
    try {
      const configuracion = { perfil_destinatario: adaptacion.perfil_destinatario,
        formato_salida: adaptacion.formato_salida, nicho_sector: adaptacion.nicho_sector };
      const respuesta = await Api.pedirHistorial(`/documentos/${encodeURIComponent(doc.id)}/adaptaciones/${encodeURIComponent(adaptacion.id)}`);
      if (apertura !== this.apertura || AppState.current === 'PROCESSING') return;
      const resultado = Api.validarResultado(respuesta, configuracion);
      this.crear();
      AppState.setState('COMPLETED', { resultado, configuracion, documento: null });
      document.getElementById('seccion-resultado').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      if (apertura === this.apertura) contenedor.append(UI.elemento('p', error.message, 'history-error'));
    }
    finally { boton.disabled = false; }
  },
};

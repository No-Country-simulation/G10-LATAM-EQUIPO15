// Los archivos viven en OCI; la identidad se conserva en una cookie HttpOnly del Backend.
const Historial = {
  documentos: [],
  cursor: null,
  version: 0,
  apertura: 0,
  confirmando: false,
  iniciar() {
    this.panel = document.getElementById('seccion-historial');
    this.lista = document.getElementById('historial-documentos');
    this.estado = document.getElementById('historial-estado');
    this.mas = document.getElementById('historial-mas');
    document.getElementById('boton-historial').addEventListener('click', () => this.mostrar());
    document.getElementById('boton-crear').addEventListener('click', () => {
      this.crear();
      document.getElementById('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
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
      const cabecera = UI.elemento('div', null, 'history-card-heading');
      const eliminar = this.botonEliminar(`Eliminar documento ${doc.nombre}`, () => this.eliminarDocumento(doc, tarjeta, eliminar));
      cabecera.append(UI.elemento('h3', doc.nombre), eliminar);
      tarjeta.append(cabecera);
      const fecha = new Date(doc.fecha).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
      tarjeta.append(UI.elemento('p', `${fecha} · ${Math.ceil(doc.tamano_bytes / 1024)} KB`, 'meta'));
      const acciones = UI.elemento('div', null, 'history-actions');
      const ver = UI.elemento('button', 'Ver resultados', 'button-secondary');
      ver.type = 'button';
      const usar = UI.elemento('button', 'Usar documento', 'button-primary');
      usar.type = 'button';
      ver.disabled = usar.disabled = !!doc.eliminacion_pendiente;
      ver.historyUnavailable = usar.historyUnavailable = !!doc.eliminacion_pendiente;
      usar.addEventListener('click', () => {
        this.crear();
        document.dispatchEvent(new CustomEvent('app:documento-guardado', { detail: doc }));
        document.getElementById('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      const original = UI.elemento('a', 'Descargar original', 'history-link');
      original.href = `/api/v1/documentos/${encodeURIComponent(doc.id)}/original`;
      if (doc.eliminacion_pendiente) {
        original.removeAttribute('href');
        tarjeta.append(UI.elemento('p', 'Eliminación pendiente. Usá la papelera para completarla.', 'history-error'));
      }
      const resultados = UI.elemento('div', null, 'history-results');
      resultados.setAttribute('aria-live', 'polite');
      ver.addEventListener('click', () => this.cargarResultados(doc, resultados, ver));
      acciones.append(ver, usar, original);
      tarjeta.append(acciones, resultados);
      this.lista.append(tarjeta);
    });
  },
  async cargarResultados(doc, contenedor, boton, cursor = null) {
    const version = this.version;
    boton.disabled = true;
    if (!cursor) contenedor.replaceChildren(UI.elemento('p', 'Cargando resultados…', 'meta'));
    try {
      const query = cursor ? '?cursor=' + encodeURIComponent(cursor) : '';
      const datos = await Api.pedirHistorial(`/documentos/${encodeURIComponent(doc.id)}/adaptaciones` + query);
      if (version !== this.version || contenedor.isConnected === false) return;
      if (!Array.isArray(datos.adaptaciones)) throw new Error('El listado de resultados no es válido.');
      if (!cursor) contenedor.replaceChildren();
      if (!datos.adaptaciones.length && !cursor) contenedor.append(UI.elemento('p', 'No hay resultados confirmados para este documento.', 'meta'));
      datos.adaptaciones.forEach(adaptacion => {
        const fila = UI.elemento('article', null, 'history-adaptation');
        const copia = UI.elemento('div', null, 'history-adaptation-copy');
        copia.append(UI.elemento('h4', adaptacion.titulo));
        const fecha = new Date(adaptacion.fecha).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
        copia.append(UI.elemento('p', `${adaptacion.formato_salida} · ${adaptacion.perfil_destinatario} · ${adaptacion.nicho_sector} · ${fecha}`, 'meta'));
        const acciones = UI.elemento('div', null, 'history-actions');
        const abrir = UI.elemento('button', 'Abrir resultado', 'button-secondary');
        abrir.type = 'button';
        abrir.disabled = !!adaptacion.eliminacion_pendiente;
        abrir.historyUnavailable = !!adaptacion.eliminacion_pendiente;
        abrir.addEventListener('click', () => this.abrir(doc, adaptacion, abrir, contenedor));
        const descargar = UI.elemento('a', 'Descargar JSON', 'history-link');
        descargar.href = `/api/v1/documentos/${encodeURIComponent(doc.id)}/adaptaciones/${encodeURIComponent(adaptacion.id)}/descarga`;
        if (adaptacion.eliminacion_pendiente) {
          descargar.removeAttribute('href');
          copia.append(UI.elemento('p', 'Eliminación pendiente. Usá la papelera para completarla.', 'history-error'));
        }
        const eliminar = this.botonEliminar(`Eliminar resultado ${adaptacion.titulo}`, () => this.eliminarResultado(doc, adaptacion, fila, eliminar, contenedor));
        acciones.append(abrir, descargar, eliminar);
        fila.append(copia, acciones);
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
      if (version === this.version) contenedor.replaceChildren(UI.elemento('p', error.message, 'history-error'));
    } finally { if (!this.confirmando) boton.disabled = !!boton.historyUnavailable; }
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
    finally { if (!this.confirmando) boton.disabled = !!boton.historyUnavailable; }
  },
  botonEliminar(etiqueta, accion) {
    const boton = UI.elemento('button', null, 'history-delete');
    boton.type = 'button';
    boton.title = etiqueta;
    boton.setAttribute('aria-label', etiqueta);
    const icono = UI.elemento('img');
    icono.src = 'assets/icons/trash.svg';
    icono.alt = '';
    icono.width = icono.height = 20;
    boton.append(icono);
    boton.addEventListener('click', () => {
      if (!this.confirmando && AppState.current !== 'PROCESSING') return accion();
    });
    return boton;
  },
  avisar(mensaje, error = false) {
    const aviso = document.getElementById('historial-aviso');
    aviso.textContent = mensaje;
    aviso.classList.toggle('history-error', error);
    aviso.setAttribute('role', error ? 'alert' : 'status');
  },
  confirmar(titulo, mensaje, accion) {
    const dialogo = document.getElementById('confirmar-eliminacion');
    if (typeof dialogo?.showModal !== 'function') {
      return Promise.resolve(typeof window.confirm === 'function' && window.confirm(`${titulo}\n\n${mensaje}`) === true);
    }
    document.getElementById('eliminacion-titulo').textContent = titulo;
    document.getElementById('eliminacion-mensaje').textContent = mensaje;
    document.getElementById('eliminacion-confirmar').textContent = accion;
    dialogo.returnValue = 'cancelar';
    return new Promise(resolve => {
      dialogo.addEventListener('close', () => resolve(dialogo.returnValue === 'eliminar'), { once: true });
      dialogo.showModal();
      document.getElementById('eliminacion-cancelar').focus();
    });
  },
  bloquearBorrado(bloqueado, tarjeta) {
    this.version++;
    this.apertura++;
    tarjeta.classList.toggle('history-deleting', bloqueado);
    tarjeta.setAttribute('aria-busy', String(bloqueado));
    if (bloqueado) {
      const botones = new Set([...this.panel.querySelectorAll('button'), ...tarjeta.querySelectorAll('button'),
        ...['boton-crear', 'boton-historial', 'historial-actualizar', 'historial-mas'].map(id => document.getElementById(id))]);
      tarjeta.historyLock = {
        botones: [...botones].map(b => [b, b.disabled]),
        enlaces: [...this.panel.querySelectorAll('a')].map(a => [a, a.tabIndex]),
      };
      tarjeta.historyLock.botones.forEach(([b]) => { b.disabled = true; });
      tarjeta.historyLock.enlaces.forEach(([a]) => { a.setAttribute('aria-disabled', 'true'); a.tabIndex = -1; });
      this.panel.classList.add('history-busy');
    } else if (tarjeta.historyLock) {
      tarjeta.historyLock.botones.forEach(([b]) => { b.disabled = !!b.historyUnavailable || AppState.current === 'PROCESSING'; });
      tarjeta.historyLock.enlaces.forEach(([a, anterior]) => { a.removeAttribute('aria-disabled'); a.tabIndex = anterior; });
      delete tarjeta.historyLock;
      this.panel.classList.remove('history-busy');
    }
  },
  retirarDocumento(doc, tarjeta) {
    tarjeta.remove();
    this.documentos = this.documentos.filter(item => item.id !== doc.id);
    this.estado.textContent = this.documentos.length ? `${this.documentos.length} documento(s) en este navegador.`
      : this.cursor ? 'Hay más documentos disponibles. Pulsá Más documentos.' : 'Todavía no guardaste documentos. Generá tu primer material para encontrarlo acá.';
    const titulo = document.getElementById('historial-titulo');
    titulo.setAttribute('tabindex', '-1');
    titulo.focus();
  },
  async eliminarDocumento(doc, tarjeta, boton) {
    if (this.confirmando) return;
    this.confirmando = true;
    boton.disabled = true;
    this.avisar('Preparando la confirmación…');
    this.bloquearBorrado(true, tarjeta);
    try {
      const resumen = await Api.pedirHistorial(`/documentos/${encodeURIComponent(doc.id)}/eliminacion`);
      if (!Number.isInteger(resumen.resultados) || resumen.resultados < 0 || typeof resumen.version !== 'string') throw new Error('No se pudo preparar la confirmación. Reintentá.');
      const cantidad = resumen.resultados;
      const mensaje = `Se eliminará “${resumen.nombre}”${cantidad ? ` y ${cantidad === 1 ? 'su resultado guardado' : `sus ${cantidad} resultados guardados`}` : ''}, junto con sus archivos en OCI. Esta acción no se puede deshacer.`;
      if (!await this.confirmar('¿Eliminar documento?', mensaje, 'Eliminar documento')) { this.avisar('Eliminación cancelada.'); return; }
      this.avisar('Eliminando documento…');
      const resultado = await Api.pedirHistorial(`/documentos/${encodeURIComponent(doc.id)}`, {
        method: 'DELETE', headers: { 'If-Match': `"${resumen.version}"` },
      });
      if (resultado.eliminado !== true) throw new Error('No se pudo confirmar la eliminación. Reintentá.');
      this.retirarDocumento(doc, tarjeta);
      this.avisar('Documento y resultados eliminados.');
    } catch (error) {
      if (error.codigo === 'RECURSO_NO_ENCONTRADO') {
        this.retirarDocumento(doc, tarjeta);
        this.avisar('El documento ya no está disponible en este historial.');
      } else this.avisar(error.message, true);
    } finally {
      this.bloquearBorrado(false, tarjeta);
      this.confirmando = false;
      boton.disabled = false;
      if (boton.isConnected) boton.focus();
    }
  },
  async eliminarResultado(doc, adaptacion, fila, boton, contenedor) {
    if (this.confirmando) return;
    this.confirmando = true;
    boton.disabled = true;
    let borrando = false;
    try {
      if (!await this.confirmar('¿Eliminar resultado?', `Se eliminará “${adaptacion.titulo}”. El documento original y los demás resultados se conservarán. Esta acción no se puede deshacer.`, 'Eliminar resultado')) {
        this.avisar('Eliminación cancelada.'); return;
      }
      borrando = true;
      this.bloquearBorrado(true, fila);
      this.avisar('Eliminando resultado…');
      const resultado = await Api.pedirHistorial(`/documentos/${encodeURIComponent(doc.id)}/adaptaciones/${encodeURIComponent(adaptacion.id)}`, { method: 'DELETE' });
      if (resultado.eliminado !== true) throw new Error('No se pudo confirmar la eliminación. Reintentá.');
      fila.remove();
      if (!contenedor.querySelector('.history-adaptation') && !contenedor.querySelector('button')) {
        contenedor.append(UI.elemento('p', 'No hay resultados confirmados para este documento.', 'meta'));
      }
      this.avisar('Resultado eliminado. El documento se conserva.');
    } catch (error) {
      if (error.codigo === 'RECURSO_NO_ENCONTRADO') {
        fila.remove();
        this.avisar('El resultado ya no está disponible en este historial.');
      } else this.avisar(error.message, true);
    } finally {
      if (borrando) this.bloquearBorrado(false, fila);
      this.confirmando = false;
      boton.disabled = false;
      if (boton.isConnected) boton.focus();
      else contenedor.closest('.history-card')?.querySelector('.history-actions button')?.focus();
    }
  },
};

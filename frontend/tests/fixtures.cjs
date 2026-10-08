function respuesta(formato = 'Flashcards') {
  const items = {
    Flashcards: [{ frente: '¿Qué verifica una firma JWT?', dorso: 'La integridad del token.' }],
    'Quiz Interactivo': [{
      pregunta: '¿Qué verifica una firma JWT?', opciones: ['Integridad', 'Cifrado', 'Compresión', 'Anonimato'],
      indice_correcto: 0, justificacion_tecnica: 'La firma permite detectar cambios en el token.',
      explicacion_distractores: 'La firma no cifra ni comprime el contenido.',
    }],
    'Resumen Ejecutivo': {
      tldr: 'JWT permite transportar claims firmados.', puntos_clave: ['Verificar integridad'],
      impacto_negocio: 'Autenticación interoperable.', recomendaciones: ['Validar firmas'],
    },
  };
  return {
    status: 'exito', codigo_respuesta: 200,
    metadatos: { perfil_aplicado: 'Junior', formato_generado: formato, nicho_contexto: 'General',
      tiempo_estimado_estudio_minutos: 3, conceptos_clave: ['JWT'] },
    contenido_adaptado: { titulo: 'JWT', introduccion_contextualizada: 'Conceptos del documento.', items: items[formato] },
    evaluacion_calidad: { anclaje_fuente_score: 0.95, claridad_pedagogica: 'Alta', reintentos_realizados: 0 },
    almacenamiento_oci: { objeto_id: 'jwt.json', status_upload: 'pendiente' },
  };
}
module.exports = { respuesta };

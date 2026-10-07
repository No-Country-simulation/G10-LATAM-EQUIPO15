import json
import logging
import re
import asyncio
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AuditorAgent:
    """
    Agente de seguridad determinista (Pure Python).
    Ejecuta reglas heurísticas y Regex sobre el payload final
    en menos de 1 milisegundo, sin latencia de red ni consumo de tokens.
    """
    
    def __init__(self):
        # Patrones comunes de inyección XSS
        self.xss_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"onload=",
            r"onerror="
        ]
        
        # Patrones de evasión o Prompt Injections que se hayan colado a la salida
        self.injection_patterns = [
            r"ignore (all )?previous instructions",
            r"system prompt",
            r"you are now",
            r"forget everything"
        ]

    async def auditar_seguridad_async(self, payload_generado: Dict[str, Any]) -> Tuple[bool, list, list]:
        """
        Escanea el paquete generado usando heurísticas rápidas de Python.
        Retorna: (is_secure, vulnerabilidades, recomendaciones)
        """
        vulnerabilidades = []
        recomendaciones = []
        is_secure = True
        
        # 1. Serializar a string para escaneo global rápido (sin importar anidación)
        payload_str = json.dumps(payload_generado, ensure_ascii=False).lower()
        
        # 2. Escaneo XSS
        for pat in self.xss_patterns:
            if re.search(pat, payload_str):
                is_secure = False
                vulnerabilidades.append(f"Posible inyección XSS detectada (patrón: {pat})")
                recomendaciones.append("Sanitizar fuertemente en Backend y rechazar payload.")
                
        # 3. Escaneo de Fugas de Contexto (Prompt Injection leaks)
        for pat in self.injection_patterns:
            if re.search(pat, payload_str):
                is_secure = False
                vulnerabilidades.append(f"Fuga de contexto o Prompt Injection detectado (patrón: {pat})")
                recomendaciones.append("Revisar las barreras semánticas del Agente Crítico.")
                
        # 4. Verificación de Integridad Lógica
        contenido = payload_generado.get("contenido_adaptado", {})
        if not contenido or not contenido.get("items"):
            is_secure = False
            vulnerabilidades.append("Estructura rota: el paquete no contiene 'contenido_adaptado.items'.")
            recomendaciones.append("Activar mecanismo de reintento en el grafo.")
        else:
            # Heurística: Si generó un formato, el texto debería tener una longitud mínima
            texto_crudo = str(contenido)
            if len(texto_crudo) < 20:
                is_secure = False
                vulnerabilidades.append(f"Contenido sospechosamente corto ({len(texto_crudo)} caracteres).")
                recomendaciones.append("Evaluar falla prematura del modelo de lenguaje.")
                
        if is_secure:
            logger.info("Auditoría Python finalizada: 0 vulnerabilidades detectadas.")
            
        return is_secure, vulnerabilidades, recomendaciones

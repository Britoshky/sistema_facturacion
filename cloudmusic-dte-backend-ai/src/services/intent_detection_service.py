"""
Servicio para detección de intenciones de usuario
Responsable de analizar y clasificar las consultas del usuario
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class IntentDetectionService:
    """Servicio para detectar intenciones avanzadas del usuario"""
    
    def __init__(self):
        self.intent_patterns = {
            "information_request": [
                "información completa", "informacion completa", "datos empresa", "datos de la empresa",
                "resumen", "mi empresa", "información empresarial", "informacion empresarial",
                "datos completos", "toda la información", "toda la informacion"
            ],
            "product_query": [
                "producto más caro", "producto mas caro", "más caro", "mas caro", "expensive",
                "precio alto", "costoso", "productos", "precios", "catálogo", "catalogo"
            ],
            "dte_query": [
                "dte", "documento tributario", "factura electrónica", "factura electronica",
                "boleta electrónica", "boleta electronica", "documentos", "códigos sii", "codigos sii",
                "código 33", "codigo 33", "código 39", "codigo 39"
            ],
            "admin_query": [
                "administrador", "quien administra", "contacto", "email", "correo",
                "responsable", "encargado", "supervisor"
            ],
            "client_query": [
                "clientes", "usuarios", "cuántos clientes", "cuantos clientes",
                "base de datos", "registros"
            ],
            "general_help": [
                "ayuda", "help", "qué puedo hacer", "que puedo hacer",
                "funciones", "opciones", "comandos"
            ]
        }
    
    def detect_intent_advanced(self, message: str, conversation_history: List = None) -> str:
        """Detectar intención avanzada basada en el mensaje y historial"""
        try:
            message_lower = message.lower()
            
            # Calcular puntuaciones para cada intención
            intent_scores = {}
            
            for intent, patterns in self.intent_patterns.items():
                score = 0
                
                # Puntuación por coincidencia exacta de patrones
                for pattern in patterns:
                    if pattern in message_lower:
                        score += 10
                        
                # Puntuación por palabras clave individuales
                pattern_words = set()
                for pattern in patterns:
                    pattern_words.update(pattern.split())
                
                message_words = set(message_lower.split())
                common_words = pattern_words.intersection(message_words)
                score += len(common_words) * 2
                
                intent_scores[intent] = score
            
            # Considerar contexto del historial de conversación
            if conversation_history:
                intent_scores = self._adjust_scores_with_history(intent_scores, conversation_history)
            
            # Determinar la intención con mayor puntuación
            if intent_scores:
                best_intent = max(intent_scores.items(), key=lambda x: x[1])
                if best_intent[1] > 0:
                    return best_intent[0]
            
            # Intención por defecto
            return "general_help"
            
        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            return "general_help"
    
    def _adjust_scores_with_history(self, scores: Dict[str, int], history: List) -> Dict[str, int]:
        """Ajustar puntuaciones basándose en el historial de conversación"""
        try:
            if not history:
                return scores
            
            # Analizar mensajes recientes para contexto
            recent_messages = history[-3:] if len(history) >= 3 else history
            
            for message in recent_messages:
                message_content = ""
                
                # Extraer contenido del mensaje de forma segura
                if isinstance(message, dict):
                    message_content = message.get('content', '') or message.get('message', '')
                elif hasattr(message, 'content'):
                    message_content = str(message.content)
                else:
                    message_content = str(message)
                
                message_content = message_content.lower()
                
                # Incrementar puntuaciones para intenciones relacionadas con el historial
                for intent, patterns in self.intent_patterns.items():
                    for pattern in patterns:
                        if pattern in message_content:
                            scores[intent] = scores.get(intent, 0) + 2
            
            return scores
            
        except Exception as e:
            logger.error(f"Error adjusting scores with history: {e}")
            return scores
    
    def get_intent_confidence(self, message: str, intent: str) -> float:
        """Obtener nivel de confianza para una intención específica"""
        try:
            message_lower = message.lower()
            patterns = self.intent_patterns.get(intent, [])
            
            if not patterns:
                return 0.0
            
            matches = sum(1 for pattern in patterns if pattern in message_lower)
            confidence = min(matches / len(patterns), 1.0)
            
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating intent confidence: {e}")
            return 0.0
    
    def get_suggested_intents(self, message: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Obtener intenciones sugeridas con puntuaciones"""
        try:
            message_lower = message.lower()
            suggestions = []
            
            for intent, patterns in self.intent_patterns.items():
                score = 0
                matches = []
                
                for pattern in patterns:
                    if pattern in message_lower:
                        score += 10
                        matches.append(pattern)
                
                if score > 0:
                    suggestions.append({
                        'intent': intent,
                        'score': score,
                        'confidence': min(score / 100, 1.0),
                        'matches': matches
                    })
            
            # Ordenar por puntuación descendente
            suggestions.sort(key=lambda x: x['score'], reverse=True)
            
            return suggestions[:top_k]
            
        except Exception as e:
            logger.error(f"Error getting suggested intents: {e}")
            return []
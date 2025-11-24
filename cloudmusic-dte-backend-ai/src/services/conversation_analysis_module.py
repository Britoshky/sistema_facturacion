"""
CloudMusic DTE AI - Conversation Analysis Module
Módulo de análisis de conversación para mejora de interactividad

Funcionalidades:
- Análisis de patrones de conversación
- Detección de contexto e intención evolución
- Adaptación dinámica según historial
- Predicción de necesidades futuras
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import re

@dataclass
class ConversationPattern:
    """Patrón de conversación identificado"""
    pattern_type: str  # 'sequential', 'repetitive', 'exploratory', 'goal_oriented'
    frequency: int
    last_occurrence: datetime
    topics: List[str]
    user_satisfaction: float = 0.0
    effectiveness_score: float = 0.0

@dataclass
class UserBehaviorProfile:
    """Perfil de comportamiento conversacional del usuario"""
    user_id: str
    company_id: str
    total_interactions: int = 0
    preferred_communication_style: str = "direct"  # direct, conversational, technical
    topic_preferences: Dict[str, int] = field(default_factory=dict)
    question_patterns: List[str] = field(default_factory=list)
    response_preferences: Dict[str, float] = field(default_factory=dict)
    interaction_times: List[datetime] = field(default_factory=list)
    satisfaction_history: List[float] = field(default_factory=list)
    common_workflows: List[List[str]] = field(default_factory=list)

@dataclass
class ConversationContext:
    """Contexto actual de la conversación"""
    session_id: str
    conversation_flow: List[Dict[str, Any]] = field(default_factory=list)
    current_topic: str = ""
    topic_depth: int = 0
    user_goal: str = ""
    urgency_level: str = "normal"  # low, normal, high, urgent
    satisfaction_indicators: List[str] = field(default_factory=list)

class ConversationAnalysisModule:
    """Módulo de análisis de conversación para mejor interactividad"""
    
    def __init__(self, redis_service=None):
        self.logger = logging.getLogger(__name__)
        self.redis_service = redis_service
        self.behavior_profiles = {}
        self.conversation_contexts = {}
        self.cache_ttl = timedelta(hours=2)
        
        # Patrones de intención y tópicos
        self.topic_keywords = {
            'dte_documents': ['dte', 'documento', 'factura', 'boleta', 'emitir', 'generar'],
            'fiscal_tax': ['iva', 'impuesto', 'fiscal', 'tributario', 'sii', 'declaración'],
            'business_info': ['empresa', 'cliente', 'producto', 'ventas', 'ingresos'],
            'technical_support': ['error', 'problema', 'ayuda', 'configuración', 'soporte'],
            'reports': ['reporte', 'informe', 'resumen', 'estadística', 'análisis']
        }
        
        # Indicadores de satisfacción
        self.satisfaction_indicators = {
            'positive': ['gracias', 'perfecto', 'excelente', 'muy bien', 'correcto'],
            'negative': ['error', 'incorrecto', 'no funciona', 'problema', 'mal'],
            'neutral': ['ok', 'bien', 'entiendo', 'claro']
        }
        
        # Patrones de urgencia
        self.urgency_patterns = {
            'urgent': ['urgente', 'inmediato', 'ahora', 'rápido', 'ya'],
            'high': ['pronto', 'necesito', 'importante', 'hoy'],
            'normal': ['cuando', 'podrías', 'puedes'],
            'low': ['después', 'más tarde', 'cuando sea posible']
        }
        
        self.logger.info("🧠 ConversationAnalysisModule inicializado")
    
    async def analyze_conversation_turn(
        self,
        user_message: str,
        user_id: str,
        company_id: str,
        session_id: str,
        ai_response: str = "",
        additional_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analiza un turno de conversación completo
        
        Args:
            user_message: Mensaje del usuario
            user_id: ID del usuario
            company_id: ID de la empresa
            session_id: ID de la sesión
            ai_response: Respuesta de la IA (opcional)
            additional_context: Contexto adicional
            
        Returns:
            Análisis completo del turno de conversación
        """
        try:
            # Obtener o crear perfil de comportamiento
            behavior_profile = await self._get_behavior_profile(user_id, company_id)
            
            # Obtener o crear contexto de conversación
            conversation_context = await self._get_conversation_context(session_id)
            
            # Análisis del mensaje del usuario
            message_analysis = await self._analyze_user_message(user_message, behavior_profile)
            
            # Actualizar contexto de conversación
            await self._update_conversation_context(
                conversation_context, 
                user_message, 
                message_analysis,
                ai_response
            )
            
            # Detectar patrones de conversación
            patterns = await self._detect_conversation_patterns(behavior_profile, conversation_context)
            
            # Generar recomendaciones para respuesta
            response_recommendations = await self._generate_response_recommendations(
                message_analysis,
                behavior_profile,
                conversation_context,
                patterns
            )
            
            # Actualizar perfil de comportamiento
            await self._update_behavior_profile(
                behavior_profile,
                message_analysis,
                conversation_context
            )
            
            # Guardar cambios
            await self._save_analysis_data(behavior_profile, conversation_context)
            
            analysis_result = {
                'message_analysis': message_analysis,
                'conversation_patterns': [p.__dict__ for p in patterns],
                'response_recommendations': response_recommendations,
                'user_profile_updates': {
                    'total_interactions': behavior_profile.total_interactions,
                    'preferred_style': behavior_profile.preferred_communication_style,
                    'current_satisfaction': behavior_profile.satisfaction_history[-1] if behavior_profile.satisfaction_history else 0.5
                },
                'conversation_context': {
                    'current_topic': conversation_context.current_topic,
                    'topic_depth': conversation_context.topic_depth,
                    'urgency_level': conversation_context.urgency_level,
                    'user_goal': conversation_context.user_goal
                }
            }
            
            self.logger.info(f"🧠 Conversación analizada: {message_analysis['topic']} (urgencia: {conversation_context.urgency_level})")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando conversación: {e}")
            return {'error': 'Análisis no disponible'}
    
    async def _analyze_user_message(self, message: str, profile: UserBehaviorProfile) -> Dict[str, Any]:
        """Analiza el mensaje del usuario en profundidad"""
        
        try:
            message_lower = message.lower()
            
            # Detectar tópico principal
            detected_topic = await self._detect_message_topic(message_lower)
            
            # Analizar intención
            intention = await self._detect_user_intention(message_lower, profile)
            
            # Detectar urgencia
            urgency = await self._detect_urgency_level(message_lower)
            
            # Analizar sentimiento
            sentiment = await self._analyze_message_sentiment(message_lower)
            
            # Detectar complejidad de la consulta
            complexity = await self._detect_query_complexity(message)
            
            # Identificar palabras clave específicas
            keywords = await self._extract_keywords(message_lower)
            
            # Detectar si es seguimiento de conversación anterior
            is_followup = await self._detect_followup_question(message_lower, profile)
            
            return {
                'topic': detected_topic,
                'intention': intention,
                'urgency': urgency,
                'sentiment': sentiment,
                'complexity': complexity,
                'keywords': keywords,
                'is_followup': is_followup,
                'message_length': len(message),
                'question_type': await self._classify_question_type(message_lower)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando mensaje: {e}")
            return {'topic': 'general', 'intention': 'information', 'urgency': 'normal'}
    
    async def _detect_message_topic(self, message: str) -> str:
        """Detecta el tópico principal del mensaje"""
        
        topic_scores = {}
        
        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        else:
            return 'general'
    
    async def _detect_user_intention(self, message: str, profile: UserBehaviorProfile) -> str:
        """Detecta la intención del usuario"""
        
        # Patrones de intención
        intention_patterns = {
            'question': ['qué', 'cómo', 'cuál', 'cuándo', 'dónde', 'por qué', '¿'],
            'request': ['necesito', 'quiero', 'puedes', 'podrías', 'ayuda'],
            'problem': ['error', 'problema', 'no funciona', 'falla'],
            'information': ['información', 'saber', 'conocer', 'mostrar'],
            'action': ['generar', 'crear', 'emitir', 'hacer', 'ejecutar']
        }
        
        intention_scores = {}
        for intention, patterns in intention_patterns.items():
            score = sum(1 for pattern in patterns if pattern in message)
            if score > 0:
                intention_scores[intention] = score
        
        if intention_scores:
            return max(intention_scores, key=intention_scores.get)
        else:
            return 'information'
    
    async def _detect_urgency_level(self, message: str) -> str:
        """Detecta el nivel de urgencia del mensaje"""
        
        for level, patterns in self.urgency_patterns.items():
            if any(pattern in message for pattern in patterns):
                return level
        
        return 'normal'
    
    async def _analyze_message_sentiment(self, message: str) -> str:
        """Analiza el sentimiento del mensaje"""
        
        positive_score = sum(1 for word in self.satisfaction_indicators['positive'] if word in message)
        negative_score = sum(1 for word in self.satisfaction_indicators['negative'] if word in message)
        
        if negative_score > positive_score:
            return 'negative'
        elif positive_score > negative_score:
            return 'positive'
        else:
            return 'neutral'
    
    async def _detect_query_complexity(self, message: str) -> str:
        """Detecta la complejidad de la consulta"""
        
        # Indicadores de complejidad
        complex_indicators = ['integrar', 'configurar', 'analizar', 'comparar', 'optimizar']
        technical_terms = ['api', 'sdk', 'webhook', 'oauth', 'json', 'xml']
        
        complexity_score = 0
        complexity_score += len(message.split())  # Longitud
        complexity_score += sum(1 for word in complex_indicators if word.lower() in message.lower())
        complexity_score += sum(1 for word in technical_terms if word.lower() in message.lower()) * 2
        
        if complexity_score > 30:
            return 'high'
        elif complexity_score > 15:
            return 'medium'
        else:
            return 'low'
    
    async def _extract_keywords(self, message: str) -> List[str]:
        """Extrae palabras clave relevantes del mensaje"""
        
        # Palabras importantes relacionadas con DTE y tributario
        important_terms = [
            'factura', 'boleta', 'dte', 'iva', 'sii', 'cliente', 'producto',
            'emitir', 'generar', 'calcular', 'reporte', 'tributario', 'fiscal'
        ]
        
        keywords = []
        for term in important_terms:
            if term in message:
                keywords.append(term)
        
        # Extraer números (posibles códigos o montos)
        numbers = re.findall(r'\d+', message)
        keywords.extend([f"num_{num}" for num in numbers[:3]])  # Máximo 3 números
        
        return keywords
    
    async def _classify_question_type(self, message: str) -> str:
        """Clasifica el tipo de pregunta"""
        
        if any(word in message for word in ['¿tengo', '¿cuántos', '¿cuál es mi']):
            return 'status_inquiry'
        elif any(word in message for word in ['¿cómo', '¿de qué manera']):
            return 'how_to'
        elif any(word in message for word in ['¿qué', '¿cuál']):
            return 'what_is'
        elif any(word in message for word in ['¿cuándo', '¿hasta cuándo']):
            return 'when'
        else:
            return 'general'
    
    async def _detect_followup_question(self, message: str, profile: UserBehaviorProfile) -> bool:
        """Detecta si es una pregunta de seguimiento"""
        
        followup_indicators = ['también', 'además', 'y', 'otra consulta', 'otro', 'más']
        
        return any(indicator in message for indicator in followup_indicators)
    
    async def _get_behavior_profile(self, user_id: str, company_id: str) -> UserBehaviorProfile:
        """Obtiene o crea perfil de comportamiento"""
        
        cache_key = f"behavior_{user_id}_{company_id}"
        
        if cache_key in self.behavior_profiles:
            return self.behavior_profiles[cache_key]
        
        # Intentar cargar desde Redis si está disponible
        if self.redis_service:
            try:
                stored_profile = await self.redis_service.get(f"conversation:profile:{cache_key}")
                if stored_profile:
                    profile_data = json.loads(stored_profile)
                    profile = UserBehaviorProfile(**profile_data)
                    self.behavior_profiles[cache_key] = profile
                    return profile
            except Exception as e:
                self.logger.warning(f"⚠️ Error cargando perfil desde Redis: {e}")
        
        # Crear nuevo perfil
        new_profile = UserBehaviorProfile(
            user_id=user_id,
            company_id=company_id
        )
        self.behavior_profiles[cache_key] = new_profile
        
        return new_profile
    
    async def _get_conversation_context(self, session_id: str) -> ConversationContext:
        """Obtiene o crea contexto de conversación"""
        
        if session_id in self.conversation_contexts:
            return self.conversation_contexts[session_id]
        
        # Intentar cargar desde Redis si está disponible
        if self.redis_service:
            try:
                stored_context = await self.redis_service.get(f"conversation:context:{session_id}")
                if stored_context:
                    context_data = json.loads(stored_context)
                    context = ConversationContext(**context_data)
                    self.conversation_contexts[session_id] = context
                    return context
            except Exception as e:
                self.logger.warning(f"⚠️ Error cargando contexto desde Redis: {e}")
        
        # Crear nuevo contexto
        new_context = ConversationContext(session_id=session_id)
        self.conversation_contexts[session_id] = new_context
        
        return new_context
    
    async def _update_conversation_context(
        self,
        context: ConversationContext,
        user_message: str,
        message_analysis: Dict[str, Any],
        ai_response: str
    ):
        """Actualiza el contexto de conversación"""
        
        try:
            # Añadir turno de conversación
            turn = {
                'timestamp': datetime.now().isoformat(),
                'user_message': user_message,
                'ai_response': ai_response,
                'analysis': message_analysis
            }
            context.conversation_flow.append(turn)
            
            # Mantener solo los últimos 10 turnos
            context.conversation_flow = context.conversation_flow[-10:]
            
            # Actualizar tópico actual
            if message_analysis.get('topic') != 'general':
                if context.current_topic == message_analysis.get('topic'):
                    context.topic_depth += 1
                else:
                    context.current_topic = message_analysis.get('topic')
                    context.topic_depth = 1
            
            # Actualizar urgencia
            if message_analysis.get('urgency') != 'normal':
                context.urgency_level = message_analysis.get('urgency')
            
            # Inferir objetivo del usuario
            if message_analysis.get('intention') == 'action':
                context.user_goal = f"Realizar acción: {message_analysis.get('topic')}"
            elif message_analysis.get('intention') == 'problem':
                context.user_goal = f"Resolver problema: {message_analysis.get('topic')}"
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando contexto: {e}")
    
    async def _detect_conversation_patterns(
        self,
        profile: UserBehaviorProfile,
        context: ConversationContext
    ) -> List[ConversationPattern]:
        """Detecta patrones en la conversación"""
        
        patterns = []
        
        try:
            # Patrón secuencial (usuario sigue un flujo lógico)
            if len(context.conversation_flow) >= 3:
                topics = [turn['analysis'].get('topic', 'general') for turn in context.conversation_flow[-3:]]
                if len(set(topics)) == len(topics):  # Todos diferentes = secuencial
                    patterns.append(ConversationPattern(
                        pattern_type='sequential',
                        frequency=1,
                        last_occurrence=datetime.now(),
                        topics=topics,
                        effectiveness_score=0.8
                    ))
            
            # Patrón repetitivo (usuario repite preguntas similares)
            if len(context.conversation_flow) >= 2:
                last_two_topics = [turn['analysis'].get('topic') for turn in context.conversation_flow[-2:]]
                if last_two_topics[0] == last_two_topics[1]:
                    patterns.append(ConversationPattern(
                        pattern_type='repetitive',
                        frequency=context.topic_depth,
                        last_occurrence=datetime.now(),
                        topics=[last_two_topics[0]],
                        effectiveness_score=0.4  # Baja efectividad
                    ))
            
            # Patrón orientado a objetivos (usuarios con intención clara)
            if context.user_goal and context.urgency_level in ['high', 'urgent']:
                patterns.append(ConversationPattern(
                    pattern_type='goal_oriented',
                    frequency=1,
                    last_occurrence=datetime.now(),
                    topics=[context.current_topic],
                    effectiveness_score=0.9
                ))
            
        except Exception as e:
            self.logger.error(f"❌ Error detectando patrones: {e}")
        
        return patterns
    
    async def _generate_response_recommendations(
        self,
        message_analysis: Dict[str, Any],
        profile: UserBehaviorProfile,
        context: ConversationContext,
        patterns: List[ConversationPattern]
    ) -> Dict[str, Any]:
        """Genera recomendaciones para mejorar la respuesta"""
        
        try:
            recommendations = {
                'tone_adjustment': 'professional',
                'detail_level': 'standard',
                'response_structure': 'structured',
                'personalization_level': 'high',
                'followup_suggestions': [],
                'urgency_response': False
            }
            
            # Ajustar tono basado en historial
            if profile.preferred_communication_style == 'technical':
                recommendations['tone_adjustment'] = 'technical'
            elif profile.preferred_communication_style == 'conversational':
                recommendations['tone_adjustment'] = 'friendly'
            
            # Ajustar nivel de detalle por complejidad
            if message_analysis.get('complexity') == 'high':
                recommendations['detail_level'] = 'detailed'
            elif message_analysis.get('complexity') == 'low':
                recommendations['detail_level'] = 'simplified'
            
            # Respuesta a urgencia
            if context.urgency_level in ['high', 'urgent']:
                recommendations['urgency_response'] = True
                recommendations['response_structure'] = 'direct'
            
            # Detectar patrones repetitivos para mejorar respuesta
            repetitive_pattern = next((p for p in patterns if p.pattern_type == 'repetitive'), None)
            if repetitive_pattern:
                recommendations['followup_suggestions'].append("Ofrecer información más detallada")
                recommendations['followup_suggestions'].append("Sugerir alternativas o enfoques diferentes")
            
            # Recomendaciones basadas en tópico
            topic = message_analysis.get('topic', 'general')
            if topic == 'dte_documents':
                recommendations['followup_suggestions'].extend([
                    "Ofrecer ayuda con configuración",
                    "Mostrar ejemplos prácticos"
                ])
            elif topic == 'fiscal_tax':
                recommendations['followup_suggestions'].extend([
                    "Explicar implicaciones fiscales",
                    "Sugerir mejores prácticas"
                ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"❌ Error generando recomendaciones: {e}")
            return {'tone_adjustment': 'professional', 'detail_level': 'standard'}
    
    async def _update_behavior_profile(
        self,
        profile: UserBehaviorProfile,
        message_analysis: Dict[str, Any],
        context: ConversationContext
    ):
        """Actualiza el perfil de comportamiento del usuario"""
        
        try:
            profile.total_interactions += 1
            profile.interaction_times.append(datetime.now())
            
            # Mantener solo los últimos 50 tiempos de interacción
            profile.interaction_times = profile.interaction_times[-50:]
            
            # Actualizar preferencias de tópicos
            topic = message_analysis.get('topic', 'general')
            profile.topic_preferences[topic] = profile.topic_preferences.get(topic, 0) + 1
            
            # Actualizar patrones de preguntas
            question_type = message_analysis.get('question_type', 'general')
            if question_type not in profile.question_patterns:
                profile.question_patterns.append(question_type)
            
            # Mantener solo los últimos 20 patrones
            profile.question_patterns = profile.question_patterns[-20:]
            
            # Estimar satisfacción basada en sentimiento
            sentiment = message_analysis.get('sentiment', 'neutral')
            satisfaction_score = {'positive': 0.8, 'neutral': 0.6, 'negative': 0.3}.get(sentiment, 0.5)
            profile.satisfaction_history.append(satisfaction_score)
            
            # Mantener solo las últimas 30 mediciones
            profile.satisfaction_history = profile.satisfaction_history[-30:]
            
            # Adaptar estilo de comunicación
            avg_satisfaction = sum(profile.satisfaction_history) / len(profile.satisfaction_history)
            if avg_satisfaction < 0.5 and profile.preferred_communication_style != 'conversational':
                profile.preferred_communication_style = 'conversational'
            elif avg_satisfaction > 0.7 and len(profile.satisfaction_history) > 5:
                # Determinar estilo por complejidad de preguntas
                complex_questions = sum(1 for turn in context.conversation_flow 
                                      if turn['analysis'].get('complexity') == 'high')
                if complex_questions > len(context.conversation_flow) * 0.5:
                    profile.preferred_communication_style = 'technical'
                else:
                    profile.preferred_communication_style = 'direct'
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando perfil: {e}")
    
    async def _save_analysis_data(self, profile: UserBehaviorProfile, context: ConversationContext):
        """Guarda datos de análisis en Redis"""
        
        try:
            if not self.redis_service:
                return
            
            # Guardar perfil de comportamiento
            profile_key = f"conversation:profile:behavior_{profile.user_id}_{profile.company_id}"
            profile_data = {
                'user_id': profile.user_id,
                'company_id': profile.company_id,
                'total_interactions': profile.total_interactions,
                'preferred_communication_style': profile.preferred_communication_style,
                'topic_preferences': profile.topic_preferences,
                'question_patterns': profile.question_patterns,
                'satisfaction_history': profile.satisfaction_history[-10:],  # Solo últimas 10
                'interaction_times': [t.isoformat() for t in profile.interaction_times[-10:]]
            }
            
            await self.redis_service.set(
                profile_key,
                json.dumps(profile_data),
                expire=int(self.cache_ttl.total_seconds())
            )
            
            # Guardar contexto de conversación
            context_key = f"conversation:context:{context.session_id}"
            context_data = {
                'session_id': context.session_id,
                'conversation_flow': context.conversation_flow[-5:],  # Solo últimos 5 turnos
                'current_topic': context.current_topic,
                'topic_depth': context.topic_depth,
                'user_goal': context.user_goal,
                'urgency_level': context.urgency_level
            }
            
            await self.redis_service.set(
                context_key,
                json.dumps(context_data),
                expire=3600  # 1 hora
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando datos de análisis: {e}")
    
    async def get_conversation_insights(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Obtiene insights de conversación para el usuario"""
        
        try:
            profile = await self._get_behavior_profile(user_id, company_id)
            
            if profile.total_interactions == 0:
                return {'message': 'No hay suficientes datos de conversación'}
            
            # Calcular métricas
            avg_satisfaction = sum(profile.satisfaction_history) / len(profile.satisfaction_history) if profile.satisfaction_history else 0.5
            most_common_topic = max(profile.topic_preferences.items(), key=lambda x: x[1])[0] if profile.topic_preferences else 'general'
            
            insights = {
                'total_interactions': profile.total_interactions,
                'average_satisfaction': round(avg_satisfaction, 2),
                'preferred_communication_style': profile.preferred_communication_style,
                'most_common_topic': most_common_topic,
                'topic_distribution': profile.topic_preferences,
                'recent_satisfaction_trend': profile.satisfaction_history[-5:] if len(profile.satisfaction_history) >= 5 else profile.satisfaction_history,
                'interaction_frequency': len([t for t in profile.interaction_times if (datetime.now() - t).days <= 7])
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo insights: {e}")
            return {'error': 'No se pudieron obtener insights'}
    
    def clear_old_data(self, days_old: int = 30):
        """Limpia datos antiguos de conversación"""
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Limpiar datos de perfiles
            for profile in self.behavior_profiles.values():
                profile.interaction_times = [t for t in profile.interaction_times if t > cutoff_date]
                
            # Limpiar contextos de conversación antiguos
            sessions_to_remove = []
            for session_id, context in self.conversation_contexts.items():
                if context.conversation_flow:
                    last_interaction = datetime.fromisoformat(context.conversation_flow[-1]['timestamp'])
                    if last_interaction < cutoff_date:
                        sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.conversation_contexts[session_id]
            
            self.logger.info(f"🧹 Limpieza completada: {len(sessions_to_remove)} sesiones antiguas eliminadas")
            
        except Exception as e:
            self.logger.error(f"❌ Error en limpieza de datos: {e}")
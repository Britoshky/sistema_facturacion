"""
Módulo de Memoria a Largo Plazo - Sistema de memoria persistente para conversaciones cross-session
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

import redis.asyncio as aioredis
from loguru import logger


@dataclass
class UserMemoryProfile:
    """Perfil de memoria del usuario"""
    user_id: str
    company_id: str
    preferences: Dict[str, Any]
    frequent_queries: List[str]
    interaction_patterns: Dict[str, int]
    interaction_history: List[Dict[str, Any]]  # Historial detallado de interacciones
    last_active: datetime
    total_sessions: int
    favorite_topics: List[str]
    response_satisfaction_avg: float
    learned_context: Dict[str, Any]


@dataclass
class ConversationMemory:
    """Memoria de conversación específica"""
    session_id: str
    user_id: str
    company_id: str
    start_time: datetime
    end_time: Optional[datetime]
    topics_discussed: List[str]
    questions_asked: List[str]
    satisfaction_score: Optional[float]
    key_insights: List[str]
    follow_up_needed: bool


class LongTermMemoryService:
    """Servicio de memoria a largo plazo para el sistema IA"""
    
    def __init__(self, redis_url: str = None):
        # Usar configuración del .env si está disponible
        import os
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.memory_retention_days = 90
        self.max_memories_per_user = 1000
        
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await asyncio.wait_for(self.redis_client.ping(), timeout=3.0)
            logger.info(f"🧠 LongTermMemoryService conectado a Redis: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ LongTermMemoryService sin Redis - modo local: {str(e)[:100]}...")
            self.redis_client = None
            
    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def get_user_memory_profile(self, user_id: str, company_id: str) -> UserMemoryProfile:
        """Obtener perfil de memoria del usuario"""
        try:
            memory_key = f"memory:profile:{user_id}:{company_id}"
            memory_data = await self.redis_client.hgetall(memory_key)
            
            if memory_data:
                # Deserializar datos complejos
                preferences = json.loads(memory_data.get('preferences', '{}'))
                frequent_queries = json.loads(memory_data.get('frequent_queries', '[]'))
                interaction_patterns = json.loads(memory_data.get('interaction_patterns', '{}'))
                favorite_topics = json.loads(memory_data.get('favorite_topics', '[]'))
                learned_context = json.loads(memory_data.get('learned_context', '{}'))
                
                return UserMemoryProfile(
                    user_id=user_id,
                    company_id=company_id,
                    preferences=preferences,
                    frequent_queries=frequent_queries,
                    interaction_patterns=interaction_patterns,
                    interaction_history=json.loads(memory_data.get('interaction_history', '[]')),
                    last_active=datetime.fromisoformat(memory_data.get('last_active', datetime.now().isoformat())),
                    total_sessions=int(memory_data.get('total_sessions', 0)),
                    favorite_topics=favorite_topics,
                    response_satisfaction_avg=float(memory_data.get('response_satisfaction_avg', 0.0)),
                    learned_context=learned_context
                )
            else:
                # Crear nuevo perfil
                return UserMemoryProfile(
                    user_id=user_id,
                    company_id=company_id,
                    preferences={},
                    frequent_queries=[],
                    interaction_patterns={},
                    interaction_history=[],
                    last_active=datetime.now(),
                    total_sessions=0,
                    favorite_topics=[],
                    response_satisfaction_avg=0.0,
                    learned_context={}
                )
        except Exception as e:
            logger.error(f"❌ Error obteniendo perfil de memoria: {e}")
            return UserMemoryProfile(
                user_id=user_id, company_id=company_id, preferences={}, 
                frequent_queries=[], interaction_patterns={}, last_active=datetime.now(),
                total_sessions=0, favorite_topics=[], response_satisfaction_avg=0.0, learned_context={}
            )
            
    async def update_user_memory_profile(self, profile: UserMemoryProfile):
        """Actualizar perfil de memoria del usuario"""
        try:
            # Solo actualizar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - perfil de memoria no persistido")
                return
                
            memory_key = f"memory:profile:{profile.user_id}:{profile.company_id}"
            
            # Serializar datos complejos
            memory_data = {
                'user_id': profile.user_id,
                'company_id': profile.company_id,
                'preferences': json.dumps(profile.preferences),
                'frequent_queries': json.dumps(profile.frequent_queries),
                'interaction_patterns': json.dumps(profile.interaction_patterns),
                'interaction_history': json.dumps(profile.interaction_history),
                'last_active': profile.last_active.isoformat(),
                'total_sessions': profile.total_sessions,
                'favorite_topics': json.dumps(profile.favorite_topics),
                'response_satisfaction_avg': profile.response_satisfaction_avg,
                'learned_context': json.dumps(profile.learned_context)
            }
            
            await self.redis_client.hset(memory_key, mapping=memory_data)
            
            # Establecer expiración
            await self.redis_client.expire(memory_key, self.memory_retention_days * 24 * 3600)
            
            logger.info(f"🧠 Perfil de memoria actualizado para usuario {profile.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando perfil de memoria: {e}")
            
    async def record_conversation_memory(self, memory: ConversationMemory):
        """Registrar memoria de conversación"""
        try:
            # Solo registrar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - memoria de conversación no registrada")
                return
                
            conversation_key = f"memory:conversation:{memory.user_id}:{memory.session_id}"
            
            conversation_data = {
                'session_id': memory.session_id,
                'user_id': memory.user_id,
                'company_id': memory.company_id,
                'start_time': memory.start_time.isoformat(),
                'end_time': memory.end_time.isoformat() if memory.end_time else None,
                'topics_discussed': json.dumps(memory.topics_discussed),
                'questions_asked': json.dumps(memory.questions_asked),
                'satisfaction_score': memory.satisfaction_score,
                'key_insights': json.dumps(memory.key_insights),
                'follow_up_needed': memory.follow_up_needed
            }
            
            await self.redis_client.hset(conversation_key, mapping=conversation_data)
            
            # Establecer expiración
            await self.redis_client.expire(conversation_key, self.memory_retention_days * 24 * 3600)
            
            # Actualizar perfil del usuario
            await self._update_profile_from_conversation(memory)
            
        except Exception as e:
            logger.error(f"❌ Error registrando memoria de conversación: {e}")
            
    async def _update_profile_from_conversation(self, conversation: ConversationMemory):
        """Actualizar perfil de usuario basado en conversación"""
        try:
            profile = await self.get_user_memory_profile(conversation.user_id, conversation.company_id)
            
            # Actualizar consultas frecuentes
            for question in conversation.questions_asked:
                if question not in profile.frequent_queries:
                    profile.frequent_queries.append(question)
                    
            # Limitar número de consultas frecuentes
            profile.frequent_queries = profile.frequent_queries[-20:]
            
            # Actualizar temas favoritos
            for topic in conversation.topics_discussed:
                if topic not in profile.favorite_topics:
                    profile.favorite_topics.append(topic)
                    
            # Limitar temas favoritos
            profile.favorite_topics = profile.favorite_topics[-10:]
            
            # Actualizar patrones de interacción
            hour = conversation.start_time.hour
            day_of_week = conversation.start_time.weekday()
            
            profile.interaction_patterns[f"hour_{hour}"] = profile.interaction_patterns.get(f"hour_{hour}", 0) + 1
            profile.interaction_patterns[f"day_{day_of_week}"] = profile.interaction_patterns.get(f"day_{day_of_week}", 0) + 1
            
            # Actualizar satisfacción promedio
            if conversation.satisfaction_score:
                current_avg = profile.response_satisfaction_avg
                total_sessions = profile.total_sessions
                new_avg = ((current_avg * total_sessions) + conversation.satisfaction_score) / (total_sessions + 1)
                profile.response_satisfaction_avg = new_avg
                
            # Actualizar contadores
            profile.total_sessions += 1
            profile.last_active = datetime.now()
            
            await self.update_user_memory_profile(profile)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando perfil desde conversación: {e}")
            
    async def get_user_context_suggestions(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Obtener sugerencias contextuales basadas en memoria"""
        try:
            profile = await self.get_user_memory_profile(user_id, company_id)
            
            suggestions = {
                'frequent_topics': profile.favorite_topics[:5],
                'suggested_questions': profile.frequent_queries[:5],
                'preferred_interaction_time': self._get_preferred_time(profile.interaction_patterns),
                'personalization_level': 'high' if profile.total_sessions > 10 else 'medium' if profile.total_sessions > 3 else 'low',
                'satisfaction_trend': 'positive' if profile.response_satisfaction_avg > 0.7 else 'neutral' if profile.response_satisfaction_avg > 0.5 else 'needs_improvement'
            }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sugerencias contextuales: {e}")
            return {}
            
    def _get_preferred_time(self, interaction_patterns: Dict[str, int]) -> Dict[str, int]:
        """Obtener horarios preferidos de interacción"""
        hour_patterns = {k: v for k, v in interaction_patterns.items() if k.startswith('hour_')}
        day_patterns = {k: v for k, v in interaction_patterns.items() if k.startswith('day_')}
        
        preferred_hour = max(hour_patterns.items(), key=lambda x: x[1])[0].split('_')[1] if hour_patterns else 0
        preferred_day = max(day_patterns.items(), key=lambda x: x[1])[0].split('_')[1] if day_patterns else 0
        
        return {
            'preferred_hour': int(preferred_hour),
            'preferred_day': int(preferred_day)
        }
        
    async def cleanup_old_memories(self):
        """Limpiar memorias antiguas"""
        try:
            # Esta tarea se ejecutaría periódicamente
            cutoff_date = datetime.now() - timedelta(days=self.memory_retention_days)
            
            # Redis TTL se encarga automáticamente de la limpieza
            logger.info("🧹 Limpieza automática de memorias antiguas completada")
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza de memorias: {e}")
            
    async def store_interaction(self, user_id: str, company_id: str, user_message: str, 
                              ai_response: str, sentiment_type=None, response_source: str = "unknown"):
        """Almacenar interacción en memoria a largo plazo"""
        try:
            interaction_data = {
                "user_message": user_message,
                "ai_response": ai_response,
                "sentiment": sentiment_type.value if sentiment_type else "neutral",
                "response_source": response_source,
                "timestamp": datetime.now().isoformat()
            }
            
            # Actualizar memoria del usuario
            memory_profile = await self.get_user_memory_profile(user_id, company_id)
            if memory_profile:
                # Verificar si los atributos existen antes de usarlos
                if hasattr(memory_profile, 'interaction_count'):
                    memory_profile.interaction_count += 1
                else:
                    memory_profile.interaction_count = 1
                    
                if hasattr(memory_profile, 'last_interaction'):
                    memory_profile.last_interaction = datetime.now()
                else:
                    memory_profile.last_interaction = datetime.now()
                
                # Añadir a historial de interacciones
                if hasattr(memory_profile, 'interaction_history'):
                    memory_profile.interaction_history.append(interaction_data)
                    # Mantener solo las últimas 50 interacciones
                    memory_profile.interaction_history = memory_profile.interaction_history[-50:]
                else:
                    memory_profile.interaction_history = [interaction_data]
                
                await self.update_user_memory_profile(memory_profile)
                
            logger.info(f"🧠 Interacción almacenada para usuario {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error almacenando interacción: {e}")
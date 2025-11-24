"""
Servicio de Cache de Sesiones - Reducir timeouts de MongoDB usando Redis
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
import redis.asyncio as aioredis
from loguru import logger

try:
    from ..contracts.ai_types import ChatSession, ChatMessage, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatSession, ChatMessage, ChatContext


class SessionCacheService:
    """Cache inteligente de sesiones para reducir latencia de MongoDB"""
    
    def __init__(self, redis_url: str = None):
        import os
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client: Optional[aioredis.Redis] = None
        self.cache_ttl = 30 * 60  # 30 minutos
        self.connected = False
    
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            self.connected = True
            logger.info("🔗 SessionCacheService conectado a Redis")
        except Exception as e:
            logger.warning(f"⚠️ SessionCacheService - Redis no disponible: {e}")
            self.connected = False
    
    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
    
    async def cache_session(self, session: ChatSession):
        """Cachear sesión en Redis"""
        if not self.connected or not self.redis_client:
            return False
        
        try:
            cache_key = f"session_cache:{session.id}"
            
            # Serializar sesión
            session_data = {
                'id': session.id,
                'user_id': session.user_id,
                'company_id': getattr(session, 'company_id', 'unknown'),
                'title': session.title,
                'status': session.status,
                'last_activity': session.last_activity.isoformat(),
                'message_count': session.message_count,
                'is_active': session.is_active,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'messages': [self._serialize_message(msg) for msg in (session.messages or [])],
                'context': self._serialize_context(session.context) if session.context else {}
            }
            
            await self.redis_client.setex(
                cache_key, 
                self.cache_ttl,
                json.dumps(session_data)
            )
            
            logger.debug(f"💾 Sesión {session.id} cacheada en Redis")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cacheando sesión {session.id}: {e}")
            return False
    
    async def get_cached_session(self, session_id: str) -> Optional[ChatSession]:
        """Obtener sesión del cache"""
        if not self.connected or not self.redis_client:
            return None
        
        try:
            cache_key = f"session_cache:{session_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if not cached_data:
                return None
            
            session_data = json.loads(cached_data)
            
            # Reconstruir objeto ChatSession
            context = self._deserialize_context(session_data.get('context', {}))
            messages = [self._deserialize_message(msg_data) for msg_data in session_data.get('messages', [])]
            
            session = ChatSession(
                id=session_data['id'],
                user_id=session_data['user_id'],
                title=session_data['title'],
                status=session_data['status'],
                last_activity=datetime.fromisoformat(session_data['last_activity']),
                message_count=session_data['message_count'],
                context=context,
                messages=messages,
                company_id=session_data.get('company_id', 'unknown'),
                created_at=datetime.fromisoformat(session_data['created_at']),
                updated_at=datetime.fromisoformat(session_data['updated_at']),
                is_active=session_data['is_active']
            )
            
            logger.debug(f"⚡ Sesión {session_id} obtenida del cache")
            return session
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sesión del cache {session_id}: {e}")
            # Limpiar cache corrupto
            try:
                await self.redis_client.delete(cache_key)
            except:
                pass
            return None
    
    async def invalidate_session_cache(self, session_id: str):
        """Invalidar cache de sesión"""
        if not self.connected or not self.redis_client:
            return
        
        try:
            cache_key = f"session_cache:{session_id}"
            await self.redis_client.delete(cache_key)
            logger.debug(f"🗑️ Cache de sesión {session_id} invalidado")
        except Exception as e:
            logger.error(f"❌ Error invalidando cache de sesión {session_id}: {e}")
    
    async def create_temporary_session(self, session_id: str, user_id: str, company_id: str) -> ChatSession:
        """Crear sesión temporal para evitar timeouts de MongoDB"""
        try:
            # Crear contexto temporal
            context = ChatContext(
                user_id=user_id,
                company_id=company_id,
                session_preferences={},
                business_context={}
            )
            
            # Crear sesión temporal
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                title=f"Chat {datetime.now().strftime('%H:%M')}",
                status="active",
                last_activity=datetime.now(timezone.utc),
                message_count=0,
                context=context,
                messages=[],
                company_id=company_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            )
            
            # Cachear sesión temporal
            await self.cache_session(session)
            
            logger.info(f"🆕 Sesión temporal creada y cacheada: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Error creando sesión temporal: {e}")
            raise
    
    def _serialize_message(self, message: ChatMessage) -> Dict:
        """Serializar mensaje a diccionario"""
        return {
            'id': message.id,
            'session_id': message.session_id,
            'role': message.role,
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'metadata': message.metadata or {}
        }
    
    def _deserialize_message(self, msg_data: Dict) -> ChatMessage:
        """Deserializar mensaje desde diccionario"""
        return ChatMessage(
            id=msg_data['id'],
            session_id=msg_data['session_id'],
            role=msg_data['role'],
            content=msg_data['content'],
            timestamp=datetime.fromisoformat(msg_data['timestamp']),
            metadata=msg_data.get('metadata', {})
        )
    
    def _serialize_context(self, context: ChatContext) -> Dict:
        """Serializar contexto a diccionario"""
        if isinstance(context, dict):
            return context
        
        return {
            'user_id': getattr(context, 'user_id', 'unknown'),
            'company_id': getattr(context, 'company_id', 'unknown'),
            'session_preferences': getattr(context, 'session_preferences', {}),
            'business_context': getattr(context, 'business_context', {})
        }
    
    def _deserialize_context(self, context_data: Dict) -> ChatContext:
        """Deserializar contexto desde diccionario"""
        return ChatContext(
            user_id=context_data.get('user_id', 'unknown'),
            company_id=context_data.get('company_id', 'unknown'),
            session_preferences=context_data.get('session_preferences', {}),
            business_context=context_data.get('business_context', {})
        )
    
    async def cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas del cache"""
        if not self.connected or not self.redis_client:
            return
        
        try:
            # Esta función se ejecutaría periódicamente
            pattern = "session_cache:*"
            keys = await self.redis_client.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # Sin TTL = clave huérfana
                    await self.redis_client.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"🧹 {cleaned_count} sesiones expiradas limpiadas del cache")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando cache de sesiones: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache de sesiones"""
        if not self.connected or not self.redis_client:
            return {'connected': False, 'total_sessions': 0}
        
        try:
            pattern = "session_cache:*"
            keys = await self.redis_client.keys(pattern)
            
            return {
                'connected': True,
                'total_sessions': len(keys),
                'cache_ttl_minutes': self.cache_ttl // 60,
                'redis_url': self.redis_url.replace('redis://localhost', 'redis://local')
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de cache: {e}")
            return {'connected': False, 'error': str(e)}
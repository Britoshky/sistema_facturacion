"""
Servicio de Integración Redis para comunicación entre backends
Maneja eventos entre Backend Node.js y Backend Python IA
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

import redis.asyncio as redis
from loguru import logger
from pydantic import ValidationError

try:
    from ..contracts.integration_types import (
except ImportError:
    from src.contracts.integration_types import (
    EventType, RedisChannel,
    AnalysisRequestEvent, AnalysisCompletedEvent,
    ChatMessageEvent, ChatResponseEvent,
    DocumentCreatedEvent, SystemStatusEvent,
    UserNotificationEvent, IntegrationResponse
)
try:
    from ..core.config import get_settings
except ImportError:
    from src.core.config import get_settings


class RedisIntegrationService:
    """Servicio de integración Redis entre backends"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.is_connected = False
    
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis = redis.from_url(
                self.settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            
            # Verificar conexión
            await self.redis.ping()
            self.is_connected = True
            
            logger.info("✅ Connected to Redis for backend integration")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Desconectar Redis"""
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            
            if self.redis:
                await self.redis.close()
            
            self.is_connected = False
            logger.info("Redis integration disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting Redis: {e}")
    
    # === PUBLICAR EVENTOS ===
    
    async def publish_analysis_completed(
        self, 
        analysis_result: AnalysisCompletedEvent
    ) -> bool:
        """Publicar resultado de análisis completado"""
        try:
            await self._publish_event(
                channel=RedisChannel.ANALYSIS,
                event=analysis_result
            )
            
            # También publicar en WebSocket para frontend
            await self._publish_event(
                channel=RedisChannel.WEBSOCKET,
                event=analysis_result
            )
            
            logger.info(f"Published analysis completed: {analysis_result.analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing analysis completed: {e}")
            return False
    
    async def publish_chat_response(
        self,
        chat_response: ChatResponseEvent
    ) -> bool:
        """Publicar respuesta de chat IA"""
        try:
            await self._publish_event(
                channel=RedisChannel.CHAT,
                event=chat_response
            )
            
            # También WebSocket para tiempo real
            await self._publish_event(
                channel=RedisChannel.WEBSOCKET,
                event=chat_response
            )
            
            logger.info(f"Published chat response: {chat_response.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing chat response: {e}")
            return False
    
    async def publish_system_status(
        self,
        status: SystemStatusEvent
    ) -> bool:
        """Publicar estado del sistema IA"""
        try:
            await self._publish_event(
                channel=RedisChannel.SYSTEM,
                event=status
            )
            
            logger.debug(f"Published system status: {status.status}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing system status: {e}")
            return False
    
    async def publish_user_notification(
        self,
        notification: UserNotificationEvent
    ) -> bool:
        """Publicar notificación para usuario"""
        try:
            await self._publish_event(
                channel=RedisChannel.NOTIFICATIONS,
                event=notification
            )
            
            # También en WebSocket del usuario específico
            user_channel = f"{RedisChannel.WEBSOCKET}:user:{notification.user_id}"
            await self._publish_event(
                channel=user_channel,
                event=notification
            )
            
            logger.info(f"Published user notification: {notification.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing user notification: {e}")
            return False
    
    # === SUSCRIBIRSE A EVENTOS ===
    
    async def subscribe_to_analysis_requests(self):
        """Suscribirse a solicitudes de análisis desde Node.js"""
        await self._subscribe_to_channel(
            channel=RedisChannel.ANALYSIS,
            handler=self._handle_analysis_request
        )
    
    async def subscribe_to_chat_messages(self):
        """Suscribirse a mensajes de chat desde Node.js"""
        await self._subscribe_to_channel(
            channel=RedisChannel.CHAT,
            handler=self._handle_chat_message
        )
    
    async def subscribe_to_document_events(self):
        """Suscribirse a eventos de documentos desde Node.js"""
        await self._subscribe_to_channel(
            channel=RedisChannel.DOCUMENTS,
            handler=self._handle_document_event
        )
    
    # === MANEJADORES DE EVENTOS ===
    
    def register_analysis_handler(self, handler: Callable[[AnalysisRequestEvent], None]):
        """Registrar manejador para solicitudes de análisis"""
        self._register_handler("analysis_request", handler)
    
    def register_chat_handler(self, handler: Callable[[ChatMessageEvent], None]):
        """Registrar manejador para mensajes de chat"""
        self._register_handler("chat_message", handler)
    
    def register_document_handler(self, handler: Callable[[DocumentCreatedEvent], None]):
        """Registrar manejador para eventos de documentos"""
        self._register_handler("document_created", handler)
    
    # === MÉTODOS PRIVADOS ===
    
    async def _publish_event(self, channel: str, event: Any):
        """Publicar evento en canal Redis"""
        if not self.is_connected:
            raise RuntimeError("Redis not connected")
        
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "source": "ai_backend_python",
            "event": event.model_dump() if hasattr(event, 'model_dump') else event
        }
        
        await self.redis.publish(channel, json.dumps(event_data))
    
    async def _subscribe_to_channel(self, channel: str, handler: Callable):
        """Suscribirse a canal Redis"""
        if not self.pubsub:
            self.pubsub = self.redis.pubsub()
        
        await self.pubsub.subscribe(channel)
        
        logger.info(f"Subscribed to Redis channel: {channel}")
        
        # Procesar mensajes en background
        asyncio.create_task(self._process_messages(handler))
    
    async def _process_messages(self, handler: Callable):
        """Procesar mensajes de Redis"""
        while True:
            try:
                message = await self.pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    await handler(message)
                    
            except Exception as e:
                logger.error(f"Error processing Redis message: {e}")
                await asyncio.sleep(1)
    
    async def _handle_analysis_request(self, message: Dict[str, Any]):
        """Manejar solicitud de análisis desde Node.js"""
        try:
            data = json.loads(message["data"])
            event_data = data["event"]
            
            # Validar evento
            request = AnalysisRequestEvent(**event_data)
            
            # Ejecutar manejadores registrados
            handlers = self.event_handlers.get("analysis_request", [])
            for handler in handlers:
                await handler(request)
                
        except ValidationError as e:
            logger.error(f"Invalid analysis request format: {e}")
        except Exception as e:
            logger.error(f"Error handling analysis request: {e}")
    
    async def _handle_chat_message(self, message: Dict[str, Any]):
        """Manejar mensaje de chat desde Node.js"""
        try:
            data = json.loads(message["data"])
            event_data = data["event"]
            
            # Validar evento
            chat_message = ChatMessageEvent(**event_data)
            
            # Ejecutar manejadores registrados
            handlers = self.event_handlers.get("chat_message", [])
            for handler in handlers:
                await handler(chat_message)
                
        except ValidationError as e:
            logger.error(f"Invalid chat message format: {e}")
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    async def _handle_document_event(self, message: Dict[str, Any]):
        """Manejar evento de documento desde Node.js"""
        try:
            data = json.loads(message["data"])
            event_data = data["event"]
            
            # Validar evento
            document_event = DocumentCreatedEvent(**event_data)
            
            # Ejecutar manejadores registrados
            handlers = self.event_handlers.get("document_created", [])
            for handler in handlers:
                await handler(document_event)
                
        except ValidationError as e:
            logger.error(f"Invalid document event format: {e}")
        except Exception as e:
            logger.error(f"Error handling document event: {e}")
    
    def _register_handler(self, event_type: str, handler: Callable):
        """Registrar manejador de evento"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")
    
    # === UTILIDADES ===
    
    async def health_check(self) -> bool:
        """Verificar estado Redis"""
        try:
            if not self.is_connected:
                return False
            
            await self.redis.ping()
            return True
            
        except Exception:
            return False
    
    async def get_channel_subscribers(self, channel: str) -> int:
        """Obtener número de suscriptores de un canal"""
        try:
            result = await self.redis.pubsub_numsub(channel)
            return result[channel] if channel in result else 0
            
        except Exception as e:
            logger.error(f"Error getting subscribers count: {e}")
            return 0
    
    async def send_direct_message(
        self,
        user_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """Enviar mensaje directo a usuario específico"""
        try:
            user_channel = f"{RedisChannel.WEBSOCKET}:user:{user_id}"
            await self._publish_event(user_channel, message)
            return True
            
        except Exception as e:
            logger.error(f"Error sending direct message: {e}")
            return False


# === INSTANCIA SINGLETON ===

_redis_service: Optional[RedisIntegrationService] = None


async def get_redis_integration() -> RedisIntegrationService:
    """Obtener instancia del servicio Redis"""
    global _redis_service
    
    if _redis_service is None:
        _redis_service = RedisIntegrationService()
        await _redis_service.connect()
    
    return _redis_service


async def shutdown_redis_integration():
    """Cerrar servicio Redis"""
    global _redis_service
    
    if _redis_service:
        await _redis_service.disconnect()
        _redis_service = None
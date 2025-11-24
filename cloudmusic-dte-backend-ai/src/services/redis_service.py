"""
Servicio de Redis para comunicación entre servicios
Manejo de eventos WebSocket y sincronización con backend Node.js
Cumple RF011 del informe: captura ≤2s, procesamiento ≤8s
"""

import json
import asyncio
from typing import Dict, Optional, Callable, Any, Union
from datetime import datetime, timezone

import redis.asyncio as redis
from loguru import logger

try:
    from ..contracts.websocket_types import WebSocketEvent, EventType, SystemStatus, NotificationEvent, BaseEvent, DocumentEvent, AIAnalysisEvent, AIResultEvent, ChatEvent
except ImportError:
    from src.contracts.websocket_types import WebSocketEvent, EventType, SystemStatus, NotificationEvent, BaseEvent, DocumentEvent, AIAnalysisEvent, AIResultEvent, ChatEvent


class RedisService:
    """Servicio de comunicación Redis para eventos inter-servicios"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        channel_prefix: str = "cloudmusic_dte"
    ):
        self.redis_url = redis_url
        self.channel_prefix = channel_prefix
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.event_handlers: Dict[Any, Callable] = {}  # Soporta tanto EventType como strings
        self._listening = False
        
        # Canales específicos
        self.channels = {
            "websocket_events": f"{channel_prefix}:websocket",
            "system_status": f"{channel_prefix}:system",
            "ai_responses": f"{channel_prefix}:ai_responses",
            "document_events": f"{channel_prefix}:documents",
            "user_notifications": f"{channel_prefix}:notifications"
        }
    
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.pubsub = self.redis_client.pubsub()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Desconectar de Redis"""
        try:
            self._listening = False
            if self.pubsub:
                await self.pubsub.close()
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    # === PUBLISHING ===
    
    async def publish_websocket_event(
        self,
        event: WebSocketEvent
    ) -> bool:
        """Publicar evento WebSocket para el backend Node.js"""
        try:
            if not self.redis_client:
                await self.connect()
            
            event_data = event.model_dump_json()
            
            await self.redis_client.publish(
                self.channels["websocket_events"],
                event_data
            )
            
            logger.debug(f"Published WebSocket event: {event.event_type}")
            return True
        except Exception as e:
            logger.error(f"Error publishing WebSocket event: {e}")
            return False
    
    async def publish_ai_response(
        self,
        session_id: str,
        message_id: str,
        content: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Publicar respuesta IA para WebSocket"""
        
        event = WebSocketEvent(
            event_id=message_id,
            event_type=EventType.AI_RESPONSE,
            user_id=user_id,
            data={
                "session_id": session_id,
                "message_id": message_id,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            metadata=metadata or {}
        )
        
        return await self.publish_websocket_event(event)
    
    async def publish_system_status(
        self,
        service_name: str,
        status: SystemStatus,
        details: Optional[Dict] = None
    ) -> bool:
        """Publicar estado del sistema"""
        try:
            if not self.redis_client:
                await self.connect()
            
            status_data = {
                "service": service_name,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": details or {}
            }
            
            await self.redis_client.publish(
                self.channels["system_status"],
                json.dumps(status_data)
            )
            
            logger.debug(f"Published system status: {service_name} - {status}")
            return True
        except Exception as e:
            logger.error(f"Error publishing system status: {e}")
            return False
    
    async def publish_document_analysis_complete(
        self,
        analysis_id: str,
        document_id: str,
        user_id: str,
        risk_level: str,
        results: Dict
    ) -> bool:
        """Publicar completación de análisis de documento"""
        
        event = WebSocketEvent(
            event_id=analysis_id,
            event_type=EventType.ANALYSIS_COMPLETE,
            user_id=user_id,
            data={
                "analysis_id": analysis_id,
                "document_id": document_id,
                "risk_level": risk_level,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return await self.publish_websocket_event(event)
    
    async def publish_notification(
        self,
        notification: NotificationEvent
    ) -> bool:
        """Publicar notificación de usuario"""
        
        event = WebSocketEvent(
            event_id=notification.notification_id,
            event_type=EventType.NOTIFICATION,
            user_id=notification.user_id,
            data=notification.model_dump(),
            metadata={"channel": "notifications"}
        )
        
        return await self.publish_websocket_event(event)
    
    # === SUBSCRIBING ===
    
    async def subscribe_to_channel(self, channel: str, handler: Callable[[str], Any]):
        """Suscribirse a un canal específico con su handler"""
        try:
            if not self.pubsub:
                await self.connect()
            
            # Suscribirse al canal
            await self.pubsub.subscribe(channel)
            
            # Registrar el handler
            self.event_handlers[channel] = handler
            
            logger.info(f"Subscribed to channel: {channel}")
                
        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {e}")
            raise
    
    async def listen_for_messages(self):
        """Escuchar mensajes de canales suscritos específicos"""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis PubSub")
        
        self._listening = True
        logger.info("Starting Redis message listener for specific channels")
        
        try:
            async for message in self.pubsub.listen():
                if not self._listening:
                    break
                
                if message["type"] == "message":
                    channel = message["channel"].decode()
                    data = message["data"].decode()
                    
                    # Buscar handler para este canal
                    if channel in self.event_handlers:
                        try:
                            await self.event_handlers[channel](data)
                        except Exception as e:
                            logger.error(f"Error in channel handler for {channel}: {e}")
                    else:
                        logger.debug(f"No handler for channel: {channel}")
                        
        except asyncio.CancelledError:
            logger.info("Redis message listener cancelled")
        except Exception as e:
            logger.error(f"Error in Redis message listener: {e}")
        finally:
            self._listening = False
    
    async def subscribe_to_events(self):
        """Suscribirse a eventos de otros servicios"""
        try:
            if not self.pubsub:
                await self.connect()
            
            # Suscribirse a canales relevantes
            channels_to_subscribe = [
                self.channels["document_events"],
                self.channels["user_notifications"],
                self.channels["system_status"]
            ]
            
            for channel in channels_to_subscribe:
                await self.pubsub.subscribe(channel)
            
            logger.info(f"Subscribed to Redis channels: {channels_to_subscribe}")
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            raise
    
    async def listen_for_events(self):
        """Escuchar eventos de Redis"""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis PubSub")
        
        self._listening = True
        logger.info("Starting Redis event listener")
        
        try:
            async for message in self.pubsub.listen():
                if not self._listening:
                    break
                
                if message["type"] == "message":
                    await self._handle_redis_message(
                        message["channel"].decode(),
                        message["data"].decode()
                    )
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")
        finally:
            self._listening = False
    
    async def _handle_redis_message(self, channel: str, data: str):
        """Manejar mensaje recibido de Redis"""
        try:
            # Parsear datos
            message_data = json.loads(data)
            
            # Determinar tipo de evento por canal
            if channel == self.channels["document_events"]:
                await self._handle_document_event(message_data)
            elif channel == self.channels["user_notifications"]:
                await self._handle_notification_event(message_data)
            elif channel == self.channels["system_status"]:
                await self._handle_system_status(message_data)
            else:
                logger.debug(f"Unhandled Redis message from channel {channel}")
                
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
    
    async def _handle_document_event(self, data: Dict):
        """Manejar evento de documento"""
        event_type = data.get("event_type")
        
        if event_type == "document_created":
            # Trigger análisis automático si está configurado
            logger.info(f"Document created: {data.get('document_id')}")
        elif event_type == "document_updated":
            logger.info(f"Document updated: {data.get('document_id')}")
        elif event_type == "analysis_requested":
            # Procesar solicitud de análisis
            await self._process_analysis_request(data)
    
    async def _handle_notification_event(self, data: Dict):
        """Manejar evento de notificación"""
        logger.info(f"Notification event: {data.get('type')} for user {data.get('user_id')}")
    
    async def _handle_system_status(self, data: Dict):
        """Manejar cambio de estado del sistema"""
        service = data.get("service")
        status = data.get("status")
        logger.info(f"System status update: {service} - {status}")
    
    async def _process_analysis_request(self, data: Dict):
        """Procesar solicitud de análisis desde Node.js backend"""
        try:
            # Importar aquí para evitar dependencias circulares
            from .document_analysis_service import DocumentAnalysisService
            from .database_service import DatabaseService
            
            # TODO: Inyectar dependencias apropiadamente
            # Por ahora, esto es un placeholder
            logger.info(f"Analysis request received for document {data.get('document_id')}")
            
        except Exception as e:
            logger.error(f"Error processing analysis request: {e}")
    
    # === CACHE OPERATIONS ===
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Guardar en caché Redis"""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Serializar valor
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            await self.redis_client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Obtener de caché Redis"""
        try:
            if not self.redis_client:
                await self.connect()
            
            value = await self.redis_client.get(key)
            if value is None:
                return None
            
            # Intentar deserializar JSON
            try:
                return json.loads(value.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return value.decode()
                
        except Exception as e:
            logger.error(f"Error getting cache: {e}")
            return None
    
    async def cache_delete(self, key: str) -> bool:
        """Eliminar de caché Redis"""
        try:
            if not self.redis_client:
                await self.connect()
            
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache: {e}")
            return False
    
    # === SIMPLE PUBLISHING ===
    
    async def publish_message(self, channel: str, message: str) -> bool:
        """Publicar mensaje simple a un canal"""
        try:
            if not self.redis_client:
                await self.connect()
            
            await self.redis_client.publish(channel, message)
            logger.debug(f"Published message to {channel}")
            return True
        except Exception as e:
            logger.error(f"Error publishing message to {channel}: {e}")
            return False
    
    # === UTILITIES ===
    
    def register_event_handler(self, event_type: Union[EventType, str], handler: Callable):
        """Registrar manejador de eventos"""
        self.event_handlers[event_type] = handler
    
    async def health_check(self) -> bool:
        """Verificar salud de conexión Redis"""
        try:
            if not self.redis_client:
                await self.connect()
            
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
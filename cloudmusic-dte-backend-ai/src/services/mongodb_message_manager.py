"""
MongoDB Message Manager - Gestión especializada de mensajes de chat
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger

from .mongodb_connection_manager import MongoDBConnectionManager, clean_unicode_string
try:
    from ..contracts.ai_types import ChatMessage
except ImportError:
    from src.contracts.ai_types import ChatMessage


class MongoDBMessageManager:
    """Gestor especializado para mensajes de chat en MongoDB"""
    
    def __init__(self, connection_manager: MongoDBConnectionManager):
        self.connection = connection_manager
    
    async def add_message_to_session(self, session_id: str, message: ChatMessage) -> bool:
        """Agregar mensaje a una sesión"""
        await self.connection.ensure_initialized()
        
        try:
            # Preparar documento del mensaje
            message_doc = {
                "_id": message.id,
                "session_id": session_id,
                "role": message.role,
                "content": clean_unicode_string(message.content),
                "timestamp": message.timestamp,
                "metadata": message.metadata or {}
            }
            
            # Insertar mensaje
            result = await self.connection.chat_messages.insert_one(message_doc)
            
            if result.inserted_id:
                logger.debug(f"💬 Mensaje {message.id} agregado a sesión {session_id}")
                return True
            else:
                logger.error(f"❌ No se pudo agregar mensaje {message.id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error agregando mensaje: {e}")
            return False
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Obtener mensajes de una sesión"""
        await self.connection.ensure_initialized()
        
        try:
            # Construir consulta
            cursor = self.connection.chat_messages.find(
                {"session_id": session_id}
            ).sort("timestamp", 1)
            
            if offset > 0:
                cursor = cursor.skip(offset)
                
            if limit:
                cursor = cursor.limit(limit)
            
            messages = []
            async for msg_doc in cursor:
                try:
                    message = ChatMessage(
                        id=msg_doc.get("_id", ""),
                        session_id=msg_doc.get("session_id", ""),
                        role=msg_doc.get("role", ""),
                        content=clean_unicode_string(msg_doc.get("content", "")),
                        timestamp=msg_doc.get("timestamp", datetime.now(timezone.utc)),
                        metadata=msg_doc.get("metadata", {})
                    )
                    messages.append(message)
                    
                except Exception as msg_error:
                    logger.warning(f"⚠️ Error procesando mensaje: {msg_error}")
                    continue
            
            logger.debug(f"📥 {len(messages)} mensajes cargados de sesión {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo mensajes sesión {session_id}: {e}")
            return []
    
    async def search_user_messages(
        self,
        user_id: str,
        search_text: str,
        company_id: Optional[str] = None,
        limit: int = 20
    ) -> List[ChatMessage]:
        """Buscar mensajes de un usuario por contenido"""
        await self.connection.ensure_initialized()
        
        try:
            # Primero obtener sesiones del usuario
            session_filter = {"user_id": user_id}
            if company_id:
                session_filter["company_id"] = company_id
            
            session_ids = []
            async for session in self.connection.chat_sessions.find(session_filter, {"_id": 1}):
                session_ids.append(session["_id"])
            
            if not session_ids:
                return []
            
            # Buscar mensajes en esas sesiones
            search_filter = {
                "session_id": {"$in": session_ids},
                "content": {"$regex": search_text, "$options": "i"}
            }
            
            messages = []
            cursor = self.connection.chat_messages.find(search_filter)\
                .sort("timestamp", -1)\
                .limit(limit)
                
            async for msg_doc in cursor:
                try:
                    message = ChatMessage(
                        id=msg_doc.get("_id", ""),
                        session_id=msg_doc.get("session_id", ""),
                        role=msg_doc.get("role", ""),
                        content=clean_unicode_string(msg_doc.get("content", "")),
                        timestamp=msg_doc.get("timestamp", datetime.now(timezone.utc)),
                        metadata=msg_doc.get("metadata", {})
                    )
                    messages.append(message)
                    
                except Exception as msg_error:
                    logger.warning(f"⚠️ Error procesando mensaje en búsqueda: {msg_error}")
                    continue
            
            logger.debug(f"🔍 {len(messages)} mensajes encontrados con '{search_text}'")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error buscando mensajes: {e}")
            return []
    
    async def get_recent_messages(self, session_id: str, count: int = 10) -> List[ChatMessage]:
        """Obtener mensajes más recientes de una sesión"""
        await self.connection.ensure_initialized()
        
        try:
            cursor = self.connection.chat_messages.find(
                {"session_id": session_id}
            ).sort("timestamp", -1).limit(count)
            
            messages = []
            async for msg_doc in cursor:
                try:
                    message = ChatMessage(
                        id=msg_doc.get("_id", ""),
                        session_id=msg_doc.get("session_id", ""),
                        role=msg_doc.get("role", ""),
                        content=clean_unicode_string(msg_doc.get("content", "")),
                        timestamp=msg_doc.get("timestamp", datetime.now(timezone.utc)),
                        metadata=msg_doc.get("metadata", {})
                    )
                    messages.append(message)
                    
                except Exception as msg_error:
                    logger.warning(f"⚠️ Error procesando mensaje reciente: {msg_error}")
                    continue
            
            # Invertir para tener orden cronológico
            messages.reverse()
            
            logger.debug(f"⏰ {len(messages)} mensajes recientes de sesión {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo mensajes recientes: {e}")
            return []
    
    async def count_user_messages(self, user_id: str, company_id: str = None) -> int:
        """Contar total de mensajes de un usuario"""
        await self.connection.ensure_initialized()
        
        try:
            # Obtener sesiones del usuario
            session_filter = {"user_id": user_id}
            if company_id:
                session_filter["company_id"] = company_id
            
            session_ids = []
            async for session in self.connection.chat_sessions.find(session_filter, {"_id": 1}):
                session_ids.append(session["_id"])
            
            if not session_ids:
                return 0
            
            # Contar mensajes
            count = await self.connection.chat_messages.count_documents({
                "session_id": {"$in": session_ids}
            })
            
            logger.debug(f"📊 Usuario {user_id} tiene {count} mensajes totales")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error contando mensajes: {e}")
            return 0
    
    async def delete_session_messages(self, session_id: str) -> bool:
        """Eliminar todos los mensajes de una sesión"""
        await self.connection.ensure_initialized()
        
        try:
            result = await self.connection.chat_messages.delete_many({
                "session_id": session_id
            })
            
            logger.info(f"🗑️ {result.deleted_count} mensajes eliminados de sesión {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error eliminando mensajes de sesión {session_id}: {e}")
            return False
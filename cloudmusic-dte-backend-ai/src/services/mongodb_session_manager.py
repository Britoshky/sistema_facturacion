"""
MongoDB Session Manager - Gestión especializada de sesiones de chat
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger

from .mongodb_connection_manager import MongoDBConnectionManager, clean_unicode_string
try:
    from ..contracts.ai_types import ChatSession, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatSession, ChatContext


class MongoDBSessionManager:
    """Gestor especializado para sesiones de chat en MongoDB"""
    
    def __init__(self, connection_manager: MongoDBConnectionManager):
        self.connection = connection_manager
    
    async def create_chat_session(self, session: ChatSession) -> bool:
        """Crear nueva sesión de chat en MongoDB"""
        await self.connection.ensure_initialized()
        
        try:
            # Preparar documento para MongoDB
            session_doc = {
                "_id": session.id,
                "user_id": session.user_id,
                "company_id": getattr(session.context, 'company_id', None) if session.context else None,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "is_active": session.is_active,
                "context": self._serialize_context(session.context) if session.context else {},
                "messages": []  # Los mensajes se almacenan por separado
            }
            
            # Insertar en MongoDB
            result = await self.connection.chat_sessions.insert_one(session_doc)
            
            if result.inserted_id:
                logger.info(f"💾 Sesión {session.id} creada en MongoDB")
                return True
            else:
                logger.error(f"❌ No se pudo crear sesión {session.id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creando sesión: {e}")
            return False
    
    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Obtener sesión de chat por ID"""
        await self.connection.ensure_initialized()
        
        try:
            # Buscar sesión en MongoDB
            session_doc = await self.connection.chat_sessions.find_one({"_id": session_id})
            
            if not session_doc:
                logger.warning(f"⚠️ Sesión {session_id} no encontrada")
                return None
            
            # Obtener mensajes de la sesión
            messages_cursor = self.connection.chat_messages.find(
                {"session_id": session_id}
            ).sort("timestamp", 1)
            
            messages = []
            async for msg_doc in messages_cursor:
                try:
                    # Convertir documento a ChatMessage
                    try:
                        from ..contracts.ai_types import ChatMessage
                    except ImportError:
                        from src.contracts.ai_types import ChatMessage
                    
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
            
            # Reconstruir contexto
            context = None
            if session_doc.get("context"):
                context = ChatContext(
                    user_id=session_doc.get("user_id", ""),
                    company_id=session_doc.get("company_id", ""),
                    session_preferences=session_doc["context"].get("session_preferences", {}),
                    business_context=session_doc["context"].get("business_context", {})
                )
            
            # Crear objeto ChatSession
            session = ChatSession(
                id=session_doc["_id"],
                user_id=session_doc["user_id"],
                context=context,
                messages=messages,
                created_at=session_doc["created_at"],
                updated_at=session_doc["updated_at"],
                is_active=session_doc.get("is_active", True)
            )
            
            logger.debug(f"📖 Sesión {session_id} cargada con {len(messages)} mensajes")
            return session
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sesión {session_id}: {e}")
            return None
    
    async def update_chat_session(self, session: ChatSession) -> bool:
        """Actualizar sesión existente"""
        await self.connection.ensure_initialized()
        
        try:
            update_doc = {
                "$set": {
                    "updated_at": datetime.now(timezone.utc),
                    "is_active": session.is_active,
                    "context": self._serialize_context(session.context) if session.context else {}
                }
            }
            
            result = await self.connection.chat_sessions.update_one(
                {"_id": session.id},
                update_doc
            )
            
            if result.modified_count > 0:
                logger.debug(f"📝 Sesión {session.id} actualizada")
                return True
            else:
                logger.warning(f"⚠️ Sesión {session.id} no se pudo actualizar")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error actualizando sesión {session.id}: {e}")
            return False
    
    async def get_user_chat_sessions(
        self, 
        user_id: str, 
        company_id: str = None,
        active_only: bool = True, 
        limit: int = 10
    ) -> List[ChatSession]:
        """Obtener sesiones de chat de un usuario"""
        await self.connection.ensure_initialized()
        
        try:
            # Construir filtro
            filter_query = {"user_id": user_id}
            
            if company_id:
                filter_query["company_id"] = company_id
                
            if active_only:
                filter_query["is_active"] = True
            
            # Buscar sesiones
            sessions_cursor = self.connection.chat_sessions.find(filter_query)\
                .sort("created_at", -1)\
                .limit(limit)
            
            sessions = []
            async for session_doc in sessions_cursor:
                try:
                    # Para optimizar, no cargar todos los mensajes
                    context = None
                    if session_doc.get("context"):
                        context = ChatContext(
                            user_id=session_doc.get("user_id", ""),
                            company_id=session_doc.get("company_id", ""),
                            session_preferences=session_doc["context"].get("session_preferences", {}),
                            business_context=session_doc["context"].get("business_context", {})
                        )
                    
                    session = ChatSession(
                        id=session_doc["_id"],
                        user_id=session_doc["user_id"],
                        context=context,
                        messages=[],  # No cargar mensajes para lista
                        created_at=session_doc["created_at"],
                        updated_at=session_doc["updated_at"],
                        is_active=session_doc.get("is_active", True)
                    )
                    sessions.append(session)
                    
                except Exception as session_error:
                    logger.warning(f"⚠️ Error procesando sesión: {session_error}")
                    continue
            
            logger.debug(f"📋 {len(sessions)} sesiones encontradas para usuario {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo sesiones usuario {user_id}: {e}")
            return []
    
    async def end_chat_session(self, session_id: str) -> bool:
        """Finalizar sesión de chat"""
        await self.connection.ensure_initialized()
        
        try:
            result = await self.connection.chat_sessions.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"🔚 Sesión {session_id} finalizada")
                return True
            else:
                logger.warning(f"⚠️ Sesión {session_id} no encontrada para finalizar")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error finalizando sesión {session_id}: {e}")
            return False
    
    async def update_session_timestamp(self, session_id: str) -> bool:
        """Actualizar timestamp de última actividad"""
        await self.connection.ensure_initialized()
        
        try:
            result = await self.connection.chat_sessions.update_one(
                {"_id": session_id},
                {"$set": {"updated_at": datetime.now(timezone.utc)}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error actualizando timestamp sesión {session_id}: {e}")
            return False
    
    def _serialize_context(self, context: ChatContext) -> Dict:
        """Serializar contexto para MongoDB"""
        if not context:
            return {}
            
        return {
            "user_id": context.user_id,
            "company_id": context.company_id,
            "session_preferences": context.session_preferences or {},
            "business_context": context.business_context or {}
        }
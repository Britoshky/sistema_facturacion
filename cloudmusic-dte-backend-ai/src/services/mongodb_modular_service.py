"""
MongoDB Modular Service - Coordinador de servicios especializados MongoDB
Reemplaza el archivo database_service.py monolítico con arquitectura modular
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger

from .mongodb_connection_manager import MongoDBConnectionManager
from .mongodb_session_manager import MongoDBSessionManager
from .mongodb_message_manager import MongoDBMessageManager
try:
    from ..contracts.ai_types import ChatSession, ChatMessage
except ImportError:
    from src.contracts.ai_types import ChatSession, ChatMessage
try:
    from ..contracts.document_types import DocumentAnalysis
except ImportError:
    from src.contracts.document_types import DocumentAnalysis


class MongoDBModularService:
    """Servicio MongoDB modular y escalable"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        # Componente central de conexión
        self.connection_manager = MongoDBConnectionManager(db)
        
        # Servicios especializados
        self.sessions = MongoDBSessionManager(self.connection_manager)
        self.messages = MongoDBMessageManager(self.connection_manager)
        
        # Referencia directa a la base de datos para otros usos
        self.db = db
    
    # === MÉTODOS DE INICIALIZACIÓN ===
    
    async def initialize_collections(self):
        """Inicializar colecciones y esquemas"""
        return await self.connection_manager.initialize_collections()
    
    async def get_collection_stats(self) -> Dict:
        """Obtener estadísticas de colecciones"""
        return await self.connection_manager.get_collection_stats()
    
    # === MÉTODOS DE COMPATIBILIDAD PARA SESIONES ===
    
    async def create_chat_session(self, session: ChatSession) -> bool:
        """Método de compatibilidad - crear sesión"""
        return await self.sessions.create_chat_session(session)
    
    async def save_chat_session(self, session: ChatSession) -> bool:
        """Método de compatibilidad - guardar sesión"""
        return await self.sessions.create_chat_session(session)
    
    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Método de compatibilidad - obtener sesión"""
        return await self.sessions.get_chat_session(session_id)
    
    async def update_chat_session(self, session: ChatSession) -> bool:
        """Método de compatibilidad - actualizar sesión"""
        return await self.sessions.update_chat_session(session)
    
    async def get_user_chat_sessions(
        self, 
        user_id: str, 
        company_id: str = None,
        active_only: bool = True, 
        limit: int = 10
    ) -> List[ChatSession]:
        """Método de compatibilidad - obtener sesiones de usuario"""
        return await self.sessions.get_user_chat_sessions(user_id, company_id, active_only, limit)
    
    async def end_chat_session(self, session_id: str) -> bool:
        """Método de compatibilidad - finalizar sesión"""
        return await self.sessions.end_chat_session(session_id)
    
    async def update_session_timestamp(self, session_id: str) -> bool:
        """Método de compatibilidad - actualizar timestamp"""
        return await self.sessions.update_session_timestamp(session_id)
    
    # === MÉTODOS DE COMPATIBILIDAD PARA MENSAJES ===
    
    async def add_message_to_session(self, session_id: str, message: ChatMessage) -> bool:
        """Método de compatibilidad - agregar mensaje"""
        return await self.messages.add_message_to_session(session_id, message)
    
    async def save_message(self, message: ChatMessage) -> bool:
        """Método de compatibilidad - guardar mensaje"""
        return await self.messages.add_message_to_session(message.session_id, message)
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Método de compatibilidad - obtener mensajes de sesión"""
        return await self.messages.get_session_messages(session_id, limit, offset)
    
    async def search_user_messages(
        self,
        user_id: str,
        search_text: str,
        company_id: Optional[str] = None,
        limit: int = 20
    ) -> List[ChatMessage]:
        """Método de compatibilidad - buscar mensajes"""
        return await self.messages.search_user_messages(user_id, search_text, company_id, limit)
    
    # === MÉTODOS DE ANÁLISIS Y ESTADÍSTICAS ===
    
    async def get_user_chat_analytics(
        self, 
        user_id: str, 
        company_id: str = None,
        days_back: int = 30
    ) -> Dict:
        """Obtener analíticas de chat de un usuario"""
        try:
            # Obtener sesiones del usuario
            sessions = await self.sessions.get_user_chat_sessions(
                user_id, company_id, active_only=False, limit=100
            )
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "total_messages": 0,
                    "avg_messages_per_session": 0,
                    "active_sessions": 0,
                    "recent_activity": [],
                    "user_id": user_id,
                    "company_id": company_id
                }
            
            # Contar mensajes totales
            total_messages = await self.messages.count_user_messages(user_id, company_id)
            
            # Calcular estadísticas
            active_sessions = len([s for s in sessions if s.is_active])
            avg_messages = total_messages / len(sessions) if sessions else 0
            
            # Actividad reciente (últimas 5 sesiones)
            recent_activity = []
            for session in sessions[:5]:
                recent_messages = await self.messages.get_recent_messages(session.id, 3)
                recent_activity.append({
                    "session_id": session.id,
                    "created_at": session.created_at,
                    "message_count": len(recent_messages),
                    "last_message": recent_messages[-1].content[:100] if recent_messages else ""
                })
            
            analytics = {
                "total_sessions": len(sessions),
                "total_messages": total_messages,
                "avg_messages_per_session": round(avg_messages, 1),
                "active_sessions": active_sessions,
                "recent_activity": recent_activity,
                "user_id": user_id,
                "company_id": company_id,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"📊 Analíticas generadas para usuario {user_id}")
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Error generando analíticas: {e}")
            return {"error": str(e)}
    
    # === MÉTODOS PARA DOCUMENTOS Y AUDITORÍA ===
    
    async def save_document_analysis(self, analysis: DocumentAnalysis) -> bool:
        """Guardar análisis de documento"""
        await self.connection_manager.ensure_initialized()
        
        try:
            analysis_doc = {
                "_id": analysis.id,
                "document_id": analysis.document_id,
                "company_id": analysis.company_id,
                "analysis_type": analysis.analysis_type,
                "results": analysis.results,
                "confidence_score": analysis.confidence_score,
                "created_at": analysis.created_at,
                "metadata": analysis.metadata or {}
            }
            
            result = await self.connection_manager.ai_document_analysis.insert_one(analysis_doc)
            
            if result.inserted_id:
                logger.info(f"📄 Análisis {analysis.id} guardado")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error guardando análisis: {e}")
            return False
    
    async def log_audit_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        company_id: str = None,
        metadata: Dict = None
    ) -> bool:
        """Registrar evento de auditoría"""
        await self.connection_manager.ensure_initialized()
        
        try:
            audit_doc = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "company_id": company_id,
                "timestamp": datetime.now(timezone.utc),
                "metadata": metadata or {}
            }
            
            result = await self.connection_manager.audit_trail.insert_one(audit_doc)
            
            if result.inserted_id:
                logger.debug(f"📋 Evento auditoría registrado: {action}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error registrando auditoría: {e}")
            return False
    
    # === MÉTODOS DE UTILIDAD ===
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Obtener perfil de usuario desde sesiones"""
        try:
            sessions = await self.sessions.get_user_chat_sessions(user_id, limit=5)
            
            if not sessions:
                return None
            
            # Extraer información del contexto de sesiones
            profile = {
                "user_id": user_id,
                "total_sessions": len(sessions),
                "last_activity": sessions[0].updated_at if sessions else None,
                "companies": list(set([
                    getattr(s.context, 'company_id', None) 
                    for s in sessions 
                    if s.context and hasattr(s.context, 'company_id')
                ])),
                "created_from_sessions": True
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo perfil usuario: {e}")
            return None
    
    async def get_company_profile(self, company_id: str) -> Optional[Dict]:
        """Obtener perfil de empresa desde sesiones"""
        try:
            # Buscar sesiones de la empresa
            sessions_cursor = self.connection_manager.db.chat_sessions.find({
                "company_id": company_id
            }).limit(20)
            
            sessions_count = 0
            user_ids = set()
            
            async for session in sessions_cursor:
                sessions_count += 1
                if session.get("user_id"):
                    user_ids.add(session["user_id"])
            
            if sessions_count == 0:
                return None
            
            profile = {
                "company_id": company_id,
                "total_sessions": sessions_count,
                "unique_users": len(user_ids),
                "user_ids": list(user_ids),
                "created_from_sessions": True
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo perfil empresa: {e}")
            return None
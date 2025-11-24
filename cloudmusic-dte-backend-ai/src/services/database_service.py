"""
Servicio de base de datos MongoDB modular para CloudMusic DTE AI Backend
ARCHIVO DE COMPATIBILIDAD - Usa arquitectura modular internamente
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

# Importar servicio modular
from .mongodb_modular_service import MongoDBModularService


class DatabaseService:
    """
    Servicio de compatibilidad que delega a la arquitectura modular
    Mantiene la misma interfaz pública para no romper código existente
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        # Usar servicio modular internamente
        self.modular_service = MongoDBModularService(db)
        
        # Mantener referencias por compatibilidad
        self.db = db
        self._initialized = False
    
    # === DELEGACIÓN A SERVICIO MODULAR ===
    
    async def initialize_collections(self):
        """Inicializar colecciones via servicio modular"""
        result = await self.modular_service.initialize_collections()
        self._initialized = True
        
        # Exponer colecciones para compatibilidad
        self.chat_sessions = self.modular_service.connection_manager.chat_sessions
        self.chat_messages = self.modular_service.connection_manager.chat_messages
        self.ai_document_analysis = self.modular_service.connection_manager.ai_document_analysis
        self.sii_responses = self.modular_service.connection_manager.sii_responses
        self.websocket_events = self.modular_service.connection_manager.websocket_events
        self.audit_trail = self.modular_service.connection_manager.audit_trail
        
        return result
    
    async def ensure_initialized(self):
        """Asegurar inicialización via servicio modular"""
        if not self._initialized:
            await self.initialize_collections()
    
    async def get_collection_stats(self) -> Dict:
        """Obtener estadísticas via servicio modular"""
        return await self.modular_service.get_collection_stats()
    
    # === SESIONES DE CHAT - DELEGACIÓN ===
    
    async def create_chat_session(self, session) -> bool:
        return await self.modular_service.create_chat_session(session)
    
    async def save_chat_session(self, session) -> bool:
        return await self.modular_service.save_chat_session(session)
    
    async def get_chat_session(self, session_id: str):
        return await self.modular_service.get_chat_session(session_id)
    
    async def update_chat_session(self, session) -> bool:
        return await self.modular_service.update_chat_session(session)
    
    async def get_user_chat_sessions(
        self, 
        user_id: str, 
        company_id: str = None,
        active_only: bool = True, 
        limit: int = 10
    ):
        return await self.modular_service.get_user_chat_sessions(
            user_id, company_id, active_only, limit
        )
    
    async def end_chat_session(self, session_id: str) -> bool:
        return await self.modular_service.end_chat_session(session_id)
    
    async def update_session_timestamp(self, session_id: str) -> bool:
        return await self.modular_service.update_session_timestamp(session_id)
    
    # === MENSAJES - DELEGACIÓN ===
    
    async def add_message_to_session(self, session_id: str, message) -> bool:
        return await self.modular_service.add_message_to_session(session_id, message)
    
    async def save_message(self, message) -> bool:
        return await self.modular_service.save_message(message)
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None,
        offset: int = 0
    ):
        return await self.modular_service.get_session_messages(session_id, limit, offset)
    
    async def search_user_messages(
        self,
        user_id: str,
        search_text: str,
        company_id: Optional[str] = None,
        limit: int = 20
    ):
        return await self.modular_service.search_user_messages(
            user_id, search_text, company_id, limit
        )
    
    # === ANÁLISIS DE DOCUMENTOS - DELEGACIÓN ===
    
    async def save_document_analysis(self, analysis) -> bool:
        return await self.modular_service.save_document_analysis(analysis)
    
    # === AUDITORÍA - DELEGACIÓN ===
    
    async def log_audit_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        company_id: str = None,
        metadata: Dict = None
    ) -> bool:
        return await self.modular_service.log_audit_event(
            user_id, action, resource_type, resource_id, company_id, metadata
        )
    
    # === ANALÍTICAS - DELEGACIÓN ===
    
    async def get_user_chat_analytics(
        self, 
        user_id: str, 
        company_id: str = None,
        days_back: int = 30
    ) -> Dict:
        return await self.modular_service.get_user_chat_analytics(
            user_id, company_id, days_back
        )
    
    # === WEBSOCKETS - VIA MODULAR SERVICE ===
    
    async def log_websocket_event(
        self,
        event_type: str,
        user_id: str,
        session_id: str = None,
        data: Dict = None
    ) -> bool:
        """Registrar evento de WebSocket via servicio modular"""
        await self.ensure_initialized()
        
        try:
            event_doc = {
                "event_type": event_type,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc),
                "data": data or {}
            }
            
            result = await self.modular_service.connection_manager.websocket_events.insert_one(event_doc)
            return bool(result.inserted_id)
            
        except Exception:
            return False
    
    # === UTILIDADES - DELEGACIÓN ===
    
    async def get_user_profile(self, user_id: str):
        return await self.modular_service.get_user_profile(user_id)
    
    async def get_company_profile(self, company_id: str):
        return await self.modular_service.get_company_profile(company_id)
    
    # === MÉTODOS DE COMPATIBILIDAD ESPECÍFICOS ===
    
    async def get_user_sessions_with_context(
        self,
        user_id: str,
        company_id: Optional[str] = None,
        limit: int = 10
    ):
        """Método específico de compatibilidad para sesiones con contexto"""
        return await self.modular_service.get_user_chat_sessions(
            user_id, company_id, active_only=False, limit=limit
        )
    
    async def get_recent_messages(self, session_id: str, limit: int = 5):
        """Método específico de compatibilidad para mensajes recientes"""
        return await self.modular_service.get_session_messages(session_id, limit=limit)
    
    async def search_sessions_by_content(
        self,
        user_id: str,
        search_text: str,
        company_id: Optional[str] = None
    ):
        """Método específico de compatibilidad para búsqueda en contenido"""
        return await self.modular_service.search_user_messages(
            user_id, search_text, company_id
        )
    
    # === LEGACY SUPPORT ===
    
    async def create_session(self, session_data: Dict) -> str:
        """Método legacy de compatibilidad"""
        # Convertir dict a ChatSession si es necesario
        if hasattr(self.modular_service, '_convert_dict_to_session'):
            session = self.modular_service._convert_dict_to_session(session_data)
        else:
            try:
                from ..contracts.ai_types import ChatSession
            except ImportError:
                from src.contracts.ai_types import ChatSession
            session = ChatSession(**session_data)
        
        success = await self.create_chat_session(session)
        return session.id if success else None
    
    async def add_message(self, session_id: str, message_data: Dict) -> bool:
        """Método legacy de compatibilidad"""
        # Convertir dict a ChatMessage si es necesario
        if hasattr(self.modular_service, '_convert_dict_to_message'):
            message = self.modular_service._convert_dict_to_message(message_data)
        else:
            try:
                from ..contracts.ai_types import ChatMessage
            except ImportError:
                from src.contracts.ai_types import ChatMessage
            message = ChatMessage(**message_data)
        
        return await self.add_message_to_session(session_id, message)
    
    # === PROPIEDADES DE COMPATIBILIDAD ===
    
    @property
    def is_initialized(self) -> bool:
        """Propiedad de compatibilidad"""
        return self._initialized
    
    @property
    def collections(self) -> Dict[str, Any]:
        """Propiedad de compatibilidad para acceso a colecciones"""
        if not self._initialized:
            return {}
        
        return {
            'chat_sessions': self.chat_sessions,
            'chat_messages': self.chat_messages,
            'ai_document_analysis': self.ai_document_analysis,
            'sii_responses': self.sii_responses,
            'websocket_events': self.websocket_events,
            'audit_trail': self.audit_trail
        }


# === ALIAS PARA COMPATIBILIDAD TOTAL ===
MongoDBService = DatabaseService  # Alias común usado en algunos lugares
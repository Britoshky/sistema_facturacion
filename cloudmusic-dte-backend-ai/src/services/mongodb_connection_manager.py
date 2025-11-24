"""
MongoDB Connection Manager - Gestión centralizada de conexiones MongoDB
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from loguru import logger


class MongoDBConnectionManager:
    """Gestor centralizado de conexiones MongoDB"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._collections_initialized = False
        
        # Referencias a colecciones
        self.chat_sessions: Optional[AsyncIOMotorCollection] = None
        self.chat_messages: Optional[AsyncIOMotorCollection] = None
        self.ai_document_analysis: Optional[AsyncIOMotorCollection] = None
        self.audit_trail: Optional[AsyncIOMotorCollection] = None
        self.websocket_events: Optional[AsyncIOMotorCollection] = None
        self.sii_responses: Optional[AsyncIOMotorCollection] = None
    
    async def initialize_collections(self):
        """Inicializar y verificar colecciones MongoDB"""
        if self._collections_initialized:
            return True
            
        try:
            # Obtener referencias a colecciones
            self.chat_sessions = self.db.chat_sessions
            self.chat_messages = self.db.chat_messages  
            self.ai_document_analysis = self.db.ai_document_analysis
            self.audit_trail = self.db.audit_trail
            self.websocket_events = self.db.websocket_events
            self.sii_responses = self.db.sii_responses
            
            # Crear índices para rendimiento
            await self._create_indexes()
            
            self._collections_initialized = True
            logger.info("✅ Colecciones MongoDB inicializadas correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando colecciones: {e}")
            return False
    
    async def _create_indexes(self):
        """Crear índices optimizados"""
        try:
            # Índices para chat_sessions
            await self.chat_sessions.create_index("user_id")
            await self.chat_sessions.create_index([("user_id", 1), ("created_at", -1)])
            await self.chat_sessions.create_index("company_id")
            await self.chat_sessions.create_index("is_active")
            
            # Índices para chat_messages  
            await self.chat_messages.create_index("session_id")
            await self.chat_messages.create_index([("session_id", 1), ("timestamp", 1)])
            await self.chat_messages.create_index("role")
            
            # Índices para ai_document_analysis
            await self.ai_document_analysis.create_index("document_id")
            await self.ai_document_analysis.create_index("company_id")
            await self.ai_document_analysis.create_index("created_at")
            
            # Índices para audit_trail
            await self.audit_trail.create_index("user_id")
            await self.audit_trail.create_index("action")
            await self.audit_trail.create_index([("company_id", 1), ("timestamp", -1)])
            
            logger.debug("📊 Índices MongoDB creados correctamente")
            
        except Exception as e:
            logger.warning(f"⚠️ Error creando algunos índices: {e}")
    
    async def get_collection_stats(self) -> dict:
        """Obtener estadísticas de colecciones"""
        if not self._collections_initialized:
            await self.initialize_collections()
            
        try:
            stats = {}
            
            collections = {
                "chat_sessions": self.chat_sessions,
                "chat_messages": self.chat_messages,
                "ai_document_analysis": self.ai_document_analysis,
                "audit_trail": self.audit_trail,
                "websocket_events": self.websocket_events,
                "sii_responses": self.sii_responses
            }
            
            for name, collection in collections.items():
                if collection:
                    count = await collection.count_documents({})
                    stats[name] = count
            
            logger.info(f"📊 Estadísticas MongoDB: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}
    
    def is_initialized(self) -> bool:
        """Verificar si las colecciones están inicializadas"""
        return self._collections_initialized
    
    async def ensure_initialized(self):
        """Asegurar que las colecciones estén inicializadas"""
        if not self._collections_initialized:
            await self.initialize_collections()


def clean_unicode_string(text: str) -> str:
    """Limpiar cadenas con caracteres Unicode problemáticos"""
    if not text:
        return ""
    
    try:
        # Normalizar y limpiar caracteres especiales
        import unicodedata
        
        # Normalizar usando NFD (descomposición canónica)
        normalized = unicodedata.normalize('NFD', text)
        
        # Filtrar caracteres de control y no imprimibles
        cleaned = ''.join(
            char for char in normalized 
            if unicodedata.category(char) not in ['Cc', 'Cf', 'Mn']
        )
        
        # Reemplazar múltiples espacios en blanco
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
        
    except Exception as e:
        logger.warning(f"Error limpiando string: {e}")
        return str(text).strip()
"""
Servicio de base de datos MongoDB modular para CloudMusic DTE AI Backend
ARCHIVO DE COMPATIBILIDAD - Usa arquitectura modular internamente
"""

from typing import Dict, List, Optional, Any
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
        self.audit_trail = db.audit_trail
        
    async def initialize_collections(self):
        """Inicializar colecciones e índices según estructura real MongoDB"""
        try:
            # Verificar conectividad antes de crear índices
            await self.db.command('ping')
            logger.info("MongoDB connection verified successfully")
            
            # Índices para ai_document_analysis (crear solo si no existen)
            await self.ai_document_analysis.create_index([("document_id", ASCENDING)], background=True)
            await self.ai_document_analysis.create_index([("company_id", ASCENDING)], background=True)
            await self.ai_document_analysis.create_index([("analysis_type", ASCENDING)], background=True)
            await self.ai_document_analysis.create_index([("analysis_timestamp", DESCENDING)], background=True)
            await self.ai_document_analysis.create_index([("ai_model", ASCENDING)], background=True)
            await self.ai_document_analysis.create_index([("risk_level", ASCENDING)], background=True)
            
            # NO crear índices por ahora - solo verificar conectividad
            logger.info("Skipping index creation - testing connectivity only...")
            
            # Verificar que las colecciones existen
            collections = await self.db.list_collection_names()
            logger.info(f"Available collections: {collections}")
            
            # Test de inserción rápida
            test_doc = {"test": "backend_ai_init", "timestamp": datetime.now(timezone.utc)}
            result = await self.ai_document_analysis.insert_one(test_doc)
            logger.info(f"Test insert successful: {result.inserted_id}")
            
            # Limpiar documento de prueba
            await self.ai_document_analysis.delete_one({"_id": result.inserted_id})
            logger.info("Test document cleaned up")
            
            logger.info("Database connectivity verified successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    # === CHAT SESSIONS ===
    
    async def save_chat_session(self, session: ChatSession) -> bool:
        """Guardar sesión de chat"""
        try:
            session_dict = session.model_dump()
            # Agregar session_id para compatibilidad
            session_dict["session_id"] = session_dict["id"]
            
            logger.debug(f"💾 Guardando sesión - user_id: {session_dict.get('user_id')}, context.user_id: {session_dict.get('context', {}).get('user_id')}")
            
            await self.chat_sessions.insert_one(session_dict)
            return True
        except Exception as e:
            logger.error(f"Error saving chat session: {e}")
            return False
    
    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Obtener sesión de chat por ID"""
        try:
            # Buscar por session_id (compatibilidad) o por id
            doc = await self.chat_sessions.find_one({
                "$or": [
                    {"session_id": session_id},
                    {"id": session_id}
                ]
            })
            if doc:
                # Convertir ObjectId a string y asegurar campo id
                if "_id" in doc:
                    doc.pop("_id", None)  # Remover _id ya que ChatSession usa id
                
                # Asegurar que tenga los campos requeridos para ChatSession
                if "id" not in doc and "session_id" in doc:
                    doc["id"] = doc["session_id"]
                
                # Crear contexto si no existe o corregir contexto existente
                if "context" not in doc:
                    try:
    from ..contracts.ai_types import ChatContext
except ImportError:
    from src.contracts.ai_types import ChatContext
                    doc["context"] = ChatContext(
                        company_id=doc.get("company_id", "unknown"),
                        user_id=doc.get("user_id", "unknown"),  # Usar user_id del documento principal
                        topic="general",
                        user_name="Usuario",  # Valor por defecto
                        company_name="Empresa",  # Valor por defecto
                        is_new_user=True,  # Primera sesión
                        total_conversations=1,  # Primera conversación
                        communication_style="professional",  # Estilo profesional
                        question_complexity="medium",  # Complejidad media
                        has_real_data=True,  # Acceso a datos reales PostgreSQL
                        business_data={},  # Datos empresariales
                        message_intent="general",  # Intención del mensaje
                        current_session_id=doc.get("id", "unknown"),  # ID de sesión actual
                        conversation_length=1,  # Longitud de conversación
                        session_topic="business_query",  # Tópico de la sesión
                        context_type_session="business_query",  # Tipo de contexto de sesión
                        user_email="usuario@empresa.com",  # Email por defecto
                        company_rut="12345678-9",  # RUT por defecto
                        favorite_topics=["facturacion", "dte", "business"],  # Tópicos favoritos por defecto
                        last_interaction=None,  # Última interacción por defecto
                        typical_session_length=5,  # Longitud típica de sesión por defecto
                        preferred_topics=["contabilidad", "facturacion", "impuestos"],  # Tópicos preferidos por defecto
                        prefers_detailed_answers=True,  # Preferencia por respuestas detalladas por defecto
                        math_frequency="medium",  # Frecuencia de uso de cálculos matemáticos por defecto
                        session_context={}  # Contexto de sesión por defecto
                    ).model_dump()
                elif isinstance(doc["context"], dict):
                    # Corregir contexto existente con user_id del documento principal si falta
                    if doc["context"].get("user_id") == "unknown" and doc.get("user_id") != "unknown":
                        doc["context"]["user_id"] = doc.get("user_id")
                        logger.debug(f"🔧 Corrigiendo user_id en contexto: {doc.get('user_id')}")
                
                # Establecer valores por defecto para campos requeridos
                defaults = {
                    "title": f"Chat Session - {doc.get('id', 'Unknown')}",
                    "status": "active",
                    "last_activity": doc.get("updated_at", datetime.now(timezone.utc)),
                    "message_count": len(doc.get("messages", [])),
                    "created_at": doc.get("created_at", datetime.now(timezone.utc)),
                    "updated_at": doc.get("updated_at", datetime.now(timezone.utc))
                }
                
                for key, value in defaults.items():
                    if key not in doc:
                        doc[key] = value
                
                # Asegurar que context sea dict para model_validate
                if not isinstance(doc.get("context"), dict):
                    try:
    from ..contracts.ai_types import ChatContext
except ImportError:
    from src.contracts.ai_types import ChatContext
                    default_context = ChatContext(
                        company_id=doc.get("company_id", "unknown"),
                        user_id=doc.get("user_id", "unknown"),
                        topic="general",
                        user_name="Usuario",
                        company_name="Empresa",
                        is_new_user=True,
                        total_conversations=1,
                        communication_style="professional",
                        question_complexity="medium",
                        has_real_data=True,
                        business_data={},
                        message_intent="general",
                        current_session_id=doc.get("id", "unknown"),
                        conversation_length=1,
                        session_topic="business_query",
                        context_type_session="business_query"
                    )
                    doc["context"] = default_context.model_dump()
                    logger.debug(f"🔧 Context creado y convertido a dict: {doc['context']}")
                
                logger.debug(f"📦 Documento final antes de crear ChatSession: {doc.keys()}")
                logger.debug(f"📦 ID en documento: {doc.get('id')}")
                logger.debug(f"📦 Context en documento: {type(doc.get('context'))}")
                
                try:
                    # Crear ChatSession con model_validate
                    try:
    from ..contracts.ai_types import ChatSession
except ImportError:
    from src.contracts.ai_types import ChatSession
                    session = ChatSession.model_validate(doc)
                    logger.debug(f"✅ ChatSession creado exitosamente: {session.id}")
                    logger.debug(f"📦 ChatSession tiene context: {hasattr(session, 'context')}")
                    if hasattr(session, 'context'):
                        logger.debug(f"📦 Context type: {type(session.context)}")
                    return session
                except Exception as session_error:
                    logger.error(f"❌ Error creando ChatSession: {session_error}")
                    logger.error(f"📦 Doc que causó el error: {doc}")
                    logger.error(f"📦 Claves del doc: {list(doc.keys())}")
                    raise session_error
            return None
        except Exception as e:
            logger.error(f"Error getting chat session: {e}")
            return None
    
    async def update_chat_session(self, session: ChatSession) -> bool:
        """Actualizar sesión de chat"""
        try:
            session_dict = session.model_dump()
            # Convertir messages a lista de dicts y limpiar contenido UTF-8
            cleaned_messages = []
            for msg in session.messages:
                msg_dict = msg.model_dump()
                if 'content' in msg_dict:
                    msg_dict['content'] = clean_unicode_string(msg_dict['content'])
                cleaned_messages.append(msg_dict)
            session_dict["messages"] = cleaned_messages
            
            result = await self.chat_sessions.update_one(
                {"session_id": session.session_id},
                {"$set": session_dict}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating chat session: {e}")
            return False
    
    async def get_user_chat_sessions(
        self,
        user_id: str,
        company_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 20
    ) -> List[ChatSession]:
        """Obtener sesiones de chat de usuario"""
        try:
            query = {"user_id": user_id}
            if company_id:
                query["company_id"] = company_id
            if active_only:
                query["is_active"] = True
            
            cursor = self.chat_sessions.find(query).sort("updated_at", DESCENDING).limit(limit)
            sessions = []
            
            async for doc in cursor:
                # Para performance, no cargar messages completos en listado
                doc["messages"] = []
                sessions.append(ChatSession(**doc))
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting user chat sessions: {e}")
            return []
    
    # === CHAT MESSAGES ===
    
    async def save_message(self, message: ChatMessage) -> bool:
        """Guardar mensaje de chat en la sesión correspondiente"""
        try:
            # Buscar sesión existente o crear nueva
            session = await self.chat_sessions.find_one({"session_id": message.session_id})
            
            if session:
                # Limpiar contenido del mensaje antes de guardarlo
                message_data = message.model_dump()
                if 'content' in message_data:
                    message_data['content'] = clean_unicode_string(message_data['content'])
                
                # Agregar mensaje a sesión existente
                await self.chat_sessions.update_one(
                    {"session_id": message.session_id},
                    {
                        "$push": {"messages": message_data},
                        "$set": {"updated_at": datetime.now(timezone.utc)}
                    }
                )
            else:
                # Crear nueva sesión con el mensaje - extraer user_id y company_id de metadata
                metadata = message.metadata or {}
                user_id = metadata.get('user_id', 'unknown')
                company_id = metadata.get('company_id', 'unknown')
                
                # Crear contexto de chat para la nueva sesión
                try:
    from ..contracts.ai_types import ChatContext
except ImportError:
    from src.contracts.ai_types import ChatContext
                chat_context = ChatContext(
                    company_id=company_id,
                    user_id=user_id,
                    topic="general"
                )
                
                # Limpiar contenido del mensaje para nueva sesión
                message_data = message.model_dump()
                if 'content' in message_data:
                    message_data['content'] = clean_unicode_string(message_data['content'])
                
                new_session = {
                    "session_id": message.session_id,
                    "user_id": user_id,
                    "company_id": company_id,
                    "context": chat_context.model_dump(),  # Agregar contexto
                    "title": f"Chat Session - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                    "status": "active",
                    "last_activity": datetime.now(timezone.utc),
                    "message_count": 1,
                    "session_start": datetime.now(timezone.utc),
                    "session_end": None,
                    "is_active": True,
                    "messages": [message_data],
                    "session_metadata": {},
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                
                logger.debug(f"💾 Creando nueva sesión desde save_message - user_id: {user_id}, company_id: {company_id}")
                await self.chat_sessions.insert_one(new_session)
            
            logger.debug(f"Chat message saved to session {message.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            return False
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Obtener mensajes de sesión desde la estructura embedida"""
        try:
            # Los mensajes están embebidos en la sesión, no en colección separada
            session_doc = await self.chat_sessions.find_one({"session_id": session_id})
            
            if not session_doc or "messages" not in session_doc:
                return []
            
            # Obtener mensajes con paginación
            all_messages = session_doc["messages"]
            
            # Aplicar offset y limit
            paginated_messages = all_messages[offset:offset + limit] if offset or limit < len(all_messages) else all_messages
            
            # Convertir a objetos ChatMessage
            messages = []
            for msg_dict in paginated_messages:
                try:
                    # Asegurar que el mensaje tiene todos los campos requeridos
                    if "message_id" not in msg_dict:
                        msg_dict["message_id"] = msg_dict.get("id", str(uuid4()))
                    
                    messages.append(ChatMessage(**msg_dict))
                except Exception as msg_error:
                    logger.warning(f"Error parsing message: {msg_error}, msg: {msg_dict}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []
    
    async def search_user_messages(
        self,
        user_id: str,
        query: str,
        company_id: Optional[str] = None,
        limit: int = 10
    ) -> List[ChatMessage]:
        """Buscar mensajes del usuario por texto"""
        try:
            # Primero obtener session_ids del usuario
            session_filter = {"user_id": user_id}
            if company_id:
                session_filter["company_id"] = company_id
            
            session_cursor = self.chat_sessions.find(session_filter, {"session_id": 1})
            session_ids = [doc["session_id"] async for doc in session_cursor]
            
            # Buscar en mensajes de esas sesiones
            search_filter = {
                "session_id": {"$in": session_ids},
                "$text": {"$search": query}
            }
            
            cursor = self.chat_messages.find(search_filter).sort("timestamp", DESCENDING).limit(limit)
            
            messages = []
            async for doc in cursor:
                messages.append(ChatMessage(**doc))
            
            return messages
        except Exception as e:
            logger.error(f"Error searching user messages: {e}")
            return []
    
    # === ANALYTICS ===
    
    async def get_user_chat_analytics(
        self,
        user_id: str,
        company_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Obtener analíticas avanzadas de chat del usuario"""
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Filtro base
            base_filter = {
                "user_id": user_id,
                "created_at": {"$gte": since_date}
            }
            if company_id:
                base_filter["company_id"] = company_id
            
            # Obtener todas las sesiones para análisis más detallado
            sessions_cursor = self.chat_sessions.find(base_filter).sort("created_at", DESCENDING)
            sessions = await sessions_cursor.to_list(None)
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "active_sessions": 0,
                    "total_messages": 0,
                    "avg_messages_per_session": 0,
                    "common_topics": [],
                    "last_session_date": None,
                    "conversation_patterns": {
                        "avg_session_duration": 0,
                        "preferred_times": [],
                        "interaction_frequency": "low"
                    },
                    "intent_analysis": {
                        "math_queries": 0,
                        "dte_queries": 0,
                        "general_queries": 0
                    }
                }
            
            # Cálculos básicos
            total_sessions = len(sessions)
            active_sessions = sum(1 for s in sessions if s.get("is_active", False))
            total_messages = sum(s.get("message_count", 0) for s in sessions)
            avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
            
            # Análisis de tópicos
            topics = [s.get("topic", "General") for s in sessions]
            topic_counts = {}
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            common_topics = sorted(topic_counts.keys(), key=lambda x: topic_counts[x], reverse=True)[:5]
            
            # Análisis de patrones de conversación
            session_durations = []
            interaction_times = []
            
            for session in sessions:
                # Duración de sesión (estimada)
                created = session.get("created_at")
                updated = session.get("updated_at")
                if created and updated:
                    duration = (updated - created).total_seconds() / 60  # en minutos
                    session_durations.append(duration)
                
                # Hora de interacción
                if created:
                    hour = created.hour
                    interaction_times.append(hour)
            
            avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0
            
            # Determinar horarios preferidos
            time_counts = {}
            for hour in interaction_times:
                time_range = self._get_time_range(hour)
                time_counts[time_range] = time_counts.get(time_range, 0) + 1
            
            preferred_times = sorted(time_counts.keys(), key=lambda x: time_counts[x], reverse=True)[:2]
            
            # Frecuencia de interacción
            if total_sessions >= 10:
                interaction_frequency = "high"
            elif total_sessions >= 5:
                interaction_frequency = "medium"
            else:
                interaction_frequency = "low"
            
            # Análisis de intenciones (basado en tópicos y nombres de sesión)
            math_queries = len([t for t in topics if any(word in t.lower() for word in ["cálculo", "iva", "matemática"])])
            dte_queries = len([t for t in topics if any(word in t.lower() for word in ["dte", "factura", "sii", "técnica"])])
            general_queries = total_sessions - math_queries - dte_queries
            
            # Última fecha de sesión
            last_session_date = sessions[0].get("created_at") if sessions else None
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": round(avg_messages, 1),
                "common_topics": common_topics,
                "last_session_date": last_session_date,
                "conversation_patterns": {
                    "avg_session_duration": round(avg_duration, 1),
                    "preferred_times": preferred_times,
                    "interaction_frequency": interaction_frequency
                },
                "intent_analysis": {
                    "math_queries": math_queries,
                    "dte_queries": dte_queries,
                    "general_queries": general_queries
                },
                "user_engagement": {
                    "engagement_level": "high" if avg_messages > 8 else "medium" if avg_messages > 4 else "low",
                    "return_user": total_sessions > 1,
                    "power_user": total_sessions > 10 and avg_messages > 6
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced chat analytics: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0, 
                "total_messages": 0,
                "avg_messages_per_session": 0,
                "common_topics": [],
                "error": str(e)
            }
    
    def _get_time_range(self, hour: int) -> str:
        """Convertir hora a rango de tiempo legible"""
        if 6 <= hour < 12:
            return "mañana"
        elif 12 <= hour < 18:
            return "tarde"
        elif 18 <= hour < 22:
            return "noche"
        else:
            return "madrugada"
    
    # === DOCUMENT ANALYSIS ===
    
    async def save_document_analysis(self, analysis: DocumentAnalysis) -> bool:
        """Guardar análisis de documento"""
        try:
            await self.document_analyses.insert_one(analysis.model_dump())
            return True
        except Exception as e:
            logger.error(f"Error saving document analysis: {e}")
            return False
    
    async def get_document_analysis(self, analysis_id: str) -> Optional[DocumentAnalysis]:
        """Obtener análisis por ID"""
        try:
            doc = await self.document_analyses.find_one({"analysis_id": analysis_id})
            if doc:
                return DocumentAnalysis(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting document analysis: {e}")
            return None
    
    async def get_document_analyses_by_document(
        self,
        document_id: str,
        limit: int = 10
    ) -> List[DocumentAnalysis]:
        """Obtener análisis de un documento específico"""
        try:
            cursor = self.document_analyses.find(
                {"document_id": document_id}
            ).sort("created_at", DESCENDING).limit(limit)
            
            analyses = []
            async for doc in cursor:
                analyses.append(DocumentAnalysis(**doc))
            
            return analyses
        except Exception as e:
            logger.error(f"Error getting document analyses: {e}")
            return []
    
    # === AUDIT TRAIL ===
    
    async def log_audit_event(
        self,
        user_id: str,
        action: str,
        resource: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Registrar evento de auditoría"""
        try:
            audit_event = {
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc),
                "ip_address": metadata.get("ip_address") if metadata else None,
                "user_agent": metadata.get("user_agent") if metadata else None
            }
            
            await self.audit_trail.insert_one(audit_event)
            return True
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
            return False
    
    # === PERFILES DE USUARIO Y EMPRESA ===
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Obtener perfil de usuario (simulado por ahora)"""
        try:
            # Por ahora, simular datos de usuario
            # En el futuro, esto se integraría con el backend Node.js
            user_profiles = {
                "user-direct-456": {
                    "name": "Carlos Rodriguez",
                    "email": "carlos@empresa.com",
                    "role": "contador",
                    "preferences": {"detailed_responses": True}
                },
                "test-user-123": {
                    "name": "Ana Martinez",
                    "email": "ana@miempresa.cl",
                    "role": "administrador",
                    "preferences": {"detailed_responses": False}
                }
            }
            
            return user_profiles.get(user_id, {
                "name": "Usuario",
                "email": "usuario@empresa.com",
                "role": "usuario",
                "preferences": {"detailed_responses": True}
            })
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def get_company_profile(self, company_id: str) -> Optional[Dict]:
        """Obtener perfil de empresa (simulado por ahora)"""
        try:
            # Por ahora, simular datos de empresa
            company_profiles = {
                "company-direct-789": {
                    "name": "Empresa Demo S.A.",
                    "rut": "12345678-9",
                    "industry": "servicios",
                    "size": "mediana"
                },
                "test-company-456": {
                    "name": "MiEmpresa Ltda.",
                    "rut": "87654321-0",
                    "industry": "comercio",
                    "size": "pequeña"
                }
            }
            
            return company_profiles.get(company_id, {
                "name": "Tu Empresa",
                "rut": "00000000-0",
                "industry": "general",
                "size": "no_definido"
            })
            
        except Exception as e:
            logger.error(f"Error getting company profile: {e}")
            return None
"""
Servicio de Chat IA Refactorizado - Coordinador principal modular
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from .database_service import DatabaseService
from .postgresql_service import PostgreSQLService
from .message_processor import MessageProcessor
from .context_manager import ContextManager
from .response_generator import ResponseGenerator
from .ollama_client import OllamaClient, OllamaConfig
from .adaptive_learning_service import AdaptiveLearningService
from .prompt_builder import PromptBuilder
try:
    from ..contracts.ai_types import ChatMessage, ChatSession, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatMessage, ChatSession, ChatContext

# Servicios avanzados
try:
    from .long_term_memory_service import LongTermMemoryService
    from .smart_direct_response_service import SmartDirectResponseService
    from .proactive_recommendation_engine import ProactiveRecommendationEngine
    from .sentiment_analysis_service import SentimentAnalysisService
    from .multi_agent_orchestrator import MultiAgentOrchestrator
    from .session_cache_service import SessionCacheService
except ImportError as e:
    logger.warning(f"Servicios avanzados no disponibles: {e}")
    LongTermMemoryService = None
    SmartDirectResponseService = None
    ProactiveRecommendationEngine = None
    SentimentAnalysisService = None
    MultiAgentOrchestrator = None
    SessionCacheService = None

# Nuevos servicios de mejora
try:
    from .data_injection_service import DataInjectionService
    from .response_quality_validator import ResponseQualityValidator
    from .dynamic_personalization_engine import DynamicPersonalizationEngine
    from .intelligent_response_system import IntelligentResponseSystem, ResponseGenerationRequest
    from .conversation_analysis_module import ConversationAnalysisModule
except ImportError as e:
    logger.warning(f"Servicios de mejora no disponibles: {e}")
    DataInjectionService = None
    ResponseQualityValidator = None
    DynamicPersonalizationEngine = None
    IntelligentResponseSystem = None
    ConversationAnalysisModule = None


class ModularChatService:
    """Servicio de chat IA modular y escalable"""
    
    def __init__(self, db: AsyncIOMotorDatabase, ollama_config: Optional[OllamaConfig] = None, postgres_service: Optional[PostgreSQLService] = None):
        print("🔍 DEBUG ModularChatService.__init__ - Iniciando...")
        self.db = db
        print("🔍 DEBUG ModularChatService.__init__ - DB asignada")
        self.ollama_config = ollama_config or OllamaConfig()
        print("🔍 DEBUG ModularChatService.__init__ - OllamaConfig creado")
        self.db_service = DatabaseService(db)
        print("🔍 DEBUG ModularChatService.__init__ - DatabaseService creado")
        self.postgres_service = postgres_service
        print("🔍 DEBUG ModularChatService.__init__ - PostgreSQL service asignado")
        
        # Crear cliente Ollama
        print("🔍 DEBUG ModularChatService.__init__ - Creando OllamaClient...")
        self.ollama_client = OllamaClient(self.ollama_config)
        print("🔍 DEBUG ModularChatService.__init__ - OllamaClient creado")
        
        # Componentes modulares
        print("🔍 DEBUG ModularChatService.__init__ - Creando ContextManager...")
        self.context_manager = ContextManager(db, postgres_service)
        print("🔍 DEBUG ModularChatService.__init__ - ContextManager creado")
        print("🔍 DEBUG ModularChatService.__init__ - Creando MessageProcessor...")
        self.message_processor = MessageProcessor(postgres_service)
        print("🔍 DEBUG ModularChatService.__init__ - MessageProcessor creado")
        print("🔍 DEBUG ModularChatService.__init__ - Creando ResponseGenerator...")
        self.response_generator = ResponseGenerator(
            ollama_client=self.ollama_client,
            context_manager=self.context_manager,
            prompt_builder=PromptBuilder()
        )
        print("🔍 DEBUG ModularChatService.__init__ - ResponseGenerator creado")
        
        # Inicializar AdaptiveLearningService para aprendizaje por usuario
        print("🔍 DEBUG ModularChatService.__init__ - Creando AdaptiveLearningService...")
        try:
            self.adaptive_learning = AdaptiveLearningService(
                postgres_service=self.postgres_service,
                mongodb_service=self.db_service
            )
            print("🔍 DEBUG ModularChatService.__init__ - AdaptiveLearningService creado")
        except Exception as e:
            print(f"❌ Error inicializando AdaptiveLearningService: {e}")
            self.adaptive_learning = None
            
        # Inicializar servicios avanzados
        self._initialize_advanced_services()
        
        # Inicializar nuevos servicios de mejora
        self._initialize_improvement_services()
        
        # Conectar servicios que requieren Redis automáticamente
        asyncio.create_task(self._auto_connect_services())
        
        print("🔍 DEBUG ModularChatService.__init__ - Completado ✅")
        
    def _initialize_advanced_services(self):
        """Inicializar servicios avanzados opcionales"""
        try:
            # Servicio de memoria a largo plazo
            if LongTermMemoryService:
                self.memory_service = LongTermMemoryService()
                print("🧠 LongTermMemoryService inicializado")
                
            # Servicio de respuestas directas
            if SmartDirectResponseService:
                self.direct_response = SmartDirectResponseService(postgres_service=self.postgres_service)
                print("⚡ SmartDirectResponseService inicializado")
                
            # Motor de recomendaciones
            if ProactiveRecommendationEngine:
                self.recommendation_engine = ProactiveRecommendationEngine()
                print("🔮 ProactiveRecommendationEngine inicializado")
                
            # Analizador de sentimientos
            if SentimentAnalysisService:
                self.sentiment_analyzer = SentimentAnalysisService()
                print("🎭 SentimentAnalysisService inicializado")
                
            # Sistema multi-agente
            if MultiAgentOrchestrator:
                self.multi_agent = MultiAgentOrchestrator()
                print("🤖 MultiAgentOrchestrator inicializado")
                
            # Cache de sesiones
            if SessionCacheService:
                self.session_cache = SessionCacheService()
                print("💾 SessionCacheService inicializado")
                
            # Cache de sesiones
            if SessionCacheService:
                self.session_cache = SessionCacheService()
                print("💾 SessionCacheService inicializado")
                
        except Exception as e:
            print(f"⚠️ Error inicializando servicios avanzados: {e}")
            # Los servicios seguirán siendo None si fallan
    
    def _initialize_improvement_services(self):
        """Inicializar nuevos servicios de mejora"""
        try:
            # Sistema inteligente de respuestas (orquestador principal)
            if IntelligentResponseSystem:
                self.intelligent_response_system = IntelligentResponseSystem(
                    postgres_service=self.postgres_service,
                    original_chat_service=self  # Referencia al servicio actual
                )
                print("🎯 IntelligentResponseSystem inicializado")
            else:
                self.intelligent_response_system = None
                
            # Módulo de análisis de conversación
            if ConversationAnalysisModule:
                self.conversation_analyzer = ConversationAnalysisModule()
                print("🧠 ConversationAnalysisModule inicializado")
            else:
                self.conversation_analyzer = None
                
            # Los otros servicios se inicializan dentro del IntelligentResponseSystem
            # para evitar duplicación
                
        except Exception as e:
            print(f"⚠️ Error inicializando servicios de mejora: {e}")
            self.intelligent_response_system = None
            self.conversation_analyzer = None
            
    async def _auto_connect_services(self):
        """Conectar servicios automáticamente en background"""
        try:
            await asyncio.sleep(0.1)  # Pequeño delay para permitir inicialización
            
            if self.memory_service:
                try:
                    await self.memory_service.connect()
                except:
                    pass
                    
            if self.direct_response:
                try:
                    await self.direct_response.connect()
                except:
                    pass
                    
            if self.recommendation_engine:
                try:
                    await self.recommendation_engine.connect()
                except:
                    pass
                    
            if self.sentiment_analyzer:
                try:
                    await self.sentiment_analyzer.connect()
                except:
                    pass
                    
            if self.multi_agent:
                try:
                    await self.multi_agent.connect()
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Error auto-conectando servicios: {e}")
            
    async def _auto_connect_services(self):
        """Conectar servicios automáticamente en background"""
        try:
            await asyncio.sleep(0.1)  # Pequeño delay para permitir inicialización
            
            if self.memory_service:
                try:
                    await self.memory_service.connect()
                except:
                    pass
                    
            if self.direct_response:
                try:
                    await self.direct_response.connect()
                except:
                    pass
                    
            if self.recommendation_engine:
                try:
                    await self.recommendation_engine.connect()
                except:
                    pass
                    
            if self.sentiment_analyzer:
                try:
                    await self.sentiment_analyzer.connect()
                except:
                    pass
                    
            if self.multi_agent:
                try:
                    await self.multi_agent.connect()
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Error auto-conectando servicios: {e}")
            
    async def connect_advanced_services(self):
        """Conectar servicios avanzados a Redis/recursos externos"""
        try:
            if self.memory_service:
                await self.memory_service.connect()
                
            if self.direct_response:
                await self.direct_response.connect()
                
            if self.recommendation_engine:
                await self.recommendation_engine.connect()
                
            if self.sentiment_analyzer:
                await self.sentiment_analyzer.connect()
                
            if self.multi_agent:
                await self.multi_agent.connect()
                
            if self.session_cache:
                await self.session_cache.connect()
                
            logger.info("🚀 Todos los servicios avanzados conectados exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error conectando servicios avanzados: {e}")
            
    async def disconnect_advanced_services(self):
        """Desconectar servicios avanzados"""
        try:
            if self.memory_service:
                await self.memory_service.disconnect()
                
            if self.direct_response:
                await self.direct_response.disconnect()
                
            if self.recommendation_engine:
                await self.recommendation_engine.disconnect()
                
            if self.sentiment_analyzer:
                await self.sentiment_analyzer.disconnect()
                
            if self.multi_agent:
                await self.multi_agent.disconnect()
                
            if self.session_cache:
                await self.session_cache.disconnect()
                
            logger.info("🛑 Todos los servicios avanzados desconectados")
            
        except Exception as e:
            logger.error(f"❌ Error desconectando servicios avanzados: {e}")
            
    async def get_user_recommendations(self, user_id: str, company_id: str) -> List:
        """Obtener recomendaciones proactivas para un usuario"""
        if not self.recommendation_engine:
            return []
            
        try:
            return await self.recommendation_engine.get_active_recommendations(user_id, company_id)
        except Exception as e:
            logger.error(f"❌ Error obteniendo recomendaciones: {e}")
            return []
            
    async def get_advanced_statistics(self, company_id: str) -> Dict[str, Any]:
        """Obtener estadísticas de todos los servicios avanzados"""
        stats = {}
        
        try:
            if self.direct_response:
                stats['direct_response'] = await self.direct_response.get_cache_statistics(company_id)
                
            if self.recommendation_engine:
                stats['recommendations'] = await self.recommendation_engine.get_recommendation_stats(company_id)
                
            if self.sentiment_analyzer:
                stats['sentiment_analysis'] = await self.sentiment_analyzer.get_sentiment_statistics(company_id)
                
            if self.multi_agent:
                stats['multi_agent'] = await self.multi_agent.get_agent_statistics(company_id)
                
            if self.memory_service:
                stats['memory_service'] = await self.memory_service.get_memory_statistics(user_id="all", company_id=company_id)
                
            if self.session_cache:
                stats['session_cache'] = await self.session_cache.get_cache_stats()
                
            if self.session_cache:
                stats['session_cache'] = await self.session_cache.get_cache_stats()
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas avanzadas: {e}")
            stats['error'] = str(e)
            
        return stats
    
    async def create_chat_session(self, user_id: str, company_id: str, metadata: Optional[Dict] = None) -> ChatSession:
        """Crear nueva sesión de chat"""
        try:
            session_id = str(uuid4())
            
            # Crear contexto inicial
            context = ChatContext(
                user_id=user_id,
                company_id=company_id,
                session_preferences={},
                business_context={}
            )
            
            # Crear sesión
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
            
            # Guardar en base de datos
            await self.db_service.create_chat_session(session)
            
            logger.debug(f"🆕 Nueva sesión creada - user_id: {user_id}, company_id: {company_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creando sesión de chat: {e}")
            raise
    
    async def process_message(self, session_id: str, user_message: str, metadata: Optional[Dict] = None) -> ChatMessage:
        """Procesar mensaje del usuario y generar respuesta"""
        try:
            logger.info(f"🔍 DEBUG ModularChatService.process_message - INICIO session_id: {session_id}")
            
            # Obtener sesión usando cache inteligente para evitar timeouts
            logger.info(f"🔍 DEBUG ModularChatService.process_message - Obteniendo sesión...")
            session = None
            
            # 1. Intentar obtener del cache primero (más rápido)
            if self.session_cache:
                try:
                    session = await self.session_cache.get_cached_session(session_id)
                    if session:
                        logger.info(f"⚡ Sesión {session_id} obtenida del cache")
                except Exception as e:
                    logger.warning(f"⚠️ Error obteniendo sesión del cache: {e}")
            
            # 2. Si no está en cache, intentar MongoDB con timeout reducido
            if not session:
                try:
                    session = await asyncio.wait_for(
                        self.db_service.get_chat_session(session_id),
                        timeout=1.5  # Timeout muy corto para evitar bloqueos
                    )
                    if session:
                        logger.info(f"💾 Sesión {session_id} obtenida de MongoDB")
                        # Cachear para próximas consultas
                        if self.session_cache:
                            await self.session_cache.cache_session(session)
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ TIMEOUT MongoDB - usando sesión temporal")
                    session = None
                except Exception as e:
                    logger.warning(f"⚠️ Error MongoDB: {e} - usando sesión temporal")
                    session = None
            
            # 3. Si no hay sesión, crear temporal usando cache service
            if not session:
                logger.info(f"🔍 DEBUG ModularChatService.process_message - Creando sesión temporal...")
                user_id = metadata.get('user_id', 'unknown') if metadata else 'unknown'
                company_id = metadata.get('company_id', 'unknown') if metadata else 'unknown'
                
                if self.session_cache:
                    try:
                        session = await self.session_cache.create_temporary_session(session_id, user_id, company_id)
                        logger.info(f"⚡ Sesión temporal creada con cache: {session.id}")
                    except Exception as e:
                        logger.error(f"❌ Error creando sesión temporal con cache: {e}")
                        session = None
                
                # Fallback manual si el cache falla
                if not session:
                    # Crear contexto temporal
                    context = ChatContext(
                        user_id=user_id,
                        company_id=company_id,
                        session_preferences={},
                        business_context={}
                    )
                    
                    # Crear sesión temporal en memoria
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
                    logger.info(f"🔍 Sesión temporal manual creada: {session.id}")
            
            # Extraer información del contexto
            user_id = session.context.user_id if hasattr(session.context, 'user_id') else session.user_id
            company_id = "unknown"
            
            if hasattr(session, 'context') and session.context:
                if isinstance(session.context, dict):
                    company_id = session.context.get('company_id', company_id)
                else:
                    company_id = getattr(session.context, 'company_id', company_id)
            
            logger.info(f"🔍 DEBUG ModularChatService.process_message - user_id: {user_id}, company_id: {company_id}")
            
            # Obtener contexto enriquecido del usuario
            logger.info(f"🔍 DEBUG ModularChatService.process_message - Obteniendo contexto enriquecido...")
            try:
                user_context = await asyncio.wait_for(
                    self.context_manager.get_enriched_user_context(user_id, company_id, session_id),
                    timeout=8.0
                )
                logger.info(f"🔍 DEBUG ModularChatService.process_message - Contexto obtenido: {len(str(user_context))} chars")
                
                # Análisis adaptativo del usuario (si está disponible)
                if self.adaptive_learning:
                    try:
                        conversation_history = session.messages if hasattr(session, 'messages') else []
                        user_profile = await asyncio.wait_for(
                            self.adaptive_learning.analyze_user_behavior(
                                user_id, company_id, conversation_history
                            ),
                            timeout=3.0
                        )
                        user_context['adaptive_profile'] = user_profile
                        logger.info(f"🧠 Perfil adaptativo - Nivel: {user_profile.technical_level}, Interacciones: {user_profile.interaction_count}")
                    except Exception as e:
                        logger.warning(f"⚠️ Error en análisis adaptativo: {e}")
                        user_context['adaptive_profile'] = None
            except asyncio.TimeoutError:
                logger.warning(f"🔍 DEBUG ModularChatService.process_message - TIMEOUT obteniendo contexto, usando básico")
                user_context = {
                    'user_id': user_id,
                    'company_id': company_id,
                    'has_real_data': True,
                    'business_data': {'total_documents': 0, 'total_clients': 0, 'total_products': 0}
                }
            except Exception as e:
                logger.warning(f"🔍 DEBUG ModularChatService.process_message - Error obteniendo contexto: {e}")
                user_context = {
                    'user_id': user_id,
                    'company_id': company_id,
                    'has_real_data': False,
                    'business_data': {}
                }
            
            # Análisis de sentimientos (nuevo)
            sentiment_analysis = None
            if self.sentiment_analyzer:
                try:
                    # Siempre intentar análisis - el servicio manejará internamente la falta de Redis
                    sentiment_analysis = await asyncio.wait_for(
                        self.sentiment_analyzer.analyze_message_sentiment(user_message, user_id, company_id),
                        timeout=3.0
                    )
                    logger.info(f"🎭 Sentimiento detectado: {sentiment_analysis.sentiment_type.value} "
                              f"(confianza: {sentiment_analysis.confidence_score:.2f})")
                except Exception as e:
                    logger.warning(f"⚠️ Error análisis sentimientos: {e}")
                    # Crear análisis neutral de fallback
                    sentiment_analysis = self.sentiment_analyzer._create_neutral_analysis(user_message, user_id, company_id)
            
            # Detectar intención del mensaje
            message_intent = self.message_processor.detect_intent_advanced(user_message, session.messages)
            
            # Verificar respuesta directa disponible (nuevo)
            direct_response = None
            confidence = 0.0  # Inicializar confidence
            if self.direct_response:
                try:
                    # Intentar obtener respuesta directa con timeout
                    direct_result = await asyncio.wait_for(
                        self.direct_response.get_direct_response(user_message, user_id, company_id),
                        timeout=2.0
                    )
                    if direct_result:
                        direct_response, confidence = direct_result
                        logger.info(f"⚡ Respuesta directa encontrada (confianza: {confidence:.2f})")
                except Exception as e:
                    logger.warning(f"⚠️ Error respuesta directa: {e}")
                    
            # Verificar si agentes especializados pueden manejar mejor la consulta (nuevo)
            agent_response = None
            if self.multi_agent and not direct_response:
                try:
                    # Los agentes funcionan sin Redis para lógica especializada
                    agent_result = await asyncio.wait_for(
                        self.multi_agent.route_query(user_message, user_id, company_id),
                        timeout=5.0
                    )
                    if agent_result:
                        agent_response = agent_result
                        logger.info(f"🤖 Respuesta de agente especializado obtenida")
                except Exception as e:
                    logger.warning(f"⚠️ Error sistema multi-agente: {e}")
            
            # Crear mensaje del usuario
            user_msg = ChatMessage(
                id=str(uuid4()),
                session_id=session_id,
                role="user",
                content=user_message,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # NUEVA LÓGICA: Priorizar respuesta directa de alta calidad sobre sistema inteligente
            if direct_response and confidence and confidence >= 0.90:
                # Usar respuesta directa inmediatamente si tiene alta confianza
                from types import SimpleNamespace
                ai_response = SimpleNamespace()
                ai_response.content = direct_response
                ai_response.model = "smart_direct_cache_priority"
                ai_response.total_duration = 0
                ai_response.eval_count = 0 
                ai_response.prompt_eval_count = 0
                response_source = "direct_response_high_confidence"
                logger.info(f"⚡ PRIORITY: Usando respuesta directa de alta confianza ({confidence:.2f}) - saltando sistema inteligente")
            
            # Usar sistema inteligente solo si no hay respuesta directa de alta calidad
            elif self.intelligent_response_system:
                try:
                    # Crear request para el sistema inteligente
                    intelligent_request = ResponseGenerationRequest(
                        user_query=user_message,
                        user_id=user_id,
                        company_id=company_id,
                        session_id=session_id,
                        context_type=message_intent,
                        additional_context=user_context,
                        quality_threshold=60.0,  # Threshold más realista
                        max_regeneration_attempts=3  # Más intentos
                    )
                    
                    # Generar respuesta inteligente
                    intelligent_response = await self.intelligent_response_system.generate_intelligent_response(
                        intelligent_request
                    )
                    
                    from types import SimpleNamespace
                    ai_response = SimpleNamespace()
                    ai_response.content = intelligent_response.response_text
                    ai_response.model = f"intelligent_system_{intelligent_response.generation_method}"
                    ai_response.total_duration = 0
                    ai_response.eval_count = 0
                    ai_response.prompt_eval_count = 0
                    response_source = f"intelligent_system"
                    
                    logger.info(f"🎯 Respuesta inteligente generada - Calidad: {intelligent_response.quality_score:.1f}/100 "
                              f"({intelligent_response.quality_level.value}) en {intelligent_response.attempts_used} intentos")
                    
                    # Análisis de conversación si está disponible
                    if self.conversation_analyzer:
                        try:
                            conversation_analysis = await self.conversation_analyzer.analyze_conversation_turn(
                                user_message, user_id, company_id, session_id, 
                                ai_response.content, user_context
                            )
                            logger.info(f"🧠 Conversación analizada - Tópico: {conversation_analysis.get('message_analysis', {}).get('topic', 'N/A')}")
                        except Exception as conv_error:
                            logger.warning(f"⚠️ Error en análisis de conversación: {conv_error}")
                    
                except Exception as intel_error:
                    logger.warning(f"⚠️ Error en sistema inteligente, usando lógica tradicional: {intel_error}")
                    ai_response = None
                    response_source = "fallback_traditional"
            else:
                ai_response = None
                response_source = "traditional_system"
            
            # Fallback: Lógica tradicional si el sistema inteligente no está disponible o falla
            if not ai_response:
                # 1. Respuesta directa (mayor prioridad para respuestas conocidas) - Solo si no se usó ya
                if direct_response and response_source != "direct_response_high_confidence":
                    from types import SimpleNamespace
                    ai_response = SimpleNamespace()
                    ai_response.content = direct_response
                    ai_response.model = "smart_direct_cache_fallback"
                    ai_response.total_duration = 0
                    ai_response.eval_count = 0 
                    ai_response.prompt_eval_count = 0
                    response_source = "direct_response_fallback"
                    logger.info(f"⚡ FALLBACK: Usando respuesta directa (confianza: {confidence:.2f})")
                    
                # 2. Agente especializado (segunda prioridad para temas específicos)
                elif agent_response:
                    from types import SimpleNamespace
                    ai_response = SimpleNamespace()
                    ai_response.content = agent_response
                    ai_response.model = "specialized_agent"
                    ai_response.total_duration = 0
                    ai_response.eval_count = 0
                    ai_response.prompt_eval_count = 0
                    response_source = "specialized_agent"
                    logger.info(f"🤖 Usando agente especializado")
                    
                # 3. Consulta empresarial directa (tercera prioridad para datos estructurados)
                elif message_intent == "business_query" and self.postgres_service and user_context.get("has_real_data"):
                    try:
                        # Usar user_id real proporcionado como parámetro
                        real_user_id = user_id
                        business_response = await self.message_processor.process_business_query(
                            user_message, real_user_id, company_id
                        )
                        
                        from types import SimpleNamespace
                        ai_response = SimpleNamespace()
                        ai_response.content = business_response
                        ai_response.model = "postgresql_direct"
                        ai_response.total_duration = 0
                        ai_response.eval_count = 0
                        ai_response.prompt_eval_count = 0
                        response_source = "business_direct"
                        logger.info(f"📊 Usando consulta empresarial directa")
                        
                    except Exception as business_error:
                        logger.error(f"Error en consulta empresarial directa: {business_error}")
                        ai_response = None
                
                # 4. IA con aprendizaje adaptativo (fallback predeterminado)
                if not ai_response:
                    ai_response = await self.response_generator.generate_adaptive_response(
                        session, user_message, user_context, message_intent, user_context.get('adaptive_profile')
                    )
                    response_source = "adaptive_ai"
                    logger.info(f"🧠 Usando IA adaptativa")
            
            # Post-procesamiento: Solo si no se usó el sistema inteligente 
            if response_source.startswith("intelligent_system"):
                # El sistema inteligente ya aplica todas las mejoras
                final_content = ai_response.content
                enhanced_content = ai_response.content  # Para compatibilidad con tono
                logger.info("🎯 Sistema inteligente usado - Post-procesamiento omitido")
            else:
                # Aplicar post-procesamiento tradicional para respuestas legacy
                try:
                    enhanced_content = await asyncio.wait_for(
                        self.response_generator.apply_dynamic_precision_enhancement(
                            ai_response.content, user_context, message_intent, user_message
                        ),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Timeout en post-procesamiento, usando respuesta original")
                    enhanced_content = ai_response.content
                except Exception as e:
                    logger.error(f"❌ Error en post-procesamiento: {e}, usando respuesta original")
                    enhanced_content = ai_response.content
                
                # Aplicar adaptación de tono basada en sentimientos (nuevo)
                final_content = enhanced_content
            
            # Aplicar adaptación de tono si está disponible
            if self.sentiment_analyzer and sentiment_analysis:
                try:
                    final_content = await self.sentiment_analyzer.adapt_response_tone(
                        enhanced_content, sentiment_analysis
                    )
                    logger.info(f"🎭 Tono adaptado según sentimiento: {sentiment_analysis.sentiment_type.value}")
                except Exception as e:
                    logger.warning(f"⚠️ Error adaptando tono: {e}")
                    
            # Actualizar motor de recomendaciones con comportamiento del usuario (nuevo)
            if self.recommendation_engine:
                try:
                    session_duration = metadata.get('session_duration', 0.0) if metadata else 0.0
                    satisfaction_score = None
                    
                    # Calcular satisfacción basada en sentimiento
                    if sentiment_analysis:
                        sentiment_to_satisfaction = {
                            "very_positive": 5.0,
                            "positive": 4.0, 
                            "neutral": 3.0,
                            "negative": 2.0,
                            "very_negative": 1.0
                        }
                        satisfaction_score = sentiment_to_satisfaction.get(
                            sentiment_analysis.sentiment_type.value, 3.0
                        )
                    
                    await asyncio.wait_for(
                        self.recommendation_engine.update_user_behavior(
                            user_id, company_id, user_message, response_source, 
                            session_duration, satisfaction_score
                        ),
                        timeout=2.0
                    )
                    logger.info(f"🔮 Comportamiento actualizado en motor de recomendaciones")
                except Exception as e:
                    logger.warning(f"⚠️ Error actualizando recomendaciones: {e}")
                    
            # Cachear respuesta de calidad para uso futuro (nuevo)
            if self.direct_response and response_source == "adaptive_ai":
                try:
                    # Calcular calidad de respuesta
                    quality_score = 0.7  # Base
                    if sentiment_analysis:
                        if sentiment_analysis.sentiment_type.value in ["positive", "very_positive"]:
                            quality_score += 0.2
                    if user_context.get('adaptive_profile'):
                        quality_score += 0.1
                        
                    await asyncio.wait_for(
                        self.direct_response.cache_ai_response(
                            user_message, final_content, user_id, company_id, quality_score
                        ),
                        timeout=2.0
                    )
                    logger.info(f"💾 Respuesta cacheada con calidad: {quality_score:.2f}")
                except Exception as e:
                    logger.warning(f"⚠️ Error cacheando respuesta: {e}")
                    
            # Actualizar memoria a largo plazo (nuevo)
            if self.memory_service:
                try:
                    await asyncio.wait_for(
                        self.memory_service.store_interaction(
                            user_id, company_id, user_message, final_content,
                            sentiment_analysis.sentiment_type if sentiment_analysis else None,
                            response_source
                        ),
                        timeout=2.0
                    )
                    logger.info(f"🧠 Interacción almacenada en memoria a largo plazo")
                except Exception as e:
                    logger.warning(f"⚠️ Error actualizando memoria: {e}")
            
            # Crear mensaje de respuesta
            assistant_msg = ChatMessage(
                id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content=final_content,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "model": getattr(ai_response, 'model', 'unknown'),
                    "intent": message_intent,
                    "processing_type": "direct" if hasattr(ai_response, 'model') and ai_response.model == "postgresql_direct" else "ai_enhanced",
                    "response_source": response_source,
                    "sentiment_detected": sentiment_analysis.sentiment_type.value if sentiment_analysis else None,
                    "sentiment_confidence": sentiment_analysis.confidence_score if sentiment_analysis else None,
                    "tone_adapted": sentiment_analysis is not None and self.sentiment_analyzer is not None,
                    "services_enabled_count": sum([
                        self.direct_response is not None,
                        self.multi_agent is not None,
                        self.sentiment_analyzer is not None,
                        self.recommendation_engine is not None,
                        self.memory_service is not None
                    ]),
                    "total_duration": getattr(ai_response, 'total_duration', 0),
                    "eval_count": getattr(ai_response, 'eval_count', 0),
                    "prompt_eval_count": getattr(ai_response, 'prompt_eval_count', 0)
                }
            )
            
            # Guardar mensajes en la sesión con timeouts
            try:
                # Intentar guardar mensajes con timeout reducido - no bloquear si falla
                mongodb_success = True
                
                try:
                    await asyncio.wait_for(
                        self.db_service.add_message_to_session(session_id, user_msg),
                        timeout=2.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Timeout guardando mensaje usuario - continuando")
                    mongodb_success = False
                
                try:
                    await asyncio.wait_for(
                        self.db_service.add_message_to_session(session_id, assistant_msg),
                        timeout=2.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Timeout guardando mensaje asistente - continuando")
                    mongodb_success = False
                    
                # Actualizar timestamp de la sesión (opcional)
                try:
                    await asyncio.wait_for(
                        self.db_service.update_session_timestamp(session_id),
                        timeout=1.0
                    )
                except (asyncio.TimeoutError, Exception):
                    pass  # No es crítico si falla
                
                # Actualizar cache con los nuevos mensajes
                if self.session_cache:
                    try:
                        # Añadir mensajes a la sesión y actualizar cache
                        if hasattr(session, 'messages'):
                            if not session.messages:
                                session.messages = []
                            session.messages.extend([user_msg, assistant_msg])
                            session.message_count = len(session.messages)
                            session.last_activity = datetime.now(timezone.utc)
                        
                        await self.session_cache.cache_session(session)
                        logger.debug(f"💾 Cache de sesión actualizado")
                    except Exception as e:
                        logger.warning(f"⚠️ Error actualizando cache de sesión: {e}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout al guardar mensajes en MongoDB (3s) - continuando sin bloqueo")
                # No bloquear el flujo por timeout de MongoDB
                pass
            except Exception as e:
                logger.error(f"❌ Error al guardar mensajes en MongoDB: {e}")
                # No bloquear por errores de guardado
                pass
            
            # Registrar calidad para aprendizaje futuro
            try:
                if hasattr(ai_response, 'quality_score') and ai_response.quality_score:
                    await asyncio.wait_for(
                        self.adaptive_learning.record_response_quality(
                            user_id, company_id, float(ai_response.quality_score)
                        ),
                        timeout=2.0
                    )
                    logger.info(f"📊 Calidad registrada: {ai_response.quality_score}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout al registrar calidad de respuesta")
            except Exception as e:
                logger.error(f"❌ Error al registrar calidad: {e}")
            
            logger.info(f"✅ Mensaje procesado para sesión {session_id} con intención '{message_intent}'")
            return assistant_msg
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            
            # Crear mensaje de error
            error_msg = ChatMessage(
                id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content="Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta nuevamente.",
                timestamp=datetime.now(timezone.utc),
                metadata={"error": str(e)}
            )
            
            try:
                await self.db_service.add_message_to_session(session_id, error_msg)
            except:
                pass  # No fallar si no se puede guardar el mensaje de error
            
            return error_msg
    
    async def get_session_history(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Obtener historial de mensajes de una sesión"""
        try:
            session = await self.db_service.get_chat_session(session_id)
            if not session:
                return []
            
            messages = session.messages or []
            
            if limit:
                messages = messages[-limit:]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error obteniendo historial de sesión {session_id}: {e}")
            return []
    
    async def end_chat_session(self, session_id: str) -> bool:
        """Finalizar sesión de chat"""
        try:
            success = await self.db_service.end_chat_session(session_id)
            
            if success:
                # Limpiar cache del contexto
                session = await self.db_service.get_chat_session(session_id)
                if session and hasattr(session, 'user_id'):
                    self.context_manager.clear_cache(session.user_id)
                
                logger.info(f"Sesión {session_id} finalizada correctamente")
            
            return success
            
        except Exception as e:
            logger.error(f"Error finalizando sesión {session_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str, company_id: str, active_only: bool = True, limit: int = 10) -> List[ChatSession]:
        """Obtener sesiones de chat de un usuario"""
        try:
            sessions = await self.db_service.get_user_chat_sessions(
                user_id, company_id, active_only, limit
            )
            return sessions
            
        except Exception as e:
            logger.error(f"Error obteniendo sesiones del usuario {user_id}: {e}")
            return []
    
    async def clear_context_cache(self, user_id: str = None):
        """Limpiar cache de contexto"""
        self.context_manager.clear_cache(user_id)
        logger.info(f"Cache de contexto limpiado para usuario {user_id or 'todos'}")
    
    async def get_system_stats(self) -> Dict:
        """Obtener estadísticas del sistema"""
        try:
            cache_stats = self.context_manager.get_cache_stats()
            
            # Estadísticas adicionales podrían agregarse aquí
            stats = {
                "cache": cache_stats,
                "components": {
                    "context_manager": "active",
                    "message_processor": "active", 
                    "response_generator": "active",
                    "database_service": "active"
                },
                "postgres_connection": "connected" if self.postgres_service else "not_connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {"error": str(e)}
    
    async def search_conversations(self, user_id: str, query: str, company_id: str = None, limit: int = 10) -> List[ChatMessage]:
        """Buscar en conversaciones del usuario"""
        try:
            # Obtener sesiones del usuario
            sessions = await self.get_user_sessions(user_id, company_id or "unknown", active_only=False, limit=50)
            
            matching_messages = []
            query_lower = query.lower()
            
            for session in sessions:
                for message in session.messages:
                    if query_lower in message.content.lower():
                        matching_messages.append(message)
                        if len(matching_messages) >= limit:
                            return matching_messages
            
            return matching_messages
            
        except Exception as e:
            logger.error(f"Error buscando conversaciones: {e}")
            return []
    
    async def get_chat_analytics(self, user_id: str, company_id: str, days: int = 30) -> Dict:
        """Obtener analíticas básicas de chat"""
        try:
            sessions = await self.get_user_sessions(user_id, company_id, active_only=False, limit=100)
            
            total_sessions = len(sessions)
            total_messages = sum(len(session.messages) for session in sessions)
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
                "active_sessions": len([s for s in sessions if s.is_active]),
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo analíticas: {e}")
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "avg_messages_per_session": 0,
                "active_sessions": 0,
                "period_days": days
            }
    
    async def search_conversations(self, user_id: str, company_id: str, query: str = "", limit: int = 20) -> List[ChatSession]:
        """Buscar conversaciones por contenido"""
        try:
            # Implementación simplificada usando las sesiones del usuario
            sessions = await self.get_user_sessions(user_id, company_id, active_only=False, limit=limit)
            
            if not query:
                return sessions
            
            # Filtrar por contenido si hay query
            filtered_sessions = []
            query_lower = query.lower()
            
            for session in sessions:
                # Buscar en los mensajes de la sesión
                for message in (session.messages or []):
                    if hasattr(message, 'content') and query_lower in message.content.lower():
                        filtered_sessions.append(session)
                        break
            
            return filtered_sessions[:limit]
            
        except Exception as e:
            logger.error(f"Error buscando conversaciones: {e}")
            return []
    
    async def get_chat_analytics(self, user_id: str, company_id: str) -> Dict:
        """Obtener análisis de conversaciones"""
        try:
            sessions = await self.get_user_sessions(user_id, company_id, active_only=False, limit=100)
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "total_messages": 0,
                    "avg_messages_per_session": 0,
                    "most_active_day": "N/A",
                    "communication_style": {"formal": 50, "friendly": 50}
                }
            
            # Análisis básico
            total_sessions = len(sessions)
            total_messages = sum(len(s.messages or []) for s in sessions)
            avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
            
            # Análisis temporal simple
            from collections import Counter
            dates = [s.created_at.strftime("%Y-%m-%d") for s in sessions if hasattr(s, 'created_at')]
            most_active_day = Counter(dates).most_common(1)[0][0] if dates else "N/A"
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": round(avg_messages, 2),
                "most_active_day": most_active_day,
                "communication_style": {"formal": 60, "friendly": 40}  # Estimación simplificada
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de chat: {e}")
            return {"error": str(e)}
    
    async def list_user_sessions(self, user_id: str, company_id: str, limit: int = 50) -> List[ChatSession]:
        """Listar sesiones del usuario (alias para compatibilidad)"""
        return await self.get_user_sessions(user_id, company_id, active_only=False, limit=limit)
    
    async def close_session(self, session_id: str, user_id: str) -> bool:
        """Cerrar sesión (alias para compatibilidad)"""
        return await self.end_chat_session(session_id)
    
    # Métodos de compatibilidad con la API existente
    async def create_session(self, user_id: str, company_id: str, metadata: Optional[Dict] = None) -> ChatSession:
        """Alias para compatibilidad"""
        return await self.create_chat_session(user_id, company_id, metadata)
    
    async def send_message(self, session_id: str, message: str, metadata: Optional[Dict] = None) -> ChatMessage:
        """Alias para compatibilidad"""
        return await self.process_message(session_id, message, metadata)
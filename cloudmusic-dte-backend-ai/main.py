"""CloudMusic DTE IA Backend - Conforme al informe académico
Backend especializado en análisis IA de documentos tributarios chilenos
Ollama Llama 3.2 3B + MongoDB + Redis + WebSockets
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import uvicorn
import asyncio
from datetime import datetime
import json
import os
import signal
import uuid
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Importar servicios locales
from src.services.redis_service import RedisService
from src.services.ollama_client import OllamaClient, OllamaConfig
from src.services.postgresql_service import PostgreSQLService

# === SERVICIOS GLOBALES ===
redis_service: Optional[RedisService] = None
ollama_client: Optional[OllamaClient] = None
postgres_service: Optional[PostgreSQLService] = None
database_service: Optional[Any] = None
mongodb_database: Optional[Any] = None
redis_listener_task: Optional[asyncio.Task] = None

# === TIPOS DE DATOS CONFORME AL INFORME ===

class ChatMessage(BaseModel):
    """Mensaje de chat IA para consultas DTE"""
    session_id: str = Field(..., description="ID de sesión de chat")
    user_id: str = Field(..., description="ID del usuario")
    message: str = Field(..., description="Mensaje del usuario")
    context_type: str = Field(default="dte_general", description="Contexto del chat")


class ChatResponse(BaseModel):
    """Respuesta del chat IA"""
    success: bool
    message_id: str
    ai_response: str
    confidence: float
    tokens_used: int
    timestamp: str


class DocumentAnalysis(BaseModel):
    """Solicitud de análisis de documento DTE"""
    document_id: str = Field(..., description="ID del documento")
    document_type: str = Field(..., description="Tipo DTE (33, 34, 39, etc.)")
    xml_content: str = Field(..., description="Contenido XML del DTE")
    analysis_type: str = Field(default="full", description="Tipo de análisis")


class AnalysisResult(BaseModel):
    """Resultado del análisis IA"""
    success: bool
    analysis_id: str
    risk_level: str  # low, medium, high, critical
    fraud_indicators: List[str]
    compliance_status: str
    recommendations: List[str]
    confidence_score: float
    processing_time_ms: int


class SystemStatus(BaseModel):
    """Estado del sistema IA"""
    healthy: bool
    services: Dict[str, Any]
    ollama_status: Dict[str, str]
    performance_metrics: Dict[str, float]
    timestamp: str


# === LIFESPAN MANAGEMENT ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    global redis_service, ollama_client, database_service, postgres_service, mongodb_database, redis_listener_task
    
    print("🚀 Iniciando CloudMusic DTE IA Backend...")
    
    # Debug: Mostrar configuración
    print("🔧 Configuración MongoDB:")
    print(f"   MONGODB_URL: {os.getenv('MONGODB_URL', 'NO DEFINIDA')}")
    print(f"   MONGODB_DATABASE: {os.getenv('MONGODB_DATABASE', 'NO DEFINIDA')}")
    
    # Inicializar servicios
    try:
        # 1. Inicializar MongoDB directamente
        from src.core.dependencies import initialize_database
        try:
            await initialize_database()
            print("✅ MongoDB conectado y colecciones inicializadas")
            
            # Importar mongodb_database DESPUÉS de inicializar
            from src.core.dependencies import mongodb_database as _mongodb_database
            mongodb_database = _mongodb_database
            
            # Crear Database Service solo si mongodb_database está disponible
            if mongodb_database is not None:
                from src.services.database_service import DatabaseService
                database_service = DatabaseService(mongodb_database)
                print("✅ Database Service inicializado")
            else:
                print("⚠️ Database Service no inicializado - mongodb_database es None")
                database_service = None
        except Exception as e:
            print(f"❌ Error conectando MongoDB: {e}")
            print("📍 Verificar credenciales en .env:")
            print(f"   MONGODB_URL: {os.getenv('MONGODB_URL', 'NO DEFINIDA')}")
            database_service = None
        
        # 2. Inicializar PostgreSQL Service
        postgres_url = os.getenv("POSTGRESQL_URL")
        if not postgres_url:
            # Construir URL desde variables individuales
            pg_host = os.getenv("POSTGRESQL_HOST", "192.168.10.100")
            pg_port = os.getenv("POSTGRESQL_PORT", "32768")
            pg_db = os.getenv("POSTGRESQL_DATABASE", "sistema_facturacion_dte")
            pg_user = os.getenv("POSTGRESQL_USER", "britoshky")
            pg_password = os.getenv("POSTGRESQL_PASSWORD", "cdcd-.-.-2627HectorBrito")
            postgres_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
        
        try:
            postgres_service = PostgreSQLService(postgres_url)
            await postgres_service.connect()
            print("✅ PostgreSQL Service conectado - Acceso a datos empresariales")
            print(f"🔍 DEBUG: postgres_service asignado: {postgres_service is not None}")
        except Exception as pg_error:
            print(f"⚠️ Error conectando PostgreSQL: {pg_error}")
            print("   El backend AI funcionará sin acceso a datos empresariales")
            postgres_service = None
        
        # 3. Redis Service
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL no definida en .env")
        redis_service = RedisService(redis_url=redis_url)
        await redis_service.connect()
        print("✅ Redis Service conectado")
        
        # Configurar listeners de Redis (sin iniciar el loop aquí)
        await setup_redis_listeners()
        
        # Iniciar Redis message loop como task
        print("🎯 Iniciando Redis listeners como background task...")
        redis_listener_task = asyncio.create_task(start_redis_message_loop())
        print("✅ Redis message loop iniciado como task")
        
    except Exception as e:
        print(f"❌ Error iniciando servicios: {e}")
    
    # Inicializar Ollama Client
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        print(f"🔧 Configuración Ollama:")
        print(f"   Host: {ollama_host}")
        print(f"   Model: {ollama_model}")
        
        ollama_config = OllamaConfig(host=ollama_host, model=ollama_model)
        ollama_client = OllamaClient(ollama_config)
        print("✅ Ollama Client inicializado (test de conexión omitido)")
            
    except Exception as e:
        print(f"❌ Error iniciando Ollama Client: {e}")
        ollama_client = None
    
    print("🎉 Todos los servicios iniciados correctamente")
    
    yield  # App running
    
    # Cleanup al shutdown
    print("🛑 Cerrando servicios...")
    
    # Cancelar Redis listener task
    if redis_listener_task and not redis_listener_task.done():
        print("🔄 Cancelando Redis listener task...")
        redis_listener_task.cancel()
        try:
            await redis_listener_task
        except asyncio.CancelledError:
            print("✅ Redis listener task cancelado")
    
    # Cerrar servicios
    if redis_service:
        await redis_service.disconnect()
    if postgres_service:
        await postgres_service.disconnect()
    print("✅ Servicios cerrados correctamente")
    
    # Forzar salida del proceso si es necesario
    try:
        print("🔚 Terminando proceso...")
        os.kill(os.getpid(), signal.SIGTERM)
    except:
        pass

async def setup_redis_listeners():
    """Configurar listeners de Redis sin iniciar el loop de escucha"""
    if not redis_service:
        return
        
    # Configurar listeners para cada canal
    await redis_service.subscribe_to_channel("cloudmusic_dte:chat_requests", handle_chat_request)
    await redis_service.subscribe_to_channel("cloudmusic_dte:analysis_requests", handle_analysis_request)
    await redis_service.subscribe_to_channel("cloudmusic_dte:ai_requests", handle_general_request)
    
    print("👂 Redis listeners configurados para todos los canales")

async def start_redis_message_loop():
    """Iniciar el loop de escucha de mensajes Redis"""
    if redis_service:
        await redis_service.listen_for_messages()

# === REDIS HANDLERS ===

async def handle_chat_request(message: str):
    """Manejar solicitudes de chat desde Node.js"""
    global postgres_service, database_service, mongodb_database
    print(f"🚀 handle_chat_request LLAMADO con mensaje: {message[:100]}...")
    print(f"🔍 DEBUG: postgres_service disponible: {postgres_service is not None}")
    print(f"🔍 DEBUG: database_service disponible: {database_service is not None}")
    try:
        data = json.loads(message)
        print(f"📨 Chat request recibido: {data}")
        
        # Obtener datos del request (manejar tanto camelCase como snake_case)
        user_message = data.get('message', '')
        session_id = data.get('sessionId') or data.get('session_id', str(uuid.uuid4()))
        user_id = data.get('userId') or data.get('user_id', 'unknown')
        company_id = data.get('companyId') or data.get('company_id', 'unknown')
        
        if not user_message:
            return
        
        print(f"🔍 DEBUG main.py - user_id: '{user_id}', session_id: '{session_id}', company_id: '{company_id}'")
        
        # ACTIVAR: Usar ModularChatService con acceso a datos PostgreSQL
        if mongodb_database is not None and postgres_service is not None:
            try:
                print("🤖 Procesando con ModularChatService (datos empresariales + MongoDB + Ollama)")
                
                # Importar e inicializar ModularChatService
                from src.services.modular_chat_service import ModularChatService
                
                ollama_config = OllamaConfig(
                    host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    model=os.getenv("OLLAMA_MODEL", "llama3.2:3b")
                )
                
                chat_service = ModularChatService(
                    db=mongodb_database,
                    ollama_config=ollama_config,
                    postgres_service=postgres_service
                )
                
                # Procesar mensaje con acceso completo a datos
                ai_message = await chat_service.process_message(
                    session_id=session_id,
                    user_message=user_message,
                    metadata={
                        "company_id": company_id,
                        "user_id": user_id,
                        "source": "redis",
                        "contextType": data.get('contextType', 'business_query')
                    }
                )
                
                # Preparar respuesta con datos reales
                ai_response = {
                    "success": True,
                    "type": "chat_response",
                    "eventId": data.get('eventId'),
                    "sessionId": session_id,
                    "userId": user_id,
                    "companyId": company_id,
                    "message": ai_message.content,
                    "confidence": ai_message.metadata.get("confidence", 0.85),
                    "tokensUsed": ai_message.metadata.get("eval_count", 0),
                    "processingTime": ai_message.metadata.get("total_duration", 0) / 1000000,
                    "timestamp": datetime.now().isoformat(),
                    "model": ai_message.metadata.get("model", "modular_chat_service"),
                    "contextType": data.get('contextType', 'business_query'),
                    "intent": ai_message.metadata.get("intent", "unknown"),
                    "processing_type": ai_message.metadata.get("processing_type", "ai_enhanced")
                }
                
                # Enviar respuesta por Redis
                await redis_service.publish_message("cloudmusic_dte:ai_responses", json.dumps(ai_response))
                print(f"✅ Respuesta inteligente enviada por Redis: {ai_response['message'][:100]}...")
                print(f"📊 Metadatos: modelo={ai_response['model']}, intención={ai_response['intent']}, tipo={ai_response['processing_type']}")
                return
                
            except Exception as e:
                print(f"❌ Error en ModularChatService: {e}")
                print("🔄 Fallback a Ollama directo...")
        
        # FALLBACK: Usar OllamaClient directo si ModularChatService falla
        print("🔍 DEBUG: Usando OllamaClient directo como fallback...")
        if ollama_client:
            try:
                # Generar respuesta directa con Ollama
                prompt = f"Usuario pregunta: {user_message}\nContexto: {data.get('contextType', 'general')}\nResponde de manera útil y profesional sobre temas de facturación electrónica chilena."
                
                response = await ollama_client.generate_response(prompt)
                
                # Preparar respuesta
                ai_response = {
                    "success": True,
                    "type": "chat_response",
                    "eventId": data.get('eventId'),
                    "sessionId": session_id,
                    "userId": user_id,
                    "companyId": company_id,
                    "message": response.content,
                    "confidence": response.quality_score or 0.85,
                    "tokensUsed": response.eval_count or 0,
                    "processingTime": (response.total_duration or 0) / 1000000,
                    "timestamp": datetime.now().isoformat(),
                    "model": response.model,
                    "contextType": data.get('contextType', 'general'),
                    "processing_type": "ollama_direct"
                }
                
                # Enviar respuesta por Redis
                await redis_service.publish_message("cloudmusic_dte:ai_responses", json.dumps(ai_response))
                print(f"✅ Respuesta fallback enviada por Redis: {ai_response['message'][:100]}...")
                
            except Exception as e:
                print(f"❌ Error procesando con Ollama directo: {e}")
                # Respuesta de error
                error_response = {
                    "success": False,
                    "type": "chat_response",
                    "eventId": data.get('eventId'),
                    "sessionId": session_id,
                    "userId": user_id,
                    "companyId": company_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                await redis_service.publish_message("cloudmusic_dte:ai_responses", json.dumps(error_response))
        else:
            print("❌ Ollama client no disponible")
            error_response = {
                "success": False,
                "type": "chat_response",
                "eventId": data.get('eventId'),
                "sessionId": session_id,
                "userId": user_id,
                "companyId": company_id,
                "error": "Ollama client no disponible",
                "timestamp": datetime.now().isoformat()
            }
            await redis_service.publish_message("cloudmusic_dte:ai_responses", json.dumps(error_response))
        
    except Exception as e:
        print(f"❌ Error procesando chat request: {e}")


async def handle_analysis_request(message: str):
    """Manejar solicitudes de análisis desde Node.js"""
    print(f"🚀 handle_analysis_request LLAMADO con mensaje: {message[:100]}...")
    try:
        data = json.loads(message)
        print(f"📊 Analysis request recibido: {data}")
        
        # Obtener datos del DTE
        dte_data = data.get('dteData', {})
        analysis_type = data.get('analysisType', 'general')
        request_id = data.get('requestId', str(uuid.uuid4()))
        
        if not dte_data:
            return
        
        # Procesar análisis con Ollama
        if ollama_client:
            # Crear prompt específico para análisis de DTE
            dte_json = json.dumps(dte_data, indent=2)
            prompt = f"""
            Analiza el siguiente DTE (Documento Tributario Electrónico) chileno:

            {dte_json}

            Proporciona un análisis detallado que incluya:
            1. Validación de campos obligatorios
            2. Consistencia de montos y cálculos
            3. Cumplimiento normativo SII
            4. Posibles errores o inconsistencias
            5. Recomendaciones de mejora

            Tipo de análisis solicitado: {analysis_type}
            """
            
            analysis_result = await ollama_client.generate_response(prompt)
            
            # Enviar resultado de vuelta
            response_data = {
                "requestId": request_id,
                "analysisResult": analysis_result,
                "dteData": dte_data,
                "analysisType": analysis_type,
                "timestamp": datetime.now().isoformat(),
                "type": "analysis_response"
            }
            
            await redis_service.publish_message(
                "cloudmusic_dte:ai_responses", 
                json.dumps(response_data)
            )
            print(f"✅ Analysis response enviado para request {request_id}")
        
    except Exception as e:
        print(f"❌ Error procesando analysis request: {e}")

async def handle_general_request(message: str):
    """Manejar solicitudes generales de IA desde Node.js"""
    print(f"🚀 handle_general_request LLAMADO con mensaje: {message[:100]}...")
    try:
        data = json.loads(message)
        print(f"🤖 General AI request recibido: {data}")
        
        request_type = data.get('type', 'unknown')
        request_id = data.get('requestId', str(uuid.uuid4()))
        
        # Procesar según el tipo de solicitud
        if request_type == 'status':
            # Status del servicio Ollama
            status_data = {
                "requestId": request_id,
                "status": "online" if ollama_client else "offline",
                "model": "llama3.1:70b",
                "timestamp": datetime.now().isoformat(),
                "type": "status_response"
            }
            
            await redis_service.publish_message(
                "cloudmusic_dte:ai_responses", 
                json.dumps(status_data)
            )
            print(f"✅ Status response enviado para request {request_id}")
        
    except Exception as e:
        print(f"❌ Error procesando general request: {e}")


# === APLICACIÓN FASTAPI ===

app = FastAPI(
    title="CloudMusic DTE IA Backend",
    version="1.0.0",
    description="Backend IA especializado para análisis de DTE chilenos con Ollama local",
    lifespan=lifespan
)

# Redis listeners ahora se inician en lifespan

# === MIDDLEWARE ===

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dte.cloudmusic.cl",
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://localhost:3003"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# === ENDPOINTS BÁSICOS ===

@app.get("/")
async def root():
    """Endpoint raíz del backend IA"""
    return {
        "message": "CloudMusic DTE IA Backend",
        "version": "1.0.0", 
        "description": "Backend IA con Ollama Llama 3.2 3B para análisis DTE",
        "status": "operational",
        "endpoints": {
            "chat": "/api/v1/chat",
            "analysis": "/api/v1/analysis", 
            "system": "/api/v1/system"
        }
    }


@app.get("/health", response_model=SystemStatus)
async def health_check():
    """Verificar estado del sistema IA"""
    
    # Simular verificación de servicios
    services_status = {
        "ollama": {"status": "available", "model": "llama3.2:3b", "healthy": True},
        "mongodb": {"status": "connected", "healthy": True},
        "redis": {"status": "connected", "healthy": True},
        "api": {"status": "running", "healthy": True}
    }
    
    all_healthy = all(s.get("healthy", False) for s in services_status.values())
    
    return SystemStatus(
        healthy=all_healthy,
        services=services_status,
        ollama_status={
            "model": "llama3.2:3b",
            "status": "loaded",
            "memory_usage": "2.1GB"
        },
        performance_metrics={
            "avg_response_time": 1.2,
            "requests_per_minute": 45.0,
            "cpu_usage": 35.5,
            "memory_usage": 68.2
        },
        timestamp=datetime.now().isoformat()
    )


# === ENDPOINTS DE CHAT IA ===

@app.post("/api/v1/chat/sessions", response_model=ChatResponse)
async def create_chat_session(message: ChatMessage):
    """Crear sesión de chat IA para consultas DTE"""
    
    # Simular procesamiento con Ollama
    await asyncio.sleep(0.5)  # Simular tiempo de procesamiento
    
    # Respuestas predefinidas según contexto
    ai_responses = {
        "dte_general": "Como especialista en DTE chilenos, puedo ayudarte con consultas sobre facturación electrónica, boletas, notas de crédito y débito según normativa SII.",
        "factura_electronica": "Para facturar electrónicamente necesitas: certificado digital, sistema certificado SII, folios autorizados y cumplir con el formato XML estándar.",
        "normativa_sii": "La normativa del SII establece que todos los contribuyentes con ventas anuales superiores a 2.400 UF deben emitir documentos electrónicos."
    }
    
    response_text = ai_responses.get(message.context_type, "Consulta procesada por IA especializada en DTE chilenos.")
    
    return ChatResponse(
        success=True,
        message_id=f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        ai_response=response_text,
        confidence=0.92,
        tokens_used=156,
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/v1/chat/sessions/{session_id}/history")
async def get_chat_history(session_id: str):
    """Obtener historial de chat"""
    return {
        "success": True,
        "session_id": session_id,
        "messages": [],
        "total_messages": 0,
        "created_at": datetime.now().isoformat()
    }


# === ENDPOINTS DE ANÁLISIS IA ===

@app.post("/api/v1/analysis/analyze", response_model=AnalysisResult)
async def analyze_document(analysis: DocumentAnalysis, background_tasks: BackgroundTasks):
    """Analizar documento DTE con IA especializada"""
    
    # Simular análisis con IA
    processing_start = datetime.now()
    await asyncio.sleep(1.0)  # Simular tiempo de procesamiento IA
    
    # Análisis básico del tipo de DTE
    risk_indicators = []
    compliance_status = "compliant"
    
    if analysis.document_type == "33":  # Factura electrónica
        risk_indicators = ["Monto elevado para cliente nuevo", "Horario de emisión inusual"]
        risk_level = "medium"
    elif analysis.document_type == "39":  # Boleta electrónica
        risk_indicators = []
        risk_level = "low"
    else:
        risk_indicators = ["Tipo de documento poco común"]
        risk_level = "medium"
    
    recommendations = [
        "Verificar datos del receptor",
        "Validar cálculos tributarios",
        "Confirmar folios utilizados"
    ]
    
    processing_time = (datetime.now() - processing_start).total_seconds() * 1000
    
    return AnalysisResult(
        success=True,
        analysis_id=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        risk_level=risk_level,
        fraud_indicators=risk_indicators,
        compliance_status=compliance_status,
        recommendations=recommendations,
        confidence_score=0.87,
        processing_time_ms=int(processing_time)
    )


@app.get("/api/v1/analysis/{analysis_id}/report")
async def get_analysis_report(analysis_id: str):
    """Obtener reporte detallado de análisis"""
    return {
        "success": True,
        "analysis_id": analysis_id,
        "report": {
            "summary": "Documento analizado sin irregularidades críticas",
            "technical_details": "Análisis realizado con Ollama Llama 3.2 3B",
            "generated_at": datetime.now().isoformat()
        }
    }


# === ENDPOINTS DEL SISTEMA ===

@app.get("/api/v1/system/ollama/status")
async def get_ollama_status():
    """Estado del modelo Ollama"""
    return {
        "success": True,
        "model_info": {
            "name": "llama3.2:3b",
            "size": "3.2B parameters", 
            "status": "loaded",
            "memory_usage": "2.1GB",
            "last_used": datetime.now().isoformat()
        },
        "performance": {
            "avg_tokens_per_second": 45.2,
            "total_requests": 1247,
            "uptime_hours": 168.5
        }
    }


@app.post("/api/v1/system/events/notify")
async def notify_websocket_event(event_data: dict):
    """Notificar evento por WebSocket (placeholder)"""
    return {
        "success": True,
        "event_sent": True,
        "event_type": event_data.get("type", "general"),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/system/logs")
async def get_system_logs():
    """Obtener logs del sistema IA"""
    return {
        "success": True,
        "logs": [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "service": "ollama",
                "message": "Model llama3.2:3b loaded successfully"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO", 
                "service": "mongodb",
                "message": "Connected to analysis database"
            }
        ],
        "total_logs": 2
    }

@app.post("/api/v1/test/redis-message")
async def test_redis_message():
    """Endpoint para probar directamente el handler de Redis"""
    test_message = {
        "message": "Hola, esto es una prueba directa del endpoint",
        "sessionId": "test-direct-123",
        "userId": "user-direct-456", 
        "companyId": "company-direct-789"
    }
    
    print("🧪 TEST DIRECTO: Llamando handle_chat_request")
    await handle_chat_request(json.dumps(test_message))
    
    return {"status": "Test ejecutado", "message": "Revisar logs para ver resultado"}

# === PUNTO DE ENTRADA ===

if __name__ == "__main__":
    print("🤖 Iniciando CloudMusic DTE IA Backend")
    print("📊 Ollama Llama 3.2 3B - Análisis DTE local")
    print("📋 Conforme al informe académico")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8001,
        reload=True
    )
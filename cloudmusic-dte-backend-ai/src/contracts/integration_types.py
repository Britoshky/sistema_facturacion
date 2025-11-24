"""
Tipos de Integración entre Backend Node.js y Python IA
Contratos JSON para comunicación Redis Pub/Sub
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


# === EVENTOS REDIS PUB/SUB ===

class EventType(str, Enum):
    """Tipos de eventos Redis entre backends"""
    # Documentos
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_COMPLETED = "analysis_completed"
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_SIGNED = "document_signed"
    SII_RESPONSE = "sii_response"
    
    # Chat IA
    CHAT_MESSAGE = "chat_message"
    CHAT_RESPONSE = "chat_response"
    
    # Sistema
    SYSTEM_STATUS = "system_status"
    USER_NOTIFICATION = "user_notification"


class RedisChannel(str, Enum):
    """Canales Redis específicos"""
    WEBSOCKET = "cloudmusic_dte:websocket"
    DOCUMENTS = "cloudmusic_dte:documents" 
    ANALYSIS = "cloudmusic_dte:analysis"
    CHAT = "cloudmusic_dte:chat"
    SYSTEM = "cloudmusic_dte:system"
    NOTIFICATIONS = "cloudmusic_dte:notifications"


# === DOCUMENTOS (Node.js → Python) ===

class AnalysisRequestEvent(BaseModel):
    """Solicitud análisis desde Node.js backend"""
    event_type: Literal["analysis_request"] = "analysis_request"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # IDs del sistema
    document_id: str = Field(..., description="UUID documento PostgreSQL")
    company_id: str = Field(..., description="UUID empresa")
    user_id: str = Field(..., description="UUID usuario solicitante")
    
    # Tipo de análisis solicitado
    analysis_type: Literal[
        "tax_compliance_check",
        "fraud_detection", 
        "anomaly_detection",
        "pattern_analysis",
        "financial_analysis"
    ]
    
    # Datos del documento para análisis
    document_data: Dict[str, Any] = Field(..., description="Datos documento desde PostgreSQL")
    
    # Metadatos del request
    priority: Literal["low", "medium", "high"] = Field(default="medium")
    callback_channel: Optional[str] = Field(None, description="Canal respuesta específico")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DocumentCreatedEvent(BaseModel):
    """Evento documento creado (Node.js → Python)"""
    event_type: Literal["document_created"] = "document_created"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    document_id: str
    company_id: str
    user_id: str
    document_type: int
    folio_number: int
    total_amount: float
    status: str


# === ANÁLISIS IA (Python → Node.js) ===

class AnalysisCompletedEvent(BaseModel):
    """Resultado análisis IA (Python → Node.js)"""
    event_type: Literal["analysis_completed"] = "analysis_completed"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # IDs relacionados
    analysis_id: str = Field(..., description="UUID análisis MongoDB")
    document_id: str = Field(..., description="UUID documento PostgreSQL")
    company_id: str = Field(..., description="UUID empresa")
    user_id: str = Field(..., description="UUID usuario")
    
    # Resultados del análisis
    analysis_type: str = Field(..., description="Tipo análisis realizado")
    risk_level: Literal["minimal", "low", "medium", "high", "critical"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    
    # Resultados detallados
    analysis_results: Dict[str, Any] = Field(..., description="Resultados completos análisis")
    
    # Métricas
    processing_time_ms: int = Field(..., description="Tiempo procesamiento")
    ai_model_used: str = Field(default="ollama-llama3.2-3b")
    
    # Estado
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(None)


# === CHAT IA ===

class ChatMessageEvent(BaseModel):
    """Mensaje chat usuario (Node.js → Python)"""
    event_type: Literal["chat_message"] = "chat_message"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    session_id: str
    user_id: str
    company_id: str
    message: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChatResponseEvent(BaseModel):
    """Respuesta IA chat (Python → Node.js)"""
    event_type: Literal["chat_response"] = "chat_response"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    session_id: str
    message_id: str
    response: str
    processing_time_ms: int
    confidence: float
    ai_model: str = "ollama-llama3.2-3b"


# === SISTEMA ===

class SystemStatusEvent(BaseModel):
    """Estado sistema IA (Python → Node.js)"""
    event_type: Literal["system_status"] = "system_status"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    service: str = "ai_backend"
    status: Literal["healthy", "degraded", "down"]
    
    ollama_status: Dict[str, Any] = Field(default_factory=dict)
    mongodb_status: Dict[str, Any] = Field(default_factory=dict)
    redis_status: Dict[str, Any] = Field(default_factory=dict)
    
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    active_analyses: int = Field(default=0)


class UserNotificationEvent(BaseModel):
    """Notificación para usuario (Python → Node.js)"""
    event_type: Literal["user_notification"] = "user_notification"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    user_id: str
    company_id: Optional[str] = None
    
    notification_type: Literal[
        "analysis_completed",
        "chat_response", 
        "system_alert",
        "recommendation"
    ]
    
    title: str
    message: str
    priority: Literal["low", "medium", "high"] = "medium"
    
    # Datos adicionales
    related_document_id: Optional[str] = None
    related_analysis_id: Optional[str] = None
    action_required: bool = Field(default=False)
    auto_dismiss_seconds: Optional[int] = Field(None)


# === MAPEO DE TIPOS NODE.JS ↔ PYTHON ===

class NodeJSDocumentType:
    """Mapeo tipos documento Node.js TypeScript → Python"""
    FACTURA_ELECTRONICA = 33        # DocumentType.FACTURA_ELECTRONICA
    FACTURA_EXENTA = 34            # DocumentType.FACTURA_EXENTA  
    BOLETA_ELECTRONICA = 39        # DocumentType.BOLETA_ELECTRONICA
    BOLETA_EXENTA = 41             # DocumentType.BOLETA_EXENTA


class NodeJSSiiStatus:
    """Mapeo estados SII Node.js → Python"""
    DRAFT = "draft"                # SIIStatus.DRAFT
    SIGNED = "signed"              # SIIStatus.SIGNED
    SENT = "sent"                  # SIIStatus.SENT
    ACCEPTED = "accepted"          # SIIStatus.ACCEPTED
    REJECTED = "rejected"          # SIIStatus.REJECTED


class NodeJSAnalysisType:
    """Mapeo tipos análisis Node.js → Python"""
    STRUCTURE_VALIDATION = "structure_validation"      # → TAX_COMPLIANCE_CHECK
    CONTENT_ANALYSIS = "content_analysis"              # → FRAUD_DETECTION
    COMPLIANCE_CHECK = "compliance_check"              # → ANOMALY_DETECTION
    ERROR_DETECTION = "error_detection"                # → PATTERN_ANALYSIS
    IMPROVEMENT_SUGGESTIONS = "improvement_suggestions" # → FINANCIAL_ANALYSIS


# === UTILIDADES DE CONVERSIÓN ===

def convert_nodejs_to_python_analysis_type(nodejs_type: str) -> str:
    """Convertir tipo análisis Node.js a Python"""
    mapping = {
        "structure_validation": "tax_compliance_check",
        "content_analysis": "fraud_detection", 
        "compliance_check": "anomaly_detection",
        "error_detection": "pattern_analysis",
        "improvement_suggestions": "financial_analysis"
    }
    return mapping.get(nodejs_type, "tax_compliance_check")


def convert_python_to_nodejs_analysis_type(python_type: str) -> str:
    """Convertir tipo análisis Python a Node.js"""
    mapping = {
        "tax_compliance_check": "structure_validation",
        "fraud_detection": "content_analysis",
        "anomaly_detection": "compliance_check", 
        "pattern_analysis": "error_detection",
        "financial_analysis": "improvement_suggestions"
    }
    return mapping.get(python_type, "structure_validation")


# === RESPUESTAS ESTÁNDARES ===

class IntegrationResponse(BaseModel):
    """Respuesta estándar para integración"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheckResponse(BaseModel):
    """Health check entre servicios"""
    service_name: str
    status: Literal["healthy", "degraded", "down"]
    version: str
    uptime_seconds: int
    dependencies: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
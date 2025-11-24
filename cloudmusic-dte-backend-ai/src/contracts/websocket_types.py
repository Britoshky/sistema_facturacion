"""
Tipos de eventos WebSocket compartidos entre Node.js y Python
Alineados con RF010, RF011 según informe del proyecto
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Tipos de eventos según backend Node.js"""
    # Eventos de documentos
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated" 
    DOCUMENT_SIGNED = "document_signed"
    DOCUMENT_SENT = "document_sent"
    DOCUMENT_ACCEPTED = "document_accepted"
    DOCUMENT_REJECTED = "document_rejected"
    
    # Eventos de análisis IA
    AI_ANALYSIS_START = "ai_analysis_start"
    AI_ANALYSIS_COMPLETE = "ai_analysis_complete"
    AI_RESPONSE = "ai_response"
    
    # Eventos del sistema
    FOLIO_WARNING = "folio_warning"
    CERTIFICATE_EXPIRY = "certificate_expiry"
    SII_STATUS_CHANGE = "sii_status_change"
    
    # Notificaciones
    NOTIFICATION = "notification"
    SYSTEM_ALERT = "system_alert"


class SystemStatus(str, Enum):
    """Estados del sistema"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class BaseEvent(BaseModel):
    """Evento base"""
    id: str = Field(..., description="ID único del evento")
    type: EventType = Field(..., description="Tipo de evento")
    timestamp: datetime = Field(default_factory=datetime.now)
    company_id: Optional[str] = Field(None, description="ID de la empresa")
    user_id: Optional[str] = Field(None, description="ID del usuario")


class WebSocketEvent(BaseModel):
    """Evento WebSocket para comunicación Node.js <-> Python"""
    event_id: str = Field(..., description="ID único del evento")
    event_type: EventType = Field(..., description="Tipo de evento")
    user_id: str = Field(..., description="Usuario destinatario")
    data: Dict[str, Any] = Field(default_factory=dict, description="Datos del evento")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")
    created_at: datetime = Field(default_factory=datetime.now)


class DocumentEvent(BaseEvent):
    """Evento específico de documento"""
    document_id: str = Field(..., description="ID del documento")
    document_type: int = Field(..., description="Tipo DTE (33=Factura, 39=Boleta, etc.)")
    folio_number: int = Field(..., description="Número de folio")
    status: str = Field(..., description="Estado del documento")
    data: Dict[str, Any] = Field(default_factory=dict)


class AIAnalysisEvent(BaseEvent):
    """Evento de análisis IA"""
    document_id: str = Field(..., description="ID del documento a analizar")
    analysis_type: str = Field(..., description="Tipo de análisis solicitado")
    priority: str = Field(default="normal", description="Prioridad del análisis")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")


class AIResultEvent(BaseEvent):
    """Evento de resultado de análisis IA"""
    analysis_id: str = Field(..., description="ID del análisis")
    document_id: str = Field(..., description="ID del documento analizado")
    risk_level: str = Field(..., description="Nivel de riesgo detectado")
    confidence_score: float = Field(..., description="Nivel de confianza del análisis")
    results: Dict[str, Any] = Field(..., description="Resultados del análisis")
    processing_time_ms: int = Field(..., description="Tiempo de procesamiento en ms")


class ChatEvent(BaseEvent):
    """Evento de chat IA"""
    session_id: str = Field(..., description="ID de la sesión de chat")
    message_id: str = Field(..., description="ID del mensaje")
    content: str = Field(..., description="Contenido del mensaje")
    role: str = Field(..., description="Rol (user/assistant)")
    context_type: Optional[str] = Field(None, description="Tipo de contexto")


class NotificationEvent(BaseModel):
    """Evento de notificación de usuario"""
    notification_id: str = Field(..., description="ID de la notificación")
    user_id: str = Field(..., description="Usuario destinatario")
    type: str = Field(..., description="Tipo de notificación")
    title: str = Field(..., description="Título de la notificación")
    message: str = Field(..., description="Mensaje de la notificación")
    severity: str = Field(default="info", description="Severidad (info/warning/error)")
    persistent: bool = Field(default=False, description="Si persiste después del logout")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")
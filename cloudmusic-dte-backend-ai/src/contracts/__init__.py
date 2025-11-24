"""
Contratos compartidos - Exportaciones principales
Facilita la importación desde otros módulos
"""

from .ai_types import (
    ChatContext,
    ChatMessage,
    ChatSession,
    SendMessageRequest,
    SendMessageResponse,
    AnalysisRequest,
    AnalysisResult,
    AIMetrics,
)

from .document_types import (
    DTEDocument,
    DTEDocumentItem,
    DocumentAnalysis,
    DocumentAnalysisRequest,
    DocumentValidation,
    DocumentType,
    SIIStatus,
    AnalysisType,
    RiskLevel,
)

from .websocket_types import (
    WebSocketEvent,
    BaseEvent,
    DocumentEvent,
    AIAnalysisEvent,
    AIResultEvent,
    ChatEvent,
    NotificationEvent,
    EventType,
    SystemStatus,
)

__all__ = [
    # AI Types
    "ChatContext",
    "ChatMessage", 
    "ChatSession",
    "SendMessageRequest",
    "SendMessageResponse",
    "AnalysisRequest",
    "AnalysisResult",
    "AIMetrics",
    
    # Document Types
    "DTEDocument",
    "DTEDocumentItem", 
    "DocumentAnalysis",
    "DocumentAnalysisRequest",
    "DocumentValidation",
    "DocumentType",
    "SIIStatus",
    "AnalysisType", 
    "RiskLevel",
    
    # WebSocket Types
    "WebSocketEvent",
    "BaseEvent",
    "DocumentEvent",
    "AIAnalysisEvent",
    "AIResultEvent",
    "ChatEvent",
    "NotificationEvent",
    "EventType",
    "SystemStatus",
]
"""
Contratos compartidos entre Node.js y Python AI Backend
Basados en src/trpc/schemas/ai.ts del backend Node.js
Mantienen consistencia de tipos entre servicios
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    """Contexto de conversación con IA"""
    company_id: str
    user_id: str
    topic: Optional[str] = None
    user_name: Optional[str] = None
    company_name: Optional[str] = None
    is_new_user: Optional[bool] = False
    total_conversations: Optional[int] = 0
    communication_style: Optional[str] = "professional"
    question_complexity: Optional[str] = "medium"
    has_real_data: Optional[bool] = True
    business_data: Optional[Dict[str, Union[str, int, float, Dict]]] = {}
    message_intent: Optional[str] = "general"
    current_session_id: Optional[str] = None
    conversation_length: Optional[int] = 1
    session_topic: Optional[str] = "general"
    context_type_session: Optional[str] = "business_query"
    user_email: Optional[str] = ""
    company_rut: Optional[str] = ""
    favorite_topics: Optional[List[str]] = []
    last_interaction: Optional[str] = None
    typical_session_length: Optional[int] = 5
    preferred_topics: Optional[List[str]] = []
    prefers_detailed_answers: Optional[bool] = True
    math_frequency: Optional[str] = "medium"
    session_context: Optional[Dict[str, Union[str, int, float, Dict]]] = {}


class ChatMessage(BaseModel):
    """Mensaje individual de chat con IA"""
    id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Union[str, int, float]]] = None


class ChatSession(BaseModel):
    """Sesión de conversación con IA"""
    id: str
    session_id: Optional[str] = None  # Para compatibilidad con código existente
    user_id: str
    title: str
    status: Literal["active", "inactive", "archived"]
    last_activity: datetime
    message_count: int
    context: Union[ChatContext, Dict[str, Any]]
    messages: Optional[List[ChatMessage]] = []
    session_metadata: Optional[Dict[str, Union[str, int, float]]] = {}
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    is_active: Optional[bool] = True
    company_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SendMessageRequest(BaseModel):
    """Solicitud de envío de mensaje"""
    session_id: Optional[str] = None
    message: str = Field(min_length=1)
    context: ChatContext


class SendMessageResponse(BaseModel):
    """Respuesta de mensaje enviado"""
    message_id: str
    session_id: str
    status: Literal["sent", "processing", "completed", "error"]
    timestamp: datetime
    message: str


class AnalysisRequest(BaseModel):
    """Solicitud de análisis IA de documentos"""
    document_id: str
    company_id: str
    user_id: str
    analysis_type: Literal["anomaly_detection", "cash_flow_prediction", "tax_optimization"]
    input_data: Dict[str, Union[str, int, float, bool]]
    priority: Literal["low", "medium", "high"] = "medium"


class AnalysisResult(BaseModel):
    """Resultado de análisis IA"""
    request_id: str
    analysis_type: str
    status: Literal["processing", "completed", "failed"]
    result: Optional[Dict[str, Union[str, int, float, bool, List]]] = None
    confidence: Optional[float] = None
    recommendations: Optional[List[str]] = None
    processing_time: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class AIMetrics(BaseModel):
    """Métricas del sistema IA en tiempo real"""
    active_chats: int
    pending_analysis: int
    completed_analysis_today: int
    average_response_time: float
    ai_availability: float
    total_interactions: int
    anomalies_detected: int
    predictions_generated: int
    system_load: float
    last_update: datetime
    performance: Dict[str, float]
    meets_latency_sla: bool
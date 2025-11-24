"""
Rutas API para Chat IA
Endpoints para interacción con el asistente IA especializado en DTE
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from ..services import ModularChatService
from ..contracts.ai_types import ChatSession, ChatMessage
from ..core.dependencies import get_modular_chat_service, get_current_user
from ..core.responses import APIResponse


router = APIRouter(prefix="/chat", tags=["Chat IA"])


# === REQUEST/RESPONSE MODELS ===

class CreateSessionRequest(BaseModel):
    """Solicitud para crear sesión de chat"""
    topic: Optional[str] = "Consulta DTE General"
    context_type: str = "general"


class SendMessageRequest(BaseModel):
    """Solicitud para enviar mensaje"""
    content: str
    metadata: Optional[Dict] = None


class SessionResponse(BaseModel):
    """Respuesta con información de sesión"""
    session_id: str
    topic: str
    context_type: str
    created_at: str
    is_active: bool
    message_count: int


class MessageResponse(BaseModel):
    """Respuesta con mensaje de chat"""
    message_id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict] = None


# === ENDPOINTS ===

@router.post("/sessions", response_model=APIResponse[SessionResponse])
async def create_chat_session(
    request: CreateSessionRequest,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Crear nueva sesión de chat IA"""
    try:
        session = await chat_service.create_chat_session(
            user_id=current_user["user_id"],
            company_id=current_user["company_id"],
            metadata={"topic": request.topic, "context_type": request.context_type}
        )
        
        response_data = SessionResponse(
            session_id=session.id,
            topic=request.topic,
            context_type=request.context_type,
            created_at=session.created_at.isoformat(),
            is_active=session.is_active,
            message_count=len(session.messages)
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="Sesión de chat creada exitosamente"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/messages", response_model=APIResponse[MessageResponse])
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Enviar mensaje y obtener respuesta IA"""
    try:
        message = await chat_service.process_message(
            session_id=session_id,
            user_message=request.content,
            metadata=request.metadata
        )
        
        response_data = MessageResponse(
            message_id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            timestamp=message.timestamp.isoformat(),
            metadata=message.metadata
        )
        
        # Publicar respuesta via WebSocket en background
        background_tasks.add_task(
            _publish_message_websocket,
            message,
            current_user["user_id"]
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="Mensaje enviado exitosamente"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=APIResponse[List[MessageResponse]])
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Obtener historial de mensajes de sesión"""
    try:
        messages = await chat_service.get_session_history(
            session_id=session_id,
            user_id=current_user["user_id"],
            limit=limit,
            offset=offset
        )
        
        response_data = [
            MessageResponse(
                message_id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat(),
                metadata=msg.metadata
            )
            for msg in messages
        ]
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"Obtenidos {len(response_data)} mensajes"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=APIResponse[List[SessionResponse]])
async def get_user_sessions(
    active_only: bool = True,
    limit: int = 20,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Obtener sesiones de chat del usuario"""
    try:
        sessions = await chat_service.get_user_sessions(
            user_id=current_user["user_id"],
            company_id=current_user.get("company_id"),
            active_only=active_only,
            limit=limit
        )
        
        response_data = [
            SessionResponse(
                session_id=session.id,
                topic="Sesión de Chat",  # Valor por defecto ya que no se almacena separadamente
                context_type="general",  # Valor por defecto
                created_at=session.created_at.isoformat(),
                is_active=session.is_active,
                message_count=session.message_count or 0
            )
            for session in sessions
        ]
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"Obtenidas {len(response_data)} sesiones"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=APIResponse[bool])
async def close_session(
    session_id: str,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Cerrar sesión de chat"""
    try:
        success = await chat_service.end_chat_session(
            session_id=session_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        
        return APIResponse(
            success=True,
            data=True,
            message="Sesión cerrada exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=APIResponse[List[MessageResponse]])
async def search_conversations(
    query: str,
    limit: int = 10,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Buscar en conversaciones del usuario"""
    try:
        if len(query.strip()) < 3:
            raise HTTPException(
                status_code=400, 
                detail="La consulta debe tener al menos 3 caracteres"
            )
        
        messages = await chat_service.search_conversations(
            user_id=current_user["user_id"],
            query=query,
            company_id=current_user.get("company_id"),
            limit=limit
        )
        
        response_data = [
            MessageResponse(
                message_id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat(),
                metadata=msg.metadata or {}
            )
            for msg in messages
        ]
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"Encontrados {len(response_data)} mensajes"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=APIResponse[Dict])
async def get_chat_analytics(
    days: int = 30,
    chat_service: ModularChatService = Depends(get_modular_chat_service),
    current_user: Dict = Depends(get_current_user)
):
    """Obtener analíticas de chat del usuario"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="El período debe estar entre 1 y 365 días"
            )
        
        analytics = await chat_service.get_chat_analytics(
            user_id=current_user["user_id"],
            company_id=current_user.get("company_id"),
            days=days
        )
        
        return APIResponse(
            success=True,
            data=analytics,
            message="Analíticas obtenidas exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === HELPER FUNCTIONS ===

async def _publish_message_websocket(message: ChatMessage, user_id: str):
    """Publicar mensaje via WebSocket (background task)"""
    try:
        # TODO: Implementar publicación WebSocket via Redis
        from ..services import RedisService
        
        # Esta función se ejecutará en background
        # Por ahora es un placeholder
        pass
        
    except Exception as e:
        # Log error pero no fallar la respuesta principal
        print(f"Error publishing WebSocket message: {e}")


# === CONTEXT TYPES ===

AVAILABLE_CONTEXT_TYPES = {
    "general": "Consultas generales sobre DTE",
    "technical": "Soporte técnico e implementación",
    "accounting": "Contabilidad y tributación",
    "legal": "Normativa y aspectos legales"
}


@router.get("/context-types", response_model=APIResponse[Dict[str, str]])
async def get_context_types():
    """Obtener tipos de contexto disponibles"""
    return APIResponse(
        success=True,
        data=AVAILABLE_CONTEXT_TYPES,
        message="Tipos de contexto obtenidos exitosamente"
    )
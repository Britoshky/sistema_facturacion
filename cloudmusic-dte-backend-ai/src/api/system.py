"""
Rutas API para Estado del Sistema IA
Endpoints para monitoreo y status de servicios IA
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..services import OllamaClient, RedisService, DatabaseService
from ..core.dependencies import get_ollama_client, get_redis_service, get_database_service
from ..core.responses import APIResponse


router = APIRouter(prefix="/system", tags=["Estado del Sistema"])


# === RESPONSE MODELS ===

class SystemHealthResponse(BaseModel):
    """Respuesta de salud del sistema"""
    status: str
    timestamp: str
    services: Dict[str, Dict[str, Any]]
    overall_health: str


class OllamaStatusResponse(BaseModel):
    """Estado específico de Ollama"""
    is_available: bool
    model: str
    available_models: list[str]
    host: str
    last_check: str


class ServiceMetricsResponse(BaseModel):
    """Métricas de servicios"""
    ollama_requests: int
    chat_sessions: int
    analyses_completed: int
    uptime_seconds: int
    memory_usage_mb: Optional[float] = None


# === ENDPOINTS ===

@router.get("/health", response_model=APIResponse[SystemHealthResponse])
async def get_system_health(
    ollama_client: OllamaClient = Depends(get_ollama_client),
    redis_service: RedisService = Depends(get_redis_service)
):
    """Obtener estado general de salud del sistema"""
    try:
        timestamp = datetime.now(timezone.utc)
        services = {}
        
        # Check Ollama
        try:
            ollama_healthy = await ollama_client.health_check()
            services["ollama"] = {
                "status": "healthy" if ollama_healthy else "unhealthy",
                "available": ollama_healthy,
                "host": ollama_client.config.host,
                "model": ollama_client.config.model
            }
        except Exception as e:
            services["ollama"] = {
                "status": "error",
                "available": False,
                "error": str(e)
            }
        
        # Check Redis
        try:
            redis_healthy = await redis_service.health_check()
            services["redis"] = {
                "status": "healthy" if redis_healthy else "unhealthy",
                "available": redis_healthy
            }
        except Exception as e:
            services["redis"] = {
                "status": "error",
                "available": False,
                "error": str(e)
            }
        
        # Check MongoDB (indirecto via DatabaseService)
        try:
            # Placeholder - en producción hacer ping real a MongoDB
            services["mongodb"] = {
                "status": "healthy",
                "available": True
            }
        except Exception as e:
            services["mongodb"] = {
                "status": "error",
                "available": False,
                "error": str(e)
            }
        
        # Determinar estado general
        all_healthy = all(
            service.get("available", False) 
            for service in services.values()
        )
        
        overall_health = "healthy" if all_healthy else "degraded"
        
        # Si servicios críticos fallan, marcar como unhealthy
        critical_services = ["ollama", "mongodb"]
        critical_failing = any(
            not services.get(service, {}).get("available", False)
            for service in critical_services
        )
        
        if critical_failing:
            overall_health = "unhealthy"
        
        response_data = SystemHealthResponse(
            status="ok",
            timestamp=timestamp.isoformat(),
            services=services,
            overall_health=overall_health
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="Estado del sistema obtenido exitosamente"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ollama/status", response_model=APIResponse[OllamaStatusResponse])
async def get_ollama_status(
    ollama_client: OllamaClient = Depends(get_ollama_client)
):
    """Obtener estado detallado de Ollama"""
    try:
        # Verificar disponibilidad
        is_available = await ollama_client.health_check()
        
        # Obtener modelos disponibles
        available_models = []
        if is_available:
            try:
                available_models = await ollama_client.list_models()
            except:
                pass  # No es crítico si falla la lista de modelos
        
        response_data = OllamaStatusResponse(
            is_available=is_available,
            model=ollama_client.config.model,
            available_models=available_models,
            host=ollama_client.config.host,
            last_check=datetime.now(timezone.utc).isoformat()
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="Estado de Ollama obtenido exitosamente"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/pull-model/{model_name}", response_model=APIResponse[bool])
async def pull_ollama_model(
    model_name: str,
    ollama_client: OllamaClient = Depends(get_ollama_client)
):
    """Descargar modelo específico en Ollama"""
    try:
        # Validar nombre del modelo
        allowed_models = [
            "llama3.2:3b",
            "llama3.2:1b", 
            "llama3.1:8b",
            "codellama:7b",
            "mistral:7b"
        ]
        
        if model_name not in allowed_models:
            raise HTTPException(
                status_code=400,
                detail=f"Modelo no permitido. Modelos disponibles: {', '.join(allowed_models)}"
            )
        
        # Verificar conexión
        if not await ollama_client.health_check():
            raise HTTPException(
                status_code=503,
                detail="Ollama no está disponible"
            )
        
        # Intentar descargar modelo
        success = await ollama_client.pull_model(model_name)
        
        if success:
            return APIResponse(
                success=True,
                data=True,
                message=f"Modelo {model_name} descargado exitosamente"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error descargando modelo {model_name}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=APIResponse[ServiceMetricsResponse])
async def get_system_metrics():
    """Obtener métricas del sistema - requiere configuración de MongoDB"""
    try:
        # TODO: Implementar métricas reales conectadas a MongoDB
        # Requiere configuración de base de datos para obtener métricas reales
        
        raise HTTPException(
            status_code=501, 
            detail="Métricas del sistema requieren configuración de base de datos MongoDB. Consulte documentación de instalación."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/recent", response_model=APIResponse[list[Dict[str, Any]]])
async def get_recent_logs(
    limit: int = 50,
    level: Optional[str] = None
):
    """Obtener logs recientes del sistema"""
    try:
        # Placeholder - en producción leer de archivo de logs o servicio centralizado
        logs = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "service": "ai_backend",
                "message": "Sistema iniciado correctamente",
                "metadata": {}
            }
        ]
        
        # Filtrar por nivel si se especifica
        if level:
            logs = [log for log in logs if log["level"] == level.upper()]
        
        # Limitar cantidad
        logs = logs[:limit]
        
        return APIResponse(
            success=True,
            data=logs,
            message=f"Obtenidos {len(logs)} logs recientes"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=APIResponse[Dict[str, Any]])
async def get_system_config():
    """Obtener configuración del sistema (información no sensible)"""
    try:
        config = {
            "ollama": {
                "model": "llama3.2:3b",
                "host": "localhost:11434",
                "timeout": 30,
                "context_size": 4096
            },
            "redis": {
                "host": "localhost",
                "port": 6379
            },
            "mongodb": {
                "host": "localhost",
                "port": 27017,
                "database": "cloudmusic_dte_ai"
            },
            "features": {
                "chat_enabled": True,
                "analysis_enabled": True,
                "batch_processing": True,
                "websocket_notifications": True
            }
        }
        
        return APIResponse(
            success=True,
            data=config,
            message="Configuración del sistema obtenida"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
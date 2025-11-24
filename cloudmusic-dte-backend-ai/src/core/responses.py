"""
Modelos de respuesta estandarizados para la API
"""

from typing import Generic, TypeVar, Optional, Any, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


# Type variable para respuestas genéricas
T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Respuesta estandarizada de la API"""
    
    success: bool = Field(description="Indica si la operación fue exitosa")
    data: Optional[T] = Field(default=None, description="Datos de respuesta")
    message: str = Field(description="Mensaje descriptivo del resultado")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp de la respuesta")
    request_id: Optional[str] = Field(default=None, description="ID único de la petición")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada"""
    
    success: bool = False
    error: Dict[str, Any] = Field(description="Detalles del error")
    message: str = Field(description="Mensaje de error")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = Field(default=None)
    
    @classmethod
    def from_exception(
        cls, 
        exception: Exception, 
        message: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> "ErrorResponse":
        """Crear respuesta de error desde excepción"""
        return cls(
            error={
                "type": type(exception).__name__,
                "details": str(exception)
            },
            message=message or str(exception),
            request_id=request_id
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada estandarizada"""
    
    success: bool = True
    data: List[T] = Field(description="Lista de elementos")
    pagination: Dict[str, Any] = Field(description="Información de paginación")
    message: str = Field(description="Mensaje descriptivo")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
        message: str = "Datos obtenidos exitosamente"
    ) -> "PaginatedResponse[T]":
        """Crear respuesta paginada"""
        
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return cls(
            data=items,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            },
            message=message
        )


class StatusResponse(BaseModel):
    """Respuesta de estado simple"""
    
    status: str = Field(description="Estado de la operación")
    message: str = Field(description="Mensaje descriptivo")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detalles adicionales")


class HealthCheckResponse(BaseModel):
    """Respuesta de health check"""
    
    healthy: bool = Field(description="Indica si el servicio está saludable")
    services: Dict[str, Any] = Field(description="Estado de servicios dependientes")
    version: str = Field(description="Versión de la aplicación")
    uptime: Optional[float] = Field(default=None, description="Tiempo de actividad en segundos")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# === RESPONSE BUILDERS ===

def success_response(
    data: T = None,
    message: str = "Operación exitosa",
    request_id: Optional[str] = None
) -> APIResponse[T]:
    """Crear respuesta exitosa"""
    return APIResponse(
        success=True,
        data=data,
        message=message,
        request_id=request_id
    )


def error_response(
    message: str,
    error_details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de error"""
    return ErrorResponse(
        error=error_details or {},
        message=message,
        request_id=request_id
    )


def validation_error_response(
    field: str,
    message: str,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de error de validación"""
    return ErrorResponse(
        error={
            "type": "ValidationError",
            "field": field,
            "details": message
        },
        message=f"Error de validación en campo '{field}': {message}",
        request_id=request_id
    )


def not_found_response(
    resource: str,
    identifier: str,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de recurso no encontrado"""
    return ErrorResponse(
        error={
            "type": "NotFoundError",
            "resource": resource,
            "identifier": identifier
        },
        message=f"{resource} con ID '{identifier}' no encontrado",
        request_id=request_id
    )


def unauthorized_response(
    message: str = "No autorizado",
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de no autorizado"""
    return ErrorResponse(
        error={
            "type": "UnauthorizedError",
            "details": "Token inválido o expirado"
        },
        message=message,
        request_id=request_id
    )


def forbidden_response(
    message: str = "Acceso denegado",
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de acceso prohibido"""
    return ErrorResponse(
        error={
            "type": "ForbiddenError", 
            "details": "Permisos insuficientes"
        },
        message=message,
        request_id=request_id
    )


def rate_limit_response(
    message: str = "Límite de requests excedido",
    retry_after: Optional[int] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de límite de rate"""
    error_details = {"type": "RateLimitError"}
    if retry_after:
        error_details["retry_after"] = retry_after
        
    return ErrorResponse(
        error=error_details,
        message=message,
        request_id=request_id
    )


def service_unavailable_response(
    service: str,
    message: Optional[str] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Crear respuesta de servicio no disponible"""
    return ErrorResponse(
        error={
            "type": "ServiceUnavailableError",
            "service": service,
            "details": f"El servicio {service} no está disponible temporalmente"
        },
        message=message or f"Servicio {service} no disponible",
        request_id=request_id
    )
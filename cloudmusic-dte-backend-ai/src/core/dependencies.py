"""
Dependencias de FastAPI para inyección
"""

from typing import Dict, Optional, Annotated
from fastapi import Depends, HTTPException, Header, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger
import jwt

from .config import get_settings, Settings
from ..services import (
    ModularChatService, DocumentAnalysisService, DatabaseService,
    OllamaClient, OllamaConfig, RedisService, BusinessContextService,
    PrecisionEnhancementService, IntentDetectionService, PostgreSQLService
)


# === CONFIGURACIÓN ===

def get_config() -> Settings:
    """Obtener configuración de la aplicación"""
    return get_settings()


# === BASE DE DATOS ===

# Cliente MongoDB global (se inicializa en startup)
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_database: Optional[AsyncIOMotorDatabase] = None


async def get_database() -> AsyncIOMotorDatabase:
    """Obtener instancia de base de datos MongoDB"""
    if mongodb_database is None:
        raise RuntimeError("Database not initialized")
    return mongodb_database


def get_database_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> DatabaseService:
    """Obtener servicio de base de datos"""
    return DatabaseService(db)


# === SERVICIOS IA ===

def get_ollama_client(config: Settings = Depends(get_config)) -> OllamaClient:
    """Obtener cliente Ollama"""
    ollama_config = OllamaConfig(
        host=config.ollama_host,
        model=config.ollama_model,
        timeout=config.ollama_timeout,
        context_size=config.ollama_context_size,
        temperature=config.ollama_temperature,
        max_tokens=config.ollama_max_tokens
    )
    return OllamaClient(ollama_config)


def get_redis_service(config: Settings = Depends(get_config)) -> RedisService:
    """Obtener servicio Redis"""
    return RedisService(
        redis_url=config.redis_url,
        channel_prefix=config.redis_channel_prefix
    )


# Servicio de chat obsoleto eliminado - usar get_modular_chat_service

def get_postgresql_service(config: Settings = Depends(get_config)) -> PostgreSQLService:
    """Obtener servicio PostgreSQL"""
    return PostgreSQLService(config.postgresql_url)


def get_modular_chat_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    config: Settings = Depends(get_config),
    postgres_service: PostgreSQLService = Depends(get_postgresql_service)
) -> ModularChatService:
    """Obtener servicio de chat modular (nueva versión)"""
    ollama_config = OllamaConfig(
        host=config.ollama_host,
        model=config.ollama_model,
        timeout=config.ollama_timeout,
        context_size=config.ollama_context_size,
        temperature=config.ollama_temperature,
        max_tokens=config.ollama_max_tokens
    )
    return ModularChatService(db, ollama_config, postgres_service)


def get_document_analysis_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    config: Settings = Depends(get_config)
) -> DocumentAnalysisService:
    """Obtener servicio de análisis de documentos"""
    ollama_config = OllamaConfig(
        host=config.ollama_host,
        model=config.ollama_model,
        timeout=config.ollama_timeout,
        context_size=config.ollama_context_size,
        temperature=config.ollama_temperature,
        max_tokens=config.ollama_max_tokens
    )
    return DocumentAnalysisService(db, ollama_config)


# === AUTENTICACIÓN ===

async def get_current_user(
    authorization: Annotated[str, Header()] = None,
    config: Settings = Depends(get_config)
) -> Dict:
    """Obtener usuario actual desde JWT token"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extraer token del header "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )
        
        # Decodificar JWT
        payload = jwt.decode(
            token, 
            config.secret_key, 
            algorithms=[config.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # En producción, validar usuario existe en base de datos
        # Por ahora retornamos los datos del token
        return {
            "user_id": user_id,
            "company_id": payload.get("company_id"),
            "email": payload.get("email"),
            "role": payload.get("role", "user")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )


async def get_admin_user(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Verificar que el usuario actual es administrador"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# === VALIDACIONES ===

def validate_file_upload(
    file_size: int,
    file_extension: str,
    config: Settings = Depends(get_config)
) -> bool:
    """Validar archivo subido"""
    
    # Verificar tamaño
    max_size_bytes = config.max_file_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {config.max_file_size_mb}MB limit"
        )
    
    # Verificar extensión
    if file_extension.lower() not in config.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {file_extension} not allowed. Allowed: {config.allowed_file_types}"
        )
    
    return True


# === LIFECYCLE FUNCTIONS ===

async def initialize_database():
    """Inicializar conexión a MongoDB"""
    global mongodb_client, mongodb_database
    
    config = get_settings()
    
    # Configurar timeouts optimizados para conexión directa (según test exitoso)
    mongodb_client = AsyncIOMotorClient(
        config.mongodb_url,  # Ya incluye directConnection=true en la URL
        serverSelectionTimeoutMS=3000   # Timeout corto y efectivo
    )
    mongodb_database = mongodb_client[config.mongodb_database]
    
    # Verificar conexión con timeout
    await mongodb_client.admin.command('ping')
    
    # La base de datos ya está inicializada - solo verificar que existe
    logger.info(f"MongoDB connected successfully to database: {config.mongodb_database}")
    collections = await mongodb_database.list_collection_names()
    logger.info(f"Available collections: {collections}")
    logger.info("Database initialization skipped - using existing database")


async def close_database():
    """Cerrar conexión a MongoDB"""
    global mongodb_client, mongodb_database
    
    if mongodb_client:
        mongodb_client.close()
        mongodb_client = None
        mongodb_database = None


# === MIDDLEWARE HELPERS ===

def get_user_context(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Obtener contexto del usuario para logging y auditoría"""
    return {
        "user_id": current_user["user_id"],
        "company_id": current_user.get("company_id"),
        "role": current_user.get("role")
    }
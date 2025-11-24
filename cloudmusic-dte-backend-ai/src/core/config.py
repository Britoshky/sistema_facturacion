"""
Configuración de la aplicación FastAPI
"""

import os
from typing import Optional
from pydantic import BaseModel
from functools import lru_cache


class Settings(BaseModel):
    """Configuración de la aplicación"""
    
    # Aplicación
    app_name: str = "CloudMusic DTE IA Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Base de datos MongoDB - Se lee desde .env
    mongodb_url: str = os.getenv("MONGODB_URL", "")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "cloudmusic_dte")
    
    # Redis - Se lee desde .env  
    redis_url: str = os.getenv("REDIS_URL", "")
    redis_channel_prefix: str = "cloudmusic_dte"
    
    # Ollama IA - Se lee desde .env
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    ollama_context_size: int = 4096
    ollama_temperature: float = 0.7
    ollama_max_tokens: int = 1000
    
    # Seguridad
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Archivos y uploads
    max_file_size_mb: int = 10
    allowed_file_types: list[str] = [".json", ".xml", ".txt"]
    upload_dir: str = "./uploads"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "{time} | {level} | {module} | {message}"
    
    # Performance
    max_concurrent_analyses: int = 5
    max_batch_size: int = 50
    cache_ttl_seconds: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración singleton"""
    return Settings()


# Variables de entorno específicas
def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Obtener variable de entorno con valor por defecto"""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is required")
    return value


# Configuraciones derivadas
def get_database_url() -> str:
    """URL completa de MongoDB"""
    settings = get_settings()
    return f"{settings.mongodb_url}/{settings.mongodb_database}"


def is_development() -> bool:
    """Verificar si estamos en modo desarrollo"""
    return get_settings().debug


def is_production() -> bool:
    """Verificar si estamos en modo producción"""
    return not is_development()
"""
Aplicación principal FastAPI - CloudMusic DTE IA Backend
Backend especializado en análisis IA de documentos tributarios electrónicos
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn

from .core.config import get_settings
from .core.dependencies import initialize_database, close_database
from .core.responses import ErrorResponse, HealthCheckResponse
from .api import chat_router, analysis_router, system_router


# === LIFECYCLE MANAGEMENT ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    
    # Startup
    logger.info("Starting CloudMusic DTE IA Backend...")
    
    try:
        # La base de datos se inicializa en main.py raíz
        # Solo loggeamos que el módulo src está listo
        logger.info("IA Backend module ready (DB initialized in root main.py)")
        
    except Exception as e:
        logger.error(f"Failed to start IA Backend module: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down IA Backend...")
    
    try:
        # Cerrar conexiones
        await close_database()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("IA Backend shut down complete")


# === APP CREATION ===

def create_app() -> FastAPI:
    """Crear y configurar aplicación FastAPI"""
    
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        Backend IA especializado para el sistema CloudMusic DTE.
        
        Funcionalidades:
        - Chat IA contextual para consultas sobre DTE chilenos
        - Análisis inteligente de documentos tributarios
        - Detección de fraudes y anomalías
        - Validación automática de cumplimiento normativo
        - Integración con Ollama para IA local (Llama 3.2 3B)
        
        Diseñado específicamente para la normativa tributaria chilena del SII.
        """,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    return app


app = create_app()
settings = get_settings()


# === MIDDLEWARE ===

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted Hosts (solo en producción)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.cloudmusic.com"]
    )


# === ERROR HANDLERS ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador global de HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error={
                "type": "HTTPException",
                "status_code": exc.status_code,
                "detail": exc.detail
            },
            message=exc.detail
        ).dict()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones no controladas"""
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error={
                "type": type(exc).__name__,
                "detail": str(exc) if settings.debug else "Internal server error"
            },
            message="Ha ocurrido un error interno del servidor"
        ).dict()
    )


# === MIDDLEWARE PERSONALIZADO ===

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware de logging para requests"""
    
    start_time = asyncio.get_event_loop().time()
    
    # Procesar request
    response = await call_next(request)
    
    # Calcular tiempo de procesamiento
    process_time = asyncio.get_event_loop().time() - start_time
    
    # Log request info
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.4f}s"
    )
    
    # Agregar header de tiempo de respuesta
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# === RUTAS ===

# Incluir routers de la API
app.include_router(
    chat_router,
    prefix=settings.api_prefix
)

app.include_router(
    analysis_router,
    prefix=settings.api_prefix
)

app.include_router(
    system_router,
    prefix=settings.api_prefix
)


# === RUTAS BASE ===

@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Health check básico"""
    return HealthCheckResponse(
        healthy=True,
        services={
            "api": {"status": "running"},
            "database": {"status": "connected"},
        },
        version=settings.app_version
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check detallado"""
    
    # Verificar servicios críticos
    services_status = {}
    
    try:
        # TODO: Verificar MongoDB, Redis, Ollama
        services_status = {
            "mongodb": {"status": "connected", "healthy": True},
            "redis": {"status": "connected", "healthy": True},
            "ollama": {"status": "available", "healthy": True}
        }
        
        all_healthy = all(s.get("healthy", False) for s in services_status.values())
        
        return HealthCheckResponse(
            healthy=all_healthy,
            services=services_status,
            version=settings.app_version
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        return HealthCheckResponse(
            healthy=False,
            services={"error": {"status": "failed", "detail": str(e)}},
            version=settings.app_version
        )


@app.get("/info")
async def app_info():
    """Información de la aplicación"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Backend IA para sistema CloudMusic DTE",
        "features": [
            "Chat IA especializado en DTE chilenos",
            "Análisis inteligente de documentos",
            "Detección de fraudes y anomalías", 
            "Validación de cumplimiento normativo",
            "Integración Ollama (IA local)"
        ],
        "endpoints": {
            "chat": f"{settings.api_prefix}/chat",
            "analysis": f"{settings.api_prefix}/analysis",
            "system": f"{settings.api_prefix}/system"
        }
    }


# === CONFIGURACIÓN DE LOGGING ===

def setup_logging():
    """Configurar sistema de logging"""
    
    logger.remove()  # Remover configuración por defecto
    
    # Configurar formato
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Logger para consola
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format=log_format,
        level=settings.log_level,
        colorize=True
    )
    
    # Logger para archivo (solo en producción)
    if not settings.debug:
        logger.add(
            "logs/ai_backend.log",
            rotation="100 MB",
            retention="30 days",
            format=log_format,
            level=settings.log_level
        )


# Configurar logging al importar
setup_logging()


# === PUNTO DE ENTRADA ===

if __name__ == "__main__":
    
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_config=None,  # Usar nuestro sistema de logging
        access_log=False  # Desactivar access log de uvicorn
    )
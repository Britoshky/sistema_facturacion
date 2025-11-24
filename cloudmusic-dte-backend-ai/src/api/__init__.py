"""
Rutas API del backend IA CloudMusic DTE
"""

from .chat import router as chat_router
from .analysis import router as analysis_router
from .system import router as system_router

__all__ = [
    "chat_router",
    "analysis_router", 
    "system_router"
]
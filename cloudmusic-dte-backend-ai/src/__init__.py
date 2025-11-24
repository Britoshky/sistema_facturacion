"""
CloudMusic DTE IA Backend
Sistema de Inteligencia Artificial para Documentos Tributarios Electrónicos

Cumple con los requisitos RF010, RF011, RF012 del informe del proyecto.
"""

__version__ = "1.0.0"
__author__ = "CloudMusic DTE Team"
__email__ = "dev@cloudmusic.cl"

# Re-exportar componentes principales para facilitar imports
from .main import app
from .core.config import get_settings

__all__ = ["app", "get_settings"]
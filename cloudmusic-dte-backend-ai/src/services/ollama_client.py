"""
Cliente Ollama para interacción conversacional inteligente - VERSIÓN MODULAR
ARCHIVO DE COMPATIBILIDAD - Usa arquitectura modular internamente
"""

from typing import Dict, List, Optional, Union
from datetime import datetime

# Importar arquitectura modular
from .ollama_modular_client import OllamaModularClient
from .ollama_connection_manager import OllamaConfig
from .ollama_response_processor import OllamaResponse
try:
    from ..contracts.ai_types import ChatMessage, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatMessage, ChatContext


# === ALIAS DE COMPATIBILIDAD ===

class OllamaClient:
    """
    Cliente Ollama de compatibilidad que delega a la arquitectura modular
    Mantiene la misma interfaz pública para no romper código existente
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        # Usar cliente modular internamente
        self.modular_client = OllamaModularClient(config)
        
        # Mantener referencias de compatibilidad
        self.config = self.modular_client.config
        self.client = None  # Se expondrá después de conexión
        
    # === CONTEXT MANAGER ===
    
    async def __aenter__(self):
        await self.modular_client.__aenter__()
        self.client = self.modular_client.client
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.modular_client.__aexit__(exc_type, exc_val, exc_tb)
    
    # === DELEGACIÓN A CLIENTE MODULAR ===
    
    async def health_check(self) -> bool:
        """Verificar estado de salud de Ollama"""
        return await self.modular_client.health_check()
    
    async def list_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        return await self.modular_client.list_models()
    
    async def pull_model(self, model_name: str) -> bool:
        """Descargar un modelo específico"""
        return await self.modular_client.pull_model(model_name)
    
    async def generate_response(
        self,
        user_prompt: str,
        context: Optional[ChatContext] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> OllamaResponse:
        """Generar respuesta conversacional inteligente"""
        return await self.modular_client.generate_response(
            user_prompt, context, system_prompt, conversation_history, model, **kwargs
        )
    
    async def analyze_document_content(
        self,
        document_text: str,
        analysis_type: str = "general",
        context: Optional[ChatContext] = None
    ) -> Dict:
        """Analizar contenido de documento"""
        return await self.modular_client.analyze_document_content(
            document_text, analysis_type, context
        )
    
    # === MÉTODOS DE COMPATIBILIDAD ESPECÍFICOS ===
    
    def _build_contextual_prompt(
        self,
        user_prompt: str,
        context: Optional[ChatContext],
        system_prompt: Optional[str],
        conversation_history: Optional[List[ChatMessage]]
    ) -> str:
        """Método de compatibilidad - delegar al prompt builder"""
        return self.modular_client.prompt_builder.build_contextual_prompt(
            user_prompt, context, system_prompt, conversation_history
        )
    
    def _analyze_user_intent(self, prompt: str) -> str:
        """Método de compatibilidad - delegar al prompt builder"""
        return self.modular_client.prompt_builder._analyze_user_intent(prompt)
    
    def _clean_response_content(self, content: str) -> str:
        """Método de compatibilidad - delegar al response processor"""
        return self.modular_client.response_processor._clean_response_content(content)
    
    def _build_smart_context_info(self, context: Optional[ChatContext], history: Optional[List[ChatMessage]]) -> str:
        """Método de compatibilidad - delegar al prompt builder"""
        return self.modular_client.prompt_builder._build_smart_context_info(context, history)
    
    def _build_conversation_history(self, conversation_history: Optional[List[ChatMessage]]) -> str:
        """Método de compatibilidad - delegar al prompt builder"""
        return self.modular_client.prompt_builder._build_conversation_history(conversation_history)
    
    def _get_continuity_instruction(self, history: Optional[List[ChatMessage]], context: Optional[ChatContext]) -> str:
        """Método de compatibilidad - delegar al prompt builder"""
        return self.modular_client.prompt_builder._get_continuity_instruction(history, context)
    
    # === UTILIDADES ===
    
    async def get_server_info(self) -> Dict:
        """Obtener información del servidor"""
        return await self.modular_client.get_server_info()
    
    async def test_connection(self) -> Dict:
        """Test de conexión básico"""
        return await self.modular_client.connection_manager.test_connection()
    
    def get_config(self) -> OllamaConfig:
        """Obtener configuración actual"""
        return self.modular_client.connection_manager.get_config()


# === EXPORTS PARA COMPATIBILIDAD TOTAL ===

# Re-exportar clases principales para compatibilidad
__all__ = [
    'OllamaClient',
    'OllamaConfig', 
    'OllamaResponse',
    'ChatMessage',
    'ChatContext'
]

# Mantener imports directos disponibles
from .ollama_connection_manager import OllamaConfig
from .ollama_response_processor import OllamaResponse
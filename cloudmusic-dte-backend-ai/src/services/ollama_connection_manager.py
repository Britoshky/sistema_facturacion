"""
Ollama Connection Manager - Gestión de conexiones y comunicación básica
Maneja configuración, health checks, modelos y conexiones HTTP con Ollama
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

import httpx
from loguru import logger
from pydantic import BaseModel


class OllamaConfig(BaseModel):
    """Configuración del cliente Ollama optimizada para conversación inteligente"""
    host: str = "http://localhost:11434"
    model: str = "llama3.2:3b"  # Modelo según informe académico
    timeout: int = 60  # Tiempo suficiente para respuestas contextuales elaboradas
    context_size: int = 12288  # Contexto extendido para mejor memoria conversacional
    temperature: float = 0.4  # Balance entre creatividad y precisión
    max_tokens: int = 2048  # Respuestas más extensas para explicaciones completas
    top_p: float = 0.85  # Diversidad balanceada para conversaciones naturales
    repeat_penalty: float = 1.15  # Penalty más fuerte contra repetición


class OllamaConnectionManager:
    """Gestor de conexiones y operaciones básicas con Ollama"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client: Optional[httpx.AsyncClient] = None
        self._connection_pool: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Establecer conexión con Ollama"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        logger.info(f"🔗 Conexión Ollama establecida: {self.config.host}")
    
    async def disconnect(self):
        """Cerrar conexión con Ollama"""
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.info("🔌 Conexión Ollama cerrada")
    
    async def ensure_connected(self):
        """Asegurar que la conexión esté establecida"""
        if self.client is None:
            await self.connect()
    
    async def health_check(self) -> bool:
        """Verificar estado de salud de Ollama"""
        await self.ensure_connected()
        
        try:
            response = await self.client.get(f"{self.config.host}/api/tags")
            is_healthy = response.status_code == 200
            
            if is_healthy:
                logger.info("✅ Ollama health check: OK")
            else:
                logger.warning(f"⚠️ Ollama health check failed: {response.status_code}")
                
            return is_healthy
            
        except Exception as e:
            logger.error(f"❌ Ollama health check error: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        await self.ensure_connected()
        
        try:
            response = await self.client.get(f"{self.config.host}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            
            logger.info(f"📋 Modelos disponibles: {models}")
            return models
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo modelos: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Descargar un modelo específico"""
        await self.ensure_connected()
        
        try:
            logger.info(f"⬇️ Descargando modelo: {model_name}")
            
            response = await self.client.post(
                f"{self.config.host}/api/pull",
                json={"name": model_name},
                timeout=300  # Timeout extendido para descarga
            )
            response.raise_for_status()
            
            logger.info(f"✅ Modelo {model_name} descargado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error descargando modelo {model_name}: {e}")
            return False
    
    async def model_exists(self, model_name: str) -> bool:
        """Verificar si un modelo específico existe"""
        models = await self.list_models()
        return model_name in models
    
    async def ensure_model_available(self, model_name: Optional[str] = None) -> bool:
        """Asegurar que el modelo esté disponible"""
        target_model = model_name or self.config.model
        
        # Verificar si el modelo ya existe
        if await self.model_exists(target_model):
            logger.info(f"✅ Modelo {target_model} ya disponible")
            return True
        
        # Intentar descargar el modelo
        logger.info(f"📥 Modelo {target_model} no encontrado, descargando...")
        return await self.pull_model(target_model)
    
    async def generate_raw(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict:
        """Generar respuesta raw de Ollama sin procesamiento"""
        await self.ensure_connected()
        
        try:
            target_model = model or self.config.model
            
            # Asegurar que el modelo esté disponible
            if not await self.ensure_model_available(target_model):
                raise Exception(f"Modelo {target_model} no disponible")
            
            # Preparar payload
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": self.config.temperature,
                    "num_ctx": self.config.context_size,
                    "num_predict": self.config.max_tokens,
                    "top_p": self.config.top_p,
                    "repeat_penalty": self.config.repeat_penalty,
                    **kwargs  # Permitir overrides
                }
            }
            
            # Realizar solicitud
            logger.debug(f"🔄 Generando con modelo {target_model}")
            response = await self.client.post(
                f"{self.config.host}/api/generate",
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Log básico del resultado
            if result.get("done"):
                logger.info(f"✅ Respuesta generada: {len(result.get('response', ''))} chars")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            raise e
    
    async def get_server_info(self) -> Dict:
        """Obtener información del servidor Ollama"""
        await self.ensure_connected()
        
        try:
            # Información básica via tags
            tags_response = await self.client.get(f"{self.config.host}/api/tags")
            tags_response.raise_for_status()
            tags_data = tags_response.json()
            
            # Compilar información
            server_info = {
                "host": self.config.host,
                "status": "connected" if tags_response.status_code == 200 else "error",
                "models_count": len(tags_data.get("models", [])),
                "available_models": [m["name"] for m in tags_data.get("models", [])],
                "default_model": self.config.model,
                "config": {
                    "timeout": self.config.timeout,
                    "context_size": self.config.context_size,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Server info: {server_info['models_count']} models available")
            return server_info
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo info del servidor: {e}")
            return {"status": "error", "error": str(e)}
    
    # === UTILIDADES ===
    
    def get_config(self) -> OllamaConfig:
        """Obtener configuración actual"""
        return self.config
    
    def update_config(self, **kwargs):
        """Actualizar configuración"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"🔧 Config actualizada: {key} = {value}")
    
    async def test_connection(self) -> Dict:
        """Test completo de conexión"""
        test_results = {
            "connection": False,
            "health_check": False,
            "models_available": False,
            "default_model_ready": False,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test conexión básica
            await self.connect()
            test_results["connection"] = True
            
            # Test health check
            test_results["health_check"] = await self.health_check()
            
            # Test modelos disponibles
            models = await self.list_models()
            test_results["models_available"] = len(models) > 0
            
            # Test modelo por defecto
            test_results["default_model_ready"] = await self.model_exists(self.config.model)
            
            # Resultado general
            all_passed = all(test_results[k] for k in test_results if k != "timestamp")
            test_results["overall_status"] = "✅ PASS" if all_passed else "❌ FAIL"
            
            logger.info(f"🧪 Test conexión Ollama: {test_results['overall_status']}")
            
        except Exception as e:
            test_results["error"] = str(e)
            test_results["overall_status"] = "❌ ERROR"
            logger.error(f"❌ Error en test conexión: {e}")
        
        return test_results
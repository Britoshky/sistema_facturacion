"""
Ollama Modular Client - Servicio coordinador de la arquitectura Ollama modular
Orquesta todos los componentes especializados manteniendo la interfaz pública original
"""

from typing import Dict, List, Optional, Union
from datetime import datetime

from loguru import logger

from .ollama_connection_manager import OllamaConnectionManager, OllamaConfig
from .ollama_prompt_builder import OllamaPromptBuilder  
from .ollama_response_processor import OllamaResponseProcessor, OllamaResponse

try:
    from ..contracts.ai_types import ChatMessage, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatMessage, ChatContext


class OllamaModularClient:
    """Cliente Ollama modular que coordina todos los componentes especializados"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        # Componentes especializados
        self.connection_manager = OllamaConnectionManager(config)
        self.prompt_builder = OllamaPromptBuilder()
        self.response_processor = OllamaResponseProcessor()
        
        # Referencias de compatibilidad
        self.config = self.connection_manager.config
        self.client = None  # Se expondrá tras conexión
    
    # === CONTEXT MANAGER SUPPORT ===
    
    async def __aenter__(self):
        await self.connection_manager.connect()
        self.client = self.connection_manager.client
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connection_manager.disconnect()
    
    # === MÉTODOS PRINCIPALES ===
    
    async def health_check(self) -> bool:
        """Verificar estado de salud de Ollama"""
        return await self.connection_manager.health_check()
    
    async def list_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        return await self.connection_manager.list_models()
    
    async def pull_model(self, model_name: str) -> bool:
        """Descargar un modelo específico"""
        return await self.connection_manager.pull_model(model_name)
    
    async def generate_response(
        self,
        user_prompt: str,
        context: Optional[ChatContext] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> OllamaResponse:
        """Generar respuesta conversacional inteligente con procesamiento completo"""
        
        try:
            logger.info(f"🚀 Generando respuesta para prompt: {user_prompt[:50]}...")
            
            # 1. Construir prompt contextual inteligente
            contextual_prompt = self.prompt_builder.build_contextual_prompt(
                user_prompt, context, system_prompt, conversation_history
            )
            
            # 2. Generar respuesta raw via connection manager
            raw_response = await self.connection_manager.generate_raw(
                contextual_prompt, model, **kwargs
            )
            
            # 3. Procesar y limpiar respuesta
            processed_response = self.response_processor.process_raw_response(raw_response)
            
            # 4. Validar calidad
            validation = self.response_processor.validate_response(processed_response)
            
            if not validation["is_valid"]:
                logger.warning(f"⚠️ Respuesta de baja calidad: {validation['issues']}")
                # En producción, podríamos regenerar automáticamente
            
            logger.info(f"✅ Respuesta generada - Calidad: {processed_response.quality_score:.2f}")
            return processed_response
            
        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            # Respuesta de fallback
            return OllamaResponse(
                content=f"Lo siento, hubo un problema generando la respuesta. Error: {str(e)}",
                model=model or self.config.model,
                created_at=datetime.now(),
                done=True,
                quality_score=0.0
            )
    
    # === MÉTODOS ESPECIALIZADOS ===
    
    async def generate_calculation_response(
        self,
        calculation_query: str,
        context: Optional[ChatContext] = None
    ) -> OllamaResponse:
        """Generar respuesta especializada para cálculos matemáticos/IVA"""
        
        # Usar prompt builder especializado
        prompt = self.prompt_builder.build_calculation_prompt(calculation_query, context)
        
        # Generar con parámetros optimizados para cálculos
        raw_response = await self.connection_manager.generate_raw(
            prompt,
            temperature=0.1,  # Muy baja para precisión máxima
            top_p=0.5         # Reducir creatividad
        )
        
        return self.response_processor.process_raw_response(raw_response)
    
    async def generate_dte_response(
        self,
        dte_query: str,
        context: Optional[ChatContext] = None
    ) -> OllamaResponse:
        """Generar respuesta especializada para consultas DTE"""
        
        # Usar prompt builder especializado
        prompt = self.prompt_builder.build_dte_prompt(dte_query, context)
        
        # Generar con parámetros balanceados para información técnica
        raw_response = await self.connection_manager.generate_raw(
            prompt,
            temperature=0.3,  # Baja pero permite algo de elaboración
            top_p=0.8
        )
        
        return self.response_processor.process_raw_response(raw_response)
    
    async def analyze_document_content(
        self,
        document_text: str,
        analysis_type: str = "general",
        context: Optional[ChatContext] = None
    ) -> Dict:
        """Analizar contenido de documento usando Ollama"""
        
        try:
            # Construir prompt de análisis
            analysis_prompt = f"""Analiza el siguiente documento de tipo '{analysis_type}':

DOCUMENTO:
{document_text[:2000]}  # Limitar para evitar tokens excesivos

PROPORCIONA:
1. Tipo de documento detectado
2. Información clave extraída
3. Posibles errores o problemas
4. Recomendaciones de mejora

Responde en formato estructurado y claro."""
            
            # Generar análisis
            response = await self.generate_response(
                analysis_prompt, 
                context,
                system_prompt="Eres un especialista en análisis de documentos DTE de Chile."
            )
            
            # Estructurar resultado
            analysis_result = {
                "document_type": analysis_type,
                "analysis": response.content,
                "quality_score": response.quality_score,
                "extracted_calculations": self.response_processor.extract_calculations_from_response(response.content),
                "dte_references": self.response_processor.extract_dte_references(response.content),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📄 Documento analizado: {analysis_type}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Error analizando documento: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    # === MÉTODOS DE GESTIÓN ===
    
    async def get_server_info(self) -> Dict:
        """Obtener información completa del servidor y configuración"""
        return await self.connection_manager.get_server_info()
    
    async def test_full_pipeline(self) -> Dict:
        """Test completo del pipeline modular"""
        
        test_results = {
            "connection_test": {},
            "prompt_builder_test": {},
            "response_processor_test": {},
            "integration_test": {},
            "overall_status": "unknown",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test 1: Connection Manager
            test_results["connection_test"] = await self.connection_manager.test_connection()
            
            # Test 2: Prompt Builder  
            test_prompt = self.prompt_builder.build_contextual_prompt(
                "Hola, soy un test", None, None, None
            )
            test_results["prompt_builder_test"] = {
                "status": "✅ OK" if len(test_prompt) > 100 else "❌ FAIL",
                "prompt_length": len(test_prompt)
            }
            
            # Test 3: Response Processor
            mock_response = {
                "response": "Esta es una respuesta de test para validar el procesador.",
                "model": "test",
                "done": True
            }
            processed = self.response_processor.process_raw_response(mock_response)
            test_results["response_processor_test"] = {
                "status": "✅ OK" if processed.quality_score > 0 else "❌ FAIL",
                "quality_score": processed.quality_score
            }
            
            # Test 4: Integración completa (si conexión OK)
            if test_results["connection_test"].get("overall_status") == "✅ PASS":
                try:
                    integration_response = await self.generate_response("Test de integración")
                    test_results["integration_test"] = {
                        "status": "✅ OK",
                        "response_length": len(integration_response.content),
                        "quality": integration_response.quality_score
                    }
                except Exception as e:
                    test_results["integration_test"] = {
                        "status": "❌ FAIL",
                        "error": str(e)
                    }
            else:
                test_results["integration_test"] = {
                    "status": "⏭️ SKIP",
                    "reason": "Connection test failed"
                }
            
            # Status general
            all_tests_ok = all(
                test.get("status", "").startswith("✅") 
                for test in test_results.values() 
                if isinstance(test, dict) and "status" in test
            )
            
            test_results["overall_status"] = "✅ PASS" if all_tests_ok else "❌ FAIL"
            
            logger.info(f"🧪 Test pipeline completo: {test_results['overall_status']}")
            
        except Exception as e:
            test_results["overall_status"] = "❌ ERROR"
            test_results["error"] = str(e)
            logger.error(f"❌ Error en test pipeline: {e}")
        
        return test_results
    
    # === UTILIDADES Y COMPATIBILIDAD ===
    
    def get_component_info(self) -> Dict:
        """Obtener información de todos los componentes"""
        return {
            "connection_manager": {
                "config": self.connection_manager.config.model_dump(),
                "connected": self.connection_manager.client is not None
            },
            "prompt_builder": {
                "default_system_length": len(self.prompt_builder.default_system_prompt),
                "available_builders": ["contextual", "calculation", "dte", "greeting"]
            },
            "response_processor": {
                "min_length": self.response_processor.min_response_length,
                "max_length": self.response_processor.max_response_length,
                "quality_thresholds": self.response_processor.quality_thresholds
            },
            "modular_client": {
                "version": "1.0.0",
                "components": 3,
                "status": "active"
            }
        }
    
    # Métodos de compatibilidad con interfaz original
    def _clean_response_content(self, content: str) -> str:
        """Método de compatibilidad - delegar al response processor"""
        return self.response_processor._clean_response_content(content)
    
    def _analyze_user_intent(self, prompt: str) -> str:
        """Método de compatibilidad - delegar al prompt builder"""
        return self.prompt_builder._analyze_user_intent(prompt)
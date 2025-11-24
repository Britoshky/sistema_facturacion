"""
Cliente Ollama Mejorado para interacción conversacional inteligente
Implementa el modelo Llama 3.2 3B con capacidades de contexto avanzado
Optimizado para coherencia conversacional y personalización por usuario
"""

import asyncio
import json
from typing import Dict, List, Optional, Union
from datetime import datetime

import httpx
from loguru import logger
from pydantic import BaseModel

try:
    from ..contracts.ai_types import ChatMessage, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatMessage, ChatContext


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


class OllamaResponse(BaseModel):
    """Respuesta de Ollama"""
    content: str
    model: str
    created_at: datetime
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaClient:
    """Cliente para interactuar con Ollama local"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client = httpx.AsyncClient(timeout=self.config.timeout)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Verificar disponibilidad de Ollama"""
        try:
            response = await self.client.get(f"{self.config.host}/api/version")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """Listar modelos disponibles"""
        try:
            response = await self.client.get(f"{self.config.host}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Descargar modelo si no está disponible"""
        try:
            payload = {"name": model_name}
            response = await self.client.post(
                f"{self.config.host}/api/pull",
                json=payload,
                timeout=300  # 5 minutos para descarga
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[ChatContext] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> OllamaResponse:
        """Generar respuesta IA contextual"""
        
        # Construir prompt contextual para DTE
        full_prompt = self._build_contextual_prompt(
            prompt, context, system_prompt, conversation_history
        )
        
        # Ajustar temperatura dinámicamente según el tipo de consulta
        temp = self.config.temperature
        
        # Detección mejorada de cálculos matemáticos
        is_math = (
            (context and hasattr(context, 'message_intent') and context.message_intent == 'math_calculation') or
            any(word in prompt.lower() for word in ["cuanto", "cuánto", "19%", "iva", "calcular", "calcula", "cálculo", "100.000", "100000", "$", "peso", "neto", "bruto", "incluido", "+", "-", "*", "/", "suma", "resta", "multiplica", "divide", "total"])
        )
        
        # Detección de consultas técnicas que requieren precisión
        is_technical = any(word in prompt.lower() for word in ["dte", "xml", "sii", "caf", "folio", "certificado"])
        
        if is_math:
            temp = 0.05  # Máxima precisión para cálculos
        elif is_technical:
            temp = 0.15  # Alta precisión para consultas técnicas
        elif context and hasattr(context, 'conversation_length') and context.conversation_length > 5:
            temp = 0.25  # Ligera variación para conversaciones largas
        else:
            temp = self.config.temperature  # Temperatura normal
        
        # Configuración de parámetros optimizada para conversación
        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "options": {
                "temperature": temp,
                "num_ctx": self.config.context_size,
                "num_predict": self.config.max_tokens,
                "top_p": 0.9 if temp > 0.2 else 0.7,  # Ajuste dinámico de top_p
                "repeat_penalty": 1.1,  # Evitar repetición
                "presence_penalty": 0.6,  # Fomentar variedad en respuestas
                "frequency_penalty": 0.7,  # Reducir repetición de frases
                "seed": -1,  # Randomización para variedad
                "stop": [
                    "Usuario:", "👤", "user:", "USER:", "USUARIO:",
                    "\nUsuario:", "\n👤", "Human:", "Humano:"
                ],  # Tokens de parada para evitar confusión
                "mirostat": 2,  # Mejor control de coherencia
                "mirostat_tau": 5.0,  # Parámetro de coherencia
                "mirostat_eta": 0.1  # Tasa de aprendizaje
            },
            "stream": False
        }
        
        try:
            logger.debug(f"Sending request to Ollama: {self.config.model}")
            logger.debug(f"URL: {self.config.host}/api/generate")
            response = await self.client.post(
                f"{self.config.host}/api/generate",
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Post-procesar la respuesta para mejorar calidad
                ai_content = data.get("response", "").strip()
                
                # Limpiar respuesta si tiene patrones problemáticos
                ai_content = self._clean_response_content(ai_content)
                
                # Log para debugging
                logger.debug(f"AI response length: {len(ai_content)} chars")
                logger.debug(f"Temperature used: {temp}")
                
                return OllamaResponse(
                    content=ai_content,
                    model=data.get("model", self.config.model),
                    created_at=datetime.now(),
                    done=data.get("done", True),
                    total_duration=data.get("total_duration"),
                    load_duration=data.get("load_duration"),
                    prompt_eval_count=data.get("prompt_eval_count"),
                    eval_count=data.get("eval_count")
                )
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise Exception(f"Ollama API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating response: {type(e).__name__}: {str(e)}")
            logger.error(f"Ollama host: {self.config.host}")
            logger.error(f"Model: {self.config.model}")
            # Respuesta de fallback contextual
            fallback_content = "Lo siento, ocurrió un error procesando tu consulta. Por favor intenta nuevamente."
            
            # Personalizar mensaje de error si hay contexto disponible
            if context and hasattr(context, 'user_name') and context.user_name:
                fallback_content = f"Disculpa {context.user_name}, ocurrió un error procesando tu consulta. Por favor intenta nuevamente."
            
            return OllamaResponse(
                content=fallback_content,
                model=self.config.model,
                created_at=datetime.now(),
                done=True
            )
    
    def _build_contextual_prompt(
        self,
        user_prompt: str,
        context: Optional[ChatContext],
        system_prompt: Optional[str],
        conversation_history: Optional[List[ChatMessage]]
    ) -> str:
        """Construir prompt contextual inteligente y conversacional mejorado"""
        
        # Sistema prompt conversacional mejorado
        default_system = """Eres CloudMusic IA, un asistente inteligente, amigable y especializado en DTE (Documentos Tributarios Electrónicos) de Chile.

PERSONALIDAD Y COMPORTAMIENTO:
- Conversacional y empático - mantiene diálogo natural y coherente
- Adaptable - ajusta respuestas según el contexto y usuario
- Proactivo - ofrece ayuda adicional relevante
- Machine Learning - aprende y se adapta del contexto conversacional
- PRECISO en cálculos matemáticos y tributarios
- COHERENTE - no se presenta repetidamente en la misma conversación

CAPACIDADES PRINCIPALES:
1. CONVERSACIÓN CONTEXTUAL: Mantiene coherencia, evita repeticiones, construye sobre mensajes anteriores
2. CÁLCULOS MATEMÁTICOS Y DE IVA PRECISOS: 
   - IVA Chile 19% - FÓRMULAS EXACTAS:
   - CON IVA INCLUIDO: Valor Neto = Precio ÷ 1.19 | IVA = Precio - Valor Neto
   - SIN IVA (agregar): IVA = Precio × 0.19 | Total = Precio + IVA
   - Ejemplo: $100,000 CON IVA → Neto = $84,034 | IVA = $15,966
3. ESPECIALIZACIÓN DTE CHILENA: 
   - Normativa SII actualizada
   - Facturación electrónica, boletas, notas de crédito/débito
   - Validación XML, folios CAF, certificados digitales
   - Resolución de errores y consultas técnicas
4. PERSONALIZACIÓN: Se adapta al estilo del usuario y contexto empresarial

REGLAS DE COHERENCIA CONVERSACIONAL:
- NO te presentes si ya lo hiciste en esta conversación
- REFERENCIA mensajes anteriores cuando sea relevante
- CONSTRUYE sobre la conversación existente progresivamente
- MANTIENE el tono y nivel establecido en la conversación
- EVITA repetir información ya proporcionada
- ADAPTA respuestas según el turno de conversación

INSTRUCCIONES DE RESPUESTA:
- Primera interacción: Saludo cordial con presentación breve
- Conversación en curso: Respuesta directa sin presentaciones repetidas
- Cálculo matemático: PASO A PASO, fórmulas exactas, verificación final
- Consulta IVA: Identificar si tiene IVA incluido, luego calcular correctamente
- Consulta DTE: Información técnica precisa y práctica
- Seguimiento: Construir sobre respuestas anteriores

Responde de manera contextual, coherente y profesional."""

        # Usar el system prompt proporcionado (ya personalizado) o el default
        system = system_prompt or default_system
        
        # Construir contexto conversacional inteligente
        context_info = self._build_smart_context_info(context, conversation_history)
        
        # Historial conversacional optimizado
        history = self._build_conversation_history(conversation_history)
        
        # Análisis del prompt actual
        prompt_analysis = self._analyze_user_intent(user_prompt)
        intent_info = f"\nANÁLISIS DEL MENSAJE ACTUAL: {prompt_analysis}"
        
        # Instrucción de continuidad conversacional
        continuity_instruction = self._get_continuity_instruction(conversation_history, context)
        
        # Prompt final optimizado para continuidad
        full_prompt = f"{system}{context_info}{history}{intent_info}{continuity_instruction}\n\n👤 USUARIO: {user_prompt}\n\n🤖 CLOUDMUSIC IA:"
        
        return full_prompt
    
    def _analyze_user_intent(self, prompt: str) -> str:
        """Analizar intención del usuario para respuesta más precisa"""
        
        prompt_lower = prompt.lower().strip()
        
        # Detectar tipo de consulta con patrones mejorados
        if any(word in prompt_lower for word in ["hola", "buenos", "hi", "hello", "saludos"]):
            return "Saludo/Inicio de conversación"
        elif any(word in prompt_lower for word in ["gracias", "perfecto", "excelente", "ok", "entiendo"]):
            return "Confirmación/Agradecimiento"
        elif any(word in prompt_lower for word in ["ayuda", "help", "no entiendo", "explica", "no sé"]):
            return "Solicitud de ayuda/Explicación"
        elif any(word in prompt_lower for word in ["cuanto", "cuánto", "calcular", "calcula", "cálculo", "19%", "iva", "porcentaje", "%", "impuesto", "neto", "bruto", "con iva", "sin iva", "incluido", "suma", "resta", "multiplica", "divide", "total", "valor", "precio", "100.000", "100000", "pesos", "$"]):
            return "CÁLCULO MATEMÁTICO/IVA - Usar precisión máxima"
        elif any(word in prompt_lower for word in ["dte", "sii", "factura", "boleta", "xml", "caf", "folio", "certificado", "timbre"]):
            return "Consulta técnica DTE"
        elif any(word in prompt_lower for word in ["cómo", "qué", "cuándo", "dónde", "por qué", "para qué"]):
            return "Pregunta informativa"
        elif any(word in prompt_lower for word in ["problema", "error", "falla", "no funciona", "ayuda"]):
            return "Resolución de problemas"
        elif any(word in prompt_lower for word in ["necesito", "quiero", "busco", "requiero"]):
            return "Solicitud de información específica"
        else:
            return "Conversación general"
    
    def _build_smart_context_info(self, context: Optional[ChatContext], history: Optional[List[ChatMessage]]) -> str:
        """Construir información de contexto inteligente"""
        if not context:
            return ""
        
        context_lines = ["\nCONTEXTO DE LA SESIÓN:"]
        
        # Información del usuario (evitar repetir si ya se mencionó en el historial)
        user_mentioned = False
        if history:
            # Verificar si ya se mencionó el nombre del usuario en los últimos mensajes
            recent_ai_messages = [msg.content for msg in history[-3:] if msg.role == "assistant"]
            user_name = getattr(context, 'user_name', '')
            if user_name and any(user_name in msg for msg in recent_ai_messages):
                user_mentioned = True
        
        if hasattr(context, 'user_name') and context.user_name and not user_mentioned:
            context_lines.append(f"- Usuario: {context.user_name}")
        
        # Información de empresa
        if hasattr(context, 'company_name') and context.company_name != "Tu empresa":
            context_lines.append(f"- Empresa: {context.company_name}")
        
        # Intención detectada
        if hasattr(context, 'message_intent'):
            intent = context.message_intent
            if intent == 'math_calculation':
                context_lines.append("- ⚠️ ATENCIÓN: Consulta de cálculo matemático - usar máxima precisión")
                context_lines.append("- IVA CHILE: Si 'con IVA' → Neto = Precio ÷ 1.19 | Si 'sin IVA' → Total = Precio × 1.19")
            elif intent not in ['general', 'greeting']:
                context_lines.append(f"- Intención: {intent}")
        
        # Tipo de contexto si es especializado
        if hasattr(context, 'context_type') and context.context_type != "general":
            context_lines.append(f"- Modo: {context.context_type}")
        
        # Estado de conversación
        if hasattr(context, 'conversation_length'):
            length = context.conversation_length
            if length > 10:
                context_lines.append("- Estado: Conversación avanzada (mantener coherencia)")
            elif length > 5:
                context_lines.append("- Estado: Conversación activa")
            elif length > 1:
                context_lines.append("- Estado: Conversación en curso")
        
        return "\n".join(context_lines) if len(context_lines) > 1 else ""
    
    def _build_conversation_history(self, conversation_history: Optional[List[ChatMessage]]) -> str:
        """Construir historial conversacional optimizado"""
        if not conversation_history or len(conversation_history) == 0:
            return ""
        
        # Tomar los últimos 8 mensajes para contexto (4 intercambios)
        recent_messages = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
        
        if len(recent_messages) == 0:
            return ""
        
        history_lines = ["\nHISTORIAL CONVERSACIONAL:"]
        
        for i, msg in enumerate(recent_messages):
            role_indicator = "👤" if msg.role == "user" else "🤖"
            
            # Truncar mensajes muy largos
            content = msg.content
            if len(content) > 150:
                content = content[:147] + "..."
            
            # Añadir número de turno para claridad
            turn = i + 1
            history_lines.append(f"{role_indicator} T{turn}: {content}")
        
        return "\n".join(history_lines)
    
    def _get_continuity_instruction(self, history: Optional[List[ChatMessage]], context: Optional[ChatContext]) -> str:
        """Obtener instrucciones de continuidad conversacional"""
        if not history or len(history) < 2:
            return "\n\nINSTRUCCIÓN: Primera interacción - saludo cordial y presentación breve."
        
        # Analizar el estado de la conversación
        last_ai_message = ""
        for msg in reversed(history):
            if msg.role == "assistant":
                last_ai_message = msg.content.lower()
                break
        
        instructions = ["\n\nINSTRUCCIONES DE CONTINUIDAD:"]
        
        # Evitar re-presentación
        if "cloudmusic" in last_ai_message or "soy" in last_ai_message:
            instructions.append("- NO te presentes de nuevo - ya lo hiciste")
        
        # Construir sobre conversación anterior
        if len(history) > 3:
            instructions.append("- CONSTRUYE sobre la conversación anterior")
            instructions.append("- MANTIENE coherencia con respuestas previas")
        
        # Si la última respuesta fue una pregunta
        if "?" in last_ai_message:
            instructions.append("- Tu última respuesta hizo una pregunta - el usuario puede estar respondiendo")
        
        # Si la conversación es sobre cálculos
        if any(word in last_ai_message for word in ["cálculo", "iva", "$", "peso"]):
            instructions.append("- CONTEXTO: Ya estamos hablando de cálculos - mantener precisión")
        
        instructions.append("- RESPONDE de forma directa y contextual")
        
        return "\n".join(instructions)
    
    async def analyze_document_content(
        self,
        document_data: Dict,
        analysis_type: str
    ) -> Dict[str, Union[str, float, List[str]]]:
        """Analizar contenido de documento DTE"""
        
        analysis_prompt = f"""
Analiza el siguiente documento DTE tipo {analysis_type}:
{json.dumps(document_data, indent=2)}

Proporciona:
1. Posibles anomalías o inconsistencias
2. Puntuación de riesgo (0.0 a 1.0)
3. Recomendaciones específicas
4. Nivel de confianza del análisis

Responde en formato JSON con las claves: anomalies, risk_score, recommendations, confidence.
"""
        
        response = await self.generate_response(analysis_prompt)
        
        try:
            # Intentar extraer JSON de la respuesta
            content = response.content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            result = json.loads(content)
            return result
        except:
            # Fallback si no se puede parsear JSON
            return {
                "anomalies": ["Análisis manual requerido"],
                "risk_score": 0.5,
                "recommendations": ["Revisar documento manualmente"],
                "confidence": 0.6
            }
    
    def _clean_response_content(self, content: str) -> str:
        """Limpiar contenido de respuesta para mejorar calidad"""
        if not content:
            return content
        
        # Remover patrones problemáticos comunes
        cleaned = content
        
        # Remover repeticiones de presentación en respuestas largas
        if "CloudMusic IA" in cleaned and cleaned.count("CloudMusic IA") > 1:
            # Mantener solo la primera mención
            parts = cleaned.split("CloudMusic IA")
            if len(parts) > 2:
                cleaned = parts[0] + "CloudMusic IA" + "".join(parts[1:])
        
        # Limpiar espacios excesivos
        cleaned = ' '.join(cleaned.split())
        
        # Remover líneas vacías excesivas
        lines = cleaned.split('\n')
        clean_lines = []
        empty_count = 0
        
        for line in lines:
            if line.strip():
                clean_lines.append(line)
                empty_count = 0
            else:
                empty_count += 1
                if empty_count <= 1:  # Permitir máximo una línea vacía
                    clean_lines.append(line)
        
        cleaned = '\n'.join(clean_lines)
        
        return cleaned.strip()
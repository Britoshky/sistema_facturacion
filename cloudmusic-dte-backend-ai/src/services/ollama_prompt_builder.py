"""
Ollama Prompt Builder - Constructor inteligente de prompts contextuales
Maneja análisis de intención, construcción conversacional y personalización
"""

from typing import Dict, List, Optional
from loguru import logger

try:
    from ..contracts.ai_types import ChatMessage, ChatContext
except ImportError:
    from src.contracts.ai_types import ChatMessage, ChatContext


class OllamaPromptBuilder:
    """Constructor especializado de prompts conversacionales inteligentes"""
    
    def __init__(self):
        self.default_system_prompt = self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Prompt de sistema conversacional mejorado por defecto"""
        return """Eres CloudMusic IA, un asistente inteligente, amigable y especializado en DTE (Documentos Tributarios Electrónicos) de Chile.

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
    
    def build_contextual_prompt(
        self,
        user_prompt: str,
        context: Optional[ChatContext] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> str:
        """Construir prompt contextual inteligente y conversacional mejorado"""
        
        # Usar sistema prompt proporcionado o el default
        system = system_prompt or self.default_system_prompt
        
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
        
        logger.debug(f"🔨 Prompt construido - Intent: {prompt_analysis}")
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
        """Construir información de contexto inteligente y relevante"""
        
        if not context:
            return ""
        
        context_parts = ["\n=== CONTEXTO DEL USUARIO ==="]
        
        # Información básica del usuario/empresa
        if hasattr(context, 'user_id') and context.user_id:
            context_parts.append(f"ID Usuario: {context.user_id}")
        
        if hasattr(context, 'company_id') and context.company_id:
            context_parts.append(f"ID Empresa: {context.company_id}")
        
        if hasattr(context, 'company_name') and context.company_name:
            context_parts.append(f"Empresa: {context.company_name}")
        
        if hasattr(context, 'user_role') and context.user_role:
            context_parts.append(f"Rol: {context.user_role}")
        
        # Contexto conversacional previo (si existe historial)
        if history and len(history) > 0:
            context_parts.append("📝 CONTINUANDO CONVERSACIÓN EXISTENTE")
            
            # Contar mensajes por rol
            user_messages = len([m for m in history if m.role == "user"])
            ai_messages = len([m for m in history if m.role == "assistant"])
            
            context_parts.append(f"Mensajes previos: {user_messages} del usuario, {ai_messages} de CloudMusic IA")
            
            # Último tema/consulta si es relevante
            if history:
                last_user_msg = None
                for msg in reversed(history):
                    if msg.role == "user":
                        last_user_msg = msg
                        break
                
                if last_user_msg:
                    last_intent = self._analyze_user_intent(last_user_msg.content)
                    context_parts.append(f"Último tema tratado: {last_intent}")
        else:
            context_parts.append("📝 PRIMERA INTERACCIÓN")
        
        # Información adicional específica del contexto
        if hasattr(context, 'additional_info') and context.additional_info:
            context_parts.append("Información adicional:")
            if isinstance(context.additional_info, dict):
                for key, value in context.additional_info.items():
                    if value:  # Solo incluir valores no vacíos
                        context_parts.append(f"  - {key}: {value}")
            else:
                context_parts.append(f"  - {context.additional_info}")
        
        context_parts.append("=== FIN CONTEXTO ===\n")
        
        result = "\n".join(context_parts)
        logger.debug(f"📋 Contexto construido: {len(result)} caracteres")
        return result
    
    def _build_conversation_history(self, conversation_history: Optional[List[ChatMessage]]) -> str:
        """Construir historial conversacional optimizado"""
        
        if not conversation_history or len(conversation_history) == 0:
            return ""
        
        history_parts = ["\n=== HISTORIAL CONVERSACIONAL ==="]
        
        # Limitar historial para evitar contextos muy largos
        recent_history = conversation_history[-8:]  # Últimos 8 mensajes
        
        for i, message in enumerate(recent_history, 1):
            role_emoji = "👤" if message.role == "user" else "🤖"
            role_name = "USUARIO" if message.role == "user" else "CLOUDMUSIC IA"
            
            # Truncar mensajes muy largos para el contexto
            content = message.content
            if len(content) > 200:
                content = content[:200] + "..."
            
            history_parts.append(f"{role_emoji} {role_name}: {content}")
        
        history_parts.append("=== FIN HISTORIAL ===\n")
        
        result = "\n".join(history_parts)
        logger.debug(f"📜 Historial construido: {len(recent_history)} mensajes")
        return result
    
    def _get_continuity_instruction(self, history: Optional[List[ChatMessage]], context: Optional[ChatContext]) -> str:
        """Generar instrucción de continuidad conversacional específica"""
        
        if not history or len(history) == 0:
            return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Primera interacción - saluda cordialmente y preséntate brevemente como CloudMusic IA."
        
        # Analizar el flujo de la conversación
        user_messages = [m for m in history if m.role == "user"]
        ai_messages = [m for m in history if m.role == "assistant"]
        
        # Determinar el tipo de continuidad necesaria
        if len(user_messages) == 1:
            return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Segunda interacción - responde directamente sin presentarte de nuevo, construye sobre la respuesta anterior."
        
        elif len(user_messages) > 1:
            # Analizar la última interacción
            if user_messages:
                last_user_intent = self._analyze_user_intent(user_messages[-1].content)
                
                if "CÁLCULO" in last_user_intent:
                    return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Enfócate en el cálculo matemático preciso PASO A PASO. Verifica el resultado final."
                elif "Confirmación" in last_user_intent or "Agradecimiento" in last_user_intent:
                    return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Responde cordialmente y ofrece ayuda adicional relacionada."
                elif "Consulta técnica" in last_user_intent:
                    return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Proporciona información técnica precisa y práctica sobre DTE."
                else:
                    return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Continúa la conversación naturalmente, construyendo sobre el contexto previo."
        
        return "\n🎯 INSTRUCCIÓN ESPECÍFICA: Mantén coherencia conversacional y evita repetir información ya proporcionada."
    
    # === BUILDERS ESPECIALIZADOS ===
    
    def build_calculation_prompt(
        self,
        calculation_query: str,
        context: Optional[ChatContext] = None
    ) -> str:
        """Construir prompt especializado para cálculos matemáticos/IVA"""
        
        system_calc = """Eres CloudMusic IA, especialista en cálculos matemáticos precisos y DTE Chile.

INSTRUCCIONES PARA CÁLCULOS:
1. Identifica si el valor tiene IVA incluido o no
2. Usa fórmulas EXACTAS para IVA 19% Chile:
   - CON IVA: Neto = Precio ÷ 1.19 | IVA = Precio - Neto  
   - SIN IVA: IVA = Precio × 0.19 | Total = Precio + IVA
3. Muestra PASO A PASO el cálculo
4. Verifica el resultado final
5. Usa formato claro con separadores de miles

RESPONDE SOLO EL CÁLCULO SOLICITADO."""
        
        return self.build_contextual_prompt(
            calculation_query,
            context,
            system_calc
        )
    
    def build_dte_prompt(
        self,
        dte_query: str,
        context: Optional[ChatContext] = None
    ) -> str:
        """Construir prompt especializado para consultas DTE"""
        
        system_dte = """Eres CloudMusic IA, especialista en DTE (Documentos Tributarios Electrónicos) de Chile.

CONOCIMIENTO DTE:
- Normativa SII actualizada
- Facturación electrónica, boletas, notas de crédito/débito  
- XML, folios CAF, certificados digitales
- Resolución de errores técnicos
- Mejores prácticas de implementación

RESPONDE CON:
1. Información técnica precisa
2. Ejemplos prácticos cuando sea útil
3. Referencias a normativa SII relevante
4. Pasos de implementación claros"""
        
        return self.build_contextual_prompt(
            dte_query,
            context,
            system_dte
        )
    
    def build_greeting_prompt(
        self,
        greeting_message: str,
        context: Optional[ChatContext] = None,
        is_first_interaction: bool = True
    ) -> str:
        """Construir prompt especializado para saludos"""
        
        if is_first_interaction:
            system_greeting = """Eres CloudMusic IA, asistente especializado en DTE de Chile.

PRIMERA INTERACCIÓN:
- Saluda cordialmente 
- Preséntate brevemente como CloudMusic IA
- Menciona tus especialidades principales (DTE, cálculos IVA, consultas SII)
- Pregunta en qué puedes ayudar

TONO: Amigable, profesional, conciso."""
        else:
            system_greeting = """Eres CloudMusic IA. Ya te has presentado en esta conversación.

SALUDO DE CONTINUIDAD:
- Responde cordialmente SIN presentarte de nuevo
- Construye sobre la conversación previa
- Mantén el tono establecido

EVITA repetir tu presentación."""
        
        return self.build_contextual_prompt(
            greeting_message,
            context,
            system_greeting
        )
    
    # === UTILIDADES ===
    
    def analyze_prompt_complexity(self, prompt: str) -> Dict:
        """Analizar complejidad y características del prompt"""
        
        analysis = {
            "length": len(prompt),
            "word_count": len(prompt.split()),
            "intent": self._analyze_user_intent(prompt),
            "has_numbers": any(char.isdigit() for char in prompt),
            "has_currency": any(symbol in prompt for symbol in ["$", "peso", "clp"]),
            "has_dte_terms": any(term in prompt.lower() for term in ["dte", "sii", "factura", "boleta", "xml"]),
            "complexity": "simple" if len(prompt.split()) < 10 else "complex"
        }
        
        return analysis
    
    def get_prompt_suggestions(self, intent: str) -> List[str]:
        """Obtener sugerencias de mejora para el prompt según la intención"""
        
        suggestions = []
        
        if "CÁLCULO" in intent:
            suggestions.extend([
                "Especifica si el valor incluye o no IVA",
                "Indica la moneda (pesos chilenos)",
                "Menciona si necesitas el desglose detallado"
            ])
        
        elif "DTE" in intent:
            suggestions.extend([
                "Especifica el tipo de documento (factura, boleta, etc.)",
                "Menciona si tienes algún error específico",
                "Indica si necesitas información técnica o práctica"
            ])
        
        elif "Saludo" in intent:
            suggestions.extend([
                "Menciona tu consulta principal después del saludo",
                "Especifica si eres nuevo usuario de DTE"
            ])
        
        return suggestions
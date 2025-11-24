"""
Constructor de Prompts - Especializado en generar prompts dinámicos y contextuales
"""

from typing import Dict, Any, Optional
from datetime import datetime


class PromptBuilder:
    """Construye prompts dinámicos basados en contexto empresarial"""
    
    def __init__(self):
        self.base_prompts = {
            "general": """Responde DIRECTAMENTE a consultas sobre DTE de Chile con información específica de la empresa.

REGLAS CRÍTICAS:
❌ NUNCA uses: "¡Hola!", "Me alegra", "Soy CloudMusic IA", presentaciones genéricas
✅ SIEMPRE responde directo al punto con datos específicos
✅ USA nombres reales, RUTs exactos, datos verificables
✅ Formato conciso y profesional

CAPACIDADES:
1. Información empresarial precisa (RUT, dirección, contacto)
2. Catálogo productos/servicios con precios exactos
3. Estado DTE (códigos 33, 39, configuraciones)
4. Cálculos tributarios precisos
5. Datos clientes y administradores

FORMATO RESPUESTA:
- Título específico de la consulta
- Datos solicitados directamente  
- Información adicional relevante
- Sin saludos ni presentaciones""",
            
            "technical": """Eres un especialista técnico en sistemas DTE para Chile.

ESPECIALIZACIÓN:
- Implementación técnica de DTE
- Validación de documentos XML
- Integración con SII
- Certificados digitales
- Folios CAF

Responde con precisión técnica usando datos específicos de la empresa.""",
            
            "accounting": """Eres un contador experto en tributación electrónica chilena.

ESPECIALIZACIÓN:
- Normativa tributaria chilena
- Cálculos de IVA (19%)
- Libros contables electrónicos
- Declaraciones al SII
- Procedimientos contables DTE

Usa información específica de la empresa para cálculos y consejos.""",
            
            "legal": """Eres un especialista legal en normativa tributaria chilena.

ESPECIALIZACIÓN:
- Ley de Factura Electrónica
- Resoluciones SII
- Marco regulatorio DTE
- Cumplimiento tributario
- Sanciones y multas

Proporciona asesoría legal específica basada en los datos de la empresa."""
        }
    
    def build_system_prompt(self, prompt_type: str = "general", company_data: Optional[Dict] = None) -> str:
        """Construir prompt del sistema con datos empresariales"""
        base_prompt = self.base_prompts.get(prompt_type, self.base_prompts["general"])
        
        if not company_data:
            return base_prompt
        
        # Agregar contexto empresarial específico
        company_context = self._build_company_context(company_data)
        
        enhanced_prompt = f"""{base_prompt}

{company_context}

IMPORTANTE: Siempre referencia la información específica de la empresa en tus respuestas."""
        
        return enhanced_prompt
    
    def _build_company_context(self, company_data: Dict) -> str:
        """Construir contexto específico de la empresa"""
        context = "INFORMACIÓN DE LA EMPRESA ACTUAL:\n"
        
        # Información básica
        context += f"• EMPRESA: {company_data.get('company_display', 'N/A')}\n"
        context += f"• RUT: {company_data.get('company_rut', 'N/A')}\n"
        context += f"• ADMINISTRADOR: {company_data.get('admin_name', 'N/A')}\n"
        context += f"• EMAIL: {company_data.get('admin_email', 'N/A')}\n"
        
        # Estadísticas
        if company_data.get('total_products'):
            context += f"• PRODUCTOS: {company_data['total_products']} registrados\n"
        
        if company_data.get('total_clients'):
            context += f"• CLIENTES: {company_data['total_clients']} registrados\n"
        
        if company_data.get('top_product'):
            context += f"• PRODUCTO PRINCIPAL: {company_data['top_product']}\n"
        
        return context
    
    def build_business_context(self, business_data: Dict) -> str:
        """Construir contexto empresarial detallado"""
        if not business_data or business_data.get('error'):
            return ""
        
        context = "\nDATOS EMPRESARIALES ESPECÍFICOS:\n"
        
        # Información de la empresa
        if business_data.get('empresa_nombre_completo'):
            context += f"- EMPRESA: {business_data['empresa_nombre_completo']}\n"
        
        if business_data.get('empresa_rut'):
            context += f"- RUT: {business_data['empresa_rut']}\n"
        
        # Información del usuario/administrador
        if business_data.get('usuario_nombre'):
            context += f"- ADMINISTRADOR: {business_data['usuario_nombre']}\n"
        
        if business_data.get('usuario_email'):
            context += f"- EMAIL: {business_data['usuario_email']}\n"
        
        # Estadísticas de documentos
        if business_data.get('total_documentos_exacto'):
            context += f"- DOCUMENTOS: {business_data['total_documentos_exacto']}\n"
        
        if business_data.get('monto_total_formateado'):
            context += f"- MONTO TOTAL: {business_data['monto_total_formateado']}\n"
        
        # Tipos de documentos
        if business_data.get('tipos_documento_codigos'):
            context += f"- TIPOS DTE: {business_data['tipos_documento_codigos']}\n"
        
        # Productos
        if business_data.get('nombres_productos_exactos'):
            productos = business_data['nombres_productos_exactos']
            context += f"- PRODUCTOS: {', '.join(productos[:3])}"
            if len(productos) > 3:
                context += f" (y {len(productos)-3} más)"
            context += "\n"
        
        # Producto más caro
        if business_data.get('producto_mas_caro'):
            context += f"- PRODUCTO PRINCIPAL: {business_data['producto_mas_caro']}\n"
        
        return context
    
    def build_context_prompt(self, user_context: Dict, intent: str) -> str:
        """Método compatible - construir prompt basado en contexto e intención"""
        try:
            # Usar método existente con parámetros convertidos
            company_data = user_context if isinstance(user_context, dict) else {}
            return self.build_system_prompt(intent, company_data)
        except Exception as e:
            print(f"❌ Error construyendo prompt: {e}")
            return self.base_prompts.get("general", "Eres un asistente IA especializado en DTE chilenos.")
    
    def build_conversation_context(self, recent_messages: list, max_messages: int = 5) -> str:
        """Construir contexto de conversación reciente"""
        if not recent_messages:
            return ""
        
        context = "\nCONTEXTO DE CONVERSACIÓN RECIENTE:\n"
        
        # Tomar solo los mensajes más recientes
        messages = recent_messages[-max_messages:] if len(recent_messages) > max_messages else recent_messages
        
        for i, msg in enumerate(messages, 1):
            role = "Usuario" if msg.get('role') == 'user' else "Asistente"
            content = msg.get('content', '')[:100]  # Limitar longitud
            if len(msg.get('content', '')) > 100:
                content += "..."
            
            context += f"{i}. {role}: {content}\n"
        
        return context
    
    def enhance_prompt_with_intent(self, base_prompt: str, intent: str, user_message: str) -> str:
        """Mejorar prompt basado en la intención detectada"""
        intent_instructions = {
            "business_query": "\nINSTRUCCIÓN ESPECÍFICA: Proporciona información empresarial completa y específica. Incluye datos reales de la empresa, RUT, administrador y estadísticas exactas.",
            
            "product_query": "\nINSTRUCCIÓN ESPECÍFICA: Responde con información detallada de productos. Incluye nombres exactos, precios, y datos específicos del catálogo de la empresa.",
            
            "client_query": "\nINSTRUCCIÓN ESPECÍFICA: Proporciona información específica de clientes. Incluye nombres, RUTs y datos de contacto cuando sea apropiado.",
            
            "dte_query": "\nINSTRUCCIÓN ESPECÍFICA: Responde con información técnica sobre documentos DTE. Incluye códigos SII específicos y normativa aplicable.",
            
            "calculation": "\nINSTRUCCIÓN ESPECÍFICA: Realiza cálculos precisos. Muestra el proceso paso a paso y utiliza las tasas tributarias chilenas correctas (IVA 19%).",
            
            "general_query": "\nINSTRUCCIÓN ESPECÍFICA: Responde de manera conversacional pero incluye información específica de la empresa cuando sea relevante."
        }
        
        instruction = intent_instructions.get(intent, intent_instructions["general_query"])
        
        enhanced_prompt = f"""{base_prompt}{instruction}

CONSULTA DEL USUARIO: "{user_message}"

Responde de manera específica y precisa, usando los datos empresariales proporcionados."""
        
        return enhanced_prompt
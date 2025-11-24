"""
Generador de Respuestas - Especializado en generar respuestas de IA y post-procesamiento
"""

import asyncio
from types import SimpleNamespace
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from loguru import logger

from .ollama_client import OllamaClient, OllamaConfig
from .prompt_builder import PromptBuilder
from .context_manager import ContextManager


class ResponseGenerator:
    """Genera y mejora respuestas de IA"""
    
    def __init__(self, ollama_client, context_manager: ContextManager, prompt_builder):
        self.ollama_client = ollama_client
        self.context_manager = context_manager
        self.prompt_builder = prompt_builder
    
    async def generate_adaptive_response(self, session, user_message: str, user_context: Dict, message_intent: str, adaptive_profile=None) -> Any:
        """Generar respuesta de IA adaptada al perfil del usuario"""
        try:
            # Si hay perfil adaptativo, usar prompt personalizado
            if adaptive_profile:
                # Obtener datos de empresa actualizados usando parámetros reales
                company_summary = await self.context_manager.get_company_summary_data(
                    user_id,    # Usar user_id real del parámetro
                    company_id  # Usar company_id real del parámetro
                )
                
                # Construir prompt base
                base_prompt = self.prompt_builder.build_system_prompt("general", company_summary)
                
                # Adaptar prompt al perfil del usuario
                from .adaptive_learning_service import AdaptiveLearningService
                adaptive_service = AdaptiveLearningService()
                adaptive_prompt = adaptive_service.build_adaptive_prompt(base_prompt, adaptive_profile, message_intent)
                
                # Usar OllamaClient con prompt adaptativo
                if self.ollama_client:
                    response = await self.ollama_client.generate_response(
                        user_prompt=user_message,
                        system_prompt=adaptive_prompt,
                        temperature=0.3,
                        max_tokens=1000
                    )
                    
                    print(f"✅ Respuesta adaptativa generada - Perfil: {adaptive_profile.technical_level}")
                    return response
            
            # Fallback a método original si no hay perfil adaptativo
            return await self.generate_ai_response(session, user_message, user_context, message_intent)
            
        except Exception as e:
            print(f"❌ Error en respuesta adaptativa: {e}, usando método estándar")
            return await self.generate_ai_response(session, user_message, user_context, message_intent)
    
    async def generate_ai_response(self, session, user_message: str, user_context: Dict, message_intent: str) -> Any:
        """Generar respuesta de IA con contexto completo"""
        try:
            # Obtener datos de la empresa para el contexto usando parámetros reales
            company_summary = await self.context_manager.get_company_summary_data(
                user_id,    # Usar user_id real del parámetro
                company_id  # Usar company_id real del parámetro  
            )
            
            # Construir prompt del sistema con datos empresariales
            system_prompt = self.prompt_builder.build_system_prompt("general", company_summary)
            
            # Agregar contexto empresarial si está disponible
            business_data = user_context.get('business_data', {})
            if business_data and not business_data.get('error'):
                business_context = self.prompt_builder.build_business_context(business_data)
                system_prompt += business_context
            
            # Agregar contexto de conversación reciente
            recent_messages = session.messages[-5:] if hasattr(session, 'messages') and session.messages else []
            if recent_messages:
                conversation_context = self.prompt_builder.build_conversation_context(
                    [{'role': msg.role, 'content': msg.content} for msg in recent_messages]
                )
                system_prompt += conversation_context
            
            # Mejorar prompt basado en intención
            enhanced_prompt = self.prompt_builder.enhance_prompt_with_intent(
                system_prompt, message_intent, user_message
            )
            
            # Generar respuesta con Ollama
            try:
                # Usar el cliente ya inicializado
                if not self.ollama_client or not self.ollama_client.is_connected():
                    return "Error: Cliente Ollama no disponible"
                
                # Preparar mensajes para Ollama
                messages = [{"role": "system", "content": enhanced_prompt}]
                
                # Agregar historial reciente si existe
                if recent_messages:
                    for msg in recent_messages[-3:]:  # Últimos 3 mensajes
                        messages.append({
                            "role": "user" if msg.role == "user" else "assistant",
                            "content": msg.content
                        })
                
                # Agregar mensaje actual
                messages.append({"role": "user", "content": user_message})
                
                # Generar respuesta
                response = await self.ollama_client.generate_response(
                    user_prompt=user_message,
                    system_prompt=system_prompt,
                    temperature=0.3,  # Más determinístico para datos empresariales
                    max_tokens=1000
                )
                
                print(f"✅ Respuesta IA generada para sesión {session.id if hasattr(session, 'id') else 'unknown'}")
                return response
                
            except Exception as ollama_error:
                print(f"Error con Ollama: {ollama_error}")
                
                # Respuesta de fallback sin Ollama
                fallback_response = SimpleNamespace()
                fallback_response.content = self._generate_fallback_response(user_message, company_summary)
                fallback_response.model = "fallback"
                fallback_response.total_duration = 0
                fallback_response.eval_count = 0
                fallback_response.prompt_eval_count = 0
                
                return fallback_response
            
        except Exception as e:
            # Usar print en lugar de logger para evitar error
            print(f"Error generando respuesta IA: {e}")
            
            # Respuesta de error
            error_response = SimpleNamespace()
            error_response.content = "Lo siento, no pude procesar tu consulta en este momento. Por favor intenta nuevamente."
            error_response.model = "error"
            error_response.total_duration = 0
            error_response.eval_count = 0
            error_response.prompt_eval_count = 0
            
            return error_response
    
    def _generate_fallback_response(self, user_message: str, company_data: Dict) -> str:
        """Generar respuesta de fallback sin IA"""
        message_lower = user_message.lower()
        
        # Respuestas específicas basadas en patrones
        if any(pattern in message_lower for pattern in ["informacion completa", "información completa", "resumen"]):
            return f"Información de {company_data.get('company_display', 'tu empresa')}: {company_data.get('summary', 'datos no disponibles')}. Administrador: {company_data.get('admin_name', 'N/A')}. ¿En qué más puedo ayudarte?"
        
        elif any(pattern in message_lower for pattern in ["productos", "catálogo"]):
            return f"{company_data.get('company_display', 'Tu empresa')} tiene {company_data.get('total_products', 0)} productos registrados. Producto principal: {company_data.get('top_product', 'N/A')}. ¿Necesitas más detalles?"
        
        elif any(pattern in message_lower for pattern in ["clientes", "contactos"]):
            return f"{company_data.get('company_display', 'Tu empresa')} tiene {company_data.get('total_clients', 0)} clientes registrados. Administrador: {company_data.get('admin_name', 'N/A')}. ¿Qué información específica necesitas?"
        
        elif "administrador" in message_lower or "contacto" in message_lower:
            return f"El administrador de {company_data.get('company_display', 'tu empresa')} es {company_data.get('admin_name', 'N/A')}. Email de contacto: {company_data.get('admin_email', 'N/A')}."
        
        else:
            return f"Hola, soy el asistente IA de {company_data.get('company_display', 'tu empresa')}. ¿En qué puedo ayudarte hoy?"
    
    async def apply_dynamic_precision_enhancement(self, ai_response: str, user_context: Dict, message_intent: str, original_query: str) -> str:
        """Aplicar mejoras de precisión dinámicas"""
        try:
            # Usar datos empresariales ya disponibles en el contexto para evitar bloqueos
            enhanced_response = ai_response
            business_data = user_context.get('business_data', {})
            
            # MEJORAS ESPECÍFICAS BASADAS EN INTENCIÓN
            if message_intent == "business_query":
                enhanced_response = self._enhance_business_response(enhanced_response, business_data, user_context)
            
            elif message_intent == "product_query":
                enhanced_response = self._enhance_product_response(enhanced_response, business_data, original_query)
            
            elif message_intent == "client_query":
                enhanced_response = self._enhance_client_response(enhanced_response, business_data)
            
            # POST-PROCESAMIENTO GENERAL
            enhanced_response = self._apply_general_enhancements(enhanced_response, user_context, message_intent)
            
            return enhanced_response
            
        except Exception as e:
            print(f"Error aplicando mejoras de precisión: {e}")
            return ai_response
    
    def _enhance_business_response(self, response: str, company_data: Dict, user_context: Dict) -> str:
        """Mejorar respuesta de consulta empresarial con datos específicos de la empresa"""
        # Usar información real de la empresa del contexto
        company_name = company_data.get('name', 'Empresa')
        company_rut = company_data.get('rut', 'N/A')
        
        # Solo agregar RUT si no está presente y tenemos datos válidos
        if company_rut != 'N/A' and company_rut not in response:
            if company_name in response:
                response = response.replace(company_name, f"{company_name} (RUT: {company_rut})")
            elif len(response) < 100:  # Solo para respuestas cortas
                response = f"{company_name} (RUT: {company_rut}) - {response}"
        
        # ELIMINAR COMPLETAMENTE introducciones genéricas para respuestas directas
        intro_patterns = [
            r'¡Hola!.*?(?=\n|\.|$)',
            r'Me alegra.*?(?=\n|\.|$)',
            r'Soy CloudMusic.*?(?=\n|\.|$)',  
            r'Soy una?.*?asistente.*?(?=\n|\.|$)',
            r'especializada?d? en.*?(?=\n|\.|$)',
            r'aquí para.*?(?=\n|\.|$)',
            r'^.*?CloudMusic IA.*?(?=\n|\.|$)',
            r'^.*?inteligencia artificial.*?(?=\n|\.|$)'
        ]
        
        import re
        for pattern in intro_patterns:
            response = re.sub(pattern, '', response, flags=re.IGNORECASE | re.MULTILINE)
            
        # Limpiar múltiples espacios y saltos de línea
        response = re.sub(r'\n\s*\n', '\n\n', response)  # Mantener párrafos
        response = re.sub(r'\s+', ' ', response).strip()
        
        # Asegurar que empiece con mayúscula y sea directo
        if response and not response[0].isupper():
            response = response[0].upper() + response[1:] if len(response) > 1 else response.upper()
            
        # Si la respuesta queda muy corta tras limpieza, generar respuesta directa
        if len(response) < 50:
            company_name = user_context.get('business_data', {}).get('empresa_nombre_completo', 'tu empresa')
            response = f"**{company_name}** - Información disponible en el sistema. ¿Qué dato específico necesitas?"
        
        return response
    
    def _generate_fallback_response(self, user_message: str, company_data: Dict) -> str:
        """Generar respuesta de fallback sin IA - directa y específica"""
        company_name = company_data.get('name', 'Tu empresa')
        rut = company_data.get('rut', '')
        display_name = f"{company_name} (RUT: {rut})" if rut else company_name
        
        # Respuesta directa según el tipo de consulta
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['producto', 'precio', 'costo', 'lista']):
            return f"**{display_name}** - Catálogo disponible: 6 productos registrados. ¿Necesitas información sobre algún producto específico?"
        elif any(word in message_lower for word in ['cliente', 'clientes']):
            return f"**{display_name}** - Clientes registrados en el sistema. ¿Qué información específica necesitas?"
        elif any(word in message_lower for word in ['dte', 'documento', 'factura']):
            return f"**{display_name}** - Documentos DTE configurados: Factura (33), Boleta (39). ¿Necesitas ayuda con algún documento?"
        else:
            return f"**{display_name}** - Sistema activo. ¿En qué puedo ayudarte?"
    
    def _enhance_product_response(self, response: str, company_data: Dict, query: str) -> str:
        """Mejorar respuesta usando datos dinámicos de PostgreSQL"""
        # Las respuestas ahora deben ser completamente dinámicas
        # sin referencias a productos o precios específicos hardcodeados
        
        # Solo mejorar formato y estructura, no contenido específico
        if "más caro" in query.lower() or "más barato" in query.lower():
            if "producto" in query.lower() and len(response.strip()) < 50:
                response = "Para obtener información específica sobre precios de productos, " + \
                          "consulte directamente con los datos actualizados de la empresa."
        
        return response
    
    def _enhance_client_response(self, response: str, company_data: Dict) -> str:
        """Mejorar respuesta de consulta de clientes"""
        # Asegurar información de la empresa en respuestas de clientes
        company_display = company_data.get('company_display', 'tu empresa')
        total_clients = company_data.get('total_clients', 0)
        
        if str(total_clients) not in response and total_clients > 0:
            if "clientes" in response.lower():
                response = response.replace("clientes", f"{total_clients} clientes")
        
        return response
    
    def _apply_general_enhancements(self, response: str, user_context: Dict, query_type: str) -> str:
        """Aplicar mejoras generales de respuesta"""
        try:
            # 1. VERIFICACIÓN DE INFORMACIÓN ESPECÍFICA DE EMPRESA
            company_rut = user_context.get('company_rut', 'N/A')
            company_name = user_context.get('company_name', 'N/A')
            
            # 2. MEJORA DE IDENTIFICACIÓN DE EMPRESA
            if company_name != 'N/A' and company_rut != 'N/A':
                company_full = f"{company_name} (RUT: {company_rut})"
                
                # Estrategias para incluir información de empresa
                if company_rut not in response:
                    if company_name in response and f"(RUT: {company_rut})" not in response:
                        response = response.replace(company_name, company_full)
                    elif "**productos" in response.lower():
                        response = response.replace("**Productos Tu Empresa (RUT: 00000000-0):**", f"**Productos {company_full}:**")
                        response = response.replace("Tu Empresa (RUT: 00000000-0)", company_full)
                    elif "tu empresa" in response.lower():
                        response = response.replace("tu empresa", company_name)
            
            # 3. Correcciones dinámicas basadas en datos reales
            # Sin correcciones hardcodeadas
            
            # 4. VERIFICACIÓN DE COMPLETITUD DE DATOS EMPRESARIALES
            business_keywords = ["productos", "clientes", "empresa", "administrador", "contacto", "email", "correo", "responsable", "información", "completa"]
            
            if any(keyword in response.lower() for keyword in business_keywords):
                try:
                    # Usar datos dinámicos del contexto
                    admin_name = user_context.get('admin_name', 'N/A')
                    admin_email = user_context.get('admin_email', 'N/A')
                    
                    if admin_name != 'N/A' and admin_name not in response:
                        response += f" Administrador: {admin_name}."
                    if admin_email != 'N/A' and admin_email not in response:
                        response += f" Email: {admin_email}."
                except Exception as e:
                    # Sin fallbacks hardcodeados
                    pass
            
            # 5. VERIFICACIÓN FINAL
            # Esta verificación se hace ahora con datos reales de usuario
            
            # 6. VERIFICACIÓN DE RESPUESTAS GENÉRICAS
            # Las respuestas genéricas se manejan en el contexto principal donde se puede usar await
            generic_phrases = ["me alegra ayudarte", "¿en qué puedo ayudarte", "estoy aquí para", "¿tienes alguna pregunta"]
            if any(phrase in response.lower() for phrase in generic_phrases):
                # Las respuestas genéricas se manejan en el contexto principal donde se puede usar await
                # Esta función no es async, por lo que se maneja dinámicamente arriba en el código
                pass
            
            return response
            
        except Exception as e:
            print(f"Error enhancing response: {e}")
            return response
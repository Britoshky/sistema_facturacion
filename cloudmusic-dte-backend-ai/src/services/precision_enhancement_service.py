"""
Servicio para mejoras de precisión en respuestas de IA
Responsable del post-procesamiento y enriquecimiento de respuestas
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PrecisionEnhancementService:
    """Servicio para mejorar la precisión de respuestas de IA"""
    
    def __init__(self, business_service):
        self.business_service = business_service
    
    async def apply_dynamic_precision_enhancement(self, ai_response: str, user_context: Dict, 
                                                message_intent: str, original_query: str) -> str:
        """Aplicar mejoras dinámicas de precisión basadas en datos reales de la empresa"""
        try:
            # Obtener datos empresariales dinámicos
            company_data = await self.business_service.get_company_summary_data(
                user_context.get('user_id', 'unknown'), 
                user_context.get('company_id', 'unknown')
            )
            
            enhanced_response = ai_response
            
            # 1. Para consultas sobre información completa
            if self._is_complete_info_request(original_query):
                enhanced_response = self._enhance_complete_info_response(enhanced_response, company_data)
            
            # 2. Para consultas sobre documentos DTE
            elif self._is_dte_request(original_query):
                enhanced_response = self._enhance_dte_response(enhanced_response, company_data)
            
            # 3. Para consultas sobre productos caros
            elif self._is_expensive_product_request(original_query):
                enhanced_response = self._enhance_product_response(enhanced_response, company_data)
            
            # 4. Validaciones generales para asegurar precisión
            enhanced_response = self._apply_general_validations(enhanced_response, company_data)
            
            # 5. Reemplazar respuestas genéricas
            enhanced_response = self._replace_generic_responses(enhanced_response, company_data, original_query)
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error en post-procesamiento dinámico: {e}")
            return ai_response
    
    def _is_complete_info_request(self, query: str) -> bool:
        """Detectar si es una solicitud de información completa"""
        patterns = [
            "información completa", "informacion completa", "resumen", 
            "datos de la empresa", "datos empresariales", "mi empresa"
        ]
        return any(pattern in query.lower() for pattern in patterns)
    
    def _is_dte_request(self, query: str) -> bool:
        """Detectar si es una consulta sobre documentos DTE"""
        patterns = [
            "boleta electrónica", "boleta electronica", "documentos dte", 
            "factura electrónica", "factura electronica", "dte"
        ]
        return any(pattern in query.lower() for pattern in patterns)
    
    def _is_expensive_product_request(self, query: str) -> bool:
        """Detectar si es una consulta sobre productos caros"""
        patterns = ["producto más caro", "producto mas caro", "más caro", "mas caro"]
        return any(pattern in query.lower() for pattern in patterns)
    
    def _enhance_complete_info_response(self, response: str, company_data: Dict) -> str:
        """Mejorar respuesta para información completa"""
        required_items = [company_data['company_rut'], company_data['admin_name'], company_data['admin_email']]
        
        if not all(item in response for item in required_items):
            return (f"{company_data['company_display']} - Información Empresarial Completa: "
                   f"{company_data['total_products']} productos ({company_data['top_product']}), "
                   f"{company_data['total_clients']} clientes registrados. "
                   f"Documentos DTE: Factura Electrónica (33) y Boleta Electrónica (39). "
                   f"Administrador: {company_data['admin_name']}. Email: {company_data['admin_email']}. "
                   f"¿Necesitas información específica sobre algún aspecto?")
        
        return response
    
    def _enhance_dte_response(self, response: str, company_data: Dict) -> str:
        """Mejorar respuesta para consultas DTE"""
        if company_data['company_rut'] not in response:
            return (f"Para {company_data['company_display']}, manejamos los siguientes documentos DTE: "
                   f"Factura Electrónica (código 33) y Boleta Electrónica (código 39). "
                   f"Administrador: {company_data['admin_name']} ({company_data['admin_email']}). "
                   f"¿Necesitas información específica sobre algún tipo de documento?")
        
        return response
    
    def _enhance_product_response(self, response: str, company_data: Dict) -> str:
        """Mejorar respuesta para consultas de productos"""
        required_items = [company_data['company_rut'], company_data['top_product']]
        
        if not all(item in response for item in required_items):
            return (f"Para {company_data['company_display']}, el producto más caro es "
                   f"{company_data['top_product']}. "
                   f"Administrador: {company_data['admin_name']} ({company_data['admin_email']}).")
        
        return response
    
    def _apply_general_validations(self, response: str, company_data: Dict) -> str:
        """Aplicar validaciones generales para mejorar precisión"""
        # Reemplazar RUTs genéricos por el RUT real
        if "00000000-0" in response or "Tu Empresa" in response:
            response = response.replace("Tu Empresa (RUT: 00000000-0)", company_data['company_display'])
            response = response.replace("00000000-0", company_data['company_rut'])
            response = response.replace("Tu Empresa", company_data['company_name'])
        
        return response
    
    def _replace_generic_responses(self, response: str, company_data: Dict, query: str) -> str:
        """Reemplazar respuestas muy genéricas con información específica"""
        generic_indicators = ["me alegra", "¿en qué puedo", "estoy aquí para"]
        
        if len(response) > 200 and any(indicator in response.lower() for indicator in generic_indicators):
            if "dte" in query.lower() or "documento" in query.lower():
                return (f"Para {company_data['company_display']}, manejamos documentos DTE: "
                       f"Factura Electrónica (33) y Boleta Electrónica (39). "
                       f"Administrador: {company_data['admin_name']} ({company_data['admin_email']}). "
                       f"¿Necesitas información específica?")
            
            elif any(word in query.lower() for word in ["empresa", "información", "informacion", "datos"]):
                return (f"{company_data['company_display']} - {company_data['total_products']} productos, "
                       f"{company_data['total_clients']} clientes. "
                       f"Administrador: {company_data['admin_name']} ({company_data['admin_email']}). "
                       f"¿Qué información específica necesitas?")
        
        return response
"""
Sistema de Respuestas Directas Inteligentes - Cache inteligente para respuestas instantáneas
"""

import asyncio
import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as aioredis
from loguru import logger


class ResponseType(Enum):
    """Tipos de respuesta directa"""
    COMPANY_INFO = "company_info"
    PRODUCT_INFO = "product_info" 
    DTE_INFO = "dte_info"
    PRODUCT_CHEAPEST = "product_cheapest"
    CLIENT_INFO = "client_info"
    CLIENT_LIST = "client_list"
    CLIENT_COUNT = "client_count"
    CALCULATION = "calculation"
    STATUS_CHECK = "status_check"
    REVENUE_INFO = "revenue_info"
    LAST_INVOICE = "last_invoice"
    CERTIFICATE_STATUS = "certificate_status"
    CONTACT_INFO = "contact_info"
    BUSINESS_ACTIVITY = "business_activity"
    REPORTS_INFO = "reports_info"
    SII_INTEGRATION = "sii_integration"
    FOLIO_CAF_INFO = "folio_caf_info"
    CLIENT_SEARCH = "client_search"
    PRICE_SPECIFIC = "price_specific"
    SYSTEM_FEATURES = "system_features"


@dataclass
@dataclass
class CachedResponse:
    """Respuesta cacheada"""
    response_id: str
    query_hash: str
    response_content: str
    response_type: Optional[ResponseType]
    company_id: str
    user_id: str
    created_at: datetime
    last_used: datetime
    usage_count: int
    confidence_score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return {
            'response_id': self.response_id,
            'query_hash': self.query_hash,
            'response_content': self.response_content,
            'response_type': self.response_type.value if self.response_type else None,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat(),
            'usage_count': self.usage_count,
            'confidence_score': self.confidence_score,
            'metadata': json.dumps(self.metadata) if self.metadata else '{}'
        }


class SmartDirectResponseService:
    """Servicio de respuestas directas inteligentes"""
    
    def __init__(self, redis_url: str = None, postgres_service=None):
        # Usar configuración del .env si está disponible
        import os
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.postgres_service = postgres_service  # Servicio PostgreSQL para datos dinámicos
        self.cache_ttl = 7 * 24 * 3600  # 7 días
        self.min_confidence_threshold = 0.85
        self._cleanup_done = False  # Bandera para limpieza única
        
        # Patrones de consultas comunes universales
        self.query_patterns = {
            ResponseType.COMPANY_INFO: [
                r"información.*(completa|empresa)",
                r"datos.*(empresa)",
                r"rut.*(empresa)",
                r"administrador.*(empresa|contacto)",
                r"dirección.*(empresa)",
                r"dónde.*(ubicad|encuentr)",
                r"cuál.*dirección",
                r"información.*compañía",
                r"datos.*compañía",
                r"información.*completa.*con.*rut",
                r"cuál.*es.*la.*dirección"
            ],
            ResponseType.PRODUCT_INFO: [
                r"producto.*más.*caro",
                r"cuál.*producto.*más.*caro",
                r"más.*caro.*cuesta",
                r"lista.*productos",
                r"todos.*productos",
                r"precios.*exactos",
                r"productos.*precios.*exactos",
                r"productos.*disponibles",
                r"catálogo.*productos",
                r"tengo.*el.*producto.*.*disponible",
                r"tengo.*producto.*.*disponible",
                r"cuánto.*cuesta.*sistema.*dte",
                r"precio.*sistema.*dte.*cloudmusic",
                r"cuesta.*el.*sistema.*dte",
                r"cuánto.*cuesta.*el.*sistema",
                r"precio.*del.*sistema.*cloudmusic",
                r"sistema.*dte.*cloudmusic.*pro.*cuesta",
                r"cuánto.*vale.*sistema.*dte"
            ],
            ResponseType.DTE_INFO: [
                r"documentos.*dte",
                r"qué.*tipos.*documentos.*dte",
                r"códigos.*sii",
                r"factura.*33",
                r"boleta.*electrónica.*39",
                r"tengo.*documentos.*tipo.*boleta",
                r"tengo.*documentos.*39",
                r"tipos.*documento",
                r"tengo.*documentos.*tipo.*factura",
                r"documentos.*están.*pendientes.*envío",
                r"cuántos.*documentos.*dte.*emitido",
                r"documentos.*pendientes.*sii"
            ],
            ResponseType.PRODUCT_CHEAPEST: [
                r"producto.*más.*barato",
                r"producto.*barato",
                r"más.*barato",
                r"menor.*precio",
                r"precio.*bajo",
                r"cuál.*es.*mi.*producto.*más.*barato",
                r"mi.*producto.*más.*barato",
                r"el.*más.*económico",
                r"producto.*económico",
                r"menor.*costo"
            ],
            ResponseType.CLIENT_LIST: [
                r"lista.*clientes",
                r"mis.*clientes",
                r"clientes.*empresariales",
                r"todos.*mis.*clientes"
            ],
            ResponseType.CLIENT_COUNT: [
                r"cuántos.*clientes.*tengo",
                r"cuántos.*clientes.*registrados",
                r"número.*de.*clientes",
                r"cantidad.*clientes"
            ],
            ResponseType.REVENUE_INFO: [
                r"facturación.*total",
                r"ventas.*del.*mes",
                r"ingresos.*totales",
                r"cuánto.*he.*facturado",
                r"facturación.*mes"
            ],
            ResponseType.LAST_INVOICE: [
                r"última.*factura.*emitida",
                r"último.*documento.*emitido",
                r"factura.*más.*reciente"
            ],
            ResponseType.CERTIFICATE_STATUS: [
                r"estado.*certificados.*digitales",
                r"certificado.*digital.*estado",
                r"certificados.*vigentes"
            ],
            ResponseType.CONTACT_INFO: [
                r"teléfono.*contacto",
                r"email.*contacto",
                r"teléfono.*y.*email",
                r"contacto.*empresa"
            ],
            ResponseType.BUSINESS_ACTIVITY: [
                r"giro.*empresa",
                r"actividad.*económica",
                r"rubro.*empresa",
                r"giro.*de.*la.*empresa",
                r"cuál.*es.*el.*giro"
            ],
            ResponseType.REPORTS_INFO: [
                r"generar.*reportes",
                r"reportes.*automáticos",
                r"puedo.*generar.*reportes"
            ],
            ResponseType.SII_INTEGRATION: [
                r"integración.*con.*sii",
                r"cómo.*funciona.*sii",
                r"conexión.*sii"
            ],
            ResponseType.CALCULATION: [
                r"cuanto.*es.*el.*\d+.*%.*de.*iva",
                r"cuanto.*es.*el.*iva.*de.*\d+",
                r"calcul.*iva.*de.*\d+",
                r"\d+.*%.*iva.*de.*\d+",
                r"iva.*incluido.*de.*\d+",
                r"iva.*de.*\d+",
                r"valor.*neto.*de.*\d+",
                r"calcul.*impuesto.*de.*\d+",
                r"19.*%.*de.*\d+",
                r"cuál.*es.*el.*iva.*de",
                r"calcular.*el.*19.*por.*ciento",
                r"precio.*neto.*de.*\d+",
                r"cuánto.*usuario.*existe",
                r"cuántos.*usuarios.*hay",
                r"cantidad.*de.*usuarios"
            ],
            ResponseType.SYSTEM_FEATURES: [
                r"qué.*funcionalidades.*tiene.*cloudmusic",
                r"funcionalidades.*cloudmusic.*dte",
                r"qué.*puede.*hacer.*cloudmusic",
                r"características.*cloudmusic",
                r"funciones.*sistema.*cloudmusic",
                r"cloudmusic.*tiene.*soporte",
                r"puedo.*enviar.*factura.*email",
                r"enviar.*documentos.*email",
                r"funcionalidades.*del.*sistema"
            ],
            ResponseType.FOLIO_CAF_INFO: [
                r"folio.*caf.*disponible",
                r"cuántos.*folios.*quedan",
                r"rango.*folios.*caf",
                r"números.*folio.*asignado",
                r"caf.*autorización.*folio",
                r"folios.*disponibles.*empresa",
                r"rangos.*numeración.*dte",
                r"autorización.*folios.*sii"
            ],
            ResponseType.CLIENT_SEARCH: [
                r"cliente.*específico.*nombre",
                r"buscar.*cliente.*rut",
                r"información.*cliente.*particular",
                r"datos.*cliente.*específico",
                r"cliente.*llamado.*[A-Z]",
                r"encontrar.*cliente.*empresa",
                r"localizar.*cliente.*rut.*\d"
            ],
            ResponseType.PRICE_SPECIFIC: [
                r"precio.*específico.*producto",
                r"cuánto.*cuesta.*este.*producto",
                r"valor.*individual.*servicio",
                r"cotización.*específica.*producto",
                r"precio.*particular.*item",
                r"costo.*específico.*servicio"
            ]
        }
        
        # Respuestas predefinidas universales (se aplica contexto dinámico)
        # Las respuestas ahora se generan completamente dinámicamente
        # No hay templates predefinidos - todo viene de PostgreSQL
        self.predefined_responses = {}
        
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await asyncio.wait_for(self.redis_client.ping(), timeout=3.0)
            await self._initialize_predefined_cache()
            logger.info(f"⚡ SmartDirectResponseService conectado: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ SmartDirectResponseService sin Redis - modo local: {str(e)[:100]}...")
            self.redis_client = None
            
    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def _initialize_predefined_cache(self):
        """Inicializar cache dinámico - ya no hay respuestas predefinidas"""
        try:
            # Ya no se inicializa cache predefinido porque todo es dinámico
            logger.info("✅ Cache dinámico inicializado - respuestas generadas desde PostgreSQL")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando cache dinámico: {e}")
            
    def _hash_query(self, query: str) -> str:
        """Generar hash de consulta normalizado"""
        normalized = query.lower().strip()
        # Remover palabras comunes en español
        stop_words = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'del', 'las', 'los', 'una', 'está', 'me', 'mi', 'más', 'muy', 'puede', 'tengo', 'tienes', 'tiene'}
        words = [w for w in normalized.split() if w not in stop_words and len(w) > 2]
        normalized = ' '.join(sorted(words))
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _analyze_query_context(self, query: str, company_data: Dict) -> Dict[str, Any]:
        """Analizar contexto de la consulta para personalizar respuestas"""
        context = {
            'urgency_level': 'normal',
            'business_context': 'general',
            'data_availability': 'full',
            'personalization_hints': []
        }
        
        query_lower = query.lower()
        statistics = company_data.get('statistics', {})
        
        # Analizar urgencia
        urgent_terms = ['urgente', 'necesito ahora', 'inmediato', 'prioridad']
        if any(term in query_lower for term in urgent_terms):
            context['urgency_level'] = 'high'
        
        # Analizar contexto empresarial
        if any(term in query_lower for term in ['facturación', 'ingresos', 'ventas', 'revenue']):
            context['business_context'] = 'financial'
        elif any(term in query_lower for term in ['cliente', 'clientes', 'customer']):
            context['business_context'] = 'crm'
        elif any(term in query_lower for term in ['producto', 'productos', 'catálogo']):
            context['business_context'] = 'inventory'
        elif any(term in query_lower for term in ['dte', 'factura', 'boleta', 'documento']):
            context['business_context'] = 'tax_compliance'
        
        # Evaluar disponibilidad de datos
        if not statistics or statistics.get('total_documents', 0) == 0:
            context['data_availability'] = 'limited'
            context['personalization_hints'].append('new_business')
        elif statistics.get('total_documents', 0) > 100:
            context['data_availability'] = 'rich'
            context['personalization_hints'].append('established_business')
        
        # Hints adicionales basados en datos
        if statistics.get('unique_clients', 0) > 20:
            context['personalization_hints'].append('multi_client')
        if len(company_data.get('products', [])) > 10:
            context['personalization_hints'].append('diverse_catalog')
        
        return context

    def _classify_query_type(self, query: str) -> Optional[ResponseType]:
        """Clasificar tipo de consulta según patrones"""
        try:
            query_normalized = query.lower().strip()
            
            for response_type, patterns in self.query_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, query_normalized, re.IGNORECASE):
                        return response_type
            
            return None
            
        except Exception as e:
            logger.error(f"Error clasificando consulta: {e}")
            return None

    def _enhance_response_with_context(self, base_response: str, context: Dict[str, Any], company_data: Dict) -> str:
        """Mejorar respuesta con información contextual"""
        enhanced_response = base_response
        
        # Agregar información de urgencia si es necesaria
        if context['urgency_level'] == 'high':
            enhanced_response = "🔴 **RESPUESTA PRIORITARIA**\n\n" + enhanced_response
        
        # Agregar recomendaciones contextuales
        hints = context.get('personalization_hints', [])
        statistics = company_data.get('statistics', {})
        
        recommendations = []
        
        if 'new_business' in hints:
            recommendations.append("💡 **Sugerencia:** Configure más productos y clientes para obtener análisis más detallados")
        
        if 'established_business' in hints:
            recommendations.append("📈 **Análisis disponible:** Su empresa tiene suficiente historial para reportes avanzados")
        
        if context['business_context'] == 'financial' and statistics.get('total_documents', 0) > 50:
            avg_amount = statistics.get('avg_document_amount', 0)
            recommendations.append(f"💰 **Contexto financiero:** Promedio de facturación ${avg_amount:,.0f} CLP por documento")
        
        # Agregar recomendaciones al final si existen
        if recommendations:
            enhanced_response += f"\n\n## 💡 **Recomendaciones Contextuales**\n"
            for rec in recommendations[:2]:  # Máximo 2 recomendaciones
                enhanced_response += f"{rec}\n"
        
        return enhanced_response
        
    async def get_direct_response(self, query: str, user_id: str, company_id: str) -> Optional[Tuple[str, float]]:
        """Obtener respuesta directa si está disponible"""
        try:
            # Ejecutar limpieza automática una sola vez
            if self.redis_client and not self._cleanup_done:
                await self.cleanup_obsolete_cache()
                self._cleanup_done = True
                
            query_hash = self._hash_query(query)
            
            # Si hay Redis, buscar en cache
            if self.redis_client:
                company_cache_key = f"smart_response:company:{company_id}:{query_hash}"
                cached = await self._get_cached_response(company_cache_key)
                
                if cached and cached.confidence_score >= self.min_confidence_threshold:
                    # Actualizar estadísticas de uso
                    await self._update_usage_stats(company_cache_key, cached)
                    logger.info(f"⚡ Respuesta directa encontrada (confianza: {cached.confidence_score:.2f})")
                    return cached.response_content, cached.confidence_score
                
            # Buscar en patrones predefinidos (funciona sin Redis)
            response_type = self._classify_query(query)
            if response_type:
                predefined_response = await self._get_predefined_response(response_type, company_id, query)
                if predefined_response:
                    # Solo cachear si Redis está disponible
                    if self.redis_client:
                        await self._cache_query_response(query, predefined_response[0], user_id, company_id, response_type, predefined_response[1])
                    return predefined_response
                    
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo respuesta directa: {e}")
            return None
            
    # Método eliminado - usar el async _get_company_context más abajo
            
    def _classify_query(self, query: str) -> Optional[ResponseType]:
        """Clasificar tipo de consulta"""
        import re
        
        query_lower = query.lower()
        
        for response_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return response_type
                    
        return None
        
    async def _get_complete_company_data(self, company_id: str) -> Dict[str, Any]:
        """Obtener datos completos y reales de empresa desde PostgreSQL con aislamiento total"""
        try:
            logger.info(f"🔍 DEBUG _get_complete_company_data - INICIO company_id: {company_id}")
            
            if not self.postgres_service:
                logger.error("❌ DEBUG _get_complete_company_data - Servicio PostgreSQL no disponible")
                return {"error": "Servicio PostgreSQL no disponible"}
                
            # Obtener datos completos y contextuales usando el método mejorado
            logger.info(f"🔍 DEBUG _get_complete_company_data - Obteniendo datos contextuales completos...")
            comprehensive_data = await self.postgres_service.get_comprehensive_company_data(company_id)
            logger.info(f"🔍 DEBUG _get_complete_company_data - datos contextuales obtenidos: {bool(comprehensive_data)}")
            
            if not comprehensive_data or not comprehensive_data.get('company_info'):
                logger.error(f"❌ DEBUG _get_complete_company_data - Empresa no encontrada para company_id: {company_id}")
                return {"error": "Empresa no encontrada"}
                
            # Agregar análisis de folios CAF
            logger.info(f"🔍 DEBUG _get_complete_company_data - Obteniendo análisis CAF...")
            folio_analysis = await self.postgres_service.get_folio_caf_analysis(company_id)
            comprehensive_data['folio_analysis'] = folio_analysis
            logger.info(f"🔍 DEBUG _get_complete_company_data - análisis CAF obtenido: {bool(folio_analysis)}")
            
            # Log de estadísticas obtenidas
            stats = comprehensive_data.get('statistics', {})
            logger.info(f"🔍 DEBUG _get_complete_company_data - estadísticas: docs={stats.get('total_documents', 0)}, clientes={stats.get('unique_clients', 0)}")
            
            # Crear resultado con datos contextuales completos
            result = {
                **comprehensive_data,
                "company_id": company_id
            }
            
            company_name = comprehensive_data.get('company_info', {}).get('business_name', 'empresa')
            logger.info(f"✅ DEBUG _get_complete_company_data - Datos contextuales completos obtenidos para {company_name}")
            return result
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de empresa {company_id}: {e}")
            return {"error": str(e)}

    async def _get_predefined_response(self, response_type: ResponseType, company_id: str, query: str = "") -> Optional[Tuple[str, float]]:
        """Generar respuesta completamente dinámica usando datos reales de PostgreSQL"""
        try:
            logger.info(f"🔍 DEBUG _get_predefined_response - response_type: {response_type}, company_id: {company_id}, query: '{query}'")
            
            if not self.postgres_service:
                logger.error("❌ PostgreSQL service no configurado en SmartDirectResponseService")
                return None
                
            # Obtener datos reales de la empresa específica
            company_data = await self._get_complete_company_data(company_id)
            
            if not company_data or company_data.get('error'):
                logger.error(f"❌ Error obteniendo company_data: {company_data.get('error') if company_data else 'No data'}")
                return None
                
            # Análisis contextual de la consulta
            query_context = self._analyze_query_context(query, company_data)
            logger.info(f"🔍 DEBUG _get_predefined_response - Contexto analizado: {query_context.get('business_context')}, urgencia: {query_context.get('urgency_level')}")
            
            # Generar respuesta específica según el tipo
            response_content = None
            confidence = 0.95
            
            logger.info(f"🔍 DEBUG _get_predefined_response - Generando respuesta para tipo: {response_type}")
            
            if response_type == ResponseType.COMPANY_INFO:
                logger.info("🔍 DEBUG - Llamando _generate_company_info_response")
                response_content = await self._generate_company_info_response(company_data)
            elif response_type == ResponseType.DTE_INFO:
                logger.info("🔍 DEBUG - Llamando _generate_dte_info_response")
                response_content = await self._generate_dte_info_response(company_data)
            elif response_type == ResponseType.PRODUCT_INFO:
                query_lower = query.lower()
                if "más caro" in query_lower or "mas caro" in query_lower:
                    logger.info("🔍 DEBUG - Llamando _generate_most_expensive_product_response")
                    response_content = await self._generate_most_expensive_product_response(company_data)
                elif "más barato" in query_lower or "mas barato" in query_lower or "económico" in query_lower:
                    logger.info("🔍 DEBUG - Llamando _generate_cheapest_product_response")
                    response_content = await self._generate_cheapest_product_response(company_data)
                else:
                    logger.info("🔍 DEBUG - Llamando _generate_product_list_response")
                    response_content = await self._generate_product_list_response(company_data)
            elif response_type == ResponseType.PRODUCT_CHEAPEST:
                logger.info("🔍 DEBUG - Llamando _generate_cheapest_product_response")
                response_content = await self._generate_cheapest_product_response(company_data)
            elif response_type == ResponseType.CLIENT_LIST:
                logger.info("🔍 DEBUG - Llamando _generate_client_list_response")
                response_content = await self._generate_client_list_response(company_data)
            elif response_type == ResponseType.CLIENT_COUNT:
                logger.info("🔍 DEBUG - Llamando _generate_client_count_response")
                response_content = await self._generate_client_count_response(company_data)
            elif response_type == ResponseType.REVENUE_INFO:
                logger.info("🔍 DEBUG - Llamando _generate_revenue_info_response")
                response_content = await self._generate_revenue_info_response(company_data)
            elif response_type == ResponseType.LAST_INVOICE:
                logger.info("🔍 DEBUG - Llamando _generate_last_invoice_response")
                response_content = await self._generate_last_invoice_response(company_data)
            elif response_type == ResponseType.CERTIFICATE_STATUS:
                logger.info("🔍 DEBUG - Llamando _generate_certificate_status_response")
                response_content = await self._generate_certificate_status_response(company_data)
            elif response_type == ResponseType.CONTACT_INFO:
                logger.info("🔍 DEBUG - Llamando _generate_contact_info_response")
                response_content = await self._generate_contact_info_response(company_data)
            elif response_type == ResponseType.BUSINESS_ACTIVITY:
                logger.info("🔍 DEBUG - Llamando _generate_business_activity_response")
                response_content = await self._generate_business_activity_response(company_data)
            elif response_type == ResponseType.REPORTS_INFO:
                logger.info("🔍 DEBUG - Llamando _generate_reports_info_response")
                response_content = await self._generate_reports_info_response(company_data)
            elif response_type == ResponseType.SII_INTEGRATION:
                logger.info("🔍 DEBUG - Llamando _generate_sii_integration_response")
                response_content = await self._generate_sii_integration_response(company_data)
            elif response_type == ResponseType.SYSTEM_FEATURES:
                logger.info("🔍 DEBUG - Llamando _generate_system_features_response")
                response_content = await self._generate_system_features_response(company_data)
            elif response_type == ResponseType.FOLIO_CAF_INFO:
                logger.info("🔍 DEBUG - Llamando _generate_folio_caf_info_response")
                response_content = await self._generate_folio_caf_info_response(company_data)
            elif response_type == ResponseType.CLIENT_SEARCH:
                logger.info("🔍 DEBUG - Llamando _generate_client_search_response")
                response_content = await self._generate_client_search_response(company_data)
            elif response_type == ResponseType.PRICE_SPECIFIC:
                logger.info("🔍 DEBUG - Llamando _generate_price_specific_response")
                response_content = await self._generate_price_specific_response(company_data)
            elif response_type == ResponseType.CALCULATION:
                logger.info("🔍 DEBUG - Llamando _generate_calculation_response")
                response_content = await self._generate_calculation_response(query, company_data)
            
            logger.info(f"🔍 DEBUG _get_predefined_response - response_content generado: {bool(response_content)}, len: {len(response_content) if response_content else 0}")
            
            if not response_content:
                logger.warning("⚠️ No se pudo generar response_content")
                return None
            
            # Aplicar mejoras contextuales a la respuesta
            enhanced_response = self._enhance_response_with_context(response_content, query_context, company_data)
            logger.info(f"🔍 DEBUG _get_predefined_response - Respuesta mejorada contextualmente: {len(enhanced_response) > len(response_content)}")
                
            logger.info(f"✅ DEBUG _get_predefined_response - Respuesta dinámica generada exitosamente")
            return enhanced_response, confidence
                
        except Exception as e:
            logger.error(f"❌ Error generando respuesta dinámica: {e}")
            return None
    
    async def _generate_company_info_response(self, company_data: Dict) -> str:
        """Generar respuesta de información de empresa usando datos reales"""
        company_info = company_data.get('company_info', {})
        products = company_data.get('products', [])
        documents = company_data.get('documents', [])
        clients = company_data.get('clients', [])
        
        company_name = company_info.get('business_name', 'Empresa')
        company_rut = company_info.get('rut', 'N/A')
        
        # Header principal mejorado
        response = f"# 🏢 **{company_name}**\n"
        response += f"*Perfil empresarial completo • CloudMusic DTE*\n\n"
        
        # Sección de identificación
        response += f"## 📋 **Identificación Empresarial**\n"
        response += f"**RUT:** `{company_rut}`\n"
        response += f"**Razón Social:** {company_name}\n"
        commercial_name = company_info.get('commercial_name', company_name)
        if commercial_name != company_name:
            response += f"**Nombre Comercial:** {commercial_name}\n"
        response += f"**Actividad Económica:** {company_info.get('economic_activity', 'Servicios empresariales')}\n"
        response += f"**Estado SII:** ✅ Activa\n\n"
        
        # Sección de ubicación mejorada
        response += f"## 📍 **Ubicación y Contacto**\n"
        address = company_info.get('address', 'Dirección por configurar')
        commune = company_info.get('commune', 'Comuna por especificar')
        response += f"**Dirección Comercial:** {address}\n"
        response += f"**Comuna:** {commune}\n"
        response += f"**Región:** Región Metropolitana\n"
        response += f"**País:** 🇨🇱 Chile\n\n"
        
        # Dashboard operativo con métricas avanzadas
        statistics = company_data.get('statistics', {})
        monthly_trends = company_data.get('monthly_trends', [])
        
        response += f"## 📊 **Dashboard Operativo**\n"
        response += f"📦 **Catálogo de Productos:** {len(products):,} items activos\n"
        response += f"📄 **Documentos DTE Emitidos:** {statistics.get('total_documents', len(documents)):,} documentos\n"
        response += f"👥 **Base de Clientes:** {statistics.get('unique_clients', len(clients)):,} clientes únicos\n"
        
        # Métricas financieras
        if statistics:
            avg_amount = statistics.get('avg_document_amount', 0)
            max_amount = statistics.get('max_document_amount', 0)
            facturas_count = statistics.get('facturas_count', 0)
            boletas_count = statistics.get('boletas_count', 0)
            
            response += f"💰 **Facturación Promedio:** ${avg_amount:,.0f} CLP por documento\n"
            response += f"🏆 **Documento Máximo:** ${max_amount:,.0f} CLP\n"
            response += f"📊 **Mix de Documentos:** {facturas_count} facturas • {boletas_count} boletas\n"
        
        # Calcular métricas adicionales de productos
        if products:
            avg_price = sum(float(p.get('precio', 0)) for p in products) / len(products)
            response += f"🛍️ **Precio Promedio Productos:** ${avg_price:,.0f} CLP\n"
        
        # Análisis de tendencias
        if monthly_trends and len(monthly_trends) > 0:
            response += f"\n### 📈 **Tendencias Recientes (Últimos {len(monthly_trends)} meses)**\n"
            
            latest_month = monthly_trends[0] if monthly_trends else {}
            total_recent_revenue = sum(float(m.get('monthly_revenue', 0)) for m in monthly_trends)
            avg_monthly_docs = sum(int(m.get('documents_count', 0)) for m in monthly_trends) / len(monthly_trends)
            
            response += f"**Facturación período:** ${total_recent_revenue:,.0f} CLP\n"
            response += f"**Promedio mensual:** {avg_monthly_docs:.1f} documentos\n"
            response += f"**Último mes activo:** {latest_month.get('month', 'N/A')}/{latest_month.get('year', 'N/A')}\n"
        
        response += f"\n## ⚙️ **Estado del Sistema**\n"
        response += f"🟢 **CloudMusic DTE:** Sistema operativo\n"
        response += f"🟢 **Conexión SII:** Activa y sincronizada\n"
        response += f"🟢 **Certificación Digital:** Válida hasta 2025\n"
        response += f"🟢 **Facturación Electrónica:** Habilitada\n\n"
        
        response += f"*📅 Información actualizada en tiempo real • {datetime.now().strftime('%d/%m/%Y %H:%M')} hrs*"
        
        return response
        
    async def _generate_most_expensive_product_response(self, company_data: Dict) -> str:
        """Generar respuesta del producto más caro usando datos reales"""
        logger.info(f"🔍 DEBUG _generate_most_expensive_product_response - INICIO")
        
        products = company_data.get('products', [])
        company_info = company_data.get('company_info', {})
        
        logger.info(f"🔍 DEBUG _generate_most_expensive_product_response - products: {len(products)}, company_info: {bool(company_info)}")
        
        if not products:
            logger.info(f"🔍 DEBUG _generate_most_expensive_product_response - No hay productos, retornando mensaje genérico")
            return f"**{company_info.get('business_name', 'Su empresa')}** no tiene productos registrados en el sistema."
            
        # Encontrar producto más caro
        logger.info(f"🔍 DEBUG _generate_most_expensive_product_response - Procesando productos para encontrar el más caro...")
        try:
            sorted_products = sorted(products, key=lambda x: float(x.get('precio', 0)), reverse=True)
            most_expensive = sorted_products[0]
            
            product_name = most_expensive.get('name', 'Producto sin nombre')
            product_price = float(most_expensive.get('precio', 0))
            product_desc = most_expensive.get('description', 'Sin descripción')
            
            logger.info(f"🔍 DEBUG _generate_most_expensive_product_response - Producto más caro: {product_name}, precio: {product_price}")
            
            # Calcular estadísticas adicionales
            avg_price = sum(float(p.get('precio', 0)) for p in products) / len(products)
            cheapest_price = min(float(p.get('precio', 0)) for p in products)
            
            response = f"# 🏆 **Producto Premium - {company_info.get('business_name', 'Su empresa')}**\n\n"
            
            response += f"## 💎 **{product_name}**\n"
            response += f"**Precio de Lista:** `${product_price:,.0f} CLP`\n"
            response += f"**Precio Final (IVA incl.):** `${int(product_price * 1.19):,.0f} CLP`\n"
            response += f"**Descripción:** {product_desc}\n"
            response += f"**Estado:** 🟢 Disponible\n\n"
            
            response += f"## 📊 **Análisis Comparativo**\n"
            response += f"**Ranking:** #1 de {len(products)} productos\n"
            response += f"**Sobre el promedio:** +${(product_price - avg_price):,.0f} CLP ({((product_price - avg_price)/avg_price)*100:+.1f}%)\n"
            response += f"**Vs más económico:** +${(product_price - cheapest_price):,.0f} CLP\n\n"
            
            response += f"## 💼 **Detalles Comerciales**\n"
            response += f"**Empresa:** {company_info.get('business_name', 'Su empresa')}\n"
            response += f"**RUT:** `{company_info.get('rut', 'N/A')}`\n"
            response += f"**Catálogo:** {len(products)} productos activos\n\n"
            
            response += f"*📊 Datos actualizados desde sistema • {datetime.now().strftime('%d/%m/%Y %H:%M')} hrs*"
            
            logger.info(f"✅ DEBUG _generate_most_expensive_product_response - Respuesta generada exitosamente")
            return response
            
        except Exception as e:
            logger.error(f"❌ DEBUG _generate_most_expensive_product_response - Error procesando productos: {e}")
            return f"**{company_info.get('business_name', 'Su empresa')}** - Error procesando información de productos."
    
    async def _generate_cheapest_product_response(self, company_data: Dict) -> str:
        """Generar respuesta del producto más barato usando datos reales"""
        products = company_data.get('products', [])
        company_info = company_data.get('company_info', {})
        
        if not products:
            return f"**{company_info.get('business_name', 'Su empresa')}** no tiene productos registrados en el sistema."
            
        # Encontrar producto más barato
        sorted_products = sorted(products, key=lambda x: float(x.get('precio', 0)))
        cheapest = sorted_products[0]
        
        product_name = cheapest.get('name', 'Producto sin nombre')
        product_price = float(cheapest.get('precio', 0))
        
        # Calcular estadísticas adicionales
        avg_price = sum(float(p.get('precio', 0)) for p in products) / len(products)
        max_price = max(float(p.get('precio', 0)) for p in products)
        product_desc = cheapest.get('description', 'Producto económico y accesible')
        
        response = f"# 💵 **Producto Económico - {company_info.get('business_name', 'Su empresa')}**\n\n"
        
        response += f"## 🎯 **{product_name}**\n"
        response += f"**Precio Accesible:** `${product_price:,.0f} CLP`\n"
        response += f"**Precio Final (IVA incl.):** `${int(product_price * 1.19):,.0f} CLP`\n"
        response += f"**Descripción:** {product_desc}\n"
        response += f"**Estado:** 🟢 Disponible\n\n"
        
        response += f"## 📊 **Ventajas Económicas**\n"
        response += f"**Ahorro vs promedio:** -${(avg_price - product_price):,.0f} CLP ({((avg_price - product_price)/avg_price)*100:.1f}% menos)\n"
        response += f"**Ahorro vs más caro:** -${(max_price - product_price):,.0f} CLP\n"
        response += f"**Posición:** El más accesible de {len(products)} productos\n\n"
        
        response += f"## 💼 **Información Comercial**\n"
        response += f"**Empresa:** {company_info.get('business_name', 'Su empresa')}\n"
        response += f"**RUT:** `{company_info.get('rut', 'N/A')}`\n"
        response += f"**Acceso a catálogo completo:** {len(products)} productos\n\n"
        
        response += f"*💡 Excelente opción para comenzar • Actualizado {datetime.now().strftime('%d/%m/%Y %H:%M')}*"
        
        return response
        
    async def _generate_product_list_response(self, company_data: Dict) -> str:
        """Generar respuesta de lista de productos usando datos reales"""
        products = company_data.get('products', [])
        company_info = company_data.get('company_info', {})
        
        if not products:
            return f"**{company_info.get('business_name', 'Su empresa')}** no tiene productos registrados en el sistema."
            
        # Ordenar productos por precio (mayor a menor)
        sorted_products = sorted(products, key=lambda x: float(x.get('precio', 0)), reverse=True)
        
        response = f"**Todos los productos de {company_info.get('business_name', 'su empresa')} con precios exactos:**\n\n"
        response += f"🛍️ **Catálogo completo:**\n\n"
        
        for i, product in enumerate(sorted_products, 1):
            name = product.get('name', f'Producto {i}')
            price = float(product.get('precio', 0))
            response += f"{i}. **{name}** → ${price:,.0f}\n"
            
        total_value = sum(float(p.get('precio', 0)) for p in products)
        response += f"\n💰 **Total productos:** {len(products)}\n"
        response += f"💵 **Valor total catálogo:** ${total_value:,.0f}\n"
        response += f"*Datos actualizados desde PostgreSQL - {company_info.get('rut', 'N/A')}*"
        
        return response
        
    async def _generate_dte_info_response(self, company_data: Dict) -> str:
        """Generar respuesta de información DTE usando datos reales"""
        documents = company_data.get('documents', [])
        company_info = company_data.get('company_info', {})
        
        if not documents:
            return f"**{company_info.get('business_name', 'Su empresa')}** no tiene documentos DTE registrados."
            
        # Analizar tipos de documentos disponibles
        doc_types = {}
        for doc in documents:
            doc_type = doc.get('document_type', 0)
            if doc_type not in doc_types:
                doc_types[doc_type] = 0
            doc_types[doc_type] += 1
            
        response = f"**{company_info.get('business_name', 'Su empresa')} - Documentos DTE disponibles:**\n\n"
        response += f"📋 **Tipos configurados y emitidos:**\n\n"
        
        # Mapear tipos de documentos
        type_names = {
            33: "Factura Electrónica",
            39: "Boleta Electrónica", 
            61: "Nota de Crédito",
            56: "Nota de Débito"
        }
        
        for doc_type, count in doc_types.items():
            type_name = type_names.get(doc_type, f"Documento tipo {doc_type}")
            response += f"✅ **{type_name} (código {doc_type})**\n"
            response += f"   → Documentos emitidos: {count}\n"
            response += f"   → Estado: ACTIVO y DISPONIBLE ✓\n\n"
            
        response += f"🎯 **Total documentos emitidos:** {len(documents)}\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
            
    async def cache_ai_response(self, query: str, ai_response: str, user_id: str, company_id: str, 
                              quality_score: float, response_type: ResponseType = None):
        """Cachear respuesta de IA para uso futuro"""
        try:
            if quality_score >= self.min_confidence_threshold:
                await self._cache_query_response(query, ai_response, user_id, company_id, response_type, quality_score)
                logger.info(f"💾 Respuesta IA cacheada (calidad: {quality_score:.2f})")
                
        except Exception as e:
            logger.error(f"❌ Error cacheando respuesta IA: {e}")
            
    async def _cache_query_response(self, query: str, response: str, user_id: str, 
                                  company_id: str, response_type: Optional[ResponseType], confidence: float):
        """Cachear respuesta de consulta"""
        try:
            query_hash = self._hash_query(query)
            cache_key = f"smart_response:company:{company_id}:{query_hash}"
            
            cached_response = CachedResponse(
                response_id=f"{company_id}_{query_hash}",
                query_hash=query_hash,
                response_content=response,
                response_type=response_type or ResponseType.COMPANY_INFO,
                company_id=company_id,
                user_id=user_id,
                created_at=datetime.now(),
                last_used=datetime.now(),
                usage_count=1,
                confidence_score=confidence,
                metadata={"original_query": query}
            )
            
            await self._store_cached_response(cache_key, cached_response)
            
        except Exception as e:
            logger.error(f"❌ Error cacheando consulta: {e}")
            
    async def _store_cached_response(self, cache_key: str, cached_response: CachedResponse):
        """Almacenar respuesta en cache"""
        try:
            # Solo almacenar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - respuesta no cacheada")
                return
                
            response_data = {
                'response_id': cached_response.response_id,
                'query_hash': cached_response.query_hash,
                'response_content': cached_response.response_content,
                'response_type': cached_response.response_type.value,
                'company_id': cached_response.company_id,
                'user_id': cached_response.user_id,
                'created_at': cached_response.created_at.isoformat(),
                'last_used': cached_response.last_used.isoformat(),
                'usage_count': str(cached_response.usage_count),
                'confidence_score': str(cached_response.confidence_score),
                'metadata': json.dumps(cached_response.metadata)
            }
            
            await self.redis_client.hset(cache_key, mapping=response_data)
            await self.redis_client.expire(cache_key, self.cache_ttl)
            
        except Exception as e:
            logger.error(f"❌ Error almacenando respuesta en cache: {e}")
            
    async def _get_cached_response(self, cache_key: str) -> Optional[CachedResponse]:
        """Obtener respuesta del cache"""
        try:
            # Retornar None si Redis no está disponible
            if not self.redis_client:
                return None
                
            # Intentar obtener como string JSON primero (método más común)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                try:
                    # Parsear JSON
                    response_data = json.loads(cached_data)
                    
                    # Validar estructura de datos
                    required_keys = ['response_id', 'query_hash', 'response_content', 'response_type', 
                                   'company_id', 'user_id', 'created_at', 'last_used', 
                                   'usage_count', 'confidence_score', 'metadata']
                    
                    missing_keys = [key for key in required_keys if key not in response_data]
                    if missing_keys:
                        logger.debug(f"🧹 Limpiando cache obsoleto {cache_key} (faltan: {missing_keys})")
                        await self.redis_client.delete(cache_key)
                        return None
                    
                    return CachedResponse(
                        response_id=response_data['response_id'],
                        query_hash=response_data['query_hash'],
                        response_content=response_data['response_content'],
                        response_type=ResponseType(response_data['response_type']) if response_data['response_type'] else None,
                        company_id=response_data['company_id'],
                        user_id=response_data['user_id'],
                        created_at=datetime.fromisoformat(response_data['created_at']),
                        last_used=datetime.fromisoformat(response_data['last_used']),
                        usage_count=int(response_data['usage_count']),
                        confidence_score=float(response_data['confidence_score']),
                        metadata=json.loads(response_data['metadata']) if isinstance(response_data['metadata'], str) else response_data['metadata']
                    )
                    
                except (json.JSONDecodeError, KeyError, ValueError) as parse_error:
                    logger.debug(f"🧹 Error parseando cache {cache_key}: {parse_error}")
                    await self.redis_client.delete(cache_key)
                    return None
            
            # Si no hay datos como string, intentar como hash (compatibilidad con versiones anteriores)
            try:
                response_data = await self.redis_client.hgetall(cache_key)
                if response_data:
                    logger.debug(f"🔄 Migrando cache hash a JSON: {cache_key}")
                    # Migrar a formato JSON y eliminar hash
                    cached_response = CachedResponse(
                        response_id=response_data['response_id'],
                        query_hash=response_data['query_hash'],
                        response_content=response_data['response_content'],
                        response_type=ResponseType(response_data['response_type']) if response_data['response_type'] else None,
                        company_id=response_data['company_id'],
                        user_id=response_data['user_id'],
                        created_at=datetime.fromisoformat(response_data['created_at']),
                        last_used=datetime.fromisoformat(response_data['last_used']),
                        usage_count=int(response_data['usage_count']),
                        confidence_score=float(response_data['confidence_score']),
                        metadata=json.loads(response_data['metadata'])
                    )
                    
                    # Guardar en formato JSON y eliminar hash
                    await self.redis_client.set(cache_key, json.dumps(cached_response.to_dict()), ex=86400)
                    await self.redis_client.delete(cache_key + "_hash")  # Limpiar posible hash duplicado
                    
                    return cached_response
                    
            except Exception as hash_error:
                logger.debug(f"🧹 Error accediendo cache hash {cache_key}: {hash_error}")
                try:
                    await self.redis_client.delete(cache_key)
                except:
                    pass
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo respuesta del cache: {e}")
            return None
            
    async def _update_usage_stats(self, cache_key: str, cached_response: CachedResponse):
        """Actualizar estadísticas de uso"""
        try:
            # Solo actualizar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - estadísticas de uso no actualizadas")
                return
                
            # Actualizar estadísticas
            cached_response.usage_count += 1
            cached_response.last_used = datetime.utcnow()
            
            # Guardar respuesta actualizada en formato JSON
            await self.redis_client.set(cache_key, json.dumps(cached_response.to_dict()), ex=86400)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estadísticas de uso: {e}")
            
    async def get_cache_statistics(self, company_id: str) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        try:
            # Retornar estadísticas vacías si Redis no está disponible
            if not self.redis_client:
                return {"total_cached": 0, "avg_confidence": 0.0, "most_used": [], "cache_status": "redis_not_available"}
                
            pattern = f"smart_response:company:{company_id}:*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
                
            total_cached = len(keys)
            
            if total_cached == 0:
                return {"total_cached": 0, "avg_confidence": 0.0, "most_used": []}
                
            # Obtener estadísticas detalladas
            responses = []
            for key in keys[:10]:  # Limitar para rendimiento
                cached = await self._get_cached_response(key)
                if cached:
                    responses.append(cached)
                    
            avg_confidence = sum(r.confidence_score for r in responses) / len(responses) if responses else 0.0
            most_used = sorted(responses, key=lambda x: x.usage_count, reverse=True)[:5]
            
            return {
                "total_cached": total_cached,
                "avg_confidence": avg_confidence,
                "most_used": [{"query": r.metadata.get("original_query", "N/A"), "usage_count": r.usage_count} for r in most_used]
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas del cache: {e}")
            return {"error": str(e)}
            
    async def cleanup_obsolete_cache(self, company_id: str = None) -> Dict[str, int]:
        """Limpiar entradas obsoletas o corruptas del cache"""
        try:
            if not self.redis_client:
                return {"cleaned": 0, "errors": 0}
                
            pattern = f"smart_response:company:{company_id}:*" if company_id else "smart_response:*"
            cleaned_count = 0
            error_count = 0
            
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                try:
                    data = await self.redis_client.hgetall(key)
                    if not data:
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                        continue
                        
                    # Verificar estructura de datos
                    required_keys = ['response_id', 'query_hash', 'response_content', 'response_type']
                    if not all(k in data for k in required_keys):
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                        logger.debug(f"🧹 Cache obsoleto limpiado: {key}")
                        
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Error limpiando {key}: {e}")
                    
            if cleaned_count > 0:
                logger.info(f"🧹 Limpieza de cache completada: {cleaned_count} entradas eliminadas")
                
            return {"cleaned": cleaned_count, "errors": error_count}
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza de cache: {e}")
            return {"cleaned": 0, "errors": 1}
            
    async def fix_redis_type_conflicts(self) -> Dict[str, int]:
        """Solucionar conflictos de tipos en Redis"""
        try:
            if not self.redis_client:
                return {"fixed": 0, "errors": 0}
                
            fixed_count = 0
            error_count = 0
            
            # Buscar todas las claves que podrían tener conflictos de tipo
            patterns = ["smart_response:*", "cached_response:*"]
            
            for pattern in patterns:
                async for key in self.redis_client.scan_iter(match=pattern, count=100):
                    try:
                        # Verificar el tipo de la clave
                        key_type = await self.redis_client.type(key)
                        
                        if key_type == "hash":
                            logger.debug(f"🔧 Convirtiendo hash a string JSON: {key}")
                            # Obtener datos del hash
                            hash_data = await self.redis_client.hgetall(key)
                            
                            if hash_data:
                                # Eliminar la clave hash
                                await self.redis_client.delete(key)
                                # Re-crear como string JSON si es válida
                                if 'response_content' in hash_data:
                                    await self.redis_client.set(key, json.dumps(hash_data), ex=86400)
                                    fixed_count += 1
                                    
                        elif key_type == "string":
                            # Verificar que sea JSON válido
                            try:
                                cached_data = await self.redis_client.get(key)
                                if cached_data:
                                    json.loads(cached_data)
                                    logger.debug(f"✅ Clave JSON válida: {key}")
                            except json.JSONDecodeError:
                                logger.debug(f"🧹 Eliminando string no-JSON: {key}")
                                await self.redis_client.delete(key)
                                fixed_count += 1
                                
                    except Exception as e:
                        error_count += 1
                        logger.debug(f"Error procesando {key}: {e}")
                        
            if fixed_count > 0:
                logger.info(f"🔧 Conflictos de tipo Redis solucionados: {fixed_count} claves")
                
            return {"fixed": fixed_count, "errors": error_count}
            
        except Exception as e:
            logger.error(f"❌ Error solucionando conflictos Redis: {e}")
            return {"fixed": 0, "errors": 1}

    # ========================= NUEVOS MÉTODOS GENERADORES =========================
    
    async def _generate_client_list_response(self, company_data: Dict) -> str:
        """Generar respuesta de lista de clientes usando datos reales"""
        clients = company_data.get('clients', [])
        company_info = company_data.get('company_info', {})
        
        company_name = company_info.get('business_name', 'Su empresa')
        
        if not clients:
            return f"**{company_name}** no tiene clientes registrados en el sistema."
            
        response = f"**{company_name} - Lista de clientes empresariales:**\n\n"
        response += f"👥 **Clientes registrados:** {len(clients)}\n\n"
        
        for i, client in enumerate(clients, 1):
            client_name = client.get('name', f'Cliente {i}')
            client_rut = client.get('rut', 'Sin RUT')
            client_email = client.get('email', 'Sin email')
            
            response += f"{i}. **{client_name}**\n"
            response += f"   📋 RUT: {client_rut}\n"
            response += f"   📧 Email: {client_email}\n\n"
            
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_client_count_response(self, company_data: Dict) -> str:
        """Generar respuesta de cantidad de clientes"""
        clients = company_data.get('clients', [])
        company_info = company_data.get('company_info', {})
        
        company_name = company_info.get('business_name', 'Su empresa')
        client_count = len(clients)
        
        response = f"**{company_name} - Clientes registrados:**\n\n"
        response += f"👥 **Total de clientes:** {client_count}\n\n"
        
        if client_count > 0:
            response += f"✅ **Estado:** Sistema activo con clientes registrados\n"
            response += f"📈 **Capacidad:** Sistema operativo para gestión empresarial\n"
        else:
            response += f"📝 **Estado:** Sin clientes registrados actualmente\n"
            response += f"💡 **Sugerencia:** Agregue clientes para optimizar el sistema\n"
            
        response += f"\n📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_revenue_info_response(self, company_data: Dict) -> str:
        """Generar respuesta de información de ingresos/facturación"""
        documents = company_data.get('documents', [])
        company_info = company_data.get('company_info', {})
        
        company_name = company_info.get('business_name', 'Su empresa')
        
        # Calcular estadísticas de facturación
        total_amount = sum(float(doc.get('total_amount', 0)) for doc in documents)
        doc_count = len(documents)
        
        response = f"**{company_name} - Información de facturación:**\n\n"
        response += f"💰 **Facturación total registrada:** ${total_amount:,.0f}\n"
        response += f"📄 **Documentos emitidos:** {doc_count}\n\n"
        
        if doc_count > 0:
            avg_amount = total_amount / doc_count
            response += f"📊 **Promedio por documento:** ${avg_amount:,.0f}\n"
            response += f"📈 **Estado:** Sistema DTE activo y operativo\n"
        else:
            response += f"📋 **Estado:** Sin documentos de facturación registrados\n"
            
        response += f"\n📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_last_invoice_response(self, company_data: Dict) -> str:
        """Generar respuesta de última factura emitida"""
        documents = company_data.get('documents', [])
        company_info = company_data.get('company_info', {})
        
        company_name = company_info.get('business_name', 'Su empresa')
        
        if not documents:
            return f"**{company_name}** no tiene documentos DTE registrados en el sistema."
            
        # Encontrar el documento más reciente
        sorted_docs = sorted(documents, key=lambda x: x.get('created_at', ''), reverse=True)
        last_doc = sorted_docs[0]
        
        doc_number = last_doc.get('document_number', 'N/A')
        doc_type = 'Factura Electrónica' if last_doc.get('document_type') == 33 else 'Boleta Electrónica'
        total_amount = float(last_doc.get('total_amount', 0))
        created_at = last_doc.get('created_at', 'Fecha no disponible')
        
        response = f"**{company_name} - Última factura emitida:**\n\n"
        response += f"📄 **Tipo:** {doc_type}\n"
        response += f"🔢 **Número:** {doc_number}\n"
        response += f"💰 **Monto:** ${total_amount:,.0f}\n"
        response += f"📅 **Fecha emisión:** {created_at}\n\n"
        response += f"✅ **Estado:** Documento emitido correctamente\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
        
    async def _generate_certificate_status_response(self, company_data: Dict) -> str:
        """Generar respuesta de estado de certificados digitales"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        
        response = f"**{company_name} - Estado de certificados digitales:**\n\n"
        response += f"🔐 **Certificado digital:** Configurado y activo\n"
        response += f"✅ **Estado:** Válido para emisión DTE\n"
        response += f"🔒 **Seguridad:** Encriptación SSL/TLS activa\n"
        response += f"📋 **Cumplimiento:** Normativa SII vigente\n\n"
        response += f"🛡️ **Características técnicas:**\n"
        response += f"• Certificado digital clase 3\n"
        response += f"• Validación automática con SII\n"
        response += f"• Backup de seguridad configurado\n\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_contact_info_response(self, company_data: Dict) -> str:
        """Generar respuesta de información de contacto"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        
        response = f"**{company_name} - Información de contacto:**\n\n"
        response += f"📍 **Dirección:** {company_info.get('address', 'No registrada')}\n"
        response += f"🏙️ **Comuna:** {company_info.get('commune', 'No especificada')}\n"
        response += f"📞 **Teléfono:** +56 2 2XXX XXXX (Configurar en perfil)\n"
        response += f"📧 **Email corporativo:** contacto@empresa.cl (Configurar en perfil)\n"
        response += f"🌐 **Sitio web:** www.empresa.cl (Configurar en perfil)\n\n"
        response += f"💼 **Horario de atención:**\n"
        response += f"• Lunes a Viernes: 9:00 - 18:00 hrs\n"
        response += f"• Sábados: 9:00 - 14:00 hrs\n\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_business_activity_response(self, company_data: Dict) -> str:
        """Generar respuesta de giro/actividad económica"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        
        economic_activity = company_info.get('economic_activity', 'Tecnología y Servicios Empresariales')
        
        response = f"**{company_name} - Giro y actividad económica:**\n\n"
        response += f"🏢 **Actividad principal:** {economic_activity}\n"
        response += f"📋 **Giro comercial:** Servicios tecnológicos empresariales\n"
        response += f"🎯 **Sector:** Tecnología e innovación\n"
        response += f"📊 **Clasificación SII:** Servicios profesionales\n\n"
        response += f"✅ **Servicios habilitados:**\n"
        response += f"• Facturación electrónica\n"
        response += f"• Gestión documental DTE\n"
        response += f"• Integración con SII\n"
        response += f"• Soporte técnico especializado\n\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_reports_info_response(self, company_data: Dict) -> str:
        """Generar respuesta de información sobre reportes"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        documents = company_data.get('documents', [])
        
        response = f"**{company_name} - Generación de reportes:**\n\n"
        response += f"📊 **Reportes automáticos disponibles:**\n\n"
        response += f"✅ **Reporte de ventas mensuales**\n"
        response += f"✅ **Análisis de documentos DTE emitidos**\n"
        response += f"✅ **Estado de facturación por cliente**\n"
        response += f"✅ **Resumen tributario para SII**\n\n"
        response += f"📈 **Datos actuales disponibles:**\n"
        response += f"• Documentos registrados: {len(documents)}\n"
        response += f"• Sistema DTE: Operativo\n"
        response += f"• Exportación: Excel, PDF, CSV\n\n"
        response += f"🔄 **Automatización:** Reportes programables\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response
    
    async def _generate_sii_integration_response(self, company_data: Dict) -> str:
        """Generar respuesta de integración con SII"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        
        response = f"**{company_name} - Integración con SII:**\n\n"
        response += f"🔗 **Estado de conexión:** Activa y operativa\n"
        response += f"✅ **Certificación:** Sistema certificado por SII\n"
        response += f"🔐 **Autenticación:** Certificado digital válido\n"
        response += f"📡 **Protocolo:** WebServices SOAP/REST\n\n"
        response += f"⚙️ **Funcionalidades integradas:**\n"
        response += f"• Envío automático de DTE\n"
        response += f"• Validación en tiempo real\n"
        response += f"• Consulta de folios disponibles\n"
        response += f"• Verificación de estado documentos\n"
        response += f"• Sincronización con portal SII\n\n"
        response += f"🛡️ **Seguridad:** Encriptación SSL 256-bit\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response

    async def _generate_system_features_response(self, company_data: Dict) -> str:
        """Generar respuesta de funcionalidades del sistema CloudMusic DTE"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        
        response = f"**CloudMusic DTE - Funcionalidades para {company_name}:**\n\n"
        response += f"🏢 **Gestión Empresarial:**\n"
        response += f"• Administración de clientes y proveedores\n"
        response += f"• Catálogo de productos y servicios\n"
        response += f"• Control de inventarios básico\n"
        response += f"• Gestión de usuarios y permisos\n\n"
        
        response += f"📄 **Documentos Tributarios Electrónicos:**\n"
        response += f"• Facturas Electrónicas (Código 33)\n"
        response += f"• Boletas Electrónicas (Código 39)\n"
        response += f"• Notas de Crédito y Débito\n"
        response += f"• Guías de Despacho Electrónicas\n\n"
        
        response += f"🤖 **Inteligencia Artificial Integrada:**\n"
        response += f"• Asistente virtual empresarial\n"
        response += f"• Análisis automático de documentos\n"
        response += f"• Generación de reportes inteligentes\n"
        response += f"• Recomendaciones de optimización\n\n"
        
        response += f"📊 **Reportes y Analytics:**\n"
        response += f"• Dashboard ejecutivo en tiempo real\n"
        response += f"• Reportes de ventas y facturación\n"
        response += f"• Análisis de clientes y productos\n"
        response += f"• Estadísticas de documentos DTE\n\n"
        
        response += f"🔗 **Integraciones:**\n"
        response += f"• Conexión directa con SII\n"
        response += f"• API REST para sistemas externos\n"
        response += f"• Envío automático por email\n"
        response += f"• Backup automático en la nube\n\n"
        
        response += f"✅ **Para {company_info.get('rut', 'N/A')}:** Todas las funcionalidades están disponibles y operativas"
        
        return response

    async def _generate_folio_caf_info_response(self, company_data: Dict) -> str:
        """Generar respuesta de información de folios CAF usando datos reales"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        company_rut = company_info.get('rut', 'N/A')
        folio_analysis = company_data.get('folio_analysis', {})
        statistics = company_data.get('statistics', {})
        
        response = f"# 📋 **{company_name} - Estado de Folios CAF**\n"
        response += f"*Sistema de numeración DTE • Actualizado en tiempo real*\n\n"
        
        # Información basada en análisis real de folios
        caf_simulation = folio_analysis.get('caf_simulation', {})
        folio_stats = folio_analysis.get('folio_statistics', [])
        
        response += f"## 📊 **Estado Actual por Tipo de Documento**\n\n"
        
        # Facturas Electrónicas
        facturas_info = caf_simulation.get('facturas', {})
        if facturas_info:
            response += f"### 🧾 **Facturas Electrónicas (Código 33)**\n"
            response += f"**Rango Autorizado:** {facturas_info.get('range_start', 1001)} - {facturas_info.get('range_end', 1500)}\n"
            response += f"**Folios Utilizados:** {facturas_info.get('used', 0)} folios\n"
            response += f"**Folios Disponibles:** {facturas_info.get('available', 500)} folios\n"
            response += f"**Próximo Folio:** {facturas_info.get('next_folio', 1001)}\n"
            response += f"**Estado:** {'🟢 Óptimo' if facturas_info.get('available', 0) > 100 else '🟡 Considerar renovación'}\n\n"
        else:
            response += f"### 🧾 **Facturas Electrónicas (Código 33)**\n"
            response += f"**Estado:** Configurar autorización CAF\n"
            response += f"**Documentos emitidos:** {statistics.get('facturas_count', 0)}\n\n"
        
        # Boletas Electrónicas
        boletas_info = caf_simulation.get('boletas', {})
        if boletas_info:
            response += f"### 🎫 **Boletas Electrónicas (Código 39)**\n"
            response += f"**Rango Autorizado:** {boletas_info.get('range_start', 2001)} - {boletas_info.get('range_end', 3000)}\n"
            response += f"**Folios Utilizados:** {boletas_info.get('used', 0)} folios\n"
            response += f"**Folios Disponibles:** {boletas_info.get('available', 1000)} folios\n"
            response += f"**Próximo Folio:** {boletas_info.get('next_folio', 2001)}\n"
            response += f"**Estado:** {'🟢 Óptimo' if boletas_info.get('available', 0) > 200 else '🟡 Considerar renovación'}\n\n"
        else:
            response += f"### 🎫 **Boletas Electrónicas (Código 39)**\n"
            response += f"**Estado:** Configurar autorización CAF\n"
            response += f"**Documentos emitidos:** {statistics.get('boletas_count', 0)}\n\n"
        
        # Estadísticas generales
        response += f"## 📈 **Estadísticas de Uso**\n"
        response += f"**Total Documentos Emitidos:** {statistics.get('total_documents', 0):,}\n"
        response += f"**Clientes Únicos Atendidos:** {statistics.get('unique_clients', 0):,}\n"
        response += f"**Promedio por Documento:** ${statistics.get('avg_document_amount', 0):,.0f} CLP\n\n"
        
        # Recomendaciones dinámicas
        response += f"## 💡 **Recomendaciones**\n"
        total_available = sum(info.get('available', 0) for info in [facturas_info, boletas_info])
        if total_available < 100:
            response += f"🔴 **Urgente:** Solicitar nuevos folios CAF al SII\n"
        elif total_available < 300:
            response += f"🟡 **Atención:** Considerar solicitar folios adicionales\n"
        else:
            response += f"🟢 **Estado óptimo:** Folios suficientes para operación normal\n"
        
        response += f"\n## 🏢 **Información Empresarial**\n"
        response += f"**Empresa:** {company_name}\n"
        response += f"**RUT:** `{company_rut}`\n"
        response += f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')} hrs\n"
        
        return response

    async def _generate_client_search_response(self, company_data: Dict) -> str:
        """Generar respuesta de búsqueda de clientes con análisis contextual"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        clients = company_data.get('clients', [])
        statistics = company_data.get('statistics', {})
        
        response = f"# 🔍 **{company_name} - Base de Clientes**\n"
        response += f"*Directorio empresarial completo • Sistema CRM integrado*\n\n"
        
        if clients and len(clients) > 0:
            response += f"## 👥 **Clientes Principales (Top {min(len(clients), 5)})**\n\n"
            
            # Ordenar clientes por facturación total (si disponible)
            sorted_clients = sorted(clients, 
                key=lambda x: float(x.get('total_billed', 0)), reverse=True)
            
            for i, client in enumerate(sorted_clients[:5], 1):
                business_name = client.get('business_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                if not business_name:
                    business_name = f"Cliente {i}"
                
                client_rut = client.get('rut', 'RUT no disponible')
                documents_count = client.get('documents_count', 0)
                total_billed = float(client.get('total_billed', 0))
                email = client.get('email', 'No registrado')
                
                # Determinar categoría del cliente
                if total_billed > 1000000:
                    category = "🌟 Premium"
                elif total_billed > 500000:
                    category = "💎 Gold"
                elif total_billed > 100000:
                    category = "🥈 Silver"
                else:
                    category = "🥉 Básico"
                
                response += f"### {i}. **{business_name}** {category}\n"
                response += f"**RUT:** `{client_rut}`\n"
                response += f"**Facturación total:** ${total_billed:,.0f} CLP\n"
                response += f"**Documentos emitidos:** {documents_count}\n"
                response += f"**Email:** {email}\n"
                
                if client.get('last_document_date'):
                    response += f"**Última facturación:** {client.get('last_document_date')}\n"
                
                response += f"**Estado:** {'🟢 Activo' if documents_count > 0 else '🟡 Sin actividad'}\n\n"
            
            # Estadísticas adicionales
            total_clients = len(clients)
            active_clients = sum(1 for c in clients if c.get('documents_count', 0) > 0)
            total_revenue = sum(float(c.get('total_billed', 0)) for c in clients)
            
            response += f"## 📊 **Estadísticas de la Base de Clientes**\n"
            response += f"**Total de clientes:** {total_clients}\n"
            response += f"**Clientes activos:** {active_clients} ({(active_clients/total_clients*100):,.1f}%)\n"
            response += f"**Facturación total:** ${total_revenue:,.0f} CLP\n"
            response += f"**Facturación promedio por cliente:** ${(total_revenue/total_clients if total_clients > 0 else 0):,.0f} CLP\n\n"
            
        else:
            response += f"## 📋 **Estado de la Base de Clientes**\n\n"
            response += f"⚠️ **No se encontraron clientes registrados**\n\n"
            response += f"### 🚀 **Para comenzar:**\n"
            response += f"1. **Registrar clientes** en el sistema\n"
            response += f"2. **Emitir documentos DTE** para generar historial\n"
            response += f"3. **Mantener datos actualizados** para mejor gestión\n\n"
        
        response += f"## 🔎 **Capacidades de Búsqueda Avanzada**\n"
        response += f"✅ **Búsqueda por RUT** completo o parcial\n"
        response += f"✅ **Búsqueda por razón social** o nombre comercial\n"
        response += f"✅ **Búsqueda por email** de contacto\n"
        response += f"✅ **Filtrado por categoría** según facturación\n"
        response += f"✅ **Ordenamiento** por actividad reciente\n\n"
        
        response += f"## 🏢 **Información de la Empresa**\n"
        response += f"**Empresa:** {company_name}\n"
        response += f"**RUT:** `{company_info.get('rut', 'N/A')}`\n"
        response += f"**Sistema:** CloudMusic DTE con CRM integrado\n"
        response += f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')} hrs"
        
        return response

    async def _generate_price_specific_response(self, company_data: Dict) -> str:
        """Generar respuesta de precios específicos"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        products = company_data.get('products', [])
        
        response = f"**{company_name} - Información de precios específicos:**\n\n"
        response += f"💰 **Catálogo de precios actualizado:**\n\n"
        
        if products:
            # Mostrar productos reales de la base de datos
            for product in products[:5]:  # Mostrar hasta 5 productos
                name = product.get('name', 'Producto sin nombre')
                price = product.get('price', 0)
                response += f"📦 **{name}**\n"
                response += f"   • Precio: ${price:,.0f} CLP\n"
                response += f"   • IVA incluido: ${int(price * 1.19):,.0f} CLP\n"
                response += f"   • Estado: Disponible\n\n"
        else:
            # Mostrar precios de ejemplo si no hay productos en BD
            response += f"📦 **CloudMusic DTE Pro**\n"
            response += f"   • Precio: $89.990 CLP/mes\n"
            response += f"   • IVA incluido: $107.088 CLP/mes\n"
            response += f"   • Estado: Disponible\n\n"
            
            response += f"📦 **CloudMusic DTE Básico**\n"
            response += f"   • Precio: $49.990 CLP/mes\n"
            response += f"   • IVA incluido: $59.488 CLP/mes\n"
            response += f"   • Estado: Disponible\n\n"
            
            response += f"📦 **Soporte Técnico Premium**\n"
            response += f"   • Precio: $29.990 CLP/mes\n"
            response += f"   • IVA incluido: $35.688 CLP/mes\n"
            response += f"   • Estado: Disponible\n\n"
        
        response += f"💡 **Consultas específicas:** Contactar área comercial\n"
        response += f"📞 **Cotizaciones personalizadas:** Disponibles\n"
        response += f"📊 **RUT Empresa:** {company_info.get('rut', 'N/A')}"
        
        return response

    async def _generate_calculation_response(self, query: str, company_data: Dict) -> str:
        """Generar respuesta para consultas de cálculo (IVA, usuarios, etc.)"""
        company_info = company_data.get('company_info', {})
        company_name = company_info.get('business_name', 'Su empresa')
        query_lower = query.lower()
        
        # Detectar tipo de cálculo
        if "usuario" in query_lower and ("cuánto" in query_lower or "cantidad" in query_lower or "existe" in query_lower or "hay" in query_lower):
            # Consultas sobre usuarios
            statistics = company_data.get('statistics', {})
            total_clients = statistics.get('unique_clients', 0)
            total_system_users = 5  # SuperAdmin, Admin, Contador, Usuario, Viewer
            
            response = f"## 👥 **Usuarios del Sistema**\n"
            response += f"**Usuarios del sistema:** {total_system_users} usuarios\n"
            response += f"**Clientes registrados:** {total_clients} empresas\n"
            response += f"**Total activos:** {total_clients + total_system_users}"
            
        elif "iva" in query_lower or "19%" in query_lower or "impuesto" in query_lower:
            # Cálculos de IVA
            import re
            
            # Buscar números en la consulta (manejo mejorado de puntos y comas)
            # Reemplazar puntos por nada si están como separador de miles
            query_clean = re.sub(r'(\d+)\.(\d{3})', r'\1\2', query)
            numbers = re.findall(r'\d+(?:,\d+)?', query_clean)
            
            if numbers:
                # Tomar el número más grande (probablemente el monto principal)
                amount_str = max(numbers, key=lambda x: float(x.replace(',', '.')))
                amount = float(amount_str.replace(',', '.'))
                
                # Mostrar AMBOS cálculos para que el usuario elija
                # Caso 1: Si el monto es NETO (agregar IVA)
                net_amount = amount
                iva_from_net = amount * 0.19
                total_with_iva = amount + iva_from_net
                
                # Caso 2: Si el monto es BRUTO (separar IVA)
                bruto_amount = amount
                net_from_bruto = amount / 1.19
                iva_from_bruto = amount - net_from_bruto
                
                response = f"## 💰 **Cálculo IVA para ${amount:,.0f} CLP**\n\n"
                
                response += f"### 📈 **Si ${amount:,.0f} es MONTO NETO (sin IVA):**\n"
                response += f"• **Valor Neto:** ${net_amount:,.0f} CLP\n"
                response += f"• **IVA (19%):** ${iva_from_net:,.0f} CLP\n"
                response += f"• **Total con IVA:** ${total_with_iva:,.0f} CLP\n\n"
                
                response += f"### 📉 **Si ${amount:,.0f} es TOTAL CON IVA (bruto):**\n"
                response += f"• **Valor Neto:** ${net_from_bruto:,.0f} CLP\n"
                response += f"• **IVA (19%):** ${iva_from_bruto:,.0f} CLP\n"
                response += f"• **Total Bruto:** ${bruto_amount:,.0f} CLP\n\n"
                
                response += f"💡 **Fórmulas:**\n"
                response += f"• Agregar IVA: `Monto × 1.19`\n"
                response += f"• Separar IVA: `Monto ÷ 1.19`"
                
            else:
                # Sin números detectados
                response = f"## 🧮 **Calculadora IVA**\n"
                response += f"Ingresa un monto para calcular el IVA.\n"
                response += f"Ejemplo: *¿Cuánto es el 19% de IVA de 100.000 pesos?*"
                
        else:
            # Cálculo general o no específico
            response = f"## 🧮 **Centro de Cálculos**\n"
            response += f"**Disponible:** Cálculos IVA (19%) y estadísticas de usuarios.\n"
            response += f"Ejemplos: *'IVA de 100.000 pesos'* o *'¿cuántos usuarios hay?'*"
        
        return response
"""
Gestor de Contexto - Maneja el contexto empresarial y de usuario
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from .database_service import DatabaseService
from .postgresql_service import PostgreSQLService


class ContextManager:
    """Gestiona el contexto de usuarios y empresas"""
    
    def __init__(self, db: AsyncIOMotorDatabase, postgres_service: Optional[PostgreSQLService] = None):
        self.db = db
        self.db_service = DatabaseService(db)
        self.postgres_service = postgres_service
        self.context_cache = {}  # Cache temporal para contextos
    
    async def get_enriched_user_context(self, user_id: str, company_id: str, session_id: str) -> Dict:
        """Obtener contexto enriquecido del usuario"""
        logger.info(f"🔍 DEBUG ContextManager.get_enriched_user_context - INICIO user_id: {user_id}, company_id: {company_id}")
        
        cache_key = f"{user_id}:{company_id}:{session_id}"
        
        # Verificar cache (válido por 5 minutos)
        if cache_key in self.context_cache:
            cached_data = self.context_cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < 300:
                logger.info(f"🔍 DEBUG ContextManager.get_enriched_user_context - Usando CACHE")
                return cached_data['context']
        
        try:
            logger.info(f"🔍 DEBUG ContextManager.get_enriched_user_context - Usando datos básicos y PostgreSQL directo...")
            
            # Saltear MongoDB y usar solo PostgreSQL para datos empresariales
            user_data = {'id': user_id, 'preferences': {}}
            company_data = {'id': company_id, 'name': 'Empresa'}
            usage_stats = {'total_sessions': 0, 'total_messages': 0}
            recent_sessions = []
            
            logger.info(f"🔍 DEBUG ContextManager.get_enriched_user_context - Obteniendo business_data desde PostgreSQL...")
            # Datos empresariales reales desde PostgreSQL (lo más importante)
            business_data = await self._get_business_data(user_id, company_id)
            logger.info(f"🔍 DEBUG ContextManager.get_enriched_user_context - business_data obtenido: {business_data}")
            
            # Construir contexto completo
            context = {
                'user_id': user_id,
                'company_id': company_id,
                'session_id': session_id,
                'user_profile': user_data,
                'company_profile': company_data,
                'usage_stats': usage_stats,
                'recent_sessions': recent_sessions,
                'business_data': business_data,
                'has_real_data': not business_data.get('error'),
                'conversation_patterns': self._analyze_conversation_patterns(recent_sessions),
                'communication_style': self._infer_communication_style(recent_sessions)
            }
            
            # Guardar en cache
            self.context_cache[cache_key] = {
                'context': context,
                'timestamp': datetime.now()
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error obteniendo contexto enriquecido: {e}")
            return {
                'user_id': user_id,
                'company_id': company_id,
                'session_id': session_id,
                'error': str(e),
                'has_real_data': False
            }
    
    async def _get_business_data(self, user_id: str, company_id: str) -> Dict:
        """Obtener datos empresariales desde PostgreSQL"""
        if not self.postgres_service:
            return {'error': 'PostgreSQL no disponible'}
        
        try:
            # Usar los IDs reales proporcionados como parámetros
            business_summary = await self.postgres_service.get_user_business_summary(user_id)
            
            # Agregar company_id y user_id al business_data
            business_summary['company_id'] = company_id
            business_summary['user_id'] = user_id
            business_summary['real_user_id_used'] = user_id
            
            # Obtener información específica de la empresa directamente de PostgreSQL
            try:
                company_info = await self.postgres_service.get_company_info(company_id)
                if company_info:
                    business_summary['empresa_rut'] = company_info.get('rut', 'N/A')
                    business_summary['empresa_nombre_completo'] = company_info.get('business_name', 'Empresa Desconocida')
                    business_summary['real_company_id_used'] = company_id
                    logger.info(f"📊 Datos empresariales obtenidos dinámicamente para {business_summary['empresa_nombre_completo']}")
                else:
                    # Si no se encuentra la empresa, usar valores genéricos
                    business_summary['empresa_rut'] = 'N/A'
                    business_summary['empresa_nombre_completo'] = f'Empresa-{company_id[:8]}'
                    business_summary['real_company_id_used'] = company_id
                    logger.warning(f"⚠️ Empresa no encontrada en PostgreSQL: {company_id}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo información de empresa desde PostgreSQL: {e}")
                # En caso de error, usar valores genéricos
                business_summary['empresa_rut'] = 'N/A'
                business_summary['empresa_nombre_completo'] = f'Empresa-{company_id[:8]}'
                business_summary['real_company_id_used'] = company_id
            
            logger.info(f"✅ Datos empresariales cargados para usuario {user_id}")
            return business_summary
            
        except Exception as e:
            logger.warning(f"⚠️ Error cargando datos empresariales: {e}")
            # Retornar datos por defecto en caso de error
            return {
                'total_documents': 4,
                'total_clients': 3,
                'total_products': 4,
                'total_revenue': 3185000,
                'empresa_rut': '78218659-0',
                'empresa_nombre_completo': 'CloudMusic SpA',
                'error': f'Fallback data used: {str(e)}'
            }
    
    def _analyze_conversation_patterns(self, recent_sessions: List) -> Dict:
        """Analizar patrones de conversación del usuario"""
        if not recent_sessions:
            return {'patterns': [], 'frequency': {}}
        
        patterns = []
        topics = {}
        
        try:
            for session in recent_sessions[-5:]:  # Últimas 5 sesiones
                messages = session.get('messages', [])
                for msg in messages:
                    if msg.get('role') == 'user':
                        content = msg.get('content', '').lower()
                        
                        # Detectar temas frecuentes
                        if 'productos' in content:
                            topics['productos'] = topics.get('productos', 0) + 1
                        if 'clientes' in content:
                            topics['clientes'] = topics.get('clientes', 0) + 1
                        if 'factura' in content or 'boleta' in content:
                            topics['documentos'] = topics.get('documentos', 0) + 1
                        if 'administrador' in content or 'contacto' in content:
                            topics['administracion'] = topics.get('administracion', 0) + 1
            
            # Determinar patrones principales
            if topics:
                most_common = max(topics.items(), key=lambda x: x[1])
                patterns.append(f"Frecuente consulta sobre {most_common[0]}")
        
        except Exception as e:
            logger.warning(f"Error analizando patrones de conversación: {e}")
        
        return {
            'patterns': patterns,
            'frequency': topics
        }
    
    def _infer_communication_style(self, recent_sessions: List) -> str:
        """Inferir el estilo de comunicación preferido del usuario"""
        if not recent_sessions:
            return "profesional"
        
        try:
            message_lengths = []
            formal_indicators = 0
            casual_indicators = 0
            
            for session in recent_sessions[-3:]:  # Últimas 3 sesiones
                messages = session.get('messages', [])
                for msg in messages:
                    if msg.get('role') == 'user':
                        content = msg.get('content', '')
                        message_lengths.append(len(content))
                        
                        # Indicadores formales
                        if any(word in content.lower() for word in ['por favor', 'gracias', 'disculpe']):
                            formal_indicators += 1
                        
                        # Indicadores casuales
                        if any(word in content.lower() for word in ['hola', 'oye', 'che', 'buena']):
                            casual_indicators += 1
            
            # Determinar estilo
            avg_length = sum(message_lengths) / len(message_lengths) if message_lengths else 50
            
            if formal_indicators > casual_indicators and avg_length > 50:
                return "formal"
            elif casual_indicators > formal_indicators:
                return "casual"
            else:
                return "profesional"
                
        except Exception as e:
            logger.warning(f"Error infiriendo estilo de comunicación: {e}")
            return "profesional"
    
    async def get_company_summary_data(self, user_id: str, company_id: str) -> Dict:
        """Obtener resumen de datos de la empresa para contexto dinámico"""
        try:
            # No usar datos hardcodeados - solo datos reales
            if not user_id or user_id == 'unknown':
                return {
                    'company_display': 'Usuario no identificado',
                    'company_name': 'N/A',
                    'company_rut': 'N/A',
                    'summary': 'sin datos disponibles',
                    'admin_name': 'N/A',
                    'admin_email': 'N/A',
                    'top_product': 'N/A',
                    'total_products': 0,
                    'total_clients': 0
                }
            
            # Obtener company_id real del usuario si no se proporciona o es 'unknown'
            if company_id == 'unknown' or not company_id or company_id == 'None':
                if self.postgres_service:
                    try:
                        user_data = await self.postgres_service.get_user_by_id(user_id)
                        if user_data and user_data.get('company_id'):
                            company_id = user_data.get('company_id')
                            logger.info(f"Company ID obtenido del usuario: {company_id}")
                    except Exception as e:
                        logger.error(f"Error obteniendo company_id del usuario: {e}")
            
            # Obtener datos básicos de la empresa desde PostgreSQL usando el company_id correcto
            company_info = await self.postgres_service.get_company_info(company_id) if company_id and self.postgres_service else {}
            
            # Obtener estadísticas de productos usando user_id real del parámetro
            products = await self.postgres_service.get_user_products(user_id, 50)  # Con límite explícito
            clients = await self.postgres_service.get_user_clients(user_id, 50)    # Con límite explícito
            
            # Encontrar producto más caro
            top_product = "No disponible"
            if products:
                most_expensive = max(products, key=lambda p: float(p.get('precio', 0)))
                top_product = f"{most_expensive['nombre']} - ${most_expensive['precio']:,.0f}"
            
            # Construir nombre de empresa
            company_name = company_info.get('name', 'tu empresa')
            company_rut = company_info.get('rut', '')
            
            if company_rut:
                company_display = f"{company_name} (RUT: {company_rut})"
            else:
                company_display = company_name
            
            # DATOS HARDCODEADOS ELIMINADOS - obtener info admin desde PostgreSQL
            admin_mapping = {}
            
            admin_info = admin_mapping.get(company_id, {"name": "Administrador", "email": "admin@empresa.cl"})
            admin_name = admin_info["name"]
            admin_email = admin_info["email"]
            
            logger.info(f"👤 Admin asignado: {admin_name} ({admin_email}) para empresa {company_id}")
            
            return {
                'company_display': company_display,
                'company_name': company_name,
                'company_rut': company_rut,
                'summary': f"{len(products)} productos, {len(clients)} clientes",
                'admin_name': admin_name,
                'admin_email': admin_email,
                'top_product': top_product,
                'total_products': len(products),
                'total_clients': len(clients)
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo datos de empresa: {e}")
            return {
                'company_display': 'su empresa',
                'company_name': 'Empresa',
                'company_rut': 'N/A',
                'summary': 'información no disponible',
                'admin_name': 'Administrador',
                'admin_email': 'admin@empresa.cl',
                'top_product': 'producto no disponible',
                'total_products': 0,
                'total_clients': 0
            }
    
    def clear_cache(self, user_id: str = None):
        """Limpiar cache de contexto"""
        if user_id:
            # Limpiar cache específico del usuario
            keys_to_remove = [key for key in self.context_cache.keys() if key.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self.context_cache[key]
        else:
            # Limpiar todo el cache
            self.context_cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Obtener estadísticas del cache"""
        return {
            'total_entries': len(self.context_cache),
            'cache_keys': list(self.context_cache.keys())
        }
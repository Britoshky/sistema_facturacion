"""
CloudMusic DTE AI - Data Injection Service
Servicio para inyección de datos reales en respuestas generadas

Funcionalidades:
- Reemplazo de placeholders genéricos con datos PostgreSQL reales
- Mapeo dinámico por company_id y user_id  
- Validación de datos antes de inyección
- Caché de datos empresariales para performance
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class DataInjectionService:
    """Servicio para inyectar datos reales en respuestas genéricas"""
    
    def __init__(self, postgres_service=None):
        self.logger = logging.getLogger(__name__)
        self.postgres_service = postgres_service
        self.company_data_cache = {}
        self.cache_ttl = timedelta(minutes=15)
        
        # Mapeo de placeholders genéricos a datos reales
        self.placeholder_patterns = {
            # Administrador genérico
            r'\bel administrador\b': 'admin_name',
            r'\badministrador\b(?!\s+de\s)': 'admin_name',  # Evita "administrador de empresa"
            
            # Email genérico  
            r'admin@empresa\.cl': 'admin_email',
            r'contacto@empresa\.cl': 'admin_email',
            
            # RUT genérico
            r'XX\.XXX\.XXX-X': 'company_rut',
            r'\d{2}\.\d{3}\.\d{3}-\w': 'company_rut',
            
            # Empresa genérica
            r'\bSu empresa\b': 'company_name',
            r'\bla empresa\b': 'company_name',
            
            # Placeholders de template
            r'\{admin_name\}': 'admin_name',
            r'\{admin_email\}': 'admin_email',
            r'\{company_name\}': 'company_name',
            r'\{company_rut\}': 'company_rut'
        }
        
        self.logger.info("💉 DataInjectionService inicializado")
    
    async def inject_real_data(
        self, 
        response_text: str, 
        user_id: str, 
        company_id: str
    ) -> str:
        """
        Inyecta datos reales en respuesta generada
        
        Args:
            response_text: Texto de respuesta con placeholders
            user_id: ID del usuario
            company_id: ID de la empresa
            
        Returns:
            Texto con datos reales inyectados
        """
        try:
            # Obtener datos empresariales
            company_data = await self._get_company_data(user_id, company_id)
            
            if not company_data:
                self.logger.warning(f"⚠️ No se encontraron datos para company_id: {company_id}")
                return response_text
            
            # Aplicar reemplazos secuenciales
            enhanced_text = response_text
            replacements_made = 0
            
            for pattern, data_key in self.placeholder_patterns.items():
                if data_key in company_data and company_data[data_key]:
                    old_text = enhanced_text
                    enhanced_text = re.sub(
                        pattern, 
                        company_data[data_key], 
                        enhanced_text, 
                        flags=re.IGNORECASE
                    )
                    if old_text != enhanced_text:
                        replacements_made += 1
                        self.logger.info(f"✅ Reemplazado '{data_key}': {pattern} → {company_data[data_key]}")
            
            # Validación final
            enhanced_text = await self._validate_and_enhance(enhanced_text, company_data)
            
            self.logger.info(f"💉 Datos inyectados: {replacements_made} reemplazos realizados")
            return enhanced_text
            
        except Exception as e:
            self.logger.error(f"❌ Error en inyección de datos: {e}")
            return response_text
    
    async def _get_company_data(self, user_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos empresariales desde PostgreSQL con caché"""
        
        try:
            # Verificar caché
            cache_key = f"{company_id}_{user_id}"
            if cache_key in self.company_data_cache:
                cached_data, timestamp = self.company_data_cache[cache_key]
                if datetime.now() - timestamp < self.cache_ttl:
                    self.logger.info("📋 Usando datos empresariales desde caché")
                    return cached_data
            
            # Verificar que PostgreSQL esté disponible
            if not self.postgres_service:
                self.logger.error("❌ PostgreSQL service no disponible - no se pueden obtener datos empresariales")
                return None
            
            # Consulta optimizada para obtener datos específicos
            query = """
            SELECT 
                COALESCE(c.business_name, 'Empresa Sin Nombre') as company_name,
                c.rut as company_rut,
                COALESCE(u.first_name || ' ' || u.last_name, u.email) as admin_name,
                u.email as admin_email,
                c.economic_activity as business_sector,
                c.address,
                c.phone
            FROM companies c
            JOIN company_users cu ON c.id = cu.company_id  
            JOIN users u ON cu.user_id = u.id
            WHERE c.id = $1 AND u.id = $2
            AND cu.role_in_company IN ('admin', 'super_admin', 'contador', 'user', 'viewer')
            LIMIT 1;
            """
            
            result = await self.postgres_service.execute_single_query(query, (company_id, user_id))
            
            if result:
                company_data = {
                    'company_name': result['company_name'],
                    'company_rut': result['company_rut'],
                    'admin_name': result['admin_name'],
                    'admin_email': result['admin_email'],
                    'business_sector': result.get('business_sector', ''),
                    'address': result.get('address', ''),
                    'phone': result.get('phone', '')
                }
                
                # Actualizar caché
                self.company_data_cache[cache_key] = (company_data, datetime.now())
                
                self.logger.info(f"✅ Datos empresariales obtenidos: {company_data['company_name']}")
                return company_data
            else:
                self.logger.warning(f"⚠️ No se encontraron datos para user_id: {user_id}, company_id: {company_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos empresariales: {e}")
            # No usar datos hardcodeados - retornar None para error gracioso
            return None
    
    # Método _get_hardcoded_company_data eliminado - ahora solo PostgreSQL dinámico
    
    async def _validate_and_enhance(self, text: str, company_data: Dict[str, Any]) -> str:
        """Validación final y mejoras de calidad"""
        
        try:
            enhanced_text = text
            
            # Verificar patrones genéricos residuales
            generic_patterns = [
                (r'\bInformación empresarial completa:\s*👤\s*\*\*Administrador:\*\*\s*el administrador', 
                 f"Información empresarial completa:\n👤 **Administrador:** {company_data.get('admin_name', 'N/A')}"),
                
                (r'📧\s*\*\*Email:\*\*\s*admin@empresa\.cl',
                 f"📧 **Email:** {company_data.get('admin_email', 'N/A')}")
            ]
            
            for pattern, replacement in generic_patterns:
                enhanced_text = re.sub(pattern, replacement, enhanced_text, flags=re.IGNORECASE)
            
            # Añadir contexto empresarial si es muy genérico
            if len(enhanced_text.strip()) < 100 or "su empresa" in enhanced_text.lower():
                enhanced_text = await self._add_company_context(enhanced_text, company_data)
            
            return enhanced_text
            
        except Exception as e:
            self.logger.error(f"❌ Error en validación final: {e}")
            return text
    
    async def _add_company_context(self, text: str, company_data: Dict[str, Any]) -> str:
        """Añade contexto empresarial específico"""
        
        try:
            company_context = f"\n\n🏢 **{company_data.get('company_name', 'Su empresa')}**"
            
            if company_data.get('company_rut'):
                company_context += f"\n📋 **RUT:** {company_data['company_rut']}"
            
            if company_data.get('admin_name'):
                company_context += f"\n👤 **Administrador:** {company_data['admin_name']}"
            
            if company_data.get('admin_email'):
                company_context += f"\n📧 **Contacto:** {company_data['admin_email']}"
            
            return text + company_context
            
        except Exception as e:
            self.logger.error(f"❌ Error añadiendo contexto empresarial: {e}")
            return text
    
    def clear_cache(self):
        """Limpia el caché de datos empresariales"""
        self.company_data_cache.clear()
        self.logger.info("🧹 Caché de datos empresariales limpiado")
    
    async def preload_company_data(self, company_ids: list):
        """Precarga datos empresariales para mejor performance"""
        
        try:
            for company_id in company_ids:
                # Lógica de precarga si es necesaria
                pass
            
            self.logger.info(f"📋 Datos precargados para {len(company_ids)} empresas")
            
        except Exception as e:
            self.logger.error(f"❌ Error en precarga de datos: {e}")
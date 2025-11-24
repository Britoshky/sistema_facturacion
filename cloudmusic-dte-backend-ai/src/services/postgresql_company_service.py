"""
PostgreSQL Company Service - Gestión especializada de empresas
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from .postgresql_connection_manager import PostgreSQLConnectionManager


class PostgreSQLCompanyService:
    """Servicio especializado para consultas de empresas"""
    
    def __init__(self, connection_manager: PostgreSQLConnectionManager):
        self.connection = connection_manager
    
    async def get_company_info(self, company_id: str) -> Optional[Dict]:
        """Obtener información completa de una empresa"""
        try:
            query = """
            SELECT 
                id, business_name, rut, address, phone, email,
                created_at, is_active,
                COALESCE(business_name, 'Empresa Sin Nombre') as display_name
            FROM companies 
            WHERE id = $1 AND is_active = true
            """
            
            result = await self.connection.execute_single_query(query, (company_id,))
            
            if result:
                logger.info(f"📊 Empresa encontrada: {result.get('display_name', 'N/A')}")
                return result
            else:
                logger.warning(f"⚠️ Empresa {company_id} no encontrada")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo empresa {company_id}: {e}")
            return None
    
    async def get_company_summary_data(self, company_id: str) -> Dict:
        """Obtener resumen de datos empresariales para contexto IA"""
        try:
            # Información básica de la empresa
            company_info = await self.get_company_info(company_id)
            if not company_info:
                return {"error": "Empresa no encontrada"}
            
            # Estadísticas agregadas
            stats_query = """
            SELECT 
                (SELECT COUNT(*) FROM users WHERE company_id = $1) as total_users,
                (SELECT COUNT(*) FROM clients WHERE company_id = $1) as total_clients,
                (SELECT COUNT(*) FROM products WHERE company_id = $1) as total_products,
                (SELECT COUNT(*) FROM documents WHERE company_id = $1) as total_documents
            """
            
            stats = await self.connection.execute_single_query(stats_query, (company_id,))
            
            return {
                "company_info": company_info,
                "stats": stats or {},
                "has_real_data": True,
                "context_type": "enterprise"
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen empresa {company_id}: {e}")
            return {"error": str(e), "has_real_data": False}
    
    async def get_company_admin(self, company_id: str) -> Optional[Dict]:
        """Obtener información del administrador de la empresa"""
        try:
            query = """
            SELECT 
                u.id, u.email, u.first_name, u.last_name, u.role,
                CONCAT(u.first_name, ' ', u.last_name) as full_name,
                u.created_at, u.is_active
            FROM users u
            WHERE u.company_id = $1 
            AND u.role IN ('admin', 'owner', 'administrator')
            AND u.is_active = true
            ORDER BY 
                CASE u.role
                    WHEN 'owner' THEN 1
                    WHEN 'admin' THEN 2  
                    WHEN 'administrator' THEN 3
                    ELSE 4
                END
            LIMIT 1
            """
            
            result = await self.connection.execute_single_query(query, (company_id,))
            
            if result:
                logger.debug(f"👤 Admin encontrado: {result.get('full_name', 'N/A')}")
                return result
            else:
                logger.warning(f"⚠️ No se encontró admin para empresa {company_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo admin empresa {company_id}: {e}")
            return None
    
    async def list_active_companies(self, limit: int = 10) -> List[Dict]:
        """Listar empresas activas"""
        try:
            query = """
            SELECT 
                id, business_name, rut,
                COALESCE(business_name, 'Empresa Sin Nombre') as display_name,
                created_at, is_active
            FROM companies 
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT $1
            """
            
            results = await self.connection.execute_query(query, (limit,))
            
            logger.info(f"📊 {len(results)} empresas activas encontradas")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error listando empresas: {e}")
            return []
    
    async def search_companies(self, search_term: str, limit: int = 5) -> List[Dict]:
        """Buscar empresas por nombre o RUT"""
        try:
            query = """
            SELECT 
                id, business_name, rut,
                COALESCE(business_name, 'Empresa Sin Nombre') as display_name
            FROM companies 
            WHERE is_active = true
            AND (
                LOWER(business_name) LIKE LOWER($1) OR
                LOWER(rut) LIKE LOWER($1)
            )
            ORDER BY business_name
            LIMIT $2
            """
            
            search_pattern = f"%{search_term}%"
            results = await self.connection.execute_query(query, (search_pattern, limit))
            
            logger.info(f"🔍 {len(results)} empresas encontradas con '{search_term}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error buscando empresas: {e}")
            return []
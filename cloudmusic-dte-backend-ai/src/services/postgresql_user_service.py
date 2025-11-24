"""
PostgreSQL User Service - Gestión especializada de usuarios
"""

from typing import Dict, List, Optional
from loguru import logger
from .postgresql_connection_manager import PostgreSQLConnectionManager


class PostgreSQLUserService:
    """Servicio especializado para consultas de usuarios"""
    
    def __init__(self, connection_manager: PostgreSQLConnectionManager):
        self.connection = connection_manager
    
    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Obtener información completa de un usuario"""
        try:
            query = """
            SELECT 
                u.id, u.email, u.first_name, u.last_name, u.role,
                u.company_id, u.created_at, u.is_active,
                CONCAT(u.first_name, ' ', u.last_name) as full_name,
                c.business_name, c.business_name,
                CASE 
                    WHEN c.business_name IS NOT NULL THEN c.business_name
                    WHEN c.business_name IS NOT NULL THEN c.business_name
                    ELSE 'Empresa Sin Nombre'
                END as company_display_name
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE u.id = $1 AND u.is_active = true
            """
            
            result = await self.connection.execute_single_query(query, (user_id,))
            
            if result:
                logger.info(f"👤 Usuario encontrado: {result.get('full_name', 'N/A')}")
                return result
            else:
                logger.warning(f"⚠️ Usuario {user_id} no encontrado")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuario {user_id}: {e}")
            return None
    
    async def get_user_context(self, user_id: str) -> Dict:
        """Obtener contexto completo del usuario para IA"""
        try:
            user_info = await self.get_user_info(user_id)
            
            if not user_info:
                return {
                    "user_found": False,
                    "error": "Usuario no encontrado",
                    "has_real_data": False
                }
            
            # Información adicional del contexto
            company_id = user_info.get('company_id')
            context = {
                "user_found": True,
                "user_id": user_info['id'],
                "user_name": user_info['full_name'],
                "user_email": user_info['email'],
                "user_role": user_info['role'],
                "company_id": company_id,
                "company_name": user_info['company_display_name'],
                "is_admin": user_info['role'] in ['admin', 'owner', 'administrator'],
                "has_real_data": True,
                "context_type": "authenticated_user"
            }
            
            logger.info(f"📋 Contexto generado para {user_info['full_name']}")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto usuario {user_id}: {e}")
            return {
                "user_found": False, 
                "error": str(e),
                "has_real_data": False
            }
    
    async def list_company_users(self, company_id: str, limit: int = 20) -> List[Dict]:
        """Listar usuarios de una empresa"""
        try:
            query = """
            SELECT 
                id, email, first_name, last_name, role,
                CONCAT(first_name, ' ', last_name) as full_name,
                created_at, is_active
            FROM users 
            WHERE company_id = $1 AND is_active = true
            ORDER BY role, last_name, first_name
            LIMIT $2
            """
            
            results = await self.connection.execute_query(query, (company_id, limit))
            
            logger.info(f"👥 {len(results)} usuarios encontrados para empresa {company_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error listando usuarios: {e}")
            return []
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Buscar usuario por email"""
        try:
            query = """
            SELECT 
                u.id, u.email, u.first_name, u.last_name, u.role,
                u.company_id, u.created_at, u.is_active,
                CONCAT(u.first_name, ' ', u.last_name) as full_name,
                c.business_name, c.business_name,
                CASE 
                    WHEN c.business_name IS NOT NULL THEN c.business_name
                    WHEN c.business_name IS NOT NULL THEN c.business_name
                    ELSE 'Empresa Sin Nombre'
                END as company_display_name
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE LOWER(u.email) = LOWER($1) AND u.is_active = true
            """
            
            result = await self.connection.execute_single_query(query, (email,))
            
            if result:
                logger.info(f"📧 Usuario encontrado por email: {result['full_name']}")
                return result
            else:
                logger.warning(f"⚠️ No se encontró usuario con email {email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error buscando usuario por email: {e}")
            return None
    
    async def get_users_stats(self, company_id: str = None) -> Dict:
        """Obtener estadísticas de usuarios"""
        try:
            if company_id:
                query = """
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN role IN ('admin', 'owner', 'administrator') THEN 1 END) as admin_users,
                    COUNT(CASE WHEN role = 'user' THEN 1 END) as regular_users,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users
                FROM users 
                WHERE company_id = $1
                """
                result = await self.connection.execute_single_query(query, (company_id,))
            else:
                query = """
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN role IN ('admin', 'owner', 'administrator') THEN 1 END) as admin_users,
                    COUNT(CASE WHEN role = 'user' THEN 1 END) as regular_users,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users
                FROM users
                """
                result = await self.connection.execute_single_query(query)
            
            stats = dict(result) if result else {
                "total_users": 0,
                "admin_users": 0,
                "regular_users": 0,
                "active_users": 0
            }
            
            logger.info(f"📊 Stats usuarios: {stats['total_users']} total, {stats['active_users']} activos")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo stats usuarios: {e}")
            return {"error": str(e)}

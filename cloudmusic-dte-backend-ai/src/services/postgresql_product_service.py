"""
PostgreSQL Product Service - Gestión especializada de productos
"""

from typing import Dict, List, Optional
from loguru import logger
from .postgresql_connection_manager import PostgreSQLConnectionManager


class PostgreSQLProductService:
    """Servicio especializado para consultas de productos"""
    
    def __init__(self, connection_manager: PostgreSQLConnectionManager):
        self.connection = connection_manager
    
    async def get_products_by_company(self, company_id: str, limit: int = 20) -> List[Dict]:
        """Obtener productos de una empresa específica"""
        try:
            query = """
            SELECT 
                id, name, description, unit_price as precio, 
                product_type, sku, created_at,
                CASE 
                    WHEN unit_price IS NOT NULL THEN ROUND(unit_price::numeric, 0)
                    ELSE 0
                END as price_formatted
            FROM products 
            WHERE company_id = $1
            ORDER BY name
            LIMIT $2
            """
            
            results = await self.connection.execute_query(query, (company_id, limit))
            
            if results:
                logger.info(f"📦 {len(results)} productos encontrados para empresa {company_id}")
                return results
            else:
                logger.warning(f"⚠️ No hay productos para empresa {company_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos: {e}")
            return []
    
    async def get_product_names(self, company_id: str) -> List[str]:
        """Obtener solo nombres de productos para respuestas rápidas"""
        try:
            query = """
            SELECT DISTINCT name 
            FROM products 
            WHERE company_id = $1 AND is_active = true
            ORDER BY name
            """
            
            results = await self.connection.execute_query(query, (company_id,))
            product_names = [row['name'] for row in results if row.get('name')]
            
            logger.info(f"📝 {len(product_names)} nombres de productos extraídos")
            return product_names
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo nombres productos: {e}")
            return []
    
    async def get_most_expensive_product(self, company_id: str) -> Optional[Dict]:
        """Obtener el producto más caro de la empresa"""
        try:
            query = """
            SELECT 
                name, description, unit_price as precio,
                ROUND(unit_price::numeric, 0) as price_formatted
            FROM products 
            WHERE company_id = $1 AND unit_price IS NOT NULL
            ORDER BY unit_price DESC
            LIMIT 1
            """
            
            result = await self.connection.execute_single_query(query, (company_id,))
            
            if result:
                logger.info(f"💰 Producto más caro: {result['name']} - ${result['price_formatted']}")
                return result
            else:
                logger.warning(f"⚠️ No hay productos con precio para empresa {company_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo producto más caro: {e}")
            return None
    
    async def search_products(self, company_id: str, search_term: str, limit: int = 10) -> List[Dict]:
        """Buscar productos por nombre o descripción"""
        try:
            query = """
            SELECT 
                id, name, description, unit_price as precio, product_type,
                CASE 
                    WHEN unit_price IS NOT NULL THEN ROUND(unit_price::numeric, 0)
                    ELSE 0
                END as price_formatted
            FROM products 
            WHERE company_id = $1
            AND (
                LOWER(name) LIKE LOWER($2) OR
                LOWER(description) LIKE LOWER($2) OR
                LOWER(product_type) LIKE LOWER($2)
            )
            ORDER BY name
            LIMIT $3
            """
            
            search_pattern = f"%{search_term}%"
            results = await self.connection.execute_query(query, (company_id, search_pattern, limit))
            
            logger.info(f"🔍 {len(results)} productos encontrados con '{search_term}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error buscando productos: {e}")
            return []
    
    async def get_product_categories(self, company_id: str) -> List[str]:
        """Obtener categorías de productos disponibles"""
        try:
            query = """
            SELECT DISTINCT product_type as category 
            FROM products 
            WHERE company_id = $1 AND product_type IS NOT NULL
            ORDER BY product_type
            """
            
            results = await self.connection.execute_query(query, (company_id,))
            categories = [row['category'] for row in results if row.get('category')]
            
            logger.info(f"🏷️ {len(categories)} tipos de productos encontrados")
            return categories
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo categorías: {e}")
            return []
    
    async def get_products_summary(self, company_id: str) -> Dict:
        """Obtener resumen estadístico de productos"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_products,
                COUNT(DISTINCT product_type) as total_categories,
                AVG(unit_price) as avg_price,
                MAX(unit_price) as max_price,
                MIN(unit_price) as min_price,
                0 as total_stock
            FROM products 
            WHERE company_id = $1
            """
            
            result = await self.connection.execute_single_query(query, (company_id,))
            
            if result:
                # Formatear precios
                summary = dict(result)
                if summary.get('avg_price'):
                    summary['avg_price'] = round(float(summary['avg_price']), 0)
                if summary.get('max_price'):
                    summary['max_price'] = round(float(summary['max_price']), 0)
                if summary.get('min_price'):
                    summary['min_price'] = round(float(summary['min_price']), 0)
                
                logger.info(f"📊 Resumen productos: {summary['total_products']} productos total")
                return summary
            else:
                return {
                    "total_products": 0,
                    "total_categories": 0,
                    "avg_price": 0,
                    "max_price": 0,
                    "min_price": 0,
                    "total_stock": 0
                }
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen productos: {e}")
            return {"error": str(e)}
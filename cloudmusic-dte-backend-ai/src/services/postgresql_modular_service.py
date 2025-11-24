"""
PostgreSQL Modular Service - Coordinador de servicios especializados
Reemplaza el archivo postgresql_service.py monolítico con arquitectura modular
"""

from typing import Dict, List, Optional, Any
from loguru import logger

from .postgresql_connection_manager import PostgreSQLConnectionManager
from .postgresql_company_service import PostgreSQLCompanyService
from .postgresql_product_service import PostgreSQLProductService  
from .postgresql_user_service import PostgreSQLUserService


class PostgreSQLModularService:
    """Servicio PostgreSQL modular y escalable"""
    
    def __init__(self, connection_string: str):
        # Componente central de conexión
        self.connection_manager = PostgreSQLConnectionManager(connection_string)
        
        # Servicios especializados
        self.companies = PostgreSQLCompanyService(self.connection_manager)
        self.products = PostgreSQLProductService(self.connection_manager)
        self.users = PostgreSQLUserService(self.connection_manager)
    
    # === MÉTODOS DE CONEXIÓN ===
    
    async def connect(self):
        """Conectar a PostgreSQL"""
        await self.connection_manager.connect()
    
    async def test_connection(self):
        """Probar conexión"""
        await self.connection_manager.test_connection()
    
    async def close(self):
        """Cerrar conexiones"""
        await self.connection_manager.close()
    
    async def disconnect(self):
        """Desconectar de PostgreSQL - alias para compatibilidad"""
        await self.close()
    
    def is_connected(self) -> bool:
        """Verificar conexión"""
        return self.connection_manager.is_connected()
    
    # === MÉTODOS DE COMPATIBILIDAD ===
    # Para mantener compatibilidad con código existente
    
    async def get_company_info(self, company_id: str) -> Optional[Dict]:
        """Método de compatibilidad - obtener info empresa"""
        return await self.companies.get_company_info(company_id)
    
    async def get_user_documents_count(self, user_id: str) -> int:
        """Obtener conteo de documentos del usuario"""
        try:
            query = """
            SELECT COUNT(*) as count 
            FROM documents d
            WHERE d.company_id IN (
                SELECT cu.company_id FROM company_users cu WHERE cu.user_id = $1
            )
            """
            result = await self.connection_manager.execute_single_query(query, (user_id,))
            return result.get('count', 0) if result else 0
        except Exception as e:
            logger.warning(f"Error contando documentos usuario {user_id}: {e}")
            return 0
    
    async def get_user_clients(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Obtener clientes del usuario"""
        try:
            query = """
            SELECT c.id, c.rut, 
                   COALESCE(c.business_name, c.first_name || ' ' || c.last_name) as nombre, 
                   c.email, c.address as direccion
            FROM clients c
            INNER JOIN company_users cu ON c.company_id = cu.company_id
            WHERE cu.user_id = $1
            ORDER BY COALESCE(c.business_name, c.first_name || ' ' || c.last_name)
            LIMIT $2
            """
            results = await self.connection_manager.execute_query(query, (user_id, limit))
            return results if results else []
        except Exception as e:
            logger.warning(f"Error obteniendo clientes usuario {user_id}: {e}")
            return []
    
    async def get_user_products(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Obtener productos del usuario"""
        try:
            query = """
            SELECT p.id, p.sku as codigo, p.name as nombre, 
                   p.unit_price as precio, p.unit_of_measure as unidad_medida
            FROM products p
            INNER JOIN company_users cu ON p.company_id = cu.company_id
            WHERE cu.user_id = $1
            ORDER BY p.name
            LIMIT $2
            """
            results = await self.connection_manager.execute_query(query, (user_id, limit))
            return results if results else []
        except Exception as e:
            logger.warning(f"Error obteniendo productos usuario {user_id}: {e}")
            return []
    
    async def get_most_expensive_product(self, user_id: str) -> Dict:
        """Obtener el producto más caro del usuario"""
        try:
            query = """
            SELECT p.id, p.sku as codigo, p.name as nombre, 
                   p.unit_price as precio, p.unit_of_measure as unidad_medida,
                   p.description as descripcion
            FROM products p
            INNER JOIN company_users cu ON p.company_id = cu.company_id
            WHERE cu.user_id = $1
            ORDER BY p.unit_price DESC
            LIMIT 1
            """
            results = await self.connection_manager.execute_query(query, (user_id,))
            return results[0] if results else {}
        except Exception as e:
            logger.warning(f"Error obteniendo producto más caro usuario {user_id}: {e}")
            return {}
    
    async def get_recent_documents(self, company_id: str, limit: int = 5) -> List[Dict]:
        """Obtener documentos recientes de la empresa"""
        try:
            query = """
            SELECT d.id, d.document_type, d.folio_number, 
                   d.issue_date, d.total_amount, d.sii_status
            FROM documents d
            WHERE d.company_id = $1
            ORDER BY d.issue_date DESC
            LIMIT $2
            """
            results = await self.connection_manager.execute_query(query, (company_id, limit))
            return results if results else []
        except Exception as e:
            logger.warning(f"Error obteniendo documentos recientes empresa {company_id}: {e}")
            return []
    
    async def get_user_business_summary(self, user_id: str) -> Dict[str, Any]:
        """Obtener resumen empresarial del usuario"""
        try:
            query = """
            SELECT 
                COUNT(DISTINCT d.id) as total_documents,
                COUNT(DISTINCT c.id) as total_clients,
                COUNT(DISTINCT p.id) as total_products,
                COALESCE(SUM(d.total_amount), 0) as total_revenue,
                MAX(d.issue_date) as last_document_date,
                MIN(d.issue_date) as first_document_date
            FROM company_users cu
            LEFT JOIN documents d ON d.company_id = cu.company_id
            LEFT JOIN clients c ON c.company_id = cu.company_id
            LEFT JOIN products p ON p.company_id = cu.company_id
            WHERE cu.user_id = $1
            """
            result = await self.connection_manager.execute_single_query(query, (user_id,))
            return result if result else {}
        except Exception as e:
            logger.warning(f"Error obteniendo resumen empresarial usuario {user_id}: {e}")
            return {}

    async def get_comprehensive_company_data(self, company_id: str) -> Dict[str, Any]:
        """Obtener datos completos y contextuales de la empresa"""
        try:
            # Información básica de la empresa
            company_info = await self.companies.get_company_info(company_id)
            
            # Productos con estadísticas
            products_query = """
            SELECT p.id, p.name, p.unit_price as precio, p.description,
                   p.sku, p.unit_of_measure,
                   RANK() OVER (ORDER BY p.unit_price DESC) as price_rank
            FROM products p 
            WHERE p.company_id = $1 
            ORDER BY p.unit_price DESC
            """
            products = await self.connection_manager.execute_query(products_query, (company_id,))
            
            # Clientes con métricas
            clients_query = """
            SELECT c.id, c.rut, c.business_name, c.email,
                   COUNT(d.id) as documents_count,
                   COALESCE(SUM(d.total_amount), 0) as total_billed
            FROM clients c
            LEFT JOIN documents d ON d.client_id = c.id AND d.company_id = c.company_id
            WHERE c.company_id = $1
            GROUP BY c.id, c.rut, c.business_name, c.email
            ORDER BY total_billed DESC
            """
            clients = await self.connection_manager.execute_query(clients_query, (company_id,))
            
            # Documentos con análisis temporal
            documents_query = """
            SELECT d.id, d.document_type, d.folio_number, d.issue_date,
                   d.total_amount, d.sii_status, c.rut as client_rut,
                   DATE_PART('month', d.issue_date) as month,
                   DATE_PART('year', d.issue_date) as year
            FROM documents d 
            LEFT JOIN clients c ON d.client_id = c.id
            WHERE d.company_id = $1 
            ORDER BY d.issue_date DESC
            """
            documents = await self.connection_manager.execute_query(documents_query, (company_id,))
            
            # Estadísticas avanzadas
            stats_query = """
            SELECT 
                COUNT(DISTINCT d.id) as total_documents,
                COUNT(DISTINCT CASE WHEN d.document_type = 33 THEN d.id END) as facturas_count,
                COUNT(DISTINCT CASE WHEN d.document_type = 39 THEN d.id END) as boletas_count,
                COALESCE(AVG(d.total_amount), 0) as avg_document_amount,
                COALESCE(MAX(d.total_amount), 0) as max_document_amount,
                COALESCE(MIN(d.total_amount), 0) as min_document_amount,
                COUNT(DISTINCT d.client_id) as unique_clients
            FROM documents d 
            WHERE d.company_id = $1
            """
            stats = await self.connection_manager.execute_single_query(stats_query, (company_id,))
            
            # Tendencias mensuales
            monthly_query = """
            SELECT 
                DATE_PART('year', d.issue_date) as year,
                DATE_PART('month', d.issue_date) as month,
                COUNT(d.id) as documents_count,
                COALESCE(SUM(d.total_amount), 0) as monthly_revenue
            FROM documents d 
            WHERE d.company_id = $1 
                AND d.issue_date >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY DATE_PART('year', d.issue_date), DATE_PART('month', d.issue_date)
            ORDER BY year DESC, month DESC
            """
            monthly_trends = await self.connection_manager.execute_query(monthly_query, (company_id,))
            
            return {
                'company_info': company_info or {},
                'products': products or [],
                'clients': clients or [],
                'documents': documents or [],
                'statistics': stats or {},
                'monthly_trends': monthly_trends or []
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos completos empresa {company_id}: {e}")
            return {
                'company_info': {},
                'products': [],
                'clients': [],
                'documents': [],
                'statistics': {},
                'monthly_trends': []
            }

    async def get_folio_caf_analysis(self, company_id: str) -> Dict[str, Any]:
        """Obtener análisis de folios CAF (simulado con datos reales)"""
        try:
            # Obtener estadísticas de documentos por tipo
            folio_query = """
            SELECT 
                d.document_type,
                COUNT(d.id) as used_folios,
                MAX(d.folio_number) as last_folio_used,
                MIN(d.folio_number) as first_folio_used
            FROM documents d 
            WHERE d.company_id = $1 
            GROUP BY d.document_type
            ORDER BY d.document_type
            """
            folio_stats = await self.connection_manager.execute_query(folio_query, (company_id,))
            
            # Simular información CAF basada en datos reales
            caf_info = {}
            for stat in folio_stats:
                doc_type = stat['document_type']
                used_folios = stat['used_folios']
                last_folio = stat['last_folio_used'] or 1000
                
                # Simular rangos CAF basados en uso real
                if doc_type == 33:  # Facturas
                    caf_info['facturas'] = {
                        'range_start': max(1001, last_folio - 500),
                        'range_end': last_folio + 500,
                        'used': used_folios,
                        'available': 500 - (used_folios % 500),
                        'next_folio': last_folio + 1
                    }
                elif doc_type == 39:  # Boletas
                    caf_info['boletas'] = {
                        'range_start': max(2001, last_folio - 1000),
                        'range_end': last_folio + 1000,
                        'used': used_folios,
                        'available': 1000 - (used_folios % 1000),
                        'next_folio': last_folio + 1
                    }
            
            return {
                'folio_statistics': folio_stats,
                'caf_simulation': caf_info,
                'last_update': 'Basado en documentos reales'
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo análisis folios CAF empresa {company_id}: {e}")
            return {'folio_statistics': [], 'caf_simulation': {}, 'last_update': 'Error'}

    async def search_clients_advanced(self, company_id: str, search_term: str) -> List[Dict]:
        """Búsqueda avanzada de clientes"""
        try:
            # Búsqueda por coincidencias múltiples
            search_query = """
            SELECT c.id, c.rut, c.business_name, c.first_name, c.last_name,
                   c.email, c.address, c.phone,
                   COUNT(d.id) as documents_count,
                   COALESCE(SUM(d.total_amount), 0) as total_billed,
                   MAX(d.issue_date) as last_document_date,
                   CASE 
                       WHEN c.business_name ILIKE $2 THEN 1
                       WHEN c.rut ILIKE $2 THEN 2  
                       WHEN CONCAT(c.first_name, ' ', c.last_name) ILIKE $2 THEN 3
                       WHEN c.email ILIKE $2 THEN 4
                       ELSE 5
                   END as relevance_score
            FROM clients c
            LEFT JOIN documents d ON d.client_id = c.id AND d.company_id = c.company_id
            WHERE c.company_id = $1 
                AND (
                    c.business_name ILIKE $2 OR
                    c.rut ILIKE $2 OR
                    CONCAT(c.first_name, ' ', c.last_name) ILIKE $2 OR
                    c.email ILIKE $2
                )
            GROUP BY c.id, c.rut, c.business_name, c.first_name, c.last_name, 
                     c.email, c.address, c.phone
            ORDER BY relevance_score, total_billed DESC
            LIMIT 10
            """
            search_pattern = f"%{search_term}%"
            results = await self.connection_manager.execute_query(
                search_query, (company_id, search_pattern)
            )
            return results if results else []
            
        except Exception as e:
            logger.error(f"Error búsqueda avanzada clientes: {e}")
            return []
    
    async def get_products_by_company(self, company_id: str, limit: int = 20) -> List[Dict]:
        """Método de compatibilidad - obtener productos"""
        return await self.products.get_products_by_company(company_id, limit)
    
    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Método de compatibilidad - obtener info usuario"""
        return await self.users.get_user_info(user_id)
    
    async def get_user_context(self, user_id: str) -> Dict:
        """Método de compatibilidad - obtener contexto usuario"""
        return await self.users.get_user_context(user_id)
    
    async def get_company_summary_data(self, company_id: str) -> Dict:
        """Método de compatibilidad - resumen empresa"""
        return await self.companies.get_company_summary_data(company_id)
    
    async def get_documents_by_company(self, company_id: str, limit: int = 50) -> List[Dict]:
        """Obtener documentos DTE de una empresa específica"""
        try:
            query = """
            SELECT 
                id, document_type, folio_number, issue_date, 
                net_amount, tax_amount, total_amount, sii_status,
                created_at
            FROM documents 
            WHERE company_id = $1
            ORDER BY issue_date DESC
            LIMIT $2
            """
            
            results = await self.connection_manager.execute_query(query, (company_id, limit))
            
            if results:
                logger.info(f"📄 {len(results)} documentos encontrados para empresa {company_id}")
                return results
            else:
                logger.warning(f"⚠️ No hay documentos para empresa {company_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos: {e}")
            return []
    
    async def get_clients_by_company(self, company_id: str, limit: int = 50) -> List[Dict]:
        """Obtener clientes de una empresa específica"""
        try:
            query = """
            SELECT 
                id, rut, client_type, business_name, 
                first_name, last_name, email, phone,
                credit_limit, payment_terms
            FROM clients 
            WHERE company_id = $1
            ORDER BY business_name, last_name
            LIMIT $2
            """
            
            results = await self.connection_manager.execute_query(query, (company_id, limit))
            
            if results:
                logger.info(f"👥 {len(results)} clientes encontrados para empresa {company_id}")
                return results
            else:
                logger.warning(f"⚠️ No hay clientes para empresa {company_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo clientes: {e}")
            return []
    
    # === MÉTODOS DE CONSULTA DIRECTA ===
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Ejecutar consulta SQL personalizada"""
        return await self.connection_manager.execute_query(query, params)
    
    async def execute_single_query(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Ejecutar consulta de un solo resultado"""
        return await self.connection_manager.execute_single_query(query, params)
    
    # === MÉTODOS DE BUSINESS LOGIC ===
    
    async def process_business_query(self, query_text: str, user_id: str, company_id: str) -> str:
        """Procesar consulta empresarial específica"""
        try:
            query_lower = query_text.lower()
            
            # Consultas de productos
            if any(keyword in query_lower for keyword in ['producto', 'productos', 'inventario', 'stock']):
                products = await self.products.get_products_by_company(company_id, 10)
                
                if not products:
                    return "No hay productos registrados en el sistema."
                
                product_names = [p['name'] for p in products if p.get('name')]
                
                if len(product_names) <= 3:
                    return f"Los productos disponibles son: {', '.join(product_names)}."
                else:
                    return f"Tenemos {len(product_names)} productos disponibles, incluyendo: {', '.join(product_names[:3])}, entre otros."
            
            # Consultas de empresa
            elif any(keyword in query_lower for keyword in ['empresa', 'compañía', 'información', 'datos']):
                company_info = await self.companies.get_company_info(company_id)
                
                if not company_info:
                    return "No se encontró información de la empresa."
                
                company_name = company_info.get('display_name', 'la empresa')
                return f"La información de {company_name} está disponible en el sistema. RUT: {company_info.get('rut', 'N/A')}"
            
            # Consultas de usuarios
            elif any(keyword in query_lower for keyword in ['usuario', 'usuarios', 'equipo', 'personal']):
                users = await self.users.list_company_users(company_id, 10)
                
                if not users:
                    return "No hay usuarios registrados en la empresa."
                
                user_count = len(users)
                return f"La empresa tiene {user_count} usuarios registrados en el sistema."
            
            # Consulta general
            else:
                # Obtener resumen general
                company_summary = await self.companies.get_company_summary_data(company_id)
                
                if company_summary.get('error'):
                    return "No se pudo obtener información de la empresa."
                
                stats = company_summary.get('stats', {})
                company_info = company_summary.get('company_info', {})
                
                company_name = company_info.get('display_name', 'Su empresa')
                
                return f"""{company_name} tiene:
• {stats.get('total_products', 0)} productos registrados
• {stats.get('total_users', 0)} usuarios
• {stats.get('total_clients', 0)} clientes
• {stats.get('total_documents', 0)} documentos"""
            
        except Exception as e:
            logger.error(f"❌ Error procesando consulta empresarial: {e}")
            return f"Error procesando la consulta: {str(e)}"


# === FUNCIONES UTILITARIAS ===

def format_currency(amount: Any) -> str:
    """Formatear moneda chilena"""
    try:
        if amount is None:
            return "$0"
        
        # Convertir a número si es string
        if isinstance(amount, str):
            amount = float(amount.replace(',', '').replace('$', ''))
        
        # Formatear con separadores de miles
        return f"${amount:,.0f}".replace(',', '.')
        
    except (ValueError, TypeError):
        return "$0"


def document_type_name(doc_type: int) -> str:
    """Obtener nombre del tipo de documento DTE"""
    types = {
        33: "Factura Electrónica",
        34: "Factura Exenta Electrónica", 
        39: "Boleta Electrónica",
        41: "Boleta Exenta Electrónica",
        52: "Guía de Despacho Electrónica",
        56: "Nota de Débito Electrónica",
        61: "Nota de Crédito Electrónica"
    }
    return types.get(doc_type, f"Documento Tipo {doc_type}")
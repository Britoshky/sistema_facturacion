"""
Servicio para manejo del contexto empresarial dinámico
Responsable de obtener y formatear información específica de cada empresa
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from .postgresql_service import PostgreSQLService

logger = logging.getLogger(__name__)

class BusinessContextService:
    """Servicio para gestionar contexto empresarial dinámico"""
    
    def __init__(self):
        self.cache = {}
        # Inicializar servicio PostgreSQL con variables de entorno
        postgres_url = os.getenv('POSTGRESQL_URL')
        if not postgres_url:
            # Construir URL desde variables individuales si no existe
            host = os.getenv('POSTGRESQL_HOST', 'localhost')
            port = os.getenv('POSTGRESQL_PORT', '5432')
            database = os.getenv('POSTGRESQL_DATABASE', 'sistema_facturacion_dte')
            user = os.getenv('POSTGRESQL_USER', 'postgres')
            password = os.getenv('POSTGRESQL_PASSWORD', '')
            postgres_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        self.postgres_service = PostgreSQLService(postgres_url)
        self._initialized = False
        
    async def get_company_summary_data(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Obtener resumen completo de datos empresariales para contexto dinámico"""
        cache_key = f"{user_id}_{company_id}"
        
        # Verificar cache
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Inicializar conexión PostgreSQL si no está inicializada
            if not self._initialized:
                await self.postgres_service.connect()
                self._initialized = True
            
            # Obtener datos reales de la empresa usando PostgreSQLService
            try:
                # Usar company_id directamente como string (UUID)
                # No hacer conversiones hardcodeadas
                pass
            except (ValueError, TypeError):
                return {'error': 'Company ID inválido'}
            
            company_data = await self.postgres_service.get_company_data(company_id)
            
            if company_data:
                # Obtener productos de la empresa
                products = await self.postgres_service.get_company_products(company_id)
                
                # Obtener clientes de la empresa
                clients_count = await self.postgres_service.get_company_clients_count(company_id)
                
                # Obtener administrador
                admin_data = await self.postgres_service.get_company_admin(company_id)
                
                # Procesar datos
                total_products = len(products) if products else 0
                total_value = sum(float(p.get('price', 0)) for p in products) if products else 0
                
                if products:
                    # Ordenar productos por precio descendente
                    sorted_products = sorted(products, key=lambda x: float(x.get('price', 0)), reverse=True)
                    top_product_data = sorted_products[0]
                    top_product = f"{top_product_data['name']} - ${float(top_product_data['price']):,.0f}"
                else:
                    top_product = "Sin productos registrados"
                
                # Información del administrador
                admin_name = admin_data.get('name', 'Administrador Sistema') if admin_data else 'Administrador Sistema'
                admin_email = admin_data.get('email', f"admin@{company_data['name'].lower().replace(' ', '')}.cl") if admin_data else f"admin@{company_data['name'].lower().replace(' ', '')}.cl"
                
                # Validación defensiva de datos
                company_name = company_data.get('name', 'Empresa Sistema')
                company_rut = company_data.get('rut', '00000000-0')
                
                result = {
                    'company_name': company_name,
                    'company_rut': company_rut,
                    'company_display': f"{company_name} (RUT: {company_rut})",
                    'total_products': total_products,
                    'total_value': total_value,
                    'top_product': top_product,
                    'total_clients': clients_count,
                    'admin_name': admin_name,
                    'admin_email': admin_email,
                    'summary': f"{total_products} productos (${total_value:,.0f} total), {clients_count} clientes"
                }
            else:
                # Empresa no encontrada - usar datos de fallback conocidos
                result = await self._get_fallback_data(company_id, user_id)
            
            # Guardar en cache
            self.cache[cache_key] = result
            return result
                
        except Exception as e:
            logger.warning(f"Error conectando a PostgreSQL: {e}")
            # Sin datos de fallback hardcodeados
            result = {'error': 'No se pudieron obtener datos de la empresa'}
            
            # Guardar en cache
            self.cache[cache_key] = result
            return result
    
    # Método de fallback eliminado - solo usar datos reales
    
    async def build_dynamic_business_context(self, user_context: Dict, enriched_context: str) -> str:
        """Construir contexto empresarial dinámico basado en datos reales de la empresa"""
        try:
            user_id = user_context.get('user_id', 'unknown')
            company_id = user_context.get('company_id', 'unknown')
            
            # Obtener datos empresariales dinámicos
            company_data = await self.get_company_summary_data(user_id, company_id)
            
            context = f"""

📋 CONTEXTO EMPRESARIAL DINÁMICO:
🏢 Empresa: {company_data['company_display']}
📊 Datos disponibles: {company_data['summary']}
👤 Administrador: {company_data['admin_name']}
📧 Email contacto: {company_data['admin_email']}
💰 Producto destacado: {company_data['top_product']}

INSTRUCCIONES PRECISIÓN:
1. USAR DATOS REALES: Siempre referenciar información específica de la empresa
2. EVITAR GENÉRICOS: No dar respuestas vagas o plantillas
3. INCLUIR DETALLES: Mencionar números exactos, nombres específicos
4. PERSONALIZAR: Adaptar respuesta al contexto empresarial real
5. COMPLETAR INFO: Incluir administrador y email cuando sea relevante
6. SER ESPECÍFICO: Usar precios exactos y nombres completos de productos

EJEMPLO FORMATO: "Para {company_data['company_display']}, [respuesta específica con datos reales]"
"""
            return context
            
        except Exception as e:
            logger.error(f"Error construyendo contexto dinámico: {e}")
            # Fallback a contexto genérico mejorado
            return """

📋 CONTEXTO EMPRESARIAL:
INSTRUCCIONES PRECISIÓN:
1. USAR DATOS DISPONIBLES: Referenciar información específica cuando esté disponible
2. EVITAR RESPUESTAS GENÉRICAS: Ser específico y detallado
3. INCLUIR INFORMACIÓN RELEVANTE: Mencionar administradores, emails, productos cuando aplique
4. PERSONALIZAR RESPUESTAS: Adaptar al contexto del usuario
5. SER PRECISO: Usar datos verificados y específicos
"""

    async def test_database_connection(self) -> bool:
        """Probar la conexión a la base de datos PostgreSQL usando el servicio"""
        try:
            if not self._initialized:
                await self.postgres_service.connect()
                self._initialized = True
            
            # Probar consulta usando el servicio PostgreSQL
            test_result = await self.postgres_service.test_connection()
            
            logger.info("✅ Conexión PostgreSQL exitosa a través del servicio")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Error de conexión PostgreSQL: {e}")
            return False
    
    async def disconnect(self):
        """Cerrar conexiones del servicio PostgreSQL"""
        try:
            if self._initialized and self.postgres_service.pool:
                await self.postgres_service.close()
                self._initialized = False
                logger.info("Conexión PostgreSQL cerrada")
        except Exception as e:
            logger.error(f"Error cerrando conexión PostgreSQL: {e}")
    
    def clear_cache(self):
        """Limpiar cache de datos empresariales"""
        self.cache.clear()
        logger.info("Cache de contexto empresarial limpiado")
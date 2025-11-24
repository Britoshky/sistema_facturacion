"""
PostgreSQL Connection Manager - Gestión centralizada de conexiones
"""

import asyncio
from typing import Optional
import asyncpg
from loguru import logger


class PostgreSQLConnectionManager:
    """Gestor centralizado de conexiones PostgreSQL"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Crear pool de conexiones a PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            logger.info("✅ Conectado a PostgreSQL - Pool creado")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            raise
    
    async def test_connection(self):
        """Verificar que la conexión funciona correctamente"""
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as conn:
                # Test básico de conectividad
                result = await conn.fetchrow("SELECT version() as version, current_database() as database")
                logger.info(f"📊 PostgreSQL Version: {result['version'][:60]}...")
                logger.info(f"📊 Database: {result['database']}")
                
                # Test de tablas principales
                tables_query = """
                SELECT 
                    table_name,
                    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """
                
                tables = await conn.fetch(tables_query)
                logger.info("📋 Tablas disponibles:")
                for table in tables:
                    logger.info(f"   - {table['table_name']}: {table['column_count']} columnas")
                
                # Contar registros en tablas principales
                main_tables = ['companies', 'users', 'clients', 'products', 'documents']
                logger.info("📋 Estadísticas de tablas principales:")
                
                for table in main_tables:
                    try:
                        count_result = await conn.fetchrow(f"SELECT COUNT(*) as count FROM {table}")
                        count = count_result['count'] if count_result else 0
                        logger.info(f"   - {table}: {count} registros")
                    except Exception as e:
                        logger.warning(f"   - {table}: No accesible ({str(e)[:30]})")
                
        except Exception as e:
            logger.error(f"❌ Error en test de conexión: {e}")
            raise
    
    async def execute_query(self, query: str, params: tuple = None):
        """Ejecutar consulta SQL"""
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as connection:
                if params:
                    result = await connection.fetch(query, *params)
                else:
                    result = await connection.fetch(query)
                
                return [dict(row) for row in result]
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            return []
    
    async def execute_single_query(self, query: str, params: tuple = None):
        """Ejecutar consulta que retorna un solo registro"""
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as connection:
                if params:
                    result = await connection.fetchrow(query, *params)
                else:
                    result = await connection.fetchrow(query)
                
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando single query: {e}")
            return None
    
    async def close(self):
        """Cerrar pool de conexiones"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("🔌 Conexión PostgreSQL cerrada")
    
    def is_connected(self) -> bool:
        """Verificar si hay conexión activa"""
        return self.pool is not None
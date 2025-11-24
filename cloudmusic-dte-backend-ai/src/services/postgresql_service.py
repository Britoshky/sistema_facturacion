"""
PostgreSQL Service - Alias de compatibilidad
Mantiene compatibilidad con código existente redirigiendo al servicio modular
"""

# Importar servicio modular
from .postgresql_modular_service import PostgreSQLModularService

# Crear alias para compatibilidad total
PostgreSQLService = PostgreSQLModularService

# Exportar funciones utilitarias
from .postgresql_modular_service import format_currency, document_type_name

__all__ = [
    "PostgreSQLService", 
    "format_currency", 
    "document_type_name"
]
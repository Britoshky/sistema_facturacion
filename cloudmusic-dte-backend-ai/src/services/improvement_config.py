"""
CloudMusic DTE AI - Sistema de Integración de Mejoras
Archivo de configuración para la integración de todos los módulos de mejora

Este archivo facilita la activación/desactivación de módulos según necesidades
"""

# Configuración de Módulos de Mejora
IMPROVEMENT_MODULES_CONFIG = {
    # Sistema inteligente de respuestas (orquestador principal)
    "intelligent_response_system": {
        "enabled": True,
        "quality_threshold": 75.0,  # Umbral mínimo de calidad
        "max_regeneration_attempts": 2,  # Máximo intentos de regeneración
        "fallback_to_traditional": True  # Si falla, usar sistema tradicional
    },
    
    # Inyección de datos reales
    "data_injection_service": {
        "enabled": True,
        "cache_ttl_minutes": 15,  # TTL del caché de datos empresariales
        "placeholder_replacement": True,  # Reemplazar placeholders genéricos
        "validation_enabled": True  # Validar datos antes de inyectar
    },
    
    # Validador de calidad de respuestas
    "response_quality_validator": {
        "enabled": True,
        "auto_regeneration": True,  # Regenerar automáticamente si calidad baja
        "detailed_scoring": True,  # Scoring detallado por categorías
        "improvement_suggestions": True  # Generar sugerencias de mejora
    },
    
    # Motor de personalización dinámico
    "dynamic_personalization_engine": {
        "enabled": True,
        "company_context_mapping": True,  # Mapeo de contexto por empresa
        "tone_adaptation": True,  # Adaptación de tono por perfil
        "complexity_adjustment": True,  # Ajuste de complejidad
        "cache_ttl_minutes": 30  # TTL del caché de perfiles
    },
    
    # Análisis de conversación
    "conversation_analysis_module": {
        "enabled": True,
        "pattern_detection": True,  # Detección de patrones
        "behavior_profiling": True,  # Creación de perfiles de comportamiento
        "satisfaction_tracking": True,  # Seguimiento de satisfacción
        "cache_ttl_hours": 2  # TTL del caché de análisis
    }
}

# Configuración de Calidad
QUALITY_CONFIG = {
    "minimum_score_threshold": 60.0,  # Score mínimo aceptable
    "excellent_score_threshold": 85.0,  # Score para calidad excelente
    "regeneration_threshold": 75.0,  # Threshold para activar regeneración
    
    # Pesos para cálculo de score total
    "score_weights": {
        "specificity": 0.25,      # 25% - Eliminación de contenido genérico
        "personalization": 0.25,  # 25% - Personalización empresarial
        "completeness": 0.20,     # 20% - Completitud de respuesta
        "accuracy": 0.20,         # 20% - Precisión técnica
        "engagement": 0.10        # 10% - Nivel de engagement
    }
}

# Configuración de Patrones
PATTERNS_CONFIG = {
    # Patrones genéricos a penalizar (patrón -> penalización)
    "generic_penalties": {
        "el administrador": -15,
        "admin@empresa.cl": -20,
        "Su empresa": -10,
        "la empresa": -8,
        "Me alegra ayudar": -5,
        "¡Hola!": -5,
        "Soy CloudMusic IA": -8
    },
    
    # Patrones específicos a bonificar (patrón -> bonificación)
    "specific_bonuses": {
        "CloudMusic SpA": +10,
        "Carlos Administrador": +15,
        "admin@cloudmusic.cl": +15,
        "78218659-0": +10,  # RUT específico
        "código 33": +8,    # Códigos DTE específicos
        "código 39": +8
    },
    
    # Palabras clave por tópico
    "topic_keywords": {
        "dte_documents": ["dte", "documento", "factura", "boleta", "emitir"],
        "fiscal_tax": ["iva", "impuesto", "fiscal", "tributario", "sii"],
        "business_info": ["empresa", "cliente", "producto", "ventas"],
        "technical_support": ["error", "problema", "configuración", "soporte"]
    }
}

# Configuración de Templates de Respuesta
RESPONSE_TEMPLATES_CONFIG = {
    "company_header_format": "🏢 **{company_name}** (RUT: {company_rut})",
    "admin_info_format": "👤 **Administrador:** {admin_name}",
    "contact_info_format": "📧 **Contacto:** {admin_email}",
    
    "intro_templates": {
        "dte_query": [
            "**{company_name} - Estado de documentos DTE:**",
            "**Información DTE para {company_name}:**",
            "**{admin_name}, aquí está el estado de sus documentos:**"
        ],
        "calculation": [
            "**Cálculo fiscal para {company_name}:**", 
            "**{admin_name}, aquí están sus números fiscales:**"
        ],
        "business_query": [
            "**Información empresarial de {company_name}:**",
            "**{admin_name}, datos de su empresa:**"
        ]
    }
}

# Configuración de Integración
INTEGRATION_CONFIG = {
    "enable_fallback_mode": True,  # Modo fallback si módulos fallan
    "log_improvement_metrics": True,  # Registrar métricas de mejora
    "cache_optimization": True,  # Optimización de caché
    "async_processing": True,  # Procesamiento asíncrono cuando sea posible
    
    "timeouts": {
        "intelligent_response_generation": 8.0,  # Timeout generación inteligente
        "data_injection": 3.0,  # Timeout inyección de datos
        "quality_validation": 2.0,  # Timeout validación de calidad
        "conversation_analysis": 2.0  # Timeout análisis de conversación
    }
}

# Configuración de Métricas y Monitoreo
METRICS_CONFIG = {
    "track_quality_improvements": True,  # Seguimiento de mejoras
    "track_regeneration_rate": True,  # Tasa de regeneración
    "track_user_satisfaction": True,  # Satisfacción del usuario
    "export_metrics_interval": 300,  # Intervalo exportación métricas (segundos)
    
    "quality_target": {
        "average_score": 80.0,  # Score promedio objetivo
        "excellent_rate": 0.7,  # % respuestas excelentes objetivo
        "regeneration_rate": 0.2  # % regeneración máxima aceptable
    }
}

def get_module_config(module_name: str) -> dict:
    """Obtiene configuración de un módulo específico"""
    return IMPROVEMENT_MODULES_CONFIG.get(module_name, {})

def is_module_enabled(module_name: str) -> bool:
    """Verifica si un módulo está habilitado"""
    return get_module_config(module_name).get("enabled", False)

def get_quality_threshold() -> float:
    """Obtiene el threshold de calidad configurado"""
    return QUALITY_CONFIG.get("regeneration_threshold", 75.0)

def get_timeout_config(operation: str) -> float:
    """Obtiene timeout configurado para una operación"""
    return INTEGRATION_CONFIG.get("timeouts", {}).get(operation, 5.0)

def get_pattern_config() -> dict:
    """Obtiene configuración de patrones"""
    return PATTERNS_CONFIG

def should_use_intelligent_system() -> bool:
    """Determina si usar el sistema inteligente"""
    return is_module_enabled("intelligent_response_system")

def get_improvement_stats_config() -> dict:
    """Obtiene configuración de estadísticas de mejora"""
    return METRICS_CONFIG
"""
CloudMusic DTE AI - Response Quality Validator
Validador de calidad para respuestas de IA

Funcionalidades:
- Análisis de calidad pre-envío
- Detección de contenido genérico
- Scoring automático de respuestas
- Activación de re-generación inteligente
"""

import logging
import re
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum

class QualityLevel(Enum):
    EXCELLENT = "excellent"  # 85-100
    GOOD = "good"           # 70-84
    AVERAGE = "average"     # 55-69
    POOR = "poor"          # 40-54
    UNACCEPTABLE = "unacceptable"  # 0-39

@dataclass
class QualityMetrics:
    """Métricas de calidad de respuesta"""
    specificity_score: float = 0.0
    personalization_score: float = 0.0
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    engagement_score: float = 0.0
    total_score: float = 0.0
    quality_level: QualityLevel = QualityLevel.UNACCEPTABLE
    improvement_suggestions: List[str] = None
    generic_patterns_found: List[str] = None

class ResponseQualityValidator:
    """Validador de calidad de respuestas de IA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patrones genéricos que reducen calidad (penalizaciones)
        self.generic_patterns = {
            r'\bel administrador\b': -15,  # Muy genérico
            r'admin@empresa\.cl': -20,     # Email genérico
            r'\bSu empresa\b': -10,        # Referencia genérica
            r'\bla empresa\b': -8,         # Referencia genérica
            r'Información empresarial completa:\s*👤\s*\*\*Administrador:\*\*\s*el administrador': -25,
            r'Me alegra\s*(poder\s*)?ayudar': -5,  # Introducción genérica
            r'¡Hola!': -5,                # Saludo genérico
            r'Soy CloudMusic IA': -8,     # Autoidentificación genérica
            r'estimado\s*(cliente|usuario)': -3,  # Tratamiento genérico
        }
        
        # Patrones específicos que aumentan calidad (bonificaciones)
        self.specific_patterns = {
            r'\bCloudMusic SpA\b': +10,           # Empresa específica
            r'\bCarlos Administrador\b': +15,     # Nombre específico
            r'admin@cloudmusic\.cl': +15,         # Email específico
            r'78218659-0': +10,                   # RUT específico
            r'\$\d{1,3}(?:\.\d{3})*': +5,       # Montos específicos
            r'\b\d{1,2}/\d{1,2}/\d{4}\b': +5,   # Fechas específicas
            r'código\s*\d+': +8,                # Códigos DTE específicos
            r'factura\s*electrónica': +5,        # Terminología DTE
            r'boleta\s*electrónica': +5,         # Terminología DTE
        }
        
        # Criterios de completitud
        self.completeness_indicators = [
            r'✅',  # Checks de confirmación
            r'📋',  # Información estructurada
            r'👤',  # Datos personales
            r'📧',  # Contacto
            r'🏢',  # Empresa
            r'💰',  # Información financiera
        ]
        
        self.logger.info("🔍 ResponseQualityValidator inicializado")
    
    async def validate_response(
        self, 
        response_text: str, 
        user_query: str,
        context_data: Dict[str, Any] = None
    ) -> QualityMetrics:
        """
        Valida calidad de respuesta generada
        
        Args:
            response_text: Texto de la respuesta
            user_query: Consulta original del usuario
            context_data: Datos de contexto disponibles
            
        Returns:
            QualityMetrics con scoring detallado
        """
        try:
            metrics = QualityMetrics(improvement_suggestions=[], generic_patterns_found=[])
            
            # 1. Análisis de especificidad
            metrics.specificity_score = await self._analyze_specificity(response_text, metrics)
            
            # 2. Análisis de personalización  
            metrics.personalization_score = await self._analyze_personalization(
                response_text, context_data, metrics
            )
            
            # 3. Análisis de completitud
            metrics.completeness_score = await self._analyze_completeness(
                response_text, user_query, metrics
            )
            
            # 4. Análisis de precisión
            metrics.accuracy_score = await self._analyze_accuracy(response_text, metrics)
            
            # 5. Análisis de engagement
            metrics.engagement_score = await self._analyze_engagement(response_text, metrics)
            
            # Cálculo de score total (ponderado)
            metrics.total_score = (
                metrics.specificity_score * 0.25 +      # 25%
                metrics.personalization_score * 0.25 +  # 25%
                metrics.completeness_score * 0.20 +     # 20%
                metrics.accuracy_score * 0.20 +         # 20%
                metrics.engagement_score * 0.10         # 10%
            )
            
            # Determinar nivel de calidad
            metrics.quality_level = self._determine_quality_level(metrics.total_score)
            
            self.logger.info(f"🔍 Respuesta evaluada: {metrics.total_score:.1f}/100 ({metrics.quality_level.value})")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error en validación de respuesta: {e}")
            return QualityMetrics()
    
    async def _analyze_specificity(self, text: str, metrics: QualityMetrics) -> float:
        """Analiza especificidad vs contenido genérico"""
        
        try:
            base_score = 50.0  # Score base
            
            # Penalizar patrones genéricos
            for pattern, penalty in self.generic_patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    base_score += penalty * len(matches)
                    metrics.generic_patterns_found.extend([f"Genérico: {match}" for match in matches])
            
            # Bonificar patrones específicos
            for pattern, bonus in self.specific_patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    base_score += bonus * len(matches)
            
            # Normalizar entre 0-100
            return max(0, min(100, base_score))
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando especificidad: {e}")
            return 0.0
    
    async def _analyze_personalization(
        self, 
        text: str, 
        context_data: Dict[str, Any], 
        metrics: QualityMetrics
    ) -> float:
        """Analiza nivel de personalización"""
        
        try:
            score = 0.0
            
            if not context_data:
                metrics.improvement_suggestions.append("Usar más datos de contexto empresarial")
                return 30.0  # Score básico sin contexto
            
            # Verificar uso de datos personales
            if context_data.get('admin_name') and context_data['admin_name'] in text:
                score += 25
            else:
                metrics.improvement_suggestions.append("Incluir nombre del administrador específico")
            
            if context_data.get('company_name') and context_data['company_name'] in text:
                score += 25
            else:
                metrics.improvement_suggestions.append("Mencionar nombre de empresa específico")
                
            if context_data.get('admin_email') and context_data['admin_email'] in text:
                score += 20
            else:
                metrics.improvement_suggestions.append("Incluir email específico de contacto")
                
            # Verificar contextualización empresarial
            if any(indicator in text for indicator in ['DTE', 'factura', 'boleta', 'SII']):
                score += 15
                
            # Verificar datos financieros específicos
            if re.search(r'\$[\d\.,]+', text):
                score += 15
            
            return min(100, score)
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando personalización: {e}")
            return 0.0
    
    async def _analyze_completeness(self, text: str, query: str, metrics: QualityMetrics) -> float:
        """Analiza completitud de la respuesta"""
        
        try:
            score = 20.0  # Score base
            
            # Verificar presencia de elementos estructurados
            for indicator in self.completeness_indicators:
                if indicator in text:
                    score += 10
            
            # Verificar longitud apropiada (no muy corta ni muy larga)
            text_length = len(text.strip())
            if 100 <= text_length <= 800:
                score += 20
            elif text_length < 50:
                score -= 20
                metrics.improvement_suggestions.append("Respuesta muy breve, agregar más detalles")
            elif text_length > 1200:
                score -= 10
                metrics.improvement_suggestions.append("Respuesta muy extensa, ser más conciso")
            
            # Verificar que responda a la consulta
            query_words = set(query.lower().split())
            text_words = set(text.lower().split())
            relevance = len(query_words.intersection(text_words)) / len(query_words)
            score += relevance * 30
            
            return min(100, score)
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando completitud: {e}")
            return 0.0
    
    async def _analyze_accuracy(self, text: str, metrics: QualityMetrics) -> float:
        """Analiza precisión y veracidad"""
        
        try:
            score = 70.0  # Score base (asumiendo precisión)
            
            # Verificar inconsistencias obvias
            inconsistency_patterns = [
                (r'admin@empresa\.cl.*admin@cloudmusic\.cl', -15),  # Emails contradictorios
                (r'el administrador.*Carlos Administrador', -10),   # Nombres contradictorios
                (r'Su empresa.*CloudMusic SpA', -5),               # Referencias contradictorias
            ]
            
            for pattern, penalty in inconsistency_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += penalty
                    metrics.improvement_suggestions.append("Resolver inconsistencias en la información")
            
            # Bonificar información técnica correcta
            technical_patterns = [
                r'código\s*33',      # Factura electrónica
                r'código\s*39',      # Boleta electrónica  
                r'código\s*61',      # Nota de crédito
                r'RUT\s*\d{8}-[\dKk]',  # Formato RUT válido
            ]
            
            for pattern in technical_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 5
            
            return min(100, max(0, score))
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando precisión: {e}")
            return 70.0
    
    async def _analyze_engagement(self, text: str, metrics: QualityMetrics) -> float:
        """Analiza nivel de engagement y conversacionalidad"""
        
        try:
            score = 50.0  # Score base
            
            # Bonificar elementos que mejoran engagement
            engagement_elements = [
                (r'✅', +8),   # Confirmaciones visuales
                (r'📋', +5),   # Información estructurada
                (r'💡', +5),   # Tips o sugerencias
                (r'⚡', +3),   # Elementos dinámicos
                (r'🔍', +3),   # Elementos exploratorios
            ]
            
            for pattern, bonus in engagement_elements:
                matches = len(re.findall(pattern, text))
                score += bonus * min(matches, 3)  # Máximo 3 bonificaciones por elemento
            
            # Penalizar respuestas muy robóticas
            if not re.search(r'[.!?]', text):
                score -= 10
                metrics.improvement_suggestions.append("Añadir puntuación para mejor legibilidad")
            
            # Bonificar estructura clara
            if re.search(r'\*\*.*\*\*', text):  # Headers en markdown
                score += 10
            
            return min(100, max(0, score))
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando engagement: {e}")
            return 50.0
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determina nivel de calidad basado en score"""
        
        if score >= 85:
            return QualityLevel.EXCELLENT
        elif score >= 70:
            return QualityLevel.GOOD
        elif score >= 55:
            return QualityLevel.AVERAGE
        elif score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    async def should_regenerate_response(self, metrics: QualityMetrics, threshold: float = 75.0) -> bool:
        """
        Determina si la respuesta debe regenerarse
        
        Args:
            metrics: Métricas de calidad
            threshold: Umbral mínimo de calidad
            
        Returns:
            True si debe regenerarse
        """
        return (
            metrics.total_score < threshold or
            metrics.quality_level in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE] or
            len(metrics.generic_patterns_found) > 2
        )
    
    def generate_improvement_report(self, metrics: QualityMetrics) -> str:
        """Genera reporte de mejoras sugeridas"""
        
        report = f"""
📊 **Reporte de Calidad de Respuesta**

🎯 **Score Total:** {metrics.total_score:.1f}/100 ({metrics.quality_level.value})

📈 **Scores Detallados:**
• Especificidad: {metrics.specificity_score:.1f}/100
• Personalización: {metrics.personalization_score:.1f}/100  
• Completitud: {metrics.completeness_score:.1f}/100
• Precisión: {metrics.accuracy_score:.1f}/100
• Engagement: {metrics.engagement_score:.1f}/100

🚨 **Patrones Genéricos Detectados:** {len(metrics.generic_patterns_found)}
{chr(10).join(f"  • {pattern}" for pattern in metrics.generic_patterns_found[:5])}

💡 **Sugerencias de Mejora:**
{chr(10).join(f"  • {suggestion}" for suggestion in metrics.improvement_suggestions[:5])}
        """
        
        return report.strip()
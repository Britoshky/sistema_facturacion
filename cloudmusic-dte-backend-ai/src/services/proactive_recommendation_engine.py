"""
Motor de Recomendaciones Proactivas - Sistema predictivo de sugerencias inteligentes
"""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter

import redis.asyncio as aioredis
from loguru import logger


class RecommendationType(Enum):
    """Tipos de recomendación"""
    PRODUCT_SUGGESTION = "product_suggestion"
    DTE_OPTIMIZATION = "dte_optimization" 
    CLIENT_MANAGEMENT = "client_management"
    WORKFLOW_IMPROVEMENT = "workflow_improvement"
    COST_REDUCTION = "cost_reduction"
    COMPLIANCE_WARNING = "compliance_warning"
    BUSINESS_INSIGHT = "business_insight"


class Priority(Enum):
    """Prioridad de recomendación"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class UserBehaviorPattern:
    """Patrón de comportamiento del usuario"""
    user_id: str
    company_id: str
    frequent_queries: List[str]
    preferred_response_types: List[str]
    interaction_times: List[datetime]
    session_durations: List[float]
    error_patterns: List[str]
    satisfaction_scores: List[float]
    last_updated: datetime


@dataclass 
class ProactiveRecommendation:
    """Recomendación proactiva"""
    recommendation_id: str
    user_id: str
    company_id: str
    recommendation_type: RecommendationType
    priority: Priority
    title: str
    description: str
    action_suggestion: str
    confidence_score: float
    potential_impact: str
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any]


class ProactiveRecommendationEngine:
    """Motor de recomendaciones proactivas"""
    
    def __init__(self, redis_url: str = None):
        # Usar configuración del .env si está disponible
        import os
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.recommendation_ttl = 24 * 3600  # 24 horas
        
        # Reglas de recomendación para CloudMusic
        self.recommendation_rules = {
            # Reglas de productos
            "cloudmusic_pro_upgrade": {
                "triggers": ["consulta_multiples_productos", "problemas_facturacion", "volumen_alto"],
                "recommendation": {
                    "type": RecommendationType.PRODUCT_SUGGESTION,
                    "priority": Priority.HIGH,
                    "title": "Upgrade a CloudMusic Pro recomendado",
                    "description": "Basado en tu actividad, CloudMusic Pro ($2,500,000) optimizaría tu gestión de facturación electrónica.",
                    "action": "Considera upgrading a CloudMusic Pro para funcionalidades avanzadas y mejor rendimiento.",
                    "impact": "Reducción de errores en 85% y ahorro de 15 horas semanales"
                }
            },
            
            # Reglas de DTE
            "dte_optimization": {
                "triggers": ["errores_dte_frecuentes", "consultas_codigos_sii"],
                "recommendation": {
                    "type": RecommendationType.DTE_OPTIMIZATION,
                    "priority": Priority.MEDIUM,
                    "title": "Optimización de procesos DTE",
                    "description": "Se detectaron oportunidades de mejora en tu proceso de facturación electrónica.",
                    "action": "Revisa la configuración de documentos DTE (Factura 33, Boleta 39) y considera capacitación adicional.",
                    "impact": "Mejora de cumplimiento SII y reducción de rechazos en 70%"
                }
            },
            
            # Reglas de clientes
            "client_management": {
                "triggers": ["consultas_clientes_frecuentes", "problemas_datos_clientes"],
                "recommendation": {
                    "type": RecommendationType.CLIENT_MANAGEMENT,
                    "priority": Priority.MEDIUM,
                    "title": "Mejora gestión de clientes",
                    "description": "Tu base de datos de clientes podría beneficiarse de organización adicional.",
                    "action": "Implementa categorización de clientes y actualiza datos de contacto regularmente.",
                    "impact": "Comunicación más efectiva y reducción de errores de facturación"
                }
            },
            
            # Reglas de cumplimiento
            "compliance_warning": {
                "triggers": ["errores_sii", "documentos_vencidos"],
                "recommendation": {
                    "type": RecommendationType.COMPLIANCE_WARNING,
                    "priority": Priority.CRITICAL,
                    "title": "Alerta de cumplimiento SII",
                    "description": "Se detectaron posibles riesgos de cumplimiento con normativas SII.",
                    "action": "Revisa inmediatamente el estado de documentos DTE y corrige inconsistencias.",
                    "impact": "Evita multas SII y mantiene el cumplimiento normativo"
                }
            },
            
            # Insights de negocio
            "revenue_optimization": {
                "triggers": ["consultas_productos_caros", "interes_servicios_premium"],
                "recommendation": {
                    "type": RecommendationType.BUSINESS_INSIGHT,
                    "priority": Priority.HIGH,
                    "title": "Oportunidad de incremento de ingresos",
                    "description": "Análisis de tu cartera sugiere potencial para servicios de mayor valor.",
                    "action": "Considera ofrecer Consultoría DTE ($1,200,000) o Auditoría Fiscal ($900,000) a clientes actuales.",
                    "impact": "Potencial incremento de ingresos de hasta 40%"
                }
            }
        }
        
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await asyncio.wait_for(self.redis_client.ping(), timeout=3.0)
            logger.info(f"🔮 ProactiveRecommendationEngine conectado: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ ProactiveRecommendationEngine sin Redis - modo local: {str(e)[:100]}...")
            self.redis_client = None
            
    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def analyze_user_behavior(self, user_id: str, company_id: str) -> UserBehaviorPattern:
        """Analizar patrones de comportamiento del usuario"""
        try:
            # Obtener datos de comportamiento desde Redis
            behavior_key = f"behavior_pattern:{company_id}:{user_id}"
            
            # Verificar si Redis está disponible
            if not self.redis_client:
                # Crear patrón básico sin datos persistentes
                return UserBehaviorPattern(
                    user_id=user_id,
                    company_id=company_id,
                    frequent_queries=[],
                    preferred_response_types=[],
                    interaction_times=[],
                    session_durations=[],
                    error_patterns=[],
                    satisfaction_scores=[],
                    last_updated=datetime.utcnow()
                )
                
            behavior_data = await self.redis_client.hgetall(behavior_key)
            
            if behavior_data:
                return UserBehaviorPattern(
                    user_id=user_id,
                    company_id=company_id,
                    frequent_queries=json.loads(behavior_data.get('frequent_queries', '[]')),
                    preferred_response_types=json.loads(behavior_data.get('preferred_response_types', '[]')),
                    interaction_times=[datetime.fromisoformat(dt) for dt in json.loads(behavior_data.get('interaction_times', '[]'))],
                    session_durations=json.loads(behavior_data.get('session_durations', '[]')),
                    error_patterns=json.loads(behavior_data.get('error_patterns', '[]')),
                    satisfaction_scores=json.loads(behavior_data.get('satisfaction_scores', '[]')),
                    last_updated=datetime.fromisoformat(behavior_data.get('last_updated', datetime.now().isoformat()))
                )
            else:
                # Crear patrón base para nuevos usuarios
                return UserBehaviorPattern(
                    user_id=user_id,
                    company_id=company_id,
                    frequent_queries=[],
                    preferred_response_types=[],
                    interaction_times=[],
                    session_durations=[],
                    error_patterns=[],
                    satisfaction_scores=[],
                    last_updated=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"❌ Error analizando comportamiento del usuario: {e}")
            return UserBehaviorPattern(user_id, company_id, [], [], [], [], [], [], datetime.now())
            
    async def update_user_behavior(self, user_id: str, company_id: str, 
                                 query: str, response_type: str, session_duration: float, 
                                 satisfaction_score: Optional[float] = None, error_occurred: bool = False):
        """Actualizar patrón de comportamiento del usuario"""
        try:
            behavior = await self.analyze_user_behavior(user_id, company_id)
            
            # Actualizar patrones
            behavior.frequent_queries.append(query)
            behavior.frequent_queries = behavior.frequent_queries[-50:]  # Mantener últimas 50
            
            behavior.preferred_response_types.append(response_type)
            behavior.preferred_response_types = behavior.preferred_response_types[-20:]
            
            behavior.interaction_times.append(datetime.now())
            behavior.interaction_times = behavior.interaction_times[-30:]  # Últimas 30 interacciones
            
            if session_duration > 0:
                behavior.session_durations.append(session_duration)
                behavior.session_durations = behavior.session_durations[-20:]
                
            if satisfaction_score is not None:
                behavior.satisfaction_scores.append(satisfaction_score)
                behavior.satisfaction_scores = behavior.satisfaction_scores[-15:]
                
            if error_occurred:
                behavior.error_patterns.append(query)
                behavior.error_patterns = behavior.error_patterns[-10:]
                
            behavior.last_updated = datetime.now()
            
            # Guardar en Redis
            await self._store_behavior_pattern(behavior)
            
            # Generar recomendaciones si es necesario
            await self._evaluate_recommendation_triggers(behavior)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando comportamiento del usuario: {e}")
            
    async def _store_behavior_pattern(self, behavior: UserBehaviorPattern):
        """Almacenar patrón de comportamiento"""
        try:
            behavior_key = f"behavior_pattern:{behavior.company_id}:{behavior.user_id}"
            
            behavior_data = {
                'frequent_queries': json.dumps(behavior.frequent_queries),
                'preferred_response_types': json.dumps(behavior.preferred_response_types),
                'interaction_times': json.dumps([dt.isoformat() for dt in behavior.interaction_times]),
                'session_durations': json.dumps(behavior.session_durations),
                'error_patterns': json.dumps(behavior.error_patterns),
                'satisfaction_scores': json.dumps(behavior.satisfaction_scores),
                'last_updated': behavior.last_updated.isoformat()
            }
            
            # Solo almacenar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - patrón de comportamiento no persistido")
                return
                
            await self.redis_client.hset(behavior_key, mapping=behavior_data)
            await self.redis_client.expire(behavior_key, 30 * 24 * 3600)  # 30 días
            
        except Exception as e:
            logger.error(f"❌ Error almacenando patrón de comportamiento: {e}")
            
    async def _evaluate_recommendation_triggers(self, behavior: UserBehaviorPattern):
        """Evaluar triggers para generar recomendaciones"""
        try:
            active_triggers = self._identify_active_triggers(behavior)
            
            for rule_id, rule in self.recommendation_rules.items():
                if self._should_trigger_recommendation(active_triggers, rule['triggers']):
                    await self._generate_recommendation(behavior, rule_id, rule['recommendation'])
                    
        except Exception as e:
            logger.error(f"❌ Error evaluando triggers de recomendación: {e}")
            
    def _identify_active_triggers(self, behavior: UserBehaviorPattern) -> List[str]:
        """Identificar triggers activos basados en el comportamiento"""
        triggers = []
        
        # Análisis de consultas frecuentes
        query_counter = Counter(behavior.frequent_queries)
        most_common_queries = [query for query, count in query_counter.most_common(10)]
        
        # Trigger: consultas múltiples productos
        product_queries = [q for q in most_common_queries if any(word in q.lower() for word in ['producto', 'servicio', 'precio'])]
        if len(product_queries) >= 3:
            triggers.append("consulta_multiples_productos")
            
        # Trigger: problemas de facturación
        if any('error' in q.lower() or 'problema' in q.lower() for q in most_common_queries):
            triggers.append("problemas_facturacion")
            
        # Trigger: volumen alto de interacciones
        if len(behavior.interaction_times) >= 15 and len(behavior.session_durations) >= 10:
            avg_session = np.mean(behavior.session_durations)
            if avg_session > 300:  # Más de 5 minutos promedio
                triggers.append("volumen_alto")
                
        # Trigger: errores DTE frecuentes
        dte_errors = [e for e in behavior.error_patterns if any(word in e.lower() for word in ['dte', 'factura', 'sii'])]
        if len(dte_errors) >= 2:
            triggers.append("errores_dte_frecuentes")
            
        # Trigger: consultas códigos SII
        sii_queries = [q for q in most_common_queries if any(word in q.lower() for word in ['codigo', 'sii', '33', '39'])]
        if len(sii_queries) >= 2:
            triggers.append("consultas_codigos_sii")
            
        # Trigger: interés en servicios premium
        premium_queries = [q for q in most_common_queries if any(word in q.lower() for word in ['pro', 'premium', 'consultoria', 'auditoria'])]
        if len(premium_queries) >= 2:
            triggers.append("interes_servicios_premium")
            
        # Trigger: baja satisfacción
        if behavior.satisfaction_scores:
            avg_satisfaction = np.mean(behavior.satisfaction_scores)
            if avg_satisfaction < 3.0:
                triggers.append("baja_satisfaccion")
                
        return triggers
        
    def _should_trigger_recommendation(self, active_triggers: List[str], rule_triggers: List[str]) -> bool:
        """Determinar si se debe activar una recomendación"""
        # Al menos 2 triggers deben coincidir para generar recomendación
        matches = sum(1 for trigger in rule_triggers if trigger in active_triggers)
        return matches >= min(2, len(rule_triggers))
        
    async def _generate_recommendation(self, behavior: UserBehaviorPattern, rule_id: str, recommendation_config: Dict[str, Any]):
        """Generar recomendación específica"""
        try:
            recommendation_id = f"{behavior.company_id}_{behavior.user_id}_{rule_id}_{int(datetime.now().timestamp())}"
            
            # Calcular confidence score basado en comportamiento
            confidence_score = self._calculate_confidence_score(behavior, rule_id)
            
            recommendation = ProactiveRecommendation(
                recommendation_id=recommendation_id,
                user_id=behavior.user_id,
                company_id=behavior.company_id,
                recommendation_type=recommendation_config['type'],
                priority=recommendation_config['priority'],
                title=recommendation_config['title'],
                description=recommendation_config['description'],
                action_suggestion=recommendation_config['action'],
                confidence_score=confidence_score,
                potential_impact=recommendation_config['impact'],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                metadata={
                    "rule_id": rule_id,
                    "user_interaction_count": len(behavior.interaction_times),
                    "avg_satisfaction": np.mean(behavior.satisfaction_scores) if behavior.satisfaction_scores else 0.0
                }
            )
            
            await self._store_recommendation(recommendation)
            logger.info(f"🔮 Recomendación generada: {recommendation.title} (confianza: {confidence_score:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendación: {e}")
            
    def _calculate_confidence_score(self, behavior: UserBehaviorPattern, rule_id: str) -> float:
        """Calcular score de confianza para la recomendación"""
        base_confidence = 0.6
        
        # Bonus por interacciones frecuentes
        if len(behavior.interaction_times) > 10:
            base_confidence += 0.15
            
        # Bonus por satisfacción alta
        if behavior.satisfaction_scores:
            avg_satisfaction = np.mean(behavior.satisfaction_scores)
            if avg_satisfaction > 4.0:
                base_confidence += 0.1
            elif avg_satisfaction < 2.5:
                base_confidence += 0.2  # Usuario insatisfecho, mayor necesidad
                
        # Bonus por patrones específicos del rule
        if rule_id == "product_upgrade" and len(behavior.error_patterns) > 3:
            base_confidence += 0.1
            
        return min(0.95, base_confidence)
        
    async def _store_recommendation(self, recommendation: ProactiveRecommendation):
        """Almacenar recomendación"""
        try:
            # Solo almacenar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - recomendación no persistida")
                return
                
            rec_key = f"recommendation:{recommendation.company_id}:{recommendation.user_id}:{recommendation.recommendation_id}"
            
            rec_data = {
                'recommendation_id': recommendation.recommendation_id,
                'user_id': recommendation.user_id,
                'company_id': recommendation.company_id,
                'recommendation_type': recommendation.recommendation_type.value,
                'priority': str(recommendation.priority.value),
                'title': recommendation.title,
                'description': recommendation.description,
                'action_suggestion': recommendation.action_suggestion,
                'confidence_score': str(recommendation.confidence_score),
                'potential_impact': recommendation.potential_impact,
                'created_at': recommendation.created_at.isoformat(),
                'expires_at': recommendation.expires_at.isoformat(),
                'metadata': json.dumps(recommendation.metadata)
            }
            
            await self.redis_client.hset(rec_key, mapping=rec_data)
            await self.redis_client.expire(rec_key, self.recommendation_ttl)
            
            # Añadir a lista de recomendaciones activas del usuario
            active_key = f"active_recommendations:{recommendation.company_id}:{recommendation.user_id}"
            await self.redis_client.sadd(active_key, recommendation.recommendation_id)
            await self.redis_client.expire(active_key, self.recommendation_ttl)
            
        except Exception as e:
            logger.error(f"❌ Error almacenando recomendación: {e}")
            
    async def get_active_recommendations(self, user_id: str, company_id: str) -> List[ProactiveRecommendation]:
        """Obtener recomendaciones activas para un usuario"""
        try:
            # Retornar lista vacía si Redis no está disponible
            if not self.redis_client:
                return []
                
            active_key = f"active_recommendations:{company_id}:{user_id}"
            recommendation_ids = await self.redis_client.smembers(active_key)
            
            recommendations = []
            for rec_id in recommendation_ids:
                rec_key = f"recommendation:{company_id}:{user_id}:{rec_id}"
                rec_data = await self.redis_client.hgetall(rec_key)
                
                if rec_data:
                    recommendation = ProactiveRecommendation(
                        recommendation_id=rec_data['recommendation_id'],
                        user_id=rec_data['user_id'],
                        company_id=rec_data['company_id'],
                        recommendation_type=RecommendationType(rec_data['recommendation_type']),
                        priority=Priority(int(rec_data['priority'])),
                        title=rec_data['title'],
                        description=rec_data['description'],
                        action_suggestion=rec_data['action_suggestion'],
                        confidence_score=float(rec_data['confidence_score']),
                        potential_impact=rec_data['potential_impact'],
                        created_at=datetime.fromisoformat(rec_data['created_at']),
                        expires_at=datetime.fromisoformat(rec_data['expires_at']),
                        metadata=json.loads(rec_data['metadata'])
                    )
                    
                    # Verificar si no ha expirado
                    if recommendation.expires_at > datetime.now():
                        recommendations.append(recommendation)
                        
            # Ordenar por prioridad y confianza
            recommendations.sort(key=lambda x: (x.priority.value, x.confidence_score), reverse=True)
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo recomendaciones activas: {e}")
            return []
            
    async def dismiss_recommendation(self, user_id: str, company_id: str, recommendation_id: str):
        """Descartar una recomendación"""
        try:
            # Solo actualizar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - recomendación no descartada")
                return
                
            # Remover de activas
            active_key = f"active_recommendations:{company_id}:{user_id}"
            await self.redis_client.srem(active_key, recommendation_id)
            
            # Marcar como descartada
            rec_key = f"recommendation:{company_id}:{user_id}:{recommendation_id}"
            await self.redis_client.hset(rec_key, "dismissed", "true")
            
            logger.info(f"🔮 Recomendación {recommendation_id} descartada")
            
        except Exception as e:
            logger.error(f"❌ Error descartando recomendación: {e}")
            
    async def get_recommendation_stats(self, company_id: str) -> Dict[str, Any]:
        """Obtener estadísticas de recomendaciones"""
        try:
            # Retornar estadísticas vacías si Redis no está disponible
            if not self.redis_client:
                return {
                    "total_recommendations": 0,
                    "active_recommendations": 0,
                    "dismissed_recommendations": 0,
                    "recommendation_types": {},
                    "status": "redis_not_available"
                }
                
            pattern = f"recommendation:{company_id}:*"
            total_recommendations = 0
            type_counts = Counter()
            priority_counts = Counter()
            
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                rec_data = await self.redis_client.hgetall(key)
                if rec_data:
                    total_recommendations += 1
                    type_counts[rec_data.get('recommendation_type', 'unknown')] += 1
                    priority_counts[rec_data.get('priority', '0')] += 1
                    
            return {
                "total_recommendations": total_recommendations,
                "by_type": dict(type_counts),
                "by_priority": dict(priority_counts),
                "generated_today": total_recommendations  # Simplificado para el ejemplo
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de recomendaciones: {e}")
            return {"error": str(e)}
"""
Servicio de Aprendizaje Adaptativo - Mejora continua basada en datos y conversaciones
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class UserLearningProfile:
    """Perfil de aprendizaje específico por usuario"""
    user_id: str
    company_id: str
    
    # Patrones de consulta
    frequent_topics: Dict[str, int] = None
    preferred_response_style: str = "profesional"
    technical_level: str = "intermedio"  # basico, intermedio, avanzado
    
    # Contexto empresarial dinámico
    business_priorities: List[str] = None
    recent_activities: List[Dict] = None
    
    # Métricas de satisfacción
    response_ratings: List[float] = None
    interaction_count: int = 0
    
    def __post_init__(self):
        if self.frequent_topics is None:
            self.frequent_topics = {}
        if self.business_priorities is None:
            self.business_priorities = []
        if self.recent_activities is None:
            self.recent_activities = []
        if self.response_ratings is None:
            self.response_ratings = []

class AdaptiveLearningService:
    """Servicio que aprende de cada conversación y mejora respuestas futuras"""
    
    def __init__(self, postgres_service=None, mongodb_service=None):
        self.postgres_service = postgres_service
        self.mongodb_service = mongodb_service
        self.user_profiles: Dict[str, UserLearningProfile] = {}
        self.conversation_patterns: Dict[str, Dict] = defaultdict(dict)
        
    async def analyze_user_behavior(self, user_id: str, company_id: str, conversation_history: List[Dict]) -> UserLearningProfile:
        """Analizar comportamiento del usuario para crear/actualizar perfil de aprendizaje"""
        
        # Obtener o crear perfil
        profile_key = f"{user_id}_{company_id}"
        if profile_key not in self.user_profiles:
            self.user_profiles[profile_key] = UserLearningProfile(user_id, company_id)
        
        profile = self.user_profiles[profile_key]
        
        # Analizar temas frecuentes
        await self._analyze_frequent_topics(profile, conversation_history)
        
        # Determinar nivel técnico
        await self._determine_technical_level(profile, conversation_history)
        
        # Identificar prioridades empresariales
        await self._identify_business_priorities(profile, user_id, company_id)
        
        # Actualizar actividades recientes
        await self._update_recent_activities(profile, user_id, company_id)
        
        profile.interaction_count += 1
        
        return profile
    
    async def _analyze_frequent_topics(self, profile: UserLearningProfile, history: List[Dict]):
        """Analizar temas más frecuentes en conversaciones"""
        topic_keywords = {
            "facturacion": ["factura", "documento", "dte", "sii", "tributario", "impuesto"],
            "productos": ["producto", "servicio", "precio", "costo", "inventario", "catalogo"],
            "clientes": ["cliente", "rut", "empresa", "contacto", "direccion"],
            "reportes": ["reporte", "informe", "estadistica", "grafico", "analisis"],
            "configuracion": ["configurar", "setup", "parametro", "ajuste", "preferencia"],
            "calculos": ["calculo", "suma", "total", "porcentaje", "iva", "neto"]
        }
        
        for message in history[-20:]:  # Últimas 20 conversaciones
            content = message.get('content', '').lower()
            for topic, keywords in topic_keywords.items():
                if any(keyword in content for keyword in keywords):
                    profile.frequent_topics[topic] = profile.frequent_topics.get(topic, 0) + 1
    
    async def _determine_technical_level(self, profile: UserLearningProfile, history: List[Dict]):
        """Determinar nivel técnico basado en el tipo de preguntas"""
        technical_indicators = {
            "basico": ["como", "que es", "explicar", "ayuda", "no se", "simple"],
            "intermedio": ["configurar", "parametro", "proceso", "procedimiento"],
            "avanzado": ["api", "integracion", "automatizar", "script", "configuracion avanzada"]
        }
        
        level_scores = {"basico": 0, "intermedio": 0, "avanzado": 0}
        
        for message in history[-10:]:
            content = message.get('content', '').lower()
            for level, indicators in technical_indicators.items():
                if any(indicator in content for indicator in indicators):
                    level_scores[level] += 1
        
        # Determinar nivel predominante
        if level_scores["avanzado"] > level_scores["intermedio"]:
            profile.technical_level = "avanzado"
        elif level_scores["basico"] > level_scores["intermedio"]:
            profile.technical_level = "basico"
        else:
            profile.technical_level = "intermedio"
    
    async def _identify_business_priorities(self, profile: UserLearningProfile, user_id: str, company_id: str):
        """Identificar prioridades empresariales basadas en datos reales"""
        if not self.postgres_service:
            return
            
        try:
            # Obtener datos empresariales actualizados
            business_data = await self.postgres_service.get_user_business_summary(user_id)
            
            priorities = []
            
            # Prioridad basada en volumen de documentos
            if business_data.get('total_documents', 0) > 10:
                priorities.append("gestion_documentos")
            
            # Prioridad basada en número de clientes
            if business_data.get('total_clients', 0) > 20:
                priorities.append("gestion_clientes")
            
            # Prioridad basada en facturación
            revenue = business_data.get('total_revenue', 0)
            if revenue > 50000000:  # > 50M CLP
                priorities.append("optimizacion_fiscal")
            
            # Prioridad basada en productos
            if business_data.get('total_products', 0) > 10:
                priorities.append("catalogo_productos")
                
            profile.business_priorities = priorities
            
        except Exception as e:
            print(f"Error identificando prioridades: {e}")
    
    async def _update_recent_activities(self, profile: UserLearningProfile, user_id: str, company_id: str):
        """Actualizar actividades recientes del usuario"""
        if not self.postgres_service:
            return
            
        try:
            # Obtener documentos recientes (usar método alternativo si get_recent_documents no existe)
            if hasattr(self.postgres_service, 'get_recent_documents'):
                recent_docs = await self.postgres_service.get_recent_documents(company_id, limit=5)
            else:
                # Usar método alternativo o crear datos de ejemplo
                recent_docs = []
            
            activities = []
            for doc in recent_docs:
                activities.append({
                    "type": "document_created",
                    "document_type": doc.get('document_type'),
                    "amount": doc.get('total_amount'),
                    "date": doc.get('issue_date'),
                    "relevance": "high" if doc.get('total_amount', 0) > 1000000 else "medium"
                })
            
            profile.recent_activities = activities[-10:]  # Mantener solo últimas 10
            
        except Exception as e:
            print(f"Error actualizando actividades: {e}")
    
    def build_adaptive_prompt(self, base_prompt: str, profile: UserLearningProfile, query_context: str) -> str:
        """Construir prompt adaptado al perfil del usuario"""
        
        # Adaptar según nivel técnico
        technical_instruction = {
            "basico": "Explica de manera simple y paso a paso, evita términos técnicos complejos.",
            "intermedio": "Proporciona explicaciones claras con algunos detalles técnicos relevantes.",
            "avanzado": "Incluye detalles técnicos, opciones avanzadas y mejores prácticas."
        }
        
        # Adaptar según temas frecuentes
        topic_focus = ""
        if profile.frequent_topics:
            main_topic = max(profile.frequent_topics.items(), key=lambda x: x[1])[0]
            topic_focus = f"El usuario frecuentemente consulta sobre: {main_topic}. "
        
        # Adaptar según prioridades empresariales
        business_context = ""
        if profile.business_priorities:
            business_context = f"Prioridades empresariales: {', '.join(profile.business_priorities)}. "
        
        # Incluir actividades recientes
        recent_context = ""
        if profile.recent_activities:
            recent_activity = profile.recent_activities[0]  # Más reciente
            recent_context = f"Actividad reciente: {recent_activity['type']} - {recent_activity.get('relevance', 'medium')} relevancia. "
        
        adaptive_prompt = f"""
{base_prompt}

PERFIL ADAPTATIVO DEL USUARIO:
- Nivel técnico: {profile.technical_level}
- Interacciones: {profile.interaction_count}
- {topic_focus}
- {business_context}
- {recent_context}

INSTRUCCIÓN ADAPTADA: {technical_instruction[profile.technical_level]}

Personaliza tu respuesta considerando este perfil específico del usuario.
        """.strip()
        
        return adaptive_prompt
    
    async def record_response_quality(self, user_id: str, company_id: str, quality_score: float, user_feedback: Optional[str] = None):
        """Registrar calidad de respuesta para aprendizaje futuro"""
        profile_key = f"{user_id}_{company_id}"
        if profile_key in self.user_profiles:
            profile = self.user_profiles[profile_key]
            profile.response_ratings.append(quality_score)
            
            # Mantener solo últimas 20 calificaciones
            if len(profile.response_ratings) > 20:
                profile.response_ratings = profile.response_ratings[-20:]
            
            # Ajustar estilo de respuesta basado en feedback
            if user_feedback:
                await self._adjust_response_style(profile, user_feedback)
    
    async def _adjust_response_style(self, profile: UserLearningProfile, feedback: str):
        """Ajustar estilo de respuesta basado en feedback del usuario"""
        feedback_lower = feedback.lower()
        
        if any(word in feedback_lower for word in ["muy técnico", "complicado", "no entiendo"]):
            if profile.technical_level == "avanzado":
                profile.technical_level = "intermedio"
            elif profile.technical_level == "intermedio":
                profile.technical_level = "basico"
        
        elif any(word in feedback_lower for word in ["más detalle", "técnico", "profundizar"]):
            if profile.technical_level == "basico":
                profile.technical_level = "intermedio"
            elif profile.technical_level == "intermedio":
                profile.technical_level = "avanzado"
    
    def get_learning_insights(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Obtener insights del aprendizaje para análisis"""
        profile_key = f"{user_id}_{company_id}"
        if profile_key not in self.user_profiles:
            return {"status": "no_data"}
        
        profile = self.user_profiles[profile_key]
        
        avg_rating = sum(profile.response_ratings) / len(profile.response_ratings) if profile.response_ratings else 0
        
        return {
            "status": "active",
            "interaction_count": profile.interaction_count,
            "technical_level": profile.technical_level,
            "frequent_topics": profile.frequent_topics,
            "business_priorities": profile.business_priorities,
            "avg_response_rating": round(avg_rating, 2),
            "learning_progress": "improving" if avg_rating > 0.7 else "needs_attention"
        }
    
    async def export_learning_data(self) -> Dict[str, Any]:
        """Exportar datos de aprendizaje para análisis o backup"""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "total_users": len(self.user_profiles),
            "profiles": {}
        }
        
        for profile_key, profile in self.user_profiles.items():
            export_data["profiles"][profile_key] = {
                "user_id": profile.user_id,
                "company_id": profile.company_id,
                "interaction_count": profile.interaction_count,
                "technical_level": profile.technical_level,
                "frequent_topics": profile.frequent_topics,
                "business_priorities": profile.business_priorities,
                "avg_rating": sum(profile.response_ratings) / len(profile.response_ratings) if profile.response_ratings else 0
            }
        
        return export_data
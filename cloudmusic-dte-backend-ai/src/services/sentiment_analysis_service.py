"""
Servicio de Análisis de Sentimientos - Inteligencia emocional adaptativa para respuestas personalizadas
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

import redis.asyncio as aioredis
from loguru import logger


class SentimentType(Enum):
    """Tipos de sentimiento"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class EmotionType(Enum):
    """Tipos de emoción específica"""
    JOY = "joy"
    SATISFACTION = "satisfaction"
    CONFIDENCE = "confidence"
    FRUSTRATION = "frustration"
    CONFUSION = "confusion"
    ANGER = "anger"
    ANXIETY = "anxiety"
    CURIOSITY = "curiosity"


class UrgencyLevel(Enum):
    """Niveles de urgencia"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SentimentAnalysis:
    """Análisis de sentimiento"""
    message_id: str
    user_id: str
    company_id: str
    original_message: str
    sentiment_type: SentimentType
    confidence_score: float
    detected_emotions: List[EmotionType]
    urgency_level: UrgencyLevel
    tone_indicators: List[str]
    escalation_needed: bool
    suggested_response_tone: str
    analyzed_at: datetime
    metadata: Dict[str, Any]


class SentimentAnalysisService:
    """Servicio de análisis de sentimientos"""
    
    def __init__(self, redis_url: str = None):
        # Usar configuración del .env si está disponible
        import os
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.analysis_ttl = 30 * 24 * 3600  # 30 días
        
        # Diccionarios de palabras clave en español para CloudMusic
        self.sentiment_keywords = {
            SentimentType.VERY_POSITIVE: [
                "excelente", "perfecto", "increíble", "fantástico", "maravilloso",
                "genial", "espectacular", "extraordinario", "brillante", "excepcional",
                "amor", "encanta", "fascina", "impresiona", "supera expectativas"
            ],
            SentimentType.POSITIVE: [
                "bueno", "bien", "correcto", "útil", "funciona", "gracias", "agradezco",
                "satisfecho", "contento", "alegre", "positivo", "recomiendo",
                "me gusta", "interesante", "práctico", "eficiente", "rápido"
            ],
            SentimentType.NEGATIVE: [
                "malo", "mal", "problema", "error", "falla", "no funciona", "defecto",
                "molesto", "decepcionado", "insatisfecho", "preocupado", "complicado",
                "difícil", "lento", "confuso", "incorrecto", "inútil"
            ],
            SentimentType.VERY_NEGATIVE: [
                "horrible", "pésimo", "terrible", "desastre", "odio", "detesto",
                "furioso", "iracundo", "indignado", "intolerable", "inaceptable",
                "estafa", "fraude", "vergonzoso", "patético", "incompetente"
            ]
        }
        
        self.emotion_keywords = {
            EmotionType.JOY: ["feliz", "alegre", "contento", "emocionado", "eufórico"],
            EmotionType.SATISFACTION: ["satisfecho", "cumple", "expectativas", "logrado", "conseguido"],
            EmotionType.CONFIDENCE: ["seguro", "confiado", "certeza", "tranquilo", "convencido"],
            EmotionType.FRUSTRATION: ["frustrado", "molesto", "hartó", "cansado", "agotado"],
            EmotionType.CONFUSION: ["confundido", "no entiendo", "perdido", "complicado", "enredado"],
            EmotionType.ANGER: ["enojado", "furioso", "rabioso", "molesto", "irritado"],
            EmotionType.ANXIETY: ["ansioso", "preocupado", "nervioso", "estresado", "agobiado"],
            EmotionType.CURIOSITY: ["curioso", "interesado", "pregunto", "quiero saber", "me intriga"]
        }
        
        self.urgency_keywords = {
            UrgencyLevel.CRITICAL: [
                "urgente", "inmediato", "ya", "ahora mismo", "crisis", "emergencia",
                "critical", "grave", "serio", "importante", "prioridad"
            ],
            UrgencyLevel.HIGH: [
                "rápido", "pronto", "necesito", "requiero", "ayuda", "problema",
                "asap", "cuanto antes", "hoy", "mañana"
            ],
            UrgencyLevel.MEDIUM: [
                "cuando puedas", "tiempo", "disponible", "consulta", "pregunta"
            ]
        }
        
        # Patrones específicos de CloudMusic
        self.cloudmusic_patterns = {
            "dte_issues": [
                r"dte.*no.*funciona", r"factura.*error", r"sii.*problema",
                r"código.*33.*falla", r"boleta.*39.*error", r"documento.*rechaza"
            ],
            "product_satisfaction": [
                r"cloudmusic.*pro.*excelente", r"producto.*perfecto",
                r"servicio.*bueno", r"consultoría.*útil"
            ],
            "pricing_concerns": [
                r"muy.*caro", r"precio.*alto", r"costo.*elevado",
                r"precio.*mucho", r"costoso"
            ],
            "technical_difficulty": [
                r"no.*entiendo", r"complicado.*usar", r"difícil.*configurar",
                r"ayuda.*técnica", r"soporte.*necesario"
            ]
        }
        
    async def connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await asyncio.wait_for(self.redis_client.ping(), timeout=3.0)
            logger.info(f"🎭 SentimentAnalysisService conectado: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ SentimentAnalysisService sin Redis - modo local: {str(e)[:100]}...")
            self.redis_client = None
            
    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def analyze_message_sentiment(self, message: str, user_id: str, company_id: str) -> SentimentAnalysis:
        """Analizar sentimiento de un mensaje"""
        try:
            message_id = f"{company_id}_{user_id}_{int(datetime.now().timestamp())}"
            
            # Normalizar mensaje
            normalized_message = self._normalize_message(message)
            
            # Detectar sentimiento principal
            sentiment_type, sentiment_confidence = self._detect_sentiment(normalized_message)
            
            # Detectar emociones específicas
            detected_emotions = self._detect_emotions(normalized_message)
            
            # Evaluar urgencia
            urgency_level = self._evaluate_urgency(normalized_message)
            
            # Detectar indicadores de tono
            tone_indicators = self._detect_tone_indicators(normalized_message)
            
            # Determinar si necesita escalación
            escalation_needed = self._needs_escalation(sentiment_type, urgency_level, detected_emotions)
            
            # Sugerir tono de respuesta
            suggested_tone = self._suggest_response_tone(sentiment_type, detected_emotions, urgency_level)
            
            # Análisis específico de CloudMusic
            cloudmusic_context = self._analyze_cloudmusic_context(normalized_message)
            
            analysis = SentimentAnalysis(
                message_id=message_id,
                user_id=user_id,
                company_id=company_id,
                original_message=message,
                sentiment_type=sentiment_type,
                confidence_score=sentiment_confidence,
                detected_emotions=detected_emotions,
                urgency_level=urgency_level,
                tone_indicators=tone_indicators,
                escalation_needed=escalation_needed,
                suggested_response_tone=suggested_tone,
                analyzed_at=datetime.now(),
                metadata={
                    "cloudmusic_context": cloudmusic_context,
                    "message_length": len(message),
                    "exclamation_count": message.count("!"),
                    "question_count": message.count("?"),
                    "caps_ratio": sum(1 for c in message if c.isupper()) / max(len(message), 1)
                }
            )
            
            # Almacenar análisis
            await self._store_sentiment_analysis(analysis)
            
            logger.info(f"🎭 Análisis de sentimiento: {sentiment_type.value} (confianza: {sentiment_confidence:.2f})")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analizando sentimiento: {e}")
            # Retornar análisis neutral por defecto
            return self._create_neutral_analysis(message, user_id, company_id)
            
    def _normalize_message(self, message: str) -> str:
        """Normalizar mensaje para análisis"""
        # Convertir a minúsculas y limpiar
        normalized = message.lower().strip()
        
        # Remover caracteres especiales pero mantener signos de puntuación importantes
        normalized = re.sub(r'[^\w\s\!\?\.\,\;\:]', ' ', normalized)
        
        # Normalizar espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
        
    def _detect_sentiment(self, message: str) -> Tuple[SentimentType, float]:
        """Detectar sentimiento principal del mensaje"""
        sentiment_scores = {sentiment: 0 for sentiment in SentimentType}
        word_count = len(message.split())
        
        # Contar palabras de cada tipo de sentimiento
        for sentiment_type, keywords in self.sentiment_keywords.items():
            for keyword in keywords:
                if keyword in message:
                    # Peso mayor para coincidencias exactas vs parciales
                    weight = 2.0 if f" {keyword} " in f" {message} " else 1.0
                    sentiment_scores[sentiment_type] += weight
                    
        # Análisis de patrones específicos
        if any(pattern in message for pattern in ["no funciona", "no sirve", "mal", "error"]):
            sentiment_scores[SentimentType.NEGATIVE] += 2.0
            
        if any(pattern in message for pattern in ["excelente", "perfecto", "genial"]):
            sentiment_scores[SentimentType.VERY_POSITIVE] += 2.0
            
        # Análisis de signos de puntuación
        exclamations = message.count("!")
        if exclamations >= 2:
            # Múltiples exclamaciones pueden indicar emoción fuerte
            if sentiment_scores[SentimentType.NEGATIVE] > 0:
                sentiment_scores[SentimentType.VERY_NEGATIVE] += 1.0
            elif sentiment_scores[SentimentType.POSITIVE] > 0:
                sentiment_scores[SentimentType.VERY_POSITIVE] += 1.0
                
        # Determinar sentimiento dominante
        max_sentiment = max(sentiment_scores, key=sentiment_scores.get)
        max_score = sentiment_scores[max_sentiment]
        
        # Si no hay palabras clave claras, es neutral
        if max_score == 0:
            return SentimentType.NEUTRAL, 0.5
            
        # Calcular confianza basada en la densidad de palabras clave
        confidence = min(0.95, max_score / max(word_count * 0.3, 1))
        confidence = max(0.3, confidence)  # Mínimo 30% de confianza
        
        return max_sentiment, confidence
        
    def _detect_emotions(self, message: str) -> List[EmotionType]:
        """Detectar emociones específicas"""
        detected = []
        
        for emotion_type, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in message:
                    if emotion_type not in detected:
                        detected.append(emotion_type)
                        
        # Análisis contextual adicional
        if "?" in message:
            if EmotionType.CURIOSITY not in detected:
                detected.append(EmotionType.CURIOSITY)
                
        if "!!!" in message:
            if any(neg in message for neg in ["no", "mal", "error"]):
                if EmotionType.FRUSTRATION not in detected:
                    detected.append(EmotionType.FRUSTRATION)
                    
        return detected
        
    def _evaluate_urgency(self, message: str) -> UrgencyLevel:
        """Evaluar nivel de urgencia"""
        urgency_scores = {level: 0 for level in UrgencyLevel}
        
        # Contar palabras de urgencia
        for urgency_level, keywords in self.urgency_keywords.items():
            for keyword in keywords:
                if keyword in message:
                    urgency_scores[urgency_level] += 1
                    
        # Patrones específicos de urgencia
        if any(pattern in message for pattern in ["ayuda", "problema", "error", "no funciona"]):
            urgency_scores[UrgencyLevel.HIGH] += 1
            
        if any(pattern in message for pattern in ["crisis", "grave", "serio", "importante"]):
            urgency_scores[UrgencyLevel.CRITICAL] += 2
            
        # Determinar nivel máximo
        max_urgency = max(urgency_scores, key=urgency_scores.get)
        return max_urgency if urgency_scores[max_urgency] > 0 else UrgencyLevel.LOW
        
    def _detect_tone_indicators(self, message: str) -> List[str]:
        """Detectar indicadores de tono"""
        indicators = []
        
        # Mayúsculas excesivas
        caps_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        if caps_ratio > 0.3:
            indicators.append("caps_heavy")
            
        # Múltiples signos de puntuación
        if message.count("!") >= 2:
            indicators.append("multiple_exclamations")
            
        if message.count("?") >= 2:
            indicators.append("multiple_questions")
            
        # Longitud del mensaje
        if len(message.split()) > 50:
            indicators.append("detailed_explanation")
        elif len(message.split()) < 5:
            indicators.append("brief_message")
            
        # Formalidad
        if any(formal in message for formal in ["usted", "señor", "señora", "estimado", "cordial"]):
            indicators.append("formal_tone")
        elif any(informal in message for informal in ["hola", "que tal", "oye", "mira"]):
            indicators.append("informal_tone")
            
        return indicators
        
    def _needs_escalation(self, sentiment: SentimentType, urgency: UrgencyLevel, emotions: List[EmotionType]) -> bool:
        """Determinar si necesita escalación"""
        # Escalación por sentimiento muy negativo
        if sentiment == SentimentType.VERY_NEGATIVE:
            return True
            
        # Escalación por urgencia crítica
        if urgency == UrgencyLevel.CRITICAL:
            return True
            
        # Escalación por combinación de factores
        negative_emotions = [EmotionType.ANGER, EmotionType.FRUSTRATION]
        if sentiment == SentimentType.NEGATIVE and any(emotion in emotions for emotion in negative_emotions):
            return True
            
        return False
        
    def _suggest_response_tone(self, sentiment: SentimentType, emotions: List[EmotionType], urgency: UrgencyLevel) -> str:
        """Sugerir tono de respuesta apropiado"""
        # Tono empático para sentimientos negativos
        if sentiment in [SentimentType.NEGATIVE, SentimentType.VERY_NEGATIVE]:
            if EmotionType.FRUSTRATION in emotions or EmotionType.ANGER in emotions:
                return "empático_calmante"
            else:
                return "comprensivo_solucionador"
                
        # Tono profesional para urgencia alta
        if urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]:
            return "profesional_urgente"
            
        # Tono enthusiastic para sentimientos positivos
        if sentiment in [SentimentType.POSITIVE, SentimentType.VERY_POSITIVE]:
            return "positivo_reforzador"
            
        # Tono informativo para curiosidad
        if EmotionType.CURIOSITY in emotions:
            return "informativo_educativo"
            
        # Tono neutral por defecto
        return "neutral_profesional"
        
    def _analyze_cloudmusic_context(self, message: str) -> Dict[str, Any]:
        """Analizar contexto específico de CloudMusic"""
        context = {
            "category": "general",
            "product_mentioned": False,
            "issue_type": None,
            "satisfaction_indicators": []
        }
        
        # Verificar menciones de productos
        products = ["cloudmusic pro", "consultoría dte", "curso facturación", "soporte técnico", "auditoría fiscal"]
        for product in products:
            if product in message:
                context["product_mentioned"] = True
                context["category"] = "product_inquiry"
                break
                
        # Verificar patrones específicos
        for pattern_type, patterns in self.cloudmusic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    context["issue_type"] = pattern_type
                    break
                    
        # Detectar indicadores de satisfacción
        if any(pos in message for pos in ["excelente", "perfecto", "recomiendo", "satisfecho"]):
            context["satisfaction_indicators"].append("positive_feedback")
            
        if any(neg in message for neg in ["caro", "costoso", "complicado", "difícil"]):
            context["satisfaction_indicators"].append("concern_expressed")
            
        return context
        
    async def _store_sentiment_analysis(self, analysis: SentimentAnalysis):
        """Almacenar análisis de sentimiento"""
        try:
            # Solo almacenar si Redis está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - análisis de sentimiento no persistido")
                return
                
            analysis_key = f"sentiment_analysis:{analysis.company_id}:{analysis.user_id}:{analysis.message_id}"
            
            analysis_data = {
                'message_id': analysis.message_id,
                'user_id': analysis.user_id,
                'company_id': analysis.company_id,
                'original_message': analysis.original_message,
                'sentiment_type': analysis.sentiment_type.value,
                'confidence_score': str(analysis.confidence_score),
                'detected_emotions': json.dumps([emotion.value for emotion in analysis.detected_emotions]),
                'urgency_level': str(analysis.urgency_level.value),
                'tone_indicators': json.dumps(analysis.tone_indicators),
                'escalation_needed': str(analysis.escalation_needed),
                'suggested_response_tone': analysis.suggested_response_tone,
                'analyzed_at': analysis.analyzed_at.isoformat(),
                'metadata': json.dumps(analysis.metadata)
            }
            
            await self.redis_client.hset(analysis_key, mapping=analysis_data)
            await self.redis_client.expire(analysis_key, self.analysis_ttl)
            
            # Añadir a histórico del usuario
            user_history_key = f"sentiment_history:{analysis.company_id}:{analysis.user_id}"
            await self.redis_client.lpush(user_history_key, analysis.message_id)
            await self.redis_client.ltrim(user_history_key, 0, 49)  # Mantener últimos 50
            await self.redis_client.expire(user_history_key, self.analysis_ttl)
            
        except Exception as e:
            logger.error(f"❌ Error almacenando análisis de sentimiento: {e}")
            
    def _create_neutral_analysis(self, message: str, user_id: str, company_id: str) -> SentimentAnalysis:
        """Crear análisis neutral por defecto en caso de error"""
        message_id = f"{company_id}_{user_id}_{int(datetime.now().timestamp())}_fallback"
        
        return SentimentAnalysis(
            message_id=message_id,
            user_id=user_id,
            company_id=company_id,
            original_message=message,
            sentiment_type=SentimentType.NEUTRAL,
            confidence_score=0.5,
            detected_emotions=[],
            urgency_level=UrgencyLevel.MEDIUM,
            tone_indicators=[],
            escalation_needed=False,
            suggested_response_tone="neutral_profesional",
            analyzed_at=datetime.now(),
            metadata={"fallback": True}
        )
        
    async def get_user_sentiment_history(self, user_id: str, company_id: str, limit: int = 10) -> List[SentimentAnalysis]:
        """Obtener histórico de sentimientos del usuario"""
        try:
            # Retornar lista vacía si Redis no está disponible
            if not self.redis_client:
                logger.debug("⚠️ Redis no disponible - histórico de sentimientos no disponible")
                return []
                
            user_history_key = f"sentiment_history:{company_id}:{user_id}"
            message_ids = await self.redis_client.lrange(user_history_key, 0, limit - 1)
            
            analyses = []
            for message_id in message_ids:
                analysis_key = f"sentiment_analysis:{company_id}:{user_id}:{message_id}"
                analysis_data = await self.redis_client.hgetall(analysis_key)
                
                if analysis_data:
                    analysis = SentimentAnalysis(
                        message_id=analysis_data['message_id'],
                        user_id=analysis_data['user_id'],
                        company_id=analysis_data['company_id'],
                        original_message=analysis_data['original_message'],
                        sentiment_type=SentimentType(analysis_data['sentiment_type']),
                        confidence_score=float(analysis_data['confidence_score']),
                        detected_emotions=[EmotionType(emotion) for emotion in json.loads(analysis_data['detected_emotions'])],
                        urgency_level=UrgencyLevel(int(analysis_data['urgency_level'])),
                        tone_indicators=json.loads(analysis_data['tone_indicators']),
                        escalation_needed=analysis_data['escalation_needed'].lower() == 'true',
                        suggested_response_tone=analysis_data['suggested_response_tone'],
                        analyzed_at=datetime.fromisoformat(analysis_data['analyzed_at']),
                        metadata=json.loads(analysis_data['metadata'])
                    )
                    analyses.append(analysis)
                    
            return analyses
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo histórico de sentimientos: {e}")
            return []
            
    async def get_sentiment_statistics(self, company_id: str) -> Dict[str, Any]:
        """Obtener estadísticas de sentimientos"""
        try:
            # Retornar estadísticas vacías si Redis no está disponible
            if not self.redis_client:
                return {
                    "total_analyses": 0,
                    "sentiment_distribution": {},
                    "emotion_distribution": {},
                    "urgency_distribution": {},
                    "escalation_rate": 0.0,
                    "analysis_period": "redis_not_available"
                }
                
            pattern = f"sentiment_analysis:{company_id}:*"
            sentiment_counts = defaultdict(int)
            emotion_counts = defaultdict(int)
            urgency_counts = defaultdict(int)
            escalation_count = 0
            total_analyses = 0
            
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                analysis_data = await self.redis_client.hgetall(key)
                if analysis_data:
                    total_analyses += 1
                    sentiment_counts[analysis_data.get('sentiment_type', 'neutral')] += 1
                    
                    emotions = json.loads(analysis_data.get('detected_emotions', '[]'))
                    for emotion in emotions:
                        emotion_counts[emotion] += 1
                        
                    urgency_counts[analysis_data.get('urgency_level', '1')] += 1
                    
                    if analysis_data.get('escalation_needed', 'false').lower() == 'true':
                        escalation_count += 1
                        
            return {
                "total_analyses": total_analyses,
                "sentiment_distribution": dict(sentiment_counts),
                "emotion_distribution": dict(emotion_counts),
                "urgency_distribution": dict(urgency_counts),
                "escalation_rate": escalation_count / max(total_analyses, 1),
                "analysis_period": "last_30_days"
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de sentimientos: {e}")
            return {"error": str(e)}
            
    async def adapt_response_tone(self, base_response: str, sentiment_analysis: SentimentAnalysis) -> str:
        """Adaptar tono de respuesta basado en análisis de sentimiento"""
        try:
            tone = sentiment_analysis.suggested_response_tone
            
            # Aplicar adaptaciones de tono - respuestas directas sin introducciones genéricas
            if tone == "empático_calmante":
                # Respuesta directa sin introducción genérica
                return f"{base_response}"
                
            elif tone == "comprensivo_solucionador":
                # Respuesta directa sin introducción genérica  
                return f"{base_response}"
                
            elif tone == "profesional_urgente":
                # Respuesta directa sin introducción genérica
                return f"{base_response}"
                
            elif tone == "positivo_reforzador":
                # Respuesta más directa sin introducción genial
                return f"{base_response}"
                
            elif tone == "informativo_educativo":
                # Evitar texto repetitivo, respuesta más directa
                return f"{base_response}"
                
            else:  # neutral_profesional
                return f"{base_response}"
                
        except Exception as e:
            logger.error(f"❌ Error adaptando tono de respuesta: {e}")
            return base_response
"""
Ollama Response Processor - Procesamiento y limpieza de respuestas
Maneja limpieza de contenido, análisis de calidad y formateo de respuestas
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger
from pydantic import BaseModel


class OllamaResponse(BaseModel):
    """Respuesta procesada de Ollama"""
    content: str
    model: str
    created_at: datetime
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    quality_score: Optional[float] = None
    cleaned: bool = False


class ResponseQualityMetrics(BaseModel):
    """Métricas de calidad de respuesta"""
    length_score: float  # Score basado en longitud apropiada
    coherence_score: float  # Score de coherencia del contenido
    completeness_score: float  # Score de completitud de respuesta
    professional_score: float  # Score de profesionalismo
    overall_score: float  # Score general


class OllamaResponseProcessor:
    """Procesador especializado de respuestas de Ollama"""
    
    def __init__(self):
        self.min_response_length = 10
        self.max_response_length = 5000
        self.quality_thresholds = {
            "excellent": 0.9,
            "good": 0.7,
            "acceptable": 0.5,
            "poor": 0.3
        }
    
    def process_raw_response(self, raw_response: Dict) -> OllamaResponse:
        """Procesar respuesta raw de Ollama en objeto estructurado"""
        
        try:
            # Extraer contenido principal
            content = raw_response.get("response", "")
            
            # Limpiar contenido
            cleaned_content = self._clean_response_content(content)
            
            # Crear respuesta estructurada
            response = OllamaResponse(
                content=cleaned_content,
                model=raw_response.get("model", "unknown"),
                created_at=datetime.now(),
                done=raw_response.get("done", False),
                total_duration=raw_response.get("total_duration"),
                load_duration=raw_response.get("load_duration"),
                prompt_eval_count=raw_response.get("prompt_eval_count"),
                eval_count=raw_response.get("eval_count"),
                cleaned=True if cleaned_content != content else False
            )
            
            # Calcular score de calidad
            response.quality_score = self._calculate_quality_score(cleaned_content)
            
            logger.debug(f"📝 Respuesta procesada: {len(cleaned_content)} chars, quality: {response.quality_score:.2f}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error procesando respuesta: {e}")
            # Respuesta de fallback
            return OllamaResponse(
                content=raw_response.get("response", "Error procesando respuesta"),
                model=raw_response.get("model", "unknown"),
                created_at=datetime.now(),
                done=True,
                quality_score=0.0,
                cleaned=False
            )
    
    def _clean_response_content(self, content: str) -> str:
        """Limpiar contenido de la respuesta de artefactos y formato"""
        
        if not content or not isinstance(content, str):
            return ""
        
        # Proceso de limpieza paso a paso
        cleaned = content
        
        # 1. Remover caracteres de control y espacios extra
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Múltiples espacios a uno
        
        # 2. Limpiar marcadores de sistema o debug
        system_markers = [
            r'^\[SYSTEM\].*?\[/SYSTEM\]',
            r'^\[DEBUG\].*?\[/DEBUG\]',
            r'^\[LOG\].*?\[/LOG\]',
            r'^DEBUG:.*?\n',
            r'^INFO:.*?\n',
            r'^ERROR:.*?\n'
        ]
        
        for pattern in system_markers:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
        
        # 3. Remover repeticiones excesivas de caracteres
        cleaned = re.sub(r'(.)\1{4,}', r'\1\1\1', cleaned)  # Max 3 repeticiones
        
        # 4. Limpiar saltos de línea excesivos
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 5. Remover espacios al inicio y final de líneas
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(line for line in lines if line)
        
        # 6. Asegurar punto final en respuestas completas
        cleaned = cleaned.strip()
        if cleaned and len(cleaned) > 20 and not cleaned.endswith(('.', '!', '?', ':')):
            # Solo agregar punto si parece una oración completa
            if any(word in cleaned.lower().split()[-5:] for word in ['el', 'la', 'los', 'las', 'un', 'una']):
                cleaned += '.'
        
        # 7. Capitalizar primera letra
        if cleaned and len(cleaned) > 0:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        logger.debug(f"🧹 Contenido limpiado: {len(content)} → {len(cleaned)} chars")
        
        return cleaned
    
    def _calculate_quality_score(self, content: str) -> float:
        """Calcular score de calidad de la respuesta"""
        
        if not content:
            return 0.0
        
        metrics = self._analyze_response_quality(content)
        
        # Score ponderado
        weights = {
            "length_score": 0.2,
            "coherence_score": 0.3,
            "completeness_score": 0.25,
            "professional_score": 0.25
        }
        
        overall_score = sum(
            (getattr(metrics, metric) or 0.0) * weight 
            for metric, weight in weights.items()
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _analyze_response_quality(self, content: str) -> ResponseQualityMetrics:
        """Analizar métricas detalladas de calidad"""
        
        # Métricas básicas
        length = len(content)
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))
        
        # 1. Score de longitud (respuestas ni muy cortas ni muy largas)
        if 50 <= length <= 1000:
            length_score = 1.0
        elif 20 <= length < 50 or 1000 < length <= 2000:
            length_score = 0.7
        elif 10 <= length < 20 or 2000 < length <= 3000:
            length_score = 0.4
        else:
            length_score = 0.1
        
        # 2. Score de coherencia (presencia de conectores, estructura)
        coherence_indicators = [
            'por lo tanto', 'además', 'sin embargo', 'por ejemplo', 'en primer lugar',
            'finalmente', 'en resumen', 'esto significa', 'es decir', 'por otra parte'
        ]
        coherence_count = sum(1 for indicator in coherence_indicators if indicator in content.lower())
        coherence_score = min(1.0, coherence_count / 3)  # Max score con 3+ conectores
        
        # 3. Score de completitud (estructura de respuesta completa)
        completeness_indicators = [
            content.strip().endswith(('.', '!', '?')),  # Termina correctamente
            sentence_count >= 2,  # Al menos 2 oraciones
            word_count >= 15,  # Al menos 15 palabras
            not content.lower().startswith('no sé'),  # No es respuesta evasiva
            'cloudmusic' in content.lower() or 'sii' in content.lower()  # Contexto relevante
        ]
        completeness_score = sum(completeness_indicators) / len(completeness_indicators)
        
        # 4. Score de profesionalismo (vocabulario técnico, formato)
        professional_indicators = [
            any(term in content.lower() for term in ['dte', 'factura', 'iva', 'sii', 'tributario']),
            not any(term in content.lower() for term in ['jaja', 'jeje', 'lol', 'xd']),
            bool(re.search(r'\d+%|\$\d+|\d+\.\d+', content)),  # Números/porcentajes
            len(re.findall(r'[A-Z]', content)) >= 3,  # Uso apropiado de mayúsculas
            not bool(re.search(r'(.)\1{3,}', content))  # Sin repeticiones excesivas
        ]
        professional_score = sum(professional_indicators) / len(professional_indicators)
        
        # Calcular score general
        overall_score = (length_score * 0.2 + coherence_score * 0.3 + 
                        completeness_score * 0.25 + professional_score * 0.25)
        
        return ResponseQualityMetrics(
            length_score=length_score,
            coherence_score=coherence_score,
            completeness_score=completeness_score,
            professional_score=professional_score,
            overall_score=overall_score
        )
    
    def validate_response(self, response: OllamaResponse) -> Dict[str, Any]:
        """Validar calidad y completitud de respuesta"""
        
        validation_result = {
            "is_valid": True,
            "quality_level": "unknown",
            "issues": [],
            "suggestions": [],
            "metrics": None
        }
        
        try:
            content = response.content
            
            # Validaciones básicas
            if not content or len(content.strip()) < self.min_response_length:
                validation_result["is_valid"] = False
                validation_result["issues"].append("Respuesta muy corta")
                validation_result["suggestions"].append("Generar respuesta más detallada")
            
            if len(content) > self.max_response_length:
                validation_result["issues"].append("Respuesta muy larga")
                validation_result["suggestions"].append("Considerar dividir en partes")
            
            # Análisis de calidad
            if response.quality_score is not None:
                validation_result["metrics"] = self._analyze_response_quality(content)
                
                # Determinar nivel de calidad
                if response.quality_score >= self.quality_thresholds["excellent"]:
                    validation_result["quality_level"] = "excellent"
                elif response.quality_score >= self.quality_thresholds["good"]:
                    validation_result["quality_level"] = "good"
                elif response.quality_score >= self.quality_thresholds["acceptable"]:
                    validation_result["quality_level"] = "acceptable"
                else:
                    validation_result["quality_level"] = "poor"
                    validation_result["is_valid"] = False
                    validation_result["suggestions"].append("Regenerar respuesta con mejor prompt")
            
            # Validaciones específicas de contenido
            content_lower = content.lower()
            
            # Detectar respuestas evasivas
            evasive_patterns = ["no sé", "no estoy seguro", "no puedo", "disculpa pero"]
            if any(pattern in content_lower for pattern in evasive_patterns):
                validation_result["issues"].append("Respuesta evasiva detectada")
                validation_result["suggestions"].append("Proporcionar información más específica")
            
            # Detectar repeticiones problemáticas
            if re.search(r'(.{10,})\1{2,}', content):
                validation_result["issues"].append("Repetición excesiva detectada")
                validation_result["suggestions"].append("Limpiar contenido repetitivo")
            
            # Log del resultado
            logger.debug(f"✅ Validación: {validation_result['quality_level']} ({len(validation_result['issues'])} issues)")
            
        except Exception as e:
            logger.error(f"❌ Error en validación: {e}")
            validation_result["is_valid"] = False
            validation_result["issues"].append(f"Error de validación: {str(e)}")
        
        return validation_result
    
    def format_response_for_display(self, response: OllamaResponse, include_metadata: bool = False) -> str:
        """Formatear respuesta para mostrar al usuario"""
        
        formatted_content = response.content
        
        # Mejorar formato visual
        if formatted_content:
            # Agregar espacios después de puntos si no los hay
            formatted_content = re.sub(r'\.([A-Z])', r'. \1', formatted_content)
            
            # Mejorar formato de listas
            formatted_content = re.sub(r'^\s*-\s*', '• ', formatted_content, flags=re.MULTILINE)
            formatted_content = re.sub(r'^\s*\d+\.\s*', lambda m: f"{m.group().strip()} ", formatted_content, flags=re.MULTILINE)
        
        # Agregar metadata si se solicita
        if include_metadata and response.quality_score:
            metadata_lines = [
                "",
                "---",
                f"📊 Calidad: {response.quality_score:.2f}/1.0",
                f"🤖 Modelo: {response.model}",
                f"⏱️ Generado: {response.created_at.strftime('%H:%M:%S')}"
            ]
            
            if response.total_duration:
                duration_seconds = response.total_duration / 1_000_000_000
                metadata_lines.append(f"⚡ Tiempo: {duration_seconds:.1f}s")
            
            formatted_content += "\n".join(metadata_lines)
        
        return formatted_content
    
    # === UTILIDADES ESPECIALIZADAS ===
    
    def extract_calculations_from_response(self, content: str) -> List[Dict]:
        """Extraer cálculos matemáticos de la respuesta"""
        
        calculations = []
        
        # Patrones para detectar cálculos
        calc_patterns = [
            r'(\$?[\d,]+(?:\.\d+)?)\s*[×x\*]\s*(\d+(?:\.\d+)?%?)',  # Multiplicación
            r'(\$?[\d,]+(?:\.\d+)?)\s*[÷/]\s*(\d+(?:\.\d+)?)',      # División
            r'(\$?[\d,]+(?:\.\d+)?)\s*[+-]\s*(\$?[\d,]+(?:\.\d+)?)', # Suma/resta
            r'IVA\s*=\s*(\$?[\d,]+(?:\.\d+)?)',                     # IVA específico
            r'Neto\s*=\s*(\$?[\d,]+(?:\.\d+)?)',                   # Neto específico
            r'Total\s*=\s*(\$?[\d,]+(?:\.\d+)?)'                   # Total específico
        ]
        
        for i, pattern in enumerate(calc_patterns):
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                calculations.append({
                    "type": ["multiplication", "division", "addition_subtraction", "iva", "net", "total"][i],
                    "match": match.group(),
                    "position": match.span(),
                    "values": match.groups()
                })
        
        logger.debug(f"🧮 Extraídos {len(calculations)} cálculos")
        return calculations
    
    def extract_dte_references(self, content: str) -> List[str]:
        """Extraer referencias a DTE y normativas"""
        
        dte_terms = [
            "factura electrónica", "boleta electrónica", "nota de crédito", 
            "nota de débito", "guía de despacho", "sii", "dte", "xml",
            "folio", "caf", "certificado digital", "timbre electrónico"
        ]
        
        found_terms = []
        content_lower = content.lower()
        
        for term in dte_terms:
            if term in content_lower:
                found_terms.append(term)
        
        return list(set(found_terms))  # Remover duplicados
    
    def get_response_summary(self, response: OllamaResponse) -> Dict:
        """Obtener resumen de la respuesta"""
        
        content = response.content
        
        summary = {
            "length": len(content),
            "word_count": len(content.split()),
            "sentence_count": len(re.findall(r'[.!?]+', content)),
            "quality_score": response.quality_score,
            "has_calculations": bool(self.extract_calculations_from_response(content)),
            "dte_references": self.extract_dte_references(content),
            "is_complete": content.strip().endswith(('.', '!', '?')),
            "processing_time": response.total_duration / 1_000_000_000 if response.total_duration else None
        }
        
        return summary
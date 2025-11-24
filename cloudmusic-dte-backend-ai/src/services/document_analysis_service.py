"""
Servicio de Análisis IA de Documentos DTE
Análisis inteligente de facturas, boletas y otros DTE usando IA local
"""

import asyncio
import json
from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
from uuid import uuid4

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from .ollama_client import OllamaClient, OllamaConfig
from .database_service import DatabaseService
try:
    from ..contracts.document_types import DocumentAnalysis, AnalysisType, RiskLevel, DocumentValidation
except ImportError:
    from src.contracts.document_types import DocumentAnalysis, AnalysisType, RiskLevel, DocumentValidation


class DocumentAnalysisService:
    """Servicio de análisis IA para documentos DTE"""
    
    def __init__(self, db: AsyncIOMotorDatabase, ollama_config: Optional[OllamaConfig] = None):
        self.db = db
        self.ollama_config = ollama_config or OllamaConfig()
        self.db_service = DatabaseService(db)
        
        # Prompts especializados por tipo de análisis
        self.analysis_prompts = {
            "fraud_detection": """
Analiza este documento DTE chileno para detectar posibles fraudes o anomalías:

Revisa específicamente:
1. Coherencia entre montos totales y subtotales
2. Validez de RUT emisor y receptor
3. Fechas lógicas de emisión vs vencimiento
4. Códigos de productos/servicios válidos
5. Cálculos de IVA y otros impuestos
6. Patrones inusuales en cantidades o precios

Documento: {document_data}

Responde en JSON con:
- "anomalies": lista de anomalías detectadas
- "risk_score": puntuación 0.0-1.0 (0=sin riesgo, 1=muy riesgoso)
- "recommendations": acciones recomendadas
- "confidence": confianza del análisis 0.0-1.0
""",
            
            "compliance_check": """
Verifica el cumplimiento normativo SII de este documento DTE:

Valida:
1. Formato correcto según normativa vigente
2. Campos obligatorios presentes
3. Rangos de folios válidos
4. Certificación digital válida
5. Esquemas XML conformes
6. Plazos de emisión cumplidos

Documento: {document_data}

Responde en JSON con:
- "compliance_issues": lista de incumplimientos
- "severity": "low", "medium", "high", "critical"
- "required_actions": acciones obligatorias
- "optional_improvements": mejoras sugeridas
""",
            
            "financial_analysis": """
Realiza análisis financiero de este documento DTE:

Analiza:
1. Consistencia en precios unitarios
2. Márgenes y descuentos aplicados
3. Impacto tributario (IVA, retenciones)
4. Categorización contable sugerida
5. Flujo de caja proyectado
6. Indicadores financieros relevantes

Documento: {document_data}

Responde en JSON con:
- "financial_metrics": métricas calculadas
- "tax_implications": implicancias tributarias
- "accounting_suggestions": sugerencias contables
- "risk_factors": factores de riesgo financiero
""",
            
            "pattern_analysis": """
Identifica patrones en este documento DTE:

Busca:
1. Patrones de consumo del cliente
2. Estacionalidad en productos/servicios
3. Frecuencia de transacciones
4. Comportamientos atípicos
5. Tendencias de crecimiento
6. Comparación con promedios históricos

Documento: {document_data}

Responde en JSON con:
- "patterns_found": patrones identificados
- "trends": tendencias observadas
- "seasonality": análisis estacional
- "predictions": predicciones futuras
"""
        }
    
    async def analyze_document(
        self,
        document_data: Dict,
        analysis_type: AnalysisType,
        user_id: str,
        company_id: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> DocumentAnalysis:
        """Realizar análisis completo de documento"""
        
        analysis_id = str(uuid4())
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Starting {analysis_type} analysis for document {document_id}")
            
            # Generar análisis con IA
            analysis_result = await self._perform_ai_analysis(
                document_data, analysis_type
            )
            
            # Determinar nivel de riesgo
            risk_level = self._calculate_risk_level(analysis_result, analysis_type)
            
            # Crear objeto de análisis
            analysis = DocumentAnalysis(
                analysis_id=analysis_id,
                document_id=document_id or str(uuid4()),
                analysis_type=analysis_type,
                user_id=user_id,
                company_id=company_id,
                created_at=start_time,
                completed_at=datetime.now(timezone.utc),
                risk_level=risk_level,
                confidence_score=analysis_result.get("confidence", 0.8),
                analysis_results=analysis_result,
                metadata=metadata or {}
            )
            
            # Guardar análisis en BD
            await self.db_service.save_document_analysis(analysis)
            
            # Log de auditoría
            await self.db_service.log_audit_event(
                user_id=user_id,
                action=f"document_analysis_{analysis_type}",
                resource=f"document:{document_id}",
                metadata={
                    "analysis_id": analysis_id,
                    "risk_level": risk_level,
                    "confidence": analysis_result.get("confidence", 0.8)
                }
            )
            
            logger.info(f"Completed analysis {analysis_id} with risk level {risk_level}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            
            # Análisis de fallback
            fallback_analysis = DocumentAnalysis(
                analysis_id=analysis_id,
                document_id=document_id or str(uuid4()),
                analysis_type=analysis_type,
                user_id=user_id,
                company_id=company_id,
                created_at=start_time,
                completed_at=datetime.now(timezone.utc),
                risk_level=RiskLevel.MEDIUM,
                confidence_score=0.3,
                analysis_results={
                    "error": str(e),
                    "status": "failed",
                    "recommendations": ["Revisión manual requerida"]
                },
                metadata=metadata or {}
            )
            
            await self.db_service.save_document_analysis(fallback_analysis)
            return fallback_analysis
    
    async def _perform_ai_analysis(
        self,
        document_data: Dict,
        analysis_type: AnalysisType
    ) -> Dict:
        """Realizar análisis con IA usando prompt especializado"""
        
        # Obtener prompt específico
        prompt_template = self.analysis_prompts.get(
            analysis_type,
            self.analysis_prompts["fraud_detection"]
        )
        
        # Preparar datos del documento (limitar tamaño)
        doc_json = json.dumps(document_data, indent=2)
        if len(doc_json) > 3000:  # Limitar contexto
            doc_json = doc_json[:3000] + "... [documento truncado]"
        
        prompt = prompt_template.format(document_data=doc_json)
        
        # Generar análisis con Ollama
        async with OllamaClient(self.ollama_config) as ollama:
            response = await ollama.analyze_document_content(
                document_data, analysis_type
            )
        
        return response
    
    def _calculate_risk_level(self, analysis_result: Dict, analysis_type: AnalysisType) -> RiskLevel:
        """Calcular nivel de riesgo basado en resultados"""
        
        risk_score = analysis_result.get("risk_score", 0.5)
        confidence = analysis_result.get("confidence", 0.5)
        
        # Ajustar por confianza del análisis
        adjusted_risk = risk_score * confidence
        
        # Mapear a niveles discretos
        if adjusted_risk >= 0.8:
            return RiskLevel.CRITICAL
        elif adjusted_risk >= 0.6:
            return RiskLevel.HIGH
        elif adjusted_risk >= 0.4:
            return RiskLevel.MEDIUM
        elif adjusted_risk >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    async def batch_analyze_documents(
        self,
        documents: List[Dict],
        analysis_type: AnalysisType,
        user_id: str,
        company_id: str,
        batch_id: Optional[str] = None
    ) -> List[DocumentAnalysis]:
        """Analizar múltiples documentos en lote"""
        
        batch_id = batch_id or str(uuid4())
        results = []
        
        logger.info(f"Starting batch analysis {batch_id} for {len(documents)} documents")
        
        # Procesar documentos en paralelo (limitado)
        semaphore = asyncio.Semaphore(5)  # Máximo 5 análisis simultáneos
        
        async def analyze_single(doc_data: Dict, index: int):
            async with semaphore:
                return await self.analyze_document(
                    document_data=doc_data,
                    analysis_type=analysis_type,
                    user_id=user_id,
                    company_id=company_id,
                    document_id=doc_data.get("id", f"{batch_id}_{index}"),
                    metadata={"batch_id": batch_id, "batch_index": index}
                )
        
        tasks = [
            analyze_single(doc, i) for i, doc in enumerate(documents)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar errores
        valid_results = [
            r for r in results if isinstance(r, DocumentAnalysis)
        ]
        
        logger.info(f"Completed batch analysis {batch_id}: {len(valid_results)}/{len(documents)} successful")
        return valid_results
    
    async def get_document_analysis_history(
        self,
        document_id: str,
        user_id: str,
        limit: int = 10
    ) -> List[DocumentAnalysis]:
        """Obtener historial de análisis de un documento"""
        
        analyses = await self.db_service.get_document_analyses_by_document(
            document_id, limit
        )
        
        # Filtrar por usuario si no es admin
        # TODO: Implementar lógica de permisos
        return analyses
    
    async def validate_document_structure(
        self,
        document_data: Dict,
        document_type: str
    ) -> DocumentValidation:
        """Validar estructura básica del documento"""
        
        validation = DocumentValidation(
            is_valid=True,
            errors=[],
            warnings=[],
            document_type=document_type,
            validated_at=datetime.now(timezone.utc)
        )
        
        # Validaciones básicas para DTE
        required_fields = {
            "factura": ["RUTEmisor", "RUTRecep", "FchEmis", "MntTotal"],
            "boleta": ["RUTEmisor", "FchEmis", "MntTotal"],
            "nota_credito": ["RUTEmisor", "RUTRecep", "FchEmis", "MntTotal"],
            "nota_debito": ["RUTEmisor", "RUTRecep", "FchEmis", "MntTotal"]
        }
        
        fields_to_check = required_fields.get(document_type, [])
        
        for field in fields_to_check:
            if field not in document_data:
                validation.errors.append(f"Campo obligatorio faltante: {field}")
                validation.is_valid = False
        
        # Validaciones adicionales
        if "RUTEmisor" in document_data:
            if not self._validate_rut(document_data["RUTEmisor"]):
                validation.errors.append("RUT Emisor inválido")
                validation.is_valid = False
        
        if "RUTRecep" in document_data:
            if not self._validate_rut(document_data["RUTRecep"]):
                validation.warnings.append("RUT Receptor podría ser inválido")
        
        if "MntTotal" in document_data:
            try:
                monto = float(document_data["MntTotal"])
                if monto <= 0:
                    validation.errors.append("Monto total debe ser positivo")
                    validation.is_valid = False
            except (ValueError, TypeError):
                validation.errors.append("Monto total debe ser numérico")
                validation.is_valid = False
        
        return validation
    
    def _validate_rut(self, rut: str) -> bool:
        """Validar formato y dígito verificador de RUT chileno"""
        try:
            # Limpiar RUT
            rut = str(rut).replace(".", "").replace("-", "").upper()
            
            if len(rut) < 2:
                return False
            
            # Separar número y dígito verificador
            rut_number = rut[:-1]
            dv = rut[-1]
            
            # Validar que el número sea entero
            if not rut_number.isdigit():
                return False
            
            # Calcular dígito verificador
            suma = 0
            multiplicador = 2
            
            for digit in reversed(rut_number):
                suma += int(digit) * multiplicador
                multiplicador += 1
                if multiplicador > 7:
                    multiplicador = 2
            
            resto = suma % 11
            dv_calculado = 11 - resto
            
            if dv_calculado == 11:
                dv_calculado = "0"
            elif dv_calculado == 10:
                dv_calculado = "K"
            else:
                dv_calculado = str(dv_calculado)
            
            return dv == dv_calculado
            
        except Exception:
            return False
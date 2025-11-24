"""
Rutas API para Análisis de Documentos IA
Endpoints para análisis inteligente de documentos DTE
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from pydantic import BaseModel

from ..services import DocumentAnalysisService
from ..contracts.document_types import (
    DocumentAnalysis, AnalysisType, RiskLevel, DocumentValidation
)
from ..core.dependencies import get_document_analysis_service, get_current_user
from ..core.responses import APIResponse


router = APIRouter(prefix="/analysis", tags=["Análisis de Documentos"])


# === REQUEST/RESPONSE MODELS ===

class AnalysisRequest(BaseModel):
    """Solicitud de análisis de documento"""
    document_data: Dict[str, Any]
    analysis_type: AnalysisType
    document_id: Optional[str] = None
    metadata: Optional[Dict] = None


class BatchAnalysisRequest(BaseModel):
    """Solicitud de análisis en lote"""
    documents: List[Dict[str, Any]]
    analysis_type: AnalysisType
    batch_id: Optional[str] = None


class ValidationRequest(BaseModel):
    """Solicitud de validación de documento"""
    document_data: Dict[str, Any]
    document_type: str


class AnalysisResponse(BaseModel):
    """Respuesta de análisis"""
    analysis_id: str
    document_id: str
    analysis_type: str
    risk_level: str
    confidence_score: float
    created_at: str
    completed_at: str
    analysis_results: Dict[str, Any]


class ValidationResponse(BaseModel):
    """Respuesta de validación"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    document_type: str
    validated_at: str


# === ENDPOINTS ===

@router.post("/analyze", response_model=APIResponse[AnalysisResponse])
async def analyze_document(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    analysis_service: DocumentAnalysisService = Depends(get_document_analysis_service),
    current_user: Dict = Depends(get_current_user)
):
    """Analizar documento individual con IA"""
    try:
        analysis = await analysis_service.analyze_document(
            document_data=request.document_data,
            analysis_type=request.analysis_type,
            user_id=current_user["user_id"],
            company_id=current_user["company_id"],
            document_id=request.document_id,
            metadata=request.metadata
        )
        
        response_data = AnalysisResponse(
            analysis_id=analysis.analysis_id,
            document_id=analysis.document_id,
            analysis_type=analysis.analysis_type,
            risk_level=analysis.risk_level,
            confidence_score=analysis.confidence_score,
            created_at=analysis.created_at.isoformat(),
            completed_at=analysis.completed_at.isoformat() if analysis.completed_at else "",
            analysis_results=analysis.analysis_results
        )
        
        # Publicar resultado via WebSocket en background
        background_tasks.add_task(
            _publish_analysis_result,
            analysis,
            current_user["user_id"]
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="Análisis completado exitosamente"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-analyze", response_model=APIResponse[List[AnalysisResponse]])
async def batch_analyze_documents(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    analysis_service: DocumentAnalysisService = Depends(get_document_analysis_service),
    current_user: Dict = Depends(get_current_user)
):
    """Analizar múltiples documentos en lote"""
    try:
        if len(request.documents) > 50:
            raise HTTPException(
                status_code=400,
                detail="Máximo 50 documentos por lote"
            )
        
        analyses = await analysis_service.batch_analyze_documents(
            documents=request.documents,
            analysis_type=request.analysis_type,
            user_id=current_user["user_id"],
            company_id=current_user["company_id"],
            batch_id=request.batch_id
        )
        
        response_data = [
            AnalysisResponse(
                analysis_id=analysis.analysis_id,
                document_id=analysis.document_id,
                analysis_type=analysis.analysis_type,
                risk_level=analysis.risk_level,
                confidence_score=analysis.confidence_score,
                created_at=analysis.created_at.isoformat(),
                completed_at=analysis.completed_at.isoformat() if analysis.completed_at else "",
                analysis_results=analysis.analysis_results
            )
            for analysis in analyses
        ]
        
        # Publicar resultados del lote
        background_tasks.add_task(
            _publish_batch_results,
            analyses,
            current_user["user_id"],
            request.batch_id
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"Análisis en lote completado: {len(response_data)} documentos procesados"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=APIResponse[ValidationResponse])
async def validate_document(
    request: ValidationRequest,
    analysis_service: DocumentAnalysisService = Depends(get_document_analysis_service),
    current_user: Dict = Depends(get_current_user)
):
    """Validar estructura y contenido básico de documento"""
    try:
        validation = await analysis_service.validate_document_structure(
            document_data=request.document_data,
            document_type=request.document_type
        )
        
        response_data = ValidationResponse(
            is_valid=validation.is_valid,
            errors=validation.errors,
            warnings=validation.warnings,
            document_type=validation.document_type,
            validated_at=validation.validated_at.isoformat()
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="Validación completada"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/history", response_model=APIResponse[List[AnalysisResponse]])
async def get_document_analysis_history(
    document_id: str,
    limit: int = 10,
    analysis_service: DocumentAnalysisService = Depends(get_document_analysis_service),
    current_user: Dict = Depends(get_current_user)
):
    """Obtener historial de análisis de un documento"""
    try:
        analyses = await analysis_service.get_document_analysis_history(
            document_id=document_id,
            user_id=current_user["user_id"],
            limit=limit
        )
        
        response_data = [
            AnalysisResponse(
                analysis_id=analysis.analysis_id,
                document_id=analysis.document_id,
                analysis_type=analysis.analysis_type,
                risk_level=analysis.risk_level,
                confidence_score=analysis.confidence_score,
                created_at=analysis.created_at.isoformat(),
                completed_at=analysis.completed_at.isoformat() if analysis.completed_at else "",
                analysis_results=analysis.analysis_results
            )
            for analysis in analyses
        ]
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"Obtenidos {len(response_data)} análisis históricos"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types", response_model=APIResponse[Dict[str, str]])
async def get_analysis_types():
    """Obtener tipos de análisis disponibles"""
    analysis_types = {
        "fraud_detection": "Detección de fraudes y anomalías",
        "compliance_check": "Verificación de cumplimiento normativo",
        "financial_analysis": "Análisis financiero y tributario",
        "pattern_analysis": "Análisis de patrones y tendencias"
    }
    
    return APIResponse(
        success=True,
        data=analysis_types,
        message="Tipos de análisis obtenidos exitosamente"
    )


@router.get("/risk-levels", response_model=APIResponse[Dict[str, str]])
async def get_risk_levels():
    """Obtener niveles de riesgo disponibles"""
    risk_levels = {
        "minimal": "Riesgo mínimo - Sin problemas detectados",
        "low": "Riesgo bajo - Revisar recomendaciones",
        "medium": "Riesgo medio - Requiere atención",
        "high": "Riesgo alto - Revisar inmediatamente",
        "critical": "Riesgo crítico - Acción inmediata requerida"
    }
    
    return APIResponse(
        success=True,
        data=risk_levels,
        message="Niveles de riesgo obtenidos exitosamente"
    )


@router.post("/upload-analyze", response_model=APIResponse[AnalysisResponse])
async def upload_and_analyze_document(
    file: UploadFile = File(...),
    analysis_type: AnalysisType = AnalysisType.FRAUD_DETECTION,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    analysis_service: DocumentAnalysisService = Depends(get_document_analysis_service),
    current_user: Dict = Depends(get_current_user)
):
    """Subir archivo y analizar documento"""
    try:
        # Validar tipo de archivo
        if not file.filename or not file.filename.endswith(('.json', '.xml')):
            raise HTTPException(
                status_code=400,
                detail="Formato no soportado. Use archivos JSON o XML"
            )
        
        # Leer contenido del archivo
        content = await file.read()
        
        # Parsear contenido según tipo
        if file.filename.endswith('.json'):
            import json
            document_data = json.loads(content.decode('utf-8'))
        else:
            # Para XML, convertir a dict (implementación simplificada)
            # En producción, usar parser XML apropiado
            document_data = {"xml_content": content.decode('utf-8')}
        
        # Realizar análisis
        analysis = await analysis_service.analyze_document(
            document_data=document_data,
            analysis_type=analysis_type,
            user_id=current_user["user_id"],
            company_id=current_user["company_id"],
            document_id=file.filename,
            metadata={"uploaded_file": file.filename, "file_size": len(content)}
        )
        
        response_data = AnalysisResponse(
            analysis_id=analysis.analysis_id,
            document_id=analysis.document_id,
            analysis_type=analysis.analysis_type,
            risk_level=analysis.risk_level,
            confidence_score=analysis.confidence_score,
            created_at=analysis.created_at.isoformat(),
            completed_at=analysis.completed_at.isoformat() if analysis.completed_at else "",
            analysis_results=analysis.analysis_results
        )
        
        # Publicar resultado
        background_tasks.add_task(
            _publish_analysis_result,
            analysis,
            current_user["user_id"]
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"Archivo {file.filename} analizado exitosamente"
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Archivo JSON inválido")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Codificación de archivo no soportada")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === HELPER FUNCTIONS ===

async def _publish_analysis_result(analysis: DocumentAnalysis, user_id: str):
    """Publicar resultado de análisis via WebSocket"""
    try:
        from ..services import RedisService
        
        # TODO: Implementar publicación real
        # Por ahora es placeholder
        pass
        
    except Exception as e:
        print(f"Error publishing analysis result: {e}")


async def _publish_batch_results(
    analyses: List[DocumentAnalysis], 
    user_id: str, 
    batch_id: Optional[str]
):
    """Publicar resultados de análisis en lote"""
    try:
        # TODO: Implementar publicación real
        pass
        
    except Exception as e:
        print(f"Error publishing batch results: {e}")
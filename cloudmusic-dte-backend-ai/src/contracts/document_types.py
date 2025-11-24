"""
Tipos de documentos alineados con PostgreSQL y MongoDB
Estructura exacta según schema de base de datos del proyecto
"""

from datetime import datetime, date
from typing import Dict, List, Literal, Optional, Union, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum


class DocumentType(int, Enum):
    """Tipos de DTE según SII (PostgreSQL documents.document_type)"""
    FACTURA_ELECTRONICA = 33
    FACTURA_EXENTA = 34
    BOLETA_ELECTRONICA = 39
    BOLETA_EXENTA = 41
    FACTURA_COMPRA = 46
    GUIA_DESPACHO = 52
    NOTA_DEBITO = 56
    NOTA_CREDITO = 61


class SIIStatus(str, Enum):
    """Estados SII (PostgreSQL documents.sii_status)"""
    DRAFT = "draft"
    SIGNED = "signed" 
    SENT = "sent"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


class AnalysisType(str, Enum):
    """Tipos análisis IA (MongoDB ai_document_analysis.analysis_type)"""
    TAX_COMPLIANCE_CHECK = "tax_compliance_check"
    FRAUD_DETECTION = "fraud_detection"
    ANOMALY_DETECTION = "anomaly_detection"
    PATTERN_ANALYSIS = "pattern_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"


class RiskLevel(str, Enum):
    """Niveles de riesgo (MongoDB ai_document_analysis.risk_level)"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# === TIPOS POSTGRESQL (BACKEND NODE.JS) ===

class DTEDocument(BaseModel):
    """Documento DTE según tabla PostgreSQL 'documents'"""
    id: str = Field(..., description="UUID del documento")
    company_id: str = Field(..., description="UUID de la empresa emisora")
    client_id: Optional[str] = Field(None, description="UUID del cliente")
    folio_id: str = Field(..., description="UUID del folio CAF")
    document_type: DocumentType = Field(..., description="Tipo DTE según SII")
    folio_number: int = Field(..., description="Número de folio")
    issue_date: date = Field(..., description="Fecha emisión")
    due_date: Optional[date] = Field(None, description="Fecha vencimiento")
    net_amount: Decimal = Field(..., description="Monto neto")
    tax_amount: Decimal = Field(..., description="Monto impuestos")
    exempt_amount: Decimal = Field(default=Decimal('0'), description="Monto exento")
    total_amount: Decimal = Field(..., description="Monto total")
    currency: str = Field(default="CLP", description="Moneda")
    sii_status: SIIStatus = Field(default=SIIStatus.DRAFT, description="Estado SII")
    track_id: Optional[str] = Field(None, description="Track ID SII")
    xml_content: Optional[str] = Field(None, description="XML del DTE")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DTEDocumentItem(BaseModel):
    """Item de documento según tabla PostgreSQL 'document_items'"""
    id: str = Field(..., description="UUID del item")
    document_id: str = Field(..., description="UUID del documento padre")
    product_id: Optional[str] = Field(None, description="UUID del producto")
    line_number: int = Field(..., description="Número de línea")
    product_code: Optional[str] = Field(None, description="Código del producto")
    product_name: str = Field(..., description="Nombre del producto/servicio")
    description: Optional[str] = Field(None, description="Descripción detallada")
    quantity: Decimal = Field(..., description="Cantidad")
    unit_price: Decimal = Field(..., description="Precio unitario")
    discount_percentage: Decimal = Field(default=Decimal('0'), description="% descuento")
    discount_amount: Decimal = Field(default=Decimal('0'), description="Monto descuento")
    net_amount: Decimal = Field(..., description="Monto neto línea")
    tax_amount: Decimal = Field(..., description="Impuesto línea")
    total_amount: Decimal = Field(..., description="Total línea")
    unit_of_measure: str = Field(default="UNIDAD", description="Unidad medida")


# === TIPOS MONGODB (BACKEND IA PYTHON) ===

class DocumentAnalysis(BaseModel):
    """Análisis IA según colección MongoDB 'ai_document_analysis'"""
    analysis_id: str = Field(..., description="ID único del análisis")
    document_id: str = Field(..., description="ID documento PostgreSQL")
    company_id: str = Field(..., description="ID empresa")
    analysis_type: AnalysisType = Field(..., description="Tipo de análisis")
    ai_model: str = Field(default="ollama-llama3.2-3b", description="Modelo IA usado")
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Input data - datos del documento analizado
    input_data: Dict[str, Any] = Field(..., description="Datos entrada análisis")
    
    # Resultados del análisis
    analysis_results: Dict[str, Any] = Field(..., description="Resultados análisis IA")
    
    # Métricas del análisis
    processing_time_ms: int = Field(..., description="Tiempo procesamiento ms")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Nivel confianza")
    risk_level: RiskLevel = Field(..., description="Nivel riesgo detectado")
    
    # Metadata
    user_id: str = Field(..., description="Usuario que solicitó análisis")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    """Sesión chat según colección MongoDB 'chat_sessions'"""
    session_id: str = Field(..., description="ID único sesión")
    user_id: str = Field(..., description="ID usuario")
    company_id: str = Field(..., description="ID empresa")
    session_start: datetime = Field(default_factory=datetime.now)
    session_end: Optional[datetime] = Field(None)
    is_active: bool = Field(default=True, description="Sesión activa")
    
    # Mensajes de la sesión
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata de la sesión
    session_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class WebSocketEvent(BaseModel):
    """Evento WebSocket según colección MongoDB 'websocket_events'"""
    event_id: str = Field(..., description="ID único evento")
    event_type: str = Field(..., description="Tipo evento")
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(None, description="ID usuario")
    company_id: Optional[str] = Field(None, description="ID empresa")
    session_id: Optional[str] = Field(None, description="ID sesión WebSocket")
    connection_id: Optional[str] = Field(None, description="ID conexión")
    
    # Datos del evento
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    broadcast_to: List[str] = Field(default_factory=list)
    processed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


class SIIResponse(BaseModel):
    """Respuesta SII según colección MongoDB 'sii_responses'"""
    track_id: str = Field(..., description="Track ID SII")
    document_id: str = Field(..., description="ID documento")
    company_id: str = Field(..., description="ID empresa")
    company_rut: str = Field(..., description="RUT empresa")
    document_type: DocumentType = Field(..., description="Tipo DTE")
    folio_number: int = Field(..., description="Número folio")
    
    submission_timestamp: datetime = Field(..., description="Timestamp envío")
    sii_environment: str = Field(..., description="Ambiente SII (certificacion/produccion)")
    submission_method: str = Field(..., description="Método envío")
    
    # Datos request y response
    request_data: Dict[str, Any] = Field(default_factory=dict)
    sii_responses: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Estado actual
    current_status: str = Field(..., description="Estado actual")
    status_history: List[Dict[str, Any]] = Field(default_factory=list)
    retry_history: List[Dict[str, Any]] = Field(default_factory=list)
    error_details: Optional[Dict[str, Any]] = Field(None)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AuditTrail(BaseModel):
    """Registro auditoría según colección MongoDB 'audit_trail'"""
    timestamp: datetime = Field(default_factory=datetime.now)
    nivel: str = Field(..., description="Nivel log (INFO, WARNING, ERROR)")
    modulo: str = Field(..., description="Módulo sistema")
    accion: str = Field(..., description="Acción realizada")
    
    # IDs relacionados
    usuarioId: Optional[str] = Field(None, description="ID usuario")
    empresaId: Optional[str] = Field(None, description="ID empresa") 
    documentoId: Optional[str] = Field(None, description="ID documento")
    tipoDocumento: Optional[int] = Field(None, description="Tipo DTE")
    folio: Optional[int] = Field(None, description="Número folio")
    
    # Detalles
    mensaje: str = Field(..., description="Mensaje descriptivo")
    detalles: Dict[str, Any] = Field(default_factory=dict)
    
    # Contexto técnico
    ipAddress: Optional[str] = Field(None, description="IP origen")
    userAgent: Optional[str] = Field(None, description="User agent")


# === TIPOS DE REQUEST/RESPONSE PARA APIs ===

class DocumentAnalysisRequest(BaseModel):
    """Request para análisis de documento"""
    document_id: str = Field(..., description="ID documento a analizar")
    analysis_type: AnalysisType = Field(..., description="Tipo análisis")
    user_id: str = Field(..., description="Usuario solicitante")
    company_id: str = Field(..., description="Empresa")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")


class DocumentValidation(BaseModel):
    """Validación estructura documento"""
    is_valid: bool = Field(..., description="¿Documento válido?")
    errors: List[str] = Field(default_factory=list, description="Errores encontrados")
    warnings: List[str] = Field(default_factory=list, description="Advertencias")
    document_type: str = Field(..., description="Tipo documento validado")
    validated_at: datetime = Field(default_factory=datetime.now)
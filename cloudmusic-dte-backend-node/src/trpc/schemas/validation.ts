/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🔍 XML VALIDATION & DOCUMENT ANALYSIS SCHEMAS
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Validación de documentos XML contra esquemas SII
 * - Validación estructural y sintáctica
 * - Verificación de reglas de negocio DTE
 * - Análisis de contenido y consistencia
 * - Estadísticas de validación
 */

import { z } from 'zod';
import { DTEType, VALID_DOCUMENT_TYPES } from './common';

// ==========================================
// 🔍 VALIDATION ENUMS
// ==========================================

/**
 * Tipos de documentos DTE según normativa SII
 */
export enum DocumentType {
  FACTURA_ELECTRONICA = 33,           // Factura electrónica afecta
  FACTURA_NO_AFECTA = 34,             // Factura electrónica exenta
  BOLETA_ELECTRONICA = 39,            // Boleta electrónica afecta
  BOLETA_EXENTA_ELECTRONICA = 41,     // Boleta electrónica exenta
  FACTURA_COMPRA = 46,                // Factura de compra electrónica
  GUIA_DESPACHO_ELECTRONICA = 52,     // Guía de despacho electrónica
  NOTA_DEBITO_ELECTRONICA = 56,       // Nota de débito electrónica
  NOTA_CREDITO_ELECTRONICA = 61       // Nota de crédito electrónica
}

// ==========================================
// 🔍 VALIDATION SCHEMAS
// ==========================================

/**
 * Schema validación XML para xmlValidator
 */
export const validateXMLSchema = z.object({
  xmlContent: z.string().min(1, 'Contenido XML requerido'),
  expectedType: z.nativeEnum(DocumentType).optional(),
  strictValidation: z.boolean().default(true),
  validateBusiness: z.boolean().default(true),
  includeWarnings: z.boolean().default(true)
});

/**
 * Schema validación masiva de documentos
 */
export const batchValidateSchema = z.object({
  documents: z.array(z.object({
    id: z.string(),
    xmlContent: z.string().min(1),
    expectedType: z.nativeEnum(DocumentType).optional()
  })).min(1).max(100, 'Máximo 100 documentos por lote'),
  stopOnFirstError: z.boolean().default(false),
  parallelProcessing: z.boolean().default(true)
});

/**
 * Schema configuración validador
 */
export const validatorConfigSchema = z.object({
  timeout: z.number().min(1000).max(60000).default(30000),
  maxFileSize: z.number().min(1024).max(10485760).default(5242880), // 5MB
  enableCache: z.boolean().default(true),
  cacheTimeout: z.number().min(300).max(3600).default(900), // 15 min
  strictMode: z.boolean().default(true)
});

/**
 * Schema análisis de documento
 */
export const analyzeDocumentSchema = z.object({
  documentId: z.string().uuid('ID documento inválido'),
  analysisType: z.enum([
    'structure',    // Validación estructura XML
    'content',      // Análisis contenido
    'business',     // Reglas de negocio
    'compliance',   // Cumplimiento normativo
    'full'          // Análisis completo
  ]).default('full'),
  includeRecommendations: z.boolean().default(true)
});

/**
 * Schema obtener historial de validaciones
 */
export const getValidationHistorySchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(100).default(20),
  documentType: z.nativeEnum(DocumentType).optional(),
  isValid: z.boolean().optional(),
  dateFrom: z.date().optional(),
  dateTo: z.date().optional()
});

/**
 * Schema configurar validaciones automáticas
 */
export const configureAutoValidationSchema = z.object({
  enabled: z.boolean(),
  documentTypes: z.array(z.nativeEnum(DocumentType)).optional(),
  validationLevel: z.enum(['basic', 'standard', 'strict']).default('standard'),
  autoFix: z.boolean().default(false)
});

/**
 * Enum AIAnalysisType (necesario para compatibilidad)
 */
export enum AIAnalysisType {
  ANOMALY_DETECTION = 'anomaly_detection',
  CASH_FLOW_PREDICTION = 'cash_flow_prediction', 
  TAX_OPTIMIZATION = 'tax_optimization'
}

// ==========================================
// 🔍 VALIDATION INTERFACES
// ==========================================

/**
 * Resultado de validación XML
 */
export interface ValidationResult {
  isValid: boolean;           // Estado general de validación
  errors: ValidationError[];  // Errores encontrados
  warnings: string[];         // Advertencias no críticas
  documentType?: DocumentType; // Tipo DTE detectado
  timing: {
    validationTime: number;   // Milisegundos de validación (SLA: ≤1000ms)
    startTime: Date;         // Timestamp inicio
    endTime: Date;           // Timestamp fin
  };
  metadata?: {
    xmlSize: number;         // Tamaño del XML en bytes
    nodeCount: number;       // Cantidad de nodos XML
    documentVersion?: string; // Versión del documento
  };
}

/**
 * Error específico de validación XML
 */
export interface ValidationError {
  code: string;               // Código único del error
  message: string;           // Mensaje descriptivo del error
  line?: number;             // Línea del XML donde ocurre
  column?: number;           // Columna del XML donde ocurre
  severity: 'error' | 'warning'; // Gravedad del problema
  field?: string;            // Campo XML relacionado
  xpath?: string;            // XPath del elemento
  suggestion?: string;       // Sugerencia de corrección
}

/**
 * Estadísticas de validación por lotes
 */
export interface ValidationStats {
  totalDocuments: number;     // Total documentos validados
  validDocuments: number;     // Documentos válidos
  invalidDocuments: number;   // Documentos con errores
  errorRate: number;         // Tasa de error % (SLA: ≤2%)
  averageTime: number;       // Tiempo promedio validación
  meetsSLATime: boolean;     // ¿Cumple SLA tiempo? (≤1s)
  meetsSLAErrorRate: boolean; // ¿Cumple SLA error? (≤2%)
  processingDetails: {
    startTime: Date;
    endTime: Date;
    totalTime: number;
    documentsPerSecond: number;
  };
}

/**
 * Resultado de validación masiva
 */
export interface BatchValidationResult {
  batchId: string;
  totalDocuments: number;
  processedDocuments: number;
  validDocuments: number;
  invalidDocuments: number;
  results: Array<{
    documentId: string;
    isValid: boolean;
    errors: ValidationError[];
    warnings: string[];
    processingTime: number;
  }>;
  summary: ValidationStats;
}

/**
 * Configuración del validador XML
 */
export interface ValidatorConfig {
  timeout: number;           // Timeout en milisegundos
  maxFileSize: number;       // Tamaño máximo archivo
  enableCache: boolean;      // Habilitar cache de resultados
  cacheTimeout: number;      // Timeout del cache
  strictMode: boolean;       // Modo estricto de validación
  schemaValidation: boolean; // Validación contra XSD
  businessRules: boolean;    // Validación reglas de negocio
}

/**
 * Resultado de análisis de documento
 */
export interface DocumentAnalysisResult {
  documentId: string;
  analysisType: string;
  findings: Array<{
    category: 'structure' | 'content' | 'business' | 'compliance';
    type: 'error' | 'warning' | 'info' | 'suggestion';
    severity: 'high' | 'medium' | 'low';
    message: string;
    field?: string;
    suggestion?: string;
    autoFixable?: boolean;
  }>;
  score: number;             // Puntuación 0-100
  recommendations: string[]; // Recomendaciones de mejora
  processingTime: number;
  timestamp: Date;
}

/**
 * Interface resultado validación masiva
 */
export interface BatchValidationResult {
  batchId: string;
  totalDocuments: number;
  processedDocuments: number;
  validDocuments: number;
  invalidDocuments: number;
  results: Array<{
    documentId: string;
    isValid: boolean;
    errors: ValidationError[];
    warnings: string[];
    processingTime: number;
  }>;
  summary: ValidationStats;
}

/**
 * Interface configuración del validador XML
 */
export interface ValidatorConfig {
  timeout: number;
  maxFileSize: number;
  enableCache: boolean;
  cacheTimeout: number;
  strictMode: boolean;
  schemaValidation: boolean;
  businessRules: boolean;
}
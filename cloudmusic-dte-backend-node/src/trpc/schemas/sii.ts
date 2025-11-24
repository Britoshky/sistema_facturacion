/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🏦 SII INTEGRATION SCHEMAS
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Integración con webservices oficiales del SII
 * - Envío y consulta de documentos DTE
 * - Autenticación y autorización
 * - Consulta de estados y acuses de recibo
 * - Configuración de ambientes (certificación/producción)
 */

import { z } from 'zod';

// ==========================================
// 🏦 SII ENUMS
// ==========================================

/**
 * Ambientes SII disponibles
 */
export enum SIIEnvironment {
  CERTIFICATION = 'certificacion',     // Ambiente pruebas SII
  PRODUCTION = 'produccion'            // Ambiente producción SII
}

/**
 * Estados de documento en SII
 */
export enum SIIDocumentStatus {
  PENDING = 'PENDING',                 // Pendiente de envío
  SENT = 'SENT',                      // Enviado al SII
  ACCEPTED = 'ACCEPTED',               // Aceptado por SII
  REJECTED = 'REJECTED',               // Rechazado por SII
  PROCESSED = 'PROCESSED'              // Procesado completamente
}

// ==========================================
// 🏦 SII VALIDATION SCHEMAS
// ==========================================

/**
 * Schema configuración SII
 */
export const siiConfigSchema = z.object({
  environment: z.nativeEnum(SIIEnvironment).default(SIIEnvironment.CERTIFICATION),
  rutEmisor: z.string().min(1, 'RUT emisor requerido'),
  dvEmisor: z.string().length(1, 'DV emisor debe ser un carácter'),
  timeout: z.number().min(5000).max(60000).default(30000),
  retryAttempts: z.number().min(0).max(5).default(3),
  userAgent: z.string().default('CloudMusic-DTE/1.0'),
  enableCompression: z.boolean().default(true),
  validateSSL: z.boolean().default(true)
});

/**
 * Schema envío DTE al SII
 */
export const sendDTESchema = z.object({
  xmlDTE: z.string().min(1, 'XML DTE requerido'),
  nombreArchivo: z.string().min(1, 'Nombre archivo requerido'),
  rutReceptor: z.string().optional(),
  dvReceptor: z.string().length(1).optional(),
  rutEnvia: z.string().optional(),
  dvEnvia: z.string().optional(),
  includeAcknowledgment: z.boolean().default(true)
});

/**
 * Schema consulta estado DTE
 */
export const queryStatusSchema = z.object({
  trackId: z.string().min(1, 'Track ID requerido'),
  rutEmisor: z.string().min(1, 'RUT emisor requerido'),
  dvEmisor: z.string().length(1, 'DV emisor requerido'),
  includeDetails: z.boolean().default(true)
});

/**
 * Schema obtener acuse de recibo
 */
export const acknowledgmentSchema = z.object({
  trackId: z.string().min(1, 'Track ID requerido'),
  rutEmisor: z.string().min(1, 'RUT emisor requerido'),
  dvEmisor: z.string().length(1, 'DV emisor requerido'),
  downloadXml: z.boolean().default(true)
});

/**
 * Schema validar RUT con SII
 */
export const validateRutSchema = z.object({
  rut: z.string().min(1, 'RUT requerido'),
  dv: z.string().length(1, 'DV requerido'),
  includeBusinessData: z.boolean().default(false)
});

/**
 * Schema obtener historial SII
 */
export const getSIIHistorySchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(100).default(20),
  documentType: z.number().int().optional(),
  status: z.nativeEnum(SIIDocumentStatus).optional(),
  dateFrom: z.date().optional(),
  dateTo: z.date().optional()
});

/**
 * Schema obtener estadísticas SII
 */
export const getSIIStatsSchema = z.object({
  period: z.enum(['day', 'week', 'month', 'year']).default('month'),
  documentType: z.number().int().optional(),
  environment: z.nativeEnum(SIIEnvironment).optional()
});

/**
 * Schema configurar webhook SII
 */
export const configureSIIWebhookSchema = z.object({
  webhookUrl: z.string().url('URL webhook inválida'),
  events: z.array(z.enum(['document_sent', 'status_changed', 'error_occurred'])),
  secret: z.string().min(16, 'Secret debe tener al menos 16 caracteres'),
  enabled: z.boolean().default(true)
});

// ==========================================
// 🏦 SII INTERFACES
// ==========================================

/**
 * Respuesta estándar de webservices SII
 */
export interface SIIResponse {
  success: boolean;           // Estado operación exitosa
  trackId?: string;          // ID seguimiento SII
  status?: string;           // Estado documento en SII
  statusCode?: number;       // Código respuesta HTTP
  message?: string;          // Mensaje descriptivo SII
  siiResponse?: string;      // Response XML completo SII
  errors: string[];          // Errores durante comunicación
  warnings: string[];        // Advertencias no críticas
  timing: {
    requestTime: number;     // Timestamp envío request
    responseTime: number;    // Timestamp recepción response
    totalTime: number;       // Tiempo total comunicación (ms)
  };
  retryCount?: number;       // Número de reintentos realizados
}

/**
 * Configuración cliente SII
 */
export interface SIIConfig {
  environment: SIIEnvironment; // Ambiente SII a usar
  rutEmisor: string;          // RUT empresa emisora
  dvEmisor: string;           // Dígito verificador RUT
  timeout: number;            // Timeout requests (ms)
  retryAttempts: number;      // Reintentos en fallas
  userAgent: string;          // User-Agent para requests
  enableCompression: boolean; // Compresión GZIP
  validateSSL: boolean;       // Validación certificados SSL
}

/**
 * Request envío DTE al SII
 */
export interface SendDTERequest {
  rutEmisor: string;          // RUT emisor documento
  dvEmisor: string;           // DV emisor documento
  rutEnvia: string;           // RUT quien envía (puede diferir)
  dvEnvia: string;            // DV quien envía
  xmlDTE: string;             // XML documento firmado
  nombreArchivo: string;      // Nombre archivo para SII
  rutReceptor?: string;       // RUT receptor (opcional)
  dvReceptor?: string;        // DV receptor (opcional)
  includeAcknowledgment?: boolean; // Incluir acuse automático
}

/**
 * Request consulta estado DTE en SII
 */
export interface QueryStatusRequest {
  trackId: string;            // ID seguimiento SII
  rutEmisor: string;          // RUT emisor documento
  dvEmisor: string;           // DV emisor documento
  includeDetails?: boolean;   // Incluir detalles adicionales
}

/**
 * Request obtener acuse recibo SII
 */
export interface AcknowledgmentRequest {
  trackId: string;            // ID seguimiento SII
  rutEmisor: string;          // RUT emisor documento
  dvEmisor: string;           // DV emisor documento
  downloadXml?: boolean;      // Descargar XML del acuse
}

/**
 * Respuesta validación RUT en SII
 */
export interface RutValidationResponse {
  isValid: boolean;           // RUT válido en SII
  businessName?: string;      // Razón social
  economicActivity?: string;  // Actividad económica
  address?: string;           // Dirección registrada
  status: 'active' | 'inactive' | 'not_found'; // Estado en SII
  lastUpdate?: Date;          // Última actualización datos
}

/**
 * Estado detallado de documento en SII
 */
export interface SIIDocumentStatusDetail {
  trackId: string;
  documentType: number;
  folioNumber: number;
  status: SIIDocumentStatus;
  statusDescription: string;
  submissionDate?: Date;
  processedDate?: Date;
  observations?: string[];
  technicalErrors?: string[];
  businessErrors?: string[];
  acknowledgmentXml?: string;
}

/**
 * Estadísticas de integración SII
 */
export interface SIIIntegrationStats {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  successRate: number;
  lastRequest?: Date;
  environmentUsed: SIIEnvironment;
  errorBreakdown: {
    connectionErrors: number;
    timeoutErrors: number;
    authenticationErrors: number;
    businessErrors: number;
  };
}

/**
 * Interface para configuración de webhook SII
 */
export interface SIIWebhookConfig {
  webhookUrl: string;
  events: Array<'document_sent' | 'status_changed' | 'error_occurred'>;
  secret: string;
  enabled: boolean;
  retryAttempts: number;
  timeoutSeconds: number;
}
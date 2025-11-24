/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 📁 FOLIOS & CAF SCHEMAS
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Gestión de folios CAF (Código de Autorización de Folios) del SII
 * - Importación y validación de archivos CAF
 * - Control de numeración secuencial
 * - Alertas de folios disponibles
 * - Integración con certificados digitales
 */

import { z } from 'zod';
import { VALID_DOCUMENT_TYPES } from './common';

// ==========================================
// 📁 FOLIO VALIDATION SCHEMAS
// ==========================================

/**
 * Schema crear folio CAF
 */
export const createFolioSchema = z.object({
  documentType: z.number().int().min(1).refine(
    val => VALID_DOCUMENT_TYPES.includes(val),
    { message: 'Tipo de documento inválido' }
  ),
  fromFolio: z.number().int().min(1, 'Folio inicial debe ser mayor a 0'),
  toFolio: z.number().int().min(1, 'Folio final debe ser mayor a 0'),
  cafFile: z.string().min(1, 'Archivo CAF es requerido')
}).refine(
  data => data.toFolio >= data.fromFolio,
  { message: 'Folio final debe ser mayor o igual al inicial' }
);

/**
 * Schema actualizar folio
 */
export const updateFolioSchema = z.object({
  currentFolio: z.number().int().min(1).optional(),
  isActive: z.boolean().optional(),
  observations: z.string().optional()
});

/**
 * Schema importar CAF desde archivo XML
 */
export const folioImportCAFSchema = z.object({
  cafXmlContent: z.string().min(1, 'Contenido CAF XML requerido'),
  validateSignature: z.boolean().default(true),
  autoActivate: z.boolean().default(false)
});

/**
 * Schema obtener siguiente folio disponible
 */
export const getNextFolioSchema = z.object({
  documentType: z.number().int().refine(
    val => VALID_DOCUMENT_TYPES.includes(val),
    { message: 'Tipo de documento inválido' }
  )
});

/**
 * Schema estadísticas de folios
 */
export const folioStatsSchema = z.object({
  documentType: z.number().int().optional(),
  includeInactive: z.boolean().default(false)
});

/**
 * Schema configurar alertas de folios
 */
export const configureFolioAlertsSchema = z.object({
  documentType: z.number().int(),
  warningThreshold: z.number().int().min(1).max(1000).default(50),
  criticalThreshold: z.number().int().min(1).max(500).default(10),
  emailNotifications: z.boolean().default(true)
});

/**
 * Schema listar folios
 */
export const listFoliosSchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(50).default(10),
  documentType: z.number().int().optional(),
  isActive: z.boolean().optional(),
  lowStock: z.boolean().optional()
});

/**
 * Schema consumir folio (marcar como usado)
 */
export const consumeFolioSchema = z.object({
  documentType: z.number().int().refine(
    val => VALID_DOCUMENT_TYPES.includes(val),
    { message: 'Tipo de documento inválido' }
  ),
  folioNumber: z.number().int().min(1).optional() // Si no se especifica, usa el siguiente
});

// ==========================================
// 📁 CAF & FOLIO INTERFACES
// ==========================================

/**
 * Archivo CAF (Código de Autorización de Folios) del SII
 */
export interface CAFFile {
  documentType: number;        // Tipo documento DTE (33, 39, etc.)
  fromFolio: number;          // Folio inicial autorizado
  toFolio: number;            // Folio final autorizado
  authorizationDate: Date;     // Fecha autorización SII
  expiryDate: Date;           // Fecha vencimiento CAF
  rut: string;                // RUT empresa autorizada
  companyName: string;        // Razón social empresa
  authorizedRange: number;    // Cantidad folios autorizados
  xmlContent: string;         // Contenido XML completo CAF
  signature?: string;         // Firma digital del CAF
  isValid: boolean;          // Estado validez actual
}

/**
 * Resultado validación archivo CAF
 */
export interface CAFValidationResult {
  isValid: boolean;           // Estado validación general
  errors: string[];           // Errores críticos encontrados
  warnings: string[];         // Advertencias no críticas
  cafData?: CAFFile;         // Datos CAF si es válido
  validationDetails?: {
    signatureValid: boolean;
    dateValid: boolean;
    rangeValid: boolean;
    rutMatches: boolean;
  };
}

/**
 * Alerta de folios agotándose
 */
export interface FolioAlert {
  companyId: string;          // ID empresa afectada
  documentType: number;       // Tipo documento DTE
  currentFolio: number;       // Folio actual en uso
  remainingFolios: number;    // Folios restantes
  totalFolios: number;        // Total folios CAF
  alertThreshold: number;     // Umbral configurado alerta
  severity: 'warning' | 'critical' | 'info'; // Gravedad alerta
  message: string;           // Mensaje descriptivo
  recommendedAction?: string; // Acción recomendada
}

/**
 * Estadísticas de uso de folios
 */
export interface FolioStats {
  documentType: number;
  totalFolios: number;
  usedFolios: number;
  remainingFolios: number;
  usagePercentage: number;
  averageDailyUsage: number;
  estimatedDaysRemaining: number;
  lastUsedFolio: number;
  nextAvailableFolio: number;
  cafExpiryDate: Date;
}

// ==========================================
// 📁 ROUTER OPERATION SCHEMAS
// ==========================================

/**
 * Schema para obtener folio por ID
 */
export const getFolioByIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema para actualizar folio con ID
 */
export const updateFolioWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateFolioSchema
});

/**
 * Schema para eliminar folio
 */
export const deleteFolioSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema para importar archivo CAF XML
 */
export const importCAFSchema = z.object({
  cafXmlContent: z.string().min(1, 'Contenido CAF requerido')
});

/**
 * Schema para obtener siguiente folio disponible
 */
export const getNextFolioAvailableSchema = z.object({
  documentType: z.number().int().min(1)
});

/**
 * Schema para obtener estadísticas de folios
 */
export const getFolioStatsSchema = z.object({
  documentType: z.number().int().optional()
});
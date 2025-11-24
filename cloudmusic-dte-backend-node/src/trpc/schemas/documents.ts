/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 📄 DOCUMENT DTE SCHEMAS & INTERFACES
 * ════════════════════════════════════════════════════════════════════════════════
 */

import { z } from 'zod';
import { DTEType, SiiStatus, VALID_DOCUMENT_TYPES, VALID_CURRENCIES } from './common';
import { searchSchema } from './common';

// ==========================================
// 📄 DOCUMENT DTE INTERFACES & TYPES
// ==========================================

/**
 * Interfaz para documento base en generación de XML
 */
export interface DTEDocumentBase {
  id: string;
  documentType: number;
  folioNumber: number;
  netAmount: number | { toNumber(): number };
  taxAmount: number | { toNumber(): number };
  totalAmount: number | { toNumber(): number };
  issueDate?: Date;
  clientId?: string | null;
}

/**
 * Tipos de validación XML para documentos DTE
 */
export type DocumentValidationType = 'DTE' | 'BOLETA' | 'NOTA_CREDITO' | 'NOTA_DEBITO' | 'FACTURA_EXENTA';

// ==========================================
// 📄 DOCUMENT VALIDATION SCHEMAS
// ==========================================

/**
 * Schema actualizar documento (expandido para edición completa)
 */
export const updateDocumentSchema = z.object({
  clientId: z.string().uuid().optional(),
  companyId: z.string().uuid().optional(),
  documentType: z.number().refine(
    val => VALID_DOCUMENT_TYPES.includes(val),
    { message: 'Tipo de documento inválido' }
  ).optional(),
  amount: z.number().min(0).optional(),
  tax: z.number().min(0).optional(),
  total: z.number().min(0).optional(),
  status: z.string().optional(),
  observations: z.string().optional(),
  paymentDate: z.string().optional(),
  internalNotes: z.string().optional(),
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().min(0.001),
    price: z.number().min(0),
    description: z.string().min(1)
  })).optional()
});

/**
 * Schema item de documento (detalle)
 */
export const documentItemSchema = z.object({
  sequence: z.number().int().min(1),
  productId: z.string().uuid(),
  description: z.string().min(1),
  quantity: z.number().min(0.001),
  unitPrice: z.number().min(0),
  totalAmount: z.number().min(0),
  taxAmount: z.number().min(0),
  exemptAmount: z.number().min(0).optional(),
  discountAmount: z.number().min(0).default(0),
  unitOfMeasure: z.string().default('unit')
});

/**
 * Schema crear documento DTE (compatible con router existente)
 */
export const createDocumentSchema = z.object({
  clientId: z.string().uuid(),
  documentType: z.number().refine(
    val => VALID_DOCUMENT_TYPES.includes(val),
    { message: 'Tipo de documento inválido' }
  ),
  amount: z.number().min(0),
  tax: z.number().min(0),
  total: z.number().min(0),
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().min(0.001),
    price: z.number().min(0),
    description: z.string().min(1)
  })).min(1, 'Debe tener al menos un item'),
  observations: z.string().optional(),
  internalNotes: z.string().optional()
});

/**
 * Schema crear documento DTE completo (nueva versión)
 */
export const createDocumentSchemaNew = z.object({
  documentType: z.number().refine(
    val => VALID_DOCUMENT_TYPES.includes(val),
    { message: 'Tipo de documento inválido' }
  ),
  folioNumber: z.number().int().min(1),
  clientId: z.string().uuid(),
  issueDate: z.date(),
  expirationDate: z.date().optional(),
  
  // Montos
  netAmount: z.number().min(0),
  taxAmount: z.number().min(0), 
  totalAmount: z.number().min(0),
  exemptAmount: z.number().min(0).optional(),
  
  // Configuración
  currency: z.enum(['CLP', 'USD', 'EUR', 'UF']).default('CLP'),
  exchangeRate: z.number().min(0).default(1),
  
  // Items del documento
  items: z.array(documentItemSchema).min(1, 'Debe tener al menos un item'),
  
  // Referencias opcionales
  referencedDocumentType: z.number().optional(),
  referencedFolioNumber: z.number().optional(),
  referenceReason: z.string().optional(),
  
  // Comentarios
  observations: z.string().optional(),
  internalNotes: z.string().optional()
});

/**
 * Schema listar documentos con filtros
 */
export const listDocumentsSchema = searchSchema.extend({
  documentType: z.number().optional(),
  clientId: z.string().uuid().optional(),
  status: z.nativeEnum(SiiStatus).optional(),
  dateFrom: z.date().optional(),
  dateTo: z.date().optional(),
  folioNumber: z.number().int().optional()
});

/**
 * Schema validar documento XML
 */
export const validateDocumentXMLSchema = z.object({
  xmlContent: z.string().min(1, 'Contenido XML es requerido'),
  validateAgainstSII: z.boolean().default(false)
});

// ==========================================
// 📄 DTE INTERFACES
// ==========================================

/**
 * Interface para respuesta SII completa
 */
export interface SiiResponse {
  success: boolean;
  trackingNumber?: string;
  glosa?: string;
  estado?: string;
  xmlResponse?: string;
  timestamp: Date;
}

/**
 * Interface para análisis de documento
 */
export interface DocumentAnalysis {
  documentId: string;
  analysisType: 'structure' | 'content' | 'compliance';
  findings: Array<{
    type: 'error' | 'warning' | 'info';
    code?: string;
    message: string;
    field?: string;
    suggestion?: string;
  }>;
  score: number; // 0-100
  timestamp: Date;
}

/**
 * Interface para datos de creación de documento simplificado
 */
export interface SimpleDocumentData {
  clientId: string;
  documentType: number;
  amount: number;
  tax: number;
  total: number;
  items: Array<{
    productId: string;
    quantity: number;
    price: number;
    description: string;
  }>;
}

// ==========================================
// 📄 ROUTER OPERATION SCHEMAS
// ==========================================

/**
 * Schema para obtener documento por ID
 */
export const getDocumentByIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema para actualizar documento con ID
 */
export const updateDocumentWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateDocumentSchema
});

/**
 * Schema para eliminar documento
 */
export const deleteDocumentSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema para validar y firmar documento
 */
export const validateAndSignDocumentSchema = z.object({
  id: z.string().uuid('ID del documento debe ser UUID válido'),
  certificateId: z.string().uuid('ID del certificado debe ser UUID válido'),
  pfxPassword: z.string().min(1, 'Contraseña del certificado es requerida')
});

/**
 * Schema para enviar documento al SII
 */
export const sendDocumentToSiiSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});
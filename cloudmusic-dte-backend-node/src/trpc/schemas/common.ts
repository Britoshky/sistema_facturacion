/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🔧 COMMON SCHEMAS & TYPES
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Schemas y tipos comunes usados en múltiples dominios
 * - Paginación
 * - ID validation  
 * - Filtros base
 * - Constantes globales
 */

import { z } from 'zod';

// ==========================================
// 📋 ENUMS ESPECÍFICOS SII/DTE
// ==========================================

/**
 * Estados específicos SII (no en Prisma - específico del negocio)
 */
export enum SiiStatus {
  DRAFT = 'draft',
  ISSUED = 'issued',
  SENT = 'sent', 
  ACCEPTED = 'accepted',
  REJECTED = 'rejected'
}

/**
 * Tipos documentos DTE según SII
 */
export enum DTEType {
  FACTURA_ELECTRONICA = 33,
  FACTURA_ELECTRONICA_EXENTA = 34,
  BOLETA_ELECTRONICA = 39,
  LIQUIDACION_FACTURA_ELECTRONICA = 43,
  FACTURA_COMPRA_ELECTRONICA = 46,
  GUIA_DESPACHO_ELECTRONICA = 52,
  NOTA_DEBITO_ELECTRONICA = 56,
  NOTA_CREDITO_ELECTRONICA = 61
}

/**
 * Constantes de validación DTE
 */
export const VALID_DOCUMENT_TYPES = [33, 34, 39, 41, 43, 46, 52, 56, 61];
export const VALID_CURRENCIES = ['CLP', 'USD', 'EUR', 'UF'];

// ==========================================
// 🔍 SCHEMAS COMUNES
// ==========================================

/**
 * Schema ID básico
 */
export const idSchema = z.object({ 
  id: z.string().min(1, 'ID es requerido')
});

/**
 * Schema ID UUID
 */
export const uuidIdSchema = z.object({ 
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema paginación estándar
 */
export const paginationSchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(100).default(10)
});

/**
 * Schema búsqueda con paginación
 */
export const searchSchema = paginationSchema.extend({
  search: z.string().optional()
});

/**
 * Schema filtros base
 */
export const baseFiltersSchema = z.object({
  isActive: z.boolean().optional(),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional()
});

/**
 * Schema paginación con búsqueda extendida
 */
export const extendedSearchSchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(100).default(10),
  search: z.string().optional()
});

/**
 * Schema importar CAF genérico
 */
export const importCAFSchema = z.object({
  cafXmlContent: z.string().min(1, 'Contenido CAF XML requerido'),
  validateSignature: z.boolean().default(true),
  autoActivate: z.boolean().default(false)
});
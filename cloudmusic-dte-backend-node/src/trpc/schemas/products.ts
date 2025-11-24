/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🏷️ PRODUCT SCHEMAS & INTERFACES
 * ════════════════════════════════════════════════════════════════════════════════
 */

import { z } from 'zod';
import { searchSchema } from './common';

// ==========================================
// 🏷️ PRODUCT VALIDATION SCHEMAS
// ==========================================

/**
 * Schema crear producto
 */
export const createProductSchema = z.object({
  name: z.string().min(1, 'Nombre es requerido'),
  description: z.string().optional(),
  sku: z.string().min(1, 'SKU es requerido'),
  price: z.number().min(0, 'Precio no puede ser negativo'),
  cost: z.number().min(0, 'Costo no puede ser negativo').optional(),
  productType: z.enum(['PRODUCT', 'SERVICE', 'ASSET']).default('PRODUCT'),
  taxClassification: z.enum(['taxable', 'exempt']).default('taxable'),
  unitOfMeasure: z.string().default('unit'),
  stockQuantity: z.number().int().min(0).default(0),
  minStockLevel: z.number().int().min(0).default(0),
  isActive: z.boolean().default(true)
});

/**
 * Schema actualizar producto
 */
export const updateProductSchema = z.object({
  name: z.string().min(1).optional(),
  description: z.string().optional(),
  sku: z.string().min(1).optional(),
  price: z.number().min(0).optional(),
  cost: z.number().min(0).optional(),
  productType: z.enum(['PRODUCT', 'SERVICE', 'ASSET']).optional(),
  taxClassification: z.enum(['taxable', 'exempt']).optional(),
  unitOfMeasure: z.string().optional(),
  stockQuantity: z.number().int().min(0).optional(),
  minStockLevel: z.number().int().min(0).optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema listar productos con filtros
 */
export const listProductsSchema = searchSchema.extend({
  limit: z.number().min(1).max(100).default(20), // Override default
  productType: z.enum(['PRODUCT', 'SERVICE', 'ASSET']).optional(),
  taxClassification: z.enum(['taxable', 'exempt']).optional(),
  lowStock: z.boolean().optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema actualizar stock producto
 */
export const updateStockSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  stockQuantity: z.number().int().min(0, 'El stock no puede ser negativo'),
  reason: z.string().optional()
});

// ==========================================
// 🏷️ ROUTER OPERATION SCHEMAS
// ==========================================

/**
 * Schema para actualizar producto con ID
 */
export const updateProductWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateProductSchema
});

/**
 * Schema para eliminar producto
 */
export const deleteProductSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});
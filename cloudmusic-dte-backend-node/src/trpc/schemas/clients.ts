/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 👥 CLIENT SCHEMAS & INTERFACES
 * ════════════════════════════════════════════════════════════════════════════════
 */

import { z } from 'zod';
import { searchSchema } from './common';

// ==========================================
// 👥 CLIENT VALIDATION SCHEMAS
// ==========================================

/**
 * Schema crear cliente
 */
export const createClientSchema = z.object({
  rut: z.string().min(1, 'RUT es requerido'),
  dv: z.string().length(1, 'DV debe ser un carácter'),
  businessName: z.string().min(1, 'Razón social es requerida'),
  commercialName: z.string().optional(),
  clientType: z.enum(['INDIVIDUAL', 'BUSINESS', 'FOREIGN']).default('BUSINESS'),
  economicActivity: z.string().optional(),
  address: z.string().optional(),
  commune: z.string().optional(),
  city: z.string().optional(),
  region: z.string().optional(),
  country: z.string().default('Chile'),
  postalCode: z.string().optional(),
  phone: z.string().optional(),
  email: z.string().email().optional(),
  website: z.string().url().optional(),
  contactPerson: z.string().optional(),
  paymentTerms: z.number().int().min(0).default(30),
  creditLimit: z.number().min(0).default(0),
  taxClassification: z.enum(['taxable', 'exempt']).default('taxable'),
  isActive: z.boolean().default(true)
});

/**
 * Schema actualizar cliente
 */
export const updateClientSchema = z.object({
  rut: z.string().min(1).optional(),
  dv: z.string().length(1).optional(),
  businessName: z.string().min(1).optional(),
  commercialName: z.string().optional(),
  clientType: z.enum(['INDIVIDUAL', 'BUSINESS', 'FOREIGN']).optional(),
  economicActivity: z.string().optional(),
  address: z.string().optional(),
  commune: z.string().optional(),
  city: z.string().optional(),
  region: z.string().optional(),
  country: z.string().optional(),
  postalCode: z.string().optional(),
  phone: z.string().optional(),
  email: z.string().email().optional(),
  website: z.string().url().optional(),
  contactPerson: z.string().optional(),
  paymentTerms: z.number().int().min(0).optional(),
  creditLimit: z.number().min(0).optional(),
  taxClassification: z.enum(['taxable', 'exempt']).optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema listar clientes con filtros
 */
export const listClientsSchema = searchSchema.extend({
  clientType: z.enum(['INDIVIDUAL', 'BUSINESS', 'FOREIGN']).optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema para listado de clientes con paginación completa
 */
export const listClientsWithPaginationSchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(100).default(20),
  search: z.string().optional(),
  clientType: z.enum(['BUSINESS', 'INDIVIDUAL', 'FOREIGN']).optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema para obtener cliente por ID
 */
export const getClientByIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema para actualizar cliente con ID
 */
export const updateClientWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateClientSchema
});

/**
 * Schema para eliminar cliente
 */
export const deleteClientSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});
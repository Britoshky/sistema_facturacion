/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🏢 COMPANY SCHEMAS & INTERFACES
 * ════════════════════════════════════════════════════════════════════════════════
 */

import { z } from 'zod';
import { searchSchema } from './common';

// ==========================================
// 🏢 COMPANY VALIDATION SCHEMAS
// ==========================================

/**
 * Schema crear empresa
 */
export const createCompanySchema = z.object({
  businessName: z.string().min(1, 'Razón social es requerida'),
  rut: z.string().min(1, 'RUT es requerido'),
  commercialName: z.string().optional(),
  economicActivity: z.string().min(1, 'Actividad económica es requerida'),
  businessLine: z.string().min(1, 'Línea de negocio es requerida'),
  address: z.string().min(1, 'Dirección es requerida'),
  commune: z.string().min(1, 'Comuna es requerida'),
  city: z.string().min(1, 'Ciudad es requerida'),
  region: z.string().min(1, 'Región es requerida'),
  postalCode: z.string().optional(),
  phone: z.string().optional(),
  email: z.string().email().optional(),
  website: z.string().url().optional(),
  logoUrl: z.string().url().optional(),
  taxRegime: z.string().default('general'),
  siiActivityCode: z.string().optional()
});

/**
 * Schema actualizar empresa
 */
export const updateCompanySchema = z.object({
  businessName: z.string().min(1).optional(),
  rut: z.string().min(1).optional(),
  commercialName: z.string().optional(),
  economicActivity: z.string().min(1).optional(),
  businessLine: z.string().min(1).optional(),
  address: z.string().min(1).optional(),
  commune: z.string().min(1).optional(),
  city: z.string().min(1).optional(),
  region: z.string().min(1).optional(),
  postalCode: z.string().optional(),
  phone: z.string().optional(),
  email: z.string().email().optional(),
  website: z.string().url().optional(),
  logoUrl: z.string().url().optional(),
  taxRegime: z.string().optional(),
  siiActivityCode: z.string().optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema listar empresas con filtros
 */
export const listCompaniesSchema = searchSchema.extend({
  region: z.string().optional(),
  city: z.string().optional(),
  businessLine: z.string().optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema para actualizar empresa con ID
 */
export const updateCompanyWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateCompanySchema
});
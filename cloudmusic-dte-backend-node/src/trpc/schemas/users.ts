/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 👤 USER SCHEMAS & INTERFACES
 * ════════════════════════════════════════════════════════════════════════════════
 */

import { z } from 'zod';
import { searchSchema } from './common';

// ==========================================
// 🔐 USER VALIDATION SCHEMAS
// ==========================================

/**
 * Schema crear usuario
 */
export const createUserSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  firstName: z.string().min(1, 'Nombre es requerido'),
  lastName: z.string().min(1, 'Apellido es requerido'),
  role: z.enum(['SUPER_ADMIN', 'ADMIN', 'CONTADOR', 'USER', 'VIEWER']).default('USER')
});

/**
 * Schema actualizar usuario
 */
export const updateUserSchema = z.object({
  email: z.string().email().optional(),
  firstName: z.string().min(1).optional(),
  lastName: z.string().min(1).optional(),
  role: z.enum(['SUPER_ADMIN', 'ADMIN', 'CONTADOR', 'USER', 'VIEWER']).optional(),
  isActive: z.boolean().optional()
});

/**
 * Schema login
 */
export const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña es requerida')
});

/**
 * Schema cambiar contraseña
 */
export const changePasswordSchema = z.object({
  currentPassword: z.string().min(1, 'Contraseña actual requerida'),
  newPassword: z.string().min(8, 'Nueva contraseña debe tener al menos 8 caracteres'),
  confirmPassword: z.string().min(8, 'Confirmación de contraseña requerida')
}).refine(data => data.newPassword === data.confirmPassword, {
  message: 'Las contraseñas no coinciden',
  path: ['confirmPassword']
});

/**
 * Schema listar usuarios con filtros
 */
export const listUsersSchema = searchSchema.extend({
  role: z.enum(['SUPER_ADMIN', 'ADMIN', 'CONTADOR', 'USER', 'VIEWER']).optional()
});

// ==========================================
// 🔑 AUTH INTERFACES
// ==========================================

/**
 * Payload token JWT estándar
 */
export interface TokenPayload {
  id?: string;          // Para compatibilidad websocket
  userId?: string;      // Estándar tRPC
  email: string;
  role?: string;
  companyId?: string;
  iat?: number;
  exp?: number;
}

/**
 * Interface usuario autenticado (para contexto)
 */
export interface AuthenticatedUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'SUPER_ADMIN' | 'ADMIN' | 'CONTADOR' | 'USER' | 'VIEWER';
  companyId?: string;
  isActive: boolean;
  lastLogin?: Date;
}

// ==========================================
// 👤 ROUTER OPERATION SCHEMAS
// ==========================================

/**
 * Schema para actualizar usuario con ID
 */
export const updateUserWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateUserSchema
});
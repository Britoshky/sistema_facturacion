import { z } from 'zod';

/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🏢 SCHEMAS COMPANY USERS - GESTIÓN EMPRESARIAL POR ROLES
 * ════════════════════════════════════════════════════════════════════════════════
 */

// Roles específicos por empresa (diferente al rol global del usuario)
export const companyRoleEnum = z.enum(['owner', 'admin', 'contador', 'user', 'viewer']);

// Schema para crear asignación usuario-empresa
export const createCompanyUserSchema = z.object({
  userId: z.string().uuid('ID de usuario inválido'),
  companyId: z.string().uuid('ID de empresa inválido'),
  roleInCompany: companyRoleEnum.default('user'),
  permissions: z.record(z.string(), z.boolean()).optional().default({}),
  isActive: z.boolean().default(true)
});

// Schema para actualizar asignación usuario-empresa
export const updateCompanyUserSchema = z.object({
  roleInCompany: companyRoleEnum.optional(),
  permissions: z.record(z.string(), z.boolean()).optional(),
  isActive: z.boolean().optional()
});

// Schema con ID para actualizaciones
export const updateCompanyUserWithIdSchema = z.object({
  id: z.string().uuid('ID de asignación inválido'),
  data: updateCompanyUserSchema
});

// Schema para listar usuarios de empresa
export const listCompanyUsersSchema = z.object({
  companyId: z.string().uuid('ID de empresa inválido'),
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(100).default(20),
  search: z.string().optional(),
  roleInCompany: companyRoleEnum.optional(),
  isActive: z.boolean().optional()
});

// Schema para listar empresas de usuario
export const listUserCompaniesSchema = z.object({
  userId: z.string().uuid('ID de usuario inválido'),
  isActive: z.boolean().optional().default(true)
});

// Schema para cambiar empresa activa
export const switchCompanySchema = z.object({
  companyId: z.string().uuid('ID de empresa inválido')
});

// Tipos TypeScript derivados
export type CompanyRole = z.infer<typeof companyRoleEnum>;
export type CreateCompanyUserInput = z.infer<typeof createCompanyUserSchema>;
export type UpdateCompanyUserInput = z.infer<typeof updateCompanyUserSchema>;
export type UpdateCompanyUserWithIdInput = z.infer<typeof updateCompanyUserWithIdSchema>;
export type ListCompanyUsersInput = z.infer<typeof listCompanyUsersSchema>;
export type ListUserCompaniesInput = z.infer<typeof listUserCompaniesSchema>;
export type SwitchCompanyInput = z.infer<typeof switchCompanySchema>;

// Interface para respuesta de usuario con empresa
export interface UserWithCompany {
  id: string; // ID del usuario
  assignmentId: string; // ID de la asignación (company_users.id)
  email: string;
  firstName: string;
  lastName: string;
  role: string; // Rol global
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  companyRole: CompanyRole; // Rol en la empresa específica
  permissions: Record<string, boolean>;
  joinedAt: Date;
}

// Interface para respuesta de empresa con rol
export interface CompanyWithRole {
  id: string;
  rut: string;
  businessName: string;
  commercialName?: string;
  address: string;
  commune: string;
  city: string;
  region: string;
  phone?: string;
  email?: string;
  website?: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  userRole: CompanyRole; // Rol del usuario en esta empresa
  permissions: Record<string, boolean>;
  joinedAt: Date;
}
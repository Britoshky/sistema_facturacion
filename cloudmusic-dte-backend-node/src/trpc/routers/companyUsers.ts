import { TRPCError } from '@trpc/server';
import { router, adminProcedure, managerProcedure, protectedProcedure } from '../init';
import {
  createCompanyUserSchema,
  updateCompanyUserWithIdSchema,
  listCompanyUsersSchema,
  listUserCompaniesSchema,
  switchCompanySchema,
  UserWithCompany,
  CompanyWithRole
} from '../schemas/companyUsers';
import { idSchema } from '../schemas/common';
import { logger } from '../../utils/logger';

// Helpers para WebSocket service
const getWebSocketService = () => {
  const globalScope = global as any;
  return globalScope.webSocketService;
};

const ensureWebSocketService = () => {
  const service = getWebSocketService();
  if (!service) {
    logger.warn('WebSocket service not available for company user events');
    return null;
  }
  return service;
};

const safeWebSocketOperation = async <T>(operation: () => Promise<T>): Promise<T | null> => {
  try {
    return await operation();
  } catch (error) {
    logger.error('WebSocket operation failed:', error);
    return null;
  }
};

/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🏢 ROUTER COMPANY USERS - GESTIÓN EMPRESARIAL POR ROLES
 * ════════════════════════════════════════════════════════════════════════════════
 */

export const companyUsersRouter = router({
  
  // Asignar usuario a empresa (Solo ADMIN/SUPER_ADMIN)
  assignUserToCompany: adminProcedure
    .input(createCompanyUserSchema)
    .mutation(async ({ ctx, input }) => {
      const { userId, companyId, roleInCompany, permissions, isActive } = input;

      // Verificar que el usuario y la empresa existen
      const [user, company] = await Promise.all([
        ctx.prisma.user.findUnique({ where: { id: userId } }),
        ctx.prisma.company.findUnique({ where: { id: companyId } })
      ]);

      if (!user) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Usuario no encontrado'
        });
      }

      if (!company) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Empresa no encontrada'
        });
      }

      // Si no es SUPER_ADMIN, verificar que puede asignar usuarios a esta empresa
      if (ctx.user.role !== 'SUPER_ADMIN') {
        // ADMIN solo puede asignar usuarios a empresas donde él es owner o admin
        const adminCompanyRelation = await ctx.prisma.companyUser.findFirst({
          where: {
            userId: ctx.user.id,
            companyId: companyId,
            roleInCompany: { in: ['owner', 'admin'] },
            isActive: true
          }
        });

        if (!adminCompanyRelation) {
          throw new TRPCError({
            code: 'FORBIDDEN',
            message: 'No tiene permisos para asignar usuarios a esta empresa'
          });
        }
      }

      // Verificar que no existe ya la relación
      const existingRelation = await ctx.prisma.companyUser.findUnique({
        where: {
          userId_companyId: {
            userId: userId,
            companyId: companyId
          }
        }
      });

      if (existingRelation) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'El usuario ya está asignado a esta empresa'
        });
      }

      // Crear la asignación
      const companyUser = await ctx.prisma.companyUser.create({
        data: {
          userId,
          companyId,
          roleInCompany,
          permissions: permissions || {},
          isActive
        },
        include: {
          user: {
            select: {
              id: true,
              email: true,
              firstName: true,
              lastName: true,
              role: true,
              isActive: true,
              createdAt: true,
              updatedAt: true
            }
          },
          company: {
            select: {
              id: true,
              rut: true,
              businessName: true,
              commercialName: true
            }
          }
        }
      });

      // Emitir evento WebSocket
      const wsService = ensureWebSocketService();
      if (wsService) {
        await safeWebSocketOperation(async () => {
          await wsService.broadcastCompanyUserEvent({
            assignment_id: companyUser.id,
            user_id: userId,
            company_id: companyId,
            action: 'assigned' as const,
            role: roleInCompany,
            user_name: `${user.firstName} ${user.lastName}`,
            company_name: company.businessName,
            performed_by: ctx.user.id
          }, companyId);
        });
      }

      return {
        message: 'Usuario asignado exitosamente a la empresa',
        assignment: companyUser
      };
    }),

  // Listar usuarios de una empresa
  getUsersByCompany: protectedProcedure
    .input(listCompanyUsersSchema)
    .query(async ({ ctx, input }) => {
      const { companyId, page, limit, search, roleInCompany, isActive } = input;

      // Verificar permisos para ver usuarios de esta empresa
      const isSystemAdmin = ['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role);
      if (!isSystemAdmin) {
        // Verificar que el usuario tiene permisos en esta empresa
        const userCompanyRelation = await ctx.prisma.companyUser.findFirst({
          where: {
            userId: ctx.user.id,
            companyId: companyId,
            roleInCompany: { in: ['owner', 'admin', 'contador'] },
            isActive: true
          }
        });

        if (!userCompanyRelation) {
          throw new TRPCError({
            code: 'FORBIDDEN',
            message: 'No tiene permisos para ver los usuarios de esta empresa'
          });
        }
      }

      const where = {
        companyId,
        ...(roleInCompany && { roleInCompany }),
        ...(isActive !== undefined && { isActive }),
        ...(search && {
          user: {
            OR: [
              { firstName: { contains: search, mode: 'insensitive' as const } },
              { lastName: { contains: search, mode: 'insensitive' as const } },
              { email: { contains: search, mode: 'insensitive' as const } }
            ]
          }
        })
      };

      const [companyUsers, total] = await Promise.all([
        ctx.prisma.companyUser.findMany({
          where,
          skip: (page - 1) * limit,
          take: limit,
          include: {
            user: {
              select: {
                id: true,
                email: true,
                firstName: true,
                lastName: true,
                role: true,
                isActive: true,
                createdAt: true,
                updatedAt: true
              }
            }
          },
          orderBy: { joinedAt: 'desc' }
        }),
        ctx.prisma.companyUser.count({ where })
      ]);

      const users: UserWithCompany[] = companyUsers.map(cu => ({
        id: cu.user.id,
        assignmentId: cu.id, // ¡AGREGAR ID DE LA ASIGNACIÓN!
        email: cu.user.email,
        firstName: cu.user.firstName,
        lastName: cu.user.lastName,
        role: cu.user.role,
        isActive: cu.user.isActive || false,
        createdAt: cu.user.createdAt || new Date(),
        updatedAt: cu.user.updatedAt || new Date(),
        companyRole: cu.roleInCompany as any,
        permissions: cu.permissions as Record<string, boolean> || {},
        joinedAt: cu.joinedAt || new Date()
      }));

      return {
        users,
        pagination: {
          page,
          limit,
          total,
          pages: Math.ceil(total / limit)
        }
      };
    }),

  // Listar empresas de un usuario
  getCompaniesByUser: protectedProcedure
    .input(listUserCompaniesSchema)
    .query(async ({ ctx, input }) => {
      const { userId, isActive } = input;

      // Solo ADMIN/SUPER_ADMIN pueden ver empresas de otros usuarios
      if (ctx.user.role !== 'SUPER_ADMIN' && ctx.user.role !== 'ADMIN' && ctx.user.id !== userId) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No tiene permisos para ver las empresas de este usuario'
        });
      }

      const companyUsers = await ctx.prisma.companyUser.findMany({
        where: {
          userId,
          ...(isActive !== undefined && { isActive })
        },
        include: {
          company: {
            select: {
              id: true,
              rut: true,
              businessName: true,
              commercialName: true,
              address: true,
              commune: true,
              city: true,
              region: true,
              phone: true,
              email: true,
              website: true,
              isActive: true,
              createdAt: true,
              updatedAt: true
            }
          }
        },
        orderBy: { joinedAt: 'desc' }
      });

      const companies: CompanyWithRole[] = companyUsers.map(cu => ({
        id: cu.company.id,
        rut: cu.company.rut,
        businessName: cu.company.businessName,
        commercialName: cu.company.commercialName || undefined,
        address: cu.company.address,
        commune: cu.company.commune,
        city: cu.company.city,
        region: cu.company.region,
        phone: cu.company.phone || undefined,
        email: cu.company.email || undefined,
        website: cu.company.website || undefined,
        isActive: cu.company.isActive || false,
        createdAt: cu.company.createdAt || new Date(),
        updatedAt: cu.company.updatedAt || new Date(),
        userRole: cu.roleInCompany as any,
        permissions: cu.permissions as Record<string, boolean> || {},
        joinedAt: cu.joinedAt || new Date()
      }));

      return companies;
    }),

  // Actualizar asignación usuario-empresa
  updateAssignment: managerProcedure
    .input(updateCompanyUserWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const { id, data } = input;

      // Buscar la asignación
      const existingAssignment = await ctx.prisma.companyUser.findUnique({
        where: { id },
        include: {
          user: true,
          company: true
        }
      });

      if (!existingAssignment) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Asignación no encontrada'
        });
      }

      // Verificar permisos
      const isSystemAdmin = ['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role);
      if (!isSystemAdmin) {
        // Verificar que puede modificar esta empresa
        const userCompanyRelation = await ctx.prisma.companyUser.findFirst({
          where: {
            userId: ctx.user.id,
            companyId: existingAssignment.companyId,
            roleInCompany: { in: ['owner', 'admin'] },
            isActive: true
          }
        });

        if (!userCompanyRelation) {
          throw new TRPCError({
            code: 'FORBIDDEN',
            message: 'No tiene permisos para modificar usuarios de esta empresa'
          });
        }
      }

      // Actualizar la asignación
      const updatedAssignment = await ctx.prisma.companyUser.update({
        where: { id },
        data: {
          ...(data.roleInCompany && { roleInCompany: data.roleInCompany }),
          ...(data.permissions && { permissions: data.permissions }),
          ...(data.isActive !== undefined && { isActive: data.isActive })
        },
        include: {
          user: {
            select: {
              id: true,
              email: true,
              firstName: true,
              lastName: true,
              role: true
            }
          },
          company: {
            select: {
              id: true,
              rut: true,
              businessName: true
            }
          }
        }
      });

      // Emitir evento WebSocket
      const wsService = ensureWebSocketService();
      if (wsService) {
        await safeWebSocketOperation(async () => {
          await wsService.broadcastCompanyUserEvent({
            assignment_id: updatedAssignment.id,
            user_id: updatedAssignment.userId,
            company_id: updatedAssignment.companyId,
            action: 'updated' as const,
            role: updatedAssignment.roleInCompany as any,
            user_name: `${updatedAssignment.user.firstName} ${updatedAssignment.user.lastName}`,
            company_name: updatedAssignment.company.businessName,
            performed_by: ctx.user.id
          }, updatedAssignment.companyId);
        });
      }

      return {
        message: 'Asignación actualizada exitosamente',
        assignment: updatedAssignment
      };
    }),

  // Remover usuario de empresa
  removeUserFromCompany: adminProcedure
    .input(idSchema)
    .mutation(async ({ ctx, input }) => {
      const { id } = input;

      // Buscar la asignación
      const assignment = await ctx.prisma.companyUser.findUnique({
        where: { id },
        include: {
          user: { select: { id: true, email: true, firstName: true, lastName: true } },
          company: { select: { id: true, businessName: true } }
        }
      });

      if (!assignment) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Asignación no encontrada'
        });
      }

      // Verificar permisos (misma lógica que update)
      const isSystemAdmin = ['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role);
      if (!isSystemAdmin) {
        const userCompanyRelation = await ctx.prisma.companyUser.findFirst({
          where: {
            userId: ctx.user.id,
            companyId: assignment.companyId,
            roleInCompany: { in: ['owner', 'admin'] },
            isActive: true
          }
        });

        if (!userCompanyRelation) {
          throw new TRPCError({
            code: 'FORBIDDEN',
            message: 'No tiene permisos para remover usuarios de esta empresa'
          });
        }
      }

      // Eliminar la asignación
      await ctx.prisma.companyUser.delete({
        where: { id }
      });

      // Emitir evento WebSocket
      const wsService = ensureWebSocketService();
      if (wsService) {
        await safeWebSocketOperation(async () => {
          await wsService.broadcastCompanyUserEvent({
            assignment_id: assignment.id,
            user_id: assignment.userId,
            company_id: assignment.companyId,
            action: 'removed' as const,
            user_name: `${assignment.user.firstName} ${assignment.user.lastName}`,
            company_name: assignment.company.businessName,
            performed_by: ctx.user.id
          }, assignment.companyId);
        });
      }

      return {
        message: `Usuario ${assignment.user.firstName} ${assignment.user.lastName} removido de ${assignment.company.businessName}`
      };
    })

});
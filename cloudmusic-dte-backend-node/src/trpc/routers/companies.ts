import { TRPCError } from '@trpc/server';
import { router, adminProcedure, managerProcedure, protectedProcedure } from '../init';
import { createCompanySchema, updateCompanySchema, updateCompanyWithIdSchema } from '../schemas/companies';
import { paginationSchema, idSchema } from '../schemas/common';
import { validateRUT } from '../../utils/helpers';

export const companiesRouter = router({
  // Listar empresas (filtradas por usuario, excepto SUPER_ADMIN que ve todas)
  list: protectedProcedure
    .input(paginationSchema.optional())
    .query(async ({ ctx, input }) => {
      const { page = 1, limit = 20 } = input || {};
      const { user } = ctx;
      
      // SUPER_ADMIN ve todas las empresas, otros usuarios solo las asignadas
      const isSuperAdmin = user.role === 'SUPER_ADMIN';
      
      let whereCondition;
      if (isSuperAdmin) {
        // SUPER_ADMIN ve todas las empresas activas
        whereCondition = { isActive: true };
      } else {
        // Otros usuarios (ADMIN, CONTADOR, USER, VIEWER) solo ven empresas asignadas
        const userCompanyIds = user.companies?.map(c => c.id) || [];
        
        if (userCompanyIds.length === 0) {
          // Si no tiene empresas asignadas, devolver lista vacía
          return {
            companies: [],
            pagination: {
              total: 0,
              page,
              limit,
              pages: 0
            }
          };
        }
        
        whereCondition = {
          isActive: true,
          id: { in: userCompanyIds }
        };
      }

      const [companies, total] = await Promise.all([
        ctx.prisma.company.findMany({
          where: whereCondition,
          include: {
            _count: {
              select: {
                companyUsers: true,
                certificates: true,
                folios: true
              }
            }
          },
          orderBy: { createdAt: 'desc' },
          skip: (page - 1) * limit,
          take: limit
        }),
        ctx.prisma.company.count({ where: whereCondition })
      ]);

      return {
        companies: companies.map((company: typeof companies[0]) => {
          // Obtener el rol del usuario en esta empresa específica
          const userCompanyInfo = user.companies?.find(c => c.id === company.id);
          
          return {
            id: company.id,
            businessName: company.businessName,
            rut: company.rut,
            economicActivity: company.economicActivity,
            businessLine: company.businessLine,
            address: company.address,
            commune: company.commune,
            city: company.city,
            phone: company.phone,
            email: company.email,
            website: company.website,
            isActive: company.isActive,
            createdAt: company.createdAt,
            updatedAt: company.updatedAt,
            totalUsers: company._count.companyUsers,
            totalCertificates: company._count.certificates,
            totalActiveFolios: company._count.folios,
            userRole: userCompanyInfo?.role || null, // Rol del usuario actual en esta empresa
            canManage: ['SUPER_ADMIN', 'ADMIN'].includes(user.role) || userCompanyInfo?.role === 'ADMIN'
          };
        }),
        pagination: {
          total,
          page,
          limit,
          pages: Math.ceil(total / limit)
        },
        userInfo: {
          role: user.role,
          isSuperAdmin,
          totalAssignedCompanies: user.companies?.length || 0
        }
      };
    }),

  // Obtener empresa por ID
  getById: protectedProcedure
    .input(idSchema)
    .query(async ({ ctx, input }) => {
      const { id } = input;

      // Verificar si es admin o si la empresa pertenece al usuario
      const isAdmin = ['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role);
      const userCompanyId = ctx.user.companyId;

      if (!isAdmin && userCompanyId !== id) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No tiene permisos para ver esta empresa'
        });
      }

      const company = await ctx.prisma.company.findUnique({
        where: { id },
        include: {
          companyUsers: {
            where: { isActive: true },
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  role: true,
                  lastLogin: true
                }
              }
            }
          },
          certificates: {
            where: { isActive: true },
            select: {
              id: true,
              certificateName: true,
              expiryDate: true,
              isDefault: true
            }
          },
          folios: {
            where: { isActive: true },
            select: {
              id: true,
              documentType: true,
              fromFolio: true,
              toFolio: true,
              currentFolio: true
            }
          }
        }
      });

      if (!company) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Empresa no encontrada'
        });
      }

      return company;
    }),

  // Crear empresa (solo SUPER_ADMIN)
  create: protectedProcedure
    .input(createCompanySchema)
    .mutation(async ({ ctx, input }) => {
      // Solo SUPER_ADMIN puede crear empresas
      if (ctx.user.role !== 'SUPER_ADMIN') {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Solo SUPER_ADMIN puede crear empresas'
        });
      }
      
      // Validar RUT
      const rutValidation = validateRUT(input.rut);
      if (!rutValidation.isValid) {
        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: 'RUT inválido',
          cause: rutValidation.error
        });
      }

      // Verificar que no exista otra empresa con el mismo RUT
      const existingCompany = await ctx.prisma.company.findFirst({
        where: {
          rut: rutValidation.formatted,
          isActive: true
        }
      });

      if (existingCompany) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'Ya existe una empresa activa con este RUT'
        });
      }

      const company = await ctx.prisma.company.create({
        data: {
          ...input,
          rut: rutValidation.formatted
        }
      });

      return {
        message: 'Empresa creada exitosamente',
        company
      };
    }),

  // Actualizar empresa
  update: managerProcedure
    .input(updateCompanyWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const { id, data } = input;

      // Verificar permisos
      const isAdmin = ['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role);
      const userCompanyId = ctx.user.companyId;

      if (!isAdmin && userCompanyId !== id) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No tiene permisos para modificar esta empresa'
        });
      }

      // Verificar que la empresa existe
      const existingCompany = await ctx.prisma.company.findUnique({
        where: { id }
      });

      if (!existingCompany) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Empresa no encontrada'
        });
      }

      const updateData = { ...data };

      // Validar RUT si se está actualizando
      if (data.rut) {
        const rutValidation = validateRUT(data.rut);
        if (!rutValidation.isValid) {
          throw new TRPCError({
            code: 'BAD_REQUEST',
            message: 'RUT inválido',
            cause: rutValidation.error
          });
        }

        // Verificar que no exista otra empresa con el mismo RUT
        const duplicateCompany = await ctx.prisma.company.findFirst({
          where: {
            rut: rutValidation.formatted,
            isActive: true,
            id: { not: id }
          }
        });

        if (duplicateCompany) {
          throw new TRPCError({
            code: 'CONFLICT',
            message: 'Ya existe otra empresa activa con este RUT'
          });
        }

        updateData.rut = rutValidation.formatted;
      }

      const company = await ctx.prisma.company.update({
        where: { id },
        data: updateData
      });

      return {
        message: 'Empresa actualizada exitosamente',
        company
      };
    }),

  // Desactivar empresa (solo SUPER_ADMIN)
  delete: protectedProcedure
    .input(idSchema)
    .mutation(async ({ ctx, input }) => {
      const { id } = input;
      
      // Solo SUPER_ADMIN puede eliminar empresas
      if (ctx.user.role !== 'SUPER_ADMIN') {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Solo SUPER_ADMIN puede eliminar empresas'
        });
      }

      const company = await ctx.prisma.company.findUnique({
        where: { id }
      });

      if (!company) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Empresa no encontrada'
        });
      }

      // Verificar si tiene documentos asociados
      const documentsCount = await ctx.prisma.document.count({
        where: { companyId: id }
      });

      if (documentsCount > 0) {
        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: 'No se puede eliminar la empresa porque tiene documentos asociados',
          cause: { documentsCount }
        });
      }

      await ctx.prisma.company.update({
        where: { id },
        data: { isActive: false }
      });

      return {
        message: 'Empresa desactivada exitosamente'
      };
    })
});
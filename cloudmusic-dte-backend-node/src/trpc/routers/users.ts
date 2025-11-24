import { router, adminProcedure, protectedProcedure } from '../init';
import { 
  createUserSchema, 
  updateUserSchema,
  listUsersSchema,
  updateUserWithIdSchema
} from '../schemas/users';
import { idSchema } from '../schemas/common';
import { TRPCError } from '@trpc/server';

export const usersRouter = router({
  // Crear nuevo usuario - Permisos diferenciados
  create: protectedProcedure
    .input(createUserSchema)
    .mutation(async ({ ctx, input }) => {
      // SUPER_ADMIN: Puede crear cualquier rol
      // ADMIN: Puede crear CONTADOR, USER, VIEWER (NO puede crear SUPER_ADMIN ni otros ADMIN)
      // CONTADOR: NO puede crear usuarios
      // USER: NO puede crear usuarios
      // VIEWER: NO puede crear usuarios
      
      if (!['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role)) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No tienes permisos para crear usuarios'
        });
      }
      
      // ADMIN no puede crear SUPER_ADMIN ni otros ADMIN
      if (ctx.user.role === 'ADMIN' && ['SUPER_ADMIN', 'ADMIN'].includes(input.role)) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Solo SUPER_ADMIN puede crear usuarios SUPER_ADMIN o ADMIN'
        });
      }
      const { email, password, ...userData } = input;
      
      // Verificar si el usuario ya existe
      const existingUser = await ctx.prisma.user.findUnique({
        where: { email }
      });

      if (existingUser) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'El usuario ya existe'
        });
      }

      return await ctx.prisma.user.create({
        data: {
          email,
          passwordHash: password,
          ...userData,
        },
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
      });
    }),

  // Obtener todos los usuarios - Permisos diferenciados
  getAll: protectedProcedure
    .input(listUsersSchema)
    .query(async ({ ctx, input }) => {
      // SUPER_ADMIN: Ve todos los usuarios
      // ADMIN: Ve usuarios de roles inferiores (CONTADOR, USER, VIEWER)
      // CONTADOR: NO puede listar usuarios
      // USER: NO puede listar usuarios
      // VIEWER: NO puede listar usuarios
      
      if (!['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role)) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No tienes permisos para listar usuarios'
        });
      }
      const { page, limit, search, role } = input;
      const skip = (page - 1) * limit;

      const where = {
        ...(search && {
          OR: [
            { firstName: { contains: search, mode: 'insensitive' as const } },
            { lastName: { contains: search, mode: 'insensitive' as const } },
            { email: { contains: search, mode: 'insensitive' as const } }
          ]
        }),
        ...(role && { role })
      };

      const [users, total] = await Promise.all([
        ctx.prisma.user.findMany({
          where,
          skip,
          take: limit,
          select: {
            id: true,
            email: true,
            firstName: true,
            lastName: true,
            role: true,
            isActive: true,
            createdAt: true,
            updatedAt: true
          },
          orderBy: { createdAt: 'desc' }
        }),
        ctx.prisma.user.count({ where })
      ]);

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

  // Obtener usuario por ID - Permisos diferenciados por rol
  getById: protectedProcedure
    .input(idSchema)
    .query(async ({ ctx, input }) => {
      const { id } = input;
      
      // SUPER_ADMIN: Puede ver todos los usuarios
      // ADMIN: Puede ver usuarios de roles inferiores + su propio perfil
      // CONTADOR: Solo puede ver su propio perfil
      // USER: Solo puede ver su propio perfil  
      // VIEWER: Solo puede ver su propio perfil
      
      if (ctx.user.role === 'SUPER_ADMIN') {
        // SUPER_ADMIN puede ver cualquier usuario
      } else if (ctx.user.role === 'ADMIN') {
        // ADMIN puede ver usuarios excepto otros SUPER_ADMIN (a menos que sea su propio perfil)
        if (ctx.user.id !== id) {
          const targetUser = await ctx.prisma.user.findUnique({ where: { id } });
          if (targetUser?.role.toUpperCase() === 'SUPER_ADMIN') {
            throw new TRPCError({
              code: 'FORBIDDEN',
              message: 'No tienes permisos para ver este SUPER_ADMIN'
            });
          }
        }
      } else {
        // CONTADOR, USER, VIEWER: Solo pueden verse a sí mismos
        if (ctx.user.id !== id) {
          throw new TRPCError({
            code: 'FORBIDDEN',
            message: 'Solo puedes ver tu propio perfil'
          });
        }
      }

      const user = await ctx.prisma.user.findUnique({
        where: { id },
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
      });

      if (!user) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Usuario no encontrado'
        });
      }

      return user;
    }),

  // Actualizar usuario - Admin o el propio usuario (con restricciones)
  update: protectedProcedure
    .input(updateUserWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const { id, data } = input;
      
      // Verificar que el usuario a actualizar existe primero
      const targetUser = await ctx.prisma.user.findUnique({
        where: { id }
      });

      if (!targetUser) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Usuario no encontrado'
        });
      }
      
      // REGLA: Solo SUPER_ADMIN puede editar otros SUPER_ADMIN
      if (targetUser.role.toUpperCase() === 'SUPER_ADMIN' && ctx.user.role !== 'SUPER_ADMIN') {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Solo SUPER_ADMIN puede editar otros SUPER_ADMIN'
        });
      }
      
      // REGLA: Solo admin o superior puede actualizar otros usuarios
      if (!['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role) && ctx.user.id !== id) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No tienes permisos para actualizar este usuario'
        });
      }

      // REGLA: Los usuarios no admin no pueden cambiar roles
      if (!['SUPER_ADMIN', 'ADMIN'].includes(ctx.user.role) && data.role) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'No puedes cambiar roles de usuarios'
        });
      }
      
      // REGLA: Solo SUPER_ADMIN puede asignar rol SUPER_ADMIN
      if (data.role?.toUpperCase() === 'SUPER_ADMIN' && ctx.user.role !== 'SUPER_ADMIN') {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Solo SUPER_ADMIN puede asignar el rol SUPER_ADMIN'
        });
      }

      // Preparar datos para actualización (normalizar rol a minúsculas para BD)
      const cleanData: any = { ...data };
      if (cleanData.role) {
        cleanData.role = cleanData.role.toLowerCase(); // BD usa minúsculas
      }
      
      // Agregar timestamp de actualización
      cleanData.updatedAt = new Date();

      return await ctx.prisma.user.update({
        where: { id },
        data: cleanData,
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
      });
    }),

  // Desactivar usuario - Permisos diferenciados
  deactivate: protectedProcedure
    .input(idSchema)
    .mutation(async ({ ctx, input }) => {
      const { id } = input;

      const targetUser = await ctx.prisma.user.findUnique({
        where: { id }
      });

      if (!targetUser) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Usuario no encontrado'
        });
      }
      
      // SUPER_ADMIN: Puede desactivar cualquier usuario (excepto a sí mismo)
      // ADMIN: Puede desactivar CONTADOR, USER, VIEWER (NO SUPER_ADMIN ni otros ADMIN)
      // Otros roles: NO pueden desactivar usuarios
      
      if (ctx.user.id === id) {
        throw new TRPCError({ code: 'FORBIDDEN', message: 'No puedes desactivarte a ti mismo' });
      }
      
      if (ctx.user.role === 'SUPER_ADMIN') {
        // Puede desactivar cualquier usuario
      } else if (ctx.user.role === 'ADMIN') {
        if (['super_admin', 'admin'].includes(targetUser.role.toLowerCase())) {
          throw new TRPCError({ 
            code: 'FORBIDDEN', 
            message: 'No puedes desactivar usuarios SUPER_ADMIN o ADMIN' 
          });
        }
      } else {
        throw new TRPCError({ 
          code: 'FORBIDDEN', 
          message: 'No tienes permisos para desactivar usuarios' 
        });
      }

      return await ctx.prisma.user.update({
        where: { id },
        data: { isActive: false },
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
      });
    }),

  // Activar usuario - Permisos diferenciados
  activate: protectedProcedure
    .input(idSchema)
    .mutation(async ({ ctx, input }) => {
      const { id } = input;

      const targetUser = await ctx.prisma.user.findUnique({
        where: { id }
      });

      if (!targetUser) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Usuario no encontrado'
        });
      }
      
      // Mismos permisos que desactivar
      if (ctx.user.role === 'SUPER_ADMIN') {
        // Puede activar cualquier usuario
      } else if (ctx.user.role === 'ADMIN') {
        if (['super_admin', 'admin'].includes(targetUser.role.toLowerCase())) {
          throw new TRPCError({ 
            code: 'FORBIDDEN', 
            message: 'No puedes activar usuarios SUPER_ADMIN o ADMIN' 
          });
        }
      } else {
        throw new TRPCError({ 
          code: 'FORBIDDEN', 
          message: 'No tienes permisos para activar usuarios' 
        });
      }

      return await ctx.prisma.user.update({
        where: { id },
        data: { isActive: true },
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
      });
    }),

});
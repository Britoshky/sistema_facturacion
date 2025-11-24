import { TRPCError } from '@trpc/server';
import bcrypt from 'bcrypt';
import { router, publicProcedure, protectedProcedure } from '../init';
import { loginSchema } from '../schemas/users';
import { generateTokens, getSessionManager } from '../../middleware/auth';

export const authRouter = router({
  login: publicProcedure
    .input(loginSchema)
    .mutation(async ({ input, ctx }) => {
      const { email, password } = input;

      // Buscar usuario
      const user = await ctx.prisma.user.findUnique({
        where: { email },
        include: {
          companyUsers: {
            where: { isActive: true },
            include: {
              company: true
            }
          }
        }
      });

      if (!user || !user.isActive) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Credenciales inválidas'
        });
      }

      // Verificar contraseña
      let isPasswordValid = false;
      
      // Primero intentar bcrypt (para hashes modernos)
      try {
        isPasswordValid = await bcrypt.compare(password, user.passwordHash);
      } catch (error) {
        console.log('❌ Error en bcrypt.compare:', error);
      }
      
      // Si bcrypt falla, verificar si es una contraseña en texto plano (SOLO DESARROLLO)
      if (!isPasswordValid && process.env.NODE_ENV !== 'production') {
        isPasswordValid = password === user.passwordHash;
        
        // Si coincide, actualizar a hash bcrypt para la próxima vez
        if (isPasswordValid) {
          const newHash = await bcrypt.hash(password, 12);
          await ctx.prisma.user.update({
            where: { id: user.id },
            data: { passwordHash: newHash }
          });
          console.log(`🔐 Password actualizada a bcrypt para ${user.email}`);
        }
      }
      
      if (!isPasswordValid) {
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Credenciales inválidas'
        });
      }

      // Actualizar último login
      await ctx.prisma.user.update({
        where: { id: user.id },
        data: { lastLogin: new Date() }
      });

      const primaryCompany = user.companyUsers[0]?.company;

      // Crear sesión en Redis
      const sessionManager = getSessionManager();
      const sessionId = await sessionManager.createSession({
        userId: user.id,
        email: user.email,
        role: user.role.toUpperCase(), // Normalizar rol
        companyId: primaryCompany?.id || '',
        ipAddress: ctx.req?.ip,
        userAgent: ctx.req?.headers['user-agent']
      });

      // Generar tokens con sessionId
      const { accessToken, refreshToken } = generateTokens({
        id: user.id,
        email: user.email,
        role: user.role.toUpperCase() as any, // Normalizar rol
        companyId: primaryCompany?.id || '',
        sessionId
      });

      return {
        user: {
          id: user.id,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          role: user.role.toUpperCase(), // Normalizar rol a mayúsculas
          company: primaryCompany ? {
            id: primaryCompany.id,
            name: primaryCompany.businessName || primaryCompany.commercialName || 'Empresa',
            rut: primaryCompany.rut
          } : null,
          companies: user.companyUsers.map((cu: any) => ({
            id: cu.company.id,
            businessName: cu.company.businessName || cu.company.commercialName || 'Empresa',
            rut: cu.company.rut,
            role: cu.roleInCompany,
            joinedAt: cu.joinedAt
          }))
        },
        tokens: {
          accessToken,
          refreshToken
        }
      };
    }),

  profile: protectedProcedure
    .query(async ({ ctx }) => {
      const user = await ctx.prisma.user.findUnique({
        where: { id: ctx.user.id },
        include: {
          companyUsers: {
            where: { isActive: true },
            include: {
              company: true
            }
          }
        }
      });

      if (!user) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Usuario no encontrado'
        });
      }

      return {
        id: user.id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role.toUpperCase(), // Normalizar rol a mayúsculas
        isActive: user.isActive,
        lastLogin: user.lastLogin,
        companies: user.companyUsers.map((cu: typeof user.companyUsers[0]) => ({
          id: cu.company.id,
          name: cu.company.businessName || cu.company.commercialName || 'Empresa',
          rut: cu.company.rut,
          role: (cu as any).roleInCompany || 'user',
          joinedAt: cu.joinedAt
        }))
      };
    }),

  logout: protectedProcedure
    .mutation(async ({ ctx }) => {
      try {
        const sessionManager = getSessionManager();
        
        // Invalidar sesión actual si existe sessionId en el token
        if (ctx.user?.sessionId) {
          await sessionManager.invalidateSession(ctx.user.sessionId);
          console.log(`🚪 Logout: Sesión ${ctx.user.sessionId} invalidada para usuario ${ctx.user.id}`);
        } else {
          // Invalidar todas las sesiones del usuario como fallback
          await sessionManager.invalidateAllUserSessions(ctx.user?.id || '');
          console.log(`🚪 Logout: Todas las sesiones invalidadas para usuario ${ctx.user?.id}`);
        }
        
        return {
          success: true,
          message: 'Sesión cerrada exitosamente'
        };
      } catch (error) {
        console.error('❌ Error en logout:', error);
        return {
          success: true, // Siempre retornamos éxito para permitir logout del frontend
          message: 'Sesión cerrada'
        };
      }
    }),

  verify: protectedProcedure
    .query(({ ctx }) => {
      return {
        valid: true,
        user: ctx.user
      };
    })
});
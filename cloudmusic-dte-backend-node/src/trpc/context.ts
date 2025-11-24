import { inferAsyncReturnType } from '@trpc/server';
import { CreateExpressContextOptions } from '@trpc/server/adapters/express';
import { prisma } from '../models/database';
import { verifyToken, getSessionManager } from '../middleware/auth';

// Contexto tRPC que se pasa a todos los procedures
export const createContext = async ({ req, res }: CreateExpressContextOptions) => {
  // Función para obtener usuario autenticado con validación de sesión
  const getUser = async () => {
    try {
      const token = req.headers.authorization?.replace('Bearer ', '');
      
      if (!token) {
        return null;
      }

      // 1. Verificar token JWT
      const decoded = verifyToken(token);
      
      if (!decoded.sessionId) {
        console.log('❌ Token sin sessionId - sesión inválida');
        return null;
      }

      // 2. Validar sesión en Redis
      const sessionManager = getSessionManager();
      const sessionData = await sessionManager.validateSession(decoded.sessionId);
      
      if (!sessionData) {
        console.log(`❌ Sesión ${decoded.sessionId} no válida o expirada`);
        return null;
      }

      // 3. Verificar usuario en base de datos
      const user = await prisma.user.findUnique({
        where: { id: decoded.id },
        include: {
          companyUsers: {
            where: { isActive: true },
            include: {
              company: {
                select: {
                  id: true,
                  businessName: true,
                  rut: true
                }
              }
            }
          }
        }
      });

      if (!user || !user.isActive) {
        console.log(`❌ Usuario ${decoded.id} no encontrado o inactivo`);
        return null;
      }

      // Obtener empresa activa desde header o la primera disponible
      const activeCompanyId = req.headers['x-active-company'] as string;
      let activeCompany = null;
      let activeCompanyRole = null;
      
      if (activeCompanyId && user.companyUsers.length > 0) {
        // Buscar la empresa específica en las asignaciones del usuario
        const companyRelation = user.companyUsers.find(cu => cu.companyId === activeCompanyId);
        if (companyRelation) {
          activeCompany = companyRelation.company;
          activeCompanyRole = companyRelation.roleInCompany;
        }
      }
      
      // Si no se encontró empresa activa, usar la primera disponible
      if (!activeCompany && user.companyUsers.length > 0) {
        const firstRelation = user.companyUsers[0];
        activeCompany = firstRelation.company;
        activeCompanyRole = firstRelation.roleInCompany;
      }

      return {
        id: user.id,
        email: user.email,
        role: user.role.toUpperCase(), // Rol global del sistema
        companyId: activeCompany?.id || null,
        company: activeCompany || null,
        companyRole: activeCompanyRole || null, // Rol específico en la empresa activa
        companies: user.companyUsers.map(cu => ({
          id: cu.company.id,
          businessName: cu.company.businessName,
          rut: cu.company.rut,
          role: cu.roleInCompany,
          isActive: cu.isActive
        })),
        sessionId: decoded.sessionId  // Incluir sessionId para logout
      };
    } catch (error) {
      console.error('❌ Error validando usuario:', error);
      return null;
    }
  };

  return {
    req,
    res,
    prisma,
    user: await getUser()
  };
};

export type Context = inferAsyncReturnType<typeof createContext>;
import { initTRPC, TRPCError } from '@trpc/server';
import { Context } from './context';
import { ZodError } from 'zod';

// Inicializar tRPC
const t = initTRPC.context<Context>().create({
  errorFormatter({ shape, error }) {
    return {
      ...shape,
      data: {
        ...shape.data,
        zodError:
          error.cause instanceof ZodError ? error.cause.flatten() : null,
      },
    };
  },
});

// Exportar helpers reutilizables
export const router = t.router;
export const publicProcedure = t.procedure;

// Middleware de autenticación
const isAuthed = t.middleware(({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({
    ctx: {
      ...ctx,
      user: ctx.user, // user is now non-nullable
    },
  });
});

// Middleware para requerir empresa
const requireCompany = t.middleware(({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  if (!ctx.user.companyId) {
    throw new TRPCError({ 
      code: 'FORBIDDEN', 
      message: 'Usuario debe estar asociado a una empresa' 
    });
  }
  return next({
    ctx: {
      ...ctx,
      user: {
        ...ctx.user,
        companyId: ctx.user.companyId! // Garantizamos que no es null
      }
    },
  });
});

// Middleware para roles específicos
const requireRole = (roles: string[]) => 
  t.middleware(({ ctx, next }) => {
    if (!ctx.user) {
      throw new TRPCError({ code: 'UNAUTHORIZED' });
    }
    if (!roles.includes(ctx.user.role)) {
      throw new TRPCError({ 
        code: 'FORBIDDEN', 
        message: `Requiere uno de los roles: ${roles.join(', ')}` 
      });
    }
    return next({
      ctx: {
        ...ctx,
        user: ctx.user,
      },
    });
  });

// Procedures protegidos
export const protectedProcedure = publicProcedure.use(isAuthed);
export const companyProcedure = publicProcedure.use(isAuthed).use(requireCompany);
export const adminProcedure = publicProcedure.use(isAuthed).use(requireRole(['SUPER_ADMIN', 'ADMIN']));
export const managerProcedure = publicProcedure.use(isAuthed).use(requireRole(['SUPER_ADMIN', 'ADMIN', 'CONTADOR']));
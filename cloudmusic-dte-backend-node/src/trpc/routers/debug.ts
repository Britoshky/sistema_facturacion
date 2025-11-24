import { router, publicProcedure } from '../init';

export const debugRouter = router({
  checkUsers: publicProcedure
    .query(async ({ ctx }) => {
      try {
        const users = await ctx.prisma.user.findMany({
          select: {
            id: true,
            email: true,
            firstName: true,
            lastName: true,
            isActive: true,
          }
        });
        
        const userCount = await ctx.prisma.user.count();
        
        return {
          success: true,
          userCount,
          users: users.slice(0, 5) // Solo los primeros 5 para no sobrecargar
        };
      } catch (error) {
        console.error('Database error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }),

  dbStatus: publicProcedure
    .query(async ({ ctx }) => {
      try {
        // Probar conexión básica
        await ctx.prisma.$queryRaw`SELECT 1 as test`;
        
        return {
          success: true,
          message: 'Database connection working',
          timestamp: new Date().toISOString()
        };
      } catch (error) {
        console.error('Database connection error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Connection failed'
        };
      }
    })
});
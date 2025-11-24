import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { 
  createFolioSchema, 
  updateFolioSchema, 
  FolioAlert,
  getFolioByIdSchema,
  updateFolioWithIdSchema,
  deleteFolioSchema,
  importCAFSchema,
  getNextFolioAvailableSchema,
  getFolioStatsSchema
} from '../schemas/folios';
import { cafService } from '../../services/cafService';

export const foliosRouter = router({
  // Listar folios
  list: companyProcedure
    .query(async ({ ctx }) => {
      const folios = await ctx.prisma.folio.findMany({
        where: { companyId: ctx.user.companyId },
        orderBy: { createdAt: 'desc' }
      });

      return folios.map((folio: typeof folios[0]) => ({
        id: folio.id,
        documentType: folio.documentType,
        fromFolio: folio.fromFolio,
        toFolio: folio.toFolio,
        currentFolio: folio.currentFolio,
        isActive: folio.isActive,
        createdAt: folio.createdAt
      }));
    }),

  // Obtener por ID
  getById: companyProcedure
    .input(getFolioByIdSchema)
    .query(async ({ ctx, input }) => {
      const folio = await ctx.prisma.folio.findFirst({
        where: {
          id: input.id,
          companyId: ctx.user.companyId
        }
      });

      if (!folio) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Folio no encontrado'
        });
      }

      return {
        id: folio.id,
        documentType: folio.documentType,
        fromFolio: folio.fromFolio,
        toFolio: folio.toFolio,
        currentFolio: folio.currentFolio,
        isActive: folio.isActive,
        createdAt: folio.createdAt
      };
    }),

  // Crear folio
  create: companyProcedure
    .input(createFolioSchema)
    .mutation(async ({ ctx, input }) => {
      const folio = await ctx.prisma.folio.create({
        data: {
          companyId: ctx.user.companyId,
          documentType: input.documentType,
          fromFolio: input.fromFolio,
          toFolio: input.toFolio,
          currentFolio: input.fromFolio,
          cafFile: input.cafFile,
          authorizationDate: new Date(),
          expiryDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)
        }
      });

      return {
        id: folio.id,
        documentType: folio.documentType,
        fromFolio: folio.fromFolio,
        toFolio: folio.toFolio,
        currentFolio: folio.currentFolio,
        isActive: folio.isActive
      };
    }),

  // Actualizar folio
  update: companyProcedure
    .input(updateFolioWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const folio = await ctx.prisma.folio.update({
        where: { id: input.id },
        data: input.data
      });

      return {
        id: folio.id,
        documentType: folio.documentType,
        currentFolio: folio.currentFolio,
        isActive: folio.isActive
      };
    }),

  // Eliminar folio
  delete: companyProcedure
    .input(deleteFolioSchema)
    .mutation(async ({ ctx, input }) => {
      await ctx.prisma.folio.update({
        where: { id: input.id },
        data: { isActive: false }
      });

      return { success: true };
    }),

  // RF008: Importar archivo CAF XML
  importCAF: companyProcedure
    .input(importCAFSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        // 1. Validar e importar CAF
        const importResult = await cafService.importCAF(input.cafXmlContent, ctx.user.companyId);
        
        if (!importResult.isValid) {
          throw new TRPCError({
            code: 'BAD_REQUEST',
            message: `Error importando CAF: ${importResult.errors.join(', ')}`
          });
        }

        const cafData = importResult.cafData!;

        // 2. Verificar que no existe overlap con folios existentes
        const existingFolios = await ctx.prisma.folio.findMany({
          where: {
            companyId: ctx.user.companyId,
            documentType: cafData.documentType,
            isActive: true,
            OR: [
              {
                AND: [
                  { fromFolio: { lte: cafData.fromFolio } },
                  { toFolio: { gte: cafData.fromFolio } }
                ]
              },
              {
                AND: [
                  { fromFolio: { lte: cafData.toFolio } },
                  { toFolio: { gte: cafData.toFolio } }
                ]
              }
            ]
          }
        });

        if (existingFolios.length > 0) {
          throw new TRPCError({
            code: 'CONFLICT',
            message: `Rango de folios se superpone con folios existentes`
          });
        }

        // 3. Crear registro de folio en base de datos
        const folio = await ctx.prisma.folio.create({
          data: {
            companyId: ctx.user.companyId,
            documentType: cafData.documentType,
            fromFolio: cafData.fromFolio,
            toFolio: cafData.toFolio,
            currentFolio: cafData.fromFolio - 1, // Empezar antes del primer folio
            cafFile: input.cafXmlContent,
            authorizationDate: cafData.authorizationDate,
            expiryDate: cafData.expiryDate,
            isActive: true
          }
        });

        return {
          id: folio.id,
          documentType: folio.documentType,
          fromFolio: folio.fromFolio,
          toFolio: folio.toFolio,
          authorizedRange: cafData.authorizedRange,
          warnings: importResult.warnings
        };

      } catch (error) {
        if (error instanceof TRPCError) {
          throw error;
        }
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error interno importando CAF'
        });
      }
    }),

  // RF008: Obtener siguiente folio disponible con control de secuencia
  getNextFolio: companyProcedure
    .input(getNextFolioAvailableSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        // 1. Buscar folio activo para el tipo de documento
        const folio = await ctx.prisma.folio.findFirst({
          where: {
            companyId: ctx.user.companyId,
            documentType: input.documentType,
            isActive: true
          },
          orderBy: { createdAt: 'asc' } // FIFO
        });

        if (!folio) {
          throw new TRPCError({
            code: 'NOT_FOUND',
            message: 'No hay folios disponibles para este tipo de documento'
          });
        }

        // 2. Incrementar folio actual
        const nextFolioNumber = folio.currentFolio + 1;

        // 3. Verificar que no excede el rango
        if (nextFolioNumber > folio.toFolio) {
          throw new TRPCError({
            code: 'BAD_REQUEST',
            message: 'Rango de folios agotado'
          });
        }

        // 4. Actualizar folio actual
        const updatedFolio = await ctx.prisma.folio.update({
          where: { id: folio.id },
          data: { currentFolio: nextFolioNumber }
        });

        // 5. Calcular folios restantes y generar alerta si es necesario
        const remainingFolios = folio.toFolio - nextFolioNumber;
        let alertGenerated = false;

        if (remainingFolios <= 50) { // RF008: Alerta con 50 folios restantes
          // Aquí se podría enviar evento via WebSocket/Redis para alertas
          alertGenerated = true;
        }

        return {
          folio: nextFolioNumber,
          folioId: updatedFolio.id,
          remainingFolios,
          alertGenerated,
          alertThreshold: remainingFolios <= 50
        };

      } catch (error) {
        if (error instanceof TRPCError) {
          throw error;
        }
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error obteniendo siguiente folio'
        });
      }
    }),

  // RF008: Generar alertas de folios bajos
  getAlerts: companyProcedure
    .query(async ({ ctx }) => {
      try {
        const folios = await ctx.prisma.folio.findMany({
          where: {
            companyId: ctx.user.companyId,
            isActive: true
          }
        });

        const alerts: FolioAlert[] = [];

        for (const folio of folios) {
          const remainingFolios = folio.toFolio - folio.currentFolio;
          const totalFolios = folio.toFolio - folio.fromFolio + 1;
          
          let severity: 'warning' | 'critical' | 'info' = 'info';
          let message = '';

          if (remainingFolios <= 10) {
            severity = 'critical';
            message = `¡CRÍTICO! Solo quedan ${remainingFolios} folios para tipo ${folio.documentType}`;
          } else if (remainingFolios <= 50) {
            severity = 'warning';
            message = `Advertencia: Quedan ${remainingFolios} folios para tipo ${folio.documentType}`;
          } else {
            continue; // No generar alerta si no es necesario
          }

          alerts.push({
            companyId: ctx.user.companyId,
            documentType: folio.documentType,
            currentFolio: folio.currentFolio,
            remainingFolios,
            totalFolios,
            alertThreshold: 50,
            severity,
            message
          });
        }

        return alerts;

      } catch (error) {
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error generando alertas de folios'
        });
      }
    }),

  // RF008: Obtener estadísticas de uso de folios
  getStats: companyProcedure
    .input(getFolioStatsSchema)
    .query(async ({ ctx, input }) => {
      try {
        const whereClause: {
          companyId: string;
          isActive: boolean;
          documentType?: number;
        } = {
          companyId: ctx.user.companyId,
          isActive: true
        };

        if (input.documentType) {
          whereClause.documentType = input.documentType;
        }

        const folios = await ctx.prisma.folio.findMany({
          where: whereClause,
          include: {
            _count: {
              select: {
                documents: true
              }
            }
          }
        });

        const stats = folios.map((folio: typeof folios[0]) => {
          const totalFolios = folio.toFolio - folio.fromFolio + 1;
          const usedFolios = folio.currentFolio - folio.fromFolio + 1;
          const remainingFolios = folio.toFolio - folio.currentFolio;
          const usagePercentage = (usedFolios / totalFolios) * 100;

          let alertLevel: 'ok' | 'warning' | 'critical' = 'ok';
          if (remainingFolios <= 10) {
            alertLevel = 'critical';
          } else if (remainingFolios <= 50) {
            alertLevel = 'warning';
          }

          return {
            folioId: folio.id,
            documentType: folio.documentType,
            fromFolio: folio.fromFolio,
            toFolio: folio.toFolio,
            currentFolio: folio.currentFolio,
            totalFolios,
            usedFolios,
            remainingFolios,
            usagePercentage,
            documentsCreated: folio._count.documents,
            alertLevel,
            expiryDate: folio.expiryDate,
            isExpiringSoon: folio.expiryDate ? 
              (folio.expiryDate.getTime() - Date.now()) < (30 * 24 * 60 * 60 * 1000) : false
          };
        });

        return stats;

      } catch (error) {
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error obteniendo estadísticas de folios'
        });
      }
    })
});
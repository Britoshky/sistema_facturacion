/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 📊 REPORTS ROUTER - CLOUDMUSIC DTE BACKEND
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Router tRPC para gestión de reportes y analytics usando Prisma:
 * ✅ Métricas del dashboard
 * ✅ Reportes de ventas
 * ✅ Reportes de documentos
 * ✅ Analytics de clientes
 * ✅ Datos de productos
 */

import { z } from 'zod';
import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';

// ==========================================
// 📋 SCHEMAS DE VALIDACIÓN
// ==========================================

const reportTypeSchema = z.enum(['sales', 'documents', 'tax', 'clients', 'products']);
const reportPeriodSchema = z.enum(['daily', 'weekly', 'monthly', 'quarterly', 'yearly']);

const generateReportSchema = z.object({
  type: reportTypeSchema,
  period: reportPeriodSchema,
  startDate: z.string().datetime().optional(),
  endDate: z.string().datetime().optional(),
  filters: z.record(z.string(), z.any()).optional()
});

const dashboardMetricsSchema = z.object({
  period: reportPeriodSchema.optional().default('monthly')
});

// ==========================================
// 📊 REPORTS ROUTER
// ==========================================

export const reportsRouter = router({
  /**
   * Obtener métricas del dashboard usando Prisma
   */
  getDashboardMetrics: companyProcedure
    .input(dashboardMetricsSchema)
    .query(async ({ ctx, input }) => {
      try {
        const { prisma, user } = ctx;
        const companyId = user.companyId;

        // Fecha límite para documentos recientes (últimos 30 días)
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        // Obtener métricas de documentos usando Prisma
        const [documentsCount, documentsRevenue, pendingDocs, completedDocs] = await Promise.all([
          // Total de documentos en los últimos 30 días
          prisma.document.count({
            where: {
              companyId,
              createdAt: { gte: thirtyDaysAgo }
            }
          }),
          // Revenue total
          prisma.document.aggregate({
            where: {
              companyId,
              createdAt: { gte: thirtyDaysAgo }
            },
            _sum: { totalAmount: true }
          }),
          // Documentos pendientes
          prisma.document.count({
            where: {
              companyId,
              siiStatus: 'draft',
              createdAt: { gte: thirtyDaysAgo }
            }
          }),
          // Documentos completados
          prisma.document.count({
            where: {
              companyId,
              siiStatus: { in: ['sent', 'accepted'] },
              createdAt: { gte: thirtyDaysAgo }
            }
          })
        ]);

        // Obtener métricas de clientes
        const [totalClients, activeClients] = await Promise.all([
          prisma.client.count({
            where: { companyId }
          }),
          prisma.client.count({
            where: { companyId, isActive: true }
          })
        ]);

        // Obtener métricas de productos
        const [totalProducts, allProducts] = await Promise.all([
          prisma.product.count({
            where: { companyId }
          }),
          prisma.product.findMany({
            where: {
              companyId,
              productType: 'PRODUCT',
              stockQuantity: { not: null },
              minStock: { not: null }
            },
            select: {
              stockQuantity: true,
              minStock: true
            }
          })
        ]);

        // Calcular productos con stock bajo manualmente
        const lowStockProducts = allProducts.filter(product => 
          (product.stockQuantity || 0) <= (product.minStock || 0)
        ).length;

        return {
          summary: {
            totalDocuments: documentsCount,
            totalRevenue: Number(documentsRevenue._sum.totalAmount) || 0,
            pendingDocuments: pendingDocs,
            completedDocuments: completedDocs,
            totalClients,
            activeClients,
            totalProducts,
            lowStockProducts
          },
          period: input.period,
          generatedAt: new Date().toISOString()
        };
        
      } catch (error) {
        console.error('[getDashboardMetrics] Error:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error al obtener métricas del dashboard'
        });
      }
    }),

  /**
   * Generar reporte personalizado usando Prisma
   */
  generateReport: companyProcedure
    .input(generateReportSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        const { prisma, user } = ctx;
        const companyId = user.companyId;

        let reportData;

        switch (input.type) {
          case 'documents':
            // Reporte de documentos DTE
            const documents = await prisma.document.findMany({
              where: { companyId },
              include: {
                client: {
                  select: {
                    rut: true,
                    businessName: true,
                    firstName: true,
                    lastName: true
                  }
                }
              },
              orderBy: { createdAt: 'desc' },
              take: 100
            });
            
            const totalAmount = documents.reduce((sum, doc) => 
              sum + Number(doc.totalAmount), 0);
            
            reportData = {
              type: 'documents',
              data: documents.map(doc => ({
                id: doc.id,
                documentType: doc.documentType,
                folioNumber: doc.folioNumber,
                totalAmount: Number(doc.totalAmount),
                siiStatus: doc.siiStatus,
                createdAt: doc.createdAt,
                clientName: doc.client?.businessName || 
                          `${doc.client?.firstName || ''} ${doc.client?.lastName || ''}`.trim() || 
                          'Cliente no especificado',
                clientRut: doc.client?.rut || 'N/A'
              })),
              summary: {
                totalDocuments: documents.length,
                totalAmount
              }
            };
            break;

          case 'clients':
            // Reporte de clientes con documentos
            const clients = await prisma.client.findMany({
              where: { companyId },
              include: {
                documents: {
                  select: {
                    id: true,
                    totalAmount: true
                  }
                }
              },
              orderBy: { createdAt: 'desc' }
            });
            
            const clientsData = clients.map(client => ({
              id: client.id,
              name: client.businessName || 
                   `${client.firstName || ''} ${client.lastName || ''}`.trim() || 
                   'Sin nombre',
              rut: client.rut,
              email: client.email || 'N/A',
              isActive: client.isActive,
              createdAt: client.createdAt,
              documentCount: client.documents.length,
              totalBilled: client.documents.reduce((sum, doc) => 
                sum + Number(doc.totalAmount), 0)
            }));
            
            reportData = {
              type: 'clients',
              data: clientsData.sort((a, b) => b.totalBilled - a.totalBilled),
              summary: {
                totalClients: clients.length,
                activeClients: clients.filter(c => c.isActive).length
              }
            };
            break;

          case 'products':
            // Reporte de productos
            const products = await prisma.product.findMany({
              where: { companyId },
              orderBy: { name: 'asc' }
            });
            
            reportData = {
              type: 'products',
              data: products.map(product => ({
                id: product.id,
                name: product.name,
                sku: product.sku,
                productType: product.productType,
                unitPrice: Number(product.unitPrice),
                stockQuantity: product.stockQuantity,
                minStock: product.minStock,
                isActive: product.isActive,
                createdAt: product.createdAt
              })),
              summary: {
                totalProducts: products.length,
                activeProducts: products.filter(p => p.isActive).length,
                lowStockProducts: products.filter(p => 
                  p.productType === 'PRODUCT' && 
                  (p.stockQuantity || 0) <= (p.minStock || 0)
                ).length
              }
            };
            break;

          case 'sales':
          case 'tax':
          default:
            // Reporte de ventas/tributario usando Prisma con agregaciones
            const salesData = await prisma.document.groupBy({
              by: ['documentType'],
              where: { companyId },
              _count: { id: true },
              _sum: {
                netAmount: true,
                taxAmount: true,
                totalAmount: true
              },
              orderBy: {
                _sum: {
                  totalAmount: 'desc'
                }
              }
            });
            
            reportData = {
              type: input.type,
              data: salesData.map(item => ({
                documentType: item.documentType,
                documentCount: item._count.id,
                netAmount: Number(item._sum.netAmount) || 0,
                taxAmount: Number(item._sum.taxAmount) || 0,
                totalAmount: Number(item._sum.totalAmount) || 0
              })),
              summary: {
                totalSales: salesData.reduce((sum, item) => 
                  sum + (Number(item._sum.totalAmount) || 0), 0),
                totalTax: salesData.reduce((sum, item) => 
                  sum + (Number(item._sum.taxAmount) || 0), 0)
              }
            };
            break;
        }

        return {
          id: `report-${Date.now()}`,
          type: input.type,
          period: input.period,
          createdAt: new Date().toISOString(),
          data: reportData,
          filters: input.filters || {}
        };

      } catch (error) {
        console.error('[generateReport] Error:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error al generar el reporte'
        });
      }
    }),

  /**
   * Obtener datos para gráficos del dashboard usando Prisma
   */
  getChartData: companyProcedure
    .input(z.object({
      chartType: z.enum(['revenue', 'documents', 'clients']),
      period: reportPeriodSchema.optional().default('monthly')
    }))
    .query(async ({ ctx, input }) => {
      try {
        const { prisma, user } = ctx;
        const companyId = user.companyId;

        // Fecha límite para datos (últimos 6 meses)
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

        let chartData: any[] = [];

        switch (input.chartType) {
          case 'revenue':
            // Obtener revenue por períodos usando Prisma
            const revenueData = await prisma.document.findMany({
              where: {
                companyId,
                createdAt: { gte: sixMonthsAgo }
              },
              select: {
                createdAt: true,
                totalAmount: true
              },
              orderBy: { createdAt: 'asc' }
            });

            // Agrupar por mes
            const revenueByMonth = revenueData.reduce((acc: any, doc) => {
              const date = new Date(doc.createdAt!);
              const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
              
              if (!acc[monthKey]) {
                acc[monthKey] = {
                  period: new Date(date.getFullYear(), date.getMonth(), 1),
                  value: 0
                };
              }
              
              acc[monthKey].value += Number(doc.totalAmount);
              return acc;
            }, {});

            chartData = Object.values(revenueByMonth)
              .sort((a: any, b: any) => a.period.getTime() - b.period.getTime())
              .slice(-6)
              .map((item: any) => ({
                period: item.period.toISOString(),
                value: Math.round(item.value),
                label: item.period.toLocaleDateString('es-CL', { month: 'short', year: 'numeric' })
              }));
            break;

          case 'documents':
            // Obtener documentos por tipo
            const documentsData = await prisma.document.groupBy({
              by: ['documentType'],
              where: {
                companyId,
                createdAt: { gte: sixMonthsAgo }
              },
              _count: { id: true },
              orderBy: {
                _count: {
                  id: 'desc'
                }
              }
            });

            const typeLabels: { [key: number]: string } = {
              33: 'Facturas Electrónicas',
              39: 'Boletas Electrónicas', 
              61: 'Notas de Crédito',
              52: 'Guías de Despacho'
            };

            chartData = documentsData.map(item => ({
              type: item.documentType.toString(),
              value: item._count.id,
              label: typeLabels[item.documentType] || `Tipo ${item.documentType}`
            }));
            break;

          case 'clients':
          default:
            // Obtener nuevos clientes por período
            const clientsData = await prisma.client.findMany({
              where: {
                companyId,
                createdAt: { gte: sixMonthsAgo }
              },
              select: {
                createdAt: true
              },
              orderBy: { createdAt: 'asc' }
            });

            // Agrupar por mes
            const clientsByMonth = clientsData.reduce((acc: any, client) => {
              const date = new Date(client.createdAt!);
              const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
              
              if (!acc[monthKey]) {
                acc[monthKey] = {
                  period: new Date(date.getFullYear(), date.getMonth(), 1),
                  value: 0
                };
              }
              
              acc[monthKey].value += 1;
              return acc;
            }, {});

            chartData = Object.values(clientsByMonth)
              .sort((a: any, b: any) => a.period.getTime() - b.period.getTime())
              .slice(-6)
              .map((item: any) => ({
                period: item.period.toISOString(),
                value: item.value,
                label: item.period.toLocaleDateString('es-CL', { month: 'short', year: 'numeric' })
              }));
            break;
        }

        return {
          chartType: input.chartType,
          period: input.period,
          data: chartData,
          generatedAt: new Date().toISOString()
        };

      } catch (error) {
        console.error('[getChartData] Error:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error al obtener datos para gráficos'
        });
      }
    })
});

export type ReportsRouter = typeof reportsRouter;
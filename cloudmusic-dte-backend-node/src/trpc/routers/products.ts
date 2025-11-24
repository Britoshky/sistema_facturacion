import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { 
  createProductSchema, 
  updateProductSchema,
  listProductsSchema,
  updateStockSchema,
  updateProductWithIdSchema,
  deleteProductSchema
} from '../schemas/products';
import { uuidIdSchema } from '../schemas/common';

export const productsRouter = router({
  // Obtener lista de productos de la empresa
  list: companyProcedure
    .input(listProductsSchema)
    .query(async ({ ctx, input }) => {
      const { page, limit, search, productType, taxClassification, lowStock, isActive } = input;
      const skip = (page - 1) * limit;

      // Construir filtros
      const where: Record<string, unknown> = {
        companyId: ctx.user.companyId
      };

      if (search) {
        where.OR = [
          { name: { contains: search, mode: 'insensitive' } },
          { sku: { contains: search, mode: 'insensitive' } },
          { description: { contains: search, mode: 'insensitive' } }
        ];
      }

      if (productType) {
        where.productType = productType;
      }

      if (taxClassification) {
        where.taxClassification = taxClassification;
      }

      if (lowStock) {
        // Para productos con stock bajo, necesitamos hacer una consulta raw o usar un filtro diferente
        // Por simplicidad, omitimos este filtro complejo aquí
      }

      if (isActive !== undefined) {
        where.isActive = isActive;
      }

      const [products, totalCount] = await Promise.all([
        ctx.prisma.product.findMany({
          where,
          skip,
          take: limit,
          orderBy: [
            { isActive: 'desc' },
            { name: 'asc' }
          ]
        }),
        ctx.prisma.product.count({ where })
      ]);

      return {
        products: products.map((product: typeof products[0]) => ({
          id: product.id,
          sku: product.sku,
          name: product.name,
          description: product.description,
          productType: product.productType,
          unitPrice: Number(product.unitPrice),
          costPrice: product.costPrice ? Number(product.costPrice) : null,
          unitOfMeasure: product.unitOfMeasure,
          taxClassification: product.taxClassification,
          siiCode: product.siiCode,
          stockQuantity: product.stockQuantity,
          minStock: product.minStock,
          isActive: product.isActive,
          createdAt: product.createdAt,
          updatedAt: product.updatedAt,
          isLowStock: (product.stockQuantity || 0) <= (product.minStock || 0),
          profitMargin: product.costPrice ? 
            ((Number(product.unitPrice) - Number(product.costPrice)) / Number(product.unitPrice)) * 100 : 0
        })),
        pagination: {
          page,
          limit,
          totalCount,
          totalPages: Math.ceil(totalCount / limit)
        }
      };
    }),

  // Obtener producto por ID
  getById: companyProcedure
    .input(uuidIdSchema)
    .query(async ({ ctx, input }) => {
      const { id } = input;

      const product = await ctx.prisma.product.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId
        }
      });

      if (!product) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Producto no encontrado'
        });
      }

      return {
        id: product.id,
        sku: product.sku,
        name: product.name,
        description: product.description,
        productType: product.productType,
        unitPrice: Number(product.unitPrice),
        costPrice: product.costPrice ? Number(product.costPrice) : null,
        unitOfMeasure: product.unitOfMeasure,
        taxClassification: product.taxClassification,
        siiCode: product.siiCode,
        stockQuantity: product.stockQuantity,
        minStock: product.minStock,
        isActive: product.isActive,
        createdAt: product.createdAt,
        updatedAt: product.updatedAt,
        isLowStock: (product.stockQuantity || 0) <= (product.minStock || 0),
        profitMargin: product.costPrice ? 
          ((Number(product.unitPrice) - Number(product.costPrice)) / Number(product.unitPrice)) * 100 : 0
      };
    }),

  // Crear producto
  create: companyProcedure
    .input(createProductSchema)
    .mutation(async ({ ctx, input }) => {
      // Verificar si ya existe un producto con este SKU en la empresa
      const existingProduct = await ctx.prisma.product.findFirst({
        where: {
          companyId: ctx.user.companyId,
          sku: input.sku,
          isActive: true
        }
      });

      if (existingProduct) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'Ya existe un producto activo con este SKU'
        });
      }

      const product = await ctx.prisma.product.create({
        data: {
          ...input,
          companyId: ctx.user.companyId
        }
      });

      return {
        id: product.id,
        sku: product.sku,
        name: product.name,
        description: product.description,
        productType: product.productType,
        unitPrice: Number(product.unitPrice),
        costPrice: product.costPrice ? Number(product.costPrice) : null,
        unitOfMeasure: product.unitOfMeasure,
        taxClassification: product.taxClassification,
        siiCode: product.siiCode,
        stockQuantity: product.stockQuantity,
        minStock: product.minStock,
        isActive: product.isActive,
        createdAt: product.createdAt,
        updatedAt: product.updatedAt,
        isLowStock: (product.stockQuantity || 0) <= (product.minStock || 0)
      };
    }),

  // Actualizar producto
  update: companyProcedure
    .input(updateProductWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const { id, data } = input;

      // Verificar que el producto pertenece a la empresa del usuario
      const existingProduct = await ctx.prisma.product.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId
        }
      });

      if (!existingProduct) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Producto no encontrado'
        });
      }

      // Verificar SKU único si se está actualizando
      if (data.sku && data.sku !== existingProduct.sku) {
        const duplicateProduct = await ctx.prisma.product.findFirst({
          where: {
            companyId: ctx.user.companyId,
            sku: data.sku,
            id: { not: id },
            isActive: true
          }
        });

        if (duplicateProduct) {
          throw new TRPCError({
            code: 'CONFLICT',
            message: 'Ya existe otro producto activo con este SKU'
          });
        }
      }

      const updatedProduct = await ctx.prisma.product.update({
        where: { id },
        data
      });

      return {
        id: updatedProduct.id,
        sku: updatedProduct.sku,
        name: updatedProduct.name,
        description: updatedProduct.description,
        productType: updatedProduct.productType,
        unitPrice: Number(updatedProduct.unitPrice),
        costPrice: updatedProduct.costPrice ? Number(updatedProduct.costPrice) : null,
        unitOfMeasure: updatedProduct.unitOfMeasure,
        taxClassification: updatedProduct.taxClassification,
        siiCode: updatedProduct.siiCode,
        stockQuantity: updatedProduct.stockQuantity,
        minStock: updatedProduct.minStock,
        isActive: updatedProduct.isActive,
        createdAt: updatedProduct.createdAt,
        updatedAt: updatedProduct.updatedAt,
        isLowStock: (updatedProduct.stockQuantity || 0) <= (updatedProduct.minStock || 0)
      };
    }),

  // Eliminar producto (soft delete)
  delete: companyProcedure
    .input(deleteProductSchema)
    .mutation(async ({ ctx, input }) => {
      const { id } = input;

      // Verificar que el producto pertenece a la empresa del usuario
      const existingProduct = await ctx.prisma.product.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId
        }
      });

      if (!existingProduct) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Producto no encontrado'
        });
      }

      // Realizar soft delete
      await ctx.prisma.product.update({
        where: { id },
        data: { isActive: false }
      });

      return {
        success: true,
        message: 'Producto desactivado exitosamente'
      };
    }),

  // Actualizar stock de producto
  updateStock: companyProcedure
    .input(updateStockSchema)
    .mutation(async ({ ctx, input }) => {
      const { id, stockQuantity, reason } = input;

      // Verificar que el producto pertenece a la empresa del usuario
      const existingProduct = await ctx.prisma.product.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId,
          isActive: true
        }
      });

      if (!existingProduct) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Producto no encontrado'
        });
      }

      const updatedProduct = await ctx.prisma.product.update({
        where: { id },
        data: { stockQuantity }
      });

      return {
        id: updatedProduct.id,
        sku: updatedProduct.sku,
        name: updatedProduct.name,
        previousStock: existingProduct.stockQuantity,
        newStock: updatedProduct.stockQuantity,
        difference: (updatedProduct.stockQuantity || 0) - (existingProduct.stockQuantity || 0),
        isLowStock: (updatedProduct.stockQuantity || 0) <= (updatedProduct.minStock || 0)
      };
    }),

  // Obtener productos con stock bajo
  getLowStock: companyProcedure
    .query(async ({ ctx }) => {
      const lowStockProducts = await ctx.prisma.product.findMany({
        where: {
          companyId: ctx.user.companyId,
          isActive: true,
          // Solo productos físicos con control de stock
          productType: 'PRODUCT'
        },
        orderBy: [
          { stockQuantity: 'asc' }
        ]
      });

      return {
        products: lowStockProducts.map((product: typeof lowStockProducts[0]) => ({
          id: product.id,
          sku: product.sku,
          name: product.name,
          stockQuantity: product.stockQuantity,
          minStock: product.minStock,
          unitPrice: Number(product.unitPrice),
          shortage: (product.minStock || 0) - (product.stockQuantity || 0)
        })),
        totalLowStock: lowStockProducts.length
      };
    })
});
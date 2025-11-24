import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { 
  createClientSchema, 
  updateClientSchema, 
  listClientsSchema,
  listClientsWithPaginationSchema,
  getClientByIdSchema,
  updateClientWithIdSchema,
  deleteClientSchema
} from '../schemas/clients';
import { validateRUT } from '../../utils/helpers';

export const clientsRouter = router({
  // Obtener lista de clientes de la empresa
  list: companyProcedure
    .input(listClientsWithPaginationSchema)
    .query(async ({ ctx, input }) => {
      const { page, limit, search, clientType, isActive } = input;
      const skip = (page - 1) * limit;

      // Construir filtros
      const where: Record<string, unknown> = {
        companyId: ctx.user.companyId
      };

      if (search) {
        where.OR = [
          { businessName: { contains: search, mode: 'insensitive' } },
          { firstName: { contains: search, mode: 'insensitive' } },
          { lastName: { contains: search, mode: 'insensitive' } },
          { rut: { contains: search, mode: 'insensitive' } },
          { email: { contains: search, mode: 'insensitive' } }
        ];
      }

      if (clientType) {
        where.clientType = clientType;
      }

      if (isActive !== undefined) {
        where.isActive = isActive;
      }

      const [clients, totalCount] = await Promise.all([
        ctx.prisma.client.findMany({
          where,
          skip,
          take: limit,
          orderBy: [
            { isActive: 'desc' },
            { createdAt: 'desc' }
          ]
        }),
        ctx.prisma.client.count({ where })
      ]);

      return {
        clients: clients.map((client: typeof clients[0]) => ({
          id: client.id,
          clientType: client.clientType?.toUpperCase() as 'INDIVIDUAL' | 'BUSINESS' | 'FOREIGN',
          businessName: client.businessName,
          firstName: client.firstName,
          lastName: client.lastName,
          rut: client.rut,
          businessLine: client.businessLine,
          address: client.address,
          commune: client.commune,
          city: client.city,
          phone: client.phone,
          email: client.email,
          creditLimit: Number(client.creditLimit),
          paymentTerms: client.paymentTerms,
          isActive: client.isActive,
          createdAt: client.createdAt,
          updatedAt: client.updatedAt,
          displayName: client.clientType === 'business' 
            ? client.businessName 
            : `${client.firstName} ${client.lastName}`
        })),
        pagination: {
          page,
          limit,
          totalCount,
          totalPages: Math.ceil(totalCount / limit)
        }
      };
    }),

  // Obtener cliente por ID
  getById: companyProcedure
    .input(getClientByIdSchema)
    .query(async ({ ctx, input }) => {
      const { id } = input;

      const client = await ctx.prisma.client.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId
        }
      });

      if (!client) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Cliente no encontrado'
        });
      }

      return {
        id: client.id,
        clientType: client.clientType?.toUpperCase() as 'INDIVIDUAL' | 'BUSINESS' | 'FOREIGN',
        businessName: client.businessName,
        firstName: client.firstName,
        lastName: client.lastName,
        rut: client.rut,
        businessLine: client.businessLine,
        address: client.address,
        commune: client.commune,
        city: client.city,
        phone: client.phone,
        email: client.email,
        creditLimit: Number(client.creditLimit),
        paymentTerms: client.paymentTerms,
        isActive: client.isActive,
        createdAt: client.createdAt,
        updatedAt: client.updatedAt,
        displayName: client.clientType === 'business' 
          ? client.businessName 
          : `${client.firstName} ${client.lastName}`
      };
    }),

  // Crear cliente
  create: companyProcedure
    .input(createClientSchema)
    .mutation(async ({ ctx, input }) => {
      // Validar RUT (combinar rut + dv)
      const fullRut = input.clientType === 'FOREIGN' ? '' : `${input.rut}${input.dv}`;
      const rutValidation = input.clientType === 'FOREIGN' 
        ? { isValid: true, formatted: '' } 
        : validateRUT(fullRut);
      
      if (!rutValidation.isValid) {
        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: rutValidation.error || 'RUT no es válido'
        });
      }

      // Verificar si ya existe un cliente con este RUT en la empresa
      const existingClient = await ctx.prisma.client.findFirst({
        where: {
          companyId: ctx.user.companyId,
          rut: rutValidation.formatted,
          isActive: true
        }
      });

      if (existingClient) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'Ya existe un cliente activo con este RUT'
        });
      }

      const client = await ctx.prisma.client.create({
        data: {
          companyId: ctx.user.companyId,
          rut: rutValidation.formatted,
          businessName: input.businessName,
          firstName: input.clientType === 'INDIVIDUAL' ? input.businessName?.split(' ')[0] : undefined,
          lastName: input.clientType === 'INDIVIDUAL' ? input.businessName?.split(' ').slice(1).join(' ') : undefined,
          businessLine: input.economicActivity, // Mapear economicActivity a businessLine
          clientType: input.clientType?.toLowerCase(), // Convertir a lowercase para DB
          address: input.address,
          commune: input.commune,
          city: input.city,
          phone: input.phone,
          email: input.email,
          paymentTerms: input.paymentTerms || 30,
          creditLimit: input.creditLimit || 0,
          isActive: input.isActive ?? true
        }
      });

      return {
        id: client.id,
        clientType: client.clientType?.toUpperCase() as 'INDIVIDUAL' | 'BUSINESS' | 'FOREIGN',
        businessName: client.businessName,
        firstName: client.firstName,
        lastName: client.lastName,
        rut: client.rut,
        businessLine: client.businessLine,
        address: client.address,
        commune: client.commune,
        city: client.city,
        phone: client.phone,
        email: client.email,
        creditLimit: client.creditLimit,
        paymentTerms: client.paymentTerms,
        isActive: client.isActive,
        createdAt: client.createdAt,
        updatedAt: client.updatedAt,
        displayName: client.clientType === 'business' 
          ? client.businessName 
          : `${client.firstName} ${client.lastName}`
      };
    }),

  // Actualizar cliente
  update: companyProcedure
    .input(updateClientWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const { id, data } = input;

      // Verificar que el cliente pertenece a la empresa del usuario
      const existingClient = await ctx.prisma.client.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId
        }
      });

      if (!existingClient) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Cliente no encontrado'
        });
      }

      // Validar RUT si se está actualizando
      let formattedRUT = existingClient.rut;
      if (data.rut) {
        const fullRut = `${data.rut}${data.dv || ''}`;
        const rutValidation = validateRUT(fullRut);
        if (!rutValidation.isValid) {
          throw new TRPCError({
            code: 'BAD_REQUEST',
            message: rutValidation.error || 'RUT no es válido'
          });
        }

        // Verificar que no exista otro cliente con el nuevo RUT
        const duplicateClient = await ctx.prisma.client.findFirst({
          where: {
            companyId: ctx.user.companyId,
            rut: rutValidation.formatted,
            id: { not: id },
            isActive: true
          }
        });

        if (duplicateClient) {
          throw new TRPCError({
            code: 'CONFLICT',
            message: 'Ya existe otro cliente activo con este RUT'
          });
        }

        formattedRUT = rutValidation.formatted;
      }

      // Mapear campos del input a campos de Prisma
      const updateData: any = {
        rut: formattedRUT
      };

      if (data.businessName !== undefined) updateData.businessName = data.businessName;
      if (data.clientType !== undefined) updateData.clientType = data.clientType.toLowerCase();
      if (data.economicActivity !== undefined) updateData.businessLine = data.economicActivity;
      if (data.address !== undefined) updateData.address = data.address;
      if (data.commune !== undefined) updateData.commune = data.commune;
      if (data.city !== undefined) updateData.city = data.city;
      if (data.phone !== undefined) updateData.phone = data.phone;
      if (data.email !== undefined) updateData.email = data.email;
      if (data.paymentTerms !== undefined) updateData.paymentTerms = data.paymentTerms;
      if (data.creditLimit !== undefined) updateData.creditLimit = data.creditLimit;
      if (data.isActive !== undefined) updateData.isActive = data.isActive;

      const updatedClient = await ctx.prisma.client.update({
        where: { id },
        data: updateData
      });

      return {
        id: updatedClient.id,
        clientType: updatedClient.clientType?.toUpperCase() as 'INDIVIDUAL' | 'BUSINESS' | 'FOREIGN',
        businessName: updatedClient.businessName,
        firstName: updatedClient.firstName,
        lastName: updatedClient.lastName,
        rut: updatedClient.rut,
        businessLine: updatedClient.businessLine,
        address: updatedClient.address,
        commune: updatedClient.commune,
        city: updatedClient.city,
        phone: updatedClient.phone,
        email: updatedClient.email,
        creditLimit: updatedClient.creditLimit,
        paymentTerms: updatedClient.paymentTerms,
        isActive: updatedClient.isActive,
        createdAt: updatedClient.createdAt,
        updatedAt: updatedClient.updatedAt,
        displayName: updatedClient.clientType === 'business' 
          ? updatedClient.businessName 
          : `${updatedClient.firstName} ${updatedClient.lastName}`
      };
    }),

  // Eliminar cliente (soft delete)
  delete: companyProcedure
    .input(deleteClientSchema)
    .mutation(async ({ ctx, input }) => {
      const { id } = input;

      // Verificar que el cliente pertenece a la empresa del usuario
      const existingClient = await ctx.prisma.client.findFirst({
        where: {
          id,
          companyId: ctx.user.companyId
        }
      });

      if (!existingClient) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Cliente no encontrado'
        });
      }

      // Realizar soft delete
      await ctx.prisma.client.update({
        where: { id },
        data: { isActive: false }
      });

      return {
        success: true,
        message: 'Cliente desactivado exitosamente'
      };
    })
});
import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { 
  createCertificateSchema, 
  updateCertificateSchema,
  getCertificateByIdSchema,
  updateCertificateWithIdSchema,
  deleteCertificateSchema
} from '../schemas/certificates';

export const certificatesRouter = router({
  // Listar certificados
  list: companyProcedure
    .query(async ({ ctx }) => {
      const certificates = await ctx.prisma.certificate.findMany({
        where: { companyId: ctx.user.companyId },
        orderBy: { createdAt: 'desc' }
      });

      return certificates.map((cert: typeof certificates[0]) => ({
        id: cert.id,
        certificateName: cert.certificateName,
        isActive: cert.isActive,
        createdAt: cert.createdAt,
        issuer: cert.issuer,
        subject: cert.subject,
        serialNumber: cert.serialNumber,
        issuedDate: cert.issuedDate,
        expiryDate: cert.expiryDate
      }));
    }),

  // Obtener por ID
  getById: companyProcedure
    .input(getCertificateByIdSchema)
    .query(async ({ ctx, input }) => {
      const certificate = await ctx.prisma.certificate.findFirst({
        where: {
          id: input.id,
          companyId: ctx.user.companyId
        }
      });

      if (!certificate) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Certificado no encontrado'
        });
      }

      return {
        id: certificate.id,
        certificateName: certificate.certificateName,
        isActive: certificate.isActive,
        createdAt: certificate.createdAt
      };
    }),

  // Crear certificado
  create: companyProcedure
    .input(createCertificateSchema)
    .mutation(async ({ ctx, input }) => {
      const pfxBuffer = Buffer.from(input.pfxFile, 'base64');

      const certificate = await ctx.prisma.certificate.create({
        data: {
          companyId: ctx.user.companyId,
          certificateName: input.certificateName,
          pfxFile: pfxBuffer,
          passwordHash: input.passwordHash,
          issuer: 'SII',
          subject: 'Empresa',
          serialNumber: '123456',
          issuedDate: new Date(),
          expiryDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)
        }
      });

      return {
        id: certificate.id,
        certificateName: certificate.certificateName,
        isActive: certificate.isActive
      };
    }),

  // Actualizar certificado
  update: companyProcedure
    .input(updateCertificateWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      const certificate = await ctx.prisma.certificate.update({
        where: { id: input.id },
        data: input.data
      });

      return {
        id: certificate.id,
        certificateName: certificate.certificateName,
        isActive: certificate.isActive
      };
    }),

  // Eliminar certificado
  delete: companyProcedure
    .input(deleteCertificateSchema)
    .mutation(async ({ ctx, input }) => {
      await ctx.prisma.certificate.update({
        where: { id: input.id },
        data: { isActive: false }
      });

      return { success: true };
    })
});
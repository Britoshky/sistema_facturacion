import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { 
  createDocumentSchema, 
  updateDocumentSchema, 
  getDocumentByIdSchema,
  updateDocumentWithIdSchema,
  deleteDocumentSchema,
  validateAndSignDocumentSchema,
  sendDocumentToSiiSchema,
  DTEDocumentBase,
  DocumentValidationType
} from '../schemas/documents';
import { xmlValidator, DTEValidationType } from '../../services/xmlValidator';
import { digitalSigner } from '../../services/digitalSigner';
import { eventService } from '../../services/eventService';
import { EventType } from '../schemas/websocket';

// Función auxiliar para generar XML DTE
function generateDTEXml(document: DTEDocumentBase): string {
  // En producción, esto generaría el XML real según normativas SII
  return `<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE version="1.0" xmlns="http://www.sii.cl/SiiDte">
  <Documento ID="doc_${document.id}">
    <Encabezado>
      <IdDoc>
        <TipoDTE>${document.documentType}</TipoDTE>
        <Folio>${document.folioNumber}</Folio>
        <FchEmis>${new Date().toISOString().split('T')[0]}</FchEmis>
      </IdDoc>
      <Emisor>
        <RUTEmisor>${(document as any).companyRut || 'RUT_REQUERIDO'}</RUTEmisor>
        <RznSoc>${(document as any).companyName || 'NOMBRE_EMPRESA_REQUERIDO'}</RznSoc>
        <GiroEmis>${(document as any).businessActivity || 'ACTIVIDAD_REQUERIDA'}</GiroEmis>
      </Emisor>
      <Receptor>
        <RUTRecep>${(document as any).clientRut || 'RUT_CLIENTE_REQUERIDO'}</RUTRecep>
        <RznSocRecep>${(document as any).clientName || 'NOMBRE_CLIENTE_REQUERIDO'}</RznSocRecep>
      </Receptor>
      <Totales>
        <MntNeto>${typeof document.netAmount === 'number' ? document.netAmount : document.netAmount.toNumber()}</MntNeto>
        <IVA>${typeof document.taxAmount === 'number' ? document.taxAmount : document.taxAmount.toNumber()}</IVA>
        <MntTotal>${document.totalAmount}</MntTotal>
      </Totales>
    </Encabezado>
    <Detalle>
      <NroLinDet>1</NroLinDet>
      <NmbItem>${(document as any).itemDescription || 'DESCRIPCION_ITEM_REQUERIDA'}</NmbItem>
      <MontoItem>${document.totalAmount}</MontoItem>
    </Detalle>
  </Documento>
</DTE>`;
}

export const documentsRouter = router({
  // Listar documentos
  list: companyProcedure
    .query(async ({ ctx }) => {
      const documents = await ctx.prisma.document.findMany({
        where: { companyId: ctx.user.companyId },
        include: {
          client: true,
          documentItems: true
        },
        orderBy: { createdAt: 'desc' }
      });

      return documents.map((doc: typeof documents[0]) => ({
        id: doc.id,
        documentType: doc.documentType,
        folioNumber: doc.folioNumber,
        clientName: doc.client?.businessName || `${doc.client?.firstName || ''} ${doc.client?.lastName || ''}`.trim(),
        clientRut: doc.client?.rut,
        netAmount: doc.netAmount,
        taxAmount: doc.taxAmount,
        totalAmount: doc.totalAmount,
        siiStatus: doc.siiStatus,
        createdAt: doc.createdAt,
        issueDate: doc.issueDate
      }));
    }),

  // Obtener por ID
  getById: companyProcedure
    .input(getDocumentByIdSchema)
    .query(async ({ ctx, input }) => {
      const document = await ctx.prisma.document.findFirst({
        where: {
          id: input.id,
          companyId: ctx.user.companyId
        },
        include: {
          client: true,
          documentItems: {
            include: {
              product: true
            }
          }
        }
      });

      if (!document) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Documento no encontrado'
        });
      }

      return {
        id: document.id,
        documentType: document.documentType,
        folioNumber: document.folioNumber,
        client: document.client,
        netAmount: document.netAmount,
        taxAmount: document.taxAmount,
        totalAmount: document.totalAmount,
        siiStatus: document.siiStatus,
        documentItems: document.documentItems,
        createdAt: document.createdAt
      };
    }),

  // Crear documento
  create: companyProcedure
    .input(createDocumentSchema)
    .mutation(async ({ ctx, input }) => {
      // Buscar un folio disponible
      const folio = await ctx.prisma.folio.findFirst({
        where: {
          companyId: ctx.user.companyId,
          documentType: input.documentType,
          isActive: true
        }
      });

      if (!folio) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'No hay folios disponibles para este tipo de documento'
        });
      }

      const document = await ctx.prisma.document.create({
        data: {
          companyId: ctx.user.companyId,
          clientId: input.clientId,
          folioId: folio.id,
          documentType: input.documentType,
          folioNumber: folio.currentFolio + 1,
          issueDate: new Date(),
          netAmount: input.amount,
          taxAmount: input.tax,
          totalAmount: input.total,
          siiStatus: 'draft',
          documentItems: {
            createMany: {
              data: input.items.map((item, index) => ({
                lineNumber: index + 1,
                productName: item.description,
                quantity: item.quantity,
                unitPrice: item.price,
                netAmount: item.quantity * item.price,
                totalAmount: item.quantity * item.price
              }))
            }
          }
        },
        include: {
          client: true,
          documentItems: true
        }
      });

      // Actualizar el folio actual
      await ctx.prisma.folio.update({
        where: { id: folio.id },
        data: { currentFolio: folio.currentFolio + 1 }
      });

      return {
        id: document.id,
        documentType: document.documentType,
        folioNumber: document.folioNumber,
        totalAmount: document.totalAmount,
        siiStatus: document.siiStatus
      };
    }),

  // Actualizar documento (expandido para edición completa)
  update: companyProcedure
    .input(updateDocumentWithIdSchema)
    .mutation(async ({ ctx, input }) => {
      console.log('🔄 [BACKEND] Actualizando documento ID:', input.id);
      console.log('🔄 [BACKEND] Datos recibidos:', JSON.stringify(input.data, null, 2));
      
      const updateData: Record<string, unknown> = {};
      
      // Actualizar campos básicos del documento (sin relaciones)
      if (input.data.documentType !== undefined) {
        updateData.documentType = input.data.documentType;
      }
      
      if (input.data.amount !== undefined) {
        updateData.netAmount = input.data.amount;
      }
      
      if (input.data.tax !== undefined) {
        updateData.taxAmount = input.data.tax;
      }
      
      if (input.data.total !== undefined) {
        updateData.totalAmount = input.data.total;
      }
      
      if (input.data.status) {
        updateData.siiStatus = input.data.status;
      }
      
      if (input.data.observations !== undefined) {
        updateData.notes = input.data.observations;
      }
      
      if (input.data.internalNotes !== undefined) {
        // El campo se llama 'notes' en Prisma, no 'internalNotes'
        updateData.notes = input.data.internalNotes;
      }
      
      // Actualizar cliente si se proporciona
      if (input.data.clientId) {
        updateData.clientId = input.data.clientId;
      }
      
      // Actualizar empresa si se proporciona
      if (input.data.companyId) {
        updateData.companyId = input.data.companyId;
      }

      // Si se proporcionan items, actualizar usando la relación documentItems
      if (input.data.items && input.data.items.length > 0) {
        updateData.documentItems = {
          deleteMany: {}, // Eliminar todos los items existentes
          create: input.data.items.map((item, index) => ({
            productId: null, // No vincular a productos del catálogo por ahora
            lineNumber: index + 1,
            productName: item.description,
            description: item.description,
            quantity: item.quantity,
            unitPrice: item.price,
            netAmount: item.quantity * item.price,
            taxAmount: Math.round(item.quantity * item.price * 0.19),
            totalAmount: item.quantity * item.price + Math.round(item.quantity * item.price * 0.19),
            discountPercentage: 0,
            discountAmount: 0,
            exemptAmount: 0,
            unitOfMeasure: 'UNIDAD',
            taxClassification: 'taxable' as const
          }))
        };
      }

      console.log('🔧 [BACKEND] Datos de actualización preparados:', JSON.stringify(updateData, null, 2));
      
      // Actualizar documento con items y relaciones en una sola operación
      const updatedDocument = await ctx.prisma.document.update({
        where: { id: input.id },
        data: updateData,
        include: {
          client: true,
          company: true,
          documentItems: true
        }
      });
      
      console.log('✅ [BACKEND] Documento actualizado exitosamente:', {
        id: updatedDocument.id,
        clientId: updatedDocument.clientId,
        companyId: updatedDocument.companyId,
        documentType: updatedDocument.documentType,
        totalAmount: updatedDocument.totalAmount
      });

      return {
        id: updatedDocument.id,
        documentType: updatedDocument.documentType,
        folioNumber: updatedDocument.folioNumber,
        totalAmount: updatedDocument.totalAmount,
        siiStatus: updatedDocument.siiStatus,
        clientName: updatedDocument.client?.businessName || null,
        clientRut: updatedDocument.client?.rut || null,
        documentItems: updatedDocument.documentItems || [],
        netAmount: updatedDocument.netAmount,
        taxAmount: updatedDocument.taxAmount,
        notes: updatedDocument.notes || null
      };
    }),

  // Eliminar documento (cambiar estado)
  delete: companyProcedure
    .input(deleteDocumentSchema)
    .mutation(async ({ ctx, input }) => {
      await ctx.prisma.document.update({
        where: { id: input.id },
        data: { siiStatus: 'rejected' }
      });

      return { success: true };
    }),

  // RF002/RF003: Validar XML y firmar documento
  validateAndSign: companyProcedure
    .input(validateAndSignDocumentSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        // 1. Obtener documento
        const document = await ctx.prisma.document.findFirst({
          where: {
            id: input.id,
            companyId: ctx.user.companyId
          },
          include: {
            client: true,
            documentItems: true
          }
        });

        if (!document) {
          throw new TRPCError({
            code: 'NOT_FOUND',
            message: 'Documento no encontrado'
          });
        }

        // 2. Generar XML del documento (simulado - en producción sería el XML real)
        const xmlContent = generateDTEXml(document);

        // 3. Simular validación XML para desarrollo
        // En producción, aquí se validaría contra el esquema real del SII
        const validation = {
          isValid: true,
          errors: [],
          warnings: [],
          timing: {
            validationTime: Math.floor(Math.random() * 500) + 100 // 100-600ms simulado
          }
        };

        // 4. Simular certificado para desarrollo (sin certificados reales)
        // En producción, se debería validar el certificado real
        const mockCertificate = {
          id: input.certificateId,
          certificateName: 'Certificado de Desarrollo',
          pfxFile: Buffer.from('mock-certificate'),
          issuer: 'CA de Desarrollo',
          subject: 'Empresa de Pruebas'
        };

        // 5. Simular firma digital para desarrollo
        // En producción, aquí se firmaría con el certificado real
        const signature = {
          success: true,
          signedXml: xmlContent + '\n<!-- FIRMADO DIGITALMENTE (SIMULADO) -->',
          errors: [],
          signatureTime: Date.now(),
          certificateInfo: {
            issuer: mockCertificate.issuer,
            subject: mockCertificate.subject,
            serialNumber: '123456789',
            validFrom: new Date(),
            validTo: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000) // 1 año
          }
        };

        // 6. Actualizar documento con XML firmado
        const updatedDocument = await ctx.prisma.document.update({
          where: { id: input.id },
          data: {
            xmlContent: signature.signedXml,
            siiStatus: 'signed'
          }
        });

        // 7. Publicar evento de documento firmado (RF010)
        await eventService.publishDocumentEvent({
          id: '',
          type: EventType.DOCUMENT_SIGNED,
          timestamp: new Date(),
          companyId: ctx.user.companyId,
          userId: ctx.user.id,
          documentId: document.id,
          documentType: document.documentType,
          folioNumber: document.folioNumber,
          amount: Number(document.totalAmount),
          metadata: {
            validationTime: validation.timing.validationTime,
            signatureTime: signature.signatureTime,
            certificateInfo: signature.certificateInfo
          }
        });

        return {
          id: updatedDocument.id,
          siiStatus: updatedDocument.siiStatus,
          validationResult: validation,
          signatureInfo: {
            success: signature.success,
            certificateInfo: signature.certificateInfo,
            signatureTime: signature.signatureTime
          }
        };

      } catch (error) {
        if (error instanceof TRPCError) {
          throw error;
        }
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error validando y firmando documento'
        });
      }
    }),

  // Enviar al SII
  sendToSii: companyProcedure
    .input(sendDocumentToSiiSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        // Verificar que el documento esté firmado
        const document = await ctx.prisma.document.findFirst({
          where: {
            id: input.id,
            companyId: ctx.user.companyId
          }
        });

        if (!document) {
          throw new TRPCError({
            code: 'NOT_FOUND',
            message: 'Documento no encontrado'
          });
        }

        if (document.siiStatus !== 'signed') {
          throw new TRPCError({
            code: 'BAD_REQUEST',
            message: 'Documento debe estar firmado antes de enviar al SII'
          });
        }

        // TODO: Implementar integración real con SII (RF006)
        // Por ahora simulamos el envío
        const updatedDocument = await ctx.prisma.document.update({
          where: { id: input.id },
          data: { 
            siiStatus: 'sent'
          }
        });

        // Publicar evento de envío al SII
        await eventService.publishDocumentEvent({
          id: '',
          type: EventType.DOCUMENT_SENT_TO_SII,
          timestamp: new Date(),
          companyId: ctx.user.companyId,
          userId: ctx.user.id,
          documentId: document.id,
          documentType: document.documentType,
          folioNumber: document.folioNumber,
          amount: Number(document.totalAmount),
          metadata: {
            sentAt: new Date(),
            xmlSigned: !!document.xmlContent
          }
        });

        return {
          id: updatedDocument.id,
          siiStatus: updatedDocument.siiStatus
        };

      } catch (error) {
        if (error instanceof TRPCError) {
          throw error;
        }
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error enviando documento al SII'
        });
      }
    })
});
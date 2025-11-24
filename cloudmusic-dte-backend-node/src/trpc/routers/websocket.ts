/**
 * Router WebSocket - CloudMusic DTE
 * Endpoints para gestionar conexiones WebSocket y eventos tiempo real
 */

import { router, publicProcedure, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { z } from 'zod';
import { logger } from '../../utils/logger';

// Helpers para WebSocket service
const getWebSocketService = () => {
  const globalScope = global as any;
  return globalScope.webSocketService;
};

const ensureWebSocketService = () => {
  const service = getWebSocketService();
  if (!service) {
    throw new TRPCError({
      code: 'SERVICE_UNAVAILABLE',
      message: 'WebSocket service not initialized'
    });
  }
  return service;
};

const safeWebSocketOperation = async <T>(operation: () => Promise<T>): Promise<T> => {
  try {
    return await operation();
  } catch (error) {
    logger.error('WebSocket operation failed:', error);
    throw new TRPCError({
      code: 'INTERNAL_SERVER_ERROR',
      message: 'WebSocket operation failed'
    });
  }
};

const joinRoomSchema = z.object({
  room: z.string(),
  userId: z.string(),
  companyId: z.string()
});

const sendNotificationSchema = z.object({
  type: z.enum(['document', 'sii', 'system', 'chat']),
  targetUserId: z.string().optional(),
  targetCompanyId: z.string().optional(),
  data: z.record(z.string(), z.any()),
  message: z.string()
});

export const websocketRouter = router({
  /**
   * Obtener información del servidor WebSocket
   */
  getServerInfo: publicProcedure
    .query(async ({ ctx }) => {
      try {
        const wsService = ensureWebSocketService();
        const info = await safeWebSocketOperation(() => wsService.getServerInfo());
        
        return {
          ...(info || {}),
          status: 'active',
          timestamp: new Date()
        };
      } catch (error) {
        logger.error('Error getting WebSocket server info:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error obteniendo información del servidor WebSocket'
        });
      }
    }),

  /**
   * Obtener conexiones activas de la empresa
   */
  getCompanyConnections: companyProcedure
    .query(async ({ ctx }) => {
      try {
        const wsService = ensureWebSocketService();
        const connections = wsService.getCompanyConnections(ctx.user.companyId);
        
        return {
          companyId: ctx.user.companyId,
          activeConnections: connections.length,
          connections: connections.map((socket: any) => ({
            socketId: socket.id,
            userId: socket.userId,
            authenticated: socket.authenticated,
            connectedAt: socket.handshake.time
          }))
        };
      } catch (error) {
        logger.error('Error getting company connections:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error obteniendo conexiones de la empresa'
        });
      }
    }),

  /**
   * Enviar notificación manual (para testing o casos especiales)
   */
  sendNotification: companyProcedure
    .input(sendNotificationSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        const wsService = ensureWebSocketService();
        const targetCompanyId = input.targetCompanyId || ctx.user.companyId;
        
        await safeWebSocketOperation(async () => {
          switch (input.type) {
            case 'document':
              await wsService.broadcastDocumentEvent({
                document_id: input.data.document_id || 'manual',
                document_type: input.data.document_type || 33,
                folio_number: input.data.folio_number || 0,
                status: input.data.status || 'draft',
                action: input.data.action || 'manual_notification'
              }, targetCompanyId, input.targetUserId);
              break;

            case 'sii':
              await wsService.broadcastSIIResponse({
              track_id: input.data.track_id || 'manual',
              document_id: input.data.document_id || 'manual',
              company_id: targetCompanyId,
              current_status: input.data.status || 'ENVIADO',
              submission_timestamp: new Date().toISOString(),
              sii_responses: [{ response_message: input.message }]
            }, targetCompanyId, input.targetUserId);
            break;

          case 'system':
            await wsService.broadcastSystemNotification({
              notification_type: input.data.notification_type || 'system_maintenance',
              message: input.message,
              urgency_level: input.data.urgency_level || 'medium',
              action_required: input.data.action_required || false,
              deadline: input.data.deadline ? new Date(input.data.deadline) : undefined,
              affected_companies: [targetCompanyId]
            });
            break;

          case 'chat':
            await wsService.broadcastChatResponse({
              _id: input.data.session_id || 'manual',
              session_id: input.data.session_id || 'manual',
              user_id: input.targetUserId || ctx.user.id,
              company_id: targetCompanyId,
              messages: [{ role: input.data.role || 'assistant', content: input.message }],
              is_active: true,
              session_metadata: { ai_model: input.data.ai_model }
            }, input.targetUserId || ctx.user.id, targetCompanyId);
            break;
          }
        });

        logger.info(`📡 Manual notification sent: ${input.type} to ${targetCompanyId}`);

        return {
          success: true,
          type: input.type,
          targetCompanyId,
          targetUserId: input.targetUserId,
          message: input.message,
          timestamp: new Date()
        };

      } catch (error) {
        logger.error('Error sending manual notification:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error enviando notificación manual'
        });
      }
    }),

  /**
   * Obtener estadísticas de eventos WebSocket
   */
  getEventStats: companyProcedure
    .query(async ({ ctx }) => {
      try {
        // Aquí podrías implementar estadísticas desde Redis o MongoDB
        // Por ahora retornamos info básica del servicio
        
        const wsService = ensureWebSocketService();
        const info = await safeWebSocketOperation(() => wsService.getServerInfo());
        const companyConnections = wsService.getCompanyConnections(ctx.user.companyId);
        
        const serverInfo = info as any;
        return {
          companyId: ctx.user.companyId,
          activeConnections: companyConnections.length,
          totalServerConnections: serverInfo?.connectedClients || 0,
          serverUptime: serverInfo?.serverTime || 0,
          redisConnected: serverInfo?.redisConnected || false,
          // Estas estadísticas se pueden expandir con datos reales de MongoDB
          eventsLast24h: {
            documents: 0,
            aiAnalysis: 0,
            siiResponses: 0,
            chatMessages: 0
          }
        };

      } catch (error) {
        logger.error('Error getting WebSocket event stats:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error obteniendo estadísticas de eventos'
        });
      }
    })
});
import { router, companyProcedure } from '../init';
import { TRPCError } from '@trpc/server';
import { redisPublisher } from '../../models/redis';
import { WEBSOCKET_EVENTS } from '../../models/websocket';
import { 
  // Nuevos schemas Redis Pub/Sub
  chatRequestSchema,
  createChatSessionSchema,
  documentAnalysisRequestSchema,
  ollamaStatusRequestSchema,
  getChatHistorySchema,
  getAnalysisStatusSchema,
  getWebSocketEventsSchema,
  // Tipos
  ChatRequest,
  DocumentAnalysisRequest,
  REDIS_CHANNELS,
  ANALYSIS_TYPES,
  CONTEXT_TYPES
} from '../schemas/ai';

// Método auxiliar para estimar tiempo de análisis
const getEstimatedAnalysisTime = (analysisType: string): number => {
  const times: Record<string, number> = {
    'anomaly_detection': 5000, // RF012: ≤5 segundos
    'cash_flow_prediction': 8000,
    'tax_optimization': 12000
  };
  return times[analysisType] || 10000;
};

// Helper para WebSocket service
const safeWebSocketBroadcast = async (data: any, userId: string, companyId: string) => {
  try {
    const globalScope = global as any;
    if (globalScope.webSocketService && typeof globalScope.webSocketService.broadcastChatResponse === 'function') {
      await globalScope.webSocketService.broadcastChatResponse(data, userId, companyId);
    }
  } catch (error) {
    console.warn('WebSocket broadcast failed:', error);
  }
};

// Helper para WebSocket document events
const safeWebSocketDocumentEvent = async (eventData: any, companyId: string, userId: string) => {
  try {
    const globalScope = global as any;
    if (globalScope.webSocketService && typeof globalScope.webSocketService.broadcastDocumentEvent === 'function') {
      await globalScope.webSocketService.broadcastDocumentEvent(eventData, companyId, userId);
    }
  } catch (error) {
    console.warn('WebSocket document event failed:', error);
  }
};



export const aiRouter = router({
  /**
   * Enviar mensaje al chat IA (RF012)
   * El backend Python procesará el mensaje vía Redis Pub/Sub
   */
  sendMessage: companyProcedure
    .input(chatRequestSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        // 1. Generar IDs únicos
        const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // 2. Crear payload para Python IA via Redis
        const redisPayload = {
          eventId: messageId,
          eventType: 'chat_request',
          sessionId: input.sessionId,
          userId: input.userId,
          companyId: input.companyId,
          message: input.message,
          contextType: input.contextType || 'general',
          contextData: input.contextData,
          priority: input.priority || 'normal',
          timestamp: new Date().toISOString()
        };
        
        // 3. Publicar a Redis canal de chat requests
        await redisPublisher.publish(
          REDIS_CHANNELS.CHAT_REQUESTS,
          JSON.stringify(redisPayload)
        );

        // 4. Notificar vía WebSocket que el mensaje fue enviado
        await safeWebSocketBroadcast({
          _id: input.sessionId,
          session_id: input.sessionId,
          user_id: input.userId,
          company_id: input.companyId,
          messages: [{ role: 'user', content: input.message }],
          is_active: true,
          session_metadata: {}
        }, input.userId, input.companyId);

        console.log(`💬 Mensaje IA enviado: ${input.sessionId} - ${input.message.substring(0, 50)}...`);

        return {
          messageId,
          sessionId: input.sessionId,
          status: 'sent',
          timestamp: new Date(),
          message: 'Mensaje enviado al asistente IA. Procesando respuesta...'
        };

      } catch (error) {
        console.error('Error enviando mensaje IA:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error comunicándose con el asistente IA'
        });
      }
    }),

  /**
   * Solicitar análisis IA específico (RF012)
   * Análisis predictivo, detección anomalías, predicciones flujo caja
   */
  requestAnalysis: companyProcedure
    .input(documentAnalysisRequestSchema)
    .mutation(async ({ ctx, input }) => {
      try {
        const requestId = `analysis_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // Crear payload para análisis IA via Redis
        const analysisPayload = {
          eventId: requestId,
          eventType: 'document_analysis',
          documentId: input.documentId,
          userId: input.userId,
          companyId: input.companyId,
          analysisType: input.analysisType,
          documentData: input.documentData,
          priority: input.priority,
          metadata: {
            ...input.metadata,
            requestedBy: ctx.user.email,
            companyContext: {
              companyId: input.companyId
            }
          },
          timestamp: new Date().toISOString()
        };

        // Publicar a Redis canal de analysis requests  
        await redisPublisher.publish(
          REDIS_CHANNELS.ANALYSIS_REQUESTS,
          JSON.stringify(analysisPayload)
        );

        // Notificar vía WebSocket que el análisis ha iniciado
        await safeWebSocketDocumentEvent({
          document_id: input.documentId,
          document_type: (input.documentData as any)?.document_type || 0,
          folio_number: (input.documentData as any)?.folio_number || 0,
          status: 'draft',
          action: 'ai_analysis_started'
        }, input.companyId, input.userId);

        console.log(`🔬 Análisis IA solicitado: ${input.analysisType} - ${requestId}`);

        return {
          requestId,
          analysisType: input.analysisType,
          status: 'pending',
          estimatedTime: getEstimatedAnalysisTime(input.analysisType),
          message: `Análisis ${input.analysisType} iniciado. Recibirás una notificación cuando esté listo.`
        };

      } catch (error) {
        console.error('Error solicitando análisis IA:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error iniciando análisis IA'
        });
      }
    }),

  /**
   * Obtener historial de sesiones de chat
   */
  getChatSessions: companyProcedure
    .input(getChatHistorySchema)
    .query(async ({ ctx, input }) => {
      try {
        // Solicitud de historial de chat via Redis a Python IA
        const requestId = `chat_history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Crear payload para solicitud de historial
        const historyPayload = {
          eventId: requestId,
          eventType: 'chat_history_request',
          userId: input.userId,
          companyId: input.companyId,
          sessionId: input.sessionId,
          limit: input.limit,
          skip: input.skip,
          timestamp: new Date().toISOString()
        };
        
        // Publicar a Redis
        await redisPublisher.publish(
          REDIS_CHANNELS.AI_REQUESTS,
          JSON.stringify(historyPayload)
        );

        // Por ahora retornamos respuesta indicando procesamiento asíncrono
        return {
          sessions: [],
          total: 0,
          hasMore: false,
          message: 'Sesiones de chat siendo procesadas por IA. Los resultados llegarán via WebSocket.',
          requestId
        };

      } catch (error) {
        console.error('Error solicitando sesiones de chat:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error comunicándose con el sistema de chat IA'
        });
      }
    }),

  /**
   * Obtener mensajes de una sesión específica
   */
  getSessionMessages: companyProcedure
    .input(getChatHistorySchema)
    .query(async ({ ctx, input }) => {
      try {
        const requestId = `session_messages_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Crear payload para mensajes de sesión
        const messagesPayload = {
          eventId: requestId,
          eventType: 'session_messages_request',
          userId: input.userId,
          companyId: input.companyId,
          sessionId: input.sessionId,
          limit: input.limit,
          skip: input.skip,
          timestamp: new Date().toISOString()
        };
        
        // Solicitar mensajes a Python IA via Redis
        await redisPublisher.publish(
          REDIS_CHANNELS.AI_REQUESTS,
          JSON.stringify(messagesPayload)
        );

        return {
          messages: [],
          sessionId: input.sessionId,
          total: 0,
          message: 'Mensajes siendo recuperados del sistema IA. Resultados via WebSocket.',
          requestId
        };

      } catch (error) {
        console.error('Error solicitando mensajes de sesión:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error comunicándose con el sistema de chat IA'
        });
      }
    }),

  /**
   * Obtener estado de análisis IA pendientes
   */
  getAnalysisStatus: companyProcedure
    .input(getAnalysisStatusSchema)
    .query(async ({ ctx, input }) => {
      try {
        const requestId = `analysis_status_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Crear payload para estado de análisis
        const statusPayload = {
          eventId: requestId,
          eventType: 'analysis_status_request',
          userId: input.userId,
          companyId: input.companyId,
          documentId: input.documentId,
          analysisId: input.analysisId,
          riskLevel: input.riskLevel,
          analysisType: input.analysisType,
          limit: input.limit,
          skip: input.skip,
          timestamp: new Date().toISOString()
        };
        
        // Solicitar estado a Python IA via Redis
        await redisPublisher.publish(
          REDIS_CHANNELS.AI_REQUESTS,
          JSON.stringify(statusPayload)
        );

        return {
          analysis: [],
          total: 0,
          message: 'Estado de análisis siendo consultado en sistema IA. Resultados via WebSocket.',
          requestId
        };

      } catch (error) {
        console.error('Error solicitando estado de análisis:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error comunicándose con el sistema de análisis IA'
        });
      }
    }),

  /**
   * Obtener métricas IA en tiempo real (RF012: ≤2s latencia)
   */
  getAIMetrics: companyProcedure
    .query(async ({ ctx }) => {
      try {
        const startTime = Date.now();
        const requestId = `ai_metrics_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Crear payload para métricas IA
        const metricsPayload = {
          eventId: requestId,
          eventType: 'ai_metrics_request',
          userId: ctx.user.id,
          companyId: ctx.user.companyId,
          timestamp: new Date().toISOString()
        };
        
        // Solicitar métricas a Python IA via Redis
        await redisPublisher.publish(
          REDIS_CHANNELS.AI_REQUESTS,
          JSON.stringify(metricsPayload)
        );

        const responseTime = Date.now() - startTime;

        return {
          message: 'Métricas IA siendo consultadas en sistema IA. Resultados via WebSocket.',
          requestId,
          responseTime,
          meetsLatencySLA: responseTime <= 2000, // RF012: ≤2s latencia
          status: 'processing'
        };

      } catch (error) {
        console.error('Error solicitando métricas IA:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error comunicándose con el sistema de métricas IA'
        });
      }
    }),


});
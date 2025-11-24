import { Server, Socket } from 'socket.io';
import { Server as HTTPServer } from 'http';
import { verifyToken } from '../middleware/auth';
import { eventService, EventType } from '../services/eventService';

import { TokenPayload } from '../trpc/schemas/users';
import { 
  DocumentCreateData, 
  DocumentStatusData,
  FolioWarningData,
  LocalAuthenticatedSocket
} from '../trpc/schemas/websocket';

interface AuthenticatedSocket extends Socket, LocalAuthenticatedSocket {}

// Configurar WebSocket con autenticación
export const setupWebSocket = (server: HTTPServer) => {
  const corsOrigins = process.env.CORS_ORIGIN ? 
    process.env.CORS_ORIGIN.split(',').map(origin => origin.trim()) : 
    ["http://localhost:3000"];

  const io = new Server(server, {
    cors: {
      origin: corsOrigins,
      methods: ["GET", "POST"],
      credentials: true
    }
  });

  // Middleware de autenticación para WebSocket - TEMPORALMENTE DESHABILITADO PARA TESTING
  io.use((socket: AuthenticatedSocket, next) => {
    const token = socket.handshake.auth.token;
    
    // TEMPORAL: Permitir conexión sin token para testing
    if (!token) {
      console.log('⚠️ Conexión sin token - usando datos de prueba');
      socket.userId = 'test-user-123';
      socket.companyId = 'test-company-456';
      socket.userEmail = 'test@example.com';
      return next();
    }

    try {
      const decoded = verifyToken(token) as TokenPayload;
      socket.userId = decoded.id;
      socket.companyId = decoded.companyId;
      socket.userEmail = decoded.email;
      next();
    } catch (error) {
      console.log('⚠️ Token inválido - usando datos de prueba para testing');
      socket.userId = 'test-user-123';
      socket.companyId = 'test-company-456';
      socket.userEmail = 'test@example.com';
      next();
    }
  });

  // Configurar EventService con Socket.IO
  eventService.setSocketIO(io);

  // Manejar conexiones WebSocket
  io.on('connection', (socket: AuthenticatedSocket) => {
    console.log(`🔗 WebSocket conectado - SETUP INICIADO`);
    console.log(`   - Socket ID: ${socket.id}`);
    console.log(`   - User ID: ${socket.userId}`);
    console.log(`   - Company ID: ${socket.companyId}`);
    console.log(`   - User Email: ${socket.userEmail}`);

    // Unir el socket a una room de la empresa
    if (socket.companyId) {
      socket.join(`company:${socket.companyId}`);
      console.log(`👥 Usuario unido a empresa: ${socket.companyId}`);
    }

    // Unir a room personal
    socket.join(`user:${socket.userId}`);

    // DEBUG: Capturar TODOS los eventos para debugging
    socket.onAny((eventName, ...args) => {
      console.log(`🎯 EVENTO RECIBIDO: ${eventName}`, args);
    });

    // Eventos personalizados usando EventService (RF010)
    socket.on('document:create', async (data: DocumentCreateData) => {
      console.log('📄 Documento creado:', data);
      
      if (socket.companyId) {
        await eventService.publishDocumentEvent({
          id: '',
          type: EventType.DOCUMENT_CREATED,
          timestamp: new Date(),
          companyId: socket.companyId,
          userId: socket.userId,
          documentId: data.documentId,
          documentType: parseInt(data.type),
          folioNumber: parseInt(data.folio),
          amount: 0, // Se completaría con datos reales
          metadata: {
            createdBy: socket.userEmail,
            socketId: socket.id
          }
        });
      }
    });

    socket.on('document:status', async (data: DocumentStatusData) => {
      console.log('📋 Estado documento actualizado:', data);
      
      if (socket.companyId) {
        await eventService.publishDocumentEvent({
          id: '',
          type: EventType.DOCUMENT_STATUS_UPDATED,
          timestamp: new Date(),
          companyId: socket.companyId,
          userId: socket.userId,
          documentId: data.documentId,
          documentType: 0, // Se completaría con datos reales
          folioNumber: 0,
          amount: 0,
          status: data.status,
          metadata: {
            updatedBy: socket.userEmail,
            socketId: socket.id
          }
        });
      }
    });

    socket.on('folio:warning', async (data: FolioWarningData) => {
      console.log('⚠️ Advertencia de folios:', data);
      
      if (socket.companyId) {
        await eventService.publishFolioAlert({
          type: EventType.FOLIO_ALERT,
          companyId: socket.companyId,
          userId: socket.userId,
          message: `Folios agotándose: ${data.remaining} restantes para tipo ${data.documentType}`,
          severity: data.remaining <= 10 ? 'error' : 'warning',
          data: {
            documentType: parseInt(data.documentType.toString()),
            currentFolio: 0,
            remainingFolios: data.remaining
          }
        });
      }
    });

    // RF012: Eventos de chat IA
    console.log('📋 Registrando handler para evento: ai:chat');
    socket.on('ai:chat', async (data: { message: string; sessionId: string }) => {
      console.log('🚀 EVENTO AI:CHAT RECIBIDO:', data);
      console.log('🔍 Socket info:', {
        id: socket.id,
        userId: socket.userId,
        companyId: socket.companyId,
        userEmail: socket.userEmail
      });
      
      if (socket.companyId) {
        console.log('📤 Publicando mensaje a EventService...');
        try {
          await eventService.publishChatMessage({
            id: '',
            type: EventType.AI_CHAT_MESSAGE,
            timestamp: new Date(),
            companyId: socket.companyId,
            userId: socket.userId,
            sessionId: data.sessionId,
            message: data.message,
            messageType: 'user',
            context: {
              socketId: socket.id,
              userEmail: socket.userEmail
            }
          });
          console.log('✅ Mensaje publicado exitosamente via EventService');
        } catch (error) {
          console.log('❌ Error publicando mensaje:', error);
        }
      } else {
        console.log('❌ No hay companyId - mensaje no publicado');
      }
    });

    // RF011: Solicitar análisis IA
    socket.on('ai:analyze', async (data: { documentId: string; analysisType: string }) => {
      console.log('🔬 Análisis IA solicitado:', data);
      
      if (socket.companyId) {
        await eventService.requestAIAnalysis({
          id: '',
          type: EventType.AI_ANALYSIS_REQUEST,
          timestamp: new Date(),
          companyId: socket.companyId,
          userId: socket.userId,
          documentId: data.documentId,
          analysisType: data.analysisType as 'anomaly_detection' | 'cash_flow_prediction' | 'tax_optimization',
          inputData: { documentId: data.documentId },
          priority: 'medium'
        });
      }
    });

    // Evento de desconexión
    socket.on('disconnect', () => {
      console.log(`❌ WebSocket desconectado: ${socket.userEmail} (${socket.id})`);
    });

    // Evento de error
    socket.on('error', (error: Error) => {
      console.error('🔴 Error WebSocket:', error.message);
    });

    console.log(`🎉 SETUP WEBSOCKET COMPLETADO para ${socket.id}`);
    console.log(`📋 Handlers registrados: ai:chat, ai:analyze, document:create, etc.`);
  });

  return io;
};
/**
 * Servicio WebSocket - CloudMusic DTE
 * Manejo de conexiones tiempo real y broadcasting de eventos
 */

import { Server as HTTPServer } from 'http';
import { Server as SocketIOServer, Socket } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { RedisService } from './redis';
import { logger } from '../utils/logger';
import { 
  WebSocketEvent, 
  WebSocketMessage, 
  DocumentNotification,
  AIAnalysisNotification,
  SIIResponseNotification,
  ChatNotification,
  SystemNotification,
  CompanyUserNotification,
  WEBSOCKET_ROOMS,
  WEBSOCKET_EVENTS
} from '../models/websocket';

interface AuthenticatedSocket extends Socket {
  userId?: string;
  companyId?: string;
  authenticated?: boolean;
}

export class WebSocketService {
  private io: SocketIOServer;
  private redisService: RedisService;
  private connectedClients: Map<string, AuthenticatedSocket> = new Map();
  private userRooms: Map<string, Set<string>> = new Map();

  constructor(server: HTTPServer, redisService: RedisService) {
    this.redisService = redisService;
    
    // Configurar Socket.IO
    this.io = new SocketIOServer(server, {
      cors: {
        origin: process.env.FRONTEND_URL || "http://localhost:3000",
        methods: ["GET", "POST"],
        credentials: true
      },
      transports: ['websocket', 'polling']
    });

    this.setupRedisAdapter();
    this.setupEventHandlers();
    this.setupRedisSubscriptions();
    
    logger.info('🔄 WebSocket service initialized');
  }

  private async setupRedisAdapter() {
    try {
      // Usar Redis como adaptador para múltiples instancias
      const pubClient = this.redisService.getClient();
      const subClient = pubClient.duplicate();
      
      await subClient.connect();
      
      this.io.adapter(createAdapter(pubClient, subClient));
      logger.info('✅ Redis adapter configured for Socket.IO');
    } catch (error) {
      logger.error('❌ Error setting up Redis adapter:', error);
    }
  }

  private setupEventHandlers() {
    this.io.on('connection', (socket: AuthenticatedSocket) => {
      logger.info(`🔌 New WebSocket connection: ${socket.id}`);
      
      // Manejar autenticación
      socket.on('authenticate', async (data: { token: string, userId: string, companyId: string }) => {
        try {
          // Aquí validarías el JWT token
          // Por ahora simulamos autenticación exitosa
          socket.userId = data.userId;
          socket.companyId = data.companyId;
          socket.authenticated = true;
          
          // Registrar cliente conectado
          this.connectedClients.set(socket.id, socket);
          
          // Unir a salas apropiadas
          await this.joinUserRooms(socket, data.userId, data.companyId);
          
          // Confirmar autenticación
          socket.emit('authenticated', { 
            success: true, 
            userId: data.userId || 'test_user_123',
            companyId: data.companyId || 'test_company_456'
          });
          
          // Notificar login via Redis
          await this.publishUserEvent('user_login', {
            user_id: data.userId,
            company_id: data.companyId,
            connection_id: socket.id
          });
          
          logger.info(`✅ Socket ${socket.id} authenticated as user ${data.userId}`);
          
        } catch (error) {
          logger.error(`❌ Authentication failed for socket ${socket.id}:`, error);
          socket.emit('authentication_error', { message: 'Invalid credentials' });
          socket.disconnect();
        }
      });

      // Manejar unión manual a salas
      socket.on('join_room', (data: { room: string }) => {
        if (socket.authenticated) {
          const room = data.room || data;
          const roomName = typeof room === 'string' ? room : room.room;
          socket.join(roomName);
          this.addUserToRoom(socket.userId!, roomName);
          socket.emit('joined_room', { room: roomName });
          logger.debug(`📢 Socket ${socket.id} joined room: ${roomName}`);
        }
      });

      // Manejar salida de salas
      socket.on('leave_room', (room: string) => {
        if (socket.authenticated) {
          socket.leave(room);
          this.removeUserFromRoom(socket.userId!, room);
          logger.debug(`📢 Socket ${socket.id} left room: ${room}`);
        }
      });

      // Manejar mensajes de chat (múltiples formatos para compatibilidad)
      socket.on('chat_message', async (data: any) => {
        if (socket.authenticated) {
          await this.handleChatMessage(socket, data);
        }
      });
      
      // También escuchar formato ai:chat para compatibilidad
      socket.on('ai:chat', async (data: any) => {
        logger.debug('🎯 Evento ai:chat recibido (formato alternativo)');
        if (socket.authenticated) {
          await this.handleChatMessage(socket, data);
        }
      });

      // Manejar desconexión
      socket.on('disconnect', async (reason) => {
        logger.info(`🔌 Socket ${socket.id} disconnected: ${reason}`);
        
        if (socket.authenticated && socket.userId) {
          // Notificar logout via Redis
          await this.publishUserEvent('user_logout', {
            user_id: socket.userId,
            company_id: socket.companyId,
            connection_id: socket.id,
            reason
          });
          
          // Limpiar referencias
          this.connectedClients.delete(socket.id);
          this.cleanupUserRooms(socket.userId);
        }
      });
    });
  }

  private async setupRedisSubscriptions() {
    try {
      // Suscribirse a eventos desde Python IA backend
      await this.redisService.subscribe('cloudmusic_dte:websocket_events', (message) => {
        this.handleRedisWebSocketEvent(JSON.parse(message));
      });

      // Suscribirse a respuestas de análisis IA
      await this.redisService.subscribe('cloudmusic_dte:ai_responses', (message) => {
        this.handleAIResponse(JSON.parse(message));
      });

      // Suscribirse a eventos del sistema
      await this.redisService.subscribe('cloudmusic_dte:system_events', (message) => {
        this.handleSystemEvent(JSON.parse(message));
      });

      logger.info('✅ WebSocket Redis subscriptions configured');
    } catch (error) {
      logger.error('❌ Error setting up Redis subscriptions:', error);
    }
  }

  private async joinUserRooms(socket: AuthenticatedSocket, userId: string, companyId: string) {
    const rooms = [
      WEBSOCKET_ROOMS.USER(userId),
      WEBSOCKET_ROOMS.COMPANY(companyId),
      WEBSOCKET_ROOMS.DOCUMENTS(companyId),
      WEBSOCKET_ROOMS.AI_CHAT(companyId),
      WEBSOCKET_ROOMS.SII_MONITOR(companyId)
    ];

    for (const room of rooms) {
      socket.join(room);
      this.addUserToRoom(userId, room);
    }

    logger.debug(`📢 User ${userId} joined ${rooms.length} rooms`);
  }

  private addUserToRoom(userId: string, room: string) {
    if (!this.userRooms.has(userId)) {
      this.userRooms.set(userId, new Set());
    }
    this.userRooms.get(userId)!.add(room);
  }

  private removeUserFromRoom(userId: string, room: string) {
    const userRoomsSet = this.userRooms.get(userId);
    if (userRoomsSet) {
      userRoomsSet.delete(room);
    }
  }

  private cleanupUserRooms(userId: string) {
    this.userRooms.delete(userId);
  }

  // === MANEJADORES DE EVENTOS ===

  private async handleRedisWebSocketEvent(event: WebSocketEvent) {
    try {
      logger.debug(`📡 Broadcasting WebSocket event: ${event.event_type}`);
      
      // Determinar salas de destino
      const targetRooms = this.determineTargetRooms(event);
      
      // Broadcast a las salas apropiadas
      for (const room of targetRooms) {
        this.io.to(room).emit(event.event_type, {
          ...event,
          timestamp: new Date()
        });
      }

      // Marcar evento como procesado en Redis
      await this.redisService.publish('cloudmusic_dte:websocket_processed', 
        JSON.stringify({ event_id: event.event_id, processed: true })
      );

    } catch (error) {
      logger.error('❌ Error handling WebSocket event:', error);
    }
  }

  private async handleAIResponse(response: any) {
    try {
      logger.debug('🤖 AI Response recibido:', response);
      
      // Manejar respuestas de chat
      if (response.type === 'chat_response') {
        return await this.handleChatResponse(response);
      }
      
      // Manejar análisis de documentos (formato original)
      const notification: AIAnalysisNotification = {
        _id: response._id || response.analysis_id,
        document_id: response.document_id,
        company_id: response.company_id,
        analysis_type: response.analysis_type,
        ai_model: response.ai_model || 'ollama',
        compliance_score: response.compliance_score,
        risk_level: response.risk_level,
        processing_time_ms: response.processing_time_ms,
        confidence_level: response.confidence_level
      };

      // Enviar a salas relevantes basadas en MongoDB structure
      if (response.company_id) {
        this.io.to(WEBSOCKET_ROOMS.AI_CHAT(response.company_id)).emit(
          WEBSOCKET_EVENTS.AI_ANALYSIS_COMPLETED, 
          notification
        );
      }

      if (response.user_id) {
        this.io.to(WEBSOCKET_ROOMS.USER(response.user_id)).emit(
          WEBSOCKET_EVENTS.AI_ANALYSIS_COMPLETED,
          notification
        );
      }

      logger.info(`🤖 AI analysis notification sent: ${response._id || response.analysis_id}`);
    } catch (error) {
      logger.error('❌ Error handling AI response:', error);
    }
  }

  private async handleChatMessage(socket: AuthenticatedSocket, data: any) {
    try {
      // Manejar tanto 'message' como 'mensaje' para compatibilidad
      const messageContent = data.message || data.mensaje;
      
      const chatMessage = {
        session_id: data.session_id,
        user_id: socket.userId!,
        company_id: socket.companyId!,
        message: messageContent,
        timestamp: new Date()
      };

      // Enviar mensaje al backend IA via Redis
      await this.redisService.publish('cloudmusic_dte:chat_requests', 
        JSON.stringify(chatMessage)
      );

      // Confirmar recepción al cliente
      socket.emit('message_sent', { 
        message_id: data.message_id || `msg_${Date.now()}`,
        status: 'sent' 
      });

      logger.debug(`💬 Chat message forwarded to AI backend from user ${socket.userId}`);
    } catch (error) {
      logger.error('❌ Error handling chat message:', error);
    }
  }

  private async handleChatResponse(response: any) {
    try {
      logger.info(`💬 Chat response para sesión ${response.sessionId}`);
      
      // Buscar usuarios en esa sesión (por company_id si está disponible)
      // Por ahora, enviar a todas las salas de IA chat
      const companies = this.getActiveCompanies();
      
      for (const companyId of companies) {
        const room = WEBSOCKET_ROOMS.AI_CHAT(companyId);
        this.io.to(room).emit(WEBSOCKET_EVENTS.AI_CHAT_MESSAGE, {
          session_id: response.sessionId,
          message: response.message,
          timestamp: response.timestamp,
          metadata: response.metadata || {}
        });
        
        logger.debug(`📤 Chat response enviado a sala: ${room}`);
      }
      
    } catch (error) {
      logger.error('❌ Error handling chat response:', error);
    }
  }

  private getActiveCompanies(): string[] {
    // Obtener IDs de companies activas desde sockets conectados
    const companies = new Set<string>();
    
    for (const socket of this.io.sockets.sockets.values()) {
      const authSocket = socket as AuthenticatedSocket;
      if (authSocket.authenticated && authSocket.companyId) {
        companies.add(authSocket.companyId);
      }
    }
    
    return Array.from(companies);
  }

  private async handleSystemEvent(event: any) {
    try {
      // Broadcast eventos del sistema a todas las conexiones relevantes
      this.io.to(WEBSOCKET_ROOMS.SYSTEM_NOTIFICATIONS).emit(
        WEBSOCKET_EVENTS.SYSTEM_NOTIFICATION,
        event
      );

      // Si es crítico, enviar a administradores
      if (event.urgency_level === 'critical') {
        this.io.to(WEBSOCKET_ROOMS.ADMIN_GLOBAL).emit(
          WEBSOCKET_EVENTS.ERROR_NOTIFICATION,
          event
        );
      }

      logger.info(`🚨 System event broadcasted: ${event.notification_type}`);
    } catch (error) {
      logger.error('❌ Error handling system event:', error);
    }
  }

  private determineTargetRooms(event: WebSocketEvent): string[] {
    const rooms: string[] = [];

    // Salas basadas en broadcast_to
    if (event.broadcast_to) {
      rooms.push(...event.broadcast_to);
    }

    // Salas basadas en user_id y company_id
    if (event.user_id) {
      rooms.push(WEBSOCKET_ROOMS.USER(event.user_id));
    }

    if (event.company_id) {
      rooms.push(WEBSOCKET_ROOMS.COMPANY(event.company_id));
      
      // Agregar salas específicas por tipo de evento
      switch (event.event_type) {
        case 'document_created':
        case 'document_signed':
          rooms.push(WEBSOCKET_ROOMS.DOCUMENTS(event.company_id));
          break;
          
        case 'ai_analysis_completed':
          rooms.push(WEBSOCKET_ROOMS.AI_CHAT(event.company_id));
          break;
          
        case 'sii_submission':
          rooms.push(WEBSOCKET_ROOMS.SII_MONITOR(event.company_id));
          break;
      }
    }

    return Array.from(new Set(rooms)); // Eliminar duplicados
  }

  // === MÉTODOS PÚBLICOS PARA BROADCASTING ===

  public async broadcastDocumentEvent(notification: DocumentNotification, companyId: string, userId?: string) {
    const rooms = [WEBSOCKET_ROOMS.DOCUMENTS(companyId)];
    if (userId) rooms.push(WEBSOCKET_ROOMS.USER(userId));

    for (const room of rooms) {
      this.io.to(room).emit(WEBSOCKET_EVENTS.DOCUMENT_UPDATED, notification);
    }

    logger.info(`📄 Document event broadcasted: ${notification.document_id}`);
  }

  public async broadcastSIIResponse(notification: SIIResponseNotification, companyId: string, userId?: string) {
    const rooms = [WEBSOCKET_ROOMS.SII_MONITOR(companyId)];
    if (userId) rooms.push(WEBSOCKET_ROOMS.USER(userId));

    for (const room of rooms) {
      this.io.to(room).emit(WEBSOCKET_EVENTS.SII_RESPONSE, notification);
    }

    logger.info(`📡 SII response broadcasted: ${notification.track_id}`);
  }

  public async broadcastSystemNotification(notification: SystemNotification) {
    this.io.to(WEBSOCKET_ROOMS.SYSTEM_NOTIFICATIONS).emit(
      WEBSOCKET_EVENTS.SYSTEM_NOTIFICATION,
      notification
    );

    logger.info(`🚨 System notification broadcasted: ${notification.notification_type}`);
  }

  public async broadcastChatResponse(notification: ChatNotification, userId: string, companyId: string) {
    const rooms = [
      WEBSOCKET_ROOMS.USER(userId),
      WEBSOCKET_ROOMS.AI_CHAT(companyId)
    ];

    for (const room of rooms) {
      this.io.to(room).emit(WEBSOCKET_EVENTS.AI_CHAT_MESSAGE, notification);
    }

    logger.debug(`💬 Chat response broadcasted to user ${userId}`);
  }

  public async broadcastCompanyUserEvent(notification: CompanyUserNotification, companyId: string) {
    const rooms = [
      WEBSOCKET_ROOMS.COMPANY(companyId),
      WEBSOCKET_ROOMS.ADMIN_PANEL(companyId),
      WEBSOCKET_ROOMS.USER(notification.user_id) // Notificar al usuario afectado
    ];

    const eventMap = {
      assigned: WEBSOCKET_EVENTS.COMPANY_USER_ASSIGNED,
      updated: WEBSOCKET_EVENTS.COMPANY_USER_UPDATED,
      removed: WEBSOCKET_EVENTS.COMPANY_USER_REMOVED
    };

    const eventType = eventMap[notification.action];

    for (const room of rooms) {
      this.io.to(room).emit(eventType, notification);
    }

    await this.publishUserEvent(eventType, {
      event_id: `company_user_${Date.now()}`,
      event_type: eventType,
      user_id: notification.user_id,
      company_id: companyId,
      session_id: '',
      connection_id: '',
      data: notification,
      processed: false,
      created_at: new Date().toISOString(),
      timestamp: new Date().toISOString(),
      broadcast_to: rooms
    });

    logger.info(`🏢 Company user event broadcasted: ${notification.action} - ${notification.user_name}`);
  }

  private async publishUserEvent(eventType: string, data: any) {
    try {
      const event = {
        event_id: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        event_type: eventType,
        timestamp: new Date(),
        ...data
      };

      await this.redisService.publish('cloudmusic_dte:websocket_events', JSON.stringify(event));
    } catch (error) {
      logger.error(`❌ Error publishing user event ${eventType}:`, error);
    }
  }

  // === MÉTODOS DE UTILIDAD ===

  public getConnectedClientsCount(): number {
    return this.connectedClients.size;
  }

  public getUserConnections(userId: string): AuthenticatedSocket[] {
    return Array.from(this.connectedClients.values())
      .filter(socket => socket.userId === userId);
  }

  public getCompanyConnections(companyId: string): AuthenticatedSocket[] {
    return Array.from(this.connectedClients.values())
      .filter(socket => socket.companyId === companyId);
  }

  public async getServerInfo() {
    return {
      connectedClients: this.connectedClients.size,
      totalRooms: this.userRooms.size,
      serverTime: new Date(),
      redisConnected: await this.redisService.ping()
    };
  }
}
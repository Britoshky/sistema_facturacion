// import { redisPublisher, redisSubscriber } from '../models/redis'; // DESHABILITADO
import { Server as SocketIOServer } from 'socket.io';
import { 
  EventType, 
  BaseEvent, 
  DocumentEvent, 
  AIAnalysisEvent,
  AIResultEvent,
  ChatEvent
} from '../trpc/schemas/websocket';

// Re-export EventType para que otros módulos puedan importarlo
export { EventType };

export class EventService {
  private io: SocketIOServer | null = null;
  private subscribers: Map<string, (event: BaseEvent) => void> = new Map();
  private redisService: any = null; // RedisService global

  constructor() {
    // La inicialización se hace cuando se configura RedisService
  }

  /**
   * Helper seguro para publicar a Redis
   */
  private async safeRedisPublish(channel: string, message: string): Promise<void> {
    try {
      if (this.redisService && this.redisService.isReady) {
        await this.redisService.publish(channel, message);
        return;
      }
      
      // Fallback: intentar usar redisPublisher directamente
      const { redisPublisher } = await import('../models/redis');
      if (redisPublisher && redisPublisher.isReady) {
        await redisPublisher.publish(channel, message);
      } else {
        console.warn(`⚠️ Redis no disponible para canal: ${channel}`);
      }
    } catch (error) {
      console.error(`❌ Error publicando a Redis canal ${channel}:`, error);
    }
  }

  /**
   * Configurar Socket.IO server
   */
  setSocketIO(io: SocketIOServer): void {
    this.io = io;
  }

  /**
   * Configurar RedisService global
   */
  setRedisService(redisService: any): void {
    this.redisService = redisService;
    console.log('✅ EventService configurado con RedisService global');
  }

  /**
   * Inicializar subscriptores Redis según RF011
   */
  private async initializeSubscribers(): Promise<void> {
    try {
      if (!this.redisService) {
        console.warn('⚠️ RedisService no configurado, saltando inicialización de subscriptores');
        return;
      }

      // Subscribirse a eventos de IA desde Python usando los canales correctos
      await this.redisService.subscribe('cloudmusic_dte:ai_responses', () => {});
      await this.redisService.subscribe('cloudmusic_dte:analysis_results', () => {});
      await this.redisService.subscribe('cloudmusic_dte:anomaly_detected', () => {});
      await this.redisService.subscribe('cloudmusic_dte:prediction_ready', () => {});

      this.redisService.on('message', (channel: string, message: string) => {
        this.handleRedisMessage(channel, message);
      });

      console.log('✅ Subscriptores Redis inicializados');
    } catch (error) {
      console.error('❌ Error inicializando subscriptores Redis:', error);
    }
  }

  /**
   * Manejar mensajes Redis de Python AI (RF011)
   */
  private handleRedisMessage(channel: string, message: string): void {
    try {
      console.log(`🔔 REDIS MESSAGE RECIBIDO:`);
      console.log(`   Canal: ${channel}`);
      console.log(`   Mensaje: ${message}`);
      
      const event = JSON.parse(message) as BaseEvent;

      // Distribuir via WebSocket según compañía
      if (this.io && event.companyId) {
        console.log(`📡 Enviando via WebSocket a company:${event.companyId}`);
        this.io.to(`company:${event.companyId}`).emit(event.type, event);
      }

      // Ejecutar callbacks registrados
      const callback = this.subscribers.get(channel);
      if (callback) {
        console.log(`🔄 Ejecutando callback para canal: ${channel}`);
        callback(event);
      }

      // Logging para debugging
      console.log(`📨 Evento Redis recibido: ${channel} -> ${event.type}`);

    } catch (error) {
      console.error('Error procesando mensaje Redis:', error);
    }
  }

  /**
   * Publicar evento de documento (RF010)
   */
  async publishDocumentEvent(event: DocumentEvent): Promise<void> {
    try {
      const eventData = {
        ...event,
        id: this.generateEventId(),
        timestamp: new Date()
      };

      // 1. Publicar a Redis para Python AI (RF011)
      await this.safeRedisPublish('node:document_event', JSON.stringify(eventData));

      // 2. Enviar via WebSocket a frontend (RF010)
      if (this.io) {
        // Notificar a la empresa
        this.io.to(`company:${event.companyId}`).emit(event.type, eventData);
        
        // Notificar al usuario específico si está definido
        if (event.userId) {
          this.io.to(`user:${event.userId}`).emit(event.type, eventData);
        }
      }

      // 3. Almacenar en MongoDB via Redis (para backend Python)
      await this.publishToMongoDB('websocket_events', eventData);

      console.log(`✅ Evento documento publicado: ${event.type} - ${event.documentId}`);

    } catch (error) {
      console.error('Error publicando evento de documento:', error);
      throw error;
    }
  }

  /**
   * Solicitar análisis IA (RF011 -> RF012)
   */
  async requestAIAnalysis(event: AIAnalysisEvent): Promise<void> {
    try {
      const eventData = {
        ...event,
        id: this.generateEventId(),
        timestamp: new Date()
      };

      // Enviar solicitud a Python AI via Redis usando el canal correcto
      await this.safeRedisPublish('cloudmusic_dte:analysis_requests', JSON.stringify(eventData));

      console.log(`🤖 Análisis IA solicitado: ${event.analysisType} - ${event.companyId}`);

    } catch (error) {
      console.error('Error solicitando análisis IA:', error);
      throw error;
    }
  }

  /**
   * Publicar mensaje de chat IA (RF012)
   */
  async publishChatMessage(event: ChatEvent): Promise<void> {
    try {
      const eventData = {
        ...event,
        id: this.generateEventId(),
        timestamp: new Date()
      };

      if (event.messageType === 'user') {
        // Enviar mensaje de usuario a IA Python usando el canal correcto
        console.log(`🚀 PUBLICANDO A REDIS: cloudmusic_dte:chat_requests`);
        console.log(`📤 Datos enviados:`, JSON.stringify(eventData, null, 2));
        console.log(`🔍 Redis service status: ${this.redisService ? 'available' : 'unavailable'}`);
        
        // Usar RedisService global
        if (this.redisService) {
          await this.redisService.publish('cloudmusic_dte:chat_requests', JSON.stringify(eventData));
          console.log(`✅ Mensaje publicado exitosamente a Redis via RedisService`);
        } else {
          console.log(`❌ RedisService no disponible - usando método seguro`);
          // El método safeRedisPublish ya maneja el fallback
          await this.safeRedisPublish('cloudmusic_dte:chat_requests', JSON.stringify(eventData));
          console.log(`✅ Mensaje publicado via método seguro (fallback)`);
        }
      } else {
        // Distribuir respuesta IA via WebSocket
        if (this.io) {
          this.io.to(`company:${event.companyId}`).emit(event.type, eventData);
        }
      }

      // Almacenar en MongoDB
      await this.publishToMongoDB('chat_sessions', eventData);

      console.log(`💬 Mensaje chat: ${event.messageType} - ${event.sessionId}`);

    } catch (error) {
      console.error('Error publicando mensaje chat:', error);
      throw error;
    }
  }

  /**
   * Publicar alerta de folios (RF008)
   */
  async publishFolioAlert(event: {
    type: string;
    companyId: string;
    userId?: string;
    message: string;
    severity: 'info' | 'warning' | 'error' | 'success';
    data?: Record<string, unknown>;
  }): Promise<void> {
    try {
      const eventData = {
        ...event,
        id: this.generateEventId(),
        timestamp: new Date(),
        type: EventType.FOLIO_ALERT
      };

      // Notificar via WebSocket
      if (this.io) {
        this.io.to(`company:${event.companyId}`).emit(EventType.FOLIO_ALERT, eventData);
      }

      // Almacenar alerta
      await this.publishToMongoDB('websocket_events', eventData);

      console.log(`⚠️ Alerta folio: ${event.severity} - ${event.message}`);

    } catch (error) {
      console.error('Error publicando alerta folio:', error);
      throw error;
    }
  }

  /**
   * Publicar evento genérico del sistema
   */
  async publishSystemEvent(
    type: EventType,
    companyId: string,
    data: Record<string, unknown>,
    userId?: string
  ): Promise<void> {
    try {
      const eventData: BaseEvent = {
        id: this.generateEventId(),
        type,
        timestamp: new Date(),
        companyId,
        userId,
        metadata: data
      };

      // Distribuir via WebSocket
      if (this.io) {
        this.io.to(`company:${companyId}`).emit(type, eventData);
        
        if (userId) {
          this.io.to(`user:${userId}`).emit(type, eventData);
        }
      }

      // Publicar a Redis para análisis
      await this.safeRedisPublish('node:system_event', JSON.stringify(eventData));

      console.log(`📡 Evento sistema: ${type} - ${companyId}`);

    } catch (error) {
      console.error('Error publicando evento sistema:', error);
      throw error;
    }
  }

  /**
   * Subscribirse a eventos específicos
   */
  subscribe(channel: string, callback: (event: BaseEvent) => void): void {
    this.subscribers.set(channel, callback);
  }

  /**
   * Desuscribirse de eventos
   */
  unsubscribe(channel: string): void {
    this.subscribers.delete(channel);
  }

  /**
   * Publicar datos a MongoDB via Redis (para Python)
   */
  private async publishToMongoDB(collection: string, data: Record<string, unknown>): Promise<void> {
    try {
      const mongoEvent = {
        collection,
        operation: 'insert',
        data,
        timestamp: new Date()
      };

      await this.safeRedisPublish('mongo:insert', JSON.stringify(mongoEvent));

    } catch (error) {
      console.error('Error publicando a MongoDB:', error);
    }
  }

  /**
   * Generar ID único para eventos
   */
  private generateEventId(): string {
    return `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Obtener estadísticas de eventos
   */
  async getEventStats(): Promise<{
    redisConnections: boolean;
    socketConnections: number;
    subscribedChannels: number;
    eventsPublished: number;
  }> {
    try {
      const socketConnections = this.io ? this.io.engine.clientsCount : 0;
      const subscribedChannels = this.subscribers.size;

      return {
        redisConnections: this.redisService ? this.redisService.isReady : false,
        socketConnections,
        subscribedChannels,
        eventsPublished: 0 // Se podría implementar contador
      };

    } catch (error) {
      console.error('Error obteniendo estadísticas:', error);
      return {
        redisConnections: false,
        socketConnections: 0,
        subscribedChannels: 0,
        eventsPublished: 0
      };
    }
  }

  /**
   * Limpiar recursos
   */
  async cleanup(): Promise<void> {
    try {
      if (this.redisService) {
        await this.redisService.unsubscribe();
      }
      this.subscribers.clear();
      console.log('🧹 EventService limpiado');
    } catch (error) {
      console.error('Error limpiando EventService:', error);
    }
  }

  /**
   * Verificar salud del sistema de eventos (RF010: latencia ≤100ms)
   */
  async healthCheck(): Promise<{
    isHealthy: boolean;
    latency: number;
    redisStatus: 'connected' | 'disconnected';
    socketStatus: 'active' | 'inactive';
    errors: string[];
  }> {
    const startTime = Date.now();
    const errors: string[] = [];

    try {
      // Test Redis ping seguro
      let redisStatus: 'connected' | 'disconnected' = 'disconnected';
      
      if (this.redisService && this.redisService.isReady) {
        await this.redisService.ping();
        redisStatus = 'connected';
      } else {
        try {
          const { redisPublisher } = await import('../models/redis');
          if (redisPublisher && redisPublisher.isReady) {
            await redisPublisher.ping();
            redisStatus = 'connected';
          }
        } catch (e) {
          errors.push('Redis no disponible');
        }
      }
      
      const latency = Date.now() - startTime;
      const socketStatus = this.io ? 'active' : 'inactive';
      const isHealthy = latency <= 100 && redisStatus === 'connected'; // RF010: ≤100ms

      if (latency > 100) {
        errors.push(`Latencia alta: ${latency}ms > 100ms`);
      }

      if (redisStatus === 'disconnected') {
        errors.push('Redis desconectado');
      }

      return {
        isHealthy,
        latency,
        redisStatus,
        socketStatus,
        errors
      };

    } catch (error) {
      errors.push(`Error en health check: ${error instanceof Error ? error.message : 'Error desconocido'}`);
      
      return {
        isHealthy: false,
        latency: Date.now() - startTime,
        redisStatus: 'disconnected',
        socketStatus: this.io ? 'active' : 'inactive',
        errors
      };
    }
  }
}

// Singleton instance
export const eventService = new EventService();
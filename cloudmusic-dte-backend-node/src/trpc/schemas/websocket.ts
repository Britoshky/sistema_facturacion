/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🔌 WEBSOCKET & EVENT SCHEMAS
 * ════════════════════════════════════════════════════════════════════════════════
 */

import { z } from 'zod';

// ==========================================
// 🔌 WEBSOCKET SCHEMAS
// ==========================================

/**
 * Schema para eventos WebSocket salientes (server -> client)
 */
export const websocketEventSchema = z.object({
  type: z.enum([
    // Sistema
    'connection_established',
    'system_notification',
    'error_notification',
    
    // Documentos DTE
    'document_created',
    'document_updated', 
    'document_status_changed',
    'sii_response_received',
    
    // IA/Chat
    'ai_message_received',
    'ai_analysis_complete',
    'ai_processing_started',
    
    // Estado sistema
    'ollama_status_changed',
    'system_health_update',
    
    // Usuarios/Sesiones
    'user_authenticated',
    'session_expired',
    'user_activity'
  ]),
  payload: z.union([
    z.string(),
    z.number(), 
    z.boolean(),
    z.object({}).passthrough(), // Para objetos genéricos
    z.array(z.unknown())
  ]),
  timestamp: z.date().default(() => new Date()),
  userId: z.string().optional(),
  sessionId: z.string().optional(),
  companyId: z.string().optional()
});

/**
 * Schema para eventos WebSocket entrantes (client -> server)
 */
export const clientEventSchema = z.object({
  type: z.enum([
    'ping',
    'subscribe_to_updates',
    'unsubscribe_from_updates',
    'request_status',
    'authenticate'
  ]),
  payload: z.union([
    z.string(),
    z.number(),
    z.boolean(), 
    z.object({}).passthrough(),
    z.array(z.unknown())
  ]).optional()
});

/**
 * Enum EventType para compatibilidad con código existente
 */
export enum EventType {
  // Eventos de documentos DTE
  DOCUMENT_CREATED = 'document:created',
  DOCUMENT_SIGNED = 'document:signed',
  DOCUMENT_SENT_TO_SII = 'document:sent_to_sii',
  DOCUMENT_STATUS_UPDATED = 'document:status_updated',
  
  // Alertas del sistema
  FOLIO_ALERT = 'folio:alert',
  CERTIFICATE_EXPIRING = 'certificate:expiring',
  SYSTEM_ALERT = 'system:alert',
  
  // Eventos IA
  AI_ANALYSIS_REQUEST = 'ai:analysis_request',
  AI_ANALYSIS_RESULT = 'ai:analysis_result',
  AI_CHAT_MESSAGE = 'ai:chat_message',
  AI_CHAT_RESPONSE = 'ai:chat_response'
}

// ==========================================
// 🔌 EVENT SYSTEM INTERFACES
// ==========================================

/**
 * Interface para eventos del sistema
 */
export interface SystemEvent {
  id: string;
  type: string;
  source: 'api' | 'websocket' | 'system' | 'ai' | 'sii';
  data: Record<string, unknown> | string | number | boolean | null;
  userId?: string;
  companyId?: string;
  timestamp: Date;
  severity: 'info' | 'warning' | 'error' | 'success';
}

/**
 * Interface para notificaciones
 */
export interface NotificationEvent {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message: string;
  userId?: string;
  companyId?: string;
  data?: Record<string, unknown> | string | number | boolean;
  persistent: boolean;
  timestamp: Date;
  expiresAt?: Date;
}

/**
 * Interface para cliente WebSocket conectado
 */
export interface ConnectedClient {
  id: string;
  userId?: string;
  companyId?: string;
  connectionTime: Date;
  lastActivity: Date;
  subscriptions: string[];
  metadata?: {
    userAgent?: string;
    ipAddress?: string;
    location?: string;
  };
}

/**
 * Interface para métricas en tiempo real
 */
export interface RealtimeMetrics {
  connectedUsers: number;
  activeDocuments: number;
  aiConversations: number;
  systemHealth: {
    cpu: number;
    memory: number;
    database: boolean;
    redis: boolean;
    ollama: boolean;
  };
  timestamp: Date;
}

/**
 * Interface para eventos base del sistema
 */
export interface BaseEvent {
  id: string;
  type: EventType;
  timestamp: Date;
  companyId: string;
  userId?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Interface para eventos de documentos DTE
 */
export interface DocumentEvent extends BaseEvent {
  documentId: string;
  documentType: number;
  folioNumber: number;
  amount: number;
  clientId?: string;
  status?: string;
}

/**
 * Interface para eventos de análisis IA
 */
export interface AIAnalysisEvent extends BaseEvent {
  documentId?: string;
  analysisType: 'anomaly_detection' | 'cash_flow_prediction' | 'tax_optimization';
  inputData: Record<string, unknown>;
  priority: 'low' | 'medium' | 'high';
}

/**
 * Interface para eventos de resultado IA
 */
export interface AIResultEvent extends BaseEvent {
  requestId: string;
  analysisType: string;
  result: Record<string, unknown>;
  confidence: number;
  processingTime: number;
}

/**
 * Interface para eventos de chat
 */
export interface ChatEvent extends BaseEvent {
  sessionId: string;
  message: string;
  messageType: 'user' | 'assistant';
  context?: Record<string, unknown>;
}

/**
 * Interfaces de compatibilidad para WebSocket
 */
export interface AuthenticatedSocket {
  id: string;
  userId?: string;
  userEmail?: string;
  companyId?: string;
  role?: string;
  join?: (room: string) => void;
  on?: (event: string, listener: Function) => void;
  handshake?: {
    headers: Record<string, string>;
    query: Record<string, string>;
    auth?: Record<string, unknown>;
  };
}

export interface ExtendedAuthenticatedSocket {
  id?: string;
  userId?: string;
  companyId?: string;
  userEmail?: string;
  join?: (room: string) => void;
  on?: (event: string, listener: Function) => void;
  handshake?: {
    headers: Record<string, string>;
    query: Record<string, string>;
    auth?: Record<string, unknown>;
  };
}

export interface LocalAuthenticatedSocket {
  userId?: string;
  companyId?: string;
  userEmail?: string;
}

/**
 * Interfaces para datos de eventos WebSocket
 */
export interface DocumentCreateData {
  clientId?: string;
  documentId: string;
  type: string;
  folio: string;
  documentType?: number;
  data?: Record<string, unknown>;
  items?: Array<{
    productId: string;
    quantity: number;
    price: number;
  }>;
}

export interface DocumentStatusData {
  documentId: string;
  status?: string;
  newStatus?: string;
  timestamp?: Date;
  observations?: string;
}

export interface FolioWarningData {
  companyId: string;
  documentType: string;
  remaining: number;
  threshold: number;
}
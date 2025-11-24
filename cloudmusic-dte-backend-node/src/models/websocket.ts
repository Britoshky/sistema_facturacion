/**
 * Tipos y esquemas para WebSocket - CloudMusic DTE
 * Comunicación tiempo real entre frontend y backend
 */

import { z } from 'zod';

// === EVENTOS WEBSOCKET ===

export const WebSocketEventSchema = z.object({
  _id: z.string().optional(),
  event_id: z.string(),
  event_type: z.enum([
    'user_login',
    'user_logout', 
    'document_created',
    'document_signed', 
    'sii_submission',
    'ai_analysis_completed',
    'system_notification',
    'company_user_assigned',
    'company_user_updated',
    'company_user_removed'
  ]),
  timestamp: z.string(),
  user_id: z.string().nullable(),
  company_id: z.string().nullable(),
  session_id: z.string(),
  connection_id: z.string(),
  data: z.record(z.string(), z.any()),
  metadata: z.record(z.string(), z.any()).optional(),
  broadcast_to: z.array(z.string()).optional(),
  processed: z.boolean(),
  created_at: z.string()
});

export const WebSocketMessageSchema = z.object({
  type: z.string(),
  payload: z.record(z.string(), z.any()),
  timestamp: z.date().default(() => new Date()),
  user_id: z.string().optional(),
  company_id: z.string().optional()
});

// === TIPOS DE NOTIFICACIONES ===

export const DocumentNotificationSchema = z.object({
  document_id: z.string(),
  document_type: z.number(),
  folio_number: z.number(),
  client_rut: z.string().optional(),
  total_amount: z.number().optional(),
  status: z.string(),
  action: z.string()
});

export const AIAnalysisNotificationSchema = z.object({
  _id: z.string(),
  document_id: z.string(),
  company_id: z.string(),
  analysis_type: z.string(),
  ai_model: z.string(),
  compliance_score: z.number(),
  risk_level: z.enum(['low', 'medium', 'high']),
  processing_time_ms: z.number(),
  confidence_level: z.number()
});

export const SIIResponseNotificationSchema = z.object({
  track_id: z.string(),
  document_id: z.string(),
  company_id: z.string(),
  current_status: z.enum(['ENVIADO', 'RECIBIDO', 'ACEPTADO', 'RECHAZADO']),
  submission_timestamp: z.string(),
  sii_responses: z.array(z.any())
});

export const ChatNotificationSchema = z.object({
  _id: z.string(),
  session_id: z.string(),
  user_id: z.string(),
  company_id: z.string(),
  messages: z.array(z.any()),
  is_active: z.boolean(),
  session_metadata: z.record(z.string(), z.any())
});

export const SystemNotificationSchema = z.object({
  notification_type: z.enum([
    'certificate_expiry_warning',
    'folio_limit_warning', 
    'system_maintenance',
    'backup_completed',
    'error_alert'
  ]),
  message: z.string(),
  urgency_level: z.enum(['low', 'medium', 'high', 'critical']),
  action_required: z.boolean(),
  deadline: z.date().optional(),
  affected_companies: z.array(z.string()).optional()
});

export const CompanyUserNotificationSchema = z.object({
  assignment_id: z.string(),
  user_id: z.string(),
  company_id: z.string(),
  action: z.enum(['assigned', 'updated', 'removed']),
  role: z.enum(['owner', 'admin', 'contador', 'user', 'viewer']).optional(),
  user_name: z.string(),
  company_name: z.string(),
  performed_by: z.string() // ID del usuario que realizó la acción
});

// === SALAS WEBSOCKET ===

export const WebSocketRoomSchema = z.object({
  user_id: z.string(),
  company_id: z.string(),
  rooms: z.array(z.string())
});

// === TIPOS EXPORTADOS ===

export type WebSocketEvent = z.infer<typeof WebSocketEventSchema>;
export type WebSocketMessage = z.infer<typeof WebSocketMessageSchema>;
export type DocumentNotification = z.infer<typeof DocumentNotificationSchema>;
export type AIAnalysisNotification = z.infer<typeof AIAnalysisNotificationSchema>;
export type SIIResponseNotification = z.infer<typeof SIIResponseNotificationSchema>;
export type ChatNotification = z.infer<typeof ChatNotificationSchema>;
export type SystemNotification = z.infer<typeof SystemNotificationSchema>;
export type CompanyUserNotification = z.infer<typeof CompanyUserNotificationSchema>;
export type WebSocketRoom = z.infer<typeof WebSocketRoomSchema>;

// === CONSTANTES ===

export const WEBSOCKET_ROOMS = {
  // Salas por usuario
  USER: (userId: string) => `user:${userId}`,
  
  // Salas por empresa
  COMPANY: (companyId: string) => `company:${companyId}`,
  
  // Salas por módulo
  DOCUMENTS: (companyId: string) => `documents:${companyId}`,
  AI_CHAT: (companyId: string) => `ai_chat:${companyId}`,
  SII_MONITOR: (companyId: string) => `sii:${companyId}`,
  ADMIN_PANEL: (companyId: string) => `admin:${companyId}`,
  
  // Salas globales
  SYSTEM_NOTIFICATIONS: 'system:notifications',
  ADMIN_GLOBAL: 'admin:global',
  REAL_TIME_STATS: 'stats:realtime'
} as const;

export const WEBSOCKET_EVENTS = {
  // Eventos de conexión
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  JOIN_ROOM: 'join_room',
  LEAVE_ROOM: 'leave_room',
  
  // Eventos de documentos
  DOCUMENT_CREATED: 'document_created',
  DOCUMENT_UPDATED: 'document_updated', 
  DOCUMENT_SIGNED: 'document_signed',
  DOCUMENT_SENT: 'document_sent',
  
  // Eventos SII
  SII_RESPONSE: 'sii_response',
  SII_ERROR: 'sii_error',
  
  // Eventos IA
  AI_ANALYSIS_STARTED: 'ai_analysis_started',
  AI_ANALYSIS_COMPLETED: 'ai_analysis_completed',
  AI_CHAT_MESSAGE: 'ai_chat_message',
  
  // Eventos del sistema
  SYSTEM_NOTIFICATION: 'system_notification',
  ERROR_NOTIFICATION: 'error_notification',
  
  // Eventos de usuario
  USER_LOGIN: 'user_login',
  USER_LOGOUT: 'user_logout',
  
  // Eventos de gestión de empresas
  COMPANY_USER_ASSIGNED: 'company_user_assigned',
  COMPANY_USER_UPDATED: 'company_user_updated',
  COMPANY_USER_REMOVED: 'company_user_removed'
} as const;
/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🤖 AI SYSTEM SCHEMAS - REDIS PUB/SUB + WEBSOCKETS ARCHITECTURE
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * ARQUITECTURA HÍBRIDA según informe:
 * Frontend ↔ Node.js (tRPC) ↔ Redis Pub/Sub ↔ Python IA (FastAPI + Ollama + MongoDB)
 *                    ↕ WebSockets (notificaciones tiempo real)
 * 
 * BASES DE DATOS:
 * - PostgreSQL: Datos estructurados DTE (users, companies, documents, etc.)
 * - MongoDB: Chat sessions, AI analysis, WebSocket events, SII responses, audit trail
 * 
 * FLUJO IA:
 * 1. Frontend envía solicitud tRPC a Node.js
 * 2. Node.js publica evento en Redis Pub/Sub  
 * 3. Python IA procesa con Ollama y almacena en MongoDB
 * 4. Python IA responde via Redis 
 * 5. Node.js notifica Frontend via WebSocket
 */

import { z } from 'zod';

// ==========================================
// 🤖 REDIS PUB/SUB COMMUNICATION SCHEMAS  
// ==========================================

/**
 * Schema para enviar solicitud de chat a Python IA via Redis
 */
export const chatRequestSchema = z.object({
  sessionId: z.string().min(1, 'Session ID requerido'), // Formato: session_{timestamp}_{random}
  userId: z.string().uuid('User ID inválido'),
  companyId: z.string().uuid('Company ID inválido'),
  message: z.string().min(1, 'Mensaje es requerido').max(4000, 'Mensaje muy largo'),
  contextType: z.enum(['general', 'technical', 'accounting', 'legal']).default('general'),
  contextData: z.object({
    documentId: z.string().optional(),
    documentType: z.number().optional(),
    relatedData: z.record(z.string(), z.unknown()).optional()
  }).optional(),
  priority: z.enum(['low', 'normal', 'high']).default('normal')
});

/**
 * Schema para crear nueva sesión de chat (genera ID manual)
 */
export const createChatSessionSchema = z.object({
  userId: z.string().uuid('User ID inválido'),
  companyId: z.string().uuid('Company ID inválido'),
  title: z.string().min(1).max(200).optional(),
  contextType: z.enum(['general', 'technical', 'accounting', 'legal']).default('general'),
  initialMessage: z.string().min(1).max(4000).optional()
});

/**
 * Schema para solicitar análisis de documento a Python IA
 */
export const documentAnalysisRequestSchema = z.object({
  documentId: z.string().uuid('Document ID inválido'),
  userId: z.string().uuid('User ID inválido'),
  companyId: z.string().uuid('Company ID inválido'),
  analysisType: z.enum([
    'fraud_detection',
    'compliance_check', 
    'data_extraction',
    'quality_analysis'
  ]),
  documentData: z.record(z.string(), z.unknown()), // XML parseado o datos del DTE
  priority: z.enum(['low', 'normal', 'high', 'urgent']).default('normal'),
  metadata: z.object({
    documentType: z.number().optional(), // Tipo DTE (33, 34, etc.)
    folioNumber: z.string().optional(),
    emissionDate: z.string().optional(),
    additionalContext: z.record(z.string(), z.unknown()).optional()
  }).optional()
});

/**
 * Schema para verificar estado Ollama via Redis
 */
export const ollamaStatusRequestSchema = z.object({
  requestId: z.string().optional(), // Si no se proporciona, se genera automáticamente
  includeModels: z.boolean().default(true),
  includeSystemInfo: z.boolean().default(false),
  timeout: z.number().min(1000).max(30000).default(5000) // ms
});

// ==========================================
// 📡 WEBSOCKET RESPONSE SCHEMAS
// ==========================================

/**
 * Schema para respuestas de chat desde Python IA (via WebSocket)
 */
export const chatResponseSchema = z.object({
  sessionId: z.string(),
  messageId: z.string(), // ID generado por MongoDB
  response: z.string(),
  contextUsed: z.array(z.string()).optional(),
  confidence: z.number().min(0).max(1).optional(),
  processingTime: z.number().optional(), // ms
  timestamp: z.string(), // ISO string
  status: z.enum(['success', 'error', 'timeout'])
});

/**
 * Schema para respuestas de análisis desde Python IA (via WebSocket)
 */
export const analysisResponseSchema = z.object({
  requestId: z.string(),
  analysisId: z.string(), // ID generado por MongoDB  
  documentId: z.string(),
  status: z.enum(['completed', 'failed', 'error']),
  results: z.object({
    riskLevel: z.enum(['low', 'medium', 'high', 'critical']).optional(),
    anomalies: z.array(z.string()).optional(),
    recommendations: z.array(z.string()).optional(),
    confidence: z.number().min(0).max(1).optional(),
    analysisData: z.record(z.string(), z.unknown()).optional(),
    summary: z.object({
      errorCount: z.number(),
      warningCount: z.number(),
      suggestionCount: z.number(),
      score: z.number().min(0).max(100) // 0-100
    }).optional()
  }).optional(),
  errorMessage: z.string().optional(),
  processingTime: z.number().optional(), // ms
  timestamp: z.string()
});

// ==========================================
// 📋 QUERY SCHEMAS (para Frontend)
// ==========================================

/**
 * Schema obtener historial de chat (almacenado en MongoDB)
 */
export const getChatHistorySchema = z.object({
  userId: z.string().uuid(),
  companyId: z.string().uuid().optional(),
  sessionId: z.string().optional(), // Formato: session_{timestamp}_{random}
  limit: z.number().min(1).max(50).default(10),
  skip: z.number().min(0).default(0) // MongoDB usa skip, no offset
});

/**
 * Schema obtener estado de análisis (almacenado en MongoDB)
 */
export const getAnalysisStatusSchema = z.object({
  userId: z.string().uuid(),
  companyId: z.string().uuid().optional(),
  documentId: z.string().uuid().optional(),
  analysisId: z.string().optional(), // ID MongoDB
  riskLevel: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  analysisType: z.enum(['fraud_detection', 'compliance_check', 'data_extraction', 'quality_analysis']).optional(),
  limit: z.number().min(1).max(100).default(20),
  skip: z.number().min(0).default(0)
});

/**
 * Schema para consultar eventos WebSocket (almacenados en MongoDB)
 */
export const getWebSocketEventsSchema = z.object({
  userId: z.string().uuid(),
  companyId: z.string().uuid().optional(),
  eventType: z.enum(['ai_chat_response', 'analysis_complete', 'analysis_progress', 'system_notification', 'error_notification']).optional(),
  sessionId: z.string().optional(),
  fromDate: z.string().optional(), // ISO date
  toDate: z.string().optional(),   // ISO date
  limit: z.number().min(1).max(100).default(50),
  skip: z.number().min(0).default(0)
});

// ==========================================
// 🔧 REDIS EVENT SCHEMAS
// ==========================================

/**
 * Schema para eventos Redis Pub/Sub hacia Python IA
 */
export const redisEventSchema = z.object({
  eventType: z.enum(['chat_request', 'document_analysis', 'ollama_status_check']),
  eventId: z.string(), // Generado automáticamente
  userId: z.string().uuid(),
  companyId: z.string().uuid(),
  payload: z.record(z.string(), z.unknown()),
  timestamp: z.string(), // ISO
  channel: z.string(), // Canal Redis específico
  priority: z.enum(['low', 'normal', 'high', 'urgent']).default('normal')
});

/**
 * Schema para respuestas Redis desde Python IA
 */
export const redisResponseSchema = z.object({
  eventId: z.string(), // Mismo ID del request
  eventType: z.enum(['chat_response', 'analysis_complete', 'ollama_status', 'error']),
  status: z.enum(['success', 'error', 'timeout', 'processing']),
  data: z.record(z.string(), z.unknown()),
  errorMessage: z.string().optional(),
  processingTime: z.number().optional(),
  timestamp: z.string()
});

// ==========================================
// 📱 WEBSOCKET EVENT SCHEMAS  
// ==========================================

/**
 * Schema para eventos WebSocket al Frontend
 */
export const websocketEventSchema = z.object({
  type: z.enum([
    'ai_chat_response',
    'analysis_complete', 
    'analysis_progress',
    'system_notification',
    'error_notification'
  ]),
  eventId: z.string(),
  userId: z.string(),
  data: z.record(z.string(), z.unknown()),
  timestamp: z.string(),
  roomId: z.string().optional() // Para room management por empresa
});

// ==========================================
// 🤖 TYPE EXPORTS (Inferidos de schemas)
// ==========================================

export type ChatRequest = z.infer<typeof chatRequestSchema>;
export type CreateChatSession = z.infer<typeof createChatSessionSchema>;
export type DocumentAnalysisRequest = z.infer<typeof documentAnalysisRequestSchema>;
export type OllamaStatusRequest = z.infer<typeof ollamaStatusRequestSchema>;
export type ChatResponse = z.infer<typeof chatResponseSchema>;
export type AnalysisResponse = z.infer<typeof analysisResponseSchema>;
export type RedisEvent = z.infer<typeof redisEventSchema>;
export type RedisResponse = z.infer<typeof redisResponseSchema>;
export type WebSocketEvent = z.infer<typeof websocketEventSchema>;

// ==========================================
// 📄 ENUMS & CONSTANTS
// ==========================================

/**
 * Canales Redis para comunicación con Python IA
 */
export const REDIS_CHANNELS = {
  // Hacia Python IA
  AI_REQUESTS: 'cloudmusic_dte:ai_requests',
  CHAT_REQUESTS: 'cloudmusic_dte:chat_requests', 
  ANALYSIS_REQUESTS: 'cloudmusic_dte:analysis_requests',
  STATUS_REQUESTS: 'cloudmusic_dte:status_requests',
  
  // Desde Python IA  
  AI_RESPONSES: 'cloudmusic_dte:ai_responses',
  CHAT_RESPONSES: 'cloudmusic_dte:chat_responses',
  ANALYSIS_RESPONSES: 'cloudmusic_dte:analysis_responses',
  STATUS_RESPONSES: 'cloudmusic_dte:status_responses',
  
  // WebSocket events
  WEBSOCKET_EVENTS: 'cloudmusic_dte:websocket'
} as const;

/**
 * Tipos de análisis soportados por Python IA
 */
export const ANALYSIS_TYPES = {
  FRAUD_DETECTION: 'fraud_detection',
  COMPLIANCE_CHECK: 'compliance_check', 
  DATA_EXTRACTION: 'data_extraction',
  QUALITY_ANALYSIS: 'quality_analysis'
} as const;

/**
 * Tipos de contexto para chat IA
 */  
export const CONTEXT_TYPES = {
  GENERAL: 'general',
  TECHNICAL: 'technical', 
  ACCOUNTING: 'accounting',
  LEGAL: 'legal'
} as const;

// ==========================================
// 🔄 COMPATIBILITY EXPORTS
// ==========================================

// Aliases para compatibilidad con schemas existentes
export const sendMessageSchema = chatRequestSchema;
export const createSessionSchema = createChatSessionSchema;
export const requestAnalysisSchema = documentAnalysisRequestSchema;
export const getChatSessionsSchema = getChatHistorySchema;
export const ollamaStatusSchema = ollamaStatusRequestSchema;
export const getSessionMessagesSchema = getChatHistorySchema;
export const chatHistorySchema = getChatHistorySchema;
export const analysisFiltersSchema = getAnalysisStatusSchema;
export const analyzeDocumentSchema = documentAnalysisRequestSchema;

// Type aliases para compatibilidad
export type ChatMessage = any;
export type ChatSession = any;
export type OllamaStatus = any;
export type AIAnalysisResult = any;
export type InternalChatSession = any;
export type InternalAnalysisRequest = any;
export type AnalysisRequest = DocumentAnalysisRequest;
export type AIAnalysisType = keyof typeof ANALYSIS_TYPES;
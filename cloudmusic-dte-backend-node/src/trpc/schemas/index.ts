/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 📦 SCHEMAS INDEX - EXPORTACIONES CENTRALES
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Punto central de exportación para todos los schemas modulares.
 * Facilita las importaciones en routers y servicios.
 * 
 * Uso:
 * import { createUserSchema, loginSchema } from '../schemas';
 * import { createDocumentSchema } from '../schemas';
 * 
 */

// ==========================================
// 🔧 COMMON & UTILITIES
// ==========================================
export * from './common';

// ==========================================
// 👤 USER DOMAIN
// ==========================================
export * from './users';

// ==========================================
// 🏢 COMPANY DOMAIN
// ==========================================
export * from './companies';

// ==========================================
// 🏷️ PRODUCT DOMAIN
// ==========================================
export * from './products';

// ==========================================
// 👥 CLIENT DOMAIN
// ==========================================
export * from './clients';

// ==========================================
// 📄 DOCUMENT DTE DOMAIN
// ==========================================
export * from './documents';

// ==========================================
// 📁 FOLIOS & CAF DOMAIN (exports específicos para evitar conflictos)
// ==========================================
export {
  createFolioSchema,
  updateFolioSchema,
  getFolioByIdSchema,
  updateFolioWithIdSchema,
  deleteFolioSchema,
  getNextFolioAvailableSchema,
  getFolioStatsSchema
} from './folios';
export type {
  FolioAlert,
  CAFFile,
  CAFValidationResult,
  FolioStats
} from './folios';

// ==========================================
// 🔐 CERTIFICATES DOMAIN
// ==========================================
export * from './certificates';

// ==========================================
// 🔍 VALIDATION DOMAIN
// ==========================================
export * from './validation';

// ==========================================
// 🏛️ SII INTEGRATION DOMAIN
// ==========================================
export * from './sii';

// ==========================================
// 🤖 AI SYSTEM DOMAIN (selective exports to avoid conflicts)
// ==========================================
export { 
  sendMessageSchema,
  createSessionSchema,
  ollamaStatusSchema,
  requestAnalysisSchema,
  getChatSessionsSchema,
  getSessionMessagesSchema,
  getAnalysisStatusSchema,
  chatHistorySchema,
  analysisFiltersSchema
} from './ai';
export type {
  AIAnalysisType,
  ChatMessage,
  ChatSession,
  OllamaStatus,
  AIAnalysisResult,
  InternalChatSession,
  InternalAnalysisRequest,
  AnalysisRequest
} from './ai';

// ==========================================
// 🔌 WEBSOCKET & EVENTS DOMAIN
// ==========================================
export * from './websocket';

// ==========================================
// 🔄 RE-EXPORTS FOR COMPATIBILITY
// ==========================================

// Re-exportar enums principales para compatibilidad
export { DocumentType } from './validation';
export { EventType } from './websocket';

// ==========================================
// 📊 DOMAIN GROUPINGS (conveniencia)
// ==========================================

/**
 * Exportaciones agrupadas para conveniencia (lazy loading)
 */
export const UserSchemas = {
  create: () => import('./users').then(m => m.createUserSchema),
  update: () => import('./users').then(m => m.updateUserSchema),
  login: () => import('./users').then(m => m.loginSchema),
  list: () => import('./users').then(m => m.listUsersSchema),
  changePassword: () => import('./users').then(m => m.changePasswordSchema)
};

export const CompanySchemas = {
  create: () => import('./companies').then(m => m.createCompanySchema),
  update: () => import('./companies').then(m => m.updateCompanySchema),
  list: () => import('./companies').then(m => m.listCompaniesSchema)
};

export const ClientSchemas = {
  create: () => import('./clients').then(m => m.createClientSchema),
  update: () => import('./clients').then(m => m.updateClientSchema),
  list: () => import('./clients').then(m => m.listClientsSchema)
};

export const ProductSchemas = {
  create: () => import('./products').then(m => m.createProductSchema),
  update: () => import('./products').then(m => m.updateProductSchema),
  list: () => import('./products').then(m => m.listProductsSchema),
  updateStock: () => import('./products').then(m => m.updateStockSchema)
};

export const DocumentSchemas = {
  create: () => import('./documents').then(m => m.createDocumentSchema),
  list: () => import('./documents').then(m => m.listDocumentsSchema),
  validate: () => import('./documents').then(m => m.validateDocumentXMLSchema)
};

export const FolioSchemas = {
  create: () => import('./folios').then(m => m.createFolioSchema),
  update: () => import('./folios').then(m => m.updateFolioSchema),
  list: () => import('./folios').then(m => m.listFoliosSchema),
  importCAF: () => import('./folios').then(m => m.folioImportCAFSchema),
  getNext: () => import('./folios').then(m => m.getNextFolioSchema),
  consume: () => import('./folios').then(m => m.consumeFolioSchema)
};

export const CertificateSchemas = {
  create: () => import('./certificates').then(m => m.createCertificateSchema),
  update: () => import('./certificates').then(m => m.updateCertificateSchema),
  list: () => import('./certificates').then(m => m.listCertificatesSchema),
  validate: () => import('./certificates').then(m => m.validateCertificateSchema),
  sign: () => import('./certificates').then(m => m.signDocumentSchema),
  import: () => import('./certificates').then(m => m.importCertificateSchema)
};

export const ValidationSchemas = {
  validateXML: () => import('./validation').then(m => m.validateXMLSchema),
  batchValidate: () => import('./validation').then(m => m.batchValidateSchema),
  analyzeDocument: () => import('./validation').then(m => m.analyzeDocumentSchema),
  getHistory: () => import('./validation').then(m => m.getValidationHistorySchema)
};

export const SIISchemas = {
  config: () => import('./sii').then(m => m.siiConfigSchema),
  sendDTE: () => import('./sii').then(m => m.sendDTESchema),
  queryStatus: () => import('./sii').then(m => m.queryStatusSchema),
  acknowledgment: () => import('./sii').then(m => m.acknowledgmentSchema),
  validateRut: () => import('./sii').then(m => m.validateRutSchema),
  getHistory: () => import('./sii').then(m => m.getSIIHistorySchema)
};

export const AISchemas = {
  sendMessage: () => import('./ai').then(m => m.sendMessageSchema),
  createSession: () => import('./ai').then(m => m.createSessionSchema),
  analyzeDocument: () => import('./ai').then(m => m.analyzeDocumentSchema),
  ollamaStatus: () => import('./ai').then(m => m.ollamaStatusSchema),
  getSessions: () => import('./ai').then(m => m.getChatSessionsSchema),
  getMessages: () => import('./ai').then(m => m.getSessionMessagesSchema),
  getAnalysisStatus: () => import('./ai').then(m => m.getAnalysisStatusSchema)
};
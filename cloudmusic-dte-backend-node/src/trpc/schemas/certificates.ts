/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🔐 CERTIFICATES & DIGITAL SIGNATURE SCHEMAS
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Gestión de certificados digitales para firma electrónica
 * - Certificados RSA-2048+SHA-256 según normativa SII
 * - Validación y verificación de certificados
 * - Configuración de firma digital
 * - Integración con proveedores chilenos (E-Cert, Accept, etc.)
 */

import { z } from 'zod';

// ==========================================
// 🔏 CERTIFICATE ENUMS
// ==========================================

/**
 * Proveedores de certificados soportados en Chile
 */
export enum CertificateProvider {
  E_CERT = 'e-cert',          // E-Cert (más común en Chile)
  ACCEPT = 'accept',          // Accept (AC del Estado)
  CAMERFIRMA = 'camerfirma'   // CamerFirma (internacional)
}

// ==========================================
// 🔐 CERTIFICATE VALIDATION SCHEMAS
// ==========================================

/**
 * Schema crear certificado
 */
export const createCertificateSchema = z.object({
  certificateName: z.string()
    .min(1, 'Nombre del certificado es requerido')
    .max(200, 'Nombre muy largo'),
  pfxFile: z.string().min(1, 'Archivo PFX es requerido'),
  passwordHash: z.string().min(1, 'Contraseña es requerida'),
  description: z.string().optional(),
  isDefault: z.boolean().default(false)
});

/**
 * Schema actualizar certificado
 */
export const updateCertificateSchema = z.object({
  certificateName: z.string().min(1).max(200).optional(),
  passwordHash: z.string().optional(),
  description: z.string().optional(),
  isActive: z.boolean().optional(),
  isDefault: z.boolean().optional()
});

/**
 * Schema validar certificado
 */
export const validateCertificateSchema = z.object({
  certificateId: z.string().uuid('ID certificado inválido'),
  checkExpiry: z.boolean().default(true),
  validateChain: z.boolean().default(true)
});

/**
 * Schema configuración de firma digital
 */
export const signatureConfigSchema = z.object({
  algorithm: z.enum(['RSA-SHA256', 'RSA-SHA1']).default('RSA-SHA256'),
  canonicalization: z.string().default('http://www.w3.org/TR/2001/REC-xml-c14n-20010315'),
  keySize: z.union([z.literal(2048), z.literal(4096)]).default(2048),
  includeCertificate: z.boolean().default(true),
  includeKeyInfo: z.boolean().default(true)
});

/**
 * Schema firmar documento XML
 */
export const signDocumentSchema = z.object({
  xmlContent: z.string().min(1, 'Contenido XML requerido'),
  certificateId: z.string().uuid('ID certificado inválido'),
  signatureConfig: signatureConfigSchema.optional()
});

/**
 * Schema listar certificados
 */
export const listCertificatesSchema = z.object({
  page: z.number().min(1).default(1),
  limit: z.number().min(1).max(50).default(10),
  isActive: z.boolean().optional(),
  provider: z.nativeEnum(CertificateProvider).optional(),
  expiringInDays: z.number().min(1).max(365).optional()
});

/**
 * Schema importar certificado desde archivo
 */
export const importCertificateSchema = z.object({
  pfxFileBase64: z.string().min(1, 'Archivo PFX requerido'),
  password: z.string().min(1, 'Contraseña requerida'),
  certificateName: z.string().min(1, 'Nombre requerido'),
  setAsDefault: z.boolean().default(false)
});

/**
 * Schema para obtener certificado por ID
 */
export const getCertificateByIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

/**
 * Schema para actualizar certificado con ID
 */
export const updateCertificateWithIdSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido'),
  data: updateCertificateSchema
});

/**
 * Schema para eliminar certificado
 */
export const deleteCertificateSchema = z.object({
  id: z.string().uuid('ID debe ser un UUID válido')
});

// ==========================================
// 🔐 CERTIFICATE INTERFACES
// ==========================================

/**
 * Información detallada del certificado digital
 */
export interface CertificateInfo {
  issuer: string;             // Emisor del certificado (CA)
  subject: string;            // Titular del certificado
  serialNumber: string;       // Número serie único
  validFrom: Date;           // Fecha inicio validez
  validTo: Date;             // Fecha fin validez
  isValid: boolean;          // Estado actual validez
  provider: CertificateProvider; // Proveedor detectado
  keySize: number;           // Tamaño clave en bits
  algorithm: string;         // Algoritmo del certificado
  fingerprint?: string;      // Huella digital
  purpose: string[];         // Usos autorizados
}

/**
 * Configuración de firma digital
 */
export interface DigitalSignatureConfig {
  algorithm: 'RSA-SHA256' | 'RSA-SHA1';   // Algoritmo firma
  canonicalization: string;               // Canonicalización XML
  keySize: 2048 | 4096;                  // Tamaño clave
  includeCertificate: boolean;            // Incluir certificado en firma
  includeKeyInfo: boolean;               // Incluir información de clave
}

/**
 * Resultado de proceso de firma digital
 */
export interface SignatureResult {
  success: boolean;           // Estado del proceso de firma
  signedXml?: string;        // XML firmado (si success=true)
  certificateInfo?: CertificateInfo; // Info del certificado usado
  signatureTime: number;     // Milisegundos de firma (SLA: ≤5000ms)
  errors: string[];          // Errores durante firma
  warnings: string[];        // Advertencias no críticas
  signatureId?: string;      // ID único de la firma
}

/**
 * Resultado validación de certificado
 */
export interface CertificateValidation {
  isValid: boolean;          // Estado validación general
  errors: string[];          // Errores críticos encontrados
  warnings: string[];        // Advertencias (ej: próximo vencimiento)
  certificateInfo?: CertificateInfo; // Datos del certificado
  remainingDays?: number;    // Días hasta vencimiento
  validationDetails?: {
    signatureValid: boolean;
    chainValid: boolean;
    dateValid: boolean;
    revokedStatus: 'valid' | 'revoked' | 'unknown';
  };
}

/**
 * Alerta de certificado próximo a vencer
 */
export interface CertificateExpiryAlert {
  certificateId: string;
  certificateName: string;
  companyId: string;
  expiryDate: Date;
  remainingDays: number;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  lastNotified?: Date;
}

/**
 * Interface para validación de certificado (extendida)
 */
export interface ExtendedCertificateValidation extends CertificateValidation {
  chainValidation?: {
    rootCA: boolean;
    intermediateCA: boolean;
    endEntity: boolean;
  };
  usage: {
    digitalSignature: boolean;
    keyEncipherment: boolean;
    dataEncipherment: boolean;
  };
}
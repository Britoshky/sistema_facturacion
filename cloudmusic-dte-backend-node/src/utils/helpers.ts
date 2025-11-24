// Utilidades básicas para CloudMusic DTE
import { DTEType, VALID_DOCUMENT_TYPES, SiiStatus } from '../trpc/schemas/common';
// ✅ Para tipos de DB, usar: import { UserRole, ClientType, ProductType } from '@prisma/client';

// Validación básica de RUT (tRPC schemas manejan validaciones complejas)
export const isValidRUT = (rut: string): boolean => {
  const cleanRut = rut.replace(/[.-]/g, '');
  
  if (cleanRut.length < 8 || cleanRut.length > 9) {
    return false;
  }
  
  const body = cleanRut.slice(0, -1);
  const dv = cleanRut.slice(-1).toLowerCase();
  
  let sum = 0;
  let multiplier = 2;
  
  for (let i = body.length - 1; i >= 0; i--) {
    sum += parseInt(body[i]) * multiplier;
    multiplier = multiplier === 7 ? 2 : multiplier + 1;
  }
  
  const expectedDV = 11 - (sum % 11);
  let calculatedDV: string;
  
  if (expectedDV === 11) {
    calculatedDV = '0';
  } else if (expectedDV === 10) {
    calculatedDV = 'k';
  } else {
    calculatedDV = expectedDV.toString();
  }
  
  return dv === calculatedDV;
};

// Formatear RUT
export const formatRUT = (rut: string): string => {
  const cleanRut = rut.replace(/[.-]/g, '');
  const body = cleanRut.slice(0, -1);
  const dv = cleanRut.slice(-1);
  
  const formattedBody = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  
  return `${formattedBody}-${dv}`;
};

// Función mejorada de validación de RUT que devuelve objeto completo  
export const validateRUT = (rut: string): { isValid: boolean; formatted: string; error?: string } => {
  if (!rut || typeof rut !== 'string') {
    return {
      isValid: false,
      formatted: '',
      error: 'RUT es requerido'
    };
  }

  const cleanRut = rut.replace(/[.-]/g, '');
  
  if (cleanRut.length < 8 || cleanRut.length > 9) {
    return {
      isValid: false,
      formatted: rut,
      error: 'RUT debe tener entre 8 y 9 dígitos'
    };
  }

  const valid = isValidRUT(rut);
  const formatted = valid ? formatRUT(rut) : rut;

  return {
    isValid: valid,
    formatted,
    error: valid ? undefined : 'RUT no es válido'
  };
};

// Generar siguiente folio
export const generateFolio = (lastFolio: number): number => {
  return lastFolio + 1;
};

// Constantes DTE para compatibilidad con código existente
export const DTE_TYPES = {
  33: 'Factura Electrónica',
  34: 'Factura No Afecta o Exenta Electrónica',
  39: 'Boleta Electrónica',
  41: 'Boleta No Afecta o Exenta Electrónica',
  46: 'Factura de Compra Electrónica',
  52: 'Guía de Despacho Electrónica',
  56: 'Nota de Débito Electrónica',
  61: 'Nota de Crédito Electrónica'
} as const;

// Estados de documentos para compatibilidad
export const DOCUMENT_STATUSES = {
  DRAFT: 'draft',
  ISSUED: 'issued',
  SENT: 'sent',
  ACCEPTED: 'accepted',
  REJECTED: 'rejected'
} as const;

export type DocumentStatus = typeof DOCUMENT_STATUSES[keyof typeof DOCUMENT_STATUSES];
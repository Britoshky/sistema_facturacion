import { parseStringPromise } from 'xml2js';
import * as crypto from 'crypto';
import { CAFFile, FolioAlert, CAFValidationResult } from '../trpc/schemas/folios';

export class CAFService {
  private readonly ALERT_THRESHOLD = 50; // RF008: Alerta con 50 folios restantes

  /**
   * Importar archivo CAF XML según RF008
   * Criterio: Importación automática de archivos CAF en XML
   */
  async importCAF(cafXmlContent: string, companyId: string): Promise<CAFValidationResult & { cafData?: CAFFile }> {
    const result: CAFValidationResult & { cafData?: CAFFile } = { 
      isValid: false, 
      errors: [], 
      warnings: [] 
    };

    try {
      // 1. Validar estructura CAF
      const validation = await this.validateCAFStructure(cafXmlContent);
      if (!validation.isValid) {
        result.errors.push(...validation.errors);
        result.warnings.push(...validation.warnings);
        return result;
      }

      const cafData = validation.cafData!;

      // 2. Verificar integridad de firma CAF
      const signatureValidation = await this.validateCAFSignature(cafXmlContent);
      if (!signatureValidation.isValid) {
        result.errors.push(...signatureValidation.errors);
        result.warnings.push(...signatureValidation.warnings);
        // Continuar con warning, no es error crítico en certificación
      }

      // 3. Verificar que no se superponga con folios existentes
      const overlapCheck = await this.checkFolioOverlap(
        companyId, 
        cafData.documentType, 
        cafData.fromFolio, 
        cafData.toFolio
      );
      
      if (overlapCheck.hasOverlap) {
        result.errors.push(`Rango de folios se superpone con folios existentes: ${overlapCheck.conflictingRanges.join(', ')}`);
        return result;
      }

      // 4. Verificar vigencia del CAF
      const now = new Date();
      if (cafData.expiryDate < now) {
        result.errors.push(`CAF expirado. Fecha de vencimiento: ${cafData.expiryDate.toISOString()}`);
        return result;
      }

      // 5. Advertir si CAF vence pronto (30 días)
      const daysToExpiry = Math.ceil((cafData.expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      if (daysToExpiry <= 30) {
        result.warnings.push(`CAF vence en ${daysToExpiry} días`);
      }

      result.isValid = true;
      result.cafData = cafData;

    } catch (error) {
      result.errors.push(`Error importando CAF: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return result;
  }

  /**
   * Validar estructura del archivo CAF XML
   */
  private async validateCAFStructure(cafXmlContent: string): Promise<CAFValidationResult> {
    const result: CAFValidationResult = { isValid: true, errors: [], warnings: [] };

    try {
      const parsed = await parseStringPromise(cafXmlContent, { explicitArray: false });
      
      // Estructura esperada del CAF
      const caf = parsed?.AUTORIZACION?.CAF;
      if (!caf) {
        result.isValid = false;
        result.errors.push('Estructura CAF inválida: elemento CAF no encontrado');
        return result;
      }

      // Extraer datos del CAF
      const documentType = parseInt(caf.DA?.TD);
      const fromFolio = parseInt(caf.DA?.RNG?.D);
      const toFolio = parseInt(caf.DA?.RNG?.H);
      const authDate = new Date(caf.DA?.FA);
      const rut = caf.DA?.RE;
      const companyName = caf.DA?.RS;

      // Validaciones básicas
      if (!documentType || ![33, 34, 39, 41, 46, 52, 56, 61].includes(documentType)) {
        result.isValid = false;
        result.errors.push(`Tipo de documento inválido: ${documentType}`);
      }

      if (!fromFolio || !toFolio || fromFolio >= toFolio) {
        result.isValid = false;
        result.errors.push(`Rango de folios inválido: ${fromFolio} - ${toFolio}`);
      }

      if (!rut || !this.validateRUT(rut)) {
        result.isValid = false;
        result.errors.push(`RUT inválido: ${rut}`);
      }

      if (isNaN(authDate.getTime())) {
        result.isValid = false;
        result.errors.push('Fecha de autorización inválida');
      }

      // Calcular fecha de expiración (normalmente 6 meses desde autorización)
      const expiryDate = new Date(authDate);
      expiryDate.setMonth(expiryDate.getMonth() + 6);

      if (result.isValid) {
        result.cafData = {
          documentType,
          fromFolio,
          toFolio,
          authorizationDate: authDate,
          expiryDate,
          rut,
          companyName: companyName || 'Sin nombre',
          authorizedRange: toFolio - fromFolio + 1,
          xmlContent: cafXmlContent,
          signature: caf.FRMA?.$ || '',
          isValid: true
        };
      }

    } catch (error) {
      result.isValid = false;
      result.errors.push(`Error parseando CAF XML: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return result;
  }

  /**
   * Validar firma digital del CAF
   */
  private async validateCAFSignature(cafXmlContent: string): Promise<{ isValid: boolean; errors: string[]; warnings: string[] }> {
    const result = { isValid: true, errors: [] as string[], warnings: [] as string[] };

    try {
      // Extraer elementos para validación de firma
      const parsed = await parseStringPromise(cafXmlContent, { explicitArray: false });
      const caf = parsed?.AUTORIZACION?.CAF;
      
      if (!caf?.FRMA) {
        result.warnings.push('CAF sin firma digital - modo certificación');
        return result;
      }

      // En un entorno real, aquí se validaría la firma RSA del SII
      // Por ahora, solo verificamos que existe la estructura
      const signature = caf.FRMA.$;
      if (!signature || signature.length < 100) {
        result.warnings.push('Firma CAF parece inválida o incompleta');
      }

      // Verificar algoritmo de firma
      const algorithm = caf.FRMA?.algoritmo || 'SHA1withRSA';
      if (algorithm !== 'SHA1withRSA' && algorithm !== 'SHA256withRSA') {
        result.warnings.push(`Algoritmo de firma no estándar: ${algorithm}`);
      }

    } catch (error) {
      result.warnings.push(`Error validando firma CAF: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return result;
  }

  /**
   * Verificar superposición de rangos de folios
   */
  private async checkFolioOverlap(
    companyId: string, 
    documentType: number, 
    fromFolio: number, 
    toFolio: number
  ): Promise<{ hasOverlap: boolean; conflictingRanges: string[] }> {
    // Esta función debería consultar la base de datos para verificar overlap
    // Por simplicidad, retornamos sin overlap - se implementaría en el router
    return { hasOverlap: false, conflictingRanges: [] };
  }

  /**
   * Generar alertas de folios bajos según RF008
   */
  async generateFolioAlerts(companyId: string): Promise<FolioAlert[]> {
    const alerts: FolioAlert[] = [];
    
    // Esta función debería consultar la base de datos
    // Implementación real estaría en el router con acceso a Prisma
    
    return alerts;
  }

  /**
   * Obtener siguiente folio disponible con control de secuencia
   */
  async getNextFolio(companyId: string, documentType: number): Promise<{
    success: boolean;
    folio?: number;
    folioId?: string;
    remainingFolios?: number;
    alertGenerated?: boolean;
    errors: string[];
  }> {
    // Implementación base - se completará en el router
    return {
      success: false,
      errors: ['Función debe implementarse en router con acceso a base de datos']
    };
  }

  /**
   * Validar secuencia de folios (sin saltos)
   */
  validateFolioSequence(folios: { folio: number; used: boolean }[]): {
    isValid: boolean;
    gaps: number[];
    duplicates: number[];
    errors: string[];
  } {
    const result = {
      isValid: true,
      gaps: [] as number[],
      duplicates: [] as number[],
      errors: [] as string[]
    };

    const usedFolios = folios.filter(f => f.used).map(f => f.folio).sort((a, b) => a - b);
    
    // Detectar gaps en secuencia
    for (let i = 1; i < usedFolios.length; i++) {
      const current = usedFolios[i];
      const previous = usedFolios[i - 1];
      
      if (current !== previous + 1) {
        // Hay un gap
        for (let gap = previous + 1; gap < current; gap++) {
          result.gaps.push(gap);
        }
      }
    }

    // Detectar duplicados
    const folioCount = new Map<number, number>();
    folios.forEach(f => {
      const count = folioCount.get(f.folio) || 0;
      folioCount.set(f.folio, count + 1);
    });

    folioCount.forEach((count, folio) => {
      if (count > 1) {
        result.duplicates.push(folio);
      }
    });

    // Generar errores
    if (result.gaps.length > 0) {
      result.isValid = false;
      result.errors.push(`Gaps en secuencia de folios: ${result.gaps.join(', ')}`);
    }

    if (result.duplicates.length > 0) {
      result.isValid = false;
      result.errors.push(`Folios duplicados: ${result.duplicates.join(', ')}`);
    }

    return result;
  }

  /**
   * Generar reporte de uso de folios
   */
  generateFolioReport(folios: { 
    folio: number; 
    documentType: number; 
    used: boolean; 
    usedDate?: Date;
    documentId?: string;
  }[]): {
    totalFolios: number;
    usedFolios: number;
    remainingFolios: number;
    usagePercentage: number;
    averageUsagePerDay: number;
    estimatedDaysRemaining: number;
    alertLevel: 'ok' | 'warning' | 'critical';
  } {
    const totalFolios = folios.length;
    const usedFolios = folios.filter(f => f.used).length;
    const remainingFolios = totalFolios - usedFolios;
    const usagePercentage = totalFolios > 0 ? (usedFolios / totalFolios) * 100 : 0;

    // Calcular promedio de uso diario
    const usedWithDates = folios.filter(f => f.used && f.usedDate);
    let averageUsagePerDay = 0;
    let estimatedDaysRemaining = Infinity;

    if (usedWithDates.length > 1) {
      const dates = usedWithDates.map(f => f.usedDate!.getTime()).sort();
      const firstDate = new Date(dates[0]);
      const lastDate = new Date(dates[dates.length - 1]);
      const daysDiff = Math.max(1, Math.ceil((lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24)));
      
      averageUsagePerDay = usedWithDates.length / daysDiff;
      
      if (averageUsagePerDay > 0) {
        estimatedDaysRemaining = Math.ceil(remainingFolios / averageUsagePerDay);
      }
    }

    // Determinar nivel de alerta
    let alertLevel: 'ok' | 'warning' | 'critical' = 'ok';
    if (remainingFolios <= 10) {
      alertLevel = 'critical';
    } else if (remainingFolios <= this.ALERT_THRESHOLD) {
      alertLevel = 'warning';
    }

    return {
      totalFolios,
      usedFolios,
      remainingFolios,
      usagePercentage,
      averageUsagePerDay,
      estimatedDaysRemaining,
      alertLevel
    };
  }

  /**
   * Validar RUT chileno
   */
  private validateRUT(rut: string): boolean {
    const cleanRUT = rut.replace(/[^0-9kK]/g, '');
    if (cleanRUT.length < 2) return false;

    const body = cleanRUT.slice(0, -1);
    const dv = cleanRUT.slice(-1).toUpperCase();

    let sum = 0;
    let multiplier = 2;

    for (let i = body.length - 1; i >= 0; i--) {
      sum += parseInt(body[i]) * multiplier;
      multiplier = multiplier === 7 ? 2 : multiplier + 1;
    }

    const expectedDV = 11 - (sum % 11);
    const calculatedDV = expectedDV === 11 ? '0' : expectedDV === 10 ? 'K' : expectedDV.toString();

    return dv === calculatedDV;
  }
}

// Singleton instance
export const cafService = new CAFService();
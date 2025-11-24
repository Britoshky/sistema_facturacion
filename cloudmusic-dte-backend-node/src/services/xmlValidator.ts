import { readFileSync } from 'fs';
import { join } from 'path';
import { parseStringPromise, Builder } from 'xml2js';
import * as libxml from 'libxmljs';
import { DTEType } from '../trpc/schemas/common';
import { ValidationResult, ValidationError } from '../trpc/schemas/validation';

export enum DTEValidationType {
  SCHEMA = 'schema',
  BUSINESS = 'business',
  FULL = 'full'
}

export class XMLValidator {
  private dteSchema: unknown | null = null; // libxml.Document
  private boletaSchema: unknown | null = null; // libxml.Document
  private schemasPath: string;

  constructor() {
    this.schemasPath = join(__dirname, '../schemas/sii');
    this.loadSchemas();
  }

  /**
   * Cargar esquemas XSD del SII según RF002
   * DTE_v10.xsd para tipos 33, 34, 46, 52, 56, 61
   * EnvioBOLETA_v11.xsd para tipos 39, 41
   */
  private loadSchemas(): void {
    try {
      // Cargar DTE_v10.xsd
      const dteSchemaPath = join(this.schemasPath, 'DTE_v10.xsd');
      if (this.fileExists(dteSchemaPath)) {
        const dteSchemaContent = readFileSync(dteSchemaPath, 'utf-8');
        this.dteSchema = libxml.parseXml(dteSchemaContent);
      }

      // Cargar EnvioBOLETA_v11.xsd  
      const boletaSchemaPath = join(this.schemasPath, 'EnvioBOLETA_v11.xsd');
      if (this.fileExists(boletaSchemaPath)) {
        const boletaSchemaContent = readFileSync(boletaSchemaPath, 'utf-8');
        this.boletaSchema = libxml.parseXml(boletaSchemaContent);
      }

      console.log('✅ Esquemas XSD del SII cargados correctamente');
    } catch (error) {
      console.warn('⚠️ No se pudieron cargar esquemas XSD:', error);
      // Continuar sin validación XSD (modo degradado)
    }
  }

  private fileExists(filePath: string): boolean {
    try {
      readFileSync(filePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Validar documento XML según tipo DTE (RF002)
   * Criterio: Tasa de error ≤ 2%, tiempo ≤ 1 segundo
   */
  async validateDocument(xmlContent: string, expectedType?: DTEType): Promise<ValidationResult> {
    const startTime = new Date();
    const result: ValidationResult = {
      isValid: true,
      errors: [],
      warnings: [],
      timing: {
        validationTime: 0,
        startTime,
        endTime: new Date()
      }
    };

    try {
      // 1. Validación de estructura XML básica
      const xmlDoc = libxml.parseXml(xmlContent);
      if (!xmlDoc) {
        result.isValid = false;
        result.errors.push({
          code: 'XML_PARSE_ERROR',
          message: 'El documento XML no es válido o está mal formado',
          severity: 'error'
        });
        return this.finalizeResult(result, startTime);
      }

      // 2. Detectar tipo de documento DTE
      const documentType = await this.detectDocumentType(xmlContent);
      result.documentType = documentType as any;

      // 3. Validar tipo esperado si se proporciona
      if (expectedType && documentType !== expectedType) {
        result.errors.push({
          code: 'DOCUMENT_TYPE_MISMATCH',
          message: `Tipo esperado: ${expectedType}, tipo encontrado: ${documentType}`,
          severity: 'error'
        });
        result.isValid = false;
      }

      // 4. Validar contra esquema XSD correspondiente
      if (documentType) {
        const schemaValidation = await this.validateAgainstSchema(xmlContent, documentType);
        result.errors.push(...schemaValidation.errors);
        result.warnings.push(...schemaValidation.warnings);
        if (schemaValidation.errors.length > 0) {
          result.isValid = false;
        }
      }

      // 5. Validaciones específicas DTE
      const dteValidation = await this.validateDTEStructure(xmlContent, documentType);
      result.errors.push(...dteValidation.errors);
      result.warnings.push(...dteValidation.warnings);
      if (dteValidation.errors.length > 0) {
        result.isValid = false;
      }

    } catch (error) {
      result.isValid = false;
      result.errors.push({
        code: 'VALIDATION_ERROR',
        message: `Error durante validación: ${error instanceof Error ? error.message : 'Error desconocido'}`,
        severity: 'error'
      });
    }

    return this.finalizeResult(result, startTime);
  }

  /**
   * Detectar tipo de documento DTE desde XML
   */
  private async detectDocumentType(xmlContent: string): Promise<DTEType | undefined> {
    try {
      const parsed = await parseStringPromise(xmlContent, { explicitArray: false });
      
      // Buscar en diferentes estructuras posibles
      const tipoDoc = 
        parsed?.DTE?.Documento?.Encabezado?.IdDoc?.TipoDTE ||
        parsed?.EnvioDTE?.SetDTE?.DTE?.Documento?.Encabezado?.IdDoc?.TipoDTE ||
        parsed?.EnvioBOLETA?.SubTotDTE?.TipoDTE;

      if (tipoDoc) {
        const typeNumber = parseInt(tipoDoc.toString());
        if (Object.values(DTEType).includes(typeNumber)) {
          return typeNumber as DTEType;
        }
      }
    } catch (error) {
      console.warn('Error detectando tipo DTE:', error);
    }
    
    return undefined;
  }

  /**
   * Validar contra esquema XSD según tipo de documento
   */
  private async validateAgainstSchema(xmlContent: string, documentType: DTEType): Promise<{ errors: ValidationError[]; warnings: string[] }> {
    const errors: ValidationError[] = [];
    const warnings: string[] = [];

    try {
      let schema: any = null;

      // Seleccionar esquema según tipo DTE (RF002)
      if ([DTEType.BOLETA_ELECTRONICA].includes(documentType)) {
        // Boletas: EnvioBOLETA_v11.xsd
        schema = this.boletaSchema;
      } else if ([DTEType.FACTURA_ELECTRONICA, DTEType.FACTURA_ELECTRONICA_EXENTA, DTEType.FACTURA_COMPRA_ELECTRONICA, DTEType.GUIA_DESPACHO_ELECTRONICA, DTEType.NOTA_DEBITO_ELECTRONICA, DTEType.NOTA_CREDITO_ELECTRONICA].includes(documentType)) {
        // DTEs: DTE_v10.xsd
        schema = this.dteSchema;
      }

      if (!schema) {
        warnings.push(`Esquema XSD no disponible para tipo ${documentType}`);
        return { errors, warnings };
      }

      // Validar XML contra esquema XSD
      const xmlDoc = libxml.parseXml(xmlContent);
      const isValid = xmlDoc.validate(schema);

      if (!isValid) {
        const validationErrors = xmlDoc.validationErrors;
        validationErrors.forEach((error, index) => {
          errors.push({
            code: `XSD_VALIDATION_${index + 1}`,
            message: error.message || 'Error de validación XSD',
            line: error.line,
            column: error.column,
            severity: 'error'
          });
        });
      }

    } catch (error) {
      errors.push({
        code: 'SCHEMA_VALIDATION_ERROR',
        message: `Error validando contra esquema: ${error instanceof Error ? error.message : 'Error desconocido'}`,
        severity: 'error'
      });
    }

    return { errors, warnings };
  }

  /**
   * Validaciones específicas de estructura DTE
   */
  private async validateDTEStructure(xmlContent: string, documentType?: DTEType): Promise<{ errors: ValidationError[]; warnings: string[] }> {
    const errors: ValidationError[] = [];
    const warnings: string[] = [];

    try {
      const parsed = await parseStringPromise(xmlContent, { explicitArray: false });

      // Validaciones comunes según normativa SII
      if (documentType && [DTEType.FACTURA_ELECTRONICA, DTEType.FACTURA_ELECTRONICA_EXENTA, DTEType.NOTA_DEBITO_ELECTRONICA, DTEType.NOTA_CREDITO_ELECTRONICA].includes(documentType)) {
        // Facturas y notas requieren RUT emisor válido
        const rutEmisor = parsed?.DTE?.Documento?.Encabezado?.Emisor?.RUTEmisor;
        if (!rutEmisor || !this.validateRUT(rutEmisor)) {
          errors.push({
            code: 'INVALID_RUT_EMISOR',
            message: 'RUT emisor inválido o faltante',
            severity: 'error'
          });
        }

        // Validar fecha de emisión
        const fechaEmision = parsed?.DTE?.Documento?.Encabezado?.IdDoc?.FchEmis;
        if (!fechaEmision || !this.validateDate(fechaEmision)) {
          errors.push({
            code: 'INVALID_EMISSION_DATE',
            message: 'Fecha de emisión inválida o faltante',
            severity: 'error'
          });
        }
      }

      // Validaciones específicas por tipo
      if (documentType === DTEType.FACTURA_ELECTRONICA) {
        // Factura debe tener montos
        const montoTotal = parsed?.DTE?.Documento?.Encabezado?.Totales?.MntTotal;
        if (!montoTotal || parseFloat(montoTotal) <= 0) {
          errors.push({
            code: 'INVALID_TOTAL_AMOUNT',
            message: 'Monto total inválido para factura electrónica',
            severity: 'error'
          });
        }
      }

    } catch (error) {
      errors.push({
        code: 'STRUCTURE_VALIDATION_ERROR',
        message: `Error validando estructura DTE: ${error instanceof Error ? error.message : 'Error desconocido'}`,
        severity: 'error'
      });
    }

    return { errors, warnings };
  }

  /**
   * Validar RUT chileno (dígito verificador)
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

  /**
   * Validar formato de fecha YYYY-MM-DD
   */
  private validateDate(date: string): boolean {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(date)) return false;

    const parsedDate = new Date(date);
    return parsedDate instanceof Date && !isNaN(parsedDate.getTime());
  }

  /**
   * Finalizar resultado con timing
   */
  private finalizeResult(result: ValidationResult, startTime: Date): ValidationResult {
    const endTime = new Date();
    result.timing.endTime = endTime;
    result.timing.validationTime = endTime.getTime() - startTime.getTime();

    // RF002: Advertir si excede 1 segundo
    if (result.timing.validationTime > 1000) {
      result.warnings.push(`Validación excedió tiempo objetivo: ${result.timing.validationTime}ms > 1000ms`);
    }

    return result;
  }

  /**
   * Validar múltiples documentos (batch)
   */
  async validateBatch(documents: { content: string; expectedType?: DocumentType }[]): Promise<ValidationResult[]> {
    const results: ValidationResult[] = [];
    
    for (const doc of documents) {
      const result = await this.validateDocument(doc.content, doc.expectedType as any);
      results.push(result);
    }

    return results;
  }

  /**
   * Obtener estadísticas de validación
   */
  getValidationStats(results: ValidationResult[]): {
    totalDocuments: number;
    validDocuments: number;
    invalidDocuments: number;
    errorRate: number;
    averageTime: number;
    meetsSLATime: boolean; // RF002: ≤ 1 segundo
    meetsSLAErrorRate: boolean; // RF002: ≤ 2% error rate
  } {
    const totalDocuments = results.length;
    const validDocuments = results.filter(r => r.isValid).length;
    const invalidDocuments = totalDocuments - validDocuments;
    const errorRate = totalDocuments > 0 ? (invalidDocuments / totalDocuments) * 100 : 0;
    const averageTime = totalDocuments > 0 
      ? results.reduce((sum, r) => sum + r.timing.validationTime, 0) / totalDocuments 
      : 0;

    return {
      totalDocuments,
      validDocuments,
      invalidDocuments,
      errorRate,
      averageTime,
      meetsSLATime: averageTime <= 1000, // RF002: ≤ 1 segundo
      meetsSLAErrorRate: errorRate <= 2   // RF002: ≤ 2% error rate
    };
  }
}

// Singleton instance
export const xmlValidator = new XMLValidator();
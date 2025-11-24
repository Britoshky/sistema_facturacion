import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import * as https from 'https';
import { Builder, parseStringPromise } from 'xml2js';
import { 
  SIIEnvironment, 
  SIIResponse, 
  SIIConfig, 
  SendDTERequest, 
  QueryStatusRequest, 
  AcknowledgmentRequest 
} from '../trpc/schemas/sii';

// Enum interno del servicio (no exportado)
enum SIIOperation {
  SEND_DTE = 'sendDTE',
  QUERY_STATUS = 'queryStatus',
  GET_ACKNOWLEDGMENT = 'getAcknowledgment',
  SEND_RECEIPT = 'sendReceipt'
}

export class SIIService {
  private axiosInstance: AxiosInstance;
  private config: SIIConfig;
  
  // URLs SII según ambiente
  private readonly ENDPOINTS = {
    [SIIEnvironment.CERTIFICATION]: {
      baseUrl: 'https://maullin.sii.cl/DTEWS/',
      uploadDTE: 'services/wsUploadDte?wsdl',
      queryStatus: 'services/wsQueryStatus?wsdl',
      getAcknowledgment: 'services/wsGetAcknowledgment?wsdl'
    },
    [SIIEnvironment.PRODUCTION]: {
      baseUrl: 'https://sii.cl/DTEWS/',
      uploadDTE: 'services/wsUploadDte?wsdl',
      queryStatus: 'services/wsQueryStatus?wsdl', 
      getAcknowledgment: 'services/wsGetAcknowledgment?wsdl'
    }
  };

  constructor(config: SIIConfig) {
    this.config = config;
    
    // Configurar axios con timeout y reintentos
    this.axiosInstance = axios.create({
      baseURL: this.ENDPOINTS[config.environment].baseUrl,
      timeout: config.timeout,
      headers: {
        'User-Agent': config.userAgent,
        'Content-Type': 'text/xml; charset=utf-8'
      },
      httpsAgent: new https.Agent({
        rejectUnauthorized: false // Para certificación SII
      })
    });

    // Interceptores para logging y manejo de errores
    this.setupInterceptors();
  }

  /**
   * Configurar interceptores de request/response
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.axiosInstance.interceptors.request.use(
      (config) => {
        console.log(`🚀 SII Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('❌ SII Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.axiosInstance.interceptors.response.use(
      (response) => {
        console.log(`✅ SII Response: ${response.status} - ${response.config.url}`);
        return response;
      },
      async (error) => {
        const config = error.config;
        
        // Reintentar si es necesario
        if (config && !config.__isRetryRequest && this.shouldRetry(error)) {
          config.__isRetryRequest = true;
          config.__retryCount = (config.__retryCount || 0) + 1;
          
          if (config.__retryCount <= this.config.retryAttempts) {
            console.log(`🔄 Reintentando SII request (${config.__retryCount}/${this.config.retryAttempts})`);
            
            // Delay exponencial
            const delay = Math.pow(2, config.__retryCount) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
            
            return this.axiosInstance.request(config);
          }
        }
        
        console.error('❌ SII Response Error:', error.message);
        return Promise.reject(error);
      }
    );
  }

  /**
   * Determinar si se debe reintentar la request
   */
  private shouldRetry(error: any): boolean {
    if (!error.response) {
      return true; // Error de red
    }
    
    const status = error.response.status;
    return status >= 500 || status === 408 || status === 429;
  }

  /**
   * Enviar DTE al SII
   */
  async sendDTE(request: SendDTERequest): Promise<SIIResponse> {
    const startTime = Date.now();
    const result: SIIResponse = {
      success: false,
      errors: [],
      warnings: [],
      timing: {
        requestTime: startTime,
        responseTime: 0,
        totalTime: 0
      }
    };

    try {
      // 1. Validar parámetros
      const validation = this.validateSendDTERequest(request);
      if (!validation.isValid) {
        result.errors.push(...validation.errors);
        return this.finalizeSIIResponse(result, startTime);
      }

      // 2. Preparar SOAP envelope para envío
      const soapEnvelope = this.buildSendDTESoapEnvelope(request);
      
      // 3. Enviar request al SII
      const response = await this.axiosInstance.post(
        this.ENDPOINTS[this.config.environment].uploadDTE,
        soapEnvelope,
        {
          headers: {
            'SOAPAction': 'upload'
          }
        }
      );

      // 4. Parsear respuesta XML
      const parsedResponse = await this.parseSIIResponse(response.data);
      
      if (parsedResponse.success) {
        result.success = true;
        result.trackId = parsedResponse.trackId;
        result.status = 'sent';
        result.siiResponse = response.data;
      } else {
        result.errors.push(...parsedResponse.errors);
        result.warnings.push(...parsedResponse.warnings);
      }

    } catch (error) {
      this.handleSIIError(error, result);
    }

    return this.finalizeSIIResponse(result, startTime);
  }

  /**
   * Consultar estado de DTE en SII
   */
  async queryDTEStatus(request: QueryStatusRequest): Promise<SIIResponse> {
    const startTime = Date.now();
    const result: SIIResponse = {
      success: false,
      errors: [],
      warnings: [],
      timing: {
        requestTime: startTime,
        responseTime: 0,
        totalTime: 0
      }
    };

    try {
      // 1. Preparar SOAP envelope para consulta
      const soapEnvelope = this.buildQueryStatusSoapEnvelope(request);
      
      // 2. Enviar consulta al SII
      const response = await this.axiosInstance.post(
        this.ENDPOINTS[this.config.environment].queryStatus,
        soapEnvelope,
        {
          headers: {
            'SOAPAction': 'queryStatus'
          }
        }
      );

      // 3. Parsear respuesta
      const parsedResponse = await this.parseQueryStatusResponse(response.data);
      
      result.success = parsedResponse.success;
      result.status = parsedResponse.status;
      result.message = parsedResponse.message;
      result.siiResponse = response.data;
      
      if (!parsedResponse.success) {
        result.errors.push(...parsedResponse.errors);
      }

    } catch (error) {
      this.handleSIIError(error, result);
    }

    return this.finalizeSIIResponse(result, startTime);
  }

  /**
   * Obtener acuse de recibo del SII
   */
  async getAcknowledgment(request: AcknowledgmentRequest): Promise<SIIResponse> {
    const startTime = Date.now();
    const result: SIIResponse = {
      success: false,
      errors: [],
      warnings: [],
      timing: {
        requestTime: startTime,
        responseTime: 0,
        totalTime: 0
      }
    };

    try {
      // 1. Preparar SOAP envelope
      const soapEnvelope = this.buildAcknowledgmentSoapEnvelope(request);
      
      // 2. Solicitar acuse al SII
      const response = await this.axiosInstance.post(
        this.ENDPOINTS[this.config.environment].getAcknowledgment,
        soapEnvelope,
        {
          headers: {
            'SOAPAction': 'getAcknowledgment'
          }
        }
      );

      // 3. Parsear acuse de recibo
      const parsedResponse = await this.parseAcknowledgmentResponse(response.data);
      
      result.success = parsedResponse.success;
      result.siiResponse = response.data;
      
      if (!parsedResponse.success) {
        result.errors.push(...parsedResponse.errors);
      }

    } catch (error) {
      this.handleSIIError(error, result);
    }

    return this.finalizeSIIResponse(result, startTime);
  }

  /**
   * Validar request de envío DTE
   */
  private validateSendDTERequest(request: SendDTERequest): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!request.rutEmisor || !request.dvEmisor) {
      errors.push('RUT emisor requerido');
    }

    if (!request.rutEnvia || !request.dvEnvia) {
      errors.push('RUT quien envía requerido');
    }

    if (!request.xmlDTE) {
      errors.push('XML DTE requerido');
    }

    if (!request.nombreArchivo) {
      errors.push('Nombre de archivo requerido');
    }

    // Validar formato RUT
    if (request.rutEmisor && !this.validateRUT(request.rutEmisor, request.dvEmisor)) {
      errors.push('RUT emisor inválido');
    }

    return { isValid: errors.length === 0, errors };
  }

  /**
   * Construir SOAP envelope para envío DTE
   */
  private buildSendDTESoapEnvelope(request: SendDTERequest): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:dte="http://sii.cl/ws/dte/upload">
  <soapenv:Header/>
  <soapenv:Body>
    <dte:upload>
      <rutEmisor>${request.rutEmisor}</rutEmisor>
      <dvEmisor>${request.dvEmisor}</dvEmisor>
      <rutEnvia>${request.rutEnvia}</rutEnvia>
      <dvEnvia>${request.dvEnvia}</dvEnvia>
      <archivo>
        <nombre>${request.nombreArchivo}</nombre>
        <contenido><![CDATA[${request.xmlDTE}]]></contenido>
      </archivo>
    </dte:upload>
  </soapenv:Body>
</soapenv:Envelope>`;
  }

  /**
   * Construir SOAP envelope para consulta estado
   */
  private buildQueryStatusSoapEnvelope(request: QueryStatusRequest): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:dte="http://sii.cl/ws/dte/query">
  <soapenv:Header/>
  <soapenv:Body>
    <dte:queryStatus>
      <rutEmisor>${request.rutEmisor}</rutEmisor>
      <dvEmisor>${request.dvEmisor}</dvEmisor>
      <trackId>${request.trackId}</trackId>
    </dte:queryStatus>
  </soapenv:Body>
</soapenv:Envelope>`;
  }

  /**
   * Construir SOAP envelope para acuse de recibo
   */
  private buildAcknowledgmentSoapEnvelope(request: AcknowledgmentRequest): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:dte="http://sii.cl/ws/dte/acknowledgment">
  <soapenv:Header/>
  <soapenv:Body>
    <dte:getAcknowledgment>
      <rutEmisor>${request.rutEmisor}</rutEmisor>
      <dvEmisor>${request.dvEmisor}</dvEmisor>
      <trackId>${request.trackId}</trackId>
    </dte:getAcknowledgment>
  </soapenv:Body>
</soapenv:Envelope>`;
  }

  /**
   * Parsear respuesta SII genérica
   */
  private async parseSIIResponse(xmlResponse: string): Promise<{
    success: boolean;
    trackId?: string;
    errors: string[];
    warnings: string[];
  }> {
    try {
      const parsed = await parseStringPromise(xmlResponse, { explicitArray: false });
      
      // Extraer información de la respuesta SOAP
      const body = parsed['soapenv:Envelope']['soapenv:Body'];
      const uploadResponse = body?.uploadResponse || body?.response;
      
      if (uploadResponse) {
        const trackId = uploadResponse.trackId;
        const status = uploadResponse.status;
        
        return {
          success: !!trackId,
          trackId: trackId,
          errors: status === 'ERROR' ? [uploadResponse.message || 'Error desconocido'] : [],
          warnings: []
        };
      }
      
      return {
        success: false,
        errors: ['Respuesta SII inválida'],
        warnings: []
      };

    } catch (error) {
      return {
        success: false,
        errors: [`Error parseando respuesta SII: ${error instanceof Error ? error.message : 'Error desconocido'}`],
        warnings: []
      };
    }
  }

  /**
   * Parsear respuesta de consulta de estado
   */
  private async parseQueryStatusResponse(xmlResponse: string): Promise<{
    success: boolean;
    status?: string;
    message?: string;
    errors: string[];
  }> {
    try {
      const parsed = await parseStringPromise(xmlResponse, { explicitArray: false });
      const body = parsed['soapenv:Envelope']['soapenv:Body'];
      const queryResponse = body?.queryStatusResponse;
      
      if (queryResponse) {
        return {
          success: true,
          status: queryResponse.status,
          message: queryResponse.message,
          errors: []
        };
      }
      
      return {
        success: false,
        errors: ['Respuesta de consulta inválida'],
      };

    } catch (error) {
      return {
        success: false,
        errors: [`Error parseando consulta: ${error instanceof Error ? error.message : 'Error desconocido'}`]
      };
    }
  }

  /**
   * Parsear respuesta de acuse de recibo
   */
  private async parseAcknowledgmentResponse(xmlResponse: string): Promise<{
    success: boolean;
    errors: string[];
  }> {
    try {
      const parsed = await parseStringPromise(xmlResponse, { explicitArray: false });
      const body = parsed['soapenv:Envelope']['soapenv:Body'];
      const ackResponse = body?.getAcknowledgmentResponse;
      
      return {
        success: !!ackResponse,
        errors: ackResponse ? [] : ['No se pudo obtener acuse de recibo']
      };

    } catch (error) {
      return {
        success: false,
        errors: [`Error parseando acuse: ${error instanceof Error ? error.message : 'Error desconocido'}`]
      };
    }
  }

  /**
   * Manejar errores SII
   */
  private handleSIIError(error: any, result: SIIResponse): void {
    if (error.response) {
      // Error HTTP
      result.statusCode = error.response.status;
      result.errors.push(`Error HTTP ${error.response.status}: ${error.response.statusText}`);
      
      if (error.response.data) {
        result.siiResponse = error.response.data;
      }
    } else if (error.request) {
      // Error de red/timeout
      result.errors.push('Error de conexión con SII - Timeout o problemas de red');
    } else {
      // Error de configuración
      result.errors.push(`Error configuración: ${error.message}`);
    }
  }

  /**
   * Finalizar respuesta SII con timing
   */
  private finalizeSIIResponse(result: SIIResponse, startTime: number): SIIResponse {
    const endTime = Date.now();
    result.timing.responseTime = endTime;
    result.timing.totalTime = endTime - startTime;

    // Advertir si es muy lento
    if (result.timing.totalTime > 10000) { // 10 segundos
      result.warnings.push(`Respuesta SII lenta: ${result.timing.totalTime}ms`);
    }

    return result;
  }

  /**
   * Validar RUT chileno
   */
  private validateRUT(rut: string, dv: string): boolean {
    const cleanRUT = rut.replace(/[^0-9]/g, '');
    if (cleanRUT.length < 1) return false;

    let sum = 0;
    let multiplier = 2;

    for (let i = cleanRUT.length - 1; i >= 0; i--) {
      sum += parseInt(cleanRUT[i]) * multiplier;
      multiplier = multiplier === 7 ? 2 : multiplier + 1;
    }

    const expectedDV = 11 - (sum % 11);
    const calculatedDV = expectedDV === 11 ? '0' : expectedDV === 10 ? 'K' : expectedDV.toString();

    return dv.toUpperCase() === calculatedDV;
  }

  /**
   * Obtener configuración actual
   */
  getConfig(): SIIConfig {
    return { ...this.config };
  }

  /**
   * Cambiar ambiente (certificación/producción)
   */
  setEnvironment(environment: SIIEnvironment): void {
    this.config.environment = environment;
    this.axiosInstance.defaults.baseURL = this.ENDPOINTS[environment].baseUrl;
  }

  /**
   * Health check del servicio SII
   */
  async healthCheck(): Promise<{
    isAvailable: boolean;
    environment: SIIEnvironment;
    responseTime: number;
    errors: string[];
  }> {
    const startTime = Date.now();
    
    try {
      // Test ping básico al SII
      const response = await this.axiosInstance.get('/', { timeout: 5000 });
      
      return {
        isAvailable: response.status < 400,
        environment: this.config.environment,
        responseTime: Date.now() - startTime,
        errors: []
      };

    } catch (error) {
      return {
        isAvailable: false,
        environment: this.config.environment,
        responseTime: Date.now() - startTime,
        errors: [error instanceof Error ? error.message : 'Error conectando con SII']
      };
    }
  }
}

// Factory para crear instancia SII
export function createSIIService(config: Partial<SIIConfig> = {}): SIIService {
  const defaultConfig: SIIConfig = {
    environment: SIIEnvironment.CERTIFICATION,
    rutEmisor: '',
    dvEmisor: '',
    timeout: 30000, // 30 segundos
    retryAttempts: 3,
    userAgent: 'CloudMusic-DTE/1.0',
    enableCompression: true,
    validateSSL: true
  };

  return new SIIService({ ...defaultConfig, ...config });
}
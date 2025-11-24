import * as forge from 'node-forge';
import * as crypto from 'crypto';
import { readFileSync } from 'fs';
import { SignedXml } from 'xml-crypto';
import * as xpath from 'xpath';
import { DOMParser } from '@xmldom/xmldom';
import { CertificateProvider, DigitalSignatureConfig, SignatureResult, CertificateInfo, CertificateValidation } from '../trpc/schemas/certificates';

export class DigitalSigner {
  private defaultConfig: DigitalSignatureConfig = {
    algorithm: 'RSA-SHA256', // RF003: RSA-2048 + SHA-256
    canonicalization: 'http://www.w3.org/2001/10/xml-exc-c14n#',
    keySize: 2048,
    includeCertificate: true,
    includeKeyInfo: true
  };

  /**
   * Firmar documento XML con certificado .pfx según RF003
   * Criterio: Tiempo de firma ≤ 5 segundos
   */
  async signXML(
    xmlContent: string, 
    pfxBuffer: Buffer, 
    pfxPassword: string,
    config: Partial<DigitalSignatureConfig> = {}
  ): Promise<SignatureResult> {
    const startTime = Date.now();
    const finalConfig = { ...this.defaultConfig, ...config };
    const result: SignatureResult = {
      success: false,
      signatureTime: 0,
      errors: [],
      warnings: []
    };

    try {
      // 1. Validar y cargar certificado .pfx
      const certificateData = await this.loadPfxCertificate(pfxBuffer, pfxPassword);
      if (!certificateData.success) {
        result.errors.push(...certificateData.errors);
        return this.finalizeSignatureResult(result, startTime);
      }

      // 2. Validar certificado
      const certValidation = await this.validateCertificate(certificateData.certificate!, certificateData.privateKey!);
      result.certificateInfo = certValidation.certificateInfo;
      
      if (!certValidation.isValid) {
        result.errors.push(...certValidation.errors);
        result.warnings.push(...certValidation.warnings);
      }

      // 3. Preparar XML para firma
      const preparedXml = this.prepareXmlForSigning(xmlContent);
      
      // 4. Crear firma XML usando xml-crypto
      const signedXml = await this.createXmlSignature(
        preparedXml, 
        certificateData.privateKey!,
        certificateData.certificate!,
        finalConfig
      );

      if (signedXml) {
        result.success = true;
        result.signedXml = signedXml;
      } else {
        result.errors.push('Error generando firma XML');
      }

    } catch (error) {
      result.errors.push(`Error durante firma digital: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return this.finalizeSignatureResult(result, startTime);
  }

  /**
   * Cargar certificado .pfx y extraer clave privada
   */
  private async loadPfxCertificate(pfxBuffer: Buffer, password: string): Promise<{
    success: boolean;
    certificate?: forge.pki.Certificate;
    privateKey?: forge.pki.PrivateKey;
    errors: string[];
  }> {
    const result = { success: false, errors: [] as string[] };

    try {
      // Decodificar archivo .pfx
      const p12Asn1 = forge.asn1.fromDer(pfxBuffer.toString('binary'));
      const p12 = forge.pkcs12.pkcs12FromAsn1(p12Asn1, password);

      // Extraer certificado y clave privada
      const bags = p12.getBags({ bagType: forge.pki.oids.certBag });
      const certBag = bags[forge.pki.oids.certBag];
      
      if (!certBag || certBag.length === 0) {
        result.errors.push('No se encontró certificado en archivo .pfx');
        return result;
      }

      const certificate = certBag[0].cert;
      if (!certificate) {
        result.errors.push('Certificado inválido en archivo .pfx');
        return result;
      }

      // Extraer clave privada
      const keyBags = p12.getBags({ bagType: forge.pki.oids.pkcs8ShroudedKeyBag });
      const keyBag = keyBags[forge.pki.oids.pkcs8ShroudedKeyBag];
      
      if (!keyBag || keyBag.length === 0) {
        result.errors.push('No se encontró clave privada en archivo .pfx');
        return result;
      }

      const privateKey = keyBag[0].key;
      if (!privateKey) {
        result.errors.push('Clave privada inválida en archivo .pfx');
        return result;
      }

      result.success = true;
      (result as any).certificate = certificate;
      (result as any).privateKey = privateKey;

    } catch (error) {
      result.errors.push(`Error cargando certificado .pfx: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return result;
  }

  /**
   * Validar certificado digital según RF003
   */
  async validateCertificate(certificate: forge.pki.Certificate, privateKey: forge.pki.PrivateKey): Promise<CertificateValidation> {
    const result: CertificateValidation = {
      isValid: true,
      errors: [],
      warnings: []
    };

    try {
      const now = new Date();
      const validFrom = certificate.validity.notBefore;
      const validTo = certificate.validity.notAfter;

      // Información del certificado
      const certificateInfo: CertificateInfo = {
        issuer: certificate.issuer.getField('CN')?.value || 'Desconocido',
        subject: certificate.subject.getField('CN')?.value || 'Desconocido',
        serialNumber: certificate.serialNumber,
        validFrom,
        validTo,
        isValid: true,
        provider: this.detectCertificateProvider(certificate),
        keySize: this.getKeySize(certificate),
        algorithm: certificate.siginfo ? certificate.siginfo.algorithmOid : 'Desconocido',
        purpose: ['digitalSignature', 'keyEncipherment']
      };

      // Validar vigencia
      if (now < validFrom) {
        result.isValid = false;
        result.errors.push('Certificado aún no es válido');
      }

      if (now > validTo) {
        result.isValid = false;
        result.errors.push('Certificado ha expirado');
      }

      // Calcular días restantes
      const remainingMs = validTo.getTime() - now.getTime();
      const remainingDays = Math.ceil(remainingMs / (1000 * 60 * 60 * 24));
      result.remainingDays = remainingDays;

      // RF003: Advertir 30 días antes del vencimiento
      if (remainingDays <= 30 && remainingDays > 0) {
        result.warnings.push(`Certificado vence en ${remainingDays} días`);
      }

      // Validar tamaño de clave (RF003: RSA-2048)
      if (certificateInfo.keySize < 2048) {
        result.errors.push(`Tamaño de clave insuficiente: ${certificateInfo.keySize} bits (mínimo 2048)`);
        result.isValid = false;
      }

      // Validar proveedor soportado (RF003)
      if (certificateInfo.provider === CertificateProvider.E_CERT ||
          certificateInfo.provider === CertificateProvider.ACCEPT ||
          certificateInfo.provider === CertificateProvider.CAMERFIRMA) {
        // Proveedor soportado
      } else {
        result.warnings.push(`Proveedor de certificado no reconocido: ${certificateInfo.issuer}`);
      }

      // Validar que la clave privada corresponde al certificado
      if (!this.validateKeyPair(certificate, privateKey)) {
        result.isValid = false;
        result.errors.push('La clave privada no corresponde al certificado');
      }

      certificateInfo.isValid = result.isValid;
      result.certificateInfo = certificateInfo;

    } catch (error) {
      result.isValid = false;
      result.errors.push(`Error validando certificado: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return result;
  }

  /**
   * Detectar proveedor del certificado
   */
  private detectCertificateProvider(certificate: forge.pki.Certificate): CertificateProvider {
    const issuer = certificate.issuer.getField('CN')?.value?.toLowerCase() || '';
    
    if (issuer.includes('e-cert')) {
      return CertificateProvider.E_CERT;
    } else if (issuer.includes('accept')) {
      return CertificateProvider.ACCEPT;
    } else if (issuer.includes('camerfirma')) {
      return CertificateProvider.CAMERFIRMA;
    }
    
    // Por defecto asumimos E-Cert (más común en Chile)
    return CertificateProvider.E_CERT;
  }

  /**
   * Obtener tamaño de clave del certificado
   */
  private getKeySize(certificate: forge.pki.Certificate): number {
    try {
      const publicKey = certificate.publicKey as forge.pki.rsa.PublicKey;
      if (publicKey && publicKey.n) {
        return publicKey.n.bitLength();
      }
    } catch {
      // Si no se puede obtener, asumir mínimo
    }
    return 0;
  }

  /**
   * Validar que clave privada corresponde al certificado
   */
  private validateKeyPair(certificate: forge.pki.Certificate, privateKey: forge.pki.PrivateKey): boolean {
    try {
      // Crear mensaje de prueba
      const testMessage = 'test-signature-validation';
      const md = forge.md.sha256.create();
      md.update(testMessage, 'utf8');

      // Firmar con clave privada
      const signature = (privateKey as any).sign(md);

      // Verificar con clave pública del certificado
      const publicKey = certificate.publicKey;
      const verified = (publicKey as any).verify(md.digest().bytes(), signature);

      return verified;
    } catch {
      return false;
    }
  }

  /**
   * Preparar XML para firma (agregar IDs necesarios)
   */
  private prepareXmlForSigning(xmlContent: string): string {
    // Agregar ID al elemento raíz si no existe
    if (!xmlContent.includes(' ID=')) {
      const rootElementMatch = xmlContent.match(/<(\w+)([^>]*?)>/);
      if (rootElementMatch) {
        const tagName = rootElementMatch[1];
        const attributes = rootElementMatch[2];
        const newTag = `<${tagName}${attributes} ID="xmldsig-${Date.now()}">`;
        xmlContent = xmlContent.replace(rootElementMatch[0], newTag);
      }
    }
    
    return xmlContent;
  }

  /**
   * Crear firma XML usando xml-crypto
   */
  private async createXmlSignature(
    xmlContent: string,
    privateKey: forge.pki.PrivateKey, 
    certificate: forge.pki.Certificate,
    config: DigitalSignatureConfig
  ): Promise<string | null> {
    try {
      // Convertir clave privada a formato PEM
      const privateKeyPem = forge.pki.privateKeyToPem(privateKey);
      const certificatePem = forge.pki.certificateToPem(certificate);

      // Configurar SignedXml
      const sig = new SignedXml();
      (sig as any).signingKey = privateKeyPem;
      sig.canonicalizationAlgorithm = config.canonicalization;
      
      // Configurar algoritmo de firma según RF003
      if (config.algorithm === 'RSA-SHA256') {
        sig.signatureAlgorithm = 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256';
      } else {
        sig.signatureAlgorithm = 'http://www.w3.org/2000/09/xmldsig#rsa-sha1';
      }

      // Agregar certificado si está configurado
      if (config.includeCertificate) {
        (sig as any).keyInfoProvider = {
          getKeyInfo: () => {
            return `<X509Data><X509Certificate>${certificatePem.replace(/-----BEGIN CERTIFICATE-----|\r|\n|-----END CERTIFICATE-----/g, '')}</X509Certificate></X509Data>`;
          }
        };
      }

      // Parsear XML
      const doc = new DOMParser().parseFromString(xmlContent, 'text/xml');
      
      // Encontrar elemento a firmar (normalmente el raíz)
      const elementsToSign = xpath.select("//*[@ID]", doc) as Node[];
      if (!elementsToSign || !Array.isArray(elementsToSign) || elementsToSign.length === 0) {
        throw new Error('No se encontró elemento con ID para firmar');
      }

      const elementToSign = elementsToSign[0] as Element;
      const idAttribute = elementToSign.getAttribute('ID');

      // Agregar referencia al elemento
      (sig as any).addReference(`//*[@ID="${idAttribute}"]`, ['http://www.w3.org/2000/09/xmldsig#enveloped-signature']);

      // Calcular firma
      sig.computeSignature(xmlContent);

      // Obtener XML firmado
      const signedXml = sig.getSignedXml();
      
      return signedXml;

    } catch (error) {
      console.error('Error creando firma XML:', error);
      return null;
    }
  }

  /**
   * Finalizar resultado con timing
   */
  private finalizeSignatureResult(result: SignatureResult, startTime: number): SignatureResult {
    result.signatureTime = Date.now() - startTime;

    // RF003: Advertir si excede 5 segundos
    if (result.signatureTime > 5000) {
      result.warnings.push(`Firma excedió tiempo objetivo: ${result.signatureTime}ms > 5000ms`);
    }

    return result;
  }

  /**
   * Verificar firma XML existente
   */
  async verifyXmlSignature(signedXmlContent: string): Promise<{
    isValid: boolean;
    certificateInfo?: CertificateInfo;
    errors: string[];
  }> {
    const result = { isValid: false, errors: [] as string[] };

    try {
      const doc = new DOMParser().parseFromString(signedXmlContent, 'text/xml');
      const signatureElements = xpath.select("//*/Signature", doc) as Node[];
      const signature = signatureElements && signatureElements.length > 0 ? signatureElements[0] as Element : null;
      
      if (!signature) {
        result.errors.push('No se encontró elemento Signature en el XML');
        return result;
      }

      const sig = new SignedXml();
      sig.loadSignature(signature);
      
      // Verificar firma
      const isValid = sig.checkSignature(signedXmlContent);
      result.isValid = isValid;

      if (!isValid) {
        result.errors.push('Firma XML inválida');
      }

    } catch (error) {
      result.errors.push(`Error verificando firma XML: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }

    return result;
  }

  /**
   * Obtener información del certificado desde XML firmado
   */
  async getCertificateFromSignedXml(signedXmlContent: string): Promise<CertificateInfo | null> {
    try {
      const doc = new DOMParser().parseFromString(signedXmlContent, 'text/xml');
      const certElements = xpath.select("//*/X509Certificate", doc) as Node[];

      if (!certElements || certElements.length === 0) {
        return null;
      }

      const certData = (certElements[0] as Element).textContent;
      if (!certData) {
        return null;
      }

      // Decodificar certificado
      const certDer = forge.util.decode64(certData);
      const certAsn1 = forge.asn1.fromDer(certDer);
      const certificate = forge.pki.certificateFromAsn1(certAsn1);

      // Extraer información
      const certificateInfo: CertificateInfo = {
        issuer: certificate.issuer.getField('CN')?.value || 'Desconocido',
        subject: certificate.subject.getField('CN')?.value || 'Desconocido',
        serialNumber: certificate.serialNumber,
        validFrom: certificate.validity.notBefore,
        validTo: certificate.validity.notAfter,
        isValid: new Date() <= certificate.validity.notAfter && new Date() >= certificate.validity.notBefore,
        provider: this.detectCertificateProvider(certificate),
        keySize: this.getKeySize(certificate),
        algorithm: certificate.siginfo ? certificate.siginfo.algorithmOid : 'Desconocido',
        purpose: ['digitalSignature', 'keyEncipherment']
      };

      return certificateInfo;

    } catch (error) {
      console.error('Error extrayendo certificado de XML firmado:', error);
      return null;
    }
  }
}

// Singleton instance
export const digitalSigner = new DigitalSigner();
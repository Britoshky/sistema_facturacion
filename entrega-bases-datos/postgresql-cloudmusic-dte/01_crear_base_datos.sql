-- ============================================
-- CLOUDMUSIC DTE - SISTEMA DE FACTURACIÓN ELECTRÓNICA
-- SCRIPT DE CREACIÓN DE BASE DE DATOS POSTGRESQL
-- ============================================
-- Proyecto de Título - Analista Programador
-- Escuela de Informática y Telecomunicaciones - IPLACEX
-- Fecha: Noviembre 2025
-- 9 TABLAS PRINCIPALES SEGÚN INFORME TÉCNICO
-- ============================================

-- Crear base de datos (ejecutar como superusuario postgres)
-- CREATE DATABASE cloudmusic_dte 
--   WITH OWNER = postgres
--        ENCODING = 'UTF8'
--        TABLESPACE = pg_default
--        LC_COLLATE = 'es_CL.UTF-8'
--        LC_CTYPE = 'es_CL.UTF-8'
--        CONNECTION LIMIT = -1;

-- Conectar a la base de datos cloudmusic_dte
-- \c sistema_facturacion_dte;

-- ============================================
-- EXTENSIONES REQUERIDAS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- TABLA 1: USERS - Gestión de usuarios y autenticación
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user', 'contador', 'viewer')),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA 2: COMPANIES - Datos tributarios del SII por empresa
-- ============================================
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rut VARCHAR(12) UNIQUE NOT NULL,
    business_name VARCHAR(200) NOT NULL,
    commercial_name VARCHAR(200),
    economic_activity VARCHAR(200) NOT NULL,
    business_line VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    commune VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    postal_code VARCHAR(10),
    phone VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(255),
    logo_url VARCHAR(500),
    tax_regime VARCHAR(50) DEFAULT 'general',
    sii_activity_code VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA 3: COMPANY_USERS - Asociación N ↔ M entre usuarios y empresas
-- ============================================
CREATE TABLE company_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role_in_company VARCHAR(50) NOT NULL DEFAULT 'user',
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, company_id)
);

-- ============================================
-- TABLA 4: CLIENTS - Cartera de clientes por empresa
-- ============================================
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    rut VARCHAR(12) NOT NULL,
    client_type VARCHAR(20) NOT NULL CHECK (client_type IN ('individual', 'business', 'foreign')),
    business_name VARCHAR(200),
    first_name VARCHAR(100),
    last_name VARCHAR(150),
    business_line VARCHAR(200),
    address TEXT,
    commune VARCHAR(100),
    city VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(255),
    credit_limit DECIMAL(15,2) DEFAULT 0,
    payment_terms INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, rut)
);

-- ============================================
-- TABLA 5: PRODUCTS - Catálogo de productos/servicios
-- ============================================
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    product_type VARCHAR(20) NOT NULL CHECK (product_type IN ('product', 'service', 'asset')),
    unit_price DECIMAL(15,2) NOT NULL DEFAULT 0,
    cost_price DECIMAL(15,2) DEFAULT 0,
    unit_of_measure VARCHAR(20) DEFAULT 'UNIDAD',
    tax_classification VARCHAR(20) DEFAULT 'taxable',
    sii_code VARCHAR(20),
    stock_quantity INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, sku)
);

-- ============================================
-- TABLA 6: CERTIFICATES - Certificados digitales .pfx SII
-- ============================================
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    certificate_name VARCHAR(200) NOT NULL,
    pfx_file BYTEA NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    issuer VARCHAR(200) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    serial_number VARCHAR(100) NOT NULL,
    issued_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    fingerprint VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA 7: FOLIOS - Rangos CAF autorizados por SII
-- ============================================
CREATE TABLE folios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    document_type INTEGER NOT NULL CHECK (document_type IN (33, 34, 39, 41, 46, 52, 56, 61)),
    caf_file TEXT NOT NULL,
    from_folio INTEGER NOT NULL,
    to_folio INTEGER NOT NULL,
    current_folio INTEGER NOT NULL,
    authorization_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    remaining_folios INTEGER GENERATED ALWAYS AS (to_folio - current_folio + 1) STORED,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, document_type, from_folio, to_folio)
);

-- ============================================
-- TABLA 8: DOCUMENTS - Facturas, boletas y notas de crédito
-- ============================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    folio_id UUID NOT NULL REFERENCES folios(id) ON DELETE RESTRICT,
    document_type INTEGER NOT NULL CHECK (document_type IN (33, 34, 39, 41, 46, 52, 56, 61)),
    folio_number INTEGER NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE,
    reference_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    reference_type INTEGER CHECK (reference_type IN (1, 2, 3)),
    reference_reason VARCHAR(200),
    net_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    exempt_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'CLP',
    exchange_rate DECIMAL(10,4) DEFAULT 1.0000,
    sii_status VARCHAR(20) DEFAULT 'draft',
    track_id VARCHAR(100),
    xml_content TEXT,
    pdf_url VARCHAR(500),
    notes TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, document_type, folio_number)
);

-- ============================================
-- TABLA 9: DOCUMENT_ITEMS - Líneas de detalle de cada DTE
-- ============================================
CREATE TABLE document_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    line_number INTEGER NOT NULL,
    product_code VARCHAR(100),
    product_name VARCHAR(200) NOT NULL,
    description TEXT,
    quantity DECIMAL(10,4) NOT NULL DEFAULT 1,
    unit_price DECIMAL(15,2) NOT NULL,
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    discount_amount DECIMAL(15,2) DEFAULT 0,
    net_amount DECIMAL(15,2) NOT NULL,
    tax_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    exempt_amount DECIMAL(15,2) DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL,
    unit_of_measure VARCHAR(20) DEFAULT 'UNIDAD',
    tax_classification VARCHAR(20) DEFAULT 'taxable',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, line_number)
);

-- ============================================
-- ÍNDICES DE RENDIMIENTO
-- ============================================

-- Índices para users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- Índices para companies
CREATE INDEX idx_companies_rut ON companies(rut);
CREATE INDEX idx_companies_active ON companies(is_active);

-- Índices para company_users
CREATE INDEX idx_company_users_user ON company_users(user_id);
CREATE INDEX idx_company_users_company ON company_users(company_id);

-- Índices para clients
CREATE INDEX idx_clients_company ON clients(company_id);
CREATE INDEX idx_clients_rut ON clients(rut);
CREATE INDEX idx_clients_type ON clients(client_type);

-- Índices para products
CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_type ON products(product_type);

-- Índices para certificates
CREATE INDEX idx_certificates_company ON certificates(company_id);
CREATE INDEX idx_certificates_active ON certificates(is_active);
CREATE INDEX idx_certificates_expiry ON certificates(expiry_date);

-- Índices para folios
CREATE INDEX idx_folios_company ON folios(company_id);
CREATE INDEX idx_folios_doc_type ON folios(document_type);
CREATE INDEX idx_folios_active ON folios(is_active);

-- Índices para documents
CREATE INDEX idx_documents_company ON documents(company_id);
CREATE INDEX idx_documents_client ON documents(client_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_folio ON documents(folio_number);
CREATE INDEX idx_documents_issue_date ON documents(issue_date);
CREATE INDEX idx_documents_status ON documents(sii_status);

-- Índices para document_items
CREATE INDEX idx_document_items_document ON document_items(document_id);
CREATE INDEX idx_document_items_product ON document_items(product_id);

-- ============================================
-- TRIGGERS PARA UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar triggers a tablas con updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_certificates_updated_at BEFORE UPDATE ON certificates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_folios_updated_at BEFORE UPDATE ON folios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TRIGGERS DE NEGOCIO
-- ============================================

-- Trigger para actualizar folio actual
CREATE OR REPLACE FUNCTION increment_current_folio()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE folios 
    SET current_folio = current_folio + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.folio_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER increment_folio_after_document 
    AFTER INSERT ON documents
    FOR EACH ROW EXECUTE FUNCTION increment_current_folio();

-- Trigger para validar RUT chileno
CREATE OR REPLACE FUNCTION validate_chilean_rut()
RETURNS TRIGGER AS $$
DECLARE
    rut_clean VARCHAR(12);
    rut_number INTEGER;
    rut_dv CHAR(1);
    calculated_dv CHAR(1);
    sum_total INTEGER := 0;
    multiplier INTEGER := 2;
    remainder INTEGER;
    i INTEGER;
BEGIN
    -- Limpiar RUT (remover puntos y guiones)
    rut_clean := REPLACE(REPLACE(NEW.rut, '.', ''), '-', '');
    
    -- Validar formato básico
    IF LENGTH(rut_clean) < 8 OR LENGTH(rut_clean) > 9 THEN
        RAISE EXCEPTION 'RUT debe tener entre 8 y 9 caracteres';
    END IF;
    
    -- Separar número y dígito verificador
    rut_number := CAST(SUBSTRING(rut_clean, 1, LENGTH(rut_clean)-1) AS INTEGER);
    rut_dv := UPPER(SUBSTRING(rut_clean, LENGTH(rut_clean), 1));
    
    -- Calcular dígito verificador
    FOR i IN REVERSE LENGTH(rut_number::TEXT)..1 LOOP
        sum_total := sum_total + (CAST(SUBSTRING(rut_number::TEXT, i, 1) AS INTEGER) * multiplier);
        multiplier := multiplier + 1;
        IF multiplier > 7 THEN
            multiplier := 2;
        END IF;
    END LOOP;
    
    remainder := sum_total % 11;
    
    IF remainder = 0 THEN
        calculated_dv := '0';
    ELSIF remainder = 1 THEN
        calculated_dv := 'K';
    ELSE
        calculated_dv := CAST(11 - remainder AS CHAR(1));
    END IF;
    
    -- Validar dígito verificador
    IF rut_dv != calculated_dv THEN
        RAISE EXCEPTION 'RUT % no es válido. DV calculado: %, DV ingresado: %', NEW.rut, calculated_dv, rut_dv;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar validación RUT
CREATE TRIGGER validate_company_rut BEFORE INSERT OR UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION validate_chilean_rut();

CREATE TRIGGER validate_client_rut BEFORE INSERT OR UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION validate_chilean_rut();

-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Vista de documentos con información completa
CREATE VIEW documents_summary AS
SELECT 
    d.id,
    d.document_type,
    d.folio_number,
    d.issue_date,
    d.total_amount,
    d.sii_status,
    c.business_name as company_name,
    cl.business_name as client_name,
    u.first_name || ' ' || u.last_name as created_by_name,
    COUNT(di.id) as line_items
FROM documents d
JOIN companies c ON d.company_id = c.id
LEFT JOIN clients cl ON d.client_id = cl.id
LEFT JOIN users u ON d.created_by = u.id
LEFT JOIN document_items di ON d.id = di.document_id
GROUP BY d.id, c.business_name, cl.business_name, u.first_name, u.last_name;

-- Vista de estado de folios
CREATE VIEW folios_status AS
SELECT 
    f.id,
    c.business_name,
    f.document_type,
    f.from_folio,
    f.to_folio,
    f.current_folio,
    f.remaining_folios,
    f.expiry_date,
    CASE 
        WHEN f.remaining_folios <= 0 THEN 'AGOTADO'
        WHEN f.remaining_folios <= 5 THEN 'CRÍTICO'
        WHEN f.remaining_folios <= 20 THEN 'BAJO'
        ELSE 'NORMAL'
    END as status_level
FROM folios f
JOIN companies c ON f.company_id = c.id
WHERE f.is_active = TRUE;

-- ============================================
-- FUNCIÓN DE INICIALIZACIÓN DE DATOS
-- ============================================

-- Función para crear usuario administrador inicial
CREATE OR REPLACE FUNCTION create_admin_user(
    p_email VARCHAR(255),
    p_password VARCHAR(255),
    p_first_name VARCHAR(100),
    p_last_name VARCHAR(150)
)
RETURNS UUID AS $$
DECLARE
    user_id UUID;
BEGIN
    INSERT INTO users (email, password_hash, first_name, last_name, role)
    VALUES (
        p_email,
        crypt(p_password, gen_salt('bf')),
        p_first_name,
        p_last_name,
        'admin'
    )
    RETURNING id INTO user_id;
    
    RETURN user_id;
END;
$$ language 'plpgsql';

-- ============================================
-- COMENTARIOS EN TABLAS
-- ============================================

COMMENT ON TABLE users IS 'Tabla principal de usuarios del sistema con autenticación';
COMMENT ON TABLE companies IS 'Empresas emisoras de documentos tributarios electrónicos';
COMMENT ON TABLE company_users IS 'Relación muchos a muchos entre usuarios y empresas';
COMMENT ON TABLE clients IS 'Cartera de clientes por empresa emisora';
COMMENT ON TABLE products IS 'Catálogo de productos y servicios por empresa';
COMMENT ON TABLE certificates IS 'Certificados digitales para firma electrónica SII';
COMMENT ON TABLE folios IS 'Rangos de folios CAF autorizados por el SII';
COMMENT ON TABLE documents IS 'Documentos tributarios electrónicos (DTE)';
COMMENT ON TABLE document_items IS 'Líneas de detalle de cada documento DTE';

-- ============================================
-- SCRIPT COMPLETADO
-- ============================================

SELECT 'Base de datos CloudMusic DTE creada exitosamente con 9 tablas principales' as resultado;
SELECT 'Tablas creadas:' as info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
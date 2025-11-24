-- ============================================
-- CLOUDMUSIC DTE - SISTEMA DE FACTURACIÓN ELECTRÓNICA
-- SCRIPT DE CARGA DE DATOS DE PRUEBA - POSTGRESQL
-- ============================================
-- Proyecto de Título - Analista Programador
-- Escuela de Informática y Telecomunicaciones - IPLACEX
-- Fecha: Noviembre 2025
-- DATOS PARA LAS 9 TABLAS PRINCIPALES
-- ============================================

-- Conectar a la base de datos
-- \c sistema_facturacion_dte;

-- Iniciando carga de datos de prueba para 9 tablas principales...

-- ============================================
-- TABLA 1: USERS - Datos de usuarios
-- ============================================
-- CREDENCIALES DE ACCESO:
-- superadmin@cloudmusic.cl → superadmin123
-- admin@cloudmusic.cl → admin123  
-- contador@cloudmusic.cl → contador123
-- user@cloudmusic.cl → user123
-- viewer@empresa2.cl → viewer123

INSERT INTO users (id, email, password_hash, first_name, last_name, role, is_active) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'superadmin@cloudmusic.cl', '$2b$12$FFGKZPovNw1NdJEx39wTz.ceOAhAovOE4Ma4LfRP8zCfq2IqzzGVu', 'Sistema', 'SuperAdmin', 'super_admin', TRUE),
('550e8400-e29b-41d4-a716-446655440001', 'admin@cloudmusic.cl', '$2b$12$M9k5sLKgwspGaskIOBUxRe.fDniM0ELcMVVPLawEuVzKi48UImTUm', 'Carlos', 'Administrador', 'admin', TRUE),
('550e8400-e29b-41d4-a716-446655440002', 'contador@cloudmusic.cl', '$2b$12$fIQOtZNTx1d7e7/BCMAe2Oifqgj2nV7/hjNLY1p4sEGw2STsl2hwe', 'María', 'González', 'contador', TRUE),
('550e8400-e29b-41d4-a716-446655440003', 'user@cloudmusic.cl', '$2b$12$B1569Um.haZigYRZapvj/.2CV7t14pGmL96Uzph5u5llMrGwQWUVy', 'Juan', 'Pérez', 'user', TRUE),
('550e8400-e29b-41d4-a716-446655440004', 'viewer@empresa2.cl', '$2b$12$NziLLbHQovZ/bRt07D/bFe1CyAtjor7W0tuD5twmAhcK328due0qe', 'Ana', 'López', 'viewer', TRUE);

-- ============================================
-- TABLA 2: COMPANIES - Empresas emisoras
-- ============================================

INSERT INTO companies (id, rut, business_name, commercial_name, economic_activity, business_line, address, commune, city, region, phone, email, sii_activity_code) VALUES
('660e8400-e29b-41d4-a716-446655440001', '78218659-0', 'CloudMusic SpA', 'CloudMusic', 'Desarrollo de Software y Servicios Tecnológicos', 'Desarrollo Software', 'Av. Providencia 1208, Piso 12', 'Providencia', 'Santiago', 'Metropolitana', '+56 2 2345 6789', 'contacto@cloudmusic.cl', '620200'),
('660e8400-e29b-41d4-a716-446655440002', '78218792-9', 'Subli SpA', 'Subli', 'Consultoría en Tecnologías de la Información', 'Consultoría TI', 'Los Leones 456, Of 302', 'Providencia', 'Santiago', 'Metropolitana', '+56 2 2987 6543', 'info@subli.cl', '620100'),
('660e8400-e29b-41d4-a716-446655440003', '78260477-5', 'Home Electric SA', 'Home Electric', 'Comercio de Equipos Eléctricos y Electrónicos', 'Retail Eléctrico', 'Av. Las Condes 789', 'Las Condes', 'Santiago', 'Metropolitana', '+56 2 2654 9876', 'contacto@homeelectric.cl', '472000');

-- ============================================
-- TABLA 3: COMPANY_USERS - Relaciones usuarios-empresas
-- ============================================

INSERT INTO company_users (user_id, company_id, role_in_company, permissions) VALUES
-- SuperAdmin con acceso a TODAS las empresas
('550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'super_admin', '{"all": true, "system": true, "manage_users": true, "cross_company": true}'),
('550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440002', 'super_admin', '{"all": true, "system": true, "manage_users": true, "cross_company": true}'),
('550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440003', 'super_admin', '{"all": true, "system": true, "manage_users": true, "cross_company": true}'),
-- Usuarios específicos por empresa
('550e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 'admin', '{"all": true}'),
('550e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', 'contador', '{"documents": true, "reports": true}'),
('550e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001', 'user', '{"documents": true}'),
('550e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440002', 'admin', '{"all": true}'),
('550e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440003', 'viewer', '{"reports": true}');

-- ============================================
-- TABLA 4: CLIENTS - Cartera de clientes
-- ============================================

INSERT INTO clients (id, company_id, rut, client_type, business_name, first_name, last_name, business_line, address, commune, city, phone, email, credit_limit, payment_terms) VALUES
('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', '19001626-9', 'business', 'Empresa Demo S.A.', NULL, NULL, 'Comercio General', 'Av. Libertador 456', 'Santiago', 'Santiago', '+56 2 2111 2222', 'contacto@empresademo.cl', 5000000, 30),
('770e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', '18519680-1', 'business', 'Retail Solutions Ltda.', NULL, NULL, 'Retail y Comercio', 'Los Leones 789', 'Providencia', 'Santiago', '+56 2 2333 4444', 'ventas@retailsol.cl', 3000000, 15),
('770e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001', '16256598-2', 'individual', NULL, 'Juan Carlos', 'Pérez', 'Persona Natural', 'Las Flores 123', 'Ñuñoa', 'Santiago', '+56 9 8765 4321', 'juan.perez@email.com', 500000, 0),
('770e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440001', '66666666-6', 'individual', 'Cliente Anónimo', 'Consumidor', 'Final', 'Consumidor Final', NULL, NULL, NULL, NULL, NULL, 0, 0),
('770e8400-e29b-41d4-a716-446655440005', '660e8400-e29b-41d4-a716-446655440002', '16531285-6', 'business', 'Banco Desarrollo SA', NULL, NULL, 'Servicios Financieros', 'Av. Apoquindo 1500', 'Las Condes', 'Santiago', '+56 2 2567 8900', 'corporativo@bancodesarrollo.cl', 10000000, 45),
('770e8400-e29b-41d4-a716-446655440006', '660e8400-e29b-41d4-a716-446655440003', '78218792-9', 'business', 'Supermercados Chile SA', NULL, NULL, 'Retail Alimentario', 'Av. Kennedy 2000', 'Vitacura', 'Santiago', '+56 2 2789 0123', 'compras@superchile.cl', 8000000, 60),
('770e8400-e29b-41d4-a716-446655440007', '660e8400-e29b-41d4-a716-446655440003', '78260477-5', 'business', 'Restaurante Gourmet Ltda', NULL, NULL, 'Gastronomía', 'Av. Vitacura 3456', 'Vitacura', 'Santiago', '+56 2 2456 7890', 'administracion@gourmet.cl', 2000000, 30);

-- ============================================
-- TABLA 5: PRODUCTS - Catálogo de productos/servicios
-- ============================================

INSERT INTO products (id, company_id, sku, name, description, product_type, unit_price, cost_price, unit_of_measure, tax_classification, sii_code) VALUES
('880e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 'SW-001', 'Sistema DTE CloudMusic Pro', 'Licencia anual sistema facturación electrónica con IA integrada', 'service', 2500000.00, 800000.00, 'UNIDAD', 'taxable', '81112000'),
('880e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', 'CONS-001', 'Consultoría DTE Implementación', 'Implementación sistema DTE - Hora de consultoría especializada', 'service', 150000.00, 50000.00, 'HORA', 'taxable', '81111500'),
('880e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001', 'CAP-001', 'Curso Facturación Electrónica', 'Capacitación DTE para 1 persona - 16 horas académicas', 'service', 350000.00, 100000.00, 'CURSO', 'taxable', '85421000'),
('880e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440001', 'SOP-001', 'Soporte Técnico Mensual', 'Soporte técnico CloudMusic DTE mensual 24/7', 'service', 85000.00, 30000.00, 'MES', 'taxable', '81112000'),
('880e8400-e29b-41d4-a716-446655440005', '660e8400-e29b-41d4-a716-446655440002', 'WEB-001', 'Desarrollo Plataforma E-Commerce', 'Plataforma completa con integración bancaria y DTE automático', 'service', 8500000.00, 3000000.00, 'PROYECTO', 'taxable', '62010000'),
('880e8400-e29b-41d4-a716-446655440006', '660e8400-e29b-41d4-a716-446655440002', 'APP-001', 'Aplicación Móvil Empresarial', 'App nativa iOS/Android con sincronización cloud', 'service', 4200000.00, 1500000.00, 'PROYECTO', 'taxable', '62010000'),
('880e8400-e29b-41d4-a716-446655440007', '660e8400-e29b-41d4-a716-446655440003', 'MKT-001', 'Campaña Marketing Digital Integral', 'Campaña digital multicanal mensual completa', 'service', 1200000.00, 400000.00, 'MES', 'taxable', '73200000');

-- ============================================
-- TABLA 6: CERTIFICATES - Certificados digitales
-- ============================================

INSERT INTO certificates (id, company_id, certificate_name, pfx_file, password_hash, issuer, subject, serial_number, issued_date, expiry_date, fingerprint, is_default) VALUES
('990e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 'CloudMusic SpA - Certificado E-Sign 2025', decode('504b0304140000000800', 'hex'), '$2b$12$uaqOpVpTgYAEMwFd5dtDnuVc8ApIoRyG4i3JIL/UadQvoZUo9Y.HS', 'E-Sign S.A.', 'CN=CloudMusic SpA, O=CloudMusic SpA, C=CL', '1234567890ABCDEF', '2024-03-15', '2025-08-24', 'SHA1:A1B2C3D4E5F6789012345678901234567890ABCD', TRUE),
('990e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440002', 'Subli SpA - Certificado AC 2025', decode('504b0304140000000801', 'hex'), '$2b$12$C1P.9Mfy5PucdP3Q3bOtI.cHGLa02JnHwsMq0nNbYqCol8a/VnFRG', 'Accept S.A.', 'CN=Subli SpA, O=Subli SpA, C=CL', '2345678901BCDEF0', '2024-01-10', '2025-06-15', 'SHA1:B2C3D4E5F6789012345678901234567890ABCDE1', TRUE),
('990e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440003', 'Home Electric SA - Certificado Digital 2025', decode('504b0304140000000802', 'hex'), '$2b$12$.i6iRvPq31oGMzW.xTaPgeDURL3cxSHADICbqvOzBlE0YcOb4qbym', 'CertiSign Chile', 'CN=Home Electric SA, O=Home Electric SA, C=CL', '3456789012CDEF01', '2024-02-20', '2025-09-30', 'SHA1:C3D4E5F6789012345678901234567890ABCDE12F', TRUE);

-- ============================================
-- TABLA 7: FOLIOS - Rangos CAF autorizados
-- ============================================

INSERT INTO folios (id, company_id, document_type, caf_file, from_folio, to_folio, current_folio, authorization_date, expiry_date) VALUES
-- CloudMusic SpA - Folios
('aa0e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', 33, '<CAF version="1.0"><DA><RE>78218659-0</RE><TD>33</TD><RNG><D>1</D><H>20</H></RNG><FA>2024-03-15</FA><RSAPK><M>...</M><E>65537</E></RSAPK><IDK>12345</IDK></DA><FRMA algoritmo="SHA1withRSA">...</FRMA></CAF>', 1, 20, 4, '2024-03-15', '2025-12-31'),
('aa0e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', 39, '<CAF version="1.0"><DA><RE>78218659-0</RE><TD>39</TD><RNG><D>1</D><H>50</H></RNG><FA>2024-03-15</FA><RSAPK><M>...</M><E>65537</E></RSAPK><IDK>12346</IDK></DA><FRMA algoritmo="SHA1withRSA">...</FRMA></CAF>', 1, 50, 2, '2024-03-15', '2025-12-31'),
('aa0e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001', 61, '<CAF version="1.0"><DA><RE>78218659-0</RE><TD>61</TD><RNG><D>1</D><H>20</H></RNG><FA>2024-03-15</FA><RSAPK><M>...</M><E>65537</E></RSAPK><IDK>12347</IDK></DA><FRMA algoritmo="SHA1withRSA">...</FRMA></CAF>', 1, 20, 1, '2024-03-15', '2025-12-31'),
-- Subli SpA - Folios
('aa0e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440002', 33, '<CAF version="1.0"><DA><RE>78218792-9</RE><TD>33</TD><RNG><D>1</D><H>30</H></RNG><FA>2024-01-10</FA><RSAPK><M>...</M><E>65537</E></RSAPK><IDK>23456</IDK></DA><FRMA algoritmo="SHA1withRSA">...</FRMA></CAF>', 1, 30, 2, '2024-01-10', '2025-12-31'),
-- Home Electric SA - Folios
('aa0e8400-e29b-41d4-a716-446655440005', '660e8400-e29b-41d4-a716-446655440003', 33, '<CAF version="1.0"><DA><RE>78260477-5</RE><TD>33</TD><RNG><D>1</D><H>25</H></RNG><FA>2024-02-20</FA><RSAPK><M>...</M><E>65537</E></RSAPK><IDK>34567</IDK></DA><FRMA algoritmo="SHA1withRSA">...</FRMA></CAF>', 1, 25, 2, '2024-02-20', '2025-12-31');

-- ============================================
-- TABLA 8: DOCUMENTS - Documentos DTE
-- ============================================

INSERT INTO documents (id, company_id, client_id, folio_id, document_type, folio_number, issue_date, due_date, net_amount, tax_amount, total_amount, sii_status, track_id, created_by) VALUES
-- CloudMusic SpA - Documentos
('bb0e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 33, 1, '2025-11-15', '2025-12-15', 2100840.00, 399160.00, 2500000.00, 'ACEPTADO', 'TRK-2025-001-CloudMusic', '550e8400-e29b-41d4-a716-446655440001'),
('bb0e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440002', 'aa0e8400-e29b-41d4-a716-446655440001', 33, 2, '2025-11-16', '2025-12-01', 252101.00, 47899.00, 300000.00, 'ACEPTADO', 'TRK-2025-002-CloudMusic', '550e8400-e29b-41d4-a716-446655440001'),
('bb0e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440003', 'aa0e8400-e29b-41d4-a716-446655440001', 33, 3, '2025-11-17', '2025-12-17', 71429.00, 13571.00, 85000.00, 'ENVIADO', 'TRK-2025-003-CloudMusic', '550e8400-e29b-41d4-a716-446655440002'),
('bb0e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440001', '770e8400-e29b-41d4-a716-446655440004', 'aa0e8400-e29b-41d4-a716-446655440002', 39, 1, '2025-11-17', NULL, 294118.00, 55882.00, 350000.00, 'ACEPTADO', 'TRK-2025-004-CloudMusic-BOL', '550e8400-e29b-41d4-a716-446655440001'),
-- Subli SpA - Documentos
('bb0e8400-e29b-41d4-a716-446655440005', '660e8400-e29b-41d4-a716-446655440002', '770e8400-e29b-41d4-a716-446655440005', 'aa0e8400-e29b-41d4-a716-446655440004', 33, 1, '2025-11-10', '2025-12-10', 7142857.00, 1357143.00, 8500000.00, 'ACEPTADO', 'TRK-2025-005-Subli', '550e8400-e29b-41d4-a716-446655440001'),
-- Home Electric SA - Documentos
('bb0e8400-e29b-41d4-a716-446655440006', '660e8400-e29b-41d4-a716-446655440003', '770e8400-e29b-41d4-a716-446655440006', 'aa0e8400-e29b-41d4-a716-446655440005', 33, 1, '2025-11-05', '2025-12-05', 1008403.00, 191597.00, 1200000.00, 'ACEPTADO', 'TRK-2025-006-HomeElectric', '550e8400-e29b-41d4-a716-446655440004');

-- ============================================
-- TABLA 9: DOCUMENT_ITEMS - Líneas de detalle
-- ============================================

INSERT INTO document_items (document_id, product_id, line_number, product_code, product_name, description, quantity, unit_price, net_amount, tax_amount, total_amount) VALUES
-- Documento 1: Sistema DTE CloudMusic Pro
('bb0e8400-e29b-41d4-a716-446655440001', '880e8400-e29b-41d4-a716-446655440001', 1, 'SW-001', 'Sistema DTE CloudMusic Pro', 'Licencia anual sistema facturación electrónica con IA integrada', 1.0000, 2500000.00, 2100840.00, 399160.00, 2500000.00),

-- Documento 2: Consultoría DTE (2 horas)
('bb0e8400-e29b-41d4-a716-446655440002', '880e8400-e29b-41d4-a716-446655440002', 1, 'CONS-001', 'Consultoría DTE Implementación', 'Implementación sistema DTE - 2 horas de consultoría especializada', 2.0000, 150000.00, 252101.00, 47899.00, 300000.00),

-- Documento 3: Soporte Técnico
('bb0e8400-e29b-41d4-a716-446655440003', '880e8400-e29b-41d4-a716-446655440003', 1, 'SOP-001', 'Soporte Técnico Mensual', 'Soporte técnico CloudMusic DTE - Noviembre 2025', 1.0000, 85000.00, 71429.00, 13571.00, 85000.00),

-- Documento 4: Curso Capacitación (Boleta)
('bb0e8400-e29b-41d4-a716-446655440004', '880e8400-e29b-41d4-a716-446655440004', 1, 'CAP-001', 'Curso Facturación Electrónica', 'Capacitación DTE para 1 persona - 16 horas académicas', 1.0000, 350000.00, 294118.00, 55882.00, 350000.00),

-- Documento 5: Desarrollo E-Commerce
('bb0e8400-e29b-41d4-a716-446655440005', '880e8400-e29b-41d4-a716-446655440005', 1, 'WEB-001', 'Desarrollo Plataforma E-Commerce', 'Plataforma completa con integración bancaria y DTE automático', 1.0000, 8500000.00, 7142857.00, 1357143.00, 8500000.00),

-- Documento 6: Campaña Marketing Digital
('bb0e8400-e29b-41d4-a716-446655440006', '880e8400-e29b-41d4-a716-446655440007', 1, 'MKT-001', 'Campaña Marketing Digital Integral', 'Campaña digital multicanal - Diciembre 2025', 1.0000, 1200000.00, 1008403.00, 191597.00, 1200000.00);

-- ============================================
-- VERIFICACIÓN DE DATOS CARGADOS
-- ============================================

-- Verificando datos cargados...

SELECT 'RESUMEN DE DATOS CARGADOS:' as info;

SELECT 'Tabla 1 - USERS:' as tabla, count(*) as registros FROM users
UNION ALL
SELECT 'Tabla 2 - COMPANIES:', count(*) FROM companies
UNION ALL
SELECT 'Tabla 3 - COMPANY_USERS:', count(*) FROM company_users
UNION ALL
SELECT 'Tabla 4 - CLIENTS:', count(*) FROM clients
UNION ALL
SELECT 'Tabla 5 - PRODUCTS:', count(*) FROM products
UNION ALL
SELECT 'Tabla 6 - CERTIFICATES:', count(*) FROM certificates
UNION ALL
SELECT 'Tabla 7 - FOLIOS:', count(*) FROM folios
UNION ALL
SELECT 'Tabla 8 - DOCUMENTS:', count(*) FROM documents
UNION ALL
SELECT 'Tabla 9 - DOCUMENT_ITEMS:', count(*) FROM document_items;

-- Verificando integridad relacional...

-- Test de integridad: Documentos con sus detalles
SELECT 
    d.document_type,
    d.folio_number,
    d.total_amount,
    COUNT(di.id) as lineas_detalle
FROM documents d
LEFT JOIN document_items di ON d.id = di.document_id
GROUP BY d.id, d.document_type, d.folio_number, d.total_amount
ORDER BY d.document_type, d.folio_number;

-- Datos de prueba cargados exitosamente para las 9 tablas principales!
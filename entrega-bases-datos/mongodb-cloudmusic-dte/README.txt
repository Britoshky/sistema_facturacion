==================================================================
               PROYECTO CLOUDMUSIC DTE - BASE DE DATOS NOSQL
                          MONGODB MODELO DOCUMENTAL
==================================================================

INFORMACIÓN DEL PROYECTO
------------------------
Nombre: CloudMusic DTE - Sistema de Facturación Electrónica
Tipo de Base de Datos: NoSQL - MongoDB (Modelo Documental)
Versión MongoDB Requerida: 7.0 o superior
Desarrollado por: Analista Programador IPLACEX
Fecha: Noviembre 2025
Institución: IPLACEX
Asignatura: Proyecto de Título

DESCRIPCIÓN GENERAL
-------------------
Esta implementación utiliza MongoDB como base de datos NoSQL orientada a documentos
para el sistema CloudMusic DTE. Se enfoca en las 5 colecciones principales definidas
en el informe técnico: auditoría, inteligencia artificial, eventos en tiempo real,
respuestas del SII y sesiones de chat.

ESTRUCTURA DE COLECCIONES PRINCIPALES (5) - SEGÚN INFORME
----------------------------------------------------------

1. AI_DOCUMENT_ANALYSIS (ai_document_analysis.json)
   - Análisis tributarios generados con IA local Ollama Llama 3.2 3B
   - Insights de cumplimiento, detección de anomalías y validaciones
   - Resultados de procesamiento con confianza y recomendaciones

2. CHAT_SESSIONS (chat_sessions.json)
   - Historial conversacional con asistente inteligente IA
   - Sesiones de soporte técnico y consultas tributarias
   - Interacciones usuario-IA con contexto y metadatos

3. WEBSOCKET_EVENTS (websocket_events.json)
   - Eventos en tiempo real del sistema CloudMusic DTE
   - Notificaciones push, estados de documentos y actividad usuario
   - Comunicación bidireccional para interfaces reactivas

4. SII_RESPONSES (sii_responses.json)
   - Estados de recepción y validación del SII
   - TrackIDs, respuestas SOAP y historial de estados DTE
   - Trazabilidad completa de comunicaciones con Servicio Impuestos Internos

5. AUDIT_TRAIL (audit_trail.json)
   - Auditoría completa de acciones del usuario
   - Registro de operaciones DTE, login/logout y cambios críticos
   - Cumplimiento normativo y trazabilidad de seguridad

JUSTIFICACIÓN TÉCNICA MONGODB VS POSTGRESQL
--------------------------------------------

✅ POSTGRESQL 16 (OLTP - Datos Estructurados)
   - Tablas relacionales con integridad referencial
   - Transacciones ACID para folios, certificados y documentos
   - Consultas SQL complejas con JOIN y constraints
   - 9 tablas principales normalizadas hasta 3FN

✅ MONGODB 7.0 (Analytics - Datos No Estructurados)  
   - Flexibilidad documental para eventos y respuestas dinámicas
   - Escalabilidad horizontal con sharding y replicación
   - Consultas rápidas en JSON anidado sin esquema rígido
   - Almacenamiento eficiente de logs, auditoría e IA

ARQUITECTURA HÍBRIDA CLOUDMUSIC DTE
-----------------------------------

[Frontend Next.js 15]
        │
        ▼
[Backend Node.js + TypeScript]
        │                    │
        ▼                    ▼
[PostgreSQL 16]    [MongoDB 7.0]    [Redis Pub/Sub]    [Python IA]
• users            • ai_analysis      • WebSockets      • Ollama 3.2 3B  
• companies        • chat_sessions    • Events          • FastAPI
• clients          • websocket_events • Notifications   • Analytics
• products         • sii_responses
• certificates     • audit_trail
• folios
• documents
• document_items

INSTALACIÓN Y CONFIGURACIÓN
----------------------------

PASO 1: Instalar MongoDB 7.0
-----------------------------
# Windows
Descargar desde: https://www.mongodb.com/try/download/community
Seguir wizard de instalación

# Ubuntu/Debian
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# Docker Compose (Recomendado)
docker run --name mongodb-cloudmusic-dte -p 27017:27017 -d mongo:7.0

PASO 2: Iniciar MongoDB
------------------------
# Servicio Windows
net start MongoDB

# Linux
sudo systemctl start mongod
sudo systemctl enable mongod

# Docker
docker start mongodb-cloudmusic-dte

PASO 3: Crear Base de Datos y Cargar Colecciones
------------------------------------------------
# Conectar a MongoDB
mongosh

# Crear base de datos
use cloudmusic_dte

# Importar las 5 colecciones principales
mongoimport --db cloudmusic_dte --collection ai_document_analysis --file ai_document_analysis.json --jsonArray
mongoimport --db cloudmusic_dte --collection chat_sessions --file chat_sessions.json --jsonArray
mongoimport --db cloudmusic_dte --collection websocket_events --file websocket_events.json --jsonArray
mongoimport --db cloudmusic_dte --collection sii_responses --file sii_responses.json --jsonArray
mongoimport --db cloudmusic_dte --collection audit_trail --file audit_trail.json --jsonArray

PASO 4: Crear Índices para Optimización
----------------------------------------
# Conectar a la base de datos
mongosh cloudmusic_dte

# Índices para AI Document Analysis
db.ai_document_analysis.createIndex({ "document_id": 1 })
db.ai_document_analysis.createIndex({ "company_id": 1 })
db.ai_document_analysis.createIndex({ "analysis_timestamp": -1 })
db.ai_document_analysis.createIndex({ "analysis_type": 1 })
db.ai_document_analysis.createIndex({ "analysis_results.compliance_score": -1 })

# Índices para Chat Sessions
db.chat_sessions.createIndex({ "user_id": 1 })
db.chat_sessions.createIndex({ "company_id": 1 })
db.chat_sessions.createIndex({ "session_start": -1 })
db.chat_sessions.createIndex({ "is_active": 1 })

# Índices para WebSocket Events
db.websocket_events.createIndex({ "timestamp": -1 })
db.websocket_events.createIndex({ "user_id": 1 })
db.websocket_events.createIndex({ "company_id": 1 })
db.websocket_events.createIndex({ "event_type": 1 })
db.websocket_events.createIndex({ "session_id": 1 })

# Índices para SII Responses
db.sii_responses.createIndex({ "track_id": 1 }, { unique: true })
db.sii_responses.createIndex({ "document_id": 1 })
db.sii_responses.createIndex({ "company_id": 1 })
db.sii_responses.createIndex({ "current_status": 1 })
db.sii_responses.createIndex({ "submission_timestamp": -1 })

# Índices para Audit Trail
db.audit_trail.createIndex({ "timestamp": -1 })
db.audit_trail.createIndex({ "user_id": 1 })
db.audit_trail.createIndex({ "company_id": 1 })
db.audit_trail.createIndex({ "action": 1 })
db.audit_trail.createIndex({ "module": 1 })

CONSULTAS DE EJEMPLO POR COLECCIÓN
----------------------------------

1. ANÁLISIS IA - Documentos con alto riesgo tributario:
   db.ai_document_analysis.find({ 
     "analysis_results.risk_level": "high" 
   }).sort({ "analysis_timestamp": -1 })

2. CHAT SESSIONS - Sesiones activas por usuario:
   db.chat_sessions.find({ 
     "user_id": "550e8400-e29b-41d4-a716-446655440001",
     "is_active": true 
   })

3. WEBSOCKET EVENTS - Eventos de login último mes:
   db.websocket_events.find({
     "event_type": "user_login",
     "timestamp": { $gte: ISODate("2025-10-19T00:00:00.000Z") }
   }).sort({ "timestamp": -1 })

4. SII RESPONSES - Documentos pendientes de validación:
   db.sii_responses.find({ 
     "current_status": { $in: ["ENVIADO", "RECIBIDO"] }
   })

5. AUDIT TRAIL - Auditoría de creación de documentos:
   db.audit_trail.find({
     "action": "create_document",
     "timestamp": { $gte: ISODate("2025-11-19T00:00:00.000Z") }
   }).sort({ "timestamp": -1 })

VALIDACIÓN DE DATOS
-------------------

# Verificar cantidad de documentos por colección
db.ai_document_analysis.countDocuments()  // Debe retornar: 3
db.chat_sessions.countDocuments()         // Debe retornar: 3  
db.websocket_events.countDocuments()      // Debe retornar: 7
db.sii_responses.countDocuments()         // Debe retornar: 3
db.audit_trail.countDocuments()          // Debe retornar: 10

CONTACTO Y SOPORTE
------------------
Para consultas sobre esta implementación MongoDB:
- Proyecto: CloudMusic DTE - Sistema Facturación Electrónica IA
- Institución: IPLACEX - Escuela de Informática y Telecomunicaciones
- Desarrollado por: Analista Programador
- Fecha: Noviembre 2025

==================================================================
             MONGODB CLOUDMUSIC DTE v2.5.3 - 5 COLECCIONES
                    CONFORME A INFORME TÉCNICO
==================================================================
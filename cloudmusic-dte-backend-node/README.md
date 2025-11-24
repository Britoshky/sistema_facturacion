# CloudMusic DTE - Backend Node.js

Backend del sistema CloudMusic DTE (Documentos Tributarios Electrónicos) desarrollado con Node.js, Express y TypeScript.

## 🏗️ Arquitectura

```
src/
├── controllers/     # Lógica de negocio y controladores
├── middleware/      # Middlewares de autenticación, validación, etc.
├── models/         # Modelos de datos (Prisma)
├── routes/         # Rutas de la API REST
├── services/       # Servicios externos (SII, validación XML)
├── utils/          # Utilidades y helpers
├── websockets/     # Manejadores de Socket.IO
└── server.ts       # Punto de entrada del servidor
```

## 🚀 Tecnologías

- **Node.js 20.10.0** - Runtime
- **Express.js** - Framework web
- **TypeScript** - Tipado estático
- **Socket.IO** - WebSockets en tiempo real
- **Prisma** - ORM para PostgreSQL
- **Redis** - Cache y Pub/Sub
- **PostgreSQL 16** - Base de datos principal

## 📋 Requisitos Previos

- Node.js 20.10.0 o superior
- Docker y Docker Compose
- PostgreSQL 16
- Redis 7.2

## ⚡ Instalación

1. **Instalar dependencias**
```bash
npm install
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con la configuración de base de datos existente:
# DATABASE_HOST=192.168.10.100
# DATABASE_PORT=32768
# DATABASE_NAME=sistema_facturacion_dte
# REDIS_HOST=192.168.10.100
# PORT=4003
```

3. **Generar cliente Prisma (conecta a BD existente)**
```bash
npm run prisma:generate
```

4. **Iniciar servidor en modo desarrollo**
```bash
npm run dev
```

> ⚠️ **Nota**: La base de datos PostgreSQL ya existe y contiene datos. 
> No es necesario ejecutar migraciones ni crear tablas.

## 🔧 Scripts Disponibles

```bash
# Desarrollo
npm run dev          # Servidor en modo desarrollo

# Producción  
npm run build        # Compilar TypeScript
npm start           # Ejecutar servidor compilado

# Base de datos
npm run prisma:generate  # Generar cliente Prisma
npm run prisma:migrate   # Ejecutar migraciones
npm run prisma:studio    # Interface visual de BD
```

## 🐳 Docker

```bash
# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

## 📊 Base de Datos

El sistema utiliza **PostgreSQL 16** con las siguientes 9 tablas principales:

1. `users` - Usuarios del sistema
2. `companies` - Empresas emisoras
3. `company_users` - Relación usuarios-empresas
4. `clients` - Clientes y proveedores
5. `products` - Catálogo de productos/servicios
6. `certificates` - Certificados digitales SII
7. `folios` - Rangos CAF autorizados
8. `documents` - Documentos tributarios (DTEs)
9. `document_items` - Líneas de detalle de DTEs

## 🔌 API Endpoints

### Autenticación
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/refresh` - Renovar token
- `POST /api/auth/logout` - Cerrar sesión

### Gestión de Datos
- `GET|POST|PUT|DELETE /api/companies` - Empresas
- `GET|POST|PUT|DELETE /api/clients` - Clientes
- `GET|POST|PUT|DELETE /api/products` - Productos
- `GET|POST|PUT|DELETE /api/documents` - Documentos DTE

### WebSockets
- Eventos en tiempo real
- Notificaciones de estado DTE
- Actualizaciones de sistema

## 🔒 Seguridad

- Autenticación JWT
- Rate limiting
- Validación RUT chileno
- Middlewares de seguridad (Helmet)
- CORS configurado

## 📈 Monitoreo

- Endpoint de salud: `GET /health`
- Logs estructurados
- Métricas de rendimiento

## 🤝 Desarrollo

Este proyecto forma parte del sistema CloudMusic DTE que incluye:
- Frontend: Next.js 15 + React 18
- Backend Node.js: API REST + WebSockets (este repo)
- Backend Python: IA + Analytics  
- Bases de datos: PostgreSQL + MongoDB

---

**CloudMusic DTE** - Sistema integral de Documentos Tributarios Electrónicos para PyMEs chilenas
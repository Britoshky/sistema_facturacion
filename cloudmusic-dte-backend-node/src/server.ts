import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { createServer } from 'http';
import rateLimit from 'express-rate-limit';
import * as trpcExpress from '@trpc/server/adapters/express';

// Importar configuraciones locales
import { connectDatabase, disconnectDatabase } from './models/database';
import { RedisService } from './services/redis';
import { WebSocketService } from './services/websocket';
import { logger } from './utils/logger';

// Importar tRPC
import { appRouter } from './trpc/routers';
import { createContext } from './trpc/context';

// Cargar variables de entorno
dotenv.config();

const app = express();
const server = createServer(app);

// Servicios globales
let redisService: RedisService;
let webSocketService: WebSocketService;

// Middlewares de seguridad
app.use(helmet());

// CORS - Configuración para múltiples orígenes
const corsOrigins = process.env.CORS_ORIGIN ? 
  process.env.CORS_ORIGIN.split(',').map(origin => origin.trim()) : 
  ["http://localhost:3000"];

app.use(cors({
  origin: corsOrigins,
  credentials: true
}));

// Rate Limiting - Configuración mejorada
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000'), // 15 minutos
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '300'), // máximo 300 requests por ventana (triplicado)
  message: {
    error: 'Demasiadas peticiones',
    message: `Has excedido el límite de ${parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '300')} peticiones por ${Math.floor(parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000') / 60000)} minutos. Por favor, espera antes de intentar nuevamente.`,
    retryAfter: Math.ceil(parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000') / 1000)
  },
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => {
    // No aplicar rate limiting a la ruta de salud
    return req.path === '/health';
  }
});
app.use(limiter);

// Parsear JSON
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Configurar tRPC
app.use(
  '/trpc',
  trpcExpress.createExpressMiddleware({
    router: appRouter,
    createContext,
  })
);

// Solo tRPC - sin rutas REST legacy

// Ruta de salud
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    message: 'CloudMusic DTE Backend - Node.js API',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Placeholder para rutas futuras
app.get('/', (req, res) => {
  res.json({
    message: 'CloudMusic DTE - Sistema de Documentos Tributarios Electrónicos',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      trpc: '/trpc'
    }
  });
});

// Middleware de manejo de errores
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Error interno del servidor',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Algo salió mal'
  });
});

// 404 handler
app.use((req: express.Request, res: express.Response) => {
  res.status(404).json({
    error: 'Endpoint no encontrado',
    path: req.path
  });
});

const PORT = process.env.PORT || 4003;

// Función principal para inicializar el servidor
async function startServer() {
  try {
    // Conectar a base de datos
    await connectDatabase();
    
    // Inicializar Redis service
    redisService = new RedisService();
    await redisService.connect();
    
    // También conectar los clientes Redis del EventService
    const { connectRedis } = await import('./models/redis');
    await connectRedis();
    
    // Inicializar SessionManager para autenticación
    const { initializeSessionManager } = await import('./middleware/auth');
    initializeSessionManager(redisService.getClient());
    
    // Inicializar WebSocket service
    webSocketService = new WebSocketService(server, redisService);
    
    // Configurar EventService con RedisService
    const { eventService } = await import('./services/eventService');
    eventService.setRedisService(redisService);
    
    // Hacer servicios globalmente accesibles
    global.redisService = redisService;
    global.webSocketService = webSocketService;
    
    // Iniciar servidor
    server.listen(PORT, () => {
      logger.info(`🚀 CloudMusic DTE Backend ejecutándose en puerto ${PORT}`);
      logger.info(`📡 WebSocket server iniciado con ${webSocketService.getConnectedClientsCount()} conexiones`);
      logger.info(`🌍 Entorno: ${process.env.NODE_ENV || 'development'}`);
      logger.info(`🗄️  Base de datos: ${process.env.DATABASE_NAME}@${process.env.DATABASE_HOST}:${process.env.DATABASE_PORT}`);
      logger.info(`🔴 Redis: ${process.env.REDIS_HOST}:${process.env.REDIS_PORT}`);
    });
  } catch (error) {
    logger.error('❌ Error iniciando servidor:', error);
    process.exit(1);
  }
}

// Manejar cierre limpio del servidor
process.on('SIGINT', async () => {
  logger.info('\n🛑 Cerrando servidor...');
  
  try {
    if (redisService) {
      await redisService.disconnect();
    }
    
    // También desconectar los clientes Redis del EventService
    const { disconnectRedis } = await import('./models/redis');
    await disconnectRedis();
    
    await disconnectDatabase();
    logger.info('✅ Servidor cerrado correctamente');
  } catch (error) {
    logger.error('❌ Error cerrando servidor:', error);
  }
  
  process.exit(0);
});

process.on('SIGTERM', async () => {
  logger.info('\n🛑 Cerrando servidor...');
  
  try {
    if (redisService) {
      await redisService.disconnect();
    }
    await disconnectDatabase();
    logger.info('✅ Servidor cerrado correctamente');
  } catch (error) {
    logger.error('❌ Error cerrando servidor:', error);
  }
  
  process.exit(0);
});

// Iniciar servidor
startServer();
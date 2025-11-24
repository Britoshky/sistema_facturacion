import { createClient } from 'redis';

// Configuración de Redis
const redisConfig = {
  socket: {
    host: process.env.REDIS_HOST || '192.168.10.100',
    port: parseInt(process.env.REDIS_PORT || '6379'),
  },
  password: process.env.REDIS_PASSWORD || 'CdCd@2627',
  database: parseInt(process.env.REDIS_DB || '1'),
};

// Cliente Redis principal
export const redisClient = createClient(redisConfig);

// Cliente Redis para Pub/Sub
export const redisPublisher = createClient(redisConfig);
export const redisSubscriber = createClient(redisConfig);

// Función para conectar Redis
export async function connectRedis() {
  try {
    await redisClient.connect();
    await redisPublisher.connect();
    await redisSubscriber.connect();
    
    console.log('✅ Conexión exitosa a Redis');
    console.log(`🔴 Redis conectado en ${redisConfig.socket.host}:${redisConfig.socket.port}`);
  } catch (error) {
    console.error('❌ Error conectando a Redis:', error);
  }
}

// Función para desconectar Redis
export async function disconnectRedis() {
  await redisClient.disconnect();
  await redisPublisher.disconnect();
  await redisSubscriber.disconnect();
  console.log('🔌 Desconectado de Redis');
}

// Eventos de conexión Redis
redisClient.on('error', (err: Error) => console.log('Redis Client Error', err));
redisClient.on('connect', () => console.log('Redis Client Connected'));
redisClient.on('ready', () => console.log('Redis Client Ready'));

export default redisClient;
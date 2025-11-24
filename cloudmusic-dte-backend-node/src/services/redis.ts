/**
 * Servicio Redis - CloudMusic DTE
 * Manejo de conexiones Redis, pub/sub y caché
 */

import Redis from 'ioredis';
import { logger } from '../utils/logger';

export class RedisService {
  private client: Redis;
  private subscriber: Redis;
  private publisher: Redis;
  private connected: boolean = false;

  constructor() {
    const redisConfig = {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD || undefined,
      retryDelayOnFailover: 100,
      maxRetriesPerRequest: 3,
      lazyConnect: true
    };

    this.client = new Redis(redisConfig);
    this.subscriber = new Redis(redisConfig);
    this.publisher = new Redis(redisConfig);
  }

  async connect(): Promise<boolean> {
    try {
      await Promise.all([
        this.client.connect(),
        this.subscriber.connect(),
        this.publisher.connect()
      ]);

      this.connected = true;
      logger.info('✅ Conectado a Redis');
      return true;

    } catch (error) {
      logger.error('❌ Error conectando a Redis:', error);
      this.connected = false;
      return false;
    }
  }

  async disconnect(): Promise<void> {
    try {
      await Promise.all([
        this.client.quit(),
        this.subscriber.quit(),
        this.publisher.quit()
      ]);

      this.connected = false;
      logger.info('✅ Desconectado de Redis');

    } catch (error) {
      logger.error('❌ Error desconectando de Redis:', error);
    }
  }

  getClient(): Redis {
    return this.client;
  }

  async ping(): Promise<boolean> {
    try {
      const result = await this.client.ping();
      return result === 'PONG';
    } catch (error) {
      return false;
    }
  }

  // === MÉTODOS PUB/SUB ===

  async publish(channel: string, message: string): Promise<number> {
    try {
      return await this.publisher.publish(channel, message);
    } catch (error) {
      logger.error(`❌ Error publicando a canal ${channel}:`, error);
      throw error;
    }
  }

  async subscribe(channel: string, callback: (message: string) => void): Promise<void> {
    try {
      await this.subscriber.subscribe(channel);
      
      this.subscriber.on('message', (receivedChannel, message) => {
        if (receivedChannel === channel) {
          callback(message);
        }
      });

      logger.debug(`📡 Suscrito al canal: ${channel}`);
    } catch (error) {
      logger.error(`❌ Error suscribiéndose al canal ${channel}:`, error);
      throw error;
    }
  }

  async unsubscribe(channel: string): Promise<void> {
    try {
      await this.subscriber.unsubscribe(channel);
      logger.debug(`📡 Desuscrito del canal: ${channel}`);
    } catch (error) {
      logger.error(`❌ Error desuscribiéndose del canal ${channel}:`, error);
      throw error;
    }
  }

  // === MÉTODOS DE CACHÉ ===

  async set(key: string, value: string, ttlSeconds?: number): Promise<void> {
    try {
      if (ttlSeconds) {
        await this.client.setex(key, ttlSeconds, value);
      } else {
        await this.client.set(key, value);
      }
    } catch (error) {
      logger.error(`❌ Error guardando clave ${key}:`, error);
      throw error;
    }
  }

  async get(key: string): Promise<string | null> {
    try {
      return await this.client.get(key);
    } catch (error) {
      logger.error(`❌ Error obteniendo clave ${key}:`, error);
      throw error;
    }
  }

  async delete(key: string): Promise<number> {
    try {
      return await this.client.del(key);
    } catch (error) {
      logger.error(`❌ Error eliminando clave ${key}:`, error);
      throw error;
    }
  }

  async exists(key: string): Promise<boolean> {
    try {
      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      logger.error(`❌ Error verificando clave ${key}:`, error);
      return false;
    }
  }

  // === MÉTODOS DE LISTA ===

  async listPush(key: string, value: string): Promise<number> {
    try {
      return await this.client.lpush(key, value);
    } catch (error) {
      logger.error(`❌ Error agregando a lista ${key}:`, error);
      throw error;
    }
  }

  async listPop(key: string): Promise<string | null> {
    try {
      return await this.client.rpop(key);
    } catch (error) {
      logger.error(`❌ Error obteniendo de lista ${key}:`, error);
      throw error;
    }
  }

  async listLength(key: string): Promise<number> {
    try {
      return await this.client.llen(key);
    } catch (error) {
      logger.error(`❌ Error obteniendo longitud de lista ${key}:`, error);
      return 0;
    }
  }

  // === MÉTODOS DE HASH ===

  async hashSet(key: string, field: string, value: string): Promise<number> {
    try {
      return await this.client.hset(key, field, value);
    } catch (error) {
      logger.error(`❌ Error guardando hash ${key}.${field}:`, error);
      throw error;
    }
  }

  async hashGet(key: string, field: string): Promise<string | null> {
    try {
      return await this.client.hget(key, field);
    } catch (error) {
      logger.error(`❌ Error obteniendo hash ${key}.${field}:`, error);
      throw error;
    }
  }

  async hashGetAll(key: string): Promise<Record<string, string>> {
    try {
      return await this.client.hgetall(key);
    } catch (error) {
      logger.error(`❌ Error obteniendo hash completo ${key}:`, error);
      throw error;
    }
  }

  // === MÉTODOS DE UTILIDAD ===

  isConnected(): boolean {
    return this.connected;
  }

  async flushall(): Promise<void> {
    if (process.env.NODE_ENV === 'development') {
      await this.client.flushall();
      logger.warn('🗑️ Redis flushed (development only)');
    }
  }

  async getStats() {
    try {
      const info = await this.client.info();
      const memory = await this.client.info('memory');
      
      return {
        connected: this.connected,
        info: info,
        memory: memory,
        timestamp: new Date()
      };
    } catch (error) {
      logger.error('❌ Error obteniendo estadísticas de Redis:', error);
      return {
        connected: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}
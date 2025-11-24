/**
 * ════════════════════════════════════════════════════════════════════════════════
 * 🔐 SISTEMA DE AUTENTICACIÓN PROFESIONAL - CLOUDMUSIC DTE
 * ════════════════════════════════════════════════════════════════════════════════
 * 
 * Autenticación híbrida con Redis para sesiones del servidor:
 * - JWT tokens para identificación
 * - Redis para control de sesiones activas
 * - Invalidación automática de sesiones
 * - Seguridad mejorada contra ataques
 */

import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import { TokenPayload } from '../trpc/schemas/users';

const JWT_SECRET = process.env.JWT_SECRET || 'your-super-secret-jwt-key-here';
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'your-super-secret-refresh-key-here';

// ==========================================
// 🎯 TIPOS DE SESIÓN
// ==========================================

export interface SessionData {
  userId: string;
  email: string;
  role: string;
  companyId: string;
  sessionId: string;
  loginTime: string;
  lastActivity: string;
  ipAddress?: string;
  userAgent?: string;
}

export interface ActiveSession {
  sessionId: string;
  userId: string;
  email: string;
  role: string;
  companyId: string;
  createdAt: Date;
  lastActivity: Date;
  ipAddress?: string;
  userAgent?: string;
}

// ==========================================
// 🔐 GESTIÓN DE TOKENS JWT
// ==========================================

export const generateTokens = (payload: TokenPayload & { sessionId: string }) => {
  const tokenPayload = {
    ...payload,
    sessionId: payload.sessionId,
    iat: Math.floor(Date.now() / 1000)
  };
  
  const accessToken = jwt.sign(tokenPayload, JWT_SECRET, { expiresIn: '8h' });
  const refreshToken = jwt.sign(
    { ...tokenPayload, tokenType: 'refresh' }, 
    JWT_REFRESH_SECRET, 
    { expiresIn: '7d' }
  );
  
  return { accessToken, refreshToken };
};

export const verifyToken = (token: string, isRefreshToken = false): TokenPayload & { sessionId: string } => {
  try {
    const secret = isRefreshToken ? JWT_REFRESH_SECRET : JWT_SECRET;
    const decoded = jwt.verify(token, secret) as TokenPayload & { sessionId: string };
    return decoded;
  } catch (error) {
    throw new Error(`Token ${isRefreshToken ? 'refresh' : 'access'} inválido`);
  }
};

// ==========================================
// 🗂️ GESTIÓN DE SESIONES CON REDIS
// ==========================================

export class SessionManager {
  private redisClient: any;
  private readonly SESSION_PREFIX = 'session:';
  private readonly USER_SESSIONS_PREFIX = 'user_sessions:';
  private readonly SESSION_TTL = 8 * 60 * 60; // 8 horas

  constructor(redisClient: any) {
    this.redisClient = redisClient;
  }

  /**
   * Crear nueva sesión
   */
  async createSession(sessionData: Omit<SessionData, 'sessionId' | 'loginTime' | 'lastActivity'>): Promise<string> {
    const sessionId = uuidv4();
    const now = new Date().toISOString();
    
    const session: SessionData = {
      ...sessionData,
      sessionId,
      loginTime: now,
      lastActivity: now
    };

    // Guardar sesión individual
    const sessionKey = `${this.SESSION_PREFIX}${sessionId}`;
    await this.redisClient.setex(
      sessionKey, 
      this.SESSION_TTL, 
      JSON.stringify(session)
    );

    // Agregar a lista de sesiones del usuario
    const userSessionsKey = `${this.USER_SESSIONS_PREFIX}${sessionData.userId}`;
    await this.redisClient.sadd(userSessionsKey, sessionId);
    await this.redisClient.expire(userSessionsKey, this.SESSION_TTL);

    console.log(`✅ Sesión creada: ${sessionId} para usuario ${sessionData.userId}`);
    return sessionId;
  }

  /**
   * Validar sesión activa
   */
  async validateSession(sessionId: string): Promise<SessionData | null> {
    try {
      const sessionKey = `${this.SESSION_PREFIX}${sessionId}`;
      const sessionRaw = await this.redisClient.get(sessionKey);
      
      if (!sessionRaw) {
        console.log(`❌ Sesión no encontrada: ${sessionId}`);
        return null;
      }

      const session: SessionData = JSON.parse(sessionRaw);
      
      // Actualizar última actividad
      session.lastActivity = new Date().toISOString();
      await this.redisClient.setex(sessionKey, this.SESSION_TTL, JSON.stringify(session));
      
      console.log(`✅ Sesión válida: ${sessionId} - Usuario: ${session.userId}`);
      return session;
    } catch (error) {
      console.error(`❌ Error validando sesión ${sessionId}:`, error);
      return null;
    }
  }

  /**
   * Invalidar sesión específica
   */
  async invalidateSession(sessionId: string): Promise<boolean> {
    try {
      const sessionKey = `${this.SESSION_PREFIX}${sessionId}`;
      const sessionRaw = await this.redisClient.get(sessionKey);
      
      if (sessionRaw) {
        const session: SessionData = JSON.parse(sessionRaw);
        
        // Remover de lista de usuario
        const userSessionsKey = `${this.USER_SESSIONS_PREFIX}${session.userId}`;
        await this.redisClient.srem(userSessionsKey, sessionId);
        
        // Eliminar sesión
        await this.redisClient.del(sessionKey);
        
        console.log(`🗑️ Sesión invalidada: ${sessionId}`);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error(`❌ Error invalidando sesión ${sessionId}:`, error);
      return false;
    }
  }

  /**
   * Invalidar todas las sesiones de un usuario
   */
  async invalidateAllUserSessions(userId: string): Promise<number> {
    try {
      const userSessionsKey = `${this.USER_SESSIONS_PREFIX}${userId}`;
      const sessionIds = await this.redisClient.smembers(userSessionsKey);
      
      let invalidated = 0;
      for (const sessionId of sessionIds) {
        if (await this.invalidateSession(sessionId)) {
          invalidated++;
        }
      }
      
      // Limpiar lista de sesiones del usuario
      await this.redisClient.del(userSessionsKey);
      
      console.log(`🗑️ ${invalidated} sesiones invalidadas para usuario: ${userId}`);
      return invalidated;
    } catch (error) {
      console.error(`❌ Error invalidando sesiones del usuario ${userId}:`, error);
      return 0;
    }
  }

  /**
   * Obtener sesiones activas de un usuario
   */
  async getUserActiveSessions(userId: string): Promise<ActiveSession[]> {
    try {
      const userSessionsKey = `${this.USER_SESSIONS_PREFIX}${userId}`;
      const sessionIds = await this.redisClient.smembers(userSessionsKey);
      
      const sessions: ActiveSession[] = [];
      
      for (const sessionId of sessionIds) {
        const sessionData = await this.validateSession(sessionId);
        if (sessionData) {
          sessions.push({
            sessionId: sessionData.sessionId,
            userId: sessionData.userId,
            email: sessionData.email,
            role: sessionData.role,
            companyId: sessionData.companyId,
            createdAt: new Date(sessionData.loginTime),
            lastActivity: new Date(sessionData.lastActivity),
            ipAddress: sessionData.ipAddress,
            userAgent: sessionData.userAgent
          });
        }
      }
      
      return sessions;
    } catch (error) {
      console.error(`❌ Error obteniendo sesiones del usuario ${userId}:`, error);
      return [];
    }
  }

  /**
   * Limpiar sesiones expiradas (tarea de mantenimiento)
   */
  async cleanExpiredSessions(): Promise<number> {
    try {
      const pattern = `${this.SESSION_PREFIX}*`;
      const keys = await this.redisClient.keys(pattern);
      
      let cleaned = 0;
      for (const key of keys) {
        const ttl = await this.redisClient.ttl(key);
        if (ttl <= 0) {
          await this.redisClient.del(key);
          cleaned++;
        }
      }
      
      console.log(`🧹 ${cleaned} sesiones expiradas limpiadas`);
      return cleaned;
    } catch (error) {
      console.error('❌ Error limpiando sesiones expiradas:', error);
      return 0;
    }
  }
}

// ==========================================
// 🚀 INSTANCIA GLOBAL DEL MANAGER
// ==========================================

let sessionManager: SessionManager | null = null;

export const initializeSessionManager = (redisClient: any): SessionManager => {
  if (!sessionManager) {
    sessionManager = new SessionManager(redisClient);
    console.log('🔐 SessionManager inicializado');
  }
  return sessionManager;
};

export const getSessionManager = (): SessionManager => {
  if (!sessionManager) {
    throw new Error('SessionManager no inicializado. Llamar initializeSessionManager() primero.');
  }
  return sessionManager;
};
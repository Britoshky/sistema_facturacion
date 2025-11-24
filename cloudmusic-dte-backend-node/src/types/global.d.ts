/**
 * Tipos globales para CloudMusic DTE Backend
 */

import { RedisService } from '../services/redis';
import { WebSocketService } from '../services/websocket';

declare global {
  var redisService: RedisService;
  var webSocketService: WebSocketService;
}

export {};
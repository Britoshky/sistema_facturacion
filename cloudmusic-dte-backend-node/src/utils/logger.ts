/**
 * Logger utility para CloudMusic DTE Backend
 * Configuración centralizada de logging
 */

// Logger utility - no necesita path por ahora

// Logger simple para evitar dependencias adicionales
class Logger {
  private getTimestamp(): string {
    return new Date().toISOString();
  }

  private formatMessage(level: string, message: string, data?: any): string {
    const timestamp = this.getTimestamp();
    const dataStr = data ? ` | ${JSON.stringify(data)}` : '';
    return `[${timestamp}] ${level.padEnd(7)} | ${message}${dataStr}`;
  }

  info(message: string, data?: any) {
    console.log(this.formatMessage('INFO', message, data));
  }

  debug(message: string, data?: any) {
    if (process.env.NODE_ENV === 'development') {
      console.log(this.formatMessage('DEBUG', message, data));
    }
  }

  warn(message: string, data?: any) {
    console.warn(this.formatMessage('WARN', message, data));
  }

  error(message: string, error?: any) {
    const errorData = error instanceof Error ? 
      { message: error.message, stack: error.stack } : 
      error;
    console.error(this.formatMessage('ERROR', message, errorData));
  }

  success(message: string, data?: any) {
    console.log(this.formatMessage('SUCCESS', message, data));
  }
}

export const logger = new Logger();
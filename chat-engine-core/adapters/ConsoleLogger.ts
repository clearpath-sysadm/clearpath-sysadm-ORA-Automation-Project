/**
 * Chat Engine Core - Console Logger Adapter
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Default logger implementation that writes to console.
 */

import type { ILogger, LogLevel, LogContext } from '../interfaces';

/**
 * Console Logger
 * 
 * Simple logger that writes to console with timestamps.
 * Can be replaced with any logging framework by implementing ILogger.
 */
export class ConsoleLogger implements ILogger {
  private readonly prefix: string;
  private readonly context: LogContext;
  private readonly minLevel: LogLevel;
  
  private static readonly LEVELS: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
  };

  constructor(options?: {
    prefix?: string;
    context?: LogContext;
    minLevel?: LogLevel;
  }) {
    this.prefix = options?.prefix ?? '[ChatEngine]';
    this.context = options?.context ?? {};
    this.minLevel = options?.minLevel ?? 'info';
  }

  debug(message: string, context?: LogContext): void {
    this.log('debug', message, context);
  }

  info(message: string, context?: LogContext): void {
    this.log('info', message, context);
  }

  warn(message: string, context?: LogContext): void {
    this.log('warn', message, context);
  }

  error(message: string, context?: LogContext): void {
    this.log('error', message, context);
  }

  child(context: LogContext): ILogger {
    return new ConsoleLogger({
      prefix: this.prefix,
      context: { ...this.context, ...context },
      minLevel: this.minLevel,
    });
  }

  private log(level: LogLevel, message: string, context?: LogContext): void {
    if (ConsoleLogger.LEVELS[level] < ConsoleLogger.LEVELS[this.minLevel]) {
      return;
    }

    const timestamp = new Date().toISOString();
    const mergedContext = { ...this.context, ...context };
    const contextStr = Object.keys(mergedContext).length > 0 
      ? ` ${JSON.stringify(mergedContext)}`
      : '';
    
    const formattedMessage = `${timestamp} ${this.prefix} [${level.toUpperCase()}] ${message}${contextStr}`;
    
    switch (level) {
      case 'debug':
      case 'info':
        console.log(formattedMessage);
        break;
      case 'warn':
        console.warn(formattedMessage);
        break;
      case 'error':
        console.error(formattedMessage);
        break;
    }
  }
}

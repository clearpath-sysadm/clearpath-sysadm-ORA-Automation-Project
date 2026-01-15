/**
 * Chat Engine Core - Retry Handler
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Retry utility with exponential backoff and circuit breaker integration.
 * Adapted from server/services/geminiAI.ts retry system.
 */

import type { ILogger, ICircuitBreaker, IMetricsService } from '../interfaces';
import type { RetryOptions } from '../types';
import { CircuitBreakerOpenError } from '../types';

/**
 * Default retry options
 */
const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxAttempts: 7,
  initialDelay: 200,
  backoffMultiplier: 1.3,
  retryableErrors: ['503', '429', 'ECONNRESET', 'ETIMEDOUT', 'UNAVAILABLE']
};

/**
 * Retry Handler
 * 
 * Provides retry functionality with exponential backoff.
 * Integrates with circuit breaker for cascading failure prevention.
 */
export class RetryHandler {
  private readonly defaultOptions: Required<RetryOptions>;
  private readonly logger?: ILogger;
  private readonly metrics?: IMetricsService;
  private readonly circuitBreaker?: ICircuitBreaker;

  constructor(options?: {
    defaultOptions?: RetryOptions;
    logger?: ILogger;
    metrics?: IMetricsService;
    circuitBreaker?: ICircuitBreaker;
  }) {
    this.defaultOptions = {
      ...DEFAULT_RETRY_OPTIONS,
      ...options?.defaultOptions
    };
    this.logger = options?.logger;
    this.metrics = options?.metrics;
    this.circuitBreaker = options?.circuitBreaker;
  }

  /**
   * Execute an operation with retry and exponential backoff
   */
  public async execute<T>(
    operation: () => Promise<T>,
    operationName: string,
    options: RetryOptions = {}
  ): Promise<T> {
    const opts = { ...this.defaultOptions, ...options };

    // Check circuit breaker first
    if (this.circuitBreaker) {
      const circuitState = this.circuitBreaker.getState();
      
      if (circuitState === 'OPEN') {
        const metrics = this.circuitBreaker.getMetrics();
        const timeSinceLastFailure = Date.now() - (metrics.lastFailureTime || 0);
        const resetTimeoutMs = 30000;
        
        if (timeSinceLastFailure < resetTimeoutMs) {
          this.log('warn', `Circuit breaker OPEN - failing fast for ${operationName}`);
          throw new CircuitBreakerOpenError(
            `Service temporarily unavailable. Retry in ${Math.round((resetTimeoutMs - timeSinceLastFailure) / 1000)}s.`
          );
        }
      }
    }

    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
      try {
        this.log('debug', `${operationName} (attempt ${attempt}/${opts.maxAttempts})`);
        
        const result = await operation();
        
        this.log('info', `${operationName} succeeded on attempt ${attempt}`);
        
        // Record success with metrics
        if (this.metrics) {
          this.metrics.increment('retry_success', 1, { operation: operationName, attempt: String(attempt) });
        }
        
        return result;
      } catch (error: unknown) {
        lastError = error as Error;
        
        const errorMessage = lastError.message || '';
        const errorStatus = (lastError as any).status?.toString() || '';
        const errorCode = (lastError as any).code || '';
        
        const isRetryable = opts.retryableErrors.some(code => 
          errorMessage.includes(code) || 
          errorStatus === code ||
          errorCode === code
        );

        if (!isRetryable) {
          this.log('error', `${operationName} failed with non-retryable error: ${errorMessage}`);
          throw error;
        }

        if (attempt === opts.maxAttempts) {
          this.log('error', `${operationName} failed after ${opts.maxAttempts} attempts`);
          
          // Log detailed diagnostics for quota errors
          if (errorStatus === '429' || errorMessage.includes('429') || errorMessage.includes('RESOURCE_EXHAUSTED')) {
            this.logQuotaDiagnostics(operationName, lastError);
          }
          
          // Record exhausted retries with metrics
          if (this.metrics) {
            this.metrics.increment('retry_exhausted', 1, { operation: operationName });
          }
          
          break;
        }

        // Calculate delay with exponential backoff
        const delay = opts.initialDelay * Math.pow(opts.backoffMultiplier, attempt - 1);
        
        this.log('warn', 
          `${operationName} attempt ${attempt} failed (${errorStatus || errorCode}), ` +
          `retrying in ${Math.round(delay)}ms...`
        );
        
        // Record retry with metrics
        if (this.metrics) {
          this.metrics.increment('retry_attempt', 1, { 
            operation: operationName, 
            attempt: String(attempt),
            error: errorStatus || errorCode
          });
        }
        
        await this.delay(delay);
      }
    }

    throw lastError!;
  }

  /**
   * Execute an operation with circuit breaker wrapper
   */
  public async executeWithCircuitBreaker<T>(
    operation: () => Promise<T>,
    operationName: string,
    options: RetryOptions = {}
  ): Promise<T> {
    if (this.circuitBreaker) {
      return this.circuitBreaker.call(() => 
        this.execute(operation, operationName, options)
      );
    }
    return this.execute(operation, operationName, options);
  }

  private logQuotaDiagnostics(operationName: string, error: Error): void {
    this.log('error', `QUOTA EXHAUSTED - Detailed Diagnosis for ${operationName}:`);
    this.log('error', `  Error Message: ${error.message}`);
    
    const errorAny = error as any;
    if (errorAny.status) this.log('error', `  Error Status: ${errorAny.status}`);
    if (errorAny.code) this.log('error', `  Error Code: ${errorAny.code}`);
    if (errorAny.details) this.log('error', `  Error Details: ${JSON.stringify(errorAny.details)}`);
    
    // Parse quota-specific information
    const quotaMatch = error.message.match(/quota.*?metric[:\s]+([^\s,]+)/i);
    if (quotaMatch) {
      this.log('error', `  QUOTA METRIC EXCEEDED: ${quotaMatch[1]}`);
    }
    
    const tokenMatch = error.message.match(/token[_\s]?count|token[_\s]?limit/i);
    const requestMatch = error.message.match(/request[_\s]?count|request[_\s]?limit|rpm/i);
    
    if (tokenMatch) {
      this.log('error', `  QUOTA TYPE: TOKEN LIMIT EXCEEDED`);
    } else if (requestMatch) {
      this.log('error', `  QUOTA TYPE: REQUEST LIMIT EXCEEDED`);
    } else {
      this.log('error', `  QUOTA TYPE: UNKNOWN - Check provider console`);
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    const prefix = '[RetryHandler]';
    if (this.logger) {
      this.logger[level](`${prefix} ${message}`);
    } else if (level !== 'debug') {
      console.log(`${prefix} ${message}`);
    }
  }
}

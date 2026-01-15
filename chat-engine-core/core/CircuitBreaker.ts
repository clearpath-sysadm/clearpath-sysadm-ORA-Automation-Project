/**
 * Chat Engine Core - Circuit Breaker Implementation
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Copied and adapted from server/services/circuitBreaker.ts
 * Uses interfaces instead of concrete dependencies.
 */

import type { 
  ICircuitBreaker, 
  CircuitBreakerState, 
  CircuitBreakerMetrics, 
  CircuitBreakerConfig,
  ILogger,
  IMetricsService
} from '../interfaces';
import { CircuitBreakerOpenError } from '../types';

/**
 * Circuit Breaker Pattern Implementation
 * 
 * Prevents cascading failures when external services are unavailable by:
 * - Tracking consecutive failures
 * - Opening circuit after threshold is reached
 * - Allowing recovery attempts after timeout
 * 
 * State Machine:
 * - CLOSED: Normal operation, all calls pass through
 * - OPEN: Circuit is tripped, calls fail fast
 * - HALF_OPEN: Recovery testing, single call allowed to test service health
 */
export class CircuitBreaker implements ICircuitBreaker {
  private state: CircuitBreakerState = 'CLOSED';
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: number | null = null;
  private lastStateChange: number = Date.now();
  private totalTrips: number = 0;
  
  private readonly config: Required<CircuitBreakerConfig>;
  private readonly logger?: ILogger;
  private readonly metrics?: IMetricsService;

  constructor(
    config: CircuitBreakerConfig,
    options?: {
      logger?: ILogger;
      metrics?: IMetricsService;
    }
  ) {
    if (config.failureThreshold <= 0) {
      throw new Error('Failure threshold must be a positive integer');
    }
    if (config.resetTimeoutMs <= 0) {
      throw new Error('Reset timeout must be a positive number');
    }

    this.config = {
      name: config.name,
      failureThreshold: config.failureThreshold,
      resetTimeoutMs: config.resetTimeoutMs,
      ignoredExceptions: config.ignoredExceptions || []
    };
    
    this.logger = options?.logger;
    this.metrics = options?.metrics;
    
    this.log('info', `Initialized with threshold=${this.config.failureThreshold}, timeout=${this.config.resetTimeoutMs}ms`);
  }

  /**
   * Execute a function through the circuit breaker
   * @throws CircuitBreakerOpenError if circuit is open and timeout hasn't elapsed
   */
  public async call<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      const timeSinceLastFailure = Date.now() - (this.lastFailureTime || 0);
      
      if (timeSinceLastFailure < this.config.resetTimeoutMs) {
        const retryIn = Math.round((this.config.resetTimeoutMs - timeSinceLastFailure) / 1000);
        this.log('warn', `Circuit OPEN - rejecting call (${retryIn}s until retry)`);
        throw new CircuitBreakerOpenError(
          `Circuit breaker "${this.config.name}" is OPEN. Retry in ${retryIn} seconds.`
        );
      } else {
        this.transitionToHalfOpen();
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error: unknown) {
      if (this.shouldIgnoreException(error as Error)) {
        this.log('debug', `Ignoring exception type: ${(error as Error).name}`);
        throw error;
      }

      this.onFailure(error as Error);
      throw error;
    }
  }

  private shouldIgnoreException(error: Error): boolean {
    return this.config.ignoredExceptions.some(
      exceptionType => error instanceof exceptionType
    );
  }

  private onSuccess(): void {
    this.successCount++;
    
    if (this.state === 'HALF_OPEN') {
      this.log('info', 'HALF_OPEN test succeeded - closing circuit');
      this.transitionToClosed();
    } else if (this.state === 'CLOSED' && this.failureCount > 0) {
      this.failureCount = 0;
    }
  }

  private onFailure(error: Error): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    this.emitMetrics('circuit_breaker_failure', {
      name: this.config.name,
      failureCount: this.failureCount,
      errorType: error.name,
      errorMessage: error.message?.substring(0, 200),
    });

    this.log('warn', `Failure #${this.failureCount}/${this.config.failureThreshold}: ${error.name}`);

    if (this.state === 'HALF_OPEN') {
      this.log('info', 'HALF_OPEN test failed - reopening circuit');
      this.transitionToOpen();
    } else if (this.failureCount >= this.config.failureThreshold) {
      this.log('warn', 'Failure threshold reached - opening circuit');
      this.transitionToOpen();
    }
  }

  private transitionToOpen(): void {
    if (this.state !== 'OPEN') {
      this.totalTrips++;
    }
    this.state = 'OPEN';
    this.lastStateChange = Date.now();
    this.emitMetrics('circuit_breaker_state_change', {
      name: this.config.name,
      state: 'OPEN',
      totalTrips: this.totalTrips,
    });
  }

  private transitionToHalfOpen(): void {
    this.log('info', 'Timeout elapsed - transitioning to HALF_OPEN');
    this.state = 'HALF_OPEN';
    this.lastStateChange = Date.now();
    this.emitMetrics('circuit_breaker_state_change', {
      name: this.config.name,
      state: 'HALF_OPEN',
    });
  }

  private transitionToClosed(): void {
    this.state = 'CLOSED';
    this.failureCount = 0;
    this.lastStateChange = Date.now();
    this.emitMetrics('circuit_breaker_state_change', {
      name: this.config.name,
      state: 'CLOSED',
    });
  }

  private emitMetrics(event: string, data: Record<string, unknown>): void {
    if (this.metrics) {
      this.metrics.event({
        name: event,
        value: 1,
        tags: Object.entries(data).reduce((acc, [k, v]) => {
          acc[k] = String(v);
          return acc;
        }, {} as Record<string, string>),
      });
    }
    this.log('debug', `Metrics: ${event} ${JSON.stringify(data)}`);
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    const prefix = `[CircuitBreaker:${this.config.name}]`;
    if (this.logger) {
      this.logger[level](`${prefix} ${message}`);
    } else {
      console.log(`${prefix} ${message}`);
    }
  }

  // Public control methods
  public close(): void {
    this.log('info', 'Manually closing circuit');
    this.transitionToClosed();
  }

  public open(): void {
    this.log('info', 'Manually opening circuit');
    this.lastFailureTime = Date.now();
    this.transitionToOpen();
  }

  public halfOpen(): void {
    this.log('info', 'Manually setting to half-open');
    this.transitionToHalfOpen();
  }

  public getState(): CircuitBreakerState {
    return this.state;
  }

  public getMetrics(): CircuitBreakerMetrics {
    return {
      name: this.config.name,
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      lastFailureTime: this.lastFailureTime,
      lastStateChange: this.lastStateChange,
      totalTrips: this.totalTrips,
    };
  }

  public reset(): void {
    this.log('info', 'Resetting circuit breaker');
    this.state = 'CLOSED';
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = null;
    this.lastStateChange = Date.now();
  }
}

/**
 * Factory function to create a circuit breaker with default AI service configuration
 */
export function createAICircuitBreaker(
  name: string = 'ai_provider',
  options?: {
    failureThreshold?: number;
    resetTimeoutMs?: number;
    logger?: ILogger;
    metrics?: IMetricsService;
  }
): CircuitBreaker {
  return new CircuitBreaker(
    {
      name,
      failureThreshold: options?.failureThreshold ?? 5,
      resetTimeoutMs: options?.resetTimeoutMs ?? 30000,
    },
    {
      logger: options?.logger,
      metrics: options?.metrics,
    }
  );
}

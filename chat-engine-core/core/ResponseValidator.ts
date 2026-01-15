/**
 * Chat Engine Core - Response Validator
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Copied and adapted from server/services/aiResponseValidator.ts
 * Uses interfaces instead of concrete dependencies.
 */

import type { ILogger, IConfigProvider } from '../interfaces';
import type { ValidationConfig, ValidationResult, ValidationMetrics } from '../types';
import { ValidationError } from '../types';

/**
 * Default validation configuration
 */
const DEFAULT_CONFIG: ValidationConfig = {
  minLength: 20,
  maxLength: 10000,
  maxRetries: 3,
  retryDelayMs: 2000,
};

/**
 * Response Validator
 * 
 * Validates AI response length, format, and coherence.
 * Implements automatic retry on validation failure with metrics tracking.
 */
export class ResponseValidator {
  private config: ValidationConfig;
  private metrics: ValidationMetrics;
  private readonly logger?: ILogger;

  constructor(options?: {
    config?: Partial<ValidationConfig>;
    configProvider?: IConfigProvider;
    logger?: ILogger;
  }) {
    // Build config from provider or defaults
    if (options?.configProvider) {
      this.config = {
        minLength: options.configProvider.get('AI_RESPONSE_MIN_LENGTH', DEFAULT_CONFIG.minLength),
        maxLength: options.configProvider.get('AI_RESPONSE_MAX_LENGTH', DEFAULT_CONFIG.maxLength),
        maxRetries: options.configProvider.get('AI_RESPONSE_MAX_RETRIES', DEFAULT_CONFIG.maxRetries),
        retryDelayMs: options.configProvider.get('AI_RESPONSE_RETRY_DELAY', DEFAULT_CONFIG.retryDelayMs),
      };
    } else {
      this.config = { ...DEFAULT_CONFIG };
    }

    // Override with explicit config
    if (options?.config) {
      this.config = { ...this.config, ...options.config };
    }

    this.logger = options?.logger;
    this.metrics = this.createEmptyMetrics();
  }

  private createEmptyMetrics(): ValidationMetrics {
    return {
      totalValidations: 0,
      validResponses: 0,
      invalidResponses: 0,
      failures: {
        lengthTooShort: 0,
        lengthTooLong: 0,
        jsonParseError: 0,
        nullOrEmpty: 0,
      },
      retries: {
        total: 0,
        successful: 0,
        exhausted: 0,
      },
      lastFailureTime: null,
      lastFailureReason: null,
    };
  }

  /**
   * Get current validation configuration
   */
  public getConfig(): ValidationConfig {
    return { ...this.config };
  }

  /**
   * Update validation configuration
   */
  public updateConfig(config: Partial<ValidationConfig>): void {
    this.config = { ...this.config, ...config };
    this.log('info', `Configuration updated: ${JSON.stringify(this.config)}`);
  }

  /**
   * Get validation metrics
   */
  public getMetrics(): ValidationMetrics & { successRate: number; retrySuccessRate: number; config: ValidationConfig } {
    const successRate = this.metrics.totalValidations > 0 
      ? (this.metrics.validResponses / this.metrics.totalValidations) * 100 
      : 100;
    
    const retrySuccessRate = this.metrics.retries.total > 0
      ? (this.metrics.retries.successful / this.metrics.retries.total) * 100
      : 100;

    return {
      ...this.metrics,
      successRate: Math.round(successRate * 100) / 100,
      retrySuccessRate: Math.round(retrySuccessRate * 100) / 100,
      config: this.getConfig(),
    };
  }

  /**
   * Reset validation metrics
   */
  public resetMetrics(): void {
    this.metrics = this.createEmptyMetrics();
    this.log('info', 'Metrics reset');
  }

  /**
   * Validate an AI response for length and optionally JSON format
   */
  public validate(
    response: string | null | undefined,
    options: {
      isJson?: boolean;
      config?: Partial<ValidationConfig>;
    } = {}
  ): ValidationResult {
    const config = { ...this.config, ...options.config };
    
    this.metrics.totalValidations++;

    // Check for null or empty responses
    if (response === null || response === undefined || response === '') {
      this.metrics.invalidResponses++;
      this.metrics.failures.nullOrEmpty++;
      this.metrics.lastFailureTime = Date.now();
      this.metrics.lastFailureReason = 'null_or_empty';
      
      this.logValidationFailure('null_or_empty', response, 'Response is null or empty');
      
      return {
        isValid: false,
        error: 'Response is null or empty',
        errorType: 'null_or_empty',
      };
    }

    const responseLength = response.length;

    // Length validation - too short
    if (responseLength < config.minLength) {
      this.metrics.invalidResponses++;
      this.metrics.failures.lengthTooShort++;
      this.metrics.lastFailureTime = Date.now();
      this.metrics.lastFailureReason = 'length_too_short';
      
      this.logValidationFailure(
        'length_too_short',
        response,
        `Response length ${responseLength} is below minimum ${config.minLength}`
      );
      
      return {
        isValid: false,
        error: `Response length ${responseLength} is below minimum ${config.minLength}`,
        errorType: 'length_too_short',
        response,
      };
    }

    // Length validation - too long
    if (responseLength > config.maxLength) {
      this.metrics.invalidResponses++;
      this.metrics.failures.lengthTooLong++;
      this.metrics.lastFailureTime = Date.now();
      this.metrics.lastFailureReason = 'length_too_long';
      
      this.logValidationFailure(
        'length_too_long',
        response.substring(0, 500) + '... [truncated]',
        `Response length ${responseLength} exceeds maximum ${config.maxLength}`
      );
      
      return {
        isValid: false,
        error: `Response length ${responseLength} exceeds maximum ${config.maxLength}`,
        errorType: 'length_too_long',
        response,
      };
    }

    // JSON parsing validation (if required)
    if (options.isJson) {
      try {
        const parsed = JSON.parse(response);
        this.metrics.validResponses++;
        return {
          isValid: true,
          response,
          parsedJson: parsed,
        };
      } catch (error: unknown) {
        this.metrics.invalidResponses++;
        this.metrics.failures.jsonParseError++;
        this.metrics.lastFailureTime = Date.now();
        this.metrics.lastFailureReason = 'json_parse_error';
        
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        this.logValidationFailure(
          'json_parse_error',
          response.substring(0, 1000),
          `JSON parsing failed: ${errorMessage}`
        );
        
        return {
          isValid: false,
          error: `JSON parsing failed: ${errorMessage}`,
          errorType: 'json_parse_error',
          response,
        };
      }
    }

    // Valid response
    this.metrics.validResponses++;
    return {
      isValid: true,
      response,
    };
  }

  /**
   * Validate and extract JSON from AI response with extraction
   */
  public validateAndExtractJson<T = unknown>(
    response: string | null | undefined,
    options: {
      config?: Partial<ValidationConfig>;
    } = {}
  ): ValidationResult & { parsedJson?: T } {
    if (!response) {
      return this.validate(response, { isJson: true, ...options }) as ValidationResult & { parsedJson?: T };
    }
    
    const extracted = this.extractJsonFromResponse(response);
    return this.validate(extracted, { isJson: true, ...options }) as ValidationResult & { parsedJson?: T };
  }

  /**
   * Extract and clean JSON from a response that might have markdown code blocks
   */
  public extractJsonFromResponse(response: string): string {
    let text = response;
    
    // Try to extract JSON from markdown code blocks
    const jsonBlockMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonBlockMatch) {
      text = jsonBlockMatch[1].trim();
    } else {
      // Try to find JSON object or array directly
      const jsonMatch = text.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
      if (jsonMatch) {
        text = jsonMatch[1].trim();
      }
    }
    
    // Fix common JSON issues
    text = text
      .replace(/,\s*}/g, '}')  // Remove trailing commas before }
      .replace(/,\s*]/g, ']')  // Remove trailing commas before ]
      .trim();
    
    return text;
  }

  /**
   * Execute a response generator with validation and automatic retry
   */
  public async retryWithValidation(
    responseGenerator: () => Promise<string>,
    options: {
      isJson?: boolean;
      config?: Partial<ValidationConfig>;
      operationName?: string;
    } = {}
  ): Promise<string> {
    const config = { ...this.config, ...options.config };
    const operationName = options.operationName || 'AI Response';
    
    let lastError: string | undefined;
    let attempts = 0;

    while (attempts < config.maxRetries) {
      attempts++;
      
      try {
        const response = await responseGenerator();
        const validationResult = this.validate(response, { isJson: options.isJson, config });

        if (validationResult.isValid) {
          if (attempts > 1) {
            this.metrics.retries.successful++;
            this.log('info', `${operationName} validated successfully after ${attempts} attempts`);
          }
          return response;
        }

        lastError = validationResult.error;
        
        if (attempts < config.maxRetries) {
          this.metrics.retries.total++;
          this.log('warn', 
            `${operationName} validation failed (attempt ${attempts}/${config.maxRetries}): ${lastError}. ` +
            `Retrying in ${config.retryDelayMs}ms...`
          );
          await this.delay(config.retryDelayMs);
        }
      } catch (error: unknown) {
        lastError = error instanceof Error ? error.message : 'Unknown error during response generation';
        this.log('error', `${operationName} generation error (attempt ${attempts}): ${lastError}`);
        
        if (attempts < config.maxRetries) {
          this.metrics.retries.total++;
          await this.delay(config.retryDelayMs);
        }
      }
    }

    this.metrics.retries.exhausted++;
    this.log('error', `${operationName} validation failed after ${config.maxRetries} retries`);
    
    throw new ValidationError(
      `AI response validation failed after ${config.maxRetries} retries: ${lastError}`,
      lastError || 'Unknown'
    );
  }

  /**
   * Execute a response generator with JSON validation and automatic retry
   */
  public async retryWithJsonValidation<T = unknown>(
    responseGenerator: () => Promise<string>,
    options: {
      config?: Partial<ValidationConfig>;
      operationName?: string;
    } = {}
  ): Promise<T> {
    const config = { ...this.config, ...options.config };
    const operationName = options.operationName || 'AI JSON Response';
    
    let lastError: string | undefined;
    let attempts = 0;

    while (attempts < config.maxRetries) {
      attempts++;
      
      try {
        const response = await responseGenerator();
        const validationResult = this.validate(response, { isJson: true, config });

        if (validationResult.isValid && validationResult.parsedJson !== undefined) {
          if (attempts > 1) {
            this.metrics.retries.successful++;
            this.log('info', `${operationName} validated successfully after ${attempts} attempts`);
          }
          return validationResult.parsedJson as T;
        }

        lastError = validationResult.error;
        
        if (attempts < config.maxRetries) {
          this.metrics.retries.total++;
          this.log('warn',
            `${operationName} validation failed (attempt ${attempts}/${config.maxRetries}): ${lastError}. ` +
            `Retrying in ${config.retryDelayMs}ms...`
          );
          await this.delay(config.retryDelayMs);
        }
      } catch (error: unknown) {
        lastError = error instanceof Error ? error.message : 'Unknown error during response generation';
        this.log('error', `${operationName} generation error (attempt ${attempts}): ${lastError}`);
        
        if (attempts < config.maxRetries) {
          this.metrics.retries.total++;
          await this.delay(config.retryDelayMs);
        }
      }
    }

    this.metrics.retries.exhausted++;
    this.log('error', `${operationName} JSON validation failed after ${config.maxRetries} retries`);
    
    throw new ValidationError(
      `AI JSON response validation failed after ${config.maxRetries} retries: ${lastError}`,
      lastError || 'Unknown'
    );
  }

  /**
   * Quick check if a response meets minimum quality standards
   * Does not update metrics - use for pre-flight checks
   */
  public quickValidate(
    response: string | null | undefined,
    minLength: number = 20
  ): boolean {
    if (!response) return false;
    return response.length >= minLength;
  }

  private logValidationFailure(
    type: string,
    response: string | null | undefined,
    reason: string
  ): void {
    const timestamp = new Date().toISOString();
    this.log('error', `VALIDATION_FAILURE | Type: ${type} | Reason: ${reason} | Preview: ${response?.substring(0, 200) || '(null/empty)'}`);
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    const prefix = '[ResponseValidator]';
    if (this.logger) {
      this.logger[level](`${prefix} ${message}`);
    } else {
      console.log(`${prefix} ${message}`);
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

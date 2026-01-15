/**
 * Chat Engine Core - Preflight Token Checker
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Validates context size before sending to AI provider.
 * Adapted from server/services/geminiAI.ts preflight token check system.
 */

import type { ILogger, AIContent } from '../interfaces';
import type { PreflightResult } from '../types';

/**
 * Model-specific token limits (conservative estimates with buffer)
 */
const DEFAULT_MODEL_TOKEN_LIMITS: Record<string, number> = {
  'gemini-2.5-pro': 900000,
  'gemini-2.5-flash': 900000,
  'gemini-2.0-flash': 900000,
  'gemini-1.5-pro': 1800000,
  'gemini-1.5-flash': 900000,
  'gpt-4': 128000,
  'gpt-4-turbo': 128000,
  'gpt-3.5-turbo': 16000,
  'claude-3-opus': 200000,
  'claude-3-sonnet': 200000,
  'claude-3-haiku': 200000,
  'default': 100000,
};

export type SupportedModel = keyof typeof DEFAULT_MODEL_TOKEN_LIMITS;

/**
 * Token Checker
 * 
 * Preflight check to validate context size before sending to AI provider.
 * Prevents oversized requests and provides helpful error messages.
 */
export class TokenChecker {
  private readonly modelLimits: Record<string, number>;
  private readonly logger?: ILogger;

  constructor(options?: {
    customLimits?: Record<string, number>;
    logger?: ILogger;
  }) {
    this.modelLimits = { ...DEFAULT_MODEL_TOKEN_LIMITS, ...options?.customLimits };
    this.logger = options?.logger;
  }

  /**
   * Estimate tokens from text (rough approximation: 1 token ~ 4 characters)
   */
  public estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }

  /**
   * Get token limit for a model
   */
  public getModelLimit(model: string): number {
    return this.modelLimits[model] || this.modelLimits['default'];
  }

  /**
   * Update token limit for a model
   */
  public setModelLimit(model: string, limit: number): void {
    this.modelLimits[model] = limit;
  }

  /**
   * Preflight check to validate context size before sending to AI
   * Returns structured result with pass/fail status and token breakdown
   */
  public check(
    systemPrompt: string,
    conversationHistory: AIContent[],
    userMessage: string,
    model: string = 'default'
  ): PreflightResult {
    const maxTokens = this.getModelLimit(model);
    
    // Calculate tokens for each component
    const systemPromptTokens = this.estimateTokens(systemPrompt);
    
    // Calculate conversation history tokens
    let conversationTokens = 0;
    for (const msg of conversationHistory) {
      for (const part of msg.parts) {
        if (part.text) {
          conversationTokens += this.estimateTokens(part.text);
        }
        if (part.functionCall) {
          conversationTokens += this.estimateTokens(JSON.stringify(part.functionCall));
        }
        if (part.functionResponse) {
          conversationTokens += this.estimateTokens(JSON.stringify(part.functionResponse));
        }
      }
    }
    
    const userMessageTokens = this.estimateTokens(userMessage);
    const totalTokens = systemPromptTokens + conversationTokens + userMessageTokens;
    
    const breakdown = {
      systemPrompt: systemPromptTokens,
      conversationHistory: conversationTokens,
      userMessage: userMessageTokens,
    };
    
    const passed = totalTokens <= maxTokens;
    
    let message: string;
    if (passed) {
      message = `Context: ${totalTokens.toLocaleString()} tokens (${model})`;
    } else {
      message = this.buildErrorMessage(totalTokens, maxTokens, model, breakdown);
    }
    
    // Log the check result
    this.log(
      passed ? 'debug' : 'warn',
      `Token check for ${model}: ${totalTokens.toLocaleString()}/${maxTokens.toLocaleString()} tokens (${passed ? 'PASSED' : 'FAILED'})`
    );
    
    if (!passed) {
      this.log('warn', `Breakdown: ${JSON.stringify(breakdown)}`);
    }
    
    return {
      passed,
      totalTokens,
      breakdown,
      limit: maxTokens,
      model,
      message,
    };
  }

  /**
   * Check if a single message fits within limits
   */
  public checkSingleMessage(message: string, model: string = 'default'): PreflightResult {
    return this.check('', [], message, model);
  }

  /**
   * Calculate remaining token budget
   */
  public getRemainingBudget(
    systemPrompt: string,
    conversationHistory: AIContent[],
    model: string = 'default'
  ): { remaining: number; used: number; limit: number } {
    const result = this.check(systemPrompt, conversationHistory, '', model);
    return {
      remaining: result.limit - result.totalTokens,
      used: result.totalTokens,
      limit: result.limit,
    };
  }

  private buildErrorMessage(
    totalTokens: number,
    maxTokens: number,
    model: string,
    breakdown: PreflightResult['breakdown']
  ): string {
    return [
      `**Context Too Large**`,
      ``,
      `Your request context is **${totalTokens.toLocaleString()} tokens** which exceeds the maximum of **${maxTokens.toLocaleString()} tokens** for ${model}.`,
      ``,
      `**Breakdown:**`,
      `- System prompt: ${breakdown.systemPrompt.toLocaleString()} tokens`,
      `- Conversation history: ${breakdown.conversationHistory.toLocaleString()} tokens`,
      `- Your message: ${breakdown.userMessage.toLocaleString()} tokens`,
      ``,
      `**To resolve:** Start a new conversation or reduce the context being loaded.`
    ].join('\n');
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    const prefix = '[TokenChecker]';
    if (this.logger) {
      this.logger[level](`${prefix} ${message}`);
    } else if (level !== 'debug') {
      console.log(`${prefix} ${message}`);
    }
  }
}

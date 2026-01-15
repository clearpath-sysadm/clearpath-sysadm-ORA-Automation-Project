/**
 * Chat Engine Core - API Usage Tracker
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Tracks request counts and estimated token usage.
 * Adapted from server/services/geminiAI.ts usage tracking system.
 */

import type { ILogger, IMetricsService } from '../interfaces';
import type { UsageStats } from '../types';

interface UsageEntry {
  timestamp: number;
  model: string;
  estimatedTokens: number;
  operation: string;
  success: boolean;
}

/**
 * API Usage Tracker
 * 
 * Tracks request counts and estimated token usage to help diagnose quota issues.
 * Maintains a rolling window of usage data.
 */
export class UsageTracker {
  private readonly usageLog: UsageEntry[] = [];
  private readonly maxAgeMs: number;
  
  private sessionRequestCount: number = 0;
  private sessionTokenCount: number = 0;
  private sessionStartTime: number = Date.now();
  
  private readonly logger?: ILogger;
  private readonly metrics?: IMetricsService;
  private readonly logInterval: number;

  constructor(options?: {
    maxAgeMs?: number;
    logInterval?: number;
    logger?: ILogger;
    metrics?: IMetricsService;
  }) {
    this.maxAgeMs = options?.maxAgeMs ?? 24 * 60 * 60 * 1000; // 24 hours
    this.logInterval = options?.logInterval ?? 50; // Log every 50 requests
    this.logger = options?.logger;
    this.metrics = options?.metrics;
  }

  /**
   * Estimate tokens from text (rough approximation: 1 token ~ 4 characters)
   */
  public estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }

  /**
   * Log an API call
   */
  public logUsage(
    model: string,
    operation: string,
    promptText: string,
    success: boolean
  ): void {
    const estimatedTokens = this.estimateTokens(promptText);
    const now = Date.now();
    
    // Add to rolling log
    this.usageLog.push({
      timestamp: now,
      model,
      estimatedTokens,
      operation,
      success
    });
    
    // Update session counters
    this.sessionRequestCount++;
    this.sessionTokenCount += estimatedTokens;
    
    // Cleanup old entries
    this.cleanupOldEntries(now);
    
    // Emit metrics
    if (this.metrics) {
      this.metrics.increment('ai_api_calls', 1, { model, operation, success: String(success) });
      this.metrics.histogram('ai_estimated_tokens', estimatedTokens, { model });
    }
    
    // Log periodic usage summary
    if (this.sessionRequestCount % this.logInterval === 0) {
      this.log('info', 
        `Session Stats: ${this.sessionRequestCount} requests, ` +
        `~${this.sessionTokenCount.toLocaleString()} estimated tokens since ${new Date(this.sessionStartTime).toLocaleTimeString()}`
      );
    }
  }

  /**
   * Get usage stats for monitoring
   */
  public getStats(): UsageStats {
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;
    
    const stats: UsageStats = {
      last1Hour: { requests: 0, tokens: 0 },
      last24Hours: { requests: 0, tokens: 0 },
      byModel: {},
      session: { 
        requests: this.sessionRequestCount, 
        tokens: this.sessionTokenCount, 
        startTime: new Date(this.sessionStartTime) 
      }
    };
    
    for (const entry of this.usageLog) {
      // 24 hour stats (all in log)
      stats.last24Hours.requests++;
      stats.last24Hours.tokens += entry.estimatedTokens;
      
      // 1 hour stats
      if (entry.timestamp >= oneHourAgo) {
        stats.last1Hour.requests++;
        stats.last1Hour.tokens += entry.estimatedTokens;
      }
      
      // By model
      if (!stats.byModel[entry.model]) {
        stats.byModel[entry.model] = { requests: 0, tokens: 0 };
      }
      stats.byModel[entry.model].requests++;
      stats.byModel[entry.model].tokens += entry.estimatedTokens;
    }
    
    return stats;
  }

  /**
   * Log usage summary (call this periodically or on errors)
   */
  public logSummary(reason: string = 'periodic'): void {
    const stats = this.getStats();
    this.log('info', `Usage Summary (${reason})`);
    this.log('info', `  Last 1 hour: ${stats.last1Hour.requests} requests, ~${stats.last1Hour.tokens.toLocaleString()} tokens`);
    this.log('info', `  Last 24 hours: ${stats.last24Hours.requests} requests, ~${stats.last24Hours.tokens.toLocaleString()} tokens`);
    this.log('info', `  Session: ${stats.session.requests} requests, ~${stats.session.tokens.toLocaleString()} tokens`);
    this.log('info', `  By model: ${JSON.stringify(stats.byModel)}`);
  }

  /**
   * Reset session counters
   */
  public resetSession(): void {
    this.sessionRequestCount = 0;
    this.sessionTokenCount = 0;
    this.sessionStartTime = Date.now();
    this.log('info', 'Session counters reset');
  }

  /**
   * Clear all usage data
   */
  public clear(): void {
    this.usageLog.length = 0;
    this.resetSession();
    this.log('info', 'All usage data cleared');
  }

  private cleanupOldEntries(now: number): void {
    const cutoff = now - this.maxAgeMs;
    while (this.usageLog.length > 0 && this.usageLog[0].timestamp < cutoff) {
      this.usageLog.shift();
    }
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    const prefix = '[UsageTracker]';
    if (this.logger) {
      this.logger[level](`${prefix} ${message}`);
    } else {
      console.log(`${prefix} ${message}`);
    }
  }
}

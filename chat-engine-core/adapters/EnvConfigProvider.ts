/**
 * Chat Engine Core - Environment Config Provider Adapter
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Default configuration provider that reads from environment variables.
 */

import type { IConfigProvider } from '../interfaces';

/**
 * Environment Config Provider
 * 
 * Reads configuration from environment variables.
 * Can be replaced with file-based or remote config by implementing IConfigProvider.
 */
export class EnvConfigProvider implements IConfigProvider {
  private readonly prefix: string;
  private readonly defaults: Record<string, unknown>;

  constructor(options?: {
    prefix?: string;
    defaults?: Record<string, unknown>;
  }) {
    this.prefix = options?.prefix ?? '';
    this.defaults = options?.defaults ?? {};
  }

  get<T = string>(key: string, defaultValue?: T): T {
    const envKey = this.prefix ? `${this.prefix}_${key}` : key;
    const value = process.env[envKey];
    
    if (value === undefined) {
      if (defaultValue !== undefined) {
        return defaultValue;
      }
      if (key in this.defaults) {
        return this.defaults[key] as T;
      }
      return undefined as T;
    }
    
    return this.parseValue(value) as T;
  }

  getRequired<T = string>(key: string): T {
    const value = this.get<T>(key);
    
    if (value === undefined || value === null) {
      const envKey = this.prefix ? `${this.prefix}_${key}` : key;
      throw new Error(`Required configuration key "${envKey}" is not set`);
    }
    
    return value;
  }

  has(key: string): boolean {
    const envKey = this.prefix ? `${this.prefix}_${key}` : key;
    return process.env[envKey] !== undefined || key in this.defaults;
  }

  keys(): string[] {
    const envKeys = Object.keys(process.env)
      .filter(key => !this.prefix || key.startsWith(this.prefix))
      .map(key => this.prefix ? key.slice(this.prefix.length + 1) : key);
    
    const defaultKeys = Object.keys(this.defaults);
    
    return [...new Set([...envKeys, ...defaultKeys])];
  }

  private parseValue(value: string): unknown {
    // Try to parse as JSON
    try {
      return JSON.parse(value);
    } catch {
      // Return as string if not valid JSON
      return value;
    }
  }
}

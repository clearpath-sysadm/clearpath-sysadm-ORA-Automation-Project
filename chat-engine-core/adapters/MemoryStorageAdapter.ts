/**
 * Chat Engine Core - Memory Storage Adapter
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * In-memory storage implementation for testing and development.
 */

import type { IStorageAdapter, QueryFilter } from '../interfaces';

/**
 * Memory Storage Adapter
 * 
 * Simple in-memory key-value store.
 * Can be replaced with PostgreSQL, Redis, etc. by implementing IStorageAdapter.
 */
export class MemoryStorageAdapter<T = unknown> implements IStorageAdapter<T> {
  private readonly store: Map<string, T> = new Map();

  async get(key: string): Promise<T | null> {
    return this.store.get(key) ?? null;
  }

  async set(key: string, value: T): Promise<void> {
    this.store.set(key, value);
  }

  async delete(key: string): Promise<boolean> {
    return this.store.delete(key);
  }

  async query(filter: QueryFilter): Promise<T[]> {
    let results = Array.from(this.store.values());
    
    // Apply where filter
    if (filter.where) {
      results = results.filter(item => {
        for (const [key, value] of Object.entries(filter.where!)) {
          if ((item as Record<string, unknown>)[key] !== value) {
            return false;
          }
        }
        return true;
      });
    }
    
    // Apply ordering
    if (filter.orderBy && filter.orderBy.length > 0) {
      results.sort((a, b) => {
        for (const { field, direction } of filter.orderBy!) {
          const aVal = (a as Record<string, unknown>)[field];
          const bVal = (b as Record<string, unknown>)[field];
          
          if (aVal < bVal) return direction === 'asc' ? -1 : 1;
          if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    
    // Apply pagination
    if (filter.offset !== undefined) {
      results = results.slice(filter.offset);
    }
    if (filter.limit !== undefined) {
      results = results.slice(0, filter.limit);
    }
    
    return results;
  }

  async exists(key: string): Promise<boolean> {
    return this.store.has(key);
  }

  async keys(): Promise<string[]> {
    return Array.from(this.store.keys());
  }

  async clear(): Promise<void> {
    this.store.clear();
  }

  /** Get current size of store (for testing) */
  get size(): number {
    return this.store.size;
  }
}

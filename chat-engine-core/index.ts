/**
 * Chat Engine Core Module
 * 
 * @clearpath/chat-engine-core
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * This module provides a clean, isolated AI chat engine that can be
 * used across multiple applications. It follows Hexagonal Architecture
 * (Ports & Adapters) pattern for clean separation of concerns.
 * 
 * Key Features:
 * - Provider-agnostic AI integration (Gemini, OpenAI, Claude, etc.)
 * - Full chat orchestration with conversation management
 * - Function calling support
 * - Circuit breaker for resilience
 * - Response validation with retry
 * - Token management and preflight checks
 * - Introspection API for AI self-reflection
 * - No external dependencies on host application
 * 
 * @example
 * import { GoogleGenAI } from "@google/genai";
 * import { createQuickStartEngine, createGeminiAdapter } from '@clearpath/chat-engine-core';
 * 
 * // Quick start - just provide an AI provider
 * const gemini = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
 * const engine = createQuickStartEngine(createGeminiAdapter(gemini));
 * 
 * const response = await engine.chat('Hello, how can you help me?');
 * console.log(response.message.content);
 * 
 * @example
 * // For full control, use createChatEngine with explicit dependencies:
 * import { createChatEngine, ConsoleLogger, EnvConfigProvider, MemoryStorageAdapter } from '@clearpath/chat-engine-core';
 * 
 * const engine = createChatEngine({
 *   aiProvider: myProvider,
 *   config: new EnvConfigProvider(),
 *   logger: new ConsoleLogger(),
 *   storage: new MemoryStorageAdapter(),
 * });
 */

// ============================================================================
// INTERFACES (Ports)
// ============================================================================
export type {
  // AI Provider
  IAIProvider,
  AIContentRequest,
  AIContentResponse,
  AIContent,
  AIPart,
  AIChunk,
  AIFunctionCall,
  AIFunctionResponse,
  AIGenerationConfig,
  AITool,
  AIFunctionDeclaration,
  AISchemaProperty,
  AICandidate,
  AISafetyRating,
  AIUsageMetadata,
  LiveSessionConfig,
  ILiveSession,
  
  // Storage & Database
  IStorageAdapter,
  IDatabaseAdapter,
  ITransaction,
  QueryFilter,
  
  // Circuit Breaker
  ICircuitBreaker,
  CircuitBreakerState,
  CircuitBreakerMetrics,
  CircuitBreakerConfig,
  
  // Configuration & Logging
  IConfigProvider,
  ILogger,
  LogLevel,
  LogContext,
  
  // Domain Services
  IPersonaService,
  IVoiceService,
  ITopicLinkingService,
  IMetricsService,
  
  // Types
  Persona,
  VoiceProfile,
  Topic,
  TopicLink,
  MetricEvent,
  
  // Factory
  ChatEngineDependencies,
} from './interfaces';

// ============================================================================
// TYPES
// ============================================================================
export type {
  // Entity & Function Types
  AIEntityType,
  AIFunctionCategory,
  AIFunctionMetadata,
  FunctionDeclaration,
  FunctionParameters,
  SchemaProperty,
  DocumentationContextVariables,
  DocumentationOptions,
  
  // Chat Types
  ChatMessage,
  ChatMessageMetadata,
  ChatConversation,
  ConversationContext,
  
  // Validation Types
  ValidationConfig,
  ValidationResult,
  ValidationMetrics,
  
  // Token & Usage Types
  TokenUsage,
  UsageStats,
  PreflightResult,
  RetryOptions,
} from './types';

export {
  // Type Guards & Filters
  hasMetadata,
  filterByEntityType,
  filterByCategory,
  filterReadOnly,
  generateFunctionDocumentation,
  
  // Error Classes
  ChatEngineError,
  ValidationError,
  CircuitBreakerOpenError,
  ProviderError,
} from './types';

// ============================================================================
// CORE COMPONENTS
// ============================================================================
export { 
  ChatEngine, 
  createChatEngine,
  createChatEngineWithDefaults,
  type ChatRequestOptions,
  type ChatResponse,
  type StreamingChatResponse,
  type MinimalChatEngineDependencies,
} from './core/ChatEngine';

export { CircuitBreaker, createAICircuitBreaker } from './core/CircuitBreaker';
export { ResponseValidator } from './core/ResponseValidator';
export { UsageTracker } from './core/UsageTracker';
export { TokenChecker } from './core/TokenChecker';
export { RetryHandler } from './core/RetryHandler';

// ============================================================================
// INTROSPECTION API
// ============================================================================
export {
  IntrospectionAPI,
  getIntrospectionAPI,
  type FileMetadata,
  type FileContent,
  type ModuleMetadata,
} from './introspection';

// ============================================================================
// ADAPTERS
// ============================================================================
export { ConsoleLogger } from './adapters/ConsoleLogger';
export { EnvConfigProvider } from './adapters/EnvConfigProvider';
export { MemoryStorageAdapter } from './adapters/MemoryStorageAdapter';
export { 
  GeminiProviderAdapter, 
  createGeminiAdapter,
  type GeminiAdapterConfig,
} from './adapters/GeminiProviderAdapter';

// ============================================================================
// CONVENIENCE FACTORY (Turnkey Defaults)
// ============================================================================
import { ConsoleLogger } from './adapters/ConsoleLogger';
import { EnvConfigProvider } from './adapters/EnvConfigProvider';
import { MemoryStorageAdapter } from './adapters/MemoryStorageAdapter';
import { ChatEngine } from './core/ChatEngine';
import type { IAIProvider } from './interfaces';

/**
 * Quick-start factory that creates a ChatEngine with sensible defaults.
 * 
 * This factory provides the easiest path to using the chat engine:
 * - ConsoleLogger for logging
 * - EnvConfigProvider for configuration
 * - MemoryStorageAdapter for conversation storage
 * 
 * Only the AI provider is required.
 * 
 * @param aiProvider - The AI provider adapter (Gemini, OpenAI, etc.)
 * @returns Configured ChatEngine instance ready to use
 * 
 * @example
 * import { GoogleGenAI } from "@google/genai";
 * import { createQuickStartEngine, createGeminiAdapter } from '@clearpath/chat-engine-core';
 * 
 * const gemini = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
 * const engine = createQuickStartEngine(createGeminiAdapter(gemini));
 * 
 * const response = await engine.chat('Hello!');
 * console.log(response.message.content);
 */
export function createQuickStartEngine(aiProvider: IAIProvider): ChatEngine {
  return new ChatEngine({
    aiProvider,
    config: new EnvConfigProvider(),
    logger: new ConsoleLogger(),
    storage: new MemoryStorageAdapter(),
  });
}

// ============================================================================
// DEPENDENCY SCANNER (NOTE-1509 Compliance)
// ============================================================================
export {
  DependencyScanner,
  runDependencyScan,
  type FileScanResult,
  type ImportInfo,
  type ImportViolation,
  type ScanReport,
} from './utils/dependencyScanner';

// ============================================================================
// MODULE METADATA
// ============================================================================

/**
 * Module version
 */
export const VERSION = '1.0.0';

/**
 * Module name
 */
export const MODULE_NAME = '@clearpath/chat-engine-core';

/**
 * Get module information
 */
export function getModuleInfo() {
  return {
    name: MODULE_NAME,
    version: VERSION,
    description: 'Isolated AI Chat Engine Core Module - TASK-860',
    features: [
      'Provider-agnostic AI integration',
      'Full chat orchestration',
      'Function calling support',
      'Circuit breaker resilience',
      'Response validation',
      'Token management',
      'Conversation persistence',
      'Introspection API',
    ],
    architecture: 'Hexagonal (Ports & Adapters)',
  };
}

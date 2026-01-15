/**
 * Chat Engine Core - Interface Definitions (Ports)
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * These interfaces define the contracts for external dependencies,
 * enabling clean separation and easy swapping of implementations.
 * 
 * Follows Hexagonal Architecture (Ports & Adapters) pattern.
 * Addresses NOTE-1509 Risk: Incomplete Dependency Abstraction
 */

// ============================================================================
// AI PROVIDER INTERFACE
// ============================================================================

/**
 * AI Content Request - Provider-agnostic request structure
 */
export interface AIContentRequest {
  model: string;
  contents: AIContent[];
  config?: AIGenerationConfig;
  tools?: AITool[];
  systemInstruction?: string;
}

export interface AIContent {
  role: 'user' | 'model' | 'system';
  parts: AIPart[];
}

export interface AIPart {
  text?: string;
  functionCall?: AIFunctionCall;
  functionResponse?: AIFunctionResponse;
}

export interface AIFunctionCall {
  name: string;
  args: Record<string, unknown>;
}

export interface AIFunctionResponse {
  name: string;
  response: unknown;
}

export interface AIGenerationConfig {
  temperature?: number;
  topP?: number;
  topK?: number;
  maxOutputTokens?: number;
  stopSequences?: string[];
  responseMimeType?: string;
}

export interface AITool {
  functionDeclarations?: AIFunctionDeclaration[];
}

export interface AIFunctionDeclaration {
  name: string;
  description: string;
  parameters: {
    type: 'object';
    properties: Record<string, AISchemaProperty>;
    required: string[];
  };
}

export interface AISchemaProperty {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object';
  description?: string;
  enum?: string[];
  items?: AISchemaProperty;
  properties?: Record<string, AISchemaProperty>;
  required?: string[];
}

/**
 * AI Content Response - Provider-agnostic response structure
 */
export interface AIContentResponse {
  text: string;
  candidates?: AICandidate[];
  usageMetadata?: AIUsageMetadata;
  functionCalls?: AIFunctionCall[];
}

export interface AICandidate {
  content: AIContent;
  finishReason?: string;
  safetyRatings?: AISafetyRating[];
}

export interface AISafetyRating {
  category: string;
  probability: string;
}

export interface AIUsageMetadata {
  promptTokenCount?: number;
  candidatesTokenCount?: number;
  totalTokenCount?: number;
}

/**
 * AI Streaming Chunk
 */
export interface AIChunk {
  text?: string;
  functionCall?: AIFunctionCall;
  usageMetadata?: AIUsageMetadata;
}

/**
 * Live Session Configuration
 */
export interface LiveSessionConfig {
  model: string;
  systemInstruction?: string;
  tools?: AITool[];
  voiceConfig?: {
    voiceName?: string;
    pitch?: number;
    speakingRate?: number;
  };
}

/**
 * Live Session Interface
 */
export interface ILiveSession {
  send(message: string): Promise<void>;
  sendAudio(data: ArrayBuffer): Promise<void>;
  receive(): AsyncIterable<AIChunk>;
  close(): Promise<void>;
}

/**
 * IAIProvider - Abstract interface for AI providers
 * Allows swapping between Gemini, OpenAI, Claude, etc.
 */
export interface IAIProvider {
  /** Provider name for logging/debugging */
  readonly name: string;
  
  /** Generate content (non-streaming) */
  generateContent(request: AIContentRequest): Promise<AIContentResponse>;
  
  /** Generate content with streaming */
  generateContentStream(request: AIContentRequest): Promise<AsyncIterable<AIChunk>>;
  
  /** Create a live/realtime session (optional capability) */
  createLiveSession?(config: LiveSessionConfig): Promise<ILiveSession>;
  
  /** Check if provider supports a specific model */
  supportsModel(model: string): boolean;
  
  /** Get available models */
  getAvailableModels(): string[];
}

// ============================================================================
// STORAGE ADAPTER INTERFACE
// ============================================================================

/**
 * Query filter for storage operations
 */
export interface QueryFilter {
  where?: Record<string, unknown>;
  orderBy?: { field: string; direction: 'asc' | 'desc' }[];
  limit?: number;
  offset?: number;
}

/**
 * IStorageAdapter - Abstract interface for data persistence
 * Allows swapping between in-memory, PostgreSQL, MongoDB, etc.
 */
export interface IStorageAdapter<T = unknown> {
  /** Get a single item by key */
  get(key: string): Promise<T | null>;
  
  /** Set/update an item */
  set(key: string, value: T): Promise<void>;
  
  /** Delete an item */
  delete(key: string): Promise<boolean>;
  
  /** Query multiple items */
  query(filter: QueryFilter): Promise<T[]>;
  
  /** Check if key exists */
  exists(key: string): Promise<boolean>;
  
  /** Get all keys (optional, for debugging) */
  keys?(): Promise<string[]>;
  
  /** Clear all data (optional, for testing) */
  clear?(): Promise<void>;
}

// ============================================================================
// DATABASE ADAPTER INTERFACE
// ============================================================================

/**
 * IDatabaseAdapter - Abstract interface for relational database operations
 * Allows swapping between PostgreSQL, MySQL, SQLite, etc.
 */
export interface IDatabaseAdapter {
  /** Execute a raw query */
  query<T = unknown>(sql: string, params?: unknown[]): Promise<T[]>;
  
  /** Execute a query returning a single row */
  queryOne<T = unknown>(sql: string, params?: unknown[]): Promise<T | null>;
  
  /** Execute an insert/update/delete and return affected rows */
  execute(sql: string, params?: unknown[]): Promise<{ affectedRows: number }>;
  
  /** Begin a transaction */
  beginTransaction(): Promise<ITransaction>;
  
  /** Check connection health */
  healthCheck(): Promise<boolean>;
}

export interface ITransaction {
  query<T = unknown>(sql: string, params?: unknown[]): Promise<T[]>;
  execute(sql: string, params?: unknown[]): Promise<{ affectedRows: number }>;
  commit(): Promise<void>;
  rollback(): Promise<void>;
}

// ============================================================================
// CIRCUIT BREAKER INTERFACE
// ============================================================================

export type CircuitBreakerState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export interface CircuitBreakerMetrics {
  name: string;
  state: CircuitBreakerState;
  failureCount: number;
  successCount: number;
  lastFailureTime: number | null;
  lastStateChange: number;
  totalTrips: number;
}

export interface CircuitBreakerConfig {
  name: string;
  failureThreshold: number;
  resetTimeoutMs: number;
  ignoredExceptions?: Array<new (...args: unknown[]) => Error>;
}

/**
 * ICircuitBreaker - Abstract interface for circuit breaker pattern
 */
export interface ICircuitBreaker {
  /** Execute a function through the circuit breaker */
  call<T>(fn: () => Promise<T>): Promise<T>;
  
  /** Get current state */
  getState(): CircuitBreakerState;
  
  /** Get metrics */
  getMetrics(): CircuitBreakerMetrics;
  
  /** Manual controls */
  close(): void;
  open(): void;
  halfOpen(): void;
  reset(): void;
}

// ============================================================================
// CONFIGURATION PROVIDER INTERFACE
// ============================================================================

/**
 * IConfigProvider - Abstract interface for configuration
 * Allows swapping between env vars, config files, remote config, etc.
 */
export interface IConfigProvider {
  /** Get a configuration value */
  get<T = string>(key: string, defaultValue?: T): T;
  
  /** Get a required configuration value (throws if missing) */
  getRequired<T = string>(key: string): T;
  
  /** Check if a key exists */
  has(key: string): boolean;
  
  /** Get all keys */
  keys(): string[];
  
  /** Subscribe to configuration changes (optional) */
  subscribe?(key: string, callback: (value: unknown) => void): () => void;
}

// ============================================================================
// LOGGER INTERFACE
// ============================================================================

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogContext {
  [key: string]: unknown;
}

/**
 * ILogger - Abstract interface for logging
 * Allows swapping between console, file, cloud logging, etc.
 */
export interface ILogger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, context?: LogContext): void;
  
  /** Create a child logger with additional context */
  child(context: LogContext): ILogger;
}

// ============================================================================
// PERSONA SERVICE INTERFACE
// ============================================================================

export interface Persona {
  id: string;
  name: string;
  role: string;
  description: string;
  systemPrompt?: string;
  traits?: string[];
  expertise?: string[];
}

/**
 * IPersonaService - Abstract interface for persona management
 */
export interface IPersonaService {
  /** Get a persona by ID */
  getById(id: string): Promise<Persona | null>;
  
  /** Get all personas */
  getAll(): Promise<Persona[]>;
  
  /** Suggest a persona based on context */
  suggest(context: string): Promise<Persona | null>;
  
  /** Get personas matching criteria */
  search(query: string): Promise<Persona[]>;
}

// ============================================================================
// VOICE SERVICE INTERFACE
// ============================================================================

export interface VoiceProfile {
  id: string;
  userId: string;
  name: string;
  settings?: Record<string, unknown>;
  trainingData?: string[];
}

/**
 * IVoiceService - Abstract interface for voice profile management
 */
export interface IVoiceService {
  /** Get a voice profile by ID */
  getById(id: string): Promise<VoiceProfile | null>;
  
  /** Get voice profile for a user */
  getByUserId(userId: string): Promise<VoiceProfile | null>;
  
  /** Create or update a voice profile */
  save(profile: VoiceProfile): Promise<VoiceProfile>;
  
  /** Invalidate cache for a profile */
  invalidateCache(profileId: string): Promise<void>;
  
  /** Analyze voice input */
  analyze?(audioData: ArrayBuffer): Promise<{ text: string; confidence: number }>;
}

// ============================================================================
// TOPIC LINKING SERVICE INTERFACE
// ============================================================================

export interface Topic {
  id: string;
  name: string;
  description?: string;
  parentId?: string;
  metadata?: Record<string, unknown>;
}

export interface TopicLink {
  sourceId: string;
  targetId: string;
  strength: number;
  type: string;
}

/**
 * ITopicLinkingService - Abstract interface for topic linking
 */
export interface ITopicLinkingService {
  /** Link an entity to topics */
  linkToTopics(entityId: string, entityType: string, topics: string[]): Promise<void>;
  
  /** Get topics for an entity */
  getTopicsForEntity(entityId: string, entityType: string): Promise<Topic[]>;
  
  /** Suggest topics based on content */
  suggestTopics(content: string): Promise<Topic[]>;
  
  /** Get related topics */
  getRelatedTopics(topicId: string): Promise<TopicLink[]>;
}

// ============================================================================
// METRICS SERVICE INTERFACE
// ============================================================================

export interface MetricEvent {
  name: string;
  value: number;
  tags?: Record<string, string>;
  timestamp?: number;
}

/**
 * IMetricsService - Abstract interface for metrics collection
 */
export interface IMetricsService {
  /** Record a counter metric */
  increment(name: string, value?: number, tags?: Record<string, string>): void;
  
  /** Record a gauge metric */
  gauge(name: string, value: number, tags?: Record<string, string>): void;
  
  /** Record a histogram/timing metric */
  histogram(name: string, value: number, tags?: Record<string, string>): void;
  
  /** Record a custom event */
  event(event: MetricEvent): void;
}

// ============================================================================
// FACTORY TYPES
// ============================================================================

/**
 * Dependencies container for creating chat engine instances
 * 
 * Required:
 * - aiProvider: The AI provider adapter (Gemini, OpenAI, etc.)
 * - config: Configuration provider
 * - logger: Logger implementation
 * 
 * Optional:
 * - storage: Conversation storage (no persistence if not provided)
 * - circuitBreaker, database, personaService, voiceService, topicService, metricsService
 * 
 * For convenience, use createChatEngineWithDefaults() which allows you to provide
 * factory functions for creating default adapters (ConsoleLogger, EnvConfigProvider, etc.)
 */
export interface ChatEngineDependencies {
  /** Required: AI provider implementation (Gemini, OpenAI, Claude, etc.) */
  aiProvider: IAIProvider;
  
  /** Required: Configuration provider */
  config: IConfigProvider;
  
  /** Required: Logger implementation */
  logger: ILogger;
  
  /** Optional: Conversation storage (no persistence if not provided) */
  storage?: IStorageAdapter;
  
  /** Optional: Circuit breaker for resilience (created automatically if not provided) */
  circuitBreaker?: ICircuitBreaker;
  
  /** Optional: Database adapter for persistence */
  database?: IDatabaseAdapter;
  
  /** Optional: Persona management service (reserved for future use) */
  personaService?: IPersonaService;
  
  /** Optional: Voice profile service (reserved for future use) */
  voiceService?: IVoiceService;
  
  /** Optional: Topic linking service (gracefully skipped if not provided) */
  topicService?: ITopicLinkingService;
  
  /** Optional: Metrics collection service (gracefully skipped if not provided) */
  metricsService?: IMetricsService;
}

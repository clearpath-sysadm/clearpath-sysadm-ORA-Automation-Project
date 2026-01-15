/**
 * Chat Engine Core - Main Chat Engine Implementation
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * The core chat engine that orchestrates AI conversations,
 * manages conversation state, and handles function calling.
 */

import type {
  IAIProvider,
  IStorageAdapter,
  IConfigProvider,
  ILogger,
  ICircuitBreaker,
  IPersonaService,
  IVoiceService,
  ITopicLinkingService,
  IMetricsService,
  ChatEngineDependencies,
  AIContentRequest,
  AIContentResponse,
  AIContent,
  AIPart,
  AIChunk,
  AIFunctionDeclaration,
} from '../interfaces';

import type {
  ChatMessage,
  ChatConversation,
  ConversationContext,
  FunctionDeclaration,
  PreflightResult,
  RetryOptions,
} from '../types';

import { ChatEngineError, ProviderError } from '../types';
import { CircuitBreaker, createAICircuitBreaker } from './CircuitBreaker';
import { ResponseValidator } from './ResponseValidator';
import { UsageTracker } from './UsageTracker';
import { TokenChecker } from './TokenChecker';
import { RetryHandler } from './RetryHandler';

/**
 * Chat request options
 */
export interface ChatRequestOptions {
  model?: string;
  systemPrompt?: string;
  functions?: FunctionDeclaration[];
  functionHandler?: (name: string, args: Record<string, unknown>) => Promise<unknown>;
  maxTokens?: number;
  temperature?: number;
  stream?: boolean;
  conversationId?: string;
  context?: ConversationContext;
}

/**
 * Chat response
 */
export interface ChatResponse {
  message: ChatMessage;
  conversation: ChatConversation;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  functionCalls?: Array<{ name: string; args: Record<string, unknown>; response?: unknown }>;
}

/**
 * Streaming chat response
 */
export interface StreamingChatResponse {
  stream: AsyncIterable<string>;
  getFullResponse: () => Promise<ChatResponse>;
}

/**
 * Chat Engine
 * 
 * Main orchestrator for AI chat interactions. Handles:
 * - Conversation management
 * - Token preflight checks
 * - Function calling
 * - Response validation
 * - Error handling with retry
 * - Usage tracking
 */
export class ChatEngine {
  private readonly aiProvider: IAIProvider;
  private readonly storage?: IStorageAdapter<ChatConversation>;
  private readonly config: IConfigProvider;
  private readonly logger: ILogger;
  private readonly circuitBreaker: ICircuitBreaker;
  private readonly personaService?: IPersonaService;
  private readonly voiceService?: IVoiceService;
  private readonly topicService?: ITopicLinkingService;
  private readonly metrics?: IMetricsService;

  private readonly validator: ResponseValidator;
  private readonly usageTracker: UsageTracker;
  private readonly tokenChecker: TokenChecker;
  private readonly retryHandler: RetryHandler;

  private readonly defaultModel: string;
  private readonly defaultSystemPrompt: string;

  constructor(dependencies: ChatEngineDependencies) {
    // Required dependencies
    if (!dependencies.aiProvider) {
      throw new Error('ChatEngine requires an aiProvider dependency');
    }
    if (!dependencies.config) {
      throw new Error('ChatEngine requires a config dependency. Use createChatEngineWithDefaults() for automatic defaults.');
    }
    if (!dependencies.logger) {
      throw new Error('ChatEngine requires a logger dependency. Use createChatEngineWithDefaults() for automatic defaults.');
    }
    
    this.aiProvider = dependencies.aiProvider;
    this.config = dependencies.config;
    this.logger = dependencies.logger;
    
    // Optional storage (null means no persistence)
    this.storage = dependencies.storage as IStorageAdapter<ChatConversation> | undefined;
    
    // Optional service dependencies (null-safe usage throughout)
    this.personaService = dependencies.personaService;
    this.voiceService = dependencies.voiceService;
    this.topicService = dependencies.topicService;
    this.metrics = dependencies.metricsService;
    
    // Create or use provided circuit breaker
    this.circuitBreaker = dependencies.circuitBreaker ?? createAICircuitBreaker(
      'chat_engine',
      { logger: this.logger }
    );
    
    // Initialize core components
    this.validator = new ResponseValidator({ 
      logger: this.logger, 
      configProvider: this.config 
    });
    this.usageTracker = new UsageTracker({ 
      logger: this.logger, 
      metrics: this.metrics 
    });
    this.tokenChecker = new TokenChecker({ 
      logger: this.logger 
    });
    this.retryHandler = new RetryHandler({ 
      logger: this.logger, 
      circuitBreaker: this.circuitBreaker 
    });
    
    // Load configuration
    this.defaultModel = this.config.get('AI_DEFAULT_MODEL', 'gemini-2.5-pro');
    this.defaultSystemPrompt = this.config.get('AI_DEFAULT_SYSTEM_PROMPT', 
      'You are a helpful AI assistant.');
  }

  /**
   * Send a chat message and get a response
   */
  public async chat(
    userMessage: string,
    options: ChatRequestOptions = {}
  ): Promise<ChatResponse> {
    const startTime = Date.now();
    const model = options.model ?? this.defaultModel;
    const systemPrompt = options.systemPrompt ?? this.defaultSystemPrompt;
    
    this.logger.info('Processing chat request', { 
      model, 
      messageLength: userMessage.length,
      hasConversation: !!options.conversationId,
      hasFunctions: !!options.functions?.length
    });

    // Load or create conversation
    let conversation = await this.getOrCreateConversation(
      options.conversationId,
      options.context
    );
    
    // Build conversation history
    const history = this.buildHistory(conversation);
    
    // Preflight token check
    const tokenCheck = this.tokenChecker.check(
      systemPrompt,
      history,
      userMessage,
      model
    );
    
    if (!tokenCheck.passed) {
      this.logger.warn('Token check failed', { 
        totalTokens: tokenCheck.totalTokens,
        limit: tokenCheck.limit
      });
      throw new ChatEngineError(
        tokenCheck.message,
        'TOKEN_LIMIT_EXCEEDED',
        { breakdown: tokenCheck.breakdown }
      );
    }

    // Add user message to conversation
    const userChatMessage: ChatMessage = {
      id: this.generateId(),
      role: 'user',
      content: userMessage,
      timestamp: Date.now(),
    };
    conversation.messages.push(userChatMessage);

    try {
      // Build AI request
      const request = this.buildRequest(
        systemPrompt,
        history,
        userMessage,
        model,
        options
      );

      // Execute with retry and circuit breaker
      const response = await this.retryHandler.executeWithCircuitBreaker(
        () => this.aiProvider.generateContent(request),
        'chat',
        { maxAttempts: 3 }
      );

      // Handle function calls if present
      let functionCalls: ChatResponse['functionCalls'] = undefined;
      if (response.functionCalls && response.functionCalls.length > 0 && options.functionHandler) {
        functionCalls = await this.handleFunctionCalls(
          response.functionCalls,
          options.functionHandler
        );
      }

      // Validate response
      const validationResult = this.validator.validate(response.text);
      if (!validationResult.isValid) {
        this.logger.warn('Response validation failed', { error: validationResult.error });
      }

      // Create assistant message
      const assistantMessage: ChatMessage = {
        id: this.generateId(),
        role: 'assistant',
        content: response.text,
        timestamp: Date.now(),
        metadata: {
          model,
          tokens: response.usageMetadata?.totalTokenCount,
          functionCalls: functionCalls?.map(fc => ({ name: fc.name, args: fc.args })),
          processingTimeMs: Date.now() - startTime,
        },
      };
      conversation.messages.push(assistantMessage);
      conversation.updatedAt = Date.now();

      // Track usage
      this.usageTracker.logUsage(model, 'chat', userMessage, true);
      
      // Emit metrics
      if (this.metrics) {
        this.metrics.histogram('chat_latency_ms', Date.now() - startTime, { model });
        this.metrics.increment('chat_requests', 1, { model, success: 'true' });
      }

      // Save conversation
      if (this.storage) {
        await this.storage.set(conversation.id, conversation);
      }

      // Link to topics if service available
      if (this.topicService && conversation.context?.entityId) {
        try {
          const topics = await this.topicService.suggestTopics(userMessage + ' ' + response.text);
          if (topics.length > 0) {
            await this.topicService.linkToTopics(
              conversation.context.entityId,
              conversation.context.entityType || 'conversation',
              topics.map(t => t.id)
            );
          }
        } catch (e) {
          this.logger.warn('Topic linking failed', { error: String(e) });
        }
      }

      return {
        message: assistantMessage,
        conversation,
        usage: response.usageMetadata ? {
          promptTokens: response.usageMetadata.promptTokenCount || 0,
          completionTokens: response.usageMetadata.candidatesTokenCount || 0,
          totalTokens: response.usageMetadata.totalTokenCount || 0,
        } : undefined,
        functionCalls,
      };

    } catch (error) {
      this.usageTracker.logUsage(model, 'chat', userMessage, false);
      
      if (this.metrics) {
        this.metrics.increment('chat_requests', 1, { model, success: 'false' });
      }
      
      throw this.wrapError(error);
    }
  }

  /**
   * Send a chat message with streaming response
   */
  public async chatStream(
    userMessage: string,
    options: ChatRequestOptions = {}
  ): Promise<StreamingChatResponse> {
    const model = options.model ?? this.defaultModel;
    const systemPrompt = options.systemPrompt ?? this.defaultSystemPrompt;
    
    // Load or create conversation
    let conversation = await this.getOrCreateConversation(
      options.conversationId,
      options.context
    );
    
    const history = this.buildHistory(conversation);
    
    // Preflight token check
    const tokenCheck = this.tokenChecker.check(
      systemPrompt,
      history,
      userMessage,
      model
    );
    
    if (!tokenCheck.passed) {
      throw new ChatEngineError(
        tokenCheck.message,
        'TOKEN_LIMIT_EXCEEDED',
        { breakdown: tokenCheck.breakdown }
      );
    }

    // Add user message
    const userChatMessage: ChatMessage = {
      id: this.generateId(),
      role: 'user',
      content: userMessage,
      timestamp: Date.now(),
    };
    conversation.messages.push(userChatMessage);

    // Build request
    const request = this.buildRequest(
      systemPrompt,
      history,
      userMessage,
      model,
      options
    );

    // Get stream
    const streamIterable = await this.retryHandler.executeWithCircuitBreaker(
      () => this.aiProvider.generateContentStream(request),
      'chat_stream'
    );

    let fullText = '';
    const startTime = Date.now();

    // Create async generator for streaming
    const self = this;
    async function* streamGenerator(): AsyncIterable<string> {
      for await (const chunk of streamIterable) {
        if (chunk.text) {
          fullText += chunk.text;
          yield chunk.text;
        }
      }
    }

    return {
      stream: streamGenerator(),
      getFullResponse: async (): Promise<ChatResponse> => {
        // Create assistant message with collected text
        const assistantMessage: ChatMessage = {
          id: self.generateId(),
          role: 'assistant',
          content: fullText,
          timestamp: Date.now(),
          metadata: {
            model,
            processingTimeMs: Date.now() - startTime,
          },
        };
        conversation.messages.push(assistantMessage);
        conversation.updatedAt = Date.now();

        // Track usage
        self.usageTracker.logUsage(model, 'chat_stream', userMessage, true);

        // Save conversation
        if (self.storage) {
          await self.storage.set(conversation.id, conversation);
        }

        return {
          message: assistantMessage,
          conversation,
        };
      },
    };
  }

  /**
   * Get or create a conversation
   */
  public async getConversation(conversationId: string): Promise<ChatConversation | null> {
    if (!this.storage) return null;
    return this.storage.get(conversationId);
  }

  /**
   * Clear conversation history
   */
  public async clearConversation(conversationId: string): Promise<void> {
    if (this.storage) {
      await this.storage.delete(conversationId);
    }
  }

  /**
   * Get usage statistics
   */
  public getUsageStats() {
    return this.usageTracker.getStats();
  }

  /**
   * Get circuit breaker status
   */
  public getCircuitBreakerStatus() {
    return this.circuitBreaker.getMetrics();
  }

  /**
   * Check if provider supports a model
   */
  public supportsModel(model: string): boolean {
    return this.aiProvider.supportsModel(model);
  }

  /**
   * Get available models
   */
  public getAvailableModels(): string[] {
    return this.aiProvider.getAvailableModels();
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  private async getOrCreateConversation(
    conversationId?: string,
    context?: ConversationContext
  ): Promise<ChatConversation> {
    if (conversationId && this.storage) {
      const existing = await this.storage.get(conversationId);
      if (existing) return existing;
    }

    return {
      id: conversationId ?? this.generateId(),
      messages: [],
      context,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
  }

  private buildHistory(conversation: ChatConversation): AIContent[] {
    return conversation.messages.map(msg => ({
      role: msg.role === 'user' ? 'user' : 'model',
      parts: [{ text: msg.content }],
    }));
  }

  private buildRequest(
    systemPrompt: string,
    history: AIContent[],
    userMessage: string,
    model: string,
    options: ChatRequestOptions
  ): AIContentRequest {
    const contents: AIContent[] = [
      ...history,
      { role: 'user', parts: [{ text: userMessage }] },
    ];

    const request: AIContentRequest = {
      model,
      contents,
      systemInstruction: systemPrompt,
      config: {
        temperature: options.temperature,
        maxOutputTokens: options.maxTokens,
      },
    };

    // Add function declarations if provided
    if (options.functions && options.functions.length > 0) {
      request.tools = [{
        functionDeclarations: options.functions.map(fn => ({
          name: fn.name,
          description: fn.description,
          parameters: fn.parameters,
        })),
      }];
    }

    return request;
  }

  private async handleFunctionCalls(
    calls: Array<{ name: string; args: Record<string, unknown> }>,
    handler: (name: string, args: Record<string, unknown>) => Promise<unknown>
  ): Promise<Array<{ name: string; args: Record<string, unknown>; response?: unknown }>> {
    const results: Array<{ name: string; args: Record<string, unknown>; response?: unknown }> = [];

    for (const call of calls) {
      try {
        this.logger.debug('Executing function call', { name: call.name });
        const response = await handler(call.name, call.args);
        results.push({ name: call.name, args: call.args, response });
      } catch (error) {
        this.logger.error('Function call failed', { 
          name: call.name, 
          error: String(error) 
        });
        results.push({ 
          name: call.name, 
          args: call.args, 
          response: { error: String(error) } 
        });
      }
    }

    return results;
  }

  private wrapError(error: unknown): ChatEngineError {
    if (error instanceof ChatEngineError) {
      return error;
    }

    const message = error instanceof Error ? error.message : String(error);
    
    if (message.includes('429') || message.includes('RESOURCE_EXHAUSTED')) {
      return new ChatEngineError(
        'AI service rate limit exceeded. Please try again later.',
        'RATE_LIMIT_EXCEEDED',
        { originalError: message }
      );
    }
    
    if (message.includes('503') || message.includes('UNAVAILABLE')) {
      return new ChatEngineError(
        'AI service temporarily unavailable. Please try again.',
        'SERVICE_UNAVAILABLE',
        { originalError: message }
      );
    }

    return new ChatEngineError(
      `Chat request failed: ${message}`,
      'CHAT_ERROR',
      { originalError: message }
    );
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * Factory function to create a chat engine with explicit dependencies
 * 
 * @param dependencies - All required dependencies must be provided
 * @returns Configured ChatEngine instance
 * 
 * @example
 * const engine = createChatEngine({
 *   aiProvider: myGeminiAdapter,
 *   config: myConfigProvider,
 *   logger: myLogger,
 * });
 */
export function createChatEngine(dependencies: ChatEngineDependencies): ChatEngine {
  return new ChatEngine(dependencies);
}

/**
 * Minimal dependencies for createChatEngineWithDefaults
 */
export interface MinimalChatEngineDependencies {
  aiProvider: IAIProvider;
  config?: IConfigProvider;
  logger?: ILogger;
  storage?: IStorageAdapter;
  circuitBreaker?: ICircuitBreaker;
  personaService?: IPersonaService;
  voiceService?: IVoiceService;
  topicService?: ITopicLinkingService;
  metricsService?: IMetricsService;
}

/**
 * Factory function to create a chat engine with default adapters
 * 
 * This factory provides sensible defaults for config, logger, and storage,
 * keeping the core ChatEngine free from direct adapter dependencies.
 * 
 * @param dependencies - Only aiProvider is required; others have defaults
 * @param defaultAdapters - Factory functions for creating default adapters
 * @returns Configured ChatEngine instance
 * 
 * @example
 * import { createChatEngineWithDefaults, ConsoleLogger, EnvConfigProvider, MemoryStorageAdapter } from '@clearpath/chat-engine-core';
 * 
 * const engine = createChatEngineWithDefaults(
 *   { aiProvider: myGeminiAdapter },
 *   {
 *     createLogger: () => new ConsoleLogger(),
 *     createConfig: () => new EnvConfigProvider(),
 *     createStorage: () => new MemoryStorageAdapter(),
 *   }
 * );
 */
export function createChatEngineWithDefaults(
  dependencies: MinimalChatEngineDependencies,
  defaultAdapters: {
    createLogger: () => ILogger;
    createConfig: () => IConfigProvider;
    createStorage?: () => IStorageAdapter;
  }
): ChatEngine {
  return new ChatEngine({
    aiProvider: dependencies.aiProvider,
    config: dependencies.config ?? defaultAdapters.createConfig(),
    logger: dependencies.logger ?? defaultAdapters.createLogger(),
    storage: dependencies.storage ?? defaultAdapters.createStorage?.(),
    circuitBreaker: dependencies.circuitBreaker,
    personaService: dependencies.personaService,
    voiceService: dependencies.voiceService,
    topicService: dependencies.topicService,
    metricsService: dependencies.metricsService,
  });
}

/**
 * Chat Engine Core - Gemini Provider Adapter (Template)
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * This is a template adapter for Google Gemini AI.
 * Host applications should implement this adapter with their
 * own @google/genai dependency.
 * 
 * NOTE: This file does NOT import @google/genai to maintain isolation.
 * It serves as a reference implementation pattern.
 */

import type {
  IAIProvider,
  AIContentRequest,
  AIContentResponse,
  AIChunk,
  LiveSessionConfig,
  ILiveSession,
  ILogger,
} from '../interfaces';

import { ProviderError } from '../types';

/**
 * Gemini SDK types (for reference - not imported)
 */
interface GeminiSDK {
  models: {
    generateContent(params: unknown): Promise<unknown>;
    generateContentStream(params: unknown): Promise<unknown>;
  };
}

/**
 * Gemini Provider Adapter Configuration
 */
export interface GeminiAdapterConfig {
  apiKey: string;
  defaultModel?: string;
  logger?: ILogger;
}

/**
 * Gemini Provider Adapter
 * 
 * Template implementation for integrating with Google Gemini AI.
 * 
 * @example
 * // In host application:
 * import { GoogleGenAI } from "@google/genai";
 * import { GeminiProviderAdapter } from "@clearpath/chat-engine-core";
 * 
 * const gemini = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
 * const adapter = new GeminiProviderAdapter({
 *   sdk: gemini,
 *   defaultModel: 'gemini-2.5-pro'
 * });
 */
export class GeminiProviderAdapter implements IAIProvider {
  readonly name = 'gemini';
  
  private readonly sdk: GeminiSDK;
  private readonly defaultModel: string;
  private readonly logger?: ILogger;

  private readonly supportedModels = [
    'gemini-2.5-pro',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-pro',
    'gemini-1.5-flash',
  ];

  /**
   * Create a Gemini provider adapter
   * 
   * @param options - Configuration including the SDK instance
   */
  constructor(options: {
    sdk: GeminiSDK;
    defaultModel?: string;
    logger?: ILogger;
  }) {
    this.sdk = options.sdk;
    this.defaultModel = options.defaultModel ?? 'gemini-2.5-pro';
    this.logger = options.logger;
  }

  async generateContent(request: AIContentRequest): Promise<AIContentResponse> {
    try {
      this.log('debug', `Generating content with model: ${request.model}`);
      
      const response = await this.sdk.models.generateContent({
        model: request.model || this.defaultModel,
        contents: this.transformContents(request.contents),
        config: request.config ? {
          temperature: request.config.temperature,
          topP: request.config.topP,
          topK: request.config.topK,
          maxOutputTokens: request.config.maxOutputTokens,
          stopSequences: request.config.stopSequences,
        } : undefined,
        systemInstruction: request.systemInstruction,
        tools: request.tools?.map(t => ({
          functionDeclarations: t.functionDeclarations,
        })),
      }) as any;

      return this.transformResponse(response);
    } catch (error) {
      this.log('error', `Gemini API error: ${error}`);
      throw new ProviderError(
        `Gemini API error: ${error instanceof Error ? error.message : String(error)}`,
        'gemini',
        (error as any)?.status
      );
    }
  }

  async generateContentStream(request: AIContentRequest): Promise<AsyncIterable<AIChunk>> {
    try {
      this.log('debug', `Starting stream with model: ${request.model}`);
      
      const stream = await this.sdk.models.generateContentStream({
        model: request.model || this.defaultModel,
        contents: this.transformContents(request.contents),
        config: request.config,
        systemInstruction: request.systemInstruction,
        tools: request.tools?.map(t => ({
          functionDeclarations: t.functionDeclarations,
        })),
      }) as AsyncIterable<any>;

      return this.transformStream(stream);
    } catch (error) {
      this.log('error', `Gemini stream error: ${error}`);
      throw new ProviderError(
        `Gemini stream error: ${error instanceof Error ? error.message : String(error)}`,
        'gemini',
        (error as any)?.status
      );
    }
  }

  supportsModel(model: string): boolean {
    return this.supportedModels.includes(model);
  }

  getAvailableModels(): string[] {
    return [...this.supportedModels];
  }

  private transformContents(contents: AIContentRequest['contents']): unknown[] {
    return contents.map(c => ({
      role: c.role === 'model' ? 'model' : c.role,
      parts: c.parts.map(p => {
        if (p.text) return { text: p.text };
        if (p.functionCall) return { functionCall: p.functionCall };
        if (p.functionResponse) return { functionResponse: p.functionResponse };
        return p;
      }),
    }));
  }

  private transformResponse(response: any): AIContentResponse {
    const candidate = response.candidates?.[0];
    const content = candidate?.content;
    
    // Extract text from parts
    let text = '';
    const functionCalls: AIContentResponse['functionCalls'] = [];
    
    if (content?.parts) {
      for (const part of content.parts) {
        if (part.text) text += part.text;
        if (part.functionCall) {
          functionCalls.push({
            name: part.functionCall.name,
            args: part.functionCall.args || {},
          });
        }
      }
    }

    return {
      text,
      candidates: response.candidates?.map((c: any) => ({
        content: c.content,
        finishReason: c.finishReason,
        safetyRatings: c.safetyRatings,
      })),
      usageMetadata: response.usageMetadata ? {
        promptTokenCount: response.usageMetadata.promptTokenCount,
        candidatesTokenCount: response.usageMetadata.candidatesTokenCount,
        totalTokenCount: response.usageMetadata.totalTokenCount,
      } : undefined,
      functionCalls: functionCalls.length > 0 ? functionCalls : undefined,
    };
  }

  private async *transformStream(stream: AsyncIterable<any>): AsyncIterable<AIChunk> {
    for await (const chunk of stream) {
      const candidate = chunk.candidates?.[0];
      const content = candidate?.content;
      
      if (content?.parts) {
        for (const part of content.parts) {
          if (part.text) {
            yield { text: part.text };
          }
          if (part.functionCall) {
            yield {
              functionCall: {
                name: part.functionCall.name,
                args: part.functionCall.args || {},
              },
            };
          }
        }
      }
      
      if (chunk.usageMetadata) {
        yield {
          usageMetadata: {
            promptTokenCount: chunk.usageMetadata.promptTokenCount,
            candidatesTokenCount: chunk.usageMetadata.candidatesTokenCount,
            totalTokenCount: chunk.usageMetadata.totalTokenCount,
          },
        };
      }
    }
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    if (this.logger) {
      this.logger[level](`[GeminiAdapter] ${message}`);
    }
  }
}

/**
 * Create a Gemini adapter from an SDK instance
 * 
 * @example
 * // In host application:
 * import { GoogleGenAI } from "@google/genai";
 * import { createGeminiAdapter } from "@clearpath/chat-engine-core";
 * 
 * const gemini = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
 * const adapter = createGeminiAdapter(gemini);
 */
export function createGeminiAdapter(
  sdk: GeminiSDK,
  options?: {
    defaultModel?: string;
    logger?: ILogger;
  }
): GeminiProviderAdapter {
  return new GeminiProviderAdapter({
    sdk,
    defaultModel: options?.defaultModel,
    logger: options?.logger,
  });
}

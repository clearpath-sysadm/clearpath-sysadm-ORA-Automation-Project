/**
 * Chat Engine Core - Type Definitions
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * 
 * Copied and adapted from shared/aiTypes.ts
 * Self-contained with no external dependencies.
 */

// ============================================================================
// ENTITY & CATEGORY TYPES
// ============================================================================

/**
 * Entity types supported by the AI function system.
 * Used for filtering functions based on the current entity context.
 */
export type AIEntityType = 'project' | 'task' | 'company' | 'contact' | 'global';

/**
 * Function category for grouping related functions.
 * Helps with organization and filtering of function declarations.
 */
export type AIFunctionCategory = 
  | 'task'
  | 'project'
  | 'project-management'
  | 'company'
  | 'contact'
  | 'persona'
  | 'navigation'
  | 'planner'
  | 'voice-training'
  | 'content'
  | 'briefing'
  | 'codebase'
  | 'logs'
  | 'universal';

// ============================================================================
// FUNCTION METADATA
// ============================================================================

/**
 * Metadata interface for AI function declarations.
 */
export interface AIFunctionMetadata {
  applicableTo: AIEntityType[];
  entityContext: Record<string, unknown>;
  category: AIFunctionCategory;
  isReadOnly?: boolean;
  displayName?: string;
}

/**
 * Schema property definition for function parameters.
 */
export interface SchemaProperty {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object';
  description?: string;
  enum?: string[];
  items?: SchemaProperty;
  properties?: Record<string, SchemaProperty>;
  required?: string[];
}

/**
 * Parameters schema for function declarations.
 */
export interface FunctionParameters {
  type: 'object';
  properties: Record<string, SchemaProperty>;
  required: string[];
}

/**
 * Complete function declaration for AI function calling.
 */
export interface FunctionDeclaration {
  name: string;
  description: string;
  parameters: FunctionParameters;
  metadata?: AIFunctionMetadata;
}

// ============================================================================
// FUNCTION FILTERING UTILITIES
// ============================================================================

/**
 * Type guard to check if a function declaration has metadata.
 */
export function hasMetadata(fn: FunctionDeclaration): fn is FunctionDeclaration & { metadata: AIFunctionMetadata } {
  return fn.metadata !== undefined;
}

/**
 * Filter function declarations by entity type using metadata.
 */
export function filterByEntityType(
  functions: FunctionDeclaration[],
  entityType: AIEntityType
): FunctionDeclaration[] {
  return functions.filter(fn => {
    if (!fn.metadata) return true;
    return fn.metadata.applicableTo.includes(entityType) || 
           fn.metadata.applicableTo.includes('global');
  });
}

/**
 * Filter function declarations by category using metadata.
 */
export function filterByCategory(
  functions: FunctionDeclaration[],
  category: AIFunctionCategory
): FunctionDeclaration[] {
  return functions.filter(fn => {
    if (!fn.metadata) return false;
    return fn.metadata.category === category;
  });
}

/**
 * Get only read-only functions (for query-only mode).
 */
export function filterReadOnly(functions: FunctionDeclaration[]): FunctionDeclaration[] {
  return functions.filter(fn => fn.metadata?.isReadOnly === true);
}

// ============================================================================
// DOCUMENTATION GENERATION
// ============================================================================

export interface DocumentationContextVariables {
  entityType?: AIEntityType;
  entityId?: string;
  entityName?: string;
  projectId?: string;
  projectName?: string;
  [key: string]: unknown;
}

export interface DocumentationOptions {
  includeParameters?: boolean;
  includeContextHints?: boolean;
  includeReadOnlyBadge?: boolean;
  categoryOrder?: AIFunctionCategory[];
}

const CATEGORY_DISPLAY_NAMES: Record<AIFunctionCategory, string> = {
  'task': 'Task Operations',
  'project': 'Project Operations',
  'project-management': 'Project Management',
  'company': 'Company Operations',
  'contact': 'Contact Operations',
  'persona': 'Expert Persona Operations',
  'navigation': 'Navigation Functions',
  'planner': 'Planner & Work Sessions',
  'voice-training': 'Voice Training',
  'content': 'Content Pipeline',
  'briefing': 'Morning Briefing',
  'codebase': 'Codebase Access',
  'logs': 'Server Logs',
  'universal': 'Universal Functions'
};

const DEFAULT_CATEGORY_ORDER: AIFunctionCategory[] = [
  'universal', 'task', 'project', 'project-management',
  'company', 'contact', 'persona', 'planner',
  'navigation', 'content', 'briefing', 'voice-training',
  'codebase', 'logs'
];

function formatParameter(name: string, prop: SchemaProperty, isRequired: boolean): string {
  const requiredBadge = isRequired ? ' (required)' : ' (optional)';
  const typeStr = prop.type === 'array' ? `array of ${prop.items?.type || 'items'}` : prop.type;
  const enumStr = prop.enum ? ` [${prop.enum.join(', ')}]` : '';
  const desc = prop.description ? ` - ${prop.description}` : '';
  return `    - \`${name}\`: ${typeStr}${enumStr}${requiredBadge}${desc}`;
}

function formatFunctionDoc(
  fn: FunctionDeclaration,
  entityType: AIEntityType,
  contextVars: DocumentationContextVariables,
  options: DocumentationOptions
): string {
  const lines: string[] = [];
  const displayName = fn.metadata?.displayName || fn.name;
  const readOnlyBadge = options.includeReadOnlyBadge && fn.metadata?.isReadOnly ? ' [read-only]' : '';
  lines.push(`- **${displayName}**${readOnlyBadge}`);
  
  let description = fn.description || 'No description provided.';
  if (contextVars) {
    for (const [key, value] of Object.entries(contextVars)) {
      if (value !== undefined && value !== null) {
        description = description.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), String(value));
      }
    }
  }
  lines.push(`  ${description}`);
  
  if (options.includeContextHints && fn.metadata?.entityContext?.[entityType]) {
    const contextInfo = fn.metadata.entityContext[entityType] as { hint?: string };
    if (contextInfo.hint) {
      lines.push(`  *Context: ${contextInfo.hint}*`);
    }
  }
  
  if (options.includeParameters && fn.parameters?.properties) {
    const paramNames = Object.keys(fn.parameters.properties);
    if (paramNames.length > 0) {
      lines.push('  Parameters:');
      const required = fn.parameters.required || [];
      for (const paramName of paramNames) {
        const prop = fn.parameters.properties[paramName];
        lines.push(formatParameter(paramName, prop, required.includes(paramName)));
      }
    }
  }
  
  return lines.join('\n');
}

function groupByCategory(functions: FunctionDeclaration[]): Map<AIFunctionCategory, FunctionDeclaration[]> {
  const groups = new Map<AIFunctionCategory, FunctionDeclaration[]>();
  
  for (const fn of functions) {
    const category: AIFunctionCategory = fn.metadata?.category || 'universal';
    if (!groups.has(category)) {
      groups.set(category, []);
    }
    groups.get(category)!.push(fn);
  }
  
  return groups;
}

/**
 * Generate formatted documentation string from function declarations.
 */
export function generateFunctionDocumentation(
  functions: FunctionDeclaration[] | null | undefined,
  entityType: AIEntityType,
  contextVariables: DocumentationContextVariables = {},
  options: DocumentationOptions = {}
): string {
  if (!functions || !Array.isArray(functions) || functions.length === 0) {
    return 'No functions provided.';
  }
  
  const validEntityTypes: AIEntityType[] = ['project', 'task', 'company', 'contact', 'global'];
  if (!validEntityTypes.includes(entityType)) {
    return `Invalid entity type: ${entityType}. Valid types: ${validEntityTypes.join(', ')}`;
  }
  
  const opts: DocumentationOptions = {
    includeParameters: options.includeParameters ?? true,
    includeContextHints: options.includeContextHints ?? true,
    includeReadOnlyBadge: options.includeReadOnlyBadge ?? true,
    categoryOrder: options.categoryOrder ?? DEFAULT_CATEGORY_ORDER
  };
  
  const contextVars: DocumentationContextVariables = { entityType, ...contextVariables };
  const groups = groupByCategory(functions);
  const outputSections: string[] = [];
  const orderedCategories = opts.categoryOrder!;
  const processedCategories = new Set<AIFunctionCategory>();
  
  for (const category of orderedCategories) {
    if (groups.has(category)) {
      const categoryFunctions = groups.get(category)!;
      const header = `## ${CATEGORY_DISPLAY_NAMES[category] || category}`;
      const functionDocs = categoryFunctions.map(fn => 
        formatFunctionDoc(fn, entityType, contextVars, opts)
      );
      outputSections.push(`${header}\n${functionDocs.join('\n\n')}`);
      processedCategories.add(category);
    }
  }
  
  for (const [category, categoryFunctions] of groups) {
    if (!processedCategories.has(category)) {
      const header = `## ${CATEGORY_DISPLAY_NAMES[category] || category}`;
      const functionDocs = categoryFunctions.map(fn => 
        formatFunctionDoc(fn, entityType, contextVars, opts)
      );
      outputSections.push(`${header}\n${functionDocs.join('\n\n')}`);
    }
  }
  
  return outputSections.join('\n\n');
}

// ============================================================================
// CHAT MESSAGE TYPES
// ============================================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  metadata?: ChatMessageMetadata;
}

export interface ChatMessageMetadata {
  model?: string;
  tokens?: number;
  functionCalls?: Array<{ name: string; args: Record<string, unknown> }>;
  functionResponses?: Array<{ name: string; response: unknown }>;
  processingTimeMs?: number;
}

export interface ChatConversation {
  id: string;
  messages: ChatMessage[];
  context?: ConversationContext;
  createdAt: number;
  updatedAt: number;
}

export interface ConversationContext {
  entityType?: AIEntityType;
  entityId?: string;
  persona?: string;
  systemPrompt?: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// VALIDATION TYPES
// ============================================================================

export interface ValidationConfig {
  minLength: number;
  maxLength: number;
  maxRetries: number;
  retryDelayMs: number;
}

export interface ValidationResult {
  isValid: boolean;
  error?: string;
  errorType?: 'length_too_short' | 'length_too_long' | 'json_parse_error' | 'null_or_empty';
  response?: string;
  parsedJson?: unknown;
}

export interface ValidationMetrics {
  totalValidations: number;
  validResponses: number;
  invalidResponses: number;
  failures: {
    lengthTooShort: number;
    lengthTooLong: number;
    jsonParseError: number;
    nullOrEmpty: number;
  };
  retries: {
    total: number;
    successful: number;
    exhausted: number;
  };
  lastFailureTime: number | null;
  lastFailureReason: string | null;
}

// ============================================================================
// TOKEN & USAGE TYPES
// ============================================================================

export interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

export interface UsageStats {
  last1Hour: { requests: number; tokens: number };
  last24Hours: { requests: number; tokens: number };
  byModel: Record<string, { requests: number; tokens: number }>;
  session: { requests: number; tokens: number; startTime: Date };
}

export interface PreflightResult {
  passed: boolean;
  totalTokens: number;
  breakdown: {
    systemPrompt: number;
    conversationHistory: number;
    userMessage: number;
  };
  limit: number;
  model: string;
  message: string;
}

// ============================================================================
// RETRY & ERROR TYPES
// ============================================================================

export interface RetryOptions {
  maxAttempts?: number;
  initialDelay?: number;
  backoffMultiplier?: number;
  retryableErrors?: string[];
}

export class ChatEngineError extends Error {
  public readonly code: string;
  public readonly timestamp: number;
  public readonly context?: Record<string, unknown>;

  constructor(message: string, code: string, context?: Record<string, unknown>) {
    super(message);
    this.name = 'ChatEngineError';
    this.code = code;
    this.timestamp = Date.now();
    this.context = context;
  }
}

export class ValidationError extends ChatEngineError {
  public readonly validationReason: string;

  constructor(message: string, reason: string) {
    super(message, 'VALIDATION_ERROR', { reason });
    this.name = 'ValidationError';
    this.validationReason = reason;
  }
}

export class CircuitBreakerOpenError extends ChatEngineError {
  constructor(message: string = 'Circuit breaker is open - service temporarily unavailable') {
    super(message, 'CIRCUIT_BREAKER_OPEN');
    this.name = 'CircuitBreakerOpenError';
  }
}

export class ProviderError extends ChatEngineError {
  public readonly provider: string;
  public readonly statusCode?: number;

  constructor(message: string, provider: string, statusCode?: number) {
    super(message, 'PROVIDER_ERROR', { provider, statusCode });
    this.name = 'ProviderError';
    this.provider = provider;
    this.statusCode = statusCode;
  }
}

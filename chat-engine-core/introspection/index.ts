/**
 * Chat Engine Core - Introspection API
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * REQ-271: Read-only access to module's own codebase
 * 
 * Provides secure, read-only access to the module's source code
 * for AI self-reflection and analysis.
 * 
 * Security Controls:
 * - Whitelist-only file access
 * - Read-only operations
 * - No external file system access
 * - Input validation and sanitization
 */

import * as fs from 'fs';
import * as path from 'path';
import type { ILogger } from '../interfaces';

/**
 * File metadata exposed by introspection
 */
export interface FileMetadata {
  name: string;
  path: string;
  size: number;
  type: 'file' | 'directory';
  extension?: string;
}

/**
 * Module metadata
 */
export interface ModuleMetadata {
  name: string;
  version: string;
  description: string;
  files: FileMetadata[];
  exports: string[];
  interfaces: string[];
  totalSize: number;
}

/**
 * File content result
 */
export interface FileContent {
  path: string;
  content: string;
  lineCount: number;
  size: number;
}

/**
 * Allowed file extensions for introspection
 */
const ALLOWED_EXTENSIONS = new Set(['.ts', '.js', '.json', '.md']);

/**
 * Files/directories to exclude from introspection
 */
const EXCLUDED_PATTERNS = [
  'node_modules',
  '.git',
  '.env',
  'secrets',
  'credentials',
  '.key',
  '.pem',
  '.cert',
];

/**
 * Introspection API
 * 
 * Provides secure, read-only access to the module's source code.
 * Implements security controls per NOTE-1509 risk mitigation.
 */
export class IntrospectionAPI {
  private readonly moduleRoot: string;
  private readonly logger?: ILogger;
  private readonly fileCache: Map<string, FileContent> = new Map();

  constructor(options?: {
    moduleRoot?: string;
    logger?: ILogger;
  }) {
    this.moduleRoot = options?.moduleRoot ?? path.resolve(__dirname, '..');
    this.logger = options?.logger;
  }

  /**
   * Get module metadata
   */
  public getModuleMetadata(): ModuleMetadata {
    const files = this.listFiles();
    
    return {
      name: '@clearpath/chat-engine-core',
      version: '1.0.0',
      description: 'Isolated AI Chat Engine Core Module',
      files,
      exports: this.getExports(),
      interfaces: this.getInterfaces(),
      totalSize: files.reduce((sum, f) => sum + f.size, 0),
    };
  }

  /**
   * List all accessible files in the module
   */
  public listFiles(subPath: string = ''): FileMetadata[] {
    const targetPath = this.resolvePath(subPath);
    
    if (!targetPath) {
      this.log('warn', `Invalid path requested: ${subPath}`);
      return [];
    }

    try {
      const files: FileMetadata[] = [];
      this.scanDirectory(targetPath, files, '');
      return files;
    } catch (error) {
      this.log('error', `Error listing files: ${error}`);
      return [];
    }
  }

  /**
   * Read file content
   */
  public readFile(filePath: string): FileContent | null {
    // Check cache first
    if (this.fileCache.has(filePath)) {
      return this.fileCache.get(filePath)!;
    }

    const resolvedPath = this.resolvePath(filePath);
    
    if (!resolvedPath) {
      this.log('warn', `Access denied for path: ${filePath}`);
      return null;
    }

    if (!this.isAllowedFile(resolvedPath)) {
      this.log('warn', `File type not allowed: ${filePath}`);
      return null;
    }

    try {
      const content = fs.readFileSync(resolvedPath, 'utf-8');
      const result: FileContent = {
        path: filePath,
        content,
        lineCount: content.split('\n').length,
        size: content.length,
      };
      
      // Cache the result
      this.fileCache.set(filePath, result);
      
      return result;
    } catch (error) {
      this.log('error', `Error reading file ${filePath}: ${error}`);
      return null;
    }
  }

  /**
   * Search for files matching a pattern
   */
  public searchFiles(pattern: string): FileMetadata[] {
    const allFiles = this.listFiles();
    const regex = new RegExp(pattern, 'i');
    
    return allFiles.filter(file => 
      regex.test(file.name) || regex.test(file.path)
    );
  }

  /**
   * Search for content within files
   */
  public searchContent(query: string, options?: {
    maxResults?: number;
    caseSensitive?: boolean;
  }): Array<{ file: string; line: number; content: string }> {
    const results: Array<{ file: string; line: number; content: string }> = [];
    const maxResults = options?.maxResults ?? 100;
    const caseSensitive = options?.caseSensitive ?? false;
    
    const searchPattern = caseSensitive ? query : query.toLowerCase();
    const allFiles = this.listFiles();
    
    for (const file of allFiles) {
      if (file.type !== 'file') continue;
      if (results.length >= maxResults) break;
      
      const content = this.readFile(file.path);
      if (!content) continue;
      
      const lines = content.content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = caseSensitive ? lines[i] : lines[i].toLowerCase();
        
        if (line.includes(searchPattern)) {
          results.push({
            file: file.path,
            line: i + 1,
            content: lines[i].trim().substring(0, 200),
          });
          
          if (results.length >= maxResults) break;
        }
      }
    }
    
    return results;
  }

  /**
   * Get list of exported symbols
   */
  public getExports(): string[] {
    const indexContent = this.readFile('index.ts');
    if (!indexContent) return [];
    
    const exports: string[] = [];
    const exportRegex = /export\s+(?:const|function|class|type|interface)\s+(\w+)/g;
    
    let match;
    while ((match = exportRegex.exec(indexContent.content)) !== null) {
      exports.push(match[1]);
    }
    
    return exports;
  }

  /**
   * Get list of interface definitions
   */
  public getInterfaces(): string[] {
    const files = this.listFiles('interfaces');
    const interfaces: string[] = [];
    
    for (const file of files) {
      if (file.type !== 'file') continue;
      
      const content = this.readFile(file.path);
      if (!content) continue;
      
      const interfaceRegex = /(?:export\s+)?interface\s+(\w+)/g;
      let match;
      while ((match = interfaceRegex.exec(content.content)) !== null) {
        interfaces.push(match[1]);
      }
    }
    
    return interfaces;
  }

  /**
   * Get type definitions for a specific interface
   */
  public getInterfaceDefinition(interfaceName: string): string | null {
    const files = this.listFiles();
    
    for (const file of files) {
      if (file.type !== 'file' || !file.path.endsWith('.ts')) continue;
      
      const content = this.readFile(file.path);
      if (!content) continue;
      
      // Find interface definition
      const interfaceRegex = new RegExp(
        `(?:export\\s+)?interface\\s+${interfaceName}\\s*(?:<[^>]*>)?\\s*\\{[^}]*\\}`,
        's'
      );
      
      const match = content.content.match(interfaceRegex);
      if (match) {
        return match[0];
      }
    }
    
    return null;
  }

  /**
   * Clear file cache
   */
  public clearCache(): void {
    this.fileCache.clear();
  }

  /**
   * Resolve and validate a path
   * Returns null if path is outside module root or matches excluded patterns
   */
  private resolvePath(requestedPath: string): string | null {
    // Sanitize input - remove any path traversal attempts
    const sanitized = requestedPath
      .replace(/\.\./g, '')
      .replace(/^[\/\\]+/, '')
      .replace(/[<>:"|?*]/g, '');
    
    const resolved = path.resolve(this.moduleRoot, sanitized);
    
    // Ensure path is within module root
    if (!resolved.startsWith(this.moduleRoot)) {
      return null;
    }
    
    // Check against excluded patterns
    for (const pattern of EXCLUDED_PATTERNS) {
      if (resolved.includes(pattern)) {
        return null;
      }
    }
    
    return resolved;
  }

  /**
   * Check if a file is allowed to be read
   */
  private isAllowedFile(filePath: string): boolean {
    const ext = path.extname(filePath).toLowerCase();
    
    // Allow directories
    try {
      if (fs.statSync(filePath).isDirectory()) {
        return true;
      }
    } catch {
      return false;
    }
    
    return ALLOWED_EXTENSIONS.has(ext);
  }

  /**
   * Recursively scan directory for files
   */
  private scanDirectory(
    dirPath: string,
    results: FileMetadata[],
    relativePath: string
  ): void {
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        const relPath = relativePath ? `${relativePath}/${entry.name}` : entry.name;
        
        // Skip excluded patterns
        if (EXCLUDED_PATTERNS.some(p => entry.name.includes(p))) {
          continue;
        }
        
        if (entry.isDirectory()) {
          results.push({
            name: entry.name,
            path: relPath,
            size: 0,
            type: 'directory',
          });
          this.scanDirectory(fullPath, results, relPath);
        } else if (entry.isFile() && this.isAllowedFile(fullPath)) {
          const stats = fs.statSync(fullPath);
          results.push({
            name: entry.name,
            path: relPath,
            size: stats.size,
            type: 'file',
            extension: path.extname(entry.name),
          });
        }
      }
    } catch (error) {
      this.log('error', `Error scanning directory ${dirPath}: ${error}`);
    }
  }

  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    const prefix = '[Introspection]';
    if (this.logger) {
      this.logger[level](`${prefix} ${message}`);
    } else if (level !== 'debug') {
      console.log(`${prefix} ${message}`);
    }
  }
}

/**
 * Create a singleton introspection API instance
 */
let introspectionInstance: IntrospectionAPI | null = null;

export function getIntrospectionAPI(options?: {
  moduleRoot?: string;
  logger?: ILogger;
}): IntrospectionAPI {
  if (!introspectionInstance) {
    introspectionInstance = new IntrospectionAPI(options);
  }
  return introspectionInstance;
}

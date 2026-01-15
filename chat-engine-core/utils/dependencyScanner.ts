/**
 * Chat Engine Core - Dependency Scanner
 * 
 * TASK-860: Isolated AI Chat Engine Module
 * NOTE-1509 Mitigation: Automated Dependency Scans
 * 
 * Scans module files for unintended external imports/dependencies.
 * Helps ensure clean separation from host application.
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * Allowed internal imports (within the module)
 */
const ALLOWED_INTERNAL_PREFIXES = [
  './',
  '../',
  './interfaces',
  './types',
  './core',
  './utils',
  './adapters',
  './introspection',
];

/**
 * Allowed external packages
 */
const ALLOWED_EXTERNAL_PACKAGES = new Set([
  'fs',
  'path',
  'crypto',
  'util',
  'events',
  'stream',
]);

/**
 * Blocked import patterns (indicate coupling to host app)
 */
const BLOCKED_PATTERNS = [
  '@shared/',
  '../storage',
  '../db',
  './gemini',
  './google',
  '@google/',
  'drizzle-orm',
  'express',
];

/**
 * Scan result for a single file
 */
export interface FileScanResult {
  file: string;
  imports: ImportInfo[];
  violations: ImportViolation[];
  isClean: boolean;
}

/**
 * Import information
 */
export interface ImportInfo {
  statement: string;
  source: string;
  line: number;
  type: 'internal' | 'external' | 'node-builtin';
}

/**
 * Import violation
 */
export interface ImportViolation {
  statement: string;
  source: string;
  line: number;
  reason: string;
  severity: 'error' | 'warning';
}

/**
 * Full scan report
 */
export interface ScanReport {
  timestamp: string;
  moduleRoot: string;
  filesScanned: number;
  filesWithViolations: number;
  totalViolations: number;
  violations: ImportViolation[];
  results: FileScanResult[];
  isClean: boolean;
}

/**
 * Dependency Scanner
 * 
 * Scans TypeScript/JavaScript files for import statements and
 * identifies violations of module isolation rules.
 */
export class DependencyScanner {
  private readonly moduleRoot: string;
  private readonly allowedExternals: Set<string>;
  private readonly blockedPatterns: string[];

  constructor(options?: {
    moduleRoot?: string;
    additionalAllowedPackages?: string[];
    additionalBlockedPatterns?: string[];
  }) {
    this.moduleRoot = options?.moduleRoot ?? path.resolve(__dirname, '..');
    this.allowedExternals = new Set([
      ...ALLOWED_EXTERNAL_PACKAGES,
      ...(options?.additionalAllowedPackages ?? []),
    ]);
    this.blockedPatterns = [
      ...BLOCKED_PATTERNS,
      ...(options?.additionalBlockedPatterns ?? []),
    ];
  }

  /**
   * Scan a single file for import violations
   */
  public scanFile(filePath: string): FileScanResult {
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');
    
    const imports: ImportInfo[] = [];
    const violations: ImportViolation[] = [];
    
    // Match import statements
    const importRegex = /^(?:import|export)\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]/;
    const requireRegex = /require\s*\(\s*['"]([^'"]+)['"]\s*\)/;
    
    lines.forEach((line, index) => {
      const lineNum = index + 1;
      const trimmedLine = line.trim();
      
      let match = trimmedLine.match(importRegex) || trimmedLine.match(requireRegex);
      
      if (match) {
        const source = match[1];
        const importInfo = this.classifyImport(source, trimmedLine, lineNum);
        imports.push(importInfo);
        
        const violation = this.checkViolation(source, trimmedLine, lineNum);
        if (violation) {
          violations.push(violation);
        }
      }
    });
    
    return {
      file: path.relative(this.moduleRoot, filePath),
      imports,
      violations,
      isClean: violations.length === 0,
    };
  }

  /**
   * Scan entire module directory
   */
  public scanModule(): ScanReport {
    const results: FileScanResult[] = [];
    const allViolations: ImportViolation[] = [];
    
    this.scanDirectory(this.moduleRoot, results);
    
    for (const result of results) {
      allViolations.push(...result.violations);
    }
    
    const filesWithViolations = results.filter(r => !r.isClean).length;
    
    return {
      timestamp: new Date().toISOString(),
      moduleRoot: this.moduleRoot,
      filesScanned: results.length,
      filesWithViolations,
      totalViolations: allViolations.length,
      violations: allViolations,
      results,
      isClean: allViolations.length === 0,
    };
  }

  /**
   * Generate HTML report
   */
  public generateHtmlReport(report: ScanReport): string {
    const statusClass = report.isClean ? 'pass' : 'fail';
    const statusText = report.isClean ? 'PASS' : 'FAIL';
    
    const violationRows = report.violations.map(v => `
      <tr class="${v.severity}">
        <td>${v.source}</td>
        <td>${v.reason}</td>
        <td>${v.severity.toUpperCase()}</td>
        <td><code>${this.escapeHtml(v.statement.substring(0, 80))}</code></td>
      </tr>
    `).join('');
    
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dependency Scan Report - TASK-860</title>
  <style>
    body { font-family: system-ui, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }
    h1, h2, h3 { color: #333; }
    .summary { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    .status { font-size: 24px; font-weight: bold; }
    .status.pass { color: #22c55e; }
    .status.fail { color: #ef4444; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #f9fafb; font-weight: 600; }
    tr.error { background: #fef2f2; }
    tr.warning { background: #fffbeb; }
    code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
    .metric { display: inline-block; margin-right: 30px; }
    .metric-value { font-size: 28px; font-weight: bold; color: #1f2937; }
    .metric-label { color: #6b7280; font-size: 14px; }
  </style>
</head>
<body>
  <h1>Dependency Scan Report</h1>
  <p><strong>TASK-860:</strong> Chat Engine Core Module Isolation</p>
  <p><strong>Generated:</strong> ${report.timestamp}</p>
  
  <div class="summary">
    <div class="status ${statusClass}">Overall Status: ${statusText}</div>
    <div style="margin-top: 20px;">
      <div class="metric">
        <div class="metric-value">${report.filesScanned}</div>
        <div class="metric-label">Files Scanned</div>
      </div>
      <div class="metric">
        <div class="metric-value">${report.filesWithViolations}</div>
        <div class="metric-label">Files with Violations</div>
      </div>
      <div class="metric">
        <div class="metric-value">${report.totalViolations}</div>
        <div class="metric-label">Total Violations</div>
      </div>
    </div>
  </div>
  
  ${report.violations.length > 0 ? `
  <h2>Violations</h2>
  <table>
    <thead>
      <tr>
        <th>Import Source</th>
        <th>Reason</th>
        <th>Severity</th>
        <th>Statement</th>
      </tr>
    </thead>
    <tbody>
      ${violationRows}
    </tbody>
  </table>
  ` : '<p>No violations found. Module is cleanly isolated.</p>'}
  
  <h2>Scan Details</h2>
  <p><strong>Module Root:</strong> <code>${report.moduleRoot}</code></p>
  <p><strong>Allowed External Packages:</strong> ${Array.from(this.allowedExternals).join(', ')}</p>
  <p><strong>Blocked Patterns:</strong> ${this.blockedPatterns.join(', ')}</p>
</body>
</html>`;
  }

  private scanDirectory(dirPath: string, results: FileScanResult[]): void {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dirPath, entry.name);
      
      if (entry.isDirectory()) {
        if (entry.name !== 'node_modules' && !entry.name.startsWith('.')) {
          this.scanDirectory(fullPath, results);
        }
      } else if (entry.isFile() && /\.(ts|js)$/.test(entry.name)) {
        results.push(this.scanFile(fullPath));
      }
    }
  }

  private classifyImport(source: string, statement: string, line: number): ImportInfo {
    let type: ImportInfo['type'];
    
    if (source.startsWith('.') || source.startsWith('/')) {
      type = 'internal';
    } else if (this.isNodeBuiltin(source)) {
      type = 'node-builtin';
    } else {
      type = 'external';
    }
    
    return { statement, source, line, type };
  }

  private checkViolation(source: string, statement: string, line: number): ImportViolation | null {
    // Check for blocked patterns
    for (const pattern of this.blockedPatterns) {
      if (source.includes(pattern)) {
        return {
          statement,
          source,
          line,
          reason: `Import matches blocked pattern: ${pattern}`,
          severity: 'error',
        };
      }
    }
    
    // Check for unallowed external packages
    if (!source.startsWith('.') && !source.startsWith('/')) {
      const packageName = source.split('/')[0];
      
      if (!this.isNodeBuiltin(packageName) && !this.allowedExternals.has(packageName)) {
        return {
          statement,
          source,
          line,
          reason: `External package "${packageName}" is not in allowed list`,
          severity: 'warning',
        };
      }
    }
    
    return null;
  }

  private isNodeBuiltin(name: string): boolean {
    const builtins = new Set([
      'fs', 'path', 'crypto', 'util', 'events', 'stream', 'buffer',
      'os', 'url', 'querystring', 'http', 'https', 'net', 'tls',
      'child_process', 'cluster', 'dgram', 'dns', 'domain',
      'assert', 'console', 'process', 'timers', 'v8', 'vm', 'zlib',
    ]);
    return builtins.has(name) || name.startsWith('node:');
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

/**
 * Run dependency scan and output results
 */
export function runDependencyScan(moduleRoot?: string): ScanReport {
  const scanner = new DependencyScanner({ moduleRoot });
  const report = scanner.scanModule();
  
  console.log('\n=== Dependency Scan Report ===');
  console.log(`Status: ${report.isClean ? 'PASS' : 'FAIL'}`);
  console.log(`Files Scanned: ${report.filesScanned}`);
  console.log(`Violations: ${report.totalViolations}`);
  
  if (!report.isClean) {
    console.log('\nViolations:');
    for (const v of report.violations) {
      console.log(`  [${v.severity.toUpperCase()}] ${v.source}: ${v.reason}`);
    }
  }
  
  return report;
}

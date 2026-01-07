"""
Server Logger Module
Provides file-based logging with rotation, log level filtering, and log reading utilities.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import pytz
import json
import re
from typing import List, Dict, Optional, Any

LOG_DIR = 'logs'
LOG_FILE = 'app.log'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 7  # Keep 7 rotated files
DEFAULT_LOG_LEVEL = 'INFO'

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

class ServerLogger:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ServerLogger._initialized:
            return
            
        self.log_path = os.path.join(LOG_DIR, LOG_FILE)
        self.logger = logging.getLogger('oracare')
        
        # Get log level from environment
        log_level_str = os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        self.logger.setLevel(log_level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # File handler with rotation
            file_handler = RotatingFileHandler(
                self.log_path,
                maxBytes=MAX_LOG_SIZE,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            
            # Format: ISO timestamp - LEVEL - source - message
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        ServerLogger._initialized = True
    
    def debug(self, message: str, source: str = 'app', user: str = None):
        actor = f'<{user}>' if user else '<system>'
        self.logger.debug(f'[{source}] {actor} {message}')
    
    def info(self, message: str, source: str = 'app', user: str = None):
        actor = f'<{user}>' if user else '<system>'
        self.logger.info(f'[{source}] {actor} {message}')
    
    def warning(self, message: str, source: str = 'app', user: str = None):
        actor = f'<{user}>' if user else '<system>'
        self.logger.warning(f'[{source}] {actor} {message}')
    
    def error(self, message: str, source: str = 'app', user: str = None, exc_info: bool = False):
        actor = f'<{user}>' if user else '<system>'
        self.logger.error(f'[{source}] {actor} {message}', exc_info=exc_info)
    
    def critical(self, message: str, source: str = 'app', user: str = None, exc_info: bool = False):
        actor = f'<{user}>' if user else '<system>'
        self.logger.critical(f'[{source}] {actor} {message}', exc_info=exc_info)


def get_logger() -> ServerLogger:
    """Get or create the singleton logger instance."""
    return ServerLogger()


def read_logs(
    level: str = 'ALL',
    source: str = 'ALL', 
    category: str = 'ALL',
    search_pattern: Optional[str] = None,
    last_n_lines: int = 500,
    hours_back: int = 24
) -> Dict[str, Any]:
    """
    Read and filter log entries from the log file.
    
    Args:
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, ALL)
        source: Filter by source/module name
        category: Filter by category (API, Database, ShipStation, etc.)
        search_pattern: Regex pattern to search in log messages
        last_n_lines: Maximum number of lines to return
        hours_back: Only include logs from the last N hours
        
    Returns:
        Dictionary with logs and statistics
    """
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    
    if not os.path.exists(log_path):
        return {
            'logs': [],
            'stats': {
                'total_lines': 0,
                'error_count': 0,
                'warning_count': 0,
                'info_count': 0,
                'debug_count': 0,
                'file_size': 0,
                'displayed_count': 0
            }
        }
    
    # Calculate cutoff time
    cst = pytz.timezone('America/Chicago')
    cutoff_time = datetime.now(cst) - timedelta(hours=hours_back)
    
    # Read all lines
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
    except Exception as e:
        return {
            'logs': [f'Error reading log file: {str(e)}'],
            'stats': {
                'total_lines': 0,
                'error_count': 0,
                'warning_count': 0,
                'info_count': 0,
                'debug_count': 0,
                'file_size': 0,
                'displayed_count': 0
            }
        }
    
    file_size = os.path.getsize(log_path)
    
    # Parse and filter logs
    filtered_logs = []
    stats = {
        'total_lines': len(all_lines),
        'error_count': 0,
        'warning_count': 0,
        'info_count': 0,
        'debug_count': 0,
        'file_size': file_size,
        'displayed_count': 0
    }
    
    # Log line pattern: 2024-01-01T12:00:00 - LEVEL - source - message
    log_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(\w+)\s*-\s*(\S+)\s*-\s*(.*)$')
    
    # Category patterns
    category_patterns = {
        'API': r'\[api\]|/api/|endpoint|request|response',
        'Database': r'\[database\]|\[db\]|postgres|sql|query|insert|update|delete',
        'ShipStation': r'\[shipstation\]|shipstation|order.*upload|sync',
        'Auth': r'\[auth\]|login|logout|session|token|permission',
        'Inventory': r'\[inventory\]|inventory|stock|lot|sku',
        'Scheduler': r'\[scheduler\]|\[cron\]|scheduled|polling|workflow',
        'Email': r'\[email\]|sendgrid|mail|notification',
        'Import': r'\[import\]|xml|google.*drive|import'
    }
    
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
            
        match = log_pattern.match(line)
        if match:
            timestamp_str, log_level, log_source, message = match.groups()
            
            # Count by level
            if log_level == 'ERROR':
                stats['error_count'] += 1
            elif log_level == 'WARNING':
                stats['warning_count'] += 1
            elif log_level == 'INFO':
                stats['info_count'] += 1
            elif log_level == 'DEBUG':
                stats['debug_count'] += 1
            
            # Filter by level
            if level != 'ALL' and log_level != level.upper():
                continue
            
            # Filter by source
            if source != 'ALL' and source.lower() not in log_source.lower():
                continue
            
            # Filter by category
            if category != 'ALL':
                category_pattern = category_patterns.get(category)
                if category_pattern and not re.search(category_pattern, line, re.IGNORECASE):
                    continue
            
            # Filter by search pattern
            if search_pattern:
                try:
                    if not re.search(search_pattern, line, re.IGNORECASE):
                        continue
                except re.error:
                    # Invalid regex, fall back to simple string search
                    if search_pattern.lower() not in line.lower():
                        continue
            
            # Filter by time
            try:
                log_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                log_time = cst.localize(log_time)
                if log_time < cutoff_time:
                    continue
            except ValueError:
                pass  # Keep line if timestamp parsing fails
            
            # Extract actor from message if present: [source] <actor> message
            actor = 'system'
            actor_match = re.match(r'^\[([^\]]+)\]\s*<([^>]+)>\s*(.*)$', message)
            if actor_match:
                msg_source, actor, clean_message = actor_match.groups()
            else:
                # Legacy format without actor
                clean_message = message
            
            filtered_logs.append({
                'timestamp': timestamp_str,
                'level': log_level,
                'source': log_source,
                'actor': actor,
                'message': clean_message,
                'raw': line
            })
        else:
            # Non-matching lines (stack traces, etc.) - append to previous log if exists
            if filtered_logs and line:
                filtered_logs[-1]['message'] += '\n' + line
                filtered_logs[-1]['raw'] += '\n' + line
    
    # Get last N lines
    filtered_logs = filtered_logs[-last_n_lines:]
    stats['displayed_count'] = len(filtered_logs)
    
    return {
        'logs': filtered_logs,
        'stats': stats
    }


def get_log_stats() -> Dict[str, Any]:
    """Get log file statistics without reading all content."""
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    
    if not os.path.exists(log_path):
        return {
            'file_exists': False,
            'file_size': 0,
            'file_size_human': '0 B',
            'last_modified': None,
            'backup_files': 0
        }
    
    file_size = os.path.getsize(log_path)
    last_modified = datetime.fromtimestamp(os.path.getmtime(log_path))
    
    # Count backup files
    backup_count = 0
    for i in range(1, BACKUP_COUNT + 1):
        if os.path.exists(f'{log_path}.{i}'):
            backup_count += 1
    
    # Human-readable size
    size_units = ['B', 'KB', 'MB', 'GB']
    size = file_size
    unit_index = 0
    while size >= 1024 and unit_index < len(size_units) - 1:
        size /= 1024
        unit_index += 1
    size_human = f'{size:.1f} {size_units[unit_index]}'
    
    return {
        'file_exists': True,
        'file_size': file_size,
        'file_size_human': size_human,
        'last_modified': last_modified.isoformat(),
        'backup_files': backup_count,
        'log_path': log_path
    }


def clear_old_logs(max_age_days: int = 30) -> int:
    """Delete log backup files older than max_age_days. Returns count of deleted files."""
    deleted_count = 0
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    
    for i in range(1, BACKUP_COUNT + 1):
        backup_path = f'{log_path}.{i}'
        if os.path.exists(backup_path):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
            if file_mtime < cutoff_time:
                try:
                    os.remove(backup_path)
                    deleted_count += 1
                except Exception:
                    pass
    
    return deleted_count


# Initialize logger on module import
logger = get_logger()

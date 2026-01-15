"""
Server Logger Module
Provides file-based logging with rotation, database persistence, log level filtering, and log reading utilities.
Logs persist in PostgreSQL database across republishes.
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
import threading

LOG_DIR = 'logs'
LOG_FILE = 'app.log'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 7  # Keep 7 rotated files
DEFAULT_LOG_LEVEL = 'INFO'

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def _write_log_to_db(level: str, source: str, actor: str, role: Optional[str], message: str):
    """Write log entry to database in a separate thread to avoid blocking."""
    try:
        from src.services.database.pg_utils import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO server_logs (level, source, actor, role, message)
            VALUES (%s, %s, %s, %s, %s)
        """, (level, source, actor, role, message))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass  # Silent fail - don't break logging if DB fails

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
            
            # Format: ISO timestamp - LEVEL - message (removed redundant logger name)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        ServerLogger._initialized = True
    
    def debug(self, message: str, source: str = 'app', user: str = None, role: str = None):
        actor = self._format_actor(user, role)
        self.logger.debug(f'[{source}] {actor} {message}')
        threading.Thread(target=_write_log_to_db, args=('DEBUG', source, user or 'system', role, message), daemon=True).start()
    
    def info(self, message: str, source: str = 'app', user: str = None, role: str = None):
        actor = self._format_actor(user, role)
        self.logger.info(f'[{source}] {actor} {message}')
        threading.Thread(target=_write_log_to_db, args=('INFO', source, user or 'system', role, message), daemon=True).start()
    
    def warning(self, message: str, source: str = 'app', user: str = None, role: str = None):
        actor = self._format_actor(user, role)
        self.logger.warning(f'[{source}] {actor} {message}')
        threading.Thread(target=_write_log_to_db, args=('WARNING', source, user or 'system', role, message), daemon=True).start()
    
    def error(self, message: str, source: str = 'app', user: str = None, role: str = None, exc_info: bool = False):
        actor = self._format_actor(user, role)
        self.logger.error(f'[{source}] {actor} {message}', exc_info=exc_info)
        threading.Thread(target=_write_log_to_db, args=('ERROR', source, user or 'system', role, message), daemon=True).start()
    
    def critical(self, message: str, source: str = 'app', user: str = None, role: str = None, exc_info: bool = False):
        actor = self._format_actor(user, role)
        self.logger.critical(f'[{source}] {actor} {message}', exc_info=exc_info)
        threading.Thread(target=_write_log_to_db, args=('CRITICAL', source, user or 'system', role, message), daemon=True).start()
    
    def _format_actor(self, user: str = None, role: str = None) -> str:
        """Format actor string with optional role"""
        if user:
            if role:
                return f'<{user}|{role}>'
            return f'<{user}>'
        return '<system>'


def get_logger() -> ServerLogger:
    """Get or create the singleton logger instance."""
    return ServerLogger()


def read_logs(
    level: str = 'ALL',
    source: str = 'ALL', 
    category: str = 'ALL',
    search_pattern: Optional[str] = None,
    last_n_lines: int = 500,
    hours_back: int = 24,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read and filter log entries from the log file.
    
    Args:
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, ALL)
        source: Filter by source/module name
        category: Filter by category (API, Database, ShipStation, etc.)
        search_pattern: Regex pattern to search in log messages
        last_n_lines: Maximum number of lines to return
        hours_back: Only include logs from the last N hours (ignored if start_time/end_time provided)
        start_time: ISO format start datetime (e.g., 2024-01-15T09:00)
        end_time: ISO format end datetime (e.g., 2024-01-15T17:00)
        
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
    
    # Calculate cutoff times
    cst = pytz.timezone('America/Chicago')
    
    # Use explicit date range if provided, otherwise fall back to hours_back
    if start_time:
        try:
            cutoff_start = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            cutoff_start = cst.localize(cutoff_start)
        except ValueError:
            cutoff_start = datetime.now(cst) - timedelta(hours=hours_back)
    else:
        cutoff_start = datetime.now(cst) - timedelta(hours=hours_back)
    
    if end_time:
        try:
            cutoff_end = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            cutoff_end = cst.localize(cutoff_end)
        except ValueError:
            cutoff_end = datetime.now(cst)
    else:
        cutoff_end = datetime.now(cst)
    
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
    
    # Log line pattern: 2024-01-01T12:00:00 - LEVEL - message (new format without logger name)
    # Also support old format with logger name for backwards compatibility
    log_pattern_new = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(\w+)\s*-\s*(.*)$')
    log_pattern_old = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(\w+)\s*-\s*\S+\s*-\s*(.*)$')
    
    # Category patterns
    category_patterns = {
        'API': r'\[api\]|/api/|endpoint|request|response',
        'Database': r'\[database\]|\[db\]|postgres|sql|query|insert|update|delete',
        'ShipStation': r'\[shipstation\]|shipstation|order.*upload|sync',
        'Auth': r'\[auth\]|login|logout|session|token|permission',
        'Inventory': r'\[inventory\]|inventory|stock|transaction',
        'SKU-Lot': r'\[sku-lot\]|sku.*lot|lot.*sku',
        'Scheduler': r'\[scheduler\]|\[cron\]|scheduled|polling|workflow',
        'Email': r'\[email\]|sendgrid|mail|notification',
        'Import': r'\[import\]|xml|google.*drive|import',
        'Reports': r'\[reports\]|eod|eow|eom|report'
    }
    
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
        
        # Try new format first, then old format for backwards compatibility
        match = log_pattern_new.match(line)
        if match:
            timestamp_str, log_level, message = match.groups()
        else:
            match = log_pattern_old.match(line)
            if match:
                timestamp_str, log_level, message = match.groups()
            else:
                # Non-matching line
                if filtered_logs and line:
                    filtered_logs[-1]['message'] += '\n' + line
                    filtered_logs[-1]['raw'] += '\n' + line
                continue
        
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
        
        # Filter by time range
        try:
            log_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
            log_time = cst.localize(log_time)
            if log_time < cutoff_start or log_time > cutoff_end:
                continue
        except ValueError:
            pass  # Keep line if timestamp parsing fails
        
        # Extract source, actor, and role from message: [source] <actor|role> message
        msg_source = 'app'
        actor = 'system'
        role = None
        clean_message = message
        
        actor_match = re.match(r'^\[([^\]]+)\]\s*<([^>]+)>\s*(.*)$', message)
        if actor_match:
            msg_source, actor_part, clean_message = actor_match.groups()
            # Parse actor and role if present: <user|role>
            if '|' in actor_part:
                actor, role = actor_part.split('|', 1)
            else:
                actor = actor_part
        
        filtered_logs.append({
            'timestamp': timestamp_str,
            'level': log_level,
            'source': msg_source,
            'actor': actor,
            'role': role,
            'message': clean_message,
            'raw': line
        })
    
    # Get last N lines and reverse for DESC order (newest first)
    filtered_logs = filtered_logs[-last_n_lines:]
    filtered_logs.reverse()  # DESC: newest first
    stats['displayed_count'] = len(filtered_logs)
    
    return {
        'logs': filtered_logs,
        'stats': stats
    }


def read_logs_from_db(
    level: str = 'ALL',
    source: str = 'ALL',
    search_pattern: Optional[str] = None,
    last_n_lines: int = 500,
    hours_back: int = 24,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read and filter log entries from the PostgreSQL database.
    These logs persist across republishes.
    """
    try:
        from src.services.database.pg_utils import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cst = pytz.timezone('America/Chicago')
        
        # Build time filter
        if start_time:
            try:
                cutoff_start = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
                cutoff_start = cst.localize(cutoff_start)
            except ValueError:
                cutoff_start = datetime.now(cst) - timedelta(hours=hours_back)
        else:
            cutoff_start = datetime.now(cst) - timedelta(hours=hours_back)
        
        if end_time:
            try:
                cutoff_end = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
                cutoff_end = cst.localize(cutoff_end)
            except ValueError:
                cutoff_end = datetime.now(cst)
        else:
            cutoff_end = datetime.now(cst)
        
        # Build query with filters
        conditions = ["timestamp >= %s", "timestamp <= %s"]
        params = [cutoff_start, cutoff_end]
        
        if level != 'ALL':
            conditions.append("level = %s")
            params.append(level.upper())
        
        if source != 'ALL':
            conditions.append("source = %s")
            params.append(source)
        
        if search_pattern:
            conditions.append("message ILIKE %s")
            params.append(f'%{search_pattern}%')
        
        where_clause = " AND ".join(conditions)
        
        # Get stats first
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE level = 'ERROR') as errors,
                COUNT(*) FILTER (WHERE level = 'WARNING') as warnings,
                COUNT(*) FILTER (WHERE level = 'INFO') as infos,
                COUNT(*) FILTER (WHERE level = 'DEBUG') as debugs
            FROM server_logs
            WHERE {where_clause}
        """, params)
        
        stats_row = cursor.fetchone()
        stats = {
            'total_lines': stats_row[0],
            'error_count': stats_row[1],
            'warning_count': stats_row[2],
            'info_count': stats_row[3],
            'debug_count': stats_row[4],
            'file_size': 0,
            'displayed_count': 0,
            'source': 'database'
        }
        
        # Get logs
        params.append(last_n_lines)
        cursor.execute(f"""
            SELECT timestamp, level, source, actor, role, message
            FROM server_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """, params)
        
        filtered_logs = []
        for row in cursor.fetchall():
            filtered_logs.append({
                'timestamp': row[0].strftime('%Y-%m-%dT%H:%M:%S') if row[0] else '',
                'level': row[1],
                'source': row[2] or 'app',
                'actor': row[3] or 'system',
                'role': row[4],
                'message': row[5],
                'raw': f"{row[0]} - {row[1]} - [{row[2]}] <{row[3]}> {row[5]}"
            })
        
        stats['displayed_count'] = len(filtered_logs)
        
        cursor.close()
        conn.close()
        
        return {
            'logs': filtered_logs,
            'stats': stats
        }
        
    except Exception as e:
        return {
            'logs': [{'message': f'Error reading logs from database: {str(e)}', 'level': 'ERROR', 'source': 'logger', 'timestamp': '', 'actor': 'system', 'role': None, 'raw': str(e)}],
            'stats': {'total_lines': 0, 'error_count': 1, 'warning_count': 0, 'info_count': 0, 'debug_count': 0, 'file_size': 0, 'displayed_count': 1, 'source': 'database'}
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

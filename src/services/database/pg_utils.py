"""
PostgreSQL database utilities - drop-in replacement for db_utils.py

Maintains same API interface for seamless migration from SQLite to PostgreSQL.
Uses psycopg2 for PostgreSQL connections.

Environment-aware database connection:
- Production (REPLIT_DEPLOYMENT=1): Uses PRODUCTION_DATABASE_URL or DATABASE_URL
- Development (workspace): Uses DATABASE_URL
"""

import os
import psycopg2
import psycopg2.extras
import time
import random
import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any

# Environment-aware database URL selection
IS_PRODUCTION = os.getenv('REPLIT_DEPLOYMENT') == '1'
if IS_PRODUCTION:
    DATABASE_URL = os.getenv('PRODUCTION_DATABASE_URL') or os.getenv('DATABASE_URL')
else:
    DATABASE_URL = os.getenv('DATABASE_URL')

logger = logging.getLogger(__name__)

_workflow_cache = {}
_cache_ttl = {}

def get_connection():
    """Get PostgreSQL connection"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    conn = psycopg2.connect(DATABASE_URL)
    # PostgreSQL enforces foreign keys by default (unlike SQLite)
    return conn

@contextmanager
def transaction():
    """Transaction context manager"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def transaction_with_retry(max_retries=10, initial_delay_ms=50):
    """
    Transaction context manager with exponential backoff retry.
    
    PostgreSQL has better concurrency than SQLite, so locks are less common.
    Kept for API compatibility.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 10)
        initial_delay_ms: Initial delay in milliseconds (default: 50ms)
    """
    retry_count = 0
    delay_ms = initial_delay_ms
    
    while True:
        try:
            conn = get_connection()
            try:
                yield conn
                conn.commit()
                return
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except psycopg2.Error as e:
            # PostgreSQL deadlock or serialization error
            if ("deadlock" in str(e).lower() or "serialize" in str(e).lower()) and retry_count < max_retries:
                retry_count += 1
                wait_time = delay_ms / 1000.0
                logger.warning(
                    f"Database conflict, retry {retry_count}/{max_retries} after {delay_ms}ms"
                )
                time.sleep(wait_time)
                delay_ms *= 2
                continue
            else:
                raise

def execute_query(sql: str, params: tuple = ()) -> List[Tuple[Any, ...]]:
    """
    Execute query and return results
    
    Note: Uses %s placeholders (PostgreSQL) instead of ? (SQLite)
    SQL strings should use %s for parameters
    """
    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

def upsert(table: str, data: dict, conflict_columns: list):
    """
    UPSERT implementation using PostgreSQL ON CONFLICT
    
    PostgreSQL uses %s placeholders instead of ?
    """
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    conflict = ', '.join(conflict_columns)
    update_clause = ', '.join([f"{k}=EXCLUDED.{k}" for k in data.keys()])
    
    sql = f"""
    INSERT INTO {table} ({columns}) VALUES ({placeholders})
    ON CONFLICT({conflict}) DO UPDATE SET {update_clause}
    """
    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(data.values()))

def is_workflow_enabled(workflow_name: str, cache_seconds: int = 45) -> bool:
    """
    Check if workflow is enabled with in-memory caching
    
    Args:
        workflow_name: Name of the workflow
        cache_seconds: Cache TTL (30-60s recommended, default 45s with jitter)
    
    Returns:
        bool: True if enabled, or if DB fails (fail-open)
    """
    now = time.time()
    
    # Check cache first
    if workflow_name in _workflow_cache:
        if now < _cache_ttl.get(workflow_name, 0):
            return _workflow_cache[workflow_name]
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT enabled FROM workflow_controls WHERE workflow_name = %s",
            (workflow_name,)
        )
        result = cursor.fetchone()
        conn.close()
        
        enabled = bool(result[0]) if result else True
        
        # Cache with jitter
        jitter = random.uniform(-10, 10)
        _workflow_cache[workflow_name] = enabled
        _cache_ttl[workflow_name] = now + cache_seconds + jitter
        
        return enabled
        
    except Exception as e:
        logger.error(f"DB error checking workflow status for {workflow_name}: {e}")
        logger.warning(f"Failing OPEN - {workflow_name} will continue")
        
        # Return cached value if available
        if workflow_name in _workflow_cache:
            logger.info(f"Using cached state for {workflow_name}: {_workflow_cache[workflow_name]}")
            return _workflow_cache[workflow_name]
        
        return True

def update_workflow_last_run(workflow_name: str):
    """
    Update the last_run_at timestamp for a workflow
    
    Args:
        workflow_name: Name of the workflow to update
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE workflow_controls SET last_run_at = CURRENT_TIMESTAMP WHERE workflow_name = %s",
            (workflow_name,)
        )
        conn.commit()
        conn.close()
        logger.debug(f"Updated last_run_at for workflow: {workflow_name}")
    except Exception as e:
        logger.error(f"Failed to update last_run_at for {workflow_name}: {e}")

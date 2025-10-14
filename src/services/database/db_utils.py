import os
import sqlite3
import time
import random
import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ora.db')
logger = logging.getLogger(__name__)

_workflow_cache = {}
_cache_ttl = {}

def get_connection():
    """Get SQLite connection with foreign keys enabled"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def transaction():
    """Transaction context manager with BEGIN IMMEDIATE"""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
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
    Transaction context manager with exponential backoff retry on database locks.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 10)
        initial_delay_ms: Initial delay in milliseconds (default: 50ms)
    
    The delay doubles with each retry: 50ms, 100ms, 200ms, 400ms, 800ms...
    Total max wait time with 10 retries: ~50 seconds
    """
    retry_count = 0
    delay_ms = initial_delay_ms
    
    while True:
        try:
            conn = get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
                return
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and retry_count < max_retries:
                retry_count += 1
                wait_time = delay_ms / 1000.0
                logger.warning(
                    f"Database locked, retry {retry_count}/{max_retries} after {delay_ms}ms"
                )
                time.sleep(wait_time)
                delay_ms *= 2
                continue
            else:
                raise

def execute_query(sql: str, params: tuple = ()) -> List[Tuple[Any, ...]]:
    """Execute query and return results"""
    with transaction() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

def upsert(table: str, data: dict, conflict_columns: list):
    """Simple UPSERT implementation"""
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    conflict = ', '.join(conflict_columns)
    update_clause = ', '.join([f"{k}=excluded.{k}" for k in data.keys()])
    
    sql = f"""
    INSERT INTO {table} ({columns}) VALUES ({placeholders})
    ON CONFLICT({conflict}) DO UPDATE SET {update_clause}
    """
    with transaction() as conn:
        conn.execute(sql, tuple(data.values()))

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
    
    if workflow_name in _workflow_cache:
        if now < _cache_ttl.get(workflow_name, 0):
            return _workflow_cache[workflow_name]
    
    try:
        conn = get_connection()
        cursor = conn.execute(
            "SELECT enabled FROM workflow_controls WHERE workflow_name = ?",
            (workflow_name,)
        )
        result = cursor.fetchone()
        conn.close()
        
        enabled = result[0] if result else True
        
        jitter = random.uniform(-10, 10)
        _workflow_cache[workflow_name] = enabled
        _cache_ttl[workflow_name] = now + cache_seconds + jitter
        
        return enabled
        
    except Exception as e:
        logger.error(f"DB error checking workflow status for {workflow_name}: {e}")
        logger.warning(f"Failing OPEN - {workflow_name} will continue")
        
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
        conn.execute(
            "UPDATE workflow_controls SET last_run_at = CURRENT_TIMESTAMP WHERE workflow_name = ?",
            (workflow_name,)
        )
        conn.commit()
        conn.close()
        logger.debug(f"Updated last_run_at for workflow: {workflow_name}")
    except Exception as e:
        logger.error(f"Failed to update last_run_at for {workflow_name}: {e}")

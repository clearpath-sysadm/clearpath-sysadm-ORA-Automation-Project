import os
import sqlite3
import time
import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ora.db')
logger = logging.getLogger(__name__)

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

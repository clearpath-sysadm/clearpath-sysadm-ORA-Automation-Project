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
    Update the last_run_at timestamp for a workflow in both tables
    
    Args:
        workflow_name: Name of the workflow to update
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Update both tables to ensure consistency
        cursor.execute(
            "UPDATE workflows SET last_run_at = CURRENT_TIMESTAMP WHERE name = %s",
            (workflow_name,)
        )
        workflows_updated = cursor.rowcount
        cursor.execute(
            "UPDATE workflow_controls SET last_run_at = CURRENT_TIMESTAMP WHERE workflow_name = %s",
            (workflow_name,)
        )
        controls_updated = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"✅ Updated last_run_at for {workflow_name} (workflows: {workflows_updated}, controls: {controls_updated})")
    except Exception as e:
        logger.error(f"❌ Failed to update last_run_at for {workflow_name}: {e}")


def eod_done_today() -> bool:
    """
    Check if EOD report has been run for today
    
    Returns:
        bool: True if EOD run today, False otherwise
    """
    import datetime
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM report_runs WHERE report_type = 'EOD' AND run_for_date = %s",
            (datetime.date.today(),)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Error checking EOD status: {e}")
        return False


def eow_done_this_week() -> bool:
    """
    Check if EOW report has been run for current week
    
    Returns:
        bool: True if EOW run this week, False otherwise
    """
    import datetime
    try:
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM report_runs WHERE report_type = 'EOW' AND run_for_date = %s",
            (week_start,)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Error checking EOW status: {e}")
        return False


def eom_done_this_month() -> bool:
    """
    Check if EOM report has been run for current month
    
    Returns:
        bool: True if EOM run this month, False otherwise
    """
    import datetime
    try:
        month_start = datetime.date.today().replace(day=1)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM report_runs WHERE report_type = 'EOM' AND run_for_date = %s",
            (month_start,)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Error checking EOM status: {e}")
        return False


def log_report_run(report_type: str, run_for_date, status: str = 'success', message: str = ''):
    """
    Log a report run to the database
    
    Args:
        report_type: Type of report ('EOD', 'EOW', 'EOM')
        run_for_date: Date the report covers (date object)
        status: Status of the run ('success', 'failed', 'in_progress')
        message: Optional message about the run
    """
    import datetime
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO report_runs (report_type, run_date, run_for_date, status, message)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (report_type, run_for_date) 
            DO UPDATE SET 
                run_date = EXCLUDED.run_date,
                status = EXCLUDED.status,
                message = EXCLUDED.message,
                created_at = NOW()
        """, (report_type, datetime.date.today(), run_for_date, status, message))
        conn.commit()
        conn.close()
        logger.info(f"Logged {report_type} report run for {run_for_date}: {status}")
    except Exception as e:
        logger.error(f"Failed to log {report_type} report run: {e}")


def get_last_report_runs():
    """
    Get the last run information for all report types
    
    Returns:
        dict: Dictionary with report types as keys and last run info as values
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT report_type, run_date, run_for_date, status, message
            FROM report_runs
            WHERE (report_type, run_date) IN (
                SELECT report_type, MAX(run_date)
                FROM report_runs
                GROUP BY report_type
            )
        """)
        results = cursor.fetchall()
        conn.close()
        
        report_status = {}
        for row in results:
            report_status[row[0]] = {
                'run_date': row[1].isoformat() if row[1] else None,
                'run_for_date': row[2].isoformat() if row[2] else None,
                'status': row[3],
                'message': row[4]
            }
        return report_status
    except Exception as e:
        logger.error(f"Error fetching last report runs: {e}")
        return {}

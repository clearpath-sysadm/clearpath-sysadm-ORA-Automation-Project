import os
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ora.db')

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

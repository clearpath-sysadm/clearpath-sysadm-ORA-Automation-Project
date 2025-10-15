"""
Database Adapter - Automatic SQLite/PostgreSQL switching

This module automatically chooses the correct database implementation
based on the DATABASE_URL environment variable presence.

If DATABASE_URL is set → Use PostgreSQL (pg_utils)
If DATABASE_URL is not set → Use SQLite (db_utils)

This allows for:
- Zero code changes in application files
- Easy rollback (just unset DATABASE_URL)
- Gradual testing and migration
"""

import os

# Determine which database to use
USE_POSTGRES = bool(os.getenv('DATABASE_URL'))

if USE_POSTGRES:
    # Use PostgreSQL
    from .pg_utils import (
        get_connection,
        transaction,
        transaction_with_retry,
        execute_query,
        upsert,
        is_workflow_enabled,
        update_workflow_last_run
    )
    DB_TYPE = "PostgreSQL"
else:
    # Use SQLite (original)
    from .db_utils import (
        get_connection,
        transaction,
        transaction_with_retry,
        execute_query,
        upsert,
        is_workflow_enabled,
        update_workflow_last_run
    )
    DB_TYPE = "SQLite"

# Export all functions (maintains same API)
__all__ = [
    'get_connection',
    'transaction',
    'transaction_with_retry',
    'execute_query',
    'upsert',
    'is_workflow_enabled',
    'update_workflow_last_run',
    'DB_TYPE',
    'USE_POSTGRES'
]

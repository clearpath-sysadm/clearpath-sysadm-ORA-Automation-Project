"""
Database Adapter - Automatic SQLite/PostgreSQL switching with Dev/Prod support

This module automatically chooses the correct database implementation
based on environment variables:

PRODUCTION MODE (REPLIT_DEPLOYMENT=1):
  - Uses PRODUCTION_DATABASE_URL if set
  - Falls back to DATABASE_URL if PRODUCTION_DATABASE_URL not set
  
DEVELOPMENT MODE (workspace):
  - Uses DATABASE_URL (development database)
  
FALLBACK:
  - Uses SQLite if no DATABASE_URL is set

This allows for:
- Automatic dev/prod database separation
- Zero code changes in application files
- Safe testing in development without affecting production data
"""

import os

# Determine environment and database URL
IS_PRODUCTION = os.getenv('REPLIT_DEPLOYMENT') == '1'

if IS_PRODUCTION:
    # Production: Use PRODUCTION_DATABASE_URL or fall back to DATABASE_URL
    DATABASE_URL = os.getenv('PRODUCTION_DATABASE_URL') or os.getenv('DATABASE_URL')
else:
    # Development: Use DATABASE_URL (dev database)
    DATABASE_URL = os.getenv('DATABASE_URL')

# Determine which database to use
USE_POSTGRES = bool(DATABASE_URL)

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

"""
Database Adapter - PostgreSQL implementation

This module provides database access using PostgreSQL.
Automatically handles dev/prod database separation via environment variables.

PRODUCTION MODE (REPLIT_DEPLOYMENT=1):
  - Uses PRODUCTION_DATABASE_URL if set
  - Falls back to DATABASE_URL if PRODUCTION_DATABASE_URL not set
  
DEVELOPMENT MODE (workspace):
  - Uses DATABASE_URL (development database)
"""

import os

# Always use PostgreSQL
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
USE_POSTGRES = True

# Export all functions
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

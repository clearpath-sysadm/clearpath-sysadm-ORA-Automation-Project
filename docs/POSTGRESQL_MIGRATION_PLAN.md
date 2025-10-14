# SQLite to PostgreSQL Migration Plan
## Resolving Replit Deployment Data Persistence Issues

---

## Executive Summary

**Problem:** SQLite database files are included in deployment snapshots. Every "Republish" replaces production's database with the dev snapshot, causing **catastrophic data loss** of all orders, shipments, and inventory updates processed since the last deployment.

**Solution:** Migrate to Replit's PostgreSQL database, which persists independently of deployments and provides true production data continuity.

**Effort:** 6-8 hours total
**Risk Level:** Medium (with proper validation and rollback procedures)
**Business Impact:** **CRITICAL** - Required for production reliability

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [Pre-Migration Preparation](#pre-migration-preparation)
3. [Phase 1: PostgreSQL Setup](#phase-1-postgresql-setup)
4. [Phase 2: Schema Migration](#phase-2-schema-migration)
5. [Phase 3: Data Migration](#phase-3-data-migration)
6. [Phase 4: Code Migration](#phase-4-code-migration)
7. [Phase 5: Testing & Validation](#phase-5-testing--validation)
8. [Phase 6: Production Cutover](#phase-6-production-cutover)
9. [Rollback Procedures](#rollback-procedures)
10. [Post-Migration Tasks](#post-migration-tasks)

---

## Migration Overview

### Current Architecture (SQLite - BROKEN)

```
Development Workspace:
  ├── ora.db (SQLite file)
  └── Python scripts → Read/Write to ora.db

Production Deployment:
  ├── ora.db (SNAPSHOT from publish time)
  └── Python scripts → Read/Write to SNAPSHOT
  
⚠️ PROBLEM: On republish → Production ora.db is REPLACED with dev snapshot
           → ALL production data LOST
```

### Target Architecture (PostgreSQL - PERSISTENT)

```
Development Workspace:
  └── Python scripts → PostgreSQL (dev database)

Production Deployment:
  └── Python scripts → PostgreSQL (prod database OR shared)
  
✅ SOLUTION: Database persists across ALL deployments
           → ZERO data loss on republish
```

### Migration Scope

**Database Changes:**
- ✅ Create Replit PostgreSQL database
- ✅ Migrate schema (12 tables, indexes, constraints)
- ✅ Migrate all current data from SQLite
- ✅ Set up environment variables for connection

**Code Changes:**
- ✅ Update `db_utils.py` for PostgreSQL support
- ✅ Replace `sqlite3` imports with `psycopg2`
- ✅ Update SQL syntax (SQLite → PostgreSQL differences)
- ✅ Update all automation scripts (8 scripts)
- ✅ Update Flask dashboard API endpoints
- ✅ Update HTML pages (minimal changes expected)

**Out of Scope:**
- ❌ No changes to business logic
- ❌ No changes to ShipStation integration
- ❌ No changes to Google Drive integration
- ❌ No changes to UI/UX

---

## Pre-Migration Preparation

### 1. Backup Current SQLite Database

```bash
# Create timestamped backup
cp ora.db backups/ora_pre_postgres_$(date +%Y%m%d_%H%M%S).db

# Verify backup integrity
sqlite3 backups/ora_pre_postgres_*.db "SELECT COUNT(*) FROM shipped_orders;"
```

**Checklist:**
- [ ] Backup created successfully
- [ ] Backup file is readable
- [ ] Row counts verified
- [ ] Backup stored safely (download from Replit)

### 2. Document Current State

```bash
# Export schema
sqlite3 ora.db ".schema" > backups/sqlite_schema_$(date +%Y%m%d).sql

# Export row counts
sqlite3 ora.db <<EOF > backups/sqlite_row_counts_$(date +%Y%m%d).txt
SELECT 'shipped_orders' as table_name, COUNT(*) as rows FROM shipped_orders
UNION ALL SELECT 'shipped_items', COUNT(*) FROM shipped_items
UNION ALL SELECT 'orders_inbox', COUNT(*) FROM orders_inbox
UNION ALL SELECT 'inventory_current', COUNT(*) FROM inventory_current
UNION ALL SELECT 'inventory_transactions', COUNT(*) FROM inventory_transactions
UNION ALL SELECT 'bundle_skus', COUNT(*) FROM bundle_skus
UNION ALL SELECT 'bundle_components', COUNT(*) FROM bundle_components
UNION ALL SELECT 'sku_lot', COUNT(*) FROM sku_lot
UNION ALL SELECT 'workflow_controls', COUNT(*) FROM workflow_controls
UNION ALL SELECT 'shipping_violations', COUNT(*) FROM shipping_violations
UNION ALL SELECT 'configuration_params', COUNT(*) FROM configuration_params
UNION ALL SELECT 'system_kpis', COUNT(*) FROM system_kpis;
EOF
```

**Checklist:**
- [ ] Schema exported
- [ ] Row counts documented
- [ ] Critical data identified (orders, inventory)
- [ ] Dependencies mapped

### 3. Install PostgreSQL Dependencies

```bash
# Install psycopg2 (PostgreSQL adapter for Python)
pip install psycopg2-binary

# Verify installation
python -c "import psycopg2; print('PostgreSQL driver installed successfully')"
```

### 4. Create Migration Workspace

```bash
# Create migration scripts directory
mkdir -p scripts/postgres_migration

# Create migration log directory
mkdir -p logs/migration
```

---

## Phase 1: PostgreSQL Setup

### 1.1 Create Replit PostgreSQL Database

**Using Replit Tools:**
1. Open your Replit project
2. Click "Tools" → "Database"
3. Select "PostgreSQL"
4. Click "Create Database"
5. Wait for provisioning (~2 minutes)

**Environment Variables (Auto-created by Replit):**
- `DATABASE_URL` - Full connection string
- `PGHOST` - Database host
- `PGPORT` - Database port (usually 5432)
- `PGUSER` - Database username
- `PGPASSWORD` - Database password
- `PGDATABASE` - Database name

### 1.2 Verify PostgreSQL Connection

```python
# scripts/test_postgres_connection.py
import os
import psycopg2

def test_connection():
    try:
        # Use DATABASE_URL from environment
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == '__main__':
    test_connection()
```

**Run test:**
```bash
python scripts/test_postgres_connection.py
```

**Expected output:**
```
✅ Connected to PostgreSQL: PostgreSQL 15.x on x86_64-pc-linux-gnu
```

---

## Phase 2: Schema Migration

### 2.1 Generate PostgreSQL Schema

**SQLite → PostgreSQL Syntax Differences:**

| SQLite | PostgreSQL |
|--------|------------|
| `INTEGER PRIMARY KEY` | `SERIAL PRIMARY KEY` or `BIGSERIAL PRIMARY KEY` |
| `TEXT` | `TEXT` or `VARCHAR(n)` |
| `REAL` | `NUMERIC` or `DOUBLE PRECISION` |
| `BLOB` | `BYTEA` |
| `DATETIME` | `TIMESTAMP` |
| `AUTOINCREMENT` | `SERIAL` |
| `PRAGMA foreign_keys = ON` | Enforced by default |
| `STRICT` tables | Use `CHECK` constraints |

### 2.2 Create PostgreSQL Schema Script

```sql
-- scripts/postgres_migration/01_create_schema.sql

-- Enable UUID extension (for future use)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Configuration Parameters Table
CREATE TABLE configuration_params (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    parameter_name VARCHAR(100) NOT NULL,
    value TEXT,
    sku VARCHAR(50),
    notes TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, parameter_name, sku)
);

-- 2. Workflow Controls Table
CREATE TABLE workflow_controls (
    workflow_name VARCHAR(100) PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50)
);

-- 3. Bundle SKUs Table
CREATE TABLE bundle_skus (
    bundle_sku VARCHAR(50) PRIMARY KEY,
    bundle_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bundle Components Table
CREATE TABLE bundle_components (
    id SERIAL PRIMARY KEY,
    bundle_sku VARCHAR(50) NOT NULL,
    component_sku VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bundle_sku) REFERENCES bundle_skus(bundle_sku) ON DELETE CASCADE,
    UNIQUE(bundle_sku, component_sku)
);

-- 5. SKU Lot Table
CREATE TABLE sku_lot (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    lot VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku, lot)
);

-- 6. Orders Inbox Table
CREATE TABLE orders_inbox (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_date TIMESTAMP,
    customer_name VARCHAR(200),
    shipping_method VARCHAR(100),
    total_amount INTEGER,
    items_json TEXT,
    source VARCHAR(50) DEFAULT 'XML',
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_to_shipstation BOOLEAN DEFAULT FALSE,
    upload_date TIMESTAMP,
    shipstation_order_id VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending'
);

-- 7. Shipped Orders Table
CREATE TABLE shipped_orders (
    order_number VARCHAR(50) PRIMARY KEY,
    order_date TIMESTAMP,
    ship_date TIMESTAMP,
    customer_name VARCHAR(200),
    carrier VARCHAR(100),
    service VARCHAR(100),
    tracking_number VARCHAR(100),
    shipstation_order_id VARCHAR(50),
    warehouse VARCHAR(100),
    import_source VARCHAR(50) DEFAULT 'ShipStation',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Shipped Items Table  
CREATE TABLE shipped_items (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL,
    sku VARCHAR(50) NOT NULL,
    lot_number VARCHAR(50),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    ship_date TIMESTAMP,
    FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number) ON DELETE CASCADE
);

-- 9. Inventory Current Table
CREATE TABLE inventory_current (
    sku VARCHAR(50) PRIMARY KEY,
    quantity_on_hand INTEGER DEFAULT 0,
    reorder_point INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Inventory Transactions Table
CREATE TABLE inventory_transactions (
    id SERIAL PRIMARY KEY,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sku VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    lot_number VARCHAR(50),
    reference_order VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. System KPIs Table
CREATE TABLE system_kpis (
    metric_name VARCHAR(100) PRIMARY KEY,
    metric_value TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Shipping Violations Table
CREATE TABLE shipping_violations (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50),
    violation_type VARCHAR(100),
    expected_value VARCHAR(200),
    actual_value VARCHAR(200),
    severity VARCHAR(20) DEFAULT 'medium',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    notes TEXT,
    FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number) ON DELETE CASCADE
);

-- Create Indexes for Performance
CREATE INDEX idx_shipped_items_order ON shipped_items(order_number);
CREATE INDEX idx_shipped_items_sku ON shipped_items(sku);
CREATE INDEX idx_shipped_items_ship_date ON shipped_items(ship_date);
CREATE INDEX idx_shipped_orders_ship_date ON shipped_orders(ship_date);
CREATE INDEX idx_orders_inbox_status ON orders_inbox(status);
CREATE INDEX idx_orders_inbox_upload ON orders_inbox(uploaded_to_shipstation);
CREATE INDEX idx_bundle_components_bundle ON bundle_components(bundle_sku);
CREATE INDEX idx_inventory_transactions_sku ON inventory_transactions(sku);
CREATE INDEX idx_inventory_transactions_date ON inventory_transactions(transaction_date);
CREATE INDEX idx_shipping_violations_order ON shipping_violations(order_number);
CREATE INDEX idx_shipping_violations_resolved ON shipping_violations(resolved_at);
```

### 2.3 Execute Schema Creation

```bash
# Run schema creation script
psql $DATABASE_URL -f scripts/postgres_migration/01_create_schema.sql

# Verify all tables created
psql $DATABASE_URL -c "\dt"
```

**Expected output:**
```
                List of relations
 Schema |         Name          | Type  |  Owner   
--------+-----------------------+-------+----------
 public | bundle_components     | table | postgres
 public | bundle_skus           | table | postgres
 public | configuration_params  | table | postgres
 public | inventory_current     | table | postgres
 public | inventory_transactions| table | postgres
 public | orders_inbox          | table | postgres
 public | shipped_items         | table | postgres
 public | shipped_orders        | table | postgres
 public | shipping_violations   | table | postgres
 public | sku_lot              | table | postgres
 public | system_kpis          | table | postgres
 public | workflow_controls     | table | postgres
```

---

## Phase 3: Data Migration

### 3.1 Create Data Migration Script

```python
# scripts/postgres_migration/02_migrate_data.py
import sqlite3
import psycopg2
import os
from datetime import datetime

def get_sqlite_connection():
    return sqlite3.connect('ora.db')

def get_postgres_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def migrate_table(table_name, sqlite_conn, pg_conn, transform_fn=None):
    """Generic table migration with optional transformation"""
    print(f"\n📦 Migrating {table_name}...")
    
    # Fetch from SQLite
    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()
    columns = [desc[0] for desc in sqlite_cur.description]
    
    if not rows:
        print(f"   ⚠️  No data in {table_name} - skipping")
        return
    
    # Transform if needed
    if transform_fn:
        rows = [transform_fn(dict(zip(columns, row))) for row in rows]
        columns = list(rows[0].keys()) if rows else columns
    
    # Insert into PostgreSQL
    pg_cur = pg_conn.cursor()
    placeholders = ','.join(['%s'] * len(columns))
    insert_sql = f"""
        INSERT INTO {table_name} ({','.join(columns)}) 
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """
    
    inserted = 0
    for row in rows:
        try:
            values = [row[col] if isinstance(row, dict) else row[i] 
                     for i, col in enumerate(columns)]
            pg_cur.execute(insert_sql, values)
            inserted += 1
        except Exception as e:
            print(f"   ❌ Error inserting row: {e}")
            continue
    
    pg_conn.commit()
    print(f"   ✅ Migrated {inserted}/{len(rows)} rows")

def boolean_transform(row):
    """Transform SQLite integers to PostgreSQL booleans"""
    for key, value in row.items():
        if key in ['enabled', 'uploaded_to_shipstation', 'is_active']:
            row[key] = bool(value) if value is not None else False
    return row

def main():
    print("🚀 Starting SQLite → PostgreSQL Migration")
    print("=" * 50)
    
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()
    
    try:
        # Migration order (respects foreign keys)
        migration_plan = [
            ('configuration_params', None),
            ('workflow_controls', boolean_transform),
            ('bundle_skus', None),
            ('bundle_components', None),
            ('sku_lot', boolean_transform),
            ('inventory_current', None),
            ('inventory_transactions', None),
            ('orders_inbox', boolean_transform),
            ('shipped_orders', None),
            ('shipped_items', None),
            ('system_kpis', None),
            ('shipping_violations', None),
        ]
        
        for table, transform in migration_plan:
            migrate_table(table, sqlite_conn, pg_conn, transform)
        
        print("\n" + "=" * 50)
        print("✅ Migration completed successfully!")
        
        # Print summary
        pg_cur = pg_conn.cursor()
        print("\n📊 Row count verification:")
        for table, _ in migration_plan:
            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = pg_cur.fetchone()[0]
            print(f"   {table}: {count} rows")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
```

### 3.2 Execute Data Migration

```bash
# Dry run first (add --dry-run flag to script)
python scripts/postgres_migration/02_migrate_data.py

# Review output for errors

# Execute actual migration
python scripts/postgres_migration/02_migrate_data.py | tee logs/migration/data_migration_$(date +%Y%m%d_%H%M%S).log
```

### 3.3 Verify Data Migration

```bash
# Compare row counts SQLite vs PostgreSQL
python scripts/postgres_migration/03_verify_migration.py
```

```python
# scripts/postgres_migration/03_verify_migration.py
import sqlite3
import psycopg2
import os

def verify():
    sqlite_conn = sqlite3.connect('ora.db')
    pg_conn = psycopg2.connect(os.environ['DATABASE_URL'])
    
    tables = [
        'configuration_params', 'workflow_controls', 'bundle_skus',
        'bundle_components', 'sku_lot', 'orders_inbox', 'shipped_orders',
        'shipped_items', 'inventory_current', 'inventory_transactions',
        'system_kpis', 'shipping_violations'
    ]
    
    print("📊 Migration Verification Report")
    print("=" * 60)
    print(f"{'Table':<30} {'SQLite':<12} {'PostgreSQL':<12} {'Status':<10}")
    print("-" * 60)
    
    all_match = True
    for table in tables:
        # SQLite count
        sqlite_cur = sqlite_conn.cursor()
        sqlite_cur.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = sqlite_cur.fetchone()[0]
        
        # PostgreSQL count
        pg_cur = pg_conn.cursor()
        pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
        pg_count = pg_cur.fetchone()[0]
        
        # Compare
        status = "✅ MATCH" if sqlite_count == pg_count else "❌ MISMATCH"
        if sqlite_count != pg_count:
            all_match = False
        
        print(f"{table:<30} {sqlite_count:<12} {pg_count:<12} {status:<10}")
    
    print("=" * 60)
    if all_match:
        print("✅ All tables verified successfully!")
    else:
        print("❌ Some tables have mismatches - review required")
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == '__main__':
    verify()
```

---

## Phase 4: Code Migration

### 4.1 Update Database Utilities

**Create new PostgreSQL utilities:**

```python
# src/services/database/pg_utils.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Connection pool setup
from psycopg2 import pool
connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=os.environ.get('DATABASE_URL')
)

def get_connection():
    """Get PostgreSQL connection from pool"""
    return connection_pool.getconn()

def return_connection(conn):
    """Return connection to pool"""
    connection_pool.putconn(conn)

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
        return_connection(conn)

def execute_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute query and return results as list of dicts"""
    with transaction() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

def execute_update(sql: str, params: tuple = ()) -> int:
    """Execute UPDATE/INSERT/DELETE and return affected rows"""
    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount

def upsert(table: str, data: dict, conflict_columns: list):
    """PostgreSQL UPSERT using ON CONFLICT"""
    columns = list(data.keys())
    values = list(data.values())
    placeholders = ','.join(['%s'] * len(columns))
    conflict = ','.join(conflict_columns)
    update_clause = ','.join([f"{k}=EXCLUDED.{k}" for k in data.keys()])
    
    sql = f"""
        INSERT INTO {table} ({','.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict}) DO UPDATE SET {update_clause}
    """
    
    execute_update(sql, tuple(values))

# Workflow control functions
_workflow_cache = {}
_cache_ttl = {}

def is_workflow_enabled(workflow_name: str, cache_ttl: int = 45) -> bool:
    """Check if workflow is enabled (with caching)"""
    import time
    
    current_time = time.time()
    
    # Check cache
    if workflow_name in _workflow_cache:
        if current_time - _cache_ttl[workflow_name] < cache_ttl:
            return _workflow_cache[workflow_name]
    
    # Query database
    try:
        result = execute_query(
            "SELECT enabled FROM workflow_controls WHERE workflow_name = %s",
            (workflow_name,)
        )
        enabled = result[0]['enabled'] if result else True  # Fail-open
        
        # Update cache
        _workflow_cache[workflow_name] = enabled
        _cache_ttl[workflow_name] = current_time
        
        return enabled
    except Exception as e:
        logger.error(f"Error checking workflow status: {e}")
        return _workflow_cache.get(workflow_name, True)  # Fail-open

def update_workflow_status(workflow_name: str, enabled: bool, updated_by: str = 'system'):
    """Update workflow enabled status"""
    upsert(
        'workflow_controls',
        {
            'workflow_name': workflow_name,
            'enabled': enabled,
            'updated_by': updated_by,
            'last_updated': 'CURRENT_TIMESTAMP'
        },
        ['workflow_name']
    )
    
    # Clear cache
    if workflow_name in _workflow_cache:
        del _workflow_cache[workflow_name]
```

### 4.2 Update All Automation Scripts

**SQL Syntax Changes Needed:**

| SQLite Syntax | PostgreSQL Syntax |
|--------------|-------------------|
| `?` placeholders | `%s` placeholders |
| `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` (same) |
| `DATETIME('now')` | `CURRENT_TIMESTAMP` |
| `DATE('now')` | `CURRENT_DATE` |
| `STRFTIME(...)` | `TO_CHAR(...)` |
| `.fetchall()` returns tuples | Use `RealDictCursor` for dicts |

**Scripts to update:**
1. ✅ `src/unified_shipstation_sync.py`
2. ✅ `src/scheduled_xml_import.py`
3. ✅ `src/scheduled_shipstation_upload.py`
4. ✅ `src/scheduled_cleanup.py`
5. ✅ `src/weekly_reporter.py`
6. ✅ `src/shipstation_units_refresher.py`
7. ✅ `app.py` (Flask dashboard)
8. ✅ All other database-dependent scripts

**Migration pattern for each script:**

```python
# OLD (SQLite)
from src.services.database.db_utils import transaction, execute_query

# NEW (PostgreSQL)  
from src.services.database.pg_utils import transaction, execute_query

# OLD: ? placeholders
cursor.execute("SELECT * FROM orders WHERE status = ?", (status,))

# NEW: %s placeholders
cursor.execute("SELECT * FROM orders WHERE status = %s", (status,))

# OLD: DATE('now')
cursor.execute("SELECT * FROM orders WHERE order_date >= DATE('now', '-7 days')")

# NEW: CURRENT_DATE
cursor.execute("SELECT * FROM orders WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'")
```

### 4.3 Update Flask Dashboard (app.py)

```python
# app.py - Update imports
# OLD
# from src.services.database.db_utils import execute_query, transaction

# NEW
from src.services.database.pg_utils import execute_query, transaction

# Update all SQL queries to use %s instead of ?
# All other logic remains the same
```

### 4.4 Update Configuration

```python
# config/settings.py - Add PostgreSQL support
import os

# Database configuration
USE_POSTGRES = os.environ.get('USE_POSTGRES', 'true').lower() == 'true'
DATABASE_URL = os.environ.get('DATABASE_URL')  # PostgreSQL connection string
SQLITE_PATH = os.environ.get('DATABASE_PATH', 'ora.db')  # Fallback for SQLite

# Import appropriate utilities
if USE_POSTGRES:
    from src.services.database import pg_utils as db
else:
    from src.services.database import db_utils as db
```

---

## Phase 5: Testing & Validation

### 5.1 Unit Testing

```bash
# Test database connectivity
python scripts/postgres_migration/test_connection.py

# Test CRUD operations
python scripts/postgres_migration/test_crud.py
```

### 5.2 Integration Testing

```bash
# Run each workflow in test mode
export DEV_MODE=1
export USE_POSTGRES=true

# Test workflows individually
python src/unified_shipstation_sync.py
python src/scheduled_xml_import.py
python src/scheduled_shipstation_upload.py
python src/weekly_reporter.py
```

### 5.3 Dashboard Testing

```bash
# Start dashboard with PostgreSQL
export USE_POSTGRES=true
python app.py

# Test all endpoints:
# - GET /api/dashboard_stats
# - GET /api/workflow_controls
# - GET /api/shipped_orders
# - GET /api/inventory_alerts
# - etc.
```

### 5.4 Data Integrity Validation

```sql
-- Run validation queries
-- scripts/postgres_migration/04_validate_integrity.sql

-- 1. Foreign key integrity
SELECT COUNT(*) as orphaned_shipped_items
FROM shipped_items si
LEFT JOIN shipped_orders so ON si.order_number = so.order_number
WHERE so.order_number IS NULL;
-- Expected: 0

-- 2. Bundle integrity
SELECT COUNT(*) as orphaned_components
FROM bundle_components bc
LEFT JOIN bundle_skus bs ON bc.bundle_sku = bs.bundle_sku
WHERE bs.bundle_sku IS NULL;
-- Expected: 0

-- 3. Data consistency
SELECT 
    (SELECT COUNT(*) FROM shipped_orders) as shipped_orders,
    (SELECT COUNT(*) FROM shipped_items) as shipped_items,
    (SELECT COUNT(*) FROM orders_inbox) as orders_inbox;
```

---

## Phase 6: Production Cutover

### 6.1 Pre-Cutover Checklist

- [ ] PostgreSQL database created and verified
- [ ] Schema migrated successfully
- [ ] Data migrated and verified (row counts match)
- [ ] All scripts updated for PostgreSQL
- [ ] Testing completed (unit + integration)
- [ ] Backup of SQLite database created
- [ ] Team notified of cutover window
- [ ] Rollback procedure documented and tested

### 6.2 Cutover Steps

**Step 1: Stop All Workflows**
```bash
# In Replit, stop the running instance
# Or set all workflows to disabled in database
psql $DATABASE_URL -c "UPDATE workflow_controls SET enabled = FALSE;"
```

**Step 2: Final Data Sync**
```bash
# Run data migration one final time to capture any last changes
python scripts/postgres_migration/02_migrate_data.py
```

**Step 3: Update Environment Variables**
```bash
# In Replit Secrets/Environment Variables:
# Add or update:
USE_POSTGRES=true
DATABASE_URL=<already set by Replit>
```

**Step 4: Deploy Updated Code**
```bash
# Commit all changes
git add .
git commit -m "feat: Migrate from SQLite to PostgreSQL for production persistence"

# In Replit, click "Republish" to deploy
```

**Step 5: Verify Deployment**
```bash
# Check logs for PostgreSQL connection
# Should see: "Connected to PostgreSQL" in logs

# Enable workflows
psql $DATABASE_URL -c "UPDATE workflow_controls SET enabled = TRUE;"
```

**Step 6: Monitor First Hour**
```bash
# Watch logs for any errors
# Verify data is being written to PostgreSQL
# Test dashboard functionality
# Confirm orders are processing
```

### 6.3 Success Criteria

✅ Migration successful when:
- All workflows running without errors
- Dashboard displays real-time data
- New orders persist after republish
- Database queries performing well (<100ms)
- No foreign key violations
- All KPIs updating correctly

---

## Rollback Procedures

### Emergency Rollback (if migration fails)

**Step 1: Revert Environment Variables**
```bash
# In Replit Secrets:
USE_POSTGRES=false
# Remove or comment out DATABASE_URL
```

**Step 2: Restore SQLite**
```bash
# Restore from backup
cp backups/ora_pre_postgres_YYYYMMDD_HHMMSS.db ora.db

# Verify restore
sqlite3 ora.db "SELECT COUNT(*) FROM shipped_orders;"
```

**Step 3: Revert Code**
```bash
# Use git to restore previous version
git revert HEAD
git push

# Or restore specific files
git checkout HEAD~1 src/services/database/
git checkout HEAD~1 src/*.py
git checkout HEAD~1 app.py
```

**Step 4: Republish**
```bash
# In Replit, click "Republish" to deploy rollback
```

**Step 5: Verify Rollback**
```bash
# Confirm SQLite is being used
# Verify workflows are running
# Test dashboard
```

---

## Post-Migration Tasks

### Week 1: Monitoring & Optimization

**Daily Tasks:**
- [ ] Monitor PostgreSQL connection pool usage
- [ ] Review slow query logs
- [ ] Check database size growth
- [ ] Verify backup retention
- [ ] Monitor workflow performance

**Query Optimization:**
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Add indexes if needed based on query patterns
```

### Week 2-4: Tuning & Documentation

- [ ] Optimize frequently used queries
- [ ] Add missing indexes if identified
- [ ] Document PostgreSQL-specific procedures
- [ ] Update operational runbooks
- [ ] Train team on PostgreSQL tools
- [ ] Archive SQLite database (keep as historical backup)

### Production Database Management

**Replit PostgreSQL Features:**
- ✅ Automatic backups (daily)
- ✅ Point-in-time recovery
- ✅ Rollback support
- ✅ Separate dev/prod databases (optional)
- ✅ Connection pooling

**Best Practices:**
1. Use connection pooling (already in `pg_utils.py`)
2. Monitor connection limits
3. Regular VACUUM and ANALYZE (auto-managed by Replit)
4. Keep sensitive queries in prepared statements
5. Use transactions for data consistency

---

## Migration Timeline

| Phase | Duration | Key Activities |
|-------|----------|---------------|
| **Preparation** | 1 hour | Backup, document state, install dependencies |
| **PostgreSQL Setup** | 30 min | Create database, verify connection |
| **Schema Migration** | 1 hour | Create tables, indexes, constraints |
| **Data Migration** | 1 hour | Migrate all data, verify row counts |
| **Code Migration** | 3-4 hours | Update scripts, dashboard, test |
| **Testing** | 1-2 hours | Unit, integration, validation |
| **Cutover** | 30 min | Deploy, enable workflows, monitor |
| **TOTAL** | **8-10 hours** | Complete migration |

**Recommended Schedule:**
- **Day 1 (4 hours):** Preparation + PostgreSQL Setup + Schema Migration
- **Day 2 (3 hours):** Data Migration + Validation
- **Day 3 (3-4 hours):** Code Migration + Testing
- **Day 4 (1 hour):** Cutover + Monitoring

---

## Troubleshooting

### Issue: Connection Pool Exhausted

**Symptom:** "Error: connection pool exhausted"

**Resolution:**
```python
# Increase pool size in pg_utils.py
connection_pool = pool.SimpleConnectionPool(
    minconn=2,
    maxconn=20,  # Increase from 10
    dsn=os.environ.get('DATABASE_URL')
)
```

### Issue: Slow Queries

**Symptom:** Dashboard/workflows slow after migration

**Diagnosis:**
```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM shipped_items WHERE ship_date >= CURRENT_DATE - INTERVAL '7 days';
```

**Resolution:**
```sql
-- Add missing index
CREATE INDEX idx_shipped_items_ship_date_optimized ON shipped_items(ship_date DESC);
```

### Issue: Data Type Mismatch

**Symptom:** "ERROR: column 'X' is of type boolean but expression is of type integer"

**Resolution:**
```python
# Update transformation function
def boolean_transform(row):
    for key in ['enabled', 'uploaded_to_shipstation']:
        if key in row and row[key] is not None:
            row[key] = bool(row[key])
    return row
```

### Issue: Foreign Key Violations

**Symptom:** "ERROR: insert or update violates foreign key constraint"

**Resolution:**
```bash
# Check migration order - ensure parent tables migrate first
# Re-run migration with correct order
python scripts/postgres_migration/02_migrate_data.py
```

---

## Success Metrics

**Technical Metrics:**
- ✅ Zero data loss on deployment
- ✅ Database queries < 100ms average
- ✅ 100% workflow success rate
- ✅ Zero foreign key violations
- ✅ Connection pool < 80% utilized

**Business Metrics:**
- ✅ No order processing delays
- ✅ Real-time inventory accuracy
- ✅ Dashboard KPIs updating live
- ✅ Zero downtime during cutover
- ✅ Team confident in new system

---

## Appendix

### A. Environment Variables Reference

```bash
# Replit-managed (auto-created)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
PGHOST=<host>
PGPORT=5432
PGUSER=<user>
PGPASSWORD=<password>
PGDATABASE=<dbname>

# Application-managed
USE_POSTGRES=true
DEV_MODE=false
```

### B. Key SQL Differences

```sql
-- SQLite: Auto-increment
id INTEGER PRIMARY KEY AUTOINCREMENT

-- PostgreSQL: Serial
id SERIAL PRIMARY KEY

-- SQLite: Current timestamp
DATETIME('now')

-- PostgreSQL: Current timestamp
CURRENT_TIMESTAMP

-- SQLite: Date arithmetic
DATE('now', '-7 days')

-- PostgreSQL: Date arithmetic
CURRENT_DATE - INTERVAL '7 days'
```

### C. Connection String Format

```
PostgreSQL: postgresql://username:password@host:port/database
SQLite: /path/to/database.db
```

---

**END OF MIGRATION PLAN**

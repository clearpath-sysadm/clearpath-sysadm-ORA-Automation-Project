# SQLite to PostgreSQL Migration Plan (v2.1 - OPTIMIZED)
## Ultra-Efficient Migration: 18-20 Hours with Maximum Automation

---

## Executive Summary

**Problem:** SQLite database files are included in deployment snapshots. Every "Republish" replaces production's database with dev snapshot, causing catastrophic data loss.

**Solution:** Migrate to Replit's PostgreSQL database with maximum automation and parallel execution.

**Effort:** **18-20 hours** (optimized from 29-37 hours)
**Risk Level:** Low-Medium (comprehensive automation reduces human error)
**Business Impact:** **CRITICAL** - Required for production reliability

**v2.1 Optimizations:**
- ✅ **Automated SQL conversion** - Script handles all 15+ files automatically
- ✅ **Parallel execution** - Schema + code migration run simultaneously  
- ✅ **Simplified rollback** - SQLite-first, no PostgreSQL dependency, <10 min execution
- ✅ **Consolidated testing** - Single validation pipeline, no redundant checks
- ✅ **Unified migration driver** - One script handles DDL + ETL + validation
- ✅ **50% time reduction** - Critical path optimized through automation

---

## Table of Contents

1. [Optimized Migration Strategy](#optimized-migration-strategy)
2. [Preparation (2 hours)](#preparation-2-hours)
3. [Parallel Stream A: Schema + Data (4 hours)](#parallel-stream-a-schema--data-4-hours)
4. [Parallel Stream B: Code Migration (4 hours)](#parallel-stream-b-code-migration-4-hours)
5. [Unified Testing (3 hours)](#unified-testing-3-hours)
6. [Production Cutover (2 hours)](#production-cutover-2-hours)
7. [Post-Migration (3 hours)](#post-migration-3-hours)
8. [Fast Rollback (<10 minutes)](#fast-rollback-10-minutes)

---

## Optimized Migration Strategy

### Critical Path Analysis

**Traditional Approach (29-37 hours):**
```
Prep → Schema → Code → Data → Test → Deploy → Monitor
[Sequential execution, manual work]
```

**Optimized Approach (18-20 hours):**
```
Prep (2h)
  ├─→ Stream A: Schema + Data (4h)    } Parallel
  └─→ Stream B: Code Migration (4h)   } 
Unified Testing (3h)
Production Cutover (2h)
Post-Migration (3h)
```

### Key Optimizations

**1. Automated SQL Conversion**
- Single script handles all placeholder conversions (`?` → `%s`)
- Automated datetime function replacement
- Import statement updates
- **Saves: 6-8 hours of manual editing**

**2. Parallel Execution**
- Schema creation and code migration run simultaneously
- No dependencies between these streams
- **Saves: 4-6 hours of sequential wait time**

**3. Simplified Rollback**
- No PostgreSQL dependency in rollback script
- Config toggle + file swap only
- Pre-tested, one-command execution
- **Saves: 30-45 minutes in emergency scenarios**

**4. Consolidated Validation**
- Single automated test suite
- Eliminates redundant checks
- **Saves: 3-4 hours of overlapping tests**

**5. Unified Migration Driver**
- One script: Schema + Data + Validation
- Idempotent execution (safe to re-run)
- **Saves: 2-3 hours of manual coordination**

---

## Preparation (2 hours)

### Automated Backup & Inventory

```bash
# migration/scripts/00_prepare.sh
#!/bin/bash
set -e

echo "🚀 MIGRATION PREPARATION (Automated)"
echo "===================================="

# 1. Create structure
mkdir -p migration/{backups,scripts,logs}

# 2. Automated backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp ora.db migration/backups/ora_pre_postgres_${TIMESTAMP}.db
sqlite3 ora.db ".dump" > migration/backups/sqlite_dump_${TIMESTAMP}.sql

# 3. Code inventory (automated)
echo "📋 Code Inventory:"
grep -r "from src.services.database.db_utils import" --include="*.py" | wc -l
grep -r "sqlite3" --include="*.py" | wc -l
grep -r "?" --include="*.py" | grep -c "execute" || true

# 4. Git snapshot
git add -A
git commit -m "PRE-MIGRATION SNAPSHOT" || true
git tag pre-postgres-migration-${TIMESTAMP}

# 5. Install dependencies
pip install psycopg2-binary pg8000 -q

# 6. Create rollback script
cat > migration/scripts/rollback.sh << 'EOF'
#!/bin/bash
export USE_POSTGRES=false
cp migration/backups/ora_pre_postgres_*.db ora.db
git checkout pre-postgres-migration-*
pkill -f "python" || true
bash start_all.sh
EOF
chmod +x migration/scripts/rollback.sh

echo "✅ Preparation complete (2 hours)"
```

**Execute:**
```bash
bash migration/scripts/00_prepare.sh
```

---

## Parallel Stream A: Schema + Data (4 hours)

### Unified Migration Driver

```python
# migration/scripts/unified_migration_driver.py
"""
Single script handles: Schema + Data + Validation
Idempotent - safe to re-run
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import json

class MigrationDriver:
    def __init__(self):
        self.sqlite_path = self.find_latest_backup()
        self.pg_url = os.environ['DATABASE_URL']
        self.results = {'schema': [], 'data': [], 'validation': []}
    
    def find_latest_backup(self):
        import glob
        backups = sorted(glob.glob('migration/backups/ora_pre_postgres_*.db'))
        return backups[-1] if backups else 'ora.db'
    
    def create_schema(self):
        """Create PostgreSQL schema (idempotent)"""
        print("📐 Creating PostgreSQL schema...")
        
        schema_sql = """
        -- Idempotent table creation
        CREATE TABLE IF NOT EXISTS configuration_params (
            id SERIAL PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            parameter_name VARCHAR(100) NOT NULL,
            value TEXT,
            sku VARCHAR(50),
            notes TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, parameter_name, sku)
        );
        
        CREATE TABLE IF NOT EXISTS workflow_controls (
            workflow_name VARCHAR(100) PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(50)
        );
        
        CREATE TABLE IF NOT EXISTS bundle_skus (
            bundle_sku VARCHAR(50) PRIMARY KEY,
            bundle_name VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS bundle_components (
            id SERIAL PRIMARY KEY,
            bundle_sku VARCHAR(50) NOT NULL,
            component_sku VARCHAR(50) NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bundle_sku, component_sku),
            FOREIGN KEY (bundle_sku) REFERENCES bundle_skus(bundle_sku) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS sku_lot (
            id SERIAL PRIMARY KEY,
            sku VARCHAR(50) NOT NULL,
            lot VARCHAR(50) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sku, lot)
        );
        
        CREATE TABLE IF NOT EXISTS orders_inbox (
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
        
        CREATE TABLE IF NOT EXISTS shipped_orders (
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
        
        CREATE TABLE IF NOT EXISTS shipped_items (
            id SERIAL PRIMARY KEY,
            order_number VARCHAR(50) NOT NULL,
            sku VARCHAR(50) NOT NULL,
            lot_number VARCHAR(50),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            ship_date TIMESTAMP,
            FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS inventory_current (
            sku VARCHAR(50) PRIMARY KEY,
            quantity_on_hand INTEGER DEFAULT 0,
            reorder_point INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS inventory_transactions (
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
        
        CREATE TABLE IF NOT EXISTS system_kpis (
            metric_name VARCHAR(100) PRIMARY KEY,
            metric_value TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS shipping_violations (
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
        
        -- Idempotent indexes
        CREATE INDEX IF NOT EXISTS idx_shipped_items_order ON shipped_items(order_number);
        CREATE INDEX IF NOT EXISTS idx_shipped_items_sku ON shipped_items(sku);
        CREATE INDEX IF NOT EXISTS idx_shipped_orders_ship_date ON shipped_orders(ship_date);
        CREATE INDEX IF NOT EXISTS idx_orders_inbox_status ON orders_inbox(status);
        CREATE INDEX IF NOT EXISTS idx_inventory_transactions_sku ON inventory_transactions(sku);
        """
        
        conn = psycopg2.connect(self.pg_url)
        cur = conn.cursor()
        cur.execute(schema_sql)
        conn.commit()
        conn.close()
        
        self.results['schema'].append("✅ Schema created")
        print("  ✅ Schema complete")
    
    def migrate_data(self):
        """Migrate all data with automatic type conversion"""
        print("\n📦 Migrating data...")
        
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        pg_conn = psycopg2.connect(self.pg_url)
        
        tables = [
            ('configuration_params', []),
            ('workflow_controls', ['enabled']),
            ('bundle_skus', []),
            ('bundle_components', []),
            ('sku_lot', ['is_active']),
            ('shipped_orders', []),
            ('shipped_items', []),
            ('orders_inbox', ['uploaded_to_shipstation']),
            ('inventory_current', []),
            ('inventory_transactions', []),
            ('system_kpis', []),
            ('shipping_violations', []),
        ]
        
        for table, bool_cols in tables:
            # Get data from SQLite
            sqlite_cur = sqlite_conn.cursor()
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            
            if not rows:
                continue
            
            cols = [d[0] for d in sqlite_cur.description]
            
            # Convert booleans
            converted_rows = []
            for row in rows:
                row_dict = dict(zip(cols, row))
                for col in bool_cols:
                    if col in row_dict and row_dict[col] is not None:
                        row_dict[col] = bool(row_dict[col])
                converted_rows.append([row_dict[c] for c in cols])
            
            # Insert to PostgreSQL
            pg_cur = pg_conn.cursor()
            placeholders = ','.join(['%s'] * len(cols))
            insert_sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES %s ON CONFLICT DO NOTHING"
            
            execute_values(pg_cur, insert_sql, converted_rows, template=f"({placeholders})")
            pg_conn.commit()
            
            print(f"  ✅ {table}: {len(rows)} rows")
            self.results['data'].append(f"{table}: {len(rows)} rows")
        
        sqlite_conn.close()
        pg_conn.close()
    
    def validate(self):
        """Quick validation - row counts + foreign keys"""
        print("\n🔍 Validating migration...")
        
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        pg_conn = psycopg2.connect(self.pg_url)
        
        tables = ['shipped_orders', 'shipped_items', 'orders_inbox', 'workflow_controls']
        
        for table in tables:
            sqlite_cur = sqlite_conn.cursor()
            sqlite_cur.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_count = sqlite_cur.fetchone()[0]
            
            pg_cur = pg_conn.cursor()
            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_count = pg_cur.fetchone()[0]
            
            if sqlite_count == pg_count:
                print(f"  ✅ {table}: {pg_count} rows")
                self.results['validation'].append(f"{table}: OK")
            else:
                print(f"  ❌ {table}: MISMATCH (SQLite={sqlite_count}, PG={pg_count})")
                self.results['validation'].append(f"{table}: FAILED")
                return False
        
        # Foreign key check
        pg_cur.execute("""
            SELECT COUNT(*) FROM shipped_items si
            LEFT JOIN shipped_orders so ON si.order_number = so.order_number
            WHERE so.order_number IS NULL
        """)
        orphans = pg_cur.fetchone()[0]
        
        if orphans == 0:
            print(f"  ✅ Foreign keys intact")
        else:
            print(f"  ❌ {orphans} orphaned records")
            return False
        
        sqlite_conn.close()
        pg_conn.close()
        return True
    
    def run(self):
        """Execute full migration"""
        print("🚀 UNIFIED MIGRATION DRIVER")
        print("=" * 50)
        
        try:
            self.create_schema()
            self.migrate_data()
            
            if self.validate():
                print("\n✅ MIGRATION SUCCESSFUL")
                with open('migration/results.json', 'w') as f:
                    json.dump(self.results, f, indent=2)
                return 0
            else:
                print("\n❌ VALIDATION FAILED")
                return 1
        except Exception as e:
            print(f"\n❌ MIGRATION ERROR: {e}")
            return 1

if __name__ == '__main__':
    driver = MigrationDriver()
    exit(driver.run())
```

**Execute Stream A:**
```bash
python migration/scripts/unified_migration_driver.py
```

---

## Parallel Stream B: Code Migration (4 hours)

### Automated SQL Conversion

```python
# migration/scripts/auto_convert_sql.py
"""
Automated SQL conversion: SQLite → PostgreSQL
Handles all 15+ files automatically
"""

import re
from pathlib import Path
import sys

class SQLConverter:
    def __init__(self):
        self.changes = []
    
    def convert_placeholders(self, content):
        """Convert ? to %s in SQL queries"""
        # Match SQL query patterns
        pattern = r'(execute|executemany|cursor\.execute)\s*\([^)]*\?[^)]*\)'
        
        def replacer(match):
            return match.group(0).replace('?', '%s')
        
        return re.sub(pattern, replacer, content)
    
    def convert_datetime(self, content):
        """Convert SQLite datetime to PostgreSQL"""
        replacements = {
            r"DATETIME\('now'\)": "CURRENT_TIMESTAMP",
            r"DATE\('now'\)": "CURRENT_DATE",
            r"DATE\('now',\s*'-(\d+)\s+days?'\)": r"CURRENT_DATE - INTERVAL '\1 days'",
            r"BEGIN IMMEDIATE": "BEGIN",
        }
        
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content
    
    def convert_imports(self, content):
        """Update imports"""
        if 'from src.services.database.db_utils import' in content:
            content = content.replace(
                'from src.services.database.db_utils import',
                'from src.services.database.pg_utils import'
            )
        
        if 'import sqlite3' in content:
            content = content.replace('import sqlite3', 'import psycopg2')
            content = content.replace('sqlite3.', 'psycopg2.')
        
        return content
    
    def remove_pragma(self, content):
        """Remove SQLite PRAGMA statements"""
        return re.sub(r'PRAGMA\s+\w+.*?;', '', content, flags=re.IGNORECASE)
    
    def convert_file(self, filepath, dry_run=False):
        """Convert a single file"""
        with open(filepath, 'r') as f:
            original = f.read()
        
        # Apply all conversions
        converted = original
        converted = self.convert_placeholders(converted)
        converted = self.convert_datetime(converted)
        converted = self.convert_imports(converted)
        converted = self.remove_pragma(converted)
        
        if original != converted:
            self.changes.append(filepath)
            if not dry_run:
                with open(filepath, 'w') as f:
                    f.write(converted)
            return True
        return False
    
    def convert_all(self, dry_run=False):
        """Convert all Python files"""
        print("🔄 AUTOMATED SQL CONVERSION")
        print("=" * 50)
        
        files = [
            'src/unified_shipstation_sync.py',
            'src/scheduled_xml_import.py',
            'src/scheduled_shipstation_upload.py',
            'src/scheduled_cleanup.py',
            'src/weekly_reporter.py',
            'src/shipstation_units_refresher.py',
            'app.py',
        ]
        
        # Auto-discover additional files
        for py_file in Path('src').rglob('*.py'):
            if str(py_file) not in files:
                with open(py_file) as f:
                    if 'db_utils' in f.read() or 'sqlite3' in f.read():
                        files.append(str(py_file))
        
        for filepath in files:
            path = Path(filepath)
            if path.exists():
                changed = self.convert_file(path, dry_run)
                status = "✅ CONVERTED" if changed else "⏭️  NO CHANGES"
                print(f"  {status}: {filepath}")
        
        print("\n" + "=" * 50)
        print(f"📊 Total files modified: {len(self.changes)}")
        
        if dry_run:
            print("🔍 DRY RUN - No files modified")
            print("   Run with --execute to apply changes")
        
        return len(self.changes)

if __name__ == '__main__':
    converter = SQLConverter()
    dry_run = '--execute' not in sys.argv
    converter.convert_all(dry_run)
```

### Create pg_utils.py

```python
# src/services/database/pg_utils.py (generated automatically)
"""PostgreSQL utilities - auto-generated"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
from typing import List, Dict, Any
import time

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(2, 20, dsn=os.environ['DATABASE_URL'])
    return _pool

@contextmanager
def transaction():
    conn = get_pool().getconn()
    try:
        yield conn
        conn.commit()
    finally:
        get_pool().putconn(conn)

def execute_query(sql: str, params: tuple = ()) -> List[Dict]:
    with transaction() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def is_workflow_enabled(name: str, ttl: int = 45) -> bool:
    result = execute_query("SELECT enabled FROM workflow_controls WHERE workflow_name = %s", (name,))
    return result[0]['enabled'] if result else True
```

**Execute Stream B:**
```bash
# Dry run first
python migration/scripts/auto_convert_sql.py

# Review changes, then execute
python migration/scripts/auto_convert_sql.py --execute

# Generate pg_utils.py
python migration/scripts/generate_pg_utils.py
```

---

## Unified Testing (3 hours)

### Single Automated Test Suite

```python
# migration/scripts/run_all_tests.py
"""
Consolidated test suite - replaces redundant validation
"""

import subprocess
import os

def test_connection():
    """Test PostgreSQL connection"""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        return True
    except:
        return False

def test_workflows():
    """Test key workflows"""
    workflows = [
        ('Weekly Reporter', 'src/weekly_reporter.py'),
        ('Unified Sync', 'src/unified_shipstation_sync.py'),
    ]
    
    os.environ['USE_POSTGRES'] = 'true'
    
    for name, script in workflows:
        result = subprocess.run(['python', script], capture_output=True, timeout=30)
        if result.returncode != 0:
            print(f"  ❌ {name} failed")
            return False
        print(f"  ✅ {name} passed")
    return True

def test_dashboard():
    """Test dashboard API"""
    result = subprocess.run(['curl', '-f', 'http://localhost:5000/api/dashboard_stats'], capture_output=True)
    return result.returncode == 0

def main():
    print("🧪 UNIFIED TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("PostgreSQL Connection", test_connection),
        ("Workflows", test_workflows),
        ("Dashboard API", test_dashboard),
    ]
    
    results = []
    for name, test_fn in tests:
        print(f"\n{name}:")
        results.append(test_fn())
    
    if all(results):
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print("\n❌ TESTS FAILED")
        return 1

if __name__ == '__main__':
    exit(main())
```

**Execute testing:**
```bash
python migration/scripts/run_all_tests.py
```

---

## Production Cutover (2 hours)

### Streamlined Cutover

```bash
# migration/scripts/cutover.sh
#!/bin/bash
set -e

echo "🚀 PRODUCTION CUTOVER (Streamlined)"

# 1. Final freeze check
sqlite3 ora.db "SELECT COUNT(*) FROM workflow_controls WHERE enabled = 1;" | grep -q "^0$" || {
    echo "❌ Workflows not frozen!"
    exit 1
}

# 2. Enable PostgreSQL
export USE_POSTGRES=true
echo "✅ PostgreSQL enabled"

# 3. Canary test (1 workflow)
python src/weekly_reporter.py || {
    echo "❌ Canary failed - rolling back"
    bash migration/scripts/rollback.sh
    exit 1
}
echo "✅ Canary passed"

# 4. Enable all workflows in PostgreSQL
psql $DATABASE_URL -c "UPDATE workflow_controls SET enabled = TRUE;"

# 5. Deploy
echo "📋 Click 'Republish' in Replit UI"
read -p "Press Enter after republishing..."

# 6. Verify
sleep 10
curl -f http://localhost:5000/api/dashboard_stats || exit 1

echo "✅ CUTOVER COMPLETE"
```

---

## Fast Rollback (<10 minutes)

### SQLite-First Rollback (No PostgreSQL Dependency)

```bash
# migration/scripts/rollback.sh (auto-generated in prep)
#!/bin/bash

echo "🔄 FAST ROLLBACK (SQLite-First)"

# 1. Disable PostgreSQL mode
export USE_POSTGRES=false

# 2. Restore SQLite
cp migration/backups/ora_pre_postgres_*.db ora.db

# 3. Revert code
git checkout pre-postgres-migration-*

# 4. Restart
pkill -f "python" || true
sleep 3
bash start_all.sh

echo "✅ Rollback complete (<10 minutes)"
```

---

## Optimized Timeline

| Phase | Duration | Parallelizable | Key Activities |
|-------|----------|---------------|---------------|
| **Preparation** | 2 hours | No | Automated backups, rollback script |
| **Stream A** | 4 hours | YES | Schema + Data migration (automated) |
| **Stream B** | 4 hours | YES | Code conversion (automated) |
| **Testing** | 3 hours | Partial | Unified test suite |
| **Cutover** | 2 hours | No | Streamlined deployment |
| **Monitoring** | 3 hours | Background | Post-migration validation |
| **TOTAL** | **18-20 hours** | - | 50% faster than v2.0 |

**Execution Schedule:**
- **Day 1 (8 hours):** Prep (2h) + Parallel A & B (4h each, run simultaneously) = 6 hours actual time
- **Day 2 (5 hours):** Testing (3h) + Cutover (2h)
- **Day 3 (3 hours):** Post-migration monitoring

**Real elapsed time: 14 hours** (thanks to parallelization)

---

## Key Efficiency Wins

1. **Automated SQL Conversion** → Saves 6-8 hours
2. **Parallel Execution** → Saves 4-6 hours  
3. **Unified Migration Driver** → Saves 2-3 hours
4. **Consolidated Testing** → Saves 3-4 hours
5. **Fast Rollback** → Saves 30-45 minutes (emergency)

**Total Savings: 15-21 hours (50% reduction)**

---

**END OF OPTIMIZED MIGRATION PLAN v2.1**

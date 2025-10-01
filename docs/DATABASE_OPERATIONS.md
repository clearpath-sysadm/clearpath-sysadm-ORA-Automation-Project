# Database Operations Guide

## Overview

This guide provides comprehensive instructions for daily database operations, maintenance, and troubleshooting for the ORA automation SQLite database. Follow these procedures to ensure optimal performance, data integrity, and reliability.

---

## Table of Contents

1. [Connection Management](#connection-management)
2. [Daily Operations](#daily-operations)
3. [Maintenance Schedule](#maintenance-schedule)
4. [Performance Monitoring](#performance-monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Backup & Recovery](#backup--recovery)
7. [Common Tasks](#common-tasks)

---

## Connection Management

### Database Connection Module

All database connections should use the centralized `db_utils.py` module for consistency and proper configuration.

**Location:** `src/services/database/db_utils.py`

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import os

class DatabaseConnection:
    """Centralized SQLite database connection management"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'ora.db')
        
    def get_connection(self):
        """Create a new database connection with production settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 30 second timeout for lock acquisition
            check_same_thread=False,  # Allow multi-threading
            isolation_level=None  # Autocommit mode off
        )
        
        # Apply production PRAGMA settings
        conn.executescript("""
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA foreign_keys = ON;
            PRAGMA busy_timeout = 8000;
            PRAGMA temp_store = MEMORY;
            PRAGMA cache_size = -20000;
        """)
        
        # Enable dict-like row access
        conn.row_factory = sqlite3.Row
        
        return conn
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        conn = self.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

# Global instance
db = DatabaseConnection()

# Usage in automation scripts:
# with db.transaction() as conn:
#     cursor = conn.execute("INSERT INTO ...")
```

### Connection Best Practices

**✅ DO:**
- Use `BEGIN IMMEDIATE` for all write transactions
- Always use context managers for connections
- Set appropriate timeout values (8-30 seconds)
- Enable row_factory for dict-like access
- Close connections in finally blocks

**❌ DON'T:**
- Keep connections open longer than necessary
- Use multiple simultaneous write connections
- Ignore busy timeout errors
- Disable foreign key constraints
- Use autocommit for batch operations

---

## Daily Operations

### Morning Health Check

**Run every morning at 8 AM:**

```bash
#!/bin/bash
# scripts/daily_health_check.sh

echo "=== ORA Database Health Check: $(date) ===" >> logs/db_health.log

# 1. Check database file exists and is accessible
if [ ! -f "ora.db" ]; then
    echo "ERROR: Database file not found!" >> logs/db_health.log
    exit 1
fi

# 2. Check integrity
sqlite3 ora.db "PRAGMA integrity_check;" >> logs/db_health.log

# 3. Check database size
DB_SIZE=$(du -h ora.db | cut -f1)
echo "Database size: $DB_SIZE" >> logs/db_health.log

# 4. Check WAL file size
WAL_SIZE=$(du -h ora.db-wal 2>/dev/null | cut -f1)
echo "WAL file size: ${WAL_SIZE:-N/A}" >> logs/db_health.log

# 5. Check free space percentage
sqlite3 ora.db <<EOF >> logs/db_health.log
SELECT 
    ROUND(CAST((SELECT freelist_count FROM pragma_freelist_count()) AS REAL) / 
          (SELECT page_count FROM pragma_page_count()) * 100, 2) 
    || '% free space' as free_space;
EOF

echo "Health check completed successfully" >> logs/db_health.log
echo "----------------------------------------" >> logs/db_health.log
```

**Add to crontab:**
```bash
0 8 * * * /path/to/scripts/daily_health_check.sh
```

### Transaction Patterns

#### Read Operations

```python
# Simple read query
def get_inventory_current():
    """Fetch current inventory levels"""
    with db.get_connection() as conn:
        cursor = conn.execute("""
            SELECT sku, product_name, current_quantity, alert_level
            FROM inventory_current
            ORDER BY alert_level DESC, current_quantity ASC
        """)
        return cursor.fetchall()
```

#### Write Operations

```python
# Single write with transaction
def update_workflow_status(workflow_name, status, details):
    """Update workflow execution status"""
    with db.transaction() as conn:
        conn.execute("""
            UPDATE workflows 
            SET status = ?, 
                details = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (status, details, workflow_name))
```

#### Batch Operations

```python
# Bulk insert with transaction
def insert_shipped_items(items_data):
    """Batch insert shipped items"""
    with db.transaction() as conn:
        conn.executemany("""
            INSERT INTO shipped_items 
            (ship_date, sku_lot, base_sku, quantity_shipped, order_number)
            VALUES (?, ?, ?, ?, ?)
        """, items_data)
```

#### UPSERT for Idempotency

```python
# Insert or update with conflict handling
def upsert_system_kpis(snapshot_date, kpis_data):
    """Insert or update daily KPIs"""
    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO system_kpis (
                snapshot_date, orders_today, shipments_sent, 
                pending_uploads, system_status
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_date) DO UPDATE SET
                orders_today = excluded.orders_today,
                shipments_sent = excluded.shipments_sent,
                pending_uploads = excluded.pending_uploads,
                system_status = excluded.system_status,
                created_at = CURRENT_TIMESTAMP
        """, (snapshot_date, *kpis_data))
```

---

## Maintenance Schedule

### Daily Maintenance (Automated)

**Run at 2 AM every day:**

```python
# scripts/daily_maintenance.py

import sqlite3
import sys
from datetime import datetime

def daily_maintenance(db_path='ora.db'):
    """Automated daily maintenance routine"""
    
    print(f"Starting daily maintenance: {datetime.now()}")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # 1. Checkpoint WAL file
        print("Checkpointing WAL...")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        # 2. Update query planner statistics
        print("Running ANALYZE...")
        conn.execute("ANALYZE")
        
        # 3. Optimize database
        print("Running OPTIMIZE...")
        conn.execute("PRAGMA optimize")
        
        # 4. Check integrity
        print("Checking integrity...")
        result = conn.execute("PRAGMA quick_check").fetchone()[0]
        if result != "ok":
            print(f"WARNING: Integrity check failed: {result}")
            return False
        
        print("Daily maintenance completed successfully")
        return True
        
    except Exception as e:
        print(f"Maintenance failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = daily_maintenance()
    sys.exit(0 if success else 1)
```

**Crontab entry:**
```bash
0 2 * * * /usr/bin/python3 /path/to/scripts/daily_maintenance.py >> /var/log/db_maintenance.log 2>&1
```

### Weekly Maintenance

**Run every Sunday at 3 AM:**

```python
# scripts/weekly_maintenance.py

def weekly_maintenance(db_path='ora.db'):
    """Weekly comprehensive maintenance"""
    
    conn = sqlite3.connect(db_path)
    
    try:
        # 1. Get database statistics
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        
        free_percentage = (freelist_count / page_count) * 100 if page_count > 0 else 0
        file_size_mb = (page_count * page_size) / (1024 * 1024)
        
        print(f"Database size: {file_size_mb:.2f} MB")
        print(f"Free space: {free_percentage:.1f}%")
        
        # 2. VACUUM if needed (>25% free space)
        if free_percentage > 25:
            print(f"Free space {free_percentage:.1f}% exceeds threshold, running VACUUM...")
            conn.execute("VACUUM")
            print("VACUUM completed")
        else:
            print(f"Free space {free_percentage:.1f}% below threshold, skipping VACUUM")
        
        # 3. Full integrity check
        print("Running full integrity check...")
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            print(f"ERROR: Integrity check failed: {result}")
            return False
        
        # 4. Analyze all tables
        print("Analyzing all tables...")
        conn.execute("ANALYZE")
        
        print("Weekly maintenance completed successfully")
        return True
        
    except Exception as e:
        print(f"Weekly maintenance failed: {e}")
        return False
    finally:
        conn.close()
```

**Crontab entry:**
```bash
0 3 * * 0 /usr/bin/python3 /path/to/scripts/weekly_maintenance.py >> /var/log/db_maintenance.log 2>&1
```

### Monthly Tasks

**First day of each month:**

1. **Database backup archive**
   ```bash
   # Archive backups older than 30 days
   tar -czf backups/archive_$(date +%Y%m).tar.gz backups/ora_*.db
   find backups -name "ora_*.db" -mtime +30 -delete
   ```

2. **Performance review**
   - Review slow query logs
   - Check index usage statistics
   - Verify backup integrity
   - Update documentation if schema changed

---

## Performance Monitoring

### Key Metrics to Track

**Database Health Metrics:**

```sql
-- Database size and fragmentation
SELECT 
    (SELECT page_count FROM pragma_page_count()) * 
    (SELECT page_size FROM pragma_page_size()) / 1024.0 / 1024.0 as size_mb,
    ROUND(
        CAST((SELECT freelist_count FROM pragma_freelist_count()) AS REAL) / 
        (SELECT page_count FROM pragma_page_count()) * 100, 2
    ) as free_space_pct,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='table') as table_count,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='index') as index_count;
```

**Query Performance:**

```python
# Enable query timing
def analyze_query_performance(query, params=()):
    """Analyze query execution plan and timing"""
    import time
    
    with db.get_connection() as conn:
        # Get query plan
        plan = conn.execute(f"EXPLAIN QUERY PLAN {query}", params).fetchall()
        print("Query Plan:")
        for row in plan:
            print(f"  {row}")
        
        # Time execution
        start = time.time()
        result = conn.execute(query, params).fetchall()
        elapsed = time.time() - start
        
        print(f"\nExecution time: {elapsed*1000:.2f}ms")
        print(f"Rows returned: {len(result)}")
        
        return result
```

### Monitoring Queries

**Daily metrics query:**

```sql
-- Save as scripts/daily_metrics.sql
.mode column
.headers on

SELECT 'Database Metrics' as category, '' as metric, '' as value
UNION ALL
SELECT 'Size', 'Total Size (MB)', 
    ROUND(page_count * page_size / 1024.0 / 1024.0, 2)
FROM pragma_page_count(), pragma_page_size()
UNION ALL
SELECT 'Size', 'Free Space (%)', 
    ROUND(CAST(freelist_count AS REAL) / page_count * 100, 2)
FROM pragma_page_count(), pragma_freelist_count()
UNION ALL
SELECT 'Performance', 'Cache Size (KB)', cache_size FROM pragma_cache_size()
UNION ALL
SELECT 'Configuration', 'Journal Mode', journal_mode FROM pragma_journal_mode()
UNION ALL
SELECT 'Configuration', 'Foreign Keys', foreign_keys FROM pragma_foreign_keys();

-- Table sizes
SELECT 
    'Table Sizes' as category,
    name as metric,
    (SELECT COUNT(*) FROM sqlite_master sm WHERE sm.name = m.name) as value
FROM sqlite_master m 
WHERE type='table' AND name NOT LIKE 'sqlite_%';
```

Run with:
```bash
sqlite3 ora.db < scripts/daily_metrics.sql
```

---

## Troubleshooting

### Database Locked Errors

**Symptom:** `database is locked` error during operations

**Diagnosis:**
```python
# Check for long-running connections
import sqlite3
conn = sqlite3.connect('ora.db')
# If this hangs, another process has exclusive lock

# Check WAL checkpoint
conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
```

**Solutions:**
1. Increase `busy_timeout` to 30 seconds
2. Use `BEGIN IMMEDIATE` for write transactions
3. Close connections promptly in finally blocks
4. Check for stuck processes: `ps aux | grep python`
5. Restart workflows if needed

### Integrity Check Failures

**Symptom:** `PRAGMA integrity_check` returns errors

**Immediate actions:**
```bash
# 1. Stop all writes to database
systemctl stop automation_workflows

# 2. Create emergency backup
cp ora.db ora_corrupted_$(date +%Y%m%d_%H%M%S).db

# 3. Attempt recovery
sqlite3 ora.db ".dump" | sqlite3 ora_recovered.db

# 4. Verify recovered database
sqlite3 ora_recovered.db "PRAGMA integrity_check;"

# 5. If successful, replace
mv ora.db ora_corrupted.db
mv ora_recovered.db ora.db

# 6. Restart workflows
systemctl start automation_workflows
```

### Performance Degradation

**Symptom:** Queries slower than normal

**Diagnosis steps:**

1. **Check database size:**
   ```sql
   SELECT page_count * page_size / 1024.0 / 1024.0 as size_mb
   FROM pragma_page_count(), pragma_page_size();
   ```

2. **Analyze query plan:**
   ```sql
   EXPLAIN QUERY PLAN 
   SELECT * FROM shipped_items WHERE ship_date > '2025-01-01';
   ```

3. **Check index usage:**
   ```sql
   -- Verify indexes exist
   SELECT name, sql FROM sqlite_master 
   WHERE type='index' AND tbl_name='shipped_items';
   ```

**Solutions:**
- Run `ANALYZE` to update statistics
- Run `VACUUM` if free space >25%
- Add missing indexes for common queries
- Review and optimize slow queries

### Foreign Key Violations

**Symptom:** `FOREIGN KEY constraint failed`

**Diagnosis:**
```sql
PRAGMA foreign_key_check;
-- Returns rows with FK violations
```

**Solutions:**
1. Identify orphaned records
2. Fix data inconsistencies
3. Ensure parent records exist before children
4. Adjust migration order if during ETL

---

## Backup & Recovery

### Automated Daily Backup

**Backup script:**

```bash
#!/bin/bash
# scripts/backup_database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
DB_PATH="ora.db"
LOG_FILE="/var/log/db_backup.log"

mkdir -p "$BACKUP_DIR"

echo "$(date): Starting backup..." >> "$LOG_FILE"

# Method 1: File copy (database must be idle)
cp "$DB_PATH" "$BACKUP_DIR/ora_${DATE}.db"

if [ $? -eq 0 ]; then
    # Verify backup integrity
    sqlite3 "$BACKUP_DIR/ora_${DATE}.db" "PRAGMA integrity_check;" > /tmp/integrity_check.txt
    
    if grep -q "ok" /tmp/integrity_check.txt; then
        echo "$(date): Backup successful - ora_${DATE}.db" >> "$LOG_FILE"
        
        # Compress backup
        gzip "$BACKUP_DIR/ora_${DATE}.db"
        
        # Cleanup old backups (keep 30 days)
        find "$BACKUP_DIR" -name "ora_*.db.gz" -mtime +30 -delete
        
        echo "$(date): Cleaned up backups older than 30 days" >> "$LOG_FILE"
    else
        echo "$(date): Backup integrity check FAILED" >> "$LOG_FILE"
        rm "$BACKUP_DIR/ora_${DATE}.db"
        exit 1
    fi
else
    echo "$(date): Backup FAILED" >> "$LOG_FILE"
    exit 1
fi
```

**Crontab:**
```bash
0 2 * * * /path/to/scripts/backup_database.sh
```

### Point-in-Time Recovery

**Using WAL files for recovery:**

```python
# scripts/point_in_time_recovery.py

import sqlite3
import shutil
from datetime import datetime

def restore_from_backup(backup_path, target_path='ora.db'):
    """Restore database from backup"""
    
    print(f"Restoring from: {backup_path}")
    
    # 1. Stop all automation workflows
    print("Stop all workflows before proceeding")
    input("Press Enter when workflows are stopped...")
    
    # 2. Backup current database
    current_backup = f"ora_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(target_path, current_backup)
    print(f"Current database backed up to: {current_backup}")
    
    # 3. Restore from backup
    shutil.copy(backup_path, target_path)
    
    # 4. Verify integrity
    conn = sqlite3.connect(target_path)
    result = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    
    if result == "ok":
        print("Restore successful! Database integrity verified.")
        return True
    else:
        print(f"Restore failed: {result}")
        # Restore original
        shutil.copy(current_backup, target_path)
        return False
```

---

## Common Tasks

### Adding New Data

```python
# Example: Add new inventory transaction
def add_inventory_transaction(date, sku, quantity, trans_type, notes=None):
    """Record inventory transaction"""
    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO inventory_transactions 
            (date, sku, quantity, transaction_type, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (date, sku, quantity, trans_type, notes))
        
        # Update inventory current
        if trans_type in ('Receive', 'Adjust Up'):
            conn.execute("""
                UPDATE inventory_current 
                SET current_quantity = current_quantity + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE sku = ?
            """, (quantity, sku))
        elif trans_type in ('Ship', 'Adjust Down'):
            conn.execute("""
                UPDATE inventory_current 
                SET current_quantity = current_quantity - ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE sku = ?
            """, (quantity, sku))
```

### Querying Data

```python
# Example: Get low stock alerts
def get_low_stock_items():
    """Fetch items below reorder point"""
    with db.get_connection() as conn:
        cursor = conn.execute("""
            SELECT 
                sku,
                product_name,
                current_quantity,
                reorder_point,
                alert_level,
                (reorder_point - current_quantity) as shortage
            FROM inventory_current
            WHERE alert_level IN ('low', 'critical')
            ORDER BY alert_level DESC, shortage DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
```

### Data Cleanup

```python
# Example: Archive old data
def archive_old_shipments(cutoff_date):
    """Archive shipments older than cutoff date"""
    with db.transaction() as conn:
        # Export to archive table or CSV
        cursor = conn.execute("""
            SELECT * FROM shipped_orders
            WHERE ship_date < ?
        """, (cutoff_date,))
        
        archived_count = len(cursor.fetchall())
        
        # Optional: Delete old records (be careful!)
        # conn.execute("DELETE FROM shipped_orders WHERE ship_date < ?", (cutoff_date,))
        
        return archived_count
```

---

## Emergency Procedures

### Database Corruption Recovery

**Step-by-step recovery:**

1. **Stop all automation immediately**
2. **Backup corrupted database**
3. **Attempt SQLite recovery:**
   ```bash
   sqlite3 ora_corrupted.db ".dump" | sqlite3 ora_recovered.db
   ```
4. **Verify recovered database**
5. **Restore from latest backup if recovery fails**
6. **Resume operations after verification**

### Rollback to Previous State

See `MIGRATION_GUIDE.md` for complete rollback procedures.

---

## Best Practices Summary

**✅ Always:**
- Use `db.transaction()` context manager for writes
- Close connections in finally blocks
- Run daily health checks
- Monitor database size and performance
- Keep backups for 30 days
- Test restores monthly
- Document schema changes

**❌ Never:**
- Run VACUUM during peak hours
- Disable foreign keys in production
- Delete backups without archiving
- Ignore integrity check failures
- Use multiple write connections
- Skip ANALYZE after bulk changes

---

## Support & Resources

**Documentation:**
- Schema reference: `docs/DATABASE_SCHEMA.md`
- Migration guide: `docs/MIGRATION_GUIDE.md`
- API integration: `docs/API_INTEGRATION.md`

**Logs:**
- Database health: `/var/log/db_health.log`
- Maintenance: `/var/log/db_maintenance.log`
- Backups: `/var/log/db_backup.log`
- Automation: `/var/log/automation_*.log`

**Tools:**
- SQLite CLI: `sqlite3 ora.db`
- Integrity check: `sqlite3 ora.db "PRAGMA integrity_check;"`
- Database stats: `sqlite3 ora.db < scripts/daily_metrics.sql`

# Google Sheets to SQLite Migration Guide

## Overview

This guide provides step-by-step instructions for migrating the ORA automation system from Google Sheets to SQLite database. This is a **one-time migration** that completely replaces Google Sheets as the data backend.

**Estimated Time:** 6-8 hours total
**Risk Level:** Medium (with proper validation and rollback procedures)

---

## Table of Contents

1. [Pre-Migration Preparation](#pre-migration-preparation)
2. [Migration Phases](#migration-phases)
3. [ETL Script Execution](#etl-script-execution)
4. [Data Validation](#data-validation)
5. [Rollback Procedures](#rollback-procedures)
6. [Post-Migration Tasks](#post-migration-tasks)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Migration Preparation

### 1. Backup Current Google Sheets

**Export all sheets to CSV:**

```bash
# Create backup directory
mkdir -p backups/google_sheets_$(date +%Y%m%d)

# Export each sheet (manual or via API)
# - ORA_Configuration
# - Inventory_Transactions
# - Shipped_Items_Data
# - Shipped_Orders_Data
# - ORA_Weekly_Shipped_History
# - SKU_Lot
# - ORA_Processing_State
```

**Verify backups:**
- [ ] All CSV files downloaded
- [ ] Row counts match Google Sheets
- [ ] Files are readable and not corrupted

### 2. Create Test Database

```bash
# Create test database with schema
python scripts/create_database.py --output test_ora.db --dry-run

# Verify schema
sqlite3 test_ora.db ".schema"
```

### 3. Validation Checklist

- [ ] Google Sheets API credentials are working
- [ ] All required sheets are accessible
- [ ] Test database schema is correct (12 tables)
- [ ] All indexes are created
- [ ] Foreign key constraints are enabled
- [ ] PRAGMA settings are configured (WAL mode, etc.)

### 4. Freeze Writes to Google Sheets

**48 hours before migration:**
- [ ] Disable all automation workflows
- [ ] Notify team of migration window
- [ ] Document last modified timestamps for each sheet

---

## Migration Phases

### Phase 1: Database Setup (1 hour)

**1.1 Create Production Database**

```bash
# Create database with full schema
python scripts/create_database.py --output ora.db

# Verify structure
sqlite3 ora.db <<EOF
.mode column
.headers on
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
EOF
```

**Expected output:**
```
configuration_params
inventory_current
inventory_transactions
order_items_inbox
orders_inbox
polling_state
schema_migrations
shipped_items
shipped_orders
system_kpis
weekly_shipped_history
workflows
```

**1.2 Configure SQLite Settings**

```bash
# Verify WAL mode and settings
sqlite3 ora.db <<EOF
PRAGMA journal_mode;
PRAGMA foreign_keys;
PRAGMA synchronous;
EOF
```

**Expected output:**
```
wal
1
1
```

**1.3 Insert Seed Data**

```bash
# Run seed data script
python scripts/seed_database.py --database ora.db

# Verify workflows table
sqlite3 ora.db "SELECT name, display_name FROM workflows;"
```

### Phase 2: ETL Development (2-3 hours)

**2.1 ETL Script Structure**

Create `scripts/migrate_from_sheets.py`:

```python
import sqlite3
import sys
from datetime import datetime
from services.google_sheets.api_client import GoogleSheetsClient

def migrate_table(sheet_name, table_name, transform_fn, conn, dry_run=False):
    """Generic migration function with validation"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating {sheet_name} -> {table_name}")
    
    # Fetch data from Google Sheets
    sheets_client = GoogleSheetsClient()
    data = sheets_client.read_sheet(sheet_name)
    
    # Transform data
    transformed_data = transform_fn(data)
    
    # Validate
    print(f"  Source rows: {len(data)}")
    print(f"  Transformed rows: {len(transformed_data)}")
    
    if dry_run:
        print(f"  [SKIPPED] Would insert {len(transformed_data)} rows")
        return
    
    # Insert data
    cursor = conn.cursor()
    # ... insertion logic with transaction
    
    conn.commit()
    print(f"  ✓ Inserted {len(transformed_data)} rows")

def main():
    dry_run = '--dry-run' in sys.argv
    
    # Create connection
    conn = sqlite3.connect('ora.db')
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Migration order (respects foreign key dependencies)
        migrate_table('ORA_Configuration', 'configuration_params', 
                     transform_config, conn, dry_run)
        migrate_table('Inventory_Transactions', 'inventory_transactions', 
                     transform_inventory_trans, conn, dry_run)
        migrate_table('Shipped_Orders_Data', 'shipped_orders', 
                     transform_shipped_orders, conn, dry_run)
        migrate_table('Shipped_Items_Data', 'shipped_items', 
                     transform_shipped_items, conn, dry_run)
        migrate_table('ORA_Weekly_Shipped_History', 'weekly_shipped_history', 
                     transform_weekly_history, conn, dry_run)
        
        # Verify migration
        if not dry_run:
            verify_migration(conn)
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
```

**2.2 Data Transformation Functions**

Example transformation for money values (convert to cents):

```python
def transform_config(sheets_data):
    """Transform ORA_Configuration data"""
    transformed = []
    for row in sheets_data:
        # Convert decimal values to cents if category is 'Rates'
        value = row['value']
        if row['category'] == 'Rates' and '.' in str(value):
            value = int(float(value) * 100)  # Convert to cents
        
        transformed.append({
            'category': row['category'],
            'parameter_name': row['parameter_name'],
            'value': str(value),
            'sku': row.get('sku'),
            'notes': row.get('notes'),
            'last_updated': row.get('last_updated')
        })
    return transformed
```

**2.3 Test ETL with Dry Run**

```bash
# Test without writing to database
python scripts/migrate_from_sheets.py --dry-run

# Review output for issues
# Expected: Row counts, transformation summary, no errors
```

### Phase 3: Migration Execution (1 hour)

**3.1 Final Pre-Migration Checks**

```bash
# Verify Google Sheets are frozen (no recent updates)
python scripts/check_sheets_modified.py

# Backup current (empty) database
cp ora.db ora_pre_migration_$(date +%Y%m%d_%H%M%S).db

# Free up system resources
# Stop dashboard server if running
```

**3.2 Execute Migration**

```bash
# Run actual migration
python scripts/migrate_from_sheets.py | tee migration_$(date +%Y%m%d_%H%M%S).log

# Monitor output for errors
# Expected: All tables migrated successfully
```

**3.3 Immediate Validation**

```bash
# Check row counts match
sqlite3 ora.db <<EOF
SELECT 'shipped_orders' as table_name, COUNT(*) as rows FROM shipped_orders
UNION ALL
SELECT 'shipped_items', COUNT(*) FROM shipped_items
UNION ALL
SELECT 'inventory_transactions', COUNT(*) FROM inventory_transactions
UNION ALL
SELECT 'weekly_shipped_history', COUNT(*) FROM weekly_shipped_history
UNION ALL
SELECT 'configuration_params', COUNT(*) FROM configuration_params;
EOF

# Compare with Google Sheets row counts
```

### Phase 4: Script Integration (4-5 hours)

**4.1 Create Database Utilities Module**

See `API_INTEGRATION.md` for complete `db_utils.py` implementation.

**4.2 Update Automation Scripts**

For each script:
1. Replace Google Sheets API calls with SQLite queries
2. Add transaction handling
3. Implement error recovery
4. Update logging

**Priority order:**
1. `weekly_reporter.py` - Critical for inventory tracking
2. `daily_shipment_processor.py` - High volume script
3. `shipstation_order_uploader.py` - Revenue critical
4. `shipstation_reporter.py` - Reporting
5. `main_order_import_daily_reporter.py` - Summary reports

**4.3 Test Scripts Individually**

```bash
# Test each script in DEV_MODE
export DEV_MODE=1
python src/weekly_reporter.py
python src/daily_shipment_processor.py
# ... etc
```

### Phase 5: Cutover (1 hour)

**5.1 Production Deployment**

```bash
# Stop all workflows
# Update .env with database path
echo "DATABASE_PATH=/path/to/ora.db" >> .env

# Restart workflows
python scripts/restart_workflows.py
```

**5.2 Monitor First Runs**

```bash
# Watch logs for first 24 hours
tail -f logs/automation_*.log

# Check for errors
grep -i error logs/automation_*.log
```

**5.3 Dashboard Verification**

- [ ] Open dashboard UI
- [ ] Verify all KPI cards display data
- [ ] Check workflow status table
- [ ] Confirm inventory alerts work
- [ ] Test pending orders count

---

## Data Validation

### Automated Validation Queries

**1. Row Count Comparison**

```sql
-- Total shipped orders match
SELECT COUNT(*) FROM shipped_orders;
-- Compare with Google Sheets row count

-- Total shipped items match
SELECT COUNT(*) FROM shipped_items;
-- Compare with Google Sheets row count
```

**2. Sum Validation (Critical Calculations)**

```sql
-- Weekly shipped history totals per week
SELECT start_date, SUM(quantity_shipped) as total
FROM weekly_shipped_history
GROUP BY start_date
ORDER BY start_date DESC
LIMIT 8;
-- Compare with Google Sheets weekly totals

-- Inventory transaction sums per SKU
SELECT sku, 
    SUM(CASE WHEN transaction_type IN ('Receive', 'Adjust Up') THEN quantity ELSE 0 END) as received,
    SUM(CASE WHEN transaction_type IN ('Ship', 'Adjust Down') THEN quantity ELSE 0 END) as shipped
FROM inventory_transactions
GROUP BY sku;
-- Compare with Google Sheets calculations
```

**3. Foreign Key Integrity**

```sql
-- Verify all shipped_items have valid orders
SELECT COUNT(*) FROM shipped_items si
LEFT JOIN shipped_orders so ON si.order_number = so.order_number
WHERE so.order_number IS NULL;
-- Expected: 0
```

**4. Data Range Checks**

```sql
-- Check for invalid dates
SELECT COUNT(*) FROM shipped_orders WHERE ship_date > DATE('now');
-- Expected: 0

-- Check for negative quantities
SELECT COUNT(*) FROM inventory_transactions WHERE quantity < 0 
    AND transaction_type NOT IN ('Adjust Down', 'Ship');
-- Expected: 0
```

### Manual Validation Checklist

- [ ] Spot-check 10 random orders (compare Sheets vs SQLite)
- [ ] Verify latest week's shipment totals
- [ ] Confirm SKU configuration parameters
- [ ] Check reorder points for all products
- [ ] Validate workflow execution history
- [ ] Review system KPIs for current week

---

## Rollback Procedures

### When to Rollback

Execute rollback if:
- Row count mismatches exceed 1%
- Critical calculation errors found
- Foreign key violations detected
- Script integration fails after 3 attempts
- Data corruption suspected

### Rollback Steps

**1. Stop All Automation**

```bash
# Stop all workflows
python scripts/stop_workflows.py

# Verify nothing is running
ps aux | grep python
```

**2. Restore Pre-Migration State**

```bash
# Remove corrupted database
mv ora.db ora_corrupted_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp ora_pre_migration_YYYYMMDD_HHMMSS.db ora.db

# Or restore to Google Sheets only mode
rm ora.db
```

**3. Revert Script Changes**

```bash
# Use git to restore previous versions
git checkout HEAD~1 src/weekly_reporter.py
git checkout HEAD~1 src/daily_shipment_processor.py
# ... etc
```

**4. Resume Google Sheets Mode**

```bash
# Update .env to use Google Sheets
sed -i '/DATABASE_PATH/d' .env

# Restart workflows
python scripts/restart_workflows.py
```

**5. Document Rollback**

```bash
# Log rollback reason and time
echo "$(date): Rollback executed due to: [REASON]" >> migration_rollback.log
```

---

## Post-Migration Tasks

### Immediate (Day 1)

- [ ] Monitor all automation scripts for 24 hours
- [ ] Verify dashboard displays real-time data
- [ ] Test manual data entry (if applicable)
- [ ] Run `ANALYZE` on all tables
- [ ] Document any issues in migration log

### Week 1

- [ ] Set up daily backup cron job
- [ ] Configure database monitoring alerts
- [ ] Train team on new database operations
- [ ] Update operational runbooks
- [ ] Archive Google Sheets (mark as read-only)

### Week 2-4

- [ ] Optimize slow queries if found
- [ ] Add additional indexes if needed
- [ ] Review and tune PRAGMA settings
- [ ] Document lessons learned
- [ ] Plan Google Sheets deprecation

### Database Maintenance Setup

**Daily Backup Script:**

```bash
#!/bin/bash
# /scripts/backup_database.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/database"
DB_PATH="/path/to/ora.db"

# Create backup
cp "$DB_PATH" "$BACKUP_DIR/ora_${DATE}.db"

# Verify backup
if [ $? -eq 0 ]; then
    echo "$(date): Backup successful - ora_${DATE}.db" >> /var/log/db_backup.log
else
    echo "$(date): Backup FAILED" >> /var/log/db_backup.log
    exit 1
fi

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "ora_*.db" -mtime +30 -delete

# Log cleanup
echo "$(date): Cleaned up backups older than 30 days" >> /var/log/db_backup.log
```

**Add to crontab:**

```bash
# Daily backup at 2 AM
0 2 * * * /scripts/backup_database.sh
```

---

## Troubleshooting

### Common Issues

**Issue 1: Row count mismatch**

```bash
# Symptom: SQLite has fewer rows than Google Sheets

# Diagnosis:
python scripts/compare_row_counts.py --sheets --database

# Resolution:
# Check for duplicate keys in source data
# Review transformation function logic
# Re-run ETL for specific table
```

**Issue 2: Foreign key constraint violations**

```bash
# Symptom: "FOREIGN KEY constraint failed"

# Diagnosis:
sqlite3 ora.db "PRAGMA foreign_key_check;"

# Resolution:
# Ensure parent records exist before child records
# Adjust migration order in ETL script
# Clean orphaned records in source data
```

**Issue 3: Data type conversion errors**

```bash
# Symptom: STRICT table rejects data

# Diagnosis:
# Review data types in transformation functions
# Check for NULL values in NOT NULL columns

# Resolution:
# Fix transformation function
# Add default values where appropriate
# Validate source data before migration
```

**Issue 4: Performance degradation**

```bash
# Symptom: Queries slower than expected

# Diagnosis:
sqlite3 ora.db "EXPLAIN QUERY PLAN SELECT * FROM shipped_items WHERE ship_date > '2025-01-01';"

# Resolution:
# Run ANALYZE to update statistics
sqlite3 ora.db "ANALYZE;"

# Add missing indexes if needed
# Review query patterns
```

### Emergency Contacts

**Database Issues:**
- Check logs: `/var/log/automation_*.log`
- Review schema: `docs/DATABASE_SCHEMA.md`
- Operations guide: `docs/DATABASE_OPERATIONS.md`

**Migration Issues:**
- Rollback procedure: See "Rollback Procedures" above
- Google Sheets backup: `/backups/google_sheets_YYYYMMDD/`
- Database backup: `/backups/database/ora_YYYYMMDD.db`

### Success Criteria

Migration is successful when:
- ✅ All row counts match source (±1% acceptable for calculated fields)
- ✅ Weekly totals match Google Sheets
- ✅ No foreign key violations
- ✅ All automation scripts run without errors
- ✅ Dashboard displays accurate real-time data
- ✅ Backups running daily
- ✅ Team trained on new system

---

## Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| Preparation | 2-3 hours | Backups, test database, validation |
| Database Setup | 1 hour | Create production DB, seed data |
| ETL Development | 2-3 hours | Write migration script, test dry-run |
| Execution | 1 hour | Run migration, validate data |
| Script Integration | 4-5 hours | Update 5 automation scripts |
| Cutover | 1 hour | Deploy, monitor, verify dashboard |
| **TOTAL** | **11-14 hours** | Complete Google Sheets replacement |

**Recommended Schedule:**
- **Day 1 (4 hours):** Preparation + Database Setup + ETL Development
- **Day 2 (2 hours):** ETL testing and dry runs
- **Day 3 (4-6 hours):** Execution + Script Integration + Cutover
- **Day 4-7:** Monitoring and optimization

---

## Appendix

### A. Sheets to Table Mapping

| Google Sheet | SQLite Table | Notes |
|--------------|--------------|-------|
| ORA_Configuration | configuration_params | Convert rates to cents |
| Inventory_Transactions | inventory_transactions | Direct mapping |
| Shipped_Items_Data | shipped_items | Add FK to shipped_orders |
| Shipped_Orders_Data | shipped_orders | Ensure unique order_number |
| ORA_Weekly_Shipped_History | weekly_shipped_history | Verify weekly totals |
| SKU_Lot | configuration_params | category='SKU_Lot' |
| ORA_Processing_State | polling_state | Single row table |

### B. Data Type Conversions

| Google Sheets Type | SQLite Type | Transformation |
|-------------------|-------------|----------------|
| Currency ($12.34) | INTEGER | Multiply by 100, store cents |
| Date (MM/DD/YYYY) | DATE | Convert to YYYY-MM-DD |
| Boolean (TRUE/FALSE) | INTEGER | 1 for TRUE, 0 for FALSE |
| Text | TEXT | Direct copy |
| Number | INTEGER or REAL | Based on precision needs |

### C. Validation Queries

Save these as `scripts/validate_migration.sql`:

```sql
-- Validation Query Set
.mode column
.headers on

-- 1. Table row counts
SELECT 'Table Row Counts' as check_type;
SELECT 'shipped_orders' as table_name, COUNT(*) as rows FROM shipped_orders
UNION ALL SELECT 'shipped_items', COUNT(*) FROM shipped_items
UNION ALL SELECT 'inventory_transactions', COUNT(*) FROM inventory_transactions
UNION ALL SELECT 'weekly_shipped_history', COUNT(*) FROM weekly_shipped_history
UNION ALL SELECT 'configuration_params', COUNT(*) FROM configuration_params;

-- 2. Foreign key integrity
SELECT 'Foreign Key Integrity' as check_type;
SELECT COUNT(*) as orphaned_shipped_items FROM shipped_items si
LEFT JOIN shipped_orders so ON si.order_number = so.order_number
WHERE so.order_number IS NULL;

-- 3. Data range validation
SELECT 'Data Range Checks' as check_type;
SELECT COUNT(*) as future_dates FROM shipped_orders WHERE ship_date > DATE('now');
SELECT COUNT(*) as negative_quantities FROM inventory_transactions 
WHERE quantity < 0 AND transaction_type IN ('Receive', 'Adjust Up');

-- 4. Weekly totals
SELECT 'Weekly Shipped Totals' as check_type;
SELECT start_date, SUM(quantity_shipped) as total
FROM weekly_shipped_history
GROUP BY start_date
ORDER BY start_date DESC
LIMIT 4;
```

Run validation:
```bash
sqlite3 ora.db < scripts/validate_migration.sql
```

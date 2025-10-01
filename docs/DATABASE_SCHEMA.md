# ORA Automation Project - Database Schema

## Table of Contents

- [Database Technology Choice](#database-technology-choice)
- [SQLite Configuration](#sqlite-configuration)
- [Tables & Field Definitions](#tables--field-definitions)
  - [workflows](#workflows)
  - [inventory_current](#inventory_current)
  - [inventory_transactions](#inventory_transactions)
  - [shipped_items](#shipped_items)
  - [shipped_orders](#shipped_orders)
  - [weekly_shipped_history](#weekly_shipped_history)
  - [system_kpis](#system_kpis)
  - [configuration_params](#configuration_params)
  - [orders_inbox](#orders_inbox)
  - [order_items_inbox](#order_items_inbox)
  - [polling_state](#polling_state)
  - [schema_migrations](#schema_migrations)
- [Foreign Key Relationships](#foreign-key-relationships)
- [Data Flow Integration](#data-flow-integration)
- [Indexing Strategy](#indexing-strategy)
- [Initial Seed Data](#initial-seed-data)
- [Migration from Google Sheets](#migration-from-google-sheets)

## Database Technology Choice

**Selected: SQLite with Write-Ahead Logging (WAL)**

### Decision Rationale
- **Zero operational cost** - Built into Replit, no hosting fees
- **Minimal development time** - Simple file-based database, no server setup
- **Sufficient for workload** - Handles 50-100 orders/day, 1 year of data easily
- **Excellent concurrency** - WAL mode supports multiple readers + single writer
- **Simple backups** - Daily file copy with timestamp

### When to Migrate to PostgreSQL
Consider migration if any of these occur:
- Sustained concurrent writes >10 transactions/second
- Database size exceeds 1-2 GB
- Complex analytical queries cause performance issues
- Need advanced features (full-text search, partitioning, replication)

## SQLite Configuration

### Required PRAGMA Settings
**Must run on EVERY database connection:**

```sql
PRAGMA journal_mode = WAL;           -- Enable Write-Ahead Logging for concurrency
PRAGMA synchronous = NORMAL;         -- Balance safety and performance
PRAGMA foreign_keys = ON;            -- Enable foreign key constraints
PRAGMA busy_timeout = 8000;          -- 8 second wait for lock acquisition
PRAGMA temp_store = MEMORY;          -- Use RAM for temporary tables
PRAGMA cache_size = -20000;          -- 20MB page cache (~20,000 KB)
```

### Maintenance Schedule

**After bulk data loads:**
```sql
ANALYZE;  -- Update query planner statistics
```

**Monthly or after large deletes:**
```sql
VACUUM;  -- Reclaim unused space and defragment
```

### File Size Projections
- Current data volume: ~50MB/year
- With 1 year retention: <100MB database file
- WAL file: Typically 10-20% of main database size

## Tables & Field Definitions

### **workflows**
*Automation workflow execution tracking and status*

```sql
CREATE TABLE workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'scheduled')),
    last_run_at DATETIME,
    duration_seconds INTEGER,
    records_processed INTEGER,
    details TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE INDEX idx_workflows_status ON workflows(status, enabled);
CREATE INDEX idx_workflows_enabled ON workflows(enabled);
CREATE INDEX idx_workflows_last_run ON workflows(status, last_run_at);
```

### **inventory_current**
*Current stock levels and alert status for all products*

```sql
CREATE TABLE inventory_current (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    current_quantity INTEGER NOT NULL,
    weekly_avg_cents INTEGER,                    -- 12-month rolling average (stored as cents)
    alert_level TEXT NOT NULL DEFAULT 'normal' CHECK (alert_level IN ('normal', 'low', 'critical')),
    reorder_point INTEGER NOT NULL DEFAULT 50,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE INDEX idx_inventory_current_alert ON inventory_current(alert_level);
CREATE INDEX idx_inventory_current_sku ON inventory_current(sku);
```

### **inventory_transactions**
*All inventory movements and adjustments (append-only audit trail)*

```sql
CREATE TABLE inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity != 0),
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Receive', 'Ship', 'Adjust Up', 'Adjust Down')),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE INDEX idx_inv_trans_sku_date ON inventory_transactions(sku, date);
CREATE INDEX idx_inv_trans_date ON inventory_transactions(date);
CREATE INDEX idx_inv_trans_type ON inventory_transactions(transaction_type);
```

### **shipped_items**
*Individual line items from all shipments*

```sql
CREATE TABLE shipped_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_date DATE NOT NULL,
    sku_lot TEXT,
    base_sku TEXT NOT NULL,
    quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
    order_number TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number)
) STRICT;

-- Indexes
CREATE INDEX idx_shipped_items_date ON shipped_items(ship_date);
CREATE INDEX idx_shipped_items_sku_date ON shipped_items(base_sku, ship_date);
CREATE INDEX idx_shipped_items_order ON shipped_items(order_number);
```

### **shipped_orders**
*Complete shipment records by order*

```sql
CREATE TABLE shipped_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_date DATE NOT NULL,
    order_number TEXT NOT NULL UNIQUE,
    customer_email TEXT,
    total_items INTEGER DEFAULT 0,
    shipstation_order_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE INDEX idx_shipped_orders_date ON shipped_orders(ship_date);
CREATE INDEX idx_shipped_orders_number ON shipped_orders(order_number);
```

### **weekly_shipped_history**
*Aggregated weekly shipment data by SKU*

```sql
CREATE TABLE weekly_shipped_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    sku TEXT NOT NULL,
    quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped >= 0),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(start_date, end_date, sku)
) STRICT;

-- Indexes
CREATE INDEX idx_weekly_history_dates ON weekly_shipped_history(start_date, end_date);
CREATE INDEX idx_weekly_history_sku_start ON weekly_shipped_history(sku, start_date);
```

### **system_kpis**
*Daily snapshots of key business metrics*

```sql
CREATE TABLE system_kpis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date DATE NOT NULL UNIQUE,
    orders_today INTEGER DEFAULT 0,
    shipments_sent INTEGER DEFAULT 0,
    pending_uploads INTEGER DEFAULT 0,
    system_status TEXT NOT NULL DEFAULT 'online' CHECK (system_status IN ('online', 'degraded', 'offline')),
    total_revenue_cents INTEGER,                 -- Daily revenue stored as cents
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE INDEX idx_kpis_date ON system_kpis(snapshot_date);
```

### **configuration_params**
*Business configuration and settings (replaces ORA_Configuration sheet)*

```sql
CREATE TABLE configuration_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    value TEXT NOT NULL,
    sku TEXT,
    notes TEXT,
    last_updated DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, parameter_name, sku)
) STRICT;

-- Indexes
CREATE INDEX idx_config_category ON configuration_params(category);
CREATE INDEX idx_config_sku ON configuration_params(sku);
```

### **orders_inbox**
*Staging area for incoming orders from XML file before ShipStation upload*

**Purpose:** Stores orders parsed from X-Cart XML files, tracks upload status to ShipStation, provides "Pending Uploads" dashboard count

```sql
CREATE TABLE orders_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    order_date DATE NOT NULL,
    customer_email TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded', 'failed')),
    shipstation_order_id TEXT,
    total_items INTEGER DEFAULT 0,
    total_amount_cents INTEGER,                  -- Order total stored as cents
    source_system TEXT DEFAULT 'X-Cart',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE INDEX idx_orders_inbox_status ON orders_inbox(status, created_at);
CREATE INDEX idx_orders_inbox_date ON orders_inbox(order_date);
```

### **order_items_inbox**
*Line items for orders in the inbox (before ShipStation upload)*

**Purpose:** Stores individual product lines for each order, needed to create complete ShipStation orders

```sql
CREATE TABLE order_items_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    sku_lot TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER,                    -- Price per unit stored as cents
    FOREIGN KEY (order_id) REFERENCES orders_inbox(id) ON DELETE CASCADE
) STRICT;

-- Indexes
CREATE INDEX idx_order_items_inbox_order ON order_items_inbox(order_id);
CREATE INDEX idx_order_items_inbox_sku ON order_items_inbox(sku);
```

### **polling_state**
*Tracks XML file polling state for 5-minute order detection*

**Purpose:** Single-row table to track last poll time and file state for detecting new orders

```sql
CREATE TABLE polling_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),       -- Single row enforcement
    last_polled_at DATETIME,
    last_xml_checksum TEXT,                      -- SHA256 hash to detect file changes
    last_seen_order_number TEXT,
    metadata TEXT,                               -- JSON for flexible state storage
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Initial row
INSERT INTO polling_state (id) VALUES (1);
```

### **schema_migrations**
*Database schema version tracking*

**Purpose:** Track applied migrations for schema evolution and rollback

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,
    checksum TEXT                                -- MD5/SHA256 of migration SQL
) STRICT;

-- Initial migration
INSERT INTO schema_migrations (version, description) VALUES
(1, 'Initial schema with 12 tables for Google Sheets replacement');
```

## Foreign Key Relationships

```
shipped_items.order_number ──→ shipped_orders.order_number
order_items_inbox.order_id ──→ orders_inbox.id (CASCADE DELETE)
```

**Note:** Foreign keys are enforced with `PRAGMA foreign_keys = ON` (must be set on every connection)

## Data Flow Integration

### **From Google Sheets to SQLite**
**One-time ETL migration:**
- `ORA_Configuration` → `configuration_params`
- `Inventory_Transactions` → `inventory_transactions`
- `Shipped_Items_Data` → `shipped_items`
- `Shipped_Orders_Data` → `shipped_orders`
- `ORA_Weekly_Shipped_History` → `weekly_shipped_history`
- `SKU_Lot` → `configuration_params` (category='SKU_Lot')
- `ORA_Processing_State` → `polling_state`

### **From Automation Scripts to Database**

**weekly_reporter.py:**
- Reads: `configuration_params`, `inventory_transactions`, `shipped_items`, `weekly_shipped_history`
- Writes: `inventory_current`, `system_kpis`, `workflows`

**daily_shipment_processor.py:**
- Reads: ShipStation API, `configuration_params`
- Writes: `shipped_items`, `shipped_orders`, `weekly_shipped_history`, `workflows`

**shipstation_order_uploader.py:**
- Reads: `orders_inbox` (WHERE status='pending'), `order_items_inbox`, `configuration_params`
- Writes: Updates `orders_inbox.status` and `shipstation_order_id`, `workflows`

**XML Polling Service (5-minute intervals):**
- Reads: Google Drive XML file, `polling_state`
- Writes: `orders_inbox`, `order_items_inbox`, `polling_state`

### **For Dashboard Queries**

**Workflow Status:**
```sql
SELECT name, display_name, status, last_run_at, records_processed 
FROM workflows 
WHERE enabled = 1
ORDER BY last_run_at DESC;
```

**Inventory Alerts:**
```sql
SELECT sku, product_name, current_quantity, alert_level, reorder_point
FROM inventory_current 
WHERE alert_level != 'normal'
ORDER BY 
    CASE alert_level 
        WHEN 'critical' THEN 1 
        WHEN 'low' THEN 2 
        ELSE 3 
    END;
```

**Today's KPIs:**
```sql
SELECT 
    orders_today,
    shipments_sent,
    pending_uploads,
    system_status,
    total_revenue_cents / 100.0 AS total_revenue_dollars
FROM system_kpis 
WHERE snapshot_date = DATE('now');
```

**Pending Orders Count:**
```sql
SELECT COUNT(*) AS pending_count
FROM orders_inbox 
WHERE status = 'pending';
```

**Weekly Shipping Trends:**
```sql
SELECT sku, start_date, quantity_shipped 
FROM weekly_shipped_history 
WHERE start_date >= DATE('now', '-8 weeks')
ORDER BY sku, start_date;
```

## Indexing Strategy

### Performance Optimization Indexes

```sql
-- Workflows
CREATE INDEX idx_workflows_status ON workflows(status, enabled);
CREATE INDEX idx_workflows_enabled ON workflows(enabled);
CREATE INDEX idx_workflows_last_run ON workflows(status, last_run_at);

-- Inventory
CREATE INDEX idx_inventory_current_alert ON inventory_current(alert_level);
CREATE INDEX idx_inventory_current_sku ON inventory_current(sku);
CREATE INDEX idx_inv_trans_sku_date ON inventory_transactions(sku, date);
CREATE INDEX idx_inv_trans_date ON inventory_transactions(date);
CREATE INDEX idx_inv_trans_type ON inventory_transactions(transaction_type);

-- Shipments
CREATE INDEX idx_shipped_items_date ON shipped_items(ship_date);
CREATE INDEX idx_shipped_items_sku_date ON shipped_items(base_sku, ship_date);
CREATE INDEX idx_shipped_items_order ON shipped_items(order_number);
CREATE INDEX idx_shipped_orders_date ON shipped_orders(ship_date);
CREATE INDEX idx_shipped_orders_number ON shipped_orders(order_number);

-- Weekly History
CREATE INDEX idx_weekly_history_dates ON weekly_shipped_history(start_date, end_date);
CREATE INDEX idx_weekly_history_sku_start ON weekly_shipped_history(sku, start_date);

-- KPIs
CREATE INDEX idx_kpis_date ON system_kpis(snapshot_date);

-- Configuration
CREATE INDEX idx_config_category ON configuration_params(category);
CREATE INDEX idx_config_sku ON configuration_params(sku);

-- Orders Inbox
CREATE INDEX idx_orders_inbox_status ON orders_inbox(status, created_at);
CREATE INDEX idx_orders_inbox_date ON orders_inbox(order_date);
CREATE INDEX idx_order_items_inbox_order ON order_items_inbox(order_id);
CREATE INDEX idx_order_items_inbox_sku ON order_items_inbox(sku);
```

## Initial Seed Data

```sql
-- Seed workflows
INSERT INTO workflows (name, display_name, status, enabled) VALUES
('weekly_reporter', 'Weekly Inventory Reporter', 'scheduled', 1),
('daily_shipment_processor', 'Daily Shipment Processor', 'scheduled', 1),
('shipstation_order_uploader', 'ShipStation Order Uploader', 'scheduled', 1),
('shipstation_reporter', 'ShipStation Reporter', 'scheduled', 1),
('main_order_import_daily_reporter', 'Daily Import Reporter', 'scheduled', 1),
('xml_polling_service', 'XML File Polling Service', 'scheduled', 1);

-- Seed key products in inventory
INSERT INTO inventory_current (sku, product_name, current_quantity, reorder_point) VALUES
('17612', 'ORA Clarity Complete Mouthwash', 950, 50),
('17914', 'ORA Clarity Rinse Refill', 680, 40), 
('17904', 'ORA Essential Kit', 420, 30),
('17975', 'ORA Travel Pack', 280, 25),
('18675', 'ORA Premium Bundle', 180, 20);

-- Initialize polling state
INSERT INTO polling_state (id) VALUES (1);

-- Initial schema version
INSERT INTO schema_migrations (version, description) VALUES
(1, 'Initial schema - 12 tables for Google Sheets replacement');
```

## Migration from Google Sheets

### Migration Strategy

**Phase 1: Database Setup (2-3 hours)**
1. Create SQLite database with all 12 tables
2. Enable WAL mode and configure PRAGMAs
3. Create all indexes
4. Insert initial seed data

**Phase 2: ETL Development (2-3 hours)**
1. Build one-time ETL script using existing Google Sheets client
2. Implement data validation and row count verification
3. Add checksum validation for critical calculations
4. Test with dry-run mode

**Phase 3: Migration Execution (1 hour)**
1. Freeze Google Sheets writes
2. Take final Sheets backup (export to CSV)
3. Run ETL in single transaction per table
4. Verify row counts match source
5. Validate sample calculations (weekly totals, inventory sums)
6. Run ANALYZE on all tables

**Phase 4: Script Integration (4-5 hours)**
1. Update 5 automation scripts to use SQLite
2. Create db_utils.py module with connection management
3. Implement transaction handling (BEGIN IMMEDIATE)
4. Add UPSERT operations for idempotency
5. Test all workflows in DEV_MODE

**Phase 5: Cutover (1 hour)**
1. Switch automation scripts to production database
2. Validate dashboard displays correctly
3. Monitor for 24 hours
4. Set up daily backup script
5. Document Sheets deprecation

### ETL Validation Checklist

**Pre-Migration:**
- [ ] Verify all Google Sheets tabs are accessible
- [ ] Export Sheets to CSV backup
- [ ] Create test database with sample data
- [ ] Validate data types and constraints

**During Migration:**
- [ ] Run ETL in transaction per table
- [ ] Verify row counts: source vs destination
- [ ] Check unique constraints (no duplicates)
- [ ] Validate foreign key relationships
- [ ] Compare weekly_shipped_history totals
- [ ] Verify inventory transaction sums

**Post-Migration:**
- [ ] Run ANALYZE on all tables
- [ ] Test all dashboard queries
- [ ] Execute automation scripts in test mode
- [ ] Verify pending orders workflow
- [ ] Take database backup snapshot

### Backup & Rollback Strategy

**Daily Backups:**
```bash
#!/bin/bash
# Daily backup script
DATE=$(date +%Y%m%d)
cp /path/to/ora.db /path/to/backups/ora_${DATE}.db
# Keep last 30 days
find /path/to/backups -name "ora_*.db" -mtime +30 -delete
```

**Pre-Migration Backup:**
```bash
# Take snapshot before migration
cp ora.db ora_pre_migration_$(date +%Y%m%d_%H%M%S).db
```

**Rollback Process:**
1. Stop all automation scripts
2. Restore from backup: `cp backup.db ora.db`
3. Restart scripts
4. Verify data integrity

### Schema Evolution Process

**Making Schema Changes:**
1. Create migration SQL file: `migrations/002_add_column.sql`
2. Test on copy of production database
3. Document in schema_migrations table
4. Apply during low-traffic window
5. Run ANALYZE after structural changes

**Example Migration:**
```sql
-- migrations/002_add_source_column.sql
ALTER TABLE orders_inbox ADD COLUMN source_file TEXT;
UPDATE orders_inbox SET source_file = 'legacy' WHERE source_file IS NULL;

INSERT INTO schema_migrations (version, description) VALUES
(2, 'Added source_file column to orders_inbox for file tracking');
```

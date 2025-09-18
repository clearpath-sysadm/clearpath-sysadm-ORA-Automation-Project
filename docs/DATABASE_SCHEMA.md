# ORA Automation Project - Database Schema

## Table of Contents

- [SQLite Tables & Field Definitions](#sqlite-tables--field-definitions)
  - [workflows](#workflows)
  - [inventory_current](#inventory_current)
  - [inventory_transactions](#inventory_transactions)
  - [shipped_items](#shipped_items)
  - [shipped_orders](#shipped_orders)
  - [weekly_shipped_history](#weekly_shipped_history)
  - [system_kpis](#system_kpis)
  - [configuration_params](#configuration_params)
- [Data Flow Integration](#data-flow-integration)
  - [From Automation Scripts to Database](#from-automation-scripts-to-database)
  - [For Dashboard Queries](#for-dashboard-queries)
- [Initial Seed Data](#initial-seed-data)
- [Indexing Strategy](#indexing-strategy)

## SQLite Tables & Field Definitions

### **workflows**
*Current status and metadata for each automation workflow*

```sql
CREATE TABLE workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- weekly_reporter, daily_shipment_processor, shipstation_order_uploader, shipstation_reporter, main_order_import_daily_reporter
    display_name TEXT NOT NULL,          -- Weekly Reporter, Daily Shipment Processor, etc.
    status TEXT NOT NULL,                -- running, completed, failed, scheduled
    last_run_at DATETIME,                -- execution timestamp
    duration_seconds INTEGER,            -- runtime in seconds
    records_processed INTEGER,           -- items/orders handled per run
    details TEXT,                        -- success/error logs
    enabled BOOLEAN DEFAULT 1,           -- on/off toggle
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **inventory_current**
*Current stock levels and alert status for all products*

```sql
CREATE TABLE inventory_current (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,            -- 17612, 17914, 17904, 17975, 18675
    product_name TEXT NOT NULL,          -- ORA Clarity Complete Mouthwash, etc.
    current_quantity INTEGER NOT NULL,   -- current stock level
    weekly_avg DECIMAL(10,2),            -- 12-month rolling average from weekly shipped history
    alert_level TEXT DEFAULT 'normal',   -- normal, low, critical (calculated from reorder points)
    reorder_point INTEGER DEFAULT 50,    -- threshold for low stock alerts
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **inventory_transactions**
*All inventory movements and adjustments*

```sql
CREATE TABLE inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,                  -- transaction date
    sku TEXT NOT NULL,                   -- product SKU
    quantity INTEGER NOT NULL,           -- amount (positive/negative)
    transaction_type TEXT NOT NULL,      -- Receive, Ship, Adjust Up, Adjust Down
    notes TEXT,                          -- optional details
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **shipped_items**
*Individual line items from all shipments*

```sql
CREATE TABLE shipped_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_date DATE NOT NULL,             -- when shipped
    sku_lot TEXT,                        -- 17612 - Lot A, etc.
    base_sku TEXT NOT NULL,              -- underlying product SKU
    quantity_shipped INTEGER NOT NULL,   -- amount sent
    order_number TEXT,                   -- links to orders
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **shipped_orders**
*Complete shipment records by order*

```sql
CREATE TABLE shipped_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_date DATE NOT NULL,             -- shipment date
    order_number TEXT NOT NULL UNIQUE,   -- unique order ID
    customer_email TEXT,                 -- recipient
    total_items INTEGER DEFAULT 0,       -- item count
    shipstation_order_id TEXT,           -- external reference
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **weekly_shipped_history**
*Aggregated weekly shipment data by SKU*

```sql
CREATE TABLE weekly_shipped_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date DATE NOT NULL,            -- week beginning (Monday)
    end_date DATE NOT NULL,              -- week end (Sunday)
    sku TEXT NOT NULL,                   -- product SKU
    quantity_shipped INTEGER NOT NULL,   -- weekly total
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(start_date, end_date, sku)
);
```

### **system_kpis**
*Daily snapshots of key business metrics*

```sql
CREATE TABLE system_kpis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date DATE NOT NULL UNIQUE,  -- daily date
    orders_today INTEGER DEFAULT 0,      -- order count
    shipments_sent INTEGER DEFAULT 0,    -- processed shipments
    pending_uploads INTEGER DEFAULT 0,   -- waiting orders
    system_status TEXT DEFAULT 'online', -- online, degraded, offline
    total_revenue DECIMAL(10,2),         -- optional daily revenue
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **configuration_params**
*Business configuration and settings from ORA_Configuration*

```sql
CREATE TABLE configuration_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,              -- Key Products, Rates, PalletConfig, InitialInventory, Inventory, Reporting
    parameter_name TEXT NOT NULL,        -- StorageRate, HandlingRate, CurrentQty, etc.
    value TEXT NOT NULL,                 -- parameter value
    sku TEXT,                            -- associated product (if applicable)
    notes TEXT,                          -- description
    last_updated DATE,                   -- change timestamp
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, parameter_name, sku)
);
```

## Data Flow Integration

### **From Automation Scripts to Database**

**weekly_reporter.py:**
- Updates `inventory_current` with calculated stock levels
- Updates `workflows` with execution status and timing

**daily_shipment_processor.py:**
- Inserts into `shipped_items` from ShipStation API
- Inserts into `shipped_orders` with unique order tracking  
- Aggregates data into `weekly_shipped_history`

**shipstation_order_uploader.py:**
- Updates `workflows` with upload status and record counts
- Links with `shipped_orders` for order lifecycle tracking

**Configuration Data:**
- `configuration_params` stores all business rules from ora_configuration.json
- Includes product definitions, rates, pallet configs, initial inventory

### **For Dashboard Queries**

**Current Status:**
```sql
SELECT name, display_name, status, last_run_at, records_processed 
FROM workflows WHERE enabled = 1;
```

**Inventory Alerts:**
```sql
SELECT sku, product_name, current_quantity, alert_level 
FROM inventory_current WHERE alert_level != 'normal';
```

**Today's KPIs:**
```sql
SELECT * FROM system_kpis WHERE snapshot_date = DATE('now');
```

**Weekly Trends:**
```sql
SELECT sku, start_date, quantity_shipped 
FROM weekly_shipped_history 
WHERE start_date >= DATE('now', '-8 weeks')
ORDER BY sku, start_date;
```

## Initial Seed Data

```sql
-- Seed workflows
INSERT INTO workflows (name, display_name, status, enabled) VALUES
('weekly_reporter', 'Weekly Inventory Reporter', 'scheduled', 1),
('daily_shipment_processor', 'Daily Shipment Processor', 'scheduled', 1),
('shipstation_order_uploader', 'ShipStation Order Uploader', 'scheduled', 1),
('shipstation_reporter', 'ShipStation Reporter', 'scheduled', 1),
('main_order_import_daily_reporter', 'Daily Import Reporter', 'scheduled', 1);

-- Seed key products
INSERT INTO inventory_current (sku, product_name, current_quantity, reorder_point) VALUES
('17612', 'ORA Clarity Complete Mouthwash', 950, 50),
('17914', 'ORA Clarity Rinse Refill', 680, 40), 
('17904', 'ORA Essential Kit', 420, 30),
('17975', 'ORA Travel Pack', 280, 25),
('18675', 'ORA Premium Bundle', 180, 20);
```

## Indexing Strategy

```sql
-- Performance indexes for common queries
CREATE INDEX idx_workflows_status ON workflows(status, enabled);
CREATE INDEX idx_inventory_current_alert ON inventory_current(alert_level);
CREATE INDEX idx_shipped_items_date_sku ON shipped_items(ship_date, base_sku);
CREATE INDEX idx_weekly_history_sku_date ON weekly_shipped_history(sku, start_date);
CREATE INDEX idx_transactions_date_sku ON inventory_transactions(date, sku);
CREATE INDEX idx_kpis_date ON system_kpis(snapshot_date);
```
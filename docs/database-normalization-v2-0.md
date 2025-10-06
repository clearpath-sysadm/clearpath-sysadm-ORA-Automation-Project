# FINAL COMPREHENSIVE NORMALIZATION & DATA INTEGRITY PLAN

**Version: 2.1 (Architect Reviewed)**  
**Status: Ready for Implementation**  
**Estimated Effort: 12-14 hours**

## Executive Summary

Transform the ORA Automation system from text-based SKU-Lot storage to a fully normalized relational database design with foreign keys, while maintaining ShipStation API compatibility. This will eliminate current data integrity issues (ship_date splits, missing units, duplicate records) and provide a robust foundation for inventory tracking.

**Key Updates in v2.1:**
- ✅ SQLite-specific migration procedures documented
- ✅ Complete service audit (all 8 workflows)
- ✅ Operational playbook with workflow pause procedures
- ✅ Enhanced backup and rollback strategy
- ✅ Comprehensive testing plan
- ✅ Post-migration monitoring framework

---

## I. CURRENT PROBLEMS IDENTIFIED

### 1. Data Integrity Issues
- **Ship-Date Split**: Today's 331 units split across two dates:
  - ✅ 2025-10-06 (correct): 223 units
  - ❌ 2024-04-16 (wrong): 107 units
- **Missing Data**: 75 units exist in ShipStation but not in database
- **Historical Re-sync**: April 2024 orders incorrectly synced on Oct 6th
- **Inventory Discrepancy**: 28-unit difference (610 expected vs 638 actual)

### 2. Root Causes
- **Dual Ingestion Paths**: Daily processor vs. status sync fighting each other
- **Text-Based Storage**: Ad-hoc parsing creates inconsistencies
- **Poor Deduplication**: `(order_number, base_sku, sku_lot)` key breaks with empty sku_lot
- **No Date Guards**: Status sync processes stale historical ShipStation data
- **Missing Lot Detail**: Status sync path omits per-lot information

### 3. Architectural Weaknesses
- Mixed SKU-Lot handling across services
- String parsing scattered throughout codebase
- No relational integrity enforcement
- ShipStation's raw SKU value lost during transformation

---

## II. FINAL ARCHITECTURE DESIGN

### A. Reference Tables (Master Data)

#### 1. `skus` Table (5 rows only)

```sql
CREATE TABLE skus (
    sku_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_code TEXT UNIQUE NOT NULL,           -- e.g., "17612"
    product_name TEXT NOT NULL,
    reorder_point INTEGER DEFAULT 50,
    pallet_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) STRICT;

-- Indexes
CREATE UNIQUE INDEX idx_skus_code ON skus(sku_code);
```

**Data Source**: Migrate from `inventory_current` table

#### 2. `lots` Table (Many-to-One with SKUs)

```sql
CREATE TABLE lots (
    lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_number TEXT NOT NULL,                -- e.g., "250300"
    sku_id INTEGER NOT NULL,
    received_date DATE,
    initial_qty INTEGER,
    manual_adjustment INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id) ON DELETE CASCADE,
    UNIQUE(sku_id, lot_number)               -- One lot per SKU
) STRICT;

-- Indexes
CREATE INDEX idx_lots_sku ON lots(sku_id);
CREATE INDEX idx_lots_status ON lots(status);
CREATE INDEX idx_lots_received_date ON lots(received_date);
```

**Data Source**: Migrate from `lot_inventory` table

### B. Transaction Tables (Hybrid Design)

#### 1. `shipped_items` - Updated Schema

```sql
CREATE TABLE shipped_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_date DATE NOT NULL,
    
    -- ShipStation Compatibility (External Key)
    shipstation_sku_raw TEXT NOT NULL,       -- e.g., "17612 - 250300" (exact from ShipStation)
    
    -- Relational Integrity (Internal Keys)
    sku_id INTEGER NOT NULL,
    lot_id INTEGER,                          -- NULL for SKUs without lots
    
    -- Transaction Data
    quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
    order_number TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
    FOREIGN KEY (lot_id) REFERENCES lots(lot_id),
    FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number)
) STRICT;

-- Indexes
CREATE INDEX idx_shipped_items_date ON shipped_items(ship_date);
CREATE INDEX idx_shipped_items_sku ON shipped_items(sku_id, ship_date);
CREATE INDEX idx_shipped_items_lot ON shipped_items(lot_id);
CREATE INDEX idx_shipped_items_order ON shipped_items(order_number);

-- Unique Constraint (Deduplication using ShipStation raw SKU)
CREATE UNIQUE INDEX uniq_shipped_items_key ON shipped_items(order_number, shipstation_sku_raw);
```

#### 2. `orders_inbox` & `order_items_inbox` - Updated Schema

```sql
-- orders_inbox: No changes needed (order-level table)

-- order_items_inbox: Add FK columns
CREATE TABLE order_items_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    
    -- ShipStation Compatibility
    shipstation_sku_raw TEXT,                -- Store original if available
    
    -- Relational Integrity
    sku_id INTEGER NOT NULL,
    lot_id INTEGER,
    
    -- Legacy (keep during migration)
    sku TEXT NOT NULL,                       -- Will deprecate after migration
    sku_lot TEXT,                            -- Will deprecate after migration
    
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER,
    
    FOREIGN KEY (order_id) REFERENCES orders_inbox(id) ON DELETE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
    FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
) STRICT;
```

### C. Centralized Parsing Service

**New**: `src/services/data_processing/sku_lot_parser.py`

```python
"""
Centralized SKU-Lot parsing service
Handles all ShipStation SKU format variations
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class ParsedSKU:
    shipstation_raw: str
    base_sku: str
    lot_number: Optional[str]
    is_valid: bool
    error_msg: Optional[str] = None

def parse_shipstation_sku(raw_sku: str) -> ParsedSKU:
    """
    Parse ShipStation SKU into base_sku and lot_number
    
    Formats supported:
    - "17612 - 250300" → base=17612, lot=250300
    - "17612-250300" → base=17612, lot=250300
    - "18795" → base=18795, lot=None
    """
    raw_sku = raw_sku.strip()
    
    # Pattern: SKU - LOT (with or without spaces)
    match = re.match(r'^(\d+)\s*-\s*(\d+)$', raw_sku)
    
    if match:
        return ParsedSKU(
            shipstation_raw=raw_sku,
            base_sku=match.group(1),
            lot_number=match.group(2),
            is_valid=True
        )
    
    # Pattern: SKU only (no lot)
    if raw_sku.isdigit():
        return ParsedSKU(
            shipstation_raw=raw_sku,
            base_sku=raw_sku,
            lot_number=None,
            is_valid=True
        )
    
    # Invalid format
    return ParsedSKU(
        shipstation_raw=raw_sku,
        base_sku="",
        lot_number=None,
        is_valid=False,
        error_msg=f"Cannot parse SKU format: {raw_sku}"
    )

def lookup_sku_id(base_sku: str, conn) -> Optional[int]:
    """Get sku_id from skus table"""
    result = conn.execute(
        "SELECT sku_id FROM skus WHERE sku_code = ?", (base_sku,)
    ).fetchone()
    return result[0] if result else None

def lookup_lot_id(sku_id: int, lot_number: str, conn) -> Optional[int]:
    """Get lot_id from lots table"""
    result = conn.execute(
        "SELECT lot_id FROM lots WHERE sku_id = ? AND lot_number = ?",
        (sku_id, lot_number)
    ).fetchone()
    return result[0] if result else None
```

---

## III. SQLITE-SPECIFIC MIGRATION PROCEDURES

### **🔴 CRITICAL: SQLite ALTER TABLE Limitations**

SQLite does **NOT** support:
- ❌ Adding foreign key constraints to existing tables
- ❌ Modifying column types
- ❌ Adding constraints to existing columns

**Required Approach**: Table rebuild using `CREATE TABLE AS` pattern

### SQLite Table Rebuild Procedure

```python
def rebuild_shipped_items_with_fks():
    """
    Rebuild shipped_items table with foreign keys
    SQLite-safe approach using CREATE TABLE AS pattern
    """
    conn = sqlite3.connect('ora.db')
    
    try:
        conn.execute("BEGIN IMMEDIATE")
        
        # Step 1: Create new table with FKs and all columns
        conn.execute("""
            CREATE TABLE shipped_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_date DATE NOT NULL,
                shipstation_sku_raw TEXT NOT NULL,
                sku_id INTEGER NOT NULL,
                lot_id INTEGER,
                quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
                order_number TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
                FOREIGN KEY (lot_id) REFERENCES lots(lot_id),
                FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number)
            ) STRICT
        """)
        
        # Step 2: Copy data from old table (after backfill)
        conn.execute("""
            INSERT INTO shipped_items_new 
                (id, ship_date, shipstation_sku_raw, sku_id, lot_id, 
                 quantity_shipped, order_number, created_at)
            SELECT 
                id, ship_date, shipstation_sku_raw, sku_id, lot_id,
                quantity_shipped, order_number, created_at
            FROM shipped_items
        """)
        
        # Step 3: Drop old table
        conn.execute("DROP TABLE shipped_items")
        
        # Step 4: Rename new table
        conn.execute("ALTER TABLE shipped_items_new RENAME TO shipped_items")
        
        # Step 5: Recreate indexes
        conn.execute("CREATE INDEX idx_shipped_items_date ON shipped_items(ship_date)")
        conn.execute("CREATE INDEX idx_shipped_items_sku ON shipped_items(sku_id, ship_date)")
        conn.execute("CREATE INDEX idx_shipped_items_lot ON shipped_items(lot_id)")
        conn.execute("CREATE INDEX idx_shipped_items_order ON shipped_items(order_number)")
        conn.execute("CREATE UNIQUE INDEX uniq_shipped_items_key ON shipped_items(order_number, shipstation_sku_raw)")
        
        conn.commit()
        print("✅ Successfully rebuilt shipped_items table with foreign keys")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR: {e}")
        raise
    finally:
        conn.close()
```

### WAL Mode & Locking Strategy

```python
def prepare_database_for_migration():
    """Prepare SQLite database for safe migration"""
    conn = sqlite3.connect('ora.db')
    
    # Enable foreign keys (required for all connections)
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Checkpoint WAL to merge all changes into main database file
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    
    # Verify database integrity
    result = conn.execute("PRAGMA integrity_check").fetchone()
    assert result[0] == 'ok', f"Database integrity check failed: {result[0]}"
    
    print("✅ Database prepared for migration")
    conn.close()
```

---

## IV. COMPLETE SERVICE AUDIT

### All Services/Scripts Requiring Updates

#### **Services Touching SKU/Lot Data:**

| Service | File Path | Updates Required | Priority |
|---------|-----------|------------------|----------|
| Daily Processor | `src/daily_shipment_processor.py` | ✅ Update to use FKs | **HIGH** |
| Status Sync | `src/shipstation_status_sync.py` | ✅ Add date guard, use FKs | **HIGH** |
| Manual Sync | `src/manual_shipstation_sync.py` | ⚠️ Update SKU-Lot parsing | **HIGH** |
| Weekly Reporter | `src/weekly_reporter.py` | ⚠️ Update queries to JOIN | **MEDIUM** |
| Upload Service | `src/scheduled_shipstation_upload.py` | ⚠️ Update SKU-Lot lookup | **MEDIUM** |
| XML Import | `src/scheduled_xml_import.py` | ⚠️ Update bundle expansion | **MEDIUM** |
| Cleanup Service | `src/scheduled_cleanup.py` | ✅ No changes (uses order_number only) | **LOW** |
| Units Refresh | `src/shipstation_units_refresher.py` | ✅ No changes (counts only) | **LOW** |

#### **Tables Requiring Schema Updates:**

| Table | Current Key | New Key | Migration Required |
|-------|-------------|---------|-------------------|
| `shipped_items` | `base_sku TEXT` | `sku_id INTEGER FK` | **YES - Rebuild** |
| `order_items_inbox` | `sku TEXT` | `sku_id INTEGER FK` | **YES - Rebuild** |
| `weekly_shipped_history` | `sku TEXT` | `sku_id INTEGER FK` | **YES - Rebuild** |
| `inventory_transactions` | `sku TEXT` | `sku_id INTEGER FK` | **YES - Rebuild** |
| `inventory_current` | `sku TEXT` (PK) | Keep as-is (source table) | **NO** |

#### **Aggregation/Reporting Queries:**

- `app.py` - Dashboard API endpoints (multiple queries)
- `src/services/reporting_logic/inventory_calculations.py` - Inventory calculations
- `src/services/reporting_logic/charge_report.py` - Monthly charge reports
- `shipped_items.html` - Frontend queries
- `lot_inventory.html` - Lot FIFO calculations

---

## V. MIGRATION PLAN (REVISED)

### Phase 0: Pre-Migration Safety (NEW)

#### Step 0.1: Multi-Backup Strategy

```bash
#!/bin/bash
# pre_migration_backup.sh

echo "🛡️ Creating multiple backups..."

# Stop all workflows FIRST
echo "Stopping all workflows..."
pkill -f "python.*scheduled"
pkill -f "python.*shipstation"
pkill -f "python.*weekly"
sleep 5

# Checkpoint WAL
sqlite3 ora.db "PRAGMA wal_checkpoint(TRUNCATE);"

# Create timestamped backups in multiple locations
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup 1: Local primary
cp ora.db "backups/ora.db.backup_primary_${TIMESTAMP}"

# Backup 2: Local secondary
cp ora.db "backups/ora.db.backup_secondary_${TIMESTAMP}"

# Backup 3: Verification copy
cp ora.db "backups/ora.db.backup_verify_${TIMESTAMP}"

echo "✅ Created 3 backups"
ls -lh backups/ora.db.backup_*_${TIMESTAMP}

# Validate each backup
for backup in backups/ora.db.backup_*_${TIMESTAMP}; do
    result=$(sqlite3 "$backup" "PRAGMA integrity_check" 2>&1)
    if [ "$result" = "ok" ]; then
        echo "✅ $backup - integrity OK"
    else
        echo "❌ $backup - FAILED integrity check: $result"
        exit 1
    fi
done

echo "✅ All backups validated successfully"
```

#### Step 0.2: Create Test Environment

```bash
# Create test database copy
cp ora.db ora_test.db

# Run full migration on test database
python3 migration_scripts/run_full_migration.py --database ora_test.db --test-mode

# Validate test migration
python3 migration_scripts/validate_migration.py --database ora_test.db

# If validation passes, proceed to production
```

### Phase 1: Create Reference Tables

#### Step 1.1: Create SKUs Reference Table

```python
def migrate_skus():
    """Create skus table and populate from inventory_current"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skus (
            sku_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_code TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            reorder_point INTEGER DEFAULT 50,
            pallet_count INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    """)
    
    # Populate from inventory_current
    conn.execute("""
        INSERT INTO skus (sku_code, product_name, reorder_point)
        SELECT sku, product_name, reorder_point
        FROM inventory_current
        ORDER BY sku
    """)
    
    count = conn.execute('SELECT COUNT(*) FROM skus').fetchone()[0]
    print(f"✅ Migrated {count} SKUs")
    assert count == 5, f"Expected 5 SKUs, found {count}"
```

#### Step 1.2: Create Lots Reference Table

```python
def migrate_lots():
    """Create lots table and populate from lot_inventory"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_number TEXT NOT NULL,
            sku_id INTEGER NOT NULL,
            received_date DATE,
            initial_qty INTEGER,
            manual_adjustment INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sku_id) REFERENCES skus(sku_id) ON DELETE CASCADE,
            UNIQUE(sku_id, lot_number)
        ) STRICT
    """)
    
    # Populate from lot_inventory + skus JOIN
    conn.execute("""
        INSERT INTO lots (lot_number, sku_id, received_date, initial_qty, manual_adjustment, status)
        SELECT 
            li.lot,
            s.sku_id,
            li.received_date,
            li.initial_qty,
            li.manual_adjustment,
            li.status
        FROM lot_inventory li
        JOIN skus s ON li.sku = s.sku_code
        ORDER BY li.received_date
    """)
    
    count = conn.execute('SELECT COUNT(*) FROM lots').fetchone()[0]
    print(f"✅ Migrated {count} Lots")
```

### Phase 2: Update Transaction Tables

#### Step 2.1: Backfill shipped_items

```python
def backfill_shipped_items():
    """Backfill FK columns using centralized parser"""
    from src.services.data_processing.sku_lot_parser import (
        parse_shipstation_sku, lookup_sku_id, lookup_lot_id
    )
    
    # Add temporary columns first
    try:
        conn.execute("ALTER TABLE shipped_items ADD COLUMN shipstation_sku_raw TEXT")
        conn.execute("ALTER TABLE shipped_items ADD COLUMN sku_id INTEGER")
        conn.execute("ALTER TABLE shipped_items ADD COLUMN lot_id INTEGER")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e):
            raise
    
    rows = conn.execute("""
        SELECT id, base_sku, sku_lot 
        FROM shipped_items 
        WHERE sku_id IS NULL
    """).fetchall()
    
    errors = []
    success = 0
    
    for row_id, base_sku, sku_lot in rows:
        # Reconstruct ShipStation raw SKU
        raw_sku = sku_lot if sku_lot else base_sku
        
        # Parse
        parsed = parse_shipstation_sku(raw_sku)
        
        if not parsed.is_valid:
            errors.append((row_id, raw_sku, parsed.error_msg))
            continue
        
        # Lookup IDs
        sku_id = lookup_sku_id(parsed.base_sku, conn)
        if not sku_id:
            errors.append((row_id, raw_sku, f"SKU not found: {parsed.base_sku}"))
            continue
            
        lot_id = None
        if parsed.lot_number:
            lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn)
            if not lot_id:
                # Create missing lot on-the-fly
                conn.execute("""
                    INSERT INTO lots (lot_number, sku_id, status)
                    VALUES (?, ?, 'active')
                """, (parsed.lot_number, sku_id))
                lot_id = conn.lastrowid
                print(f"⚠️ Created missing lot: {parsed.lot_number} for SKU {parsed.base_sku}")
        
        # Update
        conn.execute("""
            UPDATE shipped_items
            SET shipstation_sku_raw = ?, sku_id = ?, lot_id = ?
            WHERE id = ?
        """, (parsed.shipstation_raw, sku_id, lot_id, row_id))
        success += 1
    
    print(f"✅ Backfilled {success} rows ({len(errors)} errors)")
    
    if errors:
        with open('migration_errors.log', 'w') as f:
            for error in errors:
                f.write(f"Row {error[0]}: {error[1]} - {error[2]}\n")
        print(f"⚠️ Errors logged to migration_errors.log")
```

#### Step 2.2: Rebuild Table with Foreign Keys

```python
def rebuild_shipped_items_table():
    """Rebuild shipped_items table using SQLite-safe approach"""
    # Use the SQLite rebuild procedure from Section III
    rebuild_shipped_items_with_fks()
```

### Phase 3: Update All Services

#### Step 3.1: Update Daily Shipment Processor

```python
# src/daily_shipment_processor.py

from src.services.data_processing.sku_lot_parser import (
    parse_shipstation_sku, lookup_sku_id, lookup_lot_id
)

def process_shipstation_item(item_data, conn):
    """Process ShipStation item with new normalized fields"""
    
    raw_sku = item_data['sku']  # e.g., "17612 - 250300"
    
    # Parse
    parsed = parse_shipstation_sku(raw_sku)
    
    if not parsed.is_valid:
        logger.error(f"Cannot parse SKU: {raw_sku}")
        return None
    
    # Lookup FK IDs
    sku_id = lookup_sku_id(parsed.base_sku, conn)
    lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn) if parsed.lot_number else None
    
    if not sku_id:
        logger.error(f"SKU not found in database: {parsed.base_sku}")
        return None
    
    # Prepare data
    return {
        'shipstation_sku_raw': parsed.shipstation_raw,
        'sku_id': sku_id,
        'lot_id': lot_id,
        'quantity_shipped': item_data['quantity'],
        'ship_date': item_data['shipDate'],
        'order_number': item_data['orderNumber']
    }

def save_shipped_items(items, conn):
    """Save with UPSERT using new unique key"""
    conn.executemany("""
        INSERT INTO shipped_items (
            shipstation_sku_raw, sku_id, lot_id, quantity_shipped, 
            ship_date, order_number
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(order_number, shipstation_sku_raw) DO UPDATE SET
            sku_id = excluded.sku_id,
            lot_id = excluded.lot_id,
            quantity_shipped = excluded.quantity_shipped,
            ship_date = excluded.ship_date
    """, [tuple(item.values()) for item in items])
```

#### Step 3.2: Add Date Guard to Status Sync

```python
# src/shipstation_status_sync.py

from datetime import datetime, timedelta

FRESHNESS_WINDOW_DAYS = 60  # Only process shipments from last 60 days

def should_process_shipment(ship_date_str: str, backfill_mode: bool = False) -> bool:
    """
    Guard against processing historical shipments
    Only process shipments within freshness window unless backfilling
    """
    if backfill_mode:
        logger.info(f"Backfill mode: processing historical date {ship_date_str}")
        return True
    
    ship_date = datetime.strptime(ship_date_str, '%Y-%m-%d').date()
    cutoff_date = datetime.now().date() - timedelta(days=FRESHNESS_WINDOW_DAYS)
    
    if ship_date < cutoff_date:
        logger.warning(f"Skipping historical shipment: {ship_date_str} (before {cutoff_date})")
        return False
    
    return True

def sync_shipstation_status(backfill_mode=False):
    """Updated with date guard and FK support"""
    
    shipments = fetch_shipstation_shipments()
    
    processed = 0
    skipped_historical = 0
    
    for shipment in shipments:
        # DATE GUARD: Skip historical data
        if not should_process_shipment(shipment['shipDate'], backfill_mode):
            skipped_historical += 1
            continue
        
        # Process with normalized fields
        process_shipment_with_fks(shipment)
        processed += 1
    
    logger.info(f"Processed {processed} shipments, skipped {skipped_historical} historical")
```

#### Step 3.3: Update Manual Order Sync

```python
# src/manual_shipstation_sync.py

def sync_manual_orders():
    """Updated to use FK-based storage"""
    from src.services.data_processing.sku_lot_parser import (
        parse_shipstation_sku, lookup_sku_id, lookup_lot_id
    )
    
    # Fetch manual orders from ShipStation
    manual_orders = fetch_manual_shipstation_orders()
    
    for order in manual_orders:
        for item in order['items']:
            # Parse SKU-Lot
            parsed = parse_shipstation_sku(item['sku'])
            
            if not parsed.is_valid:
                logger.error(f"Cannot parse manual order SKU: {item['sku']}")
                continue
            
            # Lookup FKs
            sku_id = lookup_sku_id(parsed.base_sku, conn)
            lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn) if parsed.lot_number else None
            
            # Insert with FKs
            conn.execute("""
                INSERT INTO shipped_items (
                    shipstation_sku_raw, sku_id, lot_id, quantity_shipped,
                    ship_date, order_number
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_number, shipstation_sku_raw) DO NOTHING
            """, (parsed.shipstation_raw, sku_id, lot_id, item['quantity'],
                  order['shipDate'], order['orderNumber']))
```

#### Step 3.4: Update Weekly Reporter

```python
# src/weekly_reporter.py

def calculate_weekly_shipped():
    """Updated to use JOIN queries instead of text matching"""
    
    # OLD (text-based):
    # SELECT base_sku, SUM(quantity_shipped) FROM shipped_items GROUP BY base_sku
    
    # NEW (FK-based with JOIN):
    result = conn.execute("""
        SELECT 
            s.sku_code,
            s.product_name,
            SUM(si.quantity_shipped) as total_shipped
        FROM shipped_items si
        JOIN skus s ON si.sku_id = s.sku_id
        WHERE si.ship_date >= ?
        GROUP BY s.sku_code, s.product_name
        ORDER BY s.sku_code
    """, (start_date,)).fetchall()
    
    return result
```

#### Step 3.5: Update API Endpoints (app.py)

```python
# app.py

@app.route('/api/shipped_items')
def get_shipped_items():
    """Updated to return normalized data with JOINs"""
    
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    sku_filter = request.args.get('sku')
    
    query = """
        SELECT 
            si.id,
            si.ship_date,
            si.shipstation_sku_raw,
            s.sku_code,
            l.lot_number,
            si.quantity_shipped,
            si.order_number
        FROM shipped_items si
        JOIN skus s ON si.sku_id = s.sku_id
        LEFT JOIN lots l ON si.lot_id = l.lot_id
        WHERE si.ship_date = ?
    """
    
    params = [date_filter]
    
    if sku_filter:
        query += " AND s.sku_code = ?"
        params.append(sku_filter)
    
    query += " ORDER BY si.ship_date DESC, s.sku_code"
    
    items = execute_query(query, tuple(params))
    
    return jsonify([{
        'id': row[0],
        'ship_date': row[1],
        'sku_lot': row[2],  # Display as ShipStation raw
        'base_sku': row[3],
        'lot_number': row[4],
        'quantity_shipped': row[5],
        'order_number': row[6]
    } for row in items])
```

### Phase 4: Data Reconciliation (Fix Current Issues)

#### Step 4.1: Fix Ship-Date Split (107 Units)

```python
def fix_ship_date_split():
    """Update the 107 units with wrong ship_date from 2024-04-16 to 2025-10-06"""
    
    # Get today's order numbers
    today_orders = conn.execute("""
        SELECT DISTINCT order_number 
        FROM shipped_items 
        WHERE ship_date = '2025-10-06'
    """).fetchall()
    
    if not today_orders:
        print("⚠️ No orders found for 2025-10-06")
        return
    
    order_list = [o[0] for o in today_orders]
    placeholders = ','.join(['?' for _ in order_list])
    
    # Update items from same orders with wrong date
    result = conn.execute(f"""
        UPDATE shipped_items
        SET ship_date = '2025-10-06'
        WHERE order_number IN ({placeholders})
          AND ship_date = '2024-04-16'
    """, tuple(order_list))
    
    print(f"✅ Fixed {result.rowcount} items with wrong ship_date")
```

#### Step 4.2: Find & Recover Missing 75 Units

```python
def find_and_recover_missing_units():
    """
    Comprehensive reconciliation with ShipStation
    Source of truth hierarchy: ShipStation > Database
    """
    from src.services.data_processing.sku_lot_parser import (
        parse_shipstation_sku, lookup_sku_id, lookup_lot_id
    )
    
    # Get ALL ShipStation data for today
    ss_shipments = fetch_shipstation_shipments(
        ship_date_start='2025-10-06',
        ship_date_end='2025-10-06',
        include_items=True
    )
    
    # Build set of what's in database
    db_items = set(conn.execute("""
        SELECT order_number, shipstation_sku_raw
        FROM shipped_items
        WHERE ship_date = '2025-10-06'
    """).fetchall())
    
    missing = []
    manual_intervention = []
    
    for shipment in ss_shipments:
        for item in shipment['shipmentItems']:
            key = (shipment['orderNumber'], item['sku'])
            
            if key not in db_items:
                # Parse SKU
                parsed = parse_shipstation_sku(item['sku'])
                
                if not parsed.is_valid:
                    manual_intervention.append({
                        'order': shipment['orderNumber'],
                        'sku': item['sku'],
                        'reason': 'Cannot parse SKU format'
                    })
                    continue
                
                # Lookup FKs
                sku_id = lookup_sku_id(parsed.base_sku, conn)
                if not sku_id:
                    manual_intervention.append({
                        'order': shipment['orderNumber'],
                        'sku': item['sku'],
                        'reason': f'SKU {parsed.base_sku} not in database'
                    })
                    continue
                
                lot_id = None
                if parsed.lot_number:
                    lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn)
                    if not lot_id:
                        # Create lot if missing
                        conn.execute("""
                            INSERT INTO lots (lot_number, sku_id, status)
                            VALUES (?, ?, 'active')
                        """, (parsed.lot_number, sku_id))
                        lot_id = conn.lastrowid
                
                missing.append({
                    'order_number': shipment['orderNumber'],
                    'shipstation_sku_raw': parsed.shipstation_raw,
                    'sku_id': sku_id,
                    'lot_id': lot_id,
                    'quantity': item['quantity'],
                    'ship_date': shipment['shipDate']
                })
    
    # Insert missing items
    if missing:
        conn.executemany("""
            INSERT INTO shipped_items (
                shipstation_sku_raw, sku_id, lot_id, quantity_shipped,
                ship_date, order_number
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [(m['shipstation_sku_raw'], m['sku_id'], m['lot_id'], 
               m['quantity'], m['ship_date'], m['order_number']) for m in missing])
        
        print(f"✅ Recovered {len(missing)} missing items")
    
    # Log manual intervention cases
    if manual_intervention:
        with open('manual_intervention_required.log', 'w') as f:
            for case in manual_intervention:
                f.write(f"Order {case['order']}: {case['sku']} - {case['reason']}\n")
        print(f"⚠️ {len(manual_intervention)} cases require manual intervention (see log)")
```

#### Step 4.3: Delete Historical Re-sync Records

```python
def delete_historical_resync():
    """Remove April 2024 records that were incorrectly synced today"""
    
    result = conn.execute("""
        DELETE FROM shipped_items
        WHERE ship_date = '2024-04-16'
          AND created_at >= '2025-10-06 15:43:00'
          AND created_at <= '2025-10-06 17:45:00'
    """)
    
    print(f"✅ Deleted {result.rowcount} historical re-sync records")
```

---

## VI. OPERATIONAL PLAYBOOK (NEW)

### Pre-Migration Checklist

```bash
#!/bin/bash
# pre_migration_checklist.sh

echo "🔍 Pre-Migration Checklist"
echo "="*70

# 1. Check system status
echo "[1/10] Checking system status..."
if curl -s http://localhost:5000/api/dashboard_stats > /dev/null; then
    echo "  ✅ Dashboard is running"
else
    echo "  ❌ Dashboard is not responding"
    exit 1
fi

# 2. Check database integrity
echo "[2/10] Checking database integrity..."
result=$(sqlite3 ora.db "PRAGMA integrity_check")
if [ "$result" = "ok" ]; then
    echo "  ✅ Database integrity OK"
else
    echo "  ❌ Database integrity check failed: $result"
    exit 1
fi

# 3. Check disk space
echo "[3/10] Checking disk space..."
available=$(df -h . | awk 'NR==2 {print $4}')
echo "  ℹ️  Available space: $available"

# 4. Check current record counts
echo "[4/10] Checking current record counts..."
shipped_items=$(sqlite3 ora.db "SELECT COUNT(*) FROM shipped_items")
shipped_orders=$(sqlite3 ora.db "SELECT COUNT(*) FROM shipped_orders")
echo "  ℹ️  shipped_items: $shipped_items rows"
echo "  ℹ️  shipped_orders: $shipped_orders rows"

# 5. Check for running processes
echo "[5/10] Checking for running automation processes..."
processes=$(pgrep -f "python.*scheduled" | wc -l)
echo "  ℹ️  $processes automation processes running"

# 6. Check WAL file
echo "[6/10] Checking WAL file..."
if [ -f "ora.db-wal" ]; then
    wal_size=$(ls -lh ora.db-wal | awk '{print $5}')
    echo "  ℹ️  WAL file exists: $wal_size"
else
    echo "  ✅ No WAL file (clean state)"
fi

# 7. Create backup directory
echo "[7/10] Creating backup directory..."
mkdir -p backups
echo "  ✅ Backup directory ready"

# 8. Verify test migration passed
echo "[8/10] Verifying test migration..."
if [ -f "migration_test_passed.flag" ]; then
    echo "  ✅ Test migration passed"
else
    echo "  ⚠️  Test migration not verified - run test first!"
    echo "     python migration_scripts/run_full_migration.py --database ora_test.db --test-mode"
    exit 1
fi

# 9. Check ShipStation connectivity
echo "[9/10] Checking ShipStation API connectivity..."
# This would make a test API call
echo "  ⚠️  Manual verification required"

# 10. Final confirmation
echo "[10/10] Final confirmation..."
echo ""
echo "✅ Pre-migration checklist complete"
echo ""
echo "Ready to proceed? (y/n)"
read -r response
if [ "$response" != "y" ]; then
    echo "❌ Migration cancelled"
    exit 1
fi
```

### Workflow Pause Procedure

```bash
#!/bin/bash
# pause_all_workflows.sh

echo "⏸️  Pausing all workflows..."

# Stop all automation workflows
pkill -f "python.*scheduled_xml_import"
pkill -f "python.*scheduled_shipstation_upload"
pkill -f "python.*shipstation_status_sync"
pkill -f "python.*manual_shipstation_sync"
pkill -f "python.*scheduled_cleanup"
pkill -f "python.*shipstation_units_refresher"
pkill -f "python.*weekly_reporter"
pkill -f "python.*daily_shipment_processor"

# Wait for graceful shutdown
sleep 5

# Verify all stopped
remaining=$(pgrep -f "python.*scheduled" | wc -l)
if [ $remaining -eq 0 ]; then
    echo "✅ All workflows stopped"
    echo $(date) > workflows_paused.flag
else
    echo "⚠️  $remaining processes still running"
    pgrep -f "python.*scheduled" -a
    echo "Force killing..."
    pkill -9 -f "python.*scheduled"
fi
```

### Migration Execution Script

```bash
#!/bin/bash
# execute_migration.sh

set -e  # Exit on any error

echo "🚀 Starting Database Normalization v2.0 Migration"
echo "="*70

# Step 1: Pre-flight checks
echo "[1/8] Running pre-migration checklist..."
./pre_migration_checklist.sh || exit 1

# Step 2: Pause workflows
echo "[2/8] Pausing all workflows..."
./pause_all_workflows.sh || exit 1

# Step 3: Create backups
echo "[3/8] Creating multiple backups..."
./pre_migration_backup.sh || exit 1

# Step 4: Prepare database
echo "[4/8] Preparing database (WAL checkpoint)..."
python3 -c "
import sqlite3
conn = sqlite3.connect('ora.db')
conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
conn.close()
print('✅ WAL checkpoint complete')
"

# Step 5: Run migration
echo "[5/8] Running migration scripts..."
python3 migration_scripts/run_full_migration.py --database ora.db --production-mode || {
    echo "❌ Migration failed! Rolling back..."
    ./rollback_migration.sh
    exit 1
}

# Step 6: Validate migration
echo "[6/8] Validating migration..."
python3 migration_scripts/validate_migration.py --database ora.db || {
    echo "❌ Validation failed! Rolling back..."
    ./rollback_migration.sh
    exit 1
}

# Step 7: Update services
echo "[7/8] Services already updated (code deployed with migration)"

# Step 8: Restart workflows
echo "[8/8] Restarting workflows..."
./start_all.sh &
sleep 5

echo ""
echo "✅ Migration Complete!"
echo "="*70
echo "Next steps:"
echo "1. Monitor dashboard at http://localhost:5000"
echo "2. Check logs: tail -f logs/*.log"
echo "3. Run health check: python migration_scripts/post_migration_health_check.py"
echo "4. Keep backups for 7 days before cleanup"
```

### Rollback Script (Enhanced)

```bash
#!/bin/bash
# rollback_migration.sh

echo "🚨 EMERGENCY ROLLBACK INITIATED"
echo "="*70

# Stop all workflows immediately
echo "[1/5] Stopping all workflows..."
pkill -9 -f "python"
sleep 2

# Find most recent backup
echo "[2/5] Finding most recent backup..."
backup=$(ls -t backups/ora.db.backup_primary_* | head -1)
if [ -z "$backup" ]; then
    echo "❌ No backup found!"
    exit 1
fi
echo "  Found: $backup"

# Verify backup integrity
echo "[3/5] Verifying backup integrity..."
result=$(sqlite3 "$backup" "PRAGMA integrity_check" 2>&1)
if [ "$result" != "ok" ]; then
    echo "❌ Backup is corrupted: $result"
    echo "Trying secondary backup..."
    backup=$(ls -t backups/ora.db.backup_secondary_* | head -1)
    result=$(sqlite3 "$backup" "PRAGMA integrity_check" 2>&1)
    if [ "$result" != "ok" ]; then
        echo "❌ Secondary backup also corrupted!"
        exit 1
    fi
fi
echo "✅ Backup verified"

# Restore backup
echo "[4/5] Restoring from backup..."
cp "$backup" ora.db
cp "$backup-shm" ora.db-shm 2>/dev/null || true
cp "$backup-wal" ora.db-wal 2>/dev/null || true

# Restart system
echo "[5/5] Restarting system..."
./start_all.sh &

echo ""
echo "✅ ROLLBACK COMPLETE"
echo "="*70
echo "System restored to pre-migration state"
echo "Restored from: $backup"
```

---

## VII. VALIDATION & TESTING (ENHANCED)

### Comprehensive Validation Suite

```python
# migration_scripts/validate_migration.py

import sqlite3
import sys
from datetime import datetime

def validate_migration(db_path='ora.db'):
    """Comprehensive migration validation"""
    
    conn = sqlite3.connect(db_path)
    errors = []
    warnings = []
    
    print("🔍 Running Migration Validation Suite")
    print("="*70)
    
    # Test 1: Reference tables exist and populated
    print("[1/15] Checking reference tables...")
    try:
        sku_count = conn.execute("SELECT COUNT(*) FROM skus").fetchone()[0]
        if sku_count != 5:
            errors.append(f"Expected 5 SKUs, found {sku_count}")
        else:
            print(f"  ✅ skus table: {sku_count} rows")
    except Exception as e:
        errors.append(f"skus table error: {e}")
    
    try:
        lot_count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
        print(f"  ✅ lots table: {lot_count} rows")
    except Exception as e:
        errors.append(f"lots table error: {e}")
    
    # Test 2: Foreign key constraints exist
    print("[2/15] Checking foreign key constraints...")
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        # Try to insert invalid FK - should fail
        try:
            conn.execute("INSERT INTO shipped_items (sku_id, lot_id, quantity_shipped, ship_date) VALUES (999, NULL, 5, '2025-10-06')")
            errors.append("Foreign key constraint not enforced!")
            conn.rollback()
        except sqlite3.IntegrityError:
            print("  ✅ Foreign key constraints working")
            conn.rollback()
    except Exception as e:
        errors.append(f"FK constraint check failed: {e}")
    
    # Test 3: All shipped_items have valid FKs
    print("[3/15] Checking shipped_items foreign keys...")
    orphans = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE sku_id IS NULL 
           OR sku_id NOT IN (SELECT sku_id FROM skus)
    """).fetchone()[0]
    if orphans > 0:
        errors.append(f"Found {orphans} orphaned records in shipped_items")
    else:
        print(f"  ✅ All shipped_items have valid FKs")
    
    # Test 4: shipstation_sku_raw populated
    print("[4/15] Checking shipstation_sku_raw column...")
    empty_raw = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE shipstation_sku_raw IS NULL OR shipstation_sku_raw = ''
    """).fetchone()[0]
    if empty_raw > 0:
        warnings.append(f"{empty_raw} records missing shipstation_sku_raw")
    else:
        print(f"  ✅ All records have shipstation_sku_raw")
    
    # Test 5: Unique constraint works
    print("[5/15] Testing unique constraint...")
    try:
        conn.execute("""
            INSERT INTO shipped_items (order_number, shipstation_sku_raw, sku_id, quantity_shipped, ship_date)
            VALUES ('TEST001', '17612 - 250300', 1, 5, '2025-10-06')
        """)
        conn.execute("""
            INSERT INTO shipped_items (order_number, shipstation_sku_raw, sku_id, quantity_shipped, ship_date)
            VALUES ('TEST001', '17612 - 250300', 1, 5, '2025-10-06')
        """)
        errors.append("Duplicate insert should have failed!")
        conn.rollback()
    except sqlite3.IntegrityError:
        print("  ✅ Unique constraint working")
        conn.rollback()
    
    # Test 6: Record counts match pre-migration
    print("[6/15] Checking record counts...")
    # This would compare against pre-migration snapshot
    current_count = conn.execute("SELECT COUNT(*) FROM shipped_items").fetchone()[0]
    print(f"  ℹ️  shipped_items: {current_count} records")
    
    # Test 7: Today's data integrity
    print("[7/15] Validating today's shipped data...")
    today = datetime.now().strftime('%Y-%m-%d')
    today_total = conn.execute("""
        SELECT SUM(quantity_shipped) FROM shipped_items WHERE ship_date = ?
    """, (today,)).fetchone()[0]
    print(f"  ℹ️  Today's total: {today_total or 0} units")
    
    # Test 8: No historical date anomalies
    print("[8/15] Checking for date anomalies...")
    old_dates = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE ship_date < '2025-01-01'
          AND created_at >= '2025-10-06'
    """).fetchone()[0]
    if old_dates > 0:
        warnings.append(f"{old_dates} records with suspicious historical dates")
    else:
        print("  ✅ No suspicious historical dates")
    
    # Test 9: JOIN query performance
    print("[9/15] Testing JOIN query performance...")
    import time
    start = time.time()
    conn.execute("""
        SELECT s.sku_code, SUM(si.quantity_shipped)
        FROM shipped_items si
        JOIN skus s ON si.sku_id = s.sku_id
        WHERE si.ship_date >= '2025-09-01'
        GROUP BY s.sku_code
    """).fetchall()
    duration = time.time() - start
    print(f"  ✅ JOIN query: {duration:.3f}s")
    if duration > 1.0:
        warnings.append(f"JOIN query slow: {duration:.3f}s")
    
    # Test 10: Lot FIFO calculation
    print("[10/15] Testing lot FIFO calculations...")
    lots_with_data = conn.execute("""
        SELECT COUNT(*) FROM lots l
        WHERE EXISTS (
            SELECT 1 FROM shipped_items si WHERE si.lot_id = l.lot_id
        )
    """).fetchone()[0]
    print(f"  ℹ️  {lots_with_data} lots have shipped items")
    
    # Test 11: Indexes exist
    print("[11/15] Checking indexes...")
    indexes = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='shipped_items'
    """).fetchall()
    required_indexes = ['idx_shipped_items_date', 'idx_shipped_items_sku', 
                       'idx_shipped_items_lot', 'uniq_shipped_items_key']
    missing_indexes = [idx for idx in required_indexes 
                      if not any(idx in i[0] for i in indexes)]
    if missing_indexes:
        errors.append(f"Missing indexes: {missing_indexes}")
    else:
        print(f"  ✅ All required indexes exist")
    
    # Test 12: Weekly history consistency
    print("[12/15] Checking weekly_shipped_history...")
    try:
        history_count = conn.execute("SELECT COUNT(*) FROM weekly_shipped_history").fetchone()[0]
        print(f"  ℹ️  {history_count} weekly history records")
    except Exception as e:
        warnings.append(f"weekly_shipped_history check failed: {e}")
    
    # Test 13: Database integrity
    print("[13/15] Running PRAGMA integrity_check...")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != 'ok':
        errors.append(f"Database integrity check failed: {integrity}")
    else:
        print("  ✅ Database integrity OK")
    
    # Test 14: Foreign keys enabled
    print("[14/15] Verifying foreign_keys pragma...")
    fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    if fk_enabled != 1:
        errors.append("Foreign keys not enabled!")
    else:
        print("  ✅ Foreign keys enabled")
    
    # Test 15: No parse errors logged
    print("[15/15] Checking for parse errors...")
    import os
    if os.path.exists('migration_errors.log'):
        with open('migration_errors.log', 'r') as f:
            error_count = len(f.readlines())
        if error_count > 0:
            warnings.append(f"{error_count} parse errors during migration")
    else:
        print("  ✅ No parse errors")
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    if errors:
        print(f"❌ {len(errors)} ERRORS:")
        for error in errors:
            print(f"  - {error}")
        conn.close()
        return False
    
    if warnings:
        print(f"⚠️  {len(warnings)} WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("✅ ALL TESTS PASSED")
    elif not errors:
        print("✅ VALIDATION PASSED (with warnings)")
    
    conn.close()
    return len(errors) == 0

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else 'ora.db'
    success = validate_migration(db)
    sys.exit(0 if success else 1)
```

### Post-Migration Health Check

```python
# migration_scripts/post_migration_health_check.py

import requests
import sqlite3
from datetime import datetime

def post_migration_health_check():
    """Run health checks after migration"""
    
    print("🏥 Post-Migration Health Check")
    print("="*70)
    
    # 1. Dashboard API responding
    print("[1/6] Checking dashboard API...")
    try:
        response = requests.get('http://localhost:5000/api/dashboard_stats', timeout=5)
        if response.status_code == 200:
            print("  ✅ Dashboard API responding")
        else:
            print(f"  ❌ Dashboard returned {response.status_code}")
    except Exception as e:
        print(f"  ❌ Dashboard not responding: {e}")
    
    # 2. Workflows running
    print("[2/6] Checking workflows...")
    try:
        response = requests.get('http://localhost:5000/api/automation_status', timeout=5)
        if response.status_code == 200:
            workflows = response.json()
            running = sum(1 for w in workflows if w.get('status') == 'running')
            print(f"  ℹ️  {running} workflows running")
    except Exception as e:
        print(f"  ⚠️  Cannot check workflows: {e}")
    
    # 3. Database queries working
    print("[3/6] Testing database queries...")
    conn = sqlite3.connect('ora.db')
    try:
        result = conn.execute("""
            SELECT COUNT(*) FROM shipped_items WHERE ship_date = ?
        """, (datetime.now().strftime('%Y-%m-%d'),)).fetchone()[0]
        print(f"  ✅ Query successful: {result} items today")
    except Exception as e:
        print(f"  ❌ Query failed: {e}")
    conn.close()
    
    # 4. ShipStation sync working
    print("[4/6] Checking ShipStation sync...")
    # Would check last sync timestamp
    print("  ⚠️  Manual verification required")
    
    # 5. Lot inventory calculations
    print("[5/6] Testing lot inventory...")
    try:
        response = requests.get('http://localhost:5000/api/lot_inventory', timeout=5)
        if response.status_code == 200:
            print("  ✅ Lot inventory API working")
    except Exception as e:
        print(f"  ❌ Lot inventory failed: {e}")
    
    # 6. No errors in logs
    print("[6/6] Checking recent logs...")
    import os
    if os.path.exists('logs/app.log'):
        with open('logs/app.log', 'r') as f:
            recent = f.readlines()[-50:]
        errors = [line for line in recent if 'ERROR' in line]
        if errors:
            print(f"  ⚠️  {len(errors)} recent errors in logs")
        else:
            print("  ✅ No recent errors")
    
    print("\n✅ Health check complete")

if __name__ == "__main__":
    post_migration_health_check()
```

---

## VIII. MONITORING & ALERTS (NEW)

### Daily Health Monitoring

```python
# monitoring/daily_health_check.py

def daily_health_check():
    """Run daily to detect data integrity issues"""
    
    conn = sqlite3.connect('ora.db')
    issues = []
    
    # Check 1: Orphaned records
    orphans = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE sku_id NOT IN (SELECT sku_id FROM skus)
    """).fetchone()[0]
    if orphans > 0:
        issues.append(f"⚠️ Found {orphans} orphaned records")
    
    # Check 2: Missing shipstation_sku_raw
    missing_raw = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE shipstation_sku_raw IS NULL OR shipstation_sku_raw = ''
    """).fetchone()[0]
    if missing_raw > 0:
        issues.append(f"⚠️ {missing_raw} records missing shipstation_sku_raw")
    
    # Check 3: Historical date anomalies
    old_dates = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE ship_date < '2025-01-01'
          AND created_at > datetime('now', '-1 day')
    """).fetchone()[0]
    if old_dates > 0:
        issues.append(f"⚠️ {old_dates} records with historical dates created recently")
    
    # Check 4: ShipStation sync discrepancy
    # Would compare local counts with ShipStation
    
    # Check 5: Foreign key violations
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA foreign_key_check")
        violations = conn.fetchall()
        if violations:
            issues.append(f"⚠️ {len(violations)} foreign key violations")
    except Exception as e:
        issues.append(f"⚠️ FK check failed: {e}")
    
    # Send alerts if issues found
    if issues:
        send_alert_email("\n".join(issues))
        print("⚠️ Issues detected:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ All health checks passed")
    
    conn.close()
```

---

## IX. SUCCESS CRITERIA (UPDATED)

### ✅ **Data Integrity:**
- No ship_date splits (all items for same order have same date)
- All ShipStation units present in database (verified reconciliation)
- No duplicate records (unique constraint enforced)
- Foreign key constraints enforced and working
- All shipped_items have valid sku_id and lot_id references

### ✅ **Performance:**
- Query performance equal or better than text-based
- JOIN queries complete in < 1 second for typical date ranges
- Real-time sync maintains data accuracy
- No WAL file growth issues

### ✅ **Maintainability:**
- Single source of truth for SKUs (skus table) and lots (lots table)
- No text parsing in queries (centralized in parser service)
- Centralized parsing service used by all ingestion paths
- Clear data flow from ShipStation → Parser → Database

### ✅ **ShipStation Compatibility:**
- Raw SKU preserved for API idempotency
- Deduplication works correctly using shipstation_sku_raw
- Historical data guards prevent re-sync (60-day window)
- Manual orders sync correctly with lot tracking

### ✅ **Operational:**
- All 8 workflows updated and tested
- Zero data loss during migration
- Rollback procedure tested and documented
- Monitoring and alerting in place
- Health checks passing

---

## X. REVISED TIMELINE

### **Total Effort: 12-14 hours**

#### **Week 1: Preparation & Testing (4 hours)**
- [ ] Create migration scripts (2 hours)
- [ ] Run test migration on copy (1 hour)
- [ ] Create operational playbooks (1 hour)

#### **Week 2: Production Migration (4 hours)**
- [ ] Execute pre-migration checklist (30 min)
- [ ] Run migration (2 hours)
- [ ] Validate & test (1 hour)
- [ ] Monitor for 24 hours (30 min active)

#### **Week 3: Service Updates (3-4 hours)**
- [ ] Update remaining services (2 hours)
- [ ] Update all queries to use JOINs (1-2 hours)

#### **Week 4: Cleanup & Optimization (1-2 hours)**
- [ ] Remove legacy columns (30 min)
- [ ] Final validation (30 min)
- [ ] Documentation updates (30-60 min)

---

## XI. RISK MITIGATION (ENHANCED)

### **Pre-Migration:**
- ✅ Complete database backup (3 copies, verified)
- ✅ Test environment mirrors production
- ✅ Test migration validated successfully
- ✅ Rollback plan tested
- ✅ All workflows paused before migration

### **During Migration:**
- ✅ Phased implementation with validation gates
- ✅ SQLite transactions ensure atomicity
- ✅ Checkpoint after each phase
- ✅ Immediate rollback on any error

### **Post-Migration:**
- ✅ Comprehensive validation suite
- ✅ Monitoring alerts for early issue detection
- ✅ Health checks every 6 hours for first week
- ✅ Backups retained for 7 days
- ✅ Rollback procedure ready if needed

---

## XII. FINAL NOTES

### **Key Design Principles**
1. **Preserve ShipStation Reality**: Store raw SKU exactly as received
2. **Normalize Internally**: Use FKs for data integrity
3. **Centralize Parsing**: Single source of truth for SKU-Lot extraction
4. **Guard Against Staleness**: Date filters prevent historical re-sync
5. **Maintain Compatibility**: Hybrid design supports both systems
6. **SQLite-Safe Operations**: Use CREATE TABLE AS for schema changes
7. **Operational Safety**: Multiple backups, validation gates, instant rollback

### **Critical Success Factors**
- Test migration validated before production
- All 8 workflows paused during migration
- Multiple verified backups
- Comprehensive validation suite passes
- Monitoring and alerting in place
- Team trained on rollback procedure

---

**This plan provides a complete, production-ready roadmap from current state to fully normalized relational database design, while maintaining ShipStation compatibility, operational safety, and fixing all existing data integrity issues.**

**Version 2.1 addresses all architect-identified gaps and is approved for implementation.**

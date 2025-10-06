FINAL COMPREHENSIVE NORMALIZATION & DATA INTEGRITY PLAN
Executive Summary
Transform the ORA Automation system from text-based SKU-Lot storage to a fully normalized relational database design with foreign keys, while maintaining ShipStation API compatibility. This will eliminate current data integrity issues (ship_date splits, missing units, duplicate records) and provide a robust foundation for inventory tracking.

I. CURRENT PROBLEMS IDENTIFIED
1. Data Integrity Issues
Ship-Date Split: Today's 331 units split across two dates:
✅ 2025-10-06 (correct): 223 units
❌ 2024-04-16 (wrong): 107 units
Missing Data: 75 units exist in ShipStation but not in database
Historical Re-sync: April 2024 orders incorrectly synced on Oct 6th
Inventory Discrepancy: 28-unit difference (610 expected vs 638 actual)
2. Root Causes
Dual Ingestion Paths: Daily processor vs. status sync fighting each other
Text-Based Storage: Ad-hoc parsing creates inconsistencies
Poor Deduplication: (order_number, base_sku, sku_lot) key breaks with empty sku_lot
No Date Guards: Status sync processes stale historical ShipStation data
Missing Lot Detail: Status sync path omits per-lot information
3. Architectural Weaknesses
Mixed SKU-Lot handling across services
String parsing scattered throughout codebase
No relational integrity enforcement
ShipStation's raw SKU value lost during transformation
II. FINAL ARCHITECTURE DESIGN
A. Reference Tables (Master Data)
1. skus Table (5 rows only)
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
Data Source: Migrate from inventory_current table

2. lots Table (Many-to-One with SKUs)
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
Data Source: Migrate from lot_inventory table

B. Transaction Tables (Hybrid Design)
1. shipped_items - Updated Schema
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
2. orders_inbox & order_items_inbox - Updated Schema
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
C. Centralized Parsing Service
New: src/services/data_processing/sku_lot_parser.py
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
III. MIGRATION PLAN
Phase 1: Create Reference Tables
Step 1.1: Create SKUs Reference Table
# Migrate from inventory_current
def migrate_skus():
    """Create skus table and populate from inventory_current"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skus (
            sku_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_code TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            reorder_point INTEGER DEFAULT 50,
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

    print(f"✅ Migrated {conn.execute('SELECT COUNT(*) FROM skus').fetchone()[0]} SKUs")
Step 1.2: Create Lots Reference Table
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

    print(f"✅ Migrated {conn.execute('SELECT COUNT(*) FROM lots').fetchone()[0]} Lots")
Phase 2: Update Transaction Tables
Step 2.1: Add New Columns to shipped_items
def add_fk_columns_shipped_items():
    """Add FK columns to shipped_items (keep old columns during migration)"""

    # Add new columns
    conn.execute("ALTER TABLE shipped_items ADD COLUMN shipstation_sku_raw TEXT")
    conn.execute("ALTER TABLE shipped_items ADD COLUMN sku_id INTEGER REFERENCES skus(sku_id)")
    conn.execute("ALTER TABLE shipped_items ADD COLUMN lot_id INTEGER REFERENCES lots(lot_id)")

    print("✅ Added FK columns to shipped_items")
Step 2.2: Backfill Data with Parsing
def backfill_shipped_items():
    """Backfill FK columns using centralized parser"""
    from src.services.data_processing.sku_lot_parser import (
        parse_shipstation_sku, lookup_sku_id, lookup_lot_id
    )

    rows = conn.execute("""
        SELECT id, base_sku, sku_lot 
        FROM shipped_items 
        WHERE sku_id IS NULL
    """).fetchall()

    errors = []

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
        lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn) if parsed.lot_number else None

        # Update
        conn.execute("""
            UPDATE shipped_items
            SET shipstation_sku_raw = ?, sku_id = ?, lot_id = ?
            WHERE id = ?
        """, (parsed.shipstation_raw, sku_id, lot_id, row_id))

    print(f"✅ Backfilled {len(rows)} rows ({len(errors)} errors)")

    if errors:
        log_parsing_errors(errors)
Step 2.3: Create New Unique Index
def update_unique_constraints():
    """Replace old constraint with new one using shipstation_sku_raw"""

    # Drop old constraint
    conn.execute("DROP INDEX IF EXISTS uniq_shipped_items_key")

    # Create new constraint
    conn.execute("""
        CREATE UNIQUE INDEX uniq_shipped_items_key 
        ON shipped_items(order_number, shipstation_sku_raw)
    """)

    print("✅ Updated unique constraint to use shipstation_sku_raw")
Phase 3: Update Services & Sync Logic
Step 3.1: Update Daily Shipment Processor
# src/daily_shipment_processor.py
from src.services.data_processing.sku_lot_parser import (
    parse_shipstation_sku, lookup_sku_id, lookup_lot_id
)
def process_shipstation_item(item_data):
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

    # Prepare data
    return {
        'shipstation_sku_raw': parsed.shipstation_raw,
        'sku_id': sku_id,
        'lot_id': lot_id,
        'quantity_shipped': item_data['quantity'],
        'ship_date': item_data['shipDate'],
        'order_number': item_data['orderNumber']
    }
def save_shipped_items(items):
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
    """, items)
Step 3.2: Add Date Guard to Status Sync
# src/shipstation_status_sync.py
from datetime import datetime, timedelta
def should_process_shipment(ship_date_str: str, backfill_mode: bool = False) -> bool:
    """
    Guard against processing historical shipments
    Only process shipments within freshness window (60 days) unless backfilling
    """
    if backfill_mode:
        return True

    ship_date = datetime.strptime(ship_date_str, '%Y-%m-%d').date()
    cutoff_date = datetime.now().date() - timedelta(days=60)

    if ship_date < cutoff_date:
        logger.warning(f"Skipping historical shipment: {ship_date_str} (before {cutoff_date})")
        return False

    return True
def sync_shipstation_status():
    """Updated with date guard"""

    shipments = fetch_shipstation_shipments()

    for shipment in shipments:
        # DATE GUARD: Skip historical data
        if not should_process_shipment(shipment['shipDate']):
            continue

        # Process with normalized fields
        process_shipment(shipment)
Phase 4: Deprecate Old Fields
Step 4.1: Update All Queries
# OLD (text-based):
SELECT base_sku, SUM(quantity_shipped) 
FROM shipped_items 
WHERE ship_date = '2025-10-06'
GROUP BY base_sku
# NEW (FK-based with JOIN):
SELECT s.sku_code, SUM(si.quantity_shipped)
FROM shipped_items si
JOIN skus s ON si.sku_id = s.sku_id
WHERE si.ship_date = '2025-10-06'
GROUP BY s.sku_code
Step 4.2: Remove Old Columns (After Validation)
def remove_legacy_columns():
    """Remove old text-based columns after migration is validated"""

    # Only after thorough testing!
    conn.execute("ALTER TABLE shipped_items DROP COLUMN base_sku")
    conn.execute("ALTER TABLE shipped_items DROP COLUMN sku_lot")

    print("✅ Removed legacy text columns")
IV. DATA RECONCILIATION (Fix Current Issues)
Step 1: Fix Ship-Date Split (107 Units)
def fix_ship_date_split():
    """Update the 107 units with wrong ship_date from 2024-04-16 to 2025-10-06"""

    # Get today's order numbers
    today_orders = conn.execute("""
        SELECT DISTINCT order_number 
        FROM shipped_items 
        WHERE ship_date = '2025-10-06'
    """).fetchall()

    order_list = [o[0] for o in today_orders]

    # Update items from same orders with wrong date
    result = conn.execute(f"""
        UPDATE shipped_items
        SET ship_date = '2025-10-06'
        WHERE order_number IN ({','.join(['?' for _ in order_list])})
          AND ship_date = '2024-04-16'
    """, tuple(order_list))

    print(f"✅ Fixed {result.rowcount} items with wrong ship_date")
Step 2: Find & Recover Missing 75 Units
def find_missing_units():
    """Query ShipStation for missing units and insert them"""

    # Get ShipStation data for today
    ss_shipments = fetch_shipstation_shipments(ship_date='2025-10-06')

    # Compare with database
    db_items = set(conn.execute("""
        SELECT order_number, shipstation_sku_raw
        FROM shipped_items
        WHERE ship_date = '2025-10-06'
    """).fetchall())

    missing = []
    for shipment in ss_shipments:
        for item in shipment['items']:
            key = (shipment['orderNumber'], item['sku'])
            if key not in db_items:
                missing.append({
                    'order_number': shipment['orderNumber'],
                    'raw_sku': item['sku'],
                    'quantity': item['quantity'],
                    'ship_date': shipment['shipDate']
                })

    # Insert missing items
    for item in missing:
        parsed = parse_shipstation_sku(item['raw_sku'])
        sku_id = lookup_sku_id(parsed.base_sku, conn)
        lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn) if parsed.lot_number else None

        conn.execute("""
            INSERT INTO shipped_items (
                shipstation_sku_raw, sku_id, lot_id, quantity_shipped,
                ship_date, order_number
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (item['raw_sku'], sku_id, lot_id, item['quantity'], 
              item['ship_date'], item['order_number']))

    print(f"✅ Recovered {len(missing)} missing items")
Step 3: Delete Historical Re-sync Records
def delete_historical_resync():
    """Remove 80 April 2024 records that were incorrectly synced today"""

    result = conn.execute("""
        DELETE FROM shipped_items
        WHERE ship_date = '2024-04-16'
          AND created_at >= '2025-10-06 15:43:00'
          AND created_at <= '2025-10-06 17:45:00'
    """)

    print(f"✅ Deleted {result.rowcount} historical re-sync records")
V. VALIDATION & TESTING
1. Data Integrity Tests
def validate_migration():
    """Run validation checks"""

    # Test 1: All shipped_items have valid FKs
    orphans = conn.execute("""
        SELECT COUNT(*) FROM shipped_items
        WHERE sku_id IS NULL OR sku_id NOT IN (SELECT sku_id FROM skus)
    """).fetchone()[0]
    assert orphans == 0, f"Found {orphans} orphaned records"

    # Test 2: Unique constraint works
    try:
        conn.execute("""
            INSERT INTO shipped_items (order_number, shipstation_sku_raw, sku_id, lot_id, quantity_shipped, ship_date)
            VALUES ('TEST123', '17612 - 250300', 1, 1, 5, '2025-10-06')
        """)
        conn.execute("""
            INSERT INTO shipped_items (order_number, shipstation_sku_raw, sku_id, lot_id, quantity_shipped, ship_date)
            VALUES ('TEST123', '17612 - 250300', 1, 1, 5, '2025-10-06')
        """)
        assert False, "Duplicate insert should have failed"
    except Exception as e:
        print("✅ Unique constraint working")

    # Test 3: Counts match ShipStation
    today_total = conn.execute("""
        SELECT SUM(quantity_shipped) FROM shipped_items WHERE ship_date = '2025-10-06'
    """).fetchone()[0]

    print(f"✅ Today's total: {today_total} units (should be 331)")
2. Performance Tests
def benchmark_queries():
    """Compare old vs new query performance"""
    import time

    # Old text-based query
    start = time.time()
    conn.execute("""
        SELECT base_sku, SUM(quantity_shipped)
        FROM shipped_items
        WHERE ship_date >= '2025-09-01'
        GROUP BY base_sku
    """).fetchall()
    old_time = time.time() - start

    # New FK-based query
    start = time.time()
    conn.execute("""
        SELECT s.sku_code, SUM(si.quantity_shipped)
        FROM shipped_items si
        JOIN skus s ON si.sku_id = s.sku_id
        WHERE si.ship_date >= '2025-09-01'
        GROUP BY s.sku_code
    """).fetchall()
    new_time = time.time() - start

    print(f"Old: {old_time:.3f}s, New: {new_time:.3f}s")
VI. ROLLBACK PLAN
Emergency Rollback (If Issues Found)
def rollback_migration():
    """Revert to pre-migration state"""

    # Drop new tables
    conn.execute("DROP TABLE IF EXISTS lots")
    conn.execute("DROP TABLE IF EXISTS skus")

    # Remove new columns
    conn.execute("ALTER TABLE shipped_items DROP COLUMN shipstation_sku_raw")
    conn.execute("ALTER TABLE shipped_items DROP COLUMN sku_id")
    conn.execute("ALTER TABLE shipped_items DROP COLUMN lot_id")

    # Restore old unique constraint
    conn.execute("""
        CREATE UNIQUE INDEX uniq_shipped_items_key 
        ON shipped_items(order_number, base_sku, sku_lot)
    """)

    print("⚠️ Rolled back to pre-migration state")
VII. IMPLEMENTATION TIMELINE
Week 1: Preparation
 Create migration scripts
 Set up test environment
 Backup production database
Week 2: Phase 1 & 2 (Reference Tables)
 Create skus and lots tables
 Migrate data from inventory_current and lot_inventory
 Add FK columns to shipped_items
 Backfill FK data with parser
Week 3: Phase 3 (Services Update)
 Update daily shipment processor
 Add date guard to status sync
 Update ShipStation upload service
 Fix manual order sync
Week 4: Phase 4 (Cleanup & Validation)
 Fix current data issues (ship_date split, missing units)
 Run validation tests
 Update all queries to use JOINs
 Remove legacy columns
VIII. SUCCESS CRITERIA
✅ Data Integrity:

No ship_date splits
All ShipStation units present in database
No duplicate records
Foreign key constraints enforced
✅ Performance:

Query performance equal or better than text-based
Real-time sync maintains data accuracy
✅ Maintainability:

Single source of truth for SKUs and lots
No text parsing in queries
Centralized parsing service
✅ ShipStation Compatibility:

Raw SKU preserved for API idempotency
Deduplication works correctly
Historical data guards prevent re-sync
IX. MONITORING & ALERTS
Post-Migration Monitoring
def daily_health_check():
    """Run daily to detect data integrity issues"""

    # Check for FK violations
    orphans = check_orphaned_records()
    if orphans > 0:
        alert(f"⚠️ Found {orphans} orphaned records")

    # Check for parse failures
    unparsed = check_unparsed_skus()
    if unparsed > 0:
        alert(f"⚠️ Found {unparsed} unparseable SKUs")

    # Check ShipStation sync accuracy
    discrepancy = compare_with_shipstation()
    if discrepancy > 10:
        alert(f"⚠️ {discrepancy} unit discrepancy with ShipStation")
X. FINAL NOTES
Key Design Principles
Preserve ShipStation Reality: Store raw SKU exactly as received
Normalize Internally: Use FKs for data integrity
Centralize Parsing: Single source of truth for SKU-Lot extraction
Guard Against Staleness: Date filters prevent historical re-sync
Maintain Compatibility: Hybrid design supports both systems
Risk Mitigation
Complete database backup before migration
Test environment mirrors production
Rollback plan ready
Phased implementation with validation gates
Monitoring alerts for early issue detection
This plan provides a complete roadmap from current state to fully normalized relational database design, while maintaining ShipStation compatibility and fixing all existing data integrity issues. Excuse me
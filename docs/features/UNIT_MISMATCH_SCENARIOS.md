# Unit Mismatch Scenarios Analysis

**Last Updated:** October 27, 2025

## Overview
This document identifies the different root causes and scenarios that lead to discrepancies between ShipStation "Units to Ship" and Local Database "Awaiting Shipment" counts.

---

## Current Monitoring Systems

### 1. **Lot Mismatch Scanner** (`scheduled_lot_mismatch_scanner.py`)
- **What it detects:** SKU-Lot number mismatches
- **Example:** Order has `17612 - 250237` in ShipStation but `250238` is the active lot in local DB
- **Detection:** Every 15 minutes, 30-day lookback window
- **Resolution:** Manual via dashboard

### 2. **Unit Count Mismatch** (Dashboard KPI comparison)
- **What it shows:** Total quantity discrepancy
- **Metrics:** ShipStation Units to Ship vs Local DB Awaiting Shipment
- **Detection:** Real-time dashboard display
- **Resolution:** Currently manual investigation

---

## Mismatch Scenarios

### Scenario 1: **Duplicate Orders in ShipStation**
**Cause:** Same order uploaded multiple times due to:
- Bundle expansion creating duplicate base SKUs
- Multiple upload attempts after failures
- Concurrent upload processes

**Impact:** ShipStation units > Local DB units

**Detection:**
- `duplicate_order_alerts` table tracks orders with same order number
- Duplicate scanner runs every 15 minutes

**Example:**
```
Order #123456 uploaded twice:
  - First upload: 2 items (SKU 17612)
  - Second upload: 2 items (SKU 17612)
  - ShipStation total: 4 units
  - Local DB: 2 units (correct)
  - Mismatch: +2 units in ShipStation
```

---

### Scenario 2: **Manual Orders Created in ShipStation**
**Cause:** Orders created directly in ShipStation (not from XML import)
- Emergency orders
- Customer service adjustments
- Manual entries by warehouse staff

**Impact:** ShipStation units > Local DB units

**Detection:**
- Unified sync imports orders with `orderNumber` starting with specific prefixes
- Orders without local DB record

**Example:**
```
Manual order #999999:
  - Created in ShipStation: 5 units
  - Not in local DB: 0 units
  - Mismatch: +5 units in ShipStation
```

---

### Scenario 3: **Failed Uploads to ShipStation**
**Cause:** Orders stuck in `orders_inbox` that never uploaded:
- ShipStation API errors
- Authentication failures
- Network timeouts
- Invalid address data

**Impact:** Local DB units > ShipStation units

**Detection:**
- Orders in `orders_inbox` with status 'pending'
- No corresponding order in ShipStation

**Example:**
```
Order #123457:
  - Local DB status: pending (3 units)
  - ShipStation: not found
  - Mismatch: +3 units in Local DB
```

---

### Scenario 4: **Stale Status - Orders Already Shipped**
**Cause:** Orders shipped in ShipStation but status not yet synced back to local DB
- Sync delay (5-minute intervals)
- Orders shipped between sync cycles
- Sync failures

**Impact:** Local DB units > ShipStation units

**Detection:**
- Orders with status 'shipped' in ShipStation
- Still showing 'awaiting_shipment' in local DB

**Example:**
```
Order #123458:
  - ShipStation status: shipped (0 units awaiting)
  - Local DB status: awaiting_shipment (2 units)
  - Mismatch: +2 units in Local DB (temporary)
```

---

### Scenario 5: **Voided Orders in ShipStation**
**Cause:** Orders voided/cancelled in ShipStation but still active locally
- Customer cancellations
- Payment failures
- Address validation failures

**Impact:** Local DB units > ShipStation units

**Detection:**
- `unified_shipstation_sync.py` filters out voided shipments
- Orders exist locally but not in ShipStation awaiting_shipment status

**Example:**
```
Order #123459:
  - ShipStation status: cancelled (0 units)
  - Local DB status: awaiting_shipment (4 units)
  - Mismatch: +4 units in Local DB
```

---

### Scenario 6: **Bundle Expansion Errors**
**Cause:** Bundles not properly expanded during XML import
- Missing bundle configuration
- Component SKUs not in Key Products list
- Malformed XML data

**Impact:** Varies (could be either direction)

**Detection:**
- Logs show "Skipping bundle component" warnings
- Orders with bundle SKUs instead of expanded components

**Example:**
```
Bundle SKU BUNDLE-A (should expand to 3 components):
  - Expected: 3 items uploaded to ShipStation
  - Actual: 1 bundle item uploaded
  - Component validation failed
  - Mismatch: Depends on actual vs expected
```

---

### Scenario 7: **SKU Consolidation Issues**
**Cause:** Multiple line items with same SKU not properly consolidated
- Normalization failures
- Lot number mismatches preventing consolidation
- Data format inconsistencies

**Impact:** ShipStation units ≠ Local DB units

**Detection:**
- Upload logs show SKU transformation pipeline
- Multiple line items for same base SKU

**Example:**
```
Order #123460:
  - Local DB: 2 entries of SKU 17612 (2 + 3 = 5 units)
  - Consolidation fails due to different lot formats
  - ShipStation receives: 2 separate line items
  - Quantity discrepancy if ShipStation deduplicates
```

---

### Scenario 8: **Race Conditions**
**Cause:** Concurrent processes modifying same order
- Upload service running while status sync updates order
- Multiple instances of upload service
- Database transaction conflicts

**Impact:** Unpredictable (both directions possible)

**Detection:**
- Database transaction retry logs
- Deadlock warnings in PostgreSQL logs

**Example:**
```
Order #123461:
  - Process A: Uploading order (sets status to 'uploaded')
  - Process B: Syncing status (sets to 'shipped')
  - Race condition on status field
  - Unit count may be double-counted or missed
```

---

### Scenario 9: **Held Orders**
**Cause:** Orders on hold in local DB but released in ShipStation
- Manual hold release in ShipStation
- Hold status not synced back

**Impact:** Local DB units > ShipStation units

**Detection:**
- Orders with `hold_until_date` in local DB
- Status 'on_hold' locally but 'awaiting_shipment' in ShipStation

**Example:**
```
Order #123462:
  - Local DB status: on_hold (2 units not counted in awaiting)
  - ShipStation: awaiting_shipment (2 units counted)
  - Manual release in ShipStation
  - Mismatch: +2 units in ShipStation
```

---

## Recommended Solutions

### Immediate Actions
1. **Run EOD daily** - Syncs shipped items and updates local DB
2. **Monitor duplicate alerts** - Resolve duplicates in ShipStation
3. **Review lot mismatch alerts** - Update incorrect lot numbers

### System Improvements
1. **Add unit mismatch alerts table** - Track specific discrepancies by order
2. **Categorize mismatches** - Automatically classify by scenario
3. **Auto-resolution for certain scenarios:**
   - Sync voided/cancelled orders automatically
   - Auto-resolve shipped orders (status sync)
   - Flag duplicates for manual review

### Monitoring Enhancements
1. **Mismatch breakdown dashboard card:**
   - Show count by scenario type
   - Drill-down to specific orders
   - Historical trend chart

2. **Alerts for specific scenarios:**
   - Failed uploads (>30 minutes old)
   - Manual orders not in DB
   - Large discrepancies (>10 units)

---

## Data Sources

### ShipStation API
- **Endpoint:** `/orders?orderStatus=awaiting_shipment`
- **Update frequency:** 5 minutes (unified sync)
- **Fields used:** `orderStatus`, `items`, `orderNumber`

### Local Database
- **Table:** `orders_inbox`
- **Status filter:** `status = 'pending' OR status = 'awaiting_shipment'`
- **Join:** Aggregated item quantities from order items

### Current Detection
- **KPI Card:** Shows both counts side-by-side
- **No automatic categorization:** Manual investigation required
- **Duplicate Scanner:** Detects duplicate order numbers only
- **Lot Scanner:** Detects lot mismatches only

---

## Next Steps

1. **Create `unit_mismatch_alerts` table** with columns:
   - `order_number`
   - `shipstation_units`
   - `local_db_units`
   - `mismatch_amount` (difference)
   - `scenario_category` (enum of scenarios above)
   - `detected_at`
   - `resolved_at`
   - `resolution_notes`

2. **Build mismatch categorization logic:**
   - Check for duplicates → Scenario 1
   - Check if exists in local DB → Scenario 2
   - Check ShipStation status → Scenario 4, 5
   - Check for upload failures → Scenario 3

3. **Add dashboard card:**
   - "Unit Mismatch Breakdown"
   - Bar chart showing count by scenario
   - Click to view details

4. **Automated alerts:**
   - Email/notification when mismatch >10 units
   - Daily summary of unresolved mismatches

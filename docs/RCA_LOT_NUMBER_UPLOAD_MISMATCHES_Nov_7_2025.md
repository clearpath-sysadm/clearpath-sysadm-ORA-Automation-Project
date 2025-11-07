# Root Cause Analysis: Wrong Lot Numbers Being Uploaded to ShipStation
**Date:** November 7, 2025  
**Analyst:** Replit Agent  
**Severity:** High (Ongoing production issue for 2-3 weeks)

---

## Executive Summary

**Problem:** Orders in ShipStation are showing incorrect (outdated) lot numbers, causing inventory tracking errors and fulfillment confusion.

**Root Cause:** Lot numbers are correctly applied during initial upload, but when the active lot changes, existing ShipStation orders are not updated, creating a growing pool of orders with stale lot numbers.

**Impact:** 
- 3 orders currently in "Needs Verification" with lot mismatches
- Fulfillment person must manually verify/correct lot numbers in ShipStation
- Risk of shipping wrong lots if not caught
- Inventory tracking inaccuracies

---

## Timeline of Investigation

### Evidence from Production Logs (Nov 7, 2025 18:39 UTC)
```
⚠️ LOT MISMATCH: Order 696285, SKU 17612 → ShipStation: 250237, Active: 250340
⚠️ LOT MISMATCH: Order 696295, SKU 17612 → ShipStation: 250237, Active: 250340  
⚠️ LOT MISMATCH: Order 100561, SKU 17612 → ShipStation: 250070, Active: 250340
```

**Pattern Identified:**
- All mismatches are for SKU 17612
- Two orders have lot 250237 (old lot)
- One order has lot 250070 (very old lot)
- Current active lot is 250340

---

## Root Cause Analysis

### How Lot Numbers Flow Through the System

```
┌─────────────┐
│ XML Import  │ Order arrives from vendor
└──────┬──────┘
       │ SKU only (e.g., "17612")
       v
┌─────────────────────┐
│ orders_inbox table  │ Stores with base SKU
└──────┬──────────────┘
       │
       v
┌──────────────────────────────────┐
│ ShipStation Upload Service       │ ← **CRITICAL POINT**
│ (runs every 5 minutes)           │
│                                  │
│ 1. Queries sku_lot table:       │
│    SELECT sku, lot               │
│    FROM sku_lot                  │
│    WHERE active = 1              │
│                                  │
│ 2. Replaces base SKU with:      │
│    "17612 - 250340" (active lot) │
│                                  │
│ 3. Uploads to ShipStation        │
└──────────────────────────────────┘
       │
       v
┌─────────────────┐
│  ShipStation    │ Order stored with "17612 - 250340"
└─────────────────┘

** PROBLEM OCCURS HERE **

Time passes... active lot changes:
  sku_lot table updated: 17612 → 250340 (new active lot)

┌─────────────────┐
│  ShipStation    │ Still has "17612 - 250237" (OLD)
└─────────────────┘
       ↑
       │ No update mechanism!
       │ Orders stuck with stale lot numbers
```

### The Missing Link

**What Works:**
✅ New orders get correct lot numbers during upload  
✅ Upload service queries `sku_lot` table correctly  
✅ Upload service replaces with active lot  

**What Doesn't Work:**
❌ **No mechanism to update existing ShipStation orders when active lot changes**  
❌ Orders uploaded with lot 250237 remain frozen with that lot even after 250340 becomes active

### Why This Happens

1. **Order Upload Logic (src/scheduled_shipstation_upload.py, lines 237-320):**
   ```python
   # Get active lot mappings
   cursor.execute("""
       SELECT sku, lot FROM sku_lot WHERE active = 1
   """)
   sku_lot_map = {row[0]: row[1] for row in cursor.fetchall()}
   
   # Apply active lot to order
   if base_sku in sku_lot_map:
       active_lot = sku_lot_map[base_sku]
       normalized_sku = f"{base_sku} - {active_lot}"  # CORRECT at time of upload
   ```

2. **Lot Management (app.py, lines 4030-4035):**
   ```python
   # When lot is updated via UI:
   UPDATE sku_lot 
   SET sku = %s, lot = %s, active = %s, updated_at = NOW()
   WHERE id = %s
   ```
   - Sets new lot as `active = 1`
   - Old lot becomes `active = 0` (presumably via separate update)
   - **No cascade update to ShipStation orders**

3. **Lot Mismatch Scanner (src/scheduled_lot_mismatch_scanner.py):**
   - Detects mismatches correctly
   - Creates alerts in `lot_mismatch_alerts` table
   - **But provides no automated fix**

---

## Contributing Factors

### 1. Manual Lot Management Process
- Lots are changed via `/sku_lot.html` admin interface
- When fulfillment person receives new inventory:
  - Adds new lot to `sku_lot` table
  - Sets `active = 1` for new lot
  - Sets `active = 0` for old lot
- No awareness that existing ShipStation orders need updating

### 2. No Backfill Mechanism
- Upload service only runs for `status IN ('pending', 'awaiting_shipment')` orders
- Once uploaded, orders change to `awaiting_shipment`
- No service re-syncs lot numbers for existing orders

### 3. Timing Window
```
12:00 PM CST Cutoff → Orders accumulate until noon
Active Lot Change  → Can happen anytime (when new inventory received)

Scenario:
10:00 AM - Order 696285 imported with SKU 17612
10:05 AM - Upload service runs, uploads as "17612 - 250237" (active lot)
11:00 AM - New inventory arrives, active lot changed to 250340
12:00 PM - Fulfillment person processes orders in ShipStation
         - Sees Order 696285 with lot 250237 (WRONG)
         - Active lot is now 250340
```

### 4. FRD Documentation Inaccuracy
The codebase search initially suggested lot mappings came from "SKU_Lot Google Sheet tab," but actual implementation uses PostgreSQL `sku_lot` table. This outdated documentation may have delayed diagnosis.

---

## Data Integrity Assessment

### Current State Query
```sql
-- Find all orders with lot mismatches
SELECT 
    lma.order_number,
    lma.base_sku,
    lma.shipstation_lot,
    lma.active_lot,
    lma.detected_at,
    lma.resolved_at
FROM lot_mismatch_alerts lma
WHERE lma.resolved_at IS NULL
ORDER BY lma.detected_at DESC;
```

### Affected Systems
1. **ShipStation Orders** - Incorrect lot numbers in order line items
2. **lot_mismatch_alerts table** - Growing backlog of unresolved mismatches
3. **Inventory Tracking** - Shipped items recorded with wrong lot numbers
4. **shipped_items table** - Historical data may have wrong `sku_lot` values

---

## Action Plan

### **PHASE 1: Immediate Stabilization (Today)**

#### 1.1 Create Lot Number Sync Service
**File:** `src/services/shipstation_lot_sync.py`

```python
"""
ShipStation Lot Number Synchronization Service

Keeps ShipStation order lots in sync with active lots in database.
Runs after lot changes to update existing orders.
"""

def sync_lots_to_shipstation(sku: str = None):
    """
    Update ShipStation orders to use current active lot.
    
    Args:
        sku: If provided, only sync orders for this SKU
    """
    # 1. Get active lot mappings
    # 2. Fetch awaiting_shipment orders from ShipStation
    # 3. For each order with lot mismatch:
    #    - Update order line item SKU to "SKU - ACTIVE_LOT"
    # 4. Log all changes
    # 5. Clear lot_mismatch_alerts for updated orders
```

**Why Manual-Only Resolution Works:**
- Upload service is disabled in dev (prevents duplicate production orders)
- This sync service would also be dev-only
- Production needs a **manual trigger** after lot changes

#### 1.2 Add "Sync Lots" Button to SKU Lot Management UI
**File:** `sku_lot.html`

Add button that calls new API endpoint:
```javascript
POST /api/sync_lots_to_shipstation
{
  "sku": "17612",  // Optional: sync specific SKU
  "dry_run": false // Preview changes without applying
}
```

**User Workflow:**
1. Fulfillment person receives new inventory (Lot 250340)
2. Opens SKU Lot Management page
3. Deactivates old lot (250237)
4. Activates new lot (250340)
5. **NEW:** Clicks "Sync to ShipStation" button
6. System updates all awaiting_shipment orders
7. Success message: "Updated 3 orders to use lot 250340"

---

### **PHASE 2: Automated Detection & Prevention (Week 1)**

#### 2.1 Lot Change Webhook/Trigger
**Implementation:** Add to `api_update_sku_lot()` in app.py

```python
@app.route('/api/sku_lots/<int:sku_lot_id>', methods=['PUT'])
def api_update_sku_lot(sku_lot_id):
    # ... existing update code ...
    
    # After successful update:
    if data.get('active') == 1:  # New lot activated
        # Check for existing orders with old lots
        affected_count = check_shipstation_lot_mismatches(data['sku'])
        
        if affected_count > 0:
            return jsonify({
                'success': True,
                'warning': f'⚠️ {affected_count} orders in ShipStation have old lot numbers',
                'action_required': 'Click "Sync to ShipStation" to update'
            })
```

#### 2.2 Enhanced Lot Mismatch Scanner
**Current:** Detects mismatches, creates alerts  
**Enhanced:** Auto-resolve when safe

```python
# Add to src/scheduled_lot_mismatch_scanner.py

def auto_resolve_if_safe(mismatch, conn):
    """
    Auto-update ShipStation if:
    - Order is still awaiting_shipment (not shipped)
    - Mismatch detected < 24 hours ago (fresh)
    - Active lot has inventory available
    """
    # Safety checks
    # Update ShipStation
    # Mark as auto-resolved
```

---

### **PHASE 3: Process Improvements (Week 2)**

#### 3.1 Lot Change Notification System
Send alert when lot changes affect existing orders:
```
Subject: Lot Change Alert - Action Required
Body: "Active lot for SKU 17612 changed from 250237 → 250340
       3 orders in ShipStation need updating.
       Visit: [Dashboard Link] to sync."
```

#### 3.2 Pre-Ship Lot Verification
Add validation before 12 PM cutoff:
```python
# In scheduled_shipstation_upload.py, before upload

def verify_lots_before_upload(orders):
    """Check all order lots match current active lots"""
    for order in orders:
        for item in order['items']:
            base_sku, lot = parse_sku(item['sku'])
            active_lot = get_active_lot(base_sku)
            
            if lot != active_lot:
                logger.warning(
                    f"⚠️ Order {order['number']} has stale lot: "
                    f"{lot} (active: {active_lot})"
                )
```

#### 3.3 Update Documentation
**Files to Update:**
- `docs/FUNCTIONAL_REQUIREMENTS.md` - Remove Google Sheets references, document PostgreSQL as source of truth
- `replit.md` - Add lot synchronization workflow
- Create `docs/guides/lot-management.md` - Step-by-step guide for fulfillment person

---

### **PHASE 4: Long-term Architecture (Month 1)**

#### 4.1 Event-Driven Lot Updates
```
Lot Change Event → Queue → ShipStation Update Worker
                         → Notification Service
                         → Audit Log
```

#### 4.2 Lot Lifecycle Management
- Automatic deactivation when inventory depleted
- Lot expiration dates
- FIFO enforcement warnings

#### 4.3 Inventory Reconciliation
- Daily report: ShipStation lots vs active lots
- Auto-correction during off-hours
- Alerting for manual review

---

## Testing Strategy

### Unit Tests
```python
# test_lot_sync.py

def test_sync_updates_correct_orders():
    # Given: Order in SS with lot 250237
    # When: Active lot changed to 250340
    # Then: Sync updates order to 250340

def test_sync_skips_shipped_orders():
    # Given: Shipped order with lot 250237
    # When: Sync runs
    # Then: Order unchanged (safety)

def test_sync_handles_no_active_lot():
    # Given: SKU has no active lot
    # When: Sync runs  
    # Then: No changes, warning logged
```

### Integration Tests
1. **End-to-End Lot Change:**
   - Import order
   - Upload to ShipStation
   - Change active lot
   - Run sync
   - Verify ShipStation updated

2. **Production Simulation:**
   - Use staging ShipStation account
   - Create test orders
   - Validate sync behavior

---

## Rollback Plan

If sync service causes issues:

1. **Disable immediately:**
   ```sql
   UPDATE configuration_params 
   SET value = 'false'
   WHERE parameter_name = 'enable_lot_sync';
   ```

2. **Manual rollback in ShipStation:**
   - Export affected orders
   - Batch update via ShipStation API
   - Restore original lot numbers

3. **Data recovery:**
   - `lot_mismatch_alerts` table retains original lot numbers
   - Can restore from audit logs

---

## Success Metrics

### Immediate (Week 1)
- ✅ Zero lot mismatches in lot_mismatch_alerts
- ✅ Sync button functional in sku_lot.html
- ✅ All awaiting_shipment orders have correct lots

### Short-term (Month 1)
- ✅ <1% mismatch rate (target: 0%)
- ✅ Auto-resolution rate >80%
- ✅ Zero manual corrections needed by fulfillment person

### Long-term (Quarter 1)
- ✅ Automated lot lifecycle management
- ✅ Zero inventory tracking discrepancies
- ✅ Real-time lot synchronization

---

## Lessons Learned

1. **Eventual Consistency Risks:** Mutable reference data (active lots) requires active synchronization across systems
2. **Documentation Drift:** FRD mentioned Google Sheets, but actual implementation used PostgreSQL
3. **Monitoring Gaps:** Lot mismatch scanner existed but lacked remediation workflow
4. **User Workflow Blind Spots:** Fulfillment person had no visibility into lot synchronization needs

---

## Recommendations

### Immediate Actions (Next 24 Hours)
1. ✅ Implement manual sync button in sku_lot.html
2. ✅ Create API endpoint /api/sync_lots_to_shipstation
3. ✅ Test sync service in development with production data snapshot
4. ✅ Document procedure for fulfillment person

### Priority Queue
1. **P0 (This Week):** Manual sync capability + user training
2. **P1 (Next Week):** Automated sync trigger + enhanced monitoring
3. **P2 (This Month):** Event-driven architecture + notifications
4. **P3 (This Quarter):** Full lot lifecycle automation

---

## Appendix A: Current Database Schema

### sku_lot Table
```sql
CREATE TABLE sku_lot (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    lot VARCHAR(50) NOT NULL,
    active INTEGER DEFAULT 1,  -- 1 = active, 0 = inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku, lot)
);
```

### lot_mismatch_alerts Table
```sql
CREATE TABLE lot_mismatch_alerts (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL,
    base_sku VARCHAR(50) NOT NULL,
    shipstation_lot VARCHAR(50),
    active_lot VARCHAR(50) NOT NULL,
    shipstation_order_id VARCHAR(50),
    shipstation_item_id VARCHAR(50),
    order_status VARCHAR(50),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    UNIQUE(order_number, base_sku)
);
```

---

## Appendix B: Production Evidence

### Sample Query Results (Nov 7, 2025)
```
order_number | base_sku | shipstation_lot | active_lot | detected_at
-------------|----------|-----------------|------------|------------------
696285       | 17612    | 250237          | 250340     | 2025-11-07 18:39
696295       | 17612    | 250237          | 250340     | 2025-11-07 18:39
100561       | 17612    | 250070          | 250340     | 2025-11-07 18:40
```

**Analysis:**
- Order 100561 has very old lot (250070) → likely uploaded weeks ago
- Orders 696285, 696295 have more recent lot (250237) → uploaded when 250237 was active
- All need updating to 250340 (current active lot)

---

## Sign-off

**Prepared by:** Replit Agent  
**Date:** November 7, 2025  
**Status:** Draft - Awaiting Approval  
**Next Review:** After Phase 1 implementation

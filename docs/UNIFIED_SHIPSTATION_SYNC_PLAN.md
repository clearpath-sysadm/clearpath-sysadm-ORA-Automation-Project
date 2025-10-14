# Unified ShipStation Sync - Implementation Plan

## ⚠️ CRITICAL UPDATES - ARCHITECT REVIEW

The architect identified **5 critical issues** that MUST be addressed before implementation:

### 🔴 Issue 1: Watermark Scope Gap
**Problem:** Reusing manual-sync watermark will miss status updates for legacy orders modified before the manual watermark.

**Solution:**
- Create **dedicated watermark** for `shipstation-sync` workflow
- Seed to **14-30 days back** (not copying from manual-sync)
- Perform **one-time backfill** of order statuses in 14-day window
- Document backfill completion in migration log

### 🔴 Issue 2: Failure/Race Condition Risk
**Problem:** Updating watermark after processing without guards allows crashed runs to skip orders.

**Solution:**
- Use **run ID tracking** to prevent watermark advancement on failure
- Implement **transactional protection**: watermark updates ONLY after successful commit
- Add **exclusive lock** mechanism to prevent concurrent executions
- **Start with 5-min schedule ONLY after measuring actual runtime** (may need 10-15 min initially)

### 🔴 Issue 3: Shipped Order Handling Ambiguity
**Problem:** Plan doesn't explicitly confirm shipped orders are moved to `shipped_orders/shipped_items`.

**Solution:**
- **Explicitly document** in `update_existing_order_status()` function:
  ```python
  if ss_status == 'shipped':
      # 1. Update orders_inbox status
      # 2. Insert into shipped_orders (with ship_date, order_number, shipstation_order_id)
      # 3. Insert items into shipped_items (from order_items_inbox)
  ```
- **Confirm data parity** with current status sync behavior
- Add test case specifically for shipped order migration

### 🔴 Issue 4: Migration/Rollback Safety
**Problem:** Plan disables old workflows immediately, leaving no fast rollback if issues surface.

**Solution - SHADOW MODE DEPLOYMENT:**
1. **Phase 1 (Days 1-2): Shadow Mode**
   - Run unified sync in PARALLEL with old workflows
   - Old workflows remain active (no disruption)
   - Compare results: unified vs old (should match)
   - Log discrepancies for analysis

2. **Phase 2 (Day 3): Validation**
   - Verify 100% parity over 48 hours
   - Check watermark advancement
   - Monitor performance metrics

3. **Phase 3 (Day 4): Cutover**
   - Disable old workflows ONLY after validation
   - Keep scripts accessible (not archived yet)
   - Monitor for 24 hours

4. **Rollback Procedure:**
   - Keep enable flags ready: `UPDATE workflow_controls SET enabled = 1 WHERE workflow_name IN ('status-sync', 'manual-order-sync')`
   - Restore watermark values from backup
   - Scripts remain in `src/` during validation period

### 🔴 Issue 5: Testing Coverage Gaps
**Problem:** Tests don't cover API failures, watermark regression, or concurrency scenarios.

**Additional Test Cases Required:**
1. **API Failure Scenarios**
   - ShipStation returns 500 error → retry logic works, watermark not advanced
   - Network timeout → graceful failure, no partial updates
   - Rate limit hit → exponential backoff, resume on next cycle

2. **Watermark Integrity**
   - Run completes → watermark advances to max(modifyDate)
   - Run fails mid-process → watermark unchanged
   - Concurrent runs → only one succeeds (exclusive lock)

3. **Concurrency/Duplicate**
   - Same order modified twice in sync window → latest update wins
   - Parallel execution attempt → second run waits or skips
   - Order imported then status updated → no duplication

4. **Data Parity Validation**
   - Shipped order: compare unified vs status-sync results
   - Manual order: compare unified vs manual-sync results
   - Verify ALL fields match (carrier, service, tracking, items)

---

## Executive Summary
Combine the **Status Sync** and **Manual Order Sync** workflows into a single, efficient **ShipStation Sync** workflow that handles both manual order imports and status updates in one unified process.

**⚠️ DEPLOYMENT STRATEGY: Shadow Mode → Validation → Cutover** (see Issue 4 above)

---

## Current State Analysis

### Workflow 1: Status Sync (`src/shipstation_status_sync.py`)
- **Runs:** Hourly
- **API Strategy:** Fetches last 7 days of orders via `modifyDateStart/modifyDateEnd` params
- **Scope:** Updates existing orders that have `shipstation_order_id`
- **Data Synced:**
  - Order status (shipped, cancelled, awaiting_shipment, on_hold, awaiting_payment)
  - Carrier code, carrier ID
  - Service code, service name
  - Tracking number
- **Destination:** Updates `orders_inbox` table
- **Limitations:** 
  - 7-day window means re-fetching same data repeatedly
  - Only handles orders already in local system
  - Inefficient for high-volume systems

### Workflow 2: Manual Order Sync (`src/manual_shipstation_sync.py`)
- **Runs:** Hourly
- **API Strategy:** Watermark-based incremental sync via `modifyDateStart` param
- **Scope:** Imports manual orders created in ShipStation
- **Filters:**
  - Order number starts with "10" (manual orders only)
  - Contains key product SKUs (17612, 17904, 17914, 18675, 18795)
  - Not originated from local system (checks `shipstation_order_line_items`)
- **Data Synced:**
  - Complete order info (number, date, customer, addresses)
  - Order items with SKU-lot parsing
  - Carrier/service information
  - Creates `orders_inbox`, `order_items_inbox`
  - Creates `shipped_orders`, `shipped_items` if status=shipped
- **Destination:** Multiple tables (orders_inbox, order_items_inbox, shipped_orders, shipped_items)
- **Advantages:**
  - Watermark prevents redundant API calls
  - Comprehensive order import
  - Efficient incremental sync

### Problems with Current Design
1. **Redundant API Calls:** Both workflows fetch from ShipStation hourly
2. **Overlapping Data:** Both update carrier/service/status info
3. **Inefficient Window:** 7-day window re-fetches same orders repeatedly
4. **Delayed Detection:** Manual orders only detected once per hour
5. **Maintenance Overhead:** Two workflows with similar logic

---

## Proposed Solution: Unified ShipStation Sync

### Architecture Overview
**Single workflow** that:
1. Uses watermark-based incremental sync (more efficient)
2. Processes ALL orders modified since last sync
3. Applies intelligent routing logic based on order characteristics
4. Updates status for existing orders
5. Imports new manual orders
6. Handles shipped orders (moves to shipped_orders/shipped_items)

### Workflow Name
- **Workflow ID:** `shipstation-sync`
- **Display Name:** "ShipStation Sync"
- **File:** `src/shipstation_sync.py`
- **Schedule:** Every 5 minutes (configurable)

### Processing Logic Flow

```
┌─────────────────────────────────────────┐
│  Fetch orders modified since watermark  │
│  (modifyDateStart = last_sync_timestamp)│
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│    For each order from ShipStation:     │
└──────────────────┬──────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │ Is this a      │───NO──┐
          │ manual order?  │       │
          │ (starts w/10)  │       │
          └────────┬───────┘       │
                   │YES             │
                   ▼                ▼
    ┌──────────────────────┐  ┌─────────────────────┐
    │ Check if contains    │  │ Check if exists in  │
    │ key product SKUs     │  │ orders_inbox with   │
    │                      │  │ shipstation_order_id│
    └──────┬───────────────┘  └──────┬──────────────┘
           │YES                       │YES
           ▼                          ▼
    ┌──────────────────────┐  ┌─────────────────────┐
    │ Check if originated  │  │ Update status,      │
    │ from local system    │  │ carrier, service,   │
    │ (shipstation_order_  │  │ tracking number     │
    │  line_items lookup)  │  │                     │
    └──────┬───────────────┘  └──────┬──────────────┘
           │NO                        │
           ▼                          ▼
    ┌──────────────────────┐  ┌─────────────────────┐
    │ Import manual order: │  │ If status=shipped:  │
    │ - orders_inbox       │  │ Move to shipped_    │
    │ - order_items_inbox  │  │ orders/items        │
    │ - If shipped: also   │  │                     │
    │   shipped_orders/    │  └─────────────────────┘
    │   items              │
    └──────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │ Update watermark│
         │ to max(modifyDate)│
         └─────────────────┘
```

### Data Tables Updated

| Table | Manual Orders | Status Updates |
|-------|--------------|----------------|
| `orders_inbox` | ✅ INSERT/UPDATE | ✅ UPDATE status, carrier, service, tracking |
| `order_items_inbox` | ✅ INSERT | ❌ No change |
| `shipped_orders` | ✅ INSERT (if shipped) | ❌ Already handled by inbox status |
| `shipped_items` | ✅ INSERT (if shipped) | ❌ Already handled by inbox status |
| `sync_watermark` | ✅ UPDATE | ✅ UPDATE |

---

## Implementation Steps

### Phase 1: Create Unified Workflow (Day 1)

#### Step 1.1: Create New File
- **File:** `src/shipstation_sync.py`
- **Base:** Copy structure from `manual_shipstation_sync.py` (better watermark logic)

#### Step 1.2: Implement Core Functions
```python
# 1. get_last_sync_timestamp() - from manual_shipstation_sync.py
# 2. update_sync_watermark() - from manual_shipstation_sync.py
# 3. fetch_shipstation_orders_since_watermark() - from manual_shipstation_sync.py
# 4. is_order_from_local_system() - from manual_shipstation_sync.py
# 5. has_key_product_skus() - from manual_shipstation_sync.py
# 6. is_manual_order() - NEW: check if order_number starts with "10"
# 7. order_exists_locally() - NEW: check if order in orders_inbox with shipstation_order_id
# 8. import_manual_order() - from manual_shipstation_sync.py
# 9. update_existing_order_status() - from shipstation_status_sync.py (modified)
# 10. process_order() - NEW: routing logic
```

#### Step 1.3: Main Processing Function
```python
def run_shipstation_sync():
    """
    Unified sync: handles both manual order imports and status updates.
    """
    if not is_workflow_enabled('shipstation-sync'):
        return {"message": "Workflow disabled"}, 200
    
    update_workflow_last_run('shipstation-sync')
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    
    # Get watermark
    last_sync = get_last_sync_timestamp()
    
    # Fetch orders
    orders = fetch_shipstation_orders_since_watermark(api_key, api_secret, last_sync)
    
    # Process each order
    manual_imported = 0
    status_updated = 0
    max_modify_date = None
    
    with transaction_with_retry() as conn:
        for order in orders:
            order_id = order.get('orderId')
            order_number = order.get('orderNumber', '').strip()
            modify_date = order.get('modifyDate', '')
            
            # Track max modify date
            if modify_date and (max_modify_date is None or modify_date > max_modify_date):
                max_modify_date = modify_date
            
            # Route to appropriate handler
            if is_manual_order(order_number):
                # Manual order path
                if has_key_product_skus(order) and not is_order_from_local_system(str(order_id)):
                    if import_manual_order(order, conn):
                        manual_imported += 1
            else:
                # Status update path
                if order_exists_locally(str(order_id), conn):
                    if update_existing_order_status(order, conn):
                        status_updated += 1
    
    # Update watermark
    if max_modify_date:
        update_sync_watermark(max_modify_date)
    
    return {
        "manual_orders_imported": manual_imported,
        "status_updates": status_updated
    }, 200
```

### Phase 2: Update Workflow Configuration (Day 1)

#### Step 2.1: Register New Workflow
Update `workflow_controls` table:
```sql
INSERT INTO workflow_controls (workflow_name, enabled, description)
VALUES ('shipstation-sync', 1, 'Unified sync: imports manual orders and updates status from ShipStation')
ON CONFLICT(workflow_name) DO UPDATE SET description = excluded.description;
```

#### Step 2.2: ⚠️ CRITICAL - Watermark Migration (Addresses Issue #1)
Create dedicated watermark seeded to 14-30 days back (NOT copying from manual-sync):
```sql
-- Create new watermark for unified sync (seed to 30 days back for safety)
INSERT INTO sync_watermark (workflow_name, last_sync_timestamp)
VALUES ('shipstation-sync', datetime('now', '-30 days'))
ON CONFLICT(workflow_name) DO NOTHING;

-- Document: This ensures we capture status updates for all recent orders
-- One-time backfill will process last 30 days of orders
```

#### Step 2.3: Add Exclusive Lock Mechanism (Addresses Issue #2)
Add run ID tracking and locking to prevent concurrent executions:
```python
# In shipstation_sync.py
def acquire_sync_lock(conn, run_id: str) -> bool:
    """Acquire exclusive lock for this sync run. Returns True if acquired."""
    try:
        conn.execute("""
            INSERT INTO sync_locks (workflow_name, run_id, acquired_at)
            VALUES ('shipstation-sync', ?, CURRENT_TIMESTAMP)
        """, (run_id,))
        return True
    except:
        # Lock already held
        return False

def release_sync_lock(conn, run_id: str):
    """Release the sync lock."""
    conn.execute("""
        DELETE FROM sync_locks 
        WHERE workflow_name = 'shipstation-sync' AND run_id = ?
    """, (run_id,))

# In run_shipstation_sync():
run_id = str(uuid.uuid4())
with transaction_with_retry() as conn:
    if not acquire_sync_lock(conn, run_id):
        logger.warning("Another sync is running, skipping this cycle")
        return {"message": "Locked by another run"}, 200
    
    try:
        # ... process orders ...
        
        # Update watermark ONLY on success
        if max_modify_date and all_processed_successfully:
            update_sync_watermark(max_modify_date)
    finally:
        release_sync_lock(conn, run_id)
```

#### Step 2.4: Create Workflow Runner Script (SHADOW MODE - Addresses Issue #4)
```bash
# In start_all.sh - KEEP OLD WORKFLOWS RUNNING
# Existing workflows (KEEP ENABLED during shadow mode)
sleep 120; while true; do python src/shipstation_status_sync.py; sleep 300; done &
sleep 180; while true; do python src/manual_shipstation_sync.py; sleep 300; done &

# NEW unified workflow (SHADOW MODE - runs in parallel, every 10 min initially)
while true; do python src/shipstation_sync.py; sleep 600; done &
```

### Phase 3: Shadow Mode Validation (Days 1-3) - REVISED APPROACH

#### Step 3.1: Deploy in Shadow Mode (Day 1-2)
**Goal:** Run unified sync in PARALLEL with old workflows to validate behavior

1. **Enable unified sync** (already running from Step 2.4)
2. **Monitor both systems** for 48 hours
3. **Compare results:**
   ```sql
   -- Check for data parity
   SELECT 
       COUNT(*) as unified_imports,
       (SELECT COUNT(*) FROM orders_inbox WHERE source_system = 'ShipStation Manual' 
        AND created_at > datetime('now', '-2 days')) as manual_sync_imports
   FROM orders_inbox 
   WHERE source_system = 'ShipStation Manual' 
   AND created_at > datetime('now', '-2 days');
   
   -- Verify status updates match
   SELECT order_number, status, shipping_carrier_code, tracking_number
   FROM orders_inbox 
   WHERE updated_at > datetime('now', '-2 days')
   ORDER BY updated_at DESC;
   ```

4. **Log discrepancies** - any order handled differently between systems

#### Step 3.2: Validation Checklist (Day 3)
**Verify 100% parity before cutover:**
- [ ] Manual orders: unified imports match manual-sync imports
- [ ] Status updates: unified updates match status-sync updates
- [ ] Shipped orders: same orders moved to shipped_orders/shipped_items
- [ ] Carrier/service data: all fields populated correctly
- [ ] Watermark advancement: progresses on each successful run
- [ ] Lock mechanism: prevents concurrent executions
- [ ] Performance: unified sync completes within time window (10 min)

#### Step 3.3: Cutover (Day 4) - ONLY AFTER VALIDATION
**Prerequisites:** 48 hours of 100% parity validation

1. **Disable old workflows:**
   ```sql
   UPDATE workflow_controls SET enabled = 0 
   WHERE workflow_name IN ('status-sync', 'manual-order-sync');
   ```

2. **Update start_all.sh** (remove old workflows):
   ```bash
   # Remove these lines:
   # sleep 120; while true; do python src/shipstation_status_sync.py; sleep 300; done &
   # sleep 180; while true; do python src/manual_shipstation_sync.py; sleep 300; done &
   
   # Reduce unified sync interval to 5 min (after measuring runtime)
   while true; do python src/shipstation_sync.py; sleep 300; done &
   ```

3. **Monitor for 24 hours** - watch for any issues

4. **Archive old files** (ONLY after 24 hours of stable operation):
   ```bash
   mkdir -p archive/deprecated_syncs
   mv src/shipstation_status_sync.py archive/deprecated_syncs/
   mv src/manual_shipstation_sync.py archive/deprecated_syncs/
   ```

#### Step 3.4: Emergency Rollback Procedure
**If issues detected at ANY point:**

1. **Immediate:** Disable unified sync
   ```sql
   UPDATE workflow_controls SET enabled = 0 WHERE workflow_name = 'shipstation-sync';
   ```

2. **Re-enable old workflows:**
   ```sql
   UPDATE workflow_controls SET enabled = 1 
   WHERE workflow_name IN ('status-sync', 'manual-order-sync');
   ```

3. **Restart services:** `bash start_all.sh`

4. **Investigate** discrepancies in logs before attempting again

### Phase 4: Comprehensive Testing (Days 1-4) - EXPANDED COVERAGE (Addresses Issue #5)

#### Original Test Cases
1. **Manual Order Import (New)**
   - Create order in ShipStation with order # starting with "10"
   - Include key product SKU (17612)
   - Wait for sync (5 min)
   - Verify order appears in `orders_inbox` with source_system='ShipStation Manual'

2. **Manual Order Import (Existing - Update)**
   - Modify existing manual order in ShipStation
   - Wait for sync
   - Verify order updated in `orders_inbox`

3. **Status Update (Existing Order)**
   - Ship an order in ShipStation (from XML import)
   - Wait for sync
   - Verify status updated to 'shipped' in `orders_inbox`
   - Verify carrier/service/tracking populated

4. **Shipped Manual Order**
   - Create and ship manual order in ShipStation
   - Wait for sync
   - Verify entry in `shipped_orders` and `shipped_items`

5. **Watermark Progression**
   - Note watermark timestamp before sync
   - Run sync
   - Verify watermark advanced to latest modifyDate

6. **Duplicate Prevention**
   - Import same manual order twice
   - Verify no duplicates in database (UPSERT behavior)

7. **Filter Logic**
   - Create order without key SKUs → should skip
   - Create order not starting with "10" → should go to status update path
   - Create order from local system → should skip manual import

#### 🔴 CRITICAL - Additional Test Cases (Issue #5)

8. **API Failure Scenarios**
   - Simulate ShipStation 500 error → verify retry logic works, watermark NOT advanced
   - Simulate network timeout → verify graceful failure, no partial updates
   - Simulate rate limit (429) → verify exponential backoff, resume on next cycle

9. **Watermark Integrity Tests**
   - Run completes successfully → verify watermark advances to max(modifyDate)
   - Kill process mid-run → verify watermark UNCHANGED (no advancement)
   - Attempt concurrent runs → verify only one succeeds (exclusive lock works)
   - Corrupt watermark → verify fallback to 30-day default

10. **Concurrency & Duplicate Handling**
    - Import same order twice in same sync → verify latest update wins, no duplicates
    - Parallel execution attempt → verify second run waits or skips (lock mechanism)
    - Order imported then immediately status updated → verify no duplication, data consistent

11. **⚠️ Data Parity Validation (CRITICAL - Issue #3)**
    - Ship an order via status-sync → compare with unified sync result
    - Verify ALL fields match: status, carrier_code, carrier_id, service_code, service_name, tracking_number
    - Verify shipped order in `shipped_orders` table with ship_date, order_number, shipstation_order_id
    - Verify items in `shipped_items` table with ship_date, sku_lot, base_sku, quantity, order_number
    - **PASS CRITERIA:** 100% field-level match between old and new workflows

12. **Shipped Order Migration Test (Issue #3)**
    - Create manual order in ShipStation, ship it immediately
    - Unified sync imports order
    - Verify in `orders_inbox`: status='shipped', carrier/service data populated
    - Verify in `shipped_orders`: entry created with correct ship_date
    - Verify in `shipped_items`: all items with SKU-lot format preserved

---

## Database Schema Impact

### ⚠️ New Table Required: sync_locks
```sql
CREATE TABLE IF NOT EXISTS sync_locks (
    workflow_name TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Existing Tables (No Changes Required ✅)

### No Schema Changes Required ✅
All existing tables support the unified workflow:
- `orders_inbox` - has all necessary columns
- `order_items_inbox` - unchanged
- `shipped_orders` - unchanged
- `shipped_items` - unchanged
- `sync_watermark` - just change workflow_name

### Watermark Migration
```sql
-- Copy existing watermark if exists
INSERT INTO sync_watermark (workflow_name, last_sync_timestamp)
SELECT 'shipstation-sync', MAX(last_sync_timestamp)
FROM sync_watermark
WHERE workflow_name IN ('manual_shipstation_sync', 'status_sync')
ON CONFLICT(workflow_name) DO UPDATE SET last_sync_timestamp = excluded.last_sync_timestamp;
```

---

## Error Handling & Edge Cases

### 1. API Rate Limits
- **Strategy:** Existing `make_api_request()` has exponential backoff
- **Mitigation:** 5-minute interval provides natural rate limiting

### 2. Watermark Corruption
- **Problem:** If watermark deleted/corrupted, could re-process old orders
- **Mitigation:** 
  - Use UPSERT logic (no duplicates)
  - Default to 30 days back if watermark missing
  - Log warning when watermark reset

### 3. Partial Batch Failures
- **Strategy:** Use single transaction for entire batch
- **Mitigation:** If batch fails, rollback all changes and retry next cycle

### 4. Order Number Conflicts
- **Problem:** Same order_number from different sources
- **Current Behavior:** Uses order_number as natural key (will update existing)
- **Mitigation:** Add source_system check in conflict resolution

### 5. Missing Carrier Information
- **Problem:** ShipStation may not always provide carrier/service data
- **Mitigation:** Allow NULL values, log warnings for monitoring

### 6. Lot Number Parsing
- **Problem:** Manual orders may have different SKU-lot formats
- **Current Logic:** Splits on " - " pattern
- **Mitigation:** Validate format, log unparseable SKUs

---

## Performance Considerations

### API Efficiency Gains
| Metric | Current (2 workflows) | Unified | Improvement |
|--------|----------------------|---------|-------------|
| API calls/hour | 2 | 1 | **50% reduction** |
| Orders fetched/hour | 7-day window (~1000s) + watermark | Watermark only (~100s) | **90% reduction** |
| Processing time | 2 x 30s = 60s | 30s | **50% faster** |

### Database Efficiency
- **Batch operations:** Single transaction for all updates
- **Index usage:** Existing indexes on `shipstation_order_id`, `order_number`
- **Connection pooling:** Reuses single connection for batch

### Scalability
- **Current load:** ~100 orders/day
- **Projected capacity:** 10,000 orders/day with 5-min sync
- **Bottleneck:** ShipStation API rate limit (40 req/min)

---

## Rollback Plan

### If Issues Arise
1. **Immediate:** Disable unified workflow
   ```sql
   UPDATE workflow_controls SET enabled = 0 WHERE workflow_name = 'shipstation-sync';
   ```

2. **Restore old workflows:**
   ```bash
   cp archive/deprecated_syncs/shipstation_status_sync.py src/
   cp archive/deprecated_syncs/manual_shipstation_sync.py src/
   ```

3. **Re-enable old workflows:**
   ```sql
   UPDATE workflow_controls SET enabled = 1 WHERE workflow_name IN ('status-sync', 'manual-order-sync');
   ```

4. **Restart services:**
   ```bash
   bash start_all.sh
   ```

### Data Integrity
- **No data loss risk:** Unified workflow only adds/updates, never deletes
- **Watermark safety:** Old watermarks preserved
- **Idempotent operations:** Can safely re-run imports

---

## Monitoring & Observability

### Logging Strategy
```python
logger.info(f"=== ShipStation Sync Started ===")
logger.info(f"Fetched {len(orders)} orders since {last_sync}")
logger.info(f"Manual orders imported: {manual_imported}")
logger.info(f"Status updates: {status_updated}")
logger.info(f"Watermark advanced: {last_sync} → {max_modify_date}")
logger.info(f"=== Sync Complete in {elapsed}s ===")
```

### Dashboard Integration
Update `index.html` to show:
- **Workflow name:** "ShipStation Sync" (instead of 2 separate)
- **Last run:** Display from `workflow_controls.last_run_at`
- **Records processed:** Show `manual_imported + status_updated`

### Alerts
- Warn if sync duration > 60 seconds
- Alert if watermark hasn't advanced in 2 hours
- Error if API credentials missing

---

## Risk Assessment

### High Risk ⚠️
None identified. Changes are additive and reversible.

### Medium Risk ⚡
1. **Watermark logic bug** → Could skip orders
   - **Mitigation:** Comprehensive testing, watermark validation
   
2. **Order routing error** → Wrong path (manual vs status)
   - **Mitigation:** Clear conditional logic, extensive logging

### Low Risk ✅
1. **Performance regression** → Slower than current
   - **Likelihood:** Very low (fewer API calls = faster)
   - **Mitigation:** Performance benchmarking before/after

2. **Duplicate imports** → Same order imported twice
   - **Likelihood:** Very low (UPSERT on order_number)
   - **Mitigation:** Unique constraints prevent duplicates

---

## Success Metrics

### Technical Metrics
- ✅ API calls reduced by 50%
- ✅ Sync latency reduced by 50%
- ✅ Single workflow instead of 2
- ✅ Watermark-based efficiency for all orders

### Business Metrics
- ✅ Manual orders detected within 5 minutes (vs 60 min)
- ✅ Status updates within 5 minutes (vs 60 min)
- ✅ Reduced ShipStation API costs
- ✅ Simplified monitoring/maintenance

---

## Timeline - REVISED (Shadow Mode Deployment)

| Phase | Duration | Tasks | Status Gates |
|-------|----------|-------|--------------|
| **Phase 1: Development** | 4 hours | • Create unified workflow with locking<br>• Implement routing logic<br>• Add watermark protection<br>• Create sync_locks table | Code review ✅ |
| **Phase 2: Configuration** | 2 hours | • Register workflow<br>• Seed watermark (30 days back)<br>• Add lock mechanism<br>• Deploy in SHADOW mode (parallel) | Deploy in shadow ✅ |
| **Phase 3: Shadow Validation** | 48 hours | • Monitor both systems<br>• Compare results (SQL queries)<br>• Log discrepancies<br>• Verify parity | 100% parity ✅ |
| **Phase 4: Testing** | 6 hours | • Run original tests (1-7)<br>• Run critical tests (8-12)<br>• API failure scenarios<br>• Watermark integrity<br>• Data parity validation | All tests pass ✅ |
| **Phase 5: Cutover** | 1 hour | • Disable old workflows<br>• Remove from start_all.sh<br>• Monitor for 24 hours | 24h stable ✅ |
| **Phase 6: Cleanup** | 30 min | • Archive old files<br>• Update documentation<br>• Remove old watermarks | Complete ✅ |
| **Total** | **~4 business days** | **With 48h validation period** | |

### Critical Checkpoints
- ✋ **STOP before Phase 3:** Code must pass architect review
- ✋ **STOP before Phase 5:** Must have 100% data parity for 48 hours
- ✋ **STOP before Phase 6:** Must have 24 hours of stable operation

---

## Physical Inventory Controls & Reporting Strategy

### Overview
Replace time-based weekly/monthly automations with **user-driven button triggers** that eliminate edge cases from variable shipping completion times. Shipping completion varies daily (~1pm typical but not always), making manual triggers the most reliable approach.

### Problem Statement
- Shipping completion time varies (not always 1pm)
- Physical count verification needs **accurate, on-demand data**
- Weekly inventory reports needed at end of week
- Monthly charge reports needed at end of month
- Time-based automation creates edge case failures

### Solution: 3-Button System (EOD / EOW / EOM)

#### System Architecture

```
ALWAYS RUNNING (Background - Every 5 min):
├── XML Import → New X-Cart orders
├── ShipStation Upload → Pending orders to ShipStation  
└── Unified ShipStation Sync → Status updates + manual orders

ON-DEMAND TRIGGERS (Button-Based):
├── 📦 EOD (End of Day) → Physical count verification
├── 📊 EOW (End of Week) → Weekly inventory report
└── 💰 EOM (End of Month) → Monthly charge report
```

---

### 📦 EOD Button - Daily Physical Count Check

**Purpose:** Sync all shipped orders and refresh inventory for physical count verification

**Trigger:** Clicked when shipping complete (~1pm typically, but flexible)

**Workflow:**
```
Step 1: Force ShipStation Sync
        • Fetch latest order statuses (use unified sync)
        • Detect all shipped orders TODAY
        • Update orders_inbox with carrier/tracking data
        ↓
Step 2: Move Shipped to History
        • Transfer shipped orders to shipped_orders table
        • Create shipped_items records (with SKU-lot)
        • Include today's shipments
        ↓
Step 3: Refresh Current Inventory
        • Recalculate inventory_current table
        • Update quantities based on shipments
        • Update alert levels (critical/low/normal)
        ↓
Step 4: Display Summary
        "✅ Physical Count Ready"
        "📦 23 orders shipped today"
        "📊 47 SKUs updated"
        [View Current Inventory]
```

**API Endpoint:**
```python
@app.route('/api/sync/eod', methods=['POST'])
def end_of_day_sync():
    """Sync for physical count verification"""
    try:
        results = {
            'shipped_orders': 0,
            'skus_updated': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. Force ShipStation sync (use unified sync)
        run_shipstation_unified_sync()
        
        # 2. Move shipped orders to history
        shipped_count = move_shipped_to_history()
        results['shipped_orders'] = shipped_count
        
        # 3. Recalculate current inventory
        skus_updated = recalculate_current_inventory()
        results['skus_updated'] = skus_updated
        
        # 4. Update sync timestamp
        update_sync_timestamp('eod')
        
        return jsonify({
            'success': True,
            'message': f'Physical count ready! {shipped_count} orders shipped today.',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"EOD sync failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

### 📊 EOW Button - End of Week Report

**Purpose:** Generate weekly inventory report with rolling averages

**Trigger:** Clicked at end of week (Friday after shipping)

**Workflow:**
```
Step 1: Run EOD Sync (if not done today)
        • Ensures all today's shipments captured
        • Check last_sync_time('eod')
        • Skip if already run today
        ↓
Step 2: Aggregate Weekly History
        • Update weekly_shipped_history table
        • Calculate this week's totals per SKU
        • Archive 52-week rolling window
        ↓
Step 3: Run Weekly Reporter
        • Execute src/weekly_reporter.py
        • Calculate 52-week rolling averages
        • Update inventory projections
        • Calculate days of inventory remaining
        ↓
Step 4: Generate & Email Report
        • Save to inventory_current
        • Send weekly inventory email (SendGrid)
        • Archive for records
        ↓
Display:
        "✅ Weekly Report Generated"
        "📧 Email sent to team"
        [View Weekly Report] [Download PDF]
```

**API Endpoint:**
```python
@app.route('/api/sync/eow', methods=['POST'])
def end_of_week_sync():
    """Generate weekly inventory report"""
    try:
        results = {
            'eod_run': False,
            'weekly_history_updated': False,
            'report_generated': False,
            'email_sent': False
        }
        
        # 1. Check if EOD already run today
        last_eod = get_last_sync_time('eod')
        if not is_today(last_eod):
            logger.info("Running EOD first...")
            end_of_day_sync()
            results['eod_run'] = True
        
        # 2. Aggregate weekly shipped history
        aggregate_weekly_history()
        results['weekly_history_updated'] = True
        
        # 3. Run weekly reporter
        from src.weekly_reporter import generate_weekly_inventory_report
        generate_weekly_inventory_report()
        results['report_generated'] = True
        
        # 4. Send email (optional)
        if settings.ENABLE_EMAIL_NOTIFICATIONS:
            send_weekly_report_email()
            results['email_sent'] = True
        
        # 5. Update sync timestamp
        update_sync_timestamp('eow')
        
        return jsonify({
            'success': True,
            'message': 'Weekly report generated successfully!',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"EOW sync failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

### 💰 EOM Button - End of Month Charge Report

**Purpose:** Generate monthly ShipStation charge report

**Trigger:** Clicked at end of month (last day after shipping)

**Workflow:**
```
Step 1: Run EOW Sync (if not done this week)
        • Ensures all week's data captured
        • Check last_sync_time('eow')
        • Skip if already run this week
        ↓
Step 2: Calculate Monthly Charges
        • Query shipped_orders for current month
        • Aggregate ShipStation costs
        • Calculate carrier breakdown
        • Calculate daily totals
        ↓
Step 3: Generate Charge Report
        • Daily breakdown (orders, packages, costs)
        • Monthly totals and summaries
        • Carrier analysis (FedEx, USPS, etc.)
        • Update charge_report database
        ↓
Step 4: Email & Archive
        • Send monthly charge summary (SendGrid)
        • Save to database for history
        • Generate PDF invoice (optional)
        ↓
Display:
        "✅ Monthly Charge Report Complete"
        "💰 Total: $X,XXX.XX"
        "📧 Report emailed"
        [View Charge Report] [Download Invoice]
```

**API Endpoint:**
```python
@app.route('/api/sync/eom', methods=['POST'])
def end_of_month_sync():
    """Generate monthly charge report"""
    try:
        results = {
            'eow_run': False,
            'charges_calculated': False,
            'report_generated': False,
            'total_charges': 0,
            'email_sent': False
        }
        
        # 1. Check if EOW already run this week
        last_eow = get_last_sync_time('eow')
        if not is_this_week(last_eow):
            logger.info("Running EOW first...")
            end_of_week_sync()
            results['eow_run'] = True
        
        # 2. Calculate monthly charges
        from src.services.reporting_logic.monthly_report_generator import generate_monthly_report
        charges = calculate_monthly_charges()
        results['charges_calculated'] = True
        results['total_charges'] = charges['total']
        
        # 3. Generate charge report
        generate_monthly_report()
        results['report_generated'] = True
        
        # 4. Send email (optional)
        if settings.ENABLE_EMAIL_NOTIFICATIONS:
            send_monthly_charge_email(charges)
            results['email_sent'] = True
        
        # 5. Update sync timestamp
        update_sync_timestamp('eom')
        
        return jsonify({
            'success': True,
            'message': f"Monthly report complete! Total: ${charges['total']:,.2f}",
            'results': results
        })
        
    except Exception as e:
        logger.error(f"EOM sync failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

### Smart Dependency Management

Each button checks if prerequisite syncs have been run:

```python
def get_last_sync_time(sync_type):
    """Get timestamp of last sync for given type (eod/eow/eom)"""
    row = execute_query("""
        SELECT last_sync_timestamp 
        FROM sync_tracking 
        WHERE sync_type = ?
    """, (sync_type,))
    return row[0][0] if row else None

def is_today(timestamp):
    """Check if timestamp is from today"""
    if not timestamp:
        return False
    sync_date = datetime.fromisoformat(timestamp).date()
    return sync_date == datetime.now().date()

def is_this_week(timestamp):
    """Check if timestamp is from this week"""
    if not timestamp:
        return False
    sync_date = datetime.fromisoformat(timestamp).date()
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    return sync_date >= week_start
```

---

### 🔴 CRITICAL: Concurrency & Reliability Fixes (Architect Review)

#### Issue #1: Shared Orchestration Layer with Exclusive Locking

**Problem:** EOD/EOW/EOM buttons can run concurrently with scheduled unified sync, causing watermark corruption and duplicate processing.

**Solution:** Single global lock for ALL sync entry points.

```python
# New: src/services/sync_orchestrator.py
import uuid
import logging
from datetime import datetime, timedelta
from src.services.database.db_utils import execute_query, transaction

logger = logging.getLogger('sync_orchestrator')

class SyncOrchestrator:
    """
    Shared orchestration layer ensuring exclusive sync execution.
    Used by BOTH scheduled syncs and button-triggered workflows.
    """
    
    LOCK_TIMEOUT_MINUTES = 30  # Max time a lock can be held
    
    @staticmethod
    def acquire_lock(workflow_name):
        """Acquire exclusive lock for sync workflow"""
        run_id = str(uuid.uuid4())
        
        with transaction() as conn:
            # Check for existing lock
            existing = conn.execute("""
                SELECT run_id, acquired_at 
                FROM sync_locks 
                WHERE workflow_name = ?
            """, (workflow_name,)).fetchone()
            
            if existing:
                run_id_existing, acquired_at = existing
                lock_age = datetime.now() - datetime.fromisoformat(acquired_at)
                
                # If lock older than timeout, force release (dead process)
                if lock_age > timedelta(minutes=SyncOrchestrator.LOCK_TIMEOUT_MINUTES):
                    logger.warning(f"Releasing stale lock for {workflow_name} (age: {lock_age})")
                    conn.execute("DELETE FROM sync_locks WHERE workflow_name = ?", (workflow_name,))
                else:
                    logger.info(f"Lock held by {run_id_existing}, cannot acquire")
                    return None
            
            # Acquire lock
            conn.execute("""
                INSERT INTO sync_locks (workflow_name, run_id, acquired_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(workflow_name) DO UPDATE SET
                    run_id = excluded.run_id,
                    acquired_at = CURRENT_TIMESTAMP
            """, (workflow_name, run_id))
            
            logger.info(f"Lock acquired: {workflow_name} (run_id: {run_id})")
            return run_id
    
    @staticmethod
    def release_lock(workflow_name, run_id):
        """Release lock only if we own it"""
        with transaction() as conn:
            result = conn.execute("""
                DELETE FROM sync_locks 
                WHERE workflow_name = ? AND run_id = ?
            """, (workflow_name, run_id))
            
            if result.rowcount > 0:
                logger.info(f"Lock released: {workflow_name} (run_id: {run_id})")
                return True
            else:
                logger.warning(f"Could not release lock (not owner): {workflow_name}")
                return False
    
    @staticmethod
    def execute_with_lock(workflow_name, func, *args, **kwargs):
        """Execute function with exclusive lock"""
        run_id = SyncOrchestrator.acquire_lock(workflow_name)
        
        if not run_id:
            return {
                'success': False,
                'error': 'Another sync is already running. Please wait.',
                'status': 'locked'
            }
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            raise
        finally:
            SyncOrchestrator.release_lock(workflow_name, run_id)

# Usage in unified sync
def run_unified_sync():
    return SyncOrchestrator.execute_with_lock(
        'shipstation-sync',
        _do_unified_sync_work
    )

# Usage in EOD button
def run_eod_button():
    return SyncOrchestrator.execute_with_lock(
        'shipstation-sync',  # SAME LOCK as unified sync
        _do_eod_sync_work
    )
```

---

#### Issue #2: Background Job Queue with Single-Job Constraint

**Problem:** Synchronous Flask endpoints timeout on long-running jobs. Users can accidentally queue multiple jobs.

**Solution:** Async job queue with ONE job per sync type limit.

```python
# New: src/services/job_queue.py
import uuid
import json
from datetime import datetime
from enum import Enum
from src.services.database.db_utils import execute_query, transaction

class JobStatus(Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class JobQueue:
    """SQLite-based job queue for async processing"""
    
    @staticmethod
    def create_tables():
        """Initialize job queue tables"""
        with transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_queue (
                    job_id TEXT PRIMARY KEY,
                    sync_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    progress INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    current_step TEXT,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    completed_at TEXT,
                    UNIQUE(sync_type, status) WHERE status IN ('queued', 'running')
                )
            """)
    
    @staticmethod
    def enqueue(sync_type):
        """
        Queue a sync job. 
        Returns job_id if queued, or existing job info if already queued/running.
        """
        with transaction() as conn:
            # Check for existing job (queued or running)
            existing = conn.execute("""
                SELECT job_id, status, created_at 
                FROM job_queue 
                WHERE sync_type = ? AND status IN ('queued', 'running')
                ORDER BY created_at DESC
                LIMIT 1
            """, (sync_type,)).fetchone()
            
            if existing:
                job_id, status, created_at = existing
                return {
                    'success': False,
                    'already_queued': True,
                    'job_id': job_id,
                    'status': status,
                    'message': f'{sync_type.upper()} sync already {status}. Please wait for it to complete.'
                }
            
            # Queue new job
            job_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO job_queue (job_id, sync_type, status)
                VALUES (?, ?, 'queued')
            """, (job_id, sync_type))
            
            return {
                'success': True,
                'job_id': job_id,
                'status': 'queued',
                'message': f'{sync_type.upper()} sync queued successfully.'
            }
    
    @staticmethod
    def get_status(job_id):
        """Get job status and progress"""
        row = execute_query("""
            SELECT job_id, sync_type, status, progress, total_steps, 
                   current_step, result, error, created_at, started_at, completed_at
            FROM job_queue
            WHERE job_id = ?
        """, (job_id,))
        
        if not row:
            return None
        
        job = row[0]
        return {
            'job_id': job[0],
            'sync_type': job[1],
            'status': job[2],
            'progress': job[3],
            'total_steps': job[4],
            'current_step': job[5],
            'result': json.loads(job[6]) if job[6] else None,
            'error': job[7],
            'created_at': job[8],
            'started_at': job[9],
            'completed_at': job[10]
        }
    
    @staticmethod
    def update_progress(job_id, progress, total_steps, current_step):
        """Update job progress"""
        with transaction() as conn:
            conn.execute("""
                UPDATE job_queue
                SET progress = ?, total_steps = ?, current_step = ?
                WHERE job_id = ?
            """, (progress, total_steps, current_step, job_id))
    
    @staticmethod
    def mark_running(job_id):
        """Mark job as running"""
        with transaction() as conn:
            conn.execute("""
                UPDATE job_queue
                SET status = 'running', started_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (job_id,))
    
    @staticmethod
    def mark_completed(job_id, result):
        """Mark job as completed"""
        with transaction() as conn:
            conn.execute("""
                UPDATE job_queue
                SET status = 'completed', 
                    result = ?,
                    progress = total_steps,
                    completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (json.dumps(result), job_id))
    
    @staticmethod
    def mark_failed(job_id, error):
        """Mark job as failed"""
        with transaction() as conn:
            conn.execute("""
                UPDATE job_queue
                SET status = 'failed', 
                    error = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (str(error), job_id))

# Flask API endpoints
@app.route('/api/sync/eod', methods=['POST'])
def end_of_day_sync():
    """Queue EOD job - returns immediately"""
    result = JobQueue.enqueue('eod')
    
    if result['already_queued']:
        return jsonify(result), 409  # Conflict status
    
    # Start background processing (in separate thread/process)
    import threading
    threading.Thread(target=process_eod_job, args=(result['job_id'],)).start()
    
    return jsonify(result), 202  # Accepted

@app.route('/api/job-status/<job_id>')
def get_job_status(job_id):
    """Poll job status"""
    status = JobQueue.get_status(job_id)
    
    if not status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(status)
```

---

#### Issue #3: Checkpointed Dependency Chain with Rollback

**Problem:** EOW/EOM auto-trigger fails with no rollback. Partial state left if later step fails.

**Solution:** State machine with checkpoint/resume capability.

```python
# New: src/services/workflow_chain.py
from enum import Enum
from src.services.database.db_utils import execute_query, transaction
import logging

logger = logging.getLogger('workflow_chain')

class WorkflowStage(Enum):
    NOT_STARTED = 0
    EOD_COMPLETE = 1
    WEEKLY_HISTORY_AGGREGATED = 2
    WEEKLY_REPORT_GENERATED = 3
    EMAIL_SENT = 4
    FULLY_COMPLETE = 5

class WorkflowChain:
    """
    Manages multi-step workflows with checkpointing.
    Allows resume after partial failure without re-running completed steps.
    """
    
    @staticmethod
    def create_checkpoint_table():
        """Initialize checkpoint table"""
        with transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    sync_type TEXT PRIMARY KEY,
                    current_stage INTEGER DEFAULT 0,
                    job_id TEXT,
                    started_at TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    @staticmethod
    def get_checkpoint(sync_type):
        """Get current checkpoint for workflow"""
        row = execute_query("""
            SELECT current_stage, job_id, started_at
            FROM workflow_checkpoints
            WHERE sync_type = ?
        """, (sync_type,))
        
        if not row:
            return {'stage': 0, 'job_id': None, 'started_at': None}
        
        return {
            'stage': row[0][0],
            'job_id': row[0][1],
            'started_at': row[0][2]
        }
    
    @staticmethod
    def update_checkpoint(sync_type, stage, job_id):
        """Update checkpoint after stage completion"""
        with transaction() as conn:
            conn.execute("""
                INSERT INTO workflow_checkpoints (sync_type, current_stage, job_id, started_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(sync_type) DO UPDATE SET
                    current_stage = excluded.current_stage,
                    updated_at = CURRENT_TIMESTAMP
            """, (sync_type, stage, job_id))
        
        logger.info(f"Checkpoint updated: {sync_type} -> Stage {stage}")
    
    @staticmethod
    def clear_checkpoint(sync_type):
        """Clear checkpoint after full completion"""
        with transaction() as conn:
            conn.execute("DELETE FROM workflow_checkpoints WHERE sync_type = ?", (sync_type,))
        
        logger.info(f"Checkpoint cleared: {sync_type}")
    
    @staticmethod
    def execute_eow_with_checkpoints(job_id):
        """Execute EOW workflow with checkpoint/resume"""
        checkpoint = WorkflowChain.get_checkpoint('eow')
        results = {}
        
        try:
            # Stage 1: EOD Sync (if needed)
            if checkpoint['stage'] < WorkflowStage.EOD_COMPLETE.value:
                JobQueue.update_progress(job_id, 1, 4, 'Running EOD sync...')
                
                last_eod = get_last_sync_time('eod')
                if not is_today(last_eod):
                    logger.info("EOW: Running EOD first...")
                    eod_result = run_eod_sync_internal()
                    results['eod_run'] = True
                    results['eod_result'] = eod_result
                else:
                    logger.info("EOW: EOD already run today, skipping")
                    results['eod_run'] = False
                
                WorkflowChain.update_checkpoint('eow', WorkflowStage.EOD_COMPLETE.value, job_id)
            
            # Stage 2: Aggregate Weekly History
            if checkpoint['stage'] < WorkflowStage.WEEKLY_HISTORY_AGGREGATED.value:
                JobQueue.update_progress(job_id, 2, 4, 'Aggregating weekly history...')
                
                aggregate_weekly_history()
                results['weekly_history_updated'] = True
                
                WorkflowChain.update_checkpoint('eow', WorkflowStage.WEEKLY_HISTORY_AGGREGATED.value, job_id)
            
            # Stage 3: Generate Weekly Report
            if checkpoint['stage'] < WorkflowStage.WEEKLY_REPORT_GENERATED.value:
                JobQueue.update_progress(job_id, 3, 4, 'Generating weekly report...')
                
                from src.weekly_reporter import generate_weekly_inventory_report
                generate_weekly_inventory_report()
                results['report_generated'] = True
                
                WorkflowChain.update_checkpoint('eow', WorkflowStage.WEEKLY_REPORT_GENERATED.value, job_id)
            
            # Stage 4: Send Email (optional)
            if checkpoint['stage'] < WorkflowStage.EMAIL_SENT.value:
                JobQueue.update_progress(job_id, 4, 4, 'Sending email...')
                
                if settings.ENABLE_EMAIL_NOTIFICATIONS:
                    send_weekly_report_email()
                    results['email_sent'] = True
                else:
                    results['email_sent'] = False
                
                WorkflowChain.update_checkpoint('eow', WorkflowStage.EMAIL_SENT.value, job_id)
            
            # All stages complete - clear checkpoint
            WorkflowChain.clear_checkpoint('eow')
            update_sync_timestamp('eow')
            
            JobQueue.mark_completed(job_id, results)
            return results
            
        except Exception as e:
            logger.error(f"EOW workflow failed at stage {checkpoint['stage']}: {e}", exc_info=True)
            JobQueue.mark_failed(job_id, str(e))
            # Checkpoint remains - can resume on retry
            raise
```

---

#### Issue #4: Automated Parity Validation for Shadow Mode

**Problem:** Manual SQL spot-checks are error-prone. No codified success criteria.

**Solution:** Automated reconciliation script with field-level comparison.

```python
# New: src/validation/shadow_mode_validator.py
import logging
from datetime import datetime, timedelta
from src.services.database.db_utils import execute_query

logger = logging.getLogger('shadow_validator')

class ShadowModeValidator:
    """Automated validation comparing legacy vs unified sync outputs"""
    
    @staticmethod
    def validate_parity(hours_back=2):
        """
        Compare legacy sync vs unified sync results.
        Returns True if 100% parity, raises exception if discrepancies found.
        """
        cutoff = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        report = {
            'validation_time': datetime.now().isoformat(),
            'hours_validated': hours_back,
            'orders_match': False,
            'statuses_match': False,
            'shipped_match': False,
            'discrepancies': []
        }
        
        # 1. Compare Manual Order Imports
        legacy_orders = execute_query("""
            SELECT order_number, shipstation_order_id, source_system, created_at
            FROM orders_inbox
            WHERE source_system = 'ShipStation Manual'
            AND created_at >= ?
            ORDER BY order_number
        """, (cutoff,))
        
        unified_orders = execute_query("""
            SELECT order_number, shipstation_order_id, source_system, created_at
            FROM orders_inbox
            WHERE source_system = 'ShipStation Manual (Unified)'
            AND created_at >= ?
            ORDER BY order_number
        """, (cutoff,))
        
        if len(legacy_orders) != len(unified_orders):
            report['discrepancies'].append({
                'type': 'order_count_mismatch',
                'legacy_count': len(legacy_orders),
                'unified_count': len(unified_orders)
            })
        else:
            # Field-level comparison
            for legacy, unified in zip(legacy_orders, unified_orders):
                if legacy != unified:
                    report['discrepancies'].append({
                        'type': 'order_data_mismatch',
                        'order_number': legacy[0],
                        'legacy': legacy,
                        'unified': unified
                    })
        
        report['orders_match'] = len([d for d in report['discrepancies'] if 'order' in d['type']]) == 0
        
        # 2. Compare Status Updates
        legacy_statuses = execute_query("""
            SELECT order_number, status, shipping_carrier_code, tracking_number
            FROM orders_inbox
            WHERE updated_at >= ?
            AND source_system != 'ShipStation Manual'
            ORDER BY order_number
        """, (cutoff,))
        
        # Compare with unified sync updates (would need to tag which sync updated)
        # For now, verify no duplicates or missing updates
        
        # 3. Compare Shipped Orders/Items
        legacy_shipped = execute_query("""
            SELECT order_number, ship_date, shipstation_order_id
            FROM shipped_orders
            WHERE ship_date >= DATE('now', '-2 days')
            ORDER BY order_number
        """, ())
        
        unified_shipped = execute_query("""
            SELECT order_number, ship_date, shipstation_order_id
            FROM shipped_orders
            WHERE ship_date >= DATE('now', '-2 days')
            AND source = 'unified_sync'
            ORDER BY order_number
        """, ())
        
        report['shipped_match'] = len(legacy_shipped) == len(unified_shipped)
        
        # Final validation
        parity_achieved = (
            report['orders_match'] and 
            report['statuses_match'] and 
            report['shipped_match']
        )
        
        if parity_achieved:
            logger.info("✅ Shadow mode validation PASSED - 100% parity achieved")
            return True
        else:
            logger.error(f"❌ Shadow mode validation FAILED - Discrepancies found: {report['discrepancies']}")
            raise ValueError(f"Shadow mode parity check failed. Discrepancies: {len(report['discrepancies'])}")
```

---

### Dashboard UI Design

#### New Section: Physical Inventory Controls

```html
<!-- Physical Inventory Controls Section -->
<section class="dashboard-section">
    <div class="section-header">
        <h2 class="section-title">📊 Physical Inventory & Reporting</h2>
    </div>
    
    <div class="sync-status-bar">
        <div class="sync-status-item">
            <span class="sync-label">Last EOD:</span>
            <span class="sync-time" id="last-eod-time">Not run today</span>
        </div>
        <div class="sync-status-item">
            <span class="sync-label">Last EOW:</span>
            <span class="sync-time" id="last-eow-time">-</span>
        </div>
        <div class="sync-status-item">
            <span class="sync-label">Last EOM:</span>
            <span class="sync-time" id="last-eom-time">-</span>
        </div>
    </div>
    
    <div class="sync-buttons-grid">
        <!-- EOD Button -->
        <div class="sync-button-card">
            <div class="sync-card-icon">📦</div>
            <h3 class="sync-card-title">End of Day</h3>
            <p class="sync-card-desc">Physical Count Check</p>
            <button class="btn-sync" id="btn-eod" onclick="runEODSync()">
                Run EOD Sync
            </button>
            <div class="sync-card-help">
                Click when shipping is complete
            </div>
        </div>
        
        <!-- EOW Button -->
        <div class="sync-button-card">
            <div class="sync-card-icon">📊</div>
            <h3 class="sync-card-title">End of Week</h3>
            <p class="sync-card-desc">Weekly Inventory Report</p>
            <button class="btn-sync" id="btn-eow" onclick="runEOWSync()">
                Run EOW Sync
            </button>
            <div class="sync-card-help">
                Friday after shipping complete
            </div>
        </div>
        
        <!-- EOM Button -->
        <div class="sync-button-card">
            <div class="sync-card-icon">💰</div>
            <h3 class="sync-card-title">End of Month</h3>
            <p class="sync-card-desc">Monthly Charge Report</p>
            <button class="btn-sync" id="btn-eom" onclick="runEOMSync()">
                Run EOM Sync
            </button>
            <div class="sync-card-help">
                Last day of month
            </div>
        </div>
    </div>
    
    <!-- Quick Links -->
    <div class="sync-quick-links">
        <a href="/lot_inventory.html" class="quick-link">→ View Current Inventory</a>
        <a href="/weekly_shipped_history.html" class="quick-link">→ View Weekly Report</a>
        <a href="/charge_report.html" class="quick-link">→ View Charge Report</a>
    </div>
</section>
```

#### JavaScript for Button Interactions (with Single-Queue Constraint)

```javascript
// Global: Track active polling intervals
const activePolls = {};

async function runEODSync() {
    const btn = document.getElementById('btn-eod');
    btn.disabled = true;
    btn.textContent = 'Queueing...';
    
    try {
        // Queue the job
        const response = await fetch('/api/sync/eod', { method: 'POST' });
        const data = await response.json();
        
        if (response.status === 409) {
            // Already queued - show notification
            showWarning(
                'EOD Sync Already Running',
                `${data.message}<br><br>Current Status: <strong>${data.status}</strong>`,
                [
                    { text: 'View Progress', onclick: () => pollJobStatus(data.job_id, 'EOD') }
                ]
            );
            btn.disabled = false;
            btn.textContent = 'Run EOD Sync';
            return;
        }
        
        if (!data.success) {
            showError('Failed to queue EOD sync', data.error);
            btn.disabled = false;
            btn.textContent = 'Run EOD Sync';
            return;
        }
        
        // Successfully queued - start polling
        showInfo('EOD Sync Queued', 'Your sync has been queued and will start shortly...');
        pollJobStatus(data.job_id, 'EOD');
        
    } catch (error) {
        showError('EOD sync error', error.message);
        btn.disabled = false;
        btn.textContent = 'Run EOD Sync';
    }
}

async function pollJobStatus(jobId, syncName) {
    const btn = document.getElementById(`btn-${syncName.toLowerCase()}`);
    
    // Clear any existing poll
    if (activePolls[syncName]) {
        clearInterval(activePolls[syncName]);
    }
    
    // Poll every 2 seconds
    activePolls[syncName] = setInterval(async () => {
        try {
            const response = await fetch(`/api/job-status/${jobId}`);
            const job = await response.json();
            
            if (!job) {
                clearInterval(activePolls[syncName]);
                return;
            }
            
            // Update button text with progress
            if (job.status === 'running') {
                const percent = Math.round((job.progress / job.total_steps) * 100);
                btn.textContent = `${percent}% - ${job.current_step}`;
                
                // Update progress modal if visible
                updateProgressModal(job.current_step, job.progress, job.total_steps);
            }
            
            // Handle completion
            if (job.status === 'completed') {
                clearInterval(activePolls[syncName]);
                btn.disabled = false;
                btn.textContent = `Run ${syncName} Sync`;
                
                // Show success based on sync type
                if (syncName === 'EOD') {
                    showSuccess(
                        '✅ Physical Count Ready!',
                        `📦 ${job.result.shipped_orders} orders shipped<br>` +
                        `📊 ${job.result.skus_updated} SKUs updated`,
                        [{ text: 'View Inventory', href: '/lot_inventory.html' }]
                    );
                } else if (syncName === 'EOW') {
                    const emailMsg = job.result.email_sent ? '<br>📧 Email sent to team' : '';
                    showSuccess(
                        '✅ Weekly Report Generated!',
                        `Report ready for review${emailMsg}`,
                        [
                            { text: 'View Report', href: '/weekly_shipped_history.html' },
                            { text: 'Download PDF', href: '/api/download/weekly-report' }
                        ]
                    );
                } else if (syncName === 'EOM') {
                    const emailMsg = job.result.email_sent ? '<br>📧 Report emailed' : '';
                    showSuccess(
                        '✅ Monthly Report Complete!',
                        `💰 Total: $${job.result.total_charges.toLocaleString('en-US', {minimumFractionDigits: 2})}${emailMsg}`,
                        [
                            { text: 'View Report', href: '/charge_report.html' },
                            { text: 'Download Invoice', href: '/api/download/invoice' }
                        ]
                    );
                }
                
                updateLastSyncTime(syncName.toLowerCase(), job.completed_at);
            }
            
            // Handle failure
            if (job.status === 'failed') {
                clearInterval(activePolls[syncName]);
                btn.disabled = false;
                btn.textContent = `Run ${syncName} Sync`;
                
                showError(
                    `${syncName} Sync Failed`,
                    `Error: ${job.error}<br><br>The sync can be retried.`,
                    [
                        { text: 'Retry', onclick: () => {
                            if (syncName === 'EOD') runEODSync();
                            else if (syncName === 'EOW') runEOWSync();
                            else if (syncName === 'EOM') runEOMSync();
                        }}
                    ]
                );
            }
            
        } catch (error) {
            console.error('Polling error:', error);
            clearInterval(activePolls[syncName]);
            btn.disabled = false;
            btn.textContent = `Run ${syncName} Sync`;
        }
    }, 2000);
}

async function runEOWSync() {
    const btn = document.getElementById('btn-eow');
    btn.disabled = true;
    btn.textContent = 'Queueing...';
    
    try {
        const response = await fetch('/api/sync/eow', { method: 'POST' });
        const data = await response.json();
        
        if (response.status === 409) {
            showWarning(
                'EOW Sync Already Running',
                `${data.message}<br><br>Current Status: <strong>${data.status}</strong>`,
                [{ text: 'View Progress', onclick: () => pollJobStatus(data.job_id, 'EOW') }]
            );
            btn.disabled = false;
            btn.textContent = 'Run EOW Sync';
            return;
        }
        
        if (!data.success) {
            showError('Failed to queue EOW sync', data.error);
            btn.disabled = false;
            btn.textContent = 'Run EOW Sync';
            return;
        }
        
        showInfo('EOW Sync Queued', 'Generating weekly inventory report...');
        pollJobStatus(data.job_id, 'EOW');
        
    } catch (error) {
        showError('EOW sync error', error.message);
        btn.disabled = false;
        btn.textContent = 'Run EOW Sync';
    }
}

async function runEOMSync() {
    const btn = document.getElementById('btn-eom');
    btn.disabled = true;
    btn.textContent = 'Queueing...';
    
    try {
        const response = await fetch('/api/sync/eom', { method: 'POST' });
        const data = await response.json();
        
        if (response.status === 409) {
            showWarning(
                'EOM Sync Already Running',
                `${data.message}<br><br>Current Status: <strong>${data.status}</strong>`,
                [{ text: 'View Progress', onclick: () => pollJobStatus(data.job_id, 'EOM') }]
            );
            btn.disabled = false;
            btn.textContent = 'Run EOM Sync';
            return;
        }
        
        if (!data.success) {
            showError('Failed to queue EOM sync', data.error);
            btn.disabled = false;
            btn.textContent = 'Run EOM Sync';
            return;
        }
        
        showInfo('EOM Sync Queued', 'Generating monthly charge report...');
        pollJobStatus(data.job_id, 'EOM');
        
    } catch (error) {
        showError('EOM sync error', error.message);
        btn.disabled = false;
        btn.textContent = 'Run EOM Sync';
    }
}

// Utility: Show warning notification
function showWarning(title, message, actions = []) {
    // Similar to showSuccess/showError but with warning styling
    const modal = document.createElement('div');
    modal.className = 'notification-modal warning';
    modal.innerHTML = `
        <div class="notification-content">
            <h3>⚠️ ${title}</h3>
            <p>${message}</p>
            <div class="notification-actions">
                ${actions.map(action => 
                    `<button onclick="${action.onclick || ''}" class="btn-secondary">${action.text}</button>`
                ).join('')}
                <button onclick="this.closest('.notification-modal').remove()" class="btn-primary">OK</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}
    btn.textContent = 'Generating...';
    
    try {
        showProgress('EOW Sync', [
            'Running EOD if needed...',
            'Aggregating weekly history...',
            'Calculating rolling averages...',
            'Generating report...'
        ]);
        
        const response = await fetch('/api/sync/eow', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            const emailMsg = data.results.email_sent 
                ? '<br>📧 Email sent to team' 
                : '';
            showSuccess(
                '✅ Weekly Report Generated!',
                `Report ready for review${emailMsg}`,
                [
                    { text: 'View Report', href: '/weekly_shipped_history.html' },
                    { text: 'Download PDF', href: '/api/download/weekly-report' }
                ]
            );
            updateLastSyncTime('eow', data.results.timestamp);
        } else {
            showError('EOW sync failed', data.error);
        }
    } catch (error) {
        showError('EOW sync error', error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run EOW Sync';
    }
}

async function runEOMSync() {
    const btn = document.getElementById('btn-eom');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    
    try {
        showProgress('EOM Sync', [
            'Running EOW if needed...',
            'Calculating monthly charges...',
            'Generating charge report...',
            'Creating invoice...'
        ]);
        
        const response = await fetch('/api/sync/eom', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            const emailMsg = data.results.email_sent 
                ? '<br>📧 Report emailed' 
                : '';
            showSuccess(
                '✅ Monthly Report Complete!',
                `💰 Total: $${data.results.total_charges.toLocaleString('en-US', {minimumFractionDigits: 2})}${emailMsg}`,
                [
                    { text: 'View Report', href: '/charge_report.html' },
                    { text: 'Download Invoice', href: '/api/download/invoice' }
                ]
            );
            updateLastSyncTime('eom', data.results.timestamp);
        } else {
            showError('EOM sync failed', data.error);
        }
    } catch (error) {
        showError('EOM sync error', error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run EOM Sync';
    }
}
```

---

### Database Schema Addition

#### Sync Tracking Table

```sql
CREATE TABLE IF NOT EXISTS sync_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL UNIQUE, -- 'eod', 'eow', 'eom'
    last_sync_timestamp TEXT NOT NULL,
    records_processed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success', -- 'success', 'failed', 'running'
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial records
INSERT INTO sync_tracking (sync_type, last_sync_timestamp, status)
VALUES 
    ('eod', '1970-01-01T00:00:00', 'pending'),
    ('eow', '1970-01-01T00:00:00', 'pending'),
    ('eom', '1970-01-01T00:00:00', 'pending')
ON CONFLICT(sync_type) DO NOTHING;
```

---

### Complete Automation Schedule (Updated)

| Time/Trigger | Automation | Purpose | Type |
|--------------|------------|---------|------|
| **Every 5 min** | XML Import | Import new X-Cart orders | Auto |
| **Every 5 min** | ShipStation Upload | Upload pending orders | Auto |
| **Every 5 min** | Unified ShipStation Sync | Status + manual orders | Auto |
| **~1pm (Button)** | 📦 EOD Sync | Physical count verification | Manual |
| **Fri EOD (Button)** | 📊 EOW Sync | Weekly inventory report | Manual |
| **Last day (Button)** | 💰 EOM Sync | Monthly charge report | Manual |
| **Daily 11:59 PM** | Orders Cleanup | Delete old orders (60+ days) | Auto |

---

### Benefits of Button-Based Approach

1. ✅ **Flexible timing** - No hardcoded schedules to fail
2. ✅ **User-driven** - Shipper controls when syncs run
3. ✅ **No edge cases** - Works regardless of shipping time variation
4. ✅ **Smart dependencies** - EOW auto-runs EOD if needed, EOM auto-runs EOW if needed
5. ✅ **Clear purpose** - Each button has specific business function
6. ✅ **Progress visibility** - Shows sync steps in real-time
7. ✅ **Audit trail** - Tracks when each sync last ran
8. ✅ **Error recovery** - Can re-run if sync fails
9. ✅ **Business alignment** - Matches actual operational workflow

---

### Implementation Phases (Addition to Timeline)

| Phase | Task | Duration |
|-------|------|----------|
| **Phase 7: Physical Inventory UI** | • Add EOD/EOW/EOM buttons to dashboard<br>• Create sync_tracking table<br>• Implement API endpoints<br>• Add progress modals | 3 hours |
| **Phase 8: Dependency Logic** | • Smart EOD check in EOW<br>• Smart EOW check in EOM<br>• Timestamp tracking<br>• Error handling | 2 hours |
| **Phase 9: Testing** | • Test EOD workflow<br>• Test EOW with/without EOD<br>• Test EOM with/without EOW<br>• Verify email sending | 2 hours |
| **Total** | **Physical Inventory System** | **~7 hours (~1 day)** |

---

## Appendix A: Code Comparison

### Current Approach (Inefficient)
```python
# Status Sync (7-day window)
params = {
    'modifyDateStart': (now - 7 days),
    'modifyDateEnd': now
}
# Fetches ~1000s of orders repeatedly

# Manual Order Sync (watermark)
params = {
    'modifyDateStart': last_watermark  # More efficient
}
```

### Unified Approach (Efficient)
```python
# Single fetch with watermark
params = {
    'modifyDateStart': last_watermark
}
# Fetches only new/modified orders since last sync
```

---

## Appendix B: Workflow Comparison

### Before (2 Workflows)
```
status-sync (hourly)
  → Fetch last 7 days
  → Update status for existing orders

manual-order-sync (hourly)
  → Fetch since watermark
  → Import manual orders
```

### After (1 Workflow)
```
shipstation-sync (every 5 min)
  → Fetch since watermark
  → Route: Manual? Import : Update status
  → Advance watermark
```

---

## Conclusion

This unified approach provides:
1. **50% reduction in API calls**
2. **5-minute sync frequency** (vs 60 min)
3. **Simpler maintenance** (1 workflow vs 2)
4. **Better efficiency** (watermark for all)
5. **No schema changes** required
6. **Safe rollback** plan
7. **Comprehensive testing** strategy

**Recommendation:** ✅ **Proceed with implementation**

---

## 🔴 CRITICAL FIXES SUMMARY (Architect-Reviewed)

### Overview of Enhancements

The architect identified 4 critical gaps that have been addressed with comprehensive solutions:

#### ✅ Fix #1: Shared Orchestration Layer (Issue: Concurrent Watermark Corruption)
- **Problem:** EOD/EOW/EOM buttons could run concurrently with scheduled unified sync, advancing watermark simultaneously
- **Solution:** `SyncOrchestrator` class with exclusive locking mechanism
- **Implementation:** 
  - `src/services/sync_orchestrator.py` - Shared lock for ALL sync entry points  
  - 30-minute lock timeout for dead process recovery
  - Both scheduled and button-triggered syncs use SAME lock
- **Result:** No concurrent execution possible, watermark integrity guaranteed

#### ✅ Fix #2: Background Job Queue (Issue: Synchronous API Timeouts & Duplicate Jobs)  
- **Problem:** Long-running syncs timeout HTTP requests, users can accidentally queue duplicates
- **Solution:** SQLite-based async job queue with single-job-per-sync-type constraint
- **Implementation:**
  - `src/services/job_queue.py` - Async job processing
  - UNIQUE constraint: only ONE EOD/EOW/EOM job queued at a time
  - Flask returns HTTP 202 (Accepted) immediately, job runs in background
  - Frontend polls `/api/job-status/<job_id>` every 2 seconds
- **UX:** 
  - User clicks button → Job queued (or warning if already running)
  - Real-time progress: "75% - Updating inventory..."
  - HTTP 409 (Conflict) if job already exists → prevents duplicates

#### ✅ Fix #3: Checkpointed Dependency Chain (Issue: No Rollback on Partial Failure)
- **Problem:** If EOW runs EOD successfully but report generation fails, system left in partial state
- **Solution:** State machine with checkpoint/resume capability
- **Implementation:**
  - `src/services/workflow_chain.py` - Staged execution with checkpoints
  - `workflow_checkpoints` table tracks current stage per sync type
  - Each stage commits checkpoint before advancing
  - On failure: checkpoint remains, retry resumes from last successful stage
- **Example Recovery:**
  ```
  EOW Attempt 1:
    Stage 1: EOD Complete ✅ → Checkpoint saved
    Stage 2: Weekly History ✅ → Checkpoint saved  
    Stage 3: Report Generation ❌ → FAILS, checkpoint at Stage 2
  
  EOW Retry (automatic or manual):
    Stage 1: SKIPPED (already done)
    Stage 2: SKIPPED (already done)
    Stage 3: Retry report generation → Success ✅
  ```

#### ✅ Fix #4: Automated Parity Validation (Issue: Manual Shadow Mode Validation)
- **Problem:** Plan relied on error-prone manual SQL spot-checks for shadow mode validation
- **Solution:** Automated reconciliation script with field-level comparison
- **Implementation:**
  - `src/validation/shadow_mode_validator.py` - Automated parity checker
  - Compares legacy vs unified sync outputs across 3 dimensions:
    1. Manual order imports (count + field-level match)
    2. Status updates (carrier, tracking, etc.)
    3. Shipped orders/items (complete data parity)
  - Runs every 2 hours during shadow mode
  - Raises exception if ANY discrepancy found → blocks cutover
- **Success Criteria:** 100% parity for 48 hours before disabling legacy workflows

### New Database Tables Required

```sql
-- For exclusive locking (already exists, updated usage)
CREATE TABLE IF NOT EXISTS sync_locks (
    workflow_name TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- For async job queue (NEW)
CREATE TABLE IF NOT EXISTS job_queue (
    job_id TEXT PRIMARY KEY,
    sync_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    current_step TEXT,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    UNIQUE(sync_type, status) WHERE status IN ('queued', 'running')
);

-- For checkpointed workflows (NEW)
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    sync_type TEXT PRIMARY KEY,
    current_stage INTEGER DEFAULT 0,
    job_id TEXT,
    started_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Updated Implementation Timeline

| Phase | Duration | Tasks | Dependencies |
|-------|----------|-------|--------------|
| **Phase 1: Core Development** | 6 hours | • Build unified sync<br>• Add SyncOrchestrator<br>• Create job queue<br>• Implement checkpoints | - |
| **Phase 2: Shadow Deployment** | 2 hours | • Deploy in parallel<br>• Enable automated validation | Phase 1 ✅ |
| **Phase 3: Shadow Validation** | **48 hours** | • Monitor parity checker<br>• Compare results<br>• Log discrepancies | Phase 2 ✅ |
| **Phase 4: Testing** | 8 hours | • Run 12 test cases<br>• Test queue constraints<br>• Test checkpoint recovery | Phase 3 ✅ (100% parity) |
| **Phase 5: Physical Inventory UI** | 4 hours | • Add EOD/EOW/EOM buttons<br>• Implement polling UI<br>• Add progress modals | Phase 4 ✅ |
| **Phase 6: Cutover** | 1 hour | • Disable legacy workflows<br>• Monitor 24 hours | Phase 5 ✅ |
| **Phase 7: Cleanup** | 1 hour | • Archive old code<br>• Update docs | Phase 6 ✅ (24h stable) |
| **TOTAL** | **~6 business days** | **Includes 48h validation + 24h stability** | |

### Key Success Criteria

Before proceeding to next phase:

**Phase 3 → Phase 4:**
- ✅ Automated parity validation passing for 48 hours
- ✅ Zero discrepancies in order imports
- ✅ Zero discrepancies in status updates  
- ✅ Zero discrepancies in shipped items

**Phase 5 → Phase 6:**
- ✅ All 12 test cases passing
- ✅ Single-queue constraint verified (HTTP 409 on duplicate)
- ✅ Checkpoint recovery tested (partial failure → successful retry)
- ✅ Lock timeout recovery verified

**Phase 6 → Phase 7:**
- ✅ 24 hours of stable unified sync operation
- ✅ No watermark corruption incidents
- ✅ No duplicate processing incidents
- ✅ All EOD/EOW/EOM workflows tested in production

### Final Recommendations

1. ✅ **Use SyncOrchestrator** for ALL sync operations (scheduled + buttons)
2. ✅ **Implement job queue** before deploying buttons (prevents timeouts)
3. ✅ **Enable checkpoint system** for all dependency chains (EOW/EOM)
4. ✅ **Run automated parity validation** during entire shadow mode period
5. ✅ **Do NOT cutover** until 48 hours of 100% parity achieved

**This enhanced implementation ensures zero data corruption risk and graceful recovery from all failure scenarios.**

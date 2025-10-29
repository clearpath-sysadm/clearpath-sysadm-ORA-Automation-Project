# Ghost Order Backfill System - Implementation Action Plan

**Date:** October 29, 2025  
**Status:** Ready for Implementation  
**Priority:** Medium  
**Estimated Effort:** 2-3 hours

---

## 📋 Executive Summary

Implement an automated system to detect and fix "ghost orders" - orders that exist in `orders_inbox` but have zero items in `order_items_inbox`. This occurs when orders are manually created in ShipStation and synced to the local database without their line items.

### Problem Impact
- ✅ **Data Integrity:** Orders with 0 items contribute to count mismatches between ShipStation and local DB
- ✅ **User Experience:** Ghost orders don't appear in Orders Inbox UI but still exist in database
- ✅ **Reporting:** Incorrect order counts and unit metrics (e.g., 36 vs 37 unit discrepancy)

---

## 🔍 Root Cause Analysis

### How Ghost Orders Are Created

1. **Manual ShipStation Order Creation:**
   - User creates order directly in ShipStation (not through XML import)
   - Order bypasses the normal XML → `orders_inbox` + `order_items_inbox` flow

2. **Unified Sync Limitation:**
   - `unified_shipstation_sync.py` syncs order-level metadata (status, tracking, customer info)
   - Does NOT sync line items (SKUs, quantities, prices)
   - Result: Order shell in `orders_inbox` with no products in `order_items_inbox`

3. **Trigger Scenario:**
   - Someone manually creates/edits orders in ShipStation
   - System sees the order, creates the header, but items remain empty

### Example Ghost Order: 100528
```
orders_inbox:
  - order_number: 100528
  - status: awaiting_shipment
  - total_items: 0

order_items_inbox:
  - (no records)

ShipStation Reality:
  - order_number: 100528
  - status: shipped
  - items: 2x SKU 17612
```

---

## 🎯 Proposed Solution

### Architecture Overview

**New Module:** `src/services/ghost_order_backfill.py`  
**Integration Point:** `src/unified_shipstation_sync.py`  
**Execution Frequency:** Every 5 minutes (existing workflow cadence)

### Solution Components

#### 1. **Detection Logic**
```sql
-- Find ghost orders (0 items AND not shipped/cancelled)
-- INCLUDES on_hold orders (user confirmed - they still need accurate data)
SELECT o.id, o.order_number, o.shipstation_order_id
FROM orders_inbox o
LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
WHERE o.status NOT IN ('shipped', 'cancelled')
  AND o.shipstation_order_id IS NOT NULL  -- Skip orders without ShipStation ID
GROUP BY o.id, o.order_number, o.shipstation_order_id
HAVING COUNT(oi.id) = 0
```

#### 2. **Backfill Process**
For each ghost order:
1. Query ShipStation API: `/orders/{shipstation_order_id}`
2. Extract items array (SKU, quantity, name, price)
3. Insert into `order_items_inbox` with ON CONFLICT handling
4. Update `orders_inbox.total_items` count
5. Sync `orders_inbox.status` from ShipStation

#### 3. **Edge Case Handling**
- **Order not found (404):** Mark as `cancelled` (orphaned order)
- **Order cancelled in ShipStation:** Update local status to `cancelled`
- **Order has 0 items in ShipStation:** Keep as-is, log warning (may be work-in-progress)
- **Missing shipstation_order_id:** Skip order, log warning (cannot query ShipStation)
- **API rate limit (429):** Stop processing immediately, retry next cycle
- **API error (500):** Skip order and retry on next cycle
- **Transaction failure:** Individual order rollback (not entire batch)

---

---

## 🚨 Critical Implementation Notes

### **BLOCKER: Duplicate SKU Constraint Issue**

**Problem:** The `order_items_inbox` table has a UNIQUE constraint on `(order_inbox_id, sku)`. If a ShipStation order has the same SKU on multiple line items (e.g., different lots), only ONE line will be inserted, causing **data loss**.

**Database Constraint:**
```sql
UNIQUE (order_inbox_id, sku)
```

**Scenario:**
```
ShipStation Order 123:
  - Line 1: SKU 17612, Qty 3, Lot A
  - Line 2: SKU 17612, Qty 2, Lot B

Backfill Result:
  - Only Line 1 OR Line 2 inserted (last one wins)
  - Missing 3 or 2 units in database
```

**REQUIRED ACTION BEFORE IMPLEMENTATION:**
1. Query ShipStation to check if any orders have duplicate SKUs on multiple lines
2. If YES: Either aggregate quantities OR redesign table constraint
3. If NO: Proceed with implementation as-is, but add validation to detect and log this scenario

**Test Query (to be run during Phase 0):**
```python
# Check if any ShipStation orders have duplicate SKUs
for order in recent_orders:
    skus = [item['sku'] for item in order['items']]
    if len(skus) != len(set(skus)):
        print(f"⚠️ ALERT: Order {order['orderNumber']} has duplicate SKUs!")
```

### **Transaction Strategy: Per-Order Isolation**

**Architecture:** Each ghost order is backfilled in its own transaction, independent of others.

**Rationale:**
- One backfill failure doesn't block others
- Partial success is acceptable (3 of 5 orders backfilled is progress)
- Main sync watermark advancement is independent of backfill success

**Implementation:**
```python
def backfill_ghost_orders(main_conn) -> dict:
    """
    Main conn is READ-ONLY for detection query.
    Each order gets its own WRITE transaction.
    """
    # Read ghost orders using main connection
    ghost_orders = detect_ghost_orders(main_conn)
    
    # Process each in independent transaction
    for order in ghost_orders:
        try:
            with transaction() as order_conn:  # New transaction per order
                backfill_single_order(order, order_conn)
                # Auto-commits on success
        except Exception as e:
            # Rollback happens automatically
            # Continue to next order
            errors += 1
```

**Benefits:**
- ✅ Isolated failures (one bad order doesn't poison batch)
- ✅ Watermark can advance even if some backfills fail
- ✅ Retry failed orders on next cycle (5 min later)

### **Bundle SKU Clarification**

**USER CONFIRMED:** Bundle SKUs are NOT entered in ShipStation. Manual orders use individual SKUs only.

**Impact:** No bundle expansion logic needed in backfill. This is a non-issue.

### **On-Hold Orders**

**USER CONFIRMED:** Include `on_hold` orders in backfill. They still need accurate item data.

**Implementation:** Detection query does NOT exclude `on_hold` status.

### **Work-In-Progress Orders (0 Items)**

**USER CONFIRMED:** Do NOT auto-cancel orders with 0 items in ShipStation.

**Scenario:** User creates order shell in ShipStation, saves it, will add items later.

**Implementation:**
- Keep order as-is (don't change status)
- Log warning for visibility
- Consider adding warning system to dashboard (future enhancement)

```python
if len(items) == 0:
    logger.warning(f"⚠️ Order {order_number} has 0 items in ShipStation - may be work-in-progress")
    # Do NOT update status to cancelled
    # Do NOT insert any items
    work_in_progress_count += 1
```

**Future Enhancement:** Add dashboard alert for orders with 0 items > 24 hours old.

---

## 📐 Implementation Plan

### Phase 0: Pre-Implementation Validation (15 min)

**CRITICAL:** Test for duplicate SKU scenario before writing code.

**Test Script:**
```python
# Check recent 500 ShipStation orders for duplicate SKUs on same order
from src.services.shipstation.api_client import get_shipstation_credentials
import requests
from requests.auth import HTTPBasicAuth

api_key, api_secret = get_shipstation_credentials()
url = 'https://ssapi.shipstation.com/orders'
params = {'pageSize': 500, 'page': 1}
response = requests.get(url, auth=HTTPBasicAuth(api_key, api_secret), params=params)

if response.status_code == 200:
    orders = response.json().get('orders', [])
    for order in orders:
        skus = [item['sku'] for item in order.get('items', [])]
        if len(skus) != len(set(skus)):
            print(f"⚠️ DUPLICATE SKU ALERT: Order {order['orderNumber']} has duplicate SKUs!")
            print(f"   Items: {[(i['sku'], i['quantity']) for i in order['items']]}")
```

**Decision Point:**
- **If duplicates found:** STOP - Need to redesign constraint or aggregation logic
- **If no duplicates:** PROCEED with implementation as-is

### Phase 1: Create Standalone Module (45 min)

**File:** `src/services/ghost_order_backfill.py`

```python
def backfill_ghost_orders(read_conn) -> dict:
    """
    Detect and fix ghost orders by backfilling items from ShipStation.
    
    Uses per-order transaction isolation for fault tolerance.
    
    Args:
        read_conn: Database connection for read-only detection query
    
    Returns:
        dict: {
            'ghost_orders_found': int,
            'backfilled': int,
            'cancelled': int,
            'work_in_progress': int,
            'errors': int,
            'rate_limited': bool
        }
    """
```

**Key Features:**
- Self-contained, testable function
- Per-order transaction isolation (not batch)
- Returns metrics for logging/monitoring
- Comprehensive error handling
- ON CONFLICT safety for idempotency
- Rate limit detection and stop behavior
- NULL shipstation_order_id validation
- Work-in-progress order detection (0 items)

### Phase 2: Integrate with Unified Sync (15 min)

**File:** `src/unified_shipstation_sync.py`

Add to end of main sync loop (BEFORE watermark update):
```python
# After tracking status updates, BEFORE watermark update
from src.services.ghost_order_backfill import backfill_ghost_orders

# Backfill ghost orders (uses per-order transactions)
ghost_metrics = backfill_ghost_orders(conn)  # conn used for read-only detection
logger.info(f"👻 Ghost order backfill: {ghost_metrics['backfilled']} fixed, "
            f"{ghost_metrics['work_in_progress']} WIP, {ghost_metrics['errors']} errors")

if ghost_metrics.get('rate_limited'):
    logger.warning("⚠️ Backfill hit rate limit - remaining orders will retry next cycle")
```

**Integration Points:**
- Runs AFTER main sync processing (order status updates)
- Runs BEFORE watermark update (backfill failures don't block watermark)
- Uses main connection for read-only detection
- Creates new transactions per order for writes

### Phase 3: Testing (60 min)

#### Manual Testing
1. **Existing Ghost Order (100528):**
   - Verify function detects it
   - Confirm items are backfilled from ShipStation
   - Check status updates to 'shipped'
   - Validate total_items count = 2

2. **Create Test Ghost Order:**
   - Manually create order in ShipStation
   - Wait for unified sync to create order shell
   - Verify backfill populates items on next cycle

3. **Edge Cases:**
   - Order cancelled in ShipStation → local status updates
   - Order not found (404) → marked as cancelled
   - Order already has items → skipped (no duplicate inserts)

#### Validation Queries
```sql
-- Before backfill: Find ghost orders
SELECT order_number, total_items, status
FROM orders_inbox o
WHERE NOT EXISTS (
    SELECT 1 FROM order_items_inbox oi 
    WHERE oi.order_inbox_id = o.id
);

-- After backfill: Verify items populated
SELECT o.order_number, COUNT(oi.id) as item_count, o.total_items
FROM orders_inbox o
LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
WHERE o.order_number = '100528'
GROUP BY o.order_number, o.total_items;
```

### Phase 4: Monitoring & Validation (15 min)

1. **Check Logs:**
   - Review `/tmp/logs/unified-shipstation-sync_*.log`
   - Confirm ghost order detection and backfill
   - Verify no errors

2. **Validate Metrics:**
   - ShipStation Units vs Local DB Units should match
   - No more ghost orders in detection query

3. **UI Verification:**
   - Order 100528 should appear in Orders Inbox (if status = awaiting_shipment)
   - Or disappear if status = shipped (cleaned up by 60-day rule)

---

## 🔧 Technical Specification

### Function Signature
```python
def backfill_ghost_orders(
    read_conn: psycopg2.extensions.connection,
    api_key: str = None,
    api_secret: str = None
) -> dict:
    """
    Detect orders with 0 items and backfill from ShipStation.
    
    Uses per-order transaction isolation for fault tolerance.
    Stops immediately on rate limit (429) to preserve API quota.
    
    Args:
        read_conn: Database connection for read-only detection query
        api_key: ShipStation API key (optional, uses environment if not provided)
        api_secret: ShipStation API secret (optional, uses environment if not provided)
    
    Returns:
        dict: Metrics about backfill operation
            - ghost_orders_found: Number of ghost orders detected
            - backfilled: Number successfully backfilled with items
            - cancelled: Number marked as cancelled (404 errors)
            - work_in_progress: Number with 0 items in ShipStation
            - errors: Number of API/database errors
            - rate_limited: Boolean, True if 429 encountered
    
    Raises:
        None: All errors are caught, logged, and counted in metrics
    
    Transaction Strategy:
        - Detection query uses read_conn (read-only)
        - Each order backfill uses new transaction (write isolation)
        - Failures in one order don't affect others
    """
```

### Database Operations

#### Detection Query (Read-Only)
```python
cursor = read_conn.cursor()
cursor.execute("""
    SELECT o.id, o.order_number, o.shipstation_order_id
    FROM orders_inbox o
    LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
    WHERE o.status NOT IN ('shipped', 'cancelled')
      AND o.shipstation_order_id IS NOT NULL
    GROUP BY o.id, o.order_number, o.shipstation_order_id
    HAVING COUNT(oi.id) = 0
""")
ghost_orders = cursor.fetchall()
```

#### Insert Items (Idempotent, Per-Order Transaction)
```python
# Each order gets its own transaction
with transaction() as order_conn:
    cursor = order_conn.cursor()
    
    for item in items:
        cursor.execute("""
            INSERT INTO order_items_inbox 
            (order_inbox_id, sku, quantity, name, unit_price_cents)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (order_inbox_id, sku) 
            DO UPDATE SET 
                quantity = EXCLUDED.quantity,
                name = EXCLUDED.name,
                unit_price_cents = EXCLUDED.unit_price_cents
        """, (order_id, sku, quantity, name, price_cents))
    
    # Auto-commits on context exit
```

#### Update Order Metadata
```python
cursor.execute("""
    UPDATE orders_inbox
    SET total_items = %s,
        status = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
""", (total_items, status, order_id))
```

### API Integration

#### Fetch Order by ID
```python
url = f"https://ssapi.shipstation.com/orders/{shipstation_order_id}"
response = requests.get(
    url, 
    auth=HTTPBasicAuth(api_key, api_secret),
    timeout=10
)
```

#### Response Handling
- **200 OK:** Extract items, backfill database
- **404 Not Found:** Mark order as cancelled (orphaned order)
- **429 Rate Limit:** STOP IMMEDIATELY (set rate_limited=True, break loop)
- **500 Server Error:** Log error, skip order, continue to next
- **Timeout:** Log error, skip order, continue to next

#### Special Cases
- **0 Items in Response:** Log warning as work-in-progress, increment counter
- **NULL shipstation_order_id:** Skip during detection (WHERE clause filters these out)
- **Duplicate SKUs in Response:** Log critical warning (constraint violation risk)

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Detects all ghost orders (0 items, valid shipstation_order_id) in `orders_inbox`
- ✅ Includes on_hold orders in detection (user confirmed)
- ✅ Fetches complete order details from ShipStation
- ✅ Backfills items into `order_items_inbox`
- ✅ Updates `total_items` count accurately
- ✅ Syncs order status from ShipStation
- ✅ Handles cancelled/not-found orders gracefully
- ✅ Detects work-in-progress orders (0 items in ShipStation)
- ✅ Validates shipstation_order_id is not NULL before querying
- ✅ Stops immediately on rate limit (429)
- ✅ Runs automatically every 5 minutes
- ✅ Zero manual intervention required

### Data Integrity
- ✅ No duplicate items (ON CONFLICT handling)
- ✅ No orphaned records
- ✅ Per-order transaction isolation (partial failures acceptable)
- ✅ Preserves existing correct data
- ✅ Detects duplicate SKU constraint violations (logs critical warning)

### Monitoring
- ✅ Logs ghost order detection count
- ✅ Logs successful backfills
- ✅ Logs errors with context
- ✅ Returns metrics for dashboard integration

### Performance
- ✅ Completes in < 5 seconds for typical workload
- ✅ No impact on main sync performance
- ✅ Graceful degradation under API rate limits

---

## 🧪 Testing Plan

### Unit Tests (Optional - Manual testing sufficient for MVP)
- Test detection query returns ghost orders
- Test API call handles 200/404/500 responses
- Test database insert with ON CONFLICT
- Test metrics dictionary structure

### Integration Tests

#### Test Case 1: Backfill Order 100528
```
Precondition: Order 100528 exists with 0 items
Action: Run backfill function
Expected:
  - order_items_inbox has 2 records (SKU 17612, qty 2)
  - orders_inbox.total_items = 2
  - orders_inbox.status = 'shipped'
  - Function returns {'backfilled': 1, 'errors': 0}
```

#### Test Case 2: Work-In-Progress Order
```
Precondition: Ghost order with 0 items in ShipStation (being created)
Action: Run backfill function
Expected:
  - orders_inbox.status unchanged
  - No items added (none to add)
  - Function returns {'work_in_progress': 1, 'errors': 0}
  - Log warning: "Order X has 0 items - may be work-in-progress"
```

#### Test Case 3: Order Not Found (404)
```
Precondition: Ghost order with invalid shipstation_order_id
Action: Run backfill function
Expected:
  - orders_inbox.status = 'cancelled'
  - Log warning about orphaned order
  - Function returns {'cancelled': 1, 'errors': 0}
```

#### Test Case 4: Already Has Items
```
Precondition: Order has existing items in order_items_inbox
Action: Run backfill function
Expected:
  - Order skipped (not detected as ghost)
  - No changes to database
  - Function returns {'ghost_orders_found': 0}
```

#### Test Case 5: Rate Limit (429)
```
Precondition: 5 ghost orders, API returns 429 on 3rd request
Action: Run backfill function
Expected:
  - First 2 orders backfilled successfully
  - 3rd order triggers 429
  - Processing STOPS (remaining 2 orders NOT attempted)
  - Function returns {'backfilled': 2, 'rate_limited': True}
  - Log warning: "Hit rate limit - stopping backfill"
```

#### Test Case 6: NULL shipstation_order_id
```
Precondition: Ghost order with shipstation_order_id = NULL
Action: Run backfill function
Expected:
  - Order excluded by detection query (WHERE shipstation_order_id IS NOT NULL)
  - Not counted in ghost_orders_found
  - No API call attempted
```

### End-to-End Test

1. **Create ghost order manually:**
   - Create order in ShipStation with SKU + quantity
   - Wait for unified sync to create order shell (5 min)
   - Verify order in `orders_inbox`, no items in `order_items_inbox`

2. **Wait for backfill:**
   - Next unified sync cycle (5 min)
   - Verify ghost order detected and backfilled
   - Check logs for success message

3. **Validate result:**
   - Query database: items exist, total_items correct, status synced
   - Check UI: order appears in Orders Inbox (if awaiting shipment)

---

## 🚨 Rollback Plan

### If Issues Occur

1. **Immediate Rollback:**
   - Remove backfill function call from `unified_shipstation_sync.py`
   - Restart unified-shipstation-sync workflow
   - System reverts to current behavior (ghost orders remain)

2. **Data Cleanup (if needed):**
   ```sql
   -- If backfill created bad data for specific order
   DELETE FROM order_items_inbox 
   WHERE order_inbox_id = (
       SELECT id FROM orders_inbox WHERE order_number = 'PROBLEM_ORDER'
   );
   
   UPDATE orders_inbox 
   SET total_items = 0 
   WHERE order_number = 'PROBLEM_ORDER';
   ```

3. **Recovery Steps:**
   - Review logs to identify failure pattern
   - Fix bug in `ghost_order_backfill.py`
   - Re-test manually before re-enabling
   - Re-deploy with fix

### Low Risk Factors
- ✅ Only touches orders with 0 items (limited blast radius)
- ✅ Uses ON CONFLICT (prevents duplicates)
- ✅ Transaction safety (rollback on error)
- ✅ Easy to disable (remove function call)
- ✅ No destructive operations (only INSERT/UPDATE)

---

## 📊 Monitoring & Metrics

### Log Messages to Watch
```
👻 Found X ghost orders with 0 items
✅ Backfilled order 100528: 2 items (SKU 17612), status: shipped
⚠️ Order 100529 has 0 items in ShipStation - may be work-in-progress
⚠️ Order 100530 not found in ShipStation (404) - marked as cancelled
⚠️ Hit rate limit (429) - stopping backfill, will retry next cycle
🚨 CRITICAL: Order 100531 has duplicate SKUs - constraint violation risk!
❌ Error backfilling order 100532: API timeout
```

### Success Indicators
- Ghost order count decreases over time
- Backfilled count increases
- Error count remains at 0
- ShipStation Units = Local DB Units (metric alignment)

### Dashboard Integration (Future)
- Add ghost order count to dashboard KPI card
- Add backfill success rate metric
- Alert if ghost order count > 10

---

## 📝 Implementation Checklist

### Pre-Implementation (Phase 0)
- [ ] Run duplicate SKU detection script on ShipStation data
- [ ] Verify no orders have duplicate SKUs on multiple lines
- [ ] If duplicates found: STOP and redesign approach

### Development
- [ ] Create `src/services/ghost_order_backfill.py`
- [ ] Implement `backfill_ghost_orders()` function with per-order transactions
- [ ] Add shipstation_order_id NULL validation in detection query
- [ ] Add rate limit (429) detection and STOP behavior
- [ ] Add work-in-progress (0 items) detection and logging
- [ ] Add duplicate SKU warning for constraint violation detection
- [ ] Add comprehensive logging for all edge cases
- [ ] Add error handling for API failures (per-order isolation)
- [ ] Add ON CONFLICT safety for idempotency

### Integration
- [ ] Import function in `unified_shipstation_sync.py`
- [ ] Add function call after tracking status updates
- [ ] Update summary logging to include ghost metrics

### Testing
- [ ] Run detection query to find existing ghost orders
- [ ] Test backfill on order 100528
- [ ] Verify items populated correctly
- [ ] Check status synced from ShipStation
- [ ] Test edge cases (404, cancelled, errors)

### Validation
- [ ] Review logs for successful backfill
- [ ] Query database to confirm data integrity
- [ ] Check ShipStation Units vs Local DB Units alignment
- [ ] Verify no ghost orders remain in detection query

### Documentation
- [ ] Update `replit.md` with ghost order backfill feature
- [ ] Add log examples to troubleshooting guide
- [ ] Document edge cases and handling

### Deployment
- [ ] Restart `unified-shipstation-sync` workflow
- [ ] Monitor logs for 1 hour
- [ ] Confirm no errors or unexpected behavior
- [ ] Mark action plan as COMPLETE

---

## 🔗 Related Files

### Primary Implementation
- `src/services/ghost_order_backfill.py` (NEW)
- `src/unified_shipstation_sync.py` (MODIFIED)

### Supporting Files
- `src/services/shipstation/api_client.py` (uses existing credentials)
- `src/services/database/pg_utils.py` (uses existing connection)

### Documentation
- `docs/features/GHOST_ORDER_BACKFILL_ACTION_PLAN.md` (this file)
- `replit.md` (update after implementation)

---

## 📞 Questions & Decisions

### Resolved
- ✅ **Where to integrate:** unified_shipstation_sync (runs every 5 minutes)
- ✅ **Module structure:** Standalone function in separate file
- ✅ **Backfill scope:** Items + status + total_items count
- ✅ **Edge case handling:** Cancel orphaned orders (404), sync statuses, WIP detection
- ✅ **Transaction strategy:** Per-order isolation (not batch)
- ✅ **Bundle SKUs:** NOT applicable (bundles not entered in ShipStation)
- ✅ **On-hold orders:** INCLUDE in backfill (user confirmed)
- ✅ **0-item orders:** Keep as-is, log warning (may be work-in-progress)
- ✅ **Rate limiting:** STOP immediately on 429, retry next cycle
- ✅ **NULL shipstation_order_id:** Skip via WHERE clause in detection

### Open Questions
- ⏳ Should we add ghost order count to dashboard UI?
- ⏳ Should we add warning system for orders with 0 items > 24 hours old?
- ⏳ Should we log backfill metrics to `system_kpis` table?
- ⏳ Should we add duplicate SKU detection to prevent constraint violations?

---

---

## 🔍 Gap Analysis Summary

### Critical Gaps Addressed

| Gap | Severity | Status | Solution |
|-----|----------|--------|----------|
| **Duplicate SKU constraint** | HIGH | Mitigated | Phase 0 validation test required |
| **NULL shipstation_order_id** | Medium | Fixed | WHERE clause filters in detection query |
| **Partial failure handling** | Medium | Fixed | Per-order transaction isolation |
| **Rate limit cascade** | Medium | Fixed | STOP on 429, retry next cycle |
| **Bundle SKU expansion** | Low | N/A | Bundles not used in ShipStation |
| **On-hold orders** | Low | Fixed | Included in backfill (user confirmed) |
| **0-item orders (WIP)** | Low | Fixed | Log warning, don't cancel (user confirmed) |
| **Watermark timing** | Low | Fixed | Backfill runs BEFORE watermark update |

### Architectural Improvements

1. **Per-Order Transactions:** Each ghost order backfills in isolated transaction (fault tolerance)
2. **Rate Limit Protection:** Immediate stop on 429 (preserves API quota for main sync)
3. **Work-In-Progress Detection:** Logs 0-item orders without cancelling (user workflow support)
4. **Validation Layer:** NULL checks, duplicate SKU warnings, comprehensive error handling

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Duplicate SKU data loss | Low | High | Phase 0 validation test |
| Rate limit exhaustion | Low | Medium | STOP on 429 behavior |
| Partial backfill failures | Medium | Low | Per-order transactions |
| ShipStation API downtime | Low | Low | Skip and retry next cycle |

---

## 🎯 Next Steps

1. ✅ **Review this updated action plan** for completeness
2. **Execute Phase 0:** Run duplicate SKU validation test (BLOCKER)
3. **Approve implementation** approach (if Phase 0 passes)
4. **Execute Phase 1:** Create `ghost_order_backfill.py` module
5. **Execute Phase 2:** Integrate with unified sync
6. **Execute Phase 3:** Test with order 100528
7. **Execute Phase 4:** Monitor and validate
8. **Update documentation** and mark complete

---

**Prepared by:** Replit Agent  
**Last Updated:** October 29, 2025 (Revision 2 - Gap Analysis Complete)  
**Status:** Ready for Phase 0 Validation, Then Implementation  
**Blockers:** Duplicate SKU test must pass before proceeding

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
SELECT o.id, o.order_number, o.shipstation_order_id
FROM orders_inbox o
LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
WHERE o.status NOT IN ('shipped', 'cancelled')
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
- **Order has 0 items in ShipStation:** Keep as-is, log warning
- **API error:** Skip and retry on next cycle

---

## 📐 Implementation Plan

### Phase 1: Create Standalone Module (30 min)

**File:** `src/services/ghost_order_backfill.py`

```python
def backfill_ghost_orders(conn) -> dict:
    """
    Detect and fix ghost orders by backfilling items from ShipStation.
    
    Returns:
        dict: {
            'ghost_orders_found': int,
            'backfilled': int,
            'cancelled': int,
            'errors': int
        }
    """
```

**Key Features:**
- Self-contained, testable function
- Accepts database connection as parameter
- Returns metrics for logging/monitoring
- Comprehensive error handling
- ON CONFLICT safety for idempotency

### Phase 2: Integrate with Unified Sync (15 min)

**File:** `src/unified_shipstation_sync.py`

Add to end of main sync loop:
```python
# After tracking status updates, before final summary
from src.services.ghost_order_backfill import backfill_ghost_orders

# Backfill ghost orders
ghost_metrics = backfill_ghost_orders(conn)
logger.info(f"👻 Ghost order backfill: {ghost_metrics['backfilled']} fixed, {ghost_metrics['errors']} errors")
```

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
    conn: psycopg2.extensions.connection,
    api_key: str = None,
    api_secret: str = None
) -> dict:
    """
    Detect orders with 0 items and backfill from ShipStation.
    
    Args:
        conn: Active database connection (with transaction support)
        api_key: ShipStation API key (optional, uses environment if not provided)
        api_secret: ShipStation API secret (optional, uses environment if not provided)
    
    Returns:
        dict: Metrics about backfill operation
            - ghost_orders_found: Number of ghost orders detected
            - backfilled: Number successfully backfilled with items
            - cancelled: Number marked as cancelled
            - errors: Number of API/database errors
    
    Raises:
        None: All errors are caught, logged, and counted in metrics
    """
```

### Database Operations

#### Insert Items (Idempotent)
```python
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
- **404 Not Found:** Mark order as cancelled (orphaned)
- **429 Rate Limit:** Log warning, skip (will retry next cycle)
- **500 Server Error:** Log error, skip (transient failure)

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Detects all ghost orders (0 items) in `orders_inbox`
- ✅ Fetches complete order details from ShipStation
- ✅ Backfills items into `order_items_inbox`
- ✅ Updates `total_items` count accurately
- ✅ Syncs order status from ShipStation
- ✅ Handles cancelled/not-found orders gracefully
- ✅ Runs automatically every 5 minutes
- ✅ Zero manual intervention required

### Data Integrity
- ✅ No duplicate items (ON CONFLICT handling)
- ✅ No orphaned records
- ✅ Transaction safety (rollback on error)
- ✅ Preserves existing correct data

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

#### Test Case 2: Cancelled Order
```
Precondition: Ghost order with cancelled status in ShipStation
Action: Run backfill function
Expected:
  - orders_inbox.status = 'cancelled'
  - No items added (order has 0 items)
  - Function returns {'cancelled': 1, 'errors': 0}
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
⚠️ Order 100529 not found in ShipStation - marked as cancelled
❌ Error backfilling order 100530: API timeout
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

### Development
- [ ] Create `src/services/ghost_order_backfill.py`
- [ ] Implement `backfill_ghost_orders()` function
- [ ] Add comprehensive logging
- [ ] Add error handling for API failures
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
- ✅ **Edge case handling:** Cancel orphaned orders, sync statuses

### Open Questions
- ⏳ Should we add ghost order count to dashboard UI?
- ⏳ Should we alert if ghost order count exceeds threshold?
- ⏳ Should we log backfill metrics to `system_kpis` table?

---

## 🎯 Next Steps

1. **Review this action plan** for completeness
2. **Approve implementation** approach
3. **Execute Phase 1:** Create `ghost_order_backfill.py` module
4. **Execute Phase 2:** Integrate with unified sync
5. **Execute Phase 3:** Test with order 100528
6. **Execute Phase 4:** Monitor and validate
7. **Update documentation** and mark complete

---

**Prepared by:** Replit Agent  
**Last Updated:** October 29, 2025  
**Status:** Ready for Implementation

# Automatic Lot Number Update - Risk Analysis

## 🚨 Potential Breaking Points & Mitigation

### **CRITICAL RISKS (High Impact)**

---

### **Risk 1: Race Condition - Dual Updates**
**Scenario:** Upload service AND unified sync both try to update the same order simultaneously

**How it breaks:**
1. Upload service claims order, starts uploading (status: 'uploaded')
2. Unified sync sees order in ShipStation with status 'awaiting_shipment'
3. Sync updates local status to 'awaiting_shipment' 
4. **Lot update logic triggers** during sync
5. Sync calls ShipStation API to update lot numbers
6. Upload service also calls ShipStation API to create/update order
7. **Last write wins** - could overwrite lot number changes OR order data

**Impact:** 🔴 HIGH
- Lot numbers revert to old values
- Order data corruption
- Duplicate API calls to ShipStation

**Mitigation:**
```python
# In unified_shipstation_sync.py
if order['orderStatus'] == 'awaiting_shipment':
    # Check if order was JUST uploaded by our system (within last 5 min)
    cursor.execute("""
        SELECT updated_at FROM orders_inbox 
        WHERE order_number = %s AND status = 'uploaded'
    """, (order_number,))
    result = cursor.fetchone()
    
    if result and (datetime.now() - result[0]).seconds < 300:
        logger.info(f"⏸️ Skipping lot update for {order_number} - recently uploaded")
        return  # Let upload service finish first
    
    # Safe to update lot numbers
    update_lot_numbers(order)
```

---

### **Risk 2: Cascading Mass Updates**
**Scenario:** Lot number changes from 250300 → 250400, triggering updates to 500 orders

**How it breaks:**
1. User changes active lot for SKU 17612 from 250300 to 250400
2. Next sync cycle runs
3. System finds 500 orders with SKU "17612 - 250300"
4. **Attempts to update all 500 orders in one sync cycle**
5. ShipStation API rate limit hit (40 requests/min)
6. Half the orders update, half fail
7. Sync crashes, watermark doesn't advance
8. Next cycle tries again → infinite loop

**Impact:** 🔴 HIGH
- API rate limit violations
- Sync workflow crashes
- Orders stuck in inconsistent state
- Watermark stuck, no new orders processed

**Mitigation:**
```python
# Batch lot updates with rate limiting
MAX_LOT_UPDATES_PER_CYCLE = 10
lot_updates_this_cycle = 0

for order in orders_needing_update:
    if lot_updates_this_cycle >= MAX_LOT_UPDATES_PER_CYCLE:
        logger.info(f"⏸️ Reached lot update limit ({MAX_LOT_UPDATES_PER_CYCLE}), will continue next cycle")
        break
    
    update_lot_numbers(order)
    lot_updates_this_cycle += 1
    time.sleep(0.5)  # Rate limit: 2 updates/second max
```

**Better approach:** Don't auto-update on lot changes. Only update when order status changes to awaiting_shipment.

---

### **Risk 3: Warehouse Already Picked Old Lot**
**Scenario:** Warehouse physically picked lot 250300, but system updates to 250400

**How it breaks:**
1. Order placed with lot 250300
2. Warehouse picks lot 250300 from shelf
3. Order goes on hold (customer issue)
4. Lot changes to 250400 (new batch)
5. Order released from hold
6. **System auto-updates to lot 250400**
7. ShipStation label shows lot 250400
8. **Package contains lot 250300** (already picked)
9. Customer receives wrong lot number

**Impact:** 🔴 HIGH
- Product lot traceability broken
- Compliance/regulatory issues
- Inventory count errors
- Customer safety (if lot recall needed)

**Mitigation:**
```python
# Only update lots for orders that haven't been picked
# Check if order has been in awaiting_shipment before
cursor.execute("""
    SELECT COUNT(*) FROM order_status_history 
    WHERE order_number = %s AND status = 'awaiting_shipment'
""", (order_number,))

if cursor.fetchone()[0] > 0:
    logger.warning(f"⚠️ Order {order_number} was previously awaiting shipment - skipping lot update (may be picked)")
    return
```

**Better approach:** Only update lots for orders coming FROM on_hold, not all awaiting_shipment transitions.

---

### **MEDIUM RISKS**

---

### **Risk 4: SKU Parsing Edge Cases**
**Scenario:** Unexpected SKU formats break the parsing logic

**How it breaks:**
- SKU format: `"17612-250300"` (dash instead of space-dash-space)
- SKU format: `"17612 -250300"` (extra space)
- SKU format: `"17612 - 250300 - QA"` (multiple dashes)
- SKU format: `"BUNDLE-001"` (no lot number)

**Impact:** 🟡 MEDIUM
- Parsing fails, throws exception
- Sync cycle crashes
- Orders not processed

**Mitigation:**
```python
def extract_base_sku_safe(sku_string):
    """Safely extract base SKU with multiple format support"""
    if not sku_string:
        return None
    
    # Try space-dash-space format first
    if ' - ' in sku_string:
        return sku_string.split(' - ')[0].strip()
    
    # Try dash only
    if '-' in sku_string:
        return sku_string.split('-')[0].strip()
    
    # No lot number - return as-is
    return sku_string.strip()

def extract_lot_safe(sku_string):
    """Safely extract lot number"""
    if not sku_string or ' - ' not in sku_string:
        return None
    
    parts = sku_string.split(' - ')
    if len(parts) >= 2:
        return parts[1].strip()
    
    return None
```

---

### **Risk 5: No Active Lot Exists**
**Scenario:** SKU has no active lot in sku_lot table (discontinued product)

**How it breaks:**
1. Order has SKU 17612 with old lot 250237
2. Product discontinued, all lots marked active=0
3. Lot update logic queries for active lot → returns NULL
4. Code tries to update to NULL lot → crashes or creates invalid SKU

**Impact:** 🟡 MEDIUM
- Sync crashes
- Invalid SKU in ShipStation
- Order stuck in limbo

**Mitigation:**
```python
current_lot = get_active_lot(base_sku)

if not current_lot:
    logger.warning(f"⚠️ No active lot for SKU {base_sku} - keeping existing lot {old_lot}")
    return  # Don't update - use existing lot
```

---

### **Risk 6: ShipStation API Failure Mid-Update**
**Scenario:** API call fails after updating 5 of 10 items in an order

**How it breaks:**
1. Order has 10 items with different SKUs
2. Successfully update items 1-5 with new lot numbers
3. API call for item 6 fails (timeout, 500 error)
4. **Order now has mixed lot numbers** (5 new, 5 old)
5. Database not updated (transaction rolled back)
6. Next sync tries again → same partial failure

**Impact:** 🟡 MEDIUM
- Data inconsistency between ShipStation and local DB
- Order stuck in partial state
- Repeated failures

**Mitigation:**
```python
try:
    # Update all items in single API call (atomic)
    updated_items = []
    for item in order_items:
        new_lot = get_active_lot(item['base_sku'])
        if new_lot and new_lot != item['old_lot']:
            updated_items.append({
                'sku': f"{item['base_sku']} - {new_lot}",
                'quantity': item['quantity']
            })
    
    if updated_items:
        # Single atomic update to ShipStation
        shipstation_api.update_order(order_id, items=updated_items)
        logger.info(f"✅ Updated {len(updated_items)} items in order {order_number}")
    
except Exception as e:
    logger.error(f"❌ Failed to update order {order_number}: {e}")
    # Don't crash - log and continue
    # Next cycle will retry
```

---

### **LOW RISKS**

---

### **Risk 7: XML Import SKU Normalization Too Aggressive**
**Scenario:** Normalization strips important SKU data

**How it breaks:**
- SKU: `"17612 - Special Edition"` → normalized to `"17612"` → loses "Special Edition"
- SKU: `"17612-A"` vs `"17612-B"` → both normalized to `"17612"` → loses variant

**Impact:** 🟢 LOW
- Wrong products matched
- Incorrect inventory deductions

**Mitigation:**
```python
# Only normalize for Key Product filtering, preserve original
original_sku = item['sku']
normalized_sku = original_sku.split(' - ')[0].strip()

if normalized_sku in key_products:
    # Use ORIGINAL sku, not normalized
    filtered_items.append({'sku': original_sku, 'quantity': item['quantity']})
```

---

### **Risk 8: Performance Degradation**
**Scenario:** Lot updates slow down sync cycle significantly

**How it breaks:**
1. Each lot update requires 2 API calls (fetch order, update order)
2. 20 orders need updates = 40 API calls
3. Sync cycle takes 60 seconds instead of 5 seconds
4. Watermark advancement delayed
5. Real-time order processing slows down

**Impact:** 🟢 LOW
- Slower sync cycles
- Delayed order processing
- User perceives system as "slow"

**Mitigation:**
- Limit updates per cycle (max 10)
- Run lot updates in separate async task
- Cache active lot numbers (don't query DB for each item)

---

## 🛡️ **RECOMMENDED SAFEGUARDS**

### **1. Conservative Trigger Logic**
```python
# ONLY update lots when coming FROM on_hold
if old_status == 'on_hold' and new_status == 'awaiting_shipment':
    update_lot_numbers(order)
else:
    # Don't auto-update for other status changes
    pass
```

### **2. Rate Limiting**
```python
MAX_LOT_UPDATES_PER_CYCLE = 10
time.sleep(0.5) between updates
```

### **3. Dry-Run Mode**
```python
DRY_RUN = True  # Set via config
if DRY_RUN:
    logger.info(f"DRY-RUN: Would update {order_number} from {old_lot} → {new_lot}")
    return
```

### **4. Manual Override Flag**
```python
# Add column: manual_lot_override (boolean)
# If TRUE, never auto-update this order
cursor.execute("""
    SELECT manual_lot_override FROM orders_inbox WHERE order_number = %s
""", (order_number,))
if cursor.fetchone()[0]:
    logger.info(f"⏸️ Manual override set - skipping lot update")
    return
```

### **5. Audit Trail**
```python
# Log all lot changes to audit table
cursor.execute("""
    INSERT INTO lot_update_audit (
        order_number, base_sku, old_lot, new_lot, 
        updated_by, updated_at, reason
    ) VALUES (%s, %s, %s, %s, 'auto_sync', NOW(), %s)
""", (order_number, base_sku, old_lot, new_lot, reason))
```

---

## 🎯 **DECISION MATRIX**

| Approach | Pros | Cons | Risk Level |
|----------|------|------|------------|
| **Auto-update all awaiting_shipment** | Complete automation | May update already-picked orders | 🔴 HIGH |
| **Only update from on_hold → awaiting_shipment** | Targets specific use case | Misses other scenarios | 🟡 MEDIUM |
| **Manual approval required** | Full control | Not automated, requires user action | 🟢 LOW |
| **Dry-run mode first** | Safe testing | Requires two-phase rollout | 🟢 LOW |

---

## ✅ **RECOMMENDED APPROACH**

**Phase 1: Conservative (Safest)**
- Only update orders transitioning from `on_hold` → `awaiting_shipment`
- Limit to 10 updates per cycle
- Add dry-run mode for testing
- Comprehensive logging

**Phase 2: Expand (After validation)**
- Add other status transitions if needed
- Increase update limit
- Remove dry-run mode

**Phase 3: Full Automation (After 30 days)**
- Auto-update all qualifying orders
- Real-time monitoring dashboard
- Automated alerts for failures

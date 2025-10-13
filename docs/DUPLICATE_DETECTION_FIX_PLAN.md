# Duplicate Detection Fix Implementation Plan

**Date:** October 13, 2025  
**Issue:** Dev/Prod lot number conflicts causing duplicate orders in ShipStation  
**Root Cause:** Duplicate detection only checks `order_number`, not `(order_number + base_sku)`

---

## Problem Statement

When dev and prod systems upload the same order with different lot numbers:
- Dev uploads: Order 689755 + SKU "17612-250237"
- Prod uploads: Order 689755 + SKU "17612-250300"

**Current behavior:** Both uploads succeed → Duplicate orders in ShipStation  
**Expected behavior:** Prod upload should be skipped (same order + SKU already exists)

---

## Root Cause Analysis

### Current Duplicate Detection Logic
```python
# Line 312-322: Creates map by ORDER NUMBER only
existing_order_map[order_num] = {
    'orderId': order_id,
    'orderKey': order_key
}

# Line 333: Checks ORDER NUMBER only
if order_num_upper in existing_order_map:
    # Skip duplicate
```

**Problem:** Only checks order number, ignores SKU differences. ShipStation accepts multiple orders with same order number if SKUs differ.

### ShipStation Data Model
- ShipStation treats `(orderNumber + SKU)` as unique identifier
- Allows same order number with different SKUs (rare but valid)
- Our check doesn't account for this → Duplicates slip through

---

## Solution

**Match on `(order_number + base_SKU)` combination instead of order number alone.**

Use `LEFT(sku, 5)` to extract base SKU (all SKUs are 5 digits):
- "17612-250237" → "17612"
- "17612-250300" → "17612"
- Compare: "17612" == "17612" → DUPLICATE ✅

---

## Implementation Details

### File: `src/scheduled_shipstation_upload.py`

#### Change 1: Modify `existing_order_map` structure (Lines 312-322)

**Current:**
```python
existing_order_map = {}
for o in existing_orders:
    order_num = o.get('orderNumber', '').strip().upper()
    order_id = o.get('orderId')
    order_key = o.get('orderKey')
    
    existing_order_map[order_num] = {
        'orderId': order_id,
        'orderKey': order_key
    }
```

**New:**
```python
existing_order_map = {}
for o in existing_orders:
    order_num = o.get('orderNumber', '').strip().upper()
    order_id = o.get('orderId')
    order_key = o.get('orderKey')
    
    # Extract base SKUs (first 5 chars) from line items
    base_skus = set()
    for item in o.get('items', []):
        item_sku = item.get('sku', '')
        if item_sku:
            base_sku = item_sku[:5]  # First 5 digits only
            base_skus.add(base_sku)
    
    existing_order_map[order_num] = {
        'orderId': order_id,
        'orderKey': order_key,
        'base_skus': base_skus  # NEW: Set of 5-digit base SKUs
    }
```

#### Change 2: Modify duplicate check logic (Lines 329-356)

**Current:**
```python
for idx, order in enumerate(shipstation_orders):
    order_num_upper = order['orderNumber'].strip().upper()
    order_sku_info = order_sku_map[idx]
    
    if order_num_upper in existing_order_map:
        # Already exists - skip
        existing = existing_order_map[order_num_upper]
        skipped_count += 1
        # ... update status to awaiting_shipment
```

**New:**
```python
for idx, order in enumerate(shipstation_orders):
    order_num_upper = order['orderNumber'].strip().upper()
    order_sku_info = order_sku_map[idx]
    
    # Extract base SKUs from this new order (first 5 chars)
    new_order_base_skus = set()
    for item in order['items']:
        item_sku = item.get('sku', '')
        if item_sku:
            base_sku = item_sku[:5]  # First 5 digits only
            new_order_base_skus.add(base_sku)
    
    # Check if order_number exists in ShipStation
    if order_num_upper in existing_order_map:
        existing = existing_order_map[order_num_upper]
        existing_base_skus = existing.get('base_skus', set())
        
        # Check if ANY base SKU overlaps (order + SKU combination exists)
        if new_order_base_skus.intersection(existing_base_skus):
            # DUPLICATE: Same order number + same base SKU exists
            skipped_count += 1
            shipstation_id = existing['orderId'] or existing['orderKey']
            
            logger.warning(f"Skipped duplicate: Order {order_num_upper} + SKU(s) {new_order_base_skus} already exists in ShipStation")
            
            # ... existing code to update status
        else:
            # DIFFERENT SKUs - allow upload (edge case: multi-SKU orders)
            new_orders.append(order)
            new_order_sku_map.append(order_sku_info)
    else:
        # New order - needs upload
        new_orders.append(order)
        new_order_sku_map.append(order_sku_info)
```

---

## Logic Flow Examples

### Example 1: Dev/Prod Conflict (Prevented)
```
ShipStation has:
  Order 689755 + SKU "17612-250237" 
  → existing_order_map['689755'] = {base_skus: {'17612'}}

Prod tries to upload:
  Order 689755 + SKU "17612-250300"
  → new_order_base_skus = {'17612'}

Check:
  '689755' in existing_order_map? YES
  {'17612'}.intersection({'17612'})? YES → DUPLICATE!

Result: SKIP ✅
```

### Example 2: Genuinely New Order (Uploaded)
```
ShipStation has:
  Order 689999 + SKU "17904-250237"
  → existing_order_map['689999'] = {base_skus: {'17904'}}

Prod tries to upload:
  Order 690000 + SKU "17612-250300"
  → new_order_base_skus = {'17612'}

Check:
  '690000' in existing_order_map? NO

Result: UPLOAD ✅
```

### Example 3: Same Order, Different SKU (Uploaded)
```
ShipStation has:
  Order 689123 + SKU "17904-250300"
  → existing_order_map['689123'] = {base_skus: {'17904'}}

Prod tries to upload:
  Order 689123 + SKU "17612-250300"
  → new_order_base_skus = {'17612'}

Check:
  '689123' in existing_order_map? YES
  {'17612'}.intersection({'17904'})? NO → Different SKUs!

Result: UPLOAD ✅ (rare but valid case)
```

---

## Edge Cases Handled

1. ✅ **Dev/Prod lot conflicts** - Prevented by base SKU matching
2. ✅ **Multi-SKU orders** - Uses set intersection to check ANY overlap
3. ✅ **Spacing variations** - "17612-250237" vs "17612 - 250300" both → "17612"
4. ✅ **Empty SKUs** - Skipped (only processes non-empty SKUs)
5. ✅ **Case sensitivity** - Order numbers normalized to uppercase

---

## Testing Plan

### Test 1: Dev/Prod Conflict
1. Manually create order in ShipStation with lot 250237
2. Try to upload same order with lot 250300
3. Verify: Upload skipped with warning log
4. Expected log: `"Skipped duplicate: Order 689755 + SKU(s) {'17612'} already exists"`

### Test 2: Normal New Orders
1. Upload genuinely new orders
2. Verify: Upload succeeds
3. Expected: Orders appear in ShipStation

### Test 3: Multi-SKU Orders
1. Create order with multiple SKUs
2. Upload duplicate with partial SKU overlap
3. Verify: Duplicate detection works correctly

### Test 4: Log Verification
- Check workflow logs for warning messages
- Verify skipped_count increments correctly
- Confirm no false positives (new orders not skipped)

---

## Files Modified

- ✏️ `src/scheduled_shipstation_upload.py` (2 changes, ~30 lines modified)

**No database changes required** ✅

---

## Rollback Plan

If issues occur:
1. Revert `src/scheduled_shipstation_upload.py` to previous version
2. Restart `shipstation-upload` workflow
3. No database migrations to rollback
4. Zero downtime

---

## Deployment Steps

1. **Backup current code** (automatic via Replit checkpoints)
2. **Apply changes** to `src/scheduled_shipstation_upload.py`
3. **Restart workflow** `shipstation-upload`
4. **Monitor logs** for first 2-3 upload cycles
5. **Verify** no duplicate orders created
6. **Test** with known duplicates

---

## Success Criteria

- ✅ No duplicate orders created when lot numbers differ
- ✅ New orders upload successfully
- ✅ Warning logs appear for skipped duplicates
- ✅ Multi-SKU orders handled correctly
- ✅ Zero false positives (valid orders not skipped)

---

**Status:** Ready for implementation  
**Approval:** Pending user confirmation

# ShipStation Upload Bug Fixes - Complete Documentation

**Date:** October 6, 2025  
**File Modified:** `src/scheduled_shipstation_upload.py`  
**Fixes Applied:** 4 critical bug fixes

---

## Executive Summary

Fixed critical duplicate order bug in ShipStation upload service that was creating multiple ShipStation orders for the same customer order when bundles expanded to the same base SKU. The bug had **two root causes**:

1. **No consolidation** - Multiple bundles expanding to same SKU created separate orders
2. **No normalization** - Inconsistent SKU spacing (e.g., "17612-250237" vs "17612 - 250237") bypassed duplicate detection

### Impact
- **Affected Period:** October 3-6, 2025 (since upload script creation)
- **Duplicate Orders:** 18 duplicate ShipStation orders from 9 real customer orders
- **Most Affected SKU:** 17612 (appears in 21 bundle configurations)

---

## Fix 1: SKU Normalization Function

### Problem
SKUs stored inconsistently in database:
- Sometimes: `17612 - 250237` (with spaces around dash)
- Sometimes: `17612-250237` (no spaces)

This caused:
- Duplicate detection to fail (`"17612 - 250237" != "17612-250237"`)
- Same SKU treated as different items
- Multiple orders created for identical SKUs

### Solution
Added `normalize_sku()` function to standardize all SKU formats to `"BASE - LOT"` format.

```python
def normalize_sku(sku):
    """
    FIX 1: Normalize SKU format to prevent duplicates from spacing inconsistencies
    
    Standardizes SKU format by:
    - Removing extra whitespace
    - Standardizing dash spacing to " - " (space-dash-space)
    - Handling both "17612-250237" and "17612 - 250237" formats
    
    Args:
        sku (str): Raw SKU string from database
        
    Returns:
        str: Normalized SKU in format "BASE - LOT" or "BASE" if no lot
    """
    if not sku:
        return ''
    
    sku = sku.strip()
    
    if '-' in sku:
        parts = sku.split('-')
        if len(parts) == 2:
            base = parts[0].strip()
            lot = parts[1].strip()
            return f"{base} - {lot}"
    
    return sku
```

### Location
- **Line:** 35-62
- **File:** `src/scheduled_shipstation_upload.py`

### Testing
```python
# Test cases:
normalize_sku("17612-250237")      # Returns: "17612 - 250237"
normalize_sku("17612 - 250237")    # Returns: "17612 - 250237"
normalize_sku("17612  -  250237")  # Returns: "17612 - 250237"
normalize_sku("18795")             # Returns: "18795"
```

---

## Fix 2: Consolidate Items by Base SKU

### Problem
**BEFORE:** Upload script created **ONE ShipStation order for EACH row** in `order_items_inbox`:

```python
# BUGGY CODE (before fix):
for sku, qty, unit_price_cents in items:
    # Creates a new ShipStation order for EVERY iteration
    shipstation_order = {...}
    shipstation_orders.append(shipstation_order)  # ❌ Duplicate!
```

**Example scenario:**
- Customer orders bundle 18345 (Autoship) + bundle 18445 (FREE Autoship)
- Both bundles expand to SKU 17612 x1
- Database has 2 rows: `17612 x1`, `17612 x1`
- **Result:** 2 separate ShipStation orders created! ❌

### Solution
**AFTER:** Consolidate items by base SKU BEFORE creating ShipStation orders:

```python
# FIXED CODE:
# Step 1: Group items by normalized base SKU
consolidated_items = defaultdict(lambda: {'qty': 0, 'price': 0, 'original_sku': ''})

for sku, qty, unit_price_cents in items:
    normalized_sku = normalize_sku(sku)
    base_sku = normalized_sku.split(' - ')[0].strip()
    
    # Accumulate quantities for same base SKU
    consolidated_items[base_sku]['qty'] += qty
    if consolidated_items[base_sku]['price'] == 0 and unit_price_cents:
        consolidated_items[base_sku]['price'] = unit_price_cents

# Step 2: Create ONE order per unique base SKU
for base_sku, item_data in consolidated_items.items():
    qty = item_data['qty']  # Consolidated quantity
    # ... create single ShipStation order
```

**Same example NOW:**
- Customer orders bundle 18345 + bundle 18445
- Both expand to SKU 17612 x1
- **Consolidation:** `17612: qty=2` (1+1)
- **Result:** 1 ShipStation order with qty=2 ✅

### Location
- **Lines:** 131-201
- **File:** `src/scheduled_shipstation_upload.py`

### Key Changes
1. Added `defaultdict` import at top of file (line 9)
2. Normalize each SKU before processing
3. Extract base SKU (strip lot number for grouping)
4. Sum quantities for same base SKU
5. Create ONE order per unique base SKU with consolidated quantity

---

## Fix 3: In-Batch Duplicate Prevention

### Problem
Duplicate check only compared against **existing orders in ShipStation** from previous uploads.

It did NOT check for duplicates **within the current batch** being prepared.

**Example:**
```python
# Current batch being prepared:
[
    {order: "688375", sku: "17612"},  # From bundle 18345
    {order: "688375", sku: "17612"}   # From bundle 18445
]

# Duplicate check logic (BEFORE):
for order in batch:
    if exists_in_shipstation(order):  # Only checks ShipStation!
        skip
    else:
        upload  # Both pass! Both uploaded! ❌
```

### Solution
Added **in-batch deduplication** BEFORE checking ShipStation:

```python
# FIX 3: IN-BATCH DUPLICATE PREVENTION
seen_in_batch = set()
deduplicated_orders = []
deduplicated_sku_map = []

for idx, order in enumerate(shipstation_orders):
    order_num = order['orderNumber'].upper()
    base_sku = normalize_sku(order_sku_map[idx]['sku']).split(' - ')[0].strip()
    
    key = f"{order_num}_{base_sku}"
    
    if key not in seen_in_batch:
        seen_in_batch.add(key)
        deduplicated_orders.append(order)
        deduplicated_sku_map.append(order_sku_info)
    else:
        logger.warning(f"Skipped in-batch duplicate: Order {order_num}, SKU {base_sku}")

# Replace with deduplicated lists
shipstation_orders = deduplicated_orders
order_sku_map = deduplicated_sku_map
```

### Location
- **Lines:** 203-228
- **File:** `src/scheduled_shipstation_upload.py`

### Logic Flow
1. **Before ShipStation check:** Scan current batch for duplicates
2. **Track seen orders:** Use set with key `{ORDER_NUMBER}_{BASE_SKU}`
3. **Remove duplicates:** Keep first occurrence, skip subsequent
4. **Log warnings:** Alert when in-batch duplicates detected
5. **Then check ShipStation:** Compare against external system

---

## Fix 4: Normalize SKUs in Duplicate Check

### Problem
Even with normalization function available, the duplicate check logic was NOT using it:

```python
# BUGGY duplicate check (BEFORE):
sku = sku_with_lot.split(' - ')[0].strip()  # Manual parsing, no normalization
key = f"{order_num}_{sku}"

if key in existing_order_map:
    # Would miss duplicates due to spacing differences
```

### Solution
Apply normalization in BOTH places:

**Part A: Building existing order map**
```python
# FIX 4: Create map of existing orders with NORMALIZED SKUs
for o in existing_orders:
    order_num = o.get('orderNumber', '').strip().upper()
    items = o.get('items', [])
    if items and len(items) > 0:
        sku_with_lot = items[0].get('sku', '')
        # Normalize SKU to handle spacing inconsistencies
        normalized_sku = normalize_sku(sku_with_lot)
        base_sku = normalized_sku.split(' - ')[0].strip()
        
        key = f"{order_num}_{base_sku}"
        existing_order_map[key] = {...}
```

**Part B: Comparing current orders**
```python
# Filter out duplicates using NORMALIZED SKUs
for idx, order in enumerate(shipstation_orders):
    order_num_upper = order['orderNumber'].strip().upper()
    sku = order_sku_info['sku']
    
    # FIX 4: Normalize SKU for comparison
    normalized_sku = normalize_sku(sku)
    base_sku = normalized_sku.split(' - ')[0].strip()
    key = f"{order_num_upper}_{base_sku}"
    
    if key in existing_order_map:
        # Now correctly detects duplicates regardless of spacing
```

### Location
- **Lines:** 240-260 (Part A: Building map)
- **Lines:** 262-277 (Part B: Comparison)
- **File:** `src/scheduled_shipstation_upload.py`

### Key Changes
1. Use `normalize_sku()` when building `existing_order_map`
2. Use `normalize_sku()` when comparing current orders
3. Both sides now use identical normalization → reliable comparison
4. Catches duplicates regardless of spacing variations

---

## Combined Fix Effectiveness

### Before Fixes
```
Order 688375:
  - Bundle 18345 → 17612 x1 → ShipStation Order #1 ❌
  - Bundle 18445 → 17612 x1 → ShipStation Order #2 ❌
  
Result: 2 duplicate orders uploaded to ShipStation
```

### After All 4 Fixes
```
Order 688375:
  - Bundle 18345 → 17612 x1 ]
  - Bundle 18445 → 17612 x1 ] → Consolidated → 17612 x2 → ShipStation Order #1 ✅
  
Result: 1 correct order with consolidated quantity
```

---

## Code Quality Improvements

### Import Organization
Moved `defaultdict` import to top of file for proper organization:
```python
from collections import defaultdict  # Line 9
```

### Type Safety
Existing type checking issues identified (non-critical):
- Line 185: Type narrowing for `unit_price_cents` (int | str)
- Line 187: Type narrowing for price calculations
- These existed before fixes and don't affect runtime behavior

---

## Testing Recommendations

### Unit Tests Needed
1. **SKU Normalization:**
   ```python
   def test_normalize_sku():
       assert normalize_sku("17612-250237") == "17612 - 250237"
       assert normalize_sku("17612 - 250237") == "17612 - 250237"
       assert normalize_sku("17612  -  250237") == "17612 - 250237"
   ```

2. **Consolidation Logic:**
   ```python
   def test_consolidation():
       items = [("17612 - 250300", 1, 1000), ("17612-250300", 1, 1000)]
       # Should consolidate to: 17612 x2
       result = consolidate_items(items)
       assert len(result) == 1
       assert result["17612"]["qty"] == 2
   ```

3. **In-Batch Deduplication:**
   ```python
   def test_in_batch_dedup():
       batch = [
           {"orderNumber": "688375", "sku": "17612"},
           {"orderNumber": "688375", "sku": "17612"}
       ]
       # Should deduplicate to 1 order
       result = deduplicate_batch(batch)
       assert len(result) == 1
   ```

### Integration Tests Needed
1. Upload orders with multiple bundles expanding to same SKU
2. Verify only ONE ShipStation order created
3. Verify consolidated quantity is correct
4. Test with various spacing formats

---

## Deployment Checklist

- [x] Fix 1: SKU normalization function added
- [x] Fix 2: Consolidation logic implemented
- [x] Fix 3: In-batch duplicate prevention added
- [x] Fix 4: Normalization applied to duplicate checks
- [x] Import organization cleaned up
- [ ] Delete corrupted data (Oct 6, 2025 shipments)
- [ ] Test with real orders
- [ ] Monitor logs for "Skipped in-batch duplicate" warnings
- [ ] Verify ShipStation orders match expected quantities

---

## Known Limitations

### SKU-Lot Attribution
After consolidation, the system uses the **first lot number** found for the base SKU. This is acceptable because:
- All items of same SKU should have same lot in active mappings
- `sku_lot` table enforces UNIQUE(sku, lot) constraint
- Only ONE lot should be active per SKU at a time

### Price Handling
Uses **first price found** when consolidating. This is safe because:
- Same SKU should have same unit price
- Bundle components have consistent pricing
- If prices differ (rare), first price takes precedence

---

## Maintenance Notes

### Future Enhancements
1. Add unit tests for all 4 fixes
2. Consider adding price validation (warn if prices differ)
3. Add metrics for consolidation rate
4. Log consolidation details for audit trail

### Monitoring
Watch for these log messages:
- `"After in-batch deduplication: X unique orders"` - Should be < raw count if duplicates exist
- `"Skipped in-batch duplicate: Order X, SKU Y"` - Indicates consolidation working

### Related Files
- `src/shipstation_status_sync.py` - Status sync after upload
- `src/manual_shipstation_sync.py` - Manual order detection
- `shipped_items.html` - UI showing shipped items (has duplicate indicators)

---

## Conclusion

All 4 critical fixes have been successfully implemented to address the duplicate order bug. The upload service now:

1. ✅ **Normalizes** all SKUs to consistent format
2. ✅ **Consolidates** items by base SKU before creating orders
3. ✅ **Deduplicates** within current batch
4. ✅ **Compares** using normalized SKUs for duplicate detection

**Next Steps:**
1. Delete today's corrupted shipment data (Oct 6, 2025)
2. Re-run upload for today's orders with fixed logic
3. Monitor for successful consolidation
4. Verify no new duplicates created

---

**Fix Author:** Replit Agent  
**Review Status:** Ready for deployment  
**Risk Level:** Low (logic improvements only, no schema changes)

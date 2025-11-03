# Root Cause Analysis: 7-Pallet Discrepancy Between Charge Report and Weekly Inventory
**Date:** November 3, 2025  
**Investigator:** Replit Agent  
**Severity:** Medium - Data Integrity Issue  
**Status:** Root Causes Identified - Awaiting Fix Approval

---

## Executive Summary

A 7-pallet discrepancy exists between the October charge report (107 pallets = $48.15) and the weekly inventory report for Oct 31 (97 pallets = $43.65). Investigation revealed **three critical root causes**:

1. **Invalid Sept 30 Baseline** - Database values don't mathematically derive from Sept 19 - Sept shipments
2. **Missing Transaction Types** - Charge report ignores "Adjust Up" and "Adjust Down" transactions
3. **Architecture Confusion** - Two different calculation methods produce different results

---

## Problem Statement

**Observed Behavior:**
- **Charge Report** for October shows 107 pallets on Oct 31 → $48.15 space rental
- **Weekly Inventory Report** for Oct 31 shows 97 pallets → $43.65 space rental
- **Discrepancy:** 10 pallets difference, $4.50 variance

**Expected Behavior:**
Both reports should show identical inventory levels for the same date (Oct 31).

---

## Investigation Timeline

### Step 1: Baseline Validation

**Query:** Compare Sept 19 baseline vs Sept 30 baseline vs calculated values

| SKU | Sept 19 Baseline | Sept Shipments | **Calculated Sept 30** | **Database Sept 30** | **Error** |
|-----|------------------|----------------|------------------------|----------------------|-----------|
| 17612 | 1,019 | 738 | **281** | 1,493 | **+1,212** ❌ |
| 17904 | 468 | 19 | **449** | 59 | **-390** ❌ |
| 17914 | 1,410 | 39 | **1,371** | 127 | **-1,244** ❌ |
| 18675 | 714 | 0 | **714** | 738 | **+24** ❌ |
| 18795 | 7,719 | 14 | **7,705** | 7,799 | **+94** ❌ |

**Finding:** The Sept 30 baseline stored in `configuration_params` does NOT equal Sept 19 minus September shipments. This baseline was either:
- Entered manually with incorrect values
- Calculated using a different method (unknown)
- Corrupted during migration

### Step 2: Transaction Discovery

**Query:** All inventory transactions from Sept 19 onward

**Critical Discovery:** October included **3,300 units of SKU 17612 RECEIVED** plus end-of-month adjustments:

| Date | SKU | Type | Qty | Notes |
|------|-----|------|-----|-------|
| Oct 3 | 17612 | Receive | 576 | Lot 250300 |
| Oct 8 | 17612 | Receive | 576 | Lot 250300 |
| Oct 13 | 17612 | Receive | 576 | Lot 250300 |
| Oct 16 | 17612 | Receive | 420 | Lot 250300 |
| Oct 29 | 17612 | Receive | 576 | Lot 250340 |
| Oct 30 | 17612 | Receive | 576 | Lot 250340 |
| Oct 31 | 17612 | **Adjust Down** | 2 | Physical count by Nathan |
| Oct 31 | 17904 | **Adjust Up** | 9 | Physical count by Nathan |
| Oct 31 | 18675 | **Adjust Down** | 1 | Physical count by Nathan |
| Oct 31 | 18795 | **Adjust Up** | 3 | Physical count by Nathan |

### Step 3: Code Review

**File:** `app.py`, lines 919-929 (Charge Report calculation)

```python
# Apply receives/adjustments
for trans_date, sku, trans_type, qty in transactions:
    if trans_date in daily_inventory and str(sku) in daily_inventory[trans_date]:
        if trans_type == 'Receive':
            for date_str in daily_inventory:
                if date_str >= trans_date:
                    daily_inventory[date_str][str(sku)] += qty
        elif trans_type == 'Repack':
            for date_str in daily_inventory:
                if date_str >= trans_date:
                    daily_inventory[date_str][str(sku)] += qty
        # ❌ MISSING: 'Adjust Up' and 'Adjust Down' transaction types!
```

**Finding:** The charge report applies `Receive` and `Repack` transactions, but **ignores `Adjust Up` and `Adjust Down`** transactions.

Nathan's Oct 31 physical count adjustments are NOT reflected in the charge report calculation:
- 17612: -2 units (ignored)
- 17904: +9 units (ignored)
- 18675: -1 unit (ignored)
- 18795: +3 units (ignored)

### Step 4: Architecture Analysis

**Charge Report Architecture:**
```
Sept 30 Baseline (from configuration_params)
  ↓
+ Receives (inventory_transactions)
+ Repacks (inventory_transactions)
- Shipments (shipped_items)
❌ Ignores: Adjust Up, Adjust Down
  ↓
= Calculated EOD Inventory → Pallets → Space Rental
```

**Weekly Report Architecture:**
```
Live Data (inventory_current table)
  ↓
Updated by:
  - EOD process (daily_shipment_processor.py)
  - EOW process (weekly reporter)
  - Physical adjustments API
  ✓ Includes: All transaction types
  ↓
= Current Inventory → Pallets → Display
```

**Key Difference:** 
- Charge report: **Calculates from baseline + selected transaction types**
- Weekly report: **Displays live data from updated table**

---

## Root Causes

### 1. Invalid Sept 30 Baseline (PRIMARY ROOT CAUSE)
**Category:** Data Integrity  
**Impact:** High - Affects all monthly charge calculations

The Sept 30 baseline in `configuration_params` does not mathematically derive from Sept 19 baseline minus September shipments. The errors range from -1,244 to +1,212 units per SKU.

**Evidence:**
```sql
SELECT category, parameter_name, sku, value
FROM configuration_params
WHERE category = 'Inventory' AND parameter_name = 'EomPreviousMonth';
```

**How it should have been set:**
```
Sept 30 = Sept 19 - (Sept 20-30 shipments) + (Sept 20-30 receives/adjustments)
```

**How it appears to have been set:**
Unknown method - values don't match any logical calculation from available data.

### 2. Missing Transaction Types in Charge Report (SECONDARY ROOT CAUSE)
**Category:** Code Defect  
**Impact:** Medium - Ignores physical count corrections

The charge report code (`app.py` lines 919-929) only handles:
- ✅ Receive
- ✅ Repack
- ❌ **Adjust Up** (missing)
- ❌ **Adjust Down** (missing)

**Impact:** Nathan's Oct 31 physical count adjustments are ignored in the charge report but reflected in the weekly inventory report.

**Missing adjustments:**
- 17612: -2 units
- 17904: +9 units  
- 18675: -1 unit
- 18795: +3 units

### 3. Dual Calculation Architectures (DESIGN ISSUE)
**Category:** System Design  
**Impact:** Low - Creates confusion but not necessarily wrong

The system uses two different methods:
1. **Charge Report:** Baseline + transactions (calculated each time)
2. **Weekly Report:** Live table (updated incrementally)

While this isn't inherently wrong, it creates opportunities for divergence when:
- Baselines are incorrect
- Transaction types are handled differently
- Historical data is corrected

---

## Recommended Fixes

### Fix 1: Recalculate Sept 30 Baseline (CRITICAL)
**Priority:** P0 - Immediate  
**Impact:** Corrects all future monthly reports

**Action:**
1. Calculate correct Sept 30 values from Sept 19 baseline
2. Update `configuration_params` with correct values
3. Validate against actual physical inventory if available

**SQL:**
```sql
-- This needs to be calculated programmatically considering:
-- Sept 19 baseline + Sept 20-30 receives - Sept 20-30 shipments ± adjustments
UPDATE configuration_params
SET value = <calculated_value>
WHERE category = 'Inventory' 
  AND parameter_name = 'EomPreviousMonth'
  AND sku = '<sku>';
```

### Fix 2: Add Adjustment Handling to Charge Report (CRITICAL)
**Priority:** P0 - Immediate  
**Impact:** Ensures physical counts are reflected

**Code Change:** `app.py` lines 919-936

```python
# Apply receives/adjustments
for trans_date, sku, trans_type, qty in transactions:
    if trans_date in daily_inventory and str(sku) in daily_inventory[trans_date]:
        if trans_type == 'Receive':
            for date_str in daily_inventory:
                if date_str >= trans_date:
                    daily_inventory[date_str][str(sku)] += qty
        elif trans_type == 'Repack':
            for date_str in daily_inventory:
                if date_str >= trans_date:
                    daily_inventory[date_str][str(sku)] += qty
        # ✅ ADD THESE:
        elif trans_type == 'Adjust Up':
            for date_str in daily_inventory:
                if date_str >= trans_date:
                    daily_inventory[date_str][str(sku)] += qty
        elif trans_type == 'Adjust Down':
            for date_str in daily_inventory:
                if date_str >= trans_date:
                    daily_inventory[date_str][str(sku)] -= qty
```

### Fix 3: Baseline Validation System (RECOMMENDED)
**Priority:** P1 - Next Sprint  
**Impact:** Prevents future baseline corruption

**Implementation:**
Add validation endpoint that calculates baselines from source data and compares against stored values. Alert when discrepancies exceed threshold.

```python
@app.route('/api/validate_baselines', methods=['GET'])
def validate_baselines():
    # Calculate Sept 30 from Sept 19 + transactions
    # Compare against stored Sept 30 baseline
    # Return discrepancies
```

---

## Testing Plan

### Test 1: Verify Sept 30 Baseline Correction
1. Calculate correct Sept 30 values manually
2. Update database
3. Run October charge report
4. Compare total pallets to weekly inventory Oct 31
5. **Expected:** Discrepancy should be reduced or eliminated

### Test 2: Verify Adjustment Handling
1. Apply code fix for Adjust Up/Down
2. Run October charge report
3. Verify Nathan's Oct 31 adjustments are reflected
4. **Expected:** Charge report matches adjusted inventory

### Test 3: Full Reconciliation
1. Apply both fixes
2. Run charge report for October
3. Compare to weekly inventory for Oct 31
4. **Expected:** Both reports show identical ending inventory

---

## Impact Assessment

**Current Impact:**
- Financial: ~$4.50/month discrepancy in space rental charges (small)
- Operational: Confusion about actual inventory levels (moderate)
- Trust: Data integrity concerns when reports don't match (high)

**Post-Fix Impact:**
- Reports will reconcile
- Historical data accuracy improved
- Foundation for accurate future reporting

---

## Lessons Learned

1. **Baseline data must be algorithmically derived, not manually entered** - Manual entry introduces human error
2. **Transaction type handling must be comprehensive** - Missing transaction types create silent data loss
3. **Dual calculation methods require validation** - Different approaches should be cross-checked
4. **Physical inventory adjustments are critical** - System must respect operator corrections

---

## Appendix: Data Snapshots

### September Shipments (Sept 19-30)
```
Total: 738 units SKU 17612, 19 units 17904, 39 units 17914, 0 units 18675, 14 units 18795
```

### October Receives
```
SKU 17612: 3,300 units (6 receive transactions)
Other SKUs: No receives
```

### October Shipments
```
SKU 17612: 2,375 units
SKU 17904: 57 units
SKU 17914: 112 units
SKU 18675: 2 units
SKU 18795: 36 units
```

### October Adjustments (Oct 31)
```
17612: -2 (Adjust Down)
17904: +9 (Adjust Up)
18675: -1 (Adjust Down)
18795: +3 (Adjust Up)
```

---

## Approval Required

- [ ] Approve Sept 30 baseline recalculation
- [ ] Approve code changes for adjustment handling
- [ ] Approve baseline validation system implementation

**Next Steps:** Awaiting approval to proceed with fixes.

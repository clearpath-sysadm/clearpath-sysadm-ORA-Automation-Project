# Root Cause Analysis: October Charge Report 7-Pallet Discrepancy

**Date:** November 3, 2025  
**Issue:** October month-end charge report shows 107 pallets ($46.80) vs. Weekly inventory EOD Oct 31 showing 97 pallets ($43.65)  
**Discrepancy:** 10 pallets ($4.50 overcharge)  
**Severity:** HIGH - Billing accuracy issue

---

## 📊 Issue Summary

The monthly charge report for October shows:
- **107 pallets × $0.45/pallet = $48.15** (reported)

The weekly inventory report for EOD Friday Oct 31 shows:
- **97 pallets × $0.45/pallet = $43.65** (actual current inventory)

**Difference: 10 pallets = $4.50 overcharge**

---

## 🔍 Investigation

### Current Inventory (EOD Oct 31) - From `inventory_current` Table

| SKU | Quantity | Units/Pallet | Pallets (ceil) |
|-----|----------|--------------|----------------|
| 17612 | 1,237 | 48 | 26 |
| 17904 | 401 | 81 | 5 |
| 17914 | 1,256 | 80 | 16 |
| 18675 | 711 | 48 | 15 |
| 18795 | 7,671 | 222 | 35 |
| **TOTAL** | | | **97 pallets** ✓ |

**This matches the weekly inventory report.**

### Baseline Verification - Sept 19 vs. Sept 30

The system has **TWO DIFFERENT BASELINES**:

#### 1️⃣ September 19 Baseline (`InitialInventory.EOD_Prior_Week`)
Used by: `inventory_current` table, weekly reports

| SKU | Sept 19 Baseline |
|-----|------------------|
| 17612 | 1,019 |
| 17904 | 468 |
| 17914 | 1,410 |
| 18675 | 714 |
| 18795 | 7,719 |

#### 2️⃣ September 30 Baseline (`Inventory.EomPreviousMonth`)
Used by: Monthly charge report

| SKU | Sept 30 Baseline | Difference from Sept 19 |
|-----|------------------|-------------------------|
| 17612 | 1,493 | **+474** ⚠️ |
| 17904 | 59 | **-409** ⚠️ |
| 17914 | 127 | **-1,283** ⚠️ |
| 18675 | 738 | **+24** ⚠️ |
| 18795 | 7,799 | **+80** ⚠️ |

---

## 🎯 Root Cause

**The monthly charge report uses a DIFFERENT baseline (Sept 30) than the weekly inventory report (Sept 19).**

### Calculation Proof

**Weekly Inventory (Sept 19 baseline):**
```
SKU 17612: 1,019 + 3,300 receives - 14 adjust down - 3,068 shipped = 1,237 ✓
SKU 17904: 468 + 9 adjust up - 76 shipped = 401 ✓
SKU 17914: 1,410 - 154 shipped = 1,256 ✓
SKU 18675: 714 - 1 adjust down - 2 shipped = 711 ✓
SKU 18795: 7,719 + 2 net adjust - 50 shipped = 7,671 ✓

Total: 97 pallets (ceiling) = $43.65
```

**Monthly Charge Report (Sept 30 baseline + only October transactions):**
```
SKU 17612: 1,493 + 3,300 receives - 14 adjust - 2,375 Oct shipped = 2,404
SKU 17904: 59 + 9 adjust - 58 Oct shipped = 10
SKU 17914: 127 - 118 Oct shipped = 9
SKU 18675: 738 - 1 adjust - 2 Oct shipped = 735
SKU 18795: 7,799 + 2 net adjust - 36 Oct shipped = 7,765

Expected pallets (ceiling):
- 17612: 2,404 / 48 = 51 pallets
- 17904: 10 / 81 = 1 pallet
- 17914: 9 / 80 = 1 pallet
- 18675: 735 / 48 = 16 pallets
- 18795: 7,765 / 222 = 35 pallets

Total: 104 pallets = $46.80
```

**User Reported:** 107 pallets ($48.15)  
**Expected from BOM calc:** 104 pallets ($46.80)  
**Actual current inventory:** 97 pallets ($43.65)

---

## 💥 Impact

### Billing Impact
- **October overcharge:** $4.50 (if charge report showed $48.15 vs. actual $43.65)
- **Pattern:** Likely affects ALL monthly charge reports since Sept 30

### Inventory Tracking Impact
- **Weekly inventory:** CORRECT (uses Sept 19 baseline consistently)
- **Monthly charge report:** INCORRECT (uses Sept 30 baseline, ignores Sept 19-30 activity)

### Data Integrity Impact
- **Missing shipments:** All shipments from Sept 19-30 are NOT accounted for in monthly report starting inventory
- **Two sources of truth:** System has conflicting baseline dates

---

## 🔧 Root Cause Details

### Code Location
**File:** `src/services/reporting_logic/monthly_report_generator.py`  
**Function:** `generate_monthly_charge_report()`  
**Line:** 113

```python
daily_inventory_df = inventory_calculations.calculate_daily_inventory(
    start_of_month_inventory,  # ❌ Uses EomPreviousMonth (Sept 30)
    all_daily_transactions,
    all_dates
)
```

**File:** `src/shipstation_reporter.py`  
**Line:** 104

```python
monthly_report_df, monthly_totals_df = monthly_report_generator.generate_monthly_charge_report(
    rates,
    pallet_counts,
    eom_previous_month_data,  # ❌ WRONG BASELINE
    inventory_transactions_df,
    shipped_items_df,
    shipped_orders_df,
    current_report_year,
    current_report_month,
    key_skus_list
)
```

### Database Configuration
**Table:** `configuration_params`

```sql
-- CORRECT baseline (Sept 19) - used by weekly reports
category: 'InitialInventory', parameter_name: 'EOD_Prior_Week'

-- INCORRECT baseline (Sept 30) - used by monthly reports  
category: 'Inventory', parameter_name: 'EomPreviousMonth'
```

---

## ✅ Solution

### Option 1: Use Consistent Baseline (RECOMMENDED)

**Change monthly report to use Sept 19 baseline like weekly reports:**

```python
# In src/shipstation_reporter.py
monthly_report_df, monthly_totals_df = monthly_report_generator.generate_monthly_charge_report(
    rates,
    pallet_counts,
    initial_inventory,  # ✅ Use Sept 19 baseline instead of eom_previous_month_data
    inventory_transactions_df,
    shipped_items_df,
    shipped_orders_df,
    current_report_year,
    current_report_month,
    key_skus_list
)
```

**Why this works:**
- Both reports calculate from the same baseline (Sept 19)
- `inventory_current` table is already calculated from Sept 19
- Eliminates dual baseline confusion
- EOD Oct 31 from monthly report will match weekly inventory

### Option 2: Remove EomPreviousMonth Entirely

**Delete the incorrect baseline from configuration:**

```sql
DELETE FROM configuration_params
WHERE category = 'Inventory' AND parameter_name = 'EomPreviousMonth';
```

**Then always use `InitialInventory.EOD_Prior_Week` (Sept 19) as the single source of truth.**

---

## 📝 Verification Steps

After implementing the fix:

1. **Regenerate October charge report** with Sept 19 baseline
2. **Verify Oct 31 EOD inventory** matches `inventory_current` table:
   - Expected: 97 pallets ($43.65)
3. **Compare with weekly inventory** - should now match exactly
4. **Audit previous months** - Check if September had same issue
5. **Document baseline policy** - Establish Sept 19 as permanent baseline

---

## 🎓 Lessons Learned

1. **Single Source of Truth:** Never maintain two different baselines for the same data
2. **Data Validation:** Cross-check monthly vs. weekly reports for consistency
3. **Baseline Documentation:** Clearly document which baseline date is authoritative
4. **Configuration Naming:** `EomPreviousMonth` is ambiguous - should specify exact date

---

## 📋 Action Items

| Task | Priority | Owner | Due Date |
|------|----------|-------|----------|
| Update monthly report to use Sept 19 baseline | **HIGH** | Developer | Immediate |
| Delete EomPreviousMonth configuration | **HIGH** | Developer | Immediate |
| Regenerate October charge report | **HIGH** | Developer | Immediate |
| Audit September charge report accuracy | **MEDIUM** | Analyst | This week |
| Add baseline validation test | **MEDIUM** | Developer | This week |
| Document baseline policy in `replit.md` | **LOW** | Developer | This week |

---

## 🔢 Technical Appendix

### Complete Inventory Reconciliation (Sept 19 → Oct 31)

**SKU 17612:**
```
Sept 19 baseline:     1,019
Receives (Oct):      +3,300
Adjust Down (Oct):      -14
Total shipped:       -3,068 (693 in Sept, 2,375 in Oct)
--------------------------------------
Oct 31 EOD:           1,237 ✓
Pallets (ceiling):       26
```

**SKU 17904:**
```
Sept 19 baseline:       468
Adjust Up (Oct):         +9
Total shipped:          -76 (18 in Sept, 58 in Oct)
--------------------------------------
Oct 31 EOD:             401 ✓
Pallets (ceiling):        5
```

**SKU 17914:**
```
Sept 19 baseline:     1,410
Total shipped:         -154 (36 in Sept, 118 in Oct)
--------------------------------------
Oct 31 EOD:           1,256 ✓
Pallets (ceiling):       16
```

**SKU 18675:**
```
Sept 19 baseline:       714
Adjust Down (Oct):       -1
Total shipped:           -2 (0 in Sept, 2 in Oct)
--------------------------------------
Oct 31 EOD:             711 ✓
Pallets (ceiling):       15
```

**SKU 18795:**
```
Sept 19 baseline:     7,719
Adjust Net (Oct):        +2
Total shipped:          -50 (14 in Sept, 36 in Oct)
--------------------------------------
Oct 31 EOD:           7,671 ✓
Pallets (ceiling):       35
```

**TOTAL: 97 pallets × $0.45 = $43.65** ✓

---

**RCA Completed By:** System Analysis  
**Date:** November 3, 2025  
**Status:** Root cause identified, solution proposed, pending implementation

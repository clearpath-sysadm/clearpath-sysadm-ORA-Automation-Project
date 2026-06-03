# May 2026 Charge Report Reconciliation Analysis

**Date:** June 3, 2026  
**Source of Truth:** ShipStation pivot table (`shipstation_report_pivot_1780489406243.csv`)  
**Charge Report:** `charge_report_2026-06-02_(1)_1780489406243.csv`

---

## Overall Discrepancy Summary (CR − SS Pivot)

| SKU | Charge Report | SS Pivot | Gap | Status |
|-----|--------------|----------|-----|--------|
| 17612 | 2,011 | 2,014 | **−3** | CR under SS — investigation pending |
| 17904 | 59 | 58 | **+1** | CR over SS — investigation pending |
| 17914 | 118 | 87 | **+31** | CR over SS — ghost fix pending |
| 18675 | 127 | 113 | **+14** | CR over SS — partially addressed |
| 18795 | 23 | 23 | **0** | ✅ RECONCILED (June 3, 2026) |

---

## Root Cause: Ghost Bare-SKU Rows

A "ghost row" occurs when `shipped_items` contains **both**:
- A bare `sku_lot` (e.g. `17914`) — no lot number
- A lot-stamped `sku_lot` (e.g. `17914 - 250297`) — correct lot number

for the **same `order_number` + `base_sku`**. This causes double-counting in the charge report.

**Origin:** The `_resync_shipped_items_for_order` function (before the Task #102 fix) could write a bare row from a first pass, then a lot-stamped row from a subsequent pass without deleting the original, leaving both rows in `shipped_items`.

**Secondary issue:** Some orders have bare-only rows (no lot-stamped pair) where SS returned a unit without a lot number in the `cf1` field. These don't cause count discrepancies but lose lot traceability and must be corrected via lot lookup.

---

## Ghost Rows Identified (24 orders)

| Date | SKU | Order | Delete (Ghost) | Keep | Units Removed | Type |
|------|-----|-------|----------------|------|---------------|------|
| May 1 | 17612 | 862728 | `17612 - 260047` (5) | `17612` (6) | 5 | REVIEW |
| May 7 | 17914 | 862842 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |
| May 7 | 17914 | 862843 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |
| May 7 | 18795 | 862834 | `18795` (1) | `18795 - 11001` (1) | 1 | ✅ DONE |
| May 8 | 17612 | 862917 | `17612` (1) | `17612 - 260047` (1) | 1 | STANDARD |
| May 8 | 17914 | 862915 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |
| May 8 | 17914 | 862918 | `17914 - 250297` (12) | `17914` (15) | 12 | REVIEW |
| May 8 | 18795 | 862906 | `18795` (1) | `18795 - 11001` (1) | 1 | ✅ DONE |
| May 8 | 18795 | 862912 | `18795` (1) | `18795 - 11001` (1) | 1 | ✅ DONE |
| May 14 | 17914 | 863055 | `17914` (2) | `17914 - 250297` (2) | 2 | STANDARD |
| May 14 | 17914 | 863057 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |
| May 15 | 17612 | 863064 | `17612` (2) | `17612 - 260082` (2) | 2 | STANDARD |
| May 15 | 17612 | 863109 | `17612 - 260082` (1) | `17612` (3) | 1 | REVIEW |
| May 15 | 17914 | 863099 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |
| May 22 | 18675 | 863246 | `18675` (1) | `18675 - 240231` (1) | 1 | STANDARD |
| May 22 | 18795 | 863238 | `18795` (1) | `18795 - 11001` (1) | 1 | ✅ DONE |
| May 26 | 17612 | 863264 | `17612 - 260082` (1) | `17612` (5) | 1 | REVIEW |
| May 26 | 17612 | 863265 | `17612 - 260082` (1) | `17612` (5) | 1 | REVIEW |
| May 26 | 17914 | 863266 | `17914` (3) | `17914 - 250297` (3) | 3 | STANDARD |
| May 26 | 18795 | 863252 | `18795` (1) | `18795 - 11001` (1) | 1 | ✅ DONE |
| May 28 | 17612 | 863350 | `17612` (1) | `17612 - 260082` (1) | 1 | STANDARD |
| May 28 | 17914 | 863336 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |
| May 28 | 18675 | 863337 | `18675` (1) | `18675 - 240231` (1) | 1 | STANDARD |
| May 29 | 17914 | 863359 | `17914` (1) | `17914 - 250297` (1) | 1 | STANDARD |

**STANDARD** = delete the bare row (lot-stamped has equal or more units — clear ghost).  
**REVIEW** = bare row has more units than lot-stamped — requires manual SS verification before deleting.  
**✅ DONE** = completed June 3, 2026.

---

## Ghost Fix Impact vs. Reconciliation Target

### SKU 18795 — ✅ FULLY RECONCILED (June 3, 2026)

**Actions taken:**
1. Deleted 5 bare ghost rows (orders 862834, 862906, 862912, 863238, 863252) — removed 5 units
2. Updated 7 bare-only rows to `18795 - 11001` (orders 862939, 862947, 862981, 863135, 863155, 862908 items, and others on May 11/12/18/19) — lot traceability restored, counts unchanged

| Date | CR−SS Before | Removed | CR−SS After |
|------|-------------|---------|-------------|
| May 7 | +1 | −1 | 0 |
| May 8 | +2 | −2 | 0 |
| May 22 | +1 | −1 | 0 |
| May 26 | +1 | −1 | 0 |
| **TOTAL** | **+5** | **−5** | **0 ✓** |

**Final state:** 23 units, all rows lot-stamped `18795 - 11001`, zero bare rows remaining, matches SS pivot exactly.

---

### SKU 17914 — ⚠️ Ghost fix partially reconciles (+7 remains)

| Date | CR−SS Before | Removed | CR−SS After |
|------|-------------|---------|-------------|
| May 1 | +1 | 0 | **+1** |
| May 7 | +2 | −2 | 0 |
| May 8 | +13 | −13 | 0 |
| May 14 | +3 | −3 | 0 |
| May 15 | +1 | −1 | 0 |
| May 26 | +4 | −3 | **+1** |
| May 27 | +5 | 0 | **+5** |
| May 28 | +1 | −1 | 0 |
| May 29 | +1 | −1 | 0 |
| **TOTAL** | **+31** | **−24** | **+7** |

**Remaining gaps require separate investigation:**
- May 27 +5: No ghost rows found — different root cause unknown
- May 1 +1: No ghost rows found — different root cause unknown
- May 26 +1: One extra unit beyond identified ghost rows

---

### SKU 18675 — ⚠️ Ghost fix barely helps (+12 remains)

| Date | CR−SS Before | Removed | CR−SS After |
|------|-------------|---------|-------------|
| May 22 | +1 | −1 | 0 |
| May 28 | +1 | −1 | 0 |
| May 29 | +12 | 0 | **+12** |
| **TOTAL** | **+14** | **−2** | **+12** |

**May 29 +12:** DB shows 24 units vs SS 12 for lot `18675 - 260052`. Both rows are lot-stamped — this is a **double-write** issue, not a bare/lot ghost. Requires separate investigation.

---

### SKU 17612 — ❌ Ghost fix moves in wrong direction

The overall gap is already −3 (CR under SS). Removing ghost rows reduces CR further.

| Date | CR−SS Before | Ghost Action | CR−SS After |
|------|-------------|--------------|-------------|
| May 1 | 0 (match) | −5 (862728 REVIEW) | **−5** ← NEW problem |
| May 5 | −1 | 0 | −1 |
| May 8 | −4 | −1 (862917) | **−5** ← gets worse |
| May 11 | −6 | 0 | −6 |
| May 12 | +6 | 0 | +6 |
| May 15 | +3 | −3 (863064+863109) | 0 ✓ |
| May 26 | +8 | −2 (863264+863265) | +6 |
| May 27 | +5 | 0 | +5 |
| May 28 | −12 | −1 (863350) | **−13** ← gets worse |
| May 29 | −2 | 0 | −2 |
| **TOTAL** | **−3** | **−12** | **−15** |

**Root causes for 17612 under-count:**
- May 28 −12: `17613 → 17612` promo SKU remapping not applied for 13 units in the resync
- May 11 −6, May 8 −4, May 5 −1, May 29 −2: Under-counted dates not explained by ghost rows

The 17612 REVIEW cases (863109, 863264, 863265, 862728) keep bare rows with no lot number — these should be verified against SS before any action.

---

### SKU 17904 — ❌ Not addressed (+1 remains)

May 1 shows CR=2, SS=1. No ghost rows identified for 17904. Requires order-level investigation.

---

## Recommended Actions

| Status | SKU | Action |
|--------|-----|--------|
| ✅ Complete | **18795** | Ghost deletes + bare row lot-stamping — fully reconciled |
| 🔜 Next | **17914** | Apply 9 STANDARD ghost deletes (862842, 862843, 862915, 863055, 863057, 863099, 863266, 863336, 863359) — removes 13 units, gap −13 |
| 🔜 Next | **17914** | Apply REVIEW order 862918 after SS verification (removes 12 more units, gap −12) |
| 🔍 Investigate | **17914** | May 27 +5, May 1 +1 — no ghost rows, unknown cause |
| 🔍 Investigate | **18675** | May 29 +12: double-write on lot-stamped row `18675 - 260052` |
| 🔍 Investigate | **18675** | Apply 2 STANDARD ghost deletes (863246, 863337) after May 29 is resolved |
| 🔍 Investigate | **17612** | May 28 −12: rerun promo SKU remapping resync for May 28 before touching ghost rows |
| ⚠️ Hold | **17612** | Ghost deletes worsen overall balance — must fix remapping gap first |
| 🔍 Investigate | **17904** | May 1 +1: identify the extra order in DB not in SS |

---

## Ghost Detection SQL

```sql
SELECT
    ship_date, base_sku, order_number,
    COUNT(*)                                                                        AS row_count,
    SUM(quantity_shipped)                                                           AS total_db_units,
    STRING_AGG(sku_lot || ' (' || quantity_shipped::text || ')', ', '
               ORDER BY sku_lot)                                                    AS sku_lots,
    SUM(quantity_shipped) FILTER (WHERE sku_lot NOT LIKE '% - %')                  AS bare_units,
    SUM(quantity_shipped) FILTER (WHERE sku_lot LIKE '% - %')                      AS lot_units
FROM shipped_items
WHERE ship_date BETWEEN '2026-05-01' AND '2026-05-31'
  AND base_sku IN ('17612','17904','17914','18675','18795')
GROUP BY ship_date, base_sku, order_number
HAVING COUNT(*) FILTER (WHERE sku_lot NOT LIKE '% - %') > 0
   AND COUNT(*) FILTER (WHERE sku_lot LIKE '% - %')     > 0
ORDER BY ship_date, base_sku, order_number;
```

---

## SKU 18795 Fix — Execution Queries (Completed June 3, 2026)

### Step 1: Verify rows before deleting

```sql
SELECT
    'BEFORE'                            AS timing,
    ship_date,
    order_number,
    sku_lot,
    quantity_shipped
FROM shipped_items
WHERE base_sku = '18795'
  AND ship_date BETWEEN '2026-05-01' AND '2026-05-31'
  AND order_number IN ('862834', '862906', '862912', '863238', '863252')
ORDER BY ship_date, order_number, sku_lot;
```

Result: 10 rows (2 per order — 1 bare + 1 lot-stamped), 10 units total. ✅ Confirmed.

### Step 2: Execute the ghost delete

```sql
DELETE FROM shipped_items
WHERE base_sku = '18795'
  AND sku_lot = '18795'
  AND order_number IN ('862834', '862906', '862912', '863238', '863252');
```

Result: 5 rows deleted. ✅ Confirmed.

### Step 3: Stamp lot on remaining bare rows

```sql
UPDATE shipped_items
SET sku_lot = '18795 - 11001'
WHERE base_sku = '18795'
  AND sku_lot = '18795'
  AND ship_date BETWEEN '2026-05-01' AND '2026-05-31';
```

Result: 7 rows updated (May 11, 12, 18, 19). ✅ Confirmed.  
Basis: Lot `11001` is the only active lot for SKU 18795 (received 2025-09-19, all other lots inactive).

### Step 4: Final validation

```sql
SELECT
    ship_date,
    SUM(quantity_shipped)                                                           AS total_units,
    COUNT(*) FILTER (WHERE sku_lot NOT LIKE '% - %')                               AS bare_rows_remaining,
    STRING_AGG(DISTINCT sku_lot, ', ' ORDER BY sku_lot)                            AS lots_used
FROM shipped_items
WHERE base_sku = '18795'
  AND ship_date BETWEEN '2026-05-01' AND '2026-05-31'
GROUP BY ship_date
ORDER BY ship_date;
```

Result: 15 rows, all `✅ lot-stamped`, 23 total units, 0 bare rows, all `18795 - 11001`. ✅ Confirmed.

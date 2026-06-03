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

**May 11 BigCommerce orphan discovery (cross-SKU finding):** During 17612 investigation, 16 BigCommerce orders (100635–100650, SS IDs 285310338–285315361) were found in `shipped_orders` with no `orders_inbox` entry. All 16 have `shipped_items` rows for `18675 - 240231` (1 unit each = 16 units). These are counted in both CR and SS so they do not create a discrepancy, but the absence of `orders_inbox` entries indicates these orders bypassed the normal import flow entirely (BigCommerce migration artifact). No action needed for charge report correctness, but flagged as data quality gap.

---

### SKU 17612 — 🔍 Investigation in progress

The overall gap is −3 (CR under SS). Multiple opposing forces are at play — the ghost row fix alone would make the balance worse. Root causes must be addressed by type.

#### Date-by-date breakdown

| Date | CR−SS | Root Cause | Status |
|------|-------|------------|--------|
| May 5 | −1 | Orders never synced into `shipped_orders` — not visible to DB at all | ✅ Diagnosed — SS verification needed |
| May 8 | −4 (true −5) | Orders never synced into `shipped_orders` + ghost 862917 masks 1 unit | ✅ Diagnosed — SS verification needed |
| May 11 | −6 | Orders never synced into `shipped_orders` — BigCommerce orphan theory ruled out | ✅ Diagnosed — SS verification needed |
| May 12 | +6 | 3 bare-only rows (862946=6, 862947=6, 862954=2) — not ghost pairs, likely qty mismatch vs SS | 🔍 Pending SS verification |
| May 15 | +3 | Ghost rows: 863064 (STANDARD, 2 units) + 863109 (REVIEW, 1 unit) | ✅ Identified — fix ready |
| May 26 | +8 | Order 833686 BigCommerce migration noise (6 units) + ghost REVIEW 863264+863265 (2 units) | ⏳ Awaiting Oracare confirmation |
| May 27 | +5 | 1 bare row + 1 malformed `17612-260082` sku_lot — order-level detail pending | 🔍 Pending |
| May 28 | −12 | 13 units of `base_sku=17613` not remapped to 17612 (8 orders, all bare) | ✅ Identified — fix ready |
| May 29 | −2 | 2 units of `base_sku=17613` not remapped to 17612 (2 orders, all bare) | ✅ Identified — fix ready |

#### Under-count analysis

**May 5 −1, May 8 −4, May 11 −6 — orders never synced to DB**

Investigation confirmed these are NOT caused by:
- Unremapped 17613 rows (none exist on these dates)
- Missing `orders_inbox` entries (all orders in `shipped_orders` for May 5/8 have `orders_inbox` records)
- BigCommerce orphan orders (the 16 May 11 BigCommerce orders 100635–100650 all contain 18675, not 17612)
- Non-17612 orders being misidentified (May 5 non-17612 orders are 862769/862808 with 17914 only; May 8 non-17612 orders are 862905/862908/862918/862920 with 17914/18795/17904)

**Root cause:** SS has 17612 shipments on these dates that were never synced into `shipped_orders` at all — invisible to all DB queries. These units cannot be recovered without a targeted SS API pull for those dates.

**May 8 note:** Ghost row 862917 (bare `17612` = 1 unit) masks the true gap. True gap = −5, not −4. Do not delete this ghost until the missing units are recovered — it would expose the full −5.

**Impact on remap fix sequencing:** May 28/29 remap adds +15 units to CR (2011→2026). Combined with the unfixable May 5/8/11 under-counts (−11 total), the effective net after remap = +12 over SS. Ghost fixes and the 833686 removal will be needed to bring the balance back down.

**May 28 and May 29 — 17613 not remapped**

DB has 15 units stored as `base_sku = 17613` that SS counts as 17612:
- May 28: 13 units, 8 orders (all bare `17613`) → remap + delete ghost 862917 → DB 86 → 98 = SS ✓
- May 29: 2 units, 2 orders (all bare `17613`) → remap → DB 40 → 42 = SS ✓

#### Over-count analysis

**May 26 — order 833686**
Order number in `833xxx` range; all other May 26 orders are `863xxx`. Confirmed as a BigCommerce migration import ("imported as Shipped"). Contains 6 bare `17612` units with no lot stamp. If SS has no corresponding shipment this is pure noise. **Pending Oracare team confirmation.**

**May 27 — malformed sku_lot + bare row**
`17612-260082` (no spaces around dash) is present — written by a different code path during the end-of-month transition. Does not affect `base_sku` count directly but is a data quality issue. 1 additional bare row also present. Order-level detail needed to identify the full +5 source.

**May 12 +6 — bare-only rows**
Orders 862946 (6 units), 862947 (6 units), 862954 (2 units) are bare `17612` with no lot-stamped counterpart — NOT ghost rows. These 14 bare units represent real DB entries. The +6 over-count vs SS means SS shows 6 fewer units on May 12. Possible causes: orders in DB that SS doesn't recognise as May 12 shipments, or quantity mismatches. Requires SS-level verification of these 3 orders.

**May 15 +3 — identified and ready to fix**
Ghost row 863064 (STANDARD: delete bare 2 units) and ghost REVIEW 863109 (bare=3, lot=1 — verify in SS before deleting lot row).

#### What NOT to do yet

Do not apply any ghost deletes for 17612 until:
1. The missing record root cause for May 5/8/11 is understood and corrected (adding units will offset the over-count fixes)
2. May 28/29 remap fixes are applied first (adds 15 units to CR, shifts balance from −3 to +12 before any deletions)
3. May 26 order 833686 is confirmed by Oracare

#### Missing record investigation SQL

```sql
-- Orders in shipped_orders with 17612/17613 items that have NO shipped_items row
SELECT
    so.order_number,
    so.ship_date,
    so.shipstation_order_id,
    so.status,
    oii.sku,
    oii.quantity
FROM shipped_orders so
JOIN order_items_inbox oii ON oii.order_number = so.order_number
WHERE so.ship_date IN ('2026-05-05', '2026-05-08', '2026-05-11')
  AND oii.sku IN ('17612', '17613')
  AND NOT EXISTS (
      SELECT 1 FROM shipped_items si
      WHERE si.order_number = so.order_number
        AND si.base_sku IN ('17612', '17613')
  )
ORDER BY so.ship_date, so.order_number;
```

```sql
-- May 12 bare orders — cross-check shipstation_order_id for SS verification
SELECT
    so.order_number,
    so.shipstation_order_id,
    so.ship_date,
    so.status,
    si.sku_lot,
    si.quantity_shipped
FROM shipped_items si
JOIN shipped_orders so ON so.order_number = si.order_number
WHERE si.base_sku = '17612'
  AND si.ship_date = '2026-05-12'
  AND si.sku_lot = '17612'
ORDER BY so.order_number;
```

---

### SKU 17904 — ❌ Not addressed (+1 remains)

May 1 shows CR=2, SS=1. No ghost rows identified for 17904. Requires order-level investigation.

---

## Recommended Actions

| Status | SKU | Action |
|--------|-----|--------|
| ✅ Complete | **18795** | Ghost deletes + bare row lot-stamping — fully reconciled |
| 🔜 Next | **17914** | Apply 9 STANDARD ghost deletes (862842, 862843, 862915, 863055, 863057, 863099, 863266, 863336, 863359) — removes 13 units |
| 🔜 Next | **17914** | Verify order 862918 in SS, then apply REVIEW delete (removes 12 more units) |
| 🔍 Investigate | **17914** | May 27 +5, May 1 +1 — no ghost rows found, root cause unknown |
| 🔜 Next | **17612** | Remap May 28 `17613` rows → `17612` (13 units, 8 orders) + delete bare ghost 862917 → net +12 to CR |
| 🔜 Next | **17612** | Remap May 29 `17613` rows → `17612` (2 units, 2 orders) → net +2 to CR |
| ⏳ Awaiting | **17612** | May 26 order 833686 (6 bare units) — BigCommerce migration noise, awaiting Oracare confirmation |
| 🔍 Investigate | **17612** | May 27 +5: order-level detail needed; `17612-260082` malformed sku_lot identified |
| 🔍 Investigate | **17612** | May 5 −1, May 8 −4, May 11 −6, May 12 +6 — root causes unknown |
| ⚠️ Hold | **17612** | Ghost deletes (May 15, May 26) — apply only after remap fixes land and balance is reassessed |
| 🔍 Investigate | **18675** | May 29 +12: double-write on lot-stamped row `18675 - 260052` |
| 🔍 Investigate | **18675** | Ghost deletes 863246 + 863337 (2 units) — apply after May 29 is resolved |
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

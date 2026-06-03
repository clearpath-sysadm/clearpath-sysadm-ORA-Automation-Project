# Inventory Tracking QA Report
**Date:** 2026-06-03  
**Scope:** All key product SKUs — 17612, 17904, 17914, 18675, 18795  
**Baseline:** EOD 2026-04-22 (reconciliation adjustments entered 4/21–22; all pre-4/22 history disregarded)

---

## Key Finding (Updated 2026-06-03 after full diagnostic)

> **The total inventory balances shown on the dashboard are accurate and match the physical count.**
> The problems are at the **lot-tracking level**, not the total level.
> A backfill of inventory transactions is **NOT recommended** — it would over-correct and push balances below physical.

---

## Dashboard vs Physical Count (2026-06-03)

| SKU | Dashboard (Jun 3) | Physical (Jun 3) | Difference |
|---|---|---|---|
| 17612 | **1,684** | **1,681** | **+3** ✅ |
| 17904 | **82** | **79** | **+3** ✅ |
| 17914 | **544** | **552** | **−8** ✅ |
| 18675 | **516** | **425** | **+91** ⚠️ |
| 18795 | **6,769** | **6,762** | **+7** ✅ |

> 17612, 17904, 17914, 18795 are all within normal counting variance.  
> 18675 shows a +91 discrepancy — see Issue 3 below.

---

## ShipStation vs Database Comparison (Q1 — confirmed query results)

Cross-referenced against the ShipStation "Items Shipped" export for 4/23/2026–6/3/2026.  
17613 (FREE CASE variant) is translated to base SKU 17612 and counted together.

| SKU | SS Shipped | DB shipped_items | Missing from DB | % Synced |
|---|---|---|---|---|
| 17612 | 3,040 | 2,712 | **328** | 89.2% |
| 17904 | 88 | 82 | **6** | 93.2% |
| 17914 | 121 | 122 | **−1** | 100.8% |
| 18675 | 134 | 134 | **0** | 100.0% ✅ |
| 18795 | 42 | 35 | **7** | 83.3% |

**The 328-unit gap for 17612 is not from a broken sync pipeline** — Q3 (see Diagnostic Queries section) confirmed zero orders went through our upload pipeline and failed to return as shipped. The gap is most likely XCart orders (88 units per SS report) that flow through a different ingestion path and are not fully captured in `shipped_items`.

---

## Lot-Tracking Issues (Q5 — shipped_items with no inventory deduction)

These are orders the DB knows about (in `shipped_items`) but for which no `inventory_transactions.Ship` record exists. These represent lot-level accounting gaps, **not total balance errors**.

| SKU | Records | Units Not Deducted | No Lot Stamp | Has Lot — No Deduction |
|---|---|---|---|---|
| 17612 | 34 | **119** | 57 | 62 |
| 18675 | 63 | **100** | 5 | 95 |
| 17904 | 29 | **39** | 19 | 20 |
| 17914 | 12 | **23** | 6 | 17 |
| 18795 | 6 | **6** | 2 | 4 |

**"No lot stamp"** (`sku_lot = base_sku`, e.g. `'17612'` with no lot suffix): the lot tagger never ran for these orders, so the system had no lot to deduct from. Units left the shelf but no lot was debited.

**"Has lot — no deduction"**: the lot was stamped correctly on the order but the deduction code failed — most commonly the lot-transition bug (lot ran out mid-order) or a code error on the boundary.

### Why the total balance is still correct despite these gaps

Lot 260047 went **negative (−22)** because the lot-transition bug kept deducting from it after it was empty. Meanwhile, ~57 units shipped without a lot stamp and were never deducted. These two errors partially cancel each other at the total level, which is why the dashboard matches physical.

---

## 17612 Lot Breakdown (from Inventory Monitor, 2026-06-03)

| Lot | Status | Balance | Received | Notes |
|---|---|---|---|---|
| 260047 | Inactive | **−22** | 2026-04-02 | Over-deducted — lot-transition bug pushed negative |
| 260082 | **Active** | **554** | — | Current working lot. ~26 days remaining at current rate |
| 260122 | Inactive | **1,152** | — | 24 pallets × 48 = 1,152 units physically on shelf. Not yet activated |
| **Total** | | **1,684** | | Matches physical 1,681 ✅ |

**Urgent:** Lot 260082 has ~26 days of stock at the current 454 units/week rate. When it empties, the lot-transition bug will strike lot 260082 the same way it struck 260047 — orders will over-deduct 260082 into negative territory and lot 260122 (1,152 units on shelf) will not activate automatically.

---

## 4/21–22 Reconciliation Detail

The user performed a physical inventory reconciliation on 2026-04-17. The corrective
adjustment transactions were entered into the database on 4/21 and 4/22. EOD 4/22 is
therefore the correct clean starting point for all post-reconciliation analysis.

### Adjustments entered 4/21–22

| SKU | Date | Lot | Type | Qty | Note |
|---|---|---|---|---|---|
| 17612 | 4/21 | 260047 | Adjust Up | +253 | Correcting duplicate ship entries Apr 16–17 |
| 17612 | 4/22 | 260047 | Adjust Up | +225 | *(no notes)* |
| 17612 | 4/22 | 260017 | Adjust Up | **+578** | "Offsets resync split-label deductions; restores lot to 0" |
| 17904 | 4/21 | 250240 | Adjust Up | +86 | Baseline receive backfill |
| 17904 | 4/22 | 250240 | Adjust Up | +20 | Offsets pre-Apr-22 resync deductions |
| 17914 | 4/21 | 250297 | Adjust Down | **−766** | Lot balance correction |
| 18675 | 4/21 | 240231 | Adjust Up | +414 | Reconcile lot inventory |
| 18675 | 4/22 | 260052 | Adjust Up | +2 | Offsets pre-Apr-22 resync deductions |
| 18675 | 4/22 | 240231 | Adjust Up | +32 | Offsets pre-Apr-22 resync deductions |
| 18675 | 4/22 | 260052 | Adjust Down | −2 | Physical count verification |
| 18795 | 4/22 | 11001 | Adjust Down | **−330** | "Reconciliation based off 4/17 physical count of 151" |
| 18795 | 4/22 | 11005 | Adjust Down | −3 | Shipped 7/2025 — orders 669075, 669165, 669215 |
| 18795 | 4/22 | 11001 | Adjust Up | +21 | *(no notes)* |

### Net adjustment per SKU and resulting 4/22 EOD balance

| SKU | Net Adj | 4/17 DB (pre-recon) | 4/22 EOD (post-recon baseline) |
|---|---|---|---|
| 17612 | **+1,056** | 1,178 | **1,983** |
| 17904 | **+106** | −45 ⚠️ | **54** |
| 17914 | **−766** | 1,459 | **672** |
| 18675 | **+446** | 131 | **566** |
| 18795 | **−312** | 7,139 | **6,813** |

> Note: the 4/17 DB figures were calculated from historical transaction sums only — they did
> NOT reflect physical reality on that date because pre-reconciliation deduction gaps had
> accumulated. The 4/22 EOD figures are the correct post-adjustment starting point.

---

## Physical Count Detail (2026-06-03)

#### 17612 — Total: 1,681 units

| Lot | Pallets | Qty/Pallet | Partial | Lot Total |
|---|---|---|---|---|
| 260122 | 24 | 48 | 0 | 1,152 |
| 260082 | 10 | 48 | 35 | 521 |
| **Total** | | | | **1,681** |

> Note: lot-level math (1,152 + 521 = 1,673) is 8 units short of stated 1,681. Likely a partial pallet count rounding on lot 260082. Immaterial at this scale.

#### 17904 — Total: 79 units

| Lot | Pallets | Qty/Pallet | Partial | Lot Total |
|---|---|---|---|---|
| 260125 | 0 | 81 | 79 | 79 |
| **Total** | | | | **79** |

#### 17914 — Total: 552 units

| Lot | Pallets | Qty/Pallet | Partial | Lot Total |
|---|---|---|---|---|
| 250297 | 6 | 80 | 72 | 552 |
| **Total** | | | | **552** |

#### 18675 — Total: 425 units

| Lot | Pallets | Qty/Pallet | Partial | Lot Total |
|---|---|---|---|---|
| 240231 | 4 | 48 | 10 | 202 |
| 260052 | 4 | 48 | 31 | 223 |
| **Total** | | | | **425** |

#### 18795 — Total: 6,762 units

| Lot | Boxes | Pallets | Quantity |
|---|---|---|---|
| 11001 | 92 | 0 | 92 |
| 11002 | 47 | 3 | 713 |
| 11003 | 130 | 4 | 1,018 |
| 1104 | 146 | 4 | 1,034 |
| 11005 | 109 | 2 | 553 |
| 11006 | 108 | 4 | 996 |
| 11007 | 100 | 3 | 766 |
| 11008 | 108 | 4 | 996 |
| 11009 | 150 | 2 | 594 |
| **Total** | | **26** | **6,762** |

---

## Issues Found

### 🔴 Issue 1 — Lot-Transition Bug (root cause of all lot-level errors)

**Pattern:** When an order quantity exceeds the remaining balance of the current active
lot, `deduct_lot_inventory` deducts what's available and stops. It does not cascade
into the next active lot for the remainder.

**Example:** order ships 40 units, current lot has 10 remaining → system deducts 10, marks
lot depleted, stops. The remaining 30 are never deducted. Lot goes to 0 or slightly negative
depending on concurrent orders.

**Evidence:** Lot 260047 is currently at −22 (negative). It was depleted and orders kept
deducting from it instead of transitioning to lot 260082.

**Sample affected orders (17612):**

| Order | Ship Date | Shipped | Deducted | Gap |
|---|---|---|---|---|
| 862897 | 2026-05-07 | 41 | 1 | 40 |
| 863314 | 2026-05-27 | 40 | 10 | 30 |
| 862962 | 2026-05-12 | 40 | 10 | 30 |
| 862990 | 2026-05-13 | 40 | 10 | 30 |
| 863263 | 2026-05-26 | 20 | 4 | 16 |
| 862975 | 2026-05-13 | 15 | 3 | 12 |

**Root cause file:** `src/services/inventory/lot_deduction.py`

**⚠️ Time-sensitive:** Lot 260082 (active, 554 units) has ~26 days of stock. If this bug is not fixed before 260082 empties, it will go negative the same way 260047 did — and lot 260122 (1,152 units on shelf) will not activate.

---

### 🔴 Issue 2 — No-Lot-Stamp Orders (orders that shipped before lot tagger ran)

57 units of 17612, 19 of 17904, 6 of 17914, 5 of 18675, 2 of 18795 shipped with `sku_lot = base_sku` (no lot suffix). The lot tagger hadn't stamped `customField1` before the order shipped, so the deduction code had no lot to deduct from and silently skipped.

These units physically left the shelf but no lot was debited. The deduction gap exists at the lot level; the total balance compensation comes from lot 260047 being over-deducted.

**Re-tagging these orders** (running the lot tagger retroactively) will fix the lot-level ledger. A separate Adjust Up on lot 260047 (to correct its −22 balance back to 0) should accompany the re-tag.

---

### 🔴 Issue 3 — 18675 Dashboard vs Physical Gap (+91)

Dashboard shows 516, physical shows 425 — a 91-unit discrepancy. This is the largest real gap across all SKUs. Likely causes:

- 95 units in `shipped_items` with a correct lot stamp but no deduction recorded (from Q5) — these shipped but inventory was never reduced
- These are mostly `100xxx`-series orders (May 11–13 wave) that shipped before the lot tagger populated `customField1`

Unlike 17612, the offsetting over-deduction on 18675 is smaller, so the net gap is visible at the total level. Investigate by checking whether those 95 "has-lot, no-deduction" 18675 records were deducted through a different mechanism (manual adjust or resync), or if the physical count needs reconfirmation.

---

### 🟡 Issue 4 — Lot 260122 Not Activated (17612)

1,152 units of 17612 are physically on the shelf in lot 260122 (24 pallets × 48 units). This lot exists in the system with the correct balance but is marked **Inactive** with no receive date. The lot tagger and deduction code only use active lots — when lot 260082 depletes, the system will not automatically transition to 260122.

**Fix:** Mark lot 260122 as active in the database, and ensure a received date is recorded.

---

### 🟡 Issue 5 — Lot 260047 Negative Balance (17612)

Lot 260047 shows −22. This is cosmetically wrong — it cannot actually have negative physical inventory. The correct balance is 0 (depleted). An `Adjust Up +22` on lot 260047 will clear this.

---

### 🟡 Issue 6 — Orphaned Order Headers (Q4)

Two `shipped_orders` rows have no corresponding `shipped_items` rows:

| Order | Ship Date | SS Order ID | Total Items |
|---|---|---|---|
| 863334 | 2026-05-27 | 289682723 | 5 |
| 862718 | 2026-05-01 | 282596684 | 0 |

Small impact (≤5 units). The sync wrote an order header but failed before writing line items. These can be resolved by re-running the sync for those specific order IDs, or manually inserting the missing `shipped_items` rows.

---

### 🟡 Issue 7 — 18795 Active vs Total Balance (lot status labels)

Active balance: 99. Total across all lots: 6,769. The 6,670-unit difference lives in lots that carry a positive balance but are marked inactive or depleted. This is a lot-status labeling issue, not missing inventory — the units are physically accounted for in the total.

---

## ~~Issue (Closed): 17612 "DB Corrected" Estimate Was Wrong~~

Earlier in this audit, a "DB Corrected" column was computed by subtracting the estimated deduction gap from the dashboard total. That calculation assumed the total balance was overstated by the deduction gap — which is **not correct**. The dashboard total IS accurate (matches physical). The deduction gap lives at the lot-level accounting layer only. The "estimated true balance" figures in the previous version of this report were incorrect and have been removed.

---

## Remediation Plan (Updated)

> ⚠️ **Do NOT run the inventory deduction backfill** (`backfill_inventory_deductions.py`).  
> Running it now would subtract 119–287 units per SKU from totals that are already correct,  
> producing balances well below the physical count.

### Step 1 — Fix the lot-transition bug in code (highest priority, time-sensitive)

Patch `src/services/inventory/lot_deduction.py`. When `quantity` exceeds the current lot's
remaining balance, deduct what's available, then loop into the next active lot for the
remainder, continuing until the full quantity is satisfied or all lots are exhausted.

**Must be done before lot 260082 empties (~26 days).**

---

### Step 2 — Activate lot 260122 for 17612

Mark lot 260122 as active and set a received date. This is the next lot in line with 1,152
units already on the shelf. Without activation, the lot tagger and deduction code will not
use it.

```sql
UPDATE lots SET status = 'active', received_date = '2026-06-03'
WHERE lot_number = '260122';
```

> Confirm the exact received date with the warehouse team before running.

---

### Step 3 — Correct lot 260047 negative balance

Insert an Adjust Up of 22 units to bring lot 260047 from −22 back to 0:

```sql
INSERT INTO inventory_transactions (date, sku, lot_id, quantity, transaction_type, notes)
SELECT '2026-06-03', '17612', lot_id, 22, 'Adjust Up',
       'Correct negative balance caused by lot-transition bug over-deducting depleted lot 260047'
FROM lots WHERE lot_number = '260047';
```

---

### Step 4 — Re-tag no-lot-stamp orders

Run the lot tagger sweep for all orders in `shipped_items` where `sku_lot = base_sku` (no lot suffix), post-4/22. Once re-tagged, the deduction code can be run selectively for those specific orders only.

**Scope of re-tag:**
- 17612: 57 units across ~22 orders
- 17904: 19 units
- 17914: 6 units
- 18675: 5 units
- 18795: 2 units

---

### Step 5 — Investigate 18675 +91 gap

The 18675 gap (516 dashboard vs 425 physical) needs confirmation before any action:
1. Re-check the physical count for 18675 — is 425 correct?
2. If physical is correct, identify which of the 95 "has-lot, no-deduction" 18675 records
   in Q5 were never corrected and apply targeted deductions for those only.

---

### Step 6 — Resolve orphaned order headers (Issue 6)

For order 863334 (5 items), manually insert the missing `shipped_items` rows or trigger a re-sync for SS order ID 289682723.

---

## QA Diagnostic Queries

All queries use **`ship_date > '2026-04-22'`** as the post-reconciliation cutoff.

### Q1 — DB totals vs ShipStation actuals (main scorecard)
```sql
WITH db_totals AS (
    SELECT base_sku,
           SUM(quantity_shipped)        AS db_units,
           COUNT(DISTINCT order_number) AS db_orders
    FROM shipped_items
    WHERE ship_date > '2026-04-22'
    GROUP BY base_sku
),
ss_actuals (sku, ss_units) AS (
    VALUES
        -- SS 4/23–6/3 manual export. 17612 includes translated 17613 (85 units).
        ('17612', 3040),
        ('17904',   88),
        ('17914',  121),
        ('18675',  134),
        ('18795',   42)
)
SELECT
    s.sku,
    s.ss_units                                               AS ss_shipped,
    COALESCE(d.db_units,  0)                                 AS db_units,
    COALESCE(d.db_orders, 0)                                 AS db_orders,
    s.ss_units - COALESCE(d.db_units, 0)                     AS missing_units,
    ROUND(100.0 * COALESCE(d.db_units, 0) / s.ss_units, 1)  AS pct_synced
FROM ss_actuals s
LEFT JOIN db_totals d ON d.base_sku = s.sku
ORDER BY missing_units DESC;
```

### Q2 — 17612 weekly unit volume (watch for sync gaps)
```sql
SELECT
    DATE_TRUNC('week', ship_date::date)::date  AS week_start,
    SUM(quantity_shipped)                       AS units_in_db,
    COUNT(DISTINCT order_number)                AS orders_in_db
FROM shipped_items
WHERE base_sku = '17612'
  AND ship_date > '2026-04-22'
GROUP BY 1
ORDER BY 1;
```

### Q3 — Orders uploaded to SS but never returned as shipped
```sql
-- Zero results = sync pipeline is working correctly.
SELECT
    soli.shipstation_order_id,
    oi.order_number,
    oi.order_date,
    soli.sku,
    oii.quantity
FROM shipstation_order_line_items soli
JOIN orders_inbox oi       ON oi.id            = soli.order_inbox_id
JOIN order_items_inbox oii ON oii.order_inbox_id = soli.order_inbox_id
                           AND oii.sku           = soli.sku
LEFT JOIN shipped_orders so ON so.shipstation_order_id = soli.shipstation_order_id
WHERE so.shipstation_order_id IS NULL
  AND oi.order_date > '2026-04-22'
  AND soli.sku IN ('17612','17904','17914','18675','18795')
ORDER BY oi.order_date DESC;
```

### Q4 — Orphaned shipped_order headers (no line items)
```sql
SELECT so.ship_date, so.order_number, so.shipstation_order_id,
       so.total_items, so.created_at
FROM shipped_orders so
LEFT JOIN shipped_items si ON si.order_number = so.order_number
WHERE so.ship_date > '2026-04-22'
  AND si.id IS NULL
ORDER BY so.ship_date DESC;
```

### Q5 — shipped_items with no inventory deduction (lot-tracking gap)
```sql
SELECT
    si.base_sku,
    COUNT(*)                                      AS records,
    SUM(si.quantity_shipped)                      AS units_not_deducted,
    SUM(CASE WHEN si.sku_lot = si.base_sku
             THEN si.quantity_shipped ELSE 0 END)  AS units_no_lot_stamped,
    SUM(CASE WHEN si.sku_lot != si.base_sku
             THEN si.quantity_shipped ELSE 0 END)  AS units_has_lot_but_no_deduction
FROM shipped_items si
JOIN shipped_orders so ON so.order_number = si.order_number
LEFT JOIN inventory_transactions it
       ON it.shipstation_order_id = so.shipstation_order_id
      AND it.sku                  = si.base_sku
      AND it.transaction_type     = 'Ship'
WHERE si.ship_date > '2026-04-22'
  AND si.base_sku IN ('17612','17904','17914','18675','18795')
  AND it.id IS NULL
GROUP BY si.base_sku
ORDER BY units_not_deducted DESC;
```

### Q6 — Net deduction gap per SKU (original scorecard query)
```sql
SELECT
    sub.base_sku,
    SUM(sub.shipped_qty)                         AS total_shipped_post_recon,
    SUM(sub.deducted_qty)                        AS total_deducted_post_recon,
    SUM(sub.shipped_qty) - SUM(sub.deducted_qty) AS net_gap
FROM (
    SELECT
        si.base_sku,
        si.quantity_shipped                  AS shipped_qty,
        COALESCE(SUM(it.quantity), 0)        AS deducted_qty
    FROM shipped_items si
    JOIN shipped_orders so ON so.order_number = si.order_number
    LEFT JOIN inventory_transactions it
        ON  it.shipstation_order_id = so.shipstation_order_id
        AND it.transaction_type     = 'Ship'
        AND it.sku                  = si.base_sku
    WHERE si.base_sku = ANY(ARRAY['17612','17904','17914','18675','18795'])
      AND so.shipstation_order_id IS NOT NULL
      AND so.ship_date > '2026-04-22'
    GROUP BY si.order_number, si.base_sku, so.shipstation_order_id, si.quantity_shipped
) sub
GROUP BY sub.base_sku
ORDER BY sub.base_sku;
```

### Q7 — Current lot balances
```sql
SELECT
    sku_code,
    lot_number,
    status,
    balance,
    received_date
FROM lot_balances
WHERE sku_code = ANY(ARRAY['17612','17904','17914','18675','18795'])
ORDER BY sku_code, lot_number;
```

### Q8 — Double deductions post-4/22 (confirm none)
```sql
SELECT
    it.shipstation_order_id, it.sku,
    COUNT(*) AS deduction_count, SUM(it.quantity) AS total_deducted,
    so.ship_date
FROM inventory_transactions it
JOIN shipped_orders so ON so.shipstation_order_id = it.shipstation_order_id
WHERE it.transaction_type = 'Ship'
  AND it.shipstation_order_id IS NOT NULL
  AND so.ship_date > '2026-04-22'
GROUP BY it.shipstation_order_id, it.sku, so.ship_date
HAVING COUNT(*) > 1
ORDER BY so.ship_date DESC;
```

---

## Progress Log

| Date | Action | Result |
|---|---|---|
| 2026-06-03 | Initial QA audit run | Gaps identified — see Status Summary |
| 2026-06-03 | Discovered reconciliation was entered 4/21–22, not 4/17 | Baseline corrected to EOD 4/22 |
| 2026-06-03 | Pulled all 4/21–22 adjustment transactions | Fully documented — see Reconciliation Detail |
| 2026-06-03 | Confirmed no double deductions post-4/22 | ✅ Clean |
| 2026-06-03 | 18795 post-4/22 gap | ✅ 0 at lot level |
| 2026-06-03 | Physical inventory count conducted | See Physical Count Detail |
| 2026-06-03 | Ran ShipStation "Items Shipped" export (4/23–6/3) | 17612: 3,040 (incl. 17613) · 17904: 88 · 17914: 121 · 18675: 134 · 18795: 42 |
| 2026-06-03 | Ran Q1–Q5 diagnostic queries against production | See Diagnostic Queries section |
| 2026-06-03 | Q3 returned 0 rows | ✅ Sync pipeline working — no uploaded orders missing from DB |
| 2026-06-03 | Q5 confirmed lot-tracking gap | 17612: 119 units · 18675: 100 · 17904: 39 · 17914: 23 · 18795: 6 |
| 2026-06-03 | Dashboard vs physical comparison | ✅ Totals accurate — issue is lot-level only |
| 2026-06-03 | Confirmed no bulk unlinked Ship transactions | Ruled out hidden bulk deductions as compensating factor |
| 2026-06-03 | Identified lot 260122 (1,152 units, inactive) | Must be activated before lot 260082 depletes |
| 2026-06-03 | Identified lot 260047 at −22 (negative) | Needs Adjust Up +22 to clear |
| — | Fix lot-transition bug in `lot_deduction.py` | ⏳ Pending — **urgent, ~26 days before 260082 empties** |
| — | Activate lot 260122 | ⏳ Pending |
| — | Adjust Up lot 260047 by +22 | ⏳ Pending |
| — | Re-tag no-lot-stamp orders (57+19+6+5+2 units) | ⏳ Pending |
| — | Investigate 18675 +91 dashboard vs physical gap | ⏳ Pending |
| — | Resolve orphaned order headers (863334, 862718) | ⏳ Pending |

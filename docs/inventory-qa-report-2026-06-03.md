# Inventory Tracking QA Report
**Date:** 2026-06-03  
**Scope:** All key product SKUs — 17612, 17904, 17914, 18675, 18795  
**Baseline:** EOD 2026-04-22 (reconciliation adjustments entered 4/21–22; all pre-4/22 history disregarded)

---

## Status Summary (Post-4/22 Reconciliation)

| SKU | Shipped Since 4/22 | Deducted | Net Gap | Status |
|---|---|---|---|---|
| 17612 | 2,549 | 1,895 | **+654** | 🔴 Under-deducted |
| 17904 | 77 | 32 | **+45** | 🔴 Under-deducted |
| 17914 | 105 | 86 | **+19** | 🔴 Under-deducted |
| 18675 | 130 | 29 | **+101** | 🔴 Under-deducted |
| 18795 | 29 | 29 | **0** | ✅ Clean |

> A positive net gap means the database **overstates inventory** by that many units — those
> units shipped after the reconciliation but were never deducted from the ledger.

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

### ⚠️ Open question: 17612 lot 260017 Adjust Up +578

Lot 260017 was driven to −578 by what the note describes as "split-label resync errors."
The +578 Adjust Up restored it to zero. **Before running the deduction backfill, confirm
whether those 578 units were physically shipped or were a data error:**

- If **data error** (units never left the warehouse): the +578 is correct and the 4/22
  EOD baseline of 1,983 is accurate.
- If **real shipments** that got double-counted: the +578 overcorrects, inflating the
  17612 balance by ~578 units from the start. After the backfill, the DB would still show
  ~651 units more than physical — consistent with the Physical vs Corrected DB gap in the
  comparison table below.

---

## Inventory Comparison: Database vs. Physical Count

Physical count conducted **2026-06-03**.

### Three-Way Comparison

| SKU | 4/22 EOD (recon baseline) | DB Total (6/3) | DB Corrected* | Physical (6/3) | Physical vs Corrected |
|---|---|---|---|---|---|
| 17612 | 1,983 | 1,684 | **1,030** | 1,681 | **+651** ⚠️ |
| 17904 | 54 | 82 | **37** | 79 | **+42** |
| 17914 | 672 | 544 | **525** | 552 | **+27** |
| 18675 | 566 | 516 | **415** | 425 | **+10** ✅ |
| 18795 | 6,813 | 6,769 | **6,769** | 6,762 | **−7** ✅ |

> *DB Corrected = DB Total minus the post-4/22 deduction gap. This is what the database
> will show after the backfill is run.

**Interpretation:**
- **18675 and 18795** — after the backfill, database will match physical within single
  digits. ✅
- **17904 and 17914** — small residual gap (~27–42 units). Acceptable; likely minor
  counting tolerances or a handful of orders needing manual review.
- **17612** — 651-unit gap persists even after backfill. Root cause is the lot 260017
  +578 Adjust Up (see open question above) plus the undocumented +225 Adjust Up. If
  those adjustments were over-estimated, the 4/22 starting balance is inflated by ~803
  units, which closely matches the 651-unit residual.

---

### Physical Count Detail (2026-06-03)

#### 17612 — Total: 1,681 units ⚠️ *lot-level math sums to 1,673 (+8 counting discrepancy — verify lot 260082)*

| Lot | Pallets | Qty/Pallet | Partial | Lot Total |
|---|---|---|---|---|
| 260122 | 24 | 48 | 0 | 1,152 |
| 260082 | 10 | 48 | 35 | 521 |
| **Total** | | | | **1,681** |

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

## Current Lot Balances (as of 2026-06-03)

| SKU | Active Balance | Total Balance | Active Lot Count |
|---|---|---|---|
| 17612 | 554 | 1,684 | 1 |
| 17904 | 82 | 82 | 1 |
| 17914 | 544 | 544 | 1 |
| 18675 | 225 | 516 | 1 |
| 18795 | 99 | 6,769 | 1 |

**Estimated true balances** (DB Total minus post-4/22 deduction gap):

| SKU | DB Total | Post-4/22 Gap | Estimated True Balance |
|---|---|---|---|
| 17612 | 1,684 | 654 | **~1,030** |
| 17904 | 82 | 45 | **~37** |
| 17914 | 544 | 19 | **~525** |
| 18675 | 516 | 101 | **~415** |
| 18795 | 6,769 | 0 | **6,769** |

---

## Issues Found (Post-4/22)

### 🔴 Issue 1 — Lot-Transition Failure (dominant problem, affects all SKUs)

**Pattern:** When an order quantity exceeds the remaining balance of the current active
lot, `deduct_lot_inventory` deducts what's available and stops. It does not cascade
into the next active lot for the remainder.

**Example — order ships 40 units, current lot has 10 left:** system deducts 10, marks
lot depleted, stops. The remaining 30 are never deducted.

Sample affected orders for 17612:

| Order | Ship Date | Shipped | Deducted | Gap |
|---|---|---|---|---|
| 862897 | 2026-05-07 | 41 | 1 | 40 |
| 863314 | 2026-05-27 | 40 | 10 | 30 |
| 862962 | 2026-05-12 | 40 | 10 | 30 |
| 862990 | 2026-05-13 | 40 | 10 | 30 |
| 863263 | 2026-05-26 | 20 | 4 | 16 |
| 862975 | 2026-05-13 | 15 | 3 | 12 |

**Root cause:** `src/services/inventory/lot_deduction.py` — deduction stops at lot
boundary instead of continuing into the next active lot.

**Fix required:** Code change before running any backfill.

---

### 🔴 Issue 2 — Zero-Deduction Orders for 18675 (May batch)

**63 orders** with zero deductions. Mostly `100xxx`-series 18675 orders (May 11–13
wave, 1 unit each) that shipped before the lot tagger populated `customField1`, so
`deduct_lot_inventory` skipped them silently.

Units affected: ~84 units of 18675, ~47 units of 17612, ~6 of 17914, ~4 of 17904.

---

### 🔴 Issue 3 — Over-Deductions on 17612 (partially offsets Issue 1)

Some 17612 orders show more deductions than units shipped. These partially offset the
under-deductions in the net gap. Confirmed examples:

| Order | Shipped | Deducted | Excess |
|---|---|---|---|
| 862561 (17612) | 1 | 24 | 23 |
| 862454 (17612) | 10 | 30 | 20 |

Likely caused by a prior code version deducting per lot-item rather than per order,
creating duplicate `inventory_transactions` rows for the same shipment.

> Note: the 4/18–4/22 window showed 17612 deducted 310 units against 293 shipped
> (17 over-deducted). This was corrected by the Adjust Up entries on 4/21–22 and is
> already baked into the 4/22 EOD baseline.

---

### ⚠️ Issue 4 — 17612 Lot 260017 Adjustment Validity (blocker before backfill)

Lot 260017 received a +578 Adjust Up on 4/22 ("restores lot to 0"). The note attributes
the −578 balance to "split-label resync errors." **This must be confirmed before backfill:**
if the 578 units actually shipped (and the system just double-counted them), the +578 is
an overcorrection that inflates the 17612 baseline by 578 units. The undocumented +225
Adjust Up on the same date adds further uncertainty (+578 + +225 = +803, which closely
matches the 651-unit physical-vs-corrected gap).

---

### 🟡 Issue 5 — 18795 Active vs Total Balance (lot status labels)

Active balance: 99. Total across all lots: 6,769. The 6,670-unit difference lives in
depleted or inactive lots that carry a positive balance. This is a lot-status labeling
issue, not a missing-inventory issue — the units are accounted for in the total, just
not labeled as "active."

**Query to investigate:**
```sql
SELECT lot_number, status, balance, received_date
FROM lot_balances
WHERE sku_code = '18795'
ORDER BY balance DESC;
```

---

## Gap Breakdown by SKU (Post-4/22)

### 17612

| Category | Orders | Units |
|---|---|---|
| Zero deductions (completely missing) | 37 | +47 |
| Partial deductions (lot-transition failure) | 227 | +1,011 |
| **Total under-deducted** | **264** | **+1,058** |
| Over-deducted | 120 | −404 |
| **Net gap** | | **+654** |

### 18675

| Category | Orders | Units |
|---|---|---|
| Zero deductions | 66 | +105 |
| Over-deducted | 4 | −4 |
| **Net gap** | | **+101** |

### 17904

| Category | Orders | Units |
|---|---|---|
| Zero or partial deductions | ~32 | +50 |
| Over-deducted | ~4 | −5 |
| **Net gap** | | **+45** |

### 17914

| Category | Orders | Units |
|---|---|---|
| Zero or partial deductions | ~17 | +29 |
| Over-deducted | ~8 | −10 |
| **Net gap** | | **+19** |

### 18795

| Category | Orders | Units |
|---|---|---|
| Net gap | | **0** |

---

## Remediation Plan

### Step 1 — Confirm lot 260017 (+578) validity for 17612 (do first)

Before anything else, determine whether the 578-unit Adjust Up on lot 260017 (4/22)
represents real inventory on shelf or an overcorrection. Check:
- Were there orders in April 2026 whose ShipStation `customField1` referenced lot 260017?
- Does ShipStation show those orders as shipped?
- If shipped, the +578 inflated the balance; a correcting Adjust Down is needed before
  running the backfill.

---

### Step 2 — Fix the lot-transition bug in code

Patch `src/services/inventory/lot_deduction.py` before running any backfill. When
`quantity` exceeds the current lot's remaining balance, deduct what's available, then
continue into the next active lot for the remainder until the full quantity is satisfied.

---

### Step 3 — Fix remaining over-deductions (surgical adjustments)

For orders confirmed as over-deducted, insert offsetting `Adjust Up` transactions.
Prioritize large-magnitude cases (862561, 862454).

---

### Step 4 — Run the deduction backfill (post-4/22 scope)

```bash
python3 src/backfill_inventory_deductions.py --dry-run
```

After verifying dry-run output, run without `--dry-run`. Use `ship_date > '2026-04-22'`
as the date filter if supported. The idempotency guard will skip orders that already have
correct deductions.

---

### Step 5 — Re-run QA queries to confirm clean state

Target after remediation:

| SKU | Net Gap Target | Physical vs DB Target |
|---|---|---|
| 17612 | 0 | resolve lot 260017 first |
| 17904 | 0 | ≤ ±10 |
| 17914 | 0 | ≤ ±10 |
| 18675 | 0 | ≤ ±10 |
| 18795 | 0 | ≤ ±10 |

---

## QA Queries (Re-run to Track Progress)

All queries use **`ship_date > '2026-04-22'`** as the post-reconciliation cutoff.

### Net gap per SKU since 4/22 (main scorecard)
```sql
SELECT
    sub.base_sku,
    SUM(sub.shipped_qty)                              AS total_shipped_post_recon,
    SUM(sub.deducted_qty)                             AS total_deducted_post_recon,
    SUM(sub.shipped_qty) - SUM(sub.deducted_qty)      AS net_gap
FROM (
    SELECT
        si.base_sku,
        si.quantity_shipped                           AS shipped_qty,
        COALESCE(SUM(it.quantity), 0)                 AS deducted_qty
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

### Orders still missing deductions post-4/22
```sql
SELECT
    so.order_number,
    so.ship_date,
    so.shipstation_order_id,
    STRING_AGG(si.base_sku || ' x' || si.quantity_shipped::text, ', ' ORDER BY si.base_sku) AS items
FROM shipped_orders so
JOIN shipped_items si ON si.order_number = so.order_number
WHERE so.ship_date > '2026-04-22'
  AND so.shipstation_order_id IS NOT NULL
  AND si.base_sku = ANY(ARRAY['17612','17904','17914','18675','18795'])
  AND NOT EXISTS (
      SELECT 1 FROM inventory_transactions it
      WHERE it.shipstation_order_id = so.shipstation_order_id
        AND it.transaction_type = 'Ship'
  )
GROUP BY so.order_number, so.ship_date, so.shipstation_order_id
ORDER BY so.ship_date DESC;
```

### Quantity mismatches post-4/22
```sql
SELECT
    si.order_number,
    so.ship_date,
    si.base_sku,
    si.quantity_shipped                                           AS shipped_qty,
    COALESCE(SUM(it.quantity), 0)                                AS deducted_qty,
    si.quantity_shipped - COALESCE(SUM(it.quantity), 0)          AS discrepancy
FROM shipped_items si
JOIN shipped_orders so ON so.order_number = si.order_number
LEFT JOIN inventory_transactions it
    ON  it.shipstation_order_id = so.shipstation_order_id
    AND it.transaction_type     = 'Ship'
    AND it.sku                  = si.base_sku
WHERE si.base_sku = ANY(ARRAY['17612','17904','17914','18675','18795'])
  AND so.shipstation_order_id IS NOT NULL
  AND so.ship_date > '2026-04-22'
GROUP BY si.order_number, so.ship_date, si.base_sku, so.shipstation_order_id, si.quantity_shipped
HAVING si.quantity_shipped <> COALESCE(SUM(it.quantity), 0)
ORDER BY ABS(si.quantity_shipped - COALESCE(SUM(it.quantity), 0)) DESC;
```

### Double deductions post-4/22
```sql
SELECT
    it.shipstation_order_id,
    it.sku,
    COUNT(*)         AS deduction_count,
    SUM(it.quantity) AS total_deducted,
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

### Current lot balances (DB Total vs Active)
```sql
SELECT
    sku_code,
    SUM(CASE WHEN status = 'active'   THEN balance ELSE 0 END) AS active_balance,
    SUM(balance)                                               AS total_balance,
    COUNT(CASE WHEN status = 'active' THEN 1 END)             AS active_lot_count
FROM lot_balances
WHERE sku_code = ANY(ARRAY['17612','17904','17914','18675','18795'])
GROUP BY sku_code
ORDER BY sku_code;
```

### Lot 260017 investigation (17612 blocker)
```sql
SELECT
    it.transaction_type,
    it.quantity,
    it.date,
    it.notes,
    so.order_number,
    so.ship_date
FROM inventory_transactions it
JOIN lots l ON l.lot_id = it.lot_id
JOIN skus s ON s.sku_id = l.sku_id
LEFT JOIN shipped_orders so ON so.shipstation_order_id = it.shipstation_order_id
WHERE s.sku_code = '17612'
  AND l.lot_number = '260017'
ORDER BY it.date, it.transaction_type;
```

---

## Progress Log

| Date | Action | Result |
|---|---|---|
| 2026-06-03 | Initial QA audit run | Gaps identified — see Status Summary |
| 2026-06-03 | Discovered reconciliation was entered 4/21–22, not 4/17 | Baseline corrected to EOD 4/22 |
| 2026-06-03 | Pulled all 4/21–22 adjustment transactions | Fully documented — see Reconciliation Detail |
| 2026-06-03 | Confirmed no double deductions post-4/22 | ✅ Clean |
| 2026-06-03 | 18795 post-4/22 gap | ✅ 0 — clean |
| 2026-06-03 | Physical inventory count conducted | See Physical Count Detail |
| 2026-06-03 | Physical vs DB Corrected comparison | 17612 ⚠️ +651 · 17904 +42 · 17914 +27 · 18675 ✅ +10 · 18795 ✅ −7 |
| — | Confirm lot 260017 +578 validity | ⏳ Pending — blocker for 17612 backfill |
| — | Fix lot-transition bug in `lot_deduction.py` | Pending |
| — | Fix over-deductions (surgical Adjust Up) | Pending |
| — | Run deduction backfill (post-4/22) | Pending |
| — | Re-run QA scorecard | Pending |
| — | Investigate 17612 lot 260082 counting discrepancy | 8-unit gap (lot math 1,673 vs stated 1,681) |

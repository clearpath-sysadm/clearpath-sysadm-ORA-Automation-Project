# Inventory Tracking QA Report
**Date:** 2026-06-03  
**Scope:** All key product SKUs — 17612, 17904, 17914, 18675, 18795  
**Baseline:** EOD 2026-04-17 (accepted as correct — all pre-4/17 history disregarded)

---

## Status Summary

| SKU | Shipped Since 4/17 | Deducted | Net Gap | Status |
|---|---|---|---|---|
| 17612 | 2,842 | 2,205 | **+637** | 🔴 Under-deducted |
| 17904 | 88 | 41 | **+47** | 🔴 Under-deducted |
| 17914 | 134 | 105 | **+29** | 🔴 Under-deducted |
| 18675 | 139 | 36 | **+103** | 🔴 Under-deducted |
| 18795 | 49 | 47 | **+2** | 🟡 Near-clean |

> A positive net gap means inventory is **overstated** by that many units — those units
> were shipped but not deducted from the ledger.

---

## Current Lot Balances (as of 2026-06-03)

| SKU | Active Balance | Total Balance | Active Lot Count |
|---|---|---|---|
| 17612 | 554 | 1,684 | 1 |
| 17904 | 82 | 82 | 1 |
| 17914 | 544 | 544 | 1 |
| 18675 | 225 | 516 | 1 |
| 18795 | 99 | 6,769 | 1 |

**True active balances** (subtracting known net gaps from active balance):

| SKU | Active Balance | Net Gap to Fix | Estimated True Balance |
|---|---|---|---|
| 17612 | 554 | 637 | **~−83** (overstated) |
| 17904 | 82 | 47 | **~35** |
| 17914 | 544 | 29 | **~515** |
| 18675 | 225 | 103 | **~122** |
| 18795 | 99 | 2 | **~97** |

---

## Issues Found (Post-4/17 Only)

### 🔴 Issue 1 — Lot-Transition Failure on 17612 (dominant problem)

**227 orders** have partial deductions — the system deducted the remaining balance of a
lot when it ran dry but never continued into the next lot for the remainder of the order.

Pattern: order ships 40 units, current lot has 10 left → system deducts 10, marks lot
depleted, stops. The remaining 30 are never deducted.

Sample of affected orders:

| Order | Ship Date | Shipped | Deducted | Gap |
|---|---|---|---|---|
| 862897 | 2026-05-07 | 41 | 1 | 40 |
| 863314 | 2026-05-27 | 40 | 10 | 30 |
| 862962 | 2026-05-12 | 40 | 10 | 30 |
| 862990 | 2026-05-12 | 40 | 10 | 30 |
| 863263 | 2026-05-26 | 20 | 4 | 16 |
| 862975 | 2026-05-13 | 15 | 3 | 12 |
| 862576 | 2026-04-29 | 16 | 4 | 12 |

**Root cause:** `deduct_lot_inventory` deducts from one lot per call and does not cascade
to the next active lot when the current lot balance is insufficient for the full order
quantity.

**Fix required:** Code change to `src/services/inventory/lot_deduction.py` — when
deducting against a lot that would go to zero before the full quantity is covered, the
function must continue deducting the remainder from the next active lot for that SKU.

---

### 🔴 Issue 2 — Zero-Deduction Orders for 18675 (May batch)

**63 orders** post-4/17 with zero deductions at all. Mostly the `100xxx` series 18675
orders (May 11–13 wave, 1 unit each). These orders shipped before the lot tagger had
populated `customField1`, so `deduct_lot_inventory` skipped them silently.

Units affected: ~84 units of 18675, ~47 units of 17612, ~6 of 17914, ~4 of 17904.

---

### 🔴 Issue 3 — Over-Deductions on 17612 (partially offsets Issue 1)

**120 orders** were over-deducted, totalling **421 excess units** deducted for 17612.
These partially cancel out the under-deductions in the net gap (+1,058 missing −421
excess = +637 net). Confirmed examples:

| Order | Shipped | Deducted | Excess |
|---|---|---|---|
| 862254 (18675) | 53 | 106 | 53 |
| 862561 (17612) | 1 | 24 | 23 |
| 862454 (17612) | 10 | 30 | 20 |
| SS 278198682 (18675) | 2 | 4 | 2 |

Likely cause: a previous code version deducted per-lot-item rather than per-order,
resulting in duplicate `inventory_transactions` rows for the same shipment.

---

### 🟡 Issue 4 — Lot 260047 (17612, inactive, balance −22)

Lot received 2026-04-02, marked inactive, but carries a −22 balance (over-deducted).
Small magnitude. Correction: `Adjust Up` of 22 units against this lot, or accept as
a known offset.

---

### 🟡 Issue 5 — 18795 Total Balance Discrepancy (6,670 units in non-active lots)

Active balance: 99. Total across all lots: 6,769. The 6,670-unit gap lives in depleted
or inactive lots. Needs separate investigation to determine whether this represents
real physical inventory or a data artifact.

**Query to investigate:**
```sql
SELECT lot_number, status, balance, received_date
FROM lot_balances
WHERE sku_code = '18795'
ORDER BY balance DESC;
```

---

## Gap Breakdown by SKU (Post-4/17)

### 17612

| Category | Orders | Units |
|---|---|---|
| Zero deductions (completely missing) | 37 | 47 |
| Partial deductions (lot-transition failure) | 227 | 1,011 |
| **Total under-deducted** | **264** | **+1,058** |
| Over-deducted | 120 | −421 |
| **Net gap** | | **+637** |

### 18675

| Category | Orders | Units |
|---|---|---|
| Zero deductions | 66 | +107 |
| Over-deducted | 4 | −4 |
| **Net gap** | | **+103** |

### 17904

| Category | Orders | Units |
|---|---|---|
| Zero or partial deductions | 34 | +52 |
| Over-deducted | 4 | −5 |
| **Net gap** | | **+47** |

### 17914

| Category | Orders | Units |
|---|---|---|
| Zero or partial deductions | 19 | +44 |
| Over-deducted | 9 | −15 |
| **Net gap** | | **+29** |

### 18795

| Category | Orders | Units |
|---|---|---|
| Zero deductions | 8 | +8 |
| Over-deducted | 1 | −6 |
| **Net gap** | | **+2** |

---

## Remediation Plan

### Step 1 — Fix the lot-transition bug (code fix, do first)

Before running any backfill, the root cause must be patched. Otherwise the backfill
will reproduce the same partial deductions for any order that spans a lot boundary.

**File:** `src/services/inventory/lot_deduction.py`  
**Change:** When `quantity` exceeds the current lot's remaining balance, deduct what's
available from the current lot, then recurse/loop into the next active lot for the
remainder until the full quantity is satisfied.

---

### Step 2 — Fix over-deductions (surgical deletes/adjustments)

For orders confirmed as over-deducted, either:
- Delete the duplicate `inventory_transactions` rows, or
- Insert offsetting `Adjust Up` transactions

Prioritize the large-magnitude cases first (862254, 862561, 862454).

---

### Step 3 — Run the backfill (post-4/17 scope only)

```bash
python3 src/backfill_inventory_deductions.py --dry-run
```

After verifying dry-run output, run without `--dry-run`. The idempotency guard will
skip already-correct deductions and only fill actual gaps. Limit to post-4/17 orders
if the script supports a date filter — otherwise the pre-4/17 history will be skipped
naturally because those orders have no lot stamps in ShipStation.

---

### Step 4 — Investigate 18795 lot balance

Run the lot breakdown query above and determine whether the 6,670-unit gap is real
inventory or a data artifact before trusting the 18795 balance.

---

### Step 5 — Re-run QA queries to confirm clean state

Target state after remediation:

| SKU | Net Gap Target |
|---|---|
| 17612 | 0 |
| 17904 | 0 |
| 17914 | 0 |
| 18675 | 0 |
| 18795 | 0 |

---

## QA Queries (Re-run to Track Progress)

### Net gap per SKU since 4/17 (main scorecard)
```sql
SELECT
    sub.base_sku,
    SUM(sub.shipped_qty)   AS total_shipped_post_recon,
    SUM(sub.deducted_qty)  AS total_deducted_post_recon,
    SUM(sub.shipped_qty) - SUM(sub.deducted_qty) AS net_gap
FROM (
    SELECT
        si.base_sku,
        si.quantity_shipped                    AS shipped_qty,
        COALESCE(SUM(it.quantity), 0)          AS deducted_qty
    FROM shipped_items si
    JOIN shipped_orders so ON so.order_number = si.order_number
    LEFT JOIN inventory_transactions it
        ON  it.shipstation_order_id = so.shipstation_order_id
        AND it.transaction_type     = 'Ship'
        AND it.sku                  = si.base_sku
    WHERE si.base_sku = ANY(ARRAY['17612','17904','17914','18675','18795'])
      AND so.shipstation_order_id IS NOT NULL
      AND so.ship_date > '2026-04-17'
    GROUP BY si.order_number, si.base_sku, so.shipstation_order_id, si.quantity_shipped
) sub
GROUP BY sub.base_sku
ORDER BY sub.base_sku;
```

### Orders still missing deductions post-4/17
```sql
SELECT
    so.order_number,
    so.ship_date,
    so.shipstation_order_id,
    STRING_AGG(si.base_sku || ' x' || si.quantity_shipped::text, ', ' ORDER BY si.base_sku) AS items
FROM shipped_orders so
JOIN shipped_items si ON si.order_number = so.order_number
WHERE so.ship_date > '2026-04-17'
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

### Remaining quantity mismatches post-4/17
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
  AND so.ship_date > '2026-04-17'
GROUP BY si.order_number, so.ship_date, si.base_sku, so.shipstation_order_id, si.quantity_shipped
HAVING si.quantity_shipped <> COALESCE(SUM(it.quantity), 0)
ORDER BY ABS(si.quantity_shipped - COALESCE(SUM(it.quantity), 0)) DESC;
```

### Double deductions post-4/17
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
  AND so.ship_date > '2026-04-17'
GROUP BY it.shipstation_order_id, it.sku, so.ship_date
HAVING COUNT(*) > 1
ORDER BY so.ship_date DESC;
```

---

## Progress Log

| Date | Action | Result |
|---|---|---|
| 2026-06-03 | Initial QA audit run | Gaps identified — see Status Summary above |
| 2026-06-03 | Confirmed 4/17 EOD as baseline | Pre-4/17 history disregarded |
| — | Fix lot-transition bug | Pending |
| — | Fix over-deductions | Pending |
| — | Run backfill (post-4/17) | Pending |
| — | Re-run QA scorecard | Pending |

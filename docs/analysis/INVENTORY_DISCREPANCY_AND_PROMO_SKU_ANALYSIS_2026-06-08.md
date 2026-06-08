# Inventory Discrepancy & Promo SKU Deduction Analysis
**Date:** June 8, 2026  
**Analyst:** Agent session  
**Scope:** Production inventory count reconciliation (June 3 EOD) + promo SKU deduction audit (June 1–5)

---

## 1. Summary

Two separate but related issues were identified during this session:

1. **Inventory count discrepancies** across several SKUs between the June 3 EOD physical counts and the system's current inventory_summary values.
2. **Promo SKU deduction failure** — 66 orders / 107 units shipped since June 1 with zero inventory deduction because the promo SKU replacement process stopped working after May 27.

---

## 2. June 3 EOD Physical Counts (Verified)

| SKU | Physical Count (EOD June 3) | System at Verification | Status |
|-----|----------------------------|------------------------|--------|
| 17612 | 1,681 | 1,681 | Verified ✓ |
| 17904 | 79 | 79 | Verified ✓ |
| 17914 | 552 | 552 | Verified ✓ |
| 18675 | 425 | 425 | Verified ✓ |
| 18795 | 6,762 | 6,762 | Verified ✓ |

---

## 3. Per-SKU Reconciliation (June 4–5)

### 17904 and 18795 — Fully Reconciled
No gaps found. June 4–5 ShipStation data matches inventory_transactions exactly.

### 17612 — Under-deduction from Promo SKU
- June 4–5 regular shipments: 206 units (matched in `shipped_items` and `inventory_transactions`)
- FREE CASE 17613 shipments June 4–5: ~35 units **not deducted** (see Section 5)
- Corrective action: Enter Receive transaction for 576 units, date 2026-06-05, lot 260082 (or current active lot)

### 17914 — 16-Unit Pre-June-3 Gap
- June 4–5 ShipStation confirms exactly 11 units shipped (10 regular + 1 FREE CASE 17915 → 17914). Matches `inventory_transactions` exactly. ✓
- The 16-unit gap is **pre-June 3** — exists in the historical data before the verified EOD count
- Key suspects:
  - **766-unit Adjust Down** (lot_id=11) — needs timestamp verification
  - **Null lot_id transactions** invisible to `lot_balances` / `inventory_summary`:
    - Repack: +66 units (not counted)
    - Adjust Up: +5 units (not counted)
    - Adjust Down: -2 units (not counted)
    - Net invisible: +69 units not reflected in inventory_summary
- Investigative query needed:
  ```sql
  SELECT id, date, quantity, transaction_type, notes, created_at
  FROM inventory_transactions
  WHERE sku = '17914'
    AND transaction_type = 'Adjust Down'
    AND lot_id = 11
  ORDER BY created_at;
  ```

### 18675 — Unexplained 200-Unit Drop
- Physical count June 3 EOD: 425
- System current: 225 (200-unit drop)
- Zero June 4–5 shipments for this SKU
- Root cause not identified during this session — requires query:
  ```sql
  SELECT id, date, quantity, transaction_type, notes, created_at
  FROM inventory_transactions
  WHERE sku = '18675'
    AND created_at > '2026-06-03 23:59:59'
  ORDER BY created_at;
  ```

---

## 4. Key Schema Finding — Null Lot_id Transactions Are Invisible

`inventory_summary` = SUM(`lot_balances`) WHERE status != 'quarantine'.  
`lot_balances` is built via LEFT JOIN from the `lots` table.  
**Any `inventory_transactions` row with `lot_id = NULL` is invisible to `lot_balances` and therefore to `inventory_summary`.**

This affects 17914 specifically (net +69 units invisible). A fix or audit of null-lot-id transactions should be considered.

---

## 5. Promo SKU Deduction Failure (Primary Finding)

### What Was Found
Query against `shipped_items` revealed that since June 1, 2026, promo SKU orders are
landing with `base_sku` = promo SKU code and `sku_lot` = bare promo SKU (no lot number):

| base_sku | sku_lot | Orders | Units | Date Range |
|----------|---------|--------|-------|------------|
| 17613 | 17613 | 64 | 105 | 2026-06-01 to 2026-06-05 |
| 17915 | 17915 | 2 | 2 | 2026-05-28 to 2026-06-05 |

The `promo_sku_replacement_log` shows the last successful replacement activity was **May 27, 2026**. Nothing from June.

### Root Cause — Three Compounding Gaps

**Gap 1: CF1 is blank for promo orders**  
`src/lot_tagger/tagger.py` lines 359–378 already remaps promo SKUs in-memory before
stamping CF1 (e.g., 17613 → 17612, then stamps CF1 = "17612 - 260082"). However,
`load_promo_map()` is wrapped in a try/except that silently falls back to `{}` on any
exception. If this lookup fails on production, the lot tagger falls back to looking up
a lot for raw "17613" — which has no lot — and skips CF1 entirely. CF1 = blank.

**Gap 2: `deduct_lot_inventory` silently skips blank CF1**  
`src/services/inventory/lot_deduction.py` lines 64–66:
```python
cf1 = (customField1_value or '').strip()
if not cf1:
    logger.debug(f"Skipping deduction for order {order_number} / {base_sku}: no customField1")
```
Even though `update_existing_order_status` (lines 1093–1110) correctly remaps the promo
SKU via the promo map before calling `deduct_lot_inventory`, the deduction silently skips
when CF1 is blank — producing no `inventory_transactions` row.

**Gap 3: `shipped_items` write paths store the promo SKU unchanged**  
Three write paths all lack promo map remapping before writing `base_sku`:

| Path | Location | Issue |
|------|----------|-------|
| Regular ShipStation orders (primary) | `daily_shipment_processor.py:282-354` | `base_sku` built from raw ShipStation item SKU; CF1 upgrade check fails (`parsed[0]`="17612" ≠ `base_sku`="17613") |
| Manual import | `unified_shipstation_sync.py:714-740` | No promo map before shipped_items INSERT |
| BigCommerce import | `unified_shipstation_sync.py:886-941` | No promo map before `upsert_shipped_item` call |

### Impact
- **17612**: 105 units not deducted since June 1 (all 17613 FREE CASE orders)
- **17914**: 2 units not deducted since May 28 (17915 FREE CASE orders)
- This is contributing to 17612 appearing over-stocked in the system

---

## 6. Promo SKU Mapping Reference

From `sku_promotions` table (migration 014):

| Promo SKU | Base SKU | Description |
|-----------|----------|-------------|
| 17613 | 17612 | BXGY free unit — PT Kit |
| 17905 | 17904 | (promo) |
| 17915 | 17914 | FREE CASE PPR-PreRinse |
| 18676 | 18675 | (promo) |

### Replacement Log History (all activity pre-June 1)

| Promo SKU | Status | Count | Last Seen |
|-----------|--------|-------|-----------|
| 17613 | replaced | 289 | 2026-05-27 |
| 17613 | skipped | 870 | 2026-05-27 |
| 17613 | verify_failed | 435 | 2026-05-15 |
| 17905 | replaced | 9 | 2026-05-22 |
| 17915 | replaced | 10 | 2026-05-26 |
| 18676 | replaced | 53 | 2026-05-22 |
| 18676 | verify_failed | 176 | 2026-05-18 |

**No entries from June 1 onward for any promo SKU.**

---

## 7. Corrections Required

### 7A. Data Corrections (Run in Production)

---

#### CC1 — Corrected gap analysis (fixes fan-out bug in earlier query)
Run this first to get accurate missing-deduction numbers before touching any data.

```sql
-- Part 1: Per-SKU gap between shipped_items and inventory_transactions
SELECT
    si.base_sku                                     AS sku,
    si.total_shipped                                AS shipped_items_units,
    COALESCE(it.total_deducted, 0)                  AS deducted_units,
    si.total_shipped - COALESCE(it.total_deducted, 0) AS gap
FROM (
    SELECT base_sku, SUM(quantity_shipped) AS total_shipped
    FROM shipped_items
    WHERE base_sku IN ('17612','17904','17914','18675','18795')
    GROUP BY base_sku
) si
LEFT JOIN (
    SELECT sku, SUM(quantity) AS total_deducted
    FROM inventory_transactions
    WHERE transaction_type = 'Ship'
      AND sku IN ('17612','17904','17914','18675','18795')
    GROUP BY sku
) it ON it.sku = si.base_sku
ORDER BY gap DESC;

-- Part 2: shipped_items date coverage per SKU
SELECT
    base_sku,
    MIN(ship_date) AS earliest_ship,
    MAX(ship_date) AS latest_ship,
    COUNT(DISTINCT order_number) AS order_count,
    SUM(quantity_shipped) AS total_units
FROM shipped_items
WHERE base_sku IN ('17612','17904','17914','18675','18795')
GROUP BY base_sku
ORDER BY base_sku;
```

---

#### CC2 — Full null lot_id transaction audit

```sql
SELECT
    id, date, sku, quantity, transaction_type,
    notes, shipstation_order_id, lot_id, created_at
FROM inventory_transactions
WHERE lot_id IS NULL
ORDER BY sku, date;
```

**Known issue:** Row id=118 — 18675, 144 units, Ship, March 2026, lot_id=NULL. This makes 144
units invisible to `lot_balances` → inventory overstated by 144. Fix via CC3.

---

#### CC3 — Fix null-lot 18675 Ship row (id=118)

Step 1: Confirm lot exists:
```sql
SELECT id AS lot_id, lot_number, status, received_date
FROM lots
WHERE sku = '18675'
ORDER BY received_date;
```

Step 2: The notes field on row id=118 contains "240231" — likely the lot number. If lot 240231
exists and maps to 18675, apply:
```sql
-- Preview:
SELECT * FROM inventory_transactions WHERE id = 118;

-- Fix (replace <X> with lot_id from step 1):
UPDATE inventory_transactions
SET lot_id = <X>
WHERE id = 118;
```

Also fix the minor Adjust Down null-lot row (id=83, 18675, 1 unit, 2025-10-31) if a lot can be identified.

---

#### CC4 — Resolve 17914 May 27 discrepancy

```sql
-- What's in inventory_transactions for 17914 on May 27?
SELECT
    it.id, it.date, it.sku, it.lot_id, it.quantity,
    it.transaction_type, it.shipstation_order_id, it.notes
FROM inventory_transactions it
WHERE it.sku = '17914'
  AND it.date = '2026-05-27'
ORDER BY it.transaction_type, it.shipstation_order_id;

-- Cross-check against shipped_items for same date:
SELECT order_number, base_sku, sku_lot, quantity_shipped, ship_date
FROM shipped_items
WHERE base_sku = '17914'
  AND ship_date = '2026-05-27'
ORDER BY order_number;
```

Three orders (863305, 863319, 863326 — 4 units total) are missing deductions on this date.
Resolve before running the full backfill on 17914.

---

#### CC5 — Scoped missing-deduction count (run after CC1 confirms date range)

```sql
SELECT
    si.base_sku                       AS sku,
    COUNT(DISTINCT si.order_number)   AS orders_missing_deduction,
    SUM(si.quantity_shipped)          AS units_missing_deduction
FROM shipped_items si
JOIN orders_inbox o ON o.order_number = si.order_number
WHERE si.base_sku IN ('17612','17904','17914','18675','18795')
  AND o.status = 'shipped'
  AND si.sku_lot LIKE '% - %'
  AND NOT EXISTS (
      SELECT 1 FROM inventory_transactions it
      WHERE it.shipstation_order_id = o.shipstation_order_id
        AND it.transaction_type = 'Ship'
        AND it.sku = si.base_sku
  )
GROUP BY si.base_sku
ORDER BY units_missing_deduction DESC;
```

---

#### CC6 — 17612 Receive Transaction (June 5)

```sql
-- Step 1: Confirm lot_id for lot 260082
SELECT id AS lot_id, lot_number, sku, status
FROM lots
WHERE lot_number = '260082' AND sku = '17612';

-- Step 2: Insert receive (replace <lot_id> with result above)
INSERT INTO inventory_transactions
    (date, sku, lot_id, quantity, transaction_type, notes, created_at)
VALUES
    ('2026-06-05', '17612', <lot_id>, 576, 'Receive',
     'Physical count correction — June 5 receive entry', NOW());
```

---

#### CC7 — Promo SKU backfill (66 orders)

```sql
-- Preview: confirm which orders need correction
SELECT
    si.order_number, si.ship_date, si.base_sku, si.sku_lot, si.quantity_shipped,
    sp.base_sku AS correct_base_sku
FROM shipped_items si
JOIN sku_promotions sp ON si.base_sku = sp.promo_sku
WHERE sp.active = TRUE
ORDER BY si.ship_date DESC;
```

Run the backfill script (built as part of Task #111):
```bash
python3 src/backfill_promo_sku_deductions.py --dry-run
python3 src/backfill_promo_sku_deductions.py
```

---

#### Corrective Execution Order

1. **CC1** — Get corrected gap numbers and shipped_items date range
2. **CC2** — Full null lot_id audit
3. **CC3** — Fix 18675 null-lot Ship row (id=118)
4. **CC4** — Resolve 17914 May 27 discrepancy
5. **CC5** — Get per-SKU count of all missing deductions
6. Run backfill: `python3 src/backfill_inventory_deductions.py --dry-run` then without `--dry-run`
7. **CC6** — Insert 17612 June 5 Receive transaction
8. **CC7** — Run promo SKU backfill (after Task #111 is deployed)
9. Verify: `SELECT sku, current_quantity FROM inventory_summary WHERE sku IN ('17612','17904','17914','18675','18795');`

---

### 7B. Code Corrections (Task #111 — to be deployed)

These are code changes required to prevent the promo SKU deduction failure from recurring.
See Task #111 for the full implementation spec.

| # | What to fix | File | Details |
|---|-------------|------|---------|
| 1 | Diagnose why `load_promo_map` fails silently on production | `src/lot_tagger/tagger.py:362-367` | Check prod logs for `"Could not load promo map"` warnings. The try/except silently falls back to `{}` — if this fires, the lot tagger can't find a lot for the promo SKU and leaves CF1 blank |
| 2 | Fix `save_shipped_items_to_db` — apply promo map before CF1 comparison | `src/daily_shipment_processor.py:282-354` | Primary write path for all regular ShipStation orders. Apply `load_promo_map()` to remap `base_sku` before the `parsed[0] == str(base_sku)` check at line 332 |
| 3 | Fix manual import path — apply promo map before shipped_items INSERT | `src/unified_shipstation_sync.py:714-740` | Aggregation loop at lines 719–729 writes `b_sku` straight from ShipStation item SKU with no promo map |
| 4 | Fix BigCommerce import path — apply promo map before `upsert_shipped_item` | `src/unified_shipstation_sync.py:886-941` | Aggregation loop at lines 906–916, same issue |
| 5 | Add active-lot fallback in `deduct_lot_inventory` for blank CF1 | `src/services/inventory/lot_deduction.py:64-66` | When CF1 is blank but `base_sku` is a known key SKU, fall back to active lot lookup instead of silently skipping. This makes the deduction resilient to lot tagger timing gaps |
| 6 | Backfill 66 affected orders | New script | Update `shipped_items` + insert `inventory_transactions` Ship rows for 17613×64 orders (105 units) and 17915×2 orders (2 units) |

---

## 8. Tasks Created / Updated

| Task | Title | Status |
|------|-------|--------|
| #110 | Diagnose & correct production inventory count discrepancy | Updated with CC1–CC5 queries |
| #111 | Fix promo SKU inventory deduction | Created — covers code fix + backfill of 66 orders |

---

## 9. Outstanding Items (Not Yet Resolved)

1. **18675 -200 unit drop** — Root cause unknown. No June 4–5 shipments. Needs the `created_at > '2026-06-03 23:59:59'` query result for `sku='18675'`.
2. **17914 16-unit gap** — Pre-June-3 origin confirmed. Still need to timestamp the 766-unit Adjust Down (lot_id=11) to determine if it's a data entry error or a legitimate bulk adjustment.
3. **Lot tagger production failure** — Why is `load_promo_map` silently failing on production? Check for `"Could not load promo map"` in production logs.
4. **Null lot_id transactions for 17914** — 69 net units invisible to inventory_summary. Should these be assigned to an active lot?

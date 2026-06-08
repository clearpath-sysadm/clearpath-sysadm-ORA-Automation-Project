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

## 7. Corrective SQL (Pending Execution)

### CC1 — 17612 Receive Transaction (June 5)
```sql
-- Confirm lot_id for lot 260082 before running
SELECT id, lot_number, sku, status FROM lots WHERE lot_number = '260082' AND sku = '17612';

INSERT INTO inventory_transactions (date, sku, lot_id, quantity, transaction_type, notes, created_at)
VALUES ('2026-06-05', '17612', <lot_id_from_above>, 576, 'Receive', 'Physical count correction — June 5 receive', NOW());
```

### CC2 — Backfill Promo SKU Deductions (via Task #111)
See Task #111 plan for the full backfill script spec. High-level steps:
1. Update `shipped_items` rows where `base_sku IN ('17613','17915')` to correct base SKU + active lot
2. Insert `inventory_transactions` Ship rows for each corrected order
3. Skip orders already having a Ship transaction for the base SKU
4. Log to `promo_sku_replacement_log` with status = 'replaced'

### Verification Query — Confirm No Remaining Promo SKUs in shipped_items
```sql
SELECT base_sku, sku_lot, COUNT(*) AS orders, SUM(quantity_shipped) AS units
FROM shipped_items
WHERE base_sku IN (SELECT promo_sku FROM sku_promotions WHERE active = TRUE)
GROUP BY base_sku, sku_lot
ORDER BY base_sku;
```

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

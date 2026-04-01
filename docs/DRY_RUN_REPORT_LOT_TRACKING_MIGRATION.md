# Dry Run Report — Lot Tracking Migration (Task #6)

**Date:** 2026-04-01  
**Scope:** End-to-end review of the lot tracking schema rebuild after migration 009 was applied to the live database.

---

## Status Summary

| Check | Result |
|-------|--------|
| Python syntax (app.py + all workers) | PASS |
| Migration 009 applied | PASS — 5 SKUs, 16 lots, view created |
| Opening balance backfill | PASS — 5 Receive transactions inserted |
| `lot_balances` view returns correct data | PASS |
| `inventory_transactions.lot_id` column | PASS |
| `shipstation_order_line_items.lot_id` column | PASS |
| New unique index on `shipstation_order_line_items` | PASS |
| New unique index on `inventory_transactions` | PASS |
| Old `inventory_transactions` constraint dropped | PASS |
| `order_items_inbox` unique constraint re-added | PASS |
| No `FROM sku_lot` in app.py runtime paths | PASS |
| No `FROM sku_lot` in scheduled worker runtime paths | PASS |

---

## Failure Points Found

### Issue 1 — CRITICAL: DELETE /api/sku_lots will fail for lots with transactions

**File:** `app.py` line 5057  
**Endpoint:** `DELETE /api/sku_lots/<id>` (sku_lot management page)

`api_delete_sku_lot` runs:
```sql
DELETE FROM lots WHERE lot_id = %s
```
It does **not** first remove `inventory_transactions` rows that reference the lot via FK. Since the backfill created 5 `inventory_transactions` rows with `lot_id` set, any attempt to delete those lots will immediately throw a FK violation and return a 500 error.

The `api_delete_lot_inventory` endpoint (lot_inventory page) handles this correctly — but `api_delete_sku_lot` does not.

**Fix:** Add `DELETE FROM inventory_transactions WHERE lot_id = %s` before the `DELETE FROM lots`.

---

### Issue 2 — HIGH: Two active lots for SKU 17612 causes duplicate order rows

**Root cause:** Data conflict between `sku_lot` and `lot_inventory` tables during migration.

- `sku_lot` had `17612 / 250340` with `active = 1`
- `lot_inventory` had `17612 / 250237` with `status = 'active'` (and an opening balance of 1,019)
- Migration 009 step 4 uses `COALESCE(li.status, CASE WHEN sl.active = 1 ...)`, so `lot_inventory.status` wins for 250237 and `sku_lot.active` drives 250340 — resulting in **both** landing as `status = 'active'`

**Effect:** Every `LEFT JOIN lots … WHERE l.status = 'active'` in order management returns two rows per line item for SKU 17612:

```
order=708855, sku=17612 → lot 250237  (balance 1,019 — from lot_inventory)
order=708855, sku=17612 → lot 250340  (balance 0    — from sku_lot active=1)
```

**Fix:** Set lot 250340 to `status = 'inactive'`. Lot 250237 is the correct active lot (it has inventory).

```sql
UPDATE lots
SET status = 'inactive'
WHERE lot_number = '250340'
  AND sku_id = (SELECT sku_id FROM skus WHERE sku_code = '17612');
```

---

### Issue 3 — MEDIUM: DELETE /api/lot_inventory will fail once lot_id propagates

**File:** `app.py` line 7617  
**Endpoint:** `DELETE /api/lot_inventory/<id>` (lot_inventory page)

`api_delete_lot_inventory` deletes from `inventory_transactions` first (correct), but does **not** handle the `shipstation_order_line_items.lot_id` FK.

- **Current state:** 0 `shipstation_order_line_items` rows have `lot_id` set — safe today.
- **Future state:** The upload worker (`scheduled_shipstation_upload.py`) now writes `lot_id` on every new shipment record. The first delete of a lot that has had a shipment against it will throw a FK violation.

**Fix:** Add before the `DELETE FROM lots`:
```sql
UPDATE shipstation_order_line_items SET lot_id = NULL WHERE lot_id = %s
```

---

### Issue 4 — LOW: Three utility scripts still reference the `sku_lot` table

These are ad-hoc/run-once scripts, not scheduled workers. The `sku_lot` table still exists, so they work today.

| File | Line |
|------|------|
| `utils/cleanup_shipstation_duplicates.py` | 59 |
| `utils/create_corrected_orders.py` | 48 |
| `utils/import_initial_lot_inventory.py` | 43 |

**Fix:** Update to query `lots`/`skus` when convenient, before `sku_lot` is dropped in a future migration.

---

### Issue 5 — LOW: Duplicate correction returns raw database error

**File:** `app.py` line 7633  
**Endpoint:** `POST /api/lot_inventory/<id>/correct`

No `ON CONFLICT` clause and no `except psycopg2.IntegrityError` handler. If the same correction (same date, SKU, lot, type, and amount) is submitted twice, the unique index fires and returns a raw psycopg2 `UniqueViolation` message as a 500 error instead of a clean user-facing 409 response.

**Fix:** Add an `except psycopg2.IntegrityError` block returning a 409 with a human-readable message.

---

## Priority Fix Order

| Priority | Issue | Action | Status |
|----------|-------|--------|--------|
| 1 | Issue 2 — Duplicate active lots (data) | Dev DB only — not applicable to production | Deferred |
| 2 | Issue 1 — Delete FK violation (sku_lots page) | `app.py` `api_delete_sku_lot` — clear `inventory_transactions` + NULL `shipstation_order_line_items.lot_id` first | **Fixed** |
| 3 | Issue 3 — Delete FK violation (lot_inventory page) | `app.py` `api_delete_lot_inventory` — NULL `shipstation_order_line_items.lot_id` before delete | **Fixed** |
| 4 | Issue 5 — Correction duplicate error UX | `app.py` `api_correct_lot_inventory` — added `psycopg2.IntegrityError` → HTTP 409 handler | **Fixed** |
| 5 | Issue 4 — Utility scripts | `utils/cleanup_shipstation_duplicates.py` updated to `lots`/`skus`; two SQLite scripts are obsolete and excluded | **Fixed** |

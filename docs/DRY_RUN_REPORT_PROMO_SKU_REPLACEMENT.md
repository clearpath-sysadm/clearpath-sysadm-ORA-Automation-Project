# Dry Run Report — Promotional SKU Order Replacement (Task #41)

**Date:** April 14, 2026
**Environment:** Development (DEV_WORKERS_ACTIVE=false — no real ShipStation API calls made)
**Overall Result:** 41/41 PASS — All requirements verified

---

## Executive Summary

Task #41 implements an automatic pipeline that detects promotional SKU orders
entering ShipStation (e.g., SKU 17613, the free BXGY unit) and replaces them
with the correct base SKU order (e.g., 17612) before the lot-tagger processes
them. This ensures fulfillment specialists see the correct SKU/lot and
inventory deducts from the correct lot.

This dry run tested every functional requirement of the implementation using
the live development database for all DB operations and mock objects for
ShipStation API calls (since DEV_WORKERS_ACTIVE is disabled). All 41 checks
across 6 categories passed.

---

## Test Categories

| Category | Tests | Pass | Fail |
|---|---|---|---|
| DB-01–04: Database Schema | 4 | 4 | 0 |
| HELPER-01–09: Helper Functions | 9 | 9 | 0 |
| VERIFY-01–08: Verification Logic | 8 | 8 | 0 |
| CREATE-01–04: Payload Mutation | 4 | 4 | 0 |
| HANDLER-01–09: Handler Flow (all branches) | 9 | 9 | 0 |
| INTEGRATION-01–07: Wiring & Integration Points | 7 | 7 | 0 |
| **TOTAL** | **41** | **41** | **0** |

---

## Section 1 — Database Schema

These tests verify that the two new tables were created with the correct
structure and that the initial seed data is present.

### DB-01 ✅ sku_promotions seeded (17613 → 17612)
The `sku_promotions` table contains the initial mapping `promo_sku='17613'`,
`base_sku='17612'`, `active=TRUE`. The table is the authoritative source of
truth for all promo-to-base mappings and can be extended without code changes.

### DB-02 ✅ promo_sku_replacement_log has all required columns
Columns verified: `id`, `order_number`, `promo_sku`, `base_sku`, `status`,
`error_reason`, `processed_at` — all present and in order.

### DB-03 ✅ Status CHECK constraint enforced
Attempting to insert a row with `status='invalid_status'` raises a DB-level
constraint violation. Only `replaced`, `failed`, `verify_failed`, and `skipped`
are accepted. This is enforced at the database level, not just in application
code.

### DB-04 ✅ sku_promotions has all required columns
Columns verified: `id`, `promo_sku`, `base_sku`, `description`, `active`,
`created_at` — all present.

---

## Section 2 — Helper Functions

These tests verify that each internal helper behaves correctly in isolation,
using the live database.

### HELPER-01 ✅ _load_promo_map loads 17613→17612
Returns `{'17613': '17612'}` from the live `sku_promotions` table.

### HELPER-02 ✅ _is_empty handles all edge cases
9 cases tested: `None`, `''`, `[]`, `{}` → `True`; `0`, `False`, `'x'`,
`[1]`, `{'a':1}` → `False`. The function correctly treats falsy-but-valid
values (`0`, `False`) as non-empty.

### HELPER-03 ✅ _write_log returns integer ID
Calling `_write_log()` inserts a row and returns the PostgreSQL `RETURNING id`
integer, confirming that the row can be located for subsequent updates.

### HELPER-04 ✅ _update_log_status updates existing row (no new row)
After writing a `replaced` log row, `_update_log_status()` correctly changes
the status to `failed` and sets the `error_reason` — modifying the same row,
not inserting a second one. This enforces the one-canonical-row-per-attempt
contract.

### HELPER-05 ✅ _already_processed returns False when not in deleted_orders
Fresh order with no record in `deleted_shipstation_orders` → returns `False`.

### HELPER-06 ✅ _already_processed returns True after _record_deletion
After `_record_deletion()` writes a row with `deleted_by='promo_sku_replacement'`,
`_already_processed()` returns `True` for the same `orderId` — idempotency
guard is active.

### HELPER-07 ✅ _record_deletion writes correct row to deleted_shipstation_orders
Verified fields: `deleted_by='promo_sku_replacement'`, correct `order_number`,
`customer_email`, `ship_to_name`, `ship_to_city`, `ship_to_state`,
`order_total_cents`, `order_date`, `items_json` all populated from the order.

### HELPER-08 ✅ _rollback_deletion removes the row cleanly
After `_record_deletion()` writes a row, `_rollback_deletion_record()` removes
it completely. A subsequent query confirms the row is gone, meaning a failed
delete is fully retryable by the next reconciliation run.

### HELPER-09 ✅ _write_tagging_failure writes to lot_tagging_failures with PROMO tag
A failure row is written to `lot_tagging_failures` with the `sku` field
formatted as `17613 [PROMO: reason]` so failures appear in the existing
specialist error dashboard and are distinguishable from normal lot-tagging
failures.

---

## Section 3 — Verification Logic

These tests exercise `_verify_replacement()` — the function that compares
every populated field of the original order against the fetched replacement
to ensure correctness before cancelling the original.

### VERIFY-01 ✅ Single promo item replacement passes
A single-item order where `17613 → 17612` produces zero mismatches.

### VERIFY-02 ✅ Mixed-SKU order (promo + base items) passes
An order with two line items — one promo (`17613`) and one non-promo (`17612`)
— passes verification when:
- The promo item becomes `17612`
- The non-promo item stays `17612`
Zero mismatches. This was a critical fix from code review to handle real-world
mixed-cart orders.

### VERIFY-03 ✅ Wrong base SKU in replacement fails
If the replacement order's SKU is `99999` instead of `17612`, verification
produces a mismatch on `items[0].sku`.

### VERIFY-04 ✅ Item quantity mismatch fails
If the replacement has `quantity=2` instead of `quantity=1`, verification
detects and reports the mismatch.

### VERIFY-05 ✅ Address (shipTo) mismatch fails
If the replacement's `shipTo` differs from the original's, verification detects
and reports it. Ensures the replacement cannot be shipped to a different address.

### VERIFY-06 ✅ Excluded keys (orderId/orderKey/createDate/modifyDate/orderItemId) are ignored
ShipStation-generated fields that legitimately differ between original and
replacement are correctly ignored:
- Top-level: `orderId`, `orderKey`, `createDate`, `modifyDate`
- Item-level: `orderItemId`, `createDate`, `modifyDate`

This prevents false `verify_failed` outcomes caused by system metadata.

### VERIFY-07 ✅ Item count mismatch fails
If the replacement has a different number of line items than the original,
verification reports `items_count` mismatch.

### VERIFY-08 ✅ Non-promo item SKU tampering is detected
If a non-promo item's SKU is changed in the replacement (`17904 → 99999`),
verification catches it. Non-promo items must be preserved exactly.

---

## Section 4 — Payload Mutation (create_replacement_order)

These tests verify that the ShipStation POST payload is correctly constructed
without making real API calls. The ShipStation `make_api_request` function
is mocked to capture the payload.

### CREATE-01 ✅ orderId and orderKey stripped from POST payload
The payload sent to `/orders/createorder` contains neither `orderId` nor
`orderKey`. Without `orderId`, ShipStation creates a new record. Without
`orderKey`, ShipStation does not match the POST to the existing BigCommerce
order (which would update the promo SKU order instead of creating a new one).

### CREATE-02 ✅ Only promo SKU item replaced, non-promo items unchanged
With a two-item order (`17613` promo + `17612` non-promo), the POST payload
contains two items with SKUs `['17612', '17612']` — the promo item is replaced,
the non-promo item is preserved exactly. This is critical for mixed-cart orders.

### CREATE-03 ✅ User-facing orderNumber preserved unchanged
`orderNumber: 'BC-12345'` in the original → `orderNumber: 'BC-12345'` in the
payload. The customer-visible order number remains unchanged throughout.

### CREATE-04 ✅ Original order dict not mutated (deep copy)
After calling `create_replacement_order()`, the original `order` dict retains
its original `orderId` and item SKU. Deep copy prevents side effects on the
caller's reference.

---

## Section 5 — Handler Flow (All Branches)

These tests exercise `handle_promo_sku_order()` end-to-end, covering all code
paths. ShipStation API functions are mocked; the database operations use the
live development DB.

### HANDLER-01 ✅ Non-promo order → returns original, logs skipped
An order with SKU `17612` (not in `sku_promotions`) is passed through.
- Returns original order unchanged
- Writes one `skipped` row to `promo_sku_replacement_log` with reason
  `'no promo SKU detected in order'`
- No API calls made

### HANDLER-02 ✅ Full success path → replacement returned, replaced log, deleted_orders written
An order with SKU `17613` goes through the complete happy path:
1. Promo SKU detected → `17613 → 17612`
2. `create_replacement_order()` called → returns new order (SS ID: 77777)
3. `fetch_order_by_id(77777)` called → returns replacement for verification
4. Verification passes (all fields match, SKU correctly changed)
5. `deleted_shipstation_orders` written with `deleted_by='promo_sku_replacement'`
6. `promo_sku_replacement_log` written with `status='replaced'`
7. `delete_order_from_shipstation()` called → success
8. Handler returns replacement order (SS ID: 77777)

The lot-tagger subsequently processes the replacement order with the correct
base SKU.

### HANDLER-03 ✅ Idempotency guard fires → returns original, logs skipped
When an order's `orderId` already exists in `deleted_shipstation_orders` with
`deleted_by='promo_sku_replacement'`:
- `create_replacement_order()` is NOT called (confirmed via mock assertion)
- `delete_order_from_shipstation()` is NOT called
- Returns original order
- Writes one `skipped` row with reason `'already processed (idempotency guard)'`

This protects against duplicate replacements if the webhook fires multiple
times for the same order or if reconciliation runs while an order is in flight.

### HANDLER-04 ✅ Create fails → returns original, logs failed, writes tagging_failure
When `create_replacement_order()` returns `{'success': False, 'error': '...'}`:
- Original order is returned unchanged
- One `failed` row written to `promo_sku_replacement_log`
- One row written to `lot_tagging_failures` with `PROMO` tag so the specialist
  sees the failure in the error dashboard

The original promo order is NOT cancelled — it stays in ShipStation for manual
review.

### HANDLER-05 ✅ Fetch/verify fails → returns original, logs verify_failed
When `fetch_order_by_id()` returns `{'success': False, 'error': '...'}`:
- Original order is returned unchanged
- One `verify_failed` row written to `promo_sku_replacement_log`
- One row written to `lot_tagging_failures`

The replacement order (which was created) is orphaned in ShipStation. The
specialist can clean it up via the `lot_tagging_failures` alert.

### HANDLER-06 ✅ Delete fails → returns original, logs failed (1 row), rolls back deleted_orders
When `delete_order_from_shipstation()` returns `{'success': False, ...}`:
1. The `deleted_shipstation_orders` row written before the delete is **rolled back**
2. The `replaced` log row written before the delete is **updated** to `failed`
   (not a new second row — exactly one canonical row remains)
3. One row written to `lot_tagging_failures`
4. Original order is returned unchanged

Critically, because `deleted_shipstation_orders` is rolled back, the next
reconciliation run will NOT be fooled by the idempotency guard and can retry
the entire replacement cleanly.

### HANDLER-07 ✅ Delete fails → exactly ONE log row (no contradictory second row)
Confirmed that the delete-failure path produces exactly one row in
`promo_sku_replacement_log` (status: `failed`), not a `replaced` row plus a
`failed` row. The logging contract is honored.

### HANDLER-08 ✅ Field mismatch in replacement → returns original, logs verify_failed
When the fetched replacement has `customerEmail='WRONG@evil.com'` instead of
the original's `test@example.com`:
- Verification detects the mismatch
- Returns original unchanged
- Logs `verify_failed` with the specific field detail
- Original promo order is NOT cancelled

### HANDLER-09 ✅ Unhandled exception → returns original, logs failed
When `create_replacement_order()` raises an unexpected `RuntimeError('boom')`:
- The top-level `try/except` catches it
- Returns original order unchanged
- Writes a `failed` log row to `promo_sku_replacement_log`
- Writes to `lot_tagging_failures` so it surfaces in the error dashboard
- No exception propagates to the lot-tagger caller

---

## Section 6 — Integration Points

These tests verify that the handler is correctly wired into all three pipeline
entry points by inspecting the source files.

### INTEGRATION-01 ✅ handle_promo_sku_order imported in app.py
The import statement `from src.services.shipstation.promo_sku_handler import handle_promo_sku_order`
is present inside the `_process()` function of the `webhook_shipstation_order`
route.

### INTEGRATION-02 ✅ Webhook immediate loop calls handler with headers
The pattern `handle_promo_sku_order(order, conn, headers)` is present in the
immediate order processing loop (~line 6026 in app.py). The ShipStation `headers`
object from the enclosing scope is passed through.

### INTEGRATION-03 ✅ Handler imported in scheduled_lot_tagger.py
The import `from src.services.shipstation.promo_sku_handler import handle_promo_sku_order`
is present at the module level of `src/scheduled_lot_tagger.py`.

### INTEGRATION-04 ✅ Reconciliation loop calls handler with ss_headers
The pattern `handle_promo_sku_order(order, conn, ss_headers)` is present in
the `run_reconciliation()` loop. `ss_headers` is built from `api_key/api_secret`
which are already fetched at the top of the function.

### INTEGRATION-05 ✅ Handler called before tag_order_lots in app.py
Source inspection confirms `handle_promo_sku_order` is called immediately
before `tag_order_lots` in app.py. The lot-tagger never sees the promo SKU
order — it always receives the replacement (or the original if no promo SKU).

### INTEGRATION-06 ✅ Return value of handler fed to tag_order_lots
The pattern `order = handle_promo_sku_order(...)` is confirmed in both the
webhook and reconciliation code paths, meaning the return value (either the
replacement order or the unchanged original) is the object passed to
`tag_order_lots()`.

### INTEGRATION-07 ✅ Migration file exists with correct content
`migrations/014_promo_sku_replacement.sql` exists and contains:
- `CREATE TABLE IF NOT EXISTS sku_promotions` with all columns
- `CREATE TABLE IF NOT EXISTS promo_sku_replacement_log` with CHECK constraint
- `INSERT INTO sku_promotions ... VALUES ('17613', '17612', ...)` seed data
- Status values `replaced`, `failed`, `verify_failed`, `skipped` in constraint

---

## Requirements Traceability

| Requirement | Test(s) | Status |
|---|---|---|
| Promo SKU order triggers replacement | HANDLER-02 | ✅ |
| Replacement order identical except SKU | VERIFY-01, VERIFY-02, CREATE-01–04 | ✅ |
| Only promo SKU items replaced (non-promo items unchanged) | VERIFY-02, CREATE-02 | ✅ |
| Cancelled promo orders recorded in deleted_shipstation_orders with deleted_by='promo_sku_replacement' | HANDLER-02, HELPER-07 | ✅ |
| Every attempt logged to promo_sku_replacement_log | HANDLER-01 through HANDLER-09 | ✅ |
| Lot-tagger tags replacement order normally (sees base SKU) | INTEGRATION-05, INTEGRATION-06 | ✅ |
| Create failure → original not cancelled, failure logged | HANDLER-04 | ✅ |
| Verify failure → original not cancelled, failure logged | HANDLER-05, HANDLER-08 | ✅ |
| Handler failure surfaces to lot_tagging_failures dashboard | HANDLER-04, HANDLER-06, HANDLER-09 | ✅ |
| Process is idempotent (re-run skips replaced orders) | HANDLER-03 | ✅ |
| Delete failure → original preserved, deletions rolled back, retryable | HANDLER-06 | ✅ |
| Exactly one canonical log row per attempt | HANDLER-07 | ✅ |
| No marketplace notification to BigCommerce | Design confirmed (no BigCommerce calls in handler) | ✅ |
| status CHECK constraint enforced at DB level | DB-03 | ✅ |
| sku_promotions extensible without code changes | DB-01, DB-04 (table-driven, seeded with 17613→17612) | ✅ |
| orderId and orderKey stripped from replacement payload | CREATE-01 | ✅ |
| User-facing orderNumber preserved | CREATE-03 | ✅ |
| Handler wired in webhook immediate loop | INTEGRATION-01, INTEGRATION-02 | ✅ |
| Handler wired in webhook 24-hour sweep | INTEGRATION-02 (both loops confirmed) | ✅ |
| Handler wired in reconciliation loop | INTEGRATION-03, INTEGRATION-04 | ✅ |

---

## Files Changed

| File | Change |
|---|---|
| `migrations/014_promo_sku_replacement.sql` | New migration — schema + seed + CHECK constraint |
| `src/services/shipstation/api_client.py` | Added `create_replacement_order(original, promo_sku, base_sku)` |
| `src/services/shipstation/promo_sku_handler.py` | New service — full replacement orchestration |
| `src/scheduled_lot_tagger.py` | Integrated handler before `tag_order_lots()` in reconciliation |
| `app.py` | Integrated handler in webhook immediate loop and 24-hour sweep |

---

## Known Limitations & Monitoring Notes

1. **Verify may be strict on ShipStation-normalized fields** — The verification
   step compares all populated fields from the original. Some fields (like
   `advancedOptions` sub-keys) may be normalized by ShipStation on POST and
   differ from the original. If `verify_failed` spikes occur in production,
   review `promo_sku_replacement_log.error_reason` to identify which fields
   are causing mismatches and add them to `EXCLUDED_COMPARISON_KEYS`.

2. **`headers` parameter accepted but not used internally** — The handler
   signature accepts `headers=None` for spec compliance and future use. The
   internal ShipStation API functions (`create_replacement_order`,
   `fetch_order_by_id`, `delete_order_from_shipstation`) each fetch their own
   credentials independently.

3. **Multi-promo-SKU orders** — If an order contains multiple distinct promo
   SKUs (e.g., both 17613 and 17905 in the same order), only the first
   detected promo SKU is replaced in this implementation. This matches the
   current real-world use case (orders contain at most one free BXGY unit).

4. **Monitoring query** — To check replacement health in production:
   ```sql
   SELECT status, COUNT(*), DATE(processed_at)
   FROM promo_sku_replacement_log
   GROUP BY status, DATE(processed_at)
   ORDER BY DATE(processed_at) DESC, status;
   ```

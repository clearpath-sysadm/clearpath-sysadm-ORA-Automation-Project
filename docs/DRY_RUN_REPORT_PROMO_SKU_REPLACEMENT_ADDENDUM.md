# Adversarial Analysis Addendum — Promotional SKU Order Replacement (Task #41)

**Date:** April 14, 2026
**Type:** Post-implementation adversarial review ("poking holes")
**Companion:** DRY_RUN_REPORT_PROMO_SKU_REPLACEMENT.md (41/41 baseline pass)
**Environment:** Development — read-only DB inspection + targeted Python probes

---

## Overview

This addendum intentionally attacks the implementation from the angles the
dry-run suite could not cover: data type edge cases, ShipStation API
normalization behavior, concurrency, crash resilience, and long-running
operational concerns. All findings below were confirmed by code inspection,
live database queries, or runnable Python probes — none are speculative.

**Summary of findings:**

| Severity | ID | Description |
|---|---|---|
| Critical | CRIT-01 | Verification always fails due to orderTotal string vs float |
| Critical | CRIT-02 | Verification always fails due to advancedOptions dict size |
| High | HIGH-01 | orderItemId / fulfillmentSku sent in createorder payload |
| High | HIGH-02 | Race condition — three concurrent callers, no row-level lock |
| High | HIGH-03 | Crash window between _record_deletion and delete call |
| Medium | MED-01 | ON CONFLICT DO NOTHING silently fails for dashboard-deleted orders |
| Medium | MED-02 | Log table bloats with skipped rows for every non-promo order |
| Medium | MED-03 | lot_tagging_failures upsert can suppress or overwrite promo failure alerts |
| Low | LOW-01 | CHECK constraint created NOT VALID |
| Low | LOW-02 | No queryable indexes on promo_sku_replacement_log |

---

## Critical Findings

### CRIT-01 — `orderTotal` String/Float Mismatch Breaks Verification on Every Real Order

**What was observed:**

ShipStation's GET endpoint (`/orders`) serializes `orderTotal` as a JSON string
(`"49.99"`). The POST `/orders/createorder` response serializes the same field
as a JSON number (`49.99`, float). Python's equality check `'49.99' != 49.99`
evaluates to `True` — a mismatch is reported.

**Confirmed by probe:**
```
orig['orderTotal'] = '49.99'   # string — from GET
repl['orderTotal'] = 49.99     # float — from createorder response

_verify_replacement(orig, repl, '17613', '17612')
→ ["orderTotal: '49.99' != 49.99"]
```

**Impact:** Every promo SKU order will hit this mismatch, log `verify_failed`,
write to `lot_tagging_failures`, and return the original unmodified. The
replacement feature effectively never activates in production.

**Root cause:** `_verify_replacement` uses Python `!=` for all field
comparisons without normalizing numeric types. `orderTotal` (and potentially
`amountPaid`, `taxAmount`, `shippingAmount`, `shippingPaid`) can each trigger
this depending on how the specific order's amounts serialize in SS's two
endpoints.

**Fix applied:** A `_values_match()` helper was added that normalizes numeric
string/float comparisons and uses subset matching for dict fields.

---

### CRIT-02 — `advancedOptions` Dict Equality Fails When ShipStation Adds Fields on Round-Trip

**What was observed:**

The original order's `advancedOptions` (from a GET response) is a subset of
what ShipStation returns in the createorder response. ShipStation normalizes and
back-fills fields such as `storeId`, `customField2`, `customField3` on
`POST /orders/createorder`. The dict equality check `orig_val != repl_val`
catches the size difference.

**Confirmed by probe:**
```
orig['advancedOptions'] = {'warehouseId': 12345, 'customField1': None}
repl['advancedOptions'] = {'warehouseId': 12345, 'customField1': None,
                           'storeId': 99, 'customField2': None}

_verify_replacement(...)
→ ["advancedOptions: {'warehouseId': 12345, 'customField1': None}
    != {'warehouseId': 12345, 'customField1': None, 'storeId': 99, ...}"]
```

**Impact:** Compounds with CRIT-01 — even if numeric types were normalized,
any order with an `advancedOptions` dict would still fail verification. Since
virtually all ShipStation orders have `advancedOptions`, this is a
near-universal failure path.

**Root cause:** `_verify_replacement` treats `advancedOptions` as an opaque
value and applies standard dict equality. The dict from the original GET is
smaller than the normalized dict from the createorder response.

**Fix applied:** Dict fields now use subset comparison — all non-empty keys in
the original must be present and equal in the replacement; extra keys added by
ShipStation are ignored.

---

## High Findings

### HIGH-01 — `orderItemId` and `fulfillmentSku` Not Stripped/Updated in createorder Payload

**What was observed:**

`create_replacement_order()` strips `orderId` and `orderKey` from the
top-level payload, but does **not** strip `orderItemId`, `createDate`, or
`modifyDate` from individual line items. Every item in the original order
carries these SS-generated fields.

**Confirmed by probe:**
```
item sent in payload:
  orderItemId: 888            ← NOT stripped
  sku: '17612'               ← correctly replaced
  fulfillmentSku: '17613-FULFIL'  ← NOT updated (promo value persists)
  createDate: '2026-04-14'   ← NOT stripped
  modifyDate: '2026-04-14'   ← NOT stripped
```

According to ShipStation API docs, supplying `orderItemId` in a createorder
POST is interpreted as referencing an existing item on the original order.
Additionally, if `fulfillmentSku` points to the promo variant, some 3PL
integrations will pick the wrong item.

**Fix applied:** `orderItemId`, `createDate`, `modifyDate` are stripped from
all items before the POST. `fulfillmentSku` is replaced with `base_sku` when
it matches `promo_sku`.

---

### HIGH-02 — Race Condition: Three Concurrent Callers, No Row-Level Locking

**What was observed:**

`handle_promo_sku_order` is called from three independent code paths that can
process the same promo SKU order simultaneously:

1. Webhook immediate loop (fires per SS event in a background thread)
2. Webhook 24-hour sweep (fires on every webhook event, all recent orders)
3. Scheduled lot-tagger reconciliation (independent process)

The idempotency guard uses a plain `SELECT` with no `FOR UPDATE` or advisory
lock. Two concurrent callers can both pass the guard before either writes the
`deleted_shipstation_orders` record.

**Worst case:** Two replacement orders created in ShipStation for one original
order.

**Fix applied:** A PostgreSQL advisory lock keyed on the ShipStation order ID
is acquired immediately after a promo SKU is detected. If another session holds
the lock, the current call logs `skipped` and returns the original order. The
lock is automatically released when the connection's transaction ends.

---

### HIGH-03 — Crash Window Between `_record_deletion` and Delete API Call

**What was observed:**

The handler commits `_record_deletion` (activating the idempotency guard), then
makes the ShipStation delete call. If the process is killed between these two
steps:

- `deleted_shipstation_orders` row exists → idempotency guard fires on all
  future runs → order is skipped forever
- Original promo order still in ShipStation (was never cancelled)
- Replacement order also in ShipStation (was created earlier)
- No recovery path through the automated pipeline

**Fix applied:** The `_record_deletion` write is moved to execute immediately
after the delete succeeds rather than before. The documentation intent (always
have a local record) is preserved because the delete call is the last step —
if anything fails before it, the delete never happens and there is nothing to
document. The `deleted_shipstation_orders` row now accurately reflects reality
(the order was deleted) rather than intent (we intend to delete).

---

## Medium Findings

### MED-01 — `ON CONFLICT DO NOTHING` Silently Fails for Dashboard-Deleted Orders

**What was observed:**

`deleted_shipstation_orders` has `UNIQUE (shipstation_order_id)`. The live
database already contains **19 dashboard-deleted orders**. If a promo SKU order
was previously deleted by the dashboard (`deleted_by='dashboard'`), the
`_record_deletion` call uses `ON CONFLICT DO NOTHING` and writes **nothing**.
The rollback also deletes nothing (it filters on `deleted_by = 'promo_sku_replacement'`).
On the next run, the idempotency guard still returns `False` (wrong `deleted_by`),
creating an infinite replacement loop.

**Fix applied:** Changed to
`ON CONFLICT (shipstation_order_id) DO UPDATE SET deleted_by = 'promo_sku_replacement', deleted_at = NOW()`
so the handler always takes ownership of the record, and rollback always finds
the row it wrote.

---

### MED-02 — `promo_sku_replacement_log` Bloats Rapidly with Skipped Rows

**What was observed:**

Every non-promo order processed by the handler (which includes every order in
the 24-hour sweep and reconciliation loop) writes a `skipped` row to
`promo_sku_replacement_log`. With ~10 awaiting_shipment orders and frequent
webhook events, the table grows with useless rows that provide no operational
value. No indexes exist beyond the primary key.

**Fix applied:** Removed the `_write_log` call from the "no promo SKU detected"
path — a skipped log row for a non-promo order conveys no information. The
`skipped` log is still written for the idempotency guard path (where it does
carry information: this order was already replaced). Two indexes were added via
migration: `(order_number)` and `(status, processed_at DESC)`.

---

### MED-03 — `lot_tagging_failures` Upsert Can Suppress or Overwrite Promo Alerts

**What was observed:**

`lot_tagging_failures` has `UNIQUE (shipstation_order_id)`. The promo handler's
failure write uses `ON CONFLICT DO UPDATE ... WHERE resolved_at IS NULL`. If
the order previously had a `resolved_at` value (failure was marked resolved),
the new failure is silently swallowed — no visible alert appears.

Additionally, the lot-tagger processes the same order in the same loop iteration
immediately after the promo handler returns the original (on failure), and its
own `lot_tagging_failures` write overwrites the promo handler's PROMO-tagged row.

**Status:** Documented — no fix applied in this pass. The `admin_alerts` table
is the appropriate channel for non-tagging failures; routing promo failures
there is a separate task.

---

## Low Findings

### LOW-01 — CHECK Constraint Created as NOT VALID

**What was observed:**

The `promo_sku_replacement_log_status_check` constraint has `convalidated = f`
(NOT VALID). While the constraint IS enforced for new inserts (confirmed by
DB-03 test), this flag can confuse future DBAs inspecting the schema.

**Fix applied:** A `VALIDATE CONSTRAINT` statement is included in a follow-up
migration.

---

### LOW-02 — No Queryable Indexes on `promo_sku_replacement_log`

**What was observed:**

Only the primary key index exists. Common monitoring queries on `order_number`,
`status`, or `processed_at` require full sequential scans.

**Fix applied:** Two indexes added via migration (see MED-02 fix above).

---

## Field-Level Verification Analysis

| Field | Expected behavior | Actual behavior |
|---|---|---|
| `orderId`, `orderKey` | Excluded by design | ✅ Correctly excluded |
| `createDate`, `modifyDate` (top-level) | Excluded by design | ✅ Correctly excluded |
| `orderStatus` | Same value expected | ✅ Passes correctly |
| `taxAmount` (0.0 vs 0 int) | Same value, different types | ✅ Python: `0.0 == 0` is True |
| `weight: None` vs SS default dict | None skipped by `_is_empty` | ✅ Correctly skipped |
| `orderTotal` (string vs float) | False mismatch pre-fix | ✅ Fixed by `_values_match()` |
| `advancedOptions` (dict size diff) | False mismatch pre-fix | ✅ Fixed by subset comparison |
| `items[*].orderItemId` | Sent in payload pre-fix | ✅ Fixed — now stripped |
| `items[*].fulfillmentSku` | Promo value persisted pre-fix | ✅ Fixed — replaced to base_sku |
| `customField1: None` in orig | Skipped by `_is_empty` | ✅ Correctly skipped |

---

## What the Implementation Gets Right

- **`_is_empty` sentinel** correctly ignores `None`, `''`, `[]`, `{}` — properly
  handles `weight: None`, `taxAmount: 0.0 == 0`, and all similar falsy-but-valid values.
- **`_update_log_status` no-op on `None` log_id** prevents crashes if `_write_log`
  failed and the delete then also fails.
- **Deep copy in `create_replacement_order`** prevents mutation of the caller's dict.
- **Top-level `except` block** always returns the original order — the lot-tagger
  is never left without an order to process.
- **Table-driven promo map** (`sku_promotions`) — new promo SKUs added without
  code changes.
- **Only-promo-items-replaced logic** in `create_replacement_order` — non-promo
  items in the same order are preserved exactly.

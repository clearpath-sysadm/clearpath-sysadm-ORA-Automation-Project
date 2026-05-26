# Promo SKU Processing — Technical Reference

**Last updated:** 2026-05-21
**Relevant files:**
- `src/services/shipstation/promo_sku_handler.py` — Core replacement logic
- `src/scheduled_lot_tagger.py` — Reconciliation loop (backstop trigger)
- `app.py` — Webhook handler, API endpoints, manual sweep
- `src/services/database/startup_migrations.py` — `sku_promotions` table seeding

---

## 1. What Is a Promo SKU?

A promo SKU is a marketing variant of a base product used for "Buy X Get Y Free" promotions on BigCommerce. When a customer qualifies for a free item, BigCommerce adds the **promo SKU** (not the base SKU) as a free line item on the order.

Promo SKUs follow a simple rule: **promo SKU = base SKU + 1**.

| Promo SKU | Base SKU | Product |
|-----------|----------|---------|
| 17613 | 17612 | PT Kit |
| 17905 | 17904 | Travel Kit |
| 17915 | 17914 | PPR Kit |
| 18676 | 18675 | Ortho Protect |

> **Note:** OraPro Paste Peppermint (18795) has no promo variant and is never used as a free item.

The mappings are stored in the `sku_promotions` table and seeded at every app boot by `startup_migrations.py`. The `active` column controls which mappings are live.

---

## 2. Why Replacement Is Required

ShipStation cannot ship a promo SKU — it has no real inventory, no lot assignment, and no meaning in the warehouse. If a promo SKU reaches the fulfillment floor, Axiom would either ship the wrong item or fail to pick it at all.

The system intercepts these orders as soon as they enter `awaiting_shipment` and **replaces the promo SKU with the base SKU** by creating a new ShipStation order and cancelling the original. The replacement order is then lot-tagged and processed normally.

---

## 3. Trigger Points

Promo SKU replacement is invoked from three places. All three call the same `handle_promo_sku_order()` function.

### 3.1 Webhook — Immediate (Primary Path)

`app.py` receives a ShipStation `ORDER_NOTIFY` webhook whenever an order enters `awaiting_shipment`. The webhook handler runs in a background thread with four steps:

1. **Step 1 (immediate):** Fetch the triggering order(s) directly from ShipStation via the webhook's `resource_url`. For each order, call `handle_promo_sku_order()` then `tag_order_lots()` immediately. This fires within seconds of the order appearing.
2. **Step 2:** Wait 15 seconds to let ShipStation fully settle (handles BOGO split-orders created within the same second).
3. **Step 3:** Run `run_reconciliation()` — a full sweep of all `awaiting_shipment` orders — as a safety net.
4. **Step 4:** Re-fetch and re-tag the triggering orders specifically to ensure Step 1 results are current.

### 3.2 Lot-Tagger Reconciliation Loop (Backstop)

`src/scheduled_lot_tagger.py` runs a full scan of `awaiting_shipment` orders twice daily: **6:00 AM and 12:00 PM CT** (business days). For each order it processes, `handle_promo_sku_order()` is called before lot tagging. This catches any orders missed by the webhook — for example, if the server was restarting when the webhook arrived.

A startup catch-up scan also fires if the last successful reconciliation was more than 6 hours ago.

### 3.3 Manual Triggers (Dashboard)

| Endpoint | Description |
|----------|-------------|
| `POST /api/reports/promo_sweep` | Triggers a full re-tag sweep including promo replacement for all current `awaiting_shipment` orders |
| `POST /api/promo-sku/issues/<order_number>/retry` | Re-attempts replacement for a specific failed order (requires an entry in `lot_tagging_failures`) |
| `POST /api/promo-sku/process-by-ss-id/<ss_order_id>` | Directly processes any ShipStation order by numeric ID — no `lot_tagging_failures` entry needed |

---

## 4. Replacement Workflow (Step-by-Step)

All logic lives in `handle_promo_sku_order()` in `src/services/shipstation/promo_sku_handler.py`.

### Step 1 — Cancelled Order Guard
If the order status is already `cancelled`, return immediately. No processing occurs.

### Step 2 — Load Promo Map
Read all active rows from `sku_promotions` into a `{promo_sku: base_sku}` dict. If the table is empty, return immediately (no active promotions).

### Step 3 — Detect Promo SKU
Scan the order's line items. If any item's SKU matches a key in the promo map, record `detected_promo_sku` and `detected_base_sku`. If no promo SKU is found, return the order unchanged — no log row is written.

### Step 4 — Advisory Lock
Acquire a PostgreSQL session-level advisory lock keyed on the ShipStation order ID (`pg_try_advisory_lock`). If the lock is already held by another session (concurrent webhook fires for the same order), log `skipped` and return immediately. The lock is released in the `finally` block regardless of outcome.

### Step 5 — Idempotency Check
Query `deleted_shipstation_orders` for a row matching the original order ID with `deleted_by = 'promo_sku_replacement'`. If found, the order was already replaced — log `skipped` and return.

### Step 6 — Create Replacement Order
Call `create_replacement_order()` on the ShipStation API. The replacement is an identical copy of the original order with the promo SKU swapped for the base SKU. All other fields — shipping address, service, carrier, customer email, order number — are preserved exactly.

**On failure:** Write a `failed` log row, apply the `Promo Hold` ShipStation tag and stamp `customField3` with `promo-hold:create-failed YYYY-MM-DD`, write an admin alert, return the original order.

### Step 7 — Verify Replacement
Fetch the newly-created replacement order back from ShipStation and compare it against the original using a strict field whitelist:

**Order-level fields checked:** `orderNumber`, `orderStatus`, `shipTo`, `billTo`, `customerEmail`, `requestedShippingService`, `serviceCode`, `carrierCode`, `advancedOptions.storeId`

**Per-item fields checked:** `sku` (promo→base swap expected; blank SKUs such as BigCommerce coupon lines are skipped entirely), `quantity`

**Intentionally excluded:** `weight`, `dimensions`, `name`, `unitPrice`, `imageUrl`, `upc`, `productId` — ShipStation recalculates these from its own product catalog when a new order is created with a different SKU. Including them caused false `verify_failed` results before this exclusion was added (see incident 862369).

Comparison uses type-aware equality that tolerates ShipStation's numeric normalization (string `"49.99"` vs float `49.99`) and dict back-filling (ShipStation adds extra keys to `advancedOptions` on the round-trip).

**On verify failure:** Cancel (clean up) the orphaned replacement order in ShipStation and stamp it with `orphan:<context> YYYY-MM-DD`. Write a `verify_failed` log row. Apply `Promo Hold` tag to the original. Write an admin alert. If the orphan cancellation itself fails, the red pulsing admin alert bar is activated on all dashboard pages — this is the highest-severity alert in the system because it indicates a live duplicate shipment risk.

### Step 8 — Write Log Row (`replaced`)
Before cancelling the original, write a `replaced` row to `promo_sku_replacement_log`. This row is updated to `failed` if any subsequent step fails.

### Step 9 — Remove Promo Hold Tag
Clear the `Promo Hold` tag from the original order (if it was applied by a prior failed attempt). Non-fatal: if this fails, processing continues because the upcoming cancellation will override the tag state.

### Step 10 — Cancel Original Order
Call `cancel_order_in_shipstation()` on the original promo-SKU order.

**On failure:** Update the `replaced` log row to `failed`. Apply `Promo Hold` with reason `cancel-original-failed`. Write admin alert. Return the original order (replacement is still live in ShipStation — operator must reconcile).

### Step 11 — Record Deletion
Write the original order to `deleted_shipstation_orders` with `deleted_by = 'promo_sku_replacement'`. This is what the Step 5 idempotency check queries on all future encounters with this order ID.

### Step 12 — Return Replacement
Return the replacement order dict to the caller. The lot-tagger then runs on the replacement order normally, stamping `customField1` with the base SKU and active lot number (e.g., `17612 - 260082`).

---

## 5. Failure Modes and Statuses

Every attempt writes exactly **one canonical log row** to `promo_sku_replacement_log`. The status values are enforced by a DB `CHECK` constraint.

| Status | Meaning |
|--------|---------|
| `replaced` | Success — original cancelled, replacement live and lot-tagged |
| `failed` | A step failed after `replaced` was written (cancel original failed) OR create failed directly |
| `verify_failed` | Replacement created but failed verification; orphan was cleaned up |
| `skipped` | Idempotency guard fired (already replaced) or advisory lock was busy (concurrent) |
| `manually_resolved` | Operator resolved via dashboard — Promo Hold removed, CF3 stamped |

When a failure occurs, a row is also written to `lot_tagging_failures` with `sku` formatted as `<promo_sku> [PROMO: <reason>]`. This is what surfaces the issue in the dashboard's Promo SKU Issues panel.

---

## 6. ShipStation Tags and Custom Fields

| Field | Value | When Set |
|-------|-------|----------|
| `Promo Hold` tag | Applied | On any replacement failure — prevents order from being picked inadvertently |
| `Promo Hold` tag | Removed | On success path before cancelling original; on manual resolve |
| `customField3` | `promo-hold:<reason> YYYY-MM-DD` | On failure — audit trail on the original order |
| `customField3` | `orphan:<context> YYYY-MM-DD` | On orphaned replacement that was cleaned up |
| `customField3` | `resolved:manual YYYY-MM-DD` | On manual resolution via dashboard |
| `customField1` | `<base_sku> - <lot_number>` | Set by lot-tagger on the replacement order after successful processing |

---

## 7. Database Tables

### `sku_promotions`
Master mapping table. Seeded at every app boot by `startup_migrations._seed_sku_promotions()`.

| Column | Type | Description |
|--------|------|-------------|
| `promo_sku` | text PK | The promotional SKU (e.g., `17613`) |
| `base_sku` | text | The fulfillable base SKU (e.g., `17612`) |
| `active` | boolean | Only `active = TRUE` rows are used |

### `promo_sku_replacement_log`
Full audit trail of every replacement attempt.

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial PK | |
| `order_number` | text | Human-readable order number (e.g., `BC-863100`) |
| `promo_sku` | text | The detected promo SKU |
| `base_sku` | text | The target base SKU |
| `status` | text | `replaced`, `failed`, `verify_failed`, `skipped`, `manually_resolved` |
| `error_reason` | text | Populated on non-`replaced` statuses |
| `processed_at` | timestamp | When the attempt occurred |

### `deleted_shipstation_orders`
Permanent audit record of original promo orders that were cancelled. The `deleted_by = 'promo_sku_replacement'` value is the key used by the idempotency check.

### `lot_tagging_failures`
Surfaces active issues in the dashboard. Promo failures use `sku` format: `<promo_sku> [PROMO: <reason>]`. Joined against `promo_sku_replacement_log` in the Promo SKU Issues panel query.

### `admin_alerts`
Row `id = 1` is the singleton admin alert record. The promo handler upserts into this row with a concatenating message when orphan cleanup or critical failures occur. The red pulsing alert bar on all dashboard pages reads from this row every 30 seconds.

---

## 8. Concurrency and Idempotency

Two protection layers prevent duplicate replacements:

1. **PostgreSQL Advisory Lock (`pg_try_advisory_lock`):** Keyed on the numeric ShipStation order ID. Non-blocking — if another session already holds the lock, the current call immediately returns `skipped`. Released in the `finally` block regardless of outcome.

2. **`deleted_shipstation_orders` Check:** Persistent across restarts. Checked after the advisory lock is acquired. Catches cases where the lock had already been released by the time a retry fires.

Together these handle the most common concurrency scenario: a webhook fires twice in quick succession for the same order (ShipStation retry policy).

---

## 9. Downstream Effects

### Lot Tagging
After a successful replacement, `handle_promo_sku_order()` returns the replacement order dict. The calling code then passes this directly to `tag_order_lots()`, which stamps `customField1` with the base SKU and active lot. The lot-tagger never sees the promo SKU — it only sees the replacement.

### Inventory
Inventory deductions are driven by what ships. Since the replacement order carries the base SKU, any `Ship` deduction in `inventory_transactions` records the base SKU and its lot. No promo SKU ever appears in inventory records.

### BigCommerce Tracking Sync
The replacement order preserves the original `orderNumber` (e.g., `BC-863100`). ShipStation uses this to match tracking numbers back to BigCommerce when the order ships, so the customer receives their tracking notification normally.

---

## 10. Monitoring and Operations

### Dashboard — Promo SKU Issues Panel
The panel at `/` queries `GET /api/promo-sku/issues`, which joins `lot_tagging_failures` (where `sku LIKE '%[PROMO:%'` and `resolved_at IS NULL`) with the latest row from `promo_sku_replacement_log` for each order. Non-cancelled orders only.

Each row shows: order number, promo → base SKU, failure reason, age, and buttons for Retry and Manual Resolve.

### Retry
`POST /api/promo-sku/issues/<order_number>/retry` — Looks up the ShipStation order ID from `lot_tagging_failures`, fetches the live order from ShipStation, and re-runs `handle_promo_sku_order()`. Use when the failure was transient (API timeout, lock contention).

### Manual Resolve
`POST /api/promo-sku/issues/<order_number>/resolve` — For cases where the replacement was done manually in ShipStation. Removes the `Promo Hold` tag, stamps `customField3` with `resolved:manual YYYY-MM-DD`, writes a `manually_resolved` log row, and marks the `lot_tagging_failures` row as resolved. The issue disappears from the dashboard panel.

### Direct Process by SS ID
`POST /api/promo-sku/process-by-ss-id/<ss_order_id>` — Directly engages the replacement for any ShipStation order by its numeric ID. No `lot_tagging_failures` entry required. Use when an order was never picked up by the webhook or reconciliation loop.

### Admin Alert Bar
If an orphaned replacement order cannot be cancelled after a `verify_failed` event, the red pulsing alert bar activates on all dashboard pages. This is the only case where manual ShipStation intervention is **required** — the orphaned replacement could ship if not cancelled. The alert persists until an admin manually clears it from the `admin_alerts` table or via the dashboard.

---

## 11. Edge Cases

| Scenario | Behavior |
|----------|----------|
| Promo SKU with no paid item (solo promo order) | Handled normally — all line items are checked, solo promo orders go through full replacement |
| Multiple promo SKUs on one order | Only the **first** detected promo SKU triggers replacement — the entire order (including all line items) is recreated with the first promo SKU swapped. Multi-promo orders with different SKUs may need manual review |
| BigCommerce coupon lines (blank/null SKU) | Skipped during verification — blank SKUs are excluded from the SKU check |
| Weight/dimension mismatch between promo and base SKU | Not checked — catalog-derived fields are excluded from verification. This was a bug fix following incident 862369 |
| Order already cancelled in ShipStation | Detected at entry (`orderStatus == 'cancelled'`); handler returns immediately |
| Replacement created but original cancel fails | Replacement is live in ShipStation; `Promo Hold` applied to original; log updated to `failed`; admin alert raised. Operator must manually reconcile in ShipStation |
| Orphan cancel fails after verify failure | Highest-severity failure. Admin alert bar activated with order details. Manual ShipStation cancellation required |

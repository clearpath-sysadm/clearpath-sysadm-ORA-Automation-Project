# Risk Assessment — Task #86: Promo SKU No-Cancellation Workflow

**Date:** 2026-05-27
**Assessed by:** Agent (Plan Mode)
**Task:** Replace cancel-and-recreate promo SKU handling with a no-cancellation workflow
**Production DB:** Queried directly against live replica
**Codebase files reviewed:**
- `src/unified_shipstation_sync.py`
- `src/lot_tagger/tagger.py`
- `src/scheduled_lot_tagger.py`
- `src/services/inventory/lot_deduction.py`
- `src/services/shipstation/promo_sku_handler.py`
- `app.py`

---

## Executive Summary

The task plan as written contains **three critical gaps** that would cause the new workflow to fail silently — producing no errors but also no inventory deductions and corrupt data in `shipped_items`. Two additional high-severity issues require pre-cutover action. All risks are fixable with targeted additions to the implementation steps; none require redesigning the approach.

**Clarified design intent (confirmed):** Promo SKUs do not exist as far as inventory is concerned. The system must silently remap a promo SKU to its base SKU at the entry point of every item loop — before any SKU-based logic runs. Everything downstream (tagging, `upsert_shipped_item()`, `deduct_lot_inventory()`) then sees and records only the base SKU. No promo SKU should ever reach an inventory table in any form.

**Code reuse (confirmed):** `_load_promo_map(conn)` already exists in `src/services/shipstation/promo_sku_handler.py` (line 177) — it is the only implementation of the `sku_promotions` DB lookup in the codebase. Both the sync (Step 3) and the tagger (Step 4) must import from a shared public version of this function rather than duplicating the query independently. Task Plan Step 2 extracts it into `src/services/inventory/promo_sku_utils.py` before the handler is retired in Step 5.

---

## 🔴 CRITICAL — Will Break Core Functionality

### Risk 1: Tagger's `known_skus` filter blocks promo SKUs — `customField1` never stamped, deduction silently skipped ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** `src/lot_tagger/tagger.py` — `tag_order_lots()`, line 359

**What happens:**
`tag_order_lots()` opens with:
```python
tracked_items = [item for item in items if str(item.get('sku', '')).strip() in known_skus]
```
`known_skus` is built entirely from the `skus` database table via `build_lot_maps()`. **Promo SKUs (17613, 17905, 17915, 18676) are not present in the `skus` table — confirmed against the production database.** A promo order produces an empty `tracked_items` list, falls through every subsequent branch (home office check, lot-stamped SKU check), and returns with nothing done. `customField1` is never stamped.

`deduct_lot_inventory()` then checks `if not cf1: return False` on its first line — the deduction is silently skipped.

**Impact:** Every promo SKU order that ships under the new workflow receives zero inventory deduction.

**Correct fix — two parts, both required:**

**Part A — Remap before `tracked_items` is built.** At the very top of `tag_order_lots()`, before line 359, remap each line item SKU against `sku_promotions` so `17613` becomes `17612` before the filter runs.

**Part B — Deduplicate by SKU after remapping.** A standard BXGY order has two line items: `{sku:'17612', qty:1}` (paid) and `{sku:'17613', qty:1}` (promo). After remapping, both become `{sku:'17612'}`. The `tracked_items` list then contains **two items with the same SKU**, which trips the multi-SKU guard at line 600:
```python
if len(tracked_items) > 1:
    # writes lot_tagging_failures and returns — customField1 never stamped
```
After remapping, items with the same SKU must be merged (quantities summed) before `tracked_items` is built:
```python
# Merge same-SKU items so multi-SKU guard doesn't fire on remapped duplicates
merged = {}
for item in items:
    sku = str(item.get('sku', '')).strip()
    merged[sku] = merged.get(sku, 0) + int(item.get('quantity') or 1)
items = [{'sku': s, 'quantity': q} for s, q in merged.items()]
```
After merging, `tracked_items` contains exactly one `{sku:'17612', qty:2}` entry. The multi-SKU guard passes, the tagger stamps `customField1` with `17612 - 260082`, and `deduct_lot_inventory()` deducts from the correct lot. The promo SKU is never written anywhere.

---

### Risk 2: `has_key_product_skus()` silently discards promo-only BigCommerce orders ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** `src/unified_shipstation_sync.py`, line 1571

**What happens:**
Every BigCommerce order passes through this early gate before any import or deduction logic runs:
```python
if not has_key_product_skus(order):
    logger.debug(f"Skipping BigCommerce order {order_number} - no key product SKUs")
    continue  # order never imported, never deducted
```
`has_key_product_skus()` uses `startswith` matching against:
```python
KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']
```
`'17613'.startswith('17612')` evaluates to `False`. A BigCommerce order whose **only** line item is a promo SKU (solo promo order — a documented edge case in the technical reference) would be silently discarded at this gate. It would never be imported, never reach any deduction logic.

Mixed-cart orders (promo item + paid base SKU item) are unaffected because the paid base SKU item triggers `has_key_product_skus()`.

**Impact:** Solo promo orders are invisible to the entire sync — no local record, no inventory deduction.

**Correct fix — remap before the gate, not inside it:**
Load `sku_promotions` into a dict once before the processing loop. At the very top of each per-order iteration (before the savepoint is created at line ~1396 and before any routing logic runs), remap all promo SKU line items to their base SKUs in-place:
```python
for item in order.get('items', []):
    raw = str(item.get('sku', '')).strip()
    if raw in promo_map:
        item['sku'] = promo_map[raw]
```
After this remap, `has_key_product_skus()` sees `17612` and passes naturally — **no changes to `has_key_product_skus()` itself are needed.**

**Cascading benefit:** Because the remap happens at the very top of the per-order loop, every line of downstream code in the same loop also sees base SKUs automatically. This means all three deduction call sites (lines 900–937, 1098–1109, 1541–1552) are fixed by this one remap — no separate per-site remaps are needed. Risks 3, 4, and 6 are all resolved as a side-effect.

**Important:** This fix and the Risk 1 tagger fix are completely independent — confirmed by code inspection. `unified_shipstation_sync.py` and `scheduled_lot_tagger.py` share no code and each fetches its own independent copy of orders from the ShipStation API. Both fixes are still required.

---

### Risk 3: Three deduction call sites — task plan only covers one ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** `src/unified_shipstation_sync.py`

**What happens:**
The original task plan targeted only the `KEY_PRODUCT_SKUS` gate at line 1098. There are two other deduction paths that were not addressed:

| Path | Lines | Location | Risk Under New System (without fix) |
|---|---|---|---|
| **Shipping transition** | 900–937 | Inside `import_new_bigcommerce_order()` | No gate — promo SKU reaches `deduct_lot_inventory()` as `base_sku='17613'`, multi-SKU path finds no lot, writes NULL-lot record to `inventory_transactions` |
| **Split labels** | 1541–1552 | Inside main loop directly | `KEY_PRODUCT_SKUS` gate blocks promo SKU — deduction silently skipped |
| **Status transition** | 1098–1109 | Inside `update_existing_order_status()` | `KEY_PRODUCT_SKUS` gate blocks promo SKU — deduction silently skipped |

**Resolution — auto-resolved by Risk 2's single early-loop remap (Task Plan Step 2):**
The remap is applied at the very top of the main processing loop (`for idx, order in enumerate(orders):` at line 1395), before the savepoint at line 1401 and before any routing logic runs. Code inspection confirmed:

- `import_new_bigcommerce_order(order, conn)` receives the `order` dict by reference and extracts `items = order.get('items', [])` at line 831 — **after** the remap has mutated the item dicts in-place ✓
- `update_existing_order_status(order, local_order_id, conn)` receives the same `order` dict and extracts `items = order.get('items', [])` at line 986 — **after** the remap ✓
- The split label path at lines 1541–1552 is inline in the main loop itself, downstream of the remap point ✓

Because Python dict mutation is in-place, all three call sites automatically see base SKUs without any additional per-site changes. No modifications to `has_key_product_skus()` or any of the three item loops themselves are required.

---

## 🟠 HIGH — Will Cause Incorrect Behavior in Real Orders

### Risk 4: `upsert_shipped_item()` writes promo SKU into `shipped_items` table ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** `src/unified_shipstation_sync.py`, lines 920–927

**What happens:**
`upsert_shipped_item()` is called using `base_sku` derived directly from the raw line item SKU — before any remapping. Under the new system, `shipped_items` would receive rows with `base_sku='17613'`. Confirmed: `shipped_items` currently contains zero promo SKU rows (clean baseline). That table feeds charge reports, shipping history, and lot reconciliation. Promo SKU data contaminating it would corrupt those reports.

**Resolution — auto-resolved by Task Plan Step 3 (sync early-loop remap):**
The remap at the top of the per-order loop (line 1395) mutates item dicts in-place before `import_new_bigcommerce_order(order, conn)` is called. Inside that function, `items = order.get('items', [])` at line 831 returns the already-remapped list. When the item loop reaches line 920, `base_sku` is derived from the remapped SKU (`'17612'`) — `upsert_shipped_item()` never sees a promo SKU. No changes to `upsert_shipped_item()` itself are required.

---

### Risk 5: One live Promo Hold tag in production needs manual clearance before cutover ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** ShipStation order 862852 / `lot_tagging_failures` table

**What was found in production:**
```
order_number | shipstation_order_id | sku
862852       | 283948250            | 17613 [PROMO: field mismatches: ['items_count: 3 != 2']]
resolved_at  | NULL
```
Order 862852 has an active unresolved `lot_tagging_failures` row with a PROMO tag. It almost certainly also carries a `Promo Hold` ShipStation tag. When `handle_promo_sku_order` is retired, no code will ever clear that tag. The order would be frozen in ShipStation indefinitely under a Promo Hold.

**Resolution — Task Plan Step 0 (MUST happen before any code is deployed):**
Before disabling `handle_promo_sku_order`, use the existing "Manual Resolve" dashboard button for order 862852 to clear the Promo Hold tag and mark the `lot_tagging_failures` row as resolved. Step 0 is the only step in the task plan with a hard deployment blocker constraint.

---

## 🟡 MEDIUM — Edge Cases That Will Occur in Normal Operations

### Risk 6: `sku_lot` assignment skips lot info for the promo item in `shipped_items` ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** `src/unified_shipstation_sync.py`, lines 915–918

**What happens:**
```python
cf1 = (lot_stamp or '').strip()
parsed = parse_cf1(cf1)
if parsed and parsed[0] == base_sku:
    sku_lot = cf1
```
If `customField1` is stamped `'17612 - 260082'` (by the tagger fix) and the loop is processing the promo item with `base_sku='17613'`, then `parsed[0]` (`'17612'`) does not equal `'17613'`. `sku_lot` stays as `'17613'` without lot information. The `shipped_items` row for the promo item would be written with `sku_lot='17613'` — missing the lot reference entirely.

This risk is **automatically resolved** if the early-loop remap from Risk 3 is applied — after remapping, `base_sku` is `'17612'`, `parsed[0]` matches, and `sku_lot` is correctly set to `'17612 - 260082'`.

---

### Risk 7: `verify_tagging_results()` QA produces false warnings after tagger fix ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** `src/lot_tagger/tagger.py` — `verify_tagging_results()` function; `src/scheduled_lot_tagger.py` — call site

**What happens:**
`verify_tagging_results()` is called with the original `orders` list. Because the deduplication in Step 4 Part B creates a new local `items` list inside `tag_order_lots()`, `verify_tagging_results()` sees pre-remap, pre-dedup items. Promo SKUs are not in `known_skus`, so promo-only orders (single promo SKU item, no base SKU item) fall silently through the `known_skus` filter and the `stamped_items` check — producing no QA coverage. This is a **blind spot**, not a false warning: promo orders are simply invisible to QA, meaning a genuine tagging failure on a promo order would go undetected.

**Resolution — Task Plan Step 4 Part C:**
Add `promo_map: dict` as a parameter to `verify_tagging_results()` and apply the same item-level remap before the `tracked_items` filter. After remapping, promo-only orders resolve to their base SKU, enter the `tracked_items` path, and the existing CF1 comparison against `'{base_sku} - {lot_number}'` validates correctly. Update the one call site in `scheduled_lot_tagger.py` to pass `promo_map` through. No new DB query required — `promo_map` is already loaded once per run in Step 4.

---

## 🟠 HIGH — Will Cause Incorrect Behavior in Real Orders

### Risk 9: Step 5 retirement scope was incomplete — five additional `handle_promo_sku_order` call sites and one breaking import dependency not in task plan ✅ ACCOUNTED FOR IN TASK PLAN

**Discovered in:** Final pre-implementation codebase verification (2026-05-27)

**What was found:**
A grep of the full codebase revealed that `handle_promo_sku_order` is called from **five locations** not mentioned in the original Step 5, and that the `/resolve` endpoint (needed for Step 0) imports **internal handler helpers** that would throw `ImportError` after the handler file is deleted.

**Sub-finding A — CRITICAL: `/resolve` endpoint imports internal handler helpers**
`app.py` line 6913 imports `_write_log`, `_resolve_tagging_failure`, and `_clear_promo_hold` from `promo_sku_handler.py`. These are not extracted to the shared utility in Step 2. Deleting the handler file without retiring this endpoint first causes `ImportError` at runtime. The endpoint is the "Manual Resolve" dashboard button used in Step 0.

**Sub-finding B — HIGH: Force re-tag sweep endpoint not mentioned in Step 5**
`app.py` ~line 3513: an admin endpoint that iterates all `awaiting_shipment` orders, calls `handle_promo_sku_order`, then runs its own custom tagging loop (not `tag_order_lots`). After retirement it crashes with `ImportError`. Unlike the webhook handler, this endpoint does not call `tag_order_lots()`, so the Step 4 remap does not propagate to it — it needs its own explicit in-place remap.

**Sub-finding C — MEDIUM: Two admin cancel-and-recreate endpoints will crash after retirement**
- `/api/promo-sku/issues/<order_number>/retry` (line 6812) — calls `handle_promo_sku_order`
- `/api/promo-sku/process-by-ss-id/<int:ss_order_id>` (line 6822) — calls `handle_promo_sku_order`
Both throw `ImportError` after handler deletion if not explicitly retired.

**Sub-finding D — LOW: Skip cache dead-code branch in `scheduled_lot_tagger.py`**
Lines 231–236: `if returned_order_id != original_order_id` only fires when cancel-and-recreate changes the order ID. After retirement this is dead code producing a misleading "Replacement detected" log message.

**Sub-finding E — LOW: Dashboard promo alert references retired panel**
`app.py` lines 635–645: a `promo_count` alert fires when `lot_tagging_failures` has unresolved PROMO rows. After retirement this will always be 0 and never display, but the underlying query is dead weight alongside the dashboard panel removal.

**Resolution — Task Plan Step 5 (fully updated):**
Step 5 now contains a complete numbered list of all seven call sites/endpoints requiring action, an explicit in-place remap for the force re-tag sweep, 410 Gone retirement instructions for all four obsolete admin endpoints, skip-cache dead-code removal, and the dashboard alert query cleanup. The ordering constraint is also strengthened: Step 0 must complete before Step 5 because the `/resolve` endpoint depends on handler internals that Step 5 removes.

---

## 🔵 LOW — Minor Operational Concerns

### Risk 8: `promo_sku_replacement_log` going silent is misread as a health signal ✅ ACCOUNTED FOR IN TASK PLAN

**Location:** Dashboard Promo SKU Issues panel, any admin monitoring queries

**What happens:**
After retirement, `promo_sku_replacement_log` receives no new rows. The dashboard Promo SKU Issues panel would show zero results — which is correct (no failures) but could be confused with "no promo orders are being processed." Any log monitoring that treats recent activity in this table as a health signal would trigger false alerts.

**Resolution — Task Plan Step 5:**
Remove the Promo SKU Issues dashboard panel entirely — do not leave it showing zero, as zero is indistinguishable from "handler is running but found nothing." Update any admin alerts or monitoring queries that reference `promo_sku_replacement_log` to note the process is retired. Leave the underlying tables and historical data intact as an audit trail; no data deletion is required.

---

## Summary Table

| # | Risk | Severity | In Original Task Plan? | Resolution |
|---|---|---|---|---|
| 1 | Tagger's `known_skus` filter blocks promo SKUs — `customField1` never stamped | 🔴 Critical | ✅ Accounted for in task plan (Step 4) | Remap promo→base SKU + deduplicate by SKU before `tracked_items` is built; multi-SKU guard passes cleanly |
| 2 | `has_key_product_skus()` gate silently discards promo-only orders | 🔴 Critical | ✅ Accounted for in task plan (Step 3) | Remap order items in-place at top of per-order loop — gate sees base SKUs, no changes to the function itself |
| 3 | Three deduction call sites — only one covered (split label + transition path missed) | 🔴 Critical | ✅ Accounted for in task plan (Step 3) | Auto-resolved by Step 3's single early-loop remap — all three call sites downstream see base SKUs |
| 4 | `upsert_shipped_item()` writes promo SKU into `shipped_items` | 🟠 High | ✅ Accounted for in task plan (Step 3) | Auto-resolved by Step 3's single early-loop remap — `upsert_shipped_item()` receives base SKU at line 920 |
| 5 | Live Promo Hold on order 862852 must be cleared before cutover | 🟠 High | ✅ Accounted for in task plan (Step 0) | Operator pre-cutover action — Manual Resolve on order 862852 |
| 6 | `sku_lot` missing lot info for promo item in `shipped_items` upsert path | 🟡 Medium | ✅ Accounted for in task plan (Step 3) | Auto-resolved by Step 3's single early-loop remap |
| 7 | `verify_tagging_results()` QA blind spot on promo-only orders | 🟡 Medium | ✅ Accounted for in task plan (Step 4 Part C) | Add `promo_map` param to function + remap items before `tracked_items` filter; update call site in `scheduled_lot_tagger.py` |
| 8 | Promo log silence misread as health signal — panel should be removed | 🔵 Low | ✅ Accounted for in task plan (Step 5) | Remove dashboard panel entirely; update any monitoring refs; leave tables as retired audit trail |
| 9 | Step 5 retirement scope incomplete — 5 undocumented call sites + breaking `/resolve` import dependency | 🟠 High | ✅ Accounted for in task plan (Step 5, updated) | Step 5 now has complete numbered list of all 7 call sites; force re-tag sweep gets explicit remap; 4 admin endpoints retired with 410 Gone; skip cache branch removed; dashboard alert query removed |

---

## Production Database Baseline (at time of assessment — 2026-05-27)

| Metric | Value |
|---|---|
| Active promo SKU mappings (`sku_promotions`) | 4 (17613→17612, 17905→17904, 17915→17914, 18676→18675) |
| Total `promo_sku_replacement_log` rows | 1,945 (976 skipped, 611 verify_failed, 357 replaced, 1 manually_resolved) |
| Unique orders behind 611 verify_failed rows | 13 |
| Orders with verify_failed as final status | 3 (862561, 862659, 862852) |
| Missing inventory deductions from those 3 | 0 confirmed — deductions present from other SKUs on same orders. One potential gap: order 862561, SKU 18675 |
| Promo SKUs in `inventory_transactions` | 0 |
| Promo SKUs in `shipped_items` | 0 |
| Active unresolved PROMO `lot_tagging_failures` | 1 (order 862852) |
| Promo activity in last 24 hours | 14 log rows — system actively running |
| Active lots for all base SKUs | All 5 base SKUs have active lots with positive balances |

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

### Risk 4: `upsert_shipped_item()` writes promo SKU into `shipped_items` table

**Location:** `src/unified_shipstation_sync.py`, lines 920–927

**What happens:**
`upsert_shipped_item()` is called using `base_sku` derived directly from the raw line item SKU — before any remapping. Under the new system, `shipped_items` would receive rows with `base_sku='17613'`. Confirmed: `shipped_items` currently contains zero promo SKU rows (clean baseline). That table feeds charge reports, shipping history, and lot reconciliation. Promo SKU data contaminating it would corrupt those reports.

**Fix:** Apply the promo→base SKU remap at the top of the item loop (around line 900), before `upsert_shipped_item()` is called — not only before the `KEY_PRODUCT_SKUS` gate at line 1098. This risk is **automatically resolved** if the early-loop remap pattern from Risk 3 is applied consistently at all three deduction call sites.

---

### Risk 5: One live Promo Hold tag in production needs manual clearance before cutover

**Location:** ShipStation order 862852 / `lot_tagging_failures` table

**What was found in production:**
```
order_number | shipstation_order_id | sku
862852       | 283948250            | 17613 [PROMO: field mismatches: ['items_count: 3 != 2']]
resolved_at  | NULL
```
Order 862852 has an active unresolved `lot_tagging_failures` row with a PROMO tag. It almost certainly also carries a `Promo Hold` ShipStation tag. When `handle_promo_sku_order` is retired, no code will ever clear that tag. The order would be frozen in ShipStation indefinitely under a Promo Hold.

**Fix (pre-cutover, operator action):** Before disabling `handle_promo_sku_order`, use the existing "Manual Resolve" dashboard button for order 862852 to clear the Promo Hold tag and mark the `lot_tagging_failures` row as resolved.

---

## 🟡 MEDIUM — Edge Cases That Will Occur in Normal Operations

### Risk 6: `sku_lot` assignment skips lot info for the promo item in `shipped_items`

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

### Risk 7: `verify_tagging_results()` QA produces false warnings after tagger fix

**Location:** `src/scheduled_lot_tagger.py` — `verify_tagging_results()` call post-reconciliation

**What happens:**
The QA function checks all `awaiting_shipment` orders against `active_lots` and `known_skus`. After the tagger fix correctly stamps promo orders with the base SKU lot, the QA function still won't recognize promo SKU orders (they're not in `known_skus`). It may log false "untagged/wrong" warnings for promo orders, making QA output misleading in the logs.

**Fix:** Either exclude promo-mapped orders from the QA check, or add awareness of the `sku_promotions` mapping to `verify_tagging_results()`.

---

## 🔵 LOW — Minor Operational Concerns

### Risk 8: `promo_sku_replacement_log` going silent is misread as a health signal

**Location:** Dashboard Promo SKU Issues panel, any admin monitoring queries

**What happens:**
After retirement, `promo_sku_replacement_log` receives no new rows. The dashboard Promo SKU Issues panel would show zero results — which is correct (no failures) but could be confused with "no promo orders are being processed." Any log monitoring that treats recent activity in this table as a health signal would trigger false alerts.

**Fix:** Remove the Promo SKU Issues dashboard panel entirely rather than leaving it showing zero results. Add a comment to the table (or a note in the admin area) indicating it is a retired audit trail as of this task.

---

## Summary Table

| # | Risk | Severity | In Original Task Plan? | Resolution |
|---|---|---|---|---|
| 1 | Tagger's `known_skus` filter blocks promo SKUs — `customField1` never stamped | 🔴 Critical | ✅ Accounted for in task plan (Step 3) | Remap promo→base SKU + deduplicate by SKU before `tracked_items` is built; multi-SKU guard passes cleanly |
| 2 | `has_key_product_skus()` gate silently discards promo-only orders | 🔴 Critical | ✅ Accounted for in task plan (Step 2) | Remap order items in-place at top of per-order loop — gate sees base SKUs, no changes to the function itself |
| 3 | Three deduction call sites — only one covered (split label + transition path missed) | 🔴 Critical | ✅ Accounted for in task plan (Step 2) | Auto-resolved by Risk 2's single early-loop remap — all three call sites downstream see base SKUs |
| 4 | `upsert_shipped_item()` writes promo SKU into `shipped_items` | 🟠 High | ✅ Accounted for in task plan (Step 2) | Auto-resolved by Risk 2's single early-loop remap |
| 5 | Live Promo Hold on order 862852 must be cleared before cutover | 🟠 High | ✅ Accounted for in task plan (Step 0) | Operator pre-cutover action — Manual Resolve on order 862852 |
| 6 | `sku_lot` missing lot info for promo item in `shipped_items` upsert path | 🟡 Medium | ✅ Accounted for in task plan (Step 2) | Auto-resolved by Risk 2's single early-loop remap |
| 7 | `verify_tagging_results()` QA false warnings after tagger fix | 🟡 Medium | ❌ Not mentioned | Add `sku_promotions` awareness to QA function, or exclude remapped orders |
| 8 | Promo log silence misread as health signal — panel should be removed | 🔵 Low | Partially addressed | Remove dashboard panel; leave table as retired audit trail |

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

# SKU Variant System — Risk Assessment

**Task:** SKU Variant System Implementation  
**Date:** June 30, 2026  
**Scope:** Risks associated with executing the variant SKU implementation across tagger, inventory deduction, sync paths, and reporting

---

## Summary Table

| Risk | Severity | Mitigation |
|---|---|---|
| Migration before code in production | Critical | Strict deployment order |
| Daily processor overwrites correct qty | Critical | Simultaneous release |
| Orphan `shipped_items` rows | Critical | Step 9 must DELETE, not just log |
| `order_items_inbox` duplicate rows | High | Also DELETE orphans in Step 9 |
| Undefined fallback for unknown variant | High | Decide now: fail loudly or silent |
| Promo SKU orders in-flight | High | Confirm zero in-flight before Step 7 |
| Step 8 blast radius | High | Deploy last, isolated release |
| Billing impact of backfill | Medium | Audit must output dollar amount |
| New QA alerts misread as regression | Medium | Communicate to team before deploy |
| List reference sharing in V2 package builder | Low | One-line fix with `copy.copy` |

---

## Risk 1 — Migration must reach production before any code deploys (CRITICAL)

Every code fix in Steps 2–6 queries `sku_variants`. If the code lands in production before the migration runs, the first tagger pass crashes with "relation sku_variants does not exist" — and stays crashed. Every order in `awaiting_shipment` stops getting tagged. Labels stop generating.

The migration is the hard prerequisite for everything else and must be applied to production first, separately, before any code change touches production.

---

## Risk 2 — Daily processor overwrites correctly-written `quantity_shipped` (CRITICAL)

`upsert_shipped_item` uses `ON CONFLICT DO UPDATE` with `quantity_shipped = EXCLUDED.quantity_shipped`. If unified sync correctly writes `quantity_shipped=40` first, then the daily shipment processor runs and calls `upsert_shipped_item(quantity=1)` on the same `(order_number, base_sku, sku_lot)` key — it silently overwrites it back to 1.

The daily processor runs on a schedule independently of unified sync. These two fixes are not independent: they must be deployed together in the same release. Deploying the unified sync fix without the daily processor fix leaves a scheduled job that undoes the correct data on every run.

**Affected file:** `src/daily_shipment_processor.py` — `save_shipped_items_to_db`  
**Conflict key:** `UNIQUE(order_number, base_sku, sku_lot)` — same key, different callers

---

## Risk 3 — Orphan rows in `shipped_items` after base SKU correction (CRITICAL)

The conflict key is `(order_number, base_sku, sku_lot)`. Any variant order imported before the fix has `base_sku='17612-40'` in `shipped_items`. After the fix, new rows land with `base_sku='17612'` — a different conflict key. The old row is never touched. Both rows coexist for the same order.

The cleanup logic inside `upsert_shipped_item` (lines 47–55 of `shipped_items_service.py`) only deletes bare-SKU rows where `base_sku = %s` using the new base SKU (`'17612'`). It cannot reach rows where `base_sku='17612-40'`. Those rows are orphaned permanently and accumulate silently.

The charge report filters on `base_sku IN ('17612', '17904', ...)` — orphan rows don't double-count there. But the order audit endpoint reads `order_items_inbox.sku` and checks `shipped_items` — it would see both the old and new row and report a discrepancy that doesn't exist.

**Step 9 must explicitly DELETE orphan rows, not just log them.**

---

## Risk 4 — `order_items_inbox` duplicate rows (HIGH)

`order_items_inbox` has `UNIQUE(order_inbox_id, sku)`. Before the fix, `sku='17612-40'` is stored. After the fix, the same order re-syncs with `sku='17612'`. These are different conflict keys — no conflict fires — a second row is inserted. The same order now has two rows for the same product.

The order audit endpoint at `app.py` line 8082 reads both rows and applies `normalize_sku` — both normalize to `'17612'` — quantities are summed. The audit would show double the quantity ordered, flagging every previously-imported variant order as over-shipped.

**Step 9 must also DELETE orphan `order_items_inbox` rows with variant SKUs.**

---

## Risk 5 — Undefined fallback when `sku_variants` lookup returns no rows (HIGH)

The full variant SKU list is incomplete (Open Items in the task plan). For variants not yet seeded in `sku_variants`, every code path that does a lookup needs a defined fallback. There are two options with opposite failure modes:

- **Raise an exception:** order import fails visibly. Safe for data integrity, but halts processing of any order with an unknown variant SKU.
- **Silent fallback to `units_per_case=1`:** order processes with wrong quantity and no error. Inventory deducts 1 instead of 40 with no indication anything is wrong.

**This decision must be made explicitly during implementation, not left to however the DB query behaves on an empty result.**

---

## Risk 6 — Step 7 (promo SKU deprecation) timing (HIGH)

Removing the promo map from the tagger while any promo SKU order is still in `awaiting_shipment` status in ShipStation stalls it permanently. The tagger would no longer resolve the promo SKU to its base SKU, so it finds no lot match, writes no CF1, and the upload service blocks the order (no valid SKU-Lot mapping). Those orders don't fail loudly — they just never move.

**Step 7 requires confirming zero promo SKU orders are in-flight before execution, and must not run concurrently with an active tagger pass.**

---

## Risk 7 — Step 8 blast radius (HIGH)

Centralizing `KEY_PRODUCT_SKUS` touches 6 files simultaneously:
- `unified_shipstation_sync.py`
- `lot_deduction.py`
- `daily_shipment_processor.py`
- `shipstation_backfill_sync.py`
- `backfill_inventory_deductions.py`
- `shipstation_backfill_dry_run.py`

A single bug in the centralized config or its import — wrong module path, import-time DB failure, missing env var — causes all 6 workflows to fail at startup simultaneously. This is the entire order processing stack.

**Step 8 should be its own isolated release, deployed last, after all other steps are stable in production.**

---

## Risk 8 — Backfill audit has billing implications, not just data hygiene (MEDIUM)

The charge report bills `$0.75 per unit shipped` and reads from `shipped_items.quantity_shipped`. Every variant order already processed has `quantity_shipped=1` instead of the correct expanded count. If any `17612-40` orders have already shipped, Oracare has been under-billed.

Step 9 as written says "log findings, don't auto-correct — surface for manual review." That is the right call for the database rows, but the output of the audit needs to include a dollar figure, not just a row count.

**Treat this as a billing reconciliation, not just a data audit.**

---

## Risk 9 — New QA alerts after `verify_tagging_results` fix may be misread as a regression (MEDIUM)

Before the fix, `verify_tagging_results` silently excludes variant orders — no failures, no alerts. After the fix, it includes variant orders in QA. If any variant orders were processed incorrectly during the window between a partial tagger fix and full Step 6 deployment, the QA function will start raising failures that were never visible before.

**The team needs to know in advance that new tagging alerts immediately after deployment are the QA system working correctly for the first time on variant orders — not a sign the fix introduced a bug.**

---

## Risk 10 — Python list reference sharing in V2 package builder (LOW, latent)

`tagger.py` line 307:
```python
shipment['packages'] = [single_pkg] * num_packages
```

`[obj] * N` in Python creates N references to the same dict, not N copies. This exists in the current code for regular multi-package orders and hasn't caused problems — meaning nothing downstream currently mutates the package objects. Expanding to `num_packages=40` doesn't introduce a new bug, but it means 40 references to the same dict. If anything ever mutates a package object after this line, all 40 are mutated identically.

**Recommend a one-line fix to `copy.copy(single_pkg)` while this code is being touched anyway.**

---

## Recommended Deployment Order

1. Apply `sku_variants` migration to **production database** — independently, before any code change
2. Deploy Steps 2–6 as a single release (parser fix, normalize_sku, shipment_processor, tagger, all deduction/sync paths, daily processor) — all at once to prevent the overwrite race
3. Monitor for one full tagger cycle; review `verify_tagging_results` output — expect new variant QA entries
4. Run Step 9 backfill audit — produce row counts and dollar impact; coordinate billing reconciliation
5. Confirm zero promo SKU orders in-flight, then execute Step 7
6. Deploy Step 8 as its own isolated release after Steps 2–7 are stable

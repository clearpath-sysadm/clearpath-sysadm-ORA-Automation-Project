# SKU Variant System — Impact Analysis

**Date:** June 29, 2026  
**Subject:** Proposed BigCommerce SKU Variant mapping for bulk discounts

---

## Background

The Oracare team proposed leveraging BigCommerce's "SKU Variant" feature to encode bulk discount tiers directly in the SKU code. Example for OraCare Health Rinse:

| Variant SKU | Description | Units |
|-------------|-------------|-------|
| 17612-40 | Buy 30 Get 10 | 40 |
| 17612-15 | Buy 12 Get 3 | 15 |
| 17612-6 | Buy 5 Get 1 | 6 |
| 17612-1 | Single Case | 1 |

This pattern would be applied across all products with bulk discounts.

---

## The Core Idea in System Terms

The new format (`17612-40`) encodes two pieces of information in the SKU itself: the **base product** and the **number of units** per line item. Currently, the system treats quantity from ShipStation literally — 1 order of `17612` = 1 unit deducted. Under the new scheme, 1 order of `17612-40` = **40 units** deducted. The entire inventory math changes.

---

## 🚨 Biggest Risk: SKU Format Collision

The current SKU parser (`sku_lot_parser.py`) uses this regex to split lot stamps:

```
^(\d+)\s*-\s*(\d+)$   →   "17612 - 250300"
```

A variant SKU like `17612-40` **matches this same pattern** — the parser would mistake `40` for a lot number. This is the most dangerous ambiguity and has to be resolved first before anything else.

**Resolution strategy:** A variant SKU lookup table (in the database) would be the authoritative way to distinguish them. Before parsing as a lot stamp, the system checks: *is this SKU a known variant?*

---

## Database Changes

| Change | Details |
|--------|---------|
| **New table: `sku_variants`** | Maps `17612-40` → base SKU `17612`, `units_per_case = 40`, display name, active flag |
| **`skus` table** | Likely stays as-is (only base SKUs live here); variants reference base SKUs |
| **`sku_promotions` table** | May be partially or fully superseded — the variant system is doing what promo SKU remapping currently does, more cleanly |
| **`shipped_items` table** | The `base_sku` and `sku_lot` columns are fine; the quantity recorded there needs to reflect **expanded units**, not the raw ShipStation line quantity |

---

## Code Changes

### `src/services/data_processing/sku_lot_parser.py`
Needs a pre-check against the `sku_variants` table before attempting lot-stamp parsing. If a SKU is a known variant, return `(base_sku, None)` — no lot portion, just a base SKU expansion.

### `src/lot_tagger/tagger.py`
When tagging lots, a variant SKU like `17612-40` must be resolved to base SKU `17612` before the FIFO lot lookup. The lot stamp written back to ShipStation's `customField1` would still reference the base SKU and lot number — this part probably stays the same.

### `src/services/inventory/lot_deduction.py` *(highest impact)*
The deduction multiplier is the critical change. Currently: `deduct quantity × 1`. New logic: `deduct quantity × units_per_case`. An order of `17612-40` with qty 1 must create a Ship transaction for **40 units**, not 1. Getting this wrong silently corrupts inventory.

### `src/services/inventory/promo_sku_utils.py`
The promo SKU remapping layer either gets extended to handle variants, or more likely, variants become a cleaner replacement for the promo SKU concept entirely. This would need a deliberate decision — run both in parallel during a transition, then deprecate promo SKUs.

### `KEY_PRODUCT_SKUS` list
Currently hardcoded as `['17612', '17904', '17914', '18675', '18795']`. Any logic that gates on this list (inventory deduction, lot validation) needs to also recognize variant SKUs whose base maps to one of these — either by expanding the list dynamically from the `sku_variants` table, or by resolving to base before the check.

### Charge Report
Currently aggregates shipped units by SKU. With variants, a `17612-40` line item qty 1 must count as 40 units in the charge report, not 1. Without this fix, charge reports would dramatically undercount.

### ShipStation Reconciliation / Inventory Comparison Tools
Any place that compares ShipStation order quantities to inventory counts needs the same expansion logic applied.

---

## Migration Sequence

1. **Build `sku_variants` table** and seed it with all known variants (starting with the 4 OraCare Health Rinse variants, then expand to other products)
2. **Update the SKU parser** with variant pre-check (prevents the lot-stamp collision)
3. **Update lot tagger** to expand variants before lot lookup
4. **Update inventory deduction** with the `units_per_case` multiplier
5. **Update reporting** (charge report, shipped units summaries)
6. **Decide on promo SKU fate** — parallel-run or deprecate
7. **Backfill check** — any historical variant orders would have been deducted at qty 1 instead of the correct unit count; a backfill script may be needed

---

## What This Doesn't Touch

- The lot system itself (FIFO, lot stamps, `lot_balances` view) — structurally unchanged
- Auth, user roles, the dashboard display layer (mostly)
- ShipStation API communication — the system reads what ShipStation sends; no changes to how orders are fetched

---

## Summary

The database change is small (one new table). The code surface is moderate but concentrated in the inventory pipeline. The biggest risk is the SKU parser collision and the silent multiplication error in inventory deduction if the multiplier isn't applied consistently everywhere units are counted.

# SKU Variant System — Impact Analysis

**Date:** June 29, 2026  
**Subject:** Proposed BigCommerce SKU Variant mapping for bulk discounts  
**Status:** Revised after code review of `tagger.py`, `lot_deduction.py`, `sku_lot_parser.py`, and `promo_sku_utils.py`

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

## 🚨 Risk 1 (Highest): SKU Format Collision

The SKU parser (`sku_lot_parser.py`) handles **both spaced and unspaced** dash formats:

```
"17612 - 260017"  →  base_sku=17612, lot=260017   ✅ correct
"17612-260017"    →  base_sku=17612, lot=260017   ✅ correct
"17612-40"        →  base_sku=17612, lot=40        ❌ WRONG — lot 40 does not exist
```

A variant SKU like `17612-40` silently misparsed as a lot stamp today with no error — it just fails to find lot `40` downstream. This must be resolved before any variant SKUs go live.

**Resolution:** A `sku_variants` database table acts as the authoritative lookup. Before the parser applies its regex, it checks: *is this a known variant SKU?* If yes, return `(base_sku, units_per_case)` and skip lot parsing entirely.

---

## 🚨 Risk 2 (High): Shipping Profiles Are Hardcoded by SKU

The lot tagger (`tagger.py`) resolves box dimensions and weight from a hardcoded `SKU_SHIPPING_PROFILES` map keyed by **base SKU**. A `17612-40` bundle (40 units) ships in a completely different box than `17612-1` (1 unit). If the tagger only resolves to the base SKU profile, every variant bundle would be assigned the wrong package dimensions — causing FedEx rate errors or mislabeled shipments.

**Resolution:** The `sku_variants` table must include shipping profile data per variant (weight, dimensions, package preset). The tagger's profile resolution must check the variant lookup first, before falling back to base SKU defaults.

---

## 🚨 Risk 3 (High): Multi-SKU Guard in the Tagger

The tagger has an explicit guard: if an order contains **more than one tracked SKU**, it logs the order to `lot_tagging_failures` and skips it entirely. Under the variant system, an order containing `17612-40` and `17904-6` would — after variant resolution — be two different base SKUs. This triggers the multi-SKU guard and the order is skipped with no lot stamp.

**Resolution:** A deliberate decision is needed: either extend the tagger to support multi-product variant orders, or document that mixed-product variant orders are unsupported and must be placed as separate orders.

---

## Database Changes

| Change | Details |
|--------|---------|
| **New table: `sku_variants`** | Maps `17612-40` → base SKU `17612`, `units_per_case = 40`, display name, shipping profile (weight/dimensions/package preset), active flag |
| **`skus` table** | Stays as-is — only base SKUs live here; variants reference base SKUs |
| **`sku_promotions` table** | Likely superseded — variants do what promo SKU remapping does, more cleanly. Parallel-run during transition, then deprecate. |
| **`shipped_items` table** | `base_sku` and `sku_lot` columns are fine; quantities recorded must reflect **expanded units** (not raw ShipStation line qty) |

---

## Code Changes

### `src/services/data_processing/sku_lot_parser.py`
Add a variant pre-check against the `sku_variants` table before the regex runs. If the SKU is a known variant, return `(base_sku, None)` — skip lot parsing. This is the fix for Risk 1.

### `src/lot_tagger/tagger.py`
Two changes required:
1. **Variant resolution:** Resolve `17612-40` → `17612` before the FIFO lot lookup. The lot stamp written to ShipStation's `customField1` uses the base SKU (`17612 - {lot_number}`) — this part is unchanged.
2. **Shipping profile lookup:** Check `sku_variants` for per-variant box dimensions/weight before falling back to the base SKU profile. This is the fix for Risk 2.

### `src/services/inventory/lot_deduction.py` *(highest inventory impact)*
The unit expansion multiplier must be applied at the **aggregation step** — before quantities are summed by `(base_sku, lot)`. Currently: `deduct quantity × 1`. New logic: `deduct quantity × units_per_case`. An order of `17612-40` qty 1 must produce a Ship transaction for **40 units**, not 1. Applying this after aggregation would collapse the multiplication incorrectly.

The existing idempotency guard (checks for duplicate `Ship` transactions by `lot_id + shipstation_order_id`) continues to work correctly as long as variant resolution happens before lot assignment.

### `src/services/inventory/promo_sku_utils.py`
Variants serve the same purpose as promo SKU remapping. Decision needed: extend this utility to handle variants in parallel, or route variants through the new `sku_variants` table exclusively and begin deprecating promo SKU logic.

### `KEY_PRODUCT_SKUS` list
Currently hardcoded as `['17612', '17904', '17914', '18675', '18795']`. All logic gated on this list must resolve variant SKUs to their base before the check, or dynamically expand the list from `sku_variants` at startup.

### Charge Report
Currently sums raw `Ship` transaction quantities. With variants, a `17612-40` line item qty 1 must count as 40 units. The expansion happens upstream (in deduction), so the charge report itself is correct as long as the deduction multiplier is applied properly.

### ShipStation Reconciliation / Inventory Comparison Tools
Any tool that compares ShipStation order quantities directly to inventory counts (without going through the deduction pipeline) needs the same expansion logic applied at read time.

---

## Revised Migration Sequence

| Step | Change | Risk if Skipped |
|------|--------|-----------------|
| 1 | Build `sku_variants` table with shipping profiles; seed all known variants | Nothing else can proceed safely |
| 2 | Update SKU parser with variant pre-check | Variants silently misparse as lot numbers |
| 3 | Update lot tagger: variant → base resolution + per-variant shipping profile | Lot assignment fails; wrong box dimensions sent to FedEx |
| 4 | Decide multi-SKU guard behavior for multi-product variant orders | Mixed-product orders silently skipped |
| 5 | Apply `units_per_case` multiplier at aggregation step in deduction pipeline | Inventory silently undercounts by large margins |
| 6 | Update ShipStation reconciliation and comparison tools | Reconciliation reports show false discrepancies |
| 7 | Decide on promo SKU deprecation — parallel-run or remove | Redundant remapping logic |
| 8 | Backfill audit — identify any historical variant orders deducted at qty 1 | Past inventory records may be inaccurate |

---

## What This Doesn't Touch

- The FIFO lot assignment logic and `lot_balances` view — structurally unchanged
- The lot stamp format written to ShipStation (`{base_sku} - {lot_number}`) — unchanged
- Auth, user roles, dashboard display layer
- ShipStation API communication — the system reads what ShipStation sends; no fetch-layer changes needed

---

## Summary

The database change is small (one new table, but it must include shipping profiles per variant — not just unit counts). The code surface is moderate and concentrated in the inventory pipeline and lot tagger. Three risks were identified beyond the original analysis: the **shipping profile mismatch** (variants represent physically different package sizes), the **multi-SKU tagger guard** (mixed-product variant orders will be silently skipped), and the **aggregation step timing** for the unit multiplier. All three must be explicitly addressed in any implementation plan.

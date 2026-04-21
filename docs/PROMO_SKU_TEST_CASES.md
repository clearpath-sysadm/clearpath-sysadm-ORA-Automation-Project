# Promo SKU & BigCommerce Integration — Test Cases

Use these cases to verify that promo SKU replacement fixes are holding across the full fulfillment pipeline.

---

## Core Replacement Flow

**TC-01 — Single-item promo order**
- Order contains only a promo SKU (e.g., 17613).
- Expected: Original order is cancelled in ShipStation, a replacement order is created with the base SKU (17612), and the replacement carries the same shipping address and BC order number.

**TC-02 — Mixed-item promo order**
- Order contains a promo SKU plus one or more regular items.
- Expected: Only the promo SKU is swapped. Every other line item on the replacement is identical to the original.

**TC-03 — Multiple promo SKUs on one order**
- Order contains two or more promo items.
- Expected: All promo SKUs are replaced correctly. No line items are dropped or duplicated.

---

## Lot Tagging After Replacement

**TC-04 — Lot is stamped on the replacement, not the original**
- After replacement, check Custom Field 1 on the new order.
- Expected: Shows `17612 - 260017` (base SKU + correct active lot), not the promo SKU.

**TC-05 — FIFO lot selection on the replacement**
- Expected: The replacement order pulls from the oldest active lot with stock remaining, same as any regular order.

---

## Verification & Failure Handling

**TC-06 — Weight/dimension mismatch (previously broken)**
- Trigger a replacement where the promo SKU has different catalog weights than the base SKU in ShipStation.
- Expected: Verification does NOT fail. The replacement goes through cleanly without being blocked by catalog-derived field differences.

**TC-07 — Orphan order cleanup on verification failure**
- Simulate or locate a recent verification failure in logs.
- Expected: The orphan replacement order is automatically cancelled. The red admin alert bar appears on the dashboard if cleanup also fails.

**TC-08 — Duplicate webhook fire (idempotency)**
- Have the same promo order webhook fire twice in quick succession.
- Expected: Only one replacement order is created. The second webhook is ignored without creating a duplicate.

---

## Inventory Impact

**TC-09 — shipped_items records base SKU, not promo SKU**
- After a replaced order ships, query `shipped_items`.
- Expected: `base_sku = 17612` (not 17613), with the correct lot number.

**TC-10 — No double-deduction**
- After the replacement ships, check `inventory_transactions` for the base SKU.
- Expected: Exactly one `Ship` deduction for the ordered quantity — not one for the promo SKU and one for the base SKU.

**TC-11 — Inventory count decreases by exact ordered quantity**
- Before and after a promo order ships, compare the formula-based inventory count for the base SKU.
- Expected: Count decreases by exactly the quantity ordered (e.g., 1 unit), nothing more.

---

## BigCommerce-Specific

**TC-12 — BC order number preserved on replacement**
- After replacement, check the ShipStation replacement order.
- Expected: The original `BC-800xxx` order number is present so tracking can sync back to the customer.

**TC-13 — Tracking number syncs back to BigCommerce**
- After the replacement order ships, check the original BigCommerce order.
- Expected: Tracking number is visible on the BC order. The cancellation of the original ShipStation order does not break the tracking sync.

---

## Suggested Test Order

Run in this sequence for maximum coverage with minimum effort:

1. TC-01 (basic end-to-end)
2. TC-04 (lot stamped correctly)
3. TC-09 (inventory records correct)
4. TC-13 (BC tracking sync)
5. TC-02 (mixed-item edge case)
6. TC-06 (weight mismatch — previously broken)
7. Remaining cases as time permits

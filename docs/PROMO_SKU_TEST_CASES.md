# Promo SKU & BigCommerce Integration — Test Cases

Use these cases to verify that promo SKU replacement fixes are holding across the full fulfillment pipeline.

**How promo SKUs work:** A promo SKU is always one higher than the base SKU (e.g., 17613 is the promo for 17612). 97% of the time a promo SKU appears on an order paired with at least one paid product (Buy X Get Y Free). There is an edge case where the promo SKU arrives alone with no paid item. OraPro Paste Peppermint (18795) has no promo SKU and will not be used as a free item.

---

## Core Replacement Flow

**TC-01 — Standard Buy X Get Y order (most common case)**
- Order contains a paid base SKU plus its promo SKU as the free item.
- Expected: Promo SKU is replaced with the base SKU, paid item is untouched, replacement carries the same shipping address and BC order number.

**TC-02 — Promo SKU with no paid product (edge case)**
- Order contains only a promo SKU, no paid item in the cart.
- Expected: System still replaces the promo SKU correctly. Does not error out or get stuck because there is no paid companion product.

**TC-03 — Multiple promo SKUs on one order**
- Order contains two or more promo items (e.g., 17613 and 17905 together).
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

## BigCommerce Orders to Place

Use a real test shipping address each time. All promo SKUs follow the same pattern — the promo SKU is always the base SKU + 1. OraPro Paste (18795) has no promo SKU and is not included.

**Promo SKU reference:**
| Promo SKU (enter this) | Paired Base SKU | Product |
|------------------------|-----------------|---------|
| 17613 | 17612 | PT Kit |
| 17905 | 17904 | Travel Kit |
| 17915 | 17914 | PPR Kit |
| 18676 | 18675 | Ortho Protect |

---

### Standard Buy X Get Y orders (run one per promo SKU)

Each of these tests the normal case — a customer buys a product and gets the same product free.

| Order | Cart Contents |
|-------|--------------|
| Order A | 1x **17612** (paid) + 1x **17613** (free promo) |
| Order B | 1x **17904** (paid) + 1x **17905** (free promo) |
| Order C | 1x **17914** (paid) + 1x **17915** (free promo) |
| Order D | 1x **18675** (paid) + 1x **18676** (free promo) |

These cover TC-01, TC-04, TC-05, TC-06, TC-08, TC-09, TC-10, TC-11, TC-12, and TC-13.

---

### Edge case — Promo SKU with no paid product (run once)

| Order | Cart Contents |
|-------|--------------|
| Order E | 1x **17613** only — no paid item |

This covers TC-02. Confirms the system handles a standalone promo SKU without erroring out.

---

### Multi-promo order (run once)

| Order | Cart Contents |
|-------|--------------|
| Order F | 1x **17613** + 1x **17905** (two different promo SKUs, no paid items) |

This covers TC-03. Confirms both are replaced and nothing is dropped.

---

**TC-07** — No order needed. Check recent entries in `promo_sku_replacement_log` where status is not `replaced`, or look for the red admin alert bar on the dashboard.

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

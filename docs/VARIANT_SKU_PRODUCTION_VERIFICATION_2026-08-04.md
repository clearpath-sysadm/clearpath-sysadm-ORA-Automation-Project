# Variant SKU Production Verification — August 4, 2026

**Prepared:** August 4, 2026  
**Purpose:** Confirm variant SKU end-to-end processing is working correctly in production following Mikkah's test order rounds (08/03 and 08/04).

---

## Summary

All layers of the variant SKU system are functioning correctly in production. Orders display a single quantity (as placed), and ShipStation receives the correct number of physical packages with accurate weights and dimensions derived from the pack-size multiplier.

---

## 1. Variant Remapping

The remap maps loaded at system startup with all **16 variant SKUs** and **4 promo SKUs** active. Every variant SKU in the test batch was resolved correctly, including multi-quantity lines (qty > 1) and orders with multiple variant lines from the same base SKU.

| Order | Raw SKU(s) | Resolved |
|-------|-----------|---------|
| 864767 | `17612-6 (qty=1)` | 17612 ×6 packages |
| 864768 | `17612-15 (qty=1)` | 17612 ×15 packages |
| 864769 | `17612-40 (qty=1)` | 17612 ×40 packages |
| 864770 | `17904-6 (qty=1)` | 17904 ×6 packages |
| 864771 | `17612-6 (qty=2)` | 17612 ×**12** packages *(2 × 6 — multi-qty correct)* |
| 864772 | `17612-6 (qty=1)` + `17612-15 (qty=1)` | ×6 + ×15 *(two variant lines on same order)* |
| 864773 | `17612-40 (qty=1)` + `17612-6 (qty=1)` | ×40 + ×6 |
| 864774 | `17612-15 (qty=1)` + `17612-6 (qty=2)` | ×15 + ×12 |
| 864776 | `17612-15 (qty=1)` + `17904-1 (qty=1)` | ×15 + ×1 |
| 864779 | `17612-6 (qty=1)` | 17612 ×6 packages |
| 864780 | `17905 → 17904` (promo) + `17904-6 (qty=1)` | 17904 ×6 packages |
| 864781 | `17905 → 17904` (promo) + `17612-6 (qty=1)` | 17612 ×6 packages |
| 864799 | variant | ×15 packages |
| 864800 | `18675-40 (qty=1)` | 18675 ×40 packages |
| 864808 | `17613 → 17612` (promo) + `17612-6` | 17612 ×6 packages |
| 864809 | variant | ×2 packages |
| 864811 | auto-split → two SS orders | ×1 (17904) + ×1 (17612) *(see note)* |
| 864812 | `17613 → 17612` (promo) | 17612 ×5 packages |

---

## 2. V2 Package Counts and Weights

ShipStation received the correct package type, count, and weight for every order. The `fields=['weight']` correction logged on each order is expected — the tagger recomputes weight from the package count on every reconciliation pass to keep it current.

| Order | SS Order ID | Package Code | Count |
|-------|-------------|-------------|-------|
| 864799 | — | se-122678 | ×15 |
| 864800 | 309269458 | se-122678 | ×40 |
| 864808 | 309289405 | se-122675 | ×6 |
| 864809 | 309289420 | se-122677 | ×2 |
| 864811 | 309289411 | se-132840 | ×1 (17904 split) |
| 864811 | 309289412 | se-122675 | ×1 (17612 split) |
| 864812 | 309289424 | se-122675 | ×5 |

**Note on order 864811:** This order appears under two separate ShipStation order IDs. That is auto-split working correctly — BigCommerce placed a single order with two different product series, ShipStation split it into two individual orders before our sync picked them up, and the lot tagger tagged and packaged each split order independently.

---

## 3. Lot Tagger QA — All Passes, All Day

Every reconciliation cycle throughout the day passed with zero errors.

| Time (CDT) | QA Result | Orders scanned |
|-----------|-----------|---------------|
| 08:00 | ✅ 43/43 correct | 49 scanned |
| 08:09 | ✅ 44/44 correct | 50 scanned |
| 08:15 | ✅ 44/44 correct | 50 scanned |
| 08:36 | ✅ 44/44 correct | 46 scanned |
| 09:25 | ✅ 36/36 correct | 36 scanned |
| 09:34 | ✅ 37/37 correct | 37 scanned |
| 09:40 | ✅ 39/39 correct | 40 scanned |
| 09:47 | ✅ 36/36 correct | 40 scanned |
| 09:51 | ✅ 36/36 correct | 40 scanned |
| **10:32** | ✅ **44/44 correct** | **48 scanned** |

0 untagged or incorrectly stamped orders at any point during the day.

---

## 4. Lot Tagging Failures

No new lot tagging failures on 08/04. The only open records are for orders 864775 and 864776 from the 08/03 test batch — both of those orders are cancelled and the failures are operationally harmless (they were triggered by placing two different product series in a single order before auto-split was active, which the tagger correctly refused to process).

---

## 5. How the Single-Quantity Display Works

The behavior Mikkah observed — a single quantity on the order but multiple packages in ShipStation — is the intended design:

- **BigCommerce / order display:** Shows `qty=1` of `17612-6` (one unit of the pack-of-6 product), which is what the customer ordered.
- **`order_items_inbox`:** Stores the resolved base SKU (`17612`) and the effective unit count (`6`), used for inventory deduction and lot tracking.
- **ShipStation V2 packages:** The lot tagger converts the effective unit count into a physical package count (`×6`) with the correct per-package weight and dimensions for that SKU's pack size.

All three layers are consistent and correct.

---

## 6. Active Variant SKU Configuration

| Series | -1 | -6 | -15 | -40 |
|--------|----|----|-----|-----|
| 17612 | ✅ | ✅ | ✅ | ✅ |
| 17904 | ✅ | ✅ | ✅ | ✅ |
| 17914 | ✅ | ✅ | ✅ | ✅ |
| 18675 | ✅ | ✅ | ✅ | ✅ |

All 16 variant SKU rows are active in `sku_variants`. All four pack sizes across all four product series are live.

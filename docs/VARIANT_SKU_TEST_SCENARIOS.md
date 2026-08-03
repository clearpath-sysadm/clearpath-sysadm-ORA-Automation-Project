# Variant SKU Test Scenarios

All scenarios below are designed to test how the system handles orders containing variant SKUs — either alone or in combination with other line item types. Use real test orders in ShipStation.

---

## Single Line Item

| # | Line Item | Qty | What It Tests |
|---|-----------|-----|---------------|
| 1.1 | `17612-6` | 1 | Single variant SKU resolves to base `17612`, deducts 6 units |
| 1.2 | `17612-15` | 1 | Larger multiplier — deducts 15 units |
| 1.3 | `17612-40` | 1 | Largest pack — deducts 40 units |
| 1.4 | `17904-6` | 1 | Same logic, different SKU family |
| 1.5 | `17612-6` | 2 | Qty > 1 on the variant line — should deduct 6 × 2 = 12 units |

---

## Two Line Items — Same Base SKU, Different Variant

| # | Line Item 1 | Line Item 2 | What It Tests |
|---|-------------|-------------|---------------|
| 2.1 | `17612-6` (qty 1) | `17612-15` (qty 1) | Two variant SKUs resolving to same base — quantities must combine (6 + 15 = 21 units deducted) |
| 2.2 | `17612-6` (qty 1) | `17612-40` (qty 1) | Higher-multiplier combination (6 + 40 = 46 units) |
| 2.3 | `17612-6` (qty 2) | `17612-15` (qty 1) | Mixed qty on both lines — deducts (6×2) + 15 = 27 units |

---

## Two Line Items — Different Base SKUs

| # | Line Item 1 | Line Item 2 | What It Tests |
|---|-------------|-------------|---------------|
| 3.1 | `17612-6` (qty 1) | `17904-6` (qty 1) | Variant SKUs from two different families — system should flag as multi-SKU failure (expected behavior) |
| 3.2 | `17612-15` (qty 1) | `17904-1` (qty 1) | Different multipliers, different bases — same multi-SKU flag expected |

---

## Variant SKU + Base SKU (Same Family)

| # | Line Item 1 | Line Item 2 | What It Tests |
|---|-------------|-------------|---------------|
| 4.1 | `17612-6` (qty 1) | `17612` (qty 1) | Variant and its own base SKU together — quantities must combine before a single deduction (6 + 1 = 7 units) |
| 4.2 | `17612-15` (qty 1) | `17612` (qty 3) | Larger multiplier + multi-unit base line (15 + 3 = 18 units) |

---

## Variant SKU + Promo SKU (Same Base)

| # | Line Item 1 | Line Item 2 | What It Tests |
|---|-------------|-------------|---------------|
| 5.1 | `17612-6` (qty 1) | `17613` (qty 1) | Variant + promo SKU that both resolve to `17612` — promo remaps first, then quantities combine (6 + 1 = 7 units) |
| 5.2 | `17904-6` (qty 1) | `17905` (qty 1) | Same pattern, `17904` family — (6 + 1 = 7 units deducted from `17904`) |

---

## Variant SKU + Promo SKU (Different Bases)

| # | Line Item 1 | Line Item 2 | What It Tests |
|---|-------------|-------------|---------------|
| 6.1 | `17612-6` (qty 1) | `17905` (qty 1) | Variant for `17612` + promo for `17904` — two different resolved bases; system should flag as multi-SKU failure |

---

**What to verify for each scenario:**
- **Lot tag** written correctly to ShipStation CF1 (format: `SKU - LOT`)
- **Inventory deduction** matches the expected unit count (multiplier × qty, summed across lines)
- **Multi-SKU failures** (scenarios 3.x and 6.x) appear in the Lot Tagging Failures log — these are expected and correct
- **No double-deductions** if the same order is re-sent after already being processed

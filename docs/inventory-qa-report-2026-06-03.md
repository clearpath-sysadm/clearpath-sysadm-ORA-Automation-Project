# Inventory Tracking QA Report
**Date:** 2026-06-03  
**Scope:** All key product SKUs — 17612, 17904, 17914, 18675, 18795

---

## Queries Run

### Query 1 — Missing Deductions
Shipped orders with no `Ship` transaction in `inventory_transactions`.

### Query 2 — Double Deductions
Orders where the same SS order was deducted more than once.

### Query 3 — Quantity Mismatch
Orders where deduction amount doesn't match `shipped_items` quantity.

### Query 4 — Lot Balance Health
Negative balances and lot status mismatches.

### Query 5 — Current Inventory Summary
Per-SKU balances across all lots.

### Query 6 — NULL-lot Ship Transactions
Deductions that couldn't find a lot (ghost deductions).

### Query 7 — Orphan Transactions
Ship transactions with no corresponding `shipped_orders` record.

---

## Raw Results

### Query 2 — Double Deductions
```json
[
  {
    "shipstation_order_id": "278198682",
    "sku": "18675",
    "deduction_count": "2",
    "total_deducted": "4"
  }
]
```

### Query 4a — Negative Balance Lots
```json
[
  {
    "sku_code": "17612",
    "lot_number": "260047",
    "status": "inactive",
    "balance": "-22",
    "received_date": "2026-04-02"
  }
]
```

### Query 5 — Current Inventory Summary (simplified / correct version)
```json
[
  {
    "sku_code": "17612",
    "active_balance": "554",
    "depleted_balance": "0",
    "total_balance": "1684",
    "active_lot_count": "1"
  },
  {
    "sku_code": "17904",
    "active_balance": "82",
    "depleted_balance": "0",
    "total_balance": "82",
    "active_lot_count": "1"
  },
  {
    "sku_code": "17914",
    "active_balance": "544",
    "depleted_balance": "0",
    "total_balance": "544",
    "active_lot_count": "1"
  },
  {
    "sku_code": "18675",
    "active_balance": "225",
    "depleted_balance": "0",
    "total_balance": "516",
    "active_lot_count": "1"
  },
  {
    "sku_code": "18795",
    "active_balance": "99",
    "depleted_balance": "0",
    "total_balance": "6769",
    "active_lot_count": "1"
  }
]
```

### Query 1 — Missing Deductions (excerpt — full file contains ~25,000 lines)
Large result set. Representative sample from attached file:
- Orders in the 6xx, 7xx, 1xxx, and 863xxx series with 0 deductions recorded.
- Largest single-order gaps: multiple 17612 orders with 42 units shipped, 0 deducted.

### Query 3 — Quantity Mismatch (excerpt — full file contains ~42,000 lines)
Sample of largest discrepancies from attached file:

| order_number | base_sku | shipped_items_qty | deducted_qty | discrepancy |
|---|---|---|---|---|
| 862254 | 18675 | 53 | 106 | -53 |
| 699145 | 17612 | 42 | 0 | +42 |
| 700805 | 17612 | 42 | 0 | +42 |
| 700315 | 17612 | 42 | 0 | +42 |
| 700855 | 17612 | 42 | 0 | +42 |
| 700765 | 17612 | 42 | 0 | +42 |
| 700905 | 17612 | 42 | 0 | +42 |
| 700935 | 17612 | 42 | 0 | +42 |
| 700305 | 17612 | 42 | 0 | +42 |
| 694495 | 17612 | 41 | 0 | +41 |
| 862897 | 17612 | 41 | 1 | +40 |
| 862561 | 17612 | 1 | 24 | -23 |
| 862454 | 17612 | 10 | 30 | -20 |
| 100684 | 18675 | 20 | 0 | +20 |
| 10200  | 17612 | 18 | 0 | +18 |

### Query 7 — Orphan Transactions (today's orders, expected)
All orphan transactions are dated 2026-06-03 (today), order numbers 863xxx.
These are today's freshly-deducted orders that have not yet synced back into
`shipped_orders`. Expected behavior — recheck tomorrow; should be zero.

### Queries with No Results
- Query 1 (missing deductions) — see large attached file above
- Query 4b (active lots with balance ≤ 0) — none
- Query 4c (depleted lots with positive balance) — none
- Query 6 (NULL-lot ship transactions) — none

---

## Diagnosis

### 🔴 Issue 1 — Massive Historic Under-Deduction (17612, likely others)

Thousands of old orders (series 6xx, 7xx, 1xxx) have `shipped_items` records but
zero corresponding `Ship` entries in `inventory_transactions`. The lot-deduction
system was not running or not wired up for those older orders.

**Effect:** Inventory is significantly overstated for 17612. Every un-deducted order
is phantom inventory that was actually shipped.

**Tool available:** `src/backfill_inventory_deductions.py` — hits the ShipStation API
per order to retrieve the lot stamp (`customField1`), then calls `deduct_lot_inventory`.
Must determine scale before running (see remediation queries below).

---

### 🔴 Issue 2 — Double Deductions on Specific Orders

Confirmed cases where a single shipment was deducted from inventory more than once:

| Order | SKU | Shipped | Deducted | Over-count |
|---|---|---|---|---|
| SS 278198682 | 18675 | 2 | 4 | +2 |
| 862254 | 18675 | 53 | 106 | +53 |
| 862561 | 17612 | 1 | 24 | +23 |
| 862454 | 17612 | 10 | 30 | +20 |

**Effect:** These orders under-state inventory (debited more than was shipped). Smaller
magnitude than Issue 1 but directly corrupts lot balances.

---

### 🟡 Issue 3 — 18795 Active vs. Total Discrepancy (6,670 units in inactive/depleted lots)

Active balance: 99. Total balance across all lots: 6,769. The 6,670 unit gap is held in
lots that are no longer active. Likely cause: a large old receive was posted to a lot
that was subsequently closed out without ever being fully shipped, or lot status was
updated manually without corresponding inventory adjustments.

**Query to investigate:**
```sql
SELECT lot_number, status, balance, received_date
FROM lot_balances
WHERE sku_code = '18795'
ORDER BY balance DESC;
```

---

### 🟡 Issue 4 — Lot 260047 (17612, inactive, balance -22)

An inactive 17612 lot received 2026-04-02 was over-deducted by 22 units. Likely deducted
against while active, then inactivated without correcting the balance. Small magnitude.

---

### 🟡 Issue 5 — 17612 Total Balance vs. Active Balance (1,130 unit gap)

Active balance: 554. Total balance: 1,684. 1,130 units live in depleted/inactive lots.
Combined with the known under-deduction problem, the true active inventory figure is
unreliable until the backfill is complete.

---

## Recommended Remediation Queries

Run these before taking any corrective action to understand the full scale:

### Scale of missing deductions per SKU
```sql
SELECT
    base_sku,
    COUNT(*)                                                         AS orders_affected,
    SUM(shipped_items_qty - COALESCE(deducted_qty::int, 0))         AS units_missing_deduction
FROM (
    SELECT
        si.order_number,
        si.base_sku,
        so.shipstation_order_id,
        si.quantity_shipped                    AS shipped_items_qty,
        COALESCE(SUM(it.quantity), 0)          AS deducted_qty
    FROM shipped_items si
    JOIN shipped_orders so ON so.order_number = si.order_number
    LEFT JOIN inventory_transactions it
        ON  it.shipstation_order_id = so.shipstation_order_id
        AND it.transaction_type     = 'Ship'
        AND it.sku                  = si.base_sku
    WHERE si.base_sku = ANY(ARRAY['17612','17904','17914','18675','18795'])
      AND so.shipstation_order_id IS NOT NULL
    GROUP BY si.order_number, si.base_sku, so.shipstation_order_id, si.quantity_shipped
) sub
WHERE shipped_items_qty > deducted_qty
GROUP BY base_sku
ORDER BY units_missing_deduction DESC;
```

### Scale of over-deductions per SKU
```sql
SELECT
    base_sku,
    COUNT(*)                                                          AS orders_affected,
    SUM(ABS(shipped_items_qty - COALESCE(deducted_qty::int, 0)))     AS units_over_deducted
FROM (
    SELECT
        si.base_sku,
        si.quantity_shipped                    AS shipped_items_qty,
        COALESCE(SUM(it.quantity), 0)          AS deducted_qty
    FROM shipped_items si
    JOIN shipped_orders so ON so.order_number = si.order_number
    LEFT JOIN inventory_transactions it
        ON  it.shipstation_order_id = so.shipstation_order_id
        AND it.transaction_type     = 'Ship'
        AND it.sku                  = si.base_sku
    WHERE si.base_sku = ANY(ARRAY['17612','17904','17914','18675','18795'])
      AND so.shipstation_order_id IS NOT NULL
    GROUP BY si.order_number, si.base_sku, so.shipstation_order_id, si.quantity_shipped
) sub
WHERE deducted_qty > shipped_items_qty
GROUP BY base_sku
ORDER BY units_over_deducted DESC;
```

### 18795 lot breakdown
```sql
SELECT lot_number, status, balance, received_date
FROM lot_balances
WHERE sku_code = '18795'
ORDER BY balance DESC;
```

---

## Next Steps (in order)

1. **Run the scale queries above** — get the unit counts before touching anything.
2. **Fix over-deductions first** — delete or offset the duplicate `inventory_transactions`
   rows for the confirmed double-deduction orders (smaller set, surgical fix).
3. **Run backfill** — `python3 src/backfill_inventory_deductions.py --dry-run` first,
   then without `--dry-run`. Note: this requires ShipStation API access and hits the
   API once per order — factor in rate limits for large volumes.
4. **Investigate 18795 lot balances** — determine whether the 6,670-unit gap represents
   real physical inventory or data error before trusting that number.
5. **Re-run all QA queries** after backfill to confirm clean state.

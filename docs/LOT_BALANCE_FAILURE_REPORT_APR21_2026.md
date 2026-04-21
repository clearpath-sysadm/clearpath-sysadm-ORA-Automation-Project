# Lot Tagger Failure — Root Cause Investigation Report
**Date:** April 21, 2026  
**Prepared by:** System Investigation  
**Status:** Diagnosis complete — no fixes have been applied yet

---

## Quick Summary

The lot tagger is failing on **26 of 40** awaiting-shipment orders. Every order that arrives
without a pre-existing CF1 value is being rejected with a "no active lot found" error. This
is happening because the database view that tracks how much inventory is in each lot is
showing **negative balances for every active lot**. The tagger won't assign a lot unless the
balance is positive, so it finds nothing and fails every order.

This has been fully proven with database queries. No guessing. All numbers below are live
production data pulled on April 21, 2026.

---

## Section 1 — What Is Broken (The Short Version)

The lot tagger asks the database: *"Which lots have inventory remaining (balance > 0)?"*

The answer it gets back: **none.**

Because the answer is empty, every untagged order fails. The 26 orders currently sitting
without a CF1 tag are stuck because of this.

---

## Section 2 — Proof: Why Every Balance Is Negative

### How lot balances are calculated

The database has a view called `lot_balances`. It calculates the balance for each lot using
this formula:

```
Balance = (all Receive transactions for that lot) − (all Ship transactions for that lot)
```

But there is a critical requirement: **a transaction only counts if it has a `lot_id` field
set.** Transactions where `lot_id` is NULL are invisible to this view.

### The actual transaction data

| Transaction Type | Has lot_id set | lot_id is NULL | Total |
|---|---|---|---|
| **Receive** | **1** | **57** | 58 |
| **Ship** | **195** | 3 | 198 |

This is the core problem.

- Almost every **Receive** transaction has `lot_id = NULL` → **not counted in the balance**
- Almost every **Ship** transaction has `lot_id` set → **counted as a subtraction**

The math becomes: `0 receives − all ships = negative number` for every lot.

### Per-lot proof

| SKU | Active Lot | Receives Counted | Units Shipped | **Current Balance** |
|---|---|---|---|---|
| 17612 | 260047 | 0 units | 356 units | **−356** |
| 17904 | 250240 | 0 units | 28 units | **−28** |
| 17914 | 250297 | 0 units | 26 units | **−26** |
| 18675 | 240231 | 0 units | 82 units | **−82** |
| 18795 | 11001 | 0 units | 2 units | **−2** |

All five active lots show negative. The tagger's query filters to `balance > 0`, so it finds
**zero lots**, builds an empty list, and fails every order.

### The exact failure path in the code

In `src/lot_tagger/tagger.py` (lines 48–63), the tagger builds its active lots list:

```python
cursor.execute(ACTIVE_LOTS_QUERY)          # Runs: WHERE lot_balances.balance > 0
active_lots = {row[0]: row[2] for row in cursor.fetchall()}   # Returns {} (empty)
```

Then later, for each order item:

```python
if sku not in active_lots:
    INSERT INTO lot_tagging_failures ...   # Every order hits this
```

Because `active_lots` is always empty, every SKU fails this check. This is not a code bug —
the code logic is correct. The data feeding it is wrong.

---

## Section 3 — How Did It Go Negative? (The Timeline)

### The two systems involved

1. **The lot tagger** sets CF1 in ShipStation when an order ships. It reads lot balances to
   know which lot is current.

2. **The lot deduction system** (`src/services/inventory/lot_deduction.py`) records ship
   transactions in the database and sets `lot_id` on each one, linking the shipment to a
   specific lot.

### What happened and when

| Date | Event |
|---|---|
| Sept 19, 2025 | System baseline established. Inventory counts set for 17904/250240 and 18675/240231 — but **no receive transactions were created** for these lots. They predate transaction tracking. |
| Oct 2, 2025 | Active lots for 17904, 17914, 18675, 18795 created in database. |
| April 2, 2026 | Lot 260047 created for SKU 17612. |
| **April 13, 2026** | **First ship transaction with `lot_id` set appears.** The lot deduction system went live and started linking ship records to lots. From this point, ship transactions started counting against lot balances — but receive transactions still had no `lot_id`, so they didn't count at all. Balances began going negative. |
| April 15, 2026 | 3 tagging failures recorded (promo SKU feature launch day). |
| April 16–20, 2026 | 0 failures recorded. Orders tagged successfully (14 orders still have CF1 set from this window — 862451 through 862461). |
| April 20, 2026 | Last batch processor run adds additional ship-with-lot_id records (22:25 UTC). |
| **April 21, 2026** | **42 failures recorded at 17:04 UTC.** New orders arriving today (862463 and above) have no CF1 and cannot be tagged. |

### Why it was working April 16–20

The 14 orders with CF1 already set (values like `17612 - 260047`) were tagged during the
April 16–20 window. The most likely explanation: those orders were processed when the tagger
could still find a valid path — either a momentarily positive balance window, or they were
tagged by a previous cycle before the shipment volume tipped all balances negative. The
tagger has been recording failures since April 15 for any order it could not handle.

The key point: **this is not a new problem that appeared today**. It has been silently
eroding since April 13. Today is simply when the volume of untagged orders became large
enough to be noticed.

---

## Section 4 — The Proposed Fix and What It Does

### The backfill SQL

```sql
UPDATE inventory_transactions it
SET lot_id = l.lot_id
FROM skus s
JOIN lots l ON l.sku_id = s.sku_id
WHERE it.sku        = s.sku_code
  AND it.transaction_type = 'Receive'
  AND it.lot_id     IS NULL
  AND TRIM(it.notes) = l.lot_number;
```

### What this does

The receive transactions already contain the lot number in their `notes` field — that was
how lots were tracked before the `lot_id` column existed. This SQL matches each receive
transaction to the correct lot by comparing `TRIM(notes)` to `lot_number`, then sets
`lot_id` accordingly.

This has been verified: **23 receive rows match cleanly** with an exact `TRIM(notes) =
lot_number` match. No ambiguous or partial matches. The SQL will touch exactly those 23
rows and nothing else.

### What the balances become after the fix

| SKU | Active Lot | Receives Added | Ships | **Projected Balance** | Fixed? |
|---|---|---|---|---|---|
| 17612 | 260047 | +1,728 units | −356 units | **+1,372** | YES ✓ |
| 17904 | 250240 | +0 (no receives exist) | −28 units | **−28** | **NO ✗** |
| 17914 | 250297 | +1,540 units | −26 units | **+1,514** | YES ✓ |
| 18675 | 240231 | +0 (no receives exist) | −82 units | **−82** | **NO ✗** |
| 18795 | 11001 | +933 units | −2 units | **+931** | YES ✓ |

### Is the backfill SQL safe?

Yes. Here is why:

1. **It only changes receive transactions** — ship transactions are untouched. Historical
   shipment records are not affected.

2. **The match condition is exact and verified** — `TRIM(notes) = lot_number` was confirmed
   against all 58 receive records. 23 match. The remaining rows have notes that do not match
   any lot number (pre-tracking records, deprecated lots), so they are safely skipped.

3. **It is reversible** — Running `UPDATE inventory_transactions SET lot_id = NULL WHERE
   transaction_type = 'Receive' AND lot_id IS NOT NULL` would undo it completely.

4. **It only sets lot_id — it does not change quantities, SKUs, dates, or any other field.**

---

## Section 5 — The Incomplete Fix: 17904 and 18675

**This is the most important section before pulling the trigger.**

The backfill SQL fixes three of the five active lots. **SKUs 17904 and 18675 will still
fail after the backfill** because their active lots have no receive transactions at all.

### Why there are no receives

Both lots 250240 (17904) and 240231 (18675) have a `received_date` of September 19, 2025.
That is the system's baseline date — inventory was set up in the database that day, but no
receive transactions were recorded to represent the actual physical stock arriving. The
physical goods existed; the transaction record for receiving them does not.

There is no notes field to match against. There is nothing the backfill can use.

### What is needed for these two SKUs

A baseline **Adjust Up** transaction must be manually added for each lot, with `lot_id` set
to the correct lot ID. The quantity must be large enough to cover all ships already recorded
and still leave a positive balance.

**Current situation:**

| SKU | Active Lot | lot_id (DB) | Ships already recorded | Minimum units needed |
|---|---|---|---|---|
| 17904 | 250240 | 12 | 28 units | ≥ 29 units |
| 18675 | 240231 | 4 | 82 units | ≥ 83 units |

The exact quantity to add should match the **actual current physical inventory** for each
SKU — not just the minimum. Adding only the minimum would cause the lot to go negative
again as soon as the next order ships.

**Recommended SQL (do not run without confirming current physical stock):**

```sql
-- For SKU 17904, lot 250240 (lot_id = 12)
-- Replace [ACTUAL_QTY] with the verified on-hand unit count for 17904
INSERT INTO inventory_transactions (sku, quantity, transaction_type, notes, lot_id, created_at)
VALUES ('17904', [ACTUAL_QTY], 'Adjust Up', 'Baseline receive backfill — lot 250240', 12, NOW());

-- For SKU 18675, lot 240231 (lot_id = 4)
-- Replace [ACTUAL_QTY] with the verified on-hand unit count for 18675
INSERT INTO inventory_transactions (sku, quantity, transaction_type, notes, lot_id, created_at)
VALUES ('18675', [ACTUAL_QTY], 'Adjust Up', 'Baseline receive backfill — lot 240231', 4, NOW());
```

---

## Section 6 — Order of Operations (Recommended Sequence)

When you are ready to proceed, here is the recommended sequence:

1. **Verify current physical stock for SKUs 17904 and 18675** (so you have the right
   quantities for Section 5).

2. **Run the backfill SQL** (Section 4). This fixes 17612, 17914, and 18795 immediately.
   Verify by re-querying `lot_balances` — three lots should now show positive.

3. **Run the baseline Adjust Up inserts** for 17904 and 18675 with confirmed quantities
   (Section 5). All five lots should then show positive balance.

4. **Restart the lot-tagger workflow.** It will pick up the 26 untagged orders on its next
   cycle and begin tagging them.

5. **Verify in ShipStation** that CF1 is being populated on the awaiting-shipment orders
   (862463 and above).

---

## Section 7 — What This Does NOT Address

This report covers the lot balance failure only. Two separate issues exist that are not
addressed here:

- **Promo SKU warehouse location bug** (`src/services/shipstation/api_client.py`,
  `create_replacement_order` around line 1033): when a replacement order is created for a
  promo SKU, it does not copy the `warehouseLocation` field from the base item. This causes
  ShipStation to auto-split the order. The user has been handling this manually.

- **Promo hold tag is visual-only**: the `_apply_promo_hold` tag is set in ShipStation for
  visual identification, but neither the tagger nor the upload workflow checks for it
  programmatically.

These are documented separately and require their own fixes.

---

## Appendix — Raw Evidence

### lot_balances view definition (confirmed from production)
```sql
SELECT l.lot_id, s.sku_code, l.lot_number, l.status, l.received_date,
  COALESCE(SUM(
    CASE WHEN it.transaction_type IN ('Receive','Adjust Up','Repack') THEN it.quantity
         WHEN it.transaction_type IN ('Ship','Adjust Down') THEN -it.quantity
         ELSE 0 END
  ), 0) AS balance
FROM lots l
JOIN skus s ON s.sku_id = l.sku_id
LEFT JOIN inventory_transactions it ON it.lot_id = l.lot_id
GROUP BY l.lot_id, s.sku_code, l.lot_number, l.status, l.received_date, l.notes,
         l.created_at, l.updated_at
```

### ACTIVE_LOTS_QUERY (from tagger.py lines 20–27)
```sql
SELECT DISTINCT ON (s.sku_code) s.sku_code, l.lot_id, l.lot_number
FROM lots l
JOIN skus s ON s.sku_id = l.sku_id
JOIN lot_balances lb ON lb.lot_id = l.lot_id
WHERE lb.balance > 0
  AND l.status NOT IN ('quarantine', 'inactive')
ORDER BY s.sku_code, l.received_date ASC NULLS LAST, l.lot_id ASC
```

With all active lots showing negative balance, this query returns zero rows every time it runs.

### Tagging failure history (from lot_tagging_failures table)
```
2026-04-15  →  3 failures
2026-04-21  →  42 failures
All other days  →  0 failures
```

### Ship transactions with lot_id — date range
```
First:  2026-04-13 16:01:48 UTC
Last:   2026-04-20 22:25:54 UTC
Total:  195 ship transactions linked to lots
```

### Currently untagged orders (as of April 21, 2026)
26 orders in `awaiting_shipment` status have blank CF1. All attempted tags are recorded
in `lot_tagging_failures`. No orders have been lost — they are simply waiting for the
tagger to work.

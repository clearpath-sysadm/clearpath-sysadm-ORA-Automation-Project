# RCA: PT Kit (17612) Inventory Overcount — April 2026

**Date:** 2026-04-20  
**SKU:** 17612 — PT Kit  
**Reported symptom:** Inventory reads ~1,500 units higher than expected physical stock  
**Status:** Root cause confirmed. Production correction pending (see Remediation below).

---

## Summary

A "production seed restore" transaction added 1,728 phantom units to PT Kit inventory on April 10, 2026. This was the exact quantity of lot 260047 (three deliveries of 576 units each), which was already correctly recorded in March 2026. The result was lot 260047 being counted twice.

At the time of the April 17 physical count (2,234 units), the system showed 3,730 — a discrepancy of **1,496 units**, matching the ~1,500 reported. A secondary ship double-counting issue (tracked separately) accounts for an additional ~298 units working in the opposite direction, netting to a 1,430-unit live gap.

---

## Timeline

| Date | Event | Balance |
|------|-------|---------|
| Mar 18 | Receive lot 260047: +576 (tx 116) | — |
| Mar 24 | Receive lot 260047: +576 (tx 117) | — |
| Mar 27 | Receive lot 260047: +576 (tx 123) | — |
| Apr 1 | Nathan Neely physical count: 2,331 → 2,313 (−18 adj) | **2,313 verified** |
| Apr 7 | Snapshot: 2,069 (~41/day depletion — normal) | 2,069 |
| Apr 8 | Snapshot: 2,024 (−45 — normal) | 2,024 |
| Apr 9 | Snapshot: 1,977 (−47 — normal) | 1,977 |
| **Apr 10** | **Seed restore Receive +1,728 (tx 127) — ERRONEOUS** | **3,705** |
| Apr 10 | Ships −17 | 3,688 |
| Apr 13–15 | Ships −164 | ~3,524 |
| Apr 16 | Receive lot 260082: +576 | ~4,100 |
| Apr 16–17 | Ships −142 (incl. retroactive entries logged Apr 20) | ~3,958 |
| Apr 17 EOD | **Physical count: 2,234** (lot 260047: 1,658 + lot 260082: 576) | system ≈ 3,730 |
| Apr 20 | Current `inventory_current` | **3,664** |

---

## Root Cause

**Transaction ID 127** (2026-04-10 15:22:50 UTC):

```
type:      Receive
quantity:  1,728
notes:     "Opening balance — production seed restore 2026-04-10"
```

This was entered during the April 8–17 ShipStation integration transition. Someone observed that lot 260047 did not appear to be fully reflected in a report or view and manually re-entered the entire lot as a single "opening balance." The lot was already in the system via transactions 116, 117, and 123. The result was 1,728 units (3 × 576) counted twice.

**Identifying characteristics of the erroneous transaction:**
- No real lot number — only the generic phrase "production seed restore"
- Quantity is exactly 3 × 576 = the sum of all lot 260047 deliveries
- Every other Receive since June 2025 has a legitimate lot number (250xxx or 260xxx)
- The daily snapshot shows an unexplained +1,704 jump on April 10 with no physical receipt

---

## Physical Count Reconciliation

Apr 17 physical count by location:
- Lot 260047: 34 pallets × 48 + 26 partial = **1,658 units**
- Lot 260082: 12 pallets × 48 + 0 partial = **576 units**
- **Total: 2,234 units**

| | Units |
|---|---|
| `inventory_current` on Apr 20 | 3,664 |
| Seed restore to void (tx 127) | −1,728 |
| Balance after correction | 1,936 |
| Physical count Apr 17 EOD | 2,234 |
| Remaining gap (system under physical) | +298 |

The remaining 298-unit gap is attributable to ship transaction double-counting (a separate known issue tracked under the "Fix inventory history" task), which over-deducted shipments during the Apr 8–17 gap period.

**Two errors, opposite directions:**
- Seed restore inflates: +1,728
- Ship over-deductions deflate: −298
- Net overcount vs physical: **+1,430** (= 3,664 − 2,234 ✓)

---

## Remediation

### Step 1 — Apply correction in production (PENDING)

Run the following SQL against the production database, or submit via the dashboard's
manual adjustment UI (Inventory → Add Transaction → Adjust Down):

```sql
-- 1. Insert the correcting Adjust Down transaction
INSERT INTO inventory_transactions
    (date, sku, quantity, transaction_type, notes, created_at)
VALUES (
    '2026-04-20',
    '17612',
    1728,
    'Adjust Down',
    'Void erroneous seed restore: tx ID 127 (2026-04-10) re-entered lot 260047 '
    '(3×576=1,728 units) already recorded via tx 116/117/123 in March 2026. '
    'Confirmed by Apr 17 physical count (2,234 units).',
    NOW()
);

-- 2. Update the live balance
UPDATE inventory_current
SET current_quantity = current_quantity - 1728,
    last_updated = NOW()
WHERE sku = '17612';

-- 3. Validate
SELECT sku, product_name, current_quantity, last_updated
FROM inventory_current
WHERE sku = '17612';
-- Expected: current_quantity = 1,936
```

### Step 2 — Resolve remaining 298-unit gap

The +298 gap (physical count 2,234 vs corrected system 1,936) is tracked under the
existing "Fix inventory history / double-counting" task. It requires reversing
duplicate Ship transaction entries from the April 8–17 gap period.

---

## Preventive Controls Added

A guard was added to `app.py` (POST `/api/inventory_transactions`) that rejects
Receive transactions with a quantity ≥ 200 when no lot number is provided in the
notes field. This prevents future phantom receives from being entered without
traceable lot documentation. See commit history for the code change.

---

## Verification Queries

```sql
-- Confirm current state
SELECT sku, product_name, current_quantity, last_updated
FROM inventory_current WHERE sku = '17612';

-- Confirm the erroneous transaction exists (pre-fix)
SELECT id, date, transaction_type, quantity, notes
FROM inventory_transactions
WHERE sku = '17612' AND id = 127;

-- Confirm correction transaction (post-fix)
SELECT id, date, transaction_type, quantity, notes
FROM inventory_transactions
WHERE sku = '17612' AND transaction_type = 'Adjust Down'
ORDER BY created_at DESC LIMIT 5;

-- Cross-check against physical count snapshot
SELECT snapshot_date, eod_quantity
FROM inventory_daily_snapshots
WHERE sku = '17612' AND snapshot_date BETWEEN '2026-04-07' AND '2026-04-17'
ORDER BY snapshot_date;
-- Apr 9 should show ~1,977; Apr 10 jump to ~3,681 confirms seed restore
```

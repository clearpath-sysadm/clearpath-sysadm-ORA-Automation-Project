# Order 691965 - Manual Shipment Edge Case Analysis

**Created:** October 28, 2025  
**Order:** 691965 (Queen Charlotte Dental)  
**Issue:** Manually shipped order did not result in expected inventory adjustment during EOD

---

## Summary

Order 691965 was manually shipped outside of ShipStation, then marked as shipped in ShipStation using the "Mark as Shipped" feature. When the EOD process ran, the inventory adjustment did not match expectations.

---

## Investigation Findings

### 1. Order Status in Database

**orders_inbox table:**
```
order_number: 691965
status: shipped
shipstation_order_id: NULL
tracking_number: NULL
ship_name: Dean Nomura
source_system: X-Cart
created_at: 2025-10-22 19:06:57
updated_at: 2025-10-28 21:43:24
```

**Key Observation:** Order has status='shipped' but NO `shipstation_order_id`. This indicates it was marked as shipped in ShipStation manually, not through normal label creation workflow.

---

### 2. Shipped Items Record

**shipped_items table:**
```
order_number: 691965
ship_date: 2025-10-28
sku_lot: 17612 - 250300
quantity_shipped: 1
base_sku: 17612
tracking_number: 394732675115
```

**Key Observation:** ✅ Order WAS successfully synced from ShipStation and added to `shipped_items` with quantity=1.

---

### 3. Manual Inventory Adjustment

**inventory_transactions table:**
```
date: 2025-10-24
sku: 17612
quantity: -2 (Adjust Down)
transaction_type: Adjust Down
notes: 691965 Queen Charlotte Dental Shipped from FedEx Store
```

**Key Observation:** ⚠️ A MANUAL inventory adjustment was made on Oct 24 (4 days before shipment), reducing inventory by 2 units for this same order.

---

### 4. Current Inventory Status

**inventory_current table:**
```
sku: 17612
current_quantity: 300
last_updated: 2025-10-28 21:42:11
```

**Today's Total Shipments (Oct 28):**
```
Total SKU 17612 shipped today: 124 units
```

---

## Root Cause Analysis

### The Double-Counting Problem

**Timeline of Events:**

1. **Oct 22:** Order 691965 created in X-Cart and imported to `orders_inbox`
2. **Oct 24:** User manually ships order outside ShipStation
3. **Oct 24:** User creates manual inventory adjustment: `-2 units` for "691965 Queen Charlotte Dental"
4. **Oct 28:** User marks order as shipped in ShipStation (using "Mark as Shipped" feature)
5. **Oct 28:** EOD process runs and syncs shipments from ShipStation
6. **Oct 28:** Order 691965 appears in `shipped_items` with `quantity_shipped: 1`

### Inventory Calculation Logic

The EOD process calculates inventory using `calculate_current_inventory()` which processes:

```python
# From daily_shipment_processor.py lines 553-560

current_inventory_df = calculate_current_inventory(
    initial_inventory=initial_inventory,          # Base inventory from Sept 19
    inventory_transactions_df=transactions_df,    # INCLUDES Oct 24 manual -2
    shipped_items_df=shipped_items_df,           # INCLUDES Oct 28 ShipStation -1
    key_skus=target_skus,
    current_week_start_date=current_week_start,
    current_week_end_date=current_week_end
)
```

**Expected Behavior:**
- Initial inventory: X units
- Subtract inventory_transactions: -2 (manual adjustment Oct 24)
- Subtract shipped_items: -1 (ShipStation sync Oct 28)
- **Final: X - 3 units**

**User Expected Behavior:**
- Initial inventory: X units
- Subtract shipped quantity: -2 (the actual shipped amount)
- **Final: X - 2 units**

### The Discrepancy

The system is now deducting **3 units total** (-2 from manual adjustment, -1 from ShipStation sync) instead of the actual **2 units shipped**.

**Why the mismatch?**

1. **Manual Adjustment Quantity:** User adjusted -2 units (actual shipped qty)
2. **ShipStation Sync Quantity:** ShipStation recorded only -1 unit
3. **Total Deduction:** -2 + -1 = -3 units

**Possible Reasons:**
- User manually adjusted -2, but when marking as shipped in ShipStation, only entered 1 unit
- OR: ShipStation's "Mark as Shipped" feature only captured 1 item from the order
- OR: There's a quantity mismatch between what was actually shipped (2) vs what ShipStation recorded (1)

---

## How the Current System Handles Manual Shipments

### ShipStation "Mark as Shipped" Flow

When a user marks an order as shipped manually in ShipStation:

1. **ShipStation API Returns:**
   - `shipDate`: Date marked as shipped
   - `shipmentItems`: Items in the order with quantities
   - `trackingNumber`: Tracking number entered (if any)
   - `orderId`: ShipStation's internal order ID

2. **EOD Process (daily_shipment_processor.py):**
   - Fetches shipments with `shipment_status="shipped"` from ShipStation API
   - Filters out voided shipments
   - Processes `shipmentItems` to extract SKU, lot, quantity
   - Inserts into `shipped_items` table
   - Calculates inventory using ALL `shipped_items` + `inventory_transactions`

3. **Inventory Calculation:**
   - Treats ShipStation shipments as SEPARATE from manual inventory adjustments
   - Both are deducted from inventory independently

### The Edge Case

**Scenario:** Order shipped manually → Manual inventory adjustment → Marked in ShipStation

**Problem:** Inventory gets deducted TWICE:
1. Once from manual `inventory_transactions` entry
2. Once from `shipped_items` sync from ShipStation

---

## System Limitations Identified

### 1. No Link Between Manual Adjustments and ShipStation Orders

The system does NOT check:
- "Does this ShipStation order already have a manual inventory adjustment?"
- "Should I skip deducting inventory because it was already manually adjusted?"

**Current Logic:**
```python
# shipped_items are processed independently
# inventory_transactions are processed independently
# NO cross-checking for duplicate deductions
```

### 2. ShipStation "Mark as Shipped" Creates New Shipment Record

Even though the order was manually shipped and inventory adjusted, when marked in ShipStation, it appears as a NEW shipment in the API response, triggering a second inventory deduction.

### 3. No "Already Adjusted" Flag

The `orders_inbox` table doesn't have a field like:
- `inventory_manually_adjusted: boolean`
- `skip_inventory_deduction: boolean`

So the EOD process has no way to know "this order was already handled manually."

---

## Expected vs Actual Inventory Impact

### Scenario: Order 691965 (Actual Case)

**Actual Shipped Quantity:** 2 units of SKU 17612

**Timeline:**
- Oct 24: Manual adjustment -2 units → Inventory = X - 2
- Oct 28: ShipStation sync -1 unit → Inventory = X - 3

**Discrepancy:** Inventory is 1 unit LOWER than it should be (-3 instead of -2)

### If User Had NOT Made Manual Adjustment

**Timeline:**
- Oct 28: ShipStation sync -1 unit → Inventory = X - 1

**Discrepancy:** Inventory would be 1 unit HIGHER than it should be (-1 instead of -2)

---

## Recommended Solutions

### Option 1: Avoid Manual Inventory Adjustments for Orders (BEST PRACTICE)

**Workflow:**
1. Ship order manually outside ShipStation
2. Immediately mark as shipped in ShipStation (same day)
3. Let EOD process handle inventory deduction automatically
4. **DO NOT** create manual inventory adjustment

**Pros:**
- No double-counting
- Single source of truth (ShipStation)
- Audit trail maintained

**Cons:**
- Requires ShipStation update same day as shipment
- User must ensure correct quantity in ShipStation

---

### Option 2: Create "Manual Shipment" Transaction Type (SYSTEM ENHANCEMENT)

**Design:**
Add new `transaction_type = 'Manual Shipment'` with order number tracking

**Changes Required:**

1. **Inventory Transactions Table:**
```sql
ALTER TABLE inventory_transactions
ADD COLUMN order_number VARCHAR(100);
```

2. **Inventory Calculation Logic:**
```python
def calculate_current_inventory(...):
    # Get manual shipments (not to be double-counted)
    manual_shipments = transactions_df[
        transactions_df['transaction_type'] == 'Manual Shipment'
    ]['order_number'].tolist()
    
    # Exclude shipped_items that have corresponding manual shipments
    shipped_items_df = shipped_items_df[
        ~shipped_items_df['OrderNumber'].isin(manual_shipments)
    ]
    
    # Continue with inventory calculation
```

3. **UI Changes:**
- Add "Mark as Manual Shipment" button on Orders Inbox
- Captures order number in transaction record
- Flags order to prevent double-counting

**Pros:**
- Handles edge case systematically
- Audit trail maintained
- Prevents double-counting

**Cons:**
- Requires code changes
- Adds complexity
- Still requires user to remember to use correct transaction type

---

### Option 3: ShipStation Quantity Verification (IMMEDIATE FIX)

**Root Cause:** ShipStation shows 1 unit, manual adjustment was 2 units

**Action Required:**
1. Check order 691965 in ShipStation:
   - How many units are listed in the order?
   - Was the correct quantity entered when marking as shipped?
2. If ShipStation shows wrong quantity (1 instead of 2):
   - Update ShipStation order to correct quantity
   - Re-run EOD to recalculate inventory
3. If manual adjustment was wrong (should have been 1, not 2):
   - Adjust inventory +1 to correct the overcorrection

**Verification Query:**
```sql
-- Check if quantities match
SELECT 
    it.date as manual_adj_date,
    it.quantity as manual_qty,
    si.ship_date as shipstation_date,
    si.quantity_shipped as shipstation_qty,
    it.notes
FROM inventory_transactions it
LEFT JOIN shipped_items si ON si.order_number = '691965'
WHERE it.notes LIKE '%691965%'
ORDER BY it.date;
```

---

### Option 4: Reverse Manual Adjustment (QUICKEST FIX)

**If ShipStation quantity is correct (1 unit):**

1. **Create compensating transaction:**
```sql
INSERT INTO inventory_transactions (date, sku, quantity, transaction_type, notes)
VALUES (
    '2025-10-28',
    '17612',
    1,
    'Adjust Up',
    'Correction: Order 691965 manual adjustment was -2, but ShipStation sync shows -1. Reversing duplicate deduction of 1 unit.'
);
```

2. **Re-run EOD** to recalculate inventory

**Result:** Inventory will show correct amount (manually adjusted -2, ShipStation -1, correction +1 = net -2)

---

## Lessons Learned

### 1. Manual Shipments Create Complexity

When orders are shipped outside the normal workflow, there's a high risk of:
- Double-counting inventory deductions
- Quantity mismatches
- Lost audit trail

### 2. ShipStation is Single Source of Truth

For inventory accuracy, ShipStation should be the ONLY source of shipped quantities:
- Even manual shipments should be marked in ShipStation ASAP
- Avoid manual inventory adjustments for shipped orders
- Use transaction types (Receive, Repack, etc.) for non-shipment inventory changes

### 3. System Lacks Manual Shipment Workflow

Current system assumes all shipments flow through:
1. Order created in orders_inbox
2. Uploaded to ShipStation
3. Label created in ShipStation
4. ShipStation marks as shipped
5. EOD syncs back to database

**Gap:** No built-in workflow for "shipped outside ShipStation" scenario

---

## Immediate Action Items for User

### To Fix Current Discrepancy:

1. **Verify quantities in ShipStation:**
   - Log into ShipStation
   - Find order 691965
   - Check: Does it show 1 unit or 2 units?

2. **If ShipStation shows 1 unit (current state):**
   - Actual shipped: 2 units
   - Manual adjustment: -2 units
   - ShipStation sync: -1 unit
   - Total deducted: -3 units
   - **Fix:** Add +1 unit adjustment to compensate

3. **If ShipStation shows 2 units:**
   - Manual adjustment: -2 units (correct)
   - ShipStation should sync: -2 units (but showing -1)
   - **Fix:** Check why ShipStation API returned only 1 unit

### To Prevent Future Issues:

1. **For manual shipments:**
   - Mark as shipped in ShipStation SAME DAY
   - DO NOT create manual inventory adjustment
   - Let EOD handle inventory deduction

2. **If inventory adjustment needed before ShipStation update:**
   - Create adjustment with clear notes including order number
   - When marking in ShipStation, verify quantity matches
   - Consider using Option 4 (compensating transaction) if needed

---

## Technical Details for Developer

### Where the Inventory Deduction Happens

**File:** `src/services/reporting_logic/inventory_calculations.py`

**Function:** `calculate_current_inventory()`

**Logic Flow:**
```python
# Line ~40-90
for report_date in all_dates_for_report:
    bod_inventory = current_inventory.copy()
    
    # Process inventory transactions (INCLUDES manual adjustments)
    daily_transactions = transactions_df[transactions_df['Date'] == report_date]
    for _, txn in daily_transactions.iterrows():
        if txn['TransactionType'] == 'Receive':
            current_inventory[sku] += qty
        elif txn['TransactionType'] in ['Adjust Down', 'Manual Shipment']:
            current_inventory[sku] -= qty
        # ... etc
    
    # Process shipped items (INCLUDES ShipStation shipments)
    daily_shipments = shipped_items_df[shipped_items_df['Date'] == report_date]
    for _, ship in daily_shipments.iterrows():
        current_inventory[sku] -= ship['Quantity_Shipped']
```

**Problem:** No cross-check between `daily_transactions` and `daily_shipments` for duplicate order numbers.

---

## Conclusion

Order 691965 demonstrates an edge case where:
1. User manually shipped order and adjusted inventory (-2 units)
2. User marked order as shipped in ShipStation
3. ShipStation sync deducted inventory again (-1 unit)
4. Total deduction: -3 units instead of expected -2 units

**Root Cause:** System treats manual inventory adjustments and ShipStation shipments as independent, causing double-counting for manually shipped orders.

**Immediate Fix:** Verify quantities and create compensating adjustment if needed.

**Long-term Fix:** Implement manual shipment workflow (Option 2) or enforce best practice (Option 1).

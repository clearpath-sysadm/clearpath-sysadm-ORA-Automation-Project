# 🔧 Manual Orders Fix - Execution Guide
**Date:** October 15, 2025  
**Issue:** Orders 100521-100526 created with wrong order numbers

---

## 📊 Current Situation

**Problematic Orders:**
| Order # | Status | ShipStation ID | Can Delete? |
|---------|--------|----------------|-------------|
| 100521 | awaiting_shipment | 223387873 | ✅ Yes (API) |
| 100522 | awaiting_shipment | 223387885 | ✅ Yes (API) |
| 100523 | awaiting_shipment | 223387942 | ✅ Yes (API) |
| 100524 | awaiting_shipment | 223770760 | ✅ Yes (API) |
| 100525 | shipped | 223770778 | ❌ No (Manual) |
| 100526 | shipped | 224435389 | ❌ No (Manual) |

---

## 🚀 Step-by-Step Execution

### **Step 1: Create Backup** (REQUIRED - 2 min)

```bash
python utils/backup_shipstation_data.py
```

**Expected Output:**
```
✅ Backup created: backups/shipstation_backup_20251015_HHMMSS.json
```

---

### **Step 2: Disable Workflows** (CRITICAL - 1 min)

**Option A - Via UI:**
1. Open `workflow_controls.html`
2. Turn OFF these workflows:
   - `shipstation-upload`
   - `status-sync`  
   - `unified-shipstation-sync`

**Option B - Via SQL:**
```bash
python -c "
from src.services.database.pg_utils import execute_query
execute_query('''
    UPDATE workflow_controls 
    SET enabled = FALSE 
    WHERE name IN ('shipstation-upload', 'status-sync', 'unified-shipstation-sync')
''')
print('✅ Workflows disabled')
"
```

---

### **Step 3: Test Cancellation (DRY RUN)** (1 min)

```bash
python utils/cancel_manual_orders.py \
  --order-ids 223387873,223387885,223387942,223770760 \
  --dry-run
```

**Expected Output:**
```
[DRY RUN] Would delete order 223387873
[DRY RUN] Would delete order 223387885
[DRY RUN] Would delete order 223387942
[DRY RUN] Would delete order 223770760
✅ Successful: 4/4
```

---

### **Step 4: Execute Cancellation** (DESTRUCTIVE - 2 min)

```bash
python utils/cancel_manual_orders.py \
  --order-ids 223387873,223387885,223387942,223770760
```

**When prompted:**
```
⚠️  WARNING: This will DELETE these orders from ShipStation!
Proceed with cancellation? (yes/no): yes
```

**Expected Output:**
```
✅ Successfully deleted order ID 223387873
✅ Updated local database: 1 record(s) marked as cancelled
✅ Successfully deleted order ID 223387885
✅ Updated local database: 1 record(s) marked as cancelled
✅ Successfully deleted order ID 223387942
✅ Updated local database: 1 record(s) marked as cancelled
✅ Successfully deleted order ID 223770760
✅ Updated local database: 1 record(s) marked as cancelled

SUMMARY:
✅ Successful: 4/4
❌ Failed: 0/4
```

---

### **Step 5: Handle Shipped Orders (MANUAL)**

**For 100525 & 100526 (already shipped):**

1. **In ShipStation UI:**
   - Go to Orders → Search for order IDs `223770778` and `224435389`
   - Check if they can be voided (if not yet fulfilled)
   - If fulfilled, contact customer service to discuss options

2. **Document Details:**
   - Take screenshots of order details
   - Note tracking numbers and ship dates
   - Save customer information

3. **Update Local Database:**
```bash
python -c "
from src.services.database.pg_utils import execute_query
execute_query('''
    UPDATE orders_inbox 
    SET status = 'voided_manual', 
        updated_at = CURRENT_TIMESTAMP 
    WHERE order_number IN ('100525', '100526')
''')
print('✅ Marked 100525 & 100526 as voided_manual')
"
```

---

### **Step 6: Recreate Correct Orders** (5-10 min)

**Option A - Manual Upload to ShipStation:**
1. Prepare order data with correct numbers (100527-100532)
2. Upload via ShipStation UI or API
3. Verify lot numbers are correct

**Option B - Use existing utility (if available):**
```bash
# If you have a CSV with correct order data:
python utils/create_orders_from_csv.py --file correct_orders_100527-100532.csv
```

---

### **Step 7: Verify Results** (2 min)

```bash
# Check for duplicates
python utils/identify_shipstation_duplicates.py --mode summary

# Verify orders in database
python -c "
from src.services.database.pg_utils import execute_query
orders = execute_query('''
    SELECT order_number, status, shipstation_order_id 
    FROM orders_inbox 
    WHERE order_number >= '100521' 
    ORDER BY order_number
''')
for o in orders:
    print(f'{o[0]}: {o[1]} (SS: {o[2]})')
"
```

**Expected:**
- 100521-100524: status = `cancelled`
- 100525-100526: status = `voided_manual` or `shipped`
- 100527+: New orders with correct data

---

### **Step 8: Re-enable Workflows** (1 min)

**Option A - Via UI:**
1. Open `workflow_controls.html`
2. Turn ON:
   - `shipstation-upload`
   - `status-sync`
   - `unified-shipstation-sync`

**Option B - Via SQL:**
```bash
python -c "
from src.services.database.pg_utils import execute_query
execute_query('''
    UPDATE workflow_controls 
    SET enabled = TRUE 
    WHERE name IN ('shipstation-upload', 'status-sync', 'unified-shipstation-sync')
''')
print('✅ Workflows re-enabled')
"
```

---

### **Step 9: Monitor (24 hours)**

- Check logs for any new issues
- Verify new orders use correct lot numbers
- Monitor for duplicate detections

---

## 📋 Complete Checklist

- [ ] **Backup created** (`backups/shipstation_backup_*.json`)
- [ ] **Workflows disabled** (shipstation-upload, status-sync, unified-shipstation-sync)
- [ ] **Dry-run tested** (4 orders confirmed)
- [ ] **Orders cancelled** (100521-100524 deleted from ShipStation)
- [ ] **Local DB updated** (orders marked as cancelled)
- [ ] **Shipped orders handled** (100525-100526 manual void/documentation)
- [ ] **New orders created** (100527+ with correct numbers)
- [ ] **Results verified** (no duplicates, correct status)
- [ ] **Workflows re-enabled**
- [ ] **Monitoring active** (24 hour watch period)

---

## ⚠️ Troubleshooting

**Problem:** API fails with "Order cannot be deleted"
- **Cause:** Order status changed (might be shipped/cancelled)
- **Solution:** Check order status in ShipStation UI, handle manually

**Problem:** Local database not updated
- **Cause:** ShipStation order ID mismatch
- **Solution:** Run status sync to refresh local data

**Problem:** Accidentally deleted wrong order
- **Cause:** Wrong order ID provided
- **Solution:** Restore from backup (`backups/shipstation_backup_*.json`)

---

## 📞 Support Resources

- **Full Remediation Docs:** `docs/duplicate-remediation/`
- **Workflow Controls:** `docs/manuals/WORKFLOW_CONTROLS_USER_MANUAL.md`
- **Backup Location:** `backups/`
- **Error Logs:** `logs/`

---

**Total Time Estimate:** 15-20 minutes (excluding manual order recreation)  
**Status:** Ready to execute ✅

# 🔧 Manual Orders Fix - Execution Guide (UPDATED)
**Date:** October 15, 2025  
**Issue:** Orders 100521-100526 created with wrong order numbers

---

## 📊 Current Situation (CORRECTED)

**All Orders Can Be Cancelled via API:**

| Order # | Status | ShipStation ID | Company Name | Action |
|---------|--------|----------------|--------------|--------|
| 100521 | awaiting_shipment | 223387873 | LAKEVIEW FAMILY DENTAL | ✅ CANCEL via API |
| 100522 | awaiting_shipment | 223387885 | LAKEVIEW FAMILY DENTAL | ✅ CANCEL via API |
| 100523 | awaiting_shipment | 223387942 | LAKEVIEW FAMILY DENTAL | ✅ CANCEL via API |
| 100524 | awaiting_shipment | 223770760 | LAKEVIEW FAMILY DENTAL | ✅ CANCEL via API |
| 100525 | awaiting_shipment | 223770778 | BRAZOS RIVER DENTAL | ✅ CANCEL via API |
| 100526 | awaiting_shipment | 224435389 | BORDLEE FAMILY & COSMET | ✅ CANCEL via API |

**Good News:** All orders are "Awaiting Shipment" - no manual handling required! ✅

---

## 🚀 Quick Execution (15 minutes total)

### **Step 1: Create Backup** (2 min)
```bash
python utils/backup_shipstation_data.py
```

### **Step 2: Disable Workflows** (1 min)
```bash
python -c "
from src.services.database.pg_utils import execute_query
execute_query('''
    UPDATE workflow_controls 
    SET enabled = FALSE 
    WHERE workflow_name IN ('shipstation-upload', 'unified-shipstation-sync', 'xml-import')
''')
print('✅ Workflows disabled')
"
```
**Note:** Disables upload, sync, and XML import to prevent new orders during fix.

### **Step 3: Test Cancellation - ALL 6 Orders** (1 min)
```bash
# RECOMMENDED: CANCEL (preserves audit trail)
python utils/cancel_orders_by_status.py \
  --order-ids 223387873,223387885,223387942,223770760,223770778,224435389 \
  --dry-run
```

### **Step 4: Execute Cancellation - ALL 6 Orders** (2 min)
```bash
# RECOMMENDED: CANCEL (sets status to 'cancelled', preserves orders for audit)
python utils/cancel_orders_by_status.py \
  --order-ids 223387873,223387885,223387942,223770760,223770778,224435389
```

**When prompted, type:** `yes`

**Note:** Using CANCEL (not DELETE) to preserve audit trail.

### **Step 5: Verify Cancellation** (1 min)
```bash
python -c "
from src.services.database.pg_utils import execute_query
orders = execute_query('''
    SELECT order_number, status, shipstation_order_id 
    FROM orders_inbox 
    WHERE order_number IN ('100521','100522','100523','100524','100525','100526')
    ORDER BY order_number
''')
print('Current status:')
for o in orders:
    print(f'  {o[0]}: {o[1]} (SS: {o[2]})')
"
```

**Expected:** All 6 orders show `status = 'cancelled'`

### **Step 6: Recreate Correct Orders** (5-10 min)
Create new orders with correct numbers starting at **100527**:
- Use ShipStation UI or API
- Ensure correct lot numbers (17612 - 250070 based on screenshot)
- Verify company names match original orders

### **Step 7: Re-enable Workflows** (1 min)
```bash
python -c "
from src.services.database.pg_utils import execute_query
execute_query('''
    UPDATE workflow_controls 
    SET enabled = TRUE 
    WHERE workflow_name IN ('shipstation-upload', 'unified-shipstation-sync', 'xml-import')
''')
print('✅ Workflows re-enabled')
"
```

---

## 📋 Complete Checklist

- [ ] **Backup created** (`backups/shipstation_backup_*.json`)
- [ ] **Workflows disabled** 
- [ ] **Dry-run tested** (6 orders confirmed)
- [ ] **ALL 6 orders cancelled** (100521-100526 status set to 'cancelled' - preserved for audit)
- [ ] **Local DB updated** (all marked as cancelled)
- [ ] **New orders created** (100527+ with correct numbers and lot 250070)
- [ ] **Results verified** (no duplicates)
- [ ] **Workflows re-enabled**
- [ ] **Monitoring active** (24 hour watch)

---

## ✅ Key Updates from Original Plan

**CORRECTED:**
- ❌ ~~100525 & 100526 are shipped~~ → ✅ **All 6 orders are awaiting_shipment**
- ❌ ~~Manual handling needed~~ → ✅ **Full API automation available**
- ✅ **Simpler process** - no manual ShipStation UI steps required
- ✅ **Faster execution** - 15 minutes vs 30 minutes

---

**Total Time:** 15 minutes  
**Complexity:** Low (fully automated)  
**Risk:** Minimal (all orders can be cancelled cleanly)

✅ **Ready to execute!**

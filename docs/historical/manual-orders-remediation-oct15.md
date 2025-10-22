# Manual Orders Remediation - October 15, 2025

## Situation
Manual orders 100521-100526 were created with **incorrect order numbers**. Need to:
1. Cancel/delete wrong orders in ShipStation
2. Recreate with correct order numbers starting at 100527

## Current State

### Orders to Fix:
| Order # | Status | ShipStation ID | Action |
|---------|--------|---------------|--------|
| 100521 | awaiting_shipment | 223387873 | ✅ DELETE via API |
| 100522 | awaiting_shipment | 223387885 | ✅ DELETE via API |
| 100523 | awaiting_shipment | 223387942 | ✅ DELETE via API |
| 100524 | awaiting_shipment | 223770760 | ✅ DELETE via API |
| 100525 | shipped | 223770778 | ⚠️ MANUAL: Already shipped |
| 100526 | shipped | 224435389 | ⚠️ MANUAL: Already shipped |

## Remediation Steps

### Step 1: Create Backup (CRITICAL)
```bash
python utils/backup_shipstation_data.py
```
**Output:** `backups/shipstation_backup_YYYYMMDD_HHMMSS.json`

### Step 2: Disable Upload Workflows (PREVENT NEW ORDERS)
Via workflow_controls.html or SQL:
- Disable: `shipstation-upload`
- Disable: `status-sync`
- Disable: `manual-order-sync`

### Step 3: Cancel Awaiting Shipment Orders (API)
For 100521-100524 (awaiting_shipment status):

```bash
# Option A: Use ShipStation API to cancel
# DELETE /orders/{orderId}

# Option B: Use cleanup utility (if exists)
python utils/cleanup_shipstation_duplicates.py --execute --order-ids 223387873,223387885,223387942,223770760
```

### Step 4: Manual Handling - Shipped Orders
For 100525-100526 (already shipped):
1. **Document shipment details** (tracking, recipient, date)
2. **Void in ShipStation UI** (if possible)
3. **Update local database** to mark as cancelled/voided
4. **Create replacement orders** with correct numbers if needed

### Step 5: Recreate Orders with Correct Numbers
Starting from 100527:

```bash
# Use create_corrected_orders.py or manual ShipStation upload
# Ensure correct order numbers: 100527, 100528, 100529, 100530, 100531, 100532
```

### Step 6: Verify & Re-enable Workflows
```bash
# Verify no duplicates
python utils/identify_shipstation_duplicates.py --mode summary

# Re-enable workflows
# Via workflow_controls.html
```

## Safety Checklist
- [ ] Backup created and verified
- [ ] Workflows disabled before changes
- [ ] Awaiting orders cancelled successfully (100521-100524)
- [ ] Shipped orders handled manually (100525-100526)
- [ ] New orders created with correct numbers (100527+)
- [ ] Local database updated
- [ ] Workflows re-enabled
- [ ] System monitored for 24 hours

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Shipped orders can't be deleted | High | Manual void + recreate |
| Wrong order cancelled | High | Backup restoration |
| Duplicate recreation | Medium | Verification step |


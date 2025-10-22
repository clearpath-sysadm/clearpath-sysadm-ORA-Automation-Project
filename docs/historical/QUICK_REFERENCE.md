# Quick Reference: ShipStation Duplicate Cleanup

## TL;DR - Quick Start

### 1. Identify Duplicates (READ-ONLY, SAFE)
```bash
python utils/identify_shipstation_duplicates.py --mode both
```
This will show duplicates on screen AND save a CSV report to `reports/`.

### 2. Create Backup (RECOMMENDED)
```bash
python utils/backup_shipstation_data.py
```
Creates backup in `backups/shipstation_backup_YYYYMMDD.json`

### 3. Test Cleanup Plan (DRY-RUN, NO CHANGES)
```bash
python utils/cleanup_shipstation_duplicates.py --dry-run
```
Shows what WOULD be deleted without actually deleting anything.

### 4. Execute Cleanup (DESTRUCTIVE)
```bash
# Disable workflows first!
# Then run:
python utils/cleanup_shipstation_duplicates.py --execute
```
This WILL delete duplicate orders from ShipStation.

---

## Before You Start

### ✅ Pre-Cleanup Checklist
1. **Create Backup**: Run `utils/backup_shipstation_data.py`
2. **Disable Workflows**: Go to `workflow_controls.html` and turn OFF:
   - `shipstation-upload`
   - `status-sync`
   - `manual-order-sync`
3. **Review Duplicate Report**: Check `reports/shipstation_duplicates_*.csv`
4. **Notify Team**: Let others know you're doing maintenance

---

## Available Commands

### Identify Duplicates
```bash
# Console summary only:
python utils/identify_shipstation_duplicates.py --mode summary

# CSV report only:
python utils/identify_shipstation_duplicates.py --mode report

# Both console + CSV (recommended):
python utils/identify_shipstation_duplicates.py --mode both

# Look back 90 days instead of default 180:
python utils/identify_shipstation_duplicates.py --mode both --days-back 90
```

**Output Locations**:
- Console: Printed to screen
- Report: `reports/shipstation_duplicates_YYYYMMDD_HHMMSS.csv`

---

### Create Backup
```bash
# Standard backup (180 days):
python utils/backup_shipstation_data.py

# Backup last 90 days only:
python utils/backup_shipstation_data.py --days-back 90

# Save to custom directory:
python utils/backup_shipstation_data.py --output-dir my_backups
```

**Output Location**: `backups/shipstation_backup_YYYYMMDD_HHMMSS.json`

---

### Cleanup Duplicates

#### Dry-Run (Safe Testing)
```bash
# Test cleanup plan (shows what would happen):
python utils/cleanup_shipstation_duplicates.py --dry-run

# Test with different lookback period:
python utils/cleanup_shipstation_duplicates.py --dry-run --days-back 90
```

#### Execute Cleanup (Destructive)
```bash
# Interactive cleanup (prompts for each batch):
python utils/cleanup_shipstation_duplicates.py --execute

# Auto-confirm all batches (no prompts):
python utils/cleanup_shipstation_duplicates.py --execute --confirm

# Process 5 orders per batch (default is 10):
python utils/cleanup_shipstation_duplicates.py --execute --batch-size 5

# Wait 5 seconds between batches (default is 2):
python utils/cleanup_shipstation_duplicates.py --execute --batch-delay 5
```

**Output Locations**:
- Success/Failure Summary: Printed to console
- Error Log: `logs/cleanup_errors_YYYYMMDD_HHMMSS.log`

---

## Understanding the Cleanup Strategy

### What Gets KEPT vs DELETED

#### Priority 1: Active Lot Number
If order has SKU with **active lot** (from `sku_lot` table), KEEP that version.

**Example**:
- Order `689755` with `17612 - 250300` ✅ **KEEP** (lot 250300 is active)
- Order `689755` with `17612 - 250237` ❌ **DELETE** (old lot)

#### Priority 2: Earliest Created
If no active lot match, KEEP the **earliest uploaded** order.

**Example**:
- Order `689755` created 2025-10-01 10:00 ✅ **KEEP** (first)
- Order `689755` created 2025-10-01 10:05 ❌ **DELETE** (duplicate)

#### Protection: Shipped Orders
**CANNOT delete shipped orders** (ShipStation API restriction).
- Status: `shipped` → SKIP (manual review needed)
- Status: `cancelled` → SKIP (already handled)

---

## Common Scenarios

### Scenario 1: Same Order, Different Lots
**Problem**: Order uploaded twice with different lot numbers

**Example Duplicate**:
```
Order: 689755 | SKU: 17612 | Count: 2
  ✓ [1] 17612 - 250300 | ID: 123456 | Created: 2025-10-13 14:43
  ✗ [2] 17612 - 250237 | ID: 123457 | Created: 2025-10-13 14:44
```

**Action**: Delete order with incorrect lot (250237)

---

### Scenario 2: Same Order, Same Lot
**Problem**: Order uploaded multiple times with same SKU/lot

**Example Duplicate**:
```
Order: 689765 | SKU: 17612 | Count: 3
  ✓ [1] 17612 - 250300 | ID: 234567 | Created: 2025-10-13 10:00
  ✗ [2] 17612 - 250300 | ID: 234568 | Created: 2025-10-13 10:05
  ✗ [3] 17612 - 250300 | ID: 234569 | Created: 2025-10-13 10:10
```

**Action**: Delete duplicates #2 and #3 (keep earliest)

---

### Scenario 3: Shipped Duplicate
**Problem**: Duplicate order but one already shipped

**Example**:
```
Order: 689770 | SKU: 17612 | Count: 2
  ✓ [1] 17612 - 250300 | Status: shipped | Created: 2025-10-10
  ⚠️ [2] 17612 - 250300 | Status: awaiting_shipment | Created: 2025-10-13
```

**Action**: Script CANNOT delete shipped orders. Manual review needed.

---

## After Cleanup

### Verify Success
```bash
# Run duplicate detection again:
python utils/identify_shipstation_duplicates.py --mode summary
```

Should show: **"✅ NO DUPLICATES FOUND"**

### Re-Enable Workflows
1. Go to `workflow_controls.html`
2. Turn ON:
   - `shipstation-upload`
   - `status-sync`
   - `manual-order-sync`

### Monitor for 24 Hours
- Check logs for new duplicates
- Verify new uploads use correct lot numbers

---

## Troubleshooting

### Problem: "API rate limit exceeded"
**Solution**:
```bash
python utils/cleanup_shipstation_duplicates.py --execute --batch-delay 5
```
Increases delay between batches from 2s to 5s.

---

### Problem: "Failed to delete order: HTTP 400"
**Cause**: Order might be shipped or locked

**Solution**: Check error log:
```bash
cat logs/cleanup_errors_YYYYMMDD_HHMMSS.log
```
Manually review and handle those orders in ShipStation UI.

---

### Problem: Script hangs during execution
**Solution**:
1. Press `Ctrl+C` to kill
2. Check partial cleanup in ShipStation
3. Re-run identification: `python utils/identify_shipstation_duplicates.py --mode summary`
4. Re-run cleanup if needed

---

### Problem: Accidentally deleted wrong order
**Solution**: Restore from backup
1. Locate backup: `backups/shipstation_backup_YYYYMMDD.json`
2. Find deleted order in backup JSON
3. Manually re-create in ShipStation UI (or contact ShipStation support)

---

## Safety Features

✅ **Built-in Safeguards**:
1. **Dry-Run Default**: Must use `--execute` flag to delete
2. **Batch Processing**: Processes in small batches (default 10)
3. **Manual Confirmation**: Prompts before each batch (unless `--confirm`)
4. **Error Handling**: Continues on errors, logs all failures
5. **Shipped Order Protection**: Cannot delete shipped orders

❌ **No Undo**: Once deleted, orders must be restored from backup

---

## File Locations Summary

| File Type | Location | Created By |
|-----------|----------|------------|
| Duplicate Report (CSV) | `reports/shipstation_duplicates_*.csv` | identify script |
| Backup (JSON) | `backups/shipstation_backup_*.json` | backup script |
| Error Log | `logs/cleanup_errors_*.log` | cleanup script |
| Workflow Controls | `workflow_controls.html` | Manual access |

---

## Full Documentation
For detailed process, see: [Remediation Plan](REMEDIATION_PLAN.md)

---

**Last Updated**: October 13, 2025  
**Version**: 1.0

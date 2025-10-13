# ShipStation Duplicate Remediation Plan

## Overview
This document provides a comprehensive process to identify and clean up duplicate orders in ShipStation that were created before the duplicate detection fix was implemented.

## Problem Statement
Due to the previous duplicate detection logic checking only `order_number` (not `order_number + SKU`), the same order with different lot numbers created multiple ShipStation orders:
- **Example**: Order `689755` with SKU `17612 - 250237` AND `17612 - 250300` created 2 separate ShipStation orders

## Remediation Strategy

### Phase 1: Identification (READ-ONLY)
**Objective**: Safely identify all duplicates without making any changes

1. **Run Duplicate Detection Utility**
   ```bash
   python utils/identify_shipstation_duplicates.py --mode report
   ```
   
2. **Review Output**
   - CSV report: `reports/shipstation_duplicates_YYYYMMDD.csv`
   - Console summary with counts and affected order numbers
   - Grouped by: (order_number, base_SKU) with all ShipStation Order IDs

3. **Categorize Duplicates**
   - **Type A**: Same order, same base SKU, different lot numbers (MOST COMMON)
   - **Type B**: Same order, multiple SKU submissions (rare)
   - **Type C**: Test orders (safe to delete)

### Phase 2: Strategy Selection

#### For Type A (Same Order, Different Lots)
**Decision Criteria**: Keep the order with the CORRECT lot number (active in `sku_lot` table)

**Process**:
1. Check `sku_lot` table for current active lot:
   ```sql
   SELECT sku, lot FROM sku_lot WHERE active = 1;
   ```
2. Keep ShipStation order matching active lot
3. Delete/cancel orders with incorrect lot numbers

#### For Type B (Multiple Submissions)
**Decision Criteria**: Keep the FIRST uploaded order (earliest `createDate`)

**Process**:
1. Sort by `createDate` ascending
2. Keep earliest order
3. Delete subsequent duplicates

#### For Type C (Test Orders)
**Decision Criteria**: Delete all if not shipped

### Phase 3: Dry-Run Validation
**Objective**: Validate cleanup actions before execution

1. **Run in DRY-RUN Mode**
   ```bash
   python utils/cleanup_shipstation_duplicates.py --dry-run
   ```

2. **Review Planned Actions**
   - Orders to KEEP (with reasons)
   - Orders to DELETE (with reasons)
   - Orders to CANCEL (if already shipped)

3. **Export Action Plan**
   - CSV: `reports/cleanup_plan_YYYYMMDD.csv`
   - Contains: order_number, sku, shipstation_id, action, reason

### Phase 4: Execution (DESTRUCTIVE)
**Objective**: Execute cleanup with safety controls

#### Pre-Execution Checklist
- [ ] Backup created: `python utils/backup_shipstation_data.py`
- [ ] Dry-run reviewed and approved
- [ ] Production workflows DISABLED (prevent new uploads during cleanup)
- [ ] Team notified of maintenance window

#### Execution Steps

1. **Disable Workflows** (CRITICAL)
   ```sql
   -- Via workflow_controls.html UI or SQL:
   UPDATE workflow_controls SET enabled = FALSE WHERE name IN (
       'shipstation-upload',
       'status-sync',
       'manual-order-sync'
   );
   ```

2. **Run Cleanup Script**
   ```bash
   python utils/cleanup_shipstation_duplicates.py --execute --batch-size 10
   ```
   
   Options:
   - `--execute`: Actually perform deletions (without this, dry-run only)
   - `--batch-size N`: Process N orders at a time (default: 10)
   - `--confirm`: Skip manual confirmation prompts

3. **Monitor Progress**
   - Progress bar shows: Processed X / Total Y
   - Real-time logs: `logs/cleanup_YYYYMMDD.log`
   - Errors logged separately: `logs/cleanup_errors_YYYYMMDD.log`

4. **Handle Shipped Orders**
   - **Cannot delete shipped orders** (ShipStation API restriction)
   - Script will SKIP and log these
   - Manual review required for shipped duplicates

### Phase 5: Verification
**Objective**: Confirm successful cleanup

1. **Run Duplicate Detection Again**
   ```bash
   python utils/identify_shipstation_duplicates.py --mode report
   ```
   Should show: "No duplicates found"

2. **Check Local Database**
   ```bash
   python -c "from src.services.shipping_validator import detect_duplicate_order_sku; print(detect_duplicate_order_sku())"
   ```

3. **Verify Orders in ShipStation UI**
   - Spot-check 5-10 previously duplicate orders
   - Confirm only correct lot numbers remain

### Phase 6: Re-Enable Workflows
**Objective**: Resume normal operations

1. **Re-enable Workflows**
   ```sql
   UPDATE workflow_controls SET enabled = TRUE WHERE name IN (
       'shipstation-upload',
       'status-sync',
       'manual-order-sync'
   );
   ```
   
   Or via UI: workflow_controls.html

2. **Monitor for 24 Hours**
   - Check logs for new duplicates
   - Verify new uploads use correct lot numbers

## Safety Controls

### Built-in Safeguards
1. **Dry-Run Default**: Script requires `--execute` flag for destructive actions
2. **Batch Processing**: Processes in small batches (default 10) to prevent API rate limits
3. **Manual Confirmation**: Prompts before each batch (unless `--confirm` flag used)
4. **Error Handling**: Continues on errors, logs all failures
5. **Shipped Order Protection**: Cannot delete shipped orders (API restriction)

### Rollback Plan
If cleanup causes issues:

1. **Stop Immediately**
   ```bash
   Ctrl+C to kill cleanup script
   ```

2. **Restore from Backup** (if orders were incorrectly deleted)
   - Backup location: `backups/shipstation_backup_YYYYMMDD.json`
   - Use ShipStation API to re-create orders from backup

3. **Report Issue**
   - Check error logs: `logs/cleanup_errors_YYYYMMDD.log`
   - Review action plan: `reports/cleanup_plan_YYYYMMDD.csv`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Delete wrong order | Low | High | Dry-run validation, manual review |
| API rate limit | Medium | Low | Batch processing with delays |
| Network failure | Medium | Low | Retry logic, resume capability |
| Shipped order deletion | None | N/A | API prevents this |
| New duplicates during cleanup | Low | Low | Disable workflows first |

## Timeline Estimate

| Phase | Duration | Notes |
|-------|----------|-------|
| Identification | 10-15 min | Depends on order volume |
| Strategy Selection | 15-30 min | Manual review required |
| Dry-Run Validation | 5-10 min | Automated |
| Execution | 20-40 min | ~10 orders/min with API delays |
| Verification | 10-15 min | Automated + spot checks |
| **Total** | **60-120 min** | 1-2 hour maintenance window |

## Post-Remediation

### Ongoing Monitoring
1. **Automated Duplicate Detection**: Already runs after each upload
2. **Weekly Reports**: Check for any new duplicates
3. **Dashboard Alerts**: Yellow banner shows violation count

### Prevention
✅ **Already Implemented**:
- Duplicate detection fix using (order_number + base_SKU)
- Post-upload validation with `detect_duplicate_order_sku()`
- Workflow controls to prevent dev/prod conflicts

## Support

### Troubleshooting
**Problem**: Script fails with "API rate limit exceeded"
**Solution**: Increase batch delay: `--batch-delay 5` (5 seconds between batches)

**Problem**: Script hangs during execution
**Solution**: Kill with Ctrl+C, resume with `--resume-from <order_number>`

**Problem**: Cleanup deleted wrong order
**Solution**: Restore from backup using `utils/restore_shipstation_backup.py`

### Contact
- Documentation: `docs/manuals/WORKFLOW_CONTROLS_USER_MANUAL.md`
- Duplicate Detection: `docs/DUPLICATE_DETECTION_FIX_PLAN.md`
- System Architecture: `replit.md`

---

**Document Version**: 1.0  
**Last Updated**: October 13, 2025  
**Author**: ORA Automation System

# SQLite to PostgreSQL Remediation Plan

**Date:** October 15, 2025  
**Status:** 🔴 CRITICAL - Multiple production workflows affected  
**Root Cause:** Incomplete migration from SQLite to PostgreSQL

---

## Executive Summary

The October 2025 database migration from SQLite to PostgreSQL left **9 critical files** with SQLite syntax that fails silently on PostgreSQL. This is causing:
- ❌ Incorrect order quantities uploaded to ShipStation
- ❌ Missing inventory data
- ❌ Workflow failures across multiple services

**Impact:** Order 690045 uploaded with qty 17 instead of 40 due to failed item query (SQLite `?` placeholder rejected by PostgreSQL).

---

## Critical Issues Found

### 🔴 Priority 1: Active Production Workflows (IMMEDIATE FIX REQUIRED)

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **src/scheduled_shipstation_upload.py** | SQLite `?` placeholders + wrong import | Orders upload with wrong quantities | 168, 308, 381, 391, 440, 445, 446, 461 + line 20 |
| **src/shipstation_status_sync.py** | SQLite `?` placeholders + wrong import | Status updates fail silently | 15 locations + import |
| **src/scheduled_cleanup.py** | Wrong import (`db_utils` vs `pg_utils`) | Workflow control checks fail | Line 19 |
| **src/unified_shipstation_sync.py** | ✅ Already fixed | Working correctly | - |
| **src/scheduled_xml_import.py** | ✅ Already fixed | Working correctly | - |

### 🟡 Priority 2: Supporting Services

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **src/weekly_reporter.py** | SQLite `?` placeholders + wrong import | Weekly inventory reports fail | Line 216 + import |
| **src/services/shipping_validator.py** | SQLite `?` placeholders + wrong import | Shipping validation fails | 10 locations + import |
| **src/daily_shipment_processor.py** | SQLite `?` placeholders + wrong import | Daily processing fails | 5 locations + import |

### 🟢 Priority 3: Utility Scripts

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **src/backfill_shipstation_ids.py** | SQLite `?` placeholders + wrong import | Backfill operations fail | 4 locations + import |
| **src/services/data_processing/sku_lot_parser.py** | `cursor.lastrowid` (SQLite only) | Lot creation fails | Line 186 |
| **src/services/shipstation/metrics_refresher.py** | Wrong import | Metrics refresh fails | Import line |

---

## Remediation Steps

### Step 1: Fix Critical Production Workflows (30 minutes)

**A. Fix `scheduled_shipstation_upload.py`:**
```python
# Line 20: Change import
from src.services.database.pg_utils import get_connection, transaction_with_retry, is_workflow_enabled, update_workflow_last_run

# Lines 168, 308, 381, 391, 440, 445, 446, 461: Change ? to %s
# Example:
WHERE order_inbox_id = %s    # was: WHERE order_inbox_id = ?
```

**B. Fix `shipstation_status_sync.py`:**
```python
# Change import from db_utils to pg_utils
# Replace all ? with %s (15 locations)
```

**C. Fix `scheduled_cleanup.py`:**
```python
# Change import from db_utils to pg_utils
```

### Step 2: Fix Supporting Services (20 minutes)

**D. Fix `weekly_reporter.py`:**
```python
# Change import from db_utils to pg_utils
# Line 216: VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP) → VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
```

**E. Fix `shipping_validator.py`:**
```python
# Change import from db_utils to pg_utils
# Replace all ? with %s (10 locations)
```

**F. Fix `daily_shipment_processor.py`:**
```python
# Change import from db_utils to pg_utils
# Replace all ? with %s (5 locations)
```

### Step 3: Fix Utility Scripts (15 minutes)

**G. Fix `backfill_shipstation_ids.py`:**
```python
# Change import from db_utils to pg_utils
# Replace all ? with %s (4 locations)
```

**H. Fix `sku_lot_parser.py`:**
```python
# Line 186: Replace cursor.lastrowid with RETURNING id
cursor.execute("""
    INSERT INTO lots (sku_id, lot_number, status)
    VALUES (%s, %s, 'active')
    RETURNING id
""", (sku_id, lot_number))
new_lot_id = cursor.fetchone()[0]
```

**I. Fix `metrics_refresher.py`:**
```python
# Change import from db_utils to pg_utils
```

---

## Testing Strategy

### 1. Unit Testing (Per File)
```bash
# Test each fixed file
python -c "import src.scheduled_shipstation_upload; print('✅ Import OK')"
```

### 2. Integration Testing (Critical Path)
```bash
# Test full order flow
1. Import XML order (scheduled_xml_import.py)
2. Upload to ShipStation (scheduled_shipstation_upload.py)
3. Sync status (unified_shipstation_sync.py)
4. Verify quantities match
```

### 3. Regression Testing
- Compare order quantities: Database vs ShipStation
- Verify bundle expansion works correctly
- Check consolidation logic preserves quantities

---

## Verification Checklist

After fixes, verify:
- [ ] All `?` placeholders replaced with `%s`
- [ ] All imports use `pg_utils` instead of `db_utils`
- [ ] All `cursor.lastrowid` replaced with `RETURNING id`
- [ ] Orders upload with correct quantities
- [ ] Workflow controls work (enable/disable)
- [ ] Status sync updates correctly
- [ ] Weekly reports generate successfully

---

## Rollback Plan

If issues arise:
1. Disable affected workflows via Workflow Controls UI
2. Revert to previous commit: `git log --oneline | head -20`
3. Re-enable workflows after verification

---

## Long-Term Improvements

1. **Create PostgreSQL Test Suite:** Prevent future SQLite syntax from merging
2. **Deprecate `db_utils.py`:** Remove SQLite adapter entirely
3. **Add CI/CD Checks:** Fail builds on `?` placeholders or `db_utils` imports
4. **Database Query Audit:** Review all raw SQL for PostgreSQL compatibility

---

## Estimated Timeline

| Priority | Task | Time | Owner |
|----------|------|------|-------|
| P1 | Fix shipstation-upload | 15 min | Dev |
| P1 | Fix status sync | 10 min | Dev |
| P1 | Fix cleanup workflow | 5 min | Dev |
| P2 | Fix supporting services | 20 min | Dev |
| P3 | Fix utility scripts | 15 min | Dev |
| - | **Testing & Verification** | 30 min | Dev |
| - | **TOTAL** | ~95 min | - |

---

## Success Criteria

✅ **All workflows run without errors**  
✅ **Order quantities match: Database = ShipStation**  
✅ **No `?` placeholders in production code**  
✅ **All imports use `pg_utils`**  
✅ **Zero data loss incidents**

---

## Notes

- **Order 690045 Case Study:** Bundle 18225 (qty 1) should expand to 40x SKU 17612. Database shows 40 ✅, but ShipStation shows 17 ❌ due to failed item query on line 168.
- **Silent Failures:** PostgreSQL rejects `?` placeholders without error logging, causing partial data operations.
- **Migration Lessons:** Always test ALL code paths after database engine changes.

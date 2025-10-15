# SQLite to PostgreSQL Remediation Plan

**Date:** October 15, 2025  
**Status:** 🔴 CRITICAL - Dashboard and multiple production workflows affected  
**Root Cause:** Incomplete migration from SQLite to PostgreSQL

---

## Executive Summary

The October 2025 database migration from SQLite to PostgreSQL left **15 critical files** with SQLite syntax that fails silently on PostgreSQL. This is causing:
- ❌ **Dashboard completely broken** - Users see empty/error UI (app.py)
- ❌ **Incorrect order quantities uploaded to ShipStation** (Order 690045: 40 in DB vs 17 in ShipStation)
- ❌ **Stale metrics** - Units-to-ship showing wrong data (hardcoded SQLite connection)
- ❌ **Workflow failures** across multiple services

**Impact:** Production system partially non-functional. Dashboard APIs failing, order quantities wrong, automation workflows broken.

---

## Critical Issues Found

### 🔴 Priority 0: URGENT - User-Facing Systems (IMMEDIATE FIX REQUIRED)

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **app.py** | Wrong import (`db_utils` vs `pg_utils`) | **All dashboard APIs fail → Users see broken UI** | Line 16 |
| **src/shipstation_units_refresher.py** | Hardcoded `sqlite3.connect('ora.db')` + `?` placeholders | **Metrics always stale → Wrong FedEx alerts** | Lines 9, 53, 57 |

### 🔴 Priority 1: Active Production Workflows (IMMEDIATE FIX REQUIRED)

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **src/scheduled_shipstation_upload.py** | SQLite `?` placeholders + wrong import | Orders upload with wrong quantities | 168, 308, 381, 391, 440, 445, 446, 461 + line 20 |
| **src/shipstation_status_sync.py** | SQLite `?` placeholders + wrong import | Status updates fail silently | 15 locations + import |
| **src/scheduled_cleanup.py** | Wrong import (`db_utils` vs `pg_utils`) | Workflow control checks fail | Line 19 |

### 🟡 Priority 2: Supporting Services

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **src/cleanup_old_orders.py** | SQLite `?` placeholders + wrong import | Order cleanup fails → DB bloat | Lines 21, 47, 66, 75, 82 |
| **src/weekly_reporter.py** | SQLite `?` placeholders + wrong import | Weekly inventory reports fail | Line 216 + line 13 |
| **src/services/shipping_validator.py** | SQLite `?` placeholders + wrong import | Shipping validation fails | 10 locations + line 32 |
| **src/daily_shipment_processor.py** | SQLite `?` placeholders + wrong import | Daily processing fails | 6 locations + line 30 |

### 🟢 Priority 3: Utility Scripts

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **src/backfill_shipstation_ids.py** | SQLite `?` placeholders + wrong import | Backfill operations fail | 4 locations + line 21 |
| **src/services/data_processing/sku_lot_parser.py** | `cursor.lastrowid` (SQLite only) | Lot creation fails | Line 186 |
| **src/services/shipstation/metrics_refresher.py** | Wrong import | Metrics refresh fails | Line 9 |
| **utils/cleanup_shipstation_duplicates.py** | Wrong import | Manual cleanup tool fails | Line 31 |
| **utils/backfill_september_shipments.py** | Wrong import | Historical backfill fails | Import line |
| **utils/sync_awaiting_shipment.py** | Wrong import | Manual sync tool fails | Import line |

### ✅ Already Fixed (Using Smart Adapter)

| File | Status | Notes |
|------|--------|-------|
| **src/unified_shipstation_sync.py** | ✅ Working | Uses `%s` placeholders, imports from db_adapter |
| **src/scheduled_xml_import.py** | ✅ Working | Uses `%s` placeholders, imports from db_adapter |

### 📦 Deprecated (To Delete)

| File | Status | Replacement |
|------|--------|-------------|
| **src/manual_shipstation_sync.py** | Deprecated | Replaced by unified_shipstation_sync.py |

---

## Exact Code Fixes

### 🔴 Priority 0: URGENT - User-Facing Systems

#### **File: app.py**

**Fix 1 - Import Statement (Line 16):**
```python
# BEFORE:
from src.services.database.db_utils import get_connection, execute_query

# AFTER:
from src.services.database.pg_utils import get_connection, execute_query
```

**Impact:** This single fix enables ALL dashboard API endpoints to work with PostgreSQL.

---

#### **File: src/shipstation_units_refresher.py**

This file requires **COMPLETE REWRITE** - it's hardcoded to SQLite and bypasses all adapters.

**Fix 1 - Remove SQLite import (Line 9):**
```python
# BEFORE:
import sqlite3

# AFTER:
# (remove this line entirely)
```

**Fix 2 - Add PostgreSQL adapter import (After line 8):**
```python
# ADD NEW LINE:
from src.services.database.pg_utils import get_connection
```

**Fix 3 - Replace connection and query (Lines 53-62):**
```python
# BEFORE:
            # Update database
            conn = sqlite3.connect('ora.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO shipstation_metrics (metric_name, metric_value, last_updated)
                VALUES ('units_to_ship', ?, datetime('now'))
            """, (total_units,))
            
            conn.commit()
            conn.close()

# AFTER:
            # Update database
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO shipstation_metrics (metric_name, metric_value, last_updated)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (metric_name) 
                DO UPDATE SET metric_value = EXCLUDED.metric_value, last_updated = CURRENT_TIMESTAMP
            """, ('units_to_ship', total_units))
            
            conn.commit()
            conn.close()
```

**Changes:**
1. Remove `import sqlite3`
2. Add `from src.services.database.pg_utils import get_connection`
3. Replace `sqlite3.connect('ora.db')` with `get_connection()`
4. Replace `INSERT OR REPLACE` with PostgreSQL `INSERT ... ON CONFLICT`
5. Replace `?` with `%s`
6. Replace `datetime('now')` with `CURRENT_TIMESTAMP`

---

### 🔴 Priority 1: Critical Production Workflows

#### **File: src/scheduled_shipstation_upload.py**

**Fix 1 - Import Statement (Line 20):**
```python
# BEFORE:
from src.services.database.db_utils import get_connection, transaction_with_retry, is_workflow_enabled, update_workflow_last_run

# AFTER:
from src.services.database.pg_utils import get_connection, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
```

**Fix 2 - Line 168:**
```python
# BEFORE:
                WHERE order_inbox_id = ?

# AFTER:
                WHERE order_inbox_id = %s
```

**Fix 3 - Line 308:**
```python
# BEFORE:
                WHERE failure_reason = ?

# AFTER:
                WHERE failure_reason = %s
```

**Fix 4 - Line 381:**
```python
# BEFORE:
                            VALUES (?, ?, ?)

# AFTER:
                            VALUES (%s, %s, %s)
```

**Fix 5 - Line 391:**
```python
# BEFORE:
                        WHERE id = ?

# AFTER:
                        WHERE id = %s
```

**Fix 6 - Line 440:**
```python
# BEFORE:
                            VALUES (?, ?, ?)

# AFTER:
                            VALUES (%s, %s, %s)
```

**Fix 7 - Lines 445-446:**
```python
# BEFORE:
                        SET shipstation_order_id = ?
                        WHERE id = ? AND (shipstation_order_id IS NULL OR shipstation_order_id = '')

# AFTER:
                        SET shipstation_order_id = %s
                        WHERE id = %s AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
```

**Fix 8 - Line 461:**
```python
# BEFORE:
                        WHERE id = ?

# AFTER:
                        WHERE id = %s
```

---

#### **File: src/shipstation_status_sync.py**

**Fix 1 - Import Statement:**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction, transaction_with_retry, is_workflow_enabled, update_workflow_last_run

# AFTER:
from src.services.database.pg_utils import execute_query, transaction, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
```

**Fix 2 - Line 209:**
```python
# BEFORE:
                WHERE id = ?

# AFTER:
                WHERE id = %s
```

**Fix 3 - Line 225:**
```python
# BEFORE:
                WHERE id = ?

# AFTER:
                WHERE id = %s
```

**Fix 4 - Line 241:**
```python
# BEFORE:
                WHERE id = ?

# AFTER:
                WHERE id = %s
```

**Fix 5 - Lines 250-257:**
```python
# BEFORE:
                SET status = ?,
                    shipstation_order_id = ?,
                    shipstation_shipment_id = ?,
                    tracking_number = ?,
                    carrier_code = ?,
                    service_code = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?

# AFTER:
                SET status = %s,
                    shipstation_order_id = %s,
                    shipstation_shipment_id = %s,
                    tracking_number = %s,
                    carrier_code = %s,
                    service_code = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
```

**Fix 6 - Line 323:**
```python
# BEFORE:
            SELECT id FROM orders_inbox WHERE order_number = ?

# AFTER:
            SELECT id FROM orders_inbox WHERE order_number = %s
```

**Fix 7 - Lines 330-337:**
```python
# BEFORE:
                SET status = ?,
                    shipstation_order_id = ?,
                    shipstation_shipment_id = ?,
                    tracking_number = ?,
                    carrier_code = ?,
                    service_code = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_number = ?

# AFTER:
                SET status = %s,
                    shipstation_order_id = %s,
                    shipstation_shipment_id = %s,
                    tracking_number = %s,
                    carrier_code = %s,
                    service_code = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_number = %s
```

**Fix 8 - Lines 379, 396, 413:**
```python
# BEFORE (Line 379):
            WHERE id = ?

# BEFORE (Line 396):
            WHERE id = ?

# BEFORE (Line 413):
            WHERE id = ?

# AFTER (All three):
            WHERE id = %s
```

**Fix 9 - Lines 424-431:**
```python
# BEFORE:
                SET status = ?,
                    shipstation_order_id = ?,
                    shipstation_shipment_id = ?,
                    tracking_number = ?,
                    carrier_code = ?,
                    service_code = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?

# AFTER:
                SET status = %s,
                    shipstation_order_id = %s,
                    shipstation_shipment_id = %s,
                    tracking_number = %s,
                    carrier_code = %s,
                    service_code = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
```

---

#### **File: src/scheduled_cleanup.py**

**Fix - Import Statement (Line 19):**
```python
# BEFORE:
from src.services.database.db_utils import is_workflow_enabled, update_workflow_last_run

# AFTER:
from src.services.database.pg_utils import is_workflow_enabled, update_workflow_last_run
```

---

### 🟡 Priority 2: Supporting Services

#### **File: src/cleanup_old_orders.py**

**Fix 1 - Import Statement (Line 21):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Line 47:**
```python
# BEFORE:
                WHERE DATE(order_date) < ?

# AFTER:
                WHERE DATE(order_date) < %s
```

**Fix 3 - Line 66:**
```python
# BEFORE:
                    WHERE DATE(order_date) < ?

# AFTER:
                    WHERE DATE(order_date) < %s
```

**Fix 4 - Line 75:**
```python
# BEFORE:
                    WHERE DATE(order_date) < ?

# AFTER:
                    WHERE DATE(order_date) < %s
```

**Fix 5 - Line 82:**
```python
# BEFORE:
                WHERE DATE(order_date) < ?

# AFTER:
                WHERE DATE(order_date) < %s
```

---

#### **File: src/weekly_reporter.py**

**Fix 1 - Import Statement (Line 13):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, upsert, transaction, is_workflow_enabled, update_workflow_last_run

# AFTER:
from src.services.database.pg_utils import execute_query, upsert, transaction, is_workflow_enabled, update_workflow_last_run
```

**Fix 2 - Line 216:**
```python
# BEFORE:
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

# AFTER:
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
```

---

#### **File: src/services/shipping_validator.py**

**Fix 1 - Import Statement (Line 32):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Line 205:**
```python
# BEFORE:
                WHERE order_id = ?

# AFTER:
                WHERE order_id = %s
```

**Fix 3 - Line 235:**
```python
# BEFORE:
                WHERE order_id = ? AND violation_type = ?

# AFTER:
                WHERE order_id = %s AND violation_type = %s
```

**Fix 4 - Lines 246-248:**
```python
# BEFORE:
                        SET expected_value = ?,
                            actual_value = ?
                        WHERE id = ?

# AFTER:
                        SET expected_value = %s,
                            actual_value = %s
                        WHERE id = %s
```

**Fix 5 - Line 259:**
```python
# BEFORE:
                        WHERE id = ?

# AFTER:
                        WHERE id = %s
```

**Fix 6 - Line 269:**
```python
# BEFORE:
                    VALUES (?, ?, ?, ?, ?, 0)

# AFTER:
                    VALUES (%s, %s, %s, %s, %s, 0)
```

**Fix 7 - Line 329:**
```python
# BEFORE:
                            WHERE order_id = ?

# AFTER:
                            WHERE order_id = %s
```

**Fix 8 - Line 391:**
```python
# BEFORE:
                        WHERE order_id = ?

# AFTER:
                        WHERE order_id = %s
```

---

#### **File: src/daily_shipment_processor.py**

**Fix 1 - Import Statement (Line 30):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Line 264:**
```python
# BEFORE:
                VALUES (?, ?, ?)

# AFTER:
                VALUES (%s, %s, %s)
```

**Fix 3 - Line 309:**
```python
# BEFORE:
                ) VALUES (?, ?, ?, ?, ?, ?)

# AFTER:
                ) VALUES (%s, %s, %s, %s, %s, %s)
```

**Fix 4 - Line 352:**
```python
# BEFORE:
                        ) VALUES (?, ?, ?, ?)

# AFTER:
                        ) VALUES (%s, %s, %s, %s)
```

**Fix 5 - Line 373:**
```python
# BEFORE:
        """.format(','.join('?' * len(target_skus))), tuple(target_skus))

# AFTER:
        """.format(','.join('%s' * len(target_skus))), tuple(target_skus))
```

**Fix 6 - Line 514:**
```python
# BEFORE:
                    duration_seconds = CAST(? AS INTEGER)

# AFTER:
                    duration_seconds = CAST(%s AS INTEGER)
```

---

### 🟢 Priority 3: Utility Scripts

#### **File: src/backfill_shipstation_ids.py**

**Fix 1 - Import Statement (Line 21):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Lines 102-104:**
```python
# BEFORE:
                            SET shipstation_order_id = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE order_number = ?

# AFTER:
                            SET shipstation_order_id = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE order_number = %s
```

**Fix 3 - Lines 113-114:**
```python
# BEFORE:
                            SET shipstation_order_id = ?
                            WHERE order_number = ?

# AFTER:
                            SET shipstation_order_id = %s
                            WHERE order_number = %s
```

---

#### **File: src/services/data_processing/sku_lot_parser.py**

**Fix - Lines 183-186:**
```python
# BEFORE:
            VALUES (?, ?, 'active')
        """, (sku_id, lot_number))
        
        new_lot_id = cursor.lastrowid

# AFTER:
            VALUES (%s, %s, 'active')
            RETURNING id
        """, (sku_id, lot_number))
        
        new_lot_id = cursor.fetchone()[0]
```

---

#### **File: src/services/shipstation/metrics_refresher.py**

**Fix - Import Statement (Line 9):**
```python
# BEFORE:
from src.services.database.db_utils import get_connection

# AFTER:
from src.services.database.pg_utils import get_connection
```

---

#### **File: utils/cleanup_shipstation_duplicates.py**

**Fix - Import Statement (Line 31):**
```python
# BEFORE:
from src.services.database.db_utils import get_connection

# AFTER:
from src.services.database.pg_utils import get_connection
```

---

#### **File: utils/backfill_september_shipments.py**

**Fix - Import Statement:**
```python
# BEFORE:
from src.services.database.db_utils import [functions]

# AFTER:
from src.services.database.pg_utils import [functions]
```

---

#### **File: utils/sync_awaiting_shipment.py**

**Fix - Import Statement:**
```python
# BEFORE:
from src.services.database.db_utils import [functions]

# AFTER:
from src.services.database.pg_utils import [functions]
```

---

## Risk Assessment

### **Fix Execution Risk: ✅ LOW**

| Risk Factor | Assessment | Mitigation |
|-------------|------------|------------|
| **Data Loss** | ⭐ None | Read-only syntax changes, no DELETE/DROP operations |
| **Backwards Compatibility** | ⭐ None | PostgreSQL already in use, just fixing broken queries |
| **Rollback Complexity** | ⭐ Low | Simple git revert, or disable workflows via UI |
| **Testing Required** | ⭐ Minimal | Query syntax validation only (no business logic changes) |
| **Deployment Impact** | ⭐ None | No schema changes, no migrations needed |

### **Current Operational Risk: 🔴 HIGH**

**What's broken RIGHT NOW due to unfixed code:**

| Component | Current State | User Impact | Business Impact |
|-----------|---------------|-------------|-----------------|
| **Dashboard (app.py)** | 🔴 All APIs failing | Users see empty/error UI | **No operational visibility** |
| **Units Metric** | 🔴 Stale data | Wrong FedEx pickup alerts | **Shipping delays** |
| **Order Uploads** | 🟡 Partial failure | Some orders upload wrong qty | **Customer complaints** |
| **Status Sync** | 🟡 Partial failure | Order status not updating | **Manual tracking needed** |
| **Cleanup Script** | 🔴 Failing | Orders_inbox fills up | **Database bloat** |

### **Risks Eliminated After Fixes:**

| Fix Priority | Eliminates Risk | Restores Capability |
|--------------|-----------------|---------------------|
| **P0 (2 files)** | Dashboard broken, stale metrics | ✅ Full operational visibility + real-time alerts |
| **P1 (3 files)** | Wrong order quantities uploaded | ✅ Accurate ShipStation orders |
| **P2 (4 files)** | Status sync failures, DB bloat | ✅ Automated workflows |
| **P3 (6 files)** | Manual tools broken | ✅ Admin utilities functional |

---

## Testing Strategy

### 1. P0 Testing (Dashboard & Metrics)
```bash
# Test dashboard loads
curl http://localhost:5000/api/dashboard_stats

# Verify KPIs display
curl http://localhost:5000/api/workflow_status

# Test units refresher
python src/shipstation_units_refresher.py

# Verify metric updates
psql $DATABASE_URL -c "SELECT * FROM shipstation_metrics WHERE metric_name = 'units_to_ship';"
```

### 2. P1 Testing (Production Workflows)
```bash
# Test imports work
python -c "import src.scheduled_shipstation_upload; print('✅ Import OK')"
python -c "import src.shipstation_status_sync; print('✅ Import OK')"
python -c "import src.scheduled_cleanup; print('✅ Import OK')"

# Test full order flow
1. Import XML order (scheduled_xml_import.py)
2. Upload to ShipStation (scheduled_shipstation_upload.py)
3. Sync status (unified_shipstation_sync.py)
4. Verify quantities match: Database = ShipStation
```

### 3. P2/P3 Regression Testing
- Compare order quantities: Database vs ShipStation
- Verify bundle expansion works correctly
- Check consolidation logic preserves quantities
- Test cleanup removes old orders
- Verify weekly reports generate successfully

---

## Verification Checklist

After fixes, verify:
- [ ] All `?` placeholders replaced with `%s`
- [ ] All imports use `pg_utils` instead of `db_utils`
- [ ] All `cursor.lastrowid` replaced with `RETURNING id`
- [ ] No direct `sqlite3.connect()` calls
- [ ] Dashboard displays all KPIs correctly
- [ ] Units-to-ship metric updates every 5 minutes
- [ ] Orders upload with correct quantities
- [ ] Workflow controls work (enable/disable)
- [ ] Status sync updates correctly
- [ ] Weekly reports generate successfully

---

## Execution Timeline

| Priority | Files | Fixes | Time | Cumulative |
|----------|-------|-------|------|------------|
| P0 | 2 files (app.py, units_refresher) | 4 | 15 min | 15 min |
| P1 | 3 files (upload, sync, cleanup) | 26 | 30 min | 45 min |
| P2 | 4 files (cleanup_old, weekly, validator, daily) | 20 | 25 min | 70 min |
| P3 | 6 files (backfill, parser, metrics, utils) | 9 | 20 min | 90 min |
| Testing | All files | - | 30 min | 120 min |
| **TOTAL** | **15 files** | **59 fixes** | **~2 hours** | - |

---

## Rollback Plan

If issues arise:
1. Disable affected workflows via Workflow Controls UI
2. Revert to previous commit: `git log --oneline | head -20`
3. Re-enable workflows after verification

---

## Long-Term Improvements

1. **Delete Deprecated Files:**
   - Remove `src/manual_shipstation_sync.py` (replaced by unified_shipstation_sync.py)
   - Archive old utility scripts if no longer needed

2. **Enforce PostgreSQL-Only Pattern:**
   - **Deprecate `db_utils.py`** entirely - Remove SQLite compatibility
   - Enforce: Use `from src.services.database import` (adapter) or `from src.services.database.pg_utils import` (PostgreSQL)

3. **Prevent Regression:**
   - **Pre-commit hook:** Block commits with `db_utils` imports or `?` placeholders
   - **CI/CD check:** Fail builds if SQLite syntax detected
   - **Code review checklist:** Verify PostgreSQL compatibility

4. **Audit Remaining Code:**
   - Search for any other SQLite patterns: `grep -r "import sqlite3" src/ utils/`
   - Review all raw SQL for PostgreSQL compatibility

---

## Success Criteria

✅ **All workflows run without errors**  
✅ **Dashboard displays all KPIs correctly**  
✅ **Order quantities match: Database = ShipStation**  
✅ **No `?` placeholders in production code**  
✅ **No direct SQLite connections**  
✅ **All imports use `pg_utils` or adapter**  
✅ **Zero data loss incidents**

---

## Files Summary

### **Need Fixing (15 files, 59 fixes):**

**P0 - URGENT (2 files):**
1. app.py - 1 fix
2. src/shipstation_units_refresher.py - 3 fixes

**P1 - Critical (3 files):**
3. src/scheduled_shipstation_upload.py - 9 fixes
4. src/shipstation_status_sync.py - 16 fixes
5. src/scheduled_cleanup.py - 1 fix

**P2 - Important (4 files):**
6. src/cleanup_old_orders.py - 5 fixes
7. src/weekly_reporter.py - 2 fixes
8. src/services/shipping_validator.py - 8 fixes
9. src/daily_shipment_processor.py - 6 fixes

**P3 - Utilities (6 files):**
10. src/backfill_shipstation_ids.py - 3 fixes
11. src/services/data_processing/sku_lot_parser.py - 1 fix
12. src/services/shipstation/metrics_refresher.py - 1 fix
13. utils/cleanup_shipstation_duplicates.py - 1 fix
14. utils/backfill_september_shipments.py - 1 fix
15. utils/sync_awaiting_shipment.py - 1 fix

### **Already Fixed (2 files):**
- ✅ src/unified_shipstation_sync.py
- ✅ src/scheduled_xml_import.py

### **To Delete (1 file):**
- 📦 src/manual_shipstation_sync.py (deprecated)

---

## Notes

- **Order 690045 Case Study:** Bundle 18225 (qty 1) should expand to 40x SKU 17612. Database shows 40 ✅, but ShipStation shows 17 ❌ due to failed item query on line 168 of scheduled_shipstation_upload.py.
- **Silent Failures:** PostgreSQL rejects `?` placeholders without error logging, causing partial data operations.
- **Dashboard Impact:** app.py uses db_utils, so ALL API endpoints fail → users cannot see operational data.
- **Hardcoded SQLite:** shipstation_units_refresher.py bypasses all adapters with `sqlite3.connect('ora.db')` → metrics always stale.
- **Migration Lessons:** Always test ALL code paths after database engine changes. Verify both imports AND query syntax.

---

**Plan Updated:** October 15, 2025  
**Next Action:** Execute P0 fixes immediately to restore dashboard and metrics functionality

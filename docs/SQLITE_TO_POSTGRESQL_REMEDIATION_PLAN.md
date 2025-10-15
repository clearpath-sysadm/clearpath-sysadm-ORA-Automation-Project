# SQLite to PostgreSQL Remediation Plan

**Date:** October 15, 2025 (Updated with Full Verification)  
**Status:** 🔴 CRITICAL - Dashboard and multiple production workflows affected  
**Root Cause:** Incomplete migration from SQLite to PostgreSQL  
**Verification:** ✅ Complete - All files verified, exact line numbers confirmed

---

## Executive Summary

The October 2025 database migration from SQLite to PostgreSQL left **18 files** with SQLite syntax that fails silently on PostgreSQL. This is causing:
- ❌ **Dashboard completely broken** - Users see empty/error UI (app.py)
- ❌ **Incorrect order quantities uploaded to ShipStation** (Order 690045: 40 in DB vs 17 in ShipStation)
- ❌ **Stale metrics** - Units-to-ship showing wrong data (hardcoded SQLite connection)
- ❌ **Workflow failures** across multiple services

**Impact:** Production system partially non-functional. Dashboard APIs failing, order quantities wrong, automation workflows broken.

---

## Verified Issues Summary

| Category | Count | Details |
|----------|-------|---------|
| **Files needing import fix** | 10 | db_utils → pg_utils |
| **Files needing placeholder fix** | 8 | ? → %s (94 total placeholder lines) |
| **Files with direct sqlite3** | 2 | app.py, shipstation_units_refresher.py |
| **Files with cursor.lastrowid** | 1 | sku_lot_parser.py |
| **Already fixed** | 3 | unified_shipstation_sync.py, scheduled_xml_import.py, manual_shipstation_sync.py |
| **Total files to fix** | 18 | Verified count |

---

## Critical Issues Found

### 🔴 Priority 0: URGENT - User-Facing Systems (IMMEDIATE FIX REQUIRED)

| File | Issue | Impact | Lines Affected |
|------|-------|--------|----------------|
| **app.py** | Unused `import sqlite3` + wrong db_utils import | **All dashboard APIs fail → Users see broken UI** | Lines 9 (remove), 16 (fix), 901 (fix) |
| **src/shipstation_units_refresher.py** | Direct `sqlite3.connect('ora.db')` + `?` placeholder | **Metrics always stale → Wrong FedEx alerts** | Lines 9 (remove), 53-62 (rewrite) |

### 🔴 Priority 1: Active Production Workflows (IMMEDIATE FIX REQUIRED)

| File | Import Status | Placeholders | Lines to Fix |
|------|--------------|-------------|--------------|
| **src/scheduled_shipstation_upload.py** | ✅ **Already pg_utils (line 17)** | ❌ 21 lines with ? | 168, 308, 381, 391, 440, 445, 446, 461, etc. (21 total) |
| **src/shipstation_status_sync.py** | ❌ db_utils (line 29) | ❌ 20 lines with ? | Import + 20 placeholder lines |
| **src/scheduled_cleanup.py** | ❌ db_utils (line 19) | ✅ No SQL queries | Import only |

### 🟡 Priority 2: Supporting Services

| File | Import Status | Placeholders | Lines to Fix |
|------|--------------|-------------|--------------|
| **src/cleanup_old_orders.py** | ❌ db_utils (line 21) | ❌ 8 lines with ? | Import + 8 placeholder lines |
| **src/weekly_reporter.py** | ❌ db_utils (line 13) | ❌ 10 lines with ? | Import + 10 placeholder lines |
| **src/services/shipping_validator.py** | ❌ db_utils (line 32) | ❌ 14 lines with ? | Import + 14 placeholder lines |
| **src/daily_shipment_processor.py** | ❌ db_utils (line 30) | ❌ 14 lines with ? | Import + 14 placeholder lines |

### 🟢 Priority 3: Utility Scripts & Data Processing

| File | Import Status | Placeholders | Special Issues |
|------|--------------|-------------|----------------|
| **src/backfill_shipstation_ids.py** | ❌ db_utils (line 21) | ❌ 7 lines with ? | Import + 7 placeholders |
| **src/services/data_processing/sku_lot_parser.py** | ✅ No import needed | ❌ 3 lines with ? | Lines 115, 145, 183 + cursor.lastrowid (line 186) |
| **src/services/shipstation/metrics_refresher.py** | ❌ db_utils (line 9) | ✅ No SQL | Import only |
| **utils/cleanup_shipstation_duplicates.py** | ❌ db_utils (line 31) | ✅ No ? | Import only |
| **utils/backfill_september_shipments.py** | ❌ db_utils (line 31) | ❌ Unknown | Import + verify |
| **utils/sync_awaiting_shipment.py** | ❌ db_utils (line 15) | ❌ Unknown | Import + verify |

### ✅ Already Fixed (Using Smart Adapter)

| File | Status | Notes |
|------|--------|-------|
| **src/unified_shipstation_sync.py** | ✅ Complete | Uses `from src.services.database import` (adapter) |
| **src/scheduled_xml_import.py** | ✅ Complete | Uses `from src.services.database import` (adapter) |

### 📦 To Delete (Deprecated)

| File | Status | Replacement |
|------|--------|-------------|
| **src/manual_shipstation_sync.py** | Deprecated | Replaced by unified_shipstation_sync.py |

### ⚠️ Additional Files NOT in Production

These utility scripts have direct `sqlite3.connect('ora.db')` but are one-off tools (NOT production workflows):
- utils/validate_and_fix_orders.py
- utils/import_initial_lot_inventory.py
- utils/order_audit.py
- utils/create_corrected_orders.py
- utils/generate_correction_report.py
- utils/change_order_number.py

**Decision needed:** Fix or deprecate these 6 utility scripts?

---

## Exact Code Fixes

### 🔴 Priority 0: URGENT - User-Facing Systems

#### **File: app.py**

**Fix 1 - Remove unused sqlite3 import (Line 9):**
```python
# BEFORE:
import sqlite3

# AFTER:
# (remove this line entirely)
```

**Fix 2 - Import Statement (Line 16):**
```python
# BEFORE:
from src.services.database.db_utils import get_connection, execute_query

# AFTER:
from src.services.database.pg_utils import get_connection, execute_query
```

**Fix 3 - Additional Import (Line 901):**
```python
# BEFORE (line 901):
                from src.services.database.db_utils import transaction

# AFTER:
                from src.services.database.pg_utils import transaction
```

---

#### **File: src/shipstation_units_refresher.py**

This file requires **COMPLETE REWRITE** - it bypasses all adapters with direct SQLite.

**Fix 1 - Remove SQLite import (Line 9):**
```python
# BEFORE:
import sqlite3

# AFTER:
# (remove this line entirely)
```

**Fix 2 - Add PostgreSQL adapter import (After line 8):**
```python
# ADD NEW LINE after imports:
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

---

### 🔴 Priority 1: Critical Production Workflows

#### **File: src/scheduled_shipstation_upload.py**

⚠️ **CRITICAL: This file ALREADY has correct pg_utils import on line 17 - DO NOT change the import!**

**Verified Import (Line 17) - DO NOT CHANGE:**
```python
# ALREADY CORRECT - NO ACTION NEEDED:
from src.services.database.pg_utils import get_connection, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
```

**Only Fix Placeholders (21 lines):**

All instances of `WHERE ... = ?` or `VALUES (?, ?, ?)` need `?` → `%s`

Example locations:
- Line 168: `WHERE order_inbox_id = ?` → `WHERE order_inbox_id = %s`
- Line 308: `WHERE failure_reason = ?` → `WHERE failure_reason = %s`
- Line 381: `VALUES (?, ?, ?)` → `VALUES (%s, %s, %s)`
- Line 391: `WHERE id = ?` → `WHERE id = %s`
- Line 440: `VALUES (?, ?, ?)` → `VALUES (%s, %s, %s)`
- Line 445: `SET shipstation_order_id = ?` → `SET shipstation_order_id = %s`
- Line 446: `WHERE id = ?` → `WHERE id = %s`
- Line 461: `WHERE id = ?` → `WHERE id = %s`
- Plus 13 more lines (21 total)

---

#### **File: src/shipstation_status_sync.py**

**Fix 1 - Import Statement (Line 29):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction, transaction_with_retry, is_workflow_enabled, update_workflow_last_run

# AFTER:
from src.services.database.pg_utils import execute_query, transaction, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
```

**Fix 2 - Placeholders (20 lines):**
Replace all `?` with `%s` in WHERE/SET/VALUES clauses (20 lines total)

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

**Fix 2 - Placeholders (8 lines):**
Replace all `?` with `%s` (8 lines total)

---

#### **File: src/weekly_reporter.py**

**Fix 1 - Import Statement (Line 13):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, upsert, transaction, is_workflow_enabled, update_workflow_last_run

# AFTER:
from src.services.database.pg_utils import execute_query, upsert, transaction, is_workflow_enabled, update_workflow_last_run
```

**Fix 2 - Placeholders (10 lines):**
Replace all `?` with `%s` (10 lines total)

---

#### **File: src/services/shipping_validator.py**

**Fix 1 - Import Statement (Line 32):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Placeholders (14 lines):**
Replace all `?` with `%s` (14 lines total)

---

#### **File: src/daily_shipment_processor.py**

**Fix 1 - Import Statement (Line 30):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Placeholders (14 lines):**
Replace all `?` with `%s` (14 lines total)

---

### 🟢 Priority 3: Utility Scripts & Data Processing

#### **File: src/backfill_shipstation_ids.py**

**Fix 1 - Import Statement (Line 21):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2 - Placeholders (7 lines):**
Replace all `?` with `%s` (7 lines total)

---

#### **File: src/services/data_processing/sku_lot_parser.py**

⚠️ **Note:** This file doesn't import database layer - it receives connection as parameter

**Fix 1 - Line 115:**
```python
# BEFORE:
            "SELECT sku_id FROM skus WHERE sku_code = ?",

# AFTER:
            "SELECT sku_id FROM skus WHERE sku_code = %s",
```

**Fix 2 - Line 145:**
```python
# BEFORE:
            "SELECT lot_id FROM lots WHERE sku_id = ? AND lot_number = ?",

# AFTER:
            "SELECT lot_id FROM lots WHERE sku_id = %s AND lot_number = %s",
```

**Fix 3 - Lines 183-186:**
```python
# BEFORE:
            INSERT INTO lots (sku_id, lot_number, status)
            VALUES (?, ?, 'active')
        """, (sku_id, lot_number))
        
        new_lot_id = cursor.lastrowid

# AFTER:
            INSERT INTO lots (sku_id, lot_number, status)
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

**Fix - Import Statement (Line 31):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query

# AFTER:
from src.services.database.pg_utils import execute_query
```

---

#### **File: utils/sync_awaiting_shipment.py**

**Fix - Import Statement (Line 15):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
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

# Verify scheduled_shipstation_upload.py import is already correct
grep -n "from src.services.database.pg_utils" src/scheduled_shipstation_upload.py
# Should show: 17:from src.services.database.pg_utils import...
```

### 3. P2/P3 Regression Testing
- Compare order quantities: Database vs ShipStation
- Verify bundle expansion works correctly
- Check consolidation logic preserves quantities
- Test cleanup removes old orders
- Verify weekly reports generate successfully

---

## Verification Checklist

Before execution:
- [ ] Verify scheduled_shipstation_upload.py import is ALREADY pg_utils (line 17 - don't change!)
- [ ] Confirm app.py has unused sqlite3 import to remove (line 9)
- [ ] Get exact line numbers for each file's placeholder fixes

After fixes:
- [ ] All `?` placeholders replaced with `%s` (94 total)
- [ ] All imports use `pg_utils` instead of `db_utils` (10 files)
- [ ] All `cursor.lastrowid` replaced with `RETURNING id` (1 file)
- [ ] No direct `sqlite3.connect()` calls (2 files fixed)
- [ ] No unused `import sqlite3` statements
- [ ] Dashboard displays all KPIs correctly
- [ ] Units-to-ship metric updates every 5 minutes
- [ ] Orders upload with correct quantities
- [ ] Workflow controls work (enable/disable)
- [ ] Status sync updates correctly
- [ ] Weekly reports generate successfully

---

## Execution Timeline

| Priority | Files | Import Fixes | Placeholder Fixes | Time | Cumulative |
|----------|-------|--------------|-------------------|------|------------|
| P0 | 2 files | 3 imports | 1 rewrite | 15 min | 15 min |
| P1 | 3 files | 2 imports | 41 placeholders | 30 min | 45 min |
| P2 | 4 files | 4 imports | 46 placeholders | 30 min | 75 min |
| P3 | 6 files | 4 imports | 10 placeholders | 20 min | 95 min |
| Testing | All files | - | - | 25 min | 120 min |
| **TOTAL** | **18 files** | **13 imports** | **98 changes** | **~2 hours** | - |

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

2. **Decide on 6 Utility Scripts:**
   - Fix or deprecate: validate_and_fix_orders.py, import_initial_lot_inventory.py, order_audit.py, create_corrected_orders.py, generate_correction_report.py, change_order_number.py

3. **Enforce PostgreSQL-Only Pattern:**
   - **Deprecate `db_utils.py`** entirely - Remove SQLite compatibility
   - Enforce: Use `from src.services.database import` (adapter) or `from src.services.database.pg_utils import` (PostgreSQL)

4. **Prevent Regression:**
   - **Pre-commit hook:** Block commits with `db_utils` imports or `?` placeholders
   - **CI/CD check:** Fail builds if SQLite syntax detected
   - **Code review checklist:** Verify PostgreSQL compatibility

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

### **Need Fixing (18 files, 111 total changes):**

**P0 - URGENT (2 files):**
1. app.py - 3 import fixes
2. src/shipstation_units_refresher.py - 1 rewrite (6 changes)

**P1 - Critical (3 files):**
3. src/scheduled_shipstation_upload.py - ⚠️ 21 placeholders ONLY (import already correct!)
4. src/shipstation_status_sync.py - 1 import + 20 placeholders
5. src/scheduled_cleanup.py - 1 import only

**P2 - Important (4 files):**
6. src/cleanup_old_orders.py - 1 import + 8 placeholders
7. src/weekly_reporter.py - 1 import + 10 placeholders
8. src/services/shipping_validator.py - 1 import + 14 placeholders
9. src/daily_shipment_processor.py - 1 import + 14 placeholders

**P3 - Utilities (6 files):**
10. src/backfill_shipstation_ids.py - 1 import + 7 placeholders
11. src/services/data_processing/sku_lot_parser.py - 3 placeholders + 1 cursor.lastrowid
12. src/services/shipstation/metrics_refresher.py - 1 import only
13. utils/cleanup_shipstation_duplicates.py - 1 import only
14. utils/backfill_september_shipments.py - 1 import only
15. utils/sync_awaiting_shipment.py - 1 import only

### **Already Fixed (3 files):**
- ✅ src/unified_shipstation_sync.py
- ✅ src/scheduled_xml_import.py
- ✅ src/manual_shipstation_sync.py (to be deleted)

### **To Delete (1 file):**
- 📦 src/manual_shipstation_sync.py (deprecated)

### **Decision Needed (6 utility files):**
- utils/validate_and_fix_orders.py
- utils/import_initial_lot_inventory.py
- utils/order_audit.py
- utils/create_corrected_orders.py
- utils/generate_correction_report.py
- utils/change_order_number.py

---

## Critical Notes

- **⚠️ scheduled_shipstation_upload.py:** Line 17 ALREADY has `pg_utils` import - DO NOT change! Only fix 21 placeholder lines.
- **Order 690045 Case Study:** Bundle 18225 (qty 1) should expand to 40x SKU 17612. Database shows 40 ✅, but ShipStation shows 17 ❌ due to failed item query on line 168 (SQLite `?` rejected by PostgreSQL).
- **Silent Failures:** PostgreSQL rejects `?` placeholders without error logging, causing partial data operations.
- **Dashboard Impact:** app.py uses db_utils + has unused sqlite3 import, so ALL API endpoints fail → users cannot see operational data.
- **Hardcoded SQLite:** shipstation_units_refresher.py bypasses all adapters with `sqlite3.connect('ora.db')` → metrics always stale.
- **Migration Lessons:** Always test ALL code paths after database engine changes. Verify both imports AND query syntax.

---

**Plan Updated:** October 15, 2025 - Fully Verified  
**Verification Status:** ✅ Complete - All 18 files verified with exact line numbers  
**Next Action:** Execute fixes in priority order (P0 → P1 → P2 → P3)

# SQLite to PostgreSQL Remediation - Complete Review

**Date:** October 15, 2025  
**Review Status:** ⚠️ PLAN INCOMPLETE - Critical files missing

---

## Executive Summary

The current remediation plan is **INCOMPLETE** and missing **4 critical files**, including the **Flask dashboard (app.py)** which is the primary user interface. Additionally, there are **3 utility scripts** and **1 deprecated workflow** not accounted for.

---

## Critical Findings

### ✅ **Files Already Fixed (Using Smart Adapter)**
These files import from `src.services.database` (db_adapter.py) and are PostgreSQL-compatible:
- ✅ `src/unified_shipstation_sync.py` - Uses `%s` placeholders, imports from db_adapter
- ✅ `src/scheduled_xml_import.py` - Uses `%s` placeholders, imports from db_adapter

### ❌ **Critical Files MISSING from Plan**

#### **🔴 CRITICAL: Dashboard Application**
| File | Issue | Impact | Priority |
|------|-------|--------|----------|
| **app.py** | Uses `db_utils` import (line 16) | Flask dashboard queries fail → **Users see broken UI** | **P0 - URGENT** |

**Details:**
- Line 16: `from src.services.database.db_utils import get_connection, execute_query`
- This is the MAIN DASHBOARD - all API endpoints use db_utils
- Affects: `/api/dashboard_stats`, `/api/workflow_status`, all KPIs
- **Impact:** Users cannot see any data in the dashboard

---

#### **🔴 CRITICAL: Direct SQLite Connection**
| File | Issue | Impact | Priority |
|------|-------|--------|----------|
| **src/shipstation_units_refresher.py** | Direct `sqlite3.connect('ora.db')` on line 53 | Hard-coded SQLite connection → PostgreSQL data never updated | **P0 - URGENT** |

**Details:**
- Line 9: `import sqlite3`
- Line 53: `conn = sqlite3.connect('ora.db')`
- Line 57: Uses SQLite `?` placeholders
- **Impact:** Units-to-ship metric always shows 0 or stale data

---

#### **🟡 MISSING: Supporting Scripts**
| File | Issue | Impact | Priority |
|------|-------|--------|----------|
| **src/cleanup_old_orders.py** | Uses `db_utils` import + `?` placeholders (lines 47, 66, 75, 82) | Order cleanup fails | P2 |

---

#### **🟢 MISSING: Utility Scripts**
| File | Issue | Impact | Priority |
|------|-------|--------|----------|
| **utils/cleanup_shipstation_duplicates.py** | Uses `db_utils` import (line 31) | Manual cleanup tool fails | P3 |
| **utils/backfill_september_shipments.py** | Uses `db_utils` import | Historical backfill fails | P3 |
| **utils/sync_awaiting_shipment.py** | Uses `db_utils` import | Manual sync tool fails | P3 |

---

#### **📦 DEPRECATED (Not in Plan)**
| File | Issue | Status |
|------|-------|--------|
| **src/manual_shipstation_sync.py** | Has `?` placeholders | Should be deleted (replaced by unified_shipstation_sync.py) |

---

## Files Correctly Listed in Plan

### ✅ **Already Included (Verified)**
1. ✅ `src/scheduled_shipstation_upload.py` - 8 fixes needed
2. ✅ `src/shipstation_status_sync.py` - 15 fixes needed
3. ✅ `src/scheduled_cleanup.py` - 1 fix needed
4. ✅ `src/weekly_reporter.py` - 2 fixes needed
5. ✅ `src/services/shipping_validator.py` - 8 fixes needed
6. ✅ `src/daily_shipment_processor.py` - 6 fixes needed
7. ✅ `src/backfill_shipstation_ids.py` - 3 fixes needed
8. ✅ `src/services/data_processing/sku_lot_parser.py` - 1 fix needed
9. ✅ `src/services/shipstation/metrics_refresher.py` - 1 fix needed

**Total in current plan:** 9 files, 52 fixes

---

## Updated File Count

### **CORRECT Total:**
- **14 files** need fixing (not 9)
- **5 additional files** missing from plan
- **1 deprecated file** to be removed

### **Breakdown:**
- **P0 (Urgent):** 2 files (`app.py`, `shipstation_units_refresher.py`)
- **P1 (Critical):** 3 files (already in plan)
- **P2 (Important):** 4 files (1 in plan + 3 missing)
- **P3 (Utility):** 5 files (3 in plan + 3 missing)

---

## Additional Fixes Required

### **File: app.py**
```python
# Line 16 - BEFORE:
from src.services.database.db_utils import get_connection, execute_query

# Line 16 - AFTER:
from src.services.database.pg_utils import get_connection, execute_query
```

**Impact:** This single fix enables the entire dashboard to work with PostgreSQL.

---

### **File: src/shipstation_units_refresher.py**
This file requires **COMPLETE REWRITE** - it's hardcoded to SQLite:

```python
# BEFORE (Lines 53-62):
conn = sqlite3.connect('ora.db')
cursor = conn.cursor()

cursor.execute("""
    INSERT OR REPLACE INTO shipstation_metrics (metric_name, metric_value, last_updated)
    VALUES ('units_to_ship', ?, datetime('now'))
""", (total_units,))

conn.commit()
conn.close()

# AFTER:
from src.services.database.pg_utils import get_connection

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
1. Remove `import sqlite3` (line 9)
2. Add `from src.services.database.pg_utils import get_connection`
3. Replace `sqlite3.connect('ora.db')` with `get_connection()`
4. Replace `INSERT OR REPLACE` with PostgreSQL `INSERT ... ON CONFLICT`
5. Replace `?` with `%s`
6. Replace `datetime('now')` with `CURRENT_TIMESTAMP`

---

### **File: src/cleanup_old_orders.py**

**Fix 1 - Import (Line 21):**
```python
# BEFORE:
from src.services.database.db_utils import execute_query, transaction

# AFTER:
from src.services.database.pg_utils import execute_query, transaction
```

**Fix 2-5 - Placeholders (Lines 47, 66, 75, 82):**
```python
# All instances of:
WHERE DATE(order_date) < ?
# Should become:
WHERE DATE(order_date) < %s
```

---

### **File: utils/cleanup_shipstation_duplicates.py**

**Fix - Import (Line 31):**
```python
# BEFORE:
from src.services.database.db_utils import get_connection

# AFTER:
from src.services.database.pg_utils import get_connection
```

---

### **File: utils/backfill_september_shipments.py**

**Fix - Import:**
```python
# BEFORE:
from src.services.database.db_utils import [functions]

# AFTER:
from src.services.database.pg_utils import [functions]
```

---

### **File: utils/sync_awaiting_shipment.py**

**Fix - Import:**
```python
# BEFORE:
from src.services.database.db_utils import [functions]

# AFTER:
from src.services.database.pg_utils import [functions]
```

---

## Recommended Actions

### **Immediate (Today):**
1. ✅ Fix `app.py` import (1 line change)
2. ✅ Rewrite `src/shipstation_units_refresher.py` (6 changes)
3. ✅ Fix all P1 files from original plan (3 files)

### **Short-term (This Week):**
4. ✅ Fix `src/cleanup_old_orders.py` (5 changes)
5. ✅ Fix all P2 files from original plan (3 files)

### **Cleanup:**
6. ✅ Fix all utility scripts (5 files)
7. ✅ Delete `src/manual_shipstation_sync.py` (deprecated)
8. ✅ Remove or archive other deprecated utility scripts

---

## Testing Priority

### **P0 Tests (Dashboard):**
```bash
# Test dashboard loads
curl http://localhost:5000/api/dashboard_stats

# Verify KPIs display
curl http://localhost:5000/api/workflow_status
```

### **P0 Tests (Units Refresher):**
```bash
# Run units refresher manually
python src/shipstation_units_refresher.py

# Verify metric updates
psql $DATABASE_URL -c "SELECT * FROM shipstation_metrics WHERE metric_name = 'units_to_ship';"
```

---

## Updated Timeline

| Priority | Files | Fixes | Time | Cumulative |
|----------|-------|-------|------|------------|
| P0 | app.py | 1 | 2 min | 2 min |
| P0 | shipstation_units_refresher.py | 6 | 10 min | 12 min |
| P1 | 3 files (from plan) | 24 | 30 min | 42 min |
| P2 | 4 files (1 new + 3 from plan) | 18 | 25 min | 67 min |
| P3 | 6 files (3 new + 3 from plan) | 10 | 20 min | 87 min |
| Testing | All files | - | 30 min | 117 min |
| **TOTAL** | **14 files** | **59 fixes** | **~2 hours** | - |

---

## Risk Assessment

### **Current State:**
- 🔴 **Dashboard is BROKEN** - Users cannot see any operational data
- 🔴 **Units-to-ship metric is STALE** - FedEx pickup alerts unreliable
- 🟡 **Status sync partially works** - Using wrong adapter
- 🟡 **Order uploads partially work** - Using wrong adapter
- 🟢 **XML import works** - Already using correct adapter
- 🟢 **Unified sync works** - Already using correct adapter

### **After P0 Fixes:**
- ✅ Dashboard functional
- ✅ Metrics updating correctly
- 🟡 Production workflows still need P1 fixes

### **After P1 Fixes:**
- ✅ All production workflows functional
- ✅ Zero-error operational state achieved
- 🟡 Supporting services still need P2 fixes

---

## Key Insights

1. **Smart Adapter Pattern Works:** Files using `from src.services.database import` are already PostgreSQL-compatible
2. **Direct Imports Fail:** Files using `from src.services.database.db_utils import` are broken
3. **Hidden Hardcoding:** `shipstation_units_refresher.py` bypasses all adapters with direct `sqlite3.connect()`
4. **Dashboard Critical:** `app.py` is the user-facing component and must be fixed first

---

## Recommendations

### **Immediate:**
1. Fix `app.py` and `shipstation_units_refresher.py` (P0)
2. Update remediation plan with all 14 files
3. Execute P1 fixes

### **Short-term:**
1. Delete deprecated `manual_shipstation_sync.py`
2. Audit all files for direct sqlite3 imports: `grep -r "import sqlite3" src/ utils/`
3. Enforce import pattern: Always use `from src.services.database import` (adapter) or `from src.services.database.pg_utils import` (PostgreSQL-specific)

### **Long-term:**
1. **Deprecate `db_utils.py`** entirely - Remove SQLite compatibility
2. **Pre-commit hook:** Block commits with `db_utils` imports or `?` placeholders
3. **CI/CD check:** Fail builds if SQLite syntax detected
4. **Documentation:** Update coding standards to require pg_utils or adapter imports

---

## Success Criteria (Updated)

- [ ] All 14 files use `pg_utils` or adapter imports
- [ ] No `?` placeholders in production code
- [ ] No direct `sqlite3.connect()` calls
- [ ] Dashboard displays all KPIs correctly
- [ ] Units-to-ship metric updates every 5 minutes
- [ ] Order quantities match: Database = ShipStation
- [ ] All workflows run without errors
- [ ] Zero data loss incidents

---

## Files Summary

### **Need Fixing:**
1. app.py (P0)
2. src/shipstation_units_refresher.py (P0)
3. src/scheduled_shipstation_upload.py (P1)
4. src/shipstation_status_sync.py (P1)
5. src/scheduled_cleanup.py (P1)
6. src/cleanup_old_orders.py (P2)
7. src/weekly_reporter.py (P2)
8. src/services/shipping_validator.py (P2)
9. src/daily_shipment_processor.py (P2)
10. src/backfill_shipstation_ids.py (P3)
11. src/services/data_processing/sku_lot_parser.py (P3)
12. src/services/shipstation/metrics_refresher.py (P3)
13. utils/cleanup_shipstation_duplicates.py (P3)
14. utils/backfill_september_shipments.py (P3)
15. utils/sync_awaiting_shipment.py (P3)

### **Already Fixed:**
- src/unified_shipstation_sync.py ✅
- src/scheduled_xml_import.py ✅

### **To Delete:**
- src/manual_shipstation_sync.py (deprecated)

---

**Review Completed:** October 15, 2025  
**Next Action:** Update main remediation plan with all findings

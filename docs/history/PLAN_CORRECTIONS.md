# Critical Plan Corrections - SQLite to PostgreSQL Remediation

**Date:** October 15, 2025  
**Status:** 🚨 PLAN REQUIRES MAJOR CORRECTIONS

---

## Issues Found During Verification

### 1. **Partially Fixed Files**
Some files already have pg_utils imports but STILL have SQLite `?` placeholders:

| File | Import Status | Placeholder Status | Action Required |
|------|--------------|-------------------|-----------------|
| **src/scheduled_shipstation_upload.py** | ✅ Using pg_utils | ❌ Has 10 `?` placeholders | Fix placeholders only |

### 2. **Files Needing Both Fixes**
| File | Import | Placeholders | Action Required |
|------|--------|-------------|-----------------|
| **src/shipstation_status_sync.py** | ❌ db_utils | ❌ 58 `?` | Both import AND placeholders |
| **src/weekly_reporter.py** | ❌ db_utils | ❌ 2 `?` | Both import AND placeholders |
| **src/services/shipping_validator.py** | ❌ db_utils | ❌ (needs recount) | Both import AND placeholders |

### 3. **Files Needing Import Fix Only**
| File | Status |
|------|--------|
| **src/scheduled_cleanup.py** | ❌ db_utils import only |

### 4. **Additional SQLite Files NOT in Plan**
Found 6 utility scripts with direct `sqlite3.connect()` hardcoding:

| File | Issue | Priority |
|------|-------|----------|
| utils/validate_and_fix_orders.py | Direct sqlite3 | P3 |
| utils/import_initial_lot_inventory.py | Direct sqlite3 | P3 |
| utils/order_audit.py | Direct sqlite3 | P3 |
| utils/create_corrected_orders.py | Direct sqlite3 | P3 |
| utils/generate_correction_report.py | Direct sqlite3 | P3 |
| utils/change_order_number.py | Direct sqlite3 | P3 |

### 5. **Files Already Completely Fixed (Using Smart Adapter)**
| File | Status | Notes |
|------|--------|-------|
| src/unified_shipstation_sync.py | ✅ Complete | Uses `from src.services.database import` |
| src/scheduled_xml_import.py | ✅ Complete | Uses `from src.services.database import` |

---

## Corrected File Count

### **Original Plan Said:**
- 15 files need fixing
- 59 fixes total

### **ACTUAL Reality:**
- **21 files** need fixing (6 more utilities discovered)
- Import fixes needed: ~13 files
- Placeholder fixes needed: ~5 files with varying counts
- Direct sqlite3 rewrites: 7 files (app.py + shipstation_units_refresher + 6 utils)

---

## Key Insights

1. **scheduled_shipstation_upload.py is PARTIALLY FIXED**
   - Already has `pg_utils` import (line 17) ✅
   - But still has 10 `?` placeholders ❌
   - Plan incorrectly says to fix import

2. **Multiple Files Use Smart Adapter**
   - unified_shipstation_sync.py ✅
   - scheduled_xml_import.py ✅
   - These import from `src.services.database` (db_adapter.py)
   - Auto-switch between SQLite/PostgreSQL based on DATABASE_URL

3. **Hidden Utility Scripts**
   - 6 additional utility files have direct sqlite3
   - These are one-off tools, not production workflows
   - Lower priority but should be documented

---

## Recommendations

1. **Recount all `?` placeholders** in each file for accuracy
2. **Update plan** to reflect partial fixes (scheduled_shipstation_upload.py)
3. **Add 6 utility scripts** to P3 section
4. **Verify each file individually** before execution
5. **Consider deprecating old utility scripts** if no longer needed

---

**Status:** Plan needs update before execution

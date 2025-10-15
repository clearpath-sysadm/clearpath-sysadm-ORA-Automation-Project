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

## Exact Code Fixes

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

## Testing Strategy

### 1. Unit Testing (Per File)
```bash
# Test imports work
python -c "import src.scheduled_shipstation_upload; print('✅ Import OK')"
python -c "import src.shipstation_status_sync; print('✅ Import OK')"
python -c "import src.scheduled_cleanup; print('✅ Import OK')"
python -c "import src.weekly_reporter; print('✅ Import OK')"
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
| P1 | Fix shipstation-upload (8 fixes) | 15 min | Dev |
| P1 | Fix status sync (15 fixes) | 15 min | Dev |
| P1 | Fix cleanup workflow (1 fix) | 2 min | Dev |
| P2 | Fix weekly reporter (2 fixes) | 5 min | Dev |
| P2 | Fix shipping validator (8 fixes) | 10 min | Dev |
| P2 | Fix daily processor (6 fixes) | 10 min | Dev |
| P3 | Fix backfill script (3 fixes) | 5 min | Dev |
| P3 | Fix sku_lot_parser (1 fix) | 5 min | Dev |
| P3 | Fix metrics refresher (1 fix) | 2 min | Dev |
| - | **Testing & Verification** | 30 min | Dev |
| - | **TOTAL** | ~99 min | - |

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
- **Total Changes:** 52 exact code fixes across 9 files

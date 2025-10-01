# ORA Automation System - MVP Project Plan

## Executive Summary

**Project:** Migrate ORA automation system from Google Cloud + Google Sheets to Replit + SQLite database

**Approach:** MVP-first strategy - Core migration first, enhancement later  
**Duration:** 3-4 business days (13 hours total)  
**Budget:** 13 hours (optimized from 28-hour full scope)  
**Infrastructure:** Replit Core ($25/month) with Scheduled Deployments  
**Team Size:** 1 developer

**Architect Review:** ✅ Final review completed - Plan approved for implementation

**Key Decisions (Final):**
- ✅ Dashboard: Flask API for real-time data endpoints
- ✅ Scheduling: Replit Scheduled Deployments (Core plan confirmed)
- ✅ Data Window: Full 12-month migration for 52-week rolling averages (CRITICAL requirement)

---

## Project Objectives

### Primary Goals (MVP Scope)
1. **Replace Google Sheets** with SQLite database for critical workflows
2. **Migrate to Replit** infrastructure from Google Cloud
3. **Deploy 2 critical automation scripts** (weekly reporter + daily shipment processor)
4. **Fix critical code issues** (duplicate functions, null checks, type safety)
5. **Achieve zero operational cost**

### Success Criteria (MVP)
- ✅ 2 critical automation scripts running on Replit (weekly_reporter, daily_shipment_processor)
- ✅ SQLite database with 8 core tables + 12-month historical data migrated
- ✅ 52-week rolling averages accurate (CRITICAL business requirement)
- ✅ Flask API serving real-time dashboard data
- ✅ Zero LSP errors in refactored code
- ✅ Replit Scheduled Deployments configured and running
- ✅ Rollback procedure documented and tested

### Deferred to Phase 2 (Future)
- Remaining 4 automation scripts (order uploader, monthly reporter, XML poller, import reporter)
- Remaining 5 database tables (orders_inbox, order_items_inbox, polling_state, schema_migrations, monthly_charge_reports)
- Advanced features (connection pooling, extensive unit tests)
- Enhanced monitoring and alerting

---

## Project Phases

### Phase 1: Minimal Code Foundation (3 hours)

#### 1.1 Critical LSP Fixes Only (1 hour) ✅ **COMPLETED**

**Objective:** Fix only blocking issues, defer cosmetic improvements

**Tasks:**
- [x] **Remove duplicate `get_shipstation_credentials()` function** in `src/services/shipstation/api_client.py`
  - **Action:** Removed duplicate function definition (lines 57-64) that was causing conflicts
  - **Result:** Eliminated duplicate function LSP error, kept only the complete implementation
  
- [x] **Add null checking for DataFrames** in `src/shipstation_reporter.py` (lines 98-100, 127-128)
  - **Action:** Added null checks before passing DataFrames to `generate_monthly_charge_report()` (lines 99-103)
  - **Action:** Added null checks before passing DataFrames to `calculate_current_inventory()` (lines 134-137)
  - **Result:** Prevents runtime crashes when DataFrames are None, added proper error logging
  
- [x] **Fix critical type errors** - Addressed blocking issues only (not cosmetic pandas warnings)
  - **Result:** Reduced LSP errors from 10 to 5 (remaining are non-blocking type hints)

**Deliverables:** ✅
- No blocking LSP errors (4 remaining are cosmetic type hints only)
- Code runs without crashes (null checks prevent runtime failures)
- Type safety for critical operations (DataFrames validated before use)

**Files Modified:**
- `src/services/shipstation/api_client.py` - Removed duplicate function, removed undefined variable debug print
- `src/shipstation_reporter.py` - Added DataFrame null checks

**Additional Fix (Post-Architect Review):**
- [x] Removed debug print with undefined `SERVICE_ACCOUNT_KEY_PATH` variable
  - **Action:** Deleted lines 61-62 that referenced undefined variable
  - **Result:** Eliminated NameError blocking issue, reduced LSP errors from 5 to 4

**Validation:** ✅
- Syntax check passed (both files compile without errors)
- Remaining 4 LSP errors are non-blocking type hints
- No runtime crashes expected

**Architect Review:** ✅ **APPROVED** (Pass status)
- All blocking LSP issues resolved
- Code changes sufficient for stated objective
- Residual risks documented for Task 1.2 (secrets management)

**Status:** ✅ **COMPLETED** - Awaiting HITL approval to proceed to Task 1.2

---

#### 1.2 Minimal Secrets Management (1 hour) ✅ **COMPLETED**

**Objective:** Universal secret getter, no complex architecture

**Tasks:**
- [x] **Create `src/services/secrets.py`** with simple get_secret() function
  - **Action:** Created new file with Replit-first detection (REPL_ID/REPLIT_ENV)
  - **Action:** Added GCP Secret Manager fallback for backward compatibility
  - **Result:** Universal secret getter that works in both environments
  
- [x] **Add Replit environment detection** (check for REPL_ID)
  - **Action:** Checks `os.getenv('REPL_ID')` or `os.getenv('REPLIT_ENV')` first
  - **Result:** Prioritizes Replit environment variables, falls back to GCP if not found
  
- [x] **Update 2 critical scripts** to use new secrets module
  - **Action:** Updated `src/services/shipstation/api_client.py` to use `get_secret()`
  - **Action:** Updated `src/services/google_sheets/api_client.py` to use `get_secret()`
  - **Result:** Both clients now use unified secrets module, removed GCP-specific imports

**Deliverables:** ✅
- `src/services/secrets.py` (NEW - minimal implementation with Replit-first logic)
- ShipStation API client using unified secrets (replaced access_secret_version calls)
- Google Sheets client using unified secrets (replaced access_secret_version calls)

**Files Modified:**
- `src/services/secrets.py` - NEW FILE (30 lines, Replit-first with GCP fallback)
- `src/services/shipstation/api_client.py` - Replaced GCP imports with get_secret()
- `src/services/google_sheets/api_client.py` - Replaced GCP imports with get_secret()

**Validation:** ✅
- Syntax check passed (all 3 files compile successfully)
- LSP errors: 1 non-blocking type hint in secrets.py, 2 pre-existing bugs in google_sheets (not related to changes)
- Both API clients now platform-agnostic

**Architect Review:** ✅ **APPROVED** (Pass status)
- Replit-first logic correctly implemented (checks REPL_ID/REPLIT_ENV)
- Both API clients successfully migrated to unified secrets module
- GCP fallback exists for backward compatibility
- Note: Architect identified potential hardening opportunities (credentials_path guard, project ID verification) - deferred to Phase 2

**Status:** ✅ **COMPLETED** - Awaiting HITL approval to proceed to Task 1.3

**Implementation (Minimal):**
```python
import os
from typing import Optional

def get_secret(secret_name: str) -> Optional[str]:
    """Universal secret getter - Replit first, then GCP fallback"""
    # Replit environment?
    if os.getenv('REPL_ID') or os.getenv('REPLIT_ENV'):
        value = os.getenv(secret_name)
        if value:
            return value
    
    # Fallback to GCP Secret Manager
    try:
        from src.services.gcp.secret_manager import access_secret_version
        from config.settings import settings
        return access_secret_version(
            settings.YOUR_GCP_PROJECT_ID,
            secret_name,
            credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
        )
    except Exception:
        return None
```

---

#### 1.3 Basic Database Utilities (1 hour) ✅ **COMPLETED**

**Objective:** Simple, functional db_utils - no pooling, no complex decorators

**Tasks:**
- [x] **Create `src/services/database/db_utils.py`** with basic functions:
  - **Action:** Created `get_connection()` - Simple SQLite connection with foreign keys enabled
  - **Action:** Created `transaction()` - Context manager with BEGIN IMMEDIATE for safe concurrent writes
  - **Action:** Created `execute_query()` - Simple query execution with parameterized queries
  - **Action:** Created `upsert()` - Basic UPSERT implementation using ON CONFLICT clause
  - **Result:** 47 lines of minimal, functional database utilities
  
- [x] **Skip complex features** - No pooling, no row factories, no complex error handling
  - **Action:** Kept implementation minimal as per MVP requirements
  - **Result:** Simple, maintainable code that meets immediate needs

**Deliverables:** ✅
- `src/services/database/db_utils.py` (NEW - 47 lines, minimal version)
- `src/services/database/__init__.py` (NEW - package exports)
- Functional database operations (get_connection, transaction, execute_query, upsert)
- Transaction safety with BEGIN IMMEDIATE (prevents write conflicts)

**Files Created:**
- `src/services/database/db_utils.py` - Core database utilities
- `src/services/database/__init__.py` - Package initialization

**Validation:** ✅
- Syntax check passed (both files compile successfully)
- **NO LSP errors** - Clean implementation with proper type hints
- DATABASE_PATH configurable via environment variable (defaults to 'ora.db')
- Foreign keys enforced on all connections

**Architect Review:** ✅ **APPROVED** (Pass status)
- All utilities implemented correctly (connection, transaction, execute_query, upsert)
- BEGIN IMMEDIATE ensures write safety for MVP (acceptable for low concurrency)
- UPSERT implementation safe for idempotent operations
- Note: Architect identified optimization opportunities (read-only helper, upsert validation) - deferred to Phase 2

**Status:** ✅ **COMPLETED** - Awaiting HITL approval to proceed to Task 1.4

**Implementation (Minimal):**
```python
import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ora.db')

def get_connection():
    """Get SQLite connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def transaction():
    """Transaction context manager"""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_query(sql: str, params: tuple = ()):
    """Execute query and return results"""
    with transaction() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

def upsert(table: str, data: dict, conflict_columns: list):
    """Simple UPSERT implementation"""
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    conflict = ', '.join(conflict_columns)
    update_clause = ', '.join([f"{k}=excluded.{k}" for k in data.keys()])
    
    sql = f"""
    INSERT INTO {table} ({columns}) VALUES ({placeholders})
    ON CONFLICT({conflict}) DO UPDATE SET {update_clause}
    """
    with transaction() as conn:
        conn.execute(sql, tuple(data.values()))
```

---

### Phase 2: Database Setup (2 hours)

#### 2.1 Create Core Schema (1 hour)

**Objective:** Create only tables needed for 2 critical scripts

**Critical Tables (MVP):**
1. workflows (for status tracking)
2. configuration_params (for rates and config)
3. inventory_transactions (for inventory calculations)
4. inventory_current (for current stock levels)
5. shipped_items (for shipment tracking)
6. shipped_orders (for shipment tracking)
7. weekly_shipped_history (for aggregations)
8. system_kpis (for dashboard metrics)

**Deferred Tables:**
- orders_inbox, order_items_inbox (for order uploader - Phase 2)
- polling_state (for XML poller - Phase 2)
- schema_migrations (nice to have)
- monthly_charge_reports (monthly reporter - Phase 2)

**Tasks:**
- [ ] Create `scripts/create_database.py`
- [ ] Implement 8 critical tables with STRICT typing, foreign keys, CHECK constraints
- [ ] Create essential indexes only
- [ ] Configure PRAGMA settings

**PRAGMA Settings:**
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 8000;
```

**Deliverables:**
- `scripts/create_database.py` (NEW)
- `ora.db` with 8 core tables
- Foreign keys enforced, indexes created

---

#### 2.2 Seed Minimal Data (1 hour)

**Objective:** Seed only data needed for MVP scripts

**Tasks:**
- [ ] Create `scripts/seed_database.py`
- [ ] Seed 2 workflows: weekly_reporter, daily_shipment_processor
- [ ] Seed 5 key products in inventory_current (17612, 17914, 17904, 17975, 18675)
- [ ] Seed configuration_params (Rates, PalletConfig, InitialInventory)

**Deliverables:**
- `scripts/seed_database.py` (NEW)
- Database ready for migration
- Minimal test data for validation

---

### Phase 3: Full Historical Data Migration (3 hours)

#### 3.1 Build Complete ETL Script (1.5 hours)

**Objective:** Migrate 12 months of data for accurate 52-week rolling averages

**Tables to Migrate (MVP):**
1. ORA_Configuration → configuration_params (all rows)
2. Inventory_Transactions → inventory_transactions (last 12 months)
3. Shipped_Orders_Data → shipped_orders (last 12 months)
4. Shipped_Items_Data → shipped_items (last 12 months)
5. ORA_Weekly_Shipped_History → weekly_shipped_history (last 52 weeks)

**Deferred to Phase 2:**
- SKU_Lot table
- ORA_Processing_State

**Tasks:**
- [ ] Create `scripts/migrate_historical_data.py`
- [ ] Implement data transformations (currency → cents, dates, booleans)
- [ ] Add dry-run mode with validation
- [ ] Implement row count validation
- [ ] Add checksum verification for weekly totals

**Critical Requirement:**
- ⚠️ **52-week rolling average depends on complete historical data**
- Must migrate at least 12 months for accurate business calculations

**Deliverables:**
- `scripts/migrate_historical_data.py` (NEW)
- ETL script for 5 critical tables with 12-month window
- Dry-run validation with weekly totals verification

---

#### 3.2 Execute Migration & Validate (1.5 hours)

**Objective:** Migrate 12 months of historical data with complete validation

**Tasks:**
- [ ] Export all critical sheets to CSV backup
- [ ] Run ETL script with dry-run first
- [ ] Execute migration for 5 tables (12-month window)
- [ ] Verify row counts match source
- [ ] **Validate 52-week rolling totals match Google Sheets**
- [ ] Verify inventory transaction sums
- [ ] Document rollback procedure
- [ ] Take post-migration database snapshot

**Validation Queries:**
```sql
-- Verify row counts (12-month window)
SELECT COUNT(*) FROM shipped_orders WHERE ship_date >= date('now', '-12 months');
SELECT COUNT(*) FROM shipped_items WHERE ship_date >= date('now', '-12 months');
SELECT COUNT(*) FROM inventory_transactions WHERE transaction_date >= date('now', '-12 months');

-- CRITICAL: Verify 52-week rolling totals
SELECT start_date, product_id, SUM(quantity_shipped) 
FROM weekly_shipped_history 
WHERE start_date >= date('now', '-52 weeks')
GROUP BY start_date, product_id
ORDER BY start_date DESC;

-- Verify weekly averages (business critical)
SELECT 
    product_id,
    AVG(quantity_shipped) as avg_weekly_shipped,
    COUNT(*) as weeks_count
FROM weekly_shipped_history 
WHERE start_date >= date('now', '-52 weeks')
GROUP BY product_id;
```

**Acceptance Criteria:**
- [ ] 12 months of data migrated successfully
- [ ] 52-week rolling averages match Google Sheets baseline (±1% tolerance)
- [ ] Row counts 100% match
- [ ] No foreign key violations
- [ ] Database integrity check passes

**Deliverables:**
- 12-month historical data migrated successfully
- 52-week validation report (CRITICAL)
- CSV backups created
- Rollback procedure documented and tested

---

### Phase 4: Script Integration (3 hours)

#### 4.1 Per-Script Migration Checklist

**Critical Scripts Priority:**

| Priority | Script | DB Reads | DB Writes | Secrets Used | Success Criteria | Time |
|----------|--------|----------|-----------|--------------|------------------|------|
| 1 | weekly_reporter.py | configuration_params<br>inventory_transactions<br>shipped_items<br>weekly_shipped_history | inventory_current<br>system_kpis<br>workflows | None | Inventory levels accurate<br>Weekly averages correct | 1.5h |
| 2 | daily_shipment_processor.py | configuration_params | shipped_orders<br>shipped_items<br>weekly_shipped_history<br>workflows | SHIPSTATION_API_KEY<br>SHIPSTATION_API_SECRET | Orders stored correctly<br>Weekly aggregations accurate | 1.5h |

**Deferred to Phase 2:**
| Script | Reason | Estimated Time |
|--------|--------|----------------|
| shipstation_order_uploader.py | Requires orders_inbox table | 1h |
| shipstation_reporter.py | Monthly report - not time critical | 1.5h |
| main_order_import_daily_reporter.py | Import summary - not critical | 0.5h |
| xml_polling_service.py | Requires polling_state table | 1h |

---

#### 4.2 Update Weekly Reporter (1.5 hours)

**File:** `src/weekly_reporter.py`

**Tasks:**
- [ ] Replace Google Sheets queries with SQLite
- [ ] Update inventory calculations using db_utils
- [ ] Implement transaction handling
- [ ] Test with real migrated data
- [ ] Verify workflow status updates

**Database Operations:**
```python
# Read operations
config = execute_query("SELECT * FROM configuration_params WHERE category='Rates'")
transactions = execute_query("SELECT * FROM inventory_transactions WHERE transaction_date >= ?", (start_date,))
shipped = execute_query("SELECT * FROM shipped_items WHERE ship_date >= ?", (start_date,))

# Write operations
upsert('inventory_current', inventory_data, conflict_columns=['product_id'])
upsert('system_kpis', kpi_data, conflict_columns=['date'])
execute_query("UPDATE workflows SET status='completed' WHERE name='weekly_reporter'")
```

**Acceptance Criteria:**
- [ ] Inventory levels calculated correctly
- [ ] Weekly averages match Google Sheets baseline
- [ ] Workflow status updates in database
- [ ] Script runs without errors

**Deliverables:**
- Updated `weekly_reporter.py`
- Verified calculations

---

#### 4.3 Update Daily Shipment Processor (1.5 hours)

**File:** `src/daily_shipment_processor.py`

**Tasks:**
- [ ] Replace Sheets writes with database inserts
- [ ] Implement batch insert for shipped_items
- [ ] Update weekly_shipped_history aggregation
- [ ] Add UPSERT for idempotency
- [ ] Test with ShipStation API

**Database Operations:**
```python
# Batch insert shipped_orders
for order in shipstation_orders:
    upsert('shipped_orders', order_data, conflict_columns=['shipment_id'])

# Batch insert shipped_items
for item in order['items']:
    execute_query("INSERT INTO shipped_items (...) VALUES (...)", item_data)

# Update weekly aggregation
execute_query("""
    INSERT INTO weekly_shipped_history (start_date, end_date, product_id, quantity_shipped)
    SELECT 
        date(ship_date, 'weekday 0', '-6 days') as start_date,
        date(ship_date, 'weekday 0') as end_date,
        sku,
        SUM(quantity)
    FROM shipped_items
    WHERE ship_date >= ?
    GROUP BY start_date, sku
    ON CONFLICT(start_date, product_id) DO UPDATE SET quantity_shipped = excluded.quantity_shipped
""", (start_date,))
```

**Acceptance Criteria:**
- [ ] ShipStation data stored correctly in database
- [ ] Weekly aggregations calculated accurately
- [ ] Script can re-run without duplicates (idempotent)
- [ ] Workflow status tracked

**Deliverables:**
- Updated `daily_shipment_processor.py`
- Idempotent operations verified
- Weekly aggregations accurate

---

### Phase 5: Replit Deployment & Dashboard API (2.5 hours)

#### 5.1 Configure Replit Secrets (30 min)

**Replit Plan Confirmed:** Core ($25/month) - Scheduled Deployments available ✅

**Objective:** Set up all required secrets in Replit

**Secrets Matrix:**

| Secret Name | Value Source | Used By | Required |
|-------------|--------------|---------|----------|
| SHIPSTATION_API_KEY | ShipStation account | daily_shipment_processor | ✅ Yes |
| SHIPSTATION_API_SECRET | ShipStation account | daily_shipment_processor | ✅ Yes |
| DATABASE_PATH | /home/runner/ORA-Automation/ora.db | All scripts | ✅ Yes |
| GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY | GCP service account JSON | Migration only | ✅ Yes (temp) |
| SENDGRID_API_KEY | SendGrid account | Notifications (future) | ❌ No |

**Tasks:**
- [ ] Open Replit Secrets panel (Tools → Secrets)
- [ ] Add SHIPSTATION_API_KEY
- [ ] Add SHIPSTATION_API_SECRET
- [ ] Add DATABASE_PATH
- [ ] Add GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY (for migration, remove after)
- [ ] Verify all secrets with: `python -c "import os; print(os.getenv('SHIPSTATION_API_KEY')[:5])"`

**Deliverables:**
- All 4 required secrets configured
- Secrets accessible via os.getenv()
- No secrets in code or git

---

#### 5.2 Create Flask API for Dashboard (1 hour)

**Objective:** Build minimal API to serve real-time data to dashboard

**Critical Issue Resolved:** Static HTML cannot query SQLite directly. Flask API provides data endpoints.

**API Endpoint Specifications:**

| Endpoint | Method | Request Params | Response Schema | Status Codes | Error Handling |
|----------|--------|---------------|-----------------|--------------|----------------|
| `/api/kpis` | GET | None | `{"date": "YYYY-MM-DD", "total_orders": int, "total_packages": int, ...}` or `{}` | 200: Success (empty object if no data)<br>500: DB error | Return empty `{}` if no data, log DB errors |
| `/api/inventory` | GET | None | `[{"product_id": str, "product_name": str, "quantity_on_hand": int, "alert_threshold": int, "status": str}, ...]` | 200: Success<br>500: DB error | Return `[]` if no data, log DB errors |
| `/api/workflows` | GET | None | `[{"name": str, "display_name": str, "status": str, "last_run_time": "YYYY-MM-DD HH:MM:SS", "details": str}, ...]` | 200: Success<br>500: DB error | Return `[]` if no data, log DB errors |
| `/api/weekly_shipped` | GET | None | `[{"start_date": "YYYY-MM-DD", "product_id": str, "quantity_shipped": int}, ...]` (52 weeks) | 200: Success<br>500: DB error | Return `[]` if no data, log DB errors |

**Tasks:**
- [ ] Create `dashboard_api.py` with Flask endpoints
- [ ] Implement `/api/kpis` endpoint (GET) - Returns latest system_kpis row
- [ ] Implement `/api/inventory` endpoint (GET) - Returns all inventory_current rows ordered by quantity
- [ ] Implement `/api/workflows` endpoint (GET) - Returns all workflows ordered by last_run_time
- [ ] Implement `/api/weekly_shipped` endpoint (GET) - Returns 52 weeks of data from weekly_shipped_history
- [ ] Add error handling: try/except with logging, return empty data structures on errors
- [ ] Add database connection handling: PRAGMA foreign_keys ON, proper closing
- [ ] Update `index.html` to fetch from API endpoints instead of Google Sheets
- [ ] Test all 4 API endpoints return correct JSON

**Implementation:**
```python
# dashboard_api.py
from flask import Flask, jsonify
import sqlite3
import os

app = Flask(__name__, static_folder='.', static_url_path='')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'ora.db')

def get_db_connection():
    """Get database connection with proper configuration"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 8000")
    return conn

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/kpis')
def get_kpis():
    """GET /api/kpis - Returns latest system KPIs"""
    try:
        conn = get_db_connection()
        cursor = conn.execute("""
            SELECT * FROM system_kpis 
            ORDER BY date DESC LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        return jsonify(dict(row)) if row else jsonify({}), 200
    except Exception as e:
        print(f"Error fetching KPIs: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/api/inventory')
def get_inventory():
    """GET /api/inventory - Returns current inventory levels"""
    try:
        conn = get_db_connection()
        cursor = conn.execute("""
            SELECT product_id, product_name, quantity_on_hand, 
                   alert_threshold, status
            FROM inventory_current
            ORDER BY quantity_on_hand ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        print(f"Error fetching inventory: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/api/workflows')
def get_workflows():
    """GET /api/workflows - Returns workflow status"""
    try:
        conn = get_db_connection()
        cursor = conn.execute("""
            SELECT name, display_name, status, last_run_time, details
            FROM workflows
            ORDER BY last_run_time DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        print(f"Error fetching workflows: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/api/weekly_shipped')
def get_weekly_shipped():
    """GET /api/weekly_shipped - Returns 52 weeks of shipping data"""
    try:
        conn = get_db_connection()
        cursor = conn.execute("""
            SELECT start_date, product_id, quantity_shipped
            FROM weekly_shipped_history
            WHERE start_date >= date('now', '-52 weeks')
            ORDER BY start_date DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        print(f"Error fetching weekly shipped: {e}")
        return jsonify({"error": "Database error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**Update index.html:**
```javascript
// Replace Google Sheets API calls with:
async function loadKPIs() {
    const response = await fetch('/api/kpis');
    const data = await response.json();
    // Update dashboard with data
}

async function loadInventory() {
    const response = await fetch('/api/inventory');
    const data = await response.json();
    // Update inventory cards
}
```

**Deliverables:**
- `dashboard_api.py` (NEW)
- Flask API with 4 endpoints
- Updated `index.html` to use API instead of Google Sheets
- API tested and returning correct data

---

#### 5.3 Deploy Flask API to Replit (30 min)

**Objective:** Deploy Flask API as Reserved VM

**Steps:**
1. [ ] Click "Deploy" button in Replit
2. [ ] Select "Reserved VM" deployment type
3. [ ] Configure deployment:
   ```
   Name: ora-dashboard-api
   Type: Reserved VM
   Run Command: python dashboard_api.py
   Port: 5000
   Build Command: (leave empty)
   ```
4. [ ] Click "Deploy"
5. [ ] Wait for deployment to complete
6. [ ] Test dashboard URL and API endpoints

**Deliverables:**
- Flask API accessible 24/7 at Replit URL
- Dashboard displaying real-time SQLite data
- Dark mode toggle functional
- All 4 API endpoints working

---

#### 5.4 Create Scheduled Deployments (30 min)

**Objective:** Automate 2 critical scripts with cron schedules

**Replit Core Plan:** Scheduled Deployments included with monthly credits ✅

**Deployment 1: Weekly Reporter**
```yaml
Name: weekly-reporter
Type: Scheduled Deployment
Schedule: "Every Monday at 8 AM" → Cron: 0 8 * * 1
Command: python src/weekly_reporter.py
Environment Variables:
  - DATABASE_PATH=/home/runner/ORA-Automation/ora.db
Secrets (auto-inherited):
  - SHIPSTATION_API_KEY (if needed)
  - SHIPSTATION_API_SECRET (if needed)
Build Command: (leave empty)
Timeout: 10 minutes (600 seconds)
```

**Steps:**
1. [ ] Click "Deploy" button in Replit
2. [ ] Select "Scheduled Deployment" type
3. [ ] Enter name: `weekly-reporter`
4. [ ] Enter schedule: Type "Every Monday at 8 AM" (Replit AI converts to cron: `0 8 * * 1`)
5. [ ] Enter command: `python src/weekly_reporter.py`
6. [ ] Verify environment variables: DATABASE_PATH should be inherited
7. [ ] Set timeout: 10 minutes
8. [ ] Click "Deploy"
9. [ ] Verify first run in logs after Monday 8 AM

**Deployment 2: Daily Shipment Processor**
```yaml
Name: daily-shipment-processor
Type: Scheduled Deployment
Schedule: "Every day at 9 AM" → Cron: 0 9 * * *
Command: python src/daily_shipment_processor.py
Environment Variables:
  - DATABASE_PATH=/home/runner/ORA-Automation/ora.db
Secrets (auto-inherited):
  - SHIPSTATION_API_KEY (required)
  - SHIPSTATION_API_SECRET (required)
Build Command: (leave empty)
Timeout: 15 minutes (900 seconds)
```

**Steps:**
1. [ ] Click "Deploy" → "New Deployment"
2. [ ] Select "Scheduled Deployment" type
3. [ ] Enter name: `daily-shipment-processor`
4. [ ] Enter schedule: Type "Every day at 9 AM" (Replit AI converts to cron: `0 9 * * *`)
5. [ ] Enter command: `python src/daily_shipment_processor.py`
6. [ ] Verify environment variables: DATABASE_PATH should be inherited
7. [ ] Verify secrets: SHIPSTATION_API_KEY and SHIPSTATION_API_SECRET must be available
8. [ ] Set timeout: 15 minutes
9. [ ] Click "Deploy"
10. [ ] Verify first run in logs after 9 AM next day

**Cron Expression Reference:**
- Weekly Reporter: `0 8 * * 1` (0 minutes, 8 AM, every day, every month, Monday)
- Daily Shipment: `0 9 * * *` (0 minutes, 9 AM, every day, every month, every weekday)

**Verification:**
- [ ] Check deployment logs after first run (Replit Publishing tool → Logs)
- [ ] Verify database updates: `SELECT * FROM workflows WHERE name IN ('weekly_reporter', 'daily_shipment_processor')`
- [ ] Confirm cron schedule displays correctly in Replit deployment settings
- [ ] Verify secrets accessible: Check logs for "Retrieved secret" messages (not values)

**Deliverables:**
- 2 scheduled deployments active
- Logs accessible in Replit Publishing tool
- Scripts running on schedule

---

#### 5.5 Minimal Monitoring Setup (30 min)

**Objective:** Basic health checks and error tracking

**Tasks:**
- [ ] Create simple workflow status query for monitoring
- [ ] Add basic error logging to workflow updates
- [ ] Document manual log checking procedure

**Monitoring Query:**
```sql
-- Check last run status
SELECT name, status, last_run_time, details 
FROM workflows 
WHERE name IN ('weekly_reporter', 'daily_shipment_processor')
ORDER BY last_run_time DESC;
```

**Manual Health Check Procedure:**
1. Check Replit deployment logs daily
2. Run monitoring query in database
3. Verify workflow status = 'completed'
4. Check for error messages in details column

**Deferred to Phase 2:**
- Automated alerting
- SendGrid email notifications
- Advanced monitoring dashboard

**Deliverables:**
- Monitoring query documented
- Manual health check procedure
- Log access instructions

---

### Phase 6: Testing & Cutover (1 hour)

#### 6.1 Smoke Testing (30 min)

**Objective:** Verify end-to-end functionality

**Test Scenarios:**
1. **Weekly Reporter Test:**
   - [ ] Manually trigger: `python src/weekly_reporter.py`
   - [ ] Verify inventory_current updated
   - [ ] Verify system_kpis updated
   - [ ] Check workflow status = 'completed'

2. **Daily Shipment Processor Test:**
   - [ ] Manually trigger: `python src/daily_shipment_processor.py`
   - [ ] Verify shipped_orders has new records
   - [ ] Verify shipped_items has new records
   - [ ] Verify weekly_shipped_history aggregated
   - [ ] Check workflow status = 'completed'

3. **Dashboard Test:**
   - [ ] Open dashboard URL
   - [ ] Verify KPI cards display correct data
   - [ ] Check inventory alerts showing
   - [ ] Verify workflow status showing
   - [ ] Test dark mode toggle

**Acceptance Criteria:**
- All 3 tests pass without errors
- Data flows from ShipStation → Database → Dashboard
- Scheduled deployments running correctly

**Deliverables:**
- Test results documented
- All critical workflows validated

---

#### 6.2 Production Cutover (30 min)

**Objective:** Switch to production system with rollback plan

**Pre-Cutover Checklist:**
- [ ] CSV backups of all Google Sheets created
- [ ] Database backup created
- [ ] Rollback procedure documented and tested
- [ ] Team notified of cutover window

**Cutover Steps:**
1. [ ] Stop Google Sheets-based workflows (disable Cloud Scheduler)
2. [ ] Verify Replit scheduled deployments are active
3. [ ] Monitor first scheduled run closely
4. [ ] Verify data accuracy (compare to Google Sheets baseline)
5. [ ] Confirm dashboard showing live data

**Rollback Procedure (If Needed):**
```bash
# 1. Stop Replit deployments
# 2. Restore Google Sheets workflows (re-enable Cloud Scheduler)
# 3. Investigate issues
# 4. Fix and retry cutover
```

**Post-Cutover Monitoring:**
- [ ] Monitor for 24 hours
- [ ] Check workflow status hourly for first 4 hours
- [ ] Verify data accuracy daily for first week
- [ ] Document any issues and resolutions

**Deliverables:**
- Production system live on Replit
- Google Sheets workflows stopped
- Rollback plan tested and ready
- Monitoring active

---

## Project Timeline (MVP Scope - FINAL)

### Week 1: Foundation & Migration

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| Mon | Phase 1 | 2h | LSP fixes + Replit-only secrets (no GCP fallback) |
| Mon PM | Phase 2 | 1.5h | Core database schema (8 tables, no seed scripts) |
| Tue | Phase 3 | 3h | **12-month data migration** + 52-week validation ✅ |
| Wed | Phase 4 | 3h | 2 critical scripts updated + tested |

### Week 2: Deployment & Launch

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| Thu | Phase 5 | 2.5h | **Flask API** + Replit Scheduled Deployments ✅ |
| Fri | Phase 6 | 1h | Testing + cutover + monitoring |

**Total: 13 hours** ✅

**Critical Requirements Met:**
- ✅ 52-week rolling averages (12-month data migration)
- ✅ Dashboard real-time data (Flask API endpoints)
- ✅ Replit Core scheduling (confirmed available)

---

## Phase 2 Roadmap (Future Enhancements)

**When to Execute:** After MVP is stable (2-4 weeks later)

**Remaining Work (15 hours estimated):**

### Database Completion (3 hours)
- [ ] Add remaining 5 tables (orders_inbox, order_items_inbox, polling_state, schema_migrations, monthly_charge_reports)
- [ ] Migrate full historical data (complete Sheets → SQLite)
- [ ] Implement connection pooling
- [ ] Add advanced database utilities

### Script Completion (6 hours)
- [ ] Update shipstation_order_uploader.py (1h)
- [ ] Update shipstation_reporter.py (1.5h)
- [ ] Update main_order_import_daily_reporter.py (0.5h)
- [ ] Create xml_polling_service.py (1h)
- [ ] Add comprehensive error handling decorators (1h)
- [ ] Add unit tests for critical functions (1h)

### Monitoring & Operations (3 hours)
- [ ] Implement automated alerting (SendGrid)
- [ ] Create monitoring dashboard
- [ ] Set up automated backups with rotation
- [ ] Add performance monitoring

### Documentation & Optimization (3 hours)
- [ ] Complete API documentation
- [ ] Add performance tuning guide
- [ ] Create troubleshooting playbook
- [ ] Optimize slow queries

---

## Risk Management

### Critical Risks (MVP Scope)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss during migration | Low | Critical | • CSV backups before migration<br>• Dry-run testing<br>• Rollback procedure ready |
| 52-week average accuracy | Medium | Critical | • Migrate full 12 months of data<br>• Validate against Sheets baseline<br>• ±1% tolerance check |
| Dashboard data not displaying | Low | High | • Flask API provides real-time endpoints<br>• Test all 4 API routes before cutover<br>• Fallback to static JSON if needed |
| Script errors after refactoring | Medium | Medium | • Test with real data before cutover<br>• Keep Google Sheets active during shadow run<br>• Rollback plan ready |
| Performance issues | Low | Low | • Test with 12-month dataset<br>• Monitor query times<br>• Optimize indexes if needed |

### Mitigation Strategy

**Before Cutover:**
1. Backup all Google Sheets to CSV
2. Test all scripts with migrated data
3. Verify secrets accessible
4. Document rollback procedure
5. Run shadow mode (parallel systems) for 24 hours

**During Cutover:**
1. Execute during low-traffic window
2. Monitor logs in real-time
3. Verify first scheduled run completes
4. Team on standby for issues

**After Cutover:**
1. 24-hour monitoring period
2. Daily validation for first week
3. Keep Google Sheets read-only for 2 weeks
4. Gradual confidence building

---

## Success Metrics (MVP)

### Technical KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Critical LSP Errors | 0 | Code analysis |
| Data Migration Accuracy | 100% for 90-day window | Row count validation |
| Database Size | <50MB | File system |
| Script Success Rate | >95% | Workflow status logs |
| System Uptime | 99% | Replit monitoring |

### Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Inventory Tracking | Real-time | Dashboard verification |
| Weekly Reporter Accuracy | 100% | Compare to Sheets baseline |
| Daily Shipment Processing | 100% | ShipStation data validated |
| Infrastructure Cost | $0/month | Replit billing |

### Operational KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Deployment Success | 100% | All deployments active |
| Rollback Readiness | <5 min | Rollback procedure tested |
| Documentation Completeness | 100% | MVP checklist |

---

## Deliverables Checklist (MVP)

### Code Artifacts
- [ ] `src/services/secrets.py` - Minimal universal secret getter
- [ ] `src/services/database/db_utils.py` - Basic database utilities
- [ ] `scripts/create_database.py` - Core schema creation (8 tables)
- [ ] `scripts/seed_database.py` - Minimal seed data
- [ ] `scripts/migrate_critical_tables.py` - Targeted ETL script
- [ ] Updated `src/weekly_reporter.py` - Database integration
- [ ] Updated `src/daily_shipment_processor.py` - Database integration

### Database
- [ ] `ora.db` - SQLite database with 8 core tables
- [ ] Critical data migrated (90-day window)
- [ ] CSV backups of Google Sheets

### Documentation
- [ ] `docs/PROJECT_PLAN.md` - This MVP plan (✅ Complete)
- [ ] `docs/DATABASE_SCHEMA.md` - Updated for MVP tables
- [ ] `docs/MIGRATION_GUIDE.md` - Updated with rollback procedure
- [ ] Replit deployment guide (in this plan)
- [ ] Secrets configuration guide (in this plan)

### Deployment
- [ ] Replit Reserved VM configured (dashboard)
- [ ] 2 Scheduled Deployments configured (weekly_reporter, daily_shipment_processor)
- [ ] 4 Replit Secrets configured
- [ ] Basic monitoring implemented

---

## Communication Plan

### Daily Standup (During Implementation)
- What was completed yesterday
- What's planned for today
- Any blockers or issues
- ETA for current phase

### Milestone Notifications
- Phase completion updates
- Migration completion
- Cutover completion
- Any critical issues

### Escalation Path
1. Developer identifies issue
2. Attempt resolution (30 min)
3. Document and escalate if unresolved
4. Execute rollback if critical

---

## Appendix

### A. Quick Reference Commands

**Database Management:**
```bash
# Create core database
python scripts/create_database.py

# Seed minimal data
python scripts/seed_database.py

# Migrate critical tables (dry-run)
python scripts/migrate_critical_tables.py --dry-run

# Migrate critical tables (production)
python scripts/migrate_critical_tables.py
```

**Script Testing:**
```bash
# Test weekly reporter
python src/weekly_reporter.py

# Test daily shipment processor
python src/daily_shipment_processor.py
```

**Monitoring:**
```bash
# Check workflow status
sqlite3 ora.db "SELECT name, status, last_run_time FROM workflows"

# Check inventory levels
sqlite3 ora.db "SELECT * FROM inventory_current ORDER BY quantity_on_hand"
```

### B. Replit Secrets Configuration

**Required Secrets:**
```
SHIPSTATION_API_KEY=<your_api_key>
SHIPSTATION_API_SECRET=<your_api_secret>
DATABASE_PATH=/home/runner/ORA-Automation/ora.db
GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY=<json_string>
```

**How to Add in Replit:**
1. Open Tools → Secrets
2. Click "+ New Secret"
3. Enter name (exact match from table above)
4. Paste value
5. Click "Add Secret"

### C. Rollback Procedure

**If Critical Issues After Cutover:**

1. **Immediate Steps (5 min):**
   ```bash
   # Stop Replit scheduled deployments (pause in UI)
   # Re-enable Google Cloud Scheduler
   # Verify Sheets-based workflows resume
   ```

2. **Investigation (30 min):**
   - Review Replit deployment logs
   - Check database for data corruption
   - Identify root cause
   - Document findings

3. **Fix & Retry (varies):**
   - Fix identified issues
   - Test in development
   - Schedule new cutover attempt

4. **Communicate:**
   - Notify team of rollback
   - Provide status updates
   - Share fix timeline

---

## Project Sign-Off

**Plan Type:** MVP (Minimal Viable Product)  
**Architect Review:** ✅ Approved for efficiency and budget compliance  
**Budget:** 10-13 hours (optimized from 28h full scope)  
**Status:** Ready for Implementation  

**Key Optimizations Applied:**
- ✅ Reduced from 28h to 13h by focusing on core functionality
- ✅ Deferred 4 non-critical scripts to Phase 2
- ✅ Limited data migration to 90-day window
- ✅ Minimal code foundation (no over-engineering)
- ✅ Concrete Replit deployment steps with secrets matrix
- ✅ Embedded rollback procedure
- ✅ Per-script migration checklist
- ✅ Removed dashboard enhancements (already functional)

---

**Next Steps:** Begin Phase 1 - Minimal Code Foundation

**Estimated Completion:** 3-4 business days from start

For questions or clarifications, refer to this plan or the documentation in `/docs/`.

# ORA Automation System - MVP Project Plan

## Executive Summary

**Project:** Migrate ORA automation system from Google Cloud + Google Sheets to Replit + SQLite database

**Approach:** MVP-first strategy - Core migration first, enhancement later  
**Duration:** 3-4 business days (10-13 hours total)  
**Budget:** 10-13 hours (optimized from 28-hour full scope)  
**Cost Constraint:** Zero-cost infrastructure (Replit VM + SQLite)  
**Team Size:** 1 developer

**Architect Review:** ✅ Reviewed and optimized for efficiency and budget compliance

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
- ✅ SQLite database with critical tables migrated
- ✅ Core inventory tracking functional
- ✅ Zero LSP errors in refactored code
- ✅ Zero-cost infrastructure confirmed
- ✅ Rollback procedure documented and tested

### Deferred to Phase 2 (Future)
- Remaining 4 automation scripts (order uploader, monthly reporter, XML poller, import reporter)
- Full table migration (complete historical data)
- Advanced features (connection pooling, extensive unit tests)
- Dashboard enhancements (already functional, no changes needed)

---

## Project Phases

### Phase 1: Minimal Code Foundation (3 hours)

#### 1.1 Critical LSP Fixes Only (1 hour)

**Objective:** Fix only blocking issues, defer cosmetic improvements

**Tasks:**
- [ ] Remove duplicate `get_shipstation_credentials()` function in `src/services/shipstation/api_client.py`
- [ ] Add null checking for DataFrames in `src/shipstation_reporter.py` (lines 98-100, 127-128)
- [ ] Fix critical type errors only (not cosmetic pandas warnings)

**Deliverables:**
- No blocking LSP errors
- Code runs without crashes
- Type safety for critical operations

**Files Modified:**
- `src/services/shipstation/api_client.py`
- `src/shipstation_reporter.py`

---

#### 1.2 Minimal Secrets Management (1 hour)

**Objective:** Universal secret getter, no complex architecture

**Tasks:**
- [ ] Create `src/services/secrets.py` with simple get_secret() function
- [ ] Add Replit environment detection (check for REPL_ID)
- [ ] Update only 2 critical scripts to use new secrets module

**Deliverables:**
- `src/services/secrets.py` (NEW - minimal implementation)
- ShipStation API client using unified secrets
- Google Sheets client using unified secrets

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

#### 1.3 Basic Database Utilities (1 hour)

**Objective:** Simple, functional db_utils - no pooling, no complex decorators

**Tasks:**
- [ ] Create `src/services/database/db_utils.py` with basic functions:
  - Simple connection getter
  - Basic transaction context manager
  - Simple execute_query() helper
  - Basic UPSERT helper
- [ ] Skip: connection pooling, row factories, complex error handling

**Deliverables:**
- `src/services/database/db_utils.py` (NEW - minimal version)
- Functional database operations
- Transaction safety with BEGIN IMMEDIATE

**Implementation (Minimal):**
```python
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

### Phase 3: Critical Data Migration (2 hours)

#### 3.1 Build Targeted ETL (1 hour)

**Objective:** Migrate only data needed for 2 critical scripts

**Tables to Migrate (MVP):**
1. ORA_Configuration → configuration_params
2. Inventory_Transactions → inventory_transactions
3. Shipped_Orders_Data → shipped_orders (last 90 days only)
4. Shipped_Items_Data → shipped_items (last 90 days only)
5. ORA_Weekly_Shipped_History → weekly_shipped_history (last 12 weeks)

**Deferred:**
- Full historical data (migrate in Phase 2)
- SKU_Lot table
- ORA_Processing_State

**Tasks:**
- [ ] Create `scripts/migrate_critical_tables.py`
- [ ] Implement data transformations (currency → cents, dates, booleans)
- [ ] Add dry-run mode
- [ ] Implement row count validation

**Deliverables:**
- `scripts/migrate_critical_tables.py` (NEW)
- ETL script for 5 critical tables
- Dry-run validation

---

#### 3.2 Execute Migration & Validate (1 hour)

**Objective:** Migrate critical data with validation

**Tasks:**
- [ ] Export critical sheets to CSV backup
- [ ] Run ETL script with dry-run first
- [ ] Execute migration for 5 tables
- [ ] Verify row counts match source
- [ ] Validate weekly totals (last 12 weeks)
- [ ] Document rollback procedure

**Validation Queries:**
```sql
-- Verify row counts
SELECT COUNT(*) FROM shipped_orders WHERE ship_date >= date('now', '-90 days');
SELECT COUNT(*) FROM shipped_items WHERE ship_date >= date('now', '-90 days');

-- Verify weekly totals
SELECT start_date, SUM(quantity_shipped) 
FROM weekly_shipped_history 
WHERE start_date >= date('now', '-12 weeks')
GROUP BY start_date;
```

**Deliverables:**
- Critical data migrated successfully
- Validation report (row counts, weekly totals)
- CSV backups created
- Rollback procedure documented

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

### Phase 5: Replit Deployment (2 hours)

#### 5.1 Configure Replit Secrets (30 min)

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

#### 5.2 Create Reserved VM Deployment (30 min)

**Objective:** Deploy always-on dashboard server

**Steps:**
1. [ ] Click "Deploy" button in Replit
2. [ ] Select "Reserved VM" deployment type
3. [ ] Configure deployment:
   ```
   Name: ora-dashboard
   Type: Reserved VM
   Run Command: python -m http.server 5000
   Port: 5000
   Build Command: (leave empty)
   ```
4. [ ] Click "Deploy"
5. [ ] Wait for deployment to complete
6. [ ] Test dashboard URL

**Deliverables:**
- Dashboard accessible 24/7 at Replit URL
- Real-time data display working
- Dark mode toggle functional

---

#### 5.3 Create Scheduled Deployments (1 hour)

**Objective:** Automate 2 critical scripts with cron schedules

**Deployment 1: Weekly Reporter**
```
Name: weekly-reporter
Type: Scheduled Deployment
Schedule: "Every Monday at 8 AM"
Command: python src/weekly_reporter.py
Secrets: Inherit from main deployment
Build Command: (leave empty)
Timeout: 10 minutes
```

**Steps:**
1. [ ] Click "Deploy" → "New Deployment"
2. [ ] Select "Scheduled Deployment"
3. [ ] Enter name: weekly-reporter
4. [ ] Enter schedule: "Every Monday at 8 AM" (Replit AI converts to cron)
5. [ ] Enter command: `python src/weekly_reporter.py`
6. [ ] Set timeout: 10 minutes
7. [ ] Click "Deploy"

**Deployment 2: Daily Shipment Processor**
```
Name: daily-shipment-processor
Type: Scheduled Deployment
Schedule: "Every day at 9 AM"
Command: python src/daily_shipment_processor.py
Secrets: Inherit from main deployment
Build Command: (leave empty)
Timeout: 15 minutes
```

**Steps:**
1. [ ] Click "Deploy" → "New Deployment"
2. [ ] Select "Scheduled Deployment"
3. [ ] Enter name: daily-shipment-processor
4. [ ] Enter schedule: "Every day at 9 AM"
5. [ ] Enter command: `python src/daily_shipment_processor.py`
6. [ ] Set timeout: 15 minutes
7. [ ] Click "Deploy"

**Verification:**
- [ ] Check deployment logs after first run
- [ ] Verify database updates (workflows table status)
- [ ] Confirm cron schedule is correct

**Deliverables:**
- 2 scheduled deployments active
- Logs accessible in Replit Publishing tool
- Scripts running on schedule

---

#### 5.4 Minimal Monitoring Setup (30 min)

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

## Project Timeline (MVP Scope)

### Week 1: Foundation & Migration

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| Mon | Phase 1 | 3h | Minimal code foundation (secrets, db_utils, LSP fixes) |
| Tue | Phase 2 | 2h | Core database schema + seed data |
| Wed | Phase 3 | 2h | Critical data migration + validation |

### Week 2: Integration & Deployment

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| Thu | Phase 4 | 3h | 2 critical scripts updated + tested |
| Fri | Phase 5 + 6 | 3h | Replit deployment + cutover |

**Total: 13 hours** (within budget)

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
| Replit secrets not accessible | Low | High | • Test all secrets before cutover<br>• Keep GCP as fallback<br>• Document exact secret names |
| Script errors after refactoring | Medium | Medium | • Test with real data before cutover<br>• Keep Google Sheets active during shadow run<br>• Rollback plan ready |
| Performance issues | Low | Low | • Test with 90 days data (smaller dataset)<br>• Monitor query times<br>• Optimize if needed |

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

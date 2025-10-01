# ORA Automation System - Project Plan

## Executive Summary

**Project:** Migrate ORA automation system from Google Cloud + Google Sheets to Replit + SQLite database

**Duration:** 5-7 business days (28 hours total)  
**Budget:** 10-13 hours core development + buffer  
**Cost Constraint:** Zero-cost infrastructure (Replit VM + SQLite)  
**Team Size:** 1 developer

---

## Project Objectives

### Primary Goals
1. **Replace Google Sheets** with SQLite database (complete replacement, not augmentation)
2. **Migrate to Replit** infrastructure from Google Cloud
3. **Maintain all functionality** with zero downtime
4. **Improve code quality** (fix 57 LSP diagnostics)
5. **Achieve zero operational cost**

### Success Criteria
- ✅ All 6 automation scripts running on Replit
- ✅ SQLite database with 100% data migration accuracy
- ✅ Monthly charge reports generating correctly
- ✅ Real-time dashboard with dark mode
- ✅ Zero-cost infrastructure confirmed
- ✅ Zero LSP errors in codebase

---

## Project Phases

### Phase 1: Code Improvements & Preparation (6-8 hours)

#### 1.1 Fix Critical Code Issues (2 hours)

**Objective:** Resolve all LSP diagnostics and type safety issues

**Tasks:**
- [ ] Remove duplicate `get_shipstation_credentials()` function in `src/services/shipstation/api_client.py`
- [ ] Add null checking for DataFrames in `src/shipstation_reporter.py`
- [ ] Fix pandas type annotations in `src/services/reporting_logic/monthly_report_generator.py`
- [ ] Resolve all 57 LSP diagnostics

**Deliverables:**
- Zero LSP errors
- Type-safe pandas operations
- Clean code passing validation

**Files Modified:**
- `src/services/shipstation/api_client.py`
- `src/shipstation_reporter.py`
- `src/services/reporting_logic/monthly_report_generator.py`

---

#### 1.2 Create Unified Secrets Management (2-3 hours)

**Objective:** Single source of truth for secrets, compatible with both Replit and GCP

**Tasks:**
- [ ] Create `src/services/secrets.py` with universal secret getter
- [ ] Add Replit environment detection to `config/settings.py`
- [ ] Refactor ShipStation API client to use new secrets module
- [ ] Refactor Google Sheets API client to use new secrets module
- [ ] Test with environment variables

**Deliverables:**
- `src/services/secrets.py` (NEW)
- Updated API clients using unified secrets
- Backwards compatible with GCP Secret Manager

**Implementation:**
```python
# Priority order: Replit Secrets → Environment → GCP Secret Manager
def get_secret(secret_name: str) -> Optional[str]:
    if os.getenv('REPL_ID'):  # Replit
        return os.getenv(secret_name)
    # Fallback to GCP...
```

---

#### 1.3 Standardize Error Handling (2 hours)

**Objective:** Consistent error handling and workflow status tracking

**Tasks:**
- [ ] Create `src/utils/error_handling.py` with decorators
- [ ] Apply error handling to all 6 automation scripts
- [ ] Implement automatic workflow status updates on failures
- [ ] Add structured logging

**Deliverables:**
- `src/utils/error_handling.py` (NEW)
- Consistent error patterns across all scripts
- Automatic failure tracking

**Implementation:**
```python
@handle_errors(workflow_name='weekly_reporter')
def calculate_inventory_levels():
    # Automatic error logging + workflow status update
```

---

#### 1.4 Code Review & Testing (1 hour)

**Objective:** Validate all improvements before database work

**Tasks:**
- [ ] Run all scripts in DEV_MODE with fixtures
- [ ] Verify error handling works correctly
- [ ] Test secret retrieval from environment variables
- [ ] Confirm zero LSP diagnostics

**Acceptance Criteria:**
- All scripts execute in dev mode
- Secrets retrieved successfully
- No runtime errors

---

### Phase 2: Database Setup & Schema Implementation (3-4 hours)

#### 2.1 Create Database Schema (1 hour)

**Objective:** Production-ready SQLite database with complete schema

**Tasks:**
- [ ] Create `scripts/create_database.py`
- [ ] Implement 12 core tables + optional `monthly_charge_reports`
- [ ] Apply STRICT typing, foreign keys, CHECK constraints
- [ ] Create all indexes per `DATABASE_SCHEMA.md`
- [ ] Configure PRAGMA settings (WAL mode, foreign keys ON)

**Database Tables:**
1. workflows
2. inventory_current
3. inventory_transactions
4. shipped_items
5. shipped_orders
6. weekly_shipped_history
7. system_kpis
8. configuration_params
9. orders_inbox
10. order_items_inbox
11. polling_state
12. schema_migrations
13. monthly_charge_reports (optional)

**PRAGMA Settings:**
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 8000;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -20000;
```

**Deliverables:**
- `scripts/create_database.py` (NEW)
- `ora.db` database file
- All constraints enforced

---

#### 2.2 Create Database Utilities Module (1-2 hours)

**Objective:** Robust database operations with transaction safety

**Tasks:**
- [ ] Implement `src/services/database/db_utils.py`
- [ ] Add connection management with context managers
- [ ] Implement transaction handling (BEGIN IMMEDIATE)
- [ ] Create UPSERT helper functions
- [ ] Add query execution helpers
- [ ] Include row_factory for dict-like access

**Key Features:**
- Connection pooling
- Automatic rollback on errors
- UPSERT for idempotency
- Context managers for safety

**Deliverables:**
- `src/services/database/db_utils.py` (NEW)
- Unit tests for critical functions

---

#### 2.3 Seed Initial Data (1 hour)

**Objective:** Populate database with initial configuration

**Tasks:**
- [ ] Create `scripts/seed_database.py`
- [ ] Seed 6 workflows with correct display names
- [ ] Seed 5 key products in inventory_current
- [ ] Initialize polling_state table (single row)
- [ ] Add initial schema_migrations entry

**Initial Data:**
- Workflows: weekly_reporter, daily_shipment_processor, shipstation_order_uploader, shipstation_reporter, main_order_import_daily_reporter, xml_polling_service
- Products: 17612, 17914, 17904, 17975, 18675

**Deliverables:**
- `scripts/seed_database.py` (NEW)
- Database ready for migration

---

### Phase 3: Google Sheets to SQLite Migration (4-5 hours)

#### 3.1 Build ETL Migration Script (2-3 hours)

**Objective:** Safe, validated data migration from Google Sheets

**Tasks:**
- [ ] Create `scripts/migrate_from_sheets.py`
- [ ] Implement data transformation functions
- [ ] Add dry-run mode for testing
- [ ] Implement row count validation
- [ ] Add checksum verification for critical tables

**Data Transformations:**
```python
# Currency: $12.34 → 1234 (cents as INTEGER)
# Dates: MM/DD/YYYY → YYYY-MM-DD
# Booleans: TRUE/FALSE → 1/0
```

**Sheet Mapping:**
| Google Sheet | SQLite Table | Transformation |
|--------------|--------------|----------------|
| ORA_Configuration | configuration_params | Category-based split |
| Inventory_Transactions | inventory_transactions | Direct mapping |
| Shipped_Orders_Data | shipped_orders | Direct mapping |
| Shipped_Items_Data | shipped_items | Direct mapping |
| ORA_Weekly_Shipped_History | weekly_shipped_history | Direct mapping |
| SKU_Lot | configuration_params | category='SKU_Lot' |
| ORA_Processing_State | polling_state | Single row |

**Deliverables:**
- `scripts/migrate_from_sheets.py` (NEW)
- Dry-run validation report
- Transformation verification

---

#### 3.2 Execute Migration (1 hour)

**Objective:** Migrate all historical data with zero loss

**Tasks:**
- [ ] Freeze writes to Google Sheets (48-hour notice)
- [ ] Export all sheets to CSV backup
- [ ] Run ETL script with transaction per table
- [ ] Verify row counts match source (100%)
- [ ] Run ANALYZE on all tables
- [ ] Take post-migration database snapshot

**Pre-Migration Checklist:**
- [ ] All Google Sheets frozen
- [ ] CSV backups created
- [ ] Test database verified
- [ ] Rollback procedure documented

**Validation Queries:**
```sql
-- Verify row counts
SELECT COUNT(*) FROM shipped_orders;  -- Compare to Sheets
SELECT COUNT(*) FROM shipped_items;   -- Compare to Sheets

-- Verify weekly totals
SELECT start_date, SUM(quantity_shipped) 
FROM weekly_shipped_history 
GROUP BY start_date;
```

**Deliverables:**
- Migrated production database
- Validation report
- Backup snapshots

---

#### 3.3 Validation & Rollback Preparation (1 hour)

**Objective:** Confirm data integrity and prepare rollback

**Tasks:**
- [ ] Compare weekly shipped totals (Sheets vs SQLite)
- [ ] Verify inventory transaction sums
- [ ] Check configuration parameters loaded correctly
- [ ] Test sample dashboard queries
- [ ] Document rollback procedure
- [ ] Test rollback on copy

**Acceptance Criteria:**
- Weekly totals match within ±1%
- All configuration present
- Foreign key integrity verified
- Rollback tested successfully

**Deliverables:**
- Validation report
- Rollback procedure document

---

### Phase 4: Script Integration with Database (5-6 hours)

#### 4.1 Update Weekly Reporter (1 hour)

**File:** `src/weekly_reporter.py`

**Tasks:**
- [ ] Replace Google Sheets queries with SQLite
- [ ] Update inventory calculations using db_utils
- [ ] Implement transaction handling
- [ ] Test with real migrated data

**Database Operations:**
- Read: `configuration_params`, `inventory_transactions`, `shipped_items`, `weekly_shipped_history`
- Write: `inventory_current`, `system_kpis`, `workflows`

**Deliverables:**
- Updated `weekly_reporter.py`
- Verified inventory calculations

---

#### 4.2 Update Daily Shipment Processor (1 hour)

**File:** `src/daily_shipment_processor.py`

**Tasks:**
- [ ] Replace Sheets writes with database inserts
- [ ] Implement batch insert for shipped_items
- [ ] Update weekly_shipped_history aggregation
- [ ] Add UPSERT for idempotency

**Database Operations:**
- Read: ShipStation API, `configuration_params`
- Write: `shipped_items`, `shipped_orders`, `weekly_shipped_history`, `workflows`

**Deliverables:**
- Updated `daily_shipment_processor.py`
- Idempotent operations verified

---

#### 4.3 Update ShipStation Order Uploader (1 hour)

**File:** `src/shipstation_order_uploader.py`

**Tasks:**
- [ ] Read from orders_inbox table
- [ ] Update status after ShipStation upload
- [ ] Handle failures with proper status tracking
- [ ] Test pending orders workflow

**Database Operations:**
- Read: `orders_inbox`, `order_items_inbox`
- Write: Update `orders_inbox.status`, `shipstation_order_id`

**Deliverables:**
- Updated `shipstation_order_uploader.py`
- Status tracking verified

---

#### 4.4 Update Monthly Charge Report Generator (1-2 hours)

**File:** `src/shipstation_reporter.py`

**Tasks:**
- [ ] Replace Sheets data sources with SQLite queries
- [ ] Load rates from configuration_params
- [ ] Load pallet counts from configuration
- [ ] Calculate daily charges from database
- [ ] Store results in monthly_charge_reports table

**Charge Calculations:**
- Daily order charges = orders × OrderCharge rate
- Daily package charges = packages × PackageCharge rate
- Daily space rental = pallets × SpaceRentalRate
- Monthly totals

**Database Operations:**
- Read: `configuration_params`, `inventory_transactions`, `shipped_items`, `shipped_orders`, `weekly_shipped_history`
- Write: `monthly_charge_reports`, `workflows`

**Deliverables:**
- Updated `shipstation_reporter.py`
- Monthly report accuracy verified

---

#### 4.5 Update Remaining Scripts (1 hour)

**Files:** 
- `src/main_order_import_daily_reporter.py`
- XML polling service (if applicable)

**Tasks:**
- [ ] Update all remaining scripts to use database
- [ ] Remove Google Sheets dependencies
- [ ] Test all scripts end-to-end
- [ ] Verify workflow tracking

**Deliverables:**
- All 6 automation scripts database-enabled
- Google Sheets client marked deprecated

---

### Phase 5: Replit Deployment Configuration (3-4 hours)

#### 5.1 Configure Replit Secrets (30 min)

**Objective:** Set up secure secret management in Replit

**Tasks:**
- [ ] Add SHIPSTATION_API_KEY to Replit Secrets
- [ ] Add SHIPSTATION_API_SECRET to Replit Secrets
- [ ] Add GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY (migration only)
- [ ] Add SENDGRID_API_KEY (optional)
- [ ] Add DATABASE_PATH=/home/runner/ORA-Automation/ora.db

**Replit Secrets Panel:**
```
SHIPSTATION_API_KEY=<your_key>
SHIPSTATION_API_SECRET=<your_secret>
DATABASE_PATH=/home/runner/ORA-Automation/ora.db
GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY={"type":"service_account",...}
SENDGRID_API_KEY=<your_key>
```

**Deliverables:**
- All secrets configured
- Secrets accessible via `os.getenv()`

---

#### 5.2 Configure Reserved VM Deployment (1 hour)

**Objective:** Deploy always-on dashboard server

**Tasks:**
- [ ] Set up Reserved VM deployment
- [ ] Configure run command: `python -m http.server 5000`
- [ ] Set output type: webview
- [ ] Configure port: 5000
- [ ] Test dashboard accessibility

**Deployment Configuration:**
```yaml
Type: Reserved VM
Command: python -m http.server 5000
Port: 5000
Output: webview
```

**Deliverables:**
- Dashboard accessible 24/7
- Real-time data display verified

---

#### 5.3 Configure Scheduled Deployments (1-2 hours)

**Objective:** Automate all periodic tasks

**Tasks:**
- [ ] Configure Weekly Reporter: "Every Monday at 8 AM"
- [ ] Configure Daily Shipment Processor: "Every day at 9 AM"
- [ ] Configure Monthly Charge Report: "First day of month at 10 AM"
- [ ] Configure XML Polling: Reserved VM background task (5-min loop)

**Scheduled Deployments:**
| Workflow | Schedule | Command |
|----------|----------|---------|
| Weekly Reporter | Every Monday at 8 AM | `python src/weekly_reporter.py` |
| Daily Shipment Processor | Every day at 9 AM | `python src/daily_shipment_processor.py` |
| Monthly Charge Report | 1st of month at 10 AM | `python src/shipstation_reporter.py` |
| XML Polling | Continuous (5-min loop) | Background task |

**Deliverables:**
- All automation scheduled
- Logs accessible in Replit

---

#### 5.4 Database Maintenance Setup (1 hour)

**Objective:** Automated database health and backups

**Tasks:**
- [ ] Create daily health check script
- [ ] Create daily backup script (2 AM)
- [ ] Create weekly maintenance script (Sunday 3 AM)
- [ ] Set up backup retention (30 days)
- [ ] Configure monitoring alerts

**Maintenance Scripts:**
```bash
# Daily health check (8 AM)
scripts/daily_health_check.sh

# Daily backup (2 AM)
scripts/backup_database.sh

# Weekly maintenance (Sunday 3 AM)
scripts/weekly_maintenance.py
```

**Deliverables:**
- Automated maintenance configured
- Backup rotation working
- Health monitoring active

---

### Phase 6: Testing & Validation (3-4 hours)

#### 6.1 Integration Testing (1-2 hours)

**Objective:** End-to-end system validation

**Tasks:**
- [ ] Test complete order flow: XML → inbox → ShipStation → shipped
- [ ] Test inventory calculations with real data
- [ ] Test monthly charge report generation
- [ ] Verify dashboard displays all data correctly
- [ ] Test workflow status tracking
- [ ] Verify dark mode toggle persistence

**Test Scenarios:**
1. New order processing (XML to database)
2. Order upload to ShipStation
3. Daily shipment processing
4. Weekly inventory calculation
5. Monthly charge report generation
6. Dashboard real-time updates

**Deliverables:**
- Test results documented
- All workflows validated

---

#### 6.2 Performance Testing (1 hour)

**Objective:** Verify performance meets requirements

**Tasks:**
- [ ] Test with full data load (1 year history)
- [ ] Verify query performance (<500ms)
- [ ] Check database size (<100MB)
- [ ] Test concurrent access (dashboard + scripts)
- [ ] Monitor WAL file size

**Performance Metrics:**
- Dashboard load: < 2 seconds
- Query execution: < 500ms
- Database file: < 100MB
- Concurrent users: No locking issues

**Deliverables:**
- Performance benchmark report
- Optimization recommendations

---

#### 6.3 Monitoring & Logging Setup (1 hour)

**Objective:** Operational visibility and alerting

**Tasks:**
- [ ] Configure structured logging
- [ ] Set up error alerting
- [ ] Create monitoring dashboard
- [ ] Document troubleshooting procedures

**Monitoring Checklist:**
- [ ] Workflow execution logs
- [ ] Database health metrics
- [ ] Error rate tracking
- [ ] Performance metrics

**Deliverables:**
- Logging infrastructure
- Alert configuration
- Troubleshooting guide

---

### Phase 7: Cutover & Go-Live (2 hours)

#### 7.1 Production Cutover (1 hour)

**Objective:** Switch to production system

**Tasks:**
- [ ] Stop all Google Sheets-based workflows
- [ ] Switch to Replit-based workflows
- [ ] Monitor first 24 hours closely
- [ ] Verify all automation running
- [ ] Confirm data accuracy

**Cutover Checklist:**
- [ ] Google Sheets workflows stopped
- [ ] Replit workflows running
- [ ] Dashboard live
- [ ] No errors in logs
- [ ] Team notified

**Deliverables:**
- Production system live
- Monitoring active
- Support available

---

#### 7.2 Documentation & Handoff (1 hour)

**Objective:** Complete documentation and knowledge transfer

**Tasks:**
- [ ] Update replit.md with final configuration
- [ ] Document Replit secrets setup
- [ ] Create troubleshooting guide
- [ ] Archive Google Sheets (read-only)
- [ ] Document deprecation plan
- [ ] Create runbook for operations

**Documentation Updates:**
- Final architecture diagram
- Replit deployment guide
- Secret management procedures
- Backup/restore procedures
- Troubleshooting playbook

**Deliverables:**
- Complete documentation
- Google Sheets archived
- Knowledge transfer complete

---

## Project Timeline

### Week 1: Preparation & Migration

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| Mon | Phase 1.1-1.2 | 3h | Code fixes, unified secrets |
| Tue | Phase 1.3-1.4 | 3h | Error handling, testing |
| Wed | Phase 2 | 3h | Database setup complete |
| Thu | Phase 3.1 | 3h | ETL script ready |
| Fri | Phase 3.2-3.3 | 2h | Data migrated, validated |

### Week 2: Integration & Deployment

| Day | Phase | Hours | Key Deliverables |
|-----|-------|-------|------------------|
| Mon | Phase 4.1-4.3 | 3h | 3 scripts updated |
| Tue | Phase 4.4-4.5 | 3h | All scripts database-enabled |
| Wed | Phase 5 | 3h | Replit fully configured |
| Thu | Phase 6 | 3h | Testing complete |
| Fri | Phase 7 | 2h | Production go-live |

**Total: 28 hours** (includes buffer for issues)

---

## Risk Management

### Critical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Data loss during migration | Low | Critical | • Multiple backups before migration<br>• Dry-run testing<br>• Rollback procedure ready<br>• CSV exports as fallback |
| Type errors in production | Medium | High | • Fix all 57 LSP errors first<br>• Add comprehensive type hints<br>• Test with real data before cutover |
| Replit deployment issues | Low | Medium | • Test with small dataset first<br>• Keep GCP as fallback option<br>• Staged rollout approach |
| Performance degradation | Low | Medium | • Load test with 1 year data<br>• Monitor query execution times<br>• Optimize indexes proactively |
| Secret management failures | Low | High | • Test all secrets before cutover<br>• Maintain backup credentials<br>• Document fallback procedures |

### Mitigation Actions

**Before Migration:**
1. Complete code improvements (fix all LSP errors)
2. Create and test rollback procedures
3. Validate ETL with dry-run mode
4. Backup all Google Sheets data

**During Migration:**
1. Execute in stages with validation checkpoints
2. Monitor database integrity continuously
3. Keep Google Sheets as fallback
4. Team on standby for issues

**After Migration:**
1. 24-hour monitoring period
2. Daily data validation for first week
3. Weekly performance reviews
4. Gradual deprecation of Google Sheets

---

## Success Metrics

### Technical KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| LSP Diagnostics | 0 errors | Code analysis tool |
| Data Migration Accuracy | 100% row match | Automated validation |
| Database Size | <100MB | File system check |
| Dashboard Load Time | <2 seconds | Browser DevTools |
| Query Performance | <500ms | Database profiling |
| System Uptime | 99.9% | Replit monitoring |

### Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Monthly Charge Reports | 100% accurate | Finance validation |
| Inventory Tracking | Real-time | Dashboard verification |
| Order Processing | <5 min cycle | Workflow logs |
| Infrastructure Cost | $0/month | Billing confirmation |
| Automation Success Rate | >95% | Workflow statistics |

### Operational KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily Backups | 100% success | Backup logs |
| Error Alert Response | <1 hour | Incident tracking |
| Documentation Completeness | 100% | Checklist review |
| Team Training | 100% complete | Training records |

---

## Resource Requirements

### Development Tools
- Python 3.11+
- SQLite 3.37+ (STRICT tables support)
- Replit account (Core membership for scheduled deployments)
- Git for version control
- LSP/Pylance for type checking

### External Services
- ShipStation API (existing)
- Google Sheets API (migration only)
- SendGrid API (optional, for notifications)
- Google Drive (for XML file polling)

### Infrastructure
- Replit Reserved VM (dashboard + database)
- Replit Scheduled Deployments (automation scripts)
- Replit Secrets (API key management)

---

## Deliverables Checklist

### Code Artifacts
- [ ] `src/services/secrets.py` - Unified secret management
- [ ] `src/services/database/db_utils.py` - Database utilities
- [ ] `src/utils/error_handling.py` - Error handling framework
- [ ] `scripts/create_database.py` - Database schema creation
- [ ] `scripts/seed_database.py` - Initial data seeding
- [ ] `scripts/migrate_from_sheets.py` - ETL migration script
- [ ] Updated automation scripts (6 files)

### Database
- [ ] `ora.db` - Production SQLite database
- [ ] Daily backup script configured
- [ ] Weekly maintenance scheduled
- [ ] Monitoring queries implemented

### Documentation
- [ ] `docs/DATABASE_SCHEMA.md` - Complete schema (✅ Updated)
- [ ] `docs/MIGRATION_GUIDE.md` - Migration procedures (✅ Complete)
- [ ] `docs/DATABASE_OPERATIONS.md` - Operations guide (✅ Complete)
- [ ] `docs/API_INTEGRATION.md` - Integration patterns (✅ Complete)
- [ ] `docs/PROJECT_PLAN.md` - This document (✅ Complete)
- [ ] `replit.md` - Updated project overview (✅ Updated)

### Deployment
- [ ] Replit Reserved VM configured
- [ ] 4 Scheduled Deployments configured
- [ ] All secrets configured in Replit
- [ ] Monitoring and alerting active

---

## Communication Plan

### Stakeholders
- **Development Team:** Daily updates during migration
- **Business Users:** Weekly progress reports
- **Management:** Milestone completion notifications

### Status Updates
- **Daily:** During active development phases
- **Weekly:** Progress against timeline
- **Ad-hoc:** For critical issues or blockers

### Escalation Path
1. Developer identifies issue
2. Attempt resolution (30 min)
3. Document and escalate if unresolved
4. Team discussion for complex issues
5. Rollback if critical system impact

---

## Post-Launch Activities

### Week 1 Post-Launch
- [ ] Daily monitoring and validation
- [ ] Performance tuning as needed
- [ ] User feedback collection
- [ ] Issue resolution

### Week 2-4 Post-Launch
- [ ] Deprecate Google Sheets completely
- [ ] Archive historical Sheets data
- [ ] Optimize based on usage patterns
- [ ] Document lessons learned

### Ongoing
- [ ] Monthly performance reviews
- [ ] Quarterly capacity planning
- [ ] Continuous improvement based on metrics
- [ ] Feature enhancement roadmap

---

## Appendix

### A. Quick Reference Commands

**Database Management:**
```bash
# Create database
python scripts/create_database.py --output ora.db

# Seed initial data
python scripts/seed_database.py --database ora.db

# Run migration (dry-run)
python scripts/migrate_from_sheets.py --dry-run

# Run migration (production)
python scripts/migrate_from_sheets.py
```

**Automation Scripts:**
```bash
# Weekly reporter
python src/weekly_reporter.py

# Daily shipment processor
python src/daily_shipment_processor.py

# Monthly charge report
python src/shipstation_reporter.py
```

**Database Operations:**
```bash
# Daily health check
bash scripts/daily_health_check.sh

# Manual backup
bash scripts/backup_database.sh

# Weekly maintenance
python scripts/weekly_maintenance.py
```

### B. Important File Locations

**Source Code:**
- `/src/services/` - All service modules
- `/src/services/database/` - Database utilities
- `/scripts/` - Database and maintenance scripts

**Documentation:**
- `/docs/` - All technical documentation
- `/docs/DATABASE_SCHEMA.md` - Complete schema reference
- `/docs/MIGRATION_GUIDE.md` - Migration procedures

**Configuration:**
- `/config/settings.py` - Application configuration
- `.env` - Environment variables (local only)
- Replit Secrets - Production secrets

### C. Contact Information

**Technical Support:**
- Documentation: `/docs/` folder
- Issue tracking: Git issues
- Emergency rollback: See MIGRATION_GUIDE.md

---

## Project Sign-Off

**Prepared by:** Development Team  
**Date:** [Current Date]  
**Version:** 1.0  
**Status:** Ready for Implementation

---

**Next Steps:** Begin Phase 1 - Code Improvements & Preparation

For questions or clarifications, refer to the documentation in `/docs/` or contact the development team.

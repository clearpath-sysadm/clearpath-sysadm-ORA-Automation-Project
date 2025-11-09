# Oracare Action Planning Quick Reference

**Version:** 1.0  
**Created:** November 9, 2025  
**Purpose:** Oracare-specific supplement to the generic Action Planning System v1.1  
**Use With:** `ACTION-PLAN-TEMPLATE.md`, `EXECUTIVE-SUMMARY-TEMPLATE.md`

---

## 🎯 Quick Start

When creating an action plan for Oracare features, use this document **alongside** the generic templates to ensure all fulfillment-critical considerations are addressed.

**Process:**
1. Follow standard 7-section framework from `ACTION-PLAN-TEMPLATE.md`
2. Use this document for Oracare-specific context and risk categories
3. Generate executive summary using `EXECUTIVE-SUMMARY-TEMPLATE.md`

---

## 🏗️ Oracare System Context

### Core Architecture Components

**Database Layer:**
- PostgreSQL (Replit-managed, automatic backups)
- STRICT tables with proper constraints
- Foreign keys enforced for data integrity
- Money stored as INTEGER (cents) for precision
- UPSERT patterns with `ON CONFLICT` for idempotency
- Transaction handling with SAVEPOINT pattern for error isolation

**Key Tables:**
- `workflows` - Automation status tracking
- `inventory_current` - Real-time inventory levels
- `shipped_orders` / `shipped_items` - Shipment tracking
- `orders_inbox` - Order management (Ready to Ship, Needs Verification, etc.)
- `weekly_shipped_history` - 52-week rolling averages
- `system_kpis` - Dashboard metrics
- `bundle_skus` / `bundle_components` - SKU expansion logic
- `sku_lot` - Active lot tracking (FIFO inventory)
- `deleted_shipstation_orders` - Deletion audit trail
- `report_runs` - EOD/EOW/EOM execution logs

**Backend (Python/Flask):**
- `app.py` - Main Flask server with API endpoints
- `src/services/database/pg_utils.py` - Database utilities
- `src/services/reporting_logic/` - EOD/EOW calculation logic
- Authentication via Replit Auth (role-based: Admin/Viewer)

**Frontend:**
- `index.html` - Main dashboard (DEFAULT VIEW)
- `xml_import.html` - Orders Inbox (troubleshooting/inventory tool)
- `global-styles.css` - Centralized design system
- Premium corporate aesthetic (Oracare blue #2B7DE9, navy #1B2A4A)
- IBM Plex Sans typography

**7 Automation Workflows:**
1. `unified-shipstation-sync` - Status sync + manual order import (every 5 mins)
2. `xml-import` - Google Drive XML polling (continuous)
3. `shipstation-upload` - Upload pending orders to ShipStation (every 5 mins)
4. `duplicate-scanner` - Duplicate order detection (every 15 mins)
5. `lot-mismatch-scanner` - SKU-Lot validation
6. `orders-cleanup` - Delete old orders (daily)
7. `dashboard-server` - Flask web server

**External Integrations:**
- **ShipStation API** - Order uploads, shipment status sync
- **Google Drive** - XML file imports (X-Cart orders)
- **Replit Auth** - User authentication

---

## 🔍 Oracare-Specific Context Analysis

### Section 3 Enhancement: Gap Analysis for Oracare

When performing gap analysis, check against these **5 Oracare-specific context areas**:

#### 1. Database Schema & Integrity ✅
**Analyze:**
- Does feature require new tables or columns?
- Will it modify existing schema (migrations needed)?
- Foreign key implications (cascading deletes?)
- UPSERT pattern compliance (idempotent operations)?
- Transaction isolation requirements (SAVEPOINT usage)?
- Money precision (INTEGER cents vs DECIMAL)?

**Critical Check:**
- [ ] Zero data loss tolerance upheld
- [ ] Rollback strategy defined for schema changes
- [ ] Backup plan before destructive operations
- [ ] Migration tested against production data volume

#### 2. Automation Workflow Impact 🔄
**Analyze:**
- Which of the 7 workflows does this feature touch?
- Could it block/delay critical workflows (xml-import, shipstation-upload)?
- Does it introduce new dependencies between workflows?
- Will it affect workflow execution frequency/timing?
- Could it cause workflow failures or infinite loops?

**Critical Check:**
- [ ] 12 noon CST cutoff preserved (no delays in order processing)
- [ ] Workflow restart impact assessed
- [ ] Concurrent execution safety verified
- [ ] Workflow control toggles accessible (if needed)

#### 3. ShipStation API Integration 📦
**Analyze:**
- Does feature interact with ShipStation API?
- Will it create/read/update/delete orders in ShipStation?
- Lot number handling (SKU - LOT format)?
- Product name mapping requirements?
- Manual order handling (10xxxx order numbers)?
- Duplicate order prevention logic?

**Critical Check:**
- [ ] API rate limits respected (40 requests/min)
- [ ] Lot number source verified (`sku_lot` table with `active = 1`)
- [ ] Duplicate detection compatibility maintained
- [ ] ShipStation order deletion audit trail preserved

#### 4. Fulfillment Workflow Alignment 🎯
**Analyze:**
- How does this affect the 12 noon CST cutoff workflow?
- Impact on fulfillment person's monitoring activities?
- Does it change Orders Inbox usage patterns?
- Will it affect inventory receiving/adjustment workflows?
- Does it impact troubleshooting capabilities?

**Critical Check:**
- [ ] Dashboard remains default view (not Orders Inbox)
- [ ] Unit-based metrics maintained (not order counts)
- [ ] Real-time visibility preserved for operations
- [ ] Manual intervention capabilities retained

#### 5. Production Environment Constraints ⚙️
**Analyze:**
- Production vs development environment differences?
- Environment variable dependencies (`REPL_SLUG` checks)?
- Production log visibility (logs not visible in dev workspace)?
- Deployment impact (VM restart requirements)?
- Production database access (dev DB IS production DB)?

**Critical Check:**
- [ ] Production logging strategy defined
- [ ] No hardcoded environment assumptions
- [ ] Production troubleshooting plan documented
- [ ] Rollback mechanism available

---

## ⚠️ Oracare-Specific Risk Categories

### Section 5 Enhancement: Risk Assessment for Oracare

Add these **5 Oracare-specific risk categories** to the standard 6 generic risks:

#### Risk Category #7: Fulfillment Workflow Disruption ⏰

**Definition:** Could this feature delay, block, or interfere with the 12 noon CST order processing workflow?

**Assessment Questions:**
- Could it cause delays in XML import processing?
- Could it block ShipStation upload workflow?
- Could it interfere with EOD/EOW/EOM operations?
- Could it slow down dashboard API responses?

**Likelihood Factors:**
- Database query performance (slow queries = HIGH risk)
- Synchronous operations blocking workflows (HIGH risk)
- New workflow dependencies (MEDIUM risk)
- UI-only changes (LOW risk)

**Mitigation Strategies:**
- Background processing for heavy operations
- Async/non-blocking implementations
- Performance testing under load
- Workflow execution monitoring

**Example:**
```
Risk: New inventory calculation slows EOD by 10+ minutes
Likelihood: Medium | Impact: High | Overall: HIGH RISK
Mitigation: 
  - Cache intermediate calculations
  - Add progress indicators
  - Set timeout limits (120s)
  - Test with 52 weeks of data
```

---

#### Risk Category #8: Inventory Accuracy Degradation 📊

**Definition:** Could this feature cause lot number mismatches, inventory count errors, or FIFO logic violations?

**Assessment Questions:**
- Does it modify `sku_lot` table or lot assignment logic?
- Could it create discrepancies between database and ShipStation?
- Could it violate FIFO (first-in-first-out) inventory rules?
- Could it allow manual lot overrides without audit trail?

**Likelihood Factors:**
- Direct lot number manipulation (HIGH risk)
- Automated lot assignment changes (MEDIUM risk)
- Inventory calculation logic changes (MEDIUM risk)
- Display-only changes (LOW risk)

**Mitigation Strategies:**
- Maintain lot number audit trail
- Validate lot numbers against `sku_lot` table
- Prevent hardcoding of lot numbers
- Add inventory reconciliation checks

**Example:**
```
Risk: Manual lot editing bypasses validation, creates invalid SKU-LOT
Likelihood: Medium | Impact: High | Overall: HIGH RISK
Mitigation:
  - Database-driven dropdown (only active lots)
  - Foreign key constraint to sku_lot table
  - Audit log of all lot changes
  - ShipStation sync validation
```

---

#### Risk Category #9: ShipStation Sync Integrity ↔️

**Definition:** Could this feature create duplicate orders, sync failures, or data inconsistencies with ShipStation?

**Assessment Questions:**
- Does it modify order upload logic?
- Could it bypass duplicate detection?
- Could it create orphaned ShipStation orders?
- Could it interfere with status sync (awaiting_shipment → shipped)?

**Likelihood Factors:**
- Multi-SKU order handling (HIGH risk - known issue)
- Manual order creation (MEDIUM risk)
- Order deletion logic (HIGH risk - audit requirement)
- Status sync timing changes (MEDIUM risk)

**Mitigation Strategies:**
- SKU-aware duplicate detection (check overlapping SKUs)
- Preserve `deleted_shipstation_orders` audit trail
- Handle both `orderId` and `orderKey` in conflict checks
- Test with multi-SKU scenarios

**Example:**
```
Risk: New feature creates duplicate ShipStation orders for multi-SKU orders
Likelihood: High | Impact: High | Overall: CRITICAL RISK
Mitigation:
  - Use SKU-aware conflict detection
  - Check for overlapping SKUs (not just different SS IDs)
  - Preserve existing duplicate scanner logic
  - Add integration test with 2-SKU order
```

---

#### Risk Category #10: Database Integrity Violation 💾

**Definition:** Could this feature violate the zero data loss tolerance or corrupt production data?

**Assessment Questions:**
- Does it perform destructive database operations (DELETE, DROP)?
- Could it cause foreign key violations?
- Could it create data orphans (records without parents)?
- Does it handle transaction rollbacks properly?

**Likelihood Factors:**
- Raw SQL with DELETE/UPDATE (HIGH risk)
- Schema migrations (MEDIUM risk)
- UPSERT without conflict handling (MEDIUM risk)
- Read-only queries (LOW risk)

**Mitigation Strategies:**
- Use SAVEPOINT pattern for error isolation
- Require explicit user approval for destructive ops
- Test migrations on production data copy
- Maintain comprehensive audit trails

**Example:**
```
Risk: Order cleanup deletes records still needed for EOW reporting
Likelihood: Low | Impact: Critical | Overall: HIGH RISK
Mitigation:
  - 60-day retention window (not 30)
  - Exclude orders with unprocessed weekly_shipped_history
  - Dry-run mode first (log what would be deleted)
  - User confirmation required
```

---

#### Risk Category #11: Production Incident Response 🚨

**Definition:** Could this feature make production troubleshooting harder or hide critical errors?

**Assessment Questions:**
- Does it change logging behavior?
- Could it suppress errors that need visibility?
- Does it make production logs harder to read?
- Could it interfere with incident investigation?

**Likelihood Factors:**
- Error handling that swallows exceptions (HIGH risk)
- Changes to logging verbosity (MEDIUM risk)
- Production-only code paths (MEDIUM risk)
- Dev-only changes (LOW risk)

**Mitigation Strategies:**
- Preserve detailed production logging
- Ensure errors propagate to visible logs
- Document production troubleshooting procedures
- Test error scenarios in production-like environment

**Example:**
```
Risk: New error handling hides ShipStation API failures
Likelihood: Medium | Impact: High | Overall: HIGH RISK
Mitigation:
  - Log all API errors with full context
  - Surface critical errors in dashboard alerts
  - Preserve error details in database
  - Add monitoring for API failure rates
```

---

## 🎯 Fulfillment-Critical Considerations

### Must-Check Items for Every Oracare Action Plan

#### 1. Zero Data Loss Compliance ✅
**Requirement:** No feature may result in data loss under any circumstances.

**Verification:**
- [ ] Destructive operations require explicit user approval
- [ ] Soft deletes preferred over hard deletes (or audit trail required)
- [ ] Database transactions properly scoped
- [ ] Rollback strategy documented and tested
- [ ] Backup strategy defined for risky operations

---

#### 2. 12 Noon CST Cutoff Protection ⏰
**Requirement:** Order processing must complete reliably by 12:00 PM Central.

**Verification:**
- [ ] No synchronous operations blocking XML import workflow
- [ ] No performance regressions in ShipStation upload workflow
- [ ] Dashboard API responses remain fast (< 2s)
- [ ] Workflow execution times measured and acceptable
- [ ] No new dependencies that could delay processing

---

#### 3. Unit-Based Metrics Consistency 📊
**Requirement:** All metrics display units (not order counts) throughout system.

**Verification:**
- [ ] Dashboard KPIs show units shipped (not orders)
- [ ] Reports calculate unit totals (not order totals)
- [ ] Alerts based on unit thresholds (not order thresholds)
- [ ] Exception: Charge reports may show order counts for billing

---

#### 4. Lot Number Traceability 🔢
**Requirement:** All lot assignments must be traceable to `sku_lot` table with `active = 1`.

**Verification:**
- [ ] No hardcoded lot numbers in code
- [ ] Lot numbers sourced from `sku_lot WHERE active = 1`
- [ ] Lot changes create audit trail
- [ ] Manual lot edits validated against database
- [ ] Repacks with old lots supported (valid use case)

---

#### 5. Production Environment Awareness 🌐
**Requirement:** Development database IS production database (only one exists).

**Verification:**
- [ ] No assumptions about separate dev/prod databases
- [ ] Production logs require manual sharing from user
- [ ] Environment checks use `REPL_SLUG` correctly
- [ ] Troubleshooting procedures documented for production
- [ ] User warned about production impact of destructive operations

---

## 📋 Oracare Action Plan Checklist

Use this checklist when creating action plans for Oracare features:

### Pre-Planning Phase
- [ ] Read full feature request and understand user context
- [ ] Review `replit.md` for latest system architecture
- [ ] Check current database schema for affected tables
- [ ] Identify which workflows will be impacted

### Section 1: Feature Requirements
- [ ] Standard checklist from template
- [ ] **Oracare Add:** Specify which workflows are affected
- [ ] **Oracare Add:** Identify database tables touched
- [ ] **Oracare Add:** Clarify production vs dev environment expectations

### Section 2: Technical Implementation
- [ ] Standard checklist from template
- [ ] **Oracare Add:** Verify all imports exist in codebase
- [ ] **Oracare Add:** Confirm database utilities use pg_utils patterns
- [ ] **Oracare Add:** Check lot number sourcing (no hardcoded values)

### Section 3: Gap Analysis
- [ ] Standard 5 context areas analyzed
- [ ] **Oracare Add:** Database Schema & Integrity check
- [ ] **Oracare Add:** Automation Workflow Impact check
- [ ] **Oracare Add:** ShipStation API Integration check
- [ ] **Oracare Add:** Fulfillment Workflow Alignment check
- [ ] **Oracare Add:** Production Environment Constraints check
- [ ] Gap closure feedback loop completed
- [ ] Gap closure summary table shows all gaps closed

### Section 4: Optimization Strategy
- [ ] Standard checklist from template
- [ ] **Oracare Add:** Database query performance assessed
- [ ] **Oracare Add:** Workflow execution time impact estimated

### Section 5: Risk Assessment
- [ ] Standard 6 risk categories assessed
- [ ] **Oracare Add:** Fulfillment Workflow Disruption risk
- [ ] **Oracare Add:** Inventory Accuracy Degradation risk
- [ ] **Oracare Add:** ShipStation Sync Integrity risk
- [ ] **Oracare Add:** Database Integrity Violation risk
- [ ] **Oracare Add:** Production Incident Response risk
- [ ] Risk matrix includes ALL 11 risk categories
- [ ] Every risk has mitigation strategy

### Section 6: Deployment Process
- [ ] Standard checklist from template
- [ ] **Oracare Add:** Workflow restart plan documented
- [ ] **Oracare Add:** Production database backup strategy
- [ ] **Oracare Add:** Rollback procedure tested

### Section 7: Executive Summary
- [ ] Standard checklist from template
- [ ] **Oracare Add:** Production impact clearly stated
- [ ] **Oracare Add:** Data loss risks highlighted (if any)
- [ ] **Oracare Add:** Workflow downtime estimated (if any)

### Final Readiness Review
- [ ] All tech stack items verified to exist
- [ ] File paths checked for accuracy
- [ ] Every risk has mitigation
- [ ] Gap solutions applied to requirements
- [ ] No placeholder text (TODO, TBD, etc.)
- [ ] **Oracare Add:** Zero data loss compliance verified
- [ ] **Oracare Add:** 12 noon cutoff impact assessed

---

## 🚀 Quick Examples

### Example 1: Low-Risk UI Change
**Feature:** Add dark mode toggle to dashboard

**Oracare Context:**
- ✅ No database changes
- ✅ No workflow impact
- ✅ No ShipStation integration
- ✅ No fulfillment disruption
- ✅ No production risk

**Risk Level:** LOW (mostly CSS/frontend)

---

### Example 2: Medium-Risk Feature Addition
**Feature:** Add inventory reorder notifications

**Oracare Context:**
- ⚠️ New database table: `inventory_alerts`
- ⚠️ Impacts EOD workflow (calculates alerts)
- ✅ No ShipStation integration
- ⚠️ Could delay EOD processing if slow
- ⚠️ Production emails sent

**Risk Level:** MEDIUM (workflow + database changes)

**Key Risks:**
- Fulfillment Workflow Disruption (alert calculation time)
- Database Integrity (new table with foreign keys)
- Production Incident Response (email failures)

---

### Example 3: High-Risk Core Change
**Feature:** Modify lot assignment algorithm (FIFO logic)

**Oracare Context:**
- 🚨 Modifies `sku_lot` table logic
- 🚨 Impacts ShipStation upload workflow
- 🚨 Changes inventory accuracy calculations
- 🚨 Affects fulfillment person's manual lot edits
- 🚨 Production critical (zero error tolerance)

**Risk Level:** HIGH (core fulfillment logic)

**Key Risks:**
- Inventory Accuracy Degradation (FIFO violations)
- ShipStation Sync Integrity (lot format changes)
- Database Integrity (existing lot data migration)
- Fulfillment Workflow Disruption (upload failures)
- Production Incident Response (hard to troubleshoot)

**Mitigation Requirements:**
- Extensive testing with production data copy
- Rollback plan with data restore procedure
- Parallel run (old + new logic) for validation
- User approval at every phase
- Production monitoring for 48 hours post-deploy

---

## 📚 Reference Documents

**Always Use Together:**
1. `ACTION-PLAN-TEMPLATE.md` - Generic 7-section framework
2. `EXECUTIVE-SUMMARY-TEMPLATE.md` - Decision document format
3. **This document** - Oracare-specific considerations

**Additional Resources:**
- `replit.md` - Current system architecture
- `docs/RCA_LOT_NUMBER_UPLOAD_MISMATCHES_Nov_7_2025.md` - Lot number investigation
- `docs/FUNCTIONAL_REQUIREMENTS.md` - System requirements

---

## 🎯 Quick Decision Tree

**When planning a feature, ask:**

1. **Does it touch the database?**
   - YES → Use Risk Categories #2, #10 (Data Integrity, Database Violation)
   - NO → Skip database-specific risks

2. **Does it affect workflows?**
   - YES → Use Risk Category #7 (Fulfillment Workflow Disruption)
   - NO → Minimal workflow analysis needed

3. **Does it interact with ShipStation?**
   - YES → Use Risk Category #9 (ShipStation Sync Integrity)
   - NO → Skip ShipStation-specific analysis

4. **Does it modify lot tracking?**
   - YES → Use Risk Category #8 (Inventory Accuracy) + extensive testing
   - NO → Standard inventory checks

5. **Is it production-critical?**
   - YES → Use Risk Category #11 (Production Incident Response)
   - NO → Standard incident planning

---

## ✅ Success Criteria

**An Oracare action plan is complete when:**

- [ ] All 7 standard sections complete
- [ ] All 5 Oracare context areas analyzed
- [ ] All 11 risk categories assessed (6 generic + 5 Oracare)
- [ ] Zero data loss compliance verified
- [ ] 12 noon cutoff impact documented
- [ ] Production troubleshooting plan included
- [ ] User approval obtained before implementation

---

**Use this document alongside the generic templates for comprehensive, Oracare-aware action planning!** 🚀

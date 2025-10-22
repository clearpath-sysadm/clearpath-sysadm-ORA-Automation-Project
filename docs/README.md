# ORA Automation Documentation

This directory contains all project documentation organized into 5 main categories for easy navigation.

## 📁 Directory Structure

### Root-Level Documents
- **[PROJECT_JOURNAL.md](PROJECT_JOURNAL.md)** - Chronological log of all development work and milestones
- **[PRODUCTION_INCIDENT_LOG.md](PRODUCTION_INCIDENT_LOG.md)** - Critical issues, root cause analysis, and resolutions
- **README.md** (this file) - Documentation organization guide

---

### 1. 🎯 [features/](features/)
**Feature planning and implementation documentation**

Contains design documents, implementation plans, and technical specifications for system features:
- EOD/EOW/EOM button system design
- Optimized polling implementation plans
- Unified ShipStation sync architecture
- Lot number validation and auto-update logic
- Workflow control system design
- Bug fix documentation

**Key Files:**
- `EOD_EOW_EOM_BUTTON_SYSTEM.md` - Physical inventory controls design
- `UNIFIED_SHIPSTATION_SYNC_PLAN.md` - Status sync and manual order import
- `OPTIMIZED_POLLING_IMPLEMENTATION_PLAN_V3_FINAL.md` - Latest polling optimization
- `WORKFLOW_CONTROL_IMPLEMENTATION_PLAN.md` - Workflow management system

---

### 2. 🏗️ [architecture/](architecture/)
**System architecture, database design, and project planning**

Contains high-level system design, database schemas, and project requirements:
- Database schema and normalization
- Project requirements and specifications
- System architecture decisions

**Key Files:**
- `DATABASE_SCHEMA.md` - Complete database structure documentation
- `PROJECT_PLAN.md` - Overall project roadmap
- `REQUIREMENTS.md` - System requirements specification
- `database-normalization-v2-0.md` - Database normalization work

---

### 3. 🔧 [operations/](operations/)
**User manuals and operational guides**

Contains documentation for system operators and end users:
- User manuals for dashboard and features
- Workflow control guides
- Database operations reference

**Key Files:**
- `USER_MANUAL.md` - Complete system user guide
- `WORKFLOW_CONTROLS_USER_MANUAL.md` - Workflow management instructions
- `DATABASE_OPERATIONS.md` - Database maintenance and operations

---

### 4. 🔌 [integrations/](integrations/)
**API and authentication integration documentation**

Contains integration guides for external services and APIs:
- ShipStation API integration
- Google Drive integration
- Authentication requirements and analysis

**Key Files:**
- `API_INTEGRATION.md` - External API integration guide
- `auth-requirements-analysis.md` - Authentication system analysis
- `auth-requirements-questionnaire.md` - Auth implementation questionnaire

---

### 5. 📜 [historical/](historical/)
**Historical remediation and fix documentation**

Contains documentation of past issues, migrations, and remediation efforts:
- SQLite to PostgreSQL migration (October 2025)
- Manual orders remediation (October 2025)
- Duplicate order detection and cleanup
- Historical bug fixes and corrections
- Legacy planning documents

**Key Files:**
- `SQLITE_TO_POSTGRESQL_REMEDIATION_PLAN.md` - Database migration documentation
- `MANUAL_ORDERS_COMPLETE_HISTORY.md` - Manual orders fix history
- `REMEDIATION_PLAN.md` - Duplicate order remediation
- `DUPLICATE_DETECTION_FIX.md` - Duplicate detection system fixes
- `PLAN_CORRECTIONS.md` - Historical plan corrections

---

## 🔍 Quick Reference

### For New Team Members
1. Start with `PROJECT_JOURNAL.md` for project history
2. Review `architecture/REQUIREMENTS.md` for system requirements
3. Read `operations/USER_MANUAL.md` for system usage
4. Check `PRODUCTION_INCIDENT_LOG.md` for known issues

### For Developers
1. `features/` - Feature specifications before implementation
2. `architecture/DATABASE_SCHEMA.md` - Database structure
3. `integrations/` - API integration guides
4. `historical/` - Learn from past issues and fixes

### For Operators
1. `operations/USER_MANUAL.md` - Daily operation guide
2. `operations/WORKFLOW_CONTROLS_USER_MANUAL.md` - System controls
3. `PRODUCTION_INCIDENT_LOG.md` - Production issue tracking

### For Database Work
- See `architecture/DATABASE_SCHEMA.md` for schema reference
- Check `operations/DATABASE_OPERATIONS.md` for procedures
- Review `historical/SQLITE_TO_POSTGRESQL_REMEDIATION_PLAN.md` for migration history

---

## 📝 Documentation Standards

- **Active Documentation:** Keep root-level docs (PROJECT_JOURNAL, PRODUCTION_INCIDENT_LOG) up to date
- **Historical Preservation:** Old remediation docs go to `historical/` for reference
- **Feature Planning:** New features start in `features/` with implementation plans
- **Incident Tracking:** All production issues documented in PRODUCTION_INCIDENT_LOG.md
- **Naming Convention:** Use UPPERCASE with underscores for filenames (e.g., `FEATURE_NAME.md`)

---

*Last Updated: October 2025*

# Documentation Directory

This directory contains all project documentation, organized by category for easy navigation.

## 📁 Directory Structure

### `/planning`
Architecture, requirements, and project planning documents
- `PROJECT_PLAN.md` - Overall project plan and roadmap
- `REQUIREMENTS.md` - System requirements and specifications
- `DATABASE_SCHEMA.md` - Complete database schema documentation
- `database-normalization-v2-0.md` - Database normalization work

### `/features`
Feature implementation plans and summaries
- `UNIFIED_SHIPSTATION_SYNC_PLAN.md` - Unified sync workflow design
- `UNIFIED_SYNC_SUMMARY.md` - Sync implementation summary
- `WORKFLOW_CONTROL_IMPLEMENTATION_PLAN.md` - Workflow controls feature
- `LOT_NUMBER_VALIDATION_PLAN.md` - Lot number validation system
- `shipstation-upload-bug-fixes.md` - ShipStation upload fixes

### `/integrations`
API and authentication documentation
- `API_INTEGRATION.md` - External API integration guide
- `auth-requirements-analysis.md` - Authentication requirements analysis
- `auth-requirements-questionnaire.md` - Auth implementation questionnaire

### `/operations`
User manuals and operational documentation
- `USER_MANUAL.md` - System user manual
- `WORKFLOW_CONTROLS_USER_MANUAL.md` - Workflow controls guide
- `DATABASE_OPERATIONS.md` - Database operation procedures

### `/duplicate-remediation`
Duplicate order remediation project documentation
- `README.md` - Project overview
- `REMEDIATION_PLAN.md` - Remediation strategy
- `ASSUMPTIONS.md` - Key assumptions and constraints
- `DUPLICATE_DETECTION_FIX.md` - Detection algorithm fixes
- `QUICK_REFERENCE.md` - Quick reference guide

## 📂 Related Documentation

### Migration Documentation
Migration-related documentation is located in the `/migration` folder at the project root:
- `MIGRATION_GUIDE.md` - Step-by-step migration guide
- `MIGRATION_LOG.md` - Complete migration execution log
- `COMPARISON_REPORT.md` - SQLite vs PostgreSQL comparison
- `POSTGRESQL_MIGRATION_PLAN.md` - Original migration plan
- `POSTGRESQL_MIGRATION_PLAN_OPTIMIZED.md` - Optimized migration plan
- `analysis_report.md` - Pre-migration analysis

## 🔍 Finding Documentation

**For developers:**
- Start with `/planning` to understand system architecture
- Check `/features` for specific feature implementation details
- Refer to `/integrations` for API integration guidance

**For users:**
- Start with `/operations/USER_MANUAL.md`
- Use `/operations/WORKFLOW_CONTROLS_USER_MANUAL.md` for workflow management

**For database work:**
- See `/planning/DATABASE_SCHEMA.md` for schema reference
- Check `/operations/DATABASE_OPERATIONS.md` for procedures
- Review `/migration` folder for PostgreSQL migration history

## 📝 Contributing

When adding new documentation:
1. Place it in the appropriate category folder
2. Use clear, descriptive filenames in UPPERCASE with underscores
3. Update this README if adding a new category
4. Cross-reference related documents when applicable

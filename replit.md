# ORA Automation Project

## Overview
Business automation dashboard for ORA (Oracare) that monitors inventory, shipments, and automation workflows. The system replaces Google Sheets with a SQLite database and provides real-time visibility through a professional web interface.

**Design Constraints:**
- Lowest possible cost (zero-cost infrastructure preferred)
- Minimal development time (10-13 hour budget)
- Complete replacement of Google Sheets with database backend

## Project Architecture

### Database Layer (SQLite with WAL)
**Decision:** SQLite chosen over PostgreSQL for zero cost, minimal setup, and sufficient performance
- **Database:** `ora.db` with Write-Ahead Logging (WAL) mode
- **12 Tables:** Complete schema replacing all Google Sheets functionality
- **Location:** `docs/DATABASE_SCHEMA.md` for full schema documentation

**Core Tables:**
- `workflows` - Automation workflow tracking
- `inventory_current` - Current stock levels and alerts
- `inventory_transactions` - All inventory movements (audit trail)
- `shipped_items` - Individual line items from shipments
- `shipped_orders` - Complete shipment records
- `weekly_shipped_history` - Aggregated weekly shipment data
- `system_kpis` - Daily business metrics snapshots
- `configuration_params` - Business configuration (replaces ORA_Configuration sheet)
- `orders_inbox` - Staging area for incoming orders before ShipStation upload
- `order_items_inbox` - Line items for orders in inbox
- `polling_state` - XML file polling state for 5-minute order detection
- `schema_migrations` - Database version tracking

### Main Entry Points
- `src/weekly_reporter.py` - Calculates inventory levels and weekly averages
- `src/daily_shipment_processor.py` - Fetches shipments from ShipStation API and stores in database
- `src/shipstation_order_uploader.py` - Uploads orders from inbox to ShipStation
- `src/shipstation_reporter.py` - **Generates monthly charge reports** (orders, packages, space rental) + weekly inventory reports
- `src/main_order_import_daily_reporter.py` - Daily import summary reporter
- **NEW:** XML Polling Service (5-minute intervals) - Detects new orders from Google Drive

### Key Services
- `src/services/database/db_utils.py` - Database connection management and utilities
- `src/services/google_sheets/api_client.py` - Google Sheets API (migration only, will be deprecated)
- `src/services/shipstation/` - ShipStation API integration
- `src/services/reporting_logic/` - Business logic for reports and calculations
- `src/services/gcp/` - Google Cloud Platform integrations

### Frontend
- `index.html` - Dashboard UI with real-time KPI cards, workflow status, inventory alerts
- **Features:** Dark mode toggle with localStorage persistence, responsive design
- **Data Source:** Direct SQLite queries (replacing Google Sheets API calls)

## Current Setup in Replit

**Workflows:**
- `dashboard-server` - Web server for dashboard UI (port 5000)
- `weekly-reporter` - Inventory calculation automation

**Environment:** 
- Python 3.11 with all required dependencies installed
- SQLite database with WAL mode enabled
- VM deployment configured (stateful application)

**Deployment:**
- Type: VM (maintains server state)
- Port: 5000 (dashboard webview)

## External Dependencies & Integrations

**Available Replit Integrations:**
- Google Sheets connector (for one-time migration ETL)
- SendGrid connector (for email notifications)

**Required API Keys:**
- ShipStation API credentials (order upload and shipment tracking)
- Google Cloud Secret Manager (for production credentials)
- SendGrid API key (optional, for email notifications)

## Technical Documentation

**Core Documentation (High Priority):**
1. ✅ `docs/DATABASE_SCHEMA.md` - Complete SQLite schema with 12 tables, PRAGMA settings, indexing strategy
2. ✅ `docs/MIGRATION_GUIDE.md` - Step-by-step Google Sheets to SQLite migration guide
3. ✅ `docs/DATABASE_OPERATIONS.md` - Daily operations, maintenance, and troubleshooting
4. ✅ `docs/API_INTEGRATION.md` - How automation scripts integrate with database
5. ✅ `docs/REQUIREMENTS.md` - Original business requirements and constraints

**Future Documentation (Lower Priority):**
- `docs/BACKUP_RECOVERY.md` - Comprehensive backup and disaster recovery
- `docs/DEVELOPMENT_GUIDE.md` - Developer onboarding and coding standards
- `docs/SCHEMA_EVOLUTION.md` - Managing database changes over time
- `docs/PERFORMANCE_TUNING.md` - Query optimization and scaling guidance
- `docs/DATA_DICTIONARY.md` - Business glossary and data definitions

## Recent Changes

**Database Architecture (December 2024):**
- Designed complete SQLite schema replacing Google Sheets
- Expert reviews confirm SQLite as optimal choice (vs PostgreSQL)
- Added critical constraints: STRICT tables, foreign keys, CHECK constraints, indexes
- Configured production PRAGMA settings for performance and concurrency
- Implemented money storage as INTEGER (cents) instead of DECIMAL
- Created comprehensive migration and operations documentation

**Dashboard Enhancements:**
- Functional dark mode toggle with moon/sun icons
- localStorage persistence for theme preference
- Responsive design for all screen sizes

**Documentation:**
- Created 4 comprehensive technical documents (SCHEMA, MIGRATION, OPERATIONS, API_INTEGRATION)
- Documented data flow from XML files → orders_inbox → ShipStation → shipped_orders
- Established maintenance schedules and backup procedures

## Database Migration Status

**Current State:** Google Sheets (legacy system)
**Target State:** SQLite database (replacement)

**Migration Phases:**
1. ✅ Schema Design - Complete (12 tables with constraints and indexes)
2. ✅ Documentation - Complete (migration guide, operations, API integration)
3. ⏳ Database Setup - Pending (create production database)
4. ⏳ ETL Development - Pending (build one-time migration script)
5. ⏳ Script Integration - Pending (update 5 automation scripts)
6. ⏳ Cutover - Pending (switch to database, deprecate Sheets)

**Estimated Remaining Time:** 10-13 hours for complete migration

## Data Flow

**Current (Google Sheets):**
```
X-Cart XML → Manual Processing → Google Sheets → Dashboard
```

**Target (SQLite Database):**
```
X-Cart XML → XML Polling Service (5 min) → orders_inbox
  → ShipStation Uploader → ShipStation API
  → Daily Shipment Processor → shipped_orders/shipped_items
  → Weekly Reporter → inventory_current + weekly_shipped_history
  → Dashboard UI (real-time queries)
```

## User Preferences

**Development Philosophy:**
- Lowest cost infrastructure (SQLite over hosted databases)
- Minimal development time (pragmatic over perfect)
- Complete replacement, not augmentation (deprecate Google Sheets entirely)
- Real-time visibility for business operations
- Automated workflows with manual oversight capability

**Technical Preferences:**
- SQLite with WAL mode for concurrency
- STRICT tables with proper constraints
- Foreign keys enforced for data integrity
- Money stored as INTEGER (cents) for precision
- UPSERT patterns for idempotent operations
- Transaction handling with BEGIN IMMEDIATE

## Usage Notes

**Production Deployment:**
The system is designed for production deployment with:
- Daily automated backups (2 AM)
- Weekly maintenance (VACUUM if >25% free space)
- Integrity checks and monitoring
- 30-day backup retention
- Point-in-time recovery capability

**Development Mode:**
Set `DEV_MODE=1` environment variable to use test fixtures instead of live APIs during development.

**Monitoring:**
- Database health checks (daily at 8 AM)
- Workflow status tracking in `workflows` table
- System KPIs snapshots in `system_kpis` table
- Performance metrics and slow query logging

## Next Steps

**Immediate (Database Implementation):**
1. Create production SQLite database with schema
2. Build ETL script from Google Sheets
3. Migrate data with validation
4. Update automation scripts to use database
5. Switch dashboard to database queries
6. Deprecate Google Sheets

**Future Enhancements:**
- Real-time order notifications
- Predictive inventory alerts
- Advanced analytics and reporting
- Mobile-responsive dashboard improvements

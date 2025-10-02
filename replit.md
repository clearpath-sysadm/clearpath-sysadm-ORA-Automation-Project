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
- `xml-import-scheduler` - Automated XML import from Google Drive (every 5 minutes)

**Environment:** 
- Python 3.11 with all required dependencies installed
- SQLite database with WAL mode enabled
- VM deployment configured (stateful application)

**Deployment:**
- Type: VM (maintains server state)
- Port: 5000 (dashboard webview)

## External Dependencies & Integrations

**Available Replit Integrations:**
- ✅ Google Drive connector (OAuth2 for XML file import from folder)
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

**Completed Documentation:**
- ✅ `docs/DATABASE_SCHEMA.md` - Complete SQLite schema with 12 tables
- ✅ `docs/MIGRATION_GUIDE.md` - Step-by-step Google Sheets to SQLite migration
- ✅ `docs/DATABASE_OPERATIONS.md` - Daily operations, maintenance, troubleshooting
- ✅ `docs/API_INTEGRATION.md` - How automation scripts integrate with database
- ✅ `docs/REQUIREMENTS.md` - Original business requirements and constraints
- ✅ `docs/PROJECT_PLAN.md` - Final 13-hour MVP implementation plan (architect approved)

**Future Documentation (Phase 2):**
- `docs/BACKUP_RECOVERY.md` - Comprehensive backup and disaster recovery
- `docs/DEVELOPMENT_GUIDE.md` - Developer onboarding and coding standards
- `docs/SCHEMA_EVOLUTION.md` - Managing database changes over time
- `docs/PERFORMANCE_TUNING.md` - Query optimization and scaling guidance
- `docs/DATA_DICTIONARY.md` - Business glossary and data definitions

## Recent Changes

**Phase 4 Complete - Script Migration (October 2025):**
- ✅ weekly_reporter.py fully migrated to SQLite (replaces Google Sheets API)
- ✅ daily_shipment_processor.py fully migrated with ShipStation API integration
- ✅ Successfully fetched 854 shipments, stored 770 orders + 847 items
- ✅ 52-week rolling averages maintained (263 weekly history records)
- ✅ Workflow tracking operational (status, duration, records_processed)
- ✅ All database UPSERT operations idempotent
- ✅ ShipStation credentials configured in Replit Secrets

**Phase 5.1 Complete - Dashboard UI/UX (October 2025):**
- ✅ Auto-refresh every 60 seconds with Page Visibility API pause
- ✅ Manual refresh button with loading states
- ✅ Skeleton loaders for all dashboard sections
- ✅ Error handling with inline error banners
- ✅ "Last updated" timestamp with relative time display
- ✅ Clickable inventory alerts

**Manual Sync Feature Complete (October 2025):**
- ✅ API endpoint `/api/sync_shipstation` triggers ShipStation data refresh
- ✅ Green "Sync ShipStation" button on Shipped Items and Shipped Orders pages
- ✅ Background thread processing with 120-second timeout

**Google Drive XML Import Integration (October 2025):**
- ✅ Integrated Replit Google Drive connector with OAuth2 authentication
- ✅ Created `src/services/google_drive/api_client.py` with Replit connection functions
- ✅ API endpoints: `/api/google_drive/list_files` and `/api/google_drive/import_file/<file_id>`
- ✅ Simplified XML Import page with one-click "Import from Google Drive" button
- ✅ Automatically finds and imports orders.xml from Google Drive folder
- ✅ **Automated Import:** `src/scheduled_xml_import.py` runs every 5 minutes
- ✅ **Data Expiration:** Automatically deletes orders older than 60 days (2 months)
- ✅ Workflow `xml-import-scheduler` continuously monitors Google Drive
- ✅ Fixed download bug: added null check for status.progress() in MediaIoBaseDownload
- ✅ Fixed dark mode toggle null pointer error in index.html
- ✅ **Tested successfully:** Imported 96 orders from orders.xml to orders_inbox
- ✅ Google Drive folder ID: `1rNudeesa_c6q--KIKUAOLwXta_gyRqAE`
- ✅ Clean UX: Single button workflow (no file listing or manual upload needed)

**Dashboard Enhancements (October 2025):**
- ✅ Changed first stat card from "Today's Orders" to "Units to Ship"
- ✅ Displays total quantity from order_items_inbox (pending orders)
- ✅ FedEx trailer pickup alert triggers when units >= 185
- ✅ Alert displays FedEx phone number: 651-846-0590 (clickable link)
- ✅ Alert auto-shows/hides based on current units to ship
- ✅ Updated dashboard JavaScript to properly handle FedEx alert visibility

**Database Architecture (December 2024):**
- Designed complete SQLite schema replacing Google Sheets
- Expert reviews confirm SQLite as optimal choice (vs PostgreSQL)
- Added critical constraints: STRICT tables, foreign keys, CHECK constraints, indexes
- Configured production PRAGMA settings for performance and concurrency
- Implemented money storage as INTEGER (cents) instead of DECIMAL
- Created comprehensive migration and operations documentation

**Documentation:**
- Created 4 comprehensive technical documents (SCHEMA, MIGRATION, OPERATIONS, API_INTEGRATION)
- Documented data flow from XML files → orders_inbox → ShipStation → shipped_orders
- Established maintenance schedules and backup procedures
- Updated PROJECT_PLAN.md with Phase 4.3 and 5.1 completion status

## Database Migration Status

**Current State:** ✅ SQLite database fully operational with 3,000+ rows across all tables
**Legacy System:** Google Sheets (deprecated, migration complete)
**Status:** Phase 4 complete, Phase 5 (Dashboard API) in progress

**Migration Approach:** MVP-first strategy (13 hours total)

**Migration Phases:**
1. ✅ Schema Design - COMPLETE (8 tables with constraints and 14 indexes)
2. ✅ Documentation - COMPLETE (migration guide, operations, API integration, PROJECT_PLAN)
3. ✅ Project Plan - COMPLETE (architect approved 13-hour optimized plan)
4. ✅ Database Setup - COMPLETE (8 tables created, seeded with test data)
5. ✅ ETL Development - COMPLETE (600+ line migration script with validation)
6. ✅ Historical Data Migration - COMPLETE (917 historical rows migrated from Google Sheets)
   - configuration_params: 32 rows
   - inventory_transactions: 28 rows
   - shipped_orders: 598 historical + 770 current = 1,368 total
   - shipped_items: 847 rows (from ShipStation API)
   - weekly_shipped_history: 263 weeks (52-week rolling averages maintained)
7. ✅ Script Integration - COMPLETE (weekly_reporter + daily_shipment_processor)
   - All Google Sheets API calls eliminated
   - Transaction context manager for atomicity
   - Workflow tracking with status/duration/records_processed
   - Tested with real ShipStation API: 1,819 records processed
8. ⏳ Dashboard API - IN PROGRESS (Flask API for real-time data)
9. ⏳ Replit Deployment - Ready to start (Core plan, Scheduled Deployments confirmed)
10. ⏳ Cutover - Pending (switch scripts to database, deprecate Sheets)

**Timeline:** 13 hours (3-4 business days)
**Infrastructure:** Replit Core ($25/month) with Scheduled Deployments

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

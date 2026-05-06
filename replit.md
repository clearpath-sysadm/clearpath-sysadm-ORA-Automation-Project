# Oracare Fulfillment System
A production-ready order management platform that replaces legacy Google Sheets with a PostgreSQL database, managing inventory, shipments, and automation workflows for Oracare's fulfillment operations.

## Run & Operate
- **Run:** `python3 app.py` (Flask server) or `bash start_all.sh` (all workflows)
- **Environment Variables:**
    - `DATABASE_URL`: PostgreSQL connection string
    - `REPLIT_DB_URL`: Replit Database URL
    - `DEV_WORKERS_ACTIVE`: Set to `true` to enable scheduled workers in development.
    - `LOG_LEVEL`: Configures server logging verbosity (e.g., `INFO`, `DEBUG`).
    - `GOOGLE_SERVICE_ACCOUNT_KEY`: Google service account credentials for Drive access.
- **Database Migrations:** _Populate as you build_

## Stack
- **Backend:** Python 3.11, Flask
- **Database:** PostgreSQL (Replit-managed)
- **Frontend:** HTML with centralized CSS design system
- **Authentication:** Replit Auth with role-based access (Admin, Operations, Viewer)
- **ORM:** _Populate as you build_
- **Validation:** _Populate as you build_
- **Build Tool:** _Populate as you build_

## Where things live
- `app.py`: Main Flask application and API endpoints.
- `src/scheduled_*.py`: Automation workflow scripts.
- `src/unified_shipstation_sync.py`: Handles ShipStation status synchronization and manual order imports.
- `static/global-styles.css`: Centralized CSS design system.
- `TECHNICAL_DOCUMENTATION.md`: Comprehensive technical reference.
- `start_all.sh`: Production startup script for all services.
- `config/settings.py`: Application settings and configurations.

## Architecture decisions
- **PostgreSQL over Google Sheets:** Replaced Google Sheets for robust data persistence, real-time visibility, and zero data loss tolerance.
- **Unit-based Metrics:** All fulfillment, shipping, and inventory workflows are driven and displayed by unit counts, not order counts.
- **Strict SKU-Lot Validation:** Critical validation enforces that ShipStation never receives orders without valid SKU-Lot mappings.
- **Idempotent Operations:** Utilizes UPSERT patterns with `ON CONFLICT` clauses to ensure data consistency and prevent duplicates during concurrent operations.
- **Business Hours Optimization:** Workflows are optimized to run only during business hours (Monday-Friday 6 AM - 6 PM CT) to reduce compute usage by 64%.

## Product
- **Order Management:** Tracks orders from import through shipment.
- **Inventory Management:** Real-time inventory, lot tracking, and daily snapshots.
- **Automated Workflows:** Scheduled processes for XML import, ShipStation upload, lot tagging, and batch processing.
- **Reporting:** Provides various reports including charge reports and weekly shipping history.
- **User Activity Tracking:** Monitors user interactions with key system endpoints.
- **Admin Tools:** Features for workflow control, incident management, and data diagnostics (e.g., ShipStation backfill, unit comparison, recreate order).

## User preferences
- **Development Philosophy:**
    - Production-ready infrastructure (PostgreSQL for data persistence)
    - Minimal development time (pragmatic over perfect)
    - Complete replacement, not augmentation (deprecate Google Sheets entirely)
    - Real-time visibility for business operations
    - Automated workflows with manual oversight capability
    - Zero data loss tolerance
- **Operational Context:**
    - **Environment:** When troubleshooting, issues typically occur in PRODUCTION, not development workspace
    - **Production Logs:** Production logs are NOT visible in the development workspace. User must manually share production log file contents when troubleshooting production issues
    - **Database Note:** Development and Production have SEPARATE databases. Changes made in the dev workspace database do NOT affect production data. Schema changes and migrations must be applied to both environments.
- **Business Rules:**
    - **Unit-based metrics:** Display only unit counts (not order counts) throughout the system. Units are the driving factor for all fulfillment, shipping, and inventory workflows.
    - **SKU-Lot Validation (CRITICAL):** ShipStation should NEVER have orders without valid SKU-Lot mappings. The upload service enforces:
        1. Global Check: If `sku_lot` table has no active mappings, ABORT entire upload
        2. Item-Level Check: Individual items without lot numbers are SKIPPED
        3. Order-Level Check: Orders with NO valid items are marked as 'failed'
    - **Duplicate Prevention:** Multi-layered protection including atomic claiming (`FOR UPDATE SKIP LOCKED`), ShipStation API checks, and sync status preservation
- **Fulfillment Workflow Context:**
    - **12 noon CST cutoff:** Orders accumulate until 12:00 PM Central Standard Time
    - **Work happens in ShipStation:** Fulfillment processes orders entirely in ShipStation
    - **System role:** ORDER MANAGEMENT tool for monitoring and troubleshooting
    - **Default view:** Dashboard (not Orders Inbox)
- **Technical Preferences:**
    - PostgreSQL with Replit-managed database
    - STRICT tables with proper constraints and foreign keys
    - Money stored as INTEGER (cents) for precision
    - UPSERT patterns with ON CONFLICT for idempotent operations

## Gotchas
- **Dev/Prod Isolation:** Scheduled workers are silenced in dev by default (`DEV_WORKERS_ACTIVE` unset). Enable only when actively developing to avoid unintended production interactions.
- **Production Logs:** Production logs are not accessible from the development environment; they must be provided manually for troubleshooting.
- **Database Discrepancy:** Development and production databases are separate. Schema changes and migrations must be applied to both environments.
- **Inventory Deduction:** Historically, inventory deduction for existing orders transitioning to 'shipped' status was missing, leading to inaccurate inventory records. A backfill script exists to correct past discrepancies.
- **ShipStation Webhook:** The `ORDER_NOTIFY` webhook is exclusively registered and owned by the production environment. Development environments rely on periodic polling for order reconciliation.

## Pointers
- **Technical Documentation:** `TECHNICAL_DOCUMENTATION.md` for in-depth system details.
- **API Endpoints:** Refer to `app.py` for a comprehensive list of API endpoints.
- **Workflow Scripts:** Examine `src/scheduled_*.py` and `src/unified_shipstation_sync.py` for automation logic.
- **Google Drive API:** `src/services/google_drive/api_client.py` for Google Drive integration details.
- **ShipStation API:** Consult ShipStation API documentation for integration specifics.
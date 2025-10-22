# ORA Automation Project

> **📓 Project Journal:** For a chronological log of all development work and milestones, see [`/docs/PROJECT_JOURNAL.md`](docs/PROJECT_JOURNAL.md)
>
> **🚨 Production Incidents:** For critical issues, root cause analysis, and resolutions, see [`/docs/PRODUCTION_INCIDENT_LOG.md`](docs/PRODUCTION_INCIDENT_LOG.md)
>
> **🧪 Test Suite:** For automated tests verifying critical functionality, see [`/tests/`](tests/)

## Overview
The ORA Automation Project replaces Google Sheets with a PostgreSQL database for managing inventory, shipments, and automation workflows. Its core purpose is to provide a production-ready, zero-data-loss solution that fully deprecates the legacy Google Sheets system, transforming manual processes into automated, database-driven workflows. This project delivers a robust, real-time operational dashboard for Oracare, offering improved visibility and efficiency in business automation.

**Database Migration (October 2025):** Successfully migrated from SQLite to PostgreSQL to prevent catastrophic data loss on Replit deployments where "Republish" would replace production database with dev snapshot. Migration completed with 100% data integrity (2,864 rows in 4 seconds) using smart database adapter pattern for automatic PostgreSQL/SQLite switching based on DATABASE_URL. Critical post-migration fixes: (1) Resolved ON CONFLICT constraint mismatch in `shipped_items` table (changed from `(ship_date, sku_lot, order_number)` to `(order_number, base_sku, sku_lot)` to match actual UNIQUE constraint), eliminating recurring sync errors and enabling successful watermark advancement. (2) Manually migrated 5 critical `lot_inventory` baseline records (11,330 units from Sept 19, 2025) that were accidentally omitted from migration script. (3) Fixed Orders Inbox UI bug where class name mismatch (`table-container` vs `orders-table-container`) caused mobile card views to display simultaneously with desktop table, creating confusing mixed-format display. (4) **Final SQLite remediation (Oct 15, 2025):** Fixed 14 remaining SQLite placeholders in `app.py` (mixed `?` and `%s` syntax) that broke inventory transaction CRUD and other endpoints after PostgreSQL migration. All queries now use PostgreSQL `%s` placeholders exclusively. (5) Fixed `weekly_reporter.py` PostgreSQL compatibility bug (replaced SQLite's `julianday()` with `EXTRACT(EPOCH FROM ...)`) and re-enabled weekly-reporter workflow. (6) Added comprehensive global form element and modal styles to `global-styles.css` affecting all 13 pages: inputs, selects, textareas with focus states, custom dropdown arrows, modal overlay with backdrop blur, and form groups.

## User Preferences
- **Development Philosophy:**
    - Production-ready infrastructure (PostgreSQL for data persistence)
    - Minimal development time (pragmatic over perfect)
    - Complete replacement, not augmentation (deprecate Google Sheets entirely)
    - Real-time visibility for business operations
    - Automated workflows with manual oversight capability
    - Zero data loss tolerance
- **Technical Preferences:**
    - PostgreSQL with Replit-managed database (automatic backups, rollback support)
    - STRICT tables with proper constraints
    - Foreign keys enforced for data integrity
    - Money stored as INTEGER (cents) for precision
    - UPSERT patterns with ON CONFLICT for idempotent operations
    - Transaction handling with SAVEPOINT pattern for error isolation

## System Architecture
The system is centered around a PostgreSQL database, replacing all functionality previously handled by 14 Google Sheets. The user interface is an enterprise-grade web dashboard designed with a premium corporate aesthetic, featuring a deep navy (#1B2A4A) and accent orange (#F2994A) palette, IBM Plex Sans typography, a left sidebar navigation, and full responsiveness. It displays real-time KPI cards (including Benco and Hawaiian order tracking), workflow status, inventory alerts, and supports light/dark modes with glass effects. The dashboard directly queries the PostgreSQL database via Flask API endpoints.

**Global Stylesheet Architecture:**
A single centralized `global-styles.css` (25KB) defines the premium corporate design system used across all 13 HTML pages, ensuring consistency and ease of maintenance. This includes the color palette, typography (IBM Plex Sans body + Source Serif 4 hero stats), design tokens, component library (buttons, cards, tables, forms, modals, sidebars), light/dark mode with navy glass sidebar effect, responsive breakpoints, and an elevation system. Page-specific styles are contained in `dashboard-specific.css` (3.3KB).

**Core Services & Entry Points:**
- **Database Layer:** PostgreSQL (migrated from SQLite October 2025). Schema is documented in `docs/DATABASE_SCHEMA.md`. Key tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox`, `system_kpis`, `bundle_skus`, `bundle_components`, and `sku_lot`. The `configuration_params` table stores critical settings. The `InitialInventory` baseline date is September 19, 2025, and these values are protected from modification. Database operations use smart adapter pattern (`src/services/database/db_adapter.py`) for PostgreSQL/SQLite compatibility.
- **Backend Automation (Python scripts):**
    - **Unified ShipStation Sync (`src/unified_shipstation_sync.py`):** Production workflow that combines status sync and manual order import into single watermark-based process running every 5 minutes. Features comprehensive emoji-based logging, transaction-safe watermarking with 14-day lookback window, and only advances watermark on successful processing (zero errors). Replaces deprecated `manual_shipstation_sync.py` and `shipstation_status_sync.py`.
    - **Physical Inventory Controls (DESIGN COMPLETE):** User-driven button triggers (EOD/EOW/EOM) replacing time-based automations. EOD syncs shipped items for daily inventory updates, EOW generates weekly reports with 52-week averages, EOM generates monthly charge reports. Simplified design eliminates cascading dependencies. Full requirements documented in `/docs/features/EOD_EOW_EOM_BUTTON_SYSTEM.md`.
    - **Weekly Reporter (`src/weekly_reporter.py`):** Calculates 52-week rolling averages for inventory. Triggered on-demand via EOW button or manually.
    - **XML Polling Service:** Continuously monitors Google Drive every 5 minutes for new order XML files, automatically expanding bundle SKUs.
    - **ShipStation Upload Service (`src/scheduled_shipstation_upload.py`):** **[CRITICAL - ONLY UPLOADER]** Automatically uploads pending orders from `orders_inbox` to ShipStation every 5 minutes, applying correct SKU-Lot mappings from `sku_lot` table (where active=1) and product name mappings. Handles duplicates and updates order status. **This is the ONLY service that should upload orders to ShipStation.** Legacy upload files (shipstation_order_uploader.py, ShipStation_Importer.py, manual_shipstation_sync.py) have been archived to `src/legacy_archived/` and must not be used.
    - **Orders Cleanup Service (`src/scheduled_cleanup.py`):** Daily deletion of `orders_inbox` entries older than 60 days, maintaining `shipped_orders` for history.
    - **Duplicate Order Monitoring System (`src/scheduled_duplicate_scanner.py`):** Real-time monitoring workflow that scans ShipStation every 15 minutes for duplicate order numbers (orders sharing the same order_number). Features 90-day lookback window for comprehensive coverage. **CRITICAL SAFETY DESIGN:** Auto-resolution is intentionally disabled to prevent data loss from API failures, pagination errors, or query window limitations. All duplicate alerts require manual operator verification and resolution via dashboard. System preserves existing alerts on scan failures and only updates workflow timestamps on successful scans for monitoring capabilities. Alerts stored in `duplicate_order_alerts` table with full ShipStation record details for operator review. Dashboard displays real-time alert banner with "View Details" modal showing all duplicate records (ShipStation IDs, customers, statuses, timestamps) and one-click resolution capability.
    - **Environment Protection System:** Upload service (`src/scheduled_shipstation_upload.py`) uses belt-and-suspenders dual-layer protection to prevent dev uploads. REPL_SLUG takes absolute priority over ENVIRONMENT variable - any workspace environment (REPL_SLUG contains "workspace") is blocked regardless of ENVIRONMENT setting. Workflow-level check puts service to sleep, function-level failsafe blocks individual uploads. Production deployments work normally with same codebase. See `/docs/PRODUCTION_INCIDENT_LOG.md` for Oct 22, 2025 environment detection fix.
    - **Duplicate Order Remediation Tools:** Historical cleanup utilities (`utils/`) for identifying, backing up, and deleting duplicate orders from ShipStation using smart strategies (prioritizing active lot numbers or earliest orders) with dry-run and execution modes.
- **Frontend:** `index.html` serves as the dashboard, offering a complete enterprise layout with two-tier navigation (Dashboard, Orders Inbox, Weekly Reports, Inventory Monitor, etc.), card-based components, and responsive design. Features include auto-refresh, skeleton loaders, and error handling. It displays 6 key operational KPIs.
- **Bundle SKU System:** Database-driven management (`bundle_skus.html`) with full CRUD capabilities and automatic expansion during import.
- **SKU Lot Management:** Database-driven tracking (`sku_lot.html`) for SKU-Lot combinations with CRUD support and a unique constraint. UI formats SKU-Lot values for display.
- **Lot Inventory Management (`lot_inventory.html`):** Auto-calculated FIFO inventory tracking per lot, based on initial quantities, manual adjustments, and shipped quantities.
- **Workflow Controls System:** A programmatic system allowing on/off toggling for all automation workflows via the `workflow_controls` database table and a UI (`workflow_controls.html`). Changes persist and workflows respond within 60 seconds.
- **Shipping Validation System:** An alert-only system that compares actual carrier/service information from ShipStation against expected rules (e.g., Hawaiian orders → FedEx 2Day). Violations are stored in `shipping_violations` and displayed on the dashboard with resolution capabilities.
- **Deployment:** The system is deployed as a continuous VM in Replit, using `start_all.sh` to launch the dashboard server and all 7 background automation workflows in parallel.

## External Dependencies
- **ShipStation API:** Used for order uploads and shipment status synchronization.
- **Google Drive:** Integrated via Replit connector for XML file imports.
- **SendGrid:** (Optional) For email notifications.
- **Google Cloud Secret Manager:** For secure management of production credentials.
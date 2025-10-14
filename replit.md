# ORA Automation Project

## Overview
The ORA Automation Project replaces Google Sheets with a SQLite database for managing inventory, shipments, and automation workflows. Its core purpose is to provide a zero-cost, minimal development time solution that fully deprecates the legacy Google Sheets system, transforming manual processes into automated, database-driven workflows. This project delivers a robust, real-time operational dashboard for Oracare, offering improved visibility and efficiency in business automation.

## User Preferences
- **Development Philosophy:**
    - Lowest cost infrastructure (SQLite over hosted databases)
    - Minimal development time (pragmatic over perfect)
    - Complete replacement, not augmentation (deprecate Google Sheets entirely)
    - Real-time visibility for business operations
    - Automated workflows with manual oversight capability
- **Technical Preferences:**
    - SQLite with WAL mode for concurrency
    - STRICT tables with proper constraints
    - Foreign keys enforced for data integrity
    - Money stored as INTEGER (cents) for precision
    - UPSERT patterns for idempotent operations
    - Transaction handling with BEGIN IMMEDIATE

## System Architecture
The system is centered around a SQLite database (`ora.db`) operating in WAL mode, replacing all functionality previously handled by 14 Google Sheets. The user interface is an enterprise-grade web dashboard designed with a premium corporate aesthetic, featuring a deep navy (#1B2A4A) and accent orange (#F2994A) palette, IBM Plex Sans typography, a left sidebar navigation, and full responsiveness. It displays real-time KPI cards (including Benco and Hawaiian order tracking), workflow status, inventory alerts, and supports light/dark modes with glass effects. The dashboard directly queries the SQLite database via Flask API endpoints.

**Global Stylesheet Architecture:**
A single centralized `global-styles.css` (25KB) defines the premium corporate design system used across all 13 HTML pages, ensuring consistency and ease of maintenance. This includes the color palette, typography (IBM Plex Sans body + Source Serif 4 hero stats), design tokens, component library (buttons, cards, tables, forms, modals, sidebars), light/dark mode with navy glass sidebar effect, responsive breakpoints, and an elevation system. Page-specific styles are contained in `dashboard-specific.css` (3.3KB).

**Core Services & Entry Points:**
- **Database Layer:** SQLite with WAL mode. Schema is documented in `docs/DATABASE_SCHEMA.md`. Key tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox`, `system_kpis`, `bundle_skus`, `bundle_components`, and `sku_lot`. The `configuration_params` table stores critical settings. The `InitialInventory` baseline date is September 19, 2025, and these values are protected from modification. Migrations are managed in the `migrations/` directory.
- **Backend Automation (Python scripts):**
    - **Unified ShipStation Sync (PLANNED):** Combines status sync and manual order sync into single watermark-based workflow running every 5 minutes. Shadow mode deployment with 48-hour validation before cutover. See `docs/UNIFIED_SHIPSTATION_SYNC_PLAN.md`.
    - **Physical Inventory Controls (PLANNED):** User-driven button triggers (EOD/EOW/EOM) replacing time-based automations. EOD syncs shipped orders for physical count verification, EOW generates weekly inventory reports, EOM creates monthly charge reports. Smart dependency management ensures prerequisite syncs run automatically.
    - **Weekly Reporter (`src/weekly_reporter.py`):** Calculates 52-week rolling averages for inventory. Triggered on-demand via EOW button or manually.
    - **XML Polling Service:** Continuously monitors Google Drive every 5 minutes for new order XML files, automatically expanding bundle SKUs.
    - **ShipStation Upload Service (`src/scheduled_shipstation_upload.py`):** Automatically uploads pending orders from `orders_inbox` to ShipStation every 5 minutes, applying SKU-Lot mappings and product name mappings. Handles duplicates and updates order status.
    - **ShipStation Status Sync (`src/shipstation_status_sync.py`):** Runs hourly to update local database order statuses from ShipStation (shipped, cancelled, etc.) and moves shipped orders to `shipped_orders`. *Will be replaced by Unified Sync.*
    - **Manual Order Sync (`src/manual_shipstation_sync.py`):** Runs hourly to detect and import orders created directly in ShipStation, parsing SKU-lot formats for inventory tracking. *Will be replaced by Unified Sync.*
    - **Orders Cleanup Service (`src/scheduled_cleanup.py`):** Daily deletion of `orders_inbox` entries older than 60 days, maintaining `shipped_orders` for history.
    - **Duplicate Order Remediation System:** Tools (`utils/`) for identifying, backing up, and cleaning up historical duplicate orders in ShipStation based on a smart strategy (prioritizing active lot numbers or earliest orders) with dry-run and execution modes.
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
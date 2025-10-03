# ORA Automation Project

## Overview
The ORA Automation Project aims to replace Google Sheets with a SQLite database for managing inventory, shipments, and automation workflows. This project provides a real-time business automation dashboard, offering improved visibility and efficiency. The core purpose is to achieve a zero-cost, minimal development time solution that fully deprecates the legacy Google Sheets system, transforming manual processes into automated, database-driven workflows. The ambition is to provide a robust, real-time operational dashboard for Oracare.

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
The system is built around a SQLite database (`ora.db`) with WAL mode, replacing all Google Sheets functionality across 14 tables. The UI is an **enterprise-grade web dashboard** (`index.html`) with left sidebar navigation, professional design system (Inter font, neutral colors, 8px grid), and fully responsive mobile support. It features real-time KPI cards (including Benco and Hawaiian order tracking), workflow status, inventory alerts, dark mode, and directly queries the SQLite database via Flask API endpoints.

**Core Services & Entry Points:**
- **Database Layer:** SQLite with WAL mode for zero cost and performance. Schema is documented in `docs/DATABASE_SCHEMA.md`. Tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox` (30 columns including ship/bill address fields), `system_kpis`, `bundle_skus`, `bundle_components`, and `sku_lot`. Configuration stored in `configuration_params` table (pallet counts, key products, initial inventory). Migrations stored in `migrations/` directory for schema changes.
- **Backend Automation:** Python scripts handle core logic:
    - `src/weekly_reporter.py`: Calculates inventory and weekly averages.
    - `src/daily_shipment_processor.py`: Fetches ShipStation data.
    - `src/shipstation_order_uploader.py`: Uploads orders to ShipStation.
    - `src/shipstation_reporter.py`: Generates monthly charge and weekly inventory reports.
    - `src/main_order_import_daily_reporter.py`: Daily import summary.
    - **XML Polling Service:** Continuously monitors Google Drive for new orders from XML files every 5 minutes. Bundle SKUs are automatically expanded into component SKUs during import.
    - **ShipStation Upload Service:** Automatically uploads pending orders from `orders_inbox` to ShipStation every 5 minutes (`src/scheduled_shipstation_upload.py`). Applies SKU-Lot mappings from `sku_lot` table and product name mappings from configuration. Creates one ShipStation order per SKU with proper address fields. Detects and skips duplicates. Updates order status to 'uploaded' on success or 'failed' with error details.
    - **ShipStation Status Sync:** Runs hourly (`src/shipstation_status_sync.py`) to check uploaded orders for status changes. When orders are shipped/cancelled in ShipStation, updates local database and moves shipped orders to `shipped_orders` table. Supports statuses: pending, uploaded, shipped, cancelled, on_hold, awaiting_payment, failed, synced_manual.
    - **Manual Order Sync:** Runs hourly (`src/manual_shipstation_sync.py`) to detect and import orders created manually in ShipStation (not originated from local system). Identifies manual orders by checking if ShipStation order ID exists in `shipstation_order_line_items` table. Handles SKU-lot format (e.g., "17612 - 250237") by parsing into base_sku and sku_lot for proper inventory tracking. Backfill utility available at `utils/backfill_manual_orders.py` for historical recovery. **Known limitation**: Duplicate ShipStation order numbers (rare) will keep most recent version only.
    - **Orders Cleanup Service:** Runs daily (`src/scheduled_cleanup.py`) to automatically delete orders older than 60 days from `orders_inbox` table. Preserves `shipped_orders` for historical reporting. Maintains data hygiene with configurable retention period.
    - **Backfill Utilities:** `src/backfill_shipstation_ids.py` populates missing ShipStation IDs in `orders_inbox` and `shipped_orders` tables by querying ShipStation API. One-time utility for data integrity restoration.
- **Frontend:** `index.html` provides the dashboard UI with a complete enterprise layout, including a two-tier navigation system (Dashboard, Orders Inbox, Weekly Reports, Inventory Monitor, Bundle SKUs Management, SKU Lot Management, etc.), a neutral color palette, card-based components, and responsive design. It includes features like auto-refresh, manual refresh, skeleton loaders, and error handling. Dashboard displays 6 operational KPI cards: Units to Ship, Pending Uploads, Shipments Sent (7 days), Benco Orders, Hawaiian Orders, and System Status.
- **Bundle SKU System:** Database-driven bundle management system (`bundle_skus.html`) with full CRUD capabilities. Bundles automatically expand to component SKUs during XML import (both scheduled and manual). REST API endpoints: GET/POST/PUT/DELETE `/api/bundles`, GET `/api/bundle_components/:id`. Supports single-component (e.g., 18225 → 40× 17612) and multi-component bundles (e.g., 18615 → 4 components).
- **SKU Lot Management:** Database-driven SKU-Lot tracking system (`sku_lot.html`) with full CRUD capabilities. Manages SKU-Lot combinations with active/inactive status. REST API endpoints: GET/POST/PUT/DELETE `/api/sku_lots`. UNIQUE constraint on (sku, lot) combination prevents duplicates. Stores 12 active SKU-Lot records for tracking.
- **Key Services:** Database utilities (`db_utils.py`), ShipStation API integration, reporting logic, and Google Cloud Platform integrations.
- **Deployment:** Configured as a VM deployment in Replit using `start_all.sh` startup script that launches all automation workflows in parallel. Runs continuously on Reserved VM ($20/month, covered by Core plan credits). All processes start automatically on deployment: dashboard server (port 5000), XML polling (5 min), ShipStation upload (5 min), status sync (hourly), manual order sync (hourly), cleanup (daily), units refresh, and weekly reporter. Single deployment runs all 7 background automation workflows plus dashboard.
- **Shipping Validation System (COMPLETE):** ALERT-ONLY system (does NOT modify ShipStation orders). Database tracks carrier/service info in 4 fields (`shipping_carrier_code`, `shipping_carrier_id`, `shipping_service_code`, `shipping_service_name`) added to both `orders_inbox` and `shipped_orders` tables. Status sync (`src/shipstation_status_sync.py`) and manual order sync (`src/manual_shipstation_sync.py`) both capture actual carrier/service/carrier_id from ShipStation after upload. Validation service (`src/services/shipping_validator.py`) compares actual vs. expected for 3 rules: (1) Hawaiian (HI state)→FedEx 2Day, (2) Canadian (CA/CANADA country)→FedEx International Ground, (3) Benco (company contains "BENCO")→Benco FedEx carrier account (requires BENCO_CARRIER_IDS configuration). Violations stored in `shipping_violations` table with resolved status tracking. REST API endpoints: GET `/api/shipping_violations`, PUT `/api/shipping_violations/:id/resolve`. Sticky yellow alert banner on dashboard (`index.html`) shows violation count and summary. Modal displays detailed violation list with resolve buttons. System is cross-page persistent and auto-refreshes.

## External Dependencies
- **ShipStation API:** For order uploading and shipment tracking.
- **Google Drive:** Integrated via Replit connector for XML file import.
- **Google Sheets API:** Used for one-time migration ETL (will be deprecated).
- **SendGrid:** (Optional) For email notifications.
- **Google Cloud Secret Manager:** For managing production credentials.
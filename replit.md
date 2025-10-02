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
The system is built around a SQLite database (`ora.db`) with WAL mode, replacing all Google Sheets functionality across 14 tables. The UI is an **enterprise-grade web dashboard** (`index.html`) with left sidebar navigation, professional design system (Inter font, neutral colors, 8px grid), and fully responsive mobile support. It features real-time KPI cards, workflow status, inventory alerts, dark mode, and directly queries the SQLite database via Flask API endpoints.

**Core Services & Entry Points:**
- **Database Layer:** SQLite with WAL mode for zero cost and performance. Schema is documented in `docs/DATABASE_SCHEMA.md`. Tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox`, `system_kpis`, `bundle_skus`, `bundle_components`, and `sku_lot`.
- **Backend Automation:** Python scripts handle core logic:
    - `src/weekly_reporter.py`: Calculates inventory and weekly averages.
    - `src/daily_shipment_processor.py`: Fetches ShipStation data.
    - `src/shipstation_order_uploader.py`: Uploads orders to ShipStation.
    - `src/shipstation_reporter.py`: Generates monthly charge and weekly inventory reports.
    - `src/main_order_import_daily_reporter.py`: Daily import summary.
    - **XML Polling Service:** Continuously monitors Google Drive for new orders from XML files every 5 minutes. Bundle SKUs are automatically expanded into component SKUs during import.
- **Frontend:** `index.html` provides the dashboard UI with a complete enterprise layout, including a two-tier navigation system (Dashboard, Orders Inbox, Weekly Reports, Inventory Monitor, Bundle SKUs Management, SKU Lot Management, etc.), a neutral color palette, card-based components, and responsive design. It includes features like auto-refresh, manual refresh, skeleton loaders, and error handling.
- **Bundle SKU System:** Database-driven bundle management system (`bundle_skus.html`) with full CRUD capabilities. Bundles automatically expand to component SKUs during XML import (both scheduled and manual). REST API endpoints: GET/POST/PUT/DELETE `/api/bundles`, GET `/api/bundle_components/:id`. Supports single-component (e.g., 18225 → 40× 17612) and multi-component bundles (e.g., 18615 → 4 components).
- **SKU Lot Management:** Database-driven SKU-Lot tracking system (`sku_lot.html`) with full CRUD capabilities. Manages SKU-Lot combinations with active/inactive status. REST API endpoints: GET/POST/PUT/DELETE `/api/sku_lots`. UNIQUE constraint on (sku, lot) combination prevents duplicates. Stores 12 active SKU-Lot records for tracking.
- **Key Services:** Database utilities (`db_utils.py`), ShipStation API integration, reporting logic, and Google Cloud Platform integrations.
- **Deployment:** Configured as a VM deployment in Replit, serving the dashboard on port 5000, with scheduled workflows like `weekly-reporter` and `xml-import-scheduler`.

## External Dependencies
- **ShipStation API:** For order uploading and shipment tracking.
- **Google Drive:** Integrated via Replit connector for XML file import.
- **Google Sheets API:** Used for one-time migration ETL (will be deprecated).
- **SendGrid:** (Optional) For email notifications.
- **Google Cloud Secret Manager:** For managing production credentials.
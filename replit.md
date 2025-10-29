# Oracare Fulfillment System

## Overview
The Oracare Fulfillment System replaces Google Sheets with a PostgreSQL database to manage inventory, shipments, and automation workflows. Its core purpose is to provide a production-ready, zero-data-loss solution that fully deprecates the legacy Google Sheets system, transforming manual processes into automated, database-driven workflows. This project delivers a robust, real-time operational dashboard for Oracare, offering improved visibility and efficiency in business automation.

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
The system is centered around a PostgreSQL database, replacing all functionality previously handled by 14 Google Sheets. The user interface is an enterprise-grade web dashboard designed with a premium corporate aesthetic, featuring Oracare's professional blue (#2B7DE9) and deep navy (#1B2A4A) color palette, IBM Plex Sans typography, official Oracare logo, a left sidebar navigation, and full responsiveness. The dashboard displays real-time KPI cards, workflow status, inventory alerts, and supports light/dark modes with glass effects. Access is secured via Replit Auth with role-based permissions (Admin/Viewer). The dashboard directly queries the PostgreSQL database via Flask API endpoints with centralized authentication middleware.

**UI/UX Decisions:**
A single centralized `global-styles.css` defines the premium corporate design system used across all 13 HTML pages, ensuring consistency. This includes the color palette, typography (IBM Plex Sans body + Source Serif 4 hero stats), design tokens, component library (buttons, cards, tables, forms, modals, sidebars), light/dark mode with navy glass sidebar effect, responsive breakpoints, and an elevation system.

**Technical Implementations & Feature Specifications:**
- **Database Layer:** PostgreSQL is the core data store. The schema is documented in `docs/DATABASE_SCHEMA.md`. Key tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox`, `system_kpis`, `bundle_skus`, `bundle_components`, and `sku_lot`. The `configuration_params` table stores critical settings. The `InitialInventory` baseline date is September 19, 2025, and these values are protected from modification.
  - **Order Update Safety:** All order updates (tracking status, tracking numbers, timestamps) are blocked until `shipstation_order_id` is synced. This prevents data integrity issues with orders imported from XML that haven't been uploaded to ShipStation yet.
  - **Manual Orders (10xxxx):** Orders with numbers in the range 100000-109999 are MANUAL ORDERS created directly in ShipStation by operators, NOT imported from XML or uploaded by the system. These orders will NEVER have a `shipstation_order_id` populated by the upload service in `orders_inbox`. They are tracked locally for inventory purposes only. The Manual Order Conflicts detection system monitors for collisions when the same 10xxxx order number appears with different ShipStation IDs.
- **Replit Auth:** Implemented with role-based access control (Admin/Viewer roles) using Flask-Dance OAuth, supporting multiple login methods. It uses a dual database architecture (psycopg2 for business logic, SQLAlchemy for auth) and centralized API authentication middleware protecting ~80 endpoints.
- **Backend Automation (Python scripts):**
    - **Unified ShipStation Sync:** A production workflow combining status sync and manual order import, running every 5 minutes. Includes real-time tracking status polling, transaction-safe watermarking, and ghost order backfill to repair orders with missing items.
    - **Physical Inventory Controls:** User-driven buttons for End-of-Day (EOD), End-of-Week (EOW), and End-of-Month (EOM) operations to sync shipped items, generate weekly reports, and produce monthly charge reports.
    - **XML Polling Service:** Continuously monitors Google Drive for new order XML files and automatically expands bundle SKUs.
    - **ShipStation Upload Service:** Automatically uploads pending orders from `orders_inbox` to ShipStation every 5 minutes, handling SKU-Lot mappings and product name mappings. This is the sole service for uploading orders to ShipStation. Includes dual-layer environment protection to prevent accidental dev uploads.
    - **Orders Cleanup Service:** Daily deletion of `orders_inbox` entries older than 60 days.
    - **Duplicate Order Monitoring System:** Scans ShipStation every 15 minutes for duplicate order numbers. Alerts require manual operator verification and resolution via the dashboard. It also detects manual order conflicts where the same order number has different ShipStation IDs.
- **Frontend:** `index.html` serves as the main dashboard, offering a complete enterprise layout with two-tier navigation, card-based components, responsive design, auto-refresh, skeleton loaders, and error handling.
- **Bundle SKU System:** Database-driven management with CRUD capabilities for bundle SKUs and automatic expansion during import.
- **SKU Lot Management:** Database-driven tracking for SKU-Lot combinations with CRUD support and unique constraints.
- **Lot Inventory Management:** Auto-calculated FIFO inventory tracking per lot, based on initial quantities, manual adjustments, and shipped quantities.
- **Workflow Controls System:** A programmatic system allowing on/off toggling for all automation workflows via a database table and UI.
- **Shipping Validation System:** An alert-only system that compares actual carrier/service information from ShipStation against expected rules, displaying violations on the dashboard.
- **Production Incident Tracker:** A full-featured bug tracking system (`incidents.html`) with severity levels, status management, and enforced resolution documentation.
- **Order Management Admin Tool:** A comprehensive admin interface (`order-management.html`) for managing ShipStation orders. Features include order lookup by order number, displaying all order details (customer, company, items, status), and safe deletion of duplicate or problematic orders. The tool shows warnings when multiple orders share the same order number and provides detailed confirmation before deletion. All operations are logged and require admin authentication.
- **Deployment:** The system is deployed as a continuous VM in Replit, using `start_all.sh` to launch the dashboard server and all background automation workflows.

## External Dependencies
- **ShipStation API:** Used for order uploads and shipment status synchronization.
- **Google Drive:** Integrated for XML file imports.
- **SendGrid:** (Optional) For email notifications.
- **Google Cloud Secret Manager:** For secure management of production credentials.
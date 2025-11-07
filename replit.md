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
- **Business Rules:**
    - **Unit-based metrics:** Display only unit counts (not order counts) throughout the system. Units are the driving factor for all fulfillment, shipping, and inventory workflows. Order counts are only relevant for charge reports.
- **Fulfillment Workflow Context:**
    - **12 noon CST cutoff:** Orders accumulate until 12:00 PM Central Standard Time
    - **Work happens in ShipStation:** Fulfillment person processes orders, prints labels, affixes to products, and notes inventory entirely within ShipStation platform (NOT in this system)
    - **System role:** ORDER MANAGEMENT tool for monitoring, inventory management, and troubleshooting - NOT the fulfillment execution platform
    - **Primary user:** Fulfillment person (monitoring + inventory operations)
    - **Default view:** Dashboard (not Orders Inbox)
    - **Orders Inbox purpose:** Secondary/troubleshooting tool for investigating issues, managing inventory (receiving/adjustments), and manual interventions
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
A single centralized `global-styles.css` defines the premium corporate design system used across all 13 HTML pages, ensuring consistency. This includes the color palette, typography (IBM Plex Sans body + Source Serif 4 hero stats), design tokens, component library, light/dark mode with navy glass sidebar effect, responsive breakpoints, and an elevation system.

**Technical Implementations & Feature Specifications:**
- **Database Layer:** PostgreSQL is the core data store. Key tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox`, `system_kpis`, `bundle_skus`, `bundle_components`, and `sku_lot`. The `configuration_params` table stores critical settings. The `InitialInventory` baseline date is **September 19, 2025**. All order updates are blocked until `shipstation_order_id` is synced. Manual orders (10xxxx) are created in ShipStation and tracked locally for inventory.
- **Replit Auth:** Implemented with role-based access control (Admin/Viewer roles) using Flask-Dance OAuth, supporting multiple login methods, a dual database architecture, and centralized API authentication middleware.
- **Backend Automation (Python scripts):**
    - **Unified ShipStation Sync:** Production workflow combining status sync and manual order import, running every 5 minutes.
    - **Physical Inventory Controls:** User-driven buttons for End-of-Day (EOD), End-of-Week (EOW), and End-of-Month (EOM) operations.
    - **XML Polling Service:** Continuously monitors Google Drive for new order XML files and expands bundle SKUs.
    - **ShipStation Upload Service:** Automatically uploads pending orders from `orders_inbox` to ShipStation every 5 minutes, handling SKU-Lot mappings and product name mappings.
    - **Orders Cleanup Service:** Daily deletion of `orders_inbox` entries older than 60 days.
    - **Duplicate Order Monitoring System:** Scans ShipStation every 15 minutes for duplicate order numbers with intelligent auto-resolution and a "Permanently Exclude" feature. Tracks all ShipStation order deletions in `deleted_shipstation_orders`.
- **Frontend:** `index.html` serves as the main dashboard (DEFAULT VIEW), offering a complete enterprise layout with two-tier navigation, card-based components, responsive design, auto-refresh, skeleton loaders, and error handling.
- **Orders Inbox (xml_import.html):** Secondary interface for monitoring, troubleshooting, and manual interventions related to order status, inventory, and flagged orders. Redesigned with workflow-focused filters (Needs Verification, Ready to Ship, Shipped, Failed, All Orders) in single-select mode with "Ready to Ship" as default. Features inline lot number editing with ShipStation sync, visual order type badges (Canadian flag image, Benco logo, Hawaiian flower, International globe), and premium UI polish. Includes ✏️ edit button next to SKU-LOT displays for quick lot corrections via database-driven dropdown.
- **Bundle SKU System:** Database-driven management with CRUD capabilities for bundle SKUs and automatic expansion.
- **SKU Lot Management:** Database-driven tracking for SKU-Lot combinations with CRUD support and unique constraints.
- **Lot Inventory Management:** Auto-calculated FIFO inventory tracking per lot.
- **Workflow Controls System:** Programmatic system for toggling automation workflows via a database table and UI.
- **Shipping Validation System:** Alert-only system comparing actual carrier/service from ShipStation against expected rules.
- **Production Incident Tracker:** Bug tracking system (`incidents.html`) with severity levels, status management, and enforced resolution documentation.
- **Order Management Admin Tool:** Comprehensive admin interface (`order-management.html`) for managing ShipStation orders, including lookup, details, and safe deletion of problematic orders.
- **Deployment:** The system is deployed as a continuous VM in Replit, using `start_all.sh` to launch the dashboard server and all background automation workflows.

## External Dependencies
- **ShipStation API:** Used for order uploads and shipment status synchronization.
- **Google Drive:** Integrated for XML file imports.
- **SendGrid:** (Optional) For email notifications.
- **Google Cloud Secret Manager:** For secure management of production credentials.

## Data Flow & Integration Truth Table
**INFALLIBLE TRUTHS:**
- **X-Cart → This System:** X-Cart generates XML files with SKUs and order numbers ONLY (NO lot numbers). XML files are placed in Google Drive for polling.
- **X-Cart ↔ ShipStation:** NO direct integration exists. X-Cart does NOT communicate with ShipStation.
- **This System → ShipStation:** This system is responsible for uploading orders to ShipStation WITH lot numbers appended (format: "SKU - LOT").
- **Lot Number Assignment:** Lot numbers are ONLY managed in this system via the `sku_lot` table. The upload service queries `WHERE active = 1` to get current lots before uploading to ShipStation.
- **Upload Service Location:** `src/scheduled_shipstation_upload.py` (currently BLOCKED in workspace due to `REPL_SLUG=workspace` check at line 176).
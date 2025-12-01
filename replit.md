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
- **Operational Context:**
    - **Environment:** When troubleshooting, issues are typically occurring in PRODUCTION, not development workspace
    - **Production Logs:** Production logs are NOT visible in the development workspace. User must manually share production log file contents when troubleshooting production issues
    - **Database Note:** Development and Production have SEPARATE databases. Changes made in the dev workspace database do NOT affect production data. Schema changes and migrations must be applied to both environments.
- **Business Rules:**
    - **Unit-based metrics:** Display only unit counts (not order counts) throughout the system. Units are the driving factor for all fulfillment, shipping, and inventory workflows. Order counts are only relevant for charge reports.
    - **SKU-Lot Validation (CRITICAL):** ShipStation should NEVER have orders without valid SKU-Lot mappings. The upload service enforces three strict validations:
        1. **Global Check:** If `sku_lot` table has no active mappings, ABORT entire upload and revert orders to pending
        2. **Item-Level Check:** Individual items without lot numbers are SKIPPED with error logging
        3. **Order-Level Check:** Orders with NO valid items after filtering are marked as 'failed' and never uploaded
    - **Duplicate Prevention (Nov 2025 - Race Condition Fixes):** Multi-layered protection against duplicate order uploads:
        1. **Upload Service Guard:** Only claims orders with `status='pending'` AND `shipstation_order_id IS NULL`, preventing re-upload of already-processed orders
        2. **Sync Status Preservation:** Unified sync preserves 'uploaded' and 'failed' statuses, preventing status downgrades that could trigger re-uploads
        3. **XML Import Protection:** Re-imported orders that already have a `shipstation_order_id` are skipped to prevent clearing upload tracking
        4. **ShipStation API Check:** Queries ShipStation before uploading; orders with existing entries are skipped (handles API edge cases where items return empty)
        5. **Atomic Claiming:** `FOR UPDATE SKIP LOCKED` ensures only one upload process claims each order, preventing concurrent duplicate uploads
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
- **Database Layer:** PostgreSQL is the core data store. Key tables include `workflows`, `inventory_current`, `shipped_orders`, `orders_inbox`, `system_kpis`, `bundle_skus`, `bundle_components`, `sku_lot`, and `inventory_daily_snapshots`. The `configuration_params` table stores critical settings. The `InitialInventory` baseline date is **September 19, 2025**. All order updates are blocked until `shipstation_order_id` is synced. Manual orders (10xxxx) are created in ShipStation and tracked locally for inventory.
    - **Daily Inventory Snapshots (Dec 2025):** The `inventory_daily_snapshots` table stores historical EOD inventory for charge report BOM calculations. EOD report automatically upserts today's snapshot after each successful run. The charge report queries the snapshot for the day before the first of the month to get accurate BOM values. Backfill script: `src/backfill_daily_snapshots.py`.
- **Replit Auth:** Implemented with role-based access control (Admin/Operations/Viewer roles) using Flask-Dance OAuth, supporting multiple login methods, a dual database architecture, and centralized API authentication middleware.
    - **Admin Role:** Full system access including all CRUD operations, workflow controls, EOD/EOW/EOM reports, and charge reports.
    - **Operations Role:** Read-only access EXCEPT can run EOD/EOW (not EOM), add/edit inventory transactions, and add/edit/activate/deactivate lot numbers. Cannot delete any records. Charge report page is hidden from Operations users.
    - **Viewer Role:** Read-only access with limited write permissions (incident reporting, minor inventory adjustments ±4 units).
- **Backend Automation (Python scripts):**
    - **Business Hours Optimization:** All automation workflows operate only during business hours (Monday-Friday 6 AM - 6 PM CST) for 64% database compute time reduction with zero business impact.
    - **Unified ShipStation Sync:** Production workflow combining status sync and manual order import, running every 5 minutes during business hours.
    - **Physical Inventory Controls:** User-driven buttons for End-of-Day (EOD), End-of-Week (EOW), and End-of-Month (EOM) operations.
        - **EOD Performance Optimization (Nov 2025):** Incremental fetch since last successful EOD run instead of fixed 40-day window, reducing processing time from 120s+ (timeout) to ~66s. Includes 180s timeout buffer for edge cases and auto-recovery from failed runs.
    - **XML Polling Service:** Monitors Google Drive for new order XML files and expands bundle SKUs during business hours.
    - **ShipStation Upload Service:** Automatically uploads pending orders from `orders_inbox` to ShipStation every 5 minutes during business hours, handling SKU-Lot mappings and product name mappings.
    - **Orders Cleanup Service:** Daily deletion of `orders_inbox` entries older than 60 days, running during business hours.
    - **Duplicate Order Monitoring System:** Scans ShipStation every 15 minutes for duplicate order numbers with intelligent auto-resolution and a "Permanently Exclude" feature during business hours. Tracks all ShipStation order deletions in `deleted_shipstation_orders`.
    - **Lot Mismatch Scanner:** Detects lot number discrepancies between ShipStation and local database, running every 15 minutes during business hours.
- **Frontend:** `index.html` serves as the main dashboard (DEFAULT VIEW), offering a complete enterprise layout with two-tier navigation, card-based components, responsive design, auto-refresh, skeleton loaders, and error handling.
- **Orders Inbox (xml_import.html):** Secondary interface for monitoring, troubleshooting, and manual interventions related to order status, inventory, and flagged orders. Redesigned with workflow-focused filters (Needs Verification, Ready to Ship, Shipped, Failed, All Orders) in single-select mode with "Ready to Ship" as default. Features inline lot number editing with ShipStation sync, visual order type badges (Canadian flag image, Benco logo, Hawaiian flower, International globe), and premium UI polish. Includes ✏️ edit button next to SKU-LOT displays for quick lot corrections via database-driven dropdown.
- **Bundle SKU System:** Database-driven management with CRUD capabilities for bundle SKUs and automatic expansion.
- **SKU Lot Management:** Database-driven tracking for SKU-Lot combinations with CRUD support and unique constraints.
- **Lot Inventory Management:** Auto-calculated FIFO inventory tracking per lot.
- **Workflow Controls System:** Programmatic system for toggling automation workflows via a database table and UI. Includes manual "Run Now" buttons that bypass business hours restrictions and allow admins to trigger workflows on-demand with real-time execution feedback.
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
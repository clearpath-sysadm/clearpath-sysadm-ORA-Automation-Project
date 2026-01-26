# Oracare Fulfillment System

## Overview
The Oracare Fulfillment System is a production-ready order management platform that replaces legacy Google Sheets with a PostgreSQL database. It manages inventory, shipments, and automation workflows for Oracare's fulfillment operations, providing real-time visibility and automated business processes with zero data loss tolerance.

## User Preferences
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

## System Architecture

### Core Stack
- **Backend:** Python 3.11, Flask
- **Database:** PostgreSQL (35 tables)
- **Frontend:** 19 HTML pages with centralized CSS design system
- **Authentication:** Replit Auth with role-based access (Admin/Operations/Viewer)

### Key Components

**Database Tables (37 total):**
- Order Management: `orders_inbox`, `order_items_inbox`, `shipped_orders`, `shipped_items`
- Inventory: `inventory_current`, `inventory_transactions`, `inventory_daily_snapshots`, `lot_inventory`
- SKU/Bundles: `sku_lot`, `bundle_skus`, `bundle_components`
- Alerts: `duplicate_order_alerts`, `lot_mismatch_alerts`, `manual_order_conflicts`, `shipping_violations`
- System: `workflows`, `workflow_controls`, `configuration_params`, `users`, `workflow_heartbeats`, `stuck_workflow_incidents`

**Frontend Pages (20):**
- `index.html` - Main dashboard (DEFAULT VIEW)
- `xml_import.html` - Orders Inbox for troubleshooting
- `shipped_orders.html`, `shipped_items.html` - Historical data
- `bundle_skus.html`, `sku_lot.html` - Product management
- `lot_inventory.html`, `inventory_transactions.html`, `inventory_snapshots.html` - Inventory
- `charge_report.html`, `weekly_shipped_history.html` - Reports
- `order-management.html`, `order_audit.html` - Admin tools
- `workflow_controls.html`, `incidents.html` - System management
- `logs.html` - Server Logs viewer (Admin only)
- `email_contacts.html`, `settings.html`, `help.html`, `landing.html` - Utility pages

**Automation Workflows (8):**
| Workflow | Script | Interval |
|----------|--------|----------|
| dashboard-server | `app.py` | Continuous |
| xml-import | `scheduled_xml_import.py` | 5 min |
| shipstation-upload | `scheduled_shipstation_upload.py` | 5 min |
| unified-shipstation-sync | `unified_shipstation_sync.py` | 5 min |
| duplicate-scanner | `scheduled_duplicate_scanner.py` | 15 min |
| lot-mismatch-scanner | `scheduled_lot_mismatch_scanner.py` | 15 min |
| stuck-workflow-detector | `scheduled_stuck_workflow_detector.py` | 15 min |
| orders-cleanup | `scheduled_cleanup.py` | Daily |

**Workflow Health Monitoring:** Automatic detection of stuck workflows via heartbeat system. All workflows log heartbeats (started/completed/error phases) to `workflow_heartbeats` table. Detector runs every 15 minutes, creates incidents in `stuck_workflow_incidents`, and can auto-reset stuck workflows.

**Business Hours:** Monday-Friday 6 AM - 6 PM CST (64% compute reduction)

### Role-Based Access Control
- **Admin:** Full system access including all CRUD, reports (EOD/EOW/EOM), charge reports, workflow controls
- **Operations:** Read + limited write: EOD/EOW reports, inventory transactions, lot management. No delete, no EOM, no charge reports
- **Viewer:** Read-only with minor adjustments (±4 units)

## Data Flow

```
X-Cart → XML → Google Drive → xml-import → orders_inbox
                                              ↓
                                     shipstation-upload
                                              ↓
                                         ShipStation
                                              ↓
                               unified-shipstation-sync
                                              ↓
                                      shipped_orders
```

**SKU-Lot Assignment:** Lot numbers are managed exclusively via the `sku_lot` table. The upload service queries `WHERE active = 1` to get current lots before sending to ShipStation.

## External Dependencies
- **ShipStation API:** Order uploads and shipment sync
- **Google Drive:** XML file imports
- **Google Sheets:** (Legacy, deprecated)

## Key Files
- `app.py` - Main Flask application (100+ API endpoints)
- `start_all.sh` - Production startup script
- `src/scheduled_*.py` - Automation workflows
- `src/unified_shipstation_sync.py` - Status sync and manual order import
- `static/global-styles.css` - Design system
- `TECHNICAL_DOCUMENTATION.md` - Full technical reference

## Recent Changes (Dec 2025 - Jan 2026)
- Added `manual_order_conflicts` table and UI for conflict tracking
- Added `original_order_status` column for accurate conflict status display
- Daily inventory snapshots for charge report BOM calculations
- Multi-methodology diagnostic tooling for production issues
- **Server Logging System (Jan 2026):** File-based logging with rotation (10MB, 7 backups), configurable via LOG_LEVEL env var, Server Logs admin page (logs.html) with filtering/search/download
- **User Activity Tracking (Jan 2026):** 16 endpoints tracked with user/role attribution for Inventory, SKU-Lot, Reports, ShipStation, and Email operations
- **ShipStation Sync Fix (Jan 7, 2026):** Fixed duplicate key constraint violations in `manual_order_conflicts` table using UPSERT pattern (`ON CONFLICT DO NOTHING`). See `docs/implementation-reports/SHIPSTATION_SYNC_DUPLICATE_KEY_FIX.md`
- **ShipStation Deletion Audit Trail (Jan 7, 2026):** Enhanced `deleted_shipstation_orders` table to capture full customer data before deletion: customer_name, customer_email, customer_company, ship_to_name/city/state, order_total_cents, order_date, items_json. Server logging added for deletion events.
- **Admin Alert Bar System (Jan 7, 2026):** Admin-controlled messaging system for displaying important alerts to all users. Active alerts (red bar) cannot be dismissed; cleared alerts (green bar) can be dismissed by users. Managed via Workflow Controls page (Admin only). Database table: `admin_alerts`. API: `/api/admin/alert`.
- **Workflow Health Monitoring (Jan 17, 2026):** Automated detection of stuck workflows to prevent production outages like the Jan 9th XML import incident. Features: heartbeat logging for all workflows (`workflow_heartbeats` table), stuck workflow detector service (runs every 15 mins), incident tracking (`stuck_workflow_incidents`), UI enhancements on Workflow Controls page (health badges, reset buttons, incident history). APIs: `/api/workflow_health`, `/api/workflow/{name}/reset`, `/api/stuck_workflow_incidents`.
- **Google Drive Service Account Migration (Jan 19, 2026):** Migrated XML Import from Replit connector to Google Service Account authentication (`ora-sheets-automator@ora-automation-project.iam.gserviceaccount.com`). Added fallback file search for when file is shared directly without folder access. Secret: `GOOGLE_SERVICE_ACCOUNT_KEY`. File: `src/services/google_drive/api_client.py`.
- **ShipStation Backfill Tool (Jan 19, 2026):** Admin tool to sync missing shipped orders from ShipStation to local database. Features: dry run (compare) and sync operations, date range selection, Admin UI on Workflow Controls page. Scripts: `src/shipstation_backfill_dry_run.py`, `src/shipstation_backfill_sync.py`. APIs: `/api/admin/shipstation-backfill/dry-run`, `/api/admin/shipstation-backfill/sync`.
- **Order Status Sync Fix (Jan 19, 2026):** One-click fix for mismatch between local DB and ShipStation order counts. Root cause: XML-imported orders lack `shipstation_order_id`, preventing normal sync updates. Fix matches by `order_number` and updates status to 'shipped'. UI button on Workflow Controls page. API: `/api/admin/fix-order-status-sync`. See `docs/implementation-reports/ORDER_STATUS_SYNC_FIX.md`.
- **Polling vs Webhook Assessment (Jan 26, 2026):** Comprehensive analysis of current polling architecture vs webhook alternative. Verdict: current polling is production-grade with watermark sync, idempotency, and monitoring. Webhook switch is strategic investment (weeks), not urgent fix. See `docs/POLLING_VS_WEBHOOK_ASSESSMENT_REPORT.md`.
- **Unit Comparison Tool (Jan 26, 2026):** Diagnostic tool to compare awaiting_shipment orders between ShipStation and local database. Features: pagination support (up to 10K orders), empty order_number handling, truncation warnings. Identifies orders only in ShipStation, only in local DB, or with unit count mismatches. UI on Workflow Controls page. API: `/api/admin/unit-comparison`.

## Important Notes
- InitialInventory baseline: September 19, 2025
- Upload service blocked in workspace via `REPL_SLUG=workspace` check (line 176)
- Production deployment uses `start_all.sh` for all workflows

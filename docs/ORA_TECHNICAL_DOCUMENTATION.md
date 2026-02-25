# ORA Fulfillment System - Technical Documentation

**Version:** 1.0
**Last Updated:** February 25, 2026
**Prepared For:** Oracare Team Assessment

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Data Flow](#4-data-flow)
5. [Order Lifecycle](#5-order-lifecycle)
6. [Database Schema](#6-database-schema)
7. [Background Workflows](#7-background-workflows)
8. [API Reference](#8-api-reference)
9. [Frontend Pages](#9-frontend-pages)
10. [External Integrations](#10-external-integrations)
11. [Authentication & Access Control](#11-authentication--access-control)
12. [Business Rules](#12-business-rules)
13. [Deployment & Infrastructure](#13-deployment--infrastructure)
14. [Monitoring & Alerting](#14-monitoring--alerting)
15. [Known Limitations & Considerations](#15-known-limitations--considerations)

---

## 1. Executive Summary

The ORA Fulfillment System is a production-grade order management platform purpose-built for Oracare's warehouse fulfillment operations. It replaces a legacy Google Sheets-based workflow with a PostgreSQL-backed system that provides:

- Automated order ingestion from X-Cart via XML files hosted on Google Drive
- Automated order upload to ShipStation with SKU-Lot number enforcement
- Bi-directional status synchronization with ShipStation
- Real-time operational dashboard for warehouse staff and management
- Inventory tracking at the lot level (FEFO compliance)
- Monthly charge report generation for 3PL billing
- Duplicate order detection and lot mismatch alerting

The system is deployed on Replit and runs as a multi-process application with one Flask web server and seven background worker processes.

---

## 2. System Architecture

### High-Level Architecture

```
+--------------------+     +-------------------+     +-------------------+
|   X-Cart (Store)   |     |   Google Drive     |     |   ShipStation     |
|                    |     |   (orders.xml)     |     |   (Fulfillment)   |
+--------+-----------+     +--------+----------+     +--------+----------+
         |                          |                          ^    |
         |   XML export             |   Polling (5 min)        |    |
         +------------------------->+                          |    |
                                    |                          |    |
                          +---------v--------------------------+----v--------+
                          |              ORA SYSTEM                          |
                          |                                                  |
                          |  +-------------+    +------------------------+   |
                          |  | XML Import  |--->| orders_inbox (DB)      |   |
                          |  | Worker      |    +----------+-------------+   |
                          |  +-------------+               |                 |
                          |                      +---------v-----------+     |
                          |                      | ShipStation Upload  |---->|
                          |                      | Worker              |     |
                          |                      +---------------------+     |
                          |                                                  |
                          |                      +---------------------+     |
                          |                      | ShipStation Sync    |<----|
                          |                      | Worker              |     |
                          |                      +---------+-----------+     |
                          |                                |                 |
                          |                      +---------v-----------+     |
                          |                      | shipped_orders (DB) |     |
                          |                      +---------------------+     |
                          |                                                  |
                          |  +-------------------------------------------+   |
                          |  |         Flask Dashboard (app.py)          |   |
                          |  |  - Real-time stats & alerts               |   |
                          |  |  - Order management & audit tools         |   |
                          |  |  - Inventory tracking                     |   |
                          |  |  - Charge reports & billing               |   |
                          |  |  - Admin controls & incident tracking     |   |
                          |  +-------------------------------------------+   |
                          +--------------------------------------------------+
```

### Process Model

The system runs as 8 concurrent processes managed by `start_all.sh`:

| Process | Type | Description |
|---------|------|-------------|
| `app.py` | Web Server (Flask) | Dashboard, API endpoints, admin tools |
| 7 background workers | Python scripts | Automated polling, syncing, monitoring |

All background workers are business-hours aware (Mon-Fri, 6 AM - 6 PM CST) to reduce compute costs by ~64% during off-hours.

---

## 3. Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Language** | Python 3.11 | Primary language for backend and workers |
| **Web Framework** | Flask | REST API and static page serving |
| **Database** | PostgreSQL | Replit-managed, 37+ tables |
| **ORM** | Raw SQL (psycopg2) | Direct SQL for business logic, SQLAlchemy for auth models |
| **Frontend** | HTML/CSS/JavaScript | 20 static pages, no frontend framework |
| **Authentication** | Replit Auth (OpenID Connect) | Role-based access control |
| **Hosting** | Replit | Development workspace + production deployment |
| **External APIs** | ShipStation, Google Drive | Order management and file ingestion |

### Key Python Libraries

| Library | Purpose |
|---------|---------|
| `flask` | Web framework and API routing |
| `psycopg2` | PostgreSQL database driver |
| `requests` | HTTP client for ShipStation API |
| `defusedxml` | Secure XML parsing for order imports |
| `googleapiclient` | Google Drive file access |
| `tenacity` | Retry logic for API calls |

---

## 4. Data Flow

### Current Order Pipeline (X-Cart)

```
X-Cart Store
    |
    | (automated XML export)
    v
Google Drive (orders.xml)
    |
    | (xml-import worker, polls every 5 min)
    v
orders_inbox (status: "pending")
    |
    | - Bundle expansion (bundle_skus -> bundle_components)
    | - SKU filtering (Key Products only)
    | - Lot number assignment (sku_lot table)
    |
    | (shipstation-upload worker, polls every 5 min)
    v
orders_inbox (status: "uploaded" -> "awaiting_shipment")
    |
    | (ShipStation API: createorders endpoint)
    v
ShipStation (status: awaiting_shipment)
    |
    | (warehouse picks, packs, ships)
    v
ShipStation (status: shipped, tracking assigned)
    |
    | (unified-shipstation-sync worker, polls every 5 min)
    v
orders_inbox (status: "shipped")
shipped_orders + shipped_items (archival records)
inventory_transactions (stock decremented)
```

### Data Transformation Details

1. **XML Import**: Parses X-Cart XML, expands bundles into component SKUs, filters for "Key Products" (defined in `configuration_params`), assigns active lot numbers from `sku_lot`
2. **ShipStation Upload**: Consolidates items by SKU, enforces lot number validation, creates orders via ShipStation API with atomic claiming (`FOR UPDATE SKIP LOCKED`)
3. **Status Sync**: Watermark-based incremental sync from ShipStation, updates local statuses, imports manual orders, captures tracking numbers

---

## 5. Order Lifecycle

### Status Flow

```
pending ──────> uploaded ──────> awaiting_shipment ──────> shipped
   |                |                    |
   |                |                    +──────> cancelled
   |                |
   |                +──────> failed (reverts to pending for retry)
   |
   +──────> on_hold
```

### Status Definitions

| Status | Description | Set By |
|--------|-------------|--------|
| `pending` | Imported from XML, awaiting upload to ShipStation | XML Import worker |
| `uploaded` | Claimed by upload worker, in process of being sent to ShipStation | ShipStation Upload worker |
| `awaiting_shipment` | Successfully created in ShipStation, waiting to be fulfilled | ShipStation Upload worker |
| `shipped` | Fulfilled and shipped in ShipStation, tracking number assigned | Unified Sync worker |
| `cancelled` | Cancelled in ShipStation | Unified Sync worker |
| `on_hold` | Manually placed on hold by operator | Manual (dashboard) |
| `failed` | Upload to ShipStation failed (missing lot, API error) | ShipStation Upload worker |

### Business Hours Context

- **12:00 PM CST cutoff**: Orders accumulate throughout the morning and are processed for same-day shipment before the noon cutoff
- **Fulfillment happens in ShipStation**: ORA is the monitoring and management layer; warehouse staff work directly in ShipStation

---

## 6. Database Schema

### Core Order Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `orders_inbox` | Staging table for all incoming orders | `id`, `order_number`, `status`, `shipstation_order_id`, `customer_email`, shipping address fields, `tracking_number` |
| `order_items_inbox` | Line items for inbox orders | `id`, `order_inbox_id` (FK), `sku`, `quantity`, `unit_price_cents` |
| `shipped_orders` | Archive of completed shipments | `id`, `order_number`, `ship_date`, `carrier`, `tracking_number` |
| `shipped_items` | Line items for shipped orders | `id`, `shipped_order_id` (FK), `sku`, `sku_lot`, `quantity` |
| `shipstation_order_line_items` | ShipStation ID mapping per line item | `order_inbox_id`, `sku`, `shipstation_order_id` |
| `deleted_shipstation_orders` | Audit trail for deleted ShipStation orders | `order_number`, `shipstation_order_id`, customer data, `items_json` |

### Inventory Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `inventory_current` | Current stock levels per SKU | `sku`, `quantity`, `alert_level`, `reorder_point` |
| `inventory_transactions` | Ledger of all stock movements | `sku`, `transaction_type` (Receive/Ship/Adjust/Repack), `quantity`, `reference` |
| `lot_inventory` | Inventory tracked by manufacturing lot | `sku`, `lot_number`, `initial_quantity`, `status` (active/depleted) |
| `inventory_daily_snapshots` | Point-in-time EOD stock levels | `sku`, `date`, `quantity` |

### Product Configuration Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `sku_lot` | Active lot assignment per SKU | `sku`, `lot`, `active` |
| `bundle_skus` | Bundle product definitions | `bundle_sku`, `description` |
| `bundle_components` | Component SKUs within bundles | `bundle_sku_id` (FK), `component_sku`, `multiplier` |

### Alert & Monitoring Tables

| Table | Purpose |
|-------|---------|
| `duplicate_order_alerts` | Flagged duplicate order+SKU combinations in ShipStation |
| `excluded_duplicate_orders` | Whitelist for known-good "duplicates" |
| `lot_mismatch_alerts` | Orders where ShipStation lot differs from active lot |
| `shipping_violations` | Business rule violations (wrong carrier, etc.) |
| `manual_order_conflicts` | Conflicts from manual ShipStation entries vs imported orders |
| `production_incidents` | System-wide issue tracking with severity |
| `incident_notes` | Threaded comments on incidents |

### System Tables

| Table | Purpose |
|-------|---------|
| `workflows` | Execution history for background tasks |
| `workflow_controls` | Enable/disable toggles for each workflow |
| `workflow_heartbeats` | Health check pings from running workers |
| `stuck_workflow_incidents` | Auto-detected workflow failures |
| `sync_watermark` | Last sync timestamp for incremental fetches |
| `polling_state` | State tracking for upload/import cycles |
| `configuration_params` | Key-value settings store (intervals, SKU filters, etc.) |
| `shipstation_metrics` | Cached ShipStation API metrics (units to ship) |
| `system_kpis` | Daily performance snapshots |
| `admin_alerts` | Admin-controlled banner messages |

### Authentication Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts (Replit Auth integration) with roles |
| `oauth` | OAuth tokens and session management |

---

## 7. Background Workflows

All workflows are launched by `start_all.sh` and run as independent Python processes.

### Workflow Summary

| Workflow | Script | Interval | Description |
|----------|--------|----------|-------------|
| **XML Import** | `src/scheduled_xml_import.py` | 5 min (15s fast mode) | Polls Google Drive for `orders.xml`, parses, expands bundles, filters for key products, assigns lot numbers, inserts into `orders_inbox` |
| **ShipStation Upload** | `src/scheduled_shipstation_upload.py` | 5 min | Claims `pending` orders atomically, validates SKU-Lot mappings, uploads to ShipStation API, tracks results |
| **Unified ShipStation Sync** | `src/unified_shipstation_sync.py` | 5 min | Watermark-based sync of status changes from ShipStation (shipped, cancelled), imports manual orders, captures tracking numbers |
| **ShipStation Units Refresh** | `src/shipstation_units_refresher.py` | 5 min | Fetches total awaiting_shipment unit count from ShipStation API, updates `shipstation_metrics` cache for dashboard |
| **Duplicate Scanner** | `src/scheduled_duplicate_scanner.py` | 15 min | Scans last 90 days of ShipStation orders for duplicate order_number+SKU combinations, creates alerts |
| **Lot Mismatch Scanner** | `src/scheduled_lot_mismatch_scanner.py` | 15 min | Compares ShipStation SKU-Lot assignments against current active lots, flags mismatches |
| **Stuck Workflow Detector** | `src/scheduled_stuck_workflow_detector.py` | 15 min | Monitors `workflow_heartbeats` for missing check-ins, creates incidents, can auto-reset stuck workflows |
| **Orders Cleanup** | `src/scheduled_cleanup.py` | Daily | Deletes order records older than 60 days from `orders_inbox` and `order_items_inbox` |

### Workflow Safety Features

- **Atomic Claiming**: Upload worker uses `SELECT FOR UPDATE SKIP LOCKED` to prevent concurrent processing of the same order
- **Heartbeat System**: All workers log start/complete/error phases to `workflow_heartbeats` table
- **Business Hours**: Workers sleep outside Mon-Fri 6 AM - 6 PM CST
- **Fast Polling**: XML Import and Upload support configurable fast polling (15s) via `configuration_params`
- **Workspace Safety**: Upload worker is blocked in development workspace (`REPL_SLUG=workspace` check) to prevent accidental production uploads

---

## 8. API Reference

### Dashboard & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard_stats` | Aggregated dashboard metrics |
| GET | `/api/inventory_alerts` | Low stock / reorder point alerts |
| GET | `/api/automation_status` | Workflow enabled/disabled states |
| GET | `/api/workflow_timestamps` | Lightweight polling for workflow state changes |
| GET | `/api/kpis` | Business KPIs |
| GET | `/api/workflow_health` | System operational health analysis |
| POST | `/api/fedex_pickup/mark_completed` | Log daily FedEx pickup |

### Order Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders_inbox` | List orders in staging inbox |
| GET | `/api/order_items/<order_id>` | Items for a specific order |
| GET | `/api/shipped_orders` | Paginated shipped order history |
| GET | `/api/shipped_items` | Shipped items (last 40 days) |
| POST | `/api/xml_import` | Manual XML file upload and import |
| POST | `/api/validate_orders` | Run validation rules on pending orders |
| POST | `/api/retry_failed_orders` | Re-process failed orders |
| POST | `/api/orders_inbox/flag/<order_number>` | Flag order for review |
| POST | `/api/orders_inbox/unflag/<order_number>` | Remove review flag |

### ShipStation Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sync_shipstation` | Manual sync trigger |
| POST | `/api/upload_orders_to_shipstation` | Manual upload trigger |
| GET | `/api/shipstation/units_to_ship` | Cached unit count |
| POST | `/api/shipstation/refresh_units_to_ship` | Force refresh from API |
| GET | `/api/local/awaiting_shipment_count` | Local DB unit count |
| PUT | `/api/update_lot_in_shipstation` | Update lot on specific order |
| GET | `/api/units_discrepancy` | Compare SS vs local counts |
| GET | `/api/quantity_mismatch` | Quick mismatch check |

### Inventory & Lot Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/inventory_transactions` | View/create inventory movements |
| GET | `/api/inventory_snapshots` | Daily EOD inventory levels |
| POST | `/api/physical_count_adjustment` | Adjust stock from physical count |
| GET | `/api/lot_inventory` | Current lot-level quantities |
| GET/POST | `/api/sku_lots` | Manage SKU-Lot assignments |
| GET | `/api/lot_mismatch_alerts` | Lot mismatch alert list |
| PUT | `/api/lot_mismatch_alerts/<id>/resolve` | Resolve a mismatch alert |
| GET | `/api/lot_mismatch_count` | Count of unresolved mismatches |

### Reporting

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/charge_report` | Monthly billing/charge report |
| POST | `/api/reports/eod` | Trigger End-of-Day processing |
| POST | `/api/reports/eow` | Trigger End-of-Week reporting |
| POST | `/api/reports/eom` | Trigger End-of-Month calculations |
| GET | `/api/weekly_shipped_history` | 52-week shipping trends |

### Admin & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/admin/alert` | Get/set admin alert banner |
| GET | `/api/admin/logs` | Server application logs |
| GET | `/api/admin/db_diagnostics` | Database health diagnostics |
| POST | `/api/admin/fix-order-status-sync` | Fix stuck uploaded/shipped orders |
| POST | `/api/admin/sync_order_from_shipstation` | Force-sync single order |
| POST | `/api/admin/recreate-order` | Recreate order with corrected number |
| GET/POST | `/api/admin/shipstation-backfill/*` | Backfill missing shipped orders |
| GET/POST | `/api/admin/unit-comparison` | Compare SS vs local order-by-order |
| GET/PUT | `/api/workflow_controls` | View/toggle workflow states |
| POST | `/api/workflow/<name>/reset` | Reset stuck workflow |

### Incidents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/incidents` | List/create incidents |
| PUT | `/api/incidents/<id>` | Update incident |
| POST | `/api/incidents/<id>/notes` | Add note to incident |
| POST | `/api/incidents/<id>/screenshots` | Upload incident screenshot |
| GET | `/api/stuck_workflow_incidents` | Workflow failure history |

---

## 9. Frontend Pages

### Core Operations (Daily Use)

| Page | File | Description |
|------|------|-------------|
| **Dashboard** | `index.html` | Main landing page with real-time stats cards (ShipStation Units, Local DB Units, On-Hold Units), alert banners (duplicates, lot mismatches, manual conflicts), production health modal, quick action buttons |
| **Orders Inbox** | `xml_import.html` | Order management with status tabs (Pending, Shipped, Hold, Cancelled, Failed), order flagging, lot editing, CSV export, manual sync tools |
| **Shipped Orders** | `shipped_orders.html` | Historical view of completed shipments |
| **Shipped Items** | `shipped_items.html` | Item-level shipment history |

### Inventory Management

| Page | File | Description |
|------|------|-------------|
| **Inventory Monitor** | `inventory_transactions.html` | Transaction history, physical count adjustments with threshold-based admin approval |
| **Lot Inventory** | `lot_inventory.html` | Lot-level stock levels, expiration tracking, FEFO management |
| **Inventory Snapshots** | `inventory_snapshots.html` | Point-in-time daily stock records |

### Product Configuration

| Page | File | Description |
|------|------|-------------|
| **SKU-Lot Management** | `sku_lot.html` | Map SKUs to lot numbers, set active lots |
| **Bundle Management** | `bundle_skus.html` | Define bundle products and their component SKUs with multipliers |

### Reporting

| Page | File | Description |
|------|------|-------------|
| **Charge Report** | `charge_report.html` | Monthly 3PL billing (orders $4.25, units $0.75, pallet space), data validation, PDF/CSV export |
| **Weekly History** | `weekly_shipped_history.html` | 52-week shipping volume trends |

### Administration

| Page | File | Description |
|------|------|-------------|
| **Workflow Controls** | `workflow_controls.html` | Enable/disable background workflows, health badges, reset buttons, run diagnostics, unit comparison tool |
| **Order Management** | `order-management.html` | Admin bulk operations, database cleanup, stuck order fixes |
| **Order Audit** | `order_audit.html` | Deep investigation tool for individual order histories |
| **Server Logs** | `logs.html` | Real-time server log viewer with filtering by source (Admin only) |
| **Incidents** | `incidents.html` | Bug/issue reporting with screenshot upload |
| **Settings** | `settings.html` | User roles, system constants, API configuration |

### Utility

| Page | File | Description |
|------|------|-------------|
| **Landing** | `landing.html` | Public login page (only unauthenticated page) |
| **Help** | `help.html` | User guides and training documentation |
| **Email Contacts** | `email_contacts.html` | Notification recipient management |

---

## 10. External Integrations

### ShipStation API

- **Purpose**: Core shipping management - order creation and fulfillment status tracking
- **Authentication**: HTTP Basic Auth (API Key + Secret)
- **Endpoints Used**:
  - `POST /orders/createorders` - Upload new orders
  - `GET /orders` - Fetch order status and details
  - `GET /shipments` - Retrieve tracking numbers and ship dates
  - `DELETE /orders/{orderId}` - Remove duplicate/incorrect orders
- **Rate Handling**: Retry logic with `tenacity` library
- **Credential Storage**: Replit environment variables (`SHIPSTATION_API_KEY`, `SHIPSTATION_API_SECRET`), with fallback to GCP Secret Manager

### Google Drive API

- **Purpose**: Source for X-Cart order XML files
- **Authentication**: Google Service Account (`ora-sheets-automator@ora-automation-project.iam.gserviceaccount.com`)
- **Usage**: Polls a specific Drive folder for `orders.xml`, downloads file content into memory
- **Credential Storage**: `GOOGLE_SERVICE_ACCOUNT_KEY` environment variable (JSON key)

### Google Sheets API (Deprecated)

- **Status**: Fully deprecated. The system has migrated to 100% database-driven architecture
- **Guard**: Attempting to access Google Sheets settings raises a `RuntimeError`

### Email (SendGrid) - Planned

- **Status**: Framework exists in `src/utils/notification_manager.py` but is in placeholder/simulated state
- **Intended Use**: Daily operation summaries and critical error alerts

---

## 11. Authentication & Access Control

### Authentication Method

- **Provider**: Replit Auth via OpenID Connect
- **Session Management**: OAuth tokens stored in `oauth` table
- **User Registration**: Automatic on first login via Replit

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access: all CRUD operations, EOD/EOW/EOM reports, charge reports, workflow controls, user management, server logs, database diagnostics |
| **Operations** | Read + limited write: EOD/EOW reports, inventory transactions, lot management. No delete operations, no EOM, no charge reports |
| **Viewer** | Read-only access with minor inventory adjustments (up to +/-4 units) |

### Protected Resources

- Admin-only endpoints use `@admin_required` decorator
- Page-level access control is enforced in the navigation sidebar
- Sensitive operations (order deletion, workflow reset) require Admin role

---

## 12. Business Rules

### SKU-Lot Validation (Critical)

ShipStation should NEVER have orders without valid SKU-Lot mappings. The upload service enforces a three-tier check:

1. **Global Check**: If the `sku_lot` table has zero active mappings, the entire upload batch is aborted
2. **Item-Level Check**: Individual items without a matching lot number are skipped
3. **Order-Level Check**: Orders with no valid items remaining are marked as `failed`

### Duplicate Prevention

Multi-layered protection against duplicate orders in ShipStation:

1. **Atomic Claiming**: `SELECT FOR UPDATE SKIP LOCKED` prevents concurrent workers from processing the same order
2. **ShipStation Pre-Check**: Before upload, existing orders are fetched from ShipStation API and matched by order_number + base SKU
3. **Sync Preservation**: The unified sync worker preserves `awaiting_shipment` status and won't downgrade already-uploaded orders
4. **Post-Upload Detection**: Duplicate scanner runs every 15 minutes to catch any that slip through

### Bundle Expansion

Bundle SKUs (e.g., a multi-pack) are expanded into their component SKUs during XML import:
- Bundle definitions stored in `bundle_skus` table
- Component mappings with multipliers in `bundle_components` table
- Example: Bundle SKU "MULTI-3PK" expands to 3x "SINGLE-UNIT"

### Key Product Filtering

Only "Key Products" (defined in `configuration_params` table) are imported from XML. Orders containing no key products are silently skipped.

### Monetary Values

All monetary amounts are stored as integers in cents (e.g., $4.25 = 425) to avoid floating-point precision issues.

### Unit-Based Metrics

The system displays unit counts (not order counts) throughout all dashboards and reports. Units are the primary metric for fulfillment, shipping, and inventory decisions.

---

## 13. Deployment & Infrastructure

### Environment

- **Platform**: Replit (NixOS-based Linux containers)
- **Deployment**: Replit Deployments (separate production environment)
- **Database**: Replit-managed PostgreSQL (separate instances for dev and prod)

### Startup Process

Production startup is managed by `start_all.sh`:

```bash
# Launches 7 background workers as background processes (&)
python src/scheduled_xml_import.py &
python src/scheduled_shipstation_upload.py &
python src/unified_shipstation_sync.py &
python src/shipstation_units_refresher.py &
python src/scheduled_duplicate_scanner.py &
python src/scheduled_lot_mismatch_scanner.py &
python src/scheduled_stuck_workflow_detector.py &

# Launches Flask app in foreground
python app.py
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SHIPSTATION_API_KEY` | ShipStation API authentication |
| `SHIPSTATION_API_SECRET` | ShipStation API authentication |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Google Drive access (JSON key) |
| `REPLIT_DEPLOYMENT` | Flag for production behavior |
| `REPL_SLUG` | Environment detection (workspace vs deployed) |
| `LOG_LEVEL` | Server logging verbosity |
| `SESSION_SECRET` | Flask session encryption |

### Safety Guards

- **Workspace Check**: ShipStation upload is disabled in development workspace (`REPL_SLUG=workspace`)
- **Business Hours**: Background workers sleep outside Mon-Fri 6 AM - 6 PM CST
- **Separate Databases**: Development and production have completely separate PostgreSQL instances

---

## 14. Monitoring & Alerting

### Dashboard Alerts

The main dashboard surfaces real-time alerts for:

| Alert Type | Trigger |
|------------|---------|
| **Unit Mismatch** | ShipStation units != Local DB units |
| **Duplicate Orders** | Same order_number + SKU detected in ShipStation |
| **Lot Mismatches** | ShipStation order has different lot than active lot |
| **Manual Order Conflicts** | Manual ShipStation entry conflicts with imported order |
| **Shipping Violations** | Wrong carrier or service level detected |
| **FedEx Pickup Reminder** | Daily reminder until pickup is confirmed |
| **Admin Alert Banner** | Admin-controlled messages for all users |

### Workflow Health Monitoring

- All background workers send heartbeat pings to `workflow_heartbeats` table
- Stuck Workflow Detector runs every 15 minutes
- If a workflow misses its expected heartbeat interval, an incident is created in `stuck_workflow_incidents`
- UI shows health badges (green/yellow/red) on Workflow Controls page
- One-click reset capability for stuck workflows

### Server Logging

- File-based logging with rotation (10MB files, 7 backups)
- Configurable log level via `LOG_LEVEL` environment variable
- Admin-only Server Logs page with filtering by source, level, and time
- Structured logging with source attribution (e.g., "ShipStation Upload", "XML Import", "Dashboard")

### Incident Tracking

- Built-in incident management system
- Severity levels and status tracking
- Screenshot attachment support
- Threaded notes for investigation timeline

---

## 15. Known Limitations & Considerations

### Current Architecture Dependencies

1. **X-Cart XML Pipeline**: The entire order ingestion depends on X-Cart exporting XML to Google Drive. This is the primary pipeline that would change in a BigCommerce migration.

2. **Polling-Based Sync**: All external integrations use polling (5-15 min intervals) rather than webhooks. A comprehensive assessment concluded this is production-adequate but webhooks would be a strategic upgrade. See `docs/POLLING_VS_WEBHOOK_ASSESSMENT_REPORT.md`.

3. **Single-Instance**: The system runs as a single Replit deployment. There is no horizontal scaling or load balancing.

4. **500-Order API Limit**: ShipStation API calls use `pageSize=500`. If awaiting_shipment orders exceed 500, pagination must be used (currently handled in some endpoints but not all).

### BigCommerce Migration Considerations

With a move from X-Cart to BigCommerce:

- **Order Ingestion**: BigCommerce has native ShipStation integration - orders flow directly without XML/Google Drive
- **Potentially Retiring**: XML Import worker, Google Drive integration, bundle expansion (if BigCommerce handles bundles)
- **Still Needed**: Lot number management (SKU modification in ShipStation), inventory tracking, charge reports, monitoring/alerting, duplicate detection
- **New Consideration**: With direct BigCommerce-to-ShipStation flow, ORA would shift from "order pipeline" to "monitoring and lot management" role

### Data Retention

- `orders_inbox` records older than 60 days are automatically deleted by the cleanup worker
- `shipped_orders` and `shipped_items` are retained indefinitely
- Inventory transactions are retained indefinitely for audit compliance

---

## Appendix A: File Structure

```
/
├── app.py                          # Main Flask application (100+ endpoints)
├── start_all.sh                    # Production startup script
├── config/
│   └── settings.py                 # Centralized configuration
├── src/
│   ├── scheduled_xml_import.py     # XML Import worker
│   ├── scheduled_shipstation_upload.py  # ShipStation Upload worker
│   ├── unified_shipstation_sync.py # Status Sync worker
│   ├── shipstation_units_refresher.py  # Metrics refresh worker
│   ├── scheduled_duplicate_scanner.py  # Duplicate detection worker
│   ├── scheduled_lot_mismatch_scanner.py  # Lot mismatch worker
│   ├── scheduled_stuck_workflow_detector.py  # Health monitor worker
│   ├── scheduled_cleanup.py        # Data retention worker
│   ├── auth/                       # Authentication modules
│   ├── services/
│   │   ├── database/pg_utils.py    # PostgreSQL utilities
│   │   ├── shipstation/api_client.py  # ShipStation API client
│   │   ├── google_drive/api_client.py # Google Drive API client
│   │   ├── reporting_logic/        # Report calculations
│   │   └── data_processing/        # SKU/shipment processing
│   └── utils/
│       ├── server_logger.py        # Structured logging
│       └── notification_manager.py # Email notifications (planned)
├── models/
│   └── auth_models.py              # SQLAlchemy auth models
├── migrations/                     # Database migration scripts
├── static/
│   └── global-styles.css           # Design system
├── docs/                           # Documentation
├── *.html                          # Frontend pages (20 files)
└── database_schema_complete.sql    # Full schema dump
```

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **Key Products** | SKUs that ORA tracks and manages (defined in configuration_params) |
| **Lot Number** | Manufacturing batch identifier appended to SKU (e.g., "17612 - 250237") |
| **FEFO** | First-Expired, First-Out - lot rotation methodology |
| **Bundle** | A product SKU that represents multiple component SKUs |
| **Watermark Sync** | Incremental sync strategy using last-modified timestamps |
| **Fast Polling** | Reduced polling interval (15 seconds vs 5 minutes) for high-volume periods |
| **EOD/EOW/EOM** | End-of-Day, End-of-Week, End-of-Month reporting cycles |
| **3PL** | Third-Party Logistics provider (the warehouse fulfilling orders) |
| **Ghost Order** | An order that exists in one system but not the other |

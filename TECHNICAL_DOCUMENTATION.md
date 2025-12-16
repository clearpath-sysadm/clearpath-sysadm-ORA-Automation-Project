# Oracare Fulfillment System - Technical Documentation

**Last Updated:** December 2025  
**Version:** 2.0

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [API Reference](#api-reference)
5. [Backend Automation](#backend-automation)
6. [Frontend Pages](#frontend-pages)
7. [Authentication & Authorization](#authentication--authorization)
8. [Data Flow](#data-flow)
9. [External Integrations](#external-integrations)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)

---

## System Overview

The Oracare Fulfillment System is a production-ready order management platform that replaces legacy Google Sheets with a PostgreSQL database. It provides:

- Real-time operational dashboard for inventory and order management
- Automated order import from X-Cart via Google Drive XML files
- Bidirectional synchronization with ShipStation for order fulfillment
- FIFO lot-based inventory tracking
- Role-based access control (Admin/Operations/Viewer)
- Business hours optimization for database efficiency

### Key Business Rules

1. **Unit-based metrics**: Display unit counts (not order counts) throughout the system
2. **SKU-Lot Validation**: Orders MUST have valid SKU-Lot mappings before ShipStation upload
3. **12 Noon CST Cutoff**: Orders accumulate until noon for same-day fulfillment
4. **Lot Number Management**: Lot numbers are managed exclusively in this system via the `sku_lot` table

---

## Architecture

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, Flask |
| Database | PostgreSQL (Replit-managed) |
| Frontend | HTML5, CSS3, JavaScript (Vanilla) |
| Authentication | Replit Auth with Flask-Dance OAuth |
| Styling | IBM Plex Sans, Source Serif 4, Custom CSS |
| External APIs | ShipStation, Google Drive, Google Sheets |

### Directory Structure

```
/
├── app.py                    # Main Flask application (100+ API endpoints)
├── start_all.sh              # Production startup script
├── *.html                    # Frontend pages (19 total)
├── static/
│   └── global-styles.css     # Centralized design system
├── src/
│   ├── auth/                 # Authentication middleware
│   ├── services/             # Business logic services
│   │   ├── database/         # PostgreSQL utilities
│   │   ├── shipstation/      # ShipStation API client
│   │   ├── google_drive/     # Google Drive API client
│   │   ├── data_processing/  # SKU/Lot parsing
│   │   └── reporting_logic/  # Report generators
│   ├── scheduled_*.py        # Automation workflows
│   └── unified_shipstation_sync.py
├── config/
├── utils/
├── logs/
└── docs/
```

---

## Database Schema

### Core Tables (35 Total)

#### Order Management
| Table | Columns | Description |
|-------|---------|-------------|
| `orders_inbox` | 47 | Main order staging table from XML import |
| `order_items_inbox` | 6 | Line items for orders in inbox |
| `shipped_orders` | 11 | Historical shipped orders from ShipStation |
| `shipped_items` | 8 | Line items for shipped orders |

#### Inventory
| Table | Columns | Description |
|-------|---------|-------------|
| `inventory_current` | 8 | Current inventory levels by SKU |
| `inventory_transactions` | 7 | Inventory adjustment history |
| `inventory_daily_snapshots` | 7 | EOD inventory snapshots for reporting |
| `lot_inventory` | 10 | FIFO lot-based inventory tracking |

#### SKU & Bundle Management
| Table | Columns | Description |
|-------|---------|-------------|
| `sku_lot` | 6 | SKU to lot number mappings (active/inactive) |
| `bundle_skus` | 6 | Bundle product definitions |
| `bundle_components` | 6 | Component SKUs within bundles |

#### Alerts & Monitoring
| Table | Columns | Description |
|-------|---------|-------------|
| `duplicate_order_alerts` | 13 | Duplicate order detection alerts |
| `lot_mismatch_alerts` | 11 | SKU-Lot discrepancy alerts |
| `manual_order_conflicts` | 15 | Manual order conflict tracking |
| `shipping_violations` | 9 | Carrier/service validation alerts |

#### System Configuration
| Table | Columns | Description |
|-------|---------|-------------|
| `workflows` | 11 | Workflow status and last run times |
| `workflow_controls` | 5 | Workflow enable/disable toggles |
| `configuration_params` | 8 | System settings (polling intervals, etc.) |
| `polling_state` | 5 | XML/ShipStation polling state |
| `sync_watermark` | 4 | Incremental sync timestamps |

#### User & Auth
| Table | Columns | Description |
|-------|---------|-------------|
| `users` | 8 | User accounts and roles |
| `oauth` | 7 | OAuth session data |

#### Other Tables
| Table | Columns | Description |
|-------|---------|-------------|
| `email_contacts` | 5 | Contact management |
| `fedex_pickup_log` | 6 | FedEx pickup scheduling |
| `production_incidents` | 10 | Bug/incident tracking |
| `incident_notes` | 6 | Notes on incidents |
| `production_incident_screenshots` | 7 | Incident screenshots |
| `report_runs` | 7 | Report execution history |
| `weekly_shipped_history` | 6 | Weekly shipment summaries |
| `shipstation_metrics` | 4 | ShipStation API metrics |
| `shipstation_order_line_items` | 5 | Cached ShipStation line items |
| `deleted_shipstation_orders` | 5 | Deleted order tracking |
| `excluded_duplicate_orders` | 6 | Permanently excluded duplicates |
| `discrepancy_sync_log` | 9 | Sync discrepancy history |
| `system_kpis` | 8 | Key performance indicators |

---

## API Reference

The system provides **100+ REST API endpoints** organized by function:

### Dashboard & KPIs
- `GET /api/dashboard_stats` - Dashboard statistics
- `GET /api/kpis` - Key performance indicators
- `GET /api/inventory_alerts` - Low inventory alerts
- `GET /api/automation_status` - Workflow status

### Orders
- `GET /api/orders_inbox` - List orders in inbox
- `GET /api/order_items/<id>` - Get order line items
- `POST /api/orders_inbox/flag/<order_number>` - Flag order for attention
- `POST /api/upload_orders_to_shipstation` - Manual upload to ShipStation

### Inventory
- `GET /api/inventory_transactions` - List inventory transactions
- `POST /api/inventory_transactions` - Create transaction
- `GET /api/lot_inventory` - FIFO lot inventory
- `POST /api/physical_count_adjustment` - Adjust inventory

### Reports
- `POST /api/reports/eod` - Run End-of-Day report
- `POST /api/reports/eow` - Run End-of-Week report
- `POST /api/reports/eom` - Run End-of-Month report
- `GET /api/charge_report` - Generate charge report

### SKU & Bundles
- `GET/POST /api/sku_lots` - SKU-Lot CRUD
- `GET/POST /api/bundles` - Bundle CRUD
- `GET /api/bundle_components/<id>` - Bundle components

### Alerts & Monitoring
- `GET /api/duplicate_alerts` - Duplicate order alerts
- `GET /api/lot_mismatch_alerts` - Lot mismatch alerts
- `GET /api/manual_order_conflicts` - Manual order conflicts
- `GET /api/shipping_violations` - Shipping validation alerts

### Workflow Controls
- `GET /api/workflow_controls` - List workflow states
- `PUT /api/workflow_controls/<name>` - Toggle workflow
- `POST /api/workflow_controls/<name>/run` - Manual run

### ShipStation Integration
- `POST /api/sync_shipstation` - Force sync
- `GET /api/shipstation/units_to_ship` - Units awaiting shipment
- `PUT /api/update_lot_in_shipstation` - Update lot in ShipStation

---

## Backend Automation

### Configured Workflows (7)

| Workflow | Script | Interval | Description |
|----------|--------|----------|-------------|
| `dashboard-server` | `app.py` | Continuous | Main Flask application |
| `xml-import` | `scheduled_xml_import.py` | 5 min | Import orders from Google Drive XML |
| `shipstation-upload` | `scheduled_shipstation_upload.py` | 5 min | Upload pending orders to ShipStation |
| `unified-shipstation-sync` | `unified_shipstation_sync.py` | 5 min | Sync status + import manual orders |
| `duplicate-scanner` | `scheduled_duplicate_scanner.py` | 15 min | Detect duplicate orders in ShipStation |
| `lot-mismatch-scanner` | `scheduled_lot_mismatch_scanner.py` | 15 min | Detect lot discrepancies |
| `orders-cleanup` | `scheduled_cleanup.py` | Daily | Delete orders older than 60 days |

### Business Hours Optimization

All automation workflows only run during business hours:
- **Monday-Friday**: 6:00 AM - 6:00 PM CST
- **Weekends**: OFF

This reduces database compute time by ~64% with zero business impact.

### Manual "Run Now" Capability

Admins can trigger any workflow on-demand via the Workflow Controls page, bypassing business hours restrictions.

---

## Frontend Pages

### 19 HTML Pages

| Page | File | Description |
|------|------|-------------|
| Dashboard | `index.html` | Main dashboard with KPIs and workflow status |
| Orders Inbox | `xml_import.html` | Order management and troubleshooting |
| Shipped Orders | `shipped_orders.html` | Historical shipped order list |
| Shipped Items | `shipped_items.html` | Line item detail view |
| Bundle SKUs | `bundle_skus.html` | Bundle product management |
| SKU-Lot | `sku_lot.html` | Lot number management |
| Lot Inventory | `lot_inventory.html` | FIFO lot tracking |
| Inventory Transactions | `inventory_transactions.html` | Inventory adjustments |
| Inventory Snapshots | `inventory_snapshots.html` | Historical snapshots |
| Weekly History | `weekly_shipped_history.html` | Weekly shipment summaries |
| Charge Report | `charge_report.html` | Monthly billing report |
| Order Management | `order-management.html` | Admin order tools |
| Order Audit | `order_audit.html` | Order comparison tool |
| Workflow Controls | `workflow_controls.html` | Automation management |
| Incidents | `incidents.html` | Production incident tracker |
| Email Contacts | `email_contacts.html` | Contact management |
| Settings | `settings.html` | System configuration |
| Help | `help.html` | User documentation |
| Landing | `landing.html` | Pre-auth landing page |

### Design System

- **Primary Color**: Oracare Blue (#2B7DE9)
- **Secondary Color**: Deep Navy (#1B2A4A)
- **Typography**: IBM Plex Sans (body), Source Serif 4 (hero stats)
- **Themes**: Light/Dark mode with glass effects
- **Responsive**: Full mobile support

---

## Authentication & Authorization

### Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: CRUD all records, run all reports (EOD/EOW/EOM), workflow controls, charge reports, delete records |
| **Operations** | Read + Limited Write: Run EOD/EOW (not EOM), add/edit inventory transactions, manage lot numbers. Cannot delete or access charge reports |
| **Viewer** | Read-only + Minor: View all data, report incidents, minor inventory adjustments (±4 units) |

### Implementation

- Replit Auth with Flask-Dance OAuth
- Session-based authentication
- Centralized API middleware (`src/auth/middleware.py`)
- Role stored in `users` table

---

## Data Flow

### Order Lifecycle

```
X-Cart (eCommerce)
    │
    ▼ (XML export)
Google Drive
    │
    ▼ (xml-import workflow)
orders_inbox + order_items_inbox
    │
    ▼ (shipstation-upload workflow)
ShipStation (awaiting_shipment)
    │
    ▼ (Fulfillment in ShipStation)
ShipStation (shipped)
    │
    ▼ (unified-shipstation-sync)
shipped_orders + shipped_items
    │
    ▼ (inventory deduction)
inventory_current / lot_inventory
```

### SKU-Lot Assignment Flow

1. XML files contain base SKUs only (e.g., "17612")
2. xml-import reads active lot from `sku_lot` table
3. Order items stored with full SKU-Lot (e.g., "17612 - 250362")
4. shipstation-upload re-validates and ensures current active lot is used
5. ShipStation receives orders with correct SKU-Lot format

### Critical Business Rule

**Orders without valid SKU-Lot mappings are NEVER uploaded to ShipStation.**

Three-layer validation:
1. Global check: Abort if no active lots exist
2. Item-level: Skip items without lot mappings
3. Order-level: Mark orders with no valid items as 'failed'

---

## External Integrations

### ShipStation API

| Endpoint | Usage |
|----------|-------|
| `GET /orders` | Fetch orders for sync |
| `POST /orders/createorders` | Upload new orders |
| `GET /shipments` | Fetch shipment data for EOD |
| `PUT /orders/{orderId}` | Update order details |
| `DELETE /orders/{orderId}` | Delete duplicate orders |

**Rate Limits**: 40 requests/minute (handled with retry logic)

### Google Drive API

- Monitors folder for new XML files
- Fetches XML content for parsing
- Uses service account authentication

### Google Sheets API (Legacy)

- Deprecated but still available for historical reference
- SKU-Lot management migrated to PostgreSQL

---

## Deployment

### Production Environment

- **Platform**: Replit (Continuous VM)
- **Database**: PostgreSQL (Replit-managed, separate from development)
- **Startup**: `start_all.sh` launches all workflows

### Environment Variables (Secrets)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SHIPSTATION_API_KEY` | ShipStation API credentials |
| `SHIPSTATION_API_SECRET` | ShipStation API secret |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google API credentials |

### Important Notes

- Development and Production use **SEPARATE databases**
- Schema changes must be applied to both environments
- Production logs are NOT visible in development workspace

---

## Troubleshooting

### Common Issues

**1. Orders uploading with wrong lot number**
- Check `sku_lot` table for correct active lot
- Verify production database has correct data (separate from dev)
- Review shipstation-upload logs for lot mapping output

**2. Duplicate orders in ShipStation**
- Check duplicate-scanner alerts
- Use Order Management page to delete duplicates
- Review manual_order_conflicts for conflicts

**3. Workflow not running**
- Verify workflow is enabled in workflow_controls
- Check if within business hours (6 AM - 6 PM CST)
- Use "Run Now" to bypass business hours

**4. Missing inventory data**
- Verify EOD report ran successfully
- Check inventory_transactions for adjustments
- Review inventory_daily_snapshots for historical data

### Log Locations

- **Application logs**: `/logs/app.log`
- **Workflow-specific**: Each workflow logs to console
- **Production logs**: Must be manually retrieved from production deployment

---

## Appendix

### Initial Inventory Baseline

- **Date**: September 19, 2025
- **Purpose**: Starting point for all inventory calculations

### Key Configuration Parameters

Stored in `configuration_params` table:
- Polling intervals
- Product name mappings
- Feature flags
- Business hours settings

---

*End of Technical Documentation*

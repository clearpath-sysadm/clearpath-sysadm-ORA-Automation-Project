# Duplicate Order Alerts - Technical Documentation

## Overview

The Duplicate Order Alerts system detects and manages orders in ShipStation that share the same **order number AND base SKU** across multiple ShipStation order IDs. This is a **ShipStation-focused** detection system that runs as a scheduled background workflow and surfaces alerts on the **Dashboard** (index.html).

**Key Distinction:** This system detects duplicates at the **(order_number + base_sku)** level within ShipStation itself. It is separate from the Manual Order Conflicts system which detects order number collisions between ShipStation and the local database.

---

## Database Schema

### `duplicate_order_alerts` Table

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer (serial) | NO | auto-increment | Primary key |
| order_number | text | NO | - | The order number with duplicates |
| base_sku | varchar | YES | - | Base SKU (without lot suffix, e.g. "17612") |
| duplicate_count | integer | NO | - | Number of duplicate ShipStation records |
| shipstation_ids | text | NO | - | JSON array of ShipStation order IDs |
| details | text | YES | - | JSON array of full duplicate record details |
| first_detected | timestamp | YES | CURRENT_TIMESTAMP | When the duplicate was first found |
| last_seen | timestamp | YES | CURRENT_TIMESTAMP | Most recent scan where duplicate was confirmed |
| status | text | YES | 'active' | Alert status: 'active', 'resolved', 'excluded' |
| resolved_at | timestamp | YES | - | When the alert was resolved |
| resolved_by | text | YES | - | Who resolved the alert |
| notes | text | YES | - | Admin notes |
| resolution_notes | text | YES | - | Auto-generated resolution explanation |

### `excluded_duplicate_orders` Table

Permanently excludes specific order+SKU combinations from future detection.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer (serial) | NO | auto-increment | Primary key |
| order_number | varchar | NO | - | Order number to exclude |
| base_sku | varchar | NO | - | Base SKU to exclude |
| excluded_at | timestamp | YES | CURRENT_TIMESTAMP | When excluded |
| excluded_by | varchar | YES | 'manual' | Who excluded it |
| exclusion_reason | text | YES | - | Reason for exclusion |

### `deleted_shipstation_orders` Table (Supporting)

Tracks ShipStation orders deleted through the dashboard for audit trail and auto-resolution logic.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer (serial) | NO | auto-increment | Primary key |
| shipstation_order_id | bigint | NO | - | ShipStation order ID that was deleted |
| order_number | varchar | YES | - | Order number |
| deleted_at | timestamp | NO | CURRENT_TIMESTAMP | Deletion timestamp |
| deleted_by | varchar | YES | 'dashboard' | Source of deletion |
| customer_name | varchar | YES | - | Customer name (audit data) |
| customer_email | varchar | YES | - | Customer email (audit data) |
| customer_company | varchar | YES | - | Company name (audit data) |
| ship_to_name | varchar | YES | - | Ship-to name (audit data) |
| ship_to_city | varchar | YES | - | Ship-to city (audit data) |
| ship_to_state | varchar | YES | - | Ship-to state (audit data) |
| order_total_cents | integer | YES | - | Order total in cents (audit data) |
| order_date | date | YES | - | Original order date (audit data) |
| items_json | text | YES | - | JSON of order items before deletion (audit data) |

---

## Detection Logic

### Scanner Service: `src/scheduled_duplicate_scanner.py`

**Workflow Name:** `duplicate-scanner`
**Interval:** Every 15 minutes (900 seconds)
**Business Hours:** Monday-Friday 6 AM - 6 PM CST only

#### Step 1: Fetch Orders from ShipStation
- Fetches ALL orders from ShipStation created in the last **90 days**
- Paginates through all pages (500 orders per page)
- If any API error occurs, the scan is marked as **failed** and existing alerts are preserved (never auto-resolved on failed scans)

#### Step 2: Identify Duplicates (`identify_duplicates()`)
- Groups orders by **(order_number, base_sku)** tuple
- Base SKU is extracted by stripping the lot suffix (e.g., `17612 - 250300` → `17612`)
- A duplicate exists when **2+ orders share the same order_number AND base_sku**
- Includes ALL order statuses (shipped, awaiting_shipment, cancelled, etc.)
- Each duplicate record captures: shipstation_id, order_number, base_sku, full_sku, quantity, order_status, create_date, customer_name, customer_company, order_total

#### Step 3: Identify Order Number Collisions (`identify_order_number_collisions()`)
- Separate detection: same order_number with **different ShipStation IDs** (regardless of SKU)
- Catches: manual duplicates, order number reuse, data corruption
- Results are logged but stored separately from duplicate_order_alerts

#### Step 4: Update Alerts Database (`update_duplicate_alerts()`)
1. Load currently active alerts from `duplicate_order_alerts`
2. Load permanently excluded order+SKU combos from `excluded_duplicate_orders`
3. For each detected duplicate:
   - Skip if permanently excluded
   - Update existing active alert (refresh count, IDs, details, last_seen)
   - Create new alert if not previously detected
4. **Auto-Resolution:**
   - Alerts no longer appearing in current scan → resolved with note "No longer appears as duplicate in ShipStation scan"
   - Alerts where ALL ShipStation IDs have been deleted (via `deleted_shipstation_orders`) → resolved
   - Alerts where remaining (non-deleted) IDs no longer appear as duplicates → resolved

---

## API Endpoints

### `GET /api/duplicate_alerts`
**Auth:** Login required (viewer+)
**Purpose:** Get all active duplicate order alerts with local DB matches

**Response:**
```json
{
  "success": true,
  "alerts": [
    {
      "id": 1,
      "order_number": "705001",
      "base_sku": "17612",
      "duplicate_count": 2,
      "shipstation_ids": [123456, 789012],
      "details": [
        {
          "shipstation_id": 123456,
          "order_number": "705001",
          "base_sku": "17612",
          "full_sku": "17612 - 250340",
          "quantity": 5,
          "order_status": "shipped",
          "create_date": "2026-01-15T10:00:00",
          "customer_name": "John Doe",
          "customer_company": "ACME Corp",
          "order_total": 150.00,
          "deleted": false
        }
      ],
      "first_detected": "2026-01-20T10:00:00",
      "last_seen": "2026-01-20T15:00:00",
      "status": "active",
      "local_matches": [
        {
          "id": 100,
          "order_number": "705001",
          "shipstation_order_id": "123456",
          "ship_name": "John Doe",
          "ship_company": "ACME Corp",
          "status": "awaiting_shipment",
          "created_at": "2026-01-15T10:00:00",
          "items": [
            {"sku": "17612", "sku_lot": "17612 - 250340", "quantity": 5}
          ]
        }
      ]
    }
  ],
  "count": 1
}
```

**Logic Details:**
- Only returns alerts with `status = 'active'`
- Cross-references `deleted_shipstation_orders` to mark deleted orders in details
- Fetches local DB matches from `orders_inbox` + `order_items_inbox` for each alert

### `PUT /api/duplicate_alerts/<alert_id>/exclude`
**Auth:** Admin required (centralized auth: PUT → admin)
**Purpose:** Permanently exclude a duplicate alert from future detection

**Request Body:**
```json
{
  "reason": "Known intentional duplicate"
}
```

**Logic:**
1. Fetches the alert's order_number and base_sku
2. Inserts into `excluded_duplicate_orders` table
3. Updates alert status to 'excluded'

### `DELETE /api/duplicate_alerts/delete_order/<shipstation_order_id>`
**Auth:** Admin required (centralized auth: DELETE → admin)
**Purpose:** Delete a duplicate order from ShipStation and track the deletion

**Logic:**
1. Calls `delete_order_from_shipstation()` which fetches full order details before deletion for audit trail
2. Records deletion in `deleted_shipstation_orders` with full customer data
3. Returns deletion confirmation with customer name

### `POST /api/duplicate_alerts/relink_order`
**Auth:** Admin required (centralized auth: POST → admin)
**Purpose:** Update local DB record to use a different ShipStation ID and sync all data

**Request Body:**
```json
{
  "order_number": "705001",
  "shipstation_id": "789012"
}
```

**Logic:**
1. Finds local order by order_number in `orders_inbox`
2. Fetches full order details from ShipStation API
3. Updates `orders_inbox` with: shipstation_order_id, status, all ship-to fields, all bill-to fields
4. Backfills items from ShipStation to `order_items_inbox`

### `POST /api/duplicate_alerts/sync_items/<order_inbox_id>`
**Auth:** Admin required (centralized auth: POST → admin)
**Purpose:** Sync items from ShipStation for a specific order with missing items

### `GET /api/admin/get_duplicate_orders`
**Auth:** Admin required (explicit `@admin_required` decorator)
**Purpose:** Get all unresolved duplicate orders with full live ShipStation details

**Note:** This endpoint is used programmatically but is NOT currently integrated into the Workflow Controls page UI.

**Logic:**
- Fetches all alerts where `status != 'resolved'`
- For each alert, makes live ShipStation API calls to fetch current order details per ShipStation ID
- Returns enriched data with real-time order status, items, and customer info

---

## Frontend UI

### Dashboard (index.html)

**Alert Display:**
- Alert count badge shown in the Alerts section
- Each alert shows: order number, base SKU, duplicate count, detection dates
- Expandable details showing each ShipStation order with: status, customer, SKU, quantity, creation date
- Deleted orders are visually marked in the details

**User Actions:**
1. **Delete Order** - Delete a specific ShipStation order from the duplicate set
2. **Relink Order** - Point local DB to a different ShipStation ID
3. **Sync Items** - Refresh local items from ShipStation data
4. **Exclude** - Permanently exclude this order+SKU from future detection

### Workflow Controls (workflow_controls.html)

**Note:** The `GET /api/admin/get_duplicate_orders` endpoint exists in the backend but is NOT currently rendered in the Workflow Controls page UI. Duplicate alerts are managed exclusively through the Dashboard.

---

## Auto-Resolution Rules

| Trigger | Resolution Note |
|---------|-----------------|
| Duplicate no longer detected in 90-day scan | "Auto-resolved: No longer appears as duplicate in ShipStation scan" |
| All ShipStation IDs deleted by user | "Auto-resolved: All duplicate ShipStation records deleted by user" |
| Remaining records after deletion no longer duplicated | "Auto-resolved: Remaining records after deletion no longer duplicates" |
| Manual exclusion | Status set to 'excluded' |

**Safety:** Auto-resolution ONLY occurs when the scan completes successfully. Failed scans preserve all existing alerts.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/scheduled_duplicate_scanner.py` | Background scanner service (detection + alert management) |
| `app.py` (lines ~5944-6065) | `GET /api/duplicate_alerts` endpoint |
| `app.py` (lines ~6098-6160) | `PUT /api/duplicate_alerts/<id>/exclude` endpoint |
| `app.py` (lines ~8666-8701) | `DELETE /api/duplicate_alerts/delete_order/<id>` endpoint |
| `app.py` (lines ~8703-8861) | `POST /api/duplicate_alerts/relink_order` endpoint |
| `app.py` (lines ~8863-8950) | `POST /api/duplicate_alerts/sync_items/<id>` endpoint |
| `app.py` (lines ~8953-9050) | `rescan_duplicates_for_order()` helper |
| `app.py` (lines ~9855-9973) | `GET /api/admin/get_duplicate_orders` endpoint |
| `index.html` | Dashboard UI for duplicate alerts |
| `workflow_controls.html` | Admin UI for duplicate management |

---

## Data Flow Diagram

```
ShipStation API (90-day lookback)
        │
        ▼
scheduled_duplicate_scanner.py (every 15 min)
        │
        ├── identify_duplicates()
        │   Groups by (order_number, base_sku)
        │   Detects 2+ orders with same combo
        │
        ├── identify_order_number_collisions()
        │   Groups by order_number only
        │   Detects same order# with different SS IDs
        │
        └── update_duplicate_alerts()
            │
            ├── Check excluded_duplicate_orders → Skip
            ├── Existing active alert → Update counts/IDs
            ├── New duplicate → Insert alert
            ├── No longer duplicate → Auto-resolve
            └── All deleted → Auto-resolve
                    │
                    ▼
            duplicate_order_alerts table
                    │
                    ▼
            Dashboard (index.html)
            ├── View alerts
            ├── Delete order → deleted_shipstation_orders
            ├── Relink order → orders_inbox update
            ├── Sync items → order_items_inbox update
            └── Exclude → excluded_duplicate_orders
```

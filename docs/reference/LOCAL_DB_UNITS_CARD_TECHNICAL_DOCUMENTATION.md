# Local DB Units Card - Technical Documentation

## Overview

The **Local DB Units** card on the dashboard displays the total quantity of units in the `orders_inbox` table that are ready to be shipped. This metric is critical for monitoring fulfillment pipeline health and detecting discrepancies between local database state and ShipStation.

**Card Location:** Dashboard (`index.html`) - Second card in the stats grid
**Frontend Element ID:** `#local-db-units`
**API Endpoint:** `GET /api/local/awaiting_shipment_count`

---

## Quick Reference

| Component | Value |
|-----------|-------|
| Frontend Element | `#local-db-units` |
| API Endpoint | `/api/local/awaiting_shipment_count` |
| Primary Table | `orders_inbox` |
| Items Table | `order_items_inbox` |
| Update Frequency | On each dashboard load |
| Refresh Interval | 60 seconds (auto-refresh) |

---

## 1. API Endpoint: `/api/local/awaiting_shipment_count`

### Location
`app.py` - Line 5344

### Purpose
Returns the count of units in the local database that are ready to ship. Excludes shipped, cancelled, and on-hold orders.

### Request
```http
GET /api/local/awaiting_shipment_count
```

### Response
```json
{
  "success": true,
  "total_units": 45,
  "order_count": 12,
  "last_updated": "2026-01-16T10:30:00",
  "debug_status_breakdown": {
    "pending": 3,
    "uploaded": 5,
    "awaiting_shipment": 4,
    "shipped": 120,
    "cancelled": 8
  },
  "debug_total_orders": 140,
  "debug_total_items": 350
}
```

### Core Query
```sql
SELECT 
    COUNT(DISTINCT o.id) as order_count,
    COALESCE(SUM(oi.quantity), 0) as total_units,
    MAX(o.created_at) as last_updated
FROM orders_inbox o
LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
WHERE o.status NOT IN ('shipped', 'cancelled', 'on_hold')
```

### Status Filtering Logic
| Status | Included in Count? | Reason |
|--------|-------------------|--------|
| `pending` | YES | Awaiting upload to ShipStation |
| `uploaded` | YES | Successfully uploaded, awaiting shipment |
| `awaiting_shipment` | YES | In ShipStation awaiting fulfillment |
| `failed` | YES | Upload failed, will retry |
| `awaiting_payment` | YES | Pre-payment status |
| `synced_manual` | YES | Manually created orders |
| `shipped` | NO | Already fulfilled |
| `cancelled` | NO | Order cancelled |
| `on_hold` | NO | Paused by operations |

---

## 2. Database Tables

### 2.1 `orders_inbox` (Primary Table)

The main table storing all orders awaiting fulfillment.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | NO | Primary key (auto-increment) |
| `order_number` | text | NO | Unique order identifier |
| `order_date` | date | NO | Date order was placed |
| `customer_email` | text | YES | Customer email address |
| `status` | text | NO | Current order status |
| `shipstation_order_id` | text | YES | ShipStation order ID (when uploaded) |
| `total_items` | integer | YES | Total items count |
| `total_amount_cents` | integer | YES | Order total in cents |
| `source_system` | text | YES | Origin: 'X-Cart' or 'ShipStation Manual' |
| `created_at` | timestamp | YES | Record creation time |
| `updated_at` | timestamp | YES | Last modification time |
| `failure_reason` | text | YES | Upload failure reason |
| `ship_name` | text | YES | Ship-to name |
| `ship_company` | text | YES | Ship-to company |
| `ship_street1` | text | YES | Ship-to address line 1 |
| `ship_city` | text | YES | Ship-to city |
| `ship_state` | text | YES | Ship-to state |
| `ship_postal_code` | text | YES | Ship-to postal code |
| `ship_country` | text | YES | Ship-to country |
| `shipping_carrier_code` | text | YES | Carrier code (e.g., 'fedex') |
| `tracking_number` | text | YES | Package tracking number |
| `tracking_status` | varchar | YES | FedEx tracking status code |

### 2.2 `order_items_inbox` (Items Table)

Line items for each order. **Critical for unit count calculation.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | NO | Primary key |
| `order_inbox_id` | integer | NO | FK to orders_inbox.id |
| `sku` | text | NO | Product SKU |
| `sku_lot` | text | YES | SKU-Lot combination (e.g., "17612 - 250372") |
| `quantity` | integer | NO | Unit quantity |
| `unit_price_cents` | integer | YES | Unit price in cents |

**Key Relationship:**
```sql
order_items_inbox.order_inbox_id → orders_inbox.id (CASCADE DELETE)
```

---

## 3. Order Status Lifecycle

### 3.1 Status Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           ORDER STATUS LIFECYCLE                          │
└──────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │  X-Cart XML │
    │   Import    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐      Upload       ┌─────────────┐
    │   pending   │─────Success───────▶│  uploaded   │
    │             │                    │             │
    └──────┬──────┘                    └──────┬──────┘
           │                                  │
           │ Upload                           │ ShipStation
           │ Failure                          │ Sync
           │                                  │
           ▼                                  ▼
    ┌─────────────┐                    ┌─────────────────┐
    │   failed    │◀───Retry───        │awaiting_shipment│
    │             │                    │                 │
    └─────────────┘                    └────────┬────────┘
                                                │
                                                │ Package
                                                │ Shipped
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │   shipped   │
                                         │             │
                                         └─────────────┘

    Side Paths:
    
    ┌─────────────┐                    ┌─────────────┐
    │   on_hold   │◀───Hold Request    │  cancelled  │
    │             │                    │             │
    └─────────────┘                    └─────────────┘

    ShipStation Manual Order Path:
    
    ┌─────────────────┐                    ┌─────────────┐
    │ ShipStation API │───New Order───────▶│   pending   │
    │  (Manual Entry) │                    │synced_manual│
    └─────────────────┘                    └─────────────┘
```

### 3.2 Status Definitions

| Status | Description | Counted in Local DB Units? |
|--------|-------------|---------------------------|
| `pending` | New order from XML import, awaiting upload | YES |
| `uploaded` | Successfully sent to ShipStation | YES |
| `awaiting_shipment` | In ShipStation queue | YES |
| `failed` | Upload failed, will retry | YES |
| `awaiting_payment` | Pre-payment hold | YES |
| `synced_manual` | Imported from ShipStation (manual order) | YES |
| `shipped` | Order fulfilled | NO |
| `cancelled` | Order cancelled | NO |
| `on_hold` | Paused by operations | NO |

---

## 4. Data Flow: How Orders Enter and Exit

### 4.1 Order Entry: XML Import

**Script:** `src/scheduled_xml_import.py`
**Interval:** Every 5 minutes

**Process:**
1. Polls Google Drive for new XML files
2. Parses X-Cart order XML
3. Inserts into `orders_inbox` with `status = 'pending'`
4. Inserts items into `order_items_inbox`
5. Looks up active lot from `sku_lot` table for each SKU

**Key Insert (Line 379):**
```sql
INSERT INTO orders_inbox (
    order_number, order_date, customer_email, status, total_items, source_system, ...
)
VALUES (%s, %s, %s, 'pending', %s, 'X-Cart', ...)
```

**Item Insert:**
```sql
INSERT INTO order_items_inbox (order_inbox_id, sku, sku_lot, quantity)
VALUES (%s, %s, %s, %s)
```

### 4.2 Order Upload: ShipStation Upload Service

**Script:** `src/scheduled_shipstation_upload.py`
**Interval:** Every 5 minutes

**Process:**
1. Selects orders with `status = 'pending'`
2. Re-validates SKU-Lot mappings from `sku_lot` table
3. Creates orders in ShipStation via API
4. Updates status to `'uploaded'` on success

**Selection Query (Line 218):**
```sql
SELECT id, order_number, ...
FROM orders_inbox
WHERE status = 'pending'
  AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
  AND order_number NOT IN (SELECT order_number FROM shipped_orders)
FOR UPDATE SKIP LOCKED
```

**Status Update on Success (Line 237):**
```sql
UPDATE orders_inbox
SET status = 'uploaded',
    failure_reason = %s,
    updated_at = CURRENT_TIMESTAMP
WHERE id IN (...)
```

**Status Update on Failure (Line 704):**
```sql
UPDATE orders_inbox
SET status = 'pending',
    failure_reason = %s,
    updated_at = CURRENT_TIMESTAMP
WHERE id = %s
```

### 4.3 Status Sync: Unified ShipStation Sync

**Script:** `src/unified_shipstation_sync.py`
**Interval:** Every 5 minutes

**Two Functions:**

#### A. `import_new_manual_order()` (Line 478)
Imports orders created directly in ShipStation (not via XML).

**Status Mapping:**
| ShipStation Status | Local DB Status |
|--------------------|-----------------|
| `awaiting_payment` | `awaiting_payment` |
| `awaiting_shipment` | `pending` |
| `shipped` | `shipped` |
| `on_hold` | `on_hold` |
| `cancelled` | `cancelled` |

#### B. `update_existing_order_status()` (Line 704)
Updates status for orders already in local DB.

**Status Mapping:**
| ShipStation Status | Local DB Status |
|--------------------|-----------------|
| `awaiting_payment` | `awaiting_payment` |
| `awaiting_shipment` | `awaiting_shipment` |
| `shipped` | `shipped` |
| `on_hold` | `on_hold` |
| `cancelled` | `cancelled` |

**Critical Protection (Line 751-755):**
```python
# Prevent downgrades to 'pending'/'awaiting_shipment' for already-uploaded orders
if current_status in ('uploaded', 'failed') and db_status in ('pending', 'awaiting_shipment'):
    logger.warning(f"🔒 BLOCKED status downgrade...")
    db_status = current_status
```

### 4.4 Order Cleanup: Scheduled Cleanup

**Script:** `src/cleanup_old_orders.py` (called by `src/scheduled_cleanup.py`)
**Interval:** Daily

**CRITICAL FIX (Jan 2026):** Only deletes **terminal** orders (shipped, cancelled).

**Previous Bug:** Was deleting ALL orders older than 60 days regardless of status, causing:
- Orders still awaiting shipment in ShipStation to be deleted locally
- Local DB Units showing 0 while ShipStation showed units pending

**Current Logic:**
```python
TERMINAL_STATUSES = ('shipped', 'cancelled')

# Only delete terminal orders
DELETE FROM orders_inbox
WHERE DATE(order_date) < %s
  AND status IN ('shipped', 'cancelled')
```

**Non-terminal orders are PRESERVED indefinitely** to maintain sync with ShipStation.

---

## 5. Frontend Integration

### 5.1 Dashboard HTML (`index.html`)

**Card Definition (Line 422-435):**
```html
<!-- Local DB Count -->
<a href="/xml_import.html?filter=pending" style="text-decoration: none; color: inherit;">
    <div class="stat-card" id="local-db-card" style="cursor: pointer; position: relative;">
        <span id="local-db-badge" class="mismatch-badge" style="display: none;">Mismatch</span>
        <div class="stat-value" id="local-db-units">0</div>
        <div class="stat-label">
            Local DB Units
            <span class="help-icon">
                <span class="help-tooltip">Units in local database ready to upload to ShipStation.</span>
            </span>
        </div>
        <div class="stat-change" id="local-db-timestamp">Loading...</div>
    </div>
</a>
```

### 5.2 JavaScript Data Loading (Line 1028-1065)

```javascript
async function loadDashboardData() {
    const [statsRes, alertsRes, automationRes, shipstationRes, localDbRes, onHoldRes, lotMismatchRes] = await Promise.all([
        fetch('/api/dashboard_stats'),
        fetch('/api/inventory_alerts'),
        fetch('/api/automation_status'),
        fetch('/api/shipstation/units_to_ship'),
        fetch('/api/local/awaiting_shipment_count'),  // <-- LOCAL DB UNITS
        fetch('/api/local/on_hold_count'),
        fetch('/api/lot_mismatch_count')
    ]);
    
    const localDb = await localDbRes.json();
    
    // Update Local DB card
    if (localDb.success) {
        localUnits = localDb.total_units || 0;
        document.getElementById('local-db-units').textContent = localUnits;
        document.getElementById('local-db-timestamp').textContent = 
            'Updated: ' + formatRelativeTime(localDb.last_updated);
    }
}
```

### 5.3 Mismatch Detection (Line 1096-1108)

The dashboard compares ShipStation units with Local DB units:

```javascript
// Mismatch detection
if (shipstation.success && localDb.success) {
    const mismatch = ssUnits !== localUnits;
    const ssBadge = document.getElementById('shipstation-badge');
    const localBadge = document.getElementById('local-db-badge');
    
    if (mismatch) {
        ssBadge.style.display = 'block';
        localBadge.style.display = 'block';
    } else {
        ssBadge.style.display = 'none';
        localBadge.style.display = 'none';
    }
}
```

---

## 6. Common Issues and Troubleshooting

### Issue: Local DB Units = 0 but ShipStation shows units

**Possible Causes:**

1. **Cleanup Deleted Non-Terminal Orders** (Fixed Jan 2026)
   - Old cleanup was deleting orders older than 60 days regardless of status
   - **Solution:** Updated cleanup to only delete terminal statuses

2. **Orders Missing Items**
   - Order exists but `order_items_inbox` has no rows
   - Check: `SELECT o.id, o.order_number FROM orders_inbox o LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id WHERE oi.id IS NULL`

3. **Status Filter Excluding Orders**
   - Orders marked as `shipped`, `cancelled`, or `on_hold` won't be counted
   - Check status breakdown in API response

### Issue: Mismatch Between ShipStation and Local DB

**Diagnostic Steps:**

1. Check API response debug fields:
   ```json
   "debug_status_breakdown": {...},
   "debug_total_orders": 958,
   "debug_total_items": 2400
   ```

2. Compare with ShipStation awaiting_shipment count

3. Look for orders in ShipStation not in local DB (sync gap)

4. Look for orders in local DB not in ShipStation (upload failures)

### Issue: "Updated: Never" Showing

**Cause:** No orders in `orders_inbox` table or all orders are excluded statuses.

**Check:**
```sql
SELECT COUNT(*), MAX(created_at) FROM orders_inbox 
WHERE status NOT IN ('shipped', 'cancelled', 'on_hold');
```

---

## 7. Related Workflows

| Workflow | Script | Impact on Local DB Units |
|----------|--------|--------------------------|
| `xml-import` | `scheduled_xml_import.py` | Adds new orders (increases count) |
| `shipstation-upload` | `scheduled_shipstation_upload.py` | Changes status pending→uploaded |
| `unified-shipstation-sync` | `unified_shipstation_sync.py` | Updates statuses from ShipStation |
| `orders-cleanup` | `scheduled_cleanup.py` | Removes terminal orders |
| `lot-mismatch-scanner` | `scheduled_lot_mismatch_scanner.py` | Detects SKU-Lot issues |
| `duplicate-scanner` | `scheduled_duplicate_scanner.py` | Detects duplicate orders |

---

## 8. Related API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/api/local/awaiting_shipment_count` | Local DB units count |
| `/api/shipstation/units_to_ship` | ShipStation units count |
| `/api/local/on_hold_count` | On-hold units count |
| `/api/dashboard_stats` | General dashboard statistics |
| `/api/discrepancy_details` | Detailed order-by-order comparison |

---

## 9. Monitoring & Alerts

### Server Logging

The API endpoint logs warnings when:
- Zero units but orders exist (potential issue)
- Query returns no results

**Log Source:** `Dashboard`

**Example Log:**
```
Local DB Units: 12 orders but 0 units. Status breakdown: {'pending': 12}
```

### Mismatch Badge

Visual indicator on dashboard when ShipStation and Local DB counts differ.

---

## 10. Configuration Parameters

| Parameter | Source | Default | Description |
|-----------|--------|---------|-------------|
| Cleanup retention | `cleanup_old_orders.py` | 60 days | Days before terminal orders are deleted |
| Dashboard refresh | `index.html` | 60 seconds | Auto-refresh interval |
| Status filter | API endpoint | Excludes shipped/cancelled/on_hold | Which statuses to count |

---

## Document History

| Date | Change |
|------|--------|
| Jan 16, 2026 | Initial documentation created |
| Jan 16, 2026 | Documented cleanup fix for non-terminal order preservation |

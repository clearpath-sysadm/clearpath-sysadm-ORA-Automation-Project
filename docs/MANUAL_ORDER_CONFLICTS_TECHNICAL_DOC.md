# Manual Order Conflicts - Technical Documentation

## Overview

The Manual Order Conflicts system detects and resolves **order number collisions** between manually-created ShipStation orders and existing orders in the local database. When someone creates an order directly in ShipStation using an order number that already exists (from a previously shipped or active order), a conflict is created so the order can be recreated with a unique number.

**Key Distinction:** This system handles **manual orders only** (order numbers in the 100000-109999 range, starting with "10"). It is separate from the Duplicate Order Alerts system which detects same-order-number + same-SKU duplicates within ShipStation itself.

**Where It Appears:**
- **Dashboard (index.html):** Alert bar + modal with conflict list and resolution actions
- **Workflow Controls (workflow_controls.html):** Recreate Order Tool (manual admin tool for ad-hoc recreations)

---

## Database Schema

### `manual_order_conflicts` Table

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer (serial) | NO | auto-increment | Primary key |
| conflicting_order_number | varchar | NO | - | The order number causing the conflict |
| shipstation_order_id | varchar | NO | - | ShipStation ID of the NEW/duplicate order (unique constraint) |
| customer_name | varchar | YES | - | Customer name of the duplicate order |
| original_ship_date | timestamp | YES | - | When the original order was created/shipped |
| detected_at | timestamp | YES | CURRENT_TIMESTAMP | When the conflict was detected |
| resolved_at | timestamp | YES | - | When the conflict was resolved |
| new_order_number | varchar | YES | - | The corrected order number after recreation |
| new_shipstation_order_id | varchar | YES | - | ShipStation ID of the newly created order |
| resolution_status | varchar | YES | 'pending' | Status: 'pending', 'resolved', 'recreated', 'dismissed', 'auto_resolved', 'synced' |
| original_company | varchar | YES | - | Company name of the original order |
| original_items | jsonb | YES | - | Items from the original local DB order |
| duplicate_company | varchar | YES | - | Company name of the duplicate/new order |
| duplicate_items | jsonb | YES | - | Items from the duplicate ShipStation order |
| original_order_status | varchar | YES | - | Status of the original order (shipped, awaiting_shipment, etc.) |

**Unique Constraint:** `shipstation_order_id` — prevents duplicate conflict records for the same ShipStation order.

---

## Detection Logic

### Detection Source: `src/unified_shipstation_sync.py`

**Workflow Name:** `unified-shipstation-sync`
**Interval:** Every 5 minutes

Manual order conflicts are detected during the ShipStation sync process when importing manual orders (orders created directly in ShipStation, not from XML/X-Cart).

#### Detection Flow:

1. **Sync fetches orders** from ShipStation with status changes
2. For each order, checks if the order_number already exists in `orders_inbox`
3. If it exists, compares ShipStation IDs:
   - **CASE 1: Local order has NULL shipstation_order_id** → Links the order (not a conflict, just linking)
   - **CASE 2: Local order has DIFFERENT non-NULL shipstation_order_id** → TRUE CONFLICT
4. For TRUE CONFLICTS, applies **manual order filter**:
   - Must start with "10"
   - Must be numeric
   - Must be in range 100000-109999
   - Non-manual collisions are logged but do NOT create `manual_order_conflicts` alerts

#### Conflict Record Creation:

```python
INSERT INTO manual_order_conflicts (
    conflicting_order_number, shipstation_order_id, customer_name, original_ship_date,
    original_company, original_items, duplicate_company, duplicate_items, original_order_status
)
VALUES (...)
ON CONFLICT (shipstation_order_id) DO NOTHING
```

**Data captured:**
- `conflicting_order_number`: The shared order number
- `shipstation_order_id`: The NEW/duplicate ShipStation order's ID
- `customer_name`: Ship-to name of the new order
- `original_ship_date`: Created_at of the original order in local DB
- `original_items`: Items from the original local DB order (from `order_items_inbox`)
- `duplicate_items`: Items from the new ShipStation order
- `original_company`: (currently set to NULL in detection code)
- `duplicate_company`: Company from the new ShipStation order's ship-to

### Auto-Resolution: `auto_resolve_manual_order_conflicts()`

Called at the end of each unified sync cycle:

1. Fetches all pending conflicts
2. For each conflict, queries ShipStation for all orders with that order number
3. If only 0-1 ShipStation IDs found → auto-resolve (conflict no longer exists)
4. If the specific conflicting ShipStation ID no longer exists → auto-resolve

---

## API Endpoints

### `GET /api/manual_order_conflicts`
**Auth:** Login required (viewer+)
**Purpose:** Get all pending manual order conflicts with proposed new order numbers

**Logic:**
1. Calculates proposed new order number:
   - Queries MAX order number from `shipped_orders` + `orders_inbox` where order_number < 200000
   - First conflict gets MAX+1, second gets MAX+2, etc.
2. Fetches all conflicts with `resolution_status = 'pending'`
3. Maps `original_order_status` to display-friendly text

**Response:**
```json
{
  "success": true,
  "conflicts": [
    {
      "id": 5588,
      "conflicting_order_number": "100568",
      "shipstation_order_id": "259586963",
      "customer_name": "Prosper Family Dentistry",
      "original_ship_date": "2025-11-13",
      "detected_at": "2026-02-03 20:29:15",
      "resolution_status": "pending",
      "original_company": "BENCO DENTAL SUPPLY CO",
      "original_items": [{"sku": "17612 - 250340", "quantity": 7}],
      "duplicate_company": null,
      "duplicate_items": [{"sku": "17612 - 250070", "quantity": 6}],
      "proposed_new_order_number": "100869",
      "original_order_status": "Shipped"
    }
  ],
  "count": 1
}
```

### `POST /api/manual_order_conflicts/<conflict_id>/recreate`
**Auth:** Admin required (centralized auth: POST → admin)
**Purpose:** Recreate a conflicting manual order with a new order number

**Workflow:**
1. Verify conflict exists and is pending
2. Calculate new order number (MAX from shipped_orders + orders_inbox where < 200000, then +1)
3. Fetch original order from ShipStation API by `shipstation_order_id`
4. Copy all order data, assign new order number
5. **Replace lot numbers:** For each item, extract base SKU, look up active lot from `sku_lot` table, replace with current active lot
6. Create new order in ShipStation via `POST /orders/createorder`
7. Auto-resolve the conflict (set `resolution_status = 'resolved'`, store `new_order_number` and `new_shipstation_order_id`)

**Response:**
```json
{
  "success": true,
  "message": "New order 100869 created successfully. Old conflict auto-resolved.",
  "old_order_number": "100568",
  "new_order_number": "100869",
  "new_shipstation_order_id": "259818057",
  "old_shipstation_order_id": "259586963",
  "auto_resolved": true
}
```

### `POST /api/manual_order_conflicts/<conflict_id>/confirm_delete`
**Auth:** Admin required (centralized auth: POST → admin)
**Purpose:** Delete the OLD conflicting order from ShipStation after verifying new order was created

**Workflow:**
1. Verify conflict has `new_order_number` and `new_shipstation_order_id` (new order must exist)
2. Delete old order from ShipStation via `DELETE /orders/<shipstation_order_id>`
3. Update conflict status to `'recreated'`
4. Log deletion with user attribution

**Known Issue:** This deletion uses `make_api_request(DELETE)` directly and does NOT call `delete_order_from_shipstation()`, so it is NOT logged to `deleted_shipstation_orders` table. This is a confirmed logging gap.

### `POST /api/manual_order_conflicts/<conflict_id>/dismiss`
**Auth:** Admin required (centralized auth: POST → admin)
**Purpose:** Dismiss a conflict without taking action

**Logic:**
- Sets `resolution_status = 'dismissed'` and `resolved_at = CURRENT_TIMESTAMP`
- Logs user who dismissed it

### `POST /api/manual_order_conflicts/<conflict_id>/sync`
**Auth:** Admin required (centralized auth: POST → admin)
**Purpose:** Sync original order data from ShipStation to local database

**Workflow:**
1. Fetch original order from ShipStation by `shipstation_order_id`
2. Validate order number matches
3. Map ShipStation status to local status
4. UPSERT into `orders_inbox` (update if exists, insert if not)
5. Sync items to `order_items_inbox`
6. If order is shipped, also update `shipped_orders` and `shipped_items`
7. Mark conflict as `'synced'`

### Recreate Order Tool (Workflow Controls Page)

**Separate from the conflict-based recreate above.** This is a standalone admin tool on the Workflow Controls page.

#### `POST /api/admin/recreate-order`
**Auth:** Admin required
**Purpose:** Manually recreate any order in ShipStation (not tied to a conflict record)

**Three-step workflow:**

**Step 1 - Fetch (`action=fetch`):**
- Fetches order from ShipStation by order number or ShipStation ID
- If multiple orders found, returns list for user selection
- Returns full order details including raw order data

**Step 2 - Create (`action=create`):**
- Takes raw order data + correct order number
- Creates new order in ShipStation with corrected number
- Verifies creation by fetching back

**Step 3 - Delete (`action=delete`):**
- Deletes old order from ShipStation (requires `confirmed=true`)
- Logs deletion in `deleted_shipstation_orders` via `delete_order_from_shipstation(fetch_details_first=True)`
- Cleans up local DB: deletes from `order_items_inbox` and `orders_inbox` by matching `shipstation_order_id`

#### `POST /api/admin/next-order-number`
**Auth:** Admin required
**Purpose:** Get the next available order number for auto-population

**Logic:**
- Queries MAX from `shipped_orders`, `orders_inbox`, AND `manual_order_conflicts` where < 200000
- Returns MAX + 1

---

## Frontend UI

### Dashboard (index.html) - Manual Order Conflicts Alert

**Alert Bar:**
- Orange alert bar appears when pending conflicts exist
- Shows count: "X manual order(s) use previously shipped order numbers"
- Click "View Conflicts" to open modal

**Modal Content:**
- Lists all pending conflicts
- Each conflict shows:
  - Conflicting order number
  - Original order: company, items, ship date, status
  - Duplicate order: customer name, company, items, ShipStation ID
  - Proposed new order number (auto-calculated)

**User Actions per Conflict:**
1. **Recreate with New Order Number** - Creates new order with next available number, auto-resolves conflict
2. **Confirm Delete Old Order** - Appears after recreation, deletes the old ShipStation order
3. **Dismiss** - Marks conflict as dismissed without action
4. **Sync from ShipStation** - Pulls original order data into local DB

**JavaScript Functions:**
- `checkManualOrderConflicts()` - Polls `/api/manual_order_conflicts` and updates alert bar
- `showManualOrderConflicts()` - Opens modal with conflict list
- `recreateManualOrder(conflictId, oldOrderNumber)` - Triggers recreation flow
- `confirmDeleteOldOrder(conflictId, oldOrderNumber, oldShipstationId)` - Triggers deletion
- `dismissManualOrderConflict(conflictId, orderNumber)` - Dismisses conflict
- `syncManualOrderFromShipStation(conflictId, orderNumber)` - Syncs from ShipStation

### Workflow Controls (workflow_controls.html) - Recreate Order Tool

**Location:** Bottom of Workflow Controls page, in the Admin Tools section

**UI Flow:**
1. **Step 1:** Enter wrong order number + correct order number → Fetch
2. **Step 1b:** (If multiple found) Select which ShipStation order to recreate
3. **Step 2:** Review old vs new order details side-by-side → Create
4. **Step 3:** Verify new order created → Confirm Delete Old Order
5. **Complete:** Success message with summary

**JavaScript Functions:**
- `resetRecreateFlow()` - Resets all steps
- `fetchAndRecreateOrder()` - Step 1: fetch + validate
- `selectOrderForRecreate(shipstationId)` - Step 1b: select from multiples
- `createRecreatedOrder()` - Step 2: create new order
- `deleteOldRecreatedOrder()` - Step 3: delete old order

---

## Resolution Status Values

| Status | Meaning | Set By |
|--------|---------|--------|
| `pending` | Conflict detected, awaiting action | Detection (unified sync) |
| `resolved` | New order created (old may still exist) | Recreate endpoint (Dashboard) |
| `recreated` | New order created AND old order deleted | Confirm Delete endpoint (Dashboard) |
| `dismissed` | Conflict dismissed without action | Dismiss endpoint |
| `auto_resolved` | Conflict no longer exists in ShipStation | Auto-resolution logic |
| `synced` | Original order synced to local DB | Sync endpoint (app.py line 7009) |

---

## Key Differences: Dashboard vs Workflow Controls Recreate

| Feature | Dashboard (Manual Order Conflicts) | Workflow Controls (Recreate Order Tool) |
|---------|-------------------------------------|----------------------------------------|
| Trigger | Auto-detected conflicts from sync | Manual admin action |
| Source Data | `manual_order_conflicts` table | Direct ShipStation API query |
| Order Filter | Manual orders only (100000-109999) | Any order number |
| Lot Update | Auto-replaces with active lot from `sku_lot` | No lot replacement |
| Conflict Tracking | Updates `manual_order_conflicts` record | No conflict record (standalone) |
| Local DB Cleanup | Does NOT clean up `orders_inbox` | Cleans up `orders_inbox` + `order_items_inbox` |
| Deletion Logging | Does NOT log to `deleted_shipstation_orders` | Logs via `delete_order_from_shipstation()` |
| Auth Level | Admin required (centralized auth) | Admin required (explicit decorator) |
| New Order Number | Auto-calculated (MAX+1) | User specifies (with auto-populated suggestion) |

---

## Known Issues

1. **Dashboard Recreate: No deletion audit trail** - When `confirm_delete` is used on the Dashboard, the old order deletion is NOT logged to `deleted_shipstation_orders`. The Workflow Controls recreate tool does log deletions.

2. **Dashboard Recreate: No local DB cleanup** - After recreating and deleting via the Dashboard flow, the old order may remain in `orders_inbox` with stale data. The Workflow Controls tool does clean up local DB records.

3. **Order number collision with non-manual orders** - When a non-manual order (not in 10xxxx range) has a collision, it's logged as a warning but no alert is created. These must be investigated manually.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/unified_shipstation_sync.py` (lines ~1150-1245) | Conflict detection logic during sync |
| `src/unified_shipstation_sync.py` (lines ~940-1015) | `auto_resolve_manual_order_conflicts()` |
| `app.py` (lines ~6353-6440) | `GET /api/manual_order_conflicts` endpoint |
| `app.py` (lines ~6442-6613) | `POST /api/manual_order_conflicts/<id>/recreate` endpoint |
| `app.py` (lines ~6615-6712) | `POST /api/manual_order_conflicts/<id>/confirm_delete` endpoint |
| `app.py` (lines ~6714-6763) | `POST /api/manual_order_conflicts/<id>/dismiss` endpoint |
| `app.py` (lines ~6765-7010) | `POST /api/manual_order_conflicts/<id>/sync` endpoint |
| `app.py` (lines ~10553-10789) | `POST /api/admin/recreate-order` endpoint (Workflow Controls tool) |
| `app.py` (lines ~10505-10550) | `POST /api/admin/next-order-number` endpoint |
| `index.html` (lines ~385-390) | Dashboard conflict alert bar |
| `index.html` (lines ~2421-2700) | Dashboard conflict modal + JavaScript functions |
| `workflow_controls.html` (lines ~301-382) | Recreate Order Tool UI |
| `workflow_controls.html` (lines ~1183-1450) | Recreate Order Tool JavaScript |

---

## Data Flow Diagram

```
ShipStation (manual orders)
        │
        ▼
unified_shipstation_sync.py (every 5 min)
        │
        ├── Order exists in orders_inbox?
        │       │
        │       ├── Same SS ID → Update status
        │       ├── NULL SS ID → Link it (not a conflict)
        │       └── DIFFERENT SS ID → COLLISION!
        │               │
        │               ├── Manual order (10xxxx)?
        │               │       │
        │               │       YES → INSERT into manual_order_conflicts
        │               │               │
        │               │               ▼
        │               │       Dashboard Alert (index.html)
        │               │       ├── Recreate → New order in SS + auto-resolve
        │               │       ├── Confirm Delete → Delete old from SS
        │               │       ├── Dismiss → Mark dismissed
        │               │       └── Sync → Pull SS data to local DB
        │               │
        │               └── NO → Log warning only
        │
        └── auto_resolve_manual_order_conflicts()
                │
                ├── Only 0-1 SS IDs left → auto_resolved
                └── Specific SS ID gone → auto_resolved


Workflow Controls (workflow_controls.html)
        │
        ▼
POST /api/admin/recreate-order (standalone tool)
        │
        ├── Step 1: Fetch order from ShipStation
        ├── Step 2: Create new order with correct number
        └── Step 3: Delete old order + clean up local DB
```

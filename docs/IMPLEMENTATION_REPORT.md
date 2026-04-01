# Oracare Fulfillment — Implementation Report

**Date:** April 1, 2026  
**Scope:** Full system — lot tracking schema, API layer, UI/UX, background workers, and data integrity

---

## 1. System Overview

Oracare Fulfillment is an internal operations dashboard for a medical/dental supply company. It manages the complete lifecycle of customer orders — from XML import through inventory deduction to ShipStation upload — with full lot-level traceability on every transaction.

The system is a Flask/PostgreSQL web application hosted on Replit. All background work runs as long-lived Python worker processes. The frontend is server-rendered HTML with vanilla JavaScript calling REST endpoints. There is no build step or frontend framework.

---

## 2. Architecture

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask (Python) |
| Database | PostgreSQL (Replit managed) |
| Background workers | Python scripts, run as Replit Workflows |
| Frontend | Vanilla HTML/CSS/JavaScript |
| External integrations | ShipStation API, Google Sheets/Drive |
| Design system | Global CSS (`/static/css/global-styles.css`), IBM Plex Sans + Source Serif 4 fonts |

### Directory Structure

```
/
├── app.py                          — All Flask routes and API endpoints (~11,500 lines)
├── src/
│   ├── auth/                       — Authentication middleware
│   ├── services/
│   │   └── database/
│   │       └── pg_utils.py         — Database connection helper
│   ├── utils/                      — Shared utilities and logger
│   ├── scheduled_shipstation_upload.py   — Upload worker (active workflow)
│   ├── scheduled_xml_import.py           — Order import worker (active workflow)
│   ├── scheduled_lot_mismatch_scanner.py — Lot audit worker (active workflow)
│   ├── scheduled_cleanup.py              — Orders cleanup worker
│   ├── scheduled_duplicate_scanner.py    — Duplicate detection worker
│   ├── scheduled_stuck_workflow_detector.py — Workflow health monitor
│   ├── unified_shipstation_sync.py       — Unified sync worker
│   └── shipstation_backfill_sync.py      — Historical backfill
├── migrations/
│   └── 009_lot_tracking_schema.py        — Lot tracking migration (live)
├── utils/
│   └── cleanup_shipstation_duplicates.py — Duplicate line item cleanup
├── docs/                           — Reports and reference docs
└── static/                         — CSS, JS, images
```

### Active Workflows

| Workflow | Script | Purpose |
|----------|--------|---------|
| `dashboard-server` | `app.py` | Flask web application |
| `xml-import` | `scheduled_xml_import.py` | Imports X-Cart XML order files |
| `shipstation-upload` | `scheduled_shipstation_upload.py` | Pushes orders to ShipStation |
| `lot-mismatch-scanner` | `scheduled_lot_mismatch_scanner.py` | Audits ShipStation lot numbers |
| `duplicate-scanner` | `scheduled_duplicate_scanner.py` | Detects duplicate orders |
| `orders-cleanup` | `scheduled_cleanup.py` | Removes stale pending orders |
| `stuck-workflow-detector` | `scheduled_stuck_workflow_detector.py` | Health monitoring |
| `unified-shipstation-sync` | `unified_shipstation_sync.py` | Keeps ShipStation in sync |

---

## 3. Database Schema

### Core Tables

**`skus`** — Master list of product SKUs  
```sql
sku_id    SERIAL PRIMARY KEY
sku_code  TEXT NOT NULL UNIQUE
```
Current state: 5 rows (17612, 17904, 17914, 18675, 18795)

---

**`lots`** — Individual lot records per SKU  
```sql
lot_id        SERIAL PRIMARY KEY
sku_id        INTEGER NOT NULL REFERENCES skus(sku_id)
lot_number    TEXT NOT NULL
status        TEXT NOT NULL  -- 'active' | 'inactive' | 'depleted' | 'quarantine'
received_date DATE
notes         TEXT
created_at    TIMESTAMPTZ DEFAULT NOW()
updated_at    TIMESTAMPTZ DEFAULT NOW()
UNIQUE (sku_id, lot_number)
```
Current state: 16 rows, 6 active lots

---

**`inventory_transactions`** — Every inventory movement, keyed to a lot  
```sql
id               SERIAL PRIMARY KEY
date             DATE NOT NULL
sku              TEXT NOT NULL
quantity         INTEGER NOT NULL      -- always stored positive
transaction_type TEXT NOT NULL         -- 'Receive' | 'Ship' | 'Adjust Up' | 'Adjust Down' | 'Repack'
notes            TEXT
lot_id           INTEGER REFERENCES lots(lot_id)
UNIQUE (date, sku, transaction_type, quantity, lot_id)
```
Sign convention: the quantity column is always stored positive. The balance view derives sign from `transaction_type` — Receive/Adjust Up/Repack add to balance, Ship/Adjust Down subtract.

---

**`shipstation_order_line_items`** — Records which lot was used for each ShipStation shipment  
```sql
id                  SERIAL PRIMARY KEY
order_inbox_id      INTEGER
sku                 TEXT
shipstation_order_id TEXT
created_at          TEXT
lot_id              INTEGER REFERENCES lots(lot_id)  -- nullable
UNIQUE (order_inbox_id, sku, COALESCE(lot_id, -1))
```

---

### `lot_balances` View

The central derived object. Computes real-time balance per lot from the full transaction history — no stored balance field.

```sql
CREATE OR REPLACE VIEW lot_balances AS
SELECT
    l.lot_id,
    s.sku_code,
    l.lot_number,
    l.status,
    l.received_date,
    l.notes,
    l.created_at,
    l.updated_at,
    COALESCE(SUM(
        CASE
            WHEN it.transaction_type IN ('Receive', 'Adjust Up', 'Repack') THEN it.quantity
            WHEN it.transaction_type IN ('Ship', 'Adjust Down')            THEN -it.quantity
            ELSE 0
        END
    ), 0) AS balance
FROM lots l
JOIN skus s ON s.sku_id = l.sku_id
LEFT JOIN inventory_transactions it ON it.lot_id = l.lot_id
GROUP BY l.lot_id, s.sku_code, l.lot_number, l.status,
         l.received_date, l.notes, l.created_at, l.updated_at;
```

No balance is ever stored directly. Every number shown on screen is computed live from this view.

---

### Key Indexes and Constraints

| Name | Purpose |
|------|---------|
| `UNIQUE (sku_id, lot_number)` on `lots` | Prevents duplicate lot registration per SKU |
| `inventory_transactions_date_sku_lot_id_type_qty_key` | Prevents duplicate transaction records |
| `idx_shipstation_order_line_items_unique` | Prevents duplicate ShipStation line items, NULL-safe via COALESCE |

---

## 4. Migration History

| Migration | Description |
|-----------|-------------|
| 001 | Add status values to orders_inbox |
| 002 | Add shipping validation fields |
| 007 | Add awaiting_shipment status (SQL) |
| 008 | Add last_run_at to workflow_controls (SQL) |
| **009** | **Full lot tracking schema rebuild — skus, lots, lot_balances, lot_id FKs on transactions and shipstation line items** |

Migration 009 (`migrations/009_lot_tracking_schema.py`) is the schema foundation for all lot tracking. It was run once against the live database and is idempotent — safe to inspect but not meant to re-run.

Opening balances were backfilled via `utils/backfill_lot_opening_balances.py`, which inserted 5 Receive transactions (one per active SKU) dated September 19, 2025, representing the end-of-day inventory position at the time the system came online.

---

## 5. Lot Tracking — Business Logic

### Lot Status Values

| Status | Meaning |
|--------|---------|
| `active` | Currently in use; workers assign this lot to new orders |
| `inactive` | Historical or not yet in rotation; ignored by workers |
| `depleted` | Balance has reached zero; kept for audit trail |
| `quarantine` | Pulled from service pending investigation |

### Balance Calculation

Balance = sum of all Receive/Adjust Up/Repack transactions − sum of all Ship/Adjust Down transactions for that lot.

There is no running total stored in any column. The view re-aggregates on every read. This eliminates the possibility of the stored balance drifting from actual transaction history.

### Opening Balance Pattern

When a new lot is created via the Lot Inventory page with an initial quantity:
1. A `lots` row is inserted with the given status, received date, and notes.
2. A `Receive` transaction is inserted into `inventory_transactions` with the lot's `lot_id`, dated to the received date. This is the opening balance — it follows the same path as any other receive, so the balance view picks it up automatically.
3. `inventory_current` is updated for the SKU to keep the SKU-level total in sync.

### Correction Pattern

When a correction is applied from the Lot Inventory page:
1. An `Adjust Up` or `Adjust Down` transaction is inserted into `inventory_transactions` linked to the lot's `lot_id`.
2. `inventory_current` is updated by the signed delta.
3. The balance view immediately reflects the new total on the next page load.
4. Duplicate corrections (same date, type, and amount for the same lot) are caught by the unique index and return HTTP 409 with a user-readable message.

### Delete Pattern

Deleting a lot requires clearing two foreign key references before the `lots` row itself can be removed:
1. `DELETE FROM inventory_transactions WHERE lot_id = ?` — removes all transaction history for the lot.
2. `UPDATE shipstation_order_line_items SET lot_id = NULL WHERE lot_id = ?` — decouples any ShipStation shipment records (preserves the shipment record, removes the lot reference).
3. `DELETE FROM lots WHERE lot_id = ?` — removes the lot.

This sequence applies to both the SKU Lot Management delete path and the Lot Inventory delete path.

### Multi-Active-Lot Behavior (Known Gap)

It is valid to have more than one `active` lot for the same SKU. This occurs in production when a new lot arrives before the previous lot is fully depleted. However, the background workers build a Python dict keyed by SKU code, so only one lot per SKU survives the dict construction — the one returned last by the database query (non-deterministic without ORDER BY).

This is a documented known gap. Full resolution requires a FIFO auto-assignment feature (planned) that will always select the oldest active lot first and transition to the next lot automatically when balance reaches zero.

---

## 6. API Endpoints — Lot Tracking

All endpoints are defined in `app.py` and return JSON.

### Lot Inventory (`/api/lot_inventory`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lot_inventory` | Returns all lots with live balance from `lot_balances` view, ordered by SKU then received date (NULLS LAST) |
| POST | `/api/lot_inventory` | Creates a new lot + optional opening-balance Receive transaction |
| PUT | `/api/lot_inventory/<lot_id>` | Updates lot metadata: received_date, status, notes. Balance corrections use the `/correct` endpoint — not this one |
| DELETE | `/api/lot_inventory/<lot_id>` | Deletes lot and its transaction history after clearing FK references |
| POST | `/api/lot_inventory/<lot_id>/correct` | Records an Adjust Up or Adjust Down transaction against a specific lot |

**POST `/api/lot_inventory` required fields:**
- `sku` — SKU code string
- `lot` — lot number string
- `received_date` — ISO date string
- `initial_qty` — integer (0 is valid; no transaction is created if zero)
- `status` — one of: `active`, `inactive`, `depleted`, `quarantine`
- `notes` — optional string

**POST `/api/lot_inventory/<id>/correct` required fields:**
- `correction_type` — `"Adjust Up"` or `"Adjust Down"`
- `amount` — positive integer
- `date` — ISO date string
- `notes` — optional string

---

### SKU Lot Management (`/api/sku_lots`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sku_lots` | Returns all lots with status, mapped to an `active: 0/1` field for frontend compatibility |
| POST | `/api/sku_lots` | Creates a new lot entry. Auto-creates the SKU in `skus` if it does not exist |
| PUT | `/api/sku_lots/<lot_id>` | Updates SKU, lot number, and active/inactive status |
| DELETE | `/api/sku_lots/<lot_id>` | Clears FK dependencies then deletes the lot |

---

### Lot Mismatch (`/api/lot_mismatch_*`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/get_lot_mismatch_count` | Returns count of open lot mismatch alerts |
| GET | `/api/get_lot_mismatch_alerts` | Returns all active mismatch alerts |
| POST | `/api/resolve_lot_mismatch_alert/<id>` | Marks an alert as resolved |
| POST | `/api/update_lot_in_shipstation` | Pushes corrected lot number to ShipStation via API |

---

## 7. UI/UX

### Design System

All pages share a single global stylesheet (`/static/css/global-styles.css`) with a consistent design language:
- **Fonts:** IBM Plex Sans (body/UI), Source Serif 4 (headings)
- **Layout:** Fixed sidebar navigation + scrollable content area
- **Themes:** Light and dark mode, toggled per-session and persisted in `localStorage`
- **Responsive:** Table views collapse to card views on screens narrower than 900px
- **Brand:** Oracare logo in sidebar header

### Navigation

The sidebar divides into two sections:

**Operations (always visible):**
- Dashboard
- Orders Inbox
- Inventory Monitor
- Lot Inventory
- Charge Report

**Admin & Data (collapsible):**
- Order Management
- Weekly Reports
- Shipped Orders
- Order Audit
- Shipped Items
- Bundle SKUs
- SKU Lot Management
- Inventory Snapshots
- Email Contacts
- Workflow Controls
- Server Logs

---

### Lot Inventory Page (`/lot_inventory.html`)

**Purpose:** Primary day-to-day interface for viewing lot balances, receiving new lots, applying corrections, and managing lot status.

**Layout:**
- Header with page title and "Add New Lot" button
- Full-width table (desktop) / card list (mobile ≤ 900px)

**Table columns:** SKU | Lot Number | Balance | Received Date | Status | Notes | Actions

**Status badges:** Color-coded pills — green for active, grey for inactive, orange for quarantine, red for depleted.

**Actions per row:** Edit (opens edit modal) | Correct (opens correction modal) | Delete (confirmation prompt)

**Add / Edit modal fields:**
- SKU (text)
- Lot Number (text)
- Initial Quantity (number, shown only on create)
- Received Date (date picker)
- Status (dropdown: active / inactive / depleted / quarantine)
- Notes (textarea)

**Correction modal fields:**
- Correction Type (dropdown: Adjust Up / Adjust Down)
- Amount (positive integer — direction is set by the type, not sign)
- Date (date picker)
- Notes (textarea, optional)

**Mobile card view:** Each lot is rendered as a card with the SKU and lot number in a header, quantity displayed prominently, and metadata in a 2-column grid below. Action buttons are full-width at the bottom of the card.

**Data loading:** On `DOMContentLoaded`, the page calls `GET /api/lot_inventory` and holds the result in a `lots` array. All renders are performed against this local array; the page reloads the array after any successful create, update, or delete.

---

### SKU Lot Management Page (`/sku_lot.html`)

**Purpose:** Administrative interface for managing the lot registry itself — creating, editing, and deleting lot entries without opening-balance transaction logic.

**Layout:** Header with "Add New SKU-Lot" button + table

**Table columns:** SKU | Lot Number | Active | Created | Updated | Actions

**Active field:** Displayed as a yes/no badge. Stored internally as `active: 1/0` for frontend compatibility; persisted as `status: 'active'/'inactive'` in the database.

**Actions per row:** Edit (inline or modal) | Delete (confirmation prompt)

**Distinction from Lot Inventory:** SKU Lot Management does not show balances and does not create transactions. It is the registry of lot definitions. Lot Inventory is the operational view that reads balances and records movements.

---

## 8. Background Workers — Lot Integration

### ShipStation Upload Worker (`scheduled_shipstation_upload.py`)

At startup, the worker builds two dicts from the `lots` and `skus` tables:

```python
SELECT s.sku_code, l.lot_number, l.lot_id
FROM lots l JOIN skus s ON s.sku_id = l.sku_id
WHERE l.status = 'active'

sku_lot_map    = {row[0]: row[1] for row in rows}   # sku → lot_number
sku_lot_id_map = {row[0]: row[2] for row in rows}   # sku → lot_id
```

For every order line uploaded to ShipStation:
- The lot number from `sku_lot_map` is sent as part of the ShipStation order payload
- A record is inserted into `shipstation_order_line_items` with `lot_id` from `sku_lot_id_map` to create a traceable link between the order and the lot

---

### Lot Mismatch Scanner (`scheduled_lot_mismatch_scanner.py`)

Builds an active lot mapping via `get_active_lot_mappings()`:

```python
SELECT s.sku_code, l.lot_number
FROM lots l JOIN skus s ON s.sku_id = l.sku_id
WHERE l.status = 'active'
```

For each order in ShipStation's "awaiting shipment" queue, it compares the lot number recorded on ShipStation against the currently active lot. Any discrepancy is written to the `lot_mismatch_alerts` table and surfaced as a dashboard alert with a direct "Fix in ShipStation" action.

---

### XML Import Worker (`scheduled_xml_import.py`)

When orders are imported from X-Cart XML files, the worker automatically assigns the active lot to each order line:

```python
active_lots = {row[0]: row[1] for row in cursor.fetchall()}  # sku → lot_number
lot = active_lots.get(sku)
```

The lot number is stamped onto the order line at import time, before the order is queued for upload.

---

## 9. Data Integrity Rules

| Rule | Enforcement |
|------|-------------|
| Lot number must be unique per SKU | `UNIQUE (sku_id, lot_number)` on `lots` |
| Transaction cannot be duplicated | `UNIQUE (date, sku, transaction_type, quantity, lot_id)` on `inventory_transactions` |
| ShipStation line item cannot be duplicated | `UNIQUE INDEX` on `(order_inbox_id, sku, COALESCE(lot_id, -1))` |
| Deleting a lot clears its transactions first | Application-enforced in `api_delete_sku_lot` and `api_delete_lot_inventory` |
| ShipStation lot reference is nulled on lot delete | Application-enforced in both delete endpoints |
| Duplicate correction returns HTTP 409 | `psycopg2.IntegrityError` caught and re-raised with user message |
| Status must be valid enum value | Application-level validation before any insert or update |

---

## 10. Current Data State

### Lots by SKU (as of April 1, 2026)

| SKU | Lot Number | Status | Balance |
|-----|-----------|--------|---------|
| 17612 | 250101 | inactive | 0 |
| 17612 | 250172 | inactive | 0 |
| 17612 | 250195 | inactive | 0 |
| 17612 | 250216 | inactive | 0 |
| **17612** | **250237** | **active** | **1,019** |
| 17612 | 250300 | inactive | 0 |
| **17612** | **250340** | **active** | **0** |
| 17612 | 250362 | inactive | 0 |
| 17612 | 250372 | inactive | 0 |
| 17904 | 240276 | inactive | 0 |
| **17904** | **250240** | **active** | **468** |
| 17914 | 240286 | inactive | 0 |
| **17914** | **250297** | **active** | **1,410** |
| **18675** | **240231** | **active** | **714** |
| **18795** | **11001** | **active** | **7,719** |
| 18795 | 11002 | inactive | 0 |

Note: SKU 17612 has two active lots (250237 and 250340). This is valid business behavior — a new lot arrived before the previous was depleted. Workers currently pick one arbitrarily; FIFO assignment is planned.

---

## 11. Known Gaps and Planned Work

### FIFO Lot Auto-Assignment (Planned)

**Problem:** Workers use a plain Python dict (`{sku: lot_number}`), so when multiple lots are active for the same SKU, only one survives the dict. The surviving lot is whichever row PostgreSQL happens to return last — non-deterministic.

**Planned solution:** Replace the dict build with an ordered query using `ORDER BY l.received_date ASC NULLS LAST, l.lot_id ASC`. Workers will always pick the oldest active lot first. When the oldest lot's balance reaches zero, it is automatically transitioned to `depleted` and the next lot becomes the primary. This mirrors standard pharmaceutical FIFO inventory practice.

### Obsolete SQLite Utility Scripts

`utils/create_corrected_orders.py` and `utils/import_initial_lot_inventory.py` both reference a `sku_lot` table via `sqlite3.connect('ora.db')` against an `ora.db` file that does not exist in the production environment. These scripts cannot run. They are excluded from active maintenance and retained for historical reference only.

---

## 12. Files Reference

| File | Role |
|------|------|
| `app.py` | All Flask routes; ~11,500 lines |
| `migrations/009_lot_tracking_schema.py` | Lot tracking migration — run once, live |
| `utils/backfill_lot_opening_balances.py` | One-time opening balance loader |
| `database_schema_complete.sql` | Reference schema export |
| `src/scheduled_shipstation_upload.py` | Upload worker with lot tagging |
| `src/scheduled_xml_import.py` | Order import with lot auto-assignment |
| `src/scheduled_lot_mismatch_scanner.py` | Lot audit worker |
| `utils/cleanup_shipstation_duplicates.py` | Duplicate line item cleanup |
| `lot_inventory.html` | Lot Inventory page (840 lines) |
| `sku_lot.html` | SKU Lot Management page (613 lines) |
| `docs/DRY_RUN_REPORT_LOT_TRACKING_MIGRATION.md` | Dry run findings and fix log |
| `docs/IMPLEMENTATION_REPORT.md` | This document |

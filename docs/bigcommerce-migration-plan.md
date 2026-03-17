# BigCommerce Migration Plan

## Overview

This document covers the planned transition from the existing X-Cart/XML-based order ingestion workflow to a new BigCommerce/ShipStation-based workflow.

**Key architectural decision (confirmed):** All orders — including manual and replacement orders — will be exclusively managed in BigCommerce. There is no longer a concept of a ShipStation-native manual order. BigCommerce natively pushes all order types to ShipStation, and the new ingestion worker is the single path for all of them.

**BigCommerce order numbers** start at 800000.

The plan is broken into three tasks in dependency order:
- **Task #3** — Build the ingestion worker (immediate, for Oracare dev testing today)
- **Task #1** — Complete the migration (retire XML pipeline, clean up codebase)
- **Task #2** — Update the UI (depends on Task #1)

---

## Task #3 — Build ShipStation ingestion worker
*Immediate — scoped for Oracare dev testing today*

### What & Why
Build the new ShipStation-based order ingestion worker in isolation so Oracare can test the new workflow in the dev environment today. This worker is read-only against ShipStation (GET requests only) and is safe to run in dev alongside all existing workers without any risk of writing to ShipStation.

### Done looks like
- A new worker `src/scheduled_shipstation_import.py` runs on a 5-minute polling interval
- It detects new BigCommerce orders in ShipStation that do not yet exist in `orders_inbox`
- The primary gate is the key product SKU filter — only orders containing at least one key product SKU (queried from `configuration_params WHERE category = 'Key Products'`) are imported
- As a secondary safety constraint during transition, the worker logs and skips any order numbers matching the old manual order format (`10xxxxx`) to avoid accidentally ingesting legacy data
- It assigns active lot numbers from the `sku_lot` table before inserting
- It inserts matching orders into `orders_inbox` with `source_system = 'BigCommerce'`
- It uses the existing `sync_watermark` table with `workflow_name = 'shipstation_import'` for polling state — no new tables introduced
- Duplicate detection prevents the same order being imported twice across concurrent runs
- A new Replit workflow named `shipstation-import` runs the worker and appears in the dashboard alongside other workers
- Oracare places a test order in ShipStation (via BigCommerce) and it appears in the dev orders inbox with the correct lot number assigned

### Out of scope
- Removing the xml-import worker or any existing pipeline (deferred to Task #1)
- Retiring the manual order path in `unified_shipstation_sync.py` (deferred to Task #1 — that path will simply not fire since no `10xxxxx` orders will be created going forward)
- Any writes to the ShipStation API (this worker is GET-only)
- Frontend/UI changes (Task #2)
- Database migration for `source_system` default (deferred to Task #1)

### Implementation steps
1. **Build the worker** — Create `src/scheduled_shipstation_import.py` modelled on the watermark polling pattern from `unified_shipstation_sync.py`. Use `workflow_name = 'shipstation_import'` in the `sync_watermark` table. Use the key product SKU filter as the primary gate (read from `configuration_params`, not hardcoded). As a secondary transition guard, log and skip any order numbers matching the old manual order format (`10xxxxx`). Assign active lot numbers from `sku_lot`. Insert into `orders_inbox` with `source_system = 'BigCommerce'`. Include duplicate detection to prevent double-imports across runs.

2. **Register the workflow** — Add a new Replit workflow named `shipstation-import` that runs `src/scheduled_shipstation_import.py` on the same schedule as other polling workers. Add it to `app.py`'s `WORKFLOW_SCRIPTS` dict so it can be manually triggered from the dashboard.

### Relevant files
- `src/unified_shipstation_sync.py` (watermark pattern, duplicate detection, import logic to model from)
- `src/scheduled_xml_import.py` (key product SKU query pattern to copy)
- `src/services/shipstation/api_client.py` (existing API client to reuse)
- `src/services/database/pg_utils.py`
- `app.py:8186-8210` (WORKFLOW_SCRIPTS registration)

---

## Task #1 — Replace XML import with ShipStation ingestion
*Depends on Task #3 being validated in dev*

### What & Why
With the ingestion worker proven in dev (Task #3), this task completes the migration by retiring the entire XML/Google Drive pipeline, fully removing the ShipStation manual order path, and updating all worker registrations.

### Done looks like
- The `xml-import` worker is replaced by the `shipstation-import` worker (built in Task #3) as the registered production ingestion worker
- New BigCommerce-origin orders arriving in ShipStation are automatically detected, assigned lot numbers, and inserted into `orders_inbox` with `source_system = 'BigCommerce'`
- The X-Cart parser, Google Drive XML-fetching code, manual XML upload route, and Google Drive file listing routes are removed
- A database migration has updated the `source_system` column default from `'X-Cart'` to `'BigCommerce'`
- The manual order import path in `unified_shipstation_sync.py` (the `order_number.startswith('10')` branch) is **fully retired and removed** — it is no longer needed since all orders originate in BigCommerce
- All three worker registration locations (`app.py` WORKFLOW_SCRIPTS dict, `init_database.py` seeding, `workflows` table) reference `shipstation-import` instead of `xml-import`
- All other downstream workers (shipstation-upload, unified-shipstation-sync status/tracking sync, scanners) continue functioning without changes
- `start_all.sh` launches the shipstation-import worker instead of the old xml-import worker
- `config/settings.py` is cleaned of `X_CART_XML_FILE_ID` and Google Drive folder ID references
- Legacy archived files referencing `x_cart_parser` are deleted

### Out of scope
- Frontend/UI template changes (handled in Task #2)
- Changes to lot assignment, ShipStation upload, or sync logic
- BigCommerce API integration (BigCommerce → ShipStation is handled natively by BigCommerce)
- Removing the `order_xml` column from the schema (it will go unused; removal can be deferred)
- Removing the `polling_state` table's `last_xml_count`/`last_xml_check` columns (they go unused; removal can be deferred)

### Cutover note — drain the XML queue first
Before stopping the `xml-import` worker, confirm that all pending X-Cart orders in the `orders.xml` file on Google Drive have already been imported (no orders remain in `pending` status that haven't yet reached `awaiting_shipment` or later). Orders already in `orders_inbox` are fully safe — downstream workers are source-agnostic. This is an operational coordination step at go-live, not a code change.

### Implementation steps
1. **Promote the ingestion worker** — The worker built in Task #3 becomes the permanent replacement. Update `init_database.py`'s `insert_workflow_controls` to seed `shipstation_import` instead of `xml_import`. Update `start_all.sh` to run the new script. Update the `workflows` table entry.

2. **Fully retire the manual order import path in `unified_shipstation_sync.py`** — Remove the `order_number.startswith('10')` branch and its entire associated import path. Since all orders now originate exclusively in BigCommerce, there is no longer a concept of a ShipStation-native manual order. The unified-sync worker retains only its status and tracking update responsibilities.

3. **Remove XML import pipeline** — Delete `src/scheduled_xml_import.py` and `src/services/data_parsers/x_cart_parser.py`. Remove the XML upload, Google Drive list, and Google Drive import API routes from `app.py` (around lines 3230, 3660, 3725). Note: the `orders_inbox` API route does not filter by `source_system` and requires no change. Remove or clean up `src/services/google_drive/api_client.py` if no other feature depends on it. Clean `config/settings.py` of `X_CART_XML_FILE_ID`, the Google Drive folder ID, and related X-Cart references. Delete `src/legacy_archived/shipstation_order_uploader.py` and `python-files/py_x_cart_parser.txt`.

4. **Update `app.py` WORKFLOW_SCRIPTS** — Replace the `xml-import` entry with `shipstation-import` pointing to the new script.

5. **Write database migration** — Create `migrations/009_update_source_system_default.sql`. In PostgreSQL this is a single `ALTER TABLE orders_inbox ALTER COLUMN source_system SET DEFAULT 'BigCommerce'` statement, plus an INSERT into `schema_migrations`. No table rebuild is required.

### Relevant files
- `src/scheduled_xml_import.py`
- `src/unified_shipstation_sync.py`
- `src/scheduled_shipstation_upload.py`
- `src/services/data_parsers/x_cart_parser.py`
- `src/services/google_drive/api_client.py`
- `src/services/shipstation/api_client.py`
- `src/legacy_archived/shipstation_order_uploader.py`
- `python-files/py_x_cart_parser.txt`
- `app.py:3230-3760,8186-8210`
- `init_database.py:97-118`
- `config/settings.py`
- `start_all.sh`
- `migrations/`

---

## Task #2 — Update UI for BigCommerce workflow
*Depends on Task #1*

### What & Why
Several dashboard pages still reference X-Cart, XML import, and Google Drive as the order source. Now that the backend ingests orders from ShipStation (BigCommerce-origin), the UI must be updated to reflect the new workflow accurately, including user-facing help content and the onboarding tour.

### Done looks like
- The Orders Inbox page no longer references X-Cart or XML files; labels and descriptions reflect BigCommerce/ShipStation as the order source
- The Workflow Controls page shows the `shipstation-import` worker (not `xml-import`) with its correct status and description
- The Logs page has a "ShipStation Import" log category instead of "XML Import"
- The Dashboard no longer references X-Cart as a data source for order statistics
- The Bundle SKUs page removes any XML-specific context while bundle configuration remains fully functional
- `help.html` no longer describes the Google Drive XML polling process; it reflects the new ShipStation-pull workflow
- `static/tour.js` onboarding step is updated to match the renamed worker/page
- No broken links or references to removed API routes remain in any template

### Out of scope
- Backend worker and route changes (handled in Task #1)
- Changes to lot assignment, order management logic, or ShipStation sync behavior
- Redesigning any page layout or adding new features

### Implementation steps
1. **Update Orders Inbox page** — Replace all X-Cart and XML import references in `xml_import.html` with BigCommerce/ShipStation language. Remove or update any action buttons that relied on the XML upload or Google Drive import routes that no longer exist on the backend.

2. **Update Workflow Controls and Logs pages** — In `workflow_controls.html`, replace the `xml-import` worker entry and its description with the `shipstation-import` worker. In `logs.html`, rename the "XML Import" log category to "ShipStation Import".

3. **Update Dashboard and supporting pages** — Remove X-Cart references from `index.html`. Update `bundle_skus.html` to remove any XML-specific context while keeping bundle configuration functional.

4. **Update help content and onboarding tour** — In `help.html`, replace the section describing the 5-minute Google Drive XML polling loop with accurate documentation of the new ShipStation-pull workflow. In `static/tour.js`, update the selector and description for the step that currently targets the XML Import navigation link.

### Relevant files
- `templates/xml_import.html`
- `templates/workflow_controls.html`
- `templates/logs.html`
- `templates/index.html`
- `templates/bundle_skus.html`
- `templates/help.html`
- `static/tour.js`

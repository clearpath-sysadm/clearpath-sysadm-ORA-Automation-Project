# BigCommerce Migration Plan

## Overview

This document covers the planned transition from the existing X-Cart/XML-based order ingestion workflow to a new BigCommerce/ShipStation-based workflow. It is broken into two tasks with a defined dependency order.

---

## Task #1 — Replace XML import with ShipStation ingestion

### What & Why
The app currently ingests new orders via XML files exported from X-Cart and polled from Google Drive. BigCommerce is replacing X-Cart and natively pushes orders to ShipStation. The app must now pull new incoming orders directly from the ShipStation API instead, eliminating the XML/Google Drive pipeline entirely.

### Done looks like
- The `xml-import` worker is replaced by a new `shipstation-import` worker that runs on the same polling interval
- New BigCommerce-origin orders arriving in ShipStation are automatically detected, assigned lot numbers, and inserted into `orders_inbox` with `source_system = 'BigCommerce'`
- The X-Cart parser, Google Drive XML-fetching code, manual XML upload route, and Google Drive file listing routes are removed
- A database migration has updated the `source_system` column default from `'X-Cart'` to `'BigCommerce'`
- The `sync_watermark` table tracks the new worker's polling state under `workflow_name = 'shipstation_import'`
- All three worker registration locations (`app.py` WORKFLOW_SCRIPTS dict, `init_database.py` seeding, `workflows` table) reference the new worker instead of `xml-import`
- All existing downstream workers (shipstation-upload, unified-shipstation-sync, scanners) continue functioning without changes
- `start_all.sh` launches the new ingestion worker instead of the old xml-import worker
- `config/settings.py` is cleaned of `X_CART_XML_FILE_ID` and Google Drive folder ID references
- Legacy archived files referencing `x_cart_parser` are deleted

### Out of scope
- Frontend/UI template changes (handled in Task #2)
- Changes to lot assignment, ShipStation upload, or sync logic
- BigCommerce API integration (BigCommerce → ShipStation is handled natively by BigCommerce)
- Removing the `order_xml` column from the schema (goes unused; deferrable)
- Removing the `polling_state` table's `last_xml_count`/`last_xml_check` columns (go unused; deferrable)

### Cutover note — drain the XML queue first
Before stopping the `xml-import` worker, confirm that all pending X-Cart orders in the `orders.xml` file on Google Drive have already been imported (no orders remain in `pending` status that haven't yet reached `awaiting_shipment` or later). Orders already in `orders_inbox` are fully safe — downstream workers are source-agnostic. This is an operational coordination step at go-live, not a code change.

### Open question before implementation
The current manual-order detection logic restricts ingestion to order numbers starting with `"10"`. BigCommerce order numbers will likely follow a different format. The executor should confirm the expected BigCommerce order number pattern with the team before removing or replacing this filter, to avoid inadvertently ingesting unrelated ShipStation orders.

### Implementation steps
1. **Create new ShipStation ingestion worker** — Build `src/scheduled_shipstation_import.py` that polls ShipStation for new orders not yet in the local database, applies key-product SKU filtering, assigns active lot numbers, and inserts into `orders_inbox` with `source_system = 'BigCommerce'`. Use the existing `sync_watermark` table with `workflow_name = 'shipstation_import'` for polling state — do not introduce any new table or mechanism. Copy the key product SKU query directly from `scheduled_xml_import.py` (`SELECT sku FROM configuration_params WHERE category = 'Key Products'`) rather than using the hardcoded SKU list in `unified_shipstation_sync.py`.

2. **Update `unified_shipstation_sync.py`** — Remove or narrow the manual-order import logic (the `order_number.startswith('10')` branch and associated import path), since that responsibility now belongs to the new dedicated ingestion worker. Ensure there is no double-import between the two workers.

3. **Remove XML import pipeline** — Delete `src/scheduled_xml_import.py` and `src/services/data_parsers/x_cart_parser.py`. Remove the XML upload, Google Drive list, and Google Drive import API routes from `app.py` (around lines 3230, 3660, 3725). Note: the `orders_inbox` API route does not filter by `source_system` and requires no change. Remove or clean up `src/services/google_drive/api_client.py` if no other feature depends on it after this change. Clean `config/settings.py` of `X_CART_XML_FILE_ID`, the Google Drive folder ID, and related X-Cart references. Delete `src/legacy_archived/shipstation_order_uploader.py` and `python-files/py_x_cart_parser.txt`.

4. **Register the new worker** — In `app.py`'s `WORKFLOW_SCRIPTS` dict (around line 8196), replace the `xml-import` entry with `shipstation-import` pointing to the new script. In `init_database.py`'s `insert_workflow_controls` function, replace the `xml_import` workflow seeding entry with `shipstation_import`. Update the `workflows` table entry accordingly. Update `start_all.sh` to swap the xml-import worker for the new script.

5. **Write database migration** — Create `migrations/009_update_source_system_default.sql` following the existing numbered migration convention. In PostgreSQL this is a single `ALTER TABLE orders_inbox ALTER COLUMN source_system SET DEFAULT 'BigCommerce'` statement, plus an INSERT into `schema_migrations`. No table rebuild is required.

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
- The Workflow Controls page shows the new `shipstation-import` worker (not `xml-import`) with its correct status and description
- The Logs page has a "ShipStation Import" log category instead of "XML Import"
- The Dashboard no longer references X-Cart as a data source for order statistics
- The Bundle SKUs page removes any XML-specific context while bundle configuration remains fully functional
- `help.html` no longer describes the Google Drive XML polling process; it reflects the new ShipStation-pull workflow
- `static/tour.js` selector for the XML Import navigation step is updated to match any renamed or repurposed page/link
- No broken links or references to removed API routes remain in any template

### Out of scope
- Backend worker and route changes (handled in Task #1)
- Changes to lot assignment, order management logic, or ShipStation sync behavior
- Redesigning any page layout or adding new features

### Implementation steps
1. **Update Orders Inbox page** — Replace all X-Cart and XML import references in `xml_import.html` with BigCommerce/ShipStation language. Remove or update any action buttons that relied on the XML upload or Google Drive import routes that no longer exist on the backend.

2. **Update Workflow Controls and Logs pages** — In `workflow_controls.html`, replace the `xml-import` worker entry and its description with the new `shipstation-import` worker. In `logs.html`, rename the "XML Import" log category to "ShipStation Import" to match the new worker.

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

# X-Cart / XML Pipeline Retirement Plan

**Date:** April 17, 2026  
**Status:** Approved — Awaiting Execution (Task #51)  
**Scope:** Full removal of the X-Cart / XML import pipeline from the codebase, workflows, and database. Historical X-Cart order data in the database is preserved untouched.

---

## Guiding Constraint

Historical `orders_inbox` rows with `source_system = 'X-Cart'` must be preserved. Any existing query clause that filters or excludes X-Cart rows (e.g. `AND source_system != 'X-Cart'`) must also be preserved, as it guards ShipStation-only logic against those historical records.

---

## Category 1 — Python Files: Delete Entirely

| # | File | Lines | Why It's Safe to Delete | Verification |
|---|------|-------|--------------------------|--------------|
| 1 | `src/scheduled_xml_import.py` | 634 | Runs the XML import workflow loop. No active code calls into it — the only references are `app.py:8470` (the `WORKFLOW_SCRIPTS` map, which is itself being removed) and two non-production migration scripts (`migration/scripts/freeze_production.py`, `migration_scripts/migrate_v2.py`). | `grep` confirmed no active Python module imports it. Its Replit workflow will also be removed, so no process will try to start it. |
| 2 | `src/x_cart_importer.py` | 575 | Legacy XCart importer. No active code imports it. | `grep` found zero `import x_cart_importer` or `from x_cart_importer` references in any non-archived, non-deleted file. |
| 3 | `src/services/data_parsers/x_cart_parser.py` | 258 | XML parser for X-Cart order format. Its only callers are `src/legacy_archived/shipstation_order_uploader.py` (already in the archive, never executed by any workflow) and `src/x_cart_importer.py` (being deleted above). | `grep` confirmed the two callers. Neither is part of any running workflow. |
| 4 | `src/fix_xml_lot_stamps.py` | 152 | One-off utility script that retroactively stamped lot numbers on historical XML orders. No callers anywhere. | `grep` across all `.py` files found zero references. |

---

## Category 2 — Google Drive API Client Module: Delete Entirely

| # | File | Why It's Safe to Delete | Verification |
|---|------|--------------------------|--------------|
| 5 | `src/services/google_drive/api_client.py` | Every function in the file is XML-specific. Active callers are: (a) `app.py` — the two Google Drive API routes being removed, and (b) `src/scheduled_xml_import.py` — being deleted. The only other caller is `src/legacy_archived/shipstation_order_uploader.py`, which is archived and not executed by any workflow. | `grep` on `google_drive` across all non-archived `.py` and `.html` files found only `app.py:4091` and `app.py:4156` — both inside routes being deleted. |
| 6 | `src/services/google_drive/__init__.py` | Empty file (zero bytes). Serves no purpose once the module is gone. | Confirmed empty via `cat`. |

---

## Category 3 — Test Data and Utility Files: Delete Entirely

| # | File | Why It's Safe to Delete | Verification |
|---|------|--------------------------|--------------|
| 7 | `src/test_data/x_cart_orders_uat_test.xml` | X-Cart XML test fixture. No production code reads these paths; they were only used by the XML importer being deleted. | No references in any active `.py` file. |
| 8 | `src/test_data/x_cart_orders_test_single.xml` | Same as above. | Same. |
| 9 | `src/test_data/x_cart_orders_bundle_test.xml` | Same as above. | Same. |
| 10 | `src/services/test_data/test_x_cart_orders.xml` | Same as above. | Same. |
| 11 | `python-files/py_generate_bundle_test_xml.txt` | Script for generating test XML data for X-Cart bundle testing. No callers. | `grep` found zero references in any `.py` file. |

---

## Category 4 — `app.py` Code Removed (Surgical Edits — File Stays)

| # | What's Removed | Location | Why It's Safe | Impact If Left In |
|---|----------------|----------|----------------|-------------------|
| 12 | `'xml_import.html'` from `ALLOWED_PAGES` list | Line 357 | Once the XML upload endpoint is gone, this entry becomes stale. The page continues to serve its Orders Inbox function — removing it from ALLOWED_PAGES prevents it from being incorrectly treated as a page the file-server needs to protect. | Stale entry; no immediate harm, but incorrect. |
| 13 | `'xml-import'` from the `expected_workflows` list | Line 537 | This list is used by the system health check to flag missing workflows. Once the workflow is removed, keeping `xml-import` here causes a permanent false "missing workflow" health alert. | Causes a permanent false-negative health check warning on every status call. |
| 14 | `'xml-import'` from the `workflow_controls` SQL `WHERE IN` clause | Line ~894 | Removing the workflow means its row will be deleted from `workflow_controls` via the new migration. Querying for it would return nothing and pollute the workflow status display with a blank row. | Returns an empty phantom row in the workflow controls API response. |
| 15 | `'xml-import': 'XML Import'` from `display_names` dict | Line ~901 | Companion to #14 — the display name for a workflow row that will no longer exist. | Dead map entry; harmless but incorrect. |
| 16 | `'xml-import'` from the `workflow_timestamps` SQL `WHERE IN` clause | Line ~943 | Same reasoning as #14 — querying for a deleted workflow row returns nothing. | Returns empty in the timestamp response. |
| 17 | `@app.route('/api/xml_import', methods=['POST'])` and entire function body | Lines 3655–~3755 | This route accepts XML file uploads and writes to `orders_inbox` with `source_system = 'X-Cart'`. No other file or workflow calls this endpoint once the upload form is cleaned up. | A live POST to this URL would succeed today; after deletion it returns 404, which is the intended state. |
| 18 | `@app.route('/api/google_drive/list_files')` and body | Lines 4087–4105 | Called exclusively by `xml_import.html`'s Drive-import UI, which is being cleaned up. No other page or script calls this. | 404 after removal. |
| 19 | `load_bundle_config_from_db()` helper function | Lines 4107–4129 | Used only by the `api_google_drive_import_file` route being removed. Confirmed via `grep` — zero other callers. | Orphaned dead code if its route is removed. |
| 20 | `expand_bundles()` helper function | Lines 4131–4150 | Same — exclusively called from the Drive import route. Confirmed via `grep`. | Same. |
| 21 | `@app.route('/api/google_drive/import_file/<file_id>', methods=['POST'])` and body | Lines 4152–~4300 | Called only by `xml_import.html`'s Drive-import UI. No other callers. Imports from the `google_drive` module being deleted. | 404 after removal; also eliminates the dangling import of the deleted module. |
| 22 | `'xml-import': ['src/scheduled_xml_import.py', '--once']` from `WORKFLOW_SCRIPTS` | Line 8470 | This map entry enables manually triggering the XML import via the dashboard. Once the workflow and script are removed, triggering it would crash (file not found). Removing the entry causes the manual-trigger endpoint to return a clean "unknown workflow" rejection instead of crashing. | Would cause a Python `FileNotFoundError` if someone attempted a manual run. |
| 23 | `or 'X-Cart'` default fallback on `source_system` | Line 3882 | This fallback was used when `orders_inbox` rows had a NULL `source_system`, implying X-Cart origin. Since no new X-Cart orders will ever be created, the fallback is misleading. Changed to `or ''` to show blank rather than a false X-Cart label on any future NULL rows. | Would label any future NULL `source_system` row as X-Cart — incorrect for BigCommerce-origin orders. |

---

## Category 5 — `config/settings.py` (Edit, File Stays)

| # | What's Removed | Line | Why It's Safe | Verification |
|---|----------------|------|----------------|--------------|
| 24 | `X_CART_XML_PATH = ...` constant | 234 | Used only by `src/scheduled_xml_import.py` and `src/x_cart_importer.py` — both being deleted. | `grep` found zero other references to `X_CART_XML_PATH`. |
| 25 | `drive.readonly` from the `SCOPES` list | 160 | The `SCOPES` list feeds the Google Drive service account auth in `api_client.py`. Once that module is deleted, nothing builds a Drive API client from these scopes. The Google Sheets integration uses Replit's OAuth connector, not this service account. | `grep` confirmed `SCOPES` is only consumed by `src/services/google_drive/api_client.py:138`. Removing `drive.readonly` leaves the `spreadsheets` scope intact for any remaining sheet operations. |

---

## Category 6 — Database Migration (New File)

| # | What | Why | Safety |
|---|------|-----|--------|
| 26 | New migration: `DELETE FROM workflow_controls WHERE workflow_name = 'xml-import'` | Migration 013 already disabled this workflow (`enabled = false`). Now that the workflow is fully retired, its row should be removed entirely so it no longer appears as a phantom disabled entry in the dashboard's workflow list. | Only deletes a single row matching `workflow_name = 'xml-import'`. All other workflow control rows are untouched. Historical `orders_inbox` data is in a completely separate table and is unaffected. |

---

## Critical Correction — `xml_import.html` Is NOT Being Deleted

| Item | Initial Assessment | Corrected Assessment | Evidence |
|------|-------------------|---------------------|----------|
| `xml_import.html` | Marked "delete entirely" in the preliminary scratchpad | **Must not be deleted.** This is the live **Orders Inbox** dashboard page, titled "Orders Inbox," linked from every other page in the dashboard (19 HTML files), and used by `index.html`'s dashboard stat widgets (`?filter=pending`, `?filter=hold`). | `grep` found 19 HTML files with nav links to this page. Page title is "Orders Inbox". The XML upload section inside it is already commented out ("BigCommerce pushes orders directly"). |
| `static/tour.js` | Not in scope | References `[href="/xml_import.html"]` for the tour step on the Orders Inbox nav item. Since the page URL is staying as-is, no change is needed here. | Line 206 of `tour.js`. |

The XML upload UI within `xml_import.html` (the file upload form and Google Drive picker section) is a small contained block that can be cleaned up as a follow-on, but the page itself and its URL remain unchanged.

---

## Preserved — Explicitly Left Alone

| Item | Reason |
|------|--------|
| `AND source_system != 'X-Cart'` at `app.py:10976, 10989` | Guards ShipStation-specific counts from including historical X-Cart orders. Historical rows still exist in the DB with this value. |
| `startup_migrations.py` X-Cart timezone guards (lines 565–600) | Same reason — protects historical X-Cart orders from incorrect timezone re-application if the migration ever re-runs. |
| `migrations/013_disable_xml_import_automation.sql` | Historical record of when the workflow was first disabled. Kept as an audit trail. |
| All `orders_inbox` and `order_items_inbox` rows with `source_system = 'X-Cart'` | Historical data — never modified. |
| `src/legacy_archived/shipstation_order_uploader.py` | Already archived and not executed by any workflow. Its dead import of the google_drive module is tolerable in an archived file. |

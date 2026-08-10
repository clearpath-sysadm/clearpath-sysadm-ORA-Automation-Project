# Legacy XML-Era Archived Files

These files are **retired and inactive**. They have been archived for historical reference only and must not be used or re-enabled.

## Why retired
The X-Cart / XML import pipeline was replaced by direct ShipStation ingestion (`src/unified_shipstation_sync.py`). All order processing now flows through ShipStation; no XML files or manual uploads are needed.

## Archived files

| File | What it was | Replaced by |
|------|-------------|-------------|
| `scheduled_xml_import.py` | Polled Google Drive for orders.xml every 5 min | `unified_shipstation_sync.py` |
| `scheduled_shipstation_upload.py` | Uploaded pending X-Cart orders to ShipStation | `unified_shipstation_sync.py` |
| `x_cart_importer.py` | Parsed X-Cart XML into orders_inbox rows | ShipStation webhook / sync |
| `x_cart_parser.py` | XML data-parser for X-Cart order format | ShipStation API client |
| `google_drive_api_client.py` | Google Drive API wrapper for fetching orders.xml | No longer needed |
| `shipstation_order_uploader.py` | Early uploader (pre-lot-mapping) | `unified_shipstation_sync.py` |
| `ShipStation_Importer.py` | Legacy importer | `unified_shipstation_sync.py` |
| `manual_shipstation_sync.py` | Old manual sync | `unified_shipstation_sync.py` |

## Current active system
**`src/unified_shipstation_sync.py`** — syncs all orders directly from ShipStation every 5 minutes. No XML, no Google Drive, no manual upload step.

Archived: 2026-08-10

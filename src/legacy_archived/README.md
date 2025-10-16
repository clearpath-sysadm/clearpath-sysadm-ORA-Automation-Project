# Legacy ShipStation Upload Files

These files are archived and should NOT be used. They are preserved for reference only.

## Archived Files:
- shipstation_order_uploader.py - Old uploader (pre-lot-mapping)
- ShipStation_Importer.py - Legacy importer
- manual_shipstation_sync.py - Old manual sync (replaced by unified_shipstation_sync.py)

## Current Active Upload System:
**ONLY USE**: src/scheduled_shipstation_upload.py
- Applies correct SKU-Lot mappings from sku_lot table
- Runs every 5 minutes automatically
- Handles duplicate detection properly

Archived on: Thu Oct 16 08:42:22 PM America 2025

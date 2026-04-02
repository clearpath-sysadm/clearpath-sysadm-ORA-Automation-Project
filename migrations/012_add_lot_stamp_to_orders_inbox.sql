-- Migration 012: Add lot_stamp to orders_inbox
-- Purpose: Caches the ShipStation advancedOptions.customField1 lot stamp on the
-- local order record so the dashboard can display which lot was assigned without
-- querying ShipStation again.
--
-- Populated by import_new_bigcommerce_order() on insert and by
-- update_existing_order_status() on every sync update
-- (uses COALESCE so a populated value is never cleared by a NULL from ShipStation).

ALTER TABLE orders_inbox
    ADD COLUMN IF NOT EXISTS lot_stamp text;

-- Migration 011: Add shipstation_order_id to inventory_transactions
-- Purpose: Idempotency key for lot inventory deductions — prevents double-deduction
-- when daily shipment processor or unified sync runs against the same shipped order.
--
-- Guard: SELECT WHERE (lot_id, shipstation_order_id, transaction_type = 'Ship')
-- before any INSERT into inventory_transactions with transaction_type = 'Ship'.
--
-- Also drops the redundant unique index on shipped_items (identical to
-- shipped_items_order_number_base_sku_sku_lot_key, never used).

ALTER TABLE inventory_transactions
    ADD COLUMN IF NOT EXISTS shipstation_order_id text;

DROP INDEX IF EXISTS uniq_shipped_items_key;

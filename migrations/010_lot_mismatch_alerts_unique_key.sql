-- Migration 010: Change lot_mismatch_alerts unique constraint from (order_number, base_sku)
-- to shipstation_order_id, and make shipstation_order_id NOT NULL.
--
-- Rationale: ShipStation auto-split produces multiple shipments from one BigCommerce order,
-- all sharing the same order_number (e.g., two 17612 shipments plus one 17914 shipment).
-- The old (order_number, base_sku) key collapsed split shipments with the same SKU into
-- a single alert, hiding one entirely. The ShipStation orderId is unique per split shipment
-- and is therefore the correct deduplication key.
--
-- Safe to run repeatedly (idempotent via DO $$...END$$).

DO $$
BEGIN
    -- Drop the old composite unique constraint if it still exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'lot_mismatch_alerts'::regclass
          AND conname = 'lot_mismatch_alerts_order_number_base_sku_key'
    ) THEN
        ALTER TABLE lot_mismatch_alerts
            DROP CONSTRAINT lot_mismatch_alerts_order_number_base_sku_key;
    END IF;

    -- Make shipstation_order_id NOT NULL if it is still nullable
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'lot_mismatch_alerts'
          AND column_name = 'shipstation_order_id'
          AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE lot_mismatch_alerts
            ALTER COLUMN shipstation_order_id SET NOT NULL;
    END IF;

    -- Add the new unique constraint if it does not already exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'lot_mismatch_alerts'::regclass
          AND conname = 'lot_mismatch_alerts_shipstation_order_id_key'
    ) THEN
        ALTER TABLE lot_mismatch_alerts
            ADD CONSTRAINT lot_mismatch_alerts_shipstation_order_id_key
            UNIQUE (shipstation_order_id);
    END IF;
END $$;

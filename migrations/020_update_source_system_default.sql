-- Migration 020: Update orders_inbox.source_system default from 'X-Cart' to 'ShipStation'
-- The X-Cart/XML import pipeline has been retired. All new orders come from ShipStation ingestion.
-- This is idempotent: running it multiple times has no adverse effect.

ALTER TABLE orders_inbox ALTER COLUMN source_system SET DEFAULT 'ShipStation';

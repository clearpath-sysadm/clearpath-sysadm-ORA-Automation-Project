-- Phase 0: Optimized Polling Schema Setup
-- Date: October 16, 2025
-- Purpose: Add polling_state table, feature flags, and indexes for optimized polling

-- ============================================
-- 1. Create polling_state table
-- ============================================
CREATE TABLE IF NOT EXISTS polling_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    last_upload_count INTEGER DEFAULT 0,
    last_upload_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_xml_count INTEGER DEFAULT 0,
    last_xml_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert single row for state tracking
INSERT INTO polling_state (id) VALUES (1) 
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 2. Add feature flags to configuration_params
-- ============================================
-- Note: configuration_params uses 'parameter_name' and 'value' columns
-- Unique constraint is on (category, parameter_name, sku)
INSERT INTO configuration_params (category, parameter_name, value, sku, notes)
VALUES 
  ('Polling', 'fast_polling_enabled', 'true', NULL, 'Enable 15-second polling checks'),
  ('Polling', 'fast_polling_interval', '15', NULL, 'Seconds between polling checks'),
  ('Polling', 'sync_interval', '120', NULL, 'Seconds between ShipStation sync cycles')
ON CONFLICT (category, parameter_name, sku) DO NOTHING;

-- ============================================
-- 3. Create index on awaiting_shipment status
-- ============================================
-- CRITICAL: Use 'awaiting_shipment' not 'Pending' (actual status value in DB)
CREATE INDEX IF NOT EXISTS idx_orders_inbox_awaiting 
ON orders_inbox(status) WHERE status = 'awaiting_shipment';

-- ============================================
-- 4. Set statement timeout for fast-fail
-- ============================================
-- Note: This sets timeout for the neondb database
ALTER DATABASE neondb SET statement_timeout = '15s';

-- ============================================
-- Verification queries (run manually after migration)
-- ============================================
-- SELECT * FROM polling_state;
-- SELECT * FROM configuration_params WHERE category = 'Polling';
-- \d orders_inbox
-- SHOW statement_timeout;

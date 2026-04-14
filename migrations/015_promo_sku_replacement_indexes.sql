-- Migration 015: Indexes and constraint validation for promo SKU replacement tables
--
-- Adds two indexes to promo_sku_replacement_log for efficient monitoring queries
-- and validates the status CHECK constraint (was created NOT VALID).

CREATE INDEX IF NOT EXISTS idx_promo_log_order_number
    ON promo_sku_replacement_log (order_number);

CREATE INDEX IF NOT EXISTS idx_promo_log_status_time
    ON promo_sku_replacement_log (status, processed_at DESC);

ALTER TABLE promo_sku_replacement_log
    VALIDATE CONSTRAINT promo_sku_replacement_log_status_check;

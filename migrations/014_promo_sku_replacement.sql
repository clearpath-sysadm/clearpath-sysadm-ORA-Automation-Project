-- Migration 014: Promotional SKU order replacement tables
--
-- sku_promotions: Maps promotional SKUs to their base fulfillment SKUs.
--   Seeded with the initial pair (17613 → 17612).
--   New mappings can be added here without code changes.
--
-- promo_sku_replacement_log: Records every replacement attempt outcome.
--   status values: replaced | failed | verify_failed | skipped
--   Queryable data source for future dashboard reporting.

CREATE TABLE IF NOT EXISTS sku_promotions (
    id          SERIAL PRIMARY KEY,
    promo_sku   TEXT NOT NULL UNIQUE,
    base_sku    TEXT NOT NULL,
    description TEXT,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO sku_promotions (promo_sku, base_sku, description)
VALUES ('17613', '17612', 'BXGY free unit — PT Kit')
ON CONFLICT (promo_sku) DO NOTHING;

CREATE TABLE IF NOT EXISTS promo_sku_replacement_log (
    id           SERIAL PRIMARY KEY,
    order_number TEXT NOT NULL,
    promo_sku    TEXT NOT NULL,
    base_sku     TEXT NOT NULL,
    status       TEXT NOT NULL,
    error_reason TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

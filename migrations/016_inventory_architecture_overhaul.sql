-- 016_inventory_architecture_overhaul.sql
-- Task #67: lot_balances as single source of truth
-- Steps 1, 2, 3, 18

-- Step 1: inventory_summary VIEW
-- Aggregates lot_balances per SKU excluding quarantined lots.
-- Uses status != 'quarantine' (not IN ('active','depleted')) because inactive lots
-- can hold substantial non-zero balances that must appear in the dashboard total.
CREATE VIEW inventory_summary AS
SELECT sku_code AS sku, SUM(balance) AS current_quantity
FROM lot_balances
WHERE status != 'quarantine'
GROUP BY sku_code;

-- Step 2: inventory_reconciliation_log table
-- One row per (ship_date, sku). Populated by the EOD reconciliation comparison.
-- UPSERT key: (ship_date, sku) — re-runs are idempotent.
CREATE TABLE inventory_reconciliation_log (
    id                 serial PRIMARY KEY,
    ship_date          date NOT NULL,
    run_date           date NOT NULL,
    sku                text NOT NULL,
    shipped_items_qty  int NOT NULL DEFAULT 0,
    lot_deduction_qty  int NOT NULL DEFAULT 0,
    gap                int NOT NULL DEFAULT 0,
    gap_pct            numeric,
    alert_threshold    int NOT NULL DEFAULT 5,
    is_flagged         bool NOT NULL DEFAULT false,
    notes              text,
    created_at         timestamptz DEFAULT now(),
    UNIQUE (ship_date, sku)
);

-- Step 3: Migrate reorder_point values out of inventory_current
-- All five key SKUs currently have reorder_point = 50 (confirmed from production).
INSERT INTO configuration_params (category, parameter_name, sku, value) VALUES
    ('ReorderPoint', 'reorder_point', '17612', '50'),
    ('ReorderPoint', 'reorder_point', '17904', '50'),
    ('ReorderPoint', 'reorder_point', '17914', '50'),
    ('ReorderPoint', 'reorder_point', '18675', '50'),
    ('ReorderPoint', 'reorder_point', '18795', '50')
ON CONFLICT (category, parameter_name, sku) DO NOTHING;

-- Step 18: Deprecation marker
COMMENT ON TABLE inventory_current IS
    'DEPRECATED as of 2026-04-21. Replaced by inventory_summary VIEW derived from lot_balances. Retained 30 days for rollback. No automated process should write to this table.';

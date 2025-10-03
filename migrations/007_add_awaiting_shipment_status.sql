-- Migration: Add 'awaiting_shipment' to status CHECK constraint
-- SQLite doesn't support modifying CHECK constraints, so we need to recreate the table

BEGIN TRANSACTION;

-- Create new table with updated constraint
CREATE TABLE "orders_inbox_new" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    order_date DATE NOT NULL,
    customer_email TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded', 'awaiting_shipment', 'failed', 'synced_manual', 'shipped', 'cancelled', 'on_hold', 'awaiting_payment')),
    shipstation_order_id TEXT,
    total_items INTEGER DEFAULT 0,
    total_amount_cents INTEGER,
    source_system TEXT DEFAULT 'X-Cart',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    failure_reason TEXT,
    ship_name TEXT,
    ship_company TEXT,
    ship_street1 TEXT,
    ship_street2 TEXT,
    ship_city TEXT,
    ship_state TEXT,
    ship_postal_code TEXT,
    ship_country TEXT,
    ship_phone TEXT,
    bill_name TEXT,
    bill_company TEXT,
    bill_street1 TEXT,
    bill_street2 TEXT,
    bill_city TEXT,
    bill_state TEXT,
    bill_postal_code TEXT,
    bill_country TEXT,
    bill_phone TEXT,
    shipping_carrier_code TEXT,
    shipping_carrier_id TEXT,
    shipping_service_code TEXT,
    shipping_service_name TEXT
);

-- Copy data from old table to new table
INSERT INTO orders_inbox_new 
SELECT * FROM orders_inbox;

-- Drop old table
DROP TABLE orders_inbox;

-- Rename new table to original name
ALTER TABLE orders_inbox_new RENAME TO orders_inbox;

COMMIT;

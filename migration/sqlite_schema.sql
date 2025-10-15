-- SQLite Schema Extracted from ora.db
-- Total tables: 20

CREATE TABLE workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'scheduled')),
            last_run_at TEXT,
            duration_seconds INTEGER,
            records_processed INTEGER,
            details TEXT,
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    ;

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE inventory_current (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            current_quantity INTEGER NOT NULL,
            weekly_avg_cents INTEGER,
            alert_level TEXT NOT NULL DEFAULT 'normal' CHECK (alert_level IN ('normal', 'low', 'critical')),
            reorder_point INTEGER NOT NULL DEFAULT 50,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    ;

CREATE TABLE shipped_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ship_date TEXT NOT NULL,
            order_number TEXT NOT NULL UNIQUE,
            customer_email TEXT,
            total_items INTEGER DEFAULT 0,
            shipstation_order_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        , shipping_carrier_code TEXT, shipping_carrier_id TEXT, shipping_service_code TEXT, shipping_service_name TEXT) STRICT
    ;

CREATE TABLE shipped_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ship_date TEXT NOT NULL,
            sku_lot TEXT NOT NULL DEFAULT '',
            base_sku TEXT NOT NULL,
            quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
            order_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, tracking_number TEXT,
            UNIQUE(order_number, base_sku, sku_lot),
            FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number)
        ) STRICT
    ;

CREATE TABLE weekly_shipped_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            sku TEXT NOT NULL,
            quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(start_date, end_date, sku)
        ) STRICT
    ;

CREATE TABLE system_kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL UNIQUE,
            orders_today INTEGER DEFAULT 0,
            shipments_sent INTEGER DEFAULT 0,
            pending_uploads INTEGER DEFAULT 0,
            system_status TEXT NOT NULL DEFAULT 'online' CHECK (system_status IN ('online', 'degraded', 'offline')),
            total_revenue_cents INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    ;

CREATE TABLE configuration_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            parameter_name TEXT NOT NULL,
            value TEXT NOT NULL,
            sku TEXT,
            notes TEXT,
            last_updated TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, parameter_name, sku)
        ) STRICT
    ;

CREATE TABLE "inventory_transactions" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity != 0),
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Receive', 'Ship', 'Adjust Up', 'Adjust Down', 'Repack')),
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, sku, transaction_type, quantity)
) STRICT
;

CREATE TABLE order_items_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_inbox_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    sku_lot TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER,
    FOREIGN KEY (order_inbox_id) REFERENCES orders_inbox(id) ON DELETE CASCADE
) STRICT
;

CREATE TABLE bundle_skus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bundle_sku TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    ) STRICT
;

CREATE TABLE bundle_components (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bundle_sku_id INTEGER NOT NULL,
        component_sku TEXT NOT NULL,
        multiplier INTEGER NOT NULL CHECK (multiplier > 0),
        sequence INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (bundle_sku_id) REFERENCES bundle_skus(id) ON DELETE CASCADE
    ) STRICT
;

CREATE TABLE sku_lot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    lot TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(sku, lot)
) STRICT;

CREATE TABLE shipstation_order_line_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_inbox_id INTEGER NOT NULL,
        sku TEXT NOT NULL,
        shipstation_order_id TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_inbox_id) REFERENCES orders_inbox(id)
    );

CREATE TABLE shipstation_metrics (
        id INTEGER PRIMARY KEY,
        metric_name TEXT UNIQUE NOT NULL,
        metric_value INTEGER NOT NULL,
        last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

CREATE TABLE sync_watermark (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_name TEXT NOT NULL UNIQUE,
        last_sync_timestamp TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

CREATE TABLE shipping_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                order_number TEXT NOT NULL,
                violation_type TEXT NOT NULL CHECK (violation_type IN ('hawaiian_service', 'benco_carrier', 'canadian_service')),
                expected_value TEXT NOT NULL,
                actual_value TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                is_resolved INTEGER NOT NULL DEFAULT 0 CHECK (is_resolved IN (0, 1)),
                FOREIGN KEY (order_id) REFERENCES orders_inbox(id) ON DELETE CASCADE
            );

CREATE TABLE "orders_inbox" (
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
        , tracking_number TEXT);

CREATE TABLE lot_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    lot TEXT NOT NULL,
    initial_qty INTEGER NOT NULL DEFAULT 0,
    manual_adjustment INTEGER NOT NULL DEFAULT 0,
    received_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(sku, lot)
) STRICT
;

CREATE TABLE workflow_controls (
            workflow_name TEXT PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT DEFAULT 'system'
        , last_run_at TIMESTAMP);

-- Indexes
CREATE INDEX idx_workflows_status ON workflows(status, enabled);

CREATE INDEX idx_workflows_enabled ON workflows(enabled);

CREATE INDEX idx_workflows_last_run ON workflows(status, last_run_at);

CREATE INDEX idx_inventory_current_alert ON inventory_current(alert_level);

CREATE INDEX idx_shipped_orders_date ON shipped_orders(ship_date);

CREATE INDEX idx_shipped_items_date ON shipped_items(ship_date);

CREATE INDEX idx_shipped_items_sku_date ON shipped_items(base_sku, ship_date);

CREATE INDEX idx_shipped_items_order ON shipped_items(order_number);

CREATE INDEX idx_weekly_history_dates ON weekly_shipped_history(start_date, end_date);

CREATE INDEX idx_weekly_history_sku_start ON weekly_shipped_history(sku, start_date);

CREATE INDEX idx_config_category ON configuration_params(category);

CREATE INDEX idx_config_sku ON configuration_params(sku);

CREATE UNIQUE INDEX uniq_shipped_items_key 
    ON shipped_items(order_number, base_sku, sku_lot)
;

CREATE INDEX idx_inv_trans_sku_date ON inventory_transactions(sku, date);

CREATE INDEX idx_inv_trans_date ON inventory_transactions(date);

CREATE INDEX idx_inv_trans_type ON inventory_transactions(transaction_type);

CREATE INDEX idx_order_items_inbox_order ON order_items_inbox(order_inbox_id);

CREATE INDEX idx_order_items_inbox_sku ON order_items_inbox(sku);

CREATE INDEX idx_bundle_skus_active ON bundle_skus(active);

CREATE INDEX idx_bundle_components_bundle ON bundle_components(bundle_sku_id);

CREATE INDEX idx_bundle_components_sku ON bundle_components(component_sku);

CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique
        ON shipstation_order_line_items(order_inbox_id, sku)
    ;

CREATE INDEX idx_violations_resolved ON shipping_violations(is_resolved, detected_at);

CREATE INDEX idx_violations_order ON shipping_violations(order_id);

CREATE INDEX idx_violations_type ON shipping_violations(violation_type);


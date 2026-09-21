CREATE TABLE IF NOT EXISTS sop_json_overrides (
    document_id TEXT PRIMARY KEY,
    content JSONB NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT sop_json_overrides_document_id_check CHECK (
        document_id IN (
            'inventory-lot-control',
            'order-corrections-cancellations',
            'daily-fulfillment-pick-list',
            'period-end-reporting'
        )
    )
);
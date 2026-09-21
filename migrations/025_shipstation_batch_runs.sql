CREATE TABLE IF NOT EXISTS shipstation_batch_runs (
    ship_date DATE PRIMARY KEY,
    external_batch_id TEXT NOT NULL UNIQUE,
    source_batch_id TEXT,
    replacement_batch_id TEXT,
    shipment_ids JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    verified_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Preserve a daily FedEx pickup reminder after the awaiting-shipment unit
-- count reaches the operational threshold, even if that live count later drops.

CREATE TABLE IF NOT EXISTS fedex_pickup_reminder_state (
    operational_date date PRIMARY KEY,
    peak_units integer NOT NULL CHECK (peak_units >= 185),
    threshold_reached_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone
);

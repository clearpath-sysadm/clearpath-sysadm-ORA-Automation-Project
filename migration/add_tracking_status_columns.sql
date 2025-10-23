-- Migration: Add Tracking Status Columns to orders_inbox
-- Date: October 23, 2025
-- Purpose: Enable real-time shipment tracking status display in Orders Inbox
-- Business Hours: 6 AM Pacific to 5 PM Eastern

-- Add tracking status columns
ALTER TABLE orders_inbox 
ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(10),
ADD COLUMN IF NOT EXISTS tracking_status_description TEXT,
ADD COLUMN IF NOT EXISTS exception_description TEXT,
ADD COLUMN IF NOT EXISTS tracking_last_checked TIMESTAMP,
ADD COLUMN IF NOT EXISTS tracking_last_updated TIMESTAMP;

-- Create index for tracking status queries
CREATE INDEX IF NOT EXISTS idx_orders_tracking_status 
ON orders_inbox(tracking_status) 
WHERE tracking_status IS NOT NULL;

-- Create index for tracking last checked (for efficient polling queries)
CREATE INDEX IF NOT EXISTS idx_orders_tracking_last_checked 
ON orders_inbox(tracking_last_checked) 
WHERE tracking_number IS NOT NULL AND tracking_number != '';

-- Add comment for documentation
COMMENT ON COLUMN orders_inbox.tracking_status IS 'ShipStation tracking status code: UN (Unknown), AC (Accepted), IT (In Transit), EX (Exception), DE (Delivered)';
COMMENT ON COLUMN orders_inbox.tracking_status_description IS 'Human-readable tracking status description';
COMMENT ON COLUMN orders_inbox.exception_description IS 'Delivery exception details (only populated when tracking_status = EX)';
COMMENT ON COLUMN orders_inbox.tracking_last_checked IS 'Last time tracking status was polled from ShipStation API';
COMMENT ON COLUMN orders_inbox.tracking_last_updated IS 'Last time tracking status actually changed';

-- Verify migration
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'orders_inbox' 
  AND column_name IN ('tracking_status', 'tracking_status_description', 'exception_description', 'tracking_last_checked', 'tracking_last_updated')
ORDER BY column_name;

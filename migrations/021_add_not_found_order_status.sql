-- Allow preserved ShipStation records that return a definitive 404 to leave
-- active-order reports without being deleted as shipped/cancelled history.

ALTER TABLE orders_inbox
DROP CONSTRAINT IF EXISTS orders_inbox_status_check;

ALTER TABLE orders_inbox
ADD CONSTRAINT orders_inbox_status_check
CHECK (status IN (
    'pending',
    'uploaded',
    'awaiting_shipment',
    'failed',
    'synced_manual',
    'shipped',
    'cancelled',
    'on_hold',
    'awaiting_payment',
    'not_found'
)) NOT VALID;

ALTER TABLE orders_inbox
VALIDATE CONSTRAINT orders_inbox_status_check;

UPDATE orders_inbox
SET status = 'not_found',
    failure_reason = 'Order no longer exists in ShipStation',
    updated_at = CURRENT_TIMESTAMP
WHERE order_number = '862283'
  AND shipstation_order_id = '278284894'
  AND status IN ('pending', 'awaiting_shipment');
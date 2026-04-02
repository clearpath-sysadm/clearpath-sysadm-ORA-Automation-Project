"""
Shared lot inventory deduction helper.

Called by both the daily shipment processor and the unified ShipStation sync
whenever a shipped order needs to be reflected in inventory_transactions.
"""

import logging
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']


def deduct_lot_inventory(
    order_number: str,
    shipstation_order_id: str,
    base_sku: str,
    customField1_value: str,
    ship_date,
    quantity: int,
    conn
) -> bool:
    """
    Record a lot inventory deduction in inventory_transactions for one shipped item.

    Rules:
    - Skips silently if customField1_value is empty (lot tagger hasn't run yet).
    - Skips silently if base_sku doesn't match the SKU prefix in customField1_value
      (this item isn't the one the lot stamp covers).
    - Guards against double-deduction using (lot_id, shipstation_order_id, 'Ship').
    - Uses 'Ship' (capital S) as transaction_type — the lot_balances VIEW requires it.
    - inventory_transactions.date is a TEXT column; ship_date is inserted as 'YYYY-MM-DD'.
    - After a successful deduction, marks the lot as 'depleted' if balance <= 0.

    Args:
        order_number:         Human-readable order number (for logging only).
        shipstation_order_id: ShipStation internal order ID (text). Used as idempotency key.
        base_sku:             The item's base SKU (e.g. '17612').
        customField1_value:   The order's customField1 string (e.g. '17612 - 260017').
                              Pass empty string or None to skip.
        ship_date:            date object or 'YYYY-MM-DD' string.
        quantity:             Units shipped (positive integer). Stored as negative deduction.
        conn:                 Active database connection (within an existing transaction).

    Returns:
        True  — deduction was inserted.
        False — skipped (no customField1, SKU mismatch, already deducted, or lot not found).
    """
    cf1 = (customField1_value or '').strip()
    if not cf1:
        logger.debug(f"Skipping deduction for order {order_number} / {base_sku}: no customField1")
        return False

    if ' - ' not in cf1:
        logger.debug(f"Skipping deduction for order {order_number}: customField1 '{cf1}' has no ' - ' separator")
        return False

    parts = cf1.split(' - ', 1)
    cf1_sku = parts[0].strip()
    lot_number = parts[1].strip()

    if cf1_sku != base_sku:
        logger.debug(
            f"Skipping deduction for order {order_number} / {base_sku}: "
            f"customField1 SKU '{cf1_sku}' doesn't match item SKU"
        )
        return False

    if not lot_number:
        logger.warning(f"Skipping deduction for order {order_number}: empty lot number in customField1 '{cf1}'")
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT l.lot_id
            FROM lots l
            JOIN skus s ON l.sku_id = s.sku_id
            WHERE l.lot_number = %s AND s.sku_code = %s
            LIMIT 1
        """, (lot_number, cf1_sku))
        row = cursor.fetchone()

        if not row:
            logger.warning(
                f"Skipping deduction for order {order_number}: "
                f"no lot found for lot_number='{lot_number}', sku='{cf1_sku}'"
            )
            return False

        lot_id = row[0]

        cursor.execute("""
            SELECT id FROM inventory_transactions
            WHERE lot_id = %s
              AND shipstation_order_id = %s
              AND transaction_type = 'Ship'
            LIMIT 1
        """, (lot_id, str(shipstation_order_id)))
        if cursor.fetchone():
            logger.debug(
                f"Skipping deduction for order {order_number}: "
                f"already deducted (lot_id={lot_id}, ss_order_id={shipstation_order_id})"
            )
            return False

        ship_date_str = ship_date.strftime('%Y-%m-%d') if hasattr(ship_date, 'strftime') else str(ship_date)[:10]

        # Sign convention: store POSITIVE quantity for 'Ship' transactions.
        # The lot_balances VIEW applies "CASE WHEN 'Ship' THEN -it.quantity" so it
        # negates the stored value when computing balance.  Storing negative here
        # would produce -(-qty) = +qty, inadvertently INCREASING the balance.
        # calculate_daily_inventory likewise does eod = bod - shipped_qty, so a
        # positive shipped_qty correctly decrements inventory.
        # All existing 'Receive' rows also store positive quantities.
        cursor.execute("""
            INSERT INTO inventory_transactions
                (date, sku, quantity, transaction_type, lot_id, shipstation_order_id, notes)
            VALUES (%s, %s, %s, 'Ship', %s, %s, %s)
        """, (
            ship_date_str,
            cf1_sku,
            abs(int(quantity)),
            lot_id,
            str(shipstation_order_id),
            order_number
        ))

        logger.info(
            f"Deducted {quantity} units from lot '{lot_number}' ({cf1_sku}) "
            f"for order {order_number} (ss_id={shipstation_order_id})"
        )

        cursor.execute("""
            SELECT balance FROM lot_balances WHERE lot_id = %s
        """, (lot_id,))
        balance_row = cursor.fetchone()
        if balance_row is not None and balance_row[0] <= 0:
            cursor.execute("""
                UPDATE lots SET status = 'depleted', updated_at = CURRENT_TIMESTAMP
                WHERE lot_id = %s AND status NOT IN ('depleted', 'quarantine', 'inactive')
            """, (lot_id,))
            if cursor.rowcount > 0:
                logger.info(f"Lot '{lot_number}' ({cf1_sku}, lot_id={lot_id}) marked as depleted (balance={balance_row[0]})")

        return True

    except Exception as e:
        logger.error(
            f"Error deducting lot inventory for order {order_number} / {base_sku}: {e}",
            exc_info=True
        )
        raise

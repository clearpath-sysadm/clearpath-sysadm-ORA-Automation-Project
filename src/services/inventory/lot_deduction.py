"""
Shared lot inventory deduction helper.

Called by unified_shipstation_sync whenever a shipped order needs to be
reflected in inventory_transactions. The daily shipment processor (EOD)
no longer calls this — EOD is read-only with respect to inventory.
"""

import logging
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.data_processing.sku_lot_parser import parse_cf1

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
    - Primary SKU path: if base_sku matches the SKU in customField1, deduct from that
      named lot directly.
    - Secondary SKU path: if base_sku does NOT match the SKU in customField1 (multi-SKU
      order), looks up base_sku's own active lot and deducts against it. Falls back to
      lot_id=NULL if no active lot exists (still recorded for audit trail, logged at WARNING).
    - Guards against double-deduction using (lot_id, shipstation_order_id, 'Ship').
      NULL-lot path uses (sku IS NULL, shipstation_order_id, 'Ship') because
      WHERE lot_id = NULL is always false in SQL.
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
        False — skipped (no customField1, already deducted, or lot not found for primary SKU).
    """
    cf1 = (customField1_value or '').strip()
    if not cf1:
        logger.debug(f"Skipping deduction for order {order_number} / {base_sku}: no customField1")
        return False

    if ' - ' not in cf1:
        logger.debug(f"Skipping deduction for order {order_number}: customField1 '{cf1}' has no ' - ' separator")
        return False

    cf1_sku, lot_number = parse_cf1(cf1)

    if cf1_sku != base_sku:
        # Multi-SKU order: customField1 stamps the primary SKU (cf1_sku), but this
        # item is a secondary SKU (base_sku).  Look up base_sku's active lot and
        # record the deduction against it instead of silently skipping.
        logger.info(
            f"Multi-SKU order {order_number}: cf1 stamps '{cf1_sku}', "
            f"looking up active lot for secondary SKU '{base_sku}'"
        )
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT l.lot_id
                FROM lots l
                JOIN skus s ON l.sku_id = s.sku_id
                WHERE s.sku_code = %s AND l.status = 'active'
                LIMIT 1
            """, (base_sku,))
            secondary_lot_row = cursor.fetchone()
            secondary_lot_id = secondary_lot_row[0] if secondary_lot_row else None

            if secondary_lot_id is None:
                logger.warning(
                    f"No active lot for secondary SKU '{base_sku}' in order {order_number}. "
                    f"Recording deduction with lot_id=NULL for audit trail."
                )
                # NULL fallback: WHERE lot_id = NULL is always false in SQL, so use IS NULL
                cursor.execute("""
                    SELECT id FROM inventory_transactions
                    WHERE sku = %s
                      AND lot_id IS NULL
                      AND shipstation_order_id = %s
                      AND transaction_type = 'Ship'
                    LIMIT 1
                """, (base_sku, str(shipstation_order_id)))
            else:
                # Lot found: same guard as the primary SKU path
                cursor.execute("""
                    SELECT id FROM inventory_transactions
                    WHERE lot_id = %s
                      AND shipstation_order_id = %s
                      AND transaction_type = 'Ship'
                    LIMIT 1
                """, (secondary_lot_id, str(shipstation_order_id)))

            if cursor.fetchone():
                logger.debug(
                    f"Skipping secondary deduction for order {order_number} / {base_sku}: "
                    f"already deducted (lot_id={secondary_lot_id}, ss_order_id={shipstation_order_id})"
                )
                return False

            ship_date_str = ship_date.strftime('%Y-%m-%d') if hasattr(ship_date, 'strftime') else str(ship_date)[:10]

            cursor.execute("""
                INSERT INTO inventory_transactions
                    (date, sku, quantity, transaction_type, lot_id, shipstation_order_id, notes)
                VALUES (%s, %s, %s, 'Ship', %s, %s, %s)
            """, (
                ship_date_str,
                base_sku,               # use base_sku, NOT cf1_sku
                abs(int(quantity)),
                secondary_lot_id,       # may be None (NULL lot fallback)
                str(shipstation_order_id),
                order_number
            ))

            logger.info(
                f"Deducted {quantity} units from secondary SKU '{base_sku}' "
                f"(lot_id={secondary_lot_id}) for order {order_number} (ss_id={shipstation_order_id})"
            )

            # Depletion check — only when a real lot_id was found
            if secondary_lot_id is not None:
                cursor.execute("""
                    SELECT balance FROM lot_balances WHERE lot_id = %s
                """, (secondary_lot_id,))
                balance_row = cursor.fetchone()
                if balance_row is not None and balance_row[0] <= 0:
                    cursor.execute("""
                        UPDATE lots SET status = 'depleted', updated_at = CURRENT_TIMESTAMP
                        WHERE lot_id = %s AND status NOT IN ('depleted', 'quarantine', 'inactive')
                    """, (secondary_lot_id,))
                    if cursor.rowcount > 0:
                        logger.info(
                            f"Lot (lot_id={secondary_lot_id}, sku='{base_sku}') marked as depleted "
                            f"(balance={balance_row[0]})"
                        )

            return True

        except Exception as e:
            logger.error(
                f"Error deducting secondary lot inventory for order {order_number} / {base_sku}: {e}",
                exc_info=True
            )
            raise

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

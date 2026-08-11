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
from src.services.inventory import lot_reservation
from src.services.shipstation.promo_sku_handler import _write_admin_alert

logger = logging.getLogger(__name__)

KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']


def _auto_promote_next_lot(conn, sku_code: str, depleted_lot_number: str) -> None:
    """
    When a lot is depleted, automatically activate the next inactive lot for
    the same SKU (FIFO order: earliest received_date, then lowest lot_id as
    tiebreaker). Only promotes 'inactive' lots — 'quarantine' is intentionally
    held back. Fires an admin alert either way so the team is aware.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.lot_id, l.lot_number
            FROM lots l
            JOIN skus s ON s.sku_id = l.sku_id
            WHERE s.sku_code = %s
              AND l.status = 'inactive'
            ORDER BY
                l.received_date ASC NULLS LAST,
                l.lot_id ASC
            LIMIT 1
        """, (sku_code,))
        row = cursor.fetchone()
        if row:
            next_lot_id, next_lot_number = row
            cursor.execute("""
                UPDATE lots SET status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE lot_id = %s
            """, (next_lot_id,))
            msg = (
                f"\u2705 Lot {depleted_lot_number} ({sku_code}) depleted \u2014 "
                f"automatically activated next lot {next_lot_number}. "
                f"Verify the new lot\u2019s opening balance is correct in Lot Inventory."
            )
            logger.info(msg)
            _write_admin_alert(conn, msg)
        else:
            msg = (
                f"\u26a0\ufe0f Lot {depleted_lot_number} ({sku_code}) depleted and no inactive lot "
                f"is available to promote. Add a new lot in Lot Inventory to resume tagging."
            )
            logger.warning(msg)
            _write_admin_alert(conn, msg)
    except Exception as e:
        logger.error(f"Error during auto-promotion for SKU {sku_code}: {e}", exc_info=True)


def _check_negative_balance(conn, lot_id, sku, lot_number, order_number):
    """
    Task #131: alert (instead of silently allowing) when a lot's computed
    balance goes negative after a deduction. This is what happened in the
    2026-07-06 incident — inventory went to -108 units with no alert.
    """
    if lot_id is None:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM lot_balances WHERE lot_id = %s", (lot_id,))
    row = cursor.fetchone()
    if row is not None and row[0] < 0:
        lot_reservation.record_negative_balance_alert(
            conn, lot_id, sku, lot_number, row[0],
            context=f"After deduction for order {order_number}"
        )


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

            # Task #131: consume the reservation made at tagging time instead of
            # independently re-picking "the active lot" here — the tagger already
            # made the balance-aware decision; deduction must honor it.
            consumed = lot_reservation.consume_reservation(conn, shipstation_order_id, base_sku)
            secondary_lot_number = None
            if consumed:
                secondary_lot_id = consumed['lot_id']
                secondary_lot_number = consumed['lot_number']
                if consumed['reserved_qty'] != abs(int(quantity)):
                    logger.warning(
                        f"Reservation/ship qty mismatch for order {order_number} / {base_sku}: "
                        f"reserved={consumed['reserved_qty']} shipped={abs(int(quantity))}"
                    )
            else:
                cursor.execute("""
                    SELECT l.lot_id, l.lot_number
                    FROM lots l
                    JOIN skus s ON l.sku_id = s.sku_id
                    WHERE s.sku_code = %s AND l.status = 'active'
                    LIMIT 1
                """, (base_sku,))
                secondary_lot_row = cursor.fetchone()
                secondary_lot_id = secondary_lot_row[0] if secondary_lot_row else None
                secondary_lot_number = secondary_lot_row[1] if secondary_lot_row else None
                if secondary_lot_id is not None:
                    logger.warning(
                        f"No reservation found for order {order_number} / secondary sku {base_sku} "
                        f"(order tagged before reservation system existed?) — falling back to "
                        f"independent active-lot lookup (lot_id={secondary_lot_id})."
                    )

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
                        _auto_promote_next_lot(conn, base_sku, secondary_lot_number or str(secondary_lot_id))
                _check_negative_balance(conn, secondary_lot_id, base_sku, secondary_lot_number, order_number)

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

        # Task #131: cross-check against the reservation made at tagging time.
        # The lot_id here is derived from CF1 (which the tagger wrote from its
        # reservation), so under normal operation they always agree — this
        # consumes the reservation and alerts loudly if they ever disagree
        # (e.g. CF1 was hand-edited in ShipStation after tagging) instead of
        # silently deducting against a lot the reservation system never approved.
        consumed = lot_reservation.consume_reservation(conn, shipstation_order_id, cf1_sku)
        if consumed and consumed['lot_id'] != lot_id:
            logger.error(
                f"Reservation/CF1 lot mismatch for order {order_number} / {cf1_sku}: "
                f"reservation pointed to lot_id={consumed['lot_id']} ('{consumed['lot_number']}') "
                f"but CF1 says lot_number='{lot_number}' (lot_id={lot_id}). Deducting against the "
                f"CF1 lot (what ShipStation will actually ship) and flagging for review."
            )
            lot_reservation.record_negative_balance_alert(
                conn, lot_id, cf1_sku, lot_number, 0,
                context=(
                    f"Reservation/CF1 mismatch on order {order_number}: reserved lot_id="
                    f"{consumed['lot_id']} ('{consumed['lot_number']}') vs CF1 lot_id={lot_id} "
                    f"('{lot_number}')"
                ),
            )
        elif not consumed:
            logger.debug(
                f"No open reservation found for order {order_number} / {cf1_sku} at ship time "
                f"(order tagged before reservation system existed?) — deducting from CF1 lot directly."
            )

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
                _auto_promote_next_lot(conn, cf1_sku, lot_number)

        _check_negative_balance(conn, lot_id, cf1_sku, lot_number, order_number)

        return True

    except Exception as e:
        logger.error(
            f"Error deducting lot inventory for order {order_number} / {base_sku}: {e}",
            exc_info=True
        )
        raise

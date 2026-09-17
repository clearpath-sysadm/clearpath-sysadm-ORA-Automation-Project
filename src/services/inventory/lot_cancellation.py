"""
Inventory cancellation reversal helper.

Called by sync services whenever a previously-shipped order is cancelled in
ShipStation and its inventory deductions need to be restored.

How it works:
    Finds all 'Ship' rows in inventory_transactions keyed on the given
    shipstation_order_id and inserts a matching 'Cancel' row for each,
    restoring the lot balance.  The lot_balances VIEW credits 'Cancel'
    rows as positive contributions (same sign as 'Receive').

Idempotency:
    Each (lot_id, shipstation_order_id, 'Cancel') triple is unique in the DB
    (enforced by the inventory_transactions_lot_ss_type_key index).  The
    pre-check queries for an existing 'Cancel' row before inserting, so
    running this function multiple times for the same order is safe.

Depleted lot recovery:
    After inserting reversal rows, each affected lot's balance is re-checked.
    Lots that were marked 'depleted' solely because of the now-reversed
    shipment and whose balance is again positive are restored to 'active'.
"""

import logging
import datetime

logger = logging.getLogger(__name__)


def reverse_lot_inventory(
    order_number: str,
    shipstation_order_id: str,
    cancel_date,
    conn
) -> int:
    """
    Insert 'Cancel' transactions for every 'Ship' row tied to shipstation_order_id.

    Args:
        order_number:         Human-readable order number (for logging/notes only).
        shipstation_order_id: ShipStation internal order ID used as the lookup key.
                              Must match the value stored in the original Ship rows.
        cancel_date:          date object or 'YYYY-MM-DD' string for the Cancel row.
                              Typically today's date or the ShipStation cancel date.
        conn:                 Active database connection (within an existing transaction).

    Returns:
        Number of 'Cancel' rows inserted (0 if nothing to reverse or all already reversed).
    """
    cursor = conn.cursor()
    ss_id = str(shipstation_order_id)

    cancel_date_str = (
        cancel_date.strftime('%Y-%m-%d')
        if hasattr(cancel_date, 'strftime')
        else str(cancel_date)[:10]
    )

    # Only live Ship effects can be reversed. An archived Ship is already
    # excluded from lot_balances, so crediting it with a live Cancel row would
    # double-return the same inventory.
    cursor.execute("""
        SELECT id, lot_id, sku, quantity
        FROM inventory_transactions
        WHERE shipstation_order_id = %s
          AND transaction_type = 'Ship'
          AND archived_at IS NULL
        ORDER BY id
    """, (ss_id,))
    ship_rows = cursor.fetchall()

    if not ship_rows:
        logger.info(
            f"No Ship transactions found for order {order_number} "
            f"(ss_id={ss_id}) — nothing to reverse"
        )
        return 0

    reversals_inserted = 0

    for _ship_id, lot_id, sku, quantity in ship_rows:
        # Idempotency: any existing Cancel row, including an intentionally
        # archived one, means this shipment has already had a reversal record.
        # Do not silently recreate an administrator-archived correction.
        # NULL lot_id requires IS NULL comparison (= NULL is always false in SQL).
        if lot_id is not None:
            cursor.execute("""
                SELECT id FROM inventory_transactions
                WHERE lot_id = %s
                  AND shipstation_order_id = %s
                  AND transaction_type = 'Cancel'
                LIMIT 1
            """, (lot_id, ss_id))
        else:
            cursor.execute("""
                SELECT id FROM inventory_transactions
                WHERE lot_id IS NULL
                  AND sku = %s
                  AND shipstation_order_id = %s
                  AND transaction_type = 'Cancel'
                LIMIT 1
            """, (sku, ss_id))

        if cursor.fetchone():
            logger.debug(
                f"Cancel already exists for order {order_number}, "
                f"lot_id={lot_id}, sku={sku} — skipping"
            )
            continue

        # Insert the reversal row.
        # Sign convention: store POSITIVE quantity for 'Cancel' rows.
        # The lot_balances VIEW credits 'Cancel' as +quantity, mirroring 'Receive'.
        cursor.execute("""
            INSERT INTO inventory_transactions
                (date, sku, quantity, transaction_type, lot_id, shipstation_order_id, notes)
            VALUES (%s, %s, %s, 'Cancel', %s, %s, %s)
        """, (
            cancel_date_str,
            sku,
            abs(int(quantity)),
            lot_id,
            ss_id,
            order_number,
        ))

        reversals_inserted += 1
        logger.info(
            f"↩️  Reversed {quantity} units (lot_id={lot_id}, sku={sku}) "
            f"for order {order_number} (ss_id={ss_id})"
        )

        # Re-evaluate lot depletion status.
        # If the lot was marked 'depleted' because of this shipment and the
        # balance is now positive again, restore it to 'active'.
        if lot_id is not None:
            cursor.execute("""
                SELECT balance FROM lot_balances WHERE lot_id = %s
            """, (lot_id,))
            balance_row = cursor.fetchone()
            if balance_row is not None and balance_row[0] > 0:
                cursor.execute("""
                    UPDATE lots
                    SET status = 'active', updated_at = CURRENT_TIMESTAMP
                    WHERE lot_id = %s AND status = 'depleted'
                """, (lot_id,))
                if cursor.rowcount > 0:
                    logger.info(
                        f"Lot lot_id={lot_id} restored from 'depleted' → 'active' "
                        f"(balance now {balance_row[0]})"
                    )

    if reversals_inserted > 0:
        logger.info(
            f"✅ Inserted {reversals_inserted} Cancel row(s) for order "
            f"{order_number} (ss_id={ss_id})"
        )
    else:
        logger.info(
            f"ℹ️  All Cancel rows already present for order {order_number} "
            f"(ss_id={ss_id}) — idempotent no-op"
        )

    return reversals_inserted

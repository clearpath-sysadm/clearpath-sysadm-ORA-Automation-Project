"""
Shared shipped_items UPSERT helper.

Provides a single place for the bare-SKU cleanup + UPSERT sequence that
both daily_shipment_processor.py and unified_shipstation_sync.py need
when writing to the shipped_items table.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_shipped_item(
    conn,
    ship_date,
    sku_lot: str,
    base_sku: str,
    quantity: int,
    order_number,
    tracking_number: str = None,
) -> None:
    """
    Write one shipped-item row to the database.

    Two-step sequence:
    1. If sku_lot is lot-stamped (contains ' - '), delete any stale bare-SKU
       row for the same (order_number, base_sku) so the lot-stamped row becomes
       the canonical record.
    2. UPSERT the row into shipped_items. When tracking_number is provided it
       is included in the INSERT and ON CONFLICT UPDATE; when None it is omitted
       (matching the behaviour of the unified_shipstation_sync path which does
       not carry tracking numbers through to this table).

    Args:
        conn:            Open database connection (psycopg2 / transaction context).
        ship_date:       Ship date (date object or 'YYYY-MM-DD' string).
        sku_lot:         Full sku_lot value — either bare SKU or 'SKU - Lot'.
        base_sku:        The base SKU portion (e.g. '17612').
        quantity:        Quantity shipped (positive integer).
        order_number:    Human-readable order number (string).
        tracking_number: Optional tracking number string.
    """
    cursor = conn.cursor()

    if ' - ' in str(sku_lot):
        cursor.execute(
            """
            DELETE FROM shipped_items
            WHERE order_number = %s
              AND base_sku = %s
              AND sku_lot NOT LIKE '%% - %%'
            """,
            (str(order_number), str(base_sku)),
        )
        if cursor.rowcount > 0:
            logger.debug(
                f"Deleted {cursor.rowcount} bare-SKU record(s) for "
                f"{order_number}/{base_sku}"
            )

    if tracking_number is not None:
        cursor.execute(
            """
            INSERT INTO shipped_items (
                ship_date, sku_lot, base_sku, quantity_shipped,
                order_number, tracking_number
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT(order_number, base_sku, sku_lot) DO UPDATE SET
                ship_date        = EXCLUDED.ship_date,
                quantity_shipped = EXCLUDED.quantity_shipped,
                tracking_number  = EXCLUDED.tracking_number
            """,
            (
                str(ship_date), sku_lot, str(base_sku), int(quantity),
                str(order_number) if order_number else None,
                tracking_number,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO shipped_items (
                ship_date, sku_lot, base_sku, quantity_shipped, order_number
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(order_number, base_sku, sku_lot) DO UPDATE SET
                ship_date        = EXCLUDED.ship_date,
                quantity_shipped = EXCLUDED.quantity_shipped
            """,
            (
                str(ship_date), sku_lot, str(base_sku), int(quantity),
                str(order_number) if order_number else None,
            ),
        )

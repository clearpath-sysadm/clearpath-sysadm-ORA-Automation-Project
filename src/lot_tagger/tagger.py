"""
Lot Tagger — shared tag_order_lots() function.

Called by both the webhook handler (Flask) and the reconciliation scheduler.
Callers must build active_lots and known_skus from the DB before calling this.
"""
import logging
from typing import Dict, Set

from src.services.shipstation.api_client import update_order_custom_fields
from src.utils.server_logger import get_logger

logger = logging.getLogger(__name__)
server_logger = get_logger()

ACTIVE_LOTS_QUERY = """
    SELECT DISTINCT ON (s.sku_code) s.sku_code, l.lot_id, l.lot_number
    FROM lots l
    JOIN skus s ON s.sku_id = l.sku_id
    JOIN lot_balances lb ON lb.lot_id = l.lot_id
    WHERE lb.balance > 0
      AND l.status NOT IN ('quarantine', 'inactive')
    ORDER BY s.sku_code, l.received_date ASC NULLS LAST, l.lot_id ASC
"""

KNOWN_SKUS_QUERY = "SELECT sku_code FROM skus"


def build_lot_maps(conn):
    """
    Build active_lots dict and known_skus set from the database.
    Uses FIFO (oldest received_date first) to resolve multiple active lots per SKU.

    Returns: (active_lots: dict[sku -> lot_number], known_skus: set[sku])
    """
    cursor = conn.cursor()

    cursor.execute(ACTIVE_LOTS_QUERY)
    active_lots = {row[0]: row[2] for row in cursor.fetchall()}

    cursor.execute(KNOWN_SKUS_QUERY)
    known_skus = {row[0] for row in cursor.fetchall()}

    return active_lots, known_skus


def tag_order_lots(order: dict, active_lots: Dict[str, str], known_skus: Set[str], conn) -> None:
    """
    Tag a single ShipStation order with the correct SKU - LOT in customField1.

    Logic:
    1. Filter order items to tracked SKUs (in known_skus). Skip silently if none.
    2. If multiple tracked SKUs present (auto-split should prevent), use first, log warning.
    3. If SKU has no active lot → write lot_tagging_failures record.
    4. Three-way customField1 check:
       - Already correct → skip (idempotent)
       - Empty → write expected value
       - Non-empty but wrong → preserve to customField2, write expected value
    5. On success → mark any existing lot_tagging_failures record resolved.
    """
    order_number = order.get('orderNumber', '').strip()
    order_id = order.get('orderId')
    items = order.get('items', [])

    # Filter to tracked SKUs only
    tracked_items = [item for item in items if str(item.get('sku', '')).strip() in known_skus]

    if not tracked_items:
        return

    if len(tracked_items) > 1:
        skus_found = [item.get('sku') for item in tracked_items]
        server_logger.warning(
            f"Order {order_number} (SS ID: {order_id}) has multiple tracked SKUs {skus_found}. "
            f"Auto-split should prevent this. Processing first SKU only.",
            source="Lot Tagger"
        )

    item = tracked_items[0]
    sku = str(item.get('sku', '')).strip()
    cursor = conn.cursor()

    # SKU tracked but no active lot → failure record
    if sku not in active_lots:
        cursor.execute("""
            INSERT INTO lot_tagging_failures (order_number, shipstation_order_id, sku, detected_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (shipstation_order_id) DO UPDATE
                SET detected_at = CURRENT_TIMESTAMP,
                    sku = EXCLUDED.sku
            WHERE lot_tagging_failures.resolved_at IS NULL
        """, (order_number, str(order_id), sku))
        conn.commit()
        server_logger.warning(
            f"No active lot for SKU {sku} on order {order_number} (SS ID: {order_id}). Logged to lot_tagging_failures.",
            source="Lot Tagger"
        )
        return

    expected_value = f"{sku} - {active_lots[sku]}"
    adv = (order.get('advancedOptions') or {})
    current_cf1 = adv.get('customField1', '') or ''
    current_cf1 = current_cf1.strip()

    # Already correctly tagged — skip
    if current_cf1 == expected_value:
        logger.debug(f"Order {order_number} already tagged with '{expected_value}' — skipping.")
        return

    # Determine whether to preserve existing value to customField2
    field2_value = current_cf1 if current_cf1 else None
    if field2_value:
        server_logger.warning(
            f"Order {order_number} (SS ID: {order_id}) customField1 pre-set to '{current_cf1}'. "
            f"Moving to customField2 and writing correct lot.",
            source="Lot Tagger"
        )

    # Write to ShipStation
    result = update_order_custom_fields(order_id, expected_value, field2_value)

    if not result.get('success'):
        server_logger.error(
            f"Failed to tag order {order_number} (SS ID: {order_id}): {result.get('error')}",
            source="Lot Tagger"
        )
        return

    server_logger.info(
        f"Tagged order {order_number} (SS ID: {order_id}) with '{expected_value}'",
        source="Lot Tagger"
    )

    # Resolve any existing failure record for this order
    cursor.execute("""
        UPDATE lot_tagging_failures
        SET resolved_at = CURRENT_TIMESTAMP,
            resolved_by = 'auto'
        WHERE shipstation_order_id = %s
          AND resolved_at IS NULL
    """, (str(order_id),))
    conn.commit()

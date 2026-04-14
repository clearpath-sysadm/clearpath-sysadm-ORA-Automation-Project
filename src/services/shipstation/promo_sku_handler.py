"""
Promotional SKU Order Replacement Handler

When a ShipStation order enters awaiting_shipment and contains a promotional
SKU (mapped in the sku_promotions table), this handler:

  1. Creates a replacement order with the base SKU (identical in all other fields)
  2. Verifies the replacement matches the original (only SKU may differ)
  3. Documents the original locally BEFORE any destructive action
  4. Cancels the original promo-SKU order in ShipStation
  5. Returns the replacement order so the caller (lot-tagger) processes it

All outcomes (replaced / failed / verify_failed / skipped) are written to
promo_sku_replacement_log for future dashboard reporting.
On failure, a row is also written to lot_tagging_failures so specialists see
it in the existing error dashboard.

Called from:
  - app.py webhook immediate loop
  - app.py webhook 24-hour sweep
  - src/scheduled_lot_tagger.py reconciliation loop
"""
import json
import logging
from datetime import datetime, timezone

from src.utils.server_logger import get_logger
from src.services.shipstation.api_client import (
    create_replacement_order,
    fetch_order_by_id,
    delete_order_from_shipstation,
)

logger = logging.getLogger(__name__)
server_logger = get_logger()

FIELDS_TO_COMPARE = ('shipTo', 'billTo', 'customerEmail', 'orderNumber',
                     'carrierCode', 'serviceCode', 'amountPaid', 'taxAmount')


def _load_promo_map(conn) -> dict:
    """Return {promo_sku: base_sku} for all active rows in sku_promotions."""
    cursor = conn.cursor()
    cursor.execute("SELECT promo_sku, base_sku FROM sku_promotions WHERE active = TRUE")
    return {row[0]: row[1] for row in cursor.fetchall()}


def _write_log(conn, order_number: str, promo_sku: str, base_sku: str,
               status: str, error_reason: str = None) -> None:
    """Insert a row into promo_sku_replacement_log."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO promo_sku_replacement_log
                (order_number, promo_sku, base_sku, status, error_reason, processed_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (order_number, promo_sku, base_sku, status, error_reason))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to write promo_sku_replacement_log: {e}")


def _write_tagging_failure(conn, order_number: str, shipstation_order_id: str,
                           promo_sku: str, reason: str) -> None:
    """Record the failure in lot_tagging_failures so it surfaces in the dashboard."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lot_tagging_failures
                (order_number, shipstation_order_id, sku, detected_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (shipstation_order_id) DO UPDATE
                SET detected_at = CURRENT_TIMESTAMP,
                    sku = EXCLUDED.sku
            WHERE lot_tagging_failures.resolved_at IS NULL
        """, (order_number, str(shipstation_order_id), f"{promo_sku} [PROMO: {reason}]"))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to write lot_tagging_failures: {e}")


def _already_processed(conn, original_order_id: int) -> bool:
    """Return True if this original SS order ID was already replaced."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM deleted_shipstation_orders
        WHERE shipstation_order_id = %s
          AND deleted_by = 'promo_sku_replacement'
        LIMIT 1
    """, (original_order_id,))
    return cursor.fetchone() is not None


def _record_deletion(conn, original_order: dict) -> None:
    """
    Write the original promo-SKU order to deleted_shipstation_orders BEFORE
    the DELETE API call so there is always a local record even if deletion fails.
    """
    ship_to  = original_order.get('shipTo') or {}
    bill_to  = original_order.get('billTo') or {}
    items    = original_order.get('items', [])
    items_json = json.dumps([
        {'sku': i.get('sku'), 'quantity': i.get('quantity'), 'name': i.get('name')}
        for i in items
    ])
    order_date_str = (original_order.get('orderDate') or '')[:10] or None
    total_cents = (
        int(float(original_order.get('orderTotal', 0)) * 100)
        if original_order.get('orderTotal') else None
    )
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO deleted_shipstation_orders (
            shipstation_order_id, order_number, deleted_at, deleted_by,
            customer_name, customer_email, customer_company,
            ship_to_name, ship_to_city, ship_to_state,
            order_total_cents, order_date, items_json
        ) VALUES (%s, %s, NOW(), 'promo_sku_replacement',
                  %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        original_order.get('orderId'),
        original_order.get('orderNumber'),
        bill_to.get('name') or ship_to.get('name'),
        original_order.get('customerEmail'),
        bill_to.get('company') or ship_to.get('company'),
        ship_to.get('name'),
        ship_to.get('city'),
        ship_to.get('state'),
        total_cents,
        order_date_str,
        items_json,
    ))
    conn.commit()


def _verify_replacement(original: dict, replacement: dict, base_sku: str) -> list:
    """
    Compare key fields between the original and replacement orders.
    Returns a list of mismatched field names (empty = all good).
    The only permitted difference is the SKU in line items.
    """
    mismatches = []

    for field in FIELDS_TO_COMPARE:
        if original.get(field) != replacement.get(field):
            mismatches.append(field)

    orig_items  = original.get('items', [])
    repl_items  = replacement.get('items', [])
    if len(orig_items) != len(repl_items):
        mismatches.append('items_count')
    else:
        for i, (oi, ri) in enumerate(zip(orig_items, repl_items)):
            if oi.get('quantity') != ri.get('quantity'):
                mismatches.append(f'items[{i}].quantity')
            if ri.get('sku') != base_sku:
                mismatches.append(f'items[{i}].sku_not_base')

    return mismatches


def handle_promo_sku_order(order: dict, conn) -> dict:
    """
    Main entry point. Inspect a single awaiting_shipment order for promo SKUs
    and execute the replacement workflow if applicable.

    Returns:
        The replacement order dict on success, or the original order dict if
        no replacement was needed or if any step failed.
    """
    order_number = (order.get('orderNumber') or '').strip()
    order_id     = order.get('orderId')
    items        = order.get('items', [])

    promo_map = _load_promo_map(conn)
    if not promo_map:
        return order

    detected_promo_sku = None
    detected_base_sku  = None
    for item in items:
        sku = str(item.get('sku') or '').strip()
        if sku in promo_map:
            detected_promo_sku = sku
            detected_base_sku  = promo_map[sku]
            break

    if not detected_promo_sku:
        return order

    server_logger.info(
        f"Promo SKU detected on order {order_number} "
        f"(SS ID: {order_id}): {detected_promo_sku} → {detected_base_sku}",
        source="Promo SKU Handler"
    )

    if _already_processed(conn, order_id):
        server_logger.info(
            f"Order {order_number} (SS ID: {order_id}) already replaced — skipping.",
            source="Promo SKU Handler"
        )
        _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                   'skipped', 'already processed (idempotency guard)')
        return order

    create_result = create_replacement_order(order, detected_base_sku)
    if not create_result.get('success'):
        error = create_result.get('error', 'unknown error')
        server_logger.error(
            f"Failed to create replacement for order {order_number} "
            f"(SS ID: {order_id}): {error}",
            source="Promo SKU Handler"
        )
        _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                   'failed', f"create failed: {error}")
        _write_tagging_failure(conn, order_number, order_id,
                               detected_promo_sku, f"create failed: {error}")
        return order

    new_order    = create_result['order']
    new_order_id = new_order.get('orderId')

    verify_result = fetch_order_by_id(new_order_id)
    if not verify_result.get('success'):
        error = verify_result.get('error', 'fetch failed')
        server_logger.error(
            f"Could not fetch replacement order {new_order_id} for verification "
            f"(original: {order_number}): {error}",
            source="Promo SKU Handler"
        )
        _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                   'verify_failed', f"fetch failed: {error}")
        _write_tagging_failure(conn, order_number, order_id,
                               detected_promo_sku, f"verify fetch failed: {error}")
        return order

    fetched_replacement = verify_result['order']
    mismatches = _verify_replacement(order, fetched_replacement, detected_base_sku)
    if mismatches:
        error = f"field mismatches: {mismatches}"
        server_logger.error(
            f"Replacement order {new_order_id} failed verification for "
            f"original {order_number}: {error}",
            source="Promo SKU Handler"
        )
        _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                   'verify_failed', error)
        _write_tagging_failure(conn, order_number, order_id,
                               detected_promo_sku, error)
        return order

    _record_deletion(conn, order)
    _write_log(conn, order_number, detected_promo_sku, detected_base_sku, 'replaced')

    delete_result = delete_order_from_shipstation(order_id, fetch_details_first=False)
    if not delete_result.get('success'):
        error = delete_result.get('error', 'delete failed')
        server_logger.error(
            f"Failed to cancel original promo order {order_number} "
            f"(SS ID: {order_id}) after successful replacement: {error}",
            source="Promo SKU Handler"
        )
    else:
        server_logger.info(
            f"Replaced promo order {order_number}: "
            f"{detected_promo_sku} → {detected_base_sku} "
            f"(old SS ID: {order_id}, new SS ID: {new_order_id})",
            source="Promo SKU Handler"
        )

    return fetched_replacement

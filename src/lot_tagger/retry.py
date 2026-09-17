"""Retry unresolved lot-tagging work after inventory becomes available."""

import logging

from src.lot_tagger.tagger import BACKORDER_CF1, build_lot_maps, tag_order_lots
from src.services.database.pg_utils import get_connection
from src.services.inventory.promo_sku_utils import load_promo_map, load_variant_map
from src.services.shipstation.api_client import fetch_order_by_id, get_shipstation_credentials
from src.utils.server_logger import get_logger

logger = logging.getLogger(__name__)
server_logger = get_logger()


def _order_sort_key(order: dict) -> tuple:
    """Keep partial-receipt allocation stable and oldest-first."""
    return (
        order.get('createDate') or order.get('orderDate') or '',
        str(order.get('orderId') or ''),
    )


def retry_unresolved_lot_tagging_failures(affected_sku: str | None = None) -> dict:
    """
    Re-run the existing tagger for unresolved, awaiting-shipment orders.

    This runs only after the inventory write transaction has committed. The
    tagger remains responsible for choosing/reserving lots and resolving its
    failure record, so duplicate triggers are safe.
    """
    summary = {
        'found': 0,
        'retried': 0,
        'retagged': 0,
        'still_backordered': 0,
        'skipped_not_awaiting_shipment': 0,
        'errors': 0,
    }
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if affected_sku:
            cursor.execute("""
                SELECT id, order_number, shipstation_order_id, sku
                FROM lot_tagging_failures
                WHERE resolved_at IS NULL
                  AND sku = %s
                ORDER BY detected_at ASC
            """, (affected_sku,))
        else:
            cursor.execute("""
                SELECT id, order_number, shipstation_order_id, sku
                FROM lot_tagging_failures
                WHERE resolved_at IS NULL
                ORDER BY detected_at ASC
            """)
        failures = cursor.fetchall()
        summary['found'] = len(failures)
        if not failures:
            return summary

        # A correction can resolve a negative balance without creating any
        # shippable inventory (for example, -4 + 4 = 0). Avoid credentials,
        # ShipStation calls, and map loading unless this SKU has an eligible
        # active lot with positive live balance.
        if affected_sku:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM lots l
                    JOIN skus s ON s.sku_id = l.sku_id
                    JOIN lot_balances lb ON lb.lot_id = l.lot_id
                    WHERE s.sku_code = %s
                      AND l.status = 'active'
                      AND l.archived_at IS NULL
                      AND lb.balance > 0
                )
            """, (affected_sku,))
            has_eligible_inventory = cursor.fetchone()[0]
            if not has_eligible_inventory:
                logger.info(
                    "Retry: unresolved backorder(s) found for SKU %s, "
                    "but no active lot has positive balance; skipping",
                    affected_sku,
                )
                return summary

        # Only load credentials after the cheap database checks above show
        # there is actual retry work to perform.
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            raise RuntimeError('Failed to get ShipStation credentials')

        orders = []
        for failure_id, order_number, shipstation_order_id, sku in failures:
            try:
                fetched = fetch_order_by_id(int(shipstation_order_id), api_key, api_secret)
                if not fetched.get('success'):
                    logger.warning(
                        "Retry: failed to fetch ShipStation order %s: %s",
                        shipstation_order_id, fetched.get('error'),
                    )
                    summary['errors'] += 1
                    continue
                orders.append((failure_id, order_number, shipstation_order_id, fetched['order']))
            except Exception as exc:
                logger.error(
                    "Retry error fetching order %s: %s", order_number, exc, exc_info=True
                )
                summary['errors'] += 1

        orders.sort(key=lambda entry: _order_sort_key(entry[3]))
        active_lots, known_skus, lot_statuses, lot_candidates = build_lot_maps(conn)
        promo_map = load_promo_map(conn)
        variant_map = load_variant_map(conn)

        for failure_id, order_number, shipstation_order_id, order in orders:
            if (order.get('orderStatus') or '').lower() != 'awaiting_shipment':
                summary['skipped_not_awaiting_shipment'] += 1
                continue
            try:
                tag_order_lots(
                    order, active_lots, known_skus, lot_statuses, conn, lot_candidates,
                    promo_map=promo_map, variant_map=variant_map,
                )
                summary['retried'] += 1
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT resolved_at
                    FROM lot_tagging_failures
                    WHERE id = %s
                """, (failure_id,))
                row = cursor.fetchone()
                if row and row[0] is not None:
                    summary['retagged'] += 1
                elif ((order.get('advancedOptions') or {}).get('customField1') or '').strip() == BACKORDER_CF1:
                    summary['still_backordered'] += 1
            except Exception as exc:
                logger.error(
                    "Retry error for order %s: %s", order_number, exc, exc_info=True
                )
                summary['errors'] += 1

        return summary
    finally:
        if conn is not None:
            conn.close()
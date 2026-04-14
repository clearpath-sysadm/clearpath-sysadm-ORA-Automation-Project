"""
Promotional SKU Order Replacement Handler

When a ShipStation order enters awaiting_shipment and contains a promotional
SKU (mapped in the sku_promotions table), this handler:

  1. Returns early (no log row) if no promo SKU is detected in the order
  2. Guards idempotency via deleted_shipstation_orders
  3. Acquires a PostgreSQL session-level advisory lock keyed on the SS order ID
     to prevent concurrent duplicate replacements across callers
  4. Creates a replacement order with the base SKU (all other fields identical)
  5. Fetches the replacement back from ShipStation and verifies every populated
     field matches the original — the ONLY permitted difference is the SKU
  6. On verify failure: deletes the orphaned replacement from ShipStation,
     logs 'verify_failed', writes a lot_tagging_failures alert, returns original
  7. Logs 'replaced', cancels the original promo-SKU order in ShipStation,
     records the deletion, and returns the replacement so the lot-tagger runs normally
  8. On delete failure: updates the log row to 'failed' (no deleted_orders row
     is written since deletion never succeeded) and alerts via lot_tagging_failures

Logging contract — exactly one canonical row per attempt in promo_sku_replacement_log.
Valid statuses (enforced by DB CHECK constraint):
  'replaced'     → written just before the delete call; left as-is if everything
                   succeeds; UPDATED (not a new row) to 'failed' if delete fails
  'failed'       → inserted directly on create failure; or updated from 'replaced'
                   if the ShipStation delete call fails
  'verify_failed'→ inserted directly when fetch or field verification fails;
                   the orphaned replacement is cleaned up from ShipStation first
  'skipped'      → inserted when the idempotency guard fires or the advisory lock
                   is busy (concurrent session already processing this order)

Called from:
  - app.py webhook immediate loop
  - app.py webhook 24-hour sweep
  - src/scheduled_lot_tagger.py reconciliation loop
"""
import json
import logging

from src.utils.server_logger import get_logger
from src.services.shipstation.api_client import (
    create_replacement_order,
    fetch_order_by_id,
    delete_order_from_shipstation,
)

logger = logging.getLogger(__name__)
server_logger = get_logger()

EXCLUDED_COMPARISON_KEYS = frozenset({
    'orderId', 'orderKey',
    'createDate', 'modifyDate',
})

EXCLUDED_ITEM_COMPARISON_KEYS = frozenset({
    'orderItemId',
    'createDate', 'modifyDate',
})


def _load_promo_map(conn) -> dict:
    """Return {promo_sku: base_sku} for all active rows in sku_promotions."""
    cursor = conn.cursor()
    cursor.execute("SELECT promo_sku, base_sku FROM sku_promotions WHERE active = TRUE")
    return {row[0]: row[1] for row in cursor.fetchall()}


def _write_log(conn, order_number: str, promo_sku: str, base_sku: str,
               status: str, error_reason: str = None) -> int | None:
    """
    Insert a row into promo_sku_replacement_log and return the new row id.
    Returns None on error (logged internally).
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO promo_sku_replacement_log
                (order_number, promo_sku, base_sku, status, error_reason, processed_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (order_number, promo_sku, base_sku, status, error_reason))
        row = cursor.fetchone()
        conn.commit()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to write promo_sku_replacement_log: {e}")
        return None


def _update_log_status(conn, log_id: int, status: str, error_reason: str = None) -> None:
    """Update the status (and optionally error_reason) of an existing log row."""
    if log_id is None:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE promo_sku_replacement_log
               SET status = %s, error_reason = %s
             WHERE id = %s
        """, (status, error_reason, log_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update promo_sku_replacement_log row {log_id}: {e}")


def _write_tagging_failure(conn, order_number: str, shipstation_order_id,
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


def _already_processed(conn, original_order_id) -> bool:
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
    ship_to = original_order.get('shipTo') or {}
    bill_to = original_order.get('billTo') or {}
    items   = original_order.get('items', [])
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
        ON CONFLICT (shipstation_order_id)
        DO UPDATE SET deleted_by = 'promo_sku_replacement', deleted_at = NOW()
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


def _is_empty(val) -> bool:
    """Return True if a field value is considered unpopulated."""
    return val is None or val == '' or val == [] or val == {}


def _values_match(orig_val, repl_val) -> bool:
    """
    Type-aware equality check that tolerates ShipStation API normalization.

    Two specific cases are handled beyond plain equality:

    1. Numeric string vs float — SS GET returns amounts as strings ("49.99")
       while createorder responses return them as floats (49.99).  Python's
       '49.99' != 49.99 is True, which would cause a false verify_failed on
       every real promo order.

    2. Dict subset — SS back-fills extra keys in dict fields (e.g. storeId,
       customField2) on the createorder round-trip.  We verify that every
       non-empty key present in the original exists with the same value in the
       replacement; extra keys added by SS are ignored.
    """
    if orig_val == repl_val:
        return True

    if isinstance(orig_val, str) and isinstance(repl_val, (int, float)):
        try:
            return float(orig_val) == float(repl_val)
        except (ValueError, TypeError):
            pass

    if isinstance(orig_val, (int, float)) and isinstance(repl_val, str):
        try:
            return float(orig_val) == float(repl_val)
        except (ValueError, TypeError):
            pass

    if isinstance(orig_val, dict) and isinstance(repl_val, dict):
        for k, v in orig_val.items():
            if _is_empty(v):
                continue
            if not _values_match(v, repl_val.get(k)):
                return False
        return True

    return False


def _verify_replacement(original: dict, replacement: dict,
                        promo_sku: str, base_sku: str) -> list:
    """
    Compare ALL populated top-level fields from the original order against the
    replacement order.

    SKU rule per line item:
      - If original item SKU == promo_sku → replacement must have base_sku
      - Otherwise → replacement must preserve the original SKU unchanged

    Returns a list of mismatch descriptions (empty list means verification passed).
    orderId, orderKey, createDate, and modifyDate are excluded — they differ by design.

    Uses _values_match() rather than plain equality to tolerate:
      - Numeric type normalization (string "49.99" vs float 49.99)
      - Dict field back-filling by ShipStation (advancedOptions gets extra keys)
    """
    mismatches = []

    for key, orig_val in original.items():
        if key in EXCLUDED_COMPARISON_KEYS or key == 'items':
            continue
        if _is_empty(orig_val):
            continue
        repl_val = replacement.get(key)
        if not _values_match(orig_val, repl_val):
            safe_orig = repr(orig_val)[:120]
            safe_repl = repr(repl_val)[:120]
            mismatches.append(f"{key}: {safe_orig} != {safe_repl}")

    orig_items = original.get('items', [])
    repl_items = replacement.get('items', [])
    if len(orig_items) != len(repl_items):
        mismatches.append(f"items_count: {len(orig_items)} != {len(repl_items)}")
    else:
        for i, (oi, ri) in enumerate(zip(orig_items, repl_items)):
            for item_key, orig_item_val in oi.items():
                if item_key in EXCLUDED_ITEM_COMPARISON_KEYS:
                    continue
                if _is_empty(orig_item_val):
                    continue
                if item_key == 'sku':
                    orig_item_sku = str(orig_item_val).strip()
                    expected_sku  = base_sku if orig_item_sku == promo_sku else orig_item_sku
                    if ri.get('sku') != expected_sku:
                        mismatches.append(
                            f"items[{i}].sku: expected {expected_sku!r}, "
                            f"got {ri.get('sku')!r}"
                        )
                    continue
                repl_item_val = ri.get(item_key)
                if not _values_match(orig_item_val, repl_item_val):
                    mismatches.append(
                        f"items[{i}].{item_key}: {orig_item_val!r} != {repl_item_val!r}"
                    )

    return mismatches


def handle_promo_sku_order(order: dict, conn, headers=None) -> dict:
    """
    Main entry point. Inspect a single awaiting_shipment order for promo SKUs
    and execute the replacement workflow if applicable.

    Args:
        order:   ShipStation order dict (awaiting_shipment status expected)
        conn:    Active DB connection
        headers: ShipStation auth headers (optional; internal API calls fetch
                 credentials independently if not provided)

    Returns:
        The replacement order dict on success, or the original order dict if
        no replacement was needed or if any step failed.

    Concurrency:
        A PostgreSQL session-level advisory lock keyed on the ShipStation order
        ID is acquired as soon as a promo SKU is detected.  If another session
        already holds the lock the call returns immediately (logs 'skipped').
        The lock is released in the finally block regardless of outcome.
    """
    order_number       = (order.get('orderNumber') or '').strip()
    order_id           = order.get('orderId')
    items              = order.get('items', [])
    lock_acquired      = False
    detected_promo_sku = None
    detected_base_sku  = None

    try:
        promo_map = _load_promo_map(conn)
        if not promo_map:
            return order

        for item in items:
            sku = str(item.get('sku') or '').strip()
            if sku in promo_map:
                detected_promo_sku = sku
                detected_base_sku  = promo_map[sku]
                break

        if not detected_promo_sku:
            item_skus = [str(item.get('sku') or '').strip() for item in items]
            server_logger.debug(
                f"No promo SKU on order {order_number} (SS ID: {order_id}) — "
                f"item SKUs scanned: {item_skus}",
                source="Promo SKU Handler"
            )
            return order

        server_logger.info(
            f"Promo SKU detected on order {order_number} "
            f"(SS ID: {order_id}): {detected_promo_sku} → {detected_base_sku}",
            source="Promo SKU Handler"
        )

        if order_id is not None:
            cursor = conn.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (int(order_id),))
            lock_acquired = cursor.fetchone()[0]
            if not lock_acquired:
                server_logger.info(
                    f"Advisory lock busy for order {order_number} (SS ID: {order_id}) "
                    f"— concurrent processing in progress, skipping.",
                    source="Promo SKU Handler"
                )
                _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                           'skipped', 'concurrent processing (advisory lock busy)')
                return order

        if _already_processed(conn, order_id):
            server_logger.info(
                f"Order {order_number} (SS ID: {order_id}) already replaced — skipping.",
                source="Promo SKU Handler"
            )
            _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                       'skipped', 'already processed (idempotency guard)')
            return order

        create_result = create_replacement_order(order, detected_promo_sku, detected_base_sku)
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
            if new_order_id is not None:
                cleanup = delete_order_from_shipstation(new_order_id, fetch_details_first=False)
                if not cleanup.get('success'):
                    logger.warning(
                        f"Could not clean up orphaned replacement {new_order_id} "
                        f"after fetch failure for {order_number}: "
                        f"{cleanup.get('error', 'unknown')}"
                    )
            _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                       'verify_failed', f"fetch failed: {error}")
            _write_tagging_failure(conn, order_number, order_id,
                                   detected_promo_sku, f"verify fetch failed: {error}")
            return order

        fetched_replacement = verify_result['order']
        mismatches = _verify_replacement(order, fetched_replacement,
                                         detected_promo_sku, detected_base_sku)
        if mismatches:
            top_mismatches = mismatches[:5]
            error = f"field mismatches: {top_mismatches}"
            server_logger.error(
                f"Replacement order {new_order_id} failed verification for "
                f"original {order_number}: {error}",
                source="Promo SKU Handler"
            )
            if new_order_id is not None:
                cleanup = delete_order_from_shipstation(new_order_id, fetch_details_first=False)
                if not cleanup.get('success'):
                    logger.warning(
                        f"Could not clean up orphaned replacement {new_order_id} "
                        f"after verify failure for {order_number}: "
                        f"{cleanup.get('error', 'unknown')}"
                    )
            _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                       'verify_failed', error)
            _write_tagging_failure(conn, order_number, order_id,
                                   detected_promo_sku, error)
            return order

        log_id = _write_log(conn, order_number, detected_promo_sku, detected_base_sku,
                            'replaced')

        delete_result = delete_order_from_shipstation(order_id, fetch_details_first=False)
        if not delete_result.get('success'):
            error = delete_result.get('error', 'delete failed')
            server_logger.error(
                f"Failed to cancel original promo order {order_number} "
                f"(SS ID: {order_id}) after successful replacement: {error}",
                source="Promo SKU Handler"
            )
            _update_log_status(conn, log_id, 'failed',
                               f"cancel original failed: {error}")
            _write_tagging_failure(conn, order_number, order_id,
                                   detected_promo_sku, f"cancel original failed: {error}")
            return order

        try:
            _record_deletion(conn, order)
        except Exception as rec_err:
            logger.error(
                f"Failed to record deletion for {order_number} (SS ID: {order_id}) "
                f"after successful delete — idempotency guard will be missing: {rec_err}"
            )
            _update_log_status(conn, log_id, 'failed',
                               f"record_deletion failed after successful delete: {rec_err}")
            _write_tagging_failure(conn, order_number, order_id,
                                   detected_promo_sku,
                                   f"record_deletion failed: {rec_err}")
            return order

        server_logger.info(
            f"Replaced promo order {order_number}: "
            f"{detected_promo_sku} → {detected_base_sku} "
            f"(old SS ID: {order_id}, new SS ID: {new_order_id})",
            source="Promo SKU Handler"
        )
        return fetched_replacement

    except Exception as exc:
        logger.error(
            f"Unhandled exception in handle_promo_sku_order for {order_number} "
            f"(SS ID: {order_id}): {exc}",
            exc_info=True
        )
        try:
            promo_sku_for_log = detected_promo_sku or 'unknown'
            base_sku_for_log  = detected_base_sku  or 'unknown'
            _write_log(conn, order_number, promo_sku_for_log, base_sku_for_log,
                       'failed', f"unhandled exception: {exc}")
            _write_tagging_failure(conn, order_number, order_id,
                                   promo_sku_for_log, f"unhandled exception: {exc}")
        except Exception as log_err:
            logger.error(
                f"Could not write failure logs for {order_number}: {log_err}"
            )
        return order

    finally:
        if lock_acquired and order_id is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT pg_advisory_unlock(%s)", (int(order_id),))
                cursor.fetchone()
            except Exception as unlock_err:
                logger.warning(
                    f"Failed to release advisory lock for order {order_id}: {unlock_err}"
                )

"""
Lot staging reservation service.

Fixes the 2026-07-06 depleted-lot-reactivation incident: the tagger used to
pick "the current active lot" from an in-memory snapshot with no persisted
record of what was promised to which order. A 1-unit repack could flip a
depleted lot back to 'active' and the tagger would then stamp that lot onto
every order in the batch, even though the lot only had 1 unit of headroom.

This module makes tagging balance-aware and persists the promise:

    available(lot) = lot_balances.balance - SUM(reserved_qty of OPEN
                      reservations against that lot)

A reservation is created at tag time (CF1 write) and is later either:
    - consumed  — the unit actually shipped; deduct_lot_inventory() converts
                  the reservation into the real inventory_transactions row.
    - released  — the order was retagged (qty changed / lot changed),
                  cancelled, or the CF1 write to ShipStation failed.

Concurrency: reservation creation takes a Postgres advisory lock keyed on the
SKU so two concurrent tagger runs (webhook + reconciliation sweep) can't both
reserve against the same lot's last remaining units.
"""

import hashlib
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def _sku_lock_key(sku: str) -> int:
    """
    Deterministic 32-bit-ish lock key derived from the SKU string.

    Task #136: must NOT use Python's built-in hash() — it is salted with a
    random seed (PYTHONHASHSEED) that differs per process, so the webhook
    process and the scheduler process would compute different lock keys for
    the same SKU and the advisory lock would silently fail to serialize
    them. Use a stable hash (sha256) instead so every process agrees on the
    same key for the same SKU.
    """
    digest = hashlib.sha256(f'lot_reservation:{sku}'.encode('utf-8')).digest()
    return int.from_bytes(digest[:4], 'big') & 0x7FFFFFFF


def get_open_reserved_qty(conn, lot_id: int) -> int:
    """Sum of reserved_qty for OPEN ('reserved') reservations against a lot."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(reserved_qty), 0)
        FROM lot_staging_reservations
        WHERE lot_id = %s AND state = 'reserved'
    """, (lot_id,))
    return cursor.fetchone()[0]


def get_available_balance(conn, lot_id: int) -> int:
    """Real lot balance minus units already promised to other open orders."""
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM lot_balances WHERE lot_id = %s", (lot_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0
    return balance - get_open_reserved_qty(conn, lot_id)


def get_reservation(conn, shipstation_order_id: str, sku: str) -> Optional[dict]:
    """Return the current OPEN reservation for (order, sku), or None."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, lot_id, lot_number, reserved_qty, state
        FROM lot_staging_reservations
        WHERE shipstation_order_id = %s AND sku = %s AND state = 'reserved'
        LIMIT 1
    """, (str(shipstation_order_id), sku))
    row = cursor.fetchone()
    if not row:
        return None
    return {
        'id': row[0], 'lot_id': row[1], 'lot_number': row[2],
        'reserved_qty': row[3], 'state': row[4],
    }


def release_reservation(conn, shipstation_order_id: str, sku: str, reason: str) -> bool:
    """
    Release the OPEN reservation for (order, sku), if any.

    Used when: order is retagged with a different lot/qty, order is
    cancelled, or the ShipStation CF1 write failed after a reservation was
    tentatively created (so we don't hold inventory hostage for a stamp that
    never landed).

    Returns True if a reservation was released, False if none existed.
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE lot_staging_reservations
        SET state = 'released',
            release_reason = %s,
            released_at = NOW(),
            updated_at = NOW()
        WHERE shipstation_order_id = %s AND sku = %s AND state = 'reserved'
        RETURNING id
    """, (reason, str(shipstation_order_id), sku))
    released = cursor.fetchall()
    if released:
        logger.info(
            f"Released {len(released)} reservation(s) for order {shipstation_order_id} "
            f"/ sku {sku}: {reason}"
        )
        return True
    return False


def reserve_lot_for_order(
    conn,
    order_number: str,
    shipstation_order_id: str,
    sku: str,
    needed_qty: int,
    candidate_lots: List[Tuple[int, str, int]],
    source: str = 'tagger',
) -> Optional[dict]:
    """
    Reserve `needed_qty` units of `sku` for this order against the first
    candidate lot (in caller-supplied order — must already be sorted by
    lot_number, i.e. FIFO by lot identity, NOT by internal DB id) that has
    enough *available* balance (real balance minus other open reservations).

    Any existing OPEN reservation for this (order, sku) is released first —
    retagging always starts from a clean slate so a qty-change or lot swap
    never double-reserves.

    Args:
        candidate_lots: list of (lot_id, lot_number, balance) tuples for this
                         SKU, already restricted to truly 'active' status
                         (never 'depleted', 'inactive', or 'quarantine') and
                         sorted by lot_number ascending.

    Returns:
        {'lot_id', 'lot_number', 'reserved_qty'} on success, or None if no
        candidate lot has enough available balance for needed_qty.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_sku_lock_key(sku),))

    release_reservation(conn, shipstation_order_id, sku, reason=f'retag ({source})')

    for lot_id, lot_number, _snapshot_balance in candidate_lots:
        available = get_available_balance(conn, lot_id)
        if available >= needed_qty:
            cursor.execute("""
                INSERT INTO lot_staging_reservations
                    (shipstation_order_id, order_number, sku, lot_id, lot_number,
                     reserved_qty, state, reservation_source)
                VALUES (%s, %s, %s, %s, %s, %s, 'reserved', %s)
                RETURNING id
            """, (str(shipstation_order_id), order_number, sku, lot_id, lot_number,
                  needed_qty, source))
            cursor.fetchone()
            logger.info(
                f"Reserved {needed_qty} unit(s) of lot '{lot_number}' (lot_id={lot_id}) "
                f"for order {order_number} / sku {sku} (available was {available})"
            )
            return {'lot_id': lot_id, 'lot_number': lot_number, 'reserved_qty': needed_qty}
        else:
            logger.debug(
                f"Lot '{lot_number}' (lot_id={lot_id}) has only {available} available "
                f"— insufficient for {needed_qty} units of order {order_number}"
            )

    logger.warning(
        f"No candidate lot for sku {sku} has enough available balance "
        f"({needed_qty} needed) — order {order_number} could not be reserved."
    )
    return None


def consume_reservation(conn, shipstation_order_id: str, sku: str) -> Optional[dict]:
    """
    Mark the OPEN reservation for (order, sku) as consumed and return its
    lot_id/lot_number/reserved_qty. Called by deduct_lot_inventory() at ship
    time so the actual inventory deduction uses the exact lot that was
    reserved at tagging time — never an independently re-picked lot.

    Returns None if no open reservation exists (e.g. order was tagged before
    this migration existed) — caller must fall back to CF1-parsing.
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE lot_staging_reservations
        SET state = 'consumed', consumed_at = NOW(), updated_at = NOW()
        WHERE shipstation_order_id = %s AND sku = %s AND state = 'reserved'
        RETURNING id, lot_id, lot_number, reserved_qty
    """, (str(shipstation_order_id), sku))
    row = cursor.fetchone()
    if not row:
        return None
    logger.info(
        f"Consumed reservation id={row[0]} (lot_id={row[1]}, lot='{row[2]}', "
        f"qty={row[3]}) for order {shipstation_order_id} / sku {sku}"
    )
    return {'id': row[0], 'lot_id': row[1], 'lot_number': row[2], 'reserved_qty': row[3]}


def release_stale_reservations(conn, current_order_ids: set, max_age_hours: int = 24) -> int:
    """
    Task #136: clean up reservations that were never consumed or explicitly
    released.

    A reservation is created (committed) at tag time BEFORE the ShipStation
    CF1 write is confirmed successful (tagger.py reserves, then writes, then
    releases on write failure) — a crash or process kill between those two
    steps, or any other path that lets an order silently leave
    awaiting_shipment without a clean consume/release, would otherwise leave
    the reservation open forever, permanently reducing that lot's available
    balance for no real unit of inventory.

    Called from the reconciliation sweep (which already fetches the full,
    current awaiting_shipment order list), so it can piggyback on that data
    instead of making extra ShipStation API calls.

    Releases any OPEN ('reserved') reservation if either:
      - its shipstation_order_id is no longer in `current_order_ids` (the
        order has left awaiting_shipment — shipped, cancelled elsewhere,
        etc. — without going through the normal consume/release path), OR
      - it has been open longer than `max_age_hours` regardless of order
        status (defensive backstop against any other stranding path).

    Returns the number of reservations released.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, shipstation_order_id, sku, lot_id, lot_number, reserved_qty, created_at
        FROM lot_staging_reservations
        WHERE state = 'reserved'
    """)
    open_reservations = cursor.fetchall()
    now = _utcnow(cursor)

    released = 0
    for res_id, ss_order_id, sku, lot_id, lot_number, reserved_qty, created_at in open_reservations:
        is_orphaned = str(ss_order_id) not in current_order_ids
        is_too_old = False
        if created_at is not None:
            age_hours = (now - created_at).total_seconds() / 3600
            is_too_old = age_hours > max_age_hours

        if not (is_orphaned or is_too_old):
            continue

        reason = (
            f"stale reservation cleanup: order no longer awaiting_shipment"
            if is_orphaned else
            f"stale reservation cleanup: open longer than {max_age_hours}h"
        )
        cursor.execute("""
            UPDATE lot_staging_reservations
            SET state = 'released', release_reason = %s, released_at = NOW(), updated_at = NOW()
            WHERE id = %s AND state = 'reserved'
        """, (reason, res_id))
        if cursor.rowcount:
            released += 1
            logger.warning(
                f"Released stranded reservation id={res_id} (order={ss_order_id}, sku={sku}, "
                f"lot='{lot_number}', qty={reserved_qty}): {reason}"
            )

    if released:
        logger.warning(f"Stale reservation cleanup released {released} stranded reservation(s).")
    return released


def _utcnow(cursor):
    """Fetch DB-side current UTC time so age comparisons use the same clock as created_at."""
    cursor.execute("SELECT NOW()")
    return cursor.fetchone()[0]


def record_negative_balance_alert(conn, lot_id: int, sku: str, lot_number: str,
                                   balance: int, context: str = '') -> None:
    """
    Insert a lot_balance_alerts row when a lot's computed balance goes
    negative. Idempotent-ish: only inserts if there isn't already an
    unresolved alert for this exact lot_id.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM lot_balance_alerts
        WHERE lot_id = %s AND resolved_at IS NULL
        LIMIT 1
    """, (lot_id,))
    if cursor.fetchone():
        return
    cursor.execute("""
        INSERT INTO lot_balance_alerts
            (lot_id, sku, lot_number, balance, alert_type, context)
        VALUES (%s, %s, %s, %s, 'negative_balance', %s)
    """, (lot_id, sku, lot_number, balance, context))
    logger.error(
        f"NEGATIVE LOT BALANCE ALERT: lot '{lot_number}' (sku={sku}, lot_id={lot_id}) "
        f"balance={balance}. {context}"
    )

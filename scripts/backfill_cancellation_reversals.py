#!/usr/bin/env python3
"""
Backfill Cancellation Inventory Reversals

Finds all 'cancelled' orders in orders_inbox that have 'Ship' transactions in
inventory_transactions but no corresponding 'Cancel' transaction, then inserts
the missing reversal rows.

This fixes orders that were shipped and had inventory deducted, then later
cancelled in ShipStation before the automatic reversal logic was deployed.

Usage:
    python3 scripts/backfill_cancellation_reversals.py [--dry-run] [--order-number ORDER]

Examples:
    # Dry run for a specific order (prints what would be reversed, writes nothing)
    python3 scripts/backfill_cancellation_reversals.py --dry-run --order-number 863804

    # Apply reversal for a specific order
    python3 scripts/backfill_cancellation_reversals.py --order-number 863804

    # Dry run across ALL qualifying cancelled orders
    python3 scripts/backfill_cancellation_reversals.py --dry-run

    # Apply reversals for all qualifying cancelled orders
    python3 scripts/backfill_cancellation_reversals.py

Safe to run multiple times — the idempotency guard inside reverse_lot_inventory
prevents duplicate 'Cancel' rows.
"""

import sys
import os
import logging
import argparse
import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import setup_logging
from src.services.database import execute_query, transaction_with_retry
from src.services.inventory.lot_cancellation import reverse_lot_inventory

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'backfill_cancellation_reversals.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def find_orders_needing_reversal(order_number_filter=None):
    """
    Return cancelled orders that have Ship transactions but no Cancel transaction.

    A 'Ship' transaction exists but no 'Cancel' transaction means the inventory
    was deducted when the order shipped but was never restored after cancellation.

    Returns list of (order_number, shipstation_order_id) tuples.
    """
    base_query = """
        SELECT DISTINCT oi.order_number, oi.shipstation_order_id
        FROM orders_inbox oi
        WHERE oi.status = 'cancelled'
          AND oi.shipstation_order_id IS NOT NULL
          AND oi.shipstation_order_id != ''
          AND EXISTS (
              SELECT 1
              FROM inventory_transactions it
              WHERE it.shipstation_order_id = oi.shipstation_order_id
                AND it.transaction_type = 'Ship'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM inventory_transactions it
              WHERE it.shipstation_order_id = oi.shipstation_order_id
                AND it.transaction_type = 'Cancel'
          )
    """

    if order_number_filter:
        query = base_query + " AND oi.order_number = %s ORDER BY oi.order_number"
        rows = execute_query(query, [order_number_filter])
    else:
        query = base_query + " ORDER BY oi.order_number"
        rows = execute_query(query)

    return [(row[0], row[1]) for row in rows]


def dry_run_report(order_number, shipstation_order_id):
    """
    Print what reverse_lot_inventory would do for a given order without writing.
    """
    rows = execute_query("""
        SELECT lot_id, sku, quantity
        FROM inventory_transactions
        WHERE shipstation_order_id = %s
          AND transaction_type = 'Ship'
        ORDER BY id
    """, [str(shipstation_order_id)])

    if not rows:
        logger.info(f"  [DRY RUN] No Ship rows found for order {order_number} (ss_id={shipstation_order_id})")
        return 0

    count = 0
    for lot_id, sku, quantity in rows:
        # Check if Cancel already exists
        if lot_id is not None:
            existing = execute_query("""
                SELECT id FROM inventory_transactions
                WHERE lot_id = %s AND shipstation_order_id = %s AND transaction_type = 'Cancel'
                LIMIT 1
            """, [lot_id, str(shipstation_order_id)])
        else:
            existing = execute_query("""
                SELECT id FROM inventory_transactions
                WHERE lot_id IS NULL AND sku = %s AND shipstation_order_id = %s AND transaction_type = 'Cancel'
                LIMIT 1
            """, [sku, str(shipstation_order_id)])

        if existing:
            logger.info(f"  [DRY RUN] SKIP (already reversed): lot_id={lot_id}, sku={sku}, qty={quantity}")
        else:
            logger.info(f"  [DRY RUN] WOULD REVERSE: lot_id={lot_id}, sku={sku}, qty={quantity} units → Cancel row on {datetime.date.today()}")
            count += 1

    return count


def run_backfill(dry_run=False, order_number_filter=None):
    logger.info("=" * 70)
    logger.info("CANCELLATION REVERSAL BACKFILL STARTED")
    if dry_run:
        logger.info("*** DRY RUN — no database writes will occur ***")
    if order_number_filter:
        logger.info(f"*** Targeting order {order_number_filter} only ***")
    logger.info("=" * 70)

    orders = find_orders_needing_reversal(order_number_filter=order_number_filter)

    if not orders:
        logger.info("✅ Nothing to backfill — no cancelled orders with unreversed Ship transactions found.")
        if order_number_filter:
            logger.info(
                f"   Order {order_number_filter} either: has no Ship transactions, "
                f"already has Cancel rows, is not in 'cancelled' status, "
                f"or has no shipstation_order_id."
            )
        return

    logger.info(f"Found {len(orders)} order(s) needing reversal:")
    for order_number, ss_id in orders:
        logger.info(f"  - {order_number} (ss_id={ss_id})")

    stats = {
        'orders_processed': 0,
        'reversals_inserted': 0,
        'orders_skipped': 0,
        'errors': 0,
    }

    cancel_date = datetime.date.today()

    for order_number, shipstation_order_id in orders:
        logger.info(f"\nProcessing order {order_number} (ss_id={shipstation_order_id})")

        if dry_run:
            count = dry_run_report(order_number, shipstation_order_id)
            if count > 0:
                stats['reversals_inserted'] += count
                stats['orders_processed'] += 1
            else:
                stats['orders_skipped'] += 1
            continue

        try:
            with transaction_with_retry() as conn:
                inserted = reverse_lot_inventory(
                    order_number=order_number,
                    shipstation_order_id=str(shipstation_order_id),
                    cancel_date=cancel_date,
                    conn=conn,
                )
            if inserted > 0:
                stats['reversals_inserted'] += inserted
                stats['orders_processed'] += 1
                logger.info(f"  ✓ Inserted {inserted} Cancel row(s) for order {order_number}")
            else:
                stats['orders_skipped'] += 1
                logger.info(f"  → Skipped (all Cancel rows already present)")
        except Exception as e:
            logger.error(f"  ✗ Error processing order {order_number}: {e}", exc_info=True)
            stats['errors'] += 1

    logger.info("\n" + "=" * 70)
    logger.info("BACKFILL COMPLETE")
    if dry_run:
        logger.info("*** DRY RUN — no changes were written ***")
    logger.info(f"  Orders processed:       {stats['orders_processed']}")
    logger.info(f"  Reversals inserted:     {stats['reversals_inserted']}")
    logger.info(f"  Orders skipped:         {stats['orders_skipped']}")
    logger.info(f"  Errors:                 {stats['errors']}")
    logger.info("=" * 70)

    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Backfill missing inventory cancellation reversals for cancelled orders.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be reversed without writing anything to the database.',
    )
    parser.add_argument(
        '--order-number',
        type=str,
        default=None,
        help='Target a single order by order number (e.g. --order-number 863804).',
    )
    args = parser.parse_args()

    run_backfill(dry_run=args.dry_run, order_number_filter=args.order_number)

#!/usr/bin/env python3
"""
Inventory Deduction Backfill Script

Finds all shipped orders that have no corresponding 'Ship' transaction in
inventory_transactions, fetches each order from ShipStation to retrieve the
lot stamp (customField1), then calls deduct_lot_inventory to record the
missing deductions.

Safe to run multiple times — the idempotency guard inside deduct_lot_inventory
(keyed on lot_id + shipstation_order_id + 'Ship') prevents double-deductions.

Usage:
    python3 src/backfill_inventory_deductions.py [--dry-run] [--limit N]
"""

import sys
import os
import logging
import argparse
import time
import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import setup_logging
from src.services.database import execute_query, transaction_with_retry
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    fetch_order_by_id,
)
from src.services.inventory.lot_deduction import deduct_lot_inventory

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'backfill_inventory_deductions.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)

KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']


def find_orders_needing_deduction(limit=None):
    """
    Return shipped orders that have a shipstation_order_id but no 'Ship'
    transaction recorded in inventory_transactions for any key SKU item.

    Returns list of (order_number, shipstation_order_id) tuples.
    """
    query = """
        SELECT DISTINCT oi.order_number, oi.shipstation_order_id
        FROM orders_inbox oi
        JOIN order_items_inbox oii ON oii.order_inbox_id = oi.id
        WHERE oi.status = 'shipped'
          AND oi.shipstation_order_id IS NOT NULL
          AND oi.shipstation_order_id != ''
          AND oii.sku = ANY(%s)
          AND NOT EXISTS (
              SELECT 1
              FROM inventory_transactions it
              WHERE it.shipstation_order_id = oi.shipstation_order_id
                AND it.transaction_type = 'Ship'
          )
        ORDER BY oi.order_number
    """
    args = [KEY_PRODUCT_SKUS]
    if limit:
        query += f" LIMIT {limit}"

    rows = execute_query(query, args)
    return [(row[0], row[1]) for row in rows]


def backfill_deductions(dry_run=False, limit=None, api_delay=0.4):
    """
    Main backfill function.

    Args:
        dry_run:   If True, fetch and log what would be deducted but write nothing.
        limit:     Maximum number of orders to process (None = all).
        api_delay: Seconds to sleep between ShipStation API calls.
    """
    logger.info("=" * 70)
    logger.info("INVENTORY DEDUCTION BACKFILL STARTED")
    if dry_run:
        logger.info("*** DRY RUN — no database writes will occur ***")
    logger.info("=" * 70)

    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("ShipStation credentials not found — aborting")
        return

    orders = find_orders_needing_deduction(limit=limit)
    logger.info(f"Found {len(orders)} shipped order(s) with no inventory deduction")

    if not orders:
        logger.info("Nothing to backfill — all shipped orders are already deducted")
        return

    stats = {
        'orders_processed': 0,
        'deductions_recorded': 0,
        'skipped_no_lot_stamp': 0,
        'skipped_no_key_sku': 0,
        'skipped_already_deducted': 0,
        'api_errors': 0,
        'errors': 0,
    }

    for order_number, shipstation_order_id in orders:
        logger.info(f"Processing order {order_number} (SS ID: {shipstation_order_id})")

        result = fetch_order_by_id(int(shipstation_order_id), api_key, api_secret)
        time.sleep(api_delay)

        if not result.get('success'):
            logger.warning(
                f"  ⚠ Could not fetch order {order_number} from ShipStation: "
                f"{result.get('error', 'unknown error')}"
            )
            stats['api_errors'] += 1
            continue

        ss_order = result['order']
        adv = ss_order.get('advancedOptions') or {}
        lot_stamp = (adv.get('customField1') or '').strip()

        if not lot_stamp:
            logger.info(f"  → Skipped: no customField1 (lot stamp) in ShipStation")
            stats['skipped_no_lot_stamp'] += 1
            continue

        items = ss_order.get('items', [])
        ship_date_str = ss_order.get('shipDate', '')
        try:
            ship_date = datetime.datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
        except Exception:
            ship_date = datetime.date.today()
            logger.warning(f"  ⚠ Could not parse shipDate '{ship_date_str}' — using today")

        order_deductions = 0

        try:
            with transaction_with_retry() as conn:
                for item in items:
                    sku_raw = str(item.get('sku', '')).strip()
                    quantity = item.get('quantity', 0)

                    if not sku_raw or quantity <= 0:
                        continue

                    base_sku = sku_raw.split(' - ')[0].strip() if ' - ' in sku_raw else sku_raw

                    if base_sku not in KEY_PRODUCT_SKUS:
                        continue

                    if dry_run:
                        logger.info(
                            f"  [DRY RUN] Would deduct {quantity} × {base_sku} "
                            f"from lot stamp '{lot_stamp}' (ship_date: {ship_date})"
                        )
                        order_deductions += 1
                    else:
                        recorded = deduct_lot_inventory(
                            order_number=order_number,
                            shipstation_order_id=str(shipstation_order_id),
                            base_sku=base_sku,
                            customField1_value=lot_stamp,
                            ship_date=ship_date,
                            quantity=quantity,
                            conn=conn,
                        )
                        if recorded:
                            logger.info(
                                f"  ✓ Deducted {quantity} × {base_sku} "
                                f"from lot stamp '{lot_stamp}'"
                            )
                            order_deductions += 1
                        else:
                            logger.debug(
                                f"  → Skipped deduction for {base_sku} "
                                f"(already recorded or lot not found)"
                            )
                            stats['skipped_already_deducted'] += 1

        except Exception as e:
            logger.error(f"  ✗ Error processing order {order_number}: {e}", exc_info=True)
            stats['errors'] += 1
            continue

        if order_deductions == 0:
            stats['skipped_no_key_sku'] += 1
        else:
            stats['deductions_recorded'] += order_deductions

        stats['orders_processed'] += 1

    logger.info("=" * 70)
    logger.info("BACKFILL COMPLETE")
    logger.info(f"  Orders processed:           {stats['orders_processed']}")
    logger.info(f"  Deductions recorded:        {stats['deductions_recorded']}")
    logger.info(f"  Skipped (no lot stamp):     {stats['skipped_no_lot_stamp']}")
    logger.info(f"  Skipped (no key SKU):       {stats['skipped_no_key_sku']}")
    logger.info(f"  Skipped (already deducted): {stats['skipped_already_deducted']}")
    logger.info(f"  ShipStation API errors:     {stats['api_errors']}")
    logger.info(f"  Processing errors:          {stats['errors']}")
    logger.info("=" * 70)

    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill missing inventory deductions')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and log what would be deducted without writing to the database',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of orders to process (default: all)',
    )
    args = parser.parse_args()

    backfill_deductions(dry_run=args.dry_run, limit=args.limit)

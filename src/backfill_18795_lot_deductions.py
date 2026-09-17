"""
Backfill missing 18795 lot deduction transactions.

BACKGROUND
----------
When lot 11001 (18795) was depleted, the lot tagger stopped writing CF1.
deduct_lot_inventory() skips silently when CF1 is empty, so shipped 18795
orders after that point have rows in shipped_items but no corresponding
Ship transaction in inventory_transactions.

This script finds those gaps and inserts the missing Ship transactions,
attributing them all to lot 11001 (the only 18795 lot).

USAGE
-----
Dry-run (default):
    python src/backfill_18795_lot_deductions.py

Live write:
    python src/backfill_18795_lot_deductions.py --write

SAFETY
------
- Skips any order that already has a Ship transaction for 18795 with any lot.
- Records the backfill in the notes column so it is auditable.
- All inserts happen in one transaction; rolled back on any error.
"""

import argparse
import logging
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import psycopg2
from src.services.database.connection import get_connection

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SKU = '18795'
BACKFILL_NOTE = 'Backfill: deduction missing because CF1 was not set when lot depleted'


def run(write: bool = False):
    conn = get_connection()
    cur = conn.cursor()

    # ── 1. Find the lot_id for 18795 lot 11001 ──────────────────────────────
    cur.execute("""
        SELECT l.lot_id, l.lot_number, l.status, lb.balance
        FROM lots l
        JOIN skus s ON s.sku_id = l.sku_id
        LEFT JOIN lot_balances lb ON lb.lot_id = l.lot_id
        WHERE s.sku_code = %s
        ORDER BY l.lot_id
    """, (SKU,))
    all_lots = cur.fetchall()
    logger.info(f"All {SKU} lots:")
    for r in all_lots:
        logger.info(f"  lot_id={r[0]} lot={r[1]} status={r[2]} balance={r[3]}")

    # Backfill against the lot with the most history — lot 11001 (lot_id=7)
    # If a second lot now exists and is active, shipped orders AFTER it was
    # activated already have correct CF1 and are excluded by the guard below.
    target_lot = next((r for r in all_lots if r[1] == '11001'), None)
    if not target_lot:
        logger.error("Lot 11001 not found — cannot backfill. Check lot numbers.")
        return
    lot_id, lot_number = target_lot[0], target_lot[1]
    logger.info(f"\nBackfilling against lot_id={lot_id} (lot {lot_number})")

    # ── 2. Find shipped 18795 orders with no existing Ship deduction ─────────
    cur.execute("""
        SELECT
            si.order_number,
            si.ship_date,
            si.quantity_shipped,
            si.shipstation_order_id
        FROM shipped_items si
        WHERE si.base_sku = %s
          AND si.shipstation_order_id IS NOT NULL
          AND si.shipstation_order_id != ''
          AND NOT EXISTS (
              SELECT 1
              FROM inventory_transactions it
              WHERE it.sku = %s
                AND it.shipstation_order_id = si.shipstation_order_id
                AND it.transaction_type = 'Ship'
                AND it.archived_at IS NULL
          )
        ORDER BY si.ship_date, si.order_number
    """, (SKU, SKU))
    missing = cur.fetchall()

    if not missing:
        logger.info("No missing deductions found — nothing to backfill.")
        conn.close()
        return

    logger.info(f"\nFound {len(missing)} shipped 18795 order(s) with no Ship transaction:")
    total_units = 0
    for row in missing:
        order_number, ship_date, qty, ss_id = row
        logger.info(f"  order={order_number} ship_date={ship_date} qty={qty} ss_id={ss_id}")
        total_units += (qty or 0)
    logger.info(f"\nTotal units to backfill: {total_units}")

    if not write:
        logger.info("\nDRY RUN — no changes made. Re-run with --write to apply.")
        conn.close()
        return

    # ── 3. Insert missing Ship transactions ──────────────────────────────────
    logger.info("\nApplying backfill...")
    inserted = 0
    try:
        for order_number, ship_date, qty, ss_id in missing:
            ship_date_str = (
                ship_date.strftime('%Y-%m-%d')
                if hasattr(ship_date, 'strftime')
                else str(ship_date)[:10]
            )
            cur.execute("""
                INSERT INTO inventory_transactions
                    (date, sku, quantity, transaction_type, lot_id,
                     shipstation_order_id, notes)
                VALUES (%s, %s, %s, 'Ship', %s, %s, %s)
            """, (
                ship_date_str,
                SKU,
                abs(int(qty or 0)),
                lot_id,
                str(ss_id),
                f"{order_number} | {BACKFILL_NOTE}",
            ))
            inserted += 1
            logger.info(f"  ✅ Inserted Ship {qty} × {SKU} lot {lot_number} for order {order_number}")

        conn.commit()
        logger.info(f"\nDone — {inserted} transaction(s) inserted, {total_units} units backfilled.")
        logger.info("Run lot inventory to confirm balance is now correct.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error during backfill — rolled back: {e}", exc_info=True)
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill missing 18795 Ship transactions')
    parser.add_argument('--write', action='store_true',
                        help='Actually insert records (default is dry-run)')
    args = parser.parse_args()
    run(write=args.write)

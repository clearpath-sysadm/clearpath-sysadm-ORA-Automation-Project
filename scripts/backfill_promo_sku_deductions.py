#!/usr/bin/env python3
"""
Backfill promo SKU inventory deductions.

Corrects two issues for shipped promo SKU orders (17613, 17905, 17915, 18676):
  1. shipped_items.sku_lot was written as the bare promo SKU (e.g. '17613')
     instead of the real lot stamp from CF1 (e.g. '17612 - 260082').
  2. No inventory_transactions (Ship) rows exist for these orders.

Source of truth: orders_inbox.lot_stamp (which stores CF1 at import time).
This is a pure database operation — no ShipStation API calls needed.

Safe to re-run: all operations are idempotent.
  - Phase C UPDATE only fires where sku_lot still equals base_sku.
  - Phase D uses deduct_lot_inventory which guards against double-insertion
    via (lot_id, shipstation_order_id, 'Ship') uniqueness check.

Usage:
    python scripts/backfill_promo_sku_deductions.py
"""

import sys
import os
import logging

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.pg_utils import execute_query, transaction
from src.services.inventory.lot_deduction import deduct_lot_inventory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


def run_backfill():
    logger.info("=== Promo SKU Deduction Backfill — START ===")

    # Phase A: Identify affected rows
    logger.info("Phase A: Identifying affected rows...")
    affected = execute_query("""
        SELECT
            si.order_number,
            si.base_sku           AS promo_sku,
            si.quantity_shipped,
            si.ship_date,
            oi.lot_stamp,
            oi.shipstation_order_id,
            sp.base_sku           AS expected_base_sku
        FROM shipped_items si
        JOIN orders_inbox oi  ON oi.order_number = si.order_number
        JOIN sku_promotions sp ON sp.promo_sku = si.base_sku AND sp.active = TRUE
        WHERE si.sku_lot = si.base_sku
        ORDER BY si.base_sku, si.ship_date, si.order_number
    """)

    if not affected:
        logger.info("No affected rows found — backfill already complete.")
        return

    logger.info(f"Phase A: Found {len(affected)} affected shipped_items rows")

    # Pre-load lot lookup for validation: {(sku_code, lot_number): lot_id}
    lot_rows = execute_query("""
        SELECT s.sku_code, l.lot_number, l.lot_id
        FROM lots l
        JOIN skus s ON l.sku_id = s.sku_id
    """)
    lot_lookup = {(row[0], row[1]): row[2] for row in lot_rows} if lot_rows else {}

    # Phase B: Validate each row
    logger.info("Phase B: Validating rows...")
    validated = []
    skipped = []

    for row in affected:
        order_number, promo_sku, quantity, ship_date, lot_stamp, ss_order_id, expected_base = row

        if not lot_stamp or not lot_stamp.strip():
            skipped.append((order_number, promo_sku, "lot_stamp is blank"))
            continue

        lot_stamp = lot_stamp.strip()

        if ' - ' not in lot_stamp:
            skipped.append((order_number, promo_sku,
                            f"lot_stamp '{lot_stamp}' missing ' - ' separator"))
            continue

        parts = lot_stamp.split(' - ', 1)
        cf1_sku = parts[0].strip()
        cf1_lot = parts[1].strip()

        if cf1_sku != expected_base:
            skipped.append((order_number, promo_sku,
                            f"CF1 SKU '{cf1_sku}' != expected base '{expected_base}'"))
            continue

        lot_id = lot_lookup.get((cf1_sku, cf1_lot))
        if lot_id is None:
            skipped.append((order_number, promo_sku,
                            f"lot '{cf1_lot}' not found in lots table for SKU '{cf1_sku}'"))
            continue

        if not ss_order_id:
            skipped.append((order_number, promo_sku, "shipstation_order_id is null"))
            continue

        validated.append({
            'order_number':        order_number,
            'promo_sku':           promo_sku,
            'base_sku':            cf1_sku,
            'lot_stamp':           lot_stamp,
            'lot_id':              lot_id,
            'quantity':            quantity,
            'ship_date':           ship_date,
            'shipstation_order_id': str(ss_order_id),
        })

    logger.info(f"Phase B: {len(validated)} validated, {len(skipped)} skipped")
    for order_number, promo_sku, reason in skipped:
        logger.warning(f"  SKIPPED {order_number}/{promo_sku}: {reason}")

    if not validated:
        logger.info("No validated rows to process — nothing to do.")
        return

    # Phase C + D: Update shipped_items then insert deductions
    logger.info("Phase C: Updating shipped_items.sku_lot ...")
    logger.info("Phase D: Inserting inventory deductions ...")

    si_updated = 0
    tx_inserted = 0
    tx_already_existed = 0

    with transaction() as conn:
        cursor = conn.cursor()
        for item in validated:
            # Phase C — update sku_lot from bare promo SKU to real lot stamp
            cursor.execute("""
                UPDATE shipped_items
                SET sku_lot = %s
                WHERE order_number = %s
                  AND base_sku = %s
                  AND sku_lot = %s
            """, (item['lot_stamp'], item['order_number'],
                  item['promo_sku'], item['promo_sku']))
            if cursor.rowcount > 0:
                si_updated += cursor.rowcount
                logger.info(
                    f"  C: order {item['order_number']} / {item['promo_sku']} "
                    f"→ sku_lot='{item['lot_stamp']}'"
                )

            # Phase D — insert deduction using resolved BASE SKU (not promo SKU).
            # deduct_lot_inventory guards against double-insertion automatically.
            inserted = deduct_lot_inventory(
                order_number=item['order_number'],
                shipstation_order_id=item['shipstation_order_id'],
                base_sku=item['base_sku'],           # '17612', not '17613'
                customField1_value=item['lot_stamp'],
                ship_date=item['ship_date'],
                quantity=item['quantity'],
                conn=conn,
            )
            if inserted:
                tx_inserted += 1
            else:
                tx_already_existed += 1

    # Phase E: Audit summary
    logger.info("=== Backfill Audit Summary ===")
    logger.info(f"  Rows identified  (Phase A): {len(affected)}")
    logger.info(f"  Rows validated   (Phase B): {len(validated)}")
    logger.info(f"  Rows skipped     (Phase B): {len(skipped)}")
    logger.info(f"  shipped_items updated (C):  {si_updated}")
    logger.info(f"  tx inserted      (Phase D): {tx_inserted}")
    logger.info(f"  tx already existed (D):     {tx_already_existed}")

    # Verification
    remaining = execute_query("""
        SELECT COUNT(*)
        FROM shipped_items si
        JOIN sku_promotions sp ON sp.promo_sku = si.base_sku AND sp.active = TRUE
        WHERE si.sku_lot = si.base_sku
    """)
    remaining_count = remaining[0][0] if remaining else '?'
    logger.info(f"  Bare-SKU rows remaining:    {remaining_count} (expect 0)")

    deducted = execute_query("""
        SELECT it.sku, COUNT(*) AS tx_count, SUM(it.quantity) AS units
        FROM inventory_transactions it
        JOIN sku_promotions sp ON sp.base_sku = it.sku AND sp.active = TRUE
        WHERE it.transaction_type = 'Ship'
          AND it.shipstation_order_id IN (
            SELECT oi.shipstation_order_id
            FROM orders_inbox oi
            JOIN shipped_items si ON si.order_number = oi.order_number
            JOIN sku_promotions sp2 ON sp2.promo_sku = si.base_sku AND sp2.active = TRUE
            WHERE si.sku_lot != si.base_sku
          )
        GROUP BY it.sku
    """)
    if deducted:
        for row in deducted:
            logger.info(f"  Deductions for base SKU {row[0]}: {row[1]} tx / {row[2]} units")

    logger.info("=== Promo SKU Deduction Backfill — DONE ===")


if __name__ == '__main__':
    run_backfill()

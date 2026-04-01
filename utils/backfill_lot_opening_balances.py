#!/usr/bin/env python3
"""
Backfill opening-balance inventory transactions for every lot.

For each lot in `lot_inventory`, computes:
    opening_balance = initial_qty + COALESCE(manual_adjustment, 0)

then inserts a single 'Receive' transaction into `inventory_transactions`
tied to the matching `lots.lot_id`.  The script is idempotent: it checks for
an existing transaction whose notes field starts with the sentinel marker
and skips the lot if one already exists.

Run once after migration 009 has been applied:
    python utils/backfill_lot_opening_balances.py

Add --dry-run to preview without writing anything.
"""
import sys
import os
import argparse

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection

MARKER = 'Opening balance (migrated from lot_inventory)'


def run_backfill(dry_run: bool = False):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print(f"Lot opening-balance backfill — {'DRY RUN' if dry_run else 'LIVE'}")

        # Fetch all lot_inventory rows together with their resolved lot_id
        cursor.execute("""
            SELECT
                li.id            AS li_id,
                li.sku,
                li.lot,
                li.initial_qty,
                COALESCE(li.manual_adjustment, 0) AS manual_adj,
                COALESCE(li.received_date, CURRENT_DATE::text) AS recv_date,
                l.lot_id
            FROM lot_inventory li
            JOIN skus s  ON s.sku_code  = li.sku
            JOIN lots l  ON l.sku_id    = s.sku_id
                        AND l.lot_number = li.lot
            ORDER BY li.sku, li.received_date
        """)
        rows = cursor.fetchall()
        print(f"  Found {len(rows)} lot_inventory rows to process")

        inserted = 0
        skipped  = 0
        zero_bal = 0

        for (li_id, sku, lot, initial_qty, manual_adj,
             recv_date, lot_id) in rows:

            opening_balance = initial_qty + manual_adj

            if opening_balance == 0:
                print(f"  SKIP zero-balance: {sku} lot {lot} (li_id={li_id})")
                zero_bal += 1
                continue

            # Idempotency check — look for existing opening-balance transaction
            cursor.execute("""
                SELECT id FROM inventory_transactions
                WHERE lot_id = %s
                  AND transaction_type = 'Receive'
                  AND notes LIKE %s
                LIMIT 1
            """, (lot_id, MARKER + '%'))

            if cursor.fetchone():
                skipped += 1
                continue

            print(f"  {'(dry) ' if dry_run else ''}INSERT Receive {opening_balance:>6} "
                  f"for {sku} lot {lot} (lot_id={lot_id}, date={recv_date})")

            if not dry_run:
                cursor.execute("""
                    INSERT INTO inventory_transactions
                        (date, sku, quantity, transaction_type, notes, lot_id)
                    VALUES (%s, %s, %s, 'Receive', %s, %s)
                    ON CONFLICT DO NOTHING
                """, (recv_date, sku, opening_balance, MARKER, lot_id))

                # Reflect in inventory_current
                cursor.execute("""
                    UPDATE inventory_current
                    SET current_quantity = current_quantity + %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE sku = %s
                """, (opening_balance, sku))

            inserted += 1

        if not dry_run:
            conn.commit()

        print(f"\nSummary: {inserted} inserted, {skipped} already existed, "
              f"{zero_bal} skipped (zero balance)")
        print("Backfill complete.")

    except Exception as exc:
        conn.rollback()
        print(f"Backfill FAILED: {exc}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Backfill lot opening balances into inventory_transactions'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview changes without writing to the database'
    )
    args = parser.parse_args()
    run_backfill(dry_run=args.dry_run)

#!/usr/bin/env python3
"""
Migration 017 — Add 'Cancel' transaction type to inventory_transactions.

Purpose:
    Enables inventory reversal rows to be written when a shipped order is
    subsequently cancelled in ShipStation.

Changes:
    1. Extends the CHECK constraint on inventory_transactions.transaction_type
       to include 'Cancel'.
    2. Recreates the lot_balances VIEW so 'Cancel' rows are treated as positive
       balance contributions (same sign as 'Receive'), restoring deducted units.
    3. Recreates inventory_summary (dropped by CASCADE from lot_balances) so
       the dashboard and alerts continue to work immediately after migration.

Important:
    - Uses DROP VIEW lot_balances CASCADE because inventory_summary depends on
      lot_balances. Both views are fully recreated within this migration.
    - Run during low-traffic hours (outside business hours) — the DROP+CREATE
      window is seconds but will error any in-flight VIEW queries.
    - Do NOT edit migration 009 (already ran on production). This is the
      authoritative change for 'Cancel' support.

Rollback:
    migrate_down() removes 'Cancel' from the constraint and reverts the VIEW.
    Any existing 'Cancel' rows must be deleted first or the constraint will fail.
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import psycopg2


def get_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    return psycopg2.connect(db_url)


LOT_BALANCES_VIEW_SQL = """
    CREATE VIEW lot_balances AS
    SELECT
        l.lot_id,
        s.sku_code,
        l.lot_number,
        l.status,
        l.received_date,
        l.notes,
        l.created_at,
        l.updated_at,
        COALESCE(SUM(
            CASE
                WHEN it.transaction_type IN ('Receive', 'Adjust Up', 'Repack', 'Cancel')
                     THEN  it.quantity
                WHEN it.transaction_type IN ('Ship', 'Adjust Down')
                     THEN -it.quantity
                ELSE 0
            END
        ), 0) AS balance
    FROM lots l
    JOIN skus s ON s.sku_id = l.sku_id
    LEFT JOIN inventory_transactions it ON it.lot_id = l.lot_id
    GROUP BY l.lot_id, s.sku_code, l.lot_number, l.status,
             l.received_date, l.notes, l.created_at, l.updated_at
"""

LOT_BALANCES_VIEW_SQL_WITHOUT_CANCEL = """
    CREATE VIEW lot_balances AS
    SELECT
        l.lot_id,
        s.sku_code,
        l.lot_number,
        l.status,
        l.received_date,
        l.notes,
        l.created_at,
        l.updated_at,
        COALESCE(SUM(
            CASE
                WHEN it.transaction_type IN ('Receive', 'Adjust Up', 'Repack')
                     THEN  it.quantity
                WHEN it.transaction_type IN ('Ship', 'Adjust Down')
                     THEN -it.quantity
                ELSE 0
            END
        ), 0) AS balance
    FROM lots l
    JOIN skus s ON s.sku_id = l.sku_id
    LEFT JOIN inventory_transactions it ON it.lot_id = l.lot_id
    GROUP BY l.lot_id, s.sku_code, l.lot_number, l.status,
             l.received_date, l.notes, l.created_at, l.updated_at
"""

INVENTORY_SUMMARY_VIEW_SQL = """
    CREATE VIEW inventory_summary AS
    SELECT sku_code AS sku, SUM(balance) AS current_quantity
    FROM lot_balances
    WHERE status != 'quarantine'
    GROUP BY sku_code
"""


def migrate_up():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print("Running migration 017: Add 'Cancel' transaction type ...")

        # 1. Extend the CHECK constraint to include 'Cancel'
        cursor.execute("""
            ALTER TABLE inventory_transactions
            DROP CONSTRAINT IF EXISTS inventory_transactions_transaction_type_check
        """)
        cursor.execute("""
            ALTER TABLE inventory_transactions
            ADD CONSTRAINT inventory_transactions_transaction_type_check
            CHECK (transaction_type = ANY (ARRAY[
                'Receive'::text,
                'Ship'::text,
                'Adjust Up'::text,
                'Adjust Down'::text,
                'Repack'::text,
                'Cancel'::text
            ]))
        """)
        print("  [1/3] CHECK constraint extended to include 'Cancel'.")

        # 2. Recreate lot_balances with Cancel support.
        #    CASCADE also drops inventory_summary — recreated in step 3.
        cursor.execute("DROP VIEW IF EXISTS lot_balances CASCADE")
        cursor.execute(LOT_BALANCES_VIEW_SQL)
        print("  [2/3] lot_balances VIEW recreated (Cancel credited as +quantity).")

        # 3. Recreate inventory_summary (dropped by CASCADE above)
        cursor.execute(INVENTORY_SUMMARY_VIEW_SQL)
        print("  [3/3] inventory_summary VIEW recreated.")

        conn.commit()
        print("Migration 017 completed successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"Migration 017 FAILED: {exc}")
        raise
    finally:
        conn.close()


def migrate_down():
    """
    Reverse migration 017.
    WARNING: Any existing 'Cancel' rows in inventory_transactions must be
    deleted before running rollback, or the restored CHECK constraint will fail.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print("Rolling back migration 017 ...")

        # Restore original CHECK constraint (without 'Cancel')
        cursor.execute("""
            ALTER TABLE inventory_transactions
            DROP CONSTRAINT IF EXISTS inventory_transactions_transaction_type_check
        """)
        cursor.execute("""
            ALTER TABLE inventory_transactions
            ADD CONSTRAINT inventory_transactions_transaction_type_check
            CHECK (transaction_type = ANY (ARRAY[
                'Receive'::text,
                'Ship'::text,
                'Adjust Up'::text,
                'Adjust Down'::text,
                'Repack'::text
            ]))
        """)

        # Recreate lot_balances without Cancel and restore inventory_summary
        cursor.execute("DROP VIEW IF EXISTS lot_balances CASCADE")
        cursor.execute(LOT_BALANCES_VIEW_SQL_WITHOUT_CANCEL)
        cursor.execute(INVENTORY_SUMMARY_VIEW_SQL)

        conn.commit()
        print("Migration 017 rolled back successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"Migration 017 rollback FAILED: {exc}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_up()

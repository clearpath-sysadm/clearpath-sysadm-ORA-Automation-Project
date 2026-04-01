#!/usr/bin/env python3
"""
Migration 009: Lot tracking schema rebuild

Creates the unified `skus` and `lots` tables, populates them from the existing
`sku_lot` and `lot_inventory` data, drops stale unique constraints, adds
`lot_id` FK columns to `inventory_transactions` and
`shipstation_order_line_items`, and creates the `lot_balances` computed view.

Date: 2026-04-01
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection


def migrate_up():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Migration 009: Lot tracking schema rebuild — starting...")

        # ------------------------------------------------------------------ #
        # 1. Create skus table
        # ------------------------------------------------------------------ #
        print("  [1/8] Creating skus table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skus (
                sku_id   SERIAL PRIMARY KEY,
                sku_code TEXT   NOT NULL,
                CONSTRAINT skus_sku_code_unique UNIQUE (sku_code)
            )
        """)

        # ------------------------------------------------------------------ #
        # 2. Create lots table (consolidates sku_lot + lot_inventory)
        # ------------------------------------------------------------------ #
        print("  [2/8] Creating lots table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lots (
                lot_id        SERIAL  PRIMARY KEY,
                sku_id        INTEGER NOT NULL REFERENCES skus(sku_id),
                lot_number    TEXT    NOT NULL,
                status        TEXT    NOT NULL DEFAULT 'active'
                                  CHECK (status IN ('active','inactive','depleted','quarantine')),
                received_date TEXT,
                notes         TEXT,
                created_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
                updated_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT lots_sku_id_lot_number_unique UNIQUE (sku_id, lot_number)
            )
        """)

        # ------------------------------------------------------------------ #
        # 3. Populate skus from sku_lot
        # ------------------------------------------------------------------ #
        print("  [3/8] Populating skus...")
        cursor.execute("""
            INSERT INTO skus (sku_code)
            SELECT DISTINCT sku FROM sku_lot ORDER BY sku
            ON CONFLICT (sku_code) DO NOTHING
        """)
        cursor.execute("SELECT COUNT(*) FROM skus")
        print(f"         {cursor.fetchone()[0]} rows in skus")

        # ------------------------------------------------------------------ #
        # 4. Populate lots from sku_lot LEFT JOIN lot_inventory
        #    Prefer lot_inventory.status if a matching row exists, otherwise
        #    map sku_lot.active (1/0) → 'active'/'inactive'.
        # ------------------------------------------------------------------ #
        print("  [4/8] Populating lots...")
        cursor.execute("""
            INSERT INTO lots (sku_id, lot_number, status, received_date, notes,
                              created_at, updated_at)
            SELECT
                s.sku_id,
                sl.lot,
                COALESCE(
                    li.status,
                    CASE WHEN sl.active = 1 THEN 'active' ELSE 'inactive' END
                ),
                li.received_date,
                li.notes,
                sl.created_at,
                sl.updated_at
            FROM sku_lot sl
            JOIN skus s ON s.sku_code = sl.sku
            LEFT JOIN lot_inventory li
                   ON li.sku = sl.sku AND li.lot = sl.lot
            ON CONFLICT (sku_id, lot_number) DO NOTHING
        """)
        cursor.execute("SELECT COUNT(*) FROM lots")
        print(f"         {cursor.fetchone()[0]} rows in lots")

        # ------------------------------------------------------------------ #
        # 5. Drop stale unique constraints before adding lot_id columns
        # ------------------------------------------------------------------ #
        print("  [5/8] Dropping stale unique constraints...")
        cursor.execute("""
            ALTER TABLE order_items_inbox
            DROP CONSTRAINT IF EXISTS order_items_inbox_order_sku_unique
        """)
        cursor.execute("""
            DROP INDEX IF EXISTS idx_shipstation_order_line_items_unique
        """)

        # ------------------------------------------------------------------ #
        # 6. Add lot_id to inventory_transactions + replace uniqueness index
        # ------------------------------------------------------------------ #
        print("  [6/8] Adding lot_id to inventory_transactions...")
        cursor.execute("""
            ALTER TABLE inventory_transactions
            ADD COLUMN IF NOT EXISTS lot_id INTEGER REFERENCES lots(lot_id)
        """)
        cursor.execute("""
            ALTER TABLE inventory_transactions
            DROP CONSTRAINT IF EXISTS
                inventory_transactions_date_sku_transaction_type_quantity_key
        """)
        # Functional index handles NULL lot_id gracefully via COALESCE
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                inventory_transactions_date_sku_lot_id_type_qty_key
            ON inventory_transactions
                (date, sku, COALESCE(lot_id, -1), transaction_type, quantity)
        """)

        # ------------------------------------------------------------------ #
        # 7. Add lot_id to shipstation_order_line_items + rebuild unique index
        # ------------------------------------------------------------------ #
        print("  [7/8] Adding lot_id to shipstation_order_line_items...")
        cursor.execute("""
            ALTER TABLE shipstation_order_line_items
            ADD COLUMN IF NOT EXISTS lot_id INTEGER REFERENCES lots(lot_id)
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique
            ON shipstation_order_line_items
                (order_inbox_id, sku, COALESCE(lot_id, -1))
        """)

        # Re-add order_items_inbox unique constraint (same columns — lot_id
        # does not live on this table; multiple lots are distinguished at
        # the order level via shipstation_order_line_items)
        cursor.execute("""
            ALTER TABLE order_items_inbox
            ADD CONSTRAINT order_items_inbox_order_sku_unique
            UNIQUE (order_inbox_id, sku)
        """)

        # ------------------------------------------------------------------ #
        # 8. Create lot_balances view
        # ------------------------------------------------------------------ #
        print("  [8/8] Creating lot_balances view...")
        cursor.execute("DROP VIEW IF EXISTS lot_balances")
        cursor.execute("""
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
                        WHEN it.transaction_type IN ('Receive','Adjust Up','Repack')
                             THEN  it.quantity
                        WHEN it.transaction_type IN ('Ship','Adjust Down')
                             THEN -it.quantity
                        ELSE 0
                    END
                ), 0) AS balance
            FROM lots l
            JOIN skus s ON s.sku_id = l.sku_id
            LEFT JOIN inventory_transactions it ON it.lot_id = l.lot_id
            GROUP BY l.lot_id, s.sku_code, l.lot_number, l.status,
                     l.received_date, l.notes, l.created_at, l.updated_at
        """)

        conn.commit()
        print("Migration 009 completed successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"Migration 009 FAILED: {exc}")
        raise
    finally:
        conn.close()


def migrate_down():
    """Reverse migration 009 — removes all added objects."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Rolling back migration 009...")

        cursor.execute("DROP VIEW IF EXISTS lot_balances")

        # shipstation_order_line_items
        cursor.execute(
            "DROP INDEX IF EXISTS idx_shipstation_order_line_items_unique"
        )
        cursor.execute("""
            ALTER TABLE shipstation_order_line_items
            DROP COLUMN IF EXISTS lot_id
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique
            ON shipstation_order_line_items (order_inbox_id, sku)
        """)

        # inventory_transactions
        cursor.execute("""
            DROP INDEX IF EXISTS
                inventory_transactions_date_sku_lot_id_type_qty_key
        """)
        cursor.execute("""
            ALTER TABLE inventory_transactions DROP COLUMN IF EXISTS lot_id
        """)
        cursor.execute("""
            ALTER TABLE inventory_transactions
            ADD CONSTRAINT inventory_transactions_date_sku_transaction_type_quantity_key
            UNIQUE (date, sku, transaction_type, quantity)
        """)

        # lots / skus
        cursor.execute("DROP TABLE IF EXISTS lots")
        cursor.execute("DROP TABLE IF EXISTS skus")

        conn.commit()
        print("Rollback of migration 009 completed.")

    except Exception as exc:
        conn.rollback()
        print(f"Rollback FAILED: {exc}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        migrate_down()
    else:
        migrate_up()

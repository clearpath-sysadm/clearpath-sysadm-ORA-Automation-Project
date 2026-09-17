#!/usr/bin/env python3
"""Migration 023: auditable archive/restore for lots and inventory transactions."""

from src.services.database.pg_utils import get_connection


LOT_BALANCES_SQL = """
CREATE OR REPLACE VIEW lot_balances AS
SELECT l.lot_id, s.sku_code, l.lot_number, l.status, l.received_date,
       l.notes, l.created_at, l.updated_at,
       COALESCE(SUM(CASE
           WHEN it.transaction_type IN ('Receive','Adjust Up','Repack','Cancel')
             THEN it.quantity
           WHEN it.transaction_type IN ('Ship','Adjust Down')
             THEN -it.quantity
           ELSE 0 END), 0) AS balance
FROM lots l
JOIN skus s ON s.sku_id = l.sku_id
LEFT JOIN inventory_transactions it
  ON it.lot_id = l.lot_id AND it.archived_at IS NULL
GROUP BY l.lot_id, s.sku_code, l.lot_number, l.status, l.received_date,
         l.notes, l.created_at, l.updated_at
"""


def migrate_up():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for table in ("lots", "inventory_transactions"):
                cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS archived_by TEXT")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS archive_reason TEXT")
            cur.execute("ALTER TABLE lots ADD COLUMN IF NOT EXISTS pre_archive_status TEXT")
            cur.execute("""
                CREATE OR REPLACE FUNCTION prevent_archived_lot_transaction_write()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.lot_id IS NOT NULL AND EXISTS (
                        SELECT 1 FROM lots
                        WHERE lot_id = NEW.lot_id AND archived_at IS NOT NULL
                    ) THEN
                        RAISE EXCEPTION 'archived lots cannot receive inventory transactions';
                    END IF;
                    RETURN NEW;
                END $$;
            """)
            cur.execute("""
                DROP TRIGGER IF EXISTS inventory_transactions_reject_archived_lot
                ON inventory_transactions
            """)
            cur.execute("""
                CREATE TRIGGER inventory_transactions_reject_archived_lot
                BEFORE INSERT OR UPDATE ON inventory_transactions
                FOR EACH ROW EXECUTE FUNCTION prevent_archived_lot_transaction_write()
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inventory_lifecycle_events (
                    id BIGSERIAL PRIMARY KEY,
                    entity_type TEXT NOT NULL CHECK (entity_type IN ('lot','transaction')),
                    entity_id BIGINT NOT NULL,
                    action TEXT NOT NULL CHECK (action IN ('archive','restore')),
                    actor TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE OR REPLACE FUNCTION prevent_inventory_lifecycle_mutation()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'inventory_lifecycle_events is append-only';
                END $$;
            """)
            cur.execute("""
                DROP TRIGGER IF EXISTS inventory_lifecycle_events_append_only
                ON inventory_lifecycle_events
            """)
            cur.execute("""
                CREATE TRIGGER inventory_lifecycle_events_append_only
                BEFORE UPDATE OR DELETE ON inventory_lifecycle_events
                FOR EACH ROW EXECUTE FUNCTION prevent_inventory_lifecycle_mutation()
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS inventory_lifecycle_events_entity_idx ON inventory_lifecycle_events (entity_type, entity_id, created_at)")
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'lot_balances'
                      AND column_name = 'archived_at'
                )
            """)
            if cur.fetchone()[0]:
                cur.execute("DROP VIEW IF EXISTS inventory_summary")
                cur.execute("DROP VIEW IF EXISTS lot_balances")
            cur.execute(LOT_BALANCES_SQL)
            cur.execute("""
                CREATE OR REPLACE VIEW inventory_summary AS
                SELECT lb.sku_code AS sku, SUM(lb.balance) AS current_quantity
                FROM lot_balances lb
                JOIN lots l ON l.lot_id = lb.lot_id
                WHERE lb.status != 'quarantine' AND l.archived_at IS NULL
                GROUP BY lb.sku_code
            """)
        conn.commit()
    finally:
        conn.close()


def migrate_down():
    raise RuntimeError("Inventory archive migration is intentionally not reversible; restore records instead.")


if __name__ == "__main__":
    migrate_up()
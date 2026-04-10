"""
Startup migrations — run once at app boot before serving traffic.

Each migration is idempotent and safe to run repeatedly.
Failures are logged but do not crash the app.
"""

import logging

logger = logging.getLogger(__name__)


def _dedup_lot_mismatch_alerts(cursor):
    """
    Remove duplicate shipstation_order_id rows from lot_mismatch_alerts,
    keeping the earliest row (lowest id) per order ID.

    Background: the table used to allow one row per (order_number, base_sku),
    so multi-SKU orders could accumulate several rows under the same
    shipstation_order_id. The current design requires exactly one row per
    shipstation_order_id (the scanner uses a SELECT pre-check before INSERT).
    """
    cursor.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT shipstation_order_id)
        FROM lot_mismatch_alerts
    """)
    extra = cursor.fetchone()[0]

    if extra == 0:
        logger.info("startup_migrations: lot_mismatch_alerts — no duplicates, skipping dedup")
        return 0

    logger.warning(
        f"startup_migrations: lot_mismatch_alerts — found {extra} duplicate rows, deduplicating"
    )

    cursor.execute("""
        DELETE FROM lot_mismatch_alerts
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM lot_mismatch_alerts
            GROUP BY shipstation_order_id
        )
    """)
    deleted = cursor.rowcount
    logger.info(f"startup_migrations: lot_mismatch_alerts — deleted {deleted} duplicate rows")
    return deleted


def _ensure_shipstation_line_items_index(cursor):
    """
    Create the unique index on shipstation_order_line_items that includes lot_id.

    Background: Replit's migration generator produces wrong operator classes for
    COALESCE expressions mixed with columns of varying types, causing deployment
    failures. We manage this index directly via psycopg2 (plain SQL) to bypass
    the generator, letting Replit handle only the simple ADD COLUMN lot_id step.

    Safe to call repeatedly — checks for the column and index before acting.
    Logs an ERROR (non-fatal) if index creation fails so the issue is visible.
    """
    # Skip if lot_id column doesn't exist yet (Replit migration hasn't run)
    cursor.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'shipstation_order_line_items'
          AND column_name = 'lot_id'
    """)
    if not cursor.fetchone():
        logger.info(
            "startup_migrations: shipstation_order_line_items.lot_id not yet present — "
            "skipping index creation (Replit migration pending)"
        )
        return

    # Skip if index already exists
    cursor.execute("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'shipstation_order_line_items'
          AND indexname = 'idx_shipstation_order_line_items_unique'
    """)
    if cursor.fetchone():
        logger.info(
            "startup_migrations: idx_shipstation_order_line_items_unique already present"
        )
        return

    # Dedup first so index creation can't fail due to existing duplicates
    cursor.execute("""
        DELETE FROM shipstation_order_line_items
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM shipstation_order_line_items
            GROUP BY order_inbox_id, sku, COALESCE(lot_id, -1)
        )
    """)
    removed = cursor.rowcount
    if removed > 0:
        logger.warning(
            f"startup_migrations: shipstation_order_line_items — removed {removed} "
            "duplicate rows before index creation"
        )

    cursor.execute("""
        CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique
        ON shipstation_order_line_items (order_inbox_id, sku, COALESCE(lot_id, '-1'::integer))
    """)
    logger.info(
        "startup_migrations: idx_shipstation_order_line_items_unique created successfully"
    )


def run_all(conn):
    """
    Run every startup migration inside a single transaction.
    Rolls back and logs on any failure so the app can still start.
    """
    try:
        with conn.cursor() as cur:
            _dedup_lot_mismatch_alerts(cur)
            _ensure_shipstation_line_items_index(cur)
        conn.commit()
        logger.info("startup_migrations: all migrations completed successfully")
    except Exception as exc:
        conn.rollback()
        logger.error(f"startup_migrations: migration failed, rolled back — {exc}", exc_info=True)

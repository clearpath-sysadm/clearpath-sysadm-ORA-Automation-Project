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
    shipstation_order_id.  The current design requires exactly one row per
    shipstation_order_id (the scanner uses ON CONFLICT on that column).
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


def run_all(conn):
    """
    Run every startup migration inside a single transaction.
    Rolls back and logs on any failure so the app can still start.
    """
    try:
        with conn.cursor() as cur:
            _dedup_lot_mismatch_alerts(cur)
        conn.commit()
        logger.info("startup_migrations: all migrations completed successfully")
    except Exception as exc:
        conn.rollback()
        logger.error(f"startup_migrations: migration failed, rolled back — {exc}", exc_info=True)

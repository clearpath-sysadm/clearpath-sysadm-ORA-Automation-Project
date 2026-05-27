"""
Task #88 — One-time pre-deploy resolution script for order 862852.

Order 862852 is stranded in the promo SKU cancel-and-recreate flow (verify_failed).
It carries a Promo Hold tag in ShipStation and an unresolved lot_tagging_failures row.
This script must be run in PRODUCTION before or during the Task #86 production deploy.

What this script does:
  1. Removes the 'Promo Hold' ShipStation tag from SS order 283948250
  2. Stamps customField3 with 'resolved:manual YYYY-MM-DD' in ShipStation
  3. Writes a 'manually_resolved' row to promo_sku_replacement_log (idempotent)
  4. Marks the lot_tagging_failures row resolved (idempotent)

Run from the production environment:
    python3 scripts/resolve_order_862852.py

Safe to run multiple times — all operations are idempotent.
"""
import sys
import os
import logging
from datetime import date

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ORDER_NUMBER = '862852'
SS_ORDER_ID = 283948250
PROMO_SKU = '17613'
BASE_SKU = '17612'


def main():
    logger.info(f"=== Resolving order {ORDER_NUMBER} (SS ID {SS_ORDER_ID}) ===")

    try:
        from src.services.shipstation.api_client import (
            remove_promo_hold_tag,
            update_order_custom_fields,
        )
        from src.services.database.pg_utils import get_connection
    except ImportError as e:
        logger.error(f"Import error — run this from the project root: {e}")
        sys.exit(1)

    errors = []

    logger.info(f"Step 1: Removing Promo Hold tag from SS order {SS_ORDER_ID} ...")
    tag_result = remove_promo_hold_tag(SS_ORDER_ID)
    if tag_result.get('success'):
        logger.info("  ✓ Promo Hold tag removed successfully")
    else:
        err = tag_result.get('error', 'unknown error')
        logger.warning(f"  ✗ Tag removal failed: {err}")
        logger.warning("    The tag may not exist (already removed) or ShipStation is unavailable.")
        logger.warning("    Continuing with DB resolution — verify tag manually in ShipStation.")
        errors.append(f"tag_removal: {err}")

    today_str = date.today().isoformat()
    cf3_value = f"resolved:manual {today_str}"
    logger.info(f"Step 2: Stamping customField3 = '{cf3_value}' on SS order {SS_ORDER_ID} ...")
    cf3_result = update_order_custom_fields(
        SS_ORDER_ID,
        field1_value=None,
        skip_cf1=True,
        field3_value=cf3_value,
    )
    if cf3_result.get('success'):
        logger.info("  ✓ customField3 stamped successfully")
    else:
        err = cf3_result.get('error', 'unknown error')
        logger.warning(f"  ✗ customField3 stamp failed: {err}")
        logger.warning("    Continuing with DB resolution.")
        errors.append(f"cf3_stamp: {err}")

    logger.info("Step 3: Writing 'manually_resolved' log entry to promo_sku_replacement_log ...")
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO promo_sku_replacement_log
                (order_number, promo_sku, base_sku, status, error_reason, processed_at)
            SELECT %s, %s, %s, 'manually_resolved', %s, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM promo_sku_replacement_log
                WHERE order_number = %s
                  AND status = 'manually_resolved'
            )
        """, (
            ORDER_NUMBER, PROMO_SKU, BASE_SKU,
            f"manual resolve via scripts/resolve_order_862852.py on {today_str}",
            ORDER_NUMBER,
        ))
        if cursor.rowcount:
            logger.info("  ✓ 'manually_resolved' log entry written")
        else:
            logger.info("  ✓ 'manually_resolved' log entry already present — skipped")

        logger.info("Step 4: Marking lot_tagging_failures row resolved ...")
        cursor.execute("""
            UPDATE lot_tagging_failures
               SET resolved_at = NOW(),
                   resolved_by = 'task88_manual_resolve'
             WHERE order_number = %s
               AND resolved_at IS NULL
        """, (ORDER_NUMBER,))
        ltf_updated = cursor.rowcount
        if ltf_updated:
            logger.info(f"  ✓ {ltf_updated} lot_tagging_failures row(s) marked resolved")
        else:
            logger.info("  ✓ lot_tagging_failures row already resolved — skipped")

        conn.commit()
        conn.close()
        logger.info("  ✓ DB changes committed")

    except Exception as e:
        logger.error(f"  ✗ DB error: {e}", exc_info=True)
        errors.append(f"db: {e}")

    logger.info("=== Resolution complete ===")
    if errors:
        logger.warning(f"Completed with {len(errors)} non-fatal warning(s):")
        for err in errors:
            logger.warning(f"  - {err}")
        logger.warning("Verify ShipStation manually: SS order {SS_ORDER_ID} should have no Promo Hold tag.")
        sys.exit(0)
    else:
        logger.info("All steps succeeded. Order 862852 is fully resolved.")
        sys.exit(0)


if __name__ == '__main__':
    main()

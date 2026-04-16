#!/usr/bin/env python3
"""
Lot Tagger — Reconciliation Scheduler

Webhook-primary design: ShipStation fires ORDER_NOTIFY webhooks to the Flask app
when orders enter awaiting_shipment. This scheduler is the reliability backstop:
it runs twice daily to catch any orders missed by the webhook (server restarts,
ShipStation retry exhaustion, etc.).

Schedule: 6:00 AM and 12:00 PM CDT on business days.

Also registers the ORDER_NOTIFY webhook with ShipStation on startup (idempotent).
"""
import os
import sys
import time
import logging
import datetime
from pathlib import Path

import pytz

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.pg_utils import (
    get_connection, is_workflow_enabled, update_workflow_last_run, transaction_with_retry
)
from src.services.shipstation.api_client import (
    get_shipstation_credentials, get_shipstation_headers, register_order_notify_webhook
)
from src.lot_tagger.tagger import build_lot_maps, tag_order_lots, verify_tagging_results
from src.services.shipstation.promo_sku_handler import handle_promo_sku_order
from src.utils.server_logger import get_logger
from src.workflow_heartbeat import heartbeat, HeartbeatPhase
from utils.api_utils import make_api_request
from utils.business_hours import is_business_hours, get_sleep_until_business_hours, format_business_hours_status, is_dev_silent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
server_logger = get_logger()

WORKFLOW_NAME = 'lot-tagger'
SHIPSTATION_ORDERS_URL = 'https://ssapi.shipstation.com/orders'
CST = pytz.timezone('US/Central')

# Times at which the full reconciliation scan fires (CDT)
SCAN_TIMES = [
    datetime.time(6, 0),
    datetime.time(12, 0),
]
SCAN_WINDOW_MINUTES = 5


def _should_run_startup_catchup() -> bool:
    """
    Return True if the last successful reconciliation was more than 6 hours ago (or has
    never run), indicating a catch-up scan is needed immediately on startup.

    The threshold of 6 hours sits at the ~6-hour interval between the two
    scheduled scans (6:00 AM and 12:00 PM CDT), so a normal restart that immediately
    follows a completed scan will never trigger an unwanted duplicate run.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_run_at FROM workflow_controls WHERE workflow_name = %s",
            (WORKFLOW_NAME,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row or not row[0]:
            return True
        last_run = row[0]
        if last_run.tzinfo is None:
            last_run = pytz.UTC.localize(last_run)
        gap_hours = (datetime.datetime.now(pytz.UTC) - last_run).total_seconds() / 3600
        return gap_hours > 6
    except Exception as e:
        logger.warning(f"Could not check startup catch-up condition: {e}")
        return False


def _is_scan_time() -> bool:
    """Return True if current CDT time is within SCAN_WINDOW_MINUTES of a scheduled scan time."""
    now_cst = datetime.datetime.now(CST).time().replace(second=0, microsecond=0)
    for target in SCAN_TIMES:
        delta = abs(
            datetime.datetime.combine(datetime.date.today(), now_cst) -
            datetime.datetime.combine(datetime.date.today(), target)
        )
        if delta <= datetime.timedelta(minutes=SCAN_WINDOW_MINUTES):
            return True
    return False


def _fetch_awaiting_shipment_orders(api_key: str, api_secret: str) -> list:
    """Fetch all awaiting_shipment orders from ShipStation (paginated)."""
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    page = 1

    while True:
        response = make_api_request(
            url=SHIPSTATION_ORDERS_URL,
            method='GET',
            headers=headers,
            params={'orderStatus': 'awaiting_shipment', 'pageSize': 500, 'page': page},
            timeout=30
        )
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch orders page {page}: {response.status_code if response else 'no response'}")
            break

        data = response.json()
        orders = data.get('orders', [])
        all_orders.extend(orders)

        total_pages = data.get('pages', 1)
        logger.info(f"Fetched page {page}/{total_pages}: {len(orders)} orders")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)

    return all_orders


def run_reconciliation():
    """
    Fetch all awaiting_shipment orders and ensure every one is fully enriched:
    correct lot stamp, carrier, service, package code, and billing account.
    tag_order_lots() does a full-field comparison and only writes to ShipStation
    when one or more fields are missing or incorrect.

    Skip cache: orders confirmed clean on a previous sweep are skipped if
    ShipStation's modifyDate has not advanced and they have no unresolved
    lot_tagging_failures entry.  The cache is self-pruning — stale entries
    (orders no longer awaiting_shipment) are deleted at the start of each run.
    """
    server_logger.info("=" * 70, source="Lot Tagger")
    server_logger.info("LOT TAGGER RECONCILIATION STARTED", source="Lot Tagger")
    server_logger.info("=" * 70, source="Lot Tagger")

    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        server_logger.error("Failed to get ShipStation credentials — aborting.", source="Lot Tagger")
        return

    ss_headers = get_shipstation_headers(api_key, api_secret)
    all_orders = _fetch_awaiting_shipment_orders(api_key, api_secret)
    server_logger.info(f"Total awaiting_shipment orders retrieved: {len(all_orders)}", source="Lot Tagger")

    if not all_orders:
        server_logger.info("Lot tagger reconciliation: no awaiting_shipment orders found.", source="Lot Tagger")
        update_workflow_last_run(WORKFLOW_NAME)
        return

    processed = 0
    failed    = 0
    skipped   = 0

    with transaction_with_retry() as conn:
        current_order_ids = {int(o['orderId']) for o in all_orders if o.get('orderId')}

        # (a) Bulk-load unresolved LTF IDs — TEXT column, cast to int
        cur = conn.cursor()
        cur.execute(
            "SELECT shipstation_order_id FROM lot_tagging_failures WHERE resolved_at IS NULL"
        )
        unresolved_ltf_ids = {int(row[0]) for row in cur.fetchall()}
        cur.close()

        # (b) Load skip cache into {order_id_int: modify_date} dict
        cur = conn.cursor()
        cur.execute("SELECT shipstation_order_id, modify_date FROM reconciliation_skip_cache")
        skip_cache = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()

        # (c) Prune stale entries (orders no longer awaiting_shipment)
        stale_ids = [oid for oid in skip_cache if oid not in current_order_ids]
        if stale_ids:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM reconciliation_skip_cache WHERE shipstation_order_id = ANY(%s)",
                (stale_ids,)
            )
            cur.close()
            conn.commit()
            server_logger.info(
                f"[Skip Cache] Pruned {len(stale_ids)} stale entries.",
                source="Lot Tagger"
            )

        active_lots, known_skus = build_lot_maps(conn)
        server_logger.info(f"Active lots loaded: {len(active_lots)} SKUs | Known SKUs: {len(known_skus)}", source="Lot Tagger")

        for order in all_orders:
            original_order_id = order.get('orderId')
            order_id_int      = int(original_order_id) if original_order_id is not None else None
            modify_date       = order.get('modifyDate') or ''

            # (d) Skip check — confirmed clean + modifyDate unchanged + no LTF
            if (
                order_id_int is not None
                and order_id_int in skip_cache
                and skip_cache[order_id_int] == modify_date
                and order_id_int not in unresolved_ltf_ids
            ):
                skipped += 1
                continue

            try:
                order = handle_promo_sku_order(order, conn, ss_headers)
                tag_order_lots(order, active_lots, known_skus, conn)
                processed += 1

                # (e) Cache upsert — skip if replacement occurred or LTF unresolved
                returned_order_id = order.get('orderId')
                if returned_order_id != original_order_id:
                    server_logger.info(
                        f"[Skip Cache] Replacement detected: original SS ID {original_order_id} "
                        f"→ new SS ID {returned_order_id}. Not caching either order.",
                        source="Lot Tagger"
                    )
                else:
                    returned_id_int = int(returned_order_id) if returned_order_id is not None else None
                    if returned_id_int is not None and returned_id_int not in unresolved_ltf_ids:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO reconciliation_skip_cache
                                (shipstation_order_id, order_number, modify_date, confirmed_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (shipstation_order_id) DO UPDATE
                                SET modify_date  = EXCLUDED.modify_date,
                                    confirmed_at = EXCLUDED.confirmed_at
                        """, (returned_id_int, order.get('orderNumber'), modify_date))
                        cur.close()
                        conn.commit()

            except Exception as e:
                failed += 1
                server_logger.error(f"Error processing order {order.get('orderNumber')}: {e}", source="Lot Tagger")
                logger.error(f"Error processing order {order.get('orderNumber')}: {e}", exc_info=True)

        try:
            qa = verify_tagging_results(all_orders, active_lots, known_skus, conn)
            server_logger.info(
                f"QA: {qa['tagged_correctly']}/{qa['total_tracked']} tracked orders correct, "
                f"{qa['untagged_or_wrong']} untagged/wrong.",
                source="Lot Tagger"
            )
        except Exception as e:
            logger.error(f"QA verification failed: {e}", exc_info=True)

    update_workflow_last_run(WORKFLOW_NAME)

    summary = (
        f"Lot tagger reconciliation complete: {processed} processed, "
        f"{skipped} skipped (confirmed clean), {failed} errors, "
        f"{len(all_orders)} total awaiting shipment."
    )
    if failed > 0:
        server_logger.warning(summary, source="Lot Tagger")
    else:
        server_logger.info(summary, source="Lot Tagger")

    server_logger.info("=" * 70, source="Lot Tagger")
    server_logger.info(
        f"RECONCILIATION COMPLETE — {processed} processed, {skipped} skipped, {failed} errors",
        source="Lot Tagger"
    )
    server_logger.info("=" * 70, source="Lot Tagger")


def register_webhook_on_startup():
    """Register the ORDER_NOTIFY webhook with ShipStation (idempotent)."""
    # Never register from the dev workspace — prod always owns the ORDER_NOTIFY webhook.
    # Dev catches missed orders via the twice-daily reconciliation sweep instead.
    # This guard is unconditional: even DEV_WORKERS_ACTIVE=true does not override it.
    # REPLIT_DEPLOYMENT is set to '1' only in production containers (runtime-managed by
    # Replit, not overrideable by user-configured secrets). All other environments are dev.
    if os.getenv('REPLIT_DEPLOYMENT') != '1':
        logger.info("Dev workspace — skipping webhook registration (prod always owns the webhook).")
        return

    token = os.getenv('SHIPSTATION_WEBHOOK_TOKEN')
    if not token:
        logger.warning("SHIPSTATION_WEBHOOK_TOKEN not set — skipping webhook registration.")
        server_logger.warning(
            "SHIPSTATION_WEBHOOK_TOKEN not set. Webhook will not be registered. "
            "Generate a token with secrets.token_urlsafe(32), store it as SHIPSTATION_WEBHOOK_TOKEN, "
            "then restart this workflow.",
            source="Lot Tagger"
        )
        return

    domain = os.getenv('REPLIT_DOMAINS', '').split(',')[0].strip() or os.getenv('REPLIT_DEV_DOMAIN', '')
    if not domain:
        logger.warning("Could not determine public domain — skipping webhook registration.")
        return

    if 'picard.replit.dev' in domain:
        logger.error(
            f"WEBHOOK DOMAIN SANITY CHECK FAILED: resolved domain looks like a dev workspace URL "
            f"({domain}) but we are in a production container (REPLIT_DEPLOYMENT=1). "
            f"REPLIT_DOMAINS='{os.getenv('REPLIT_DOMAINS', '')}' "
            f"REPLIT_DEV_DOMAIN='{os.getenv('REPLIT_DEV_DOMAIN', '')}'. "
            f"Skipping webhook registration to avoid pointing ShipStation at the wrong server."
        )
        return

    target_url = f"https://{domain}/webhooks/shipstation/order/{token}"
    logger.info(f"Registering ORDER_NOTIFY webhook to production domain: {domain}")
    result = register_order_notify_webhook(target_url)

    if result.get('success'):
        if result.get('already_exists'):
            server_logger.info(f"ORDER_NOTIFY webhook already registered.", source="Lot Tagger")
        else:
            server_logger.info(f"ORDER_NOTIFY webhook registered successfully.", source="Lot Tagger")
    else:
        server_logger.error(
            f"Failed to register ORDER_NOTIFY webhook: {result.get('error')}",
            source="Lot Tagger"
        )


def main():
    logger.info("Lot Tagger scheduler starting...")
    logger.info("Schedule: 6:00 AM and 12:00 PM CDT on business days")

    try:
        register_webhook_on_startup()
    except Exception as e:
        logger.warning(f"Webhook registration failed on startup (will retry next run): {e}")

    is_production = os.getenv('REPLIT_DEPLOYMENT') == '1'
    if not is_dev_silent() and (is_production or _should_run_startup_catchup()):
        reason = "production redeploy" if is_production else "last run was over 6 hours ago"
        logger.info(f"Startup reconciliation triggered: {reason}.")
        server_logger.info(
            f"Startup reconciliation triggered: {reason}.",
            source="Lot Tagger"
        )
        try:
            run_reconciliation()
        except Exception as e:
            logger.error(f"Startup catch-up reconciliation error: {e}", exc_info=True)

    last_scan_minute = None

    while True:
        try:
            if is_dev_silent():
                logger.debug("DEV SILENT MODE — set DEV_WORKERS_ACTIVE=true in Secrets to enable.")
                time.sleep(60)
                continue

            if not is_business_hours():
                status = format_business_hours_status()
                logger.info(status)
                sleep_duration = get_sleep_until_business_hours()
                logger.info(f"Sleeping {sleep_duration}s until business hours")
                time.sleep(sleep_duration)
                continue

            if not is_workflow_enabled(WORKFLOW_NAME):
                logger.info(f"Workflow '{WORKFLOW_NAME}' is DISABLED — sleeping 60s")
                time.sleep(60)
                continue

            # Time-of-day gate: only run at 6:00 AM or 12:00 PM CDT (within 5 min window)
            now_minute = datetime.datetime.now(CST).strftime('%H:%M')
            if _is_scan_time() and now_minute != last_scan_minute:
                last_scan_minute = now_minute
                heartbeat(WORKFLOW_NAME, HeartbeatPhase.STARTED)
                try:
                    run_reconciliation()
                    heartbeat(WORKFLOW_NAME, HeartbeatPhase.COMPLETED)
                except Exception as e:
                    heartbeat(WORKFLOW_NAME, HeartbeatPhase.ERROR, details={'error': str(e)[:200]})
                    logger.error(f"Reconciliation error: {e}", exc_info=True)
            else:
                logger.debug(f"Not a scan time ({now_minute} CT) — sleeping 60s")

            time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Lot tagger stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            time.sleep(60)


def run_once():
    """Run a single reconciliation pass (for manual triggers / testing)."""
    logger.info("Running one-time lot tagger reconciliation (manual trigger)")
    run_reconciliation()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        run_once()
    else:
        main()

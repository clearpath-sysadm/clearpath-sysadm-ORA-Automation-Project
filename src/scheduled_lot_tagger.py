#!/usr/bin/env python3
"""
Lot Tagger — Reconciliation Scheduler

Webhook-primary design: ShipStation fires ORDER_NOTIFY webhooks to the Flask app
when orders enter awaiting_shipment. This scheduler is the reliability backstop:
it runs twice daily to catch any orders missed by the webhook (server restarts,
ShipStation retry exhaustion, etc.).

Schedule: 6:30 AM and 12:00 PM CT on business days.

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

# Times at which the full reconciliation scan fires (CT)
SCAN_TIMES = [
    datetime.time(6, 30),
    datetime.time(12, 0),
]
SCAN_WINDOW_MINUTES = 5


def _should_run_startup_catchup() -> bool:
    """
    Return True if the last successful reconciliation was more than 6 hours ago (or has
    never run), indicating a catch-up scan is needed immediately on startup.

    The threshold of 6 hours sits safely above the ~5.5-hour interval between the two
    scheduled scans (6:30 AM and 12:00 PM CT), so a normal restart that immediately
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
    """Return True if current CT time is within SCAN_WINDOW_MINUTES of a scheduled scan time."""
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
    """
    logger.info("=" * 70)
    logger.info("LOT TAGGER RECONCILIATION STARTED")
    logger.info("=" * 70)

    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("Failed to get ShipStation credentials — aborting.")
        return

    all_orders = _fetch_awaiting_shipment_orders(api_key, api_secret)
    logger.info(f"Total awaiting_shipment orders retrieved: {len(all_orders)}")

    if not all_orders:
        server_logger.info("Lot tagger reconciliation: no awaiting_shipment orders found.", source="Lot Tagger")
        update_workflow_last_run(WORKFLOW_NAME)
        return

    processed = 0
    failed = 0

    with transaction_with_retry() as conn:
        active_lots, known_skus = build_lot_maps(conn)
        logger.info(f"Active lots loaded: {len(active_lots)} SKUs | Known SKUs: {len(known_skus)}")

        for order in all_orders:
            try:
                tag_order_lots(order, active_lots, known_skus, conn)
                processed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Error processing order {order.get('orderNumber')}: {e}", exc_info=True)

        try:
            qa = verify_tagging_results(all_orders, active_lots, known_skus, conn)
            logger.info(
                f"QA: {qa['tagged_correctly']}/{qa['total_tracked']} tracked orders correct, "
                f"{qa['untagged_or_wrong']} untagged/wrong."
            )
        except Exception as e:
            logger.error(f"QA verification failed: {e}", exc_info=True)

    update_workflow_last_run(WORKFLOW_NAME)

    summary = (
        f"Lot tagger reconciliation complete: {processed} orders checked, "
        f"{failed} errors, {len(all_orders)} total awaiting shipment."
    )
    if failed > 0:
        server_logger.warning(summary, source="Lot Tagger")
    else:
        server_logger.info(summary, source="Lot Tagger")

    logger.info("=" * 70)
    logger.info(f"RECONCILIATION COMPLETE — {processed} checked, {failed} errors")
    logger.info("=" * 70)


def register_webhook_on_startup():
    """Register the ORDER_NOTIFY webhook with ShipStation (idempotent)."""
    # Never register from the dev workspace — prod always owns the ORDER_NOTIFY webhook.
    # Dev catches missed orders via the twice-daily reconciliation sweep instead.
    # This guard is unconditional: even DEV_WORKERS_ACTIVE=true does not override it.
    repl_slug = os.getenv('REPL_SLUG', '').lower()
    if 'workspace' in repl_slug:
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

    domain = os.getenv('REPLIT_DEV_DOMAIN') or os.getenv('REPLIT_DOMAINS', '').split(',')[0].strip()
    if not domain:
        logger.warning("Could not determine public domain — skipping webhook registration.")
        return

    target_url = f"https://{domain}/webhooks/shipstation/order/{token}"
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
    logger.info("Schedule: 6:30 AM and 12:00 PM CT on business days")

    register_webhook_on_startup()

    if not is_dev_silent() and _should_run_startup_catchup():
        logger.info("Startup catch-up: last run was over 6 hours ago — running reconciliation now.")
        server_logger.info(
            "Startup catch-up scan triggered (last successful run was over 6 hours ago).",
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

            # Time-of-day gate: only run at 6:30 AM or 12:00 PM CST (within 5 min window)
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

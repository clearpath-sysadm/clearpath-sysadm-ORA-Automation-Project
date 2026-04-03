#!/usr/bin/env python3
"""
LOT NUMBER MISMATCH SCANNER
Scans awaiting_shipment ShipStation orders and compares customField1
(format: 'SKU - LOT') against the current FIFO active lot in the local database.

An alert is raised when:
  - customField1 is non-empty AND
  - the lot in customField1 differs from the expected FIFO active lot

Orders with an empty customField1 are skipped (lot tagger job, not mismatch scanner).

Safety Design: Manual-only resolution to prevent data loss.
"""

import os
import sys
import time
import logging
import datetime
from typing import Dict
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.pg_utils import transaction_with_retry, is_workflow_enabled, update_workflow_last_run
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from src.lot_tagger.tagger import build_lot_maps
from src.utils.server_logger import get_logger
from src.workflow_heartbeat import heartbeat, HeartbeatPhase
from utils.api_utils import make_api_request
from utils.business_hours import is_business_hours, get_sleep_until_business_hours, format_business_hours_status

server_logger = get_logger()
SHIPSTATION_ORDERS_ENDPOINT = 'https://ssapi.shipstation.com/orders'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WORKFLOW_NAME = "lot-mismatch-scanner"


def scan_for_lot_mismatches(api_key: str, api_secret: str):
    """
    Scan ShipStation awaiting_shipment orders for lot number mismatches.

    Reads customField1 (format: 'SKU - LOT') and compares against the FIFO active
    lot for that SKU. Raises alerts when they differ. Orders with empty customField1
    are silently skipped — those are the lot tagger's responsibility.
    """
    logger.info("=" * 80)
    logger.info("LOT MISMATCH SCANNER STARTED")
    logger.info("=" * 80)

    scan_start = datetime.datetime.now()

    try:
        with transaction_with_retry() as conn:
            active_lots, _ = build_lot_maps(conn)
            logger.info(f"Active lots (FIFO): {len(active_lots)} SKUs")

            if active_lots:
                lots_detail = ', '.join([f"{sku}={lot}" for sku, lot in active_lots.items()])
                server_logger.info(f"Lot mismatch scanner using active lots (FIFO): {lots_detail}", source="Lot Mismatch")
            else:
                server_logger.warning("Lot mismatch scanner: No active lots found!", source="Lot Mismatch")

            lookback_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            params = {
                'orderStatus': 'awaiting_shipment',
                'modifyDateStart': lookback_date,
                'pageSize': 500
            }

            logger.info(f"Fetching orders modified since {lookback_date}")

            all_orders = []
            page = 1
            headers = get_shipstation_headers(api_key, api_secret)

            while True:
                params['page'] = page
                response = make_api_request(
                    url=SHIPSTATION_ORDERS_ENDPOINT,
                    method='GET',
                    headers=headers,
                    params=params,
                    timeout=30
                )

                if not response or response.status_code != 200:
                    logger.error(f"ShipStation API error on page {page}: {response.status_code if response else 'no response'}")
                    break

                data = response.json()
                if not data or 'orders' not in data:
                    break

                orders = data['orders']
                all_orders.extend(orders)

                total_pages = data.get('pages', 1)
                logger.info(f"Page {page}/{total_pages}: {len(orders)} orders")

                if page >= total_pages:
                    break

                page += 1
                time.sleep(0.5)

            logger.info(f"Retrieved {len(all_orders)} total awaiting_shipment orders")

            mismatches_found = 0
            mismatches_created = 0
            cursor = conn.cursor()

            for order in all_orders:
                order_number = order.get('orderNumber', '').strip()
                order_id = order.get('orderId')
                order_status = order.get('orderStatus', '').lower()

                # Read customField1 at the order level — lot tagger writes 'SKU - LOT' here
                cf1 = ((order.get('advancedOptions') or {}).get('customField1') or '').strip()

                # Skip orders with empty customField1 — lot tagger hasn't run yet (not a mismatch)
                if not cf1:
                    continue

                # Loop through items to get the tracked SKU for this order.
                # Auto-split ensures one tracked SKU per order; we stop at the first match.
                for item in (order.get('items') or []):
                    base_sku = item.get('sku', '').strip()

                    # Skip untracked SKUs (not in active lots dict, which is built from the skus JOIN)
                    if base_sku not in active_lots:
                        continue

                    expected = f"{base_sku} - {active_lots[base_sku]}"

                    if cf1 == expected:
                        break  # Correct — no mismatch for this order

                    # Mismatch detected — extract the lot number from customField1 ('SKU - LOT')
                    cf1_lot = cf1.split(' - ', 1)[1] if ' - ' in cf1 else cf1

                    mismatches_found += 1
                    mismatch_msg = (
                        f"Lot mismatch: Order {order_number} (SS ID: {order_id}), SKU {base_sku} — "
                        f"customField1 is '{cf1}' but expected '{expected}'"
                    )
                    logger.warning(mismatch_msg)
                    server_logger.warning(mismatch_msg, source="Lot Mismatch")

                    cursor.execute("""
                        INSERT INTO lot_mismatch_alerts (
                            order_number,
                            base_sku,
                            shipstation_lot,
                            active_lot,
                            shipstation_order_id,
                            order_status,
                            detected_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (shipstation_order_id) DO UPDATE
                            SET shipstation_lot = EXCLUDED.shipstation_lot,
                                active_lot = EXCLUDED.active_lot,
                                order_status = EXCLUDED.order_status,
                                detected_at = CURRENT_TIMESTAMP
                            WHERE lot_mismatch_alerts.resolved_at IS NULL
                    """, (
                        order_number,
                        base_sku,
                        cf1_lot,
                        active_lots[base_sku],
                        str(order_id),
                        order_status
                    ))

                    if cursor.rowcount > 0:
                        mismatches_created += 1

                    break  # One tracked SKU per order (auto-split); stop after first match

            # Auto-resolve alerts for orders that no longer appear in the scan
            # (e.g., order shipped, or lot corrected)
            cursor.execute("""
                UPDATE lot_mismatch_alerts
                SET resolved_at = CURRENT_TIMESTAMP,
                    resolved_by = 'auto'
                WHERE resolved_at IS NULL
                  AND detected_at < %s
            """, (scan_start,))

            auto_resolved = cursor.rowcount

        update_workflow_last_run(WORKFLOW_NAME)

        elapsed = (datetime.datetime.now() - scan_start).total_seconds()

        logger.info("=" * 80)
        logger.info("SCAN SUMMARY:")
        logger.info(f"   Lot mismatches found: {mismatches_found}")
        logger.info(f"   New/updated alerts: {mismatches_created}")
        logger.info(f"   Auto-resolved: {auto_resolved}")
        logger.info(f"   Duration: {elapsed:.1f}s")
        logger.info("=" * 80)

        if mismatches_found > 0:
            server_logger.warning(
                f"Lot mismatch scan complete: {mismatches_found} mismatches found, "
                f"{mismatches_created} alerts created/updated, {auto_resolved} auto-resolved ({elapsed:.1f}s)",
                source="Lot Mismatch"
            )
        else:
            server_logger.info(
                f"Lot mismatch scan complete: No mismatches found, "
                f"{auto_resolved} auto-resolved ({elapsed:.1f}s)",
                source="Lot Mismatch"
            )

    except Exception as e:
        logger.error(f"Error scanning for lot mismatches: {e}", exc_info=True)


def main():
    """Main loop — runs every 15 minutes during business hours (Mon-Fri 6 AM - 6 PM CT)."""
    logger.info("Starting Lot Mismatch Scanner (every 900s)")
    logger.info("Business Hours: Monday-Friday 6 AM - 6 PM CT | Weekends OFF")

    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.critical("Failed to get ShipStation credentials")
        return

    while True:
        try:
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

            heartbeat(WORKFLOW_NAME, HeartbeatPhase.STARTED)
            server_logger.info("Lot mismatch scanner workflow started", source="Scheduler")
            scan_for_lot_mismatches(api_key, api_secret)
            heartbeat(WORKFLOW_NAME, HeartbeatPhase.COMPLETED)
            server_logger.info("Lot mismatch scanner workflow completed", source="Scheduler")

            logger.info("Next scan in 900 seconds (15 minutes)")
            time.sleep(900)

        except KeyboardInterrupt:
            logger.info("Lot mismatch scanner stopped by user")
            break
        except Exception as e:
            heartbeat(WORKFLOW_NAME, HeartbeatPhase.ERROR, details={'error': str(e)[:200]})
            logger.error(f"Error in main loop: {e}", exc_info=True)
            logger.info("Retrying in 60 seconds after error")
            time.sleep(60)


def run_once():
    """Run a single scan cycle and exit (for manual triggers)."""
    logger.info("Running one-time lot mismatch scan (manual trigger mode)")

    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.critical("Failed to get ShipStation credentials")
            return

        if not is_workflow_enabled(WORKFLOW_NAME):
            logger.warning(f"Workflow '{WORKFLOW_NAME}' is DISABLED")
            return

        scan_for_lot_mismatches(api_key, api_secret)
        logger.info("One-time lot mismatch scan complete")

    except Exception as e:
        logger.error(f"Error in one-time scan: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        run_once()
    else:
        main()

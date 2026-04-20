#!/usr/bin/env python3
"""
Batch Processor — Noon CT Batch Creation

Runs once per business day at 12:00 PM CT. Fetches all pending Axiom shipments
from ShipStation V2 and bundles them into a batch. Labels are NOT created
automatically — print them from within ShipStation after the batch is ready.

Schedule: 12:00 PM CT on business days.

Dev-safety: Batching is blocked in workspace (REPL_SLUG contains 'workspace')
unless ALLOW_DEV_UPLOAD=true is set in Secrets.
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

from src.services.database.pg_utils import is_workflow_enabled, update_workflow_last_run, get_connection
from src.services.shipstation.api_client import (
    v2_get_pending_axiom_shipments,
    v2_create_batch,
)
from src.utils.server_logger import get_logger
from src.workflow_heartbeat import heartbeat, HeartbeatPhase
from utils.business_hours import is_business_hours, get_sleep_until_business_hours, format_business_hours_status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
server_logger = get_logger()

WORKFLOW_NAME = 'batch-processor'
CST = pytz.timezone('US/Central')
BATCH_TIME = datetime.time(12, 0)
BATCH_WINDOW_MINUTES = 5


def _is_batch_time() -> bool:
    """Return True if CT time is within BATCH_WINDOW_MINUTES of 12:00 PM."""
    now_ct = datetime.datetime.now(CST).time().replace(second=0, microsecond=0)
    delta = abs(
        datetime.datetime.combine(datetime.date.today(), now_ct) -
        datetime.datetime.combine(datetime.date.today(), BATCH_TIME)
    )
    return delta <= datetime.timedelta(minutes=BATCH_WINDOW_MINUTES)


def _is_dev_blocked() -> bool:
    """Return True if running in a dev workspace and neither DEV_WORKERS_ACTIVE
    nor ALLOW_DEV_UPLOAD is set to 'true'."""
    repl_slug = os.getenv('REPL_SLUG', '').lower()
    environment = os.getenv('ENVIRONMENT', '').lower()
    allow_dev = (
        os.getenv('DEV_WORKERS_ACTIVE', '').lower() == 'true'
        or os.getenv('ALLOW_DEV_UPLOAD', '').lower() == 'true'
    )

    if 'workspace' in repl_slug:
        is_dev = True
    elif environment == 'production':
        is_dev = False
    else:
        is_dev = True

    return is_dev and not allow_dev


def _already_batched_today(today_str: str) -> bool:
    """Return True if a batch was already created today (CT date), checked via DB.
    Fails open (returns False) on DB errors so a genuine first run is never blocked."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM configuration_params "
            "WHERE category = 'BatchProcessor' AND parameter_name = 'last_batch_date' AND sku = ''",
        )
        row = cursor.fetchone()
        conn.close()
        return bool(row and row[0] == today_str)
    except Exception as e:
        logger.warning(f"Could not read last_batch_date from DB (failing open): {e}")
        return False


def _record_batch_run(today_str: str, batch_id: str) -> bool:
    """Persist today's batch date to configuration_params so restarts skip re-firing.
    Returns True on success, False on failure. Callers should treat False as an error
    to prevent silent duplicate-batch risk on future restarts."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO configuration_params (category, parameter_name, sku, value, notes, last_updated)
            VALUES ('BatchProcessor', 'last_batch_date', '', %s, %s, NOW()::text)
            ON CONFLICT (category, parameter_name, sku)
            DO UPDATE SET value = EXCLUDED.value, notes = EXCLUDED.notes, last_updated = NOW()::text
            """,
            (today_str, f"batch_id={batch_id}"),
        )
        conn.commit()
        conn.close()
        logger.info(f"Recorded batch run: date={today_str}, batch_id={batch_id}")
        return True
    except Exception as e:
        logger.error(f"CRITICAL: Could not persist last_batch_date to DB after batch creation — "
                     f"duplicate batch risk on restart: {e}")
        return False


def run_batch_job() -> str:
    """
    Fetch all pending Axiom shipments, create a V2 batch, and trigger label processing.
    Logs results to the server logger for visibility in the dashboard.

    Returns one of:
        'completed' — batch created and labels triggered successfully
        'skipped'   — no pending Axiom shipments; nothing to do OR already ran today
        'blocked'   — running in dev workspace and upload not enabled
        'error'     — an API call failed (details already logged)
    """
    today_ct = datetime.datetime.now(CST)
    ship_date = today_ct.strftime('%Y-%m-%d')

    logger.info("=" * 70)
    logger.info("BATCH PROCESSOR STARTED")
    logger.info(f"Ship date: {ship_date}")
    logger.info("=" * 70)

    if _is_dev_blocked():
        logger.warning("=" * 70)
        logger.warning("BATCH PROCESSOR BLOCKED — running in development/workspace")
        logger.warning("Set ALLOW_DEV_UPLOAD=true in Secrets to override (use with caution)")
        logger.warning("=" * 70)
        server_logger.warning(
            "Batch processor blocked: running in workspace environment.",
            source="Batch Processor"
        )
        return 'blocked'

    if _already_batched_today(ship_date):
        logger.info(f"Batch already created today ({ship_date}) — skipping to prevent duplicates.")
        server_logger.info(
            f"Batch processor: already ran today ({ship_date}). Skipping duplicate run.",
            source="Batch Processor"
        )
        return 'skipped_duplicate'

    result = v2_get_pending_axiom_shipments()
    if not result.get('success'):
        error = result.get('error', 'unknown error')
        logger.error(f"Failed to fetch pending shipments: {error}")
        server_logger.error(
            f"Batch processor failed to fetch pending shipments: {error}",
            source="Batch Processor"
        )
        return 'error'

    shipment_ids = result['shipment_ids']

    if not shipment_ids:
        logger.info("No pending Axiom shipments — nothing to batch.")
        server_logger.info(
            "Batch processor: no pending Axiom shipments found. Nothing to batch.",
            source="Batch Processor"
        )
        update_workflow_last_run(WORKFLOW_NAME)
        return 'skipped'

    logger.info(f"Found {len(shipment_ids)} pending Axiom shipment(s) — creating batch...")

    batch_result = v2_create_batch(shipment_ids)
    if not batch_result.get('success'):
        error = batch_result.get('error', 'unknown error')
        logger.error(f"Failed to create batch: {error}")
        server_logger.error(
            f"Batch processor failed to create batch ({len(shipment_ids)} shipments): {error}",
            source="Batch Processor"
        )
        return 'error'

    batch_id = batch_result['batch_id']
    confirmed_count = batch_result.get('shipment_count', len(shipment_ids))
    if confirmed_count == 0:
        logger.warning(
            f"Batch {batch_id} created but API reports 0 shipments — "
            f"payload may have been rejected silently. Requested: {len(shipment_ids)}."
        )
        server_logger.warning(
            f"Batch {batch_id} created with 0 shipments (requested {len(shipment_ids)}) — "
            f"investigate API payload or ShipStation configuration.",
            source="Batch Processor"
        )

    if not _record_batch_run(ship_date, batch_id):
        server_logger.error(
            f"Batch {batch_id} created but could not persist run date to DB. "
            f"Restarting within the noon window may create a duplicate batch.",
            source="Batch Processor"
        )
        return 'error'

    update_workflow_last_run(WORKFLOW_NAME)
    summary = (
        f"Batch processor complete: batch {batch_id} created with "
        f"{len(shipment_ids)} shipment(s). Labels not created — print from ShipStation."
    )
    logger.info("=" * 70)
    logger.info(f"BATCH PROCESSOR COMPLETE — {len(shipment_ids)} shipments, batch {batch_id}")
    logger.info("=" * 70)
    server_logger.info(summary, source="Batch Processor")
    return 'completed'


def main():
    logger.info("Batch Processor scheduler starting...")
    logger.info("Schedule: 12:00 PM CT on business days")

    if _is_dev_blocked():
        logger.warning("=" * 80)
        logger.warning("BATCH PROCESSOR DISABLED IN DEVELOPMENT ENVIRONMENT")
        logger.warning("Set ALLOW_DEV_UPLOAD=true in Secrets to enable.")
        logger.warning("=" * 80)
        while True:
            time.sleep(3600)

    last_batch_minute = None

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
                logger.debug(f"Workflow '{WORKFLOW_NAME}' is DISABLED — sleeping 60s")
                time.sleep(60)
                continue

            now_minute = datetime.datetime.now(CST).strftime('%H:%M')
            if _is_batch_time() and now_minute != last_batch_minute:
                last_batch_minute = now_minute
                heartbeat(WORKFLOW_NAME, HeartbeatPhase.STARTED)
                try:
                    status = run_batch_job()
                    if status == 'skipped':
                        heartbeat(WORKFLOW_NAME, HeartbeatPhase.SKIPPED, details={'reason': 'no_pending_shipments'})
                    elif status == 'skipped_duplicate':
                        heartbeat(WORKFLOW_NAME, HeartbeatPhase.SKIPPED, details={'reason': 'already_ran_today'})
                    elif status == 'error':
                        heartbeat(WORKFLOW_NAME, HeartbeatPhase.ERROR, details={'reason': 'api_call_failed'})
                    else:
                        heartbeat(WORKFLOW_NAME, HeartbeatPhase.COMPLETED)
                except Exception as e:
                    heartbeat(WORKFLOW_NAME, HeartbeatPhase.ERROR, details={'error': str(e)[:200]})
                    logger.error(f"Batch job error: {e}", exc_info=True)
                    server_logger.error(
                        f"Batch processor encountered an unexpected error: {e}",
                        source="Batch Processor"
                    )
            else:
                logger.debug(f"Not batch time ({now_minute} CT) — sleeping 60s")

            time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Batch processor stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            time.sleep(60)


def run_once():
    """Run a single batch job and exit (for manual triggers / testing)."""
    logger.info("Running one-time batch job (manual trigger)")
    run_batch_job()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        run_once()
    else:
        main()

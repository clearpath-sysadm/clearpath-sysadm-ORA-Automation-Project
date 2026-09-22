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
import json
from pathlib import Path

import pytz

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.pg_utils import is_workflow_enabled, update_workflow_last_run, get_connection
from src.services.shipstation.api_client import (
    v2_get_pending_axiom_shipments,
    v2_create_batch,
    v2_get_batch,
    v2_get_batch_by_external_id,
    v2_get_shipment_batch_assignments,
    v2_get_batch_shipment_ids,
    v2_delete_batch,
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
RECOVERY_START_TIME = datetime.time(12, 10)
RECOVERY_END_TIME = datetime.time(12, 30)
RECOVERY_LOOKBACK_MINUTES = 15
BATCH_LOCK_KEY = 0x4F524142  # Stable "ORAB" key; never use Python's randomized hash().
RECONCILE_DELAY_SECONDS = 15 * 60
EMPTY_BATCH_CLEANUP_ENABLED = (
    os.getenv('SHIPSTATION_EMPTY_BATCH_CLEANUP_ENABLED', '').lower() == 'true'
)


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
    nor ALLOW_DEV_UPLOAD is set to 'true'.

    REPLIT_DEPLOYMENT is set by Replit only in deployed production VMs — it is
    the authoritative production signal. Without it the process is treated as
    dev and blocked unless explicitly opted in."""
    if os.getenv('REPLIT_DEPLOYMENT'):
        return False  # definitively in a production deployment

    allow_dev = (
        os.getenv('DEV_WORKERS_ACTIVE', '').lower() == 'true'
        or os.getenv('ALLOW_DEV_UPLOAD', '').lower() == 'true'
    )
    return not allow_dev


def _had_started_heartbeat_within(minutes: int) -> bool:
    """Return True if a STARTED heartbeat was recorded for this workflow within
    the last `minutes` minutes. Fails closed (returns True) on DB errors to
    avoid triggering a spurious recovery run."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1 FROM workflow_heartbeats
            WHERE workflow_name = %s
              AND execution_phase = 'started'
              AND heartbeat_at >= NOW() - (%s * INTERVAL '1 minute')
            LIMIT 1
            """,
            (WORKFLOW_NAME, minutes),
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        logger.warning(f"Could not check recent heartbeats (failing closed): {e}")
        return True  # fail closed — don't trigger recovery if we can't verify


def _run_with_heartbeat(label: str = '') -> None:
    """Run run_batch_job() wrapped with STARTED/terminal heartbeats.
    label is an optional log prefix (e.g. 'recovery')."""
    heartbeat(WORKFLOW_NAME, HeartbeatPhase.STARTED)
    prefix = f"{label} " if label else ""
    _run_ok = False
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
        _run_ok = status not in ('error',)
    except Exception as e:
        heartbeat(WORKFLOW_NAME, HeartbeatPhase.ERROR, details={'error': str(e)[:200]})
        logger.error(f"Batch {prefix}job error: {e}", exc_info=True)
        server_logger.error(
            f"Batch processor {prefix}encountered an unexpected error: {e}",
            source="Batch Processor"
        )
    finally:
        _terminal = "SUCCESS" if _run_ok else "FAILED"
        logger.info(f"[{WORKFLOW_NAME}] {prefix}run complete — {_terminal}")


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


def _record_batch_run(
    today_str: str,
    batch_id: str,
    external_batch_id: str,
    shipment_ids: list,
) -> bool:
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
        cursor.execute(
            """
            INSERT INTO shipstation_batch_runs
                (ship_date, external_batch_id, source_batch_id, shipment_ids, status, updated_at)
            VALUES (%s, %s, %s, %s::jsonb, 'created', NOW())
            ON CONFLICT (ship_date) DO UPDATE SET
                external_batch_id = EXCLUDED.external_batch_id,
                source_batch_id = EXCLUDED.source_batch_id,
                shipment_ids = EXCLUDED.shipment_ids,
                replacement_batch_id = NULL,
                status = 'created',
                verified_at = NULL,
                reconciled_at = NULL,
                updated_at = NOW()
            """,
            (today_str, external_batch_id, batch_id, json.dumps(shipment_ids)),
        )
        conn.commit()
        conn.close()
        logger.info(f"Recorded batch run: date={today_str}, batch_id={batch_id}")
        return True
    except Exception as e:
        logger.error(f"CRITICAL: Could not persist last_batch_date to DB after batch creation — "
                     f"duplicate batch risk on restart: {e}")
        return False


def _ensure_batch_run_storage() -> bool:
    """Ensure the independent worker can start safely before the web app."""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shipstation_batch_runs (
                    ship_date DATE PRIMARY KEY,
                    external_batch_id TEXT NOT NULL UNIQUE,
                    source_batch_id TEXT,
                    replacement_batch_id TEXT,
                    shipment_ids JSONB NOT NULL,
                    status TEXT NOT NULL DEFAULT 'created',
                    verified_at TIMESTAMPTZ,
                    last_observed_at TIMESTAMPTZ,
                    reconciled_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cursor.execute(
                "ALTER TABLE shipstation_batch_runs ALTER COLUMN source_batch_id DROP NOT NULL"
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Batch safety storage is unavailable; refusing to create: {e}")
        return False


def _claim_batch_run(today_str: str, external_batch_id: str, shipment_ids: list) -> bool:
    """Atomically claim the date before the non-idempotent ShipStation POST."""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO shipstation_batch_runs
                    (ship_date, external_batch_id, shipment_ids, status)
                VALUES (%s, %s, %s::jsonb, 'creating')
                ON CONFLICT (ship_date) DO NOTHING
                """,
                (today_str, external_batch_id, json.dumps(shipment_ids)),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                conn.close()
                return False
            cursor.execute(
                """
                INSERT INTO configuration_params
                    (category, parameter_name, sku, value, notes, last_updated)
                VALUES ('BatchProcessor', 'last_batch_date', '', %s, %s, NOW()::text)
                ON CONFLICT (category, parameter_name, sku)
                DO UPDATE SET value = EXCLUDED.value,
                              notes = EXCLUDED.notes,
                              last_updated = NOW()::text
                """,
                (today_str, f"creating_external_id={external_batch_id}"),
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Could not claim daily batch creation: {e}", exc_info=True)
        return False


def _clear_definite_failed_claim(today_str: str, external_batch_id: str) -> None:
    """Release a claim only after a definite HTTP rejection (never ambiguity)."""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM shipstation_batch_runs
                WHERE ship_date = %s AND external_batch_id = %s
                  AND status = 'creating' AND source_batch_id IS NULL
                """,
                (today_str, external_batch_id),
            )
            if cursor.rowcount:
                cursor.execute(
                    """
                    UPDATE configuration_params
                    SET value = '', notes = 'definite_create_failure', last_updated = NOW()::text
                    WHERE category = 'BatchProcessor'
                      AND parameter_name = 'last_batch_date' AND sku = ''
                      AND value = %s
                    """,
                    (today_str,),
                )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Could not clear definite failed batch claim: {e}", exc_info=True)


def _get_claimed_shipment_ids(today_str: str) -> list:
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT shipment_ids FROM shipstation_batch_runs WHERE ship_date = %s",
                (today_str,),
            )
            row = cursor.fetchone()
        conn.close()
        return list(row[0]) if row else []
    except Exception as e:
        logger.error(f"Could not read claimed batch membership: {e}", exc_info=True)
        return []


def _get_batch_run_status(today_str: str):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM shipstation_batch_runs WHERE ship_date = %s",
                (today_str,),
            )
            row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Could not read batch run status: {e}", exc_info=True)
        return None


def _mark_batch_verified(today_str: str) -> None:
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE shipstation_batch_runs
                SET status = 'verified', verified_at = NOW(), updated_at = NOW()
                WHERE ship_date = %s
                """,
                (today_str,),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Could not record verified batch state: {e}", exc_info=True)


def _acquire_batch_lock():
    """Acquire the cross-process creation lock; fail closed on DB errors."""
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (BATCH_LOCK_KEY,))
            acquired = bool(cursor.fetchone()[0])
        if acquired:
            return conn
        conn.close()
        return None
    except Exception as e:
        logger.error(f"Could not acquire batch creation lock; refusing to create: {e}")
        return None


def _release_batch_lock(conn) -> None:
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", (BATCH_LOCK_KEY,))
    finally:
        conn.close()


def _set_reconciliation_state(
    ship_date,
    status,
    replacement_batch_id=None,
    update_daily_record=False,
):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE shipstation_batch_runs
                SET status = %s,
                    replacement_batch_id = COALESCE(%s, replacement_batch_id),
                    last_observed_at = NOW(),
                    reconciled_at = CASE WHEN %s IN ('observed_empty','retired') THEN NOW() ELSE reconciled_at END,
                    updated_at = NOW()
                WHERE ship_date = %s
                """,
                (status, replacement_batch_id, status, ship_date),
            )
            if update_daily_record and replacement_batch_id:
                cursor.execute(
                    """
                    UPDATE configuration_params
                    SET notes = %s, last_updated = NOW()::text
                    WHERE category = 'BatchProcessor'
                      AND parameter_name = 'last_batch_date' AND sku = ''
                      AND value = %s
                    """,
                    (
                        f"batch_id={replacement_batch_id}; replaced_empty_source=true",
                        str(ship_date),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def _reconcile_recent_batches() -> None:
    """Observe verified batches after creation; never block daily batch creation."""
    try:
        statuses = ('verified', 'observed_empty') if EMPTY_BATCH_CLEANUP_ENABLED else ('verified',)
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ship_date, external_batch_id, source_batch_id, shipment_ids,
                       status, replacement_batch_id
                FROM shipstation_batch_runs
                WHERE status = ANY(%s)
                  AND (
                      (status = 'verified'
                       AND verified_at <= NOW() - (%s * INTERVAL '1 second'))
                      OR
                      (status = 'observed_empty'
                       AND last_observed_at <= NOW() - (%s * INTERVAL '1 second'))
                  )
                ORDER BY verified_at
                LIMIT 1
                """,
                (
                    list(statuses),
                    RECONCILE_DELAY_SECONDS,
                    RECONCILE_DELAY_SECONDS,
                ),
            )
            rows = cursor.fetchall()
        conn.close()

        for (
            ship_date,
            external_id,
            source_batch_id,
            shipment_ids,
            reconciliation_status,
            recorded_replacement_id,
        ) in rows:
            source = v2_get_batch(source_batch_id)
            if not source.get('success'):
                if (
                    reconciliation_status == 'observed_empty'
                    and source.get('error_type') == 'not_found'
                    and recorded_replacement_id
                ):
                    logger.info(
                        f"Previously observed empty batch {source_batch_id} is already gone; "
                        "recording it as retired"
                    )
                    _set_reconciliation_state(
                        ship_date,
                        'retired',
                        recorded_replacement_id,
                        update_daily_record=True,
                    )
                    continue
                logger.warning(f"Batch reconciliation could not read source {source_batch_id}")
                continue
            source_count = source.get('shipment_count')
            if (
                not isinstance(source_count, int)
                or isinstance(source_count, bool)
                or source_count < 0
            ):
                logger.error(
                    f"Refusing cleanup analysis for batch {source_batch_id}: "
                    "shipment count is missing or invalid"
                )
                _set_reconciliation_state(ship_date, 'uncertain')
                continue
            if source_count > 0:
                _set_reconciliation_state(ship_date, 'stable')
                continue
            if source.get('status') != 'open':
                logger.error(
                    f"Refusing cleanup analysis for empty batch {source_batch_id}: "
                    f"status is {source.get('status')!r}, not 'open'"
                )
                _set_reconciliation_state(ship_date, 'uncertain')
                continue
            if source.get('external_batch_id') != external_id:
                logger.error(
                    f"Refusing empty-batch reconciliation for {source_batch_id}: "
                    "external identity does not match"
                )
                _set_reconciliation_state(ship_date, 'uncertain')
                continue

            original_ids = list(shipment_ids)
            if not original_ids:
                _set_reconciliation_state(ship_date, 'uncertain')
                continue
            assignments = v2_get_shipment_batch_assignments(original_ids)
            if not assignments.get('success'):
                logger.warning(f"Could not reconcile shipment assignments for {source_batch_id}")
                continue
            replacement_sets = [
                set(assignments['assignments'].get(shipment_id, []))
                for shipment_id in original_ids
            ]
            if (
                any(len(batch_ids) != 1 for batch_ids in replacement_sets)
                or len({next(iter(batch_ids)) for batch_ids in replacement_sets}) != 1
            ):
                logger.error(
                    f"Empty batch {source_batch_id} has incomplete or split replacement assignments; "
                    "leaving it unchanged"
                )
                server_logger.error(
                    f"Batch processor found empty batch {source_batch_id}, but could not prove all "
                    "shipments moved to one replacement. Manual review required.",
                    source="Batch Processor",
                )
                _set_reconciliation_state(ship_date, 'uncertain')
                continue

            replacement_id = next(iter(replacement_sets[0]))
            if replacement_id == source_batch_id:
                logger.error(
                    f"Empty batch {source_batch_id} is still listed as the shipment "
                    "assignment; refusing to treat it as its own replacement"
                )
                _set_reconciliation_state(ship_date, 'uncertain')
                continue
            replacement = v2_get_batch(replacement_id)
            replacement_shipments = v2_get_batch_shipment_ids(replacement_id)
            if (
                not replacement.get('success')
                or not replacement_shipments.get('success')
                or not set(original_ids).issubset(set(replacement_shipments['shipment_ids']))
            ):
                logger.error(
                    f"Replacement batch {replacement_id} could not be verified for {source_batch_id}"
                )
                _set_reconciliation_state(ship_date, 'uncertain')
                continue

            # Enabling cleanup never skips observation. A verified source must
            # first be persisted as observed_empty, then survive the delay and
            # every safety check again before a later run may delete it.
            if reconciliation_status != 'observed_empty':
                logger.warning(
                    f"OBSERVATION ONLY: automated batch {source_batch_id} became empty; "
                    f"all {len(original_ids)} shipments moved to {replacement_id}. "
                    "A later reconciliation may retire it if cleanup is enabled."
                )
                server_logger.warning(
                    f"Batch processor observation: {source_batch_id} became empty after its "
                    f"shipments moved to {replacement_id}. No ShipStation changes were made.",
                    source="Batch Processor",
                )
                _set_reconciliation_state(
                    ship_date, 'observed_empty', replacement_id, update_daily_record=True
                )
                continue

            if recorded_replacement_id != replacement_id:
                logger.warning(
                    f"Replacement for empty batch {source_batch_id} changed from "
                    f"{recorded_replacement_id} to {replacement_id}; restarting observation delay"
                )
                _set_reconciliation_state(
                    ship_date, 'observed_empty', replacement_id, update_daily_record=True
                )
                continue

            deleted = v2_delete_batch(source_batch_id)
            if deleted.get('success'):
                logger.info(f"Retired proven-empty automated batch {source_batch_id}")
                _set_reconciliation_state(
                    ship_date, 'retired', replacement_id, update_daily_record=True
                )
            else:
                logger.error(f"Failed to retire proven-empty batch {source_batch_id}")
                server_logger.error(
                    f"Batch processor could not retire proven-empty batch {source_batch_id}; "
                    "it will re-verify and retry later.",
                    source="Batch Processor",
                )
                _set_reconciliation_state(
                    ship_date,
                    'observed_empty',
                    replacement_id,
                    update_daily_record=True,
                )
    except Exception as e:
        logger.error(f"Non-blocking batch reconciliation failed: {e}", exc_info=True)


VERIFY_WAIT_SECONDS = 3


def _verify_batch(batch_id: str, requested_count: int) -> str:
    """
    GET the batch from ShipStation and check its shipment count.

    Returns one of:
        'ok'           — batch exists and count matches
        'not_found'    — 404; batch definitively does not exist — safe to retry
        'mismatch'     — batch exists but count differs — do NOT retry
        'api_error'    — uncertain state (network/5xx) — do NOT retry
    """
    logger.info(f"Verifying batch {batch_id} on ShipStation (waiting {VERIFY_WAIT_SECONDS}s for propagation)...")
    time.sleep(VERIFY_WAIT_SECONDS)

    result = v2_get_batch(batch_id)

    if result.get('success'):
        verified_count = result.get('shipment_count', 0)
        if verified_count == requested_count:
            logger.info(
                f"Batch {batch_id} verified ✓ — {verified_count}/{requested_count} shipments confirmed on ShipStation"
            )
            return 'ok'
        else:
            logger.error(
                f"Batch {batch_id} count MISMATCH — requested {requested_count}, "
                f"ShipStation confirms {verified_count}"
            )
            return 'mismatch'

    error_type = result.get('error_type', 'api_error')
    error_msg = result.get('error', 'unknown')
    if error_type == 'not_found':
        logger.warning(
            f"Batch {batch_id} NOT FOUND after creation; retaining the daily claim "
            "and refusing an automatic retry"
        )
        return 'not_found'
    else:
        logger.error(f"Batch {batch_id} verification failed with uncertain state: {error_msg}")
        return 'api_error'


def run_batch_job() -> str:
    """Serialize the existing daily creation flow across all worker processes."""
    if not _ensure_batch_run_storage():
        return 'error'
    lock_conn = _acquire_batch_lock()
    if not lock_conn:
        logger.warning("Another batch processor instance holds the creation lock; skipping.")
        return 'skipped_locked'
    try:
        return _run_batch_job_locked()
    finally:
        _release_batch_lock(lock_conn)


def _run_batch_job_locked() -> str:
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

    external_batch_id = f"oracare-axiom-{ship_date}"
    already_recorded = _already_batched_today(ship_date)
    local_status = _get_batch_run_status(ship_date)
    if already_recorded and local_status not in ('creating', 'created'):
        logger.info(f"Batch already created today ({ship_date}) — skipping to prevent duplicates.")
        server_logger.info(
            f"Batch processor: already ran today ({ship_date}). Skipping duplicate run.",
            source="Batch Processor"
        )
        return 'skipped_duplicate'

    existing = v2_get_batch_by_external_id(external_batch_id)
    if existing.get('success'):
        existing_batch_id = existing.get('batch_id')
        listed = v2_get_batch_shipment_ids(existing_batch_id)
        if not listed.get('success'):
            return 'error'
        shipment_ids = listed['shipment_ids'] or _get_claimed_shipment_ids(ship_date)
        if not shipment_ids:
            server_logger.error(
                f"Recovered automated batch {existing_batch_id}, but its original shipment "
                "membership is unavailable. Manual review required.",
                source="Batch Processor",
            )
            return 'error'
        logger.warning(
            f"Recovered existing automated batch {existing_batch_id} by external ID; "
            "will not create a duplicate"
        )
        if not _record_batch_run(
            ship_date, existing_batch_id, external_batch_id, shipment_ids
        ):
            return 'error'
        _mark_batch_verified(ship_date)
        return 'completed'
    if existing.get('error_type') != 'not_found':
        logger.error(
            "Could not safely check for an existing automated batch; refusing to create a duplicate"
        )
        return 'error'

    if already_recorded:
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

    if not _claim_batch_run(ship_date, external_batch_id, shipment_ids):
        logger.warning("The daily batch date was claimed by another run; skipping.")
        return 'skipped_locked'

    batch_result = v2_create_batch(
        shipment_ids,
        external_batch_id=external_batch_id,
        batch_notes=f"Oracare automated Axiom batch {ship_date}",
    )
    if not batch_result.get('success'):
        error = batch_result.get('error', 'unknown error')
        logger.error(f"Failed to create batch: {error}")
        server_logger.error(
            f"Batch processor failed to create batch ({len(shipment_ids)} shipments): {error}",
            source="Batch Processor"
        )
        if not batch_result.get('ambiguous'):
            _clear_definite_failed_claim(ship_date, external_batch_id)
        else:
            server_logger.error(
                "Batch creation result is uncertain. The daily claim was retained to prevent "
                "an automatic duplicate; the next run will recover by external ID.",
                source="Batch Processor",
            )
        return 'error'

    batch_id = batch_result['batch_id']

    if not _record_batch_run(
        ship_date, batch_id, external_batch_id, shipment_ids
    ):
        server_logger.error(
            f"Batch {batch_id} created but could not persist run date to DB. "
            f"Restarting within the noon window may create a duplicate batch.",
            source="Batch Processor"
        )
        return 'error'

    verify_status = _verify_batch(batch_id, len(shipment_ids))

    if verify_status == 'ok':
        _mark_batch_verified(ship_date)
        update_workflow_last_run(WORKFLOW_NAME)
        summary = (
            f"Batch processor complete: batch {batch_id} created and verified with "
            f"{len(shipment_ids)} shipment(s). Labels not created — print from ShipStation."
        )
        logger.info("=" * 70)
        logger.info(f"BATCH PROCESSOR COMPLETE — {len(shipment_ids)} shipments, batch {batch_id} ✓ verified")
        logger.info("=" * 70)
        server_logger.info(summary, source="Batch Processor")
        return 'completed'

    elif verify_status == 'mismatch':
        server_logger.error(
            f"Batch {batch_id} exists on ShipStation but shipment count does not match "
            f"(requested {len(shipment_ids)}). Do NOT retry — manual review required in ShipStation.",
            source="Batch Processor"
        )
        return 'error'

    else:
        server_logger.error(
            f"Batch {batch_id} verification returned uncertain state — cannot confirm existence. "
            f"Do NOT retry automatically. Check ShipStation and logs manually.",
            source="Batch Processor"
        )
        return 'error'


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

            now_ct = datetime.datetime.now(CST)
            now_minute = now_ct.strftime('%H:%M')
            now_time = now_ct.time().replace(second=0, microsecond=0)

            if _is_batch_time() and now_minute != last_batch_minute:
                last_batch_minute = now_minute
                _run_with_heartbeat()
            elif RECOVERY_START_TIME <= now_time <= RECOVERY_END_TIME:
                today_str = now_ct.strftime('%Y-%m-%d')
                if (not _already_batched_today(today_str)
                        and not _had_started_heartbeat_within(RECOVERY_LOOKBACK_MINUTES)):
                    logger.warning(
                        f"RECOVERY: No batch created today ({today_str}) and no STARTED "
                        f"heartbeat in the last {RECOVERY_LOOKBACK_MINUTES} min — "
                        f"triggering recovery batch at {now_minute} CT"
                    )
                    server_logger.warning(
                        f"Batch processor recovery: primary noon window was missed — "
                        f"triggering recovery batch at {now_minute} CT.",
                        source="Batch Processor"
                    )
                    _run_with_heartbeat(label='recovery')
            else:
                logger.debug(f"Not batch time ({now_minute} CT) — sleeping 60s")

            # Reconciliation runs only after schedule decisions and at most
            # once every five minutes. It cannot consume the primary batch
            # window, and each pass handles one terminal observation.
            if not _is_batch_time() and now_ct.minute % 5 == 0:
                if _ensure_batch_run_storage():
                    _reconcile_recent_batches()

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

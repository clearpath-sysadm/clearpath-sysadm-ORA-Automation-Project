"""
Stuck Workflow Detector Service

Monitors all workflows and detects when they become stuck (haven't updated
their status within their expected interval * threshold multiplier).

When a stuck workflow is detected:
1. Creates an incident record in stuck_workflow_incidents
2. Optionally auto-resets the workflow status to allow new executions
3. Logs a warning to the server logs

Runs every 15 minutes (configurable via configuration_params).
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.database.pg_utils import get_connection, is_workflow_enabled
from src.workflow_heartbeat import cleanup_old_heartbeats
from utils.logging_config import setup_logging
from src.utils.server_logger import get_logger

setup_logging()
logger = logging.getLogger(__name__)
server_logger = get_logger()

WORKFLOW_NAME = 'stuck-workflow-detector'


def get_config_value(param_name: str, default: str) -> str:
    """Get a configuration parameter value."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value FROM configuration_params 
            WHERE parameter_name = %s
        """, (param_name,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if row else default
    except Exception as e:
        logger.error(f"Failed to get config {param_name}: {e}")
        return default


def get_workflow_health_data() -> list:
    """
    Get health data for all workflows, combining workflows table data
    with workflow_controls enabled status and latest heartbeats.
    
    Returns list of dicts with workflow health info.
    """
    logger.info("📊 Fetching workflow health data from database...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                w.name,
                w.display_name,
                w.status,
                w.last_run_at,
                w.expected_interval_seconds,
                wc.enabled,
                wc.last_updated as controls_last_updated,
                (
                    SELECT heartbeat_at 
                    FROM workflow_heartbeats 
                    WHERE workflow_name = w.name 
                    ORDER BY heartbeat_at DESC 
                    LIMIT 1
                ) as last_heartbeat,
                (
                    SELECT execution_phase 
                    FROM workflow_heartbeats 
                    WHERE workflow_name = w.name 
                    ORDER BY heartbeat_at DESC 
                    LIMIT 1
                ) as last_phase
            FROM workflows w
            LEFT JOIN workflow_controls wc ON w.name = wc.workflow_name
            WHERE w.name != 'dashboard-server'
            ORDER BY w.name
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        workflows = [{
            'name': row[0],
            'display_name': row[1],
            'status': row[2],
            'last_run_at': row[3],
            'expected_interval_seconds': row[4],
            'enabled': row[5],
            'controls_last_updated': row[6],
            'last_heartbeat': row[7],
            'last_phase': row[8]
        } for row in rows]
        
        logger.info(f"📊 Found {len(workflows)} workflows to monitor")
        for wf in workflows:
            enabled_status = "enabled" if wf.get('enabled', True) else "DISABLED"
            heartbeat_info = wf['last_heartbeat'].strftime('%H:%M:%S') if wf['last_heartbeat'] else "none"
            phase_info = wf['last_phase'] or "n/a"
            logger.info(f"   - {wf['name']}: {enabled_status}, last_heartbeat={heartbeat_info}, phase={phase_info}")
        
        return workflows
        
    except Exception as e:
        logger.error(f"Failed to get workflow health data: {e}")
        server_logger.error(f"Failed to get workflow health data: {e}", source='Stuck Detector')
        return []


def get_cst_now() -> datetime:
    """Get current time in CST (Central Standard Time, UTC-6)."""
    from datetime import timezone
    utc_now = datetime.now(timezone.utc)
    cst_offset = timedelta(hours=-6)
    return utc_now + cst_offset


def get_last_business_end_time() -> datetime:
    """
    Get the end time of the most recent business period in UTC.
    Business hours: Mon-Fri 6 AM - 6 PM CST
    
    This function determines when the last business period ended, which helps
    identify if a workflow's stale heartbeat is simply due to scheduled downtime.
    
    Returns UTC datetime of when business hours last ended.
    """
    cst_now = get_cst_now()
    weekday = cst_now.weekday()  # 0=Monday, 6=Sunday
    hour = cst_now.hour
    
    # If currently in business hours (Mon-Fri 6AM-6PM CST), 
    # the last end was yesterday at 6 PM (or Friday if it's Monday before 6 PM)
    if weekday <= 4 and 6 <= hour < 18:  # Business hours now
        if weekday == 0:  # Monday during hours - last end was Friday 6 PM
            days_back = 3
        else:  # Tue-Fri during hours - last end was yesterday 6 PM
            days_back = 1
        last_end_cst = (cst_now - timedelta(days=days_back)).replace(hour=18, minute=0, second=0, microsecond=0)
    else:
        # Currently after hours or on weekend
        if weekday >= 5:  # Weekend (Sat=5, Sun=6)
            days_back = weekday - 4  # Sat: 1 day back, Sun: 2 days back to Friday
        elif hour < 6:  # Before 6 AM on weekday
            if weekday == 0:  # Before 6 AM Monday -> Friday 6 PM
                days_back = 3
            else:  # Before 6 AM Tue-Fri -> yesterday 6 PM
                days_back = 1
        else:  # After 6 PM on weekday
            days_back = 0
        last_end_cst = (cst_now - timedelta(days=days_back)).replace(hour=18, minute=0, second=0, microsecond=0)
    
    # Convert CST to UTC (CST = UTC-6)
    return last_end_cst + timedelta(hours=6)


def get_current_business_start_time() -> datetime:
    """
    Get the start time of the current business day in UTC.
    Business hours: Mon-Fri 6 AM - 6 PM CST
    
    Returns UTC datetime of when the current business day started (or when
    the next business period will start if currently outside business hours).
    """
    cst_now = get_cst_now()
    weekday = cst_now.weekday()  # 0=Monday, 6=Sunday
    hour = cst_now.hour
    
    if weekday <= 4 and 6 <= hour < 18:  # Currently in business hours
        business_start_cst = cst_now.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        # Not in business hours - find start of next business period
        if weekday >= 5:  # Weekend
            days_until_monday = 7 - weekday
            business_start_cst = (cst_now + timedelta(days=days_until_monday)).replace(hour=6, minute=0, second=0, microsecond=0)
        elif hour < 6:  # Before 6 AM on weekday
            business_start_cst = cst_now.replace(hour=6, minute=0, second=0, microsecond=0)
        else:  # After 6 PM on weekday (Fri after 6 PM -> Monday)
            if weekday == 4:  # Friday after 6 PM
                days_until_monday = 3
            else:
                days_until_monday = 1
            business_start_cst = (cst_now + timedelta(days=days_until_monday)).replace(hour=6, minute=0, second=0, microsecond=0)
    
    # Convert CST to UTC (CST = UTC-6)
    return business_start_cst + timedelta(hours=6)


def detect_stuck_workflows(threshold_multiplier: float = 3.0) -> list:
    """
    Detect workflows that appear to be stuck or have stopped running.
    
    A workflow is considered stuck if ANY of these conditions are met:
    1. Last activity (heartbeat or last_run) is older than expected_interval * threshold
       This catches workflows that have completely stopped running
    2. Last heartbeat phase is 'started' or 'error' (refines messaging for mid-run crashes)
    
    Uses heartbeat timestamp as primary indicator (most accurate),
    falls back to last_run_at if no heartbeat data exists.
    
    GRACE PERIOD: After business hours resume (Monday morning, after-hours end),
    workflows get a grace period equal to their expected interval plus a buffer
    to allow them to start and emit a fresh heartbeat. This prevents false positives
    when workflows are just starting up after scheduled downtime.
    
    Args:
        threshold_multiplier: Factor to multiply expected interval by
    
    Returns:
        List of stuck workflow dicts
    """
    stuck_workflows = []
    workflows = get_workflow_health_data()
    now = datetime.utcnow()
    
    business_start = get_current_business_start_time()
    last_business_end = get_last_business_end_time()
    time_since_business_start = (now - business_start).total_seconds()
    startup_grace_period = int(get_config_value('stuck_workflow_startup_grace_seconds', '900'))
    
    logger.info(f"⏱️  Detection Parameters:")
    logger.info(f"   - Current time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   - Business start (UTC): {business_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   - Last business end (UTC): {last_business_end.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   - Time since business start: {int(time_since_business_start)}s ({int(time_since_business_start/60)} min)")
    logger.info(f"   - Threshold multiplier: {threshold_multiplier}x")
    logger.info(f"   - Startup grace period: {startup_grace_period}s ({int(startup_grace_period/60)} min)")
    logger.info(f"")
    logger.info(f"🔬 Evaluating {len(workflows)} workflows...")
    
    for wf in workflows:
        wf_name = wf['name']
        
        if not wf.get('enabled', True):
            logger.info(f"   [{wf_name}] SKIPPED - workflow is disabled")
            continue
            
        expected_interval = wf.get('expected_interval_seconds')
        if not expected_interval:
            logger.info(f"   [{wf_name}] SKIPPED - no expected interval configured")
            continue
        
        last_heartbeat = wf.get('last_heartbeat')
        last_run = wf.get('last_run_at')
        last_phase = wf.get('last_phase')
        
        reference_time = last_heartbeat if last_heartbeat else last_run
        if not reference_time:
            logger.info(f"   [{wf_name}] SKIPPED - no heartbeat or last_run timestamp available")
            continue
        
        if hasattr(reference_time, 'replace'):
            reference_naive = reference_time.replace(tzinfo=None)
        else:
            reference_naive = reference_time
            
        threshold_seconds = expected_interval * threshold_multiplier
        actual_gap = (now - reference_naive).total_seconds()
        time_source = "heartbeat" if last_heartbeat else "last_run_at"
        
        logger.info(f"   [{wf_name}] Evaluating:")
        logger.info(f"      - Expected interval: {expected_interval}s ({int(expected_interval/60)} min)")
        logger.info(f"      - Stuck threshold: {int(threshold_seconds)}s ({int(threshold_seconds/60)} min)")
        logger.info(f"      - Last activity ({time_source}): {reference_naive.strftime('%H:%M:%S')}")
        logger.info(f"      - Last phase: {last_phase or 'n/a'}")
        logger.info(f"      - Gap since activity: {int(actual_gap)}s ({int(actual_gap/60)} min)")
        
        workflow_grace_period = expected_interval + startup_grace_period
        if time_since_business_start < workflow_grace_period:
            if reference_naive < last_business_end.replace(tzinfo=None):
                logger.info(
                    f"      - GRACE PERIOD ACTIVE: Last activity was before business ended. "
                    f"Remaining grace: {int(workflow_grace_period - time_since_business_start)}s"
                )
                logger.info(f"      - Result: HEALTHY (grace period)")
                continue
        
        is_stuck = False
        stuck_reason = None
        
        if actual_gap > threshold_seconds:
            is_stuck = True
            
            if last_phase in ('started', 'error'):
                stuck_reason = f"last phase was '{last_phase}' but no completion for {int(actual_gap)}s (possible mid-run crash)"
            else:
                stuck_reason = f"no activity for {int(actual_gap)}s (threshold: {int(threshold_seconds)}s, source: {time_source})"
            
            logger.warning(f"      - Result: STUCK - {stuck_reason}")
        else:
            remaining = int(threshold_seconds - actual_gap)
            logger.info(f"      - Result: HEALTHY (gap {int(actual_gap)}s < threshold {int(threshold_seconds)}s, {remaining}s remaining)")
        
        if is_stuck:
            stuck_workflows.append({
                'name': wf['name'],
                'display_name': wf['display_name'],
                'last_run_at': last_run,
                'expected_interval_seconds': expected_interval,
                'actual_gap_seconds': int(actual_gap),
                'threshold_seconds': int(threshold_seconds),
                'last_heartbeat': last_heartbeat,
                'last_phase': last_phase,
                'stuck_reason': stuck_reason
            })
    
    logger.info(f"")
    logger.info(f"📋 Detection Summary:")
    logger.info(f"   - Workflows evaluated: {len(workflows)}")
    logger.info(f"   - Stuck workflows found: {len(stuck_workflows)}")
    if stuck_workflows:
        for sw in stuck_workflows:
            logger.warning(f"   - ⚠️  {sw['name']}: {sw['stuck_reason']}")
    else:
        logger.info(f"   - All workflows are healthy")
    
    return stuck_workflows


def create_incident(workflow: dict) -> Optional[int]:
    """Create a stuck workflow incident record."""
    wf_name = workflow['name']
    logger.info(f"📝 Creating incident for stuck workflow: {wf_name}")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM stuck_workflow_incidents
            WHERE workflow_name = %s AND status = 'active'
            LIMIT 1
        """, (wf_name,))
        
        existing = cursor.fetchone()
        if existing:
            logger.info(f"   Active incident #{existing[0]} already exists for {wf_name} - not creating duplicate")
            cursor.close()
            conn.close()
            return existing[0]
        
        logger.info(f"   No existing incident - creating new one")
        cursor.execute("""
            INSERT INTO stuck_workflow_incidents
            (workflow_name, last_heartbeat, expected_interval_seconds, actual_gap_seconds, status)
            VALUES (%s, %s, %s, %s, 'active')
            RETURNING id
        """, (
            wf_name,
            workflow.get('last_heartbeat'),
            workflow['expected_interval_seconds'],
            workflow['actual_gap_seconds']
        ))
        
        result = cursor.fetchone()
        if not result:
            logger.error(f"   Failed to get incident ID for {wf_name}")
            conn.commit()
            cursor.close()
            conn.close()
            return None
        
        incident_id = result[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"   Created incident #{incident_id}")
        logger.info(f"   - Workflow: {wf_name}")
        logger.info(f"   - Gap: {workflow['actual_gap_seconds']}s")
        logger.info(f"   - Threshold: {workflow['threshold_seconds']}s")
        logger.info(f"   - Last phase: {workflow.get('last_phase', 'n/a')}")
        
        server_logger.warning(
            f"STUCK WORKFLOW INCIDENT #{incident_id}: {wf_name} - "
            f"no activity for {workflow['actual_gap_seconds']}s (threshold: {workflow['threshold_seconds']}s)",
            source='Stuck Detector'
        )
        
        return incident_id
        
    except Exception as e:
        logger.error(f"Failed to create incident for {wf_name}: {e}")
        server_logger.error(f"Failed to create incident for {wf_name}: {e}", source='Stuck Detector')
        return None


def auto_reset_workflow(workflow_name: str, incident_id: int) -> bool:
    """
    Auto-reset a stuck workflow by setting its status to 'completed'.
    This allows the scheduler to start a new execution.
    """
    logger.info(f"🔄 Auto-resetting stuck workflow: {workflow_name}")
    logger.info(f"   - Incident ID: {incident_id}")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        logger.info(f"   - Setting workflow status to 'completed'...")
        cursor.execute("""
            UPDATE workflows 
            SET status = 'completed',
                last_run_at = NOW(),
                updated_at = NOW()
            WHERE name = %s
        """, (workflow_name,))
        
        logger.info(f"   - Resolving incident #{incident_id}...")
        cursor.execute("""
            UPDATE stuck_workflow_incidents
            SET status = 'resolved',
                resolved_at = NOW(),
                resolved_by = 'auto_detector',
                resolution_method = 'auto_reset'
            WHERE id = %s
        """, (incident_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"   - Auto-reset complete for {workflow_name}")
        
        server_logger.info(
            f"AUTO-RESET: Workflow '{workflow_name}' has been automatically reset (incident #{incident_id})",
            source='Stuck Detector'
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to auto-reset {workflow_name}: {e}")
        server_logger.error(f"Failed to auto-reset {workflow_name}: {e}", source='Stuck Detector')
        return False


def run_stuck_detector():
    """Main detection loop."""
    
    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"🚀 STUCK WORKFLOW DETECTOR - Starting Up")
    logger.info(f"{'='*60}")
    logger.info(f"")
    logger.info(f"📋 Service Configuration:")
    logger.info(f"   - Workflow Name: {WORKFLOW_NAME}")
    logger.info(f"   - Business Hours: Monday-Friday 6 AM - 6 PM CST")
    logger.info(f"   - Weekend Behavior: Sleep (1 hour intervals)")
    logger.info(f"   - After Hours Behavior: Sleep (1 hour intervals)")
    logger.info(f"")
    
    scan_count = 0
    
    while True:
        try:
            now = datetime.now()
            hour = now.hour
            weekday = now.weekday()
            
            if weekday >= 5:
                logger.info(f"⏰ WEEKEND | {now.strftime('%A %I:%M %p CST')} | Detection paused")
                logger.info(f"💤 Sleeping for 3600s to reduce compute costs")
                time.sleep(3600)
                continue
            
            cst_hour = (hour - 6) % 24
            if cst_hour < 6 or cst_hour >= 18:
                logger.info(f"⏰ AFTER HOURS | {now.strftime('%A %I:%M %p CST')} | Detection paused")
                logger.info(f"💤 Sleeping for 3600s to reduce compute costs")
                time.sleep(3600)
                continue
            
            if not is_workflow_enabled(WORKFLOW_NAME):
                logger.info(f"⏸️ Workflow '{WORKFLOW_NAME}' is DISABLED via workflow_controls")
                logger.info(f"   Sleeping for 60s and checking again...")
                time.sleep(60)
                continue
            
            threshold_multiplier = float(get_config_value('stuck_workflow_threshold_multiplier', '3'))
            auto_reset_enabled = get_config_value('stuck_workflow_auto_reset_enabled', 'true') == 'true'
            check_interval = int(get_config_value('stuck_workflow_check_interval_seconds', '900'))
            retention_days = int(get_config_value('stuck_workflow_heartbeat_retention_days', '7'))
            
            scan_count += 1
            logger.info(f"")
            logger.info(f"{'='*60}")
            logger.info(f"🔍 SCAN #{scan_count} | {now.strftime('%Y-%m-%d %H:%M:%S CST')}")
            logger.info(f"{'='*60}")
            logger.info(f"")
            logger.info(f"📋 Configuration (loaded from database):")
            logger.info(f"   - Threshold Multiplier: {threshold_multiplier}x")
            logger.info(f"   - Auto-Reset Enabled: {auto_reset_enabled}")
            logger.info(f"   - Check Interval: {check_interval}s ({int(check_interval/60)} min)")
            logger.info(f"   - Heartbeat Retention: {retention_days} days")
            logger.info(f"")
            
            stuck = detect_stuck_workflows(threshold_multiplier)
            
            if stuck:
                logger.warning(f"")
                logger.warning(f"🚨 ALERT: Found {len(stuck)} stuck workflow(s)!")
                logger.warning(f"")
                
                for wf in stuck:
                    logger.warning(f"   Processing stuck workflow: {wf['name']}")
                    incident_id = create_incident(wf)
                    
                    if incident_id and auto_reset_enabled:
                        logger.info(f"   Auto-reset is ENABLED - attempting reset...")
                        auto_reset_workflow(wf['name'], incident_id)
                    elif incident_id:
                        logger.info(f"   Auto-reset is DISABLED - incident #{incident_id} created, awaiting manual intervention")
                        server_logger.warning(
                            f"Manual intervention required: Workflow '{wf['name']}' is stuck (incident #{incident_id})",
                            source='Stuck Detector'
                        )
            else:
                logger.info(f"")
                logger.info(f"✅ All workflows healthy - no issues detected")
            
            logger.info(f"")
            logger.info(f"🧹 Cleaning up old heartbeat records (retention: {retention_days} days)...")
            cleanup_old_heartbeats(retention_days)
            
            logger.info(f"")
            logger.info(f"😴 Scan complete. Next scan in {check_interval}s ({int(check_interval/60)} min)")
            logger.info(f"{'='*60}")
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"")
            logger.error(f"❌ ERROR in stuck detector: {e}")
            logger.error(f"   Sleeping 60s before retry...")
            server_logger.error(f"Stuck detector error: {e}", source='Stuck Detector')
            time.sleep(60)


if __name__ == '__main__':
    run_stuck_detector()

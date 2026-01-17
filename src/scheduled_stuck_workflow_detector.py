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
        
        return [{
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
        
    except Exception as e:
        logger.error(f"Failed to get workflow health data: {e}")
        return []


def get_last_business_end_time() -> datetime:
    """
    Get the end time of the most recent business period in UTC.
    Business hours: Mon-Fri 6 AM - 6 PM CST
    
    This function determines when the last business period ended, which helps
    identify if a workflow's stale heartbeat is simply due to scheduled downtime.
    
    Returns UTC datetime of when business hours last ended.
    """
    from config.settings import get_cst_now
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
    from config.settings import get_cst_now
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
    
    logger.debug(f"Business context: start={business_start.isoformat()}, last_end={last_business_end.isoformat()}, since_start={int(time_since_business_start)}s")
    
    for wf in workflows:
        if not wf.get('enabled', True):
            continue
            
        expected_interval = wf.get('expected_interval_seconds')
        if not expected_interval:
            continue
        
        last_heartbeat = wf.get('last_heartbeat')
        last_run = wf.get('last_run_at')
        last_phase = wf.get('last_phase')
        
        reference_time = last_heartbeat if last_heartbeat else last_run
        if not reference_time:
            continue
        
        if hasattr(reference_time, 'replace'):
            reference_naive = reference_time.replace(tzinfo=None)
        else:
            reference_naive = reference_time
            
        threshold_seconds = expected_interval * threshold_multiplier
        actual_gap = (now - reference_naive).total_seconds()
        
        workflow_grace_period = expected_interval + startup_grace_period
        if time_since_business_start < workflow_grace_period:
            if reference_naive < last_business_end.replace(tzinfo=None):
                logger.debug(
                    f"Skipping {wf['name']} during startup grace period - "
                    f"last activity was before business hours ended "
                    f"({int(time_since_business_start)}s < {int(workflow_grace_period)}s grace)"
                )
                continue
        
        is_stuck = False
        stuck_reason = None
        
        if actual_gap > threshold_seconds:
            is_stuck = True
            time_source = "heartbeat" if last_heartbeat else "last_run_at"
            
            if last_phase in ('started', 'error'):
                stuck_reason = f"last phase was '{last_phase}' but no completion for {int(actual_gap)}s (possible mid-run crash)"
            else:
                stuck_reason = f"no activity for {int(actual_gap)}s (threshold: {int(threshold_seconds)}s, source: {time_source})"
        
        if is_stuck:
            stuck_workflows.append({
                'name': wf['name'],
                'display_name': wf['display_name'],
                'last_run_at': last_run,
                'expected_interval_seconds': expected_interval,
                'actual_gap_seconds': int(actual_gap),
                'threshold_seconds': int(threshold_seconds),
                'last_heartbeat': last_heartbeat,
                'last_phase': last_phase
            })
            logger.warning(f"Stuck workflow detected: {wf['name']} - {stuck_reason}")
    
    return stuck_workflows


def create_incident(workflow: dict) -> Optional[int]:
    """Create a stuck workflow incident record."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM stuck_workflow_incidents
            WHERE workflow_name = %s AND status = 'active'
            LIMIT 1
        """, (workflow['name'],))
        
        existing = cursor.fetchone()
        if existing:
            logger.debug(f"Active incident already exists for {workflow['name']}")
            cursor.close()
            conn.close()
            return existing[0]
        
        cursor.execute("""
            INSERT INTO stuck_workflow_incidents
            (workflow_name, last_heartbeat, expected_interval_seconds, actual_gap_seconds, status)
            VALUES (%s, %s, %s, %s, 'active')
            RETURNING id
        """, (
            workflow['name'],
            workflow.get('last_heartbeat'),
            workflow['expected_interval_seconds'],
            workflow['actual_gap_seconds']
        ))
        
        result = cursor.fetchone()
        if not result:
            logger.error(f"Failed to get incident ID for {workflow['name']}")
            conn.commit()
            cursor.close()
            conn.close()
            return None
        
        incident_id = result[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        server_logger.warning(
            f"Stuck workflow detected: {workflow['name']} - no activity for {workflow['actual_gap_seconds']}s",
            source='Stuck Detector'
        )
        
        logger.info(f"Created incident #{incident_id} for stuck workflow {workflow['name']}")
        return incident_id
        
    except Exception as e:
        logger.error(f"Failed to create incident for {workflow['name']}: {e}")
        return None


def auto_reset_workflow(workflow_name: str, incident_id: int) -> bool:
    """
    Auto-reset a stuck workflow by setting its status to 'completed'.
    This allows the scheduler to start a new execution.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workflows 
            SET status = 'completed',
                last_run_at = NOW(),
                updated_at = NOW()
            WHERE name = %s
        """, (workflow_name,))
        
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
        
        server_logger.info(
            f"Auto-reset stuck workflow: {workflow_name}",
            source='Stuck Detector'
        )
        
        logger.info(f"Auto-reset workflow {workflow_name} (incident #{incident_id})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to auto-reset {workflow_name}: {e}")
        return False


def run_stuck_detector():
    """Main detection loop."""
    
    logger.info(f"🚀 Starting {WORKFLOW_NAME}")
    logger.info("⏰ Business Hours: Monday-Friday 6 AM - 6 PM CST | Weekends OFF")
    
    while True:
        try:
            now = datetime.now()
            hour = now.hour
            weekday = now.weekday()
            
            if weekday >= 5:
                logger.info(f"⏰ WEEKEND | {now.strftime('%A %I:%M %p CST')} | Sleeping")
                logger.info("💤 Database sleeping for 3600s to reduce compute time")
                time.sleep(3600)
                continue
            
            cst_hour = (hour - 6) % 24
            if cst_hour < 6 or cst_hour >= 18:
                logger.info(f"⏰ AFTER HOURS | {now.strftime('%A %I:%M %p CST')} | Sleeping")
                logger.info("💤 Database sleeping for 3600s to reduce compute time")
                time.sleep(3600)
                continue
            
            if not is_workflow_enabled(WORKFLOW_NAME):
                logger.info(f"⏸️ Workflow '{WORKFLOW_NAME}' is DISABLED - sleeping 60s")
                time.sleep(60)
                continue
            
            threshold_multiplier = float(get_config_value('stuck_workflow_threshold_multiplier', '3'))
            auto_reset_enabled = get_config_value('stuck_workflow_auto_reset_enabled', 'true') == 'true'
            check_interval = int(get_config_value('stuck_workflow_check_interval_seconds', '900'))
            retention_days = int(get_config_value('stuck_workflow_heartbeat_retention_days', '7'))
            
            logger.info(f"🔍 Scanning for stuck workflows (threshold: {threshold_multiplier}x)")
            
            stuck = detect_stuck_workflows(threshold_multiplier)
            
            if stuck:
                logger.warning(f"⚠️ Found {len(stuck)} stuck workflow(s)")
                
                for wf in stuck:
                    incident_id = create_incident(wf)
                    
                    if incident_id and auto_reset_enabled:
                        auto_reset_workflow(wf['name'], incident_id)
            else:
                logger.info("✅ All workflows healthy")
            
            cleanup_old_heartbeats(retention_days)
            
            logger.info(f"😴 Next scan in {check_interval} seconds")
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error in stuck detector: {e}")
            time.sleep(60)


if __name__ == '__main__':
    run_stuck_detector()

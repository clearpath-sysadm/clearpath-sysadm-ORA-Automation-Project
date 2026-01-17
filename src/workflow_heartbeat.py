"""
Workflow Heartbeat Utility Module

Provides functions for workflows to log heartbeats, which are used by the
stuck workflow detector to identify workflows that have stopped executing.

Each workflow should call heartbeat() at key execution phases:
- 'started': When the workflow begins processing
- 'processing': During active work (optional, for long-running tasks)
- 'completed': When the workflow finishes successfully
- 'error': When the workflow encounters an error

Usage:
    from workflow_heartbeat import heartbeat, HeartbeatPhase
    
    heartbeat('xml-import', HeartbeatPhase.STARTED)
    # ... do work ...
    heartbeat('xml-import', HeartbeatPhase.COMPLETED, records_processed=10)
"""

import logging
from datetime import datetime
from typing import Optional
from enum import Enum
import json

from src.services.database.pg_utils import get_connection

logger = logging.getLogger(__name__)


class HeartbeatPhase(Enum):
    STARTED = 'started'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    ERROR = 'error'
    SKIPPED = 'skipped'


def heartbeat(
    workflow_name: str,
    phase: HeartbeatPhase,
    records_processed: int = 0,
    details: Optional[dict] = None
) -> bool:
    """
    Log a heartbeat for a workflow.
    
    Args:
        workflow_name: Name of the workflow (e.g., 'xml-import')
        phase: Current execution phase
        records_processed: Number of records processed (optional)
        details: Additional details as a dict (optional)
    
    Returns:
        True if heartbeat was logged successfully, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        details_json = json.dumps(details) if details else None
        
        cursor.execute("""
            INSERT INTO workflow_heartbeats 
            (workflow_name, heartbeat_at, execution_phase, records_processed, details)
            VALUES (%s, NOW(), %s, %s, %s)
        """, (workflow_name, phase.value, records_processed, details_json))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.debug(f"Heartbeat logged: {workflow_name} - {phase.value}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log heartbeat for {workflow_name}: {e}")
        return False


def get_latest_heartbeat(workflow_name: str) -> Optional[dict]:
    """
    Get the most recent heartbeat for a workflow.
    
    Args:
        workflow_name: Name of the workflow
    
    Returns:
        Dict with heartbeat info or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_name, heartbeat_at, execution_phase, records_processed, details
            FROM workflow_heartbeats
            WHERE workflow_name = %s
            ORDER BY heartbeat_at DESC
            LIMIT 1
        """, (workflow_name,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return {
                'workflow_name': row[0],
                'heartbeat_at': row[1],
                'execution_phase': row[2],
                'records_processed': row[3],
                'details': row[4]
            }
        return None
        
    except Exception as e:
        logger.error(f"Failed to get heartbeat for {workflow_name}: {e}")
        return None


def get_all_latest_heartbeats() -> list:
    """
    Get the most recent heartbeat for each workflow.
    
    Returns:
        List of dicts with heartbeat info for each workflow
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT ON (workflow_name) 
                workflow_name, heartbeat_at, execution_phase, records_processed, details
            FROM workflow_heartbeats
            ORDER BY workflow_name, heartbeat_at DESC
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [{
            'workflow_name': row[0],
            'heartbeat_at': row[1],
            'execution_phase': row[2],
            'records_processed': row[3],
            'details': row[4]
        } for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get all heartbeats: {e}")
        return []


def cleanup_old_heartbeats(retention_days: int = 7) -> int:
    """
    Delete heartbeat records older than retention_days.
    
    Args:
        retention_days: Number of days to keep records
    
    Returns:
        Number of records deleted
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM workflow_heartbeats
            WHERE heartbeat_at < NOW() - INTERVAL '%s days'
        """, (retention_days,))
        
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old heartbeat records")
        
        return deleted
        
    except Exception as e:
        logger.error(f"Failed to cleanup heartbeats: {e}")
        return 0


def update_workflow_status_and_heartbeat(
    workflow_name: str,
    status: str,
    phase: HeartbeatPhase,
    records_processed: int = 0,
    details: Optional[dict] = None
) -> bool:
    """
    Update workflow status in the workflows table AND log a heartbeat.
    This is a convenience function for workflows to do both in one call.
    
    Args:
        workflow_name: Name of the workflow
        status: Status to set in workflows table (e.g., 'running', 'completed')
        phase: Heartbeat phase
        records_processed: Number of records processed
        details: Additional details
    
    Returns:
        True if both operations succeeded
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workflows 
            SET status = %s, 
                last_run_at = NOW(), 
                updated_at = NOW()
            WHERE name = %s
        """, (status, workflow_name))
        
        details_json = json.dumps(details) if details else None
        
        cursor.execute("""
            INSERT INTO workflow_heartbeats 
            (workflow_name, heartbeat_at, execution_phase, records_processed, details)
            VALUES (%s, NOW(), %s, %s, %s)
        """, (workflow_name, phase.value, records_processed, details_json))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.debug(f"Updated workflow status and heartbeat: {workflow_name} - {status}/{phase.value}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update workflow status/heartbeat for {workflow_name}: {e}")
        return False

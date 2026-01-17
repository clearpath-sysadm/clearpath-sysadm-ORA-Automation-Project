# Workflow Health Monitoring System
## Implementation Summary & Technical Note

**Document Version:** 1.0  
**Implementation Date:** January 17, 2026  
**Author:** Replit Agent  
**Status:** Production Ready

---

## 1. Executive Summary

### Problem Statement

On January 9, 2026, the XML Import workflow became stuck in a "zombie" state—the process appeared to be running but had stopped processing orders. This went undetected for several hours, causing a backlog of unprocessed orders and impacting fulfillment operations.

The root cause was that the workflow entered an error state but never recovered or alerted operators. The existing system had no mechanism to:
- Detect workflows that had stopped making progress
- Alert operators to stuck processes
- Provide manual intervention capabilities

### Solution Implemented

The **Workflow Health Monitoring System** provides automated detection of stuck workflows through a heartbeat-based monitoring approach. Key capabilities include:

1. **Heartbeat Logging** - All scheduled workflows now log their execution phases (started, completed, error, skipped) to a central database table
2. **Stuck Detection Service** - A new background service runs every 15 minutes to identify workflows that haven't reported activity within expected thresholds
3. **Incident Tracking** - Detected issues are logged to an incidents table with full context for post-mortem analysis
4. **Manual Intervention** - Operators can view health status and manually reset stuck workflows via the Workflow Controls UI

The system includes intelligent grace period handling to avoid false positives during scheduled downtime (weekends, outside business hours).

---

## 2. Technical Breakdown

### 2.1 Database Schema Changes

#### New Table: `workflow_heartbeats`

Stores real-time execution status from all monitored workflows.

```sql
CREATE TABLE workflow_heartbeats (
    id SERIAL PRIMARY KEY,
    workflow_name VARCHAR(100) NOT NULL,
    execution_phase VARCHAR(50) NOT NULL,  -- 'started', 'completed', 'error', 'skipped'
    heartbeat_at TIMESTAMP DEFAULT NOW(),
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workflow_heartbeats_name_time 
ON workflow_heartbeats(workflow_name, heartbeat_at DESC);
```

**Execution Phases:**
- `started` - Workflow began processing
- `completed` - Workflow finished successfully
- `error` - Workflow encountered an error
- `skipped` - Workflow skipped (outside business hours or disabled)

#### New Table: `stuck_workflow_incidents`

Tracks all detected stuck workflow incidents for historical analysis.

```sql
CREATE TABLE stuck_workflow_incidents (
    id SERIAL PRIMARY KEY,
    workflow_name VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    last_heartbeat_at TIMESTAMP,
    last_phase VARCHAR(50),
    gap_seconds INTEGER,
    threshold_seconds INTEGER,
    status VARCHAR(50) DEFAULT 'active',  -- 'active', 'resolved', 'auto_resolved'
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stuck_incidents_status 
ON stuck_workflow_incidents(status, detected_at DESC);
```

#### New Configuration Parameters

Added to `configuration_params` table:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `stuck_workflow_threshold_multiplier` | 3.0 | Multiplier applied to expected interval to determine stuck threshold |
| `stuck_workflow_startup_grace_seconds` | 900 | Extra grace period (seconds) after business hours resume |
| `stuck_workflow_auto_reset_enabled` | false | Whether to automatically reset stuck workflows |

### 2.2 New Services

#### `src/scheduled_stuck_workflow_detector.py`

A new scheduled service (8th workflow) that monitors all other workflows for stuck conditions.

**Key Features:**
- Runs every 15 minutes during business hours (Mon-Fri 6 AM - 6 PM CST)
- Sleeps during off-hours to reduce compute costs
- Uses heartbeat timestamps as primary detection indicator
- Falls back to `last_run_at` if no heartbeats exist
- Implements startup grace period to avoid Monday morning false positives
- Creates incidents in `stuck_workflow_incidents` table
- Logs all detection activity for debugging

**Detection Algorithm:**
```
threshold_seconds = expected_interval × threshold_multiplier
actual_gap = current_time - last_heartbeat_time

IF actual_gap > threshold_seconds:
    workflow is STUCK
```

#### `src/workflow_heartbeat.py`

Utility module providing heartbeat logging functions for all workflows.

```python
from src.workflow_heartbeat import log_heartbeat

# Log workflow start
log_heartbeat('xml-import', 'started')

# Log successful completion
log_heartbeat('xml-import', 'completed', details='Processed 15 orders')

# Log error
log_heartbeat('xml-import', 'error', details=str(exception))

# Log skip (outside business hours)
log_heartbeat('xml-import', 'skipped', details='Outside business hours')
```

### 2.3 New API Endpoints

#### `GET /api/workflow_health`

Returns current health status of all monitored workflows.

**Response:**
```json
{
  "workflows": [
    {
      "name": "xml-import",
      "display_name": "XML Import",
      "status": "completed",
      "last_run_at": "2026-01-17T12:00:00Z",
      "last_heartbeat": "2026-01-17T12:00:05Z",
      "last_phase": "completed",
      "health_status": "healthy",
      "stuck_warning": null,
      "enabled": true
    }
  ],
  "threshold_multiplier": 3.0,
  "checked_at": "2026-01-17T12:15:00Z"
}
```

**Health Status Values:**
- `healthy` - Within expected interval
- `warning` - Delayed (1.5x expected interval)
- `stuck` - Exceeded threshold (3x expected interval)

#### `POST /api/workflow/{name}/reset`

Manually reset a stuck workflow (Admin only).

**Actions Performed:**
1. Sets workflow status to 'completed'
2. Updates `last_run_at` timestamp
3. Resolves any active incidents for this workflow
4. Logs a 'completed' heartbeat with manual reset notation

**Response:**
```json
{
  "success": true,
  "message": "Workflow xml-import has been reset",
  "old_status": "running",
  "new_status": "completed"
}
```

#### `GET /api/stuck_workflow_incidents`

Returns incident history with optional filtering.

**Query Parameters:**
- `status` - Filter by status ('active', 'resolved', 'all')
- `limit` - Number of records (default: 50)

**Response:**
```json
{
  "incidents": [
    {
      "id": 1,
      "workflow_name": "xml-import",
      "detected_at": "2026-01-09T14:30:00Z",
      "last_heartbeat_at": "2026-01-09T10:15:00Z",
      "last_phase": "started",
      "gap_seconds": 15300,
      "threshold_seconds": 900,
      "status": "resolved",
      "resolved_at": "2026-01-09T15:00:00Z",
      "resolution_notes": "Manually reset by admin"
    }
  ],
  "total": 1
}
```

### 2.4 UI Enhancements

#### Workflow Controls Page (`workflow_controls.html`)

**New Elements:**

1. **Health Status Badges** - Each workflow row displays a colored badge:
   - 🟢 Green "Healthy" - Operating normally
   - 🟡 Yellow "Warning" - Delayed but not yet stuck
   - 🔴 Red "Stuck" - Exceeded threshold, needs attention

2. **Stuck Warning Messages** - Detailed information when workflow is stuck:
   - Time since last activity
   - Last execution phase
   - Threshold that was exceeded

3. **Reset Buttons** - Admin-only button appears for stuck workflows:
   - One-click manual reset
   - Confirms action before executing
   - Shows success/failure feedback

4. **Incident History Table** - New section showing:
   - All detected incidents (active and resolved)
   - Detection timestamp
   - Gap duration vs threshold
   - Resolution status and notes
   - Filter by status

---

## 3. Logic Evolution

The detection logic underwent several refinements based on architect feedback during development.

### 3.1 Initial Approach: Status-Based Detection

**Original Logic:**
```
IF workflow.status == 'running' AND time_since_last_run > threshold:
    workflow is STUCK
```

**Problems Identified:**
- Status field wasn't reliably updated during crashes
- Couldn't distinguish between "actively running" and "crashed mid-run"
- No visibility into what phase the workflow was in when it stopped

### 3.2 Refinement 1: Heartbeat-Based Detection

**Improved Logic:**
```
reference_time = last_heartbeat OR last_run_at (fallback)
IF current_time - reference_time > threshold:
    workflow is STUCK
```

**Benefits:**
- Heartbeats provide real-time activity signals
- Phase tracking identifies crash patterns (e.g., 'started' with no 'completed')
- Graceful fallback for workflows that haven't adopted heartbeats yet

### 3.3 Refinement 2: Startup Grace Period

**Problem:** On Monday mornings, all workflows would be flagged as "stuck" because their last activity was Friday evening—well beyond any reasonable threshold.

**Solution: Business Hours Awareness**

```python
def get_last_business_end_time():
    """Calculate when the last business period ended"""
    if today is Monday:
        # Last business was Friday 6 PM
        return friday_6pm_cst
    else:
        # Last business was yesterday 6 PM
        return yesterday_6pm_cst

# Skip detection if:
# 1. We're within grace period since business hours started, AND
# 2. Last workflow activity was before business hours ended
if time_since_business_start < grace_period:
    if last_activity < last_business_end:
        skip_detection()  # Expected gap, not a real stuck condition
```

**Grace Period Calculation:**
```
workflow_grace_period = expected_interval + startup_grace_seconds
```

For a 5-minute interval workflow with 900s startup grace:
- Grace period = 300 + 900 = 1200 seconds (20 minutes)
- Workflow has 20 minutes after business hours start before being flagged

### 3.4 Refinement 3: Phase-Aware Messaging

**Enhancement:** Different warning messages based on last execution phase.

```python
if last_phase in ('started', 'error'):
    warning = f"Last phase '{last_phase}' with no completion - possible crash"
else:
    warning = f"No activity for {gap}s (threshold: {threshold}s)"
```

This helps operators quickly identify crash scenarios vs. simple delays.

---

## 4. Final Configuration

### 4.1 Configurable Parameters

All parameters are stored in the `configuration_params` table and can be modified without code changes.

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `stuck_workflow_threshold_multiplier` | 3.0 | 1.5 - 10.0 | How many multiples of expected interval before flagging as stuck |
| `stuck_workflow_startup_grace_seconds` | 900 | 0 - 3600 | Extra seconds to wait after business hours resume |
| `stuck_workflow_auto_reset_enabled` | false | true/false | Automatically reset stuck workflows (use with caution) |

### 4.2 Workflow Intervals

Each workflow has an expected interval configured in the `workflows` table:

| Workflow | Expected Interval | Stuck Threshold (3x) |
|----------|------------------|---------------------|
| xml-import | 300s (5 min) | 900s (15 min) |
| shipstation-upload | 300s (5 min) | 900s (15 min) |
| unified-shipstation-sync | 300s (5 min) | 900s (15 min) |
| duplicate-scanner | 900s (15 min) | 2700s (45 min) |
| lot-mismatch-scanner | 900s (15 min) | 2700s (45 min) |
| orders-cleanup | 86400s (24 hr) | 259200s (72 hr) |
| stuck-workflow-detector | 900s (15 min) | 2700s (45 min) |

### 4.3 Business Hours

The detector service respects business hours to reduce compute costs:

- **Active:** Monday-Friday, 6 AM - 6 PM CST
- **Sleeping:** Weekends and outside business hours
- **Sleep Duration:** 3600 seconds (1 hour) during off-hours

---

## 5. Appendix

### 5.1 Files Modified/Created

| File | Type | Description |
|------|------|-------------|
| `src/scheduled_stuck_workflow_detector.py` | New | Stuck detection service |
| `src/workflow_heartbeat.py` | New | Heartbeat logging utility |
| `src/scheduled_xml_import.py` | Modified | Added heartbeat logging |
| `src/scheduled_shipstation_upload.py` | Modified | Added heartbeat logging |
| `src/unified_shipstation_sync.py` | Modified | Added heartbeat logging |
| `src/scheduled_duplicate_scanner.py` | Modified | Added heartbeat logging |
| `src/scheduled_lot_mismatch_scanner.py` | Modified | Added heartbeat logging |
| `src/scheduled_cleanup.py` | Modified | Added heartbeat logging |
| `templates/workflow_controls.html` | Modified | Health UI enhancements |
| `app.py` | Modified | New API endpoints |

### 5.2 Related Incidents

| Date | Incident | Resolution |
|------|----------|------------|
| Jan 9, 2026 | XML Import stuck for 4+ hours | Manual restart; prompted this feature |

### 5.3 Future Enhancements

1. **Email/Slack Alerting** - Send notifications when workflows are detected as stuck
2. **Auto-Reset with Limits** - Automatically reset up to N times before requiring manual intervention
3. **Historical Analytics** - Dashboard showing incident trends over time
4. **Heartbeat API** - External monitoring systems could query heartbeat status

---

*End of Document*

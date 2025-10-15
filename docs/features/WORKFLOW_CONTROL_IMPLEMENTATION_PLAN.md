# Workflow Control System - Implementation Plan

## Overview
Add programmatic on/off switches for all automation workflows to prevent dev/prod conflicts and enable maintenance control.

## Problem Statement
- Dev and prod deployments share ShipStation API, causing conflicting uploads
- Dev workflows auto-restart even when manually stopped
- No way to temporarily pause workflows without killing processes
- Lot number discrepancies (dev: 250237, prod: 250300) causing data inconsistencies

## Proposed Solution
Database-driven workflow enable/disable flags with UI dashboard control.

---

## Architecture

### 1. Database Schema
**New Table: `workflow_controls`**
```sql
CREATE TABLE workflow_controls (
    workflow_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT DEFAULT 'system'
);
```

**Initial Data:**
```sql
INSERT INTO workflow_controls (workflow_name, enabled) VALUES
    ('xml-import', TRUE),
    ('shipstation-upload', TRUE),
    ('status-sync', TRUE),
    ('manual-order-sync', TRUE),
    ('orders-cleanup', TRUE),
    ('weekly-reporter', TRUE);
```

### 2. Backend Components

#### A. Database Utility Function
**File: `src/db_utils.py`**
```python
def is_workflow_enabled(workflow_name: str) -> bool:
    """Check if workflow is enabled in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT enabled FROM workflow_controls WHERE workflow_name = ?",
            (workflow_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else True  # Default to enabled
    finally:
        conn.close()
```

#### B. API Endpoints
**File: `app.py`**
```python
# GET /api/workflow_controls - List all workflows
# PUT /api/workflow_controls/:name - Toggle workflow
# Body: {"enabled": true/false}
```

### 3. Workflow Modifications
Each workflow script gets enable check in main loop:

**Pattern for all 6 workflows:**
```python
while True:
    # CHECK ENABLED STATUS FIRST
    if not is_workflow_enabled('workflow-name'):
        logger.info(f"Workflow 'workflow-name' is DISABLED - sleeping 60s")
        time.sleep(60)
        continue
    
    # EXISTING WORKFLOW LOGIC
    logger.info("Running scheduled [task]...")
    # ... existing code ...
```

**Files to modify:**
1. `src/scheduled_xml_import.py`
2. `src/scheduled_shipstation_upload.py`
3. `src/shipstation_status_sync.py`
4. `src/manual_shipstation_sync.py`
5. `src/scheduled_cleanup.py`
6. `src/weekly_reporter.py`

### 4. UI Dashboard

#### New Page: `workflow_controls.html`
**Features:**
- Toggle switches for each workflow
- Real-time status indicators (green=running, gray=stopped)
- Last updated timestamp
- Color-coded status badges

**Navigation:**
- Add link to left sidebar after "Bundle SKUs Management"

---

## Implementation Steps

### Phase 1: Database Setup (5 min)
1. Create `workflow_controls` table via SQL tool
2. Insert 6 initial workflow records
3. Test query with `is_workflow_enabled()` function

### Phase 2: Backend API (10 min)
4. Add `is_workflow_enabled()` to `db_utils.py`
5. Create GET `/api/workflow_controls` endpoint
6. Create PUT `/api/workflow_controls/:name` endpoint
7. Test API with curl/Postman

### Phase 3: Workflow Integration (15 min)
8. Modify `scheduled_xml_import.py` - add enable check
9. Modify `scheduled_shipstation_upload.py` - add enable check
10. Modify `shipstation_status_sync.py` - add enable check
11. Modify `manual_shipstation_sync.py` - add enable check
12. Modify `scheduled_cleanup.py` - add enable check
13. Modify `weekly_reporter.py` - add enable check

### Phase 4: UI Dashboard (15 min)
14. Create `workflow_controls.html` with toggle switches
15. Add JavaScript for toggle API calls
16. Add navigation link to sidebar
17. Test toggle functionality

### Phase 5: Testing (10 min)
18. Toggle each workflow OFF - verify it stops processing
19. Toggle each workflow ON - verify it resumes
20. Test persistence across page refreshes

---

## Benefits

### Immediate Wins
✅ **Solves dev/prod conflict** - Disable dev workflows completely  
✅ **No process restarts needed** - Workflows check DB every loop  
✅ **Maintenance mode** - Pause uploads during ShipStation maintenance  
✅ **Emergency stop** - Instant kill switch for runaway workflows  

### Long-term Value
✅ **Environment isolation** - Each deployment can have own DB flags  
✅ **Audit trail** - Track when workflows were disabled/enabled  
✅ **User-friendly** - Non-technical users can control automation  
✅ **Zero downtime** - Toggle without redeploying  

---

## Rollback Plan
If issues arise:
1. Set all workflows to `enabled=TRUE` in database
2. Workflows fall back to default behavior
3. Remove enable checks from workflow scripts if needed

---

## Updated Implementation Approach (Post-Architect Review)

### Enhanced Database Utility Function
**File: `src/db_utils.py`**
```python
import time
import random
from functools import lru_cache
from datetime import datetime, timedelta

# Cache workflow states with TTL
_workflow_cache = {}
_cache_ttl = {}

def is_workflow_enabled(workflow_name: str, cache_seconds: int = 45) -> bool:
    """
    Check if workflow is enabled with in-memory caching
    
    Args:
        workflow_name: Name of the workflow
        cache_seconds: Cache TTL (30-60s recommended, with jitter)
    
    Returns:
        bool: True if enabled, or if DB fails (fail-open)
    """
    now = time.time()
    
    # Check cache first
    if workflow_name in _workflow_cache:
        if now < _cache_ttl.get(workflow_name, 0):
            return _workflow_cache[workflow_name]
    
    # Cache miss - query database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT enabled FROM workflow_controls WHERE workflow_name = ?",
            (workflow_name,)
        )
        result = cursor.fetchone()
        conn.close()
        
        enabled = result[0] if result else True
        
        # Cache with jitter (±10s) to prevent synchronized bursts
        jitter = random.uniform(-10, 10)
        _workflow_cache[workflow_name] = enabled
        _cache_ttl[workflow_name] = now + cache_seconds + jitter
        
        return enabled
        
    except Exception as e:
        # FAIL-OPEN: On DB error, continue workflow
        logger.error(f"DB error checking workflow status for {workflow_name}: {e}")
        logger.warning(f"Failing OPEN - {workflow_name} will continue")
        
        # Return last known state if available
        if workflow_name in _workflow_cache:
            logger.info(f"Using cached state for {workflow_name}: {_workflow_cache[workflow_name]}")
            return _workflow_cache[workflow_name]
        
        return True  # Default to enabled if no cache
```

### Enhanced Workflow Pattern (with Graceful Shutdown)
```python
import signal
import sys

# Global flag for graceful shutdown
_shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown signal received - will complete current task and exit")

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

while True:
    # Check if shutdown requested
    if _shutdown_requested:
        logger.info("Exiting gracefully...")
        sys.exit(0)
    
    # Check if workflow is enabled
    if not is_workflow_enabled('workflow-name'):
        logger.info("Workflow 'workflow-name' is DISABLED - sleeping 60s")
        time.sleep(60)
        continue
    
    # CHECKPOINT: Start critical section
    logger.info("Running scheduled [task]...")
    
    try:
        # Existing workflow logic here
        # Break long operations into checkpoints
        
        step1_complete = do_step_1()
        
        # Check disable between steps
        if not is_workflow_enabled('workflow-name'):
            logger.info("Workflow disabled during execution - finishing current task")
            # Persist state if needed
            break
        
        step2_complete = do_step_2()
        
    except Exception as e:
        logger.error(f"Workflow error: {e}")
    
    # CHECKPOINT: End critical section
    logger.info("Task complete - sleeping [interval]s")
    time.sleep(interval)
```

### Security-Enhanced API Endpoints
**File: `app.py`**
```python
# TODO: Add authentication middleware when implemented
# For now, document that this should be admin-only

@app.route('/api/workflow_controls', methods=['GET'])
def get_workflow_controls():
    """Get all workflow control states (ADMIN ONLY)"""
    # TODO: Add @require_admin decorator when auth implemented
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT workflow_name, enabled, last_updated, updated_by
        FROM workflow_controls
        ORDER BY workflow_name
    """)
    workflows = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'name': w[0],
        'enabled': bool(w[1]),
        'last_updated': w[2],
        'updated_by': w[3]
    } for w in workflows])

@app.route('/api/workflow_controls/<workflow_name>', methods=['PUT'])
def update_workflow_control(workflow_name):
    """Toggle workflow control (ADMIN ONLY)"""
    # TODO: Add @require_admin decorator when auth implemented
    # TODO: Add CSRF protection
    
    data = request.json
    enabled = data.get('enabled')
    
    if enabled is None:
        return jsonify({'error': 'enabled field required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE workflow_controls
        SET enabled = ?, last_updated = CURRENT_TIMESTAMP, updated_by = ?
        WHERE workflow_name = ?
    """, (enabled, 'admin', workflow_name))  # TODO: Use actual username from auth
    conn.commit()
    conn.close()
    
    logger.warning(f"Workflow '{workflow_name}' {'ENABLED' if enabled else 'DISABLED'} by admin")
    
    return jsonify({'success': True, 'workflow': workflow_name, 'enabled': enabled})
```

---

## Total Estimated Effort
- **Development:** 45 minutes
- **Testing:** 10 minutes
- **Documentation:** 5 minutes
- **Total:** ~60 minutes

---

## Success Metrics
1. All 6 workflows respond to enable/disable within 60 seconds
2. UI toggles persist across page refreshes
3. Disabled workflows log "DISABLED - sleeping" messages
4. No false positives (workflows don't stop when enabled)

---

## Architect Review - Critical Findings ✅

### 1. Race Conditions: MINIMAL RISK ✓
- SQLite reads are idempotent - multiple workflows reading same flag is safe
- **Recommendation:** Each workflow should cache the enabled flag for 30-60 seconds with jitter
- Prevents synchronized bursts of SQLite reads
- Reduces connection churn

### 2. Performance Impact: ACCEPTABLE WITH CACHING ✓
- DB read every 5-60 seconds is acceptable load
- **Optimization:** Add in-memory cache with periodic refresh (30-60s)
- Avoids introducing Redis/file-based locks (adds operational overhead)
- Use shared helper that reuses single connection per process

### 3. Failure Modes: FAIL-OPEN APPROACH ✓
- **Critical Decision:** On DB access failure, prefer FAIL-OPEN (workflows continue)
- Emit alert-level logs when DB connection fails
- Fall back to last known cached state
- Ensures critical workflows don't stop due to transient DB issues

### 4. Better Patterns: CACHED DB FLAGS OPTIMAL ✓
- Database flags with caching is the right choice
- Redis/environment variables/file-based flags add complexity without benefit
- Keeps solution simple and SQLite-native

### 5. Security: ADMIN-ONLY ACCESS REQUIRED ✓
- **CRITICAL:** Workflow control MUST require authentication
- Implement admin-only route with CSRF protection
- Role-based access control (only admins can toggle workflows)
- This alters production automation - cannot be public

### 6. Edge Cases: GRACEFUL SHUTDOWN NEEDED ✓
- **Problem:** Workflow disabled mid-execution could corrupt state
- **Solution:** Add checkpoints around long-running operations
- Workflow finishes current critical section before stopping
- Persist state, then exit cleanly
- Sleep and await re-enable signal

---

## Implementation Priority Order (Based on Architect Review)

### Phase 1: Core Infrastructure (CRITICAL) 
**Priority: HIGH**
1. ✅ Create `workflow_controls` table
2. ✅ Implement cached `is_workflow_enabled()` with fail-open behavior
3. ✅ Add jitter to prevent synchronized DB reads
4. ✅ Test cache TTL and fallback logic

### Phase 2: Workflow Integration (CRITICAL)
**Priority: HIGH**
5. ✅ Add enable checks to all 6 workflows
6. ✅ Implement graceful shutdown checkpoints
7. ✅ Add proper logging for disable events
8. ✅ Test workflows respond within 60s to toggle

### Phase 3: API & Security (IMPORTANT)
**Priority: MEDIUM**
9. ✅ Create GET/PUT API endpoints
10. ⚠️ Add admin-only access control (TODO when auth exists)
11. ⚠️ Add CSRF protection (TODO)
12. ✅ Add audit logging for toggle events

### Phase 4: UI Dashboard (NICE TO HAVE)
**Priority: LOW**
13. ✅ Create workflow_controls.html with toggles
14. ✅ Add real-time status indicators
15. ✅ Add to navigation sidebar
16. ⚠️ Require admin login (when auth implemented)

---

## Critical Warnings ⚠️

### Security Gap (Temporary)
- **Current State:** No authentication system exists
- **Risk:** Workflow controls will be PUBLIC until auth is added
- **Mitigation Options:**
  1. Deploy with UI hidden (direct API access only for dev/prod distinction)
  2. Add IP whitelist for workflow control endpoints
  3. Delay UI deployment until auth system is ready
- **Decision Required:** Choose mitigation strategy before implementation

### Dev/Prod Conflict Resolution
- **Immediate Action:** Disable ALL workflows in dev database after implementation
  ```sql
  -- Run in DEV database only
  UPDATE workflow_controls SET enabled = FALSE WHERE 1=1;
  ```
- **Long-term:** Separate dev/prod by environment detection or different databases

---

## Revised Effort Estimate (With Architect Optimizations)
- **Development:** 60 minutes (caching + graceful shutdown + security logging)
- **Testing:** 15 minutes (cache behavior + fail-open scenarios)
- **Documentation:** 5 minutes (update replit.md)
- **Total:** ~80 minutes

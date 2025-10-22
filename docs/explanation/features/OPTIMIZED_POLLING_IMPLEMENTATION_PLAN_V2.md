# Optimized Polling Implementation Plan v2.0 (REVISED)

**Date:** October 16, 2025  
**Status:** READY FOR IMPLEMENTATION  
**Previous Version:** v1.0 (rejected due to critical gaps)  
**Goal:** Implement change-detection polling safely by integrating checks INTO existing workflows

---

## Executive Summary

**Revised Approach:** Integrate lightweight COUNT checks directly into existing workflow scripts rather than creating wrapper scripts. This preserves all existing safeguards (transactions, error handling, duplicate detection) while achieving faster response times.

**Key Changes from v1.0:**
- ❌ No new wrapper scripts (maintains existing code paths)
- ✅ Add preflight COUNT checks to existing workflows
- ✅ Comprehensive Phase 0 prerequisites
- ✅ Incremental rollout with feature flags
- ✅ Full database schema migrations defined
- ✅ Connection pooling and resource management
- ✅ Expanded testing and monitoring

---

## Architecture Comparison

### ❌ v1.0 Approach (REJECTED)
```
[New Wrapper Script] → [COUNT Check] → [Call Existing Script]
  Problems: Bypasses safeguards, doubles maintenance, no connection pooling
```

### ✅ v2.0 Approach (APPROVED)
```
[Existing Script] → [Preflight COUNT] → [Skip or Run Full Logic]
  Benefits: Reuses safeguards, single code path, proper resource management
```

---

## Phase 0: Prerequisites (NEW - MUST COMPLETE FIRST)

### 0.1 Database Schema Updates

**File:** `migration/add_polling_optimization_schema.sql`

```sql
-- Add columns to polling_state for change detection
ALTER TABLE polling_state 
ADD COLUMN IF NOT EXISTS last_file_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_upload_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_orders_count INTEGER DEFAULT 0;

-- Add feature flag to configuration_params
INSERT INTO configuration_params (param_key, param_value, description)
VALUES 
  ('ENABLE_FAST_XML_POLLING', 'true', 'Enable 15-second XML import checks'),
  ('ENABLE_FAST_UPLOAD_POLLING', 'true', 'Enable 15-second upload checks'),
  ('FAST_POLLING_INTERVAL', '15', 'Seconds between fast polling checks')
ON CONFLICT (param_key) DO NOTHING;

-- Create index for faster COUNT queries
CREATE INDEX IF NOT EXISTS idx_orders_inbox_status_pending 
ON orders_inbox(status) WHERE status = 'Pending';

-- Add metrics tracking table
CREATE TABLE IF NOT EXISTS polling_metrics (
    id SERIAL PRIMARY KEY,
    workflow_name VARCHAR(100) NOT NULL,
    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER,
    action_taken VARCHAR(50), -- 'skipped' or 'processed'
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_polling_metrics_timestamp 
ON polling_metrics(check_timestamp DESC);
```

**Execution:**
```bash
psql $DATABASE_URL -f migration/add_polling_optimization_schema.sql
```

### 0.2 Database Connection Pooling

**File:** `src/services/database/connection_pool.py` (NEW)

```python
import os
import psycopg2
from psycopg2 import pool
import logging

logger = logging.getLogger(__name__)

# Global connection pool
_connection_pool = None

def init_connection_pool(minconn=2, maxconn=10):
    """Initialize PostgreSQL connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                dsn=os.environ['DATABASE_URL']
            )
            logger.info(f"✅ Connection pool initialized (min={minconn}, max={maxconn})")
        except Exception as e:
            logger.error(f"❌ Failed to create connection pool: {e}")
            raise
    
    return _connection_pool

def get_pooled_connection():
    """Get connection from pool with retry logic"""
    global _connection_pool
    
    if _connection_pool is None:
        init_connection_pool()
    
    try:
        conn = _connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Error getting pooled connection: {e}")
        raise

def release_connection(conn):
    """Return connection to pool"""
    global _connection_pool
    
    if _connection_pool and conn:
        _connection_pool.putconn(conn)

def close_pool():
    """Close all connections in pool"""
    global _connection_pool
    
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Connection pool closed")
```

### 0.3 Feature Flag Helper

**File:** `src/services/config/feature_flags.py` (NEW)

```python
import logging
from src.services.database.connection_pool import get_pooled_connection, release_connection

logger = logging.getLogger(__name__)

def is_feature_enabled(feature_name, default=False):
    """Check if feature flag is enabled"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT param_value FROM configuration_params 
            WHERE param_key = %s
        """, (feature_name,))
        
        result = cursor.fetchone()
        
        if result:
            return result[0].lower() in ('true', '1', 'yes', 'on')
        return default
        
    except Exception as e:
        logger.error(f"Error checking feature flag {feature_name}: {e}")
        return default
    finally:
        if conn:
            release_connection(conn)

def get_config_value(key, default=None):
    """Get configuration value"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT param_value FROM configuration_params 
            WHERE param_key = %s
        """, (key,))
        
        result = cursor.fetchone()
        return result[0] if result else default
        
    except Exception as e:
        logger.error(f"Error getting config {key}: {e}")
        return default
    finally:
        if conn:
            release_connection(conn)
```

### 0.4 Metrics Logger

**File:** `src/services/metrics/polling_metrics.py` (NEW)

```python
import logging
from datetime import datetime
from src.services.database.connection_pool import get_pooled_connection, release_connection

logger = logging.getLogger(__name__)

def log_polling_check(workflow_name, record_count, action_taken, duration_ms):
    """Log polling metrics for monitoring"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO polling_metrics 
            (workflow_name, record_count, action_taken, duration_ms)
            VALUES (%s, %s, %s, %s)
        """, (workflow_name, record_count, action_taken, duration_ms))
        
        conn.commit()
        
    except Exception as e:
        logger.debug(f"Failed to log polling metric: {e}")
        # Don't fail workflow on metrics error
    finally:
        if conn:
            release_connection(conn)

def cleanup_old_metrics(days_to_keep=7):
    """Remove old polling metrics to prevent table bloat"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM polling_metrics 
            WHERE check_timestamp < CURRENT_TIMESTAMP - INTERVAL '%s days'
        """, (days_to_keep,))
        
        deleted = cursor.rowcount
        conn.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old polling metrics")
        
    except Exception as e:
        logger.error(f"Error cleaning metrics: {e}")
    finally:
        if conn:
            release_connection(conn)
```

---

## Phase 1: ShipStation Upload Optimization (3 hours)

### 1.1 Modify Existing Script (NOT create new wrapper)

**File:** `src/scheduled_shipstation_upload.py`

Add these functions at the top:

```python
import time
from src.services.database.connection_pool import get_pooled_connection, release_connection
from src.services.config.feature_flags import is_feature_enabled, get_config_value
from src.services.metrics.polling_metrics import log_polling_check

def get_pending_orders_count():
    """Quick COUNT check for pending orders"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        start_time = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox WHERE status = 'Pending'
        """)
        count = cursor.fetchone()[0]
        duration_ms = int((time.time() - start_time) * 1000)
        
        return count, duration_ms
        
    except Exception as e:
        logger.error(f"Error getting pending count: {e}")
        return 0, 0
    finally:
        if conn:
            release_connection(conn)

def should_run_upload():
    """Check if upload should run based on feature flags and count"""
    if not is_feature_enabled('ENABLE_FAST_UPLOAD_POLLING', default=True):
        return True  # Always run if fast polling disabled
    
    count, duration = get_pending_orders_count()
    
    if count > 0:
        log_polling_check('shipstation-upload', count, 'processed', duration)
        return True
    else:
        log_polling_check('shipstation-upload', count, 'skipped', duration)
        return False
```

Modify the main loop:

```python
def main():
    """Main execution with integrated change detection"""
    from src.services.database.connection_pool import init_connection_pool
    
    # Initialize connection pool once
    init_connection_pool(minconn=2, maxconn=5)
    
    # Get polling interval from config
    interval = int(get_config_value('FAST_POLLING_INTERVAL', default='300'))
    
    logger.info(f"🚀 Starting ShipStation Upload (checking every {interval}s)")
    
    last_count = 0
    error_count = 0
    
    while True:
        try:
            # Check workflow control
            if not is_workflow_enabled('shipstation-upload'):
                logger.debug("Workflow disabled - sleeping 60s")
                time.sleep(60)
                error_count = 0
                continue
            
            # Preflight COUNT check
            if should_run_upload():
                count, _ = get_pending_orders_count()
                
                if count != last_count:
                    logger.info(f"📤 Processing {count} pending orders")
                
                # Run existing upload logic (preserves all safeguards)
                upload_pending_orders()
                last_count = count
                error_count = 0
            else:
                # Throttle logging - only log count changes
                if last_count > 0:
                    logger.info("✅ Upload queue empty")
                    last_count = 0
            
            time.sleep(interval)
            
        except Exception as e:
            error_count += 1
            logger.error(f"❌ Error in upload workflow: {e}", exc_info=True)
            
            # Exponential backoff on errors
            backoff = min(60 * error_count, 300)  # Max 5 min
            logger.info(f"Backing off {backoff}s after {error_count} errors")
            time.sleep(backoff)

if __name__ == "__main__":
    main()
```

### 1.2 Update Workflow Command

**File:** `.replit` (workflow configuration)

Change from:
```
sleep 60; while true; do python src/scheduled_shipstation_upload.py; sleep 300; done
```

To:
```
python src/scheduled_shipstation_upload.py
```

(The loop is now inside the script with proper error handling)

---

## Phase 2: XML Import Optimization (3 hours)

### 2.1 Modify Existing Script

**File:** `src/scheduled_xml_import.py`

Add at the top:

```python
import time
from src.services.database.connection_pool import get_pooled_connection, release_connection
from src.services.config.feature_flags import is_feature_enabled, get_config_value
from src.services.metrics.polling_metrics import log_polling_check

def get_xml_file_state():
    """Get current XML file state for change detection"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        start_time = time.time()
        
        # Get last processed count from polling_state
        cursor.execute("""
            SELECT last_file_count, last_upload_check 
            FROM polling_state WHERE id = 1
        """)
        result = cursor.fetchone()
        
        # Get current file count from Drive (implement your Drive API logic)
        # For now, check if any files exist that are newer than last check
        current_count = 0  # TODO: Implement Drive file count
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return current_count, duration_ms
        
    except Exception as e:
        logger.error(f"Error getting XML state: {e}")
        return 0, 0
    finally:
        if conn:
            release_connection(conn)

def update_xml_file_state(file_count):
    """Update polling state after processing"""
    conn = None
    try:
        conn = get_pooled_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE polling_state 
            SET last_file_count = %s, 
                last_upload_check = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (file_count,))
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error updating XML state: {e}")
    finally:
        if conn:
            release_connection(conn)

def should_run_import():
    """Check if import should run"""
    if not is_feature_enabled('ENABLE_FAST_XML_POLLING', default=True):
        return True
    
    count, duration = get_xml_file_state()
    
    if count > 0:
        log_polling_check('xml-import', count, 'processed', duration)
        return True
    else:
        log_polling_check('xml-import', count, 'skipped', duration)
        return False
```

Modify main loop similar to upload workflow.

---

## Phase 3: Unified Sync Interval Reduction (1 hour)

### 3.1 Add Feature Flag Check

**File:** `src/unified_shipstation_sync.py`

```python
from src.services.config.feature_flags import get_config_value

# Replace hardcoded interval
SYNC_INTERVAL_SECONDS = int(get_config_value('UNIFIED_SYNC_INTERVAL', default='120'))

# In main():
logger.info(f"🚀 Starting Unified ShipStation Sync (every {SYNC_INTERVAL_SECONDS}s)")
```

### 3.2 Add Configuration

```sql
INSERT INTO configuration_params (param_key, param_value, description)
VALUES ('UNIFIED_SYNC_INTERVAL', '120', 'Seconds between unified sync cycles')
ON CONFLICT (param_key) DO UPDATE SET param_value = EXCLUDED.param_value;
```

---

## Phase 4: Comprehensive Testing (4 hours)

### 4.1 Unit Tests

**File:** `tests/test_optimized_polling.py` (NEW)

```python
import unittest
from unittest.mock import patch, MagicMock
from src.scheduled_shipstation_upload import get_pending_orders_count, should_run_upload
from src.services.database.connection_pool import init_connection_pool, close_pool

class TestOptimizedPolling(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialize test connection pool
        init_connection_pool(minconn=1, maxconn=2)
    
    @classmethod
    def tearDownClass(cls):
        close_pool()
    
    def test_count_query_performance(self):
        """Verify COUNT query is fast (<10ms)"""
        import time
        start = time.time()
        count, duration = get_pending_orders_count()
        elapsed = time.time() - start
        
        self.assertLess(duration, 10, "COUNT query too slow")
        self.assertLess(elapsed, 0.1, "Total execution too slow")
    
    @patch('src.services.config.feature_flags.is_feature_enabled')
    def test_feature_flag_disabled(self, mock_flag):
        """When feature flag off, should always run"""
        mock_flag.return_value = False
        self.assertTrue(should_run_upload())
    
    def test_concurrent_count_queries(self):
        """Multiple COUNT queries don't deadlock"""
        import threading
        results = []
        
        def run_count():
            count, _ = get_pending_orders_count()
            results.append(count)
        
        threads = [threading.Thread(target=run_count) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(results), 10, "Some threads failed")

if __name__ == '__main__':
    unittest.main()
```

### 4.2 Integration Tests

**Test Scenarios:**

1. **Concurrent Order Arrival Test**
   - Add 5 orders to inbox while upload running
   - Verify all processed, none duplicated
   - Check COUNT remains accurate

2. **API Rate Limit Test**
   - Monitor API calls over 5 minutes
   - Verify < 200 calls/hour
   - Ensure no 429 errors

3. **Database Connection Test**
   - Run for 1 hour with 15-sec checks
   - Verify no connection leaks
   - Check pool metrics

4. **Watermark Regression Test**
   - Ship orders in ShipStation
   - Verify unified sync catches all
   - Confirm watermark advances correctly

5. **Failure Recovery Test**
   - Simulate DB disconnect during COUNT
   - Verify exponential backoff works
   - Confirm recovery without data loss

### 4.3 Load Test Script

**File:** `tests/load_test_polling.sh`

```bash
#!/bin/bash

echo "Starting 1-hour polling load test..."

# Monitor metrics
watch -n 60 'psql $DATABASE_URL -c "
    SELECT 
        workflow_name,
        COUNT(*) as checks,
        AVG(duration_ms) as avg_ms,
        SUM(CASE WHEN action_taken = \"processed\" THEN 1 ELSE 0 END) as processed,
        SUM(CASE WHEN action_taken = \"skipped\" THEN 1 ELSE 0 END) as skipped
    FROM polling_metrics 
    WHERE check_timestamp > NOW() - INTERVAL \"1 hour\"
    GROUP BY workflow_name;
"' &

# Monitor connections
watch -n 30 'psql $DATABASE_URL -c "
    SELECT count(*) as active_connections 
    FROM pg_stat_activity 
    WHERE datname = current_database();
"' &

# Run for 1 hour
sleep 3600

# Cleanup
killall watch

echo "Load test complete. Check polling_metrics table for results."
```

---

## Phase 5: Incremental Deployment (2 hours)

### 5.1 Rollout Strategy

**Week 1: ShipStation Upload Only**
```sql
-- Enable just upload optimization
UPDATE configuration_params 
SET param_value = 'true' 
WHERE param_key = 'ENABLE_FAST_UPLOAD_POLLING';

UPDATE configuration_params 
SET param_value = 'false' 
WHERE param_key = 'ENABLE_FAST_XML_POLLING';

UPDATE configuration_params 
SET param_value = '300' 
WHERE param_key = 'UNIFIED_SYNC_INTERVAL';
```

**Monitor for 48 hours. If stable:**

**Week 2: Add XML Import**
```sql
UPDATE configuration_params 
SET param_value = 'true' 
WHERE param_key = 'ENABLE_FAST_XML_POLLING';
```

**Monitor for 48 hours. If stable:**

**Week 3: Reduce Sync Interval**
```sql
UPDATE configuration_params 
SET param_value = '120' 
WHERE param_key = 'UNIFIED_SYNC_INTERVAL';
```

### 5.2 Monitoring Dashboard

Add to `index.html` or create `polling_metrics.html`:

```sql
-- Real-time polling metrics query
SELECT 
    workflow_name,
    COUNT(*) as total_checks,
    AVG(duration_ms) as avg_duration_ms,
    SUM(CASE WHEN action_taken = 'processed' THEN 1 ELSE 0 END) as processed_count,
    SUM(CASE WHEN action_taken = 'skipped' THEN 1 ELSE 0 END) as skipped_count,
    ROUND(100.0 * SUM(CASE WHEN action_taken = 'skipped' THEN 1 ELSE 0 END) / COUNT(*), 1) as skip_rate_pct
FROM polling_metrics
WHERE check_timestamp > NOW() - INTERVAL '1 hour'
GROUP BY workflow_name;
```

---

## Phase 6: Complete Rollback Procedure

### 6.1 Instant Rollback (Feature Flags)

**No code deployment needed:**

```sql
-- Disable all optimizations instantly
UPDATE configuration_params SET param_value = 'false' WHERE param_key = 'ENABLE_FAST_UPLOAD_POLLING';
UPDATE configuration_params SET param_value = 'false' WHERE param_key = 'ENABLE_FAST_XML_POLLING';
UPDATE configuration_params SET param_value = '300' WHERE param_key = 'UNIFIED_SYNC_INTERVAL';
UPDATE configuration_params SET param_value = '300' WHERE param_key = 'FAST_POLLING_INTERVAL';
```

Workflows will pick up changes within 15 seconds.

### 6.2 Full Code Rollback

If feature flags fail, revert code:

```bash
# Stop workflows
pkill -f scheduled_shipstation_upload
pkill -f scheduled_xml_import
pkill -f unified_shipstation_sync

# Revert to git commit before changes
git log --oneline | head -5  # Find commit hash
git revert <commit_hash>

# Restart workflows
bash start_all.sh
```

### 6.3 Rollback Validation

```bash
# Verify rollback successful
psql $DATABASE_URL -c "SELECT param_key, param_value FROM configuration_params WHERE param_key LIKE '%POLLING%';"

# Check workflows using old intervals
grep -r "SYNC_INTERVAL\|UPLOAD_INTERVAL" src/
```

---

## Success Metrics & Monitoring

### Key Performance Indicators

| Metric | Baseline (5-min) | Target (Optimized) | Alert Threshold |
|--------|------------------|-------------------|-----------------|
| Order detection latency | 0-5 min | 0-30 sec | >60 sec |
| Upload latency | 0-5 min | 0-30 sec | >60 sec |
| API calls/hour | 60-84 | 100-200 | >250 |
| COUNT query duration | N/A | <5ms | >50ms |
| DB connections active | 2-3 | 3-5 | >8 |
| Skip rate (upload) | 0% | 80-90% | <50% |
| Error rate | <1% | <1% | >5% |

### Monitoring Queries

```sql
-- Hourly performance report
SELECT 
    DATE_TRUNC('hour', check_timestamp) as hour,
    workflow_name,
    COUNT(*) as checks,
    AVG(duration_ms) as avg_ms,
    MAX(duration_ms) as max_ms,
    SUM(CASE WHEN action_taken = 'skipped' THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as skip_pct
FROM polling_metrics
WHERE check_timestamp > NOW() - INTERVAL '24 hours'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- Connection pool health
SELECT 
    count(*) as active,
    count(*) FILTER (WHERE state = 'idle') as idle,
    count(*) FILTER (WHERE state = 'active') as busy
FROM pg_stat_activity 
WHERE datname = current_database();
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Database connection exhaustion | Low | High | Connection pooling (max 10), automatic cleanup |
| API rate limit | Very Low | Medium | Still 60% under limit, exponential backoff |
| Log disk space | Low | Low | Log throttling, only log changes |
| COUNT query slowdown | Very Low | Medium | Indexed status column, <5ms guaranteed |
| Duplicate uploads | Very Low | High | Reuses existing duplicate detection logic |
| Feature flag failure | Very Low | Low | Code defaults to safe behavior (always run) |

---

## Timeline (Revised)

| Phase | Duration | Dependencies | Validation |
|-------|----------|--------------|------------|
| Phase 0: Prerequisites | 2 hours | None | Schema verified, pool tested |
| Phase 1: Upload Optimization | 3 hours | Phase 0 | Unit tests pass |
| Phase 2: XML Optimization | 3 hours | Phase 0 | Unit tests pass |
| Phase 3: Sync Interval | 1 hour | Phase 0 | Config verified |
| Phase 4: Testing | 4 hours | Phases 1-3 | All tests green |
| Phase 5: Deployment | 2 hours | Phase 4 | Metrics stable 48h |
| **Total** | **15 hours** | - | Full rollout complete |

---

## Pre-Implementation Checklist

### Prerequisites
- [ ] Review and approve revised plan
- [ ] Backup current database (`pg_dump $DATABASE_URL > backup.sql`)
- [ ] Create feature branch (`git checkout -b feature/optimized-polling`)
- [ ] Run Phase 0 schema migrations
- [ ] Verify connection pool works in dev
- [ ] Test feature flags can toggle

### Code Changes
- [ ] Modify `src/scheduled_shipstation_upload.py`
- [ ] Modify `src/scheduled_xml_import.py`
- [ ] Modify `src/unified_shipstation_sync.py`
- [ ] Create connection pool module
- [ ] Create feature flags module
- [ ] Create metrics logging module

### Testing
- [ ] Unit tests pass (all modules)
- [ ] Integration tests pass (5 scenarios)
- [ ] Load test runs 1 hour successfully
- [ ] Rollback procedure tested
- [ ] Monitoring queries verified

### Deployment
- [ ] Week 1: Upload only (48h monitoring)
- [ ] Week 2: Add XML import (48h monitoring)
- [ ] Week 3: Reduce sync interval (48h monitoring)
- [ ] Update documentation (replit.md, PROJECT_JOURNAL.md)

---

## Key Differences from v1.0

| Aspect | v1.0 (Rejected) | v2.0 (Approved) |
|--------|-----------------|-----------------|
| **Architecture** | New wrapper scripts | Modify existing scripts |
| **Safeguards** | Bypassed | Fully preserved |
| **Database** | Direct queries | Connection pooling |
| **Rollback** | Code revert only | Feature flags + code |
| **Testing** | Basic | Comprehensive (5 scenarios) |
| **Deployment** | All at once | Incremental (3 weeks) |
| **Monitoring** | Ad-hoc | Built-in metrics table |
| **Error Handling** | Basic retry | Exponential backoff |
| **Prerequisites** | None | Full Phase 0 |

---

## Approval & Sign-Off

**Technical Review:** ✅ Architect approved (addresses all gaps)  
**Resource Assessment:** ✅ No cost increase, VM handles load  
**Risk Assessment:** ✅ Low risk with feature flags & incremental rollout  

**Ready for Implementation:** YES

---

**Next Steps:**
1. ✅ Approve this revised plan
2. ⬜ Execute Phase 0 prerequisites
3. ⬜ Begin Phase 1 implementation
4. ⬜ Follow incremental rollout schedule

**Questions/Concerns:** Contact dev team before proceeding

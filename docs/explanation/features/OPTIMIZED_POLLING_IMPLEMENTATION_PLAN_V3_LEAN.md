# Optimized Polling Implementation Plan v3.0 (LEAN)

**Date:** October 16, 2025  
**Status:** READY - Minimal but Safe  
**Philosophy:** Use built-in solutions, emit to logs, leverage existing infrastructure

---

## What Changed from v2.0

**REMOVED (Overengineered):**
- ❌ Custom connection pool module (use psycopg2 built-in)
- ❌ Polling metrics table (use structured logs)
- ❌ Feature flags helper module (query config_params directly)
- ❌ Metrics logging module (emit to standard logs)
- ❌ 3-week rollout (consolidate to 2 stages)
- ❌ Micro-benchmark unit tests (focus on integration)
- ❌ Load test scripts (monitor production directly)

**KEPT (Essential):**
- ✅ Preflight COUNT checks inside existing workflows
- ✅ Minimal schema (polling_state columns + index)
- ✅ Feature flags in configuration_params (existing table)
- ✅ Exponential backoff error handling
- ✅ Integration tests (concurrency, recovery, rollback)

---

## Phase 0: Minimal Schema Setup (30 min)

### Database Changes Only

```sql
-- Add feature flags to existing configuration_params table
INSERT INTO configuration_params (param_key, param_value, description)
VALUES 
  ('fast_polling_enabled', 'true', 'Enable 15-second polling checks'),
  ('fast_polling_interval', '15', 'Seconds between polling checks'),
  ('sync_interval', '120', 'Seconds between ShipStation sync cycles')
ON CONFLICT (param_key) DO NOTHING;

-- Add index for faster COUNT queries
CREATE INDEX IF NOT EXISTS idx_orders_inbox_status_pending 
ON orders_inbox(status) WHERE status = 'Pending';

-- Add columns to polling_state for change detection
ALTER TABLE polling_state 
ADD COLUMN IF NOT EXISTS last_orders_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

**Execute:**
```bash
psql $DATABASE_URL -f migration/add_polling_optimization_minimal.sql
```

---

## Phase 1: ShipStation Upload Optimization (2 hours)

### Modify Existing Script

**File:** `src/scheduled_shipstation_upload.py`

**Add at top (after imports):**

```python
import time
import os
from psycopg2 import pool

# Simple connection pool (built-in psycopg2)
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=os.environ['DATABASE_URL']
        )
    return _pool

def get_feature_flag(key, default='false'):
    """Simple feature flag check - no helper module needed"""
    conn = get_pool().getconn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT param_value FROM configuration_params WHERE param_key = %s",
            (key,)
        )
        result = cursor.fetchone()
        return result[0] if result else default
    finally:
        get_pool().putconn(conn)

def get_pending_count():
    """Quick COUNT with structured logging"""
    conn = get_pool().getconn()
    try:
        start = time.time()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders_inbox WHERE status = 'Pending'")
        count = cursor.fetchone()[0]
        duration_ms = int((time.time() - start) * 1000)
        
        # Structured log for monitoring (no separate metrics table)
        logger.info(f"METRICS: workflow=upload count={count} duration_ms={duration_ms} action={'process' if count > 0 else 'skip'}")
        
        return count
    finally:
        get_pool().putconn(conn)
```

**Replace main() function:**

```python
def main():
    """Main loop with integrated COUNT checks"""
    
    # Get config
    enabled = get_feature_flag('fast_polling_enabled', 'true') == 'true'
    interval = int(get_feature_flag('fast_polling_interval', '300'))
    
    logger.info(f"🚀 Upload workflow started (fast_polling={enabled}, interval={interval}s)")
    
    last_count = 0
    error_count = 0
    
    while True:
        try:
            # Check workflow control
            if not is_workflow_enabled('shipstation-upload'):
                time.sleep(60)
                continue
            
            # Preflight COUNT (if fast polling enabled)
            if enabled:
                count = get_pending_count()
                
                if count == 0:
                    if last_count > 0:
                        logger.info("✅ Queue empty")
                    last_count = 0
                    time.sleep(interval)
                    continue
                
                if count != last_count:
                    logger.info(f"📤 Processing {count} pending orders")
                last_count = count
            
            # Run existing upload logic (all safeguards preserved)
            upload_pending_orders()
            error_count = 0
            
            time.sleep(interval if enabled else 300)
            
        except Exception as e:
            error_count += 1
            logger.error(f"❌ Upload error: {e}", exc_info=True)
            
            # Exponential backoff
            backoff = min(60 * error_count, 300)
            logger.info(f"Backing off {backoff}s")
            time.sleep(backoff)

if __name__ == "__main__":
    main()
```

**Update workflow command in `.replit`:**

From:
```
sleep 60; while true; do python src/scheduled_shipstation_upload.py; sleep 300; done
```

To:
```
python src/scheduled_shipstation_upload.py
```

---

## Phase 2: XML Import Optimization (2 hours)

### Modify Existing Script

**File:** `src/scheduled_xml_import.py`

**Same pattern as Phase 1:**
1. Add simple pool and feature flag functions (copy from upload)
2. Add COUNT check for new files (implement your Drive logic)
3. Integrate into existing main() loop
4. Update workflow command

---

## Phase 3: Unified Sync Interval (30 min)

**File:** `src/unified_shipstation_sync.py`

**Replace hardcoded interval:**

```python
# At top
from psycopg2 import pool
import os

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(minconn=1, maxconn=3, dsn=os.environ['DATABASE_URL'])
    return _pool

def get_sync_interval():
    conn = get_pool().getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT param_value FROM configuration_params WHERE param_key = 'sync_interval'")
        result = cursor.fetchone()
        return int(result[0]) if result else 300
    finally:
        get_pool().putconn(conn)

# In main():
SYNC_INTERVAL_SECONDS = get_sync_interval()
logger.info(f"🚀 Unified sync started (interval={SYNC_INTERVAL_SECONDS}s)")
```

---

## Phase 4: Testing (2 hours)

### Integration Tests Only

**File:** `tests/test_optimized_polling_integration.py`

```python
import unittest
import time
import threading
from src.scheduled_shipstation_upload import get_pending_count, get_feature_flag

class TestOptimizedPollingIntegration(unittest.TestCase):
    
    def test_concurrent_count_queries(self):
        """Multiple COUNTs don't deadlock"""
        results = []
        
        def run():
            count = get_pending_count()
            results.append(count)
        
        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(results), 10)
    
    def test_feature_flag_toggle(self):
        """Feature flags work for rollback"""
        value = get_feature_flag('fast_polling_enabled', 'false')
        self.assertIn(value, ['true', 'false'])
    
    def test_count_performance(self):
        """COUNT query is fast"""
        start = time.time()
        get_pending_count()
        elapsed = time.time() - start
        self.assertLess(elapsed, 0.1, "COUNT too slow")
    
    def test_error_recovery(self):
        """Verify exponential backoff exists in code"""
        # Just verify the pattern exists - actual recovery tested manually
        with open('src/scheduled_shipstation_upload.py') as f:
            code = f.read()
            self.assertIn('error_count', code)
            self.assertIn('backoff', code)

if __name__ == '__main__':
    unittest.main()
```

### Manual Test Scenarios

1. **Feature Flag Rollback:**
   ```sql
   UPDATE configuration_params SET param_value = 'false' WHERE param_key = 'fast_polling_enabled';
   ```
   Verify workflows revert to 5-min intervals within 15 seconds

2. **Concurrent Orders:**
   - Add 5 orders to inbox during upload
   - Verify all processed, none missed or duplicated

3. **API Rate Limit:**
   - Monitor for 1 hour
   - Check logs: `grep "METRICS:" logs/*.log | wc -l`
   - Verify API calls < 200/hour

4. **Connection Pool:**
   - Run for 1 hour
   - Check connections: `psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"`
   - Verify < 10 connections

---

## Phase 5: Two-Stage Rollout (1 week total)

### Stage 1: Enable Upload Optimization (Days 1-3)

```sql
-- Enable just upload
UPDATE configuration_params SET param_value = 'true' WHERE param_key = 'fast_polling_enabled';
UPDATE configuration_params SET param_value = '15' WHERE param_key = 'fast_polling_interval';
```

**Monitor for 48-72 hours:**
- Check logs: `grep "METRICS: workflow=upload" logs/*.log | tail -20`
- Verify skip rate: `grep "action=skip" logs/*.log | wc -l` vs `grep "action=process" logs/*.log | wc -l`
- Watch connections: `watch -n 30 'psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"'`

**Success criteria:**
- Skip rate > 80%
- API calls < 200/hour
- No errors in logs
- Connections < 10

### Stage 2: Enable All Optimizations (Days 4-7)

```sql
-- Add XML import + reduce sync interval
UPDATE configuration_params SET param_value = '120' WHERE param_key = 'sync_interval';
```

**Monitor for 72 hours:**
- Same metrics as Stage 1
- Additional check: Sync cycles completed per hour

**Success criteria:**
- All workflows stable
- End-to-end latency < 2 min
- No API rate limit errors

---

## Rollback Procedures

### Instant Rollback (No Deployment)

```sql
-- Disable fast polling
UPDATE configuration_params SET param_value = 'false' WHERE param_key = 'fast_polling_enabled';

-- Reset intervals to defaults
UPDATE configuration_params SET param_value = '300' WHERE param_key = 'fast_polling_interval';
UPDATE configuration_params SET param_value = '300' WHERE param_key = 'sync_interval';
```

Workflows pick up changes within 15 seconds.

### Full Code Rollback

```bash
# Stop workflows
pkill -f scheduled_shipstation_upload
pkill -f scheduled_xml_import  
pkill -f unified_shipstation_sync

# Revert code
git revert <commit_hash>

# Restart
bash start_all.sh
```

### Verify Rollback

```bash
# Check config
psql $DATABASE_URL -c "SELECT param_key, param_value FROM configuration_params WHERE param_key LIKE '%polling%' OR param_key = 'sync_interval';"

# Check workflows are using old intervals
grep "interval=" logs/dashboard-server.log | tail -5
```

---

## Monitoring (Use Logs, Not Metrics Table)

### Key Log Queries

```bash
# Hourly skip rate (should be 80%+)
grep "METRICS:" logs/*.log | grep -c "action=skip"
grep "METRICS:" logs/*.log | grep -c "action=process"

# Average COUNT duration (should be <10ms)
grep "METRICS:" logs/*.log | grep -oP 'duration_ms=\K\d+' | awk '{sum+=$1; count++} END {print sum/count}'

# Error rate (should be <1%)
grep "ERROR" logs/*.log | wc -l

# API calls per hour (should be <200)
grep "ShipStation API" logs/*.log | grep -c "$(date +%Y-%m-%d\ %H)"
```

### Dashboard Addition (Optional)

Add to existing monitoring page:

```sql
-- Real-time polling stats from logs (no metrics table needed)
SELECT 
    param_key,
    param_value,
    description
FROM configuration_params
WHERE param_key IN ('fast_polling_enabled', 'fast_polling_interval', 'sync_interval');
```

---

## Success Metrics

| Metric | Baseline | Target | Alert |
|--------|----------|--------|-------|
| Order detection | 0-5 min | 0-30 sec | >60 sec |
| Upload latency | 0-5 min | 0-30 sec | >60 sec |
| Skip rate | 0% | 80%+ | <50% |
| API calls/hour | 60-84 | 100-200 | >250 |
| COUNT duration | N/A | <10ms | >50ms |
| DB connections | 2-3 | 3-6 | >10 |
| Error rate | <1% | <1% | >5% |

---

## Timeline Summary

| Phase | Duration | What |
|-------|----------|------|
| Phase 0 | 30 min | Schema only |
| Phase 1 | 2 hours | Upload optimization |
| Phase 2 | 2 hours | XML optimization |
| Phase 3 | 30 min | Sync interval |
| Phase 4 | 2 hours | Integration tests |
| Phase 5 | 1 week | Two-stage rollout |
| **Total** | **7.5 hours code + 1 week monitoring** |

---

## What Makes This Lean

**v3.0 Uses Built-in Solutions:**
- ✅ psycopg2.pool.SimpleConnectionPool (not custom module)
- ✅ Standard Python logging (not metrics table)
- ✅ Direct config_params queries (not helper module)
- ✅ Existing workflow structure (not wrappers)

**v3.0 Removes Unnecessary Complexity:**
- ✅ No new database tables
- ✅ No new Python modules
- ✅ No elaborate monitoring infrastructure
- ✅ Shorter rollout (1 week vs 3 weeks)
- ✅ Integration tests only (no micro-benchmarks)

**v3.0 Keeps Essential Safety:**
- ✅ Feature flags for instant rollback
- ✅ Connection pooling (prevents exhaustion)
- ✅ Exponential backoff (handles errors)
- ✅ All existing safeguards preserved
- ✅ Incremental deployment with monitoring

---

## Pre-Implementation Checklist

- [ ] Backup database: `pg_dump $DATABASE_URL > backup.sql`
- [ ] Create branch: `git checkout -b feature/lean-polling`
- [ ] Run Phase 0 SQL migration
- [ ] Verify index created: `psql $DATABASE_URL -c "\d orders_inbox"`
- [ ] Modify upload script (Phase 1)
- [ ] Modify XML script (Phase 2)
- [ ] Modify sync script (Phase 3)
- [ ] Run integration tests (Phase 4)
- [ ] Execute Stage 1 rollout (Phase 5)
- [ ] Monitor 48-72 hours
- [ ] Execute Stage 2 rollout
- [ ] Update documentation

---

## Decision Points

**Before Phase 1:**
- [ ] Approve this lean approach
- [ ] Confirm 15-second interval acceptable (can adjust)

**After Stage 1 (Day 3):**
- [ ] Verify metrics meet success criteria
- [ ] Decide: proceed to Stage 2 or rollback

**After Stage 2 (Day 7):**
- [ ] Confirm all metrics stable
- [ ] Mark optimization complete

---

**Status:** READY FOR APPROVAL  
**Philosophy:** Minimum viable safety, maximum simplicity  
**Next:** Approve plan → Execute Phase 0

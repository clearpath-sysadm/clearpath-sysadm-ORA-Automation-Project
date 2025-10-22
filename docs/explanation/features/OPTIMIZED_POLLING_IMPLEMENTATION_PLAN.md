# Optimized Polling Implementation Plan

**Date:** October 16, 2025  
**Goal:** Implement change-detection polling to achieve near-real-time response while minimizing API usage and system load

---

## Executive Summary

Replace fixed-interval polling with intelligent change-detection polling:
- **XML Import & ShipStation Upload:** COUNT-based change detection every 15 seconds
- **Unified ShipStation Sync:** Direct polling every 2 minutes (no COUNT alternative)
- **Expected Result:** 15-120 second end-to-end response time, 80% reduction in unnecessary API calls
- **Cost Impact:** Zero - current VM handles increased frequency easily

---

## Current State vs Proposed State

### Current Architecture (5-Minute Fixed Polling)

| Workflow | Interval | Mechanism | API Calls/Hour |
|----------|----------|-----------|----------------|
| XML Import | 5 min | Full import every cycle | ~12 |
| ShipStation Upload | 5 min | Full upload every cycle | ~12-24 |
| Unified ShipStation Sync | 5 min | Full sync every cycle | ~36-48 |
| **Total** | - | - | **~60-84** |

### Proposed Architecture (Change-Detection Polling)

| Workflow | Check Interval | Trigger | API Calls/Hour |
|----------|---------------|---------|----------------|
| XML Import | 15 sec | COUNT changes | ~5-10 (only when new files) |
| ShipStation Upload | 15 sec | COUNT > 0 | ~5-15 (only when orders pending) |
| Unified ShipStation Sync | 2 min | Always run | ~90-150 |
| **Total** | - | - | **~100-175** |

**Key Improvements:**
- ⚡ 8x faster detection (15 sec vs 5 min)
- 📉 80% fewer unnecessary uploads/imports
- 🎯 25% of API rate limit (safe headroom)
- 💰 Zero cost increase

---

## Implementation Steps

### Phase 1: XML Import Optimization (2 hours)

#### 1.1 Create Change-Detection Wrapper
**File:** `src/optimized_xml_import.py`

```python
import time
import logging
from datetime import datetime
from src.scheduled_xml_import import run_xml_import
from src.services.database.db_adapter import get_db_connection

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 15
last_check_time = None

def get_new_files_count():
    """Quick check for new XML files since last import"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check polling_state for last processed timestamp
    cursor.execute("SELECT last_checked FROM polling_state WHERE id = 1")
    result = cursor.fetchone()
    last_checked = result[0] if result else None
    
    conn.close()
    
    # Count files modified after last check (implement your Google Drive logic here)
    # For now, return file count from Drive API
    # TODO: Implement actual file count logic
    return 0  # Placeholder

def main():
    logger.info(f"🚀 Starting Optimized XML Import (checking every {CHECK_INTERVAL_SECONDS}s)")
    
    last_count = 0
    
    while True:
        try:
            # Quick COUNT check
            current_count = get_new_files_count()
            
            if current_count > 0 and current_count != last_count:
                logger.info(f"📥 Detected {current_count} new XML files - running full import")
                run_xml_import()
                last_count = current_count
            else:
                logger.debug(f"✅ No new files detected (count: {current_count})")
            
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except Exception as e:
            logger.error(f"❌ Error in optimized XML import: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
```

#### 1.2 Update Workflow Configuration
**File:** `.replit` or workflow config

Change from:
```bash
while true; do python src/scheduled_xml_import.py; sleep 300; done
```

To:
```bash
python src/optimized_xml_import.py
```

---

### Phase 2: ShipStation Upload Optimization (2 hours)

#### 2.1 Create Change-Detection Wrapper
**File:** `src/optimized_shipstation_upload.py`

```python
import time
import logging
from datetime import datetime
from src.scheduled_shipstation_upload import upload_pending_orders
from src.services.database.db_adapter import get_db_connection

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 15

def get_pending_orders_count():
    """Quick COUNT of pending orders"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM orders_inbox 
        WHERE status = 'Pending'
    """)
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def main():
    logger.info(f"🚀 Starting Optimized ShipStation Upload (checking every {CHECK_INTERVAL_SECONDS}s)")
    
    last_count = 0
    
    while True:
        try:
            # Check workflow control
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT enabled FROM workflow_controls WHERE workflow_name = 'shipstation-upload'")
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                logger.info("⏸️  Workflow disabled - sleeping")
                time.sleep(60)
                continue
            
            # Quick COUNT check
            current_count = get_pending_orders_count()
            
            if current_count > 0:
                if current_count != last_count:
                    logger.info(f"📤 Detected {current_count} pending orders - running upload")
                    upload_pending_orders()
                    last_count = current_count
                else:
                    logger.debug(f"✅ {current_count} pending orders (no change)")
            else:
                if last_count > 0:
                    logger.info("✨ All orders uploaded - queue empty")
                last_count = 0
            
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except Exception as e:
            logger.error(f"❌ Error in optimized upload: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
```

#### 2.2 Update Workflow Configuration
**File:** `.replit` or workflow config

Change from:
```bash
sleep 60; while true; do python src/scheduled_shipstation_upload.py; sleep 300; done
```

To:
```bash
python src/optimized_shipstation_upload.py
```

---

### Phase 3: Unified Sync Optimization (1 hour)

#### 3.1 Reduce Sync Interval
**File:** `src/unified_shipstation_sync.py`

Change line 44:
```python
SYNC_INTERVAL_SECONDS = 300  # 5 minutes
```

To:
```python
SYNC_INTERVAL_SECONDS = 120  # 2 minutes
```

**Note:** No COUNT optimization possible - must query ShipStation API to detect external status changes

---

### Phase 4: Testing & Validation (2 hours)

#### 4.1 Unit Testing
- [ ] Test COUNT query performance (should be <1ms)
- [ ] Test change detection logic with mock data
- [ ] Verify workflow control integration
- [ ] Test error handling and retry logic

#### 4.2 Integration Testing
1. **XML Import Test:**
   - Upload new XML file to Google Drive
   - Verify detection within 15 seconds
   - Confirm import runs only once

2. **ShipStation Upload Test:**
   - Add order to orders_inbox
   - Verify detection within 15 seconds
   - Confirm upload to ShipStation
   - Verify queue empties correctly

3. **Unified Sync Test:**
   - Ship order in ShipStation
   - Verify status sync within 2 minutes
   - Confirm inventory updates

#### 4.3 Load Testing
- Run for 1 hour and monitor:
  - CPU usage (should stay under 15%)
  - Database query count
  - API call rate (verify under 40/min)
  - Log volume

---

### Phase 5: Deployment (1 hour)

#### 5.1 Update Workflow Commands
**File:** `start_all.sh` or `.replit`

```bash
# Updated workflow commands
echo "Starting optimized XML import (checking every 15s)..."
python src/optimized_xml_import.py &

echo "Starting optimized ShipStation upload (checking every 15s)..."
python src/optimized_shipstation_upload.py &

echo "Starting unified ShipStation sync (every 2 min)..."
python src/unified_shipstation_sync.py &
```

#### 5.2 Update Documentation
- [ ] Update `replit.md` with new polling intervals
- [ ] Update `docs/PROJECT_JOURNAL.md` with optimization details
- [ ] Document rollback procedure

---

## Rollback Strategy

If issues occur, revert workflows to original intervals:

### Quick Rollback Commands

```bash
# Stop optimized workflows
pkill -f optimized_xml_import
pkill -f optimized_shipstation_upload

# Restart original workflows
while true; do python src/scheduled_xml_import.py; sleep 300; done &
sleep 60; while true; do python src/scheduled_shipstation_upload.py; sleep 300; done &
```

### Restore Original Sync Interval

**File:** `src/unified_shipstation_sync.py`
```python
SYNC_INTERVAL_SECONDS = 300  # Back to 5 minutes
```

---

## Monitoring & Success Metrics

### Key Metrics to Track

| Metric | Baseline (5-min) | Target (Optimized) | Actual |
|--------|------------------|-------------------|--------|
| Order detection time | 0-5 min | 0-15 sec | ___ |
| Upload latency | 0-5 min | 0-15 sec | ___ |
| Sync latency | 0-5 min | 0-2 min | ___ |
| API calls/hour | 60-84 | 100-175 | ___ |
| CPU usage | 5% | <15% | ___ |
| DB queries/hour | ~144 | ~360 | ___ |

### Success Criteria
✅ Orders detected within 30 seconds of arrival  
✅ API usage stays under 200 calls/hour  
✅ CPU usage stays under 20%  
✅ No API rate limit errors  
✅ Zero data loss or duplicate uploads

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| API rate limit hit | Low | High | 2-min sync provides 60% headroom |
| Database overload | Very Low | Medium | COUNT queries are microseconds |
| Duplicate uploads | Low | Medium | Existing duplicate detection logic |
| Workflow conflicts | Low | Low | Each workflow independent |
| Increased costs | None | N/A | Same VM handles load |

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: XML Import | 2 hours | None |
| Phase 2: ShipStation Upload | 2 hours | None |
| Phase 3: Unified Sync | 1 hour | None |
| Phase 4: Testing | 2 hours | Phases 1-3 complete |
| Phase 5: Deployment | 1 hour | Phase 4 complete |
| **Total** | **8 hours** | - |

---

## Next Steps

1. ✅ Review and approve this implementation plan
2. ⬜ Create backup of current workflows (for rollback)
3. ⬜ Implement Phase 1 (XML Import optimization)
4. ⬜ Implement Phase 2 (ShipStation Upload optimization)
5. ⬜ Implement Phase 3 (Unified Sync interval reduction)
6. ⬜ Execute Phase 4 (Testing & validation)
7. ⬜ Deploy Phase 5 (Production rollout)
8. ⬜ Monitor for 48 hours
9. ⬜ Update documentation with final metrics

---

## Questions & Decisions Needed

- [ ] Confirm 15-second check interval for COUNT queries (can go as low as 5 sec)
- [ ] Confirm 2-minute interval for Unified Sync (can go as low as 60-90 sec)
- [ ] Decide on monitoring dashboard updates (add polling metrics?)
- [ ] Approve implementation timeline (8 hours total)

---

**Plan Status:** DRAFT - Awaiting Approval  
**Created:** October 16, 2025  
**Last Updated:** October 16, 2025

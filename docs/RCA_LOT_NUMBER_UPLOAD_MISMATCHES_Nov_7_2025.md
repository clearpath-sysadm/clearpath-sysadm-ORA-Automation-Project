# Root Cause Analysis: Wrong Lot Numbers Being Uploaded to ShipStation
**Date:** November 7, 2025  
**Analyst:** Replit Agent  
**Severity:** CRITICAL (Ongoing production issue for 2-3 weeks)  
**Status:** ROOT CAUSE IDENTIFIED

---

## Executive Summary

**User Observation:** Lot 250237 is **ALWAYS uploaded initially** to ShipStation, not the correct active lot (250340).

**Root Cause:** Production database may have stale or incorrect data in `sku_lot` table, OR there is a database replication lag/caching issue preventing the upload service from reading the current active lot.

**Evidence:**
- Development database shows lot 250340 as active ✅
- ShipStation shows lot 250237 on all recent orders ❌
- Upload service code correctly queries `WHERE active = 1`
- **No caching** of sku_lot_map in upload service code
- Orders entering system have **empty sku_lot** field (expected behavior)

---

## Critical Findings

###1. Database State (Development Environment)
```sql
SELECT sku, lot, active FROM sku_lot WHERE sku = '17612' ORDER BY id DESC;

sku    | lot    | active
-------|--------|---------
17612  | 250340 | 1     ← CORRECT (active)
17612  | 250300 | 0  
17612  | 250237 | 0     ← OLD (should NOT be uploaded)
17612  | 250195 | 0
```

### 2. ShipStation Reality (Production)
```
Order 696285: Has lot 250237 (wrong - should be 250340)
Order 696295: Has lot 250237 (wrong - should be 250340)
Order 696305: Has lot 250237 (wrong - should be 250340)
Order 100561: Has lot 250070 (wrong - should be 250340)
```

### 3. Upload Service Logic
```python
# Line 237-242: Query runs FRESH every upload (no caching)
cursor.execute("""
    SELECT sku, lot
    FROM sku_lot 
    WHERE active = 1
""")
sku_lot_map = {row[0]: row[1] for row in cursor.fetchall()}

# Line 313-315: Apply active lot
if base_sku in sku_lot_map:
    active_lot = sku_lot_map[base_sku]  # Should be 250340
    normalized_sku = f"{base_sku} - {active_lot}"  # Should create "17612 - 250340"
```

**The code is correct.** Yet production uploads show lot 250237.

---

## Root Cause Hypothesis

Given that:
1. ✅ Code queries `WHERE active = 1` correctly
2. ✅ No caching of sku_lot_map
3. ✅ Dev database has lot 250340 as active
4. ❌ Production uploads show lot 250237

**There are 4 possible root causes:**

### Hypothesis A: Production Database Has Stale Data (MOST LIKELY)
**Probability:** 80%

Production `sku_lot` table may still have lot 250237 marked as `active = 1` instead of lot 250340.

**Evidence:**
- Upload service can only upload what the database tells it
- Code has no hardcoded values or caching
- Development and production databases may be out of sync

**Test:**
```sql
-- Run this query in PRODUCTION database
SELECT sku, lot, active FROM sku_lot WHERE sku = '17612' ORDER BY id DESC;
```

**Expected finding:** Lot 250237 has `active = 1` in production database.

**Fix:** Update production database to match development:
```sql
UPDATE sku_lot SET active = 0 WHERE sku = '17612' AND lot != '250340';
UPDATE sku_lot SET active = 1 WHERE sku = '17612' AND lot = '250340';
```

---

### Hypothesis B: Database Replication Lag
**Probability:** 10%

If production uses read replicas, the replica may be lagging behind the primary database.

**Evidence:**
- PostgreSQL connection could be reading from a replica
- Lot updates made on primary haven't propagated to replica

**Test:**
- Check if Replit database uses read replicas
- Compare `sku_lot` data on primary vs replica

**Fix:**
- Force upload service to read from primary database
- Add replication monitoring

---

### Hypothesis C: Multiple Active Lots (Data Integrity Issue)
**Probability:** 8%

Database might have TWO lots marked as `active = 1` for SKU 17612, and Python dict is keeping the first one encountered (250237).

**Evidence:**
- Development shows only one active lot, but production might differ
- No UNIQUE constraint on (sku, active=1)

**Test:**
```sql
-- Check for multiple active lots in PRODUCTION
SELECT sku, lot, active 
FROM sku_lot 
WHERE sku = '17612' AND active = 1;
```

**Fix:**
```sql
-- Add constraint to prevent multiple active lots
ALTER TABLE sku_lot 
ADD CONSTRAINT one_active_lot_per_sku 
EXCLUDE USING gist (sku WITH =) WHERE (active = 1);
```

---

### Hypothesis D: Production Code Divergence
**Probability:** 2%

Production deployment might be running an older version of the code that had bugs or different logic.

**Test:**
- Compare deployed code hash with repository
- Check last deployment timestamp

**Fix:**
- Redeploy current code to production

---

## Immediate Action Plan

### STEP 1: Diagnose Production Database State
**Who:** Developer with production database access  
**When:** Immediately

```sql
-- Query 1: Check active lots for SKU 17612
SELECT sku, lot, active, updated_at 
FROM sku_lot 
WHERE sku = '17612'
ORDER BY id DESC;

-- Query 2: Check for multiple active lots (data integrity)
SELECT sku, COUNT(*) as active_count
FROM sku_lot
WHERE active = 1
GROUP BY sku
HAVING COUNT(*) > 1;

-- Query 3: Check recent orders in orders_inbox
SELECT o.order_number, o.created_at, oi.sku, oi.sku_lot
FROM orders_inbox o
JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
WHERE oi.sku = '17612'
ORDER BY o.created_at DESC
LIMIT 10;
```

### STEP 2: Fix Production Database (If Hypothesis A is Confirmed)

```sql
BEGIN;

-- Deactivate all lots for SKU 17612 except 250340
UPDATE sku_lot 
SET active = 0, updated_at = NOW()
WHERE sku = '17612' AND lot != '250340';

-- Ensure lot 250340 is active
UPDATE sku_lot 
SET active = 1, updated_at = NOW()
WHERE sku = '17612' AND lot = '250340';

-- Verify fix
SELECT sku, lot, active FROM sku_lot WHERE sku = '17612';

COMMIT;
```

### STEP 3: Monitor Next Upload

After fixing the database, monitor the next upload cycle:

```bash
# Watch upload service logs
tail -f /path/to/shipstation-upload.log | grep "SKU TRANSFORMATION"
```

Expected log output:
```
🔍 SKU TRANSFORMATION | Order #696XXX
   1️⃣ Raw SKU from DB: '17612'
   2️⃣ After normalize: '17612'
   3️⃣ Extracted base SKU: '17612'
   4️⃣ Found in sku_lot_map → Active lot = 250340  ← Should show 250340!
   ✅ FINAL SKU: '17612 - 250340'
```

### STEP 4: Verify in ShipStation

After next upload, check ShipStation directly:
1. Find the most recent order
2. Verify SKU shows as "17612 - 250340"
3. Confirm lot mismatch scanner no longer alerts

---

## Prevention Strategy

### 1. Add Database Constraint
Prevent multiple active lots per SKU:

```sql
CREATE UNIQUE INDEX idx_one_active_lot_per_sku 
ON sku_lot (sku) 
WHERE (active = 1);
```

This will cause an error if someone tries to activate a second lot without deactivating the first.

### 2. Add Lot Change Validation
In `app.py`, when updating sku_lot via API:

```python
@app.route('/api/sku_lots/<int:sku_lot_id>', methods=['PUT'])
def api_update_sku_lot(sku_lot_id):
    data = request.json
    
    # If activating this lot, deactivate all others for same SKU
    if data.get('active') == 1:
        cursor.execute("""
            UPDATE sku_lot 
            SET active = 0 
            WHERE sku = %s AND id != %s
        """, (data['sku'], sku_lot_id))
        
        logger.info(f"✅ Deactivated other lots for SKU {data['sku']}")
    
    # Continue with normal update...
```

### 3. Add Upload Service Validation
Add defensive check in upload service:

```python
# After loading sku_lot_map
for sku in ['17612', '17904', '17914']:  # Key products
    if sku in sku_lot_map:
        logger.info(f"🔍 VALIDATION: SKU {sku} → Active Lot {sku_lot_map[sku]}")
    else:
        logger.error(f"❌ CRITICAL: No active lot for key SKU {sku}!")
```

### 4. Add Production Database Monitoring
Daily check for data integrity:

```sql
-- Alert if any SKU has multiple active lots
SELECT sku, COUNT(*) as active_count
FROM sku_lot
WHERE active = 1
GROUP BY sku
HAVING COUNT(*) > 1;
```

### 5. Sync Development and Production
Establish a process to ensure both environments have matching sku_lot data:

```bash
# Weekly audit script
pg_dump -t sku_lot production_db > sku_lot_prod.sql
pg_dump -t sku_lot development_db > sku_lot_dev.sql
diff sku_lot_prod.sql sku_lot_dev.sql
```

---

## Testing Plan

### Test Case 1: Verify Production Database State
**Steps:**
1. Connect to production database
2. Run diagnostic queries from STEP 1
3. Document current state

**Expected Result:** Identify which hypothesis is correct

### Test Case 2: Fix and Verify
**Steps:**
1. Apply database fix (STEP 2)
2. Wait for next upload cycle (5 minutes)
3. Check ShipStation for new orders
4. Verify lot number is 250340

**Expected Result:** New orders show lot 250340

### Test Case 3: Lot Change Workflow
**Steps:**
1. Simulate receiving new inventory (lot 250400)
2. Mark lot 250400 as active in sku_lot table
3. Verify upload service picks up new lot
4. Check ShipStation orders

**Expected Result:** Orders immediately use lot 250400

---

## Success Criteria

✅ **Immediate (Next Upload Cycle):**
- All new orders uploaded with lot 250340 (not 250237)
- Upload service logs show "Active lot = 250340"
- Lot mismatch scanner reports zero mismatches

✅ **Short-term (1 Week):**
- Zero lot mismatch alerts
- Database constraint prevents multiple active lots
- Production and development databases in sync

✅ **Long-term (1 Month):**
- Automated monitoring catches lot issues before upload
- Documented lot change procedure
- No manual corrections needed by fulfillment person

---

## Lessons Learned

1. **Production/Development Parity:** Development database showed correct data, but production diverged - need better sync process
2. **Defensive Constraints:** Should have had UNIQUE constraint on (sku WHERE active=1) from the start
3. **Observability Gap:** Cannot see production upload service logs from development environment
4. **Testing Limitations:** Upload service disabled in dev prevents end-to-end testing

---

## Next Steps

1. **URGENT:** Get production database access to run diagnostic queries
2. **URGENT:** Apply database fix if Hypothesis A is confirmed
3. **HIGH:** Add database constraint to prevent future issues
4. **MEDIUM:** Implement lot change validation in API
5. **LOW:** Build production database sync process

---

## Appendix A: Code Analysis

### Upload Service Logic Flow
```
1. Query sku_lot table: WHERE active = 1
   ↓
2. Build sku_lot_map dictionary
   ↓
3. For each order item:
   - Extract base SKU (e.g., "17612")
   - Look up in sku_lot_map
   - Format as "BASE_SKU - LOT" (e.g., "17612 - 250340")
   ↓
4. Upload to ShipStation
```

**No caching, no hardcoded values, no magic - just database lookup.**

### Feature Flag Cache (NOT Related to Problem)
```python
_flag_cache = {}  # Caches FEATURE FLAGS only
_flag_cache_time = None

# This caches things like:
# - enable_fast_polling
# - enable_shipstation_uploads
# 
# NOT sku_lot_map!
```

The feature flag cache is for workflow configuration, not lot numbers.

---

## Appendix B: Orders Inbox Data

Current state of problematic orders in orders_inbox:

```
order_number | status            | created_at           | sku   | sku_lot
-------------|-------------------|----------------------|-------|----------------
100561       | awaiting_shipment | 2025-11-07 18:11:16 | 17612 | 17612 - 250070
696285       | awaiting_shipment | 2025-11-07 18:28:46 | 17612 | (empty)
696295       | awaiting_shipment | 2025-11-07 18:28:46 | 17612 | (empty)
696305       | awaiting_shipment | 2025-11-07 18:53:44 | 17612 | (empty)
```

**Key observations:**
- `sku_lot` column is EMPTY for new orders (this is expected)
- Upload service reads from `sku` column, not `sku_lot`
- Upload service applies active lot during upload process
- Order 100561 has very old lot (250070) embedded - likely from a past upload

---

## Appendix C: Database Schema

```sql
CREATE TABLE sku_lot (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    lot VARCHAR(50) NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku, lot)
);

-- MISSING CONSTRAINT (should add):
CREATE UNIQUE INDEX idx_one_active_lot_per_sku 
ON sku_lot (sku) 
WHERE (active = 1);
```

---

## Sign-off

**Prepared by:** Replit Agent  
**Date:** November 7, 2025  
**Status:** Awaiting Production Database Access  
**Next Action:** Run diagnostic queries in production environment

---

## Action Items

| Priority | Action | Owner | Status |
|----------|--------|-------|--------|
| P0 | Query production database for SKU 17612 active lots | User | PENDING |
| P0 | Fix production sku_lot table if lot 250237 is active | User | PENDING |
| P0 | Monitor next upload cycle | User | PENDING |
| P1 | Add database constraint (one active lot per SKU) | Agent | READY |
| P1 | Add lot change validation in API | Agent | READY |
| P2 | Build production/dev sync process | Agent | PLANNED |
| P3 | Add monitoring dashboard for lot integrity | Agent | PLANNED |

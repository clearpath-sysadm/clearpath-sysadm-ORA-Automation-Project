# EOD/EOW/EOM Button System - Design & Requirements

## Overview
User-driven physical inventory control buttons to replace time-based automations. These buttons give the shipping team control over when reports are generated, eliminating edge cases from variable shipping schedules.

**Status:** 🟡 PARTIALLY IMPLEMENTED (50% Complete - Backend 70%, Frontend 30%)  
**Last Updated:** October 16, 2025

---

## 📊 IMPLEMENTATION STATUS

### ✅ Completed Components (50%)

#### 1. Database Infrastructure ✓
- ✅ Created `report_runs` table with UNIQUE constraint on (report_type, run_for_date)
- ✅ All data tables exist (shipped_items, shipped_orders, weekly_shipped_history)

#### 2. Helper Functions (pg_utils.py) ✓
- ✅ `eod_done_today()` - Check if EOD run for today
- ✅ `eow_done_this_week()` - Check if EOW run for current week
- ✅ `eom_done_this_month()` - Check if EOM run for current month
- ✅ `log_report_run()` - Log execution to database
- ✅ `get_last_report_runs()` - Fetch last run times for UI

#### 3. API Endpoints (app.py) ✓
- ✅ `POST /api/reports/eod` - Triggers daily_shipment_processor.py
- ✅ `POST /api/reports/eow` - Triggers weekly_reporter.py (with EOD dependency check)
- ✅ `POST /api/reports/eom` - Calculates monthly ShipStation charges
- ✅ `GET /api/reports/status` - Returns last run times for UI

#### 4. UI - HTML ✓
- ✅ Button section added to index.html (horizontal layout)
- ✅ Positioned between "Operational Pulse" and "Inventory Risk" sections
- ✅ Warning banner placeholder added

#### 5. Workflow Configuration ✓
- ✅ Disabled automated `weekly_reporter` in start_all.sh (now button-only)

### 🚨 Critical Issues Identified (MUST FIX)

#### Issue #1: EOM Query Bug 🔴
**Location:** `app.py` line ~1535-1547  
**Problem:** Using window functions incorrectly - produces duplicate rows instead of aggregated summary  
**Current Code:**
```python
SELECT carrier, service, shipping_cost_cents,
       COUNT(*) OVER (PARTITION BY carrier, service) as service_count,
       SUM(shipping_cost_cents) OVER (PARTITION BY carrier, service) as service_total
FROM shipped_orders
WHERE ship_date >= %s AND ship_date <= %s
```
**Fix Required:**
```python
SELECT carrier, service,
       COUNT(*) as order_count,
       SUM(shipping_cost_cents) as total_cents
FROM shipped_orders
WHERE ship_date >= %s AND ship_date <= %s
GROUP BY carrier, service
ORDER BY carrier, service
```

#### Issue #2: No Concurrency Guards 🔴
**Location:** All 3 report endpoints  
**Problem:** Two users clicking same button simultaneously will launch duplicate subprocess instances  
**Risk:** Database conflicts, duplicate processing  
**Fix Required:**
```python
_report_locks = {'EOD': False, 'EOW': False, 'EOM': False}

@app.route('/api/reports/eod', methods=['POST'])
def api_run_eod():
    if _report_locks['EOD']:
        return jsonify({'success': False, 'error': 'EOD already running'}), 409
    
    _report_locks['EOD'] = True
    try:
        # ... existing code ...
    finally:
        _report_locks['EOD'] = False
```

**⚠️ Important Limitation:**  
In-memory locks only protect a **single Flask process**. Current deployment uses one worker, so this is sufficient. If multiple workers/processes are ever deployed, upgrade to **database advisory locks** (`SELECT pg_advisory_lock()`) or transaction-based guards to ensure system-wide concurrency protection.

#### Issue #3: Date Logic Unverified ⚠️
**Location:** `pg_utils.py` - `eow_done_this_week()`, `eom_done_this_month()`  
**Problem:** Week start calculation uses `today.weekday()` - behavior needs validation  
**Risk:** Wrong week/month boundaries → UNIQUE constraint fails or checks wrong period  
**Verification Needed:**
- Confirm `weekday()` returns 0=Monday (not 0=Sunday)
- Test month_start calculation for edge cases (Jan 1, Dec 31, leap years)
- Validate week_start calculation for boundary conditions

#### Issue #4: Error Handling Gaps ⚠️
**Location:** All 3 report endpoints  
**Problem:** Some failure paths might not log to `report_runs` table  
**Fix Required:** Ensure ALL exception paths call `log_report_run()` before returning error

#### Issue #5: Subprocess Idempotency Requirements ℹ️
**Location:** All report scripts (daily_shipment_processor.py, weekly_reporter.py, EOM calculation)  
**Requirement:** Scripts must be **idempotent** and handle reruns safely  
**Critical Behaviors:**
1. **Non-zero exit codes on failure** - Scripts must return exit code != 0 when they fail so subprocess can detect errors
2. **Safe reruns** - Running the same report twice for the same date should not corrupt data or create duplicates
3. **Partial failure handling** - If a script fails midway, the database should remain in a consistent state (use transactions)
4. **Clear error messages** - Scripts should print errors to stderr for subprocess capture

**Validation Required:**
- Test that daily_shipment_processor.py returns non-zero on ShipStation API failure
- Test that weekly_reporter.py can be rerun for the same week without issues
- Verify all scripts use database transactions properly

### 🔴 Missing Components (50%)

#### 1. JavaScript Functions - NOT STARTED
Missing all button handlers:
- ❌ `runEOD()` - Disable button, call API, show success/error, re-enable
- ❌ `runEOW()` - Same pattern with progress indicator  
- ❌ `runEOM()` - Same pattern with charge total display
- ❌ `loadReportStatus()` - Fetch /api/reports/status on page load
- ❌ `checkReportWarnings()` - Show warning if EOD not run by 2 PM

#### 2. CSS Styling - NOT STARTED
Missing all button styles:
- ❌ `.report-controls-container` - Horizontal flexbox layout
- ❌ `.report-btn` - Button styling with hover effects
- ❌ `.report-btn-icon` - Emoji icon styling
- ❌ `.report-btn-status` - Last run timestamp styling
- ❌ `#report-warnings` - Warning banner styling (orange/yellow alert)

#### 3. Testing - NOT STARTED
Zero testing completed - requires comprehensive test coverage:

**Database & Backend Tests:**
- ❌ **UNIQUE constraint behavior** - Test duplicate report_runs inserts for same date are rejected
- ❌ **Helper function date calculations** - Verify weekday() logic, week/month boundaries
- ❌ **API endpoint success scenarios** - Each button completes successfully and logs to report_runs
- ❌ **API endpoint failure scenarios** - Subprocess timeout/error properly logged with status='failed'
- ❌ **EOW dependency check** - Verify EOW auto-runs EOD when not already done today
- ❌ **EOM monthly charge totals** - Validate aggregation accuracy against known October data
- ❌ **Subprocess error propagation** - Verify scripts return non-zero on failure, Flask catches it
- ❌ **Idempotency validation** - Rerun same report twice, verify no data corruption

**Concurrency & Edge Case Tests:**
- ❌ **Simultaneous button clicks** - Two users click EOD at same time → lock prevents duplicates (409 response)
- ❌ **Timeout handling** - Script runs >120s → timeout detected, logged as failed
- ❌ **Week boundary** - Click EOW on Monday vs Sunday, verify correct week_start calculation
- ❌ **Month boundary** - Click EOM on last day of month (Oct 31), verify month_start/month_end
- ❌ **Year boundary** - Test Dec 31 → Jan 1 transitions for both EOW and EOM
- ❌ **Already run protection** - Click EOD twice in same day → second returns "already run" message

**UI & Integration Tests:**
- ❌ **Button clicks** - All 3 buttons trigger correct endpoints and show success/error
- ❌ **Status display updates** - After clicking, last run timestamp updates in UI
- ❌ **Warning banner** - If EOD not run by 2 PM, warning appears on dashboard
- ❌ **Button disabled during run** - Button grays out while processing, re-enables after
- ❌ **Error message display** - API errors show in UI with clear messaging

### 📋 Remaining Work Estimate

| Phase | Tasks | Estimated Time | Status |
|-------|-------|----------------|--------|
| **Backend Hardening** | Fix EOM query, add concurrency guards, validate dates, harden error logging | 2 hours | 🔴 Not Started |
| **Frontend Implementation** | JavaScript functions, CSS styling, integration | 2 hours | 🔴 Not Started |
| **Testing & Validation** | End-to-end testing, edge cases, UI/UX validation | 1 hour | 🔴 Not Started |
| **TOTAL** | | **5 hours** | **50% Complete** |

### 🎯 Next Steps (Prioritized)

1. **IMMEDIATE: Fix EOM Query** (15 min) - Critical bug, wrong totals
2. **HIGH: Add Concurrency Guards** (30 min) - Prevent duplicate processing
3. **HIGH: Validate Helper Functions** (30 min) - Verify date calculations
4. **MEDIUM: Complete Frontend** (2 hours) - JavaScript + CSS
5. **HIGH: End-to-End Testing** (1 hour) - Test all scenarios
6. **FINAL: User Acceptance** (30 min) - Get sign-off

### 📚 Related Documentation
- **Gap Analysis:** `/docs/features/EOD_EOW_EOM_GAP_ANALYSIS.md`
- **Current State Analysis:** `/docs/features/EOD_EOW_EOM_CURRENT_STATE_ANALYSIS.md`
- **Project Journal:** `/docs/PROJECT_JOURNAL.md`

---

## 🎯 Core Requirements

### Three Independent Buttons

**📦 EOD (End of Day)** - Daily Inventory Update  
**📊 EOW (End of Week)** - Weekly Inventory Report  
**💰 EOM (End of Month)** - Monthly Charge Report

**Key Principle:** Minimal dependencies, no cascading duplication

---

## 📋 Data Requirements (Per Button)

### EOD - End of Day
**Purpose:** Know current inventory after daily shipping is complete

**Data Needed:**
- ✅ `shipped_items` table (ship_date, base_sku, quantity_shipped, sku_lot)
- ❌ NOT `shipped_orders` (only needed for charge calculations)

**Process:**
1. Sync latest shipped items from ShipStation
2. Calculate: `Current Inventory = Initial Inventory - Total Shipped`
3. Update inventory display
4. Log completion in `report_runs` table

**Output:** "✅ Daily inventory updated - 23 orders shipped today"

---

### EOW - End of Week
**Purpose:** Same as EOD + generate 52-week rolling averages for weekly email

**Data Needed:**
- ✅ Everything from EOD (shipped_items)
- ✅ `weekly_shipped_history` table (52-week historical data)
- ✅ New week's aggregated shipments by SKU

**Process:**
1. Check if EOD already run today
   - If NO → Run EOD first
   - If YES → Skip to step 2
2. Aggregate this week's shipments by SKU
3. Calculate 52-week rolling averages
4. Insert new week into `weekly_shipped_history`
5. Generate weekly inventory report
6. Send email to team
7. Log completion in `report_runs` table

**Output:** "✅ Weekly report sent - Avg weekly shipments calculated"

**Smart Dependency:** Only runs EOD if not already completed today (prevents duplication)

---

### EOM - End of Month
**Purpose:** Generate monthly ShipStation billing/charge report

**Data Needed:**
- ✅ `shipped_orders` table (order_number, ship_date, shipping_cost, carrier, service)
- ✅ `shipped_items` table (for package count calculations only)

**Process:**
1. Calculate monthly ShipStation charges grouped by:
   - Carrier (FedEx, USPS, etc.)
   - Service level (Ground, 2Day, Overnight, etc.)
   - Daily breakdown
2. Generate charge report with totals
3. Email monthly invoice summary
4. Log completion in `report_runs` table

**Output:** "✅ Monthly charge report sent - Total: $X,XXX.XX"

**Independence:** EOM does NOT depend on EOD or EOW (uses different data)

---

## 👤 User Workflow

### Daily Operations
**Normal day (~1pm after shipping):**
```
Shipping complete → Click EOD button → Inventory updated
```

**Friday (~1pm after shipping):**
```
Shipping complete → Click EOW button → EOD runs (if needed) → Weekly report emailed
```

**Last day of month:**
```
Click EOD or EOW (per normal schedule)
THEN click EOM button → Monthly charge report emailed
```

**Key:** User controls exact timing. No time-based automations.

---

## 🔧 Backend Implementation (Simplified)

### EOD Function
```python
def run_eod():
    """Sync shipped items and update inventory"""
    # 1. Sync from ShipStation
    sync_shipped_items_from_shipstation()
    
    # 2. Calculate current inventory
    calculate_current_inventory()
    
    # 3. Log completion
    log_report_run('EOD', date.today(), date.today(), 'success')
    
    return {
        'success': True,
        'message': f'✅ Daily inventory updated - {count} orders shipped today'
    }
```

### EOW Function
```python
def run_eow():
    """Generate weekly report with 52-week averages"""
    # 1. Check if EOD done today
    if not eod_done_today():
        run_eod()  # Only run if needed
    
    # 2. Aggregate this week's shipments
    weekly_shipments = aggregate_weekly_shipments(this_week_start, this_week_end)
    
    # 3. Calculate 52-week rolling averages
    rolling_averages = calculate_52_week_averages()
    
    # 4. Insert into weekly_shipped_history
    insert_weekly_history(weekly_shipments, rolling_averages)
    
    # 5. Generate and email report
    send_weekly_inventory_email()
    
    # 6. Log completion
    log_report_run('EOW', date.today(), this_week_start, 'success')
    
    return {
        'success': True,
        'message': '✅ Weekly report sent - Avg weekly shipments calculated'
    }
```

### EOM Function
```python
def run_eom():
    """Generate monthly charge report (independent of EOD/EOW)"""
    # 1. Calculate monthly charges from shipped_orders
    monthly_charges = calculate_monthly_shipstation_charges(
        start_date=first_day_of_month,
        end_date=last_day_of_month
    )
    
    # 2. Group by carrier and service
    charge_breakdown = group_charges_by_carrier_service(monthly_charges)
    
    # 3. Generate charge report
    generate_monthly_charge_report(charge_breakdown)
    
    # 4. Email monthly invoice
    send_monthly_charge_email()
    
    # 5. Log completion
    log_report_run('EOM', date.today(), first_day_of_month, 'success')
    
    return {
        'success': True,
        'message': f'✅ Monthly charge report sent - Total: ${total:,.2f}'
    }
```

---

## 🚨 Edge Case: Forgot to Push Buttons

### Problem
Shipping person forgets to push buttons, especially critical for EOM at month-end.

### Solutions

#### Option 1: Dashboard Warnings (Recommended)
```python
# Show warnings on dashboard when buttons not pushed
if not eod_done_today() and current_time > '14:00':
    display_warning("⚠️ EOD not run today - Click to run now")

if is_friday() and not eow_done_this_week():
    display_warning("⚠️ Weekly report not generated - Click to run now")

if is_last_day_of_month() and not eom_done_this_month():
    display_warning("⚠️ Monthly charge report missing - Click to run now")
```

#### Option 2: Manual Date Picker
- Add "Run for Specific Date" option
- User selects past date and clicks button
- System runs report for that historical period

#### Option 3: Auto Catch-up on Next Click
```python
def run_eod():
    # Check for missed days
    missed_days = get_missed_eod_days()
    if missed_days:
        for day in missed_days:
            run_eod_for_date(day)  # Backfill
    
    # Run for today
    run_eod_for_date(date.today())
```

**Recommendation:** Start with Option 1 (warnings), add Option 2 if needed.

---

## 🗄️ Database Schema

### New Table: report_runs
```sql
CREATE TABLE report_runs (
    id SERIAL PRIMARY KEY,
    report_type VARCHAR(10) NOT NULL,  -- 'EOD', 'EOW', 'EOM'
    run_date DATE NOT NULL,            -- When button was clicked
    run_for_date DATE NOT NULL,        -- Which period it covers
    status VARCHAR(20) NOT NULL,       -- 'success', 'failed', 'in_progress'
    message TEXT,                      -- Success/error message
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(report_type, run_for_date)  -- Prevent duplicate runs
);
```

### Helper Functions
```python
def eod_done_today():
    """Check if EOD already run for today"""
    return exists_query(
        "SELECT 1 FROM report_runs WHERE report_type = 'EOD' AND run_for_date = %s",
        [date.today()]
    )

def eow_done_this_week():
    """Check if EOW already run for current week"""
    week_start = get_week_start(date.today())
    return exists_query(
        "SELECT 1 FROM report_runs WHERE report_type = 'EOW' AND run_for_date = %s",
        [week_start]
    )

def eom_done_this_month():
    """Check if EOM already run for current month"""
    month_start = date.today().replace(day=1)
    return exists_query(
        "SELECT 1 FROM report_runs WHERE report_type = 'EOM' AND run_for_date = %s",
        [month_start]
    )

def log_report_run(report_type, run_date, run_for_date, status, message=''):
    """Log report run to database"""
    upsert(
        'report_runs',
        {'report_type': report_type, 'run_for_date': run_for_date},
        {
            'run_date': run_date,
            'status': status,
            'message': message,
            'created_at': 'NOW()'
        }
    )
```

---

## 🎨 UI Implementation

### Dashboard Additions

**Button Section:**
```html
<div class="report-controls">
    <div class="button-group">
        <button id="btn-eod" onclick="runEOD()">
            📦 EOD - Daily Inventory
        </button>
        <span class="last-run">Last: Oct 15, 1:30 PM</span>
    </div>
    
    <div class="button-group">
        <button id="btn-eow" onclick="runEOW()">
            📊 EOW - Weekly Report
        </button>
        <span class="last-run">Last: Oct 11 (Friday)</span>
    </div>
    
    <div class="button-group">
        <button id="btn-eom" onclick="runEOM()">
            💰 EOM - Monthly Charges
        </button>
        <span class="last-run">Last: Sep 30</span>
    </div>
</div>

<!-- Warnings -->
<div id="report-warnings" class="warnings-section">
    <!-- Dynamic warnings appear here -->
</div>
```

**JavaScript Functions:**
```javascript
async function runEOD() {
    const btn = document.getElementById('btn-eod');
    btn.disabled = true;
    btn.textContent = '⏳ Running EOD...';
    
    try {
        const response = await fetch('/api/reports/eod', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message);
            updateLastRunTime('eod', new Date());
        } else {
            showError('EOD failed', data.error);
        }
    } catch (error) {
        showError('EOD error', error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '📦 EOD - Daily Inventory';
    }
}

async function runEOW() {
    // Similar to EOD, with progress indicator
    // Shows: "Running EOD if needed..." then "Calculating averages..."
}

async function runEOM() {
    // Similar to EOD
    // Shows: "Calculating monthly charges..."
}
```

---

## 🔒 Duplicate Prevention

**Constraint:** `UNIQUE(report_type, run_for_date)` prevents duplicate runs

**Behavior when button clicked twice:**
1. First click: Success, data inserted
2. Second click: Upsert updates existing record (idempotent)
3. UI shows: "Already run for today - refreshing data..."

**User can force re-run:** Add "Force Re-run" checkbox for manual corrections

---

## 📝 Open Questions

### 1. EOW Smart Dependency
**Q:** Should EOW ALWAYS run EOD first, or only if EOD hasn't been done today?  
**A:** _Pending decision - Current plan: Only run if not done today_

### 2. Edge Case Handling
**Q:** Dashboard auto-warnings OR manual date picker for missed runs?  
**A:** _Pending decision - Recommendation: Start with warnings_

### 3. EOM Data Independence
**Q:** Confirm EOM doesn't need inventory data (shipped_items), only charges (shipped_orders)?  
**A:** _Needs confirmation - Current analysis shows EOM uses shipped_orders primarily_

### 4. Duplicate Button Clicks
**Q:** If someone accidentally clicks button twice, prevent re-run or allow it?  
**A:** _Pending decision - Current plan: Idempotent updates (safe to re-run)_

---

## 📈 Implementation Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **1. Database Setup** | 1 hour | Create `report_runs` table, helper functions |
| **2. Backend Endpoints** | 3 hours | Implement `/api/reports/eod`, `/eow`, `/eom` |
| **3. UI Components** | 2 hours | Add buttons, warnings, last-run timestamps |
| **4. Testing** | 2 hours | Test all scenarios, edge cases |
| **5. Documentation** | 1 hour | User manual updates |
| **Total** | 9 hours | End-to-end implementation |

---

## 🔗 Related Documentation

- `/docs/features/UNIFIED_SHIPSTATION_SYNC_PLAN.md` - ShipStation sync that feeds EOD/EOW
- `/docs/operations/USER_MANUAL.md` - User-facing instructions (needs update)
- `/docs/planning/DATABASE_SCHEMA.md` - Schema documentation (needs `report_runs` table)

---

## ✅ Next Steps

1. **Review & approve** this simplified design with stakeholder
2. **Decide on open questions** (especially edge case handling)
3. **Create implementation task list** once approved
4. **Update replit.md** to change status from PLANNED to IN_PROGRESS

---

**Design Status:** ✅ Requirements complete, awaiting approval for implementation

# EOD/EOW/EOM Button System - Design & Requirements

## Overview
User-driven physical inventory control buttons to replace time-based automations. These buttons give the shipping team control over when reports are generated, eliminating edge cases from variable shipping schedules.

**Status:** Requirements defined, implementation pending  
**Last Updated:** October 15, 2025

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

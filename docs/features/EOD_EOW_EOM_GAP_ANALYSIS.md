# EOD/EOW/EOM Button System - Gap Analysis

**Date:** October 16, 2025  
**Status:** Planning → Implementation Readiness Assessment

---

## 📊 Executive Summary

**Overall Readiness: 65%** - Partial infrastructure exists, core components need implementation

| Component | Status | Gap Size |
|-----------|--------|----------|
| **Database Tables** | 🟡 Partial | Medium - Missing `report_runs` table |
| **Backend Functions** | 🟡 Partial | Medium - Core logic exists but not wired to buttons |
| **API Endpoints** | 🔴 Missing | Large - No button endpoints exist |
| **UI Components** | 🔴 Missing | Large - No buttons on dashboard |
| **Data Dependencies** | 🟢 Complete | Small - All required tables exist |

---

## ✅ What We HAVE (Existing Infrastructure)

### 1. Database Tables ✓
All required data tables exist:
- ✅ `shipped_items` (1,272 records, latest: Oct 15, 2025)
- ✅ `shipped_orders` (order-level shipment data)
- ✅ `weekly_shipped_history` (52-week historical data)
- ✅ `configuration_params` (Initial Inventory baseline: Sept 19, 2025)

### 2. Core Business Logic ✓
Existing reusable functions:
- ✅ **Shipped Items Sync:** `daily_shipment_processor.py` fetches ShipStation shipments and populates `shipped_items`
- ✅ **Unified ShipStation Sync:** `unified_shipstation_sync.py` handles status updates and manual order imports (creates shipped_items for shipped orders)
- ✅ **Inventory Calculations:** `src/services/reporting_logic/inventory_calculations.py` - `calculate_current_inventory()` function exists
- ✅ **52-Week Averages:** `src/services/reporting_logic/average_calculations.py` - `calculate_12_month_rolling_average()` function exists
- ✅ **Weekly Reporter:** `src/weekly_reporter.py` - Already calculates rolling averages and updates `weekly_shipped_history`

### 3. Supporting Services ✓
- ✅ ShipStation API client (`src/services/shipstation/api_client.py`)
- ✅ Database utilities with transaction support (`src/services/database/pg_utils.py`)
- ✅ Workflow control system (can disable/enable automation)

---

## ❌ What We're MISSING (Implementation Gaps)

### 1. Database Schema Gap - `report_runs` Table
**Status:** 🔴 Missing  
**Impact:** HIGH - Cannot track button execution or prevent duplicates

**Required Table:**
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

**Helper Functions Needed:**
- `eod_done_today()` - Check if EOD already run
- `eow_done_this_week()` - Check if EOW already run
- `eom_done_this_month()` - Check if EOM already run
- `log_report_run()` - Log execution to database

---

### 2. Backend API Endpoints Gap
**Status:** 🔴 Missing  
**Impact:** HIGH - No way to trigger button actions

**Required Endpoints:**
```python
# app.py - Need to add:
@app.route('/api/reports/eod', methods=['POST'])
def api_run_eod():
    # 1. Sync shipped items from ShipStation
    # 2. Calculate current inventory
    # 3. Log completion
    # 4. Return success message

@app.route('/api/reports/eow', methods=['POST'])
def api_run_eow():
    # 1. Check if EOD done today (run if needed)
    # 2. Aggregate this week's shipments
    # 3. Calculate 52-week averages
    # 4. Update weekly_shipped_history
    # 5. Send email report
    # 6. Log completion

@app.route('/api/reports/eom', methods=['POST'])
def api_run_eom():
    # 1. Calculate monthly ShipStation charges
    # 2. Group by carrier/service
    # 3. Generate charge report
    # 4. Send email
    # 5. Log completion
```

**Additional Endpoint:**
```python
@app.route('/api/reports/status', methods=['GET'])
def api_get_report_status():
    # Return last run times for each button
    # Used to show "Last run: Oct 15, 1:30 PM"
```

---

### 3. UI Components Gap
**Status:** 🔴 Missing  
**Impact:** HIGH - No user interface for buttons

**Required HTML (index.html):**
```html
<div class="report-controls-section">
    <h3>📋 Physical Inventory Controls</h3>
    
    <div class="button-group">
        <button id="btn-eod" class="report-button" onclick="runEOD()">
            📦 EOD - Daily Inventory
        </button>
        <span class="last-run" id="eod-last-run">Last: --</span>
    </div>
    
    <div class="button-group">
        <button id="btn-eow" class="report-button" onclick="runEOW()">
            📊 EOW - Weekly Report
        </button>
        <span class="last-run" id="eow-last-run">Last: --</span>
    </div>
    
    <div class="button-group">
        <button id="btn-eom" class="report-button" onclick="runEOM()">
            💰 EOM - Monthly Charges
        </button>
        <span class="last-run" id="eom-last-run">Last: --</span>
    </div>
</div>

<!-- Dashboard warnings section -->
<div id="report-warnings" class="warnings-section"></div>
```

**Required JavaScript:**
```javascript
// Fetch last run times on page load
async function loadReportStatus() { ... }

// Button handlers
async function runEOD() { ... }
async function runEOW() { ... }
async function runEOM() { ... }

// Dashboard warnings
function checkReportWarnings() { ... }
```

**Required CSS:**
```css
.report-controls-section { ... }
.report-button { ... }
.last-run { ... }
.warnings-section { ... }
```

---

### 4. Business Logic Integration Gap
**Status:** 🟡 Partial  
**Impact:** MEDIUM - Need to wire existing functions into new endpoints

**EOD Implementation:**
Current: `daily_shipment_processor.py` runs as scheduled job  
**Need:** Trigger on-demand via button
```python
# Can reuse existing:
from src.daily_shipment_processor import run_daily_shipment_processing

def run_eod():
    # Call existing function
    run_daily_shipment_processing()
    # Log to report_runs
    log_report_run('EOD', ...)
```

**EOW Implementation:**
Current: `weekly_reporter.py` exists but runs independently  
**Need:** Wire to button with EOD dependency check
```python
from src.weekly_reporter import main as run_weekly_report

def run_eow():
    # 1. Check if EOD done today
    if not eod_done_today():
        run_eod()
    
    # 2. Run weekly report
    run_weekly_report()
    
    # 3. Log completion
    log_report_run('EOW', ...)
```

**EOM Implementation:**
Current: No monthly charge report exists  
**Need:** Build from scratch
```python
def run_eom():
    # 1. Query shipped_orders for month
    # 2. Calculate charges by carrier/service
    # 3. Generate report
    # 4. Send email
    # 5. Log completion
```

---

### 5. Email Integration Gap
**Status:** 🔴 Missing  
**Impact:** MEDIUM - Reports need email delivery

**Missing Components:**
- Email template for weekly inventory report
- Email template for monthly charge report
- SendGrid integration (optional - already available as dependency)

---

## 🔧 Implementation Priority

### Phase 1: Foundation (2 hours)
1. ✅ Create `report_runs` database table
2. ✅ Add helper functions (eod_done_today, log_report_run, etc.)
3. ✅ Add `/api/reports/status` endpoint

### Phase 2: EOD Button (2 hours)
1. ✅ Create `/api/reports/eod` endpoint
2. ✅ Wire to existing `daily_shipment_processor`
3. ✅ Add EOD button to dashboard UI
4. ✅ Test execution and logging

### Phase 3: EOW Button (2 hours)
1. ✅ Create `/api/reports/eow` endpoint
2. ✅ Wire to existing `weekly_reporter` with EOD dependency
3. ✅ Add EOW button to dashboard UI
4. ✅ Test execution and email delivery

### Phase 4: EOM Button (3 hours)
1. ✅ Build monthly charge calculation logic
2. ✅ Create `/api/reports/eom` endpoint
3. ✅ Add EOM button to dashboard UI
4. ✅ Create email template and test delivery

### Phase 5: Polish (1 hour)
1. ✅ Add dashboard warnings for missed runs
2. ✅ Style improvements
3. ✅ User documentation

**Total: 10 hours** (vs 9 hours in original plan)

---

## 🚨 Critical Design Questions to Resolve

### Q1: Daily Shipment Processor Timing
**Current:** `daily_shipment_processor.py` is NOT in `start_all.sh` (not running automatically)  
**Question:** Should we:
- A) Keep it manual (only triggered by EOD button) ✅ RECOMMENDED
- B) Run it automatically AND via button (potential duplication)

**Recommendation:** Option A - Button-only trigger eliminates scheduling complexity

### Q2: EOW Smart Dependency
**Current Plan:** EOW checks if EOD done today, runs it if not  
**Question:** Is this acceptable or should EOW ALWAYS run EOD first?

**Recommendation:** Keep smart dependency (prevents duplication on Fridays)

### Q3: Weekly Reporter Integration
**Current:** `weekly_reporter.py` runs independently in `start_all.sh`  
**Question:** Should we:
- A) Disable scheduled run, make it button-only
- B) Keep both (automated + manual button)

**Recommendation:** Option A - Button-only (user controls timing)

### Q4: EOM Independence Confirmation
**Current Plan:** EOM uses `shipped_orders` only (not `shipped_items`)  
**Question:** Confirm EOM doesn't need inventory data?

**Analysis:** ✅ CONFIRMED - Monthly charges only need order-level shipping costs from `shipped_orders`

---

## 📋 Action Items Before Implementation

### Immediate Decisions Needed:
1. ⚠️ **Remove `weekly_reporter` from `start_all.sh`?** (Make it button-only)
2. ⚠️ **Confirm `daily_shipment_processor` stays manual?** (No auto-scheduling)
3. ⚠️ **Email delivery method?** (SendGrid, SMTP, or skip for now)
4. ⚠️ **Dashboard placement?** (Where should buttons appear on index.html)

### Documentation Updates:
1. Update `replit.md` - Change EOD/EOW/EOM status from "DESIGN COMPLETE" to "IN PROGRESS"
2. Update `start_all.sh` - Remove weekly_reporter if going button-only
3. Create user manual section for button usage

---

## 💡 Key Insights

### What's Working Well:
✅ Data infrastructure is solid (tables exist, data is current)  
✅ Core business logic already exists (inventory calcs, averages, ShipStation sync)  
✅ Can reuse 80% of existing code  
✅ Design is simple and minimal dependencies

### What Needs Attention:
⚠️ No button infrastructure exists (UI, endpoints, tracking table)  
⚠️ Monthly charge report needs to be built from scratch  
⚠️ Email integration needs implementation  
⚠️ Need to decide on automated vs button-only workflows

### Biggest Risk:
🚨 **Workflow confusion** - Need clear decision on which services are automated vs button-triggered to avoid duplicate processing

---

## ✅ Recommendation

**PROCEED WITH IMPLEMENTATION** - Infrastructure is 65% ready. The gaps are clear and addressable. Estimated 10 hours to complete all three buttons with full functionality.

**Next Step:** Get decisions on the 4 critical questions above, then start with Phase 1 (Foundation).

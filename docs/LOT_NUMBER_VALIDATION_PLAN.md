# Lot Number Validation System - Implementation Plan

## Overview
A validation system that monitors ShipStation orders to ensure they use the correct, currently-active lot numbers. When orders are found with incorrect/outdated lot numbers, the system alerts users and provides resolution capabilities.

## Problem Statement
Currently, orders may be uploaded to ShipStation with outdated lot numbers if:
- SKU-Lot mappings in the database are stale
- Manual overrides were applied in ShipStation
- Timing issues between lot number updates and order processing

This creates inventory tracking issues and potential compliance problems.

## Solution Design

### Architecture
Leverage existing Shipping Validation System infrastructure to add lot number validation as a new violation type.

### Key Components

#### 1. Data Collection (Unified ShipStation Sync)
**File:** `src/unified_shipstation_sync.py`

**Changes Needed:**
- Parse lot numbers from ShipStation item SKU format: `"17612 - 250070"`
- Extract base SKU and lot number separately
- Pass lot number data to validation logic

**Implementation:**
```python
def parse_sku_lot_from_shipstation(item_sku: str) -> tuple:
    """
    Parse SKU and lot number from ShipStation format.
    Examples:
        "17612 - 250070" -> ("17612", "250070")
        "17612" -> ("17612", None)
    """
    if ' - ' in item_sku:
        parts = item_sku.split(' - ')
        return (parts[0].strip(), parts[1].strip())
    return (item_sku.strip(), None)
```

#### 2. Validation Logic
**File:** `src/validators/lot_number_validator.py` (NEW)

**Responsibilities:**
- Query active lot number for each SKU from `sku_lot` table
- Compare ShipStation lot vs. active lot
- Generate violation records for mismatches

**Core Logic:**
```python
def validate_order_lot_numbers(order: dict) -> list:
    """
    Validate all items in an order have correct lot numbers.
    Returns list of violations.
    """
    violations = []
    
    for item in order['items']:
        sku, ss_lot = parse_sku_lot_from_shipstation(item['sku'])
        
        # Get active lot from database
        active_lot = get_active_lot_for_sku(sku)
        
        if active_lot and ss_lot != active_lot:
            violations.append({
                'order_number': order['orderNumber'],
                'sku': sku,
                'shipstation_lot': ss_lot,
                'expected_lot': active_lot,
                'order_date': order['orderDate']
            })
    
    return violations
```

#### 3. Database Schema
**Table:** Extend `shipping_violations` or create new `lot_number_violations`

**Option A - Extend Existing (RECOMMENDED):**
Add new violation type to existing `shipping_violations` table:
- `violation_type = 'LOT_MISMATCH'`
- Store SKU, ShipStation lot, expected lot in existing JSON fields

**Option B - New Table:**
```sql
CREATE TABLE IF NOT EXISTS lot_number_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL,
    sku TEXT NOT NULL,
    shipstation_lot TEXT,
    expected_lot TEXT NOT NULL,
    order_date TEXT,
    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    resolved_by TEXT,
    resolution_notes TEXT,
    UNIQUE(order_number, sku)
);
```

**Recommendation:** Use Option A to maintain consistency with existing validation system.

#### 4. API Endpoints
**File:** `app.py`

**New/Updated Endpoints:**

1. **GET /api/lot_violations** - Retrieve active lot number violations
2. **PUT /api/lot_violations/:id/resolve** - Mark violation as resolved
3. **GET /api/lot_violations/stats** - Summary statistics

**Implementation:**
```python
@app.route('/api/lot_violations')
def get_lot_violations():
    """Get unresolved lot number violations"""
    violations = execute_query("""
        SELECT * FROM shipping_violations 
        WHERE violation_type = 'LOT_MISMATCH' 
        AND resolved_at IS NULL
        ORDER BY detected_at DESC
    """)
    return jsonify([dict(zip([...], v)) for v in violations])
```

#### 5. UI Components

**Dashboard Alert Card:**
- Add "Lot Number Alerts" KPI card
- Show count of active violations
- Link to detailed view

**Dedicated Page: `lot_violations.html` (NEW)**
- Table view of all violations
- Columns: Order #, SKU, ShipStation Lot, Expected Lot, Order Date, Actions
- Resolve button per violation
- Filter by: Date range, SKU, Resolved/Unresolved

**Styling:**
- Reuse existing `global-styles.css` components
- Alert styling similar to shipping violations
- Highlight severity (red/orange) based on age

## Implementation Steps

### Phase 1: Data Collection (30 min)
1. Add lot number parsing to `unified_shipstation_sync.py`
2. Extract SKU and lot from ShipStation format
3. Log parsed data for verification

### Phase 2: Validation Logic (45 min)
1. Create `src/validators/lot_number_validator.py`
2. Implement active lot lookup from `sku_lot` table
3. Implement comparison logic
4. Generate violation records

### Phase 3: Database Integration (30 min)
1. Extend `shipping_violations` table schema (or create new table)
2. Add `violation_type = 'LOT_MISMATCH'`
3. Create indexes for performance
4. Test UPSERT patterns

### Phase 4: API Development (30 min)
1. Create violation retrieval endpoint
2. Create resolution endpoint
3. Add statistics endpoint
4. Test API responses

### Phase 5: UI Development (60 min)
1. Create `lot_violations.html` page
2. Add dashboard alert card
3. Add navigation menu item
4. Implement real-time updates
5. Add resolution workflow

### Phase 6: Testing & Validation (30 min)
1. Test with known mismatched orders
2. Verify detection accuracy
3. Test resolution workflow
4. Validate UI responsiveness

## Database Queries

### Get Active Lot for SKU
```sql
SELECT lot_number 
FROM sku_lot 
WHERE sku = ? AND is_active = 1
LIMIT 1;
```

### Record Violation
```sql
INSERT INTO shipping_violations (
    order_number, violation_type, violation_details, detected_at
) VALUES (?, 'LOT_MISMATCH', ?, CURRENT_TIMESTAMP)
ON CONFLICT(order_number, violation_type) DO UPDATE SET
    violation_details = excluded.violation_details,
    detected_at = excluded.detected_at;
```

### Get Unresolved Violations
```sql
SELECT * FROM shipping_violations 
WHERE violation_type = 'LOT_MISMATCH' 
  AND resolved_at IS NULL
ORDER BY detected_at DESC;
```

## Integration Points

### Unified ShipStation Sync
**When:** During order processing loop
**Action:** After fetching order, before storing in database
**Call:** `validate_order_lot_numbers(order)` → store violations

### Dashboard
**When:** Page load and auto-refresh
**Action:** Fetch violation count
**Display:** Alert card with count and link

### Workflow Controls
**When:** User disables workflows
**Impact:** Violation detection paused (existing violations persist)

## Error Handling

### Missing Active Lot
- **Scenario:** SKU has no active lot in database
- **Action:** Log warning, skip validation for that SKU
- **Reason:** Prevents false positives for non-inventory items

### Parse Failures
- **Scenario:** ShipStation SKU format unexpected
- **Action:** Log error, extract base SKU only
- **Fallback:** Treat as no lot number (null)

### Database Failures
- **Scenario:** Cannot query sku_lot table
- **Action:** Log error, skip validation
- **Reason:** Fail-open to prevent blocking order sync

## Performance Considerations

### Caching Strategy
- Cache active lot numbers (60s TTL)
- Reduces database queries during bulk processing
- Invalidate on sku_lot updates

### Batch Processing
- Validate all order items in single pass
- Bulk insert violations (single transaction)
- Avoid N+1 query patterns

### Index Requirements
```sql
CREATE INDEX IF NOT EXISTS idx_sku_lot_active 
ON sku_lot(sku, is_active);

CREATE INDEX IF NOT EXISTS idx_violations_type_resolved 
ON shipping_violations(violation_type, resolved_at);
```

## Testing Scenarios

### Test Case 1: Correct Lot Number
- **Setup:** Order with "17612 - 250070", active lot is "250070"
- **Expected:** No violation

### Test Case 2: Outdated Lot Number
- **Setup:** Order with "17612 - 250070", active lot is "250300"
- **Expected:** Violation created with both lot numbers

### Test Case 3: Missing Lot Number
- **Setup:** Order with "17612" (no lot), active lot is "250070"
- **Expected:** Violation created (missing lot)

### Test Case 4: No Active Lot
- **Setup:** Order with "17612 - 250070", SKU has no active lot
- **Expected:** Skip validation (no violation)

### Test Case 5: Resolution Workflow
- **Setup:** Existing violation
- **Action:** User marks resolved with notes
- **Expected:** `resolved_at` timestamp set, notes saved

## Future Enhancements

### Auto-Correction (Phase 2)
- Automatically update ShipStation orders with correct lot
- Requires ShipStation API write permission
- User confirmation required

### Lot History Tracking
- Track all lot changes over time
- Audit trail for compliance
- Historical analysis of lot usage

### Predictive Alerts
- Warn before lot changeover
- Suggest optimal lot transition timing
- Inventory-based recommendations

### Email Notifications
- Daily digest of new violations
- Critical alerts for high-priority orders
- SendGrid integration (optional)

## Success Criteria

### Functional Requirements
✅ Detect lot number mismatches with 100% accuracy
✅ Display violations on dashboard within 5 minutes
✅ Allow manual resolution with notes
✅ Maintain performance (<500ms per order validation)

### Non-Functional Requirements
✅ Zero impact on existing sync performance
✅ Fail-open on errors (don't block order processing)
✅ Mobile-responsive UI
✅ Consistent with existing design system

## Rollout Plan

### Step 1: Development (3 hours)
- Implement all components
- Unit test validation logic
- Integration test with real data

### Step 2: Staging Testing (1 hour)
- Deploy to development environment
- Test with production data copy
- Verify accuracy and performance

### Step 3: Production Deployment (15 min)
- Deploy to production
- Monitor for 24 hours
- Validate detection accuracy

### Step 4: User Training (30 min)
- Document resolution workflow
- Train users on alert interpretation
- Establish escalation procedures

## Maintenance

### Daily Tasks
- Review new violations
- Resolve false positives
- Update lot mappings if needed

### Weekly Tasks
- Analyze violation trends
- Optimize detection rules
- Update documentation

### Monthly Tasks
- Performance review
- Feature enhancement planning
- Compliance audit

## Documentation Updates

**Files to Update:**
1. `replit.md` - Add lot validation to System Architecture
2. `DATABASE_SCHEMA.md` - Document violation table schema
3. User guide (if exists) - Resolution workflow

## Total Effort Estimate

**Development:** 3-4 hours
**Testing:** 1 hour
**Documentation:** 30 minutes
**Deployment:** 15 minutes

**Total: 4.75 - 5.75 hours** (approximately 1 business day)

## Risk Mitigation

### Risk: False Positives
- **Mitigation:** Comprehensive testing, user feedback loop
- **Fallback:** Easy resolution workflow

### Risk: Performance Impact
- **Mitigation:** Caching, indexing, batch processing
- **Monitoring:** Track validation time per order

### Risk: Data Quality Issues
- **Mitigation:** Robust parsing, error handling
- **Fallback:** Log errors, continue processing

## Conclusion

This lot number validation system will provide real-time visibility into inventory tracking accuracy, prevent compliance issues, and maintain data integrity across ShipStation and the ORA database. The implementation leverages existing infrastructure, minimizes development time, and delivers immediate value with clear ROI.

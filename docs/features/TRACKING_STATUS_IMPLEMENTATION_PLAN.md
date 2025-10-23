# Tracking Status Implementation Plan

**Feature:** Real-Time Shipment Tracking Status with Smart Updates  
**Created:** October 23, 2025  
**Estimated Effort:** 6-8 hours  
**Priority:** Medium

---

## 📋 Feature Overview

Add visual tracking status indicators to the Orders Inbox by fetching real-time delivery status from ShipStation API. Display status icons next to tracking numbers with smart, efficient polling that minimizes API usage.

### Goals
- ✅ Show real-time delivery status for active shipments
- ✅ Reduce customer service time (no need to check ShipStation website)
- ✅ Alert on exceptions that need attention
- ✅ Minimize API calls to stay within rate limits
- ✅ Stop tracking delivered orders automatically

### Non-Goals
- ❌ Full tracking timeline/events (too complex for MVP)
- ❌ Real-time push notifications (use polling instead)
- ❌ Historical tracking data storage

---

## 🎯 User Experience

### Before
```
Tracking: 📦 View → Modal → "Track on FedEx" button
```

### After
```
Tracking: ✅ 394575293100 (Delivered)
          🚚 394575291346 (In Transit)
          ⚠️ 394575285373 (Exception - Address Issue)
          ❓ 394575282466 (Not Scanned)
          📋 394575289276 (Accepted)
```

---

## 📊 Tracking Status Codes

| Code | Status | Icon | Description | Keep Tracking? |
|------|--------|------|-------------|----------------|
| **UN** | Unknown | ❓ | Label created, not scanned | ✅ Yes |
| **AC** | Accepted | 📋 | Carrier has package | ✅ Yes |
| **IT** | In Transit | 🚚 | Moving to destination | ✅ Yes |
| **EX** | Exception | ⚠️ | Delivery problem | ✅ Yes (Alert!) |
| **DE** | Delivered | ✅ | Final delivery | ❌ **STOP** |

---

## 🔧 Technical Requirements

### Database Changes

**Add columns to `orders_inbox`:**
```sql
ALTER TABLE orders_inbox 
ADD COLUMN tracking_status VARCHAR(10),
ADD COLUMN tracking_status_description TEXT,
ADD COLUMN exception_description TEXT,
ADD COLUMN tracking_last_checked TIMESTAMP,
ADD COLUMN tracking_last_updated TIMESTAMP;

CREATE INDEX idx_orders_tracking_status ON orders_inbox(tracking_status) 
WHERE tracking_status IS NOT NULL;
```

### API Integration

**ShipStation Tracking API:**
- **Endpoint:** `GET https://api.shipengine.com/v1/tracking`
- **Parameters:** `carrier_code=fedex&tracking_number={number}`
- **Rate Limit:** 40-200 requests/minute (depends on plan)
- **Authentication:** Same API key/secret as current ShipStation integration

**Response Structure:**
```json
{
  "tracking_number": "394575293100",
  "status_code": "IT",
  "status_description": "In Transit",
  "carrier_status_description": "Package moving through network",
  "exception_description": null,
  "events": [...]
}
```

---

## 🚀 Implementation Plan

### Phase 1: Database Setup (1 hour)

**Tasks:**
1. Create database migration script
2. Add new columns to `orders_inbox`
3. Create index on `tracking_status`
4. Test migration on development database

**Files to modify:**
- `migration/scripts/postgres/add_tracking_status.sql` (new)

---

### Phase 2: Backend - Tracking Service (3 hours)

**Create tracking service module:**

**File:** `src/services/shipstation/tracking_service.py`

```python
def fetch_tracking_status(tracking_number: str, carrier_code: str = 'fedex') -> dict:
    """
    Fetch tracking status from ShipStation API.
    Returns: {
        'status_code': 'IT',
        'status_description': 'In Transit',
        'exception_description': None
    }
    """
    pass

def should_track_order(order: dict) -> bool:
    """
    Determine if order should be tracked.
    Rules:
    - Has tracking number
    - Status not 'delivered' (DE)
    - During business hours (9 AM - 5 PM CT)
    - Last checked > 5 minutes ago
    """
    pass

def is_business_hours() -> bool:
    """Check if current time is 9 AM - 5 PM Central Time."""
    pass

def update_order_tracking_status(order_number: str, tracking_data: dict, conn):
    """Update order tracking status in database."""
    pass
```

**Business Hours Logic:**
```python
import pytz
from datetime import datetime

def is_business_hours() -> bool:
    ct = pytz.timezone('America/Chicago')
    now_ct = datetime.now(ct)
    hour = now_ct.hour
    # 9 AM to 5 PM Central Time
    return 9 <= hour < 17
```

**Files to create:**
- `src/services/shipstation/tracking_service.py`

**Files to modify:**
- None (new module)

---

### Phase 3: Integration with Unified Sync (2 hours)

**Modify:** `src/unified_shipstation_sync.py`

**Add tracking status fetch after shipments processing:**

```python
def sync_tracking_statuses(conn, api_key: str, api_secret: str):
    """
    Fetch tracking statuses for active (non-delivered) orders.
    Only runs during business hours.
    """
    if not is_business_hours():
        logger.info("⏰ Outside business hours - skipping tracking status updates")
        return 0
    
    cursor = conn.cursor()
    
    # Get orders that need tracking
    cursor.execute("""
        SELECT order_number, tracking_number, shipping_carrier_name, tracking_status
        FROM orders_inbox
        WHERE tracking_number IS NOT NULL
          AND tracking_number != ''
          AND (tracking_status IS NULL OR tracking_status != 'DE')
          AND (tracking_last_checked IS NULL 
               OR tracking_last_checked < NOW() - INTERVAL '5 minutes')
        ORDER BY tracking_last_checked NULLS FIRST
        LIMIT 50
    """)
    
    orders = cursor.fetchall()
    
    if not orders:
        logger.info("📭 No orders need tracking status updates")
        return 0
    
    logger.info(f"🔍 Checking tracking status for {len(orders)} orders...")
    
    updated = 0
    for order_number, tracking_number, carrier, current_status in orders:
        try:
            # Handle multiple tracking numbers (comma-separated)
            tracking_nums = [t.strip() for t in tracking_number.split(',')]
            primary_tracking = tracking_nums[0]
            
            # Fetch status from ShipStation
            carrier_code = map_carrier_to_code(carrier)
            tracking_data = fetch_tracking_status(primary_tracking, carrier_code)
            
            # Update database
            update_order_tracking_status(order_number, tracking_data, conn)
            updated += 1
            
            # Log status changes
            if tracking_data['status_code'] != current_status:
                logger.info(f"📊 Order {order_number}: {current_status or 'NEW'} → {tracking_data['status_code']}")
                
                # Alert on exceptions
                if tracking_data['status_code'] == 'EX':
                    logger.warning(f"⚠️ EXCEPTION for order {order_number}: {tracking_data.get('exception_description')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update tracking for {order_number}: {e}")
            continue
    
    logger.info(f"✅ Updated tracking status for {updated}/{len(orders)} orders")
    return updated
```

**Add to main sync loop:**
```python
# After shipment processing, before watermark update
if stats['errors'] == 0:
    tracking_updated = sync_tracking_statuses(conn, api_key, api_secret)
    stats['tracking_status_updates'] = tracking_updated
```

**Files to modify:**
- `src/unified_shipstation_sync.py`

---

### Phase 4: Frontend UI Updates (1 hour)

**Modify:** `xml_import.html`

**Replace tracking modal with status display:**

```javascript
// Icon mapping
function getTrackingStatusIcon(status) {
    const icons = {
        'DE': '✅',  // Delivered
        'IT': '🚚',  // In Transit
        'EX': '⚠️',  // Exception
        'AC': '📋',  // Accepted
        'UN': '❓'   // Unknown
    };
    return icons[status] || '📦';
}

// Format tracking cell
const trackingCell = order.tracking_number 
    ? `
        <span style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 18px;">${getTrackingStatusIcon(order.tracking_status)}</span>
            <span style="font-family: monospace; color: var(--text-secondary);">${order.tracking_number}</span>
            ${order.tracking_status === 'EX' ? 
                `<span style="color: var(--critical-red); font-size: 12px; font-weight: 600;">ALERT</span>` 
                : ''}
        </span>
    `
    : '<span style="color: var(--text-tertiary);">-</span>';
```

**Add tooltip with status description:**
```javascript
title="${order.tracking_status_description || ''}"
```

**Mobile card view:**
```javascript
${order.tracking_number ? `
<div class="order-card-detail-row">
    <span class="order-card-detail-label">Tracking:</span>
    <span class="order-card-detail-value">
        ${getTrackingStatusIcon(order.tracking_status)} ${order.tracking_number}
        ${order.exception_description ? 
            `<br><span style="color: var(--critical-red); font-size: 11px;">${order.exception_description}</span>` 
            : ''}
    </span>
</div>
` : ''}
```

**Remove tracking modal:** (Keep for future use or delete)

**Files to modify:**
- `xml_import.html` (lines ~882-884, ~973-977)

---

### Phase 5: Exception Alert Dashboard Widget (Optional - 1 hour)

**Add to dashboard (`index.html`):**

```html
<!-- Tracking Exceptions Alert -->
<div id="tracking-exceptions-alert" class="alert-banner" style="display: none;">
    <div class="alert-content">
        <span class="alert-icon">⚠️</span>
        <div class="alert-text">
            <div class="alert-title">Shipment Exceptions</div>
            <div class="alert-details" id="exception-summary">Loading...</div>
        </div>
    </div>
    <div class="alert-actions">
        <button class="btn-view-alert" onclick="window.location.href='/xml_import.html?filter=exceptions'">
            View Orders
        </button>
        <button class="btn-dismiss-alert" onclick="dismissExceptionAlert()">×</button>
    </div>
</div>
```

**API endpoint:**
```python
@app.route('/api/tracking_exceptions')
def get_tracking_exceptions():
    """Get count of orders with exception status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM orders_inbox 
        WHERE tracking_status = 'EX'
    """)
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return jsonify({'count': count})
```

**Files to modify:**
- `index.html` (optional)
- `app.py` (optional)

---

## 🧪 Testing Plan

### Unit Tests
1. ✅ Business hours detection (9 AM - 5 PM CT)
2. ✅ Status code mapping (UN, AC, IT, EX, DE)
3. ✅ Should track logic (filters delivered orders)
4. ✅ Multiple tracking numbers handling

### Integration Tests
1. ✅ ShipStation API connection
2. ✅ Database updates (status, timestamps)
3. ✅ Error handling (API failures, rate limits)

### Manual Testing Checklist
- [ ] Create test order with tracking number
- [ ] Verify status appears in UI
- [ ] Test during business hours (9 AM - 5 PM CT)
- [ ] Test outside business hours (no updates)
- [ ] Simulate delivered status (stops tracking)
- [ ] Simulate exception status (shows alert)
- [ ] Test with multiple tracking numbers
- [ ] Verify mobile view displays correctly
- [ ] Check API rate limit headers

---

## 📈 API Usage Analysis

### Current Usage
- Unified sync: 2-5 calls every 5 min
- Upload service: 1-2 calls every 5 min
- **Total: ~5-10 calls per 5 min = 1-2 calls/minute**

### After Implementation
- Active orders tracking: ~10-20 orders
- Business hours only: 96 cycles/day (9 AM - 5 PM = 480 min ÷ 5)
- **Additional: 10-20 calls per cycle = 2-4 calls/minute**

### Total Projected Usage
- **Combined: 3-6 calls/minute average**
- ShipStation limit: 40-200 calls/minute
- **Utilization: 3-15% (very safe)**

---

## 🚨 Rate Limit Safety

### Monitoring
```python
def check_rate_limit(response):
    """Monitor ShipStation rate limit headers."""
    remaining = response.headers.get('X-Rate-Limit-Remaining')
    reset = response.headers.get('X-Rate-Limit-Reset')
    
    if remaining and int(remaining) < 10:
        logger.warning(f"⚠️ Low rate limit: {remaining} remaining, resets in {reset}s")
        # Optional: pause tracking temporarily
```

### Fallback Strategy
If rate limit exceeded (HTTP 429):
1. Log error
2. Skip tracking for this cycle
3. Mark `tracking_last_checked` as failed
4. Retry in next cycle (5 minutes)
5. Alert in logs

---

## 🔒 Security & Privacy

### API Credentials
- ✅ Use existing ShipStation API key/secret
- ✅ Stored in environment variables (already secured)
- ✅ No new credentials needed

### Data Storage
- Tracking status: Public info (OK to store)
- Exception descriptions: May contain customer info
- Retention: Delete with order (60-day cleanup)

---

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] Test in development environment
- [ ] Verify database migration runs successfully
- [ ] Confirm API access to ShipStation tracking endpoint
- [ ] Check rate limit on ShipStation account
- [ ] Test business hours logic (wait until 9 AM CT)

### Deployment Steps
1. [ ] Run database migration
2. [ ] Deploy code updates
3. [ ] Restart unified-shipstation-sync workflow
4. [ ] Monitor logs for first tracking cycle
5. [ ] Verify UI displays status icons
6. [ ] Check API rate limit headers

### Post-Deployment
- [ ] Monitor for 24 hours
- [ ] Check error logs
- [ ] Verify tracking updates during business hours
- [ ] Confirm no updates outside business hours
- [ ] Document any issues in production incident log

---

## 🎯 Success Metrics

### Functional
- ✅ Tracking status displays for all active orders
- ✅ Status updates every 5 minutes during business hours
- ✅ Delivered orders stop tracking automatically
- ✅ Exceptions flagged and visible

### Performance
- ✅ API calls stay under 10% of rate limit
- ✅ No 429 rate limit errors
- ✅ Database queries < 100ms
- ✅ UI loads without delay

### Business Impact
- ✅ Faster customer service (no ShipStation lookup needed)
- ✅ Proactive exception handling (alerts visible)
- ✅ Reduced manual tracking checks

---

## 🔄 Future Enhancements

### Phase 2 (Optional)
1. **Full tracking timeline** - Show all events in modal
2. **Push notifications** - Email on exceptions
3. **Delivery predictions** - Estimated delivery date
4. **Historical tracking** - Archive tracking events
5. **Webhooks** - Real-time updates instead of polling

### Phase 3 (Advanced)
1. **Multi-carrier support** - UPS, USPS tracking
2. **Customer portal** - Let customers track orders
3. **Analytics** - Delivery time metrics
4. **Auto-resolution** - Address correction suggestions

---

## 📚 Documentation Updates

### Files to Update
- [x] This implementation plan
- [ ] `replit.md` - Add tracking status feature
- [ ] `docs/DATABASE_SCHEMA.md` - Document new columns
- [ ] `docs/API_ENDPOINTS.md` - Add tracking endpoints (if creating)

---

## 👥 Stakeholder Communication

### Before Implementation
**Message to user:**
> We're adding real-time tracking status to the Orders Inbox. You'll see icons (✅🚚⚠️) next to tracking numbers showing delivery status. This will update automatically during business hours and help catch delivery exceptions faster.

### After Implementation
**Message to user:**
> ✅ Tracking status is now live! Look for status icons in the Orders Inbox. Delivered orders show ✅, active shipments show 🚚, and any problems show ⚠️. Updates happen every 5 minutes during business hours (9 AM - 5 PM).

---

## 💰 Cost Analysis

### Development Time
- Database setup: 1 hour
- Backend service: 3 hours
- Integration: 2 hours
- Frontend UI: 1 hour
- Testing: 1 hour
- **Total: 6-8 hours**

### Ongoing Costs
- API calls: Included in existing ShipStation plan
- Database storage: Negligible (~5 columns × 300 orders = minimal)
- Compute: Negligible (runs in existing workflow)

### ROI
- Time saved per customer inquiry: ~2-3 minutes
- Customer inquiries per day: ~5-10
- **Time saved: 10-30 minutes/day**
- **Payback: ~2-3 weeks**

---

## ✅ Acceptance Criteria

### Must Have
- [x] Tracking status displays in Orders Inbox
- [x] Status updates during business hours only
- [x] Delivered orders stop tracking
- [x] API usage stays under 10% of rate limit
- [x] Exception status highlighted/alerted

### Nice to Have
- [ ] Exception alert banner on dashboard
- [ ] Tooltip with full status description
- [ ] Filter orders by tracking status
- [ ] Export includes tracking status

### Out of Scope
- Full tracking event timeline
- Real-time push notifications
- Customer-facing tracking page
- Historical tracking data

---

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Status:** Ready for Implementation

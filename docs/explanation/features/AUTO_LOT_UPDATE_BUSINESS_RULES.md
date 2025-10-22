# Automatic Lot Number Update - Business Rules

## Purpose
Ensure orders always ship from current active inventory lots, even if they were placed on hold with older lot numbers.

## Core Business Rules

### Rule 1: Update Trigger Scenarios
**Update lot numbers in ShipStation when:**

1. **Order released from hold** → Status changes from `on_hold` → `awaiting_shipment`
2. **Order manually updated** → Status changes to `awaiting_shipment` from any status
3. **Legacy order re-activated** → Any order with old lot numbers moves to `awaiting_shipment`

**DO NOT update when:**
- Order status is `shipped` (already processed)
- Order status is `cancelled` (not shipping)
- Order status is `on_hold` (not ready to ship yet)
- Lot number in ShipStation already matches current active lot

### Rule 2: Lot Number Validation
**Before updating:**
1. Extract base SKU from lot-formatted SKU (e.g., `"17612 - 250237"` → `"17612"`)
2. Query `sku_lot` table for current active lot where `sku = base_sku AND active = 1`
3. If no active lot found → Log warning, skip update, use existing lot
4. If active lot found AND different from ShipStation lot → Update ShipStation

### Rule 3: ShipStation Update Logic
**Update method:**
1. Call ShipStation API: `POST /orders/createorder` with existing order data + updated SKU
2. ShipStation will update the existing order (idempotent by orderNumber)
3. Updated SKU format: `"{base_sku} - {current_lot}"`
4. Preserve all other order data (quantity, price, shipping, etc.)

### Rule 4: Local DB Sync
**After ShipStation update:**
1. The unified sync will pick up the updated order on next cycle
2. Order metadata remains unchanged in local DB
3. Only the effective lot number in ShipStation changes

### Rule 5: FIFO Compliance
**Inventory accuracy:**
- Always use the CURRENT active lot from `sku_lot` table
- This ensures FIFO: ship from newest lot, not depleted old lots
- Lot rotation is managed by user via `sku_lot.html` admin interface

## Implementation Checkpoints

### Pre-Update Validations
```python
# 1. Check order status
if order_status not in ['awaiting_shipment']:
    skip_update = True

# 2. Extract and validate SKU
base_sku = extract_base_sku(shipstation_sku)
if not base_sku:
    log_error("Invalid SKU format")
    skip_update = True

# 3. Get current active lot
current_lot = get_active_lot(base_sku)
if not current_lot:
    log_warning(f"No active lot for SKU {base_sku}, using existing")
    skip_update = True

# 4. Check if update needed
shipstation_lot = extract_lot_from_sku(shipstation_sku)
if shipstation_lot == current_lot:
    skip_update = True  # Already correct

# 5. Validate lot exists in sku_lot table
if not validate_lot_exists(base_sku, current_lot):
    log_error(f"Lot {current_lot} not found for SKU {base_sku}")
    skip_update = True
```

### Error Handling
- **API failure** → Log error, don't block sync, retry on next cycle
- **Invalid SKU** → Log warning, skip update, continue processing
- **No active lot** → Use existing lot, log warning for review
- **Partial update** → Rollback, retry on next sync cycle

### Logging & Monitoring
- Log every lot number change: `"Order {order_number}: Updated SKU {base_sku} from lot {old_lot} → {new_lot}"`
- Count updates per sync cycle: Track in workflow status
- Alert on update failures: Email/dashboard notification

## Edge Cases

### Case 1: Multi-Item Orders
- Update lot numbers for ALL items in the order
- Each item gets its own active lot based on base SKU
- If any item update fails → rollback all changes to that order

### Case 2: Bundle SKUs
- Bundles are already expanded to component SKUs in our system
- Each component gets updated with its own active lot
- No special bundle handling needed

### Case 3: Discontinued SKUs
- If SKU no longer has active lot (active=0) → Use lot from ShipStation (don't update)
- Log warning for manual review

### Case 4: Concurrent Updates
- If upload service and sync both try to update same order → ShipStation handles idempotency
- Last update wins (by timestamp)
- Our system should prevent this via status-based locking

## Testing Scenarios

### Test 1: On-Hold Order Release
1. Create order with SKU 17612 - Lot 250237
2. Mark as `on_hold` in ShipStation
3. Change active lot to 250300 in `sku_lot` table
4. Release order to `awaiting_shipment`
5. **Expected:** Order updates to SKU "17612 - 250300"

### Test 2: Legacy Order with Old Lot
1. Find order from Oct 8 with old lot number
2. Change to `awaiting_shipment` status
3. **Expected:** Lot number updates to current active lot

### Test 3: Order with Current Lot
1. Order already has current active lot
2. Status changes to `awaiting_shipment`
3. **Expected:** No update (skip), log "already current"

### Test 4: Multiple SKUs in One Order
1. Order has SKU 17612 (lot 250237) and SKU 17914 (lot 250290)
2. Both have new active lots
3. **Expected:** Both SKUs update to their respective current lots

## Success Metrics
- **Zero orphaned orders** → All orders have valid items after XML re-processing
- **FIFO compliance** → All shipped orders use current lot numbers
- **Data consistency** → Local DB units = ShipStation units (KPI match)
- **Audit trail** → All lot number changes logged with timestamps

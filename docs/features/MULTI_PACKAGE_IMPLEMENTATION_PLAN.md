# Multi-Package Shipment Implementation Plan

**Created:** October 28, 2025  
**Status:** Planning Phase  
**Goal:** Automate the manual package duplication workflow in ShipStation

---

## Problem Statement

### Current Manual Workflow
When an order has a quantity > 1 (e.g., 6 cases of SKU 17612), warehouse staff must:
1. Open the order in ShipStation
2. Verify the correct package type is selected (predefined weight/dimensions)
3. Manually duplicate the package 5 times (for 6 total packages)
4. Ensure all 6 packages have identical weight and dimensions
5. Create the shipment with 6 packages

**Pain Points:**
- ⏱️ Time-consuming manual process
- ⚠️ Human error risk (wrong package count, incorrect dimensions)
- 📉 Slows down fulfillment workflow
- 🔄 Repetitive task that should be automated

---

## Solution Overview

### Automated Multi-Package System
When an order is uploaded from `orders_inbox`:
1. ✅ System detects quantity > 1 for any SKU
2. ✅ Looks up predefined package configuration for that SKU
3. ✅ Uses ShipStation API V2 to create label with multiple packages
4. ✅ Each package gets identical weight/dimensions from config
5. ✅ Warehouse receives ready-to-print multi-package labels

**Benefits:**
- ⚡ Zero manual package duplication
- ✅ 100% consistent package configurations
- 🚀 Faster order processing
- 📊 Audit trail of package configurations

---

## Technical Architecture

### API Strategy: Hybrid V1 + V2

**Keep V1 for:**
- Order uploads (single-package orders)
- Status synchronization
- Order management
- Existing workflows

**Add V2 for:**
- Multi-package label creation (new capability)
- No refactoring of existing V1 code required

**Implementation Pattern:**
```python
if order_requires_multiple_packages(order):
    create_multi_package_label_v2(order)  # NEW V2
else:
    upload_order_v1(order)  # EXISTING V1 (unchanged)
```

---

## Phase 1: Database Schema - Package Configurations

### New Table: `package_configurations`

**Purpose:** Store predefined package weight/dimensions for each SKU

```sql
CREATE TABLE package_configurations (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    package_name VARCHAR(100),
    weight_value DECIMAL(10,2) NOT NULL,  -- e.g., 25.5
    weight_unit VARCHAR(10) NOT NULL DEFAULT 'pound',  -- 'pound' or 'ounce'
    length_value DECIMAL(10,2) NOT NULL,  -- inches
    width_value DECIMAL(10,2) NOT NULL,   -- inches
    height_value DECIMAL(10,2) NOT NULL,  -- inches
    dimension_unit VARCHAR(10) NOT NULL DEFAULT 'inch',
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example data for SKU 17612 (case of product)
INSERT INTO package_configurations (
    sku, package_name, 
    weight_value, weight_unit,
    length_value, width_value, height_value
) VALUES (
    '17612', 'Standard Case - 17612',
    12.5, 'pound',
    16, 12, 8
);
```

**Key Fields:**
- `sku` - Links to your product SKUs
- `package_name` - Human-readable description
- `weight_*` - Weight value and unit for ONE case
- `length/width/height` - Dimensions for ONE case
- `is_active` - Enable/disable package configs

---

## Phase 2: V2 API Integration Module

### New File: `src/services/shipstation/api_client_v2.py`

**Purpose:** Handle all V2 API interactions (separate from existing V1 code)

```python
"""
ShipStation API V2 Client
Handles multi-package label creation
Does NOT modify existing V1 code
"""

import requests
import os
import logging

logger = logging.getLogger(__name__)

V2_BASE_URL = "https://api.shipstation.com/v2"

def get_v2_headers():
    """Get V2 API headers (different auth from V1)"""
    api_key = os.getenv('SHIPSTATION_V2_API_KEY')
    if not api_key:
        raise ValueError("SHIPSTATION_V2_API_KEY not found")
    
    return {
        "API-Key": api_key,
        "Content-Type": "application/json"
    }


def create_multi_package_label(shipment_data):
    """
    Create multi-package label using V2 API
    
    Args:
        shipment_data: dict with shipment details including packages array
    
    Returns:
        dict: Response with label_id, tracking_numbers, label_download URLs
    """
    url = f"{V2_BASE_URL}/labels"
    headers = get_v2_headers()
    
    logger.info(f"Creating multi-package label with {len(shipment_data['shipment']['packages'])} packages")
    
    response = requests.post(url, headers=headers, json=shipment_data, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    logger.info(f"✅ Multi-package label created: {data.get('label_id')}")
    
    return data
```

---

## Phase 3: Package Configuration Management

### New UI: `package_configurations.html`

**Purpose:** CRUD interface for managing package configurations

**Features:**
1. **List View:**
   - Table showing all SKU package configurations
   - Columns: SKU, Package Name, Weight, Dimensions, Status
   - Search/filter by SKU

2. **Add/Edit Form:**
   - SKU (lookup from `sku_lot` or Key Products)
   - Package Name (descriptive)
   - Weight (value + unit dropdown: pound/ounce)
   - Dimensions (L x W x H in inches)
   - Notes field
   - Active/Inactive toggle

3. **Validation:**
   - SKU must exist in system
   - Weight/dimensions > 0
   - No duplicate SKUs

**API Endpoints (Flask):**
```python
# GET /api/package_configurations - List all
# POST /api/package_configurations - Create new
# PUT /api/package_configurations/<id> - Update
# DELETE /api/package_configurations/<id> - Delete
```

---

## Phase 4: Multi-Package Detection Logic

### Update: `src/scheduled_shipstation_upload.py`

**Add detection function:**

```python
def get_package_config_from_db(base_sku):
    """Get package configuration for a SKU"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT weight_value, weight_unit,
                   length_value, width_value, height_value,
                   dimension_unit
            FROM package_configurations
            WHERE sku = %s AND is_active = TRUE
        """, (base_sku,))
        row = cursor.fetchone()
        
        if row:
            return {
                'weight': {'value': float(row[0]), 'unit': row[1]},
                'dimensions': {
                    'length': float(row[2]),
                    'width': float(row[3]),
                    'height': float(row[4]),
                    'unit': row[5]
                }
            }
        return None


def requires_multi_package(order_items):
    """
    Check if order needs multi-package label
    
    Returns:
        bool: True if ANY item has quantity > 1 AND has package config
    """
    for sku, qty, price in order_items:
        base_sku = sku.split(' - ')[0] if ' - ' in sku else sku
        
        if qty > 1:
            package_config = get_package_config_from_db(base_sku)
            if package_config:
                return True
    
    return False
```

---

## Phase 5: Multi-Package Label Builder

### Build V2 shipment payload:

```python
def build_multi_package_shipment(order_number, order_data, order_items):
    """
    Build V2 API shipment payload with multiple packages
    
    Args:
        order_number: Order number
        order_data: Order metadata (addresses, etc.)
        order_items: List of (sku, qty, price) tuples
    
    Returns:
        dict: V2 API shipment payload
    """
    packages = []
    
    for sku, qty, price in order_items:
        base_sku = sku.split(' - ')[0] if ' - ' in sku else sku
        package_config = get_package_config_from_db(base_sku)
        
        if not package_config:
            logger.warning(f"No package config for SKU {base_sku}, skipping")
            continue
        
        # Create 'qty' number of identical packages
        for i in range(qty):
            packages.append({
                "weight": package_config['weight'],
                "dimensions": package_config['dimensions'],
                "insured_value": {
                    "amount": float(price) / 100,  # Convert cents to dollars
                    "currency": "USD"
                }
            })
    
    # Build V2 shipment structure
    shipment = {
        "shipment": {
            "carrier_id": determine_carrier(order_data),  # Map from your carrier logic
            "service_code": determine_service(order_data),  # Map from your service logic
            "ship_to": {
                "name": order_data['ship_to_name'],
                "phone": order_data['ship_to_phone'],
                "address_line1": order_data['ship_to_street1'],
                "city_locality": order_data['ship_to_city'],
                "state_province": order_data['ship_to_state'],
                "postal_code": order_data['ship_to_postal'],
                "country_code": order_data['ship_to_country'],
                "address_residential_indicator": "yes"  # or logic to determine
            },
            "ship_from": {
                # Your warehouse address from config
            },
            "packages": packages,
            "external_order_id": order_number  # Link to your order
        }
    }
    
    return shipment
```

---

## Phase 6: Upload Service Integration

### Modified upload workflow:

```python
def process_order_for_shipstation(order_number):
    """
    Main order processing function
    Decides V1 (single) vs V2 (multi-package)
    """
    # Get order data from orders_inbox
    order_data = get_order_from_inbox(order_number)
    order_items = get_order_items(order_number)
    
    # Decision point: V1 or V2?
    if requires_multi_package(order_items):
        logger.info(f"📦 Order {order_number} requires MULTI-PACKAGE label (V2)")
        
        # Build V2 shipment payload
        shipment_payload = build_multi_package_shipment(
            order_number, 
            order_data, 
            order_items
        )
        
        # Create label via V2 API
        from src.services.shipstation.api_client_v2 import create_multi_package_label
        result = create_multi_package_label(shipment_payload)
        
        # Update local database with V2 response
        update_order_status_v2(order_number, result)
        
        logger.info(f"✅ Multi-package label created: {result['label_id']}")
        
    else:
        logger.info(f"📦 Order {order_number} is SINGLE-PACKAGE (V1)")
        
        # Use existing V1 upload logic (UNCHANGED)
        upload_order_to_shipstation_v1(order_number, order_data, order_items)
```

---

## Phase 7: Status Tracking & Database Updates

### Track V2 labels in database:

**Option A: Add fields to existing `shipped_orders` table:**
```sql
ALTER TABLE shipped_orders 
ADD COLUMN api_version VARCHAR(2) DEFAULT 'v1',  -- 'v1' or 'v2'
ADD COLUMN label_id VARCHAR(100),  -- V2 label_id
ADD COLUMN package_count INTEGER DEFAULT 1;  -- Number of packages
```

**Option B: New table for V2 labels (cleaner):**
```sql
CREATE TABLE shipstation_v2_labels (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(100) NOT NULL,
    label_id VARCHAR(100) NOT NULL UNIQUE,
    shipment_id VARCHAR(100),
    package_count INTEGER NOT NULL,
    total_cost_cents INTEGER,
    tracking_numbers TEXT[],  -- Array of tracking numbers
    label_download_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_number) REFERENCES orders_inbox(order_number)
);
```

---

## Phase 8: Testing & Rollout

### Testing Strategy

**1. Development Testing:**
- Use ShipStation test labels (`testLabel: true` in V1, test environment in V2)
- Create package configs for 2-3 test SKUs
- Upload test orders with varying quantities (1, 2, 5, 10)
- Verify package count matches quantity
- Verify weights/dimensions are correct

**2. Production Pilot:**
- Start with ONE SKU (e.g., 17612)
- Add package configuration
- Monitor for 1 week
- Validate labels print correctly
- Confirm carrier acceptance

**3. Gradual Rollout:**
- Add package configs for top 10 SKUs
- Monitor duplicate order alerts (should decrease)
- Add remaining SKUs over 2-4 weeks

---

## Migration Checklist

### Prerequisites
- [ ] ShipStation plan supports V2 API (Scale-Gold/Accelerate or higher)
- [ ] Generate V2 API key in ShipStation settings
- [ ] Store `SHIPSTATION_V2_API_KEY` in environment variables

### Database Setup
- [ ] Create `package_configurations` table
- [ ] Add sample data for 2-3 test SKUs
- [ ] Decide on Option A (alter table) vs Option B (new table) for V2 tracking

### Code Implementation
- [ ] Create `src/services/shipstation/api_client_v2.py`
- [ ] Create `package_configurations.html` UI
- [ ] Add Flask API endpoints for package config CRUD
- [ ] Update `scheduled_shipstation_upload.py` with detection logic
- [ ] Add multi-package builder function
- [ ] Update upload service to route V1 vs V2

### Testing
- [ ] Test V2 API authentication
- [ ] Test single-package order (should use V1, unchanged)
- [ ] Test multi-package order with config (should use V2)
- [ ] Test multi-package order WITHOUT config (fallback to V1)
- [ ] Verify label downloads and printing
- [ ] Test status sync from ShipStation back to local DB

### Documentation
- [ ] Update `replit.md` with V2 integration details
- [ ] Document package configuration workflow
- [ ] Create operator guide for adding new SKU configs

---

## Rollback Plan

If issues arise:
1. **Set all package configs to `is_active = FALSE`** - System falls back to V1
2. **No V1 code was modified** - Existing workflow continues normally
3. **V2 labels are independent** - Can void in ShipStation if needed
4. **Re-enable gradually** - SKU by SKU basis

---

## Success Metrics

### Operational Metrics
- **Time Savings:** Manual duplication time eliminated (measure before/after)
- **Error Reduction:** Package count mismatches should drop to zero
- **Processing Speed:** Orders with qty > 1 should ship faster

### Technical Metrics
- **V2 API Success Rate:** Target 99%+ successful label creation
- **Package Config Coverage:** % of orders with package configs defined
- **Duplicate Alerts:** Should decrease (no more manual duplication errors)

---

## Cost Analysis

### Development Time Estimate
- **Phase 1 (Database):** 1 hour
- **Phase 2 (V2 API module):** 2 hours
- **Phase 3 (Package Config UI):** 3 hours
- **Phase 4-6 (Integration):** 4 hours
- **Phase 7 (Tracking):** 2 hours
- **Phase 8 (Testing):** 3 hours

**Total: ~15 hours development + testing**

### Ongoing Costs
- **ShipStation V2 API:** Included in Scale-Gold/Accelerate plans (no extra cost)
- **Maintenance:** Minimal (add package configs as new SKUs introduced)

---

## Open Questions

1. **Carrier Selection:**
   - Does carrier/service logic differ for multi-package vs single-package?
   - Are there carrier restrictions on multi-package labels?

2. **Package Configurations:**
   - Do all SKUs have standardized case dimensions?
   - Who maintains package configurations (warehouse manager, ops, admin)?

3. **Edge Cases:**
   - What if order has SKU A (qty=3) + SKU B (qty=2) with different package sizes?
   - Should system create separate shipments or try to mix package types?

4. **Insurance:**
   - Should each package be insured individually?
   - Total order value divided by package count, or fixed per package?

5. **Labels:**
   - Does warehouse have printer that supports multi-page PDF labels?
   - Or need individual ZPL labels?

---

## Next Steps

**Immediate:**
1. Verify ShipStation plan supports V2 API
2. Generate V2 API key
3. Create `package_configurations` table with test data

**Short-term:**
1. Implement V2 API module
2. Build package configuration UI
3. Test with 1-2 orders manually

**Long-term:**
1. Integrate into upload service
2. Pilot with one SKU
3. Gradual rollout across all SKUs

---

## Additional Notes

- **No refactoring required:** V1 code stays 100% intact
- **Gradual adoption:** Can enable SKU-by-SKU
- **Safety net:** Fallback to V1 if no package config exists
- **Monitoring:** Watch duplicate order alerts (should decrease)
- **Warehouse training:** May need brief training on multi-package label printing

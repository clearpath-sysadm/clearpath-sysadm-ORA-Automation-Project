#!/usr/bin/env python3
"""
Fix ShipStation lot assignments for SKU 17612
- Keep only first 34 units as 17612 - 250237 (old lot)  
- Change remaining units to 17612 - 250300 (new lot)
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHIPSTATION_ORDERS_ENDPOINT = "https://ssapi.shipstation.com/orders"

def main():
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("❌ Failed to retrieve ShipStation credentials")
        return False
    
    headers = get_shipstation_headers(api_key, api_secret)
    
    # Step 1: Query ShipStation for awaiting_shipment orders
    print("🔍 Querying ShipStation for orders...")
    
    params = {
        'orderStatus': 'awaiting_shipment',
        'pageSize': 500,
        'page': 1
    }
    
    response = make_api_request(
        url=SHIPSTATION_ORDERS_ENDPOINT,
        method='GET',
        params=params,
        headers=headers,
        timeout=30
    )
    
    if not response or response.status_code != 200:
        logger.error(f"❌ Failed to fetch orders from ShipStation")
        return False
    
    data = response.json()
    all_orders = data.get('orders', [])
    
    # Sort orders by order number to process in consistent order
    all_orders.sort(key=lambda x: x.get('orderNumber', ''))
    
    print(f"✅ Found {len(all_orders)} orders in 'awaiting_shipment' status\n")
    
    # Step 2: Process ONLY orders with 17612 - 250237 that need to change
    orders_to_update = []
    units_allocated = 0  # Track how many units of 250237 we've kept
    MAX_250237_UNITS = 34
    
    for order in all_orders:
        items = order.get('items', [])[:]  # Make a copy
        needs_update = False
        updated_items = []
        
        for idx, item in enumerate(items):
            sku = item.get('sku', '')
            quantity = item.get('quantity', 0)
            
            # Only process items that are currently 17612 - 250237
            if sku == '17612 - 250237':
                # Check if we still have 250237 allocation left
                if units_allocated < MAX_250237_UNITS:
                    # Keep some or all units as 250237
                    if units_allocated + quantity <= MAX_250237_UNITS:
                        # Keep all units as 250237
                        units_allocated += quantity
                        updated_items.append(item)  # No change
                    else:
                        # Split: some stay 250237, rest become 250300
                        # But ShipStation doesn't support splitting items, so move entire item
                        # Decision: if majority stays, keep as 250237; otherwise change to 250300
                        remaining_250237 = MAX_250237_UNITS - units_allocated
                        if remaining_250237 >= quantity / 2:
                            # Keep as 250237
                            units_allocated += quantity
                            updated_items.append(item)
                        else:
                            # Change to 250300
                            item_copy = item.copy()
                            item_copy['sku'] = '17612 - 250300'
                            updated_items.append(item_copy)
                            needs_update = True
                else:
                    # No more 250237 allocation - change to 250300
                    item_copy = item.copy()
                    item_copy['sku'] = '17612 - 250300'
                    updated_items.append(item_copy)
                    needs_update = True
            else:
                # Not a 250237 item, keep as is
                updated_items.append(item)
        
        if needs_update:
            orders_to_update.append({
                'order_data': order,
                'updated_items': updated_items
            })
    
    print(f"\n📊 Analysis:")
    print(f"   Keeping {units_allocated} units as 17612 - 250237")
    print(f"   Orders needing update: {len(orders_to_update)}")
    
    if not orders_to_update:
        print("\n✅ All orders are correctly assigned!")
        return True
    
    # Show what will change
    print(f"\n🔄 Orders that will be updated:")
    for idx, order_info in enumerate(orders_to_update[:10], 1):
        order_num = order_info['order_data'].get('orderNumber')
        print(f"   {idx}. Order #{order_num}")
    if len(orders_to_update) > 10:
        print(f"   ... and {len(orders_to_update) - 10} more")
    
    # Confirm
    print(f"\n⚠️  This will update {len(orders_to_update)} orders in ShipStation")
    print(f"   Changing some 17612 - 250237 items to 17612 - 250300")
    response = input("Proceed? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Update cancelled")
        return False
    
    # Step 3: Update orders
    print(f"\n🔄 Updating {len(orders_to_update)} orders...")
    success_count = 0
    error_count = 0
    
    for order_info in orders_to_update:
        order_data = order_info['order_data']
        updated_items = order_info['updated_items']
        
        # Prepare update payload
        update_payload = {
            'orderId': order_data['orderId'],
            'orderNumber': order_data['orderNumber'],
            'orderKey': order_data['orderKey'],
            'orderDate': order_data['orderDate'],
            'orderStatus': order_data['orderStatus'],
            'customerUsername': order_data.get('customerUsername'),
            'customerEmail': order_data.get('customerEmail'),
            'billTo': order_data['billTo'],
            'shipTo': order_data['shipTo'],
            'items': updated_items,
            'amountPaid': order_data.get('amountPaid', 0),
            'taxAmount': order_data.get('taxAmount', 0),
            'shippingAmount': order_data.get('shippingAmount', 0),
            'customerNotes': order_data.get('customerNotes', ''),
            'internalNotes': order_data.get('internalNotes', ''),
            'paymentMethod': order_data.get('paymentMethod'),
            'requestedShippingService': order_data.get('requestedShippingService'),
            'carrierCode': order_data.get('carrierCode'),
            'serviceCode': order_data.get('serviceCode'),
            'packageCode': order_data.get('packageCode'),
            'confirmation': order_data.get('confirmation'),
            'shipDate': order_data.get('shipDate'),
            'weight': order_data.get('weight'),
            'dimensions': order_data.get('dimensions'),
            'insuranceOptions': order_data.get('insuranceOptions'),
            'internationalOptions': order_data.get('internationalOptions'),
            'advancedOptions': order_data.get('advancedOptions')
        }
        
        # Send update
        update_response = make_api_request(
            url=f"{SHIPSTATION_ORDERS_ENDPOINT}/createorder",
            method='POST',
            data=update_payload,
            headers={**headers, 'Content-Type': 'application/json'},
            timeout=30
        )
        
        if update_response and update_response.status_code == 200:
            print(f"✅ Updated Order #{order_data['orderNumber']}")
            success_count += 1
        else:
            error_msg = update_response.text if update_response else "No response"
            logger.error(f"❌ Failed Order #{order_data['orderNumber']}: {error_msg}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully updated: {success_count} orders")
    if error_count > 0:
        print(f"❌ Failed: {error_count} orders")
    print(f"{'='*60}")
    
    return error_count == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

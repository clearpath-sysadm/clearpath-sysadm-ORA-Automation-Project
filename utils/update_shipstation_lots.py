#!/usr/bin/env python3
"""
Update ShipStation orders with SKU 17612 to assign correct lot numbers
- First 34 units: 17612 - 250237 (old lot)
- Remaining units: 17612 - 250300 (new lot)
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
    print("🔍 Querying ShipStation for orders in 'awaiting_shipment' status...")
    
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
    print(f"✅ Found {len(all_orders)} orders in 'awaiting_shipment' status\n")
    
    # Step 2: Find orders with SKU 17612 (including variations with lots)
    orders_to_update = []
    units_remaining = 34  # First 34 units get the old lot
    
    for order in all_orders:
        items = order.get('items', [])
        # Process ALL 17612 items in each order (not just first one)
        for idx, item in enumerate(items):
            sku = item.get('sku', '')
            # Match SKU 17612 with or without lot number
            if sku == '17612' or sku.startswith('17612 - ') or sku.startswith('17612-'):
                quantity = item.get('quantity', 0)
                
                # Determine lot assignment
                if units_remaining > 0:
                    if quantity <= units_remaining:
                        # Entire item gets old lot
                        lot_assignment = '17612 - 250237'
                        units_remaining -= quantity
                    else:
                        # This item spans both lots - split at threshold
                        logger.warning(f"⚠️ Order #{order.get('orderNumber')} item has {quantity} units which spans both lots")
                        if units_remaining >= quantity / 2:
                            lot_assignment = '17612 - 250237'
                            units_remaining -= quantity
                        else:
                            lot_assignment = '17612 - 250300'
                            units_remaining = 0  # All used up
                else:
                    # All remaining items get new lot
                    lot_assignment = '17612 - 250300'
                
                orders_to_update.append({
                    'orderId': order.get('orderId'),
                    'orderNumber': order.get('orderNumber'),
                    'orderKey': order.get('orderKey'),
                    'item_index': idx,
                    'item': item,
                    'quantity': quantity,
                    'current_sku': sku,
                    'lot_assignment': lot_assignment,
                    'order_data': order
                })
                
                print(f"📦 Order #{order.get('orderNumber')} [Item {idx}] - Qty: {quantity} | Current: {sku} → New: {lot_assignment}")
    
    if not orders_to_update:
        print("\n✅ No orders found with SKU 17612 in awaiting_shipment status")
        return True
    
    print(f"\n📊 Total: {len(orders_to_update)} orders to update")
    print(f"   Lot 250237: {sum(1 for o in orders_to_update if '250237' in o['lot_assignment'])} orders")
    print(f"   Lot 250300: {sum(1 for o in orders_to_update if '250300' in o['lot_assignment'])} orders")
    
    # Step 3: Group by order to update (avoid duplicates)
    orders_by_id = {}
    for order_info in orders_to_update:
        order_id = order_info['orderId']
        if order_id not in orders_by_id:
            orders_by_id[order_id] = {
                'order_data': order_info['order_data'],
                'items_to_update': []
            }
        orders_by_id[order_id]['items_to_update'].append(order_info)
    
    print(f"\n📊 Summary:")
    print(f"   Unique orders to update: {len(orders_by_id)}")
    print(f"   Total line items: {len(orders_to_update)}")
    print(f"   Lot 250237: {sum(1 for o in orders_to_update if '250237' in o['lot_assignment'])} items")
    print(f"   Lot 250300: {sum(1 for o in orders_to_update if '250300' in o['lot_assignment'])} items")
    print(f"   Total units: {sum(o['quantity'] for o in orders_to_update)}")
    
    # Step 4: Confirm with user
    import sys
    if sys.stdin.isatty():
        response = input("\n⚠️  Proceed with updating these orders in ShipStation? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Update cancelled")
            return False
    else:
        print("\n✅ Auto-proceeding (non-interactive mode)")
    
    # Step 5: Update orders in ShipStation
    print("\n🔄 Updating orders in ShipStation...")
    success_count = 0
    error_count = 0
    
    for order_id, order_update_info in orders_by_id.items():
        order_data = order_update_info['order_data'].copy()
        items_to_update = order_update_info['items_to_update']
        
        # Update all 17612 items in this order
        items = order_data.get('items', [])[:]  # Make a copy
        for update_info in items_to_update:
            item_index = update_info['item_index']
            lot_assignment = update_info['lot_assignment']
            if item_index < len(items):
                items[item_index]['sku'] = lot_assignment
        order_data['items'] = items
        
        # Prepare update payload (only include necessary fields to avoid changing other data)
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
            'items': items,
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
        
        # Send update to ShipStation
        update_response = make_api_request(
            url=f"{SHIPSTATION_ORDERS_ENDPOINT}/createorder",
            method='POST',
            data=update_payload,
            headers={**headers, 'Content-Type': 'application/json'},
            timeout=30
        )
        
        if update_response and update_response.status_code == 200:
            items_desc = ", ".join([f"{i['lot_assignment']}" for i in items_to_update])
            print(f"✅ Updated Order #{order_data['orderNumber']} → {items_desc}")
            success_count += 1
        else:
            error_msg = update_response.text if update_response else "No response"
            logger.error(f"❌ Failed to update Order #{order_data['orderNumber']}: {error_msg}")
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

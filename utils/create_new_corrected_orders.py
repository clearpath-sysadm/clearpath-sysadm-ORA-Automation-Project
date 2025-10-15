#!/usr/bin/env python3
"""
Create NEW Manual Orders (100527-100532) with Corrected Items
Based on cancelled orders 100521-100526 customer info
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_utils import make_api_request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from services.database.pg_utils import transaction
from services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers

# Mapping: OLD order (cancelled) -> NEW order number + corrected items
ORDER_MAPPING = {
    223387873: {  # Old 100521
        'new_order_number': '100527',
        'correct_sku': '17612 - 250300',
        'correct_qty': 11,
        'tags': [24637],
        'notes': 'CORRECTED ORDER - Replaces cancelled order 100521 (SS: 223387873)'
    },
    223387885: {  # Old 100522
        'new_order_number': '100528',
        'correct_sku': '17612 - 250300',
        'correct_qty': 2,
        'tags': [24637],
        'notes': 'CORRECTED ORDER - Replaces cancelled order 100522 (SS: 223387885)'
    },
    223387942: {  # Old 100523
        'new_order_number': '100529',
        'correct_sku': '17612 - 250300',
        'correct_qty': 2,
        'tags': [24637],
        'notes': 'CORRECTED ORDER - Replaces cancelled order 100523 (SS: 223387942)'
    },
    223770760: {  # Old 100524
        'new_order_number': '100530',
        'correct_sku': '17612 - 250300',
        'correct_qty': 8,
        'tags': [],
        'notes': 'CORRECTED ORDER - Replaces cancelled order 100524 (SS: 223770760)'
    },
    223770778: {  # Old 100525
        'new_order_number': '100531',
        'correct_sku': '17612 - 250300',
        'correct_qty': 3,
        'tags': [28576],
        'notes': 'CORRECTED ORDER - Replaces cancelled order 100525 (SS: 223770778)'
    },
    224435389: {  # Old 100526
        'new_order_number': '100532',
        'correct_sku': '17612 - 250300',
        'correct_qty': 1,
        'tags': [24745],
        'notes': 'CORRECTED ORDER - Replaces cancelled order 100526 (SS: 224435389)'
    }
}


def load_backup():
    backup_file = 'backups/shipstation_backup_20251015_170017.json'
    with open(backup_file, 'r') as f:
        return json.load(f)


def create_new_order(api_key, api_secret, original_order, mapping):
    """Create a new order with corrected items"""
    
    new_order = {
        'orderNumber': mapping['new_order_number'],
        'orderDate': original_order['orderDate'],
        'orderStatus': 'awaiting_shipment',
        'billTo': original_order['billTo'],
        'shipTo': original_order['shipTo'],
        'items': [{
            'sku': mapping['correct_sku'],
            'name': f"SKU {mapping['correct_sku'].split(' - ')[0]}",
            'quantity': mapping['correct_qty'],
            'unitPrice': original_order['items'][0].get('unitPrice', 0),
        }],
        'internalNotes': mapping['notes'],
        'customerNotes': original_order.get('customerNotes', ''),
        'tagIds': mapping['tags'] if mapping['tags'] else None,
        'advancedOptions': original_order.get('advancedOptions', {})
    }
    
    if new_order['tagIds'] is None:
        del new_order['tagIds']
    
    print(f"Creating NEW order {mapping['new_order_number']}...")
    print(f"  Items: {mapping['correct_sku']} x {mapping['correct_qty']}")
    print(f"  Customer: {original_order['shipTo']['name']}")
    
    try:
        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'
        
        response = make_api_request(
            url='https://ssapi.shipstation.com/orders/createorder',
            method='POST',
            data=new_order,
            headers=headers
        )
        
        response_data = response.json() if hasattr(response, 'json') else response
        new_order_id = response_data.get('orderId')
        print(f"✅ Created order {mapping['new_order_number']} with ShipStation ID: {new_order_id}")
        return new_order_id
        
    except Exception as e:
        print(f"❌ Failed to create order {mapping['new_order_number']}: {e}")
        return None


def update_local_database(order_number, new_shipstation_id, order_date):
    """Add new order to local database"""
    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders_inbox (order_number, shipstation_order_id, order_date, status, created_at, updated_at)
            VALUES (%s, %s, %s, 'pending', NOW(), NOW())
            ON CONFLICT (order_number) DO UPDATE 
            SET shipstation_order_id = EXCLUDED.shipstation_order_id,
                order_date = EXCLUDED.order_date,
                status = 'pending',
                updated_at = NOW()
        ''', (order_number, new_shipstation_id, order_date))
        
        print(f"✅ Added order {order_number} to local database")


def main():
    print("=" * 80)
    print("CREATE NEW CORRECTED ORDERS (100527-100532)")
    print("=" * 80)
    print("\nThis will create NEW orders with corrected items")
    print()
    
    backup_data = load_backup()
    
    api_key = os.environ.get('SHIPSTATION_API_KEY')
    api_secret = os.environ.get('SHIPSTATION_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ ShipStation credentials not found")
        return 1
    
    original_orders = {}
    for order in backup_data['orders']:
        if order['orderId'] in ORDER_MAPPING:
            original_orders[order['orderId']] = order
    
    print(f"Found {len(original_orders)} original orders\n")
    
    response = input("Proceed with creating NEW orders 100527-100532? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return 0
    
    print()
    
    success_count = 0
    fail_count = 0
    
    for original_id, mapping in sorted(ORDER_MAPPING.items(), key=lambda x: x[1]['new_order_number']):
        print(f"\n--- Creating Order {mapping['new_order_number']} ---")
        
        original_order = original_orders.get(original_id)
        if not original_order:
            print(f"❌ Original order {original_id} not found in backup")
            fail_count += 1
            continue
        
        new_id = create_new_order(api_key, api_secret, original_order, mapping)
        
        if new_id:
            update_local_database(mapping['new_order_number'], new_id, original_order['orderDate'])
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully created: {success_count}/6")
    print(f"❌ Failed: {fail_count}/6")
    print("=" * 80)
    
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

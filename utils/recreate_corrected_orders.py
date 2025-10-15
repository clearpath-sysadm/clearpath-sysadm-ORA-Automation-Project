#!/usr/bin/env python3
"""
Recreate Manual Orders with Correct Items
Replaces cancelled orders 100521-100526 with corrected versions
"""

import json
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_utils import make_api_request

# Import database utilities
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from services.database.pg_utils import transaction
from services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers

# Mapping of cancelled orders to corrected versions
CORRECTIONS = {
    223387873: {  # 100521
        'order_number': '100521',
        'correct_sku': '17612 - 250300',
        'correct_qty': 11,
        'was_qty': 5,
        'tags': [24637],
        'original_notes': 'CORRECTED ORDER - Original: 688195 - Mis-shipped on 10/06/2025'
    },
    223387885: {  # 100522
        'order_number': '100522',
        'correct_sku': '17612 - 250300',
        'correct_qty': 2,
        'was_qty': 1,
        'tags': [24637],
        'original_notes': 'CORRECTED ORDER - Original: 688245 - Mis-shipped on 10/06/2025'
    },
    223387942: {  # 100523
        'order_number': '100523',
        'correct_sku': '17612 - 250300',
        'correct_qty': 2,
        'was_sku': '17914 - 250297',
        'was_qty': 2,
        'tags': [24637],
        'original_notes': 'CORRECTED ORDER - Original: 688595 - Mis-shipped on 10/06/2025'
    },
    223770760: {  # 100524
        'order_number': '100524',
        'correct_sku': '17612 - 250300',
        'correct_qty': 8,
        'was_qty': 1,
        'tags': [],
        'original_notes': 'Recreated from order 100518 - Client duplicate conflict'
    },
    223770778: {  # 100525
        'order_number': '100525',
        'correct_sku': '17612 - 250300',
        'correct_qty': 3,
        'was_qty': 2,
        'tags': [28576],
        'original_notes': 'Recreated from order 100519 - Client duplicate conflict'
    },
    224435389: {  # 100526
        'order_number': '100526',
        'correct_sku': '17612 - 250300',
        'correct_qty': 1,
        'was_qty': 1,
        'tags': [24745],
        'original_notes': 'COPY OF ORDER 100520 - Created via API'
    }
}


def load_backup():
    """Load the backup file"""
    backup_file = 'backups/shipstation_backup_20251015_170017.json'
    with open(backup_file, 'r') as f:
        return json.load(f)


def create_corrected_order(api_key, api_secret, original_order, correction):
    """Create a corrected version of the order in ShipStation"""
    
    # Build new internal notes
    new_notes = f"RECREATED ORDER - Replaces cancelled ShipStation ID {original_order['orderId']}\n"
    new_notes += f"Original had incorrect items. Corrected on {datetime.now().strftime('%m/%d/%Y')}\n"
    new_notes += f"Previous notes: {correction['original_notes']}"
    
    # Build the corrected order payload
    new_order = {
        'orderNumber': correction['order_number'],
        'orderDate': original_order['orderDate'],
        'orderStatus': 'awaiting_shipment',
        'billTo': original_order['billTo'],
        'shipTo': original_order['shipTo'],
        'items': [{
            'sku': correction['correct_sku'],
            'name': f"SKU {correction['correct_sku'].split(' - ')[0]}",
            'quantity': correction['correct_qty'],
            'unitPrice': original_order['items'][0].get('unitPrice', 0),
        }],
        'internalNotes': new_notes,
        'customerNotes': original_order.get('customerNotes', ''),
        'tagIds': correction['tags'] if correction['tags'] else None,
        'advancedOptions': original_order.get('advancedOptions', {})
    }
    
    # Remove None values
    if new_order['tagIds'] is None:
        del new_order['tagIds']
    
    print(f"Creating corrected order {correction['order_number']}...")
    print(f"  Items: {correction['correct_sku']} x {correction['correct_qty']}")
    print(f"  Tags: {correction['tags']}")
    
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
        print(f"✅ Created order {correction['order_number']} with ShipStation ID: {new_order_id}")
        return new_order_id
        
    except Exception as e:
        print(f"❌ Failed to create order {correction['order_number']}: {e}")
        return None


def update_local_database(order_number, new_shipstation_id):
    """Update the local database with new ShipStation ID and status"""
    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders_inbox 
            SET shipstation_order_id = %s,
                status = 'pending',
                updated_at = NOW()
            WHERE order_number = %s
        ''', (new_shipstation_id, order_number))
        
        print(f"✅ Updated local database for order {order_number}")


def main():
    print("=" * 80)
    print("RECREATE CORRECTED ORDERS")
    print("=" * 80)
    print("\nThis will create NEW orders in ShipStation with corrected items")
    print("Original orders (100521-100526) were cancelled/deleted")
    print()
    
    # Load backup
    backup_data = load_backup()
    
    # Get API credentials from environment
    import os
    api_key = os.environ.get('SHIPSTATION_API_KEY')
    api_secret = os.environ.get('SHIPSTATION_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ ShipStation credentials not found in environment")
        return 1
    
    # Find original orders in backup
    original_orders = {}
    for order in backup_data['orders']:
        if order['orderId'] in CORRECTIONS:
            original_orders[order['orderId']] = order
    
    print(f"Found {len(original_orders)} orders to recreate\n")
    
    # Confirm
    response = input("Proceed with order creation? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled by user")
        return 0
    
    print()
    
    # Create each corrected order
    success_count = 0
    fail_count = 0
    
    for original_id, correction in sorted(CORRECTIONS.items(), key=lambda x: x[1]['order_number']):
        print(f"\n--- Creating Order {correction['order_number']} ---")
        
        original_order = original_orders.get(original_id)
        if not original_order:
            print(f"❌ Original order {original_id} not found in backup")
            fail_count += 1
            continue
        
        new_id = create_corrected_order(api_key, api_secret, original_order, correction)
        
        if new_id:
            update_local_database(correction['order_number'], new_id)
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully created: {success_count}/{len(CORRECTIONS)}")
    print(f"❌ Failed: {fail_count}/{len(CORRECTIONS)}")
    print("=" * 80)
    
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

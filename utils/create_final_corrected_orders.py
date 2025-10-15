#!/usr/bin/env python3
"""
Create FINAL Corrected Orders (100527-100532)
Using CORRECT customer info from cancelled orders
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_utils import make_api_request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from services.database.pg_utils import transaction
from services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers

# Correct customer data from cancelled orders
NEW_ORDERS = [
    {
        'new_order_number': '100527',
        'original_cancelled_id': 224817179,
        'items': [{'sku': '17612 - 250300', 'quantity': 11, 'unitPrice': 0.0}],
        'ship_to': {
            'name': 'Robert Nakisher',
            'company': 'LAKEVIEW FAMILY DENTAL - FARMINGTON HILLS',
            'street1': '28200 ORCHARD LAKE RD STE 100',
            'city': 'FARMINGTN HLS',
            'state': 'MI',
            'postalCode': '48334-3761',
            'country': 'US',
            'phone': '3049184302'
        },
        'tags': [24637],
        'notes': 'CORRECTED ORDER - Replaces cancelled 100521 (SS:224817179)'
    },
    {
        'new_order_number': '100528',
        'original_cancelled_id': 224817794,
        'items': [{'sku': '17612 - 250300', 'quantity': 2, 'unitPrice': 0.0}],
        'ship_to': {
            'name': 'Robert Nakisher',
            'company': 'LAKEVIEW FAMILY DENTAL- LIVONIA',
            'street1': '31215 5 MILE RD',
            'city': 'LIVONIA',
            'state': 'MI',
            'postalCode': '48154-3627',
            'country': 'US',
            'phone': '304-918-4302'
        },
        'tags': [24637],
        'notes': 'CORRECTED ORDER - Replaces cancelled 100522 (SS:224817794)'
    },
    {
        'new_order_number': '100529',
        'original_cancelled_id': 224818379,
        'items': [{'sku': '17612 - 250300', 'quantity': 2, 'unitPrice': 0.0}],
        'ship_to': {
            'name': 'Robert Nakisher',
            'company': 'LAKEVIEW FAMILY DENTAL SOUTHFIELD',
            'street1': '26206 W 12 MILE RD STE 303',
            'city': 'SOUTHFIELD',
            'state': 'MI',
            'postalCode': '48034-8501',
            'country': 'US',
            'phone': '3049184302'
        },
        'tags': [24637],
        'notes': 'CORRECTED ORDER - Replaces cancelled 100523 (SS:224818379)'
    },
    {
        'new_order_number': '100530',
        'original_cancelled_id': 224818828,
        'items': [{'sku': '17612 - 250300', 'quantity': 8, 'unitPrice': 0.0}],
        'ship_to': {
            'name': 'Robert Nakisher',
            'company': 'LAKEVIEW FAMILY DENTAL- KEEGO HARBOR',
            'street1': '2819 ORCHARD LAKE RD',
            'city': 'KEEGO HARBOR',
            'state': 'MI',
            'postalCode': '48320-1448',
            'country': 'US',
            'phone': '304-918-4302'
        },
        'tags': [],
        'notes': 'CORRECTED ORDER - Replaces cancelled 100524 (SS:224818828)'
    },
    {
        'new_order_number': '100531',
        'original_cancelled_id': 225040390,
        'items': [{'sku': '17612 - 250300', 'quantity': 3, 'unitPrice': 0.0}],
        'ship_to': {
            'name': 'Brazos River Dental',
            'company': 'BRAZOS RIVER DENTAL',
            'street1': '917 E HUBBARD ST',
            'city': 'MINERAL WELLS',
            'state': 'TX',
            'postalCode': '76067-5450',
            'country': 'US',
            'phone': '3049184302'
        },
        'tags': [28576],
        'notes': 'CORRECTED ORDER - Replaces cancelled 100525 (SS:225040390)'
    },
    {
        'new_order_number': '100532',
        'original_cancelled_id': 225041006,
        'items': [{'sku': '17612 - 250300', 'quantity': 1, 'unitPrice': 0.0}],
        'ship_to': {
            'name': 'Eric Bordlee',
            'company': 'BORDLEE FAMILY & COSMETIC DENTISTRY',
            'street1': '6204 RIDGE AVE',
            'city': 'CINCINNATI',
            'state': 'OH',
            'postalCode': '45213-1316',
            'country': 'US',
            'phone': '3049184302'
        },
        'tags': [24745],
        'notes': 'CORRECTED ORDER - Replaces cancelled 100526 (SS:225041006)'
    }
]


def create_order(api_key, api_secret, order_data):
    """Create order in ShipStation"""
    
    new_order = {
        'orderNumber': order_data['new_order_number'],
        'orderDate': '2025-10-14T00:00:00.0000000',
        'orderStatus': 'awaiting_shipment',
        'billTo': {
            'name': order_data['ship_to']['name'],
            'company': order_data['ship_to']['company'],
            'street1': '',
            'city': '',
            'state': '',
            'postalCode': '',
            'country': 'US'
        },
        'shipTo': order_data['ship_to'],
        'items': [{'sku': item['sku'], 'name': f"SKU {item['sku'].split(' - ')[0]}", 'quantity': item['quantity'], 'unitPrice': item['unitPrice']} for item in order_data['items']],
        'internalNotes': order_data['notes'],
        'tagIds': order_data['tags'] if order_data['tags'] else None
    }
    
    if new_order['tagIds'] is None:
        del new_order['tagIds']
    
    print(f"Creating order {order_data['new_order_number']}...")
    print(f"  Company: {order_data['ship_to']['company']}")
    print(f"  Items: {order_data['items'][0]['sku']} x {order_data['items'][0]['quantity']}")
    
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
        new_id = response_data.get('orderId')
        print(f"✅ Created ShipStation ID: {new_id}")
        return new_id
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


def update_database(order_number, shipstation_id):
    """Add to database"""
    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders_inbox (order_number, shipstation_order_id, order_date, status, created_at, updated_at)
            VALUES (%s, %s, '2025-10-14', 'pending', NOW(), NOW())
            ON CONFLICT (order_number) DO UPDATE 
            SET shipstation_order_id = EXCLUDED.shipstation_order_id,
                status = 'pending',
                updated_at = NOW()
        ''', (order_number, shipstation_id))
        print(f"✅ Added to database\n")


def main():
    print("=" * 80)
    print("CREATE FINAL CORRECTED ORDERS (100527-100532)")
    print("=" * 80)
    print()
    
    api_key = os.environ.get('SHIPSTATION_API_KEY')
    api_secret = os.environ.get('SHIPSTATION_API_SECRET')
    
    response = input("Create orders 100527-100532 with CORRECT customer info? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        return 0
    
    print()
    success = 0
    fail = 0
    
    for order_data in NEW_ORDERS:
        new_id = create_order(api_key, api_secret, order_data)
        if new_id:
            update_database(order_data['new_order_number'], new_id)
            success += 1
        else:
            fail += 1
    
    print("=" * 80)
    print(f"✅ Success: {success}/6")
    print(f"❌ Failed: {fail}/6")
    print("=" * 80)
    
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

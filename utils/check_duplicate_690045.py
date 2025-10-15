#!/usr/bin/env python3
"""Check if there are multiple ShipStation orders for 690045"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

api_key, api_secret = get_shipstation_credentials()
headers = get_shipstation_headers(api_key, api_secret)

# Search for ALL orders with number containing 690045
for page in range(1, 5):
    response = make_api_request(
        method='GET',
        url='https://ssapi.shipstation.com/orders',
        headers=headers,
        params={
            'orderNumber': '690045',
            'page': page,
            'pageSize': 500
        }
    )
    
    data = response.json()
    
    if data and 'orders' in data and len(data['orders']) > 0:
        print(f"\n=== Page {page}: Found {len(data['orders'])} orders ===")
        for order in data['orders']:
            print(f"\nOrder Number: {order.get('orderNumber')}")
            print(f"Order ID: {order.get('orderId')}")
            print(f"Order Status: {order.get('orderStatus')}")
            print(f"Items:")
            total_qty = 0
            for item in order.get('items', []):
                qty = item.get('quantity')
                total_qty += qty
                print(f"  - SKU: {item.get('sku')} | Qty: {qty}")
            print(f"TOTAL QUANTITY: {total_qty}")
    else:
        print(f"Page {page}: No more orders")
        break

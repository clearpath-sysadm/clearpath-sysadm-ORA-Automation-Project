#!/usr/bin/env python3
"""Check order 690045 in ShipStation to compare quantities"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

api_key, api_secret = get_shipstation_credentials()
headers = get_shipstation_headers(api_key, api_secret)

# Get order 690045 from ShipStation
response = make_api_request(
    method='GET',
    url='https://ssapi.shipstation.com/orders',
    headers=headers,
    params={'orderNumber': '690045'}
)

data = response.json()

if data and 'orders' in data and len(data['orders']) > 0:
    order = data['orders'][0]
    print(f"Order Number: {order.get('orderNumber')}")
    print(f"Order Date: {order.get('orderDate')}")
    print(f"Order Status: {order.get('orderStatus')}")
    print(f"\nItems in ShipStation:")
    for item in order.get('items', []):
        print(f"  - SKU: {item.get('sku')} | Qty: {item.get('quantity')} | Name: {item.get('name')}")
else:
    print("Order not found in ShipStation")

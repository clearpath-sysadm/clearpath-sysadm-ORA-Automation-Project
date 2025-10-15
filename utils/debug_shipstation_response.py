#!/usr/bin/env python3
"""Debug script to see what ShipStation API actually returns"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request
import json

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"

api_key, api_secret = get_shipstation_credentials()
headers = get_shipstation_headers(api_key, api_secret)

params = {
    'orderStatus': 'awaiting_shipment',
    'pageSize': 5,  # Just get 5 to see structure
    'page': 1
}

response = make_api_request(
    method='GET',
    url=f"{SHIPSTATION_BASE_URL}/orders",
    headers=headers,
    params=params
)

print("=" * 80)
print("SHIPSTATION API RESPONSE:")
print("=" * 80)
print(json.dumps(response, indent=2))

if response and 'orders' in response:
    print(f"\nTotal orders in response: {len(response['orders'])}")
    if response['orders']:
        print(f"\nFirst order structure:")
        print(json.dumps(response['orders'][0], indent=2))
else:
    print(f"\nResponse keys: {response.keys() if response else 'None'}")

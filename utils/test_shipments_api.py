#!/usr/bin/env python3
"""
Quick diagnostic script to test ShipStation shipments API
and see what's actually being returned.
"""

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import make_api_request
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers

def test_shipments_query():
    """Test various shipments queries to diagnose the issue."""
    
    api_key, api_secret = get_shipstation_credentials()
    
    if not api_key or not api_secret:
        print("❌ ShipStation credentials not found in environment")
        return
    
    print("=" * 80)
    print("🔍 SHIPSTATION SHIPMENTS API DIAGNOSTIC")
    print("=" * 80)
    
    # Test 1: Query with createDate for last 24 hours
    print("\n📋 TEST 1: Last 24 hours (createDate)")
    print("-" * 40)
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    params_create = {
        'createDateStart': yesterday.strftime('%Y-%m-%dT%H:%M:%S'),
        'createDateEnd': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'pageSize': 50
    }
    print(f"Query params: {json.dumps(params_create, indent=2)}")
    
    headers = get_shipstation_headers(api_key, api_secret)
    response = make_api_request(
        url='https://ssapi.shipstation.com/shipments',
        method='GET',
        headers=headers,
        params=params_create
    )
    
    if response and response.status_code == 200:
        data = response.json()
        shipments = data.get('shipments', [])
        print(f"✅ Found {len(shipments)} shipments")
        
        if shipments:
            print("\n📦 Sample shipments:")
            for s in shipments[:5]:
                print(f"  - Order #{s.get('orderNumber')}: {s.get('trackingNumber')} (created: {s.get('createDate')})")
    else:
        print(f"❌ API returned status: {response.status_code if response else 'None'}")
    
    # Test 2: Query with shipDate for today
    print("\n📋 TEST 2: Today only (shipDate)")
    print("-" * 40)
    today_start = now.replace(hour=0, minute=0, second=0)
    today_end = now.replace(hour=23, minute=59, second=59)
    
    params_ship = {
        'shipDateStart': today_start.strftime('%Y-%m-%d'),
        'shipDateEnd': today_end.strftime('%Y-%m-%d'),
        'pageSize': 50
    }
    print(f"Query params: {json.dumps(params_ship, indent=2)}")
    
    headers = get_shipstation_headers(api_key, api_secret)
    response = make_api_request(
        url='https://ssapi.shipstation.com/shipments',
        method='GET',
        headers=headers,
        params=params_ship
    )
    
    if response and response.status_code == 200:
        data = response.json()
        shipments = data.get('shipments', [])
        print(f"✅ Found {len(shipments)} shipments")
        
        if shipments:
            print("\n📦 Sample shipments:")
            for s in shipments[:5]:
                print(f"  - Order #{s.get('orderNumber')}: {s.get('trackingNumber')} (shipDate: {s.get('shipDate')})")
    else:
        print(f"❌ API returned status: {response.status_code if response else 'None'}")
    
    # Test 3: Search for specific order 692135
    print("\n📋 TEST 3: Search for Order 692135 specifically")
    print("-" * 40)
    
    params_specific = {
        'orderNumber': '692135',
        'pageSize': 10
    }
    print(f"Query params: {json.dumps(params_specific, indent=2)}")
    
    headers = get_shipstation_headers(api_key, api_secret)
    response = make_api_request(
        url='https://ssapi.shipstation.com/shipments',
        method='GET',
        headers=headers,
        params=params_specific
    )
    
    if response and response.status_code == 200:
        data = response.json()
        shipments = data.get('shipments', [])
        print(f"✅ Found {len(shipments)} shipments")
        
        if shipments:
            print("\n📦 Shipment details:")
            for s in shipments:
                print(json.dumps(s, indent=2))
    else:
        print(f"❌ API returned status: {response.status_code if response else 'None'}")
    
    print("\n" + "=" * 80)
    print("🏁 DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    test_shipments_query()

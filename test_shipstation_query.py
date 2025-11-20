#!/usr/bin/env python3
"""
Test script to manually query ShipStation API for a specific order
"""
import os
import sys
import requests
import json
from base64 import b64encode

def query_shipstation_order(order_number):
    """Query ShipStation for a specific order by order number"""
    
    # Get credentials from environment
    api_key = os.environ.get('SHIPSTATION_API_KEY')
    api_secret = os.environ.get('SHIPSTATION_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ ERROR: ShipStation API credentials not found in environment")
        return None
    
    # Create auth header
    credentials = f"{api_key}:{api_secret}"
    encoded_credentials = b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    # Query by order number
    url = 'https://ssapi.shipstation.com/orders'
    params = {
        'orderNumber': order_number
    }
    
    print("=" * 80)
    print(f"🔍 Querying ShipStation for order: {order_number}")
    print(f"📡 URL: {url}")
    print(f"📋 Params: {params}")
    print("=" * 80)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"\n✅ Response Status Code: {response.status_code}")
        print(f"📦 Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'retry-after', 'x-rate-limit-remaining', 'x-rate-limit-limit']:
                print(f"   {key}: {value}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 Response Data:")
            print(json.dumps(data, indent=2))
            
            if 'orders' in data:
                order_count = len(data['orders'])
                print(f"\n✅ Found {order_count} order(s) for order number {order_number}")
                
                if order_count > 0:
                    order = data['orders'][0]
                    print(f"\n📦 Order Details:")
                    print(f"   Order ID: {order.get('orderId')}")
                    print(f"   Order Number: {order.get('orderNumber')}")
                    print(f"   Order Status: {order.get('orderStatus')}")
                    print(f"   Order Date: {order.get('orderDate')}")
                    print(f"   Ship Date: {order.get('shipDate')}")
                    print(f"   Items: {len(order.get('items', []))}")
                    
                    if order.get('items'):
                        print(f"\n   📋 Items:")
                        for item in order['items']:
                            print(f"      - {item.get('name')} (SKU: {item.get('sku')}, Qty: {item.get('quantity')})")
                else:
                    print(f"\n⚠️ No orders found for order number {order_number}")
                    print(f"   This could mean:")
                    print(f"   1. Order was deleted from ShipStation")
                    print(f"   2. Order number doesn't exist")
                    print(f"   3. API key doesn't have access to this order")
            
            return data
            
        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 'unknown')
            print(f"\n⚠️ RATE LIMITED (429)")
            print(f"   Retry-After: {retry_after} seconds")
            print(f"   Response: {response.text}")
            
        elif response.status_code == 404:
            print(f"\n❌ NOT FOUND (404)")
            print(f"   Order {order_number} does not exist in ShipStation")
            print(f"   Response: {response.text}")
            
        elif response.status_code == 403:
            print(f"\n❌ FORBIDDEN (403)")
            print(f"   API key doesn't have permission to access this order")
            print(f"   Response: {response.text}")
            
        else:
            print(f"\n❌ ERROR: Unexpected status code")
            print(f"   Response: {response.text}")
        
        return None
        
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out (30 seconds)")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: Connection error: {e}")
        return None
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    order_number = sys.argv[1] if len(sys.argv) > 1 else '698985'
    result = query_shipstation_order(order_number)
    
    print("\n" + "=" * 80)
    if result:
        print("✅ Query completed successfully")
    else:
        print("❌ Query failed or returned no data")
    print("=" * 80)

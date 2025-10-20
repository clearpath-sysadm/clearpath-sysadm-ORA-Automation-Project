#!/usr/bin/env python3
"""
Populate full details for order 100528 conflict alert
"""

import sys
import os
import json

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database import get_connection
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

def main():
    """Fetch and populate order 100528 details"""
    
    # Get ShipStation credentials
    api_key, api_secret = get_shipstation_credentials()
    headers = get_shipstation_headers(api_key, api_secret)
    
    # Fetch the duplicate order (ID: 226240850)
    print("Fetching duplicate order 226240850...")
    duplicate_url = 'https://ssapi.shipstation.com/orders/226240850'
    duplicate_response = make_api_request(url=duplicate_url, method='GET', headers=headers, timeout=30)
    
    if not duplicate_response or duplicate_response.status_code != 200:
        print("❌ Failed to fetch duplicate order")
        return
    
    duplicate_order = duplicate_response.json()
    
    # Extract duplicate order details
    duplicate_ship_to = duplicate_order.get('shipTo') or {}
    duplicate_company = (duplicate_ship_to.get('company') or '').strip() or None
    duplicate_items = []
    for item in duplicate_order.get('items', []):
        sku = item.get('sku', '')
        qty = item.get('quantity', 0)
        duplicate_items.append({'sku': sku, 'quantity': qty})
    
    print(f"Duplicate Company: {duplicate_company}")
    print(f"Duplicate Items: {duplicate_items}")
    
    # Search for original order with same order number
    print("\nSearching for original order 100528...")
    search_url = f'https://ssapi.shipstation.com/orders?orderNumber=100528'
    search_resp = make_api_request(url=search_url, method='GET', headers=headers, timeout=30)
    
    if not search_resp or search_resp.status_code != 200:
        print("❌ Failed to search for original order")
        return
    
    search_response = search_resp.json()
    orders = search_response.get('orders', [])
    
    # Find the shipped order (different ID)
    original_order = None
    for order in orders:
        order_id = str(order.get('orderId'))
        order_status = order.get('orderStatus', '')
        if order_id != '226240850' and order_status == 'shipped':
            original_order = order
            print(f"✅ Found original order ID: {order_id}")
            break
    
    if not original_order:
        print("❌ No shipped order found")
        return
    
    # Extract original order details
    original_ship_to = original_order.get('shipTo') or {}
    original_company = (original_ship_to.get('company') or '').strip() or None
    original_items = []
    for item in original_order.get('items', []):
        sku = item.get('sku', '')
        qty = item.get('quantity', 0)
        original_items.append({'sku': sku, 'quantity': qty})
    
    print(f"Original Company: {original_company}")
    print(f"Original Items: {original_items}")
    
    # Update database
    print("\nUpdating database...")
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE manual_order_conflicts
        SET original_company = %s,
            original_items = %s,
            duplicate_company = %s,
            duplicate_items = %s
        WHERE conflicting_order_number = '100528'
    """, (original_company, json.dumps(original_items), duplicate_company, json.dumps(duplicate_items)))
    
    conn.commit()
    conn.close()
    
    print("✅ Database updated successfully!")
    print("\n=== Final Data ===")
    print(f"Original: {original_company} | {original_items}")
    print(f"Duplicate: {duplicate_company} | {duplicate_items}")

if __name__ == '__main__':
    main()

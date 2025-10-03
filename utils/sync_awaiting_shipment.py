#!/usr/bin/env python3
"""
One-time utility to sync orders with 'awaiting_shipment' status from ShipStation.
Fixes data mismatches and imports manual orders not in local database.
"""
import sys
import os
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import requests
from requests.auth import HTTPBasicAuth
from src.services.database.db_utils import execute_query, transaction
from src.services.shipstation.api_client import get_shipstation_credentials

def fetch_awaiting_shipment_orders():
    """Fetch all orders with awaiting_shipment status from ShipStation."""
    api_key, api_secret = get_shipstation_credentials()
    
    url = 'https://ssapi.shipstation.com/orders'
    params = {
        'orderStatus': 'awaiting_shipment',
        'pageSize': 500
    }
    
    response = requests.get(url, auth=HTTPBasicAuth(api_key, api_secret), params=params)
    response.raise_for_status()
    
    data = response.json()
    return data.get('orders', [])

def sync_order_status(order):
    """Sync a single order's status from ShipStation to local database."""
    order_number = order.get('orderNumber')
    shipstation_order_id = str(order.get('orderId'))
    order_status = order.get('orderStatus', 'awaiting_shipment')
    
    carrier_code = order.get('carrierCode', '')
    service_code = order.get('serviceCode', '')
    carrier_id = order.get('advancedOptions', {}).get('carrierId')
    service_name = order.get('serviceName', '')
    
    print(f"\n🔄 Processing Order #{order_number} (SS ID: {shipstation_order_id})")
    print(f"   ShipStation Status: {order_status}")
    print(f"   Carrier: {carrier_code}, Service: {service_code}, Carrier ID: {carrier_id}")
    
    # Check if order exists in orders_inbox
    rows = execute_query(
        "SELECT id, status FROM orders_inbox WHERE order_number = ?",
        (order_number,)
    )
    
    if rows:
        local_id, local_status = rows[0]
        print(f"   Local Status: {local_status}")
        
        if local_status != 'awaiting_shipment':
            # Update status to awaiting_shipment
            with transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE orders_inbox 
                    SET status = ?,
                        shipstation_order_id = ?,
                        shipping_carrier_code = ?,
                        shipping_service_code = ?,
                        shipping_carrier_id = ?,
                        shipping_service_name = ?
                    WHERE order_number = ?
                """, (
                    'awaiting_shipment',
                    shipstation_order_id,
                    carrier_code,
                    service_code,
                    carrier_id,
                    service_name,
                    order_number
                ))
            print(f"   ✅ Updated: {local_status} → awaiting_shipment")
            return 'updated'
        else:
            print(f"   ℹ️  Already awaiting_shipment")
            return 'already_synced'
    
    # Order doesn't exist locally - manual ShipStation order
    print(f"   ⚠️  Order #{order_number} not found in local database")
    print(f"   This order exists only in ShipStation (manual order or data loss)")
    print(f"   Manual orders should be synced by the manual_shipstation_sync service")
    return 'not_found'

def main():
    print("=" * 60)
    print("Syncing Awaiting Shipment Orders from ShipStation")
    print("=" * 60)
    
    # Fetch orders
    print("\n📡 Fetching orders with 'awaiting_shipment' status from ShipStation...")
    orders = fetch_awaiting_shipment_orders()
    print(f"✅ Found {len(orders)} orders")
    
    # Sync each order
    results = {
        'updated': 0,
        'already_synced': 0,
        'not_found': 0
    }
    
    for order in orders:
        result = sync_order_status(order)
        if result in results:
            results[result] += 1
    
    print("\n" + "=" * 60)
    print("📊 Sync Summary:")
    print(f"   Updated status: {results['updated']}")
    print(f"   Already synced: {results['already_synced']}")
    print(f"   Not found locally: {results['not_found']}")
    print("=" * 60)
    
    # Show current local state
    print("\n📋 Local Database After Sync:")
    rows = execute_query("""
        SELECT status, COUNT(*) 
        FROM orders_inbox 
        GROUP BY status
    """)
    for row in rows:
        print(f"   {row[0]}: {row[1]} orders")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Utility to change order number in ShipStation
This script fetches an order by its current number, updates the order number, and saves it back to ShipStation

Usage:
    python utils/change_order_number.py <shipstation_order_id> <new_order_number>
    
Example:
    python utils/change_order_number.py 224419681 100526
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from config.settings import settings
from utils.api_utils import make_api_request
import json


def fetch_order_by_id(api_key, api_secret, order_id):
    """
    Fetch a single order from ShipStation by order ID
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        order_id: ShipStation order ID
        
    Returns:
        dict: Order data or None if not found
    """
    headers = get_shipstation_headers(api_key, api_secret)
    
    # Get order by ID
    url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
    
    print(f"🔍 Fetching order ID {order_id}...")
    
    response = make_api_request(
        url=url,
        method='GET',
        headers=headers,
        timeout=30
    )
    
    if response and response.status_code == 200:
        order = response.json()
        print(f"✅ Found order: {order.get('orderNumber')} (ID: {order.get('orderId')})")
        print(f"   Status: {order.get('orderStatus')}")
        print(f"   Company: {order.get('shipTo', {}).get('company')}")
        print(f"   Items: {len(order.get('items', []))}")
        return order
    else:
        print(f"❌ API request failed: {response.status_code if response else 'No response'}")
        return None


def update_order_number(api_key, api_secret, order_data, new_order_number):
    """
    Update the order number in ShipStation
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        order_data: Full order data from ShipStation
        new_order_number: New order number to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    headers = get_shipstation_headers(api_key, api_secret)
    headers['Content-Type'] = 'application/json'
    
    # Prepare update payload with new order number
    update_payload = {
        'orderId': order_data['orderId'],
        'orderNumber': new_order_number,  # NEW ORDER NUMBER
        'orderKey': order_data['orderKey'],
        'orderDate': order_data['orderDate'],
        'orderStatus': order_data['orderStatus'],
        'customerUsername': order_data.get('customerUsername'),
        'customerEmail': order_data.get('customerEmail'),
        'billTo': order_data['billTo'],
        'shipTo': order_data['shipTo'],
        'items': order_data['items'],
        'amountPaid': order_data.get('amountPaid', 0),
        'taxAmount': order_data.get('taxAmount', 0),
        'shippingAmount': order_data.get('shippingAmount', 0),
        'customerNotes': order_data.get('customerNotes', ''),
        'internalNotes': order_data.get('internalNotes', ''),
        'paymentMethod': order_data.get('paymentMethod'),
        'requestedShippingService': order_data.get('requestedShippingService'),
        'carrierCode': order_data.get('carrierCode'),
        'serviceCode': order_data.get('serviceCode'),
        'packageCode': order_data.get('packageCode'),
        'confirmation': order_data.get('confirmation'),
        'shipDate': order_data.get('shipDate'),
        'weight': order_data.get('weight'),
        'dimensions': order_data.get('dimensions'),
        'insuranceOptions': order_data.get('insuranceOptions'),
        'internationalOptions': order_data.get('internationalOptions'),
        'advancedOptions': order_data.get('advancedOptions')
    }
    
    print(f"\n🔄 Updating order number from {order_data['orderNumber']} to {new_order_number}...")
    
    # Send update to ShipStation
    url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/createorder"
    
    response = make_api_request(
        url=url,
        method='POST',
        data=update_payload,
        headers=headers,
        timeout=30
    )
    
    if response and response.status_code == 200:
        result = response.json()
        print(f"✅ Successfully updated order number to {result.get('orderNumber')}")
        print(f"   Order ID: {result.get('orderId')}")
        print(f"   Status: {result.get('orderStatus')}")
        return True
    else:
        # FIX: Proper error handling without assuming JSON response
        try:
            error_data = response.json() if response else None
            error_msg = error_data.get('message', str(error_data)) if error_data else 'No response'
        except (ValueError, AttributeError):
            error_msg = response.text if response else 'No response'
        
        print(f"❌ Failed to update order: {error_msg}")
        return False


def update_local_database(old_order_number, new_order_number, shipstation_order_id):
    """
    Update the order number in the local database
    
    Args:
        old_order_number: Original order number
        new_order_number: New order number
        shipstation_order_id: ShipStation order ID to match (as integer or string)
        
    Returns:
        bool: True if successful, False otherwise
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect('ora.db')
        cursor = conn.cursor()
        
        print(f"\n💾 Updating local database...")
        
        # FIX: Try both integer and string formats for shipstation_order_id
        # First attempt: match as-is (no string coercion)
        cursor.execute("""
            UPDATE orders_inbox
            SET order_number = ?
            WHERE order_number = ?
            AND shipstation_order_id = ?
        """, (new_order_number, old_order_number, shipstation_order_id))
        
        updated_inbox = cursor.rowcount
        
        # If no match, try string conversion
        if updated_inbox == 0:
            cursor.execute("""
                UPDATE orders_inbox
                SET order_number = ?
                WHERE order_number = ?
                AND shipstation_order_id = ?
            """, (new_order_number, old_order_number, str(shipstation_order_id)))
            
            updated_inbox = cursor.rowcount
        
        # Update shipped_orders (in case it exists there too)
        cursor.execute("""
            UPDATE shipped_orders
            SET order_number = ?
            WHERE order_number = ?
            AND shipstation_order_id = ?
        """, (new_order_number, old_order_number, shipstation_order_id))
        
        updated_shipped = cursor.rowcount
        
        # If no match, try string conversion
        if updated_shipped == 0:
            cursor.execute("""
                UPDATE shipped_orders
                SET order_number = ?
                WHERE order_number = ?
                AND shipstation_order_id = ?
            """, (new_order_number, old_order_number, str(shipstation_order_id)))
            
            updated_shipped = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # FIX: Detect zero-row updates and warn user
        if updated_inbox == 0 and updated_shipped == 0:
            print(f"⚠️  WARNING: Local database not updated (0 records found)")
            print(f"   This order may not exist locally yet, or has already been updated.")
            print(f"   ShipStation update was successful, but local DB is not in sync.")
            return False
        
        print(f"✅ Updated local database:")
        print(f"   - orders_inbox: {updated_inbox} record(s)")
        print(f"   - shipped_orders: {updated_shipped} record(s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating local database: {e}")
        return False


def main():
    """Main execution function"""
    
    # Parse command-line arguments
    if len(sys.argv) < 3:
        print("❌ Usage: python utils/change_order_number.py <shipstation_order_id> <new_order_number>")
        print("\nExample:")
        print("  python utils/change_order_number.py 224419681 100526")
        return 1
    
    try:
        SHIPSTATION_ORDER_ID = int(sys.argv[1])
        NEW_ORDER_NUMBER = sys.argv[2]
    except ValueError:
        print("❌ Error: ShipStation order ID must be a number")
        return 1
    
    print("=" * 80)
    print("ShipStation Order Number Change Utility")
    print("=" * 80)
    print(f"Target Order ID: {SHIPSTATION_ORDER_ID}")
    print(f"New Order Number: {NEW_ORDER_NUMBER}")
    print("=" * 80)
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        print("❌ Failed to retrieve ShipStation credentials")
        return 1
    
    # Step 1: Fetch the order by ID
    order_data = fetch_order_by_id(api_key, api_secret, SHIPSTATION_ORDER_ID)
    if not order_data:
        return 1
    
    old_order_number = order_data.get('orderNumber')
    
    # Step 2: Confirm with user
    print("\n" + "=" * 80)
    print("⚠️  CONFIRMATION REQUIRED")
    print("=" * 80)
    print(f"This will change order number from {old_order_number} to {NEW_ORDER_NUMBER}")
    print(f"Order Details:")
    print(f"  - ShipStation ID: {order_data.get('orderId')}")
    print(f"  - Status: {order_data.get('orderStatus')}")
    print(f"  - Customer: {order_data.get('billTo', {}).get('name')}")
    print(f"  - Company: {order_data.get('shipTo', {}).get('company')}")
    print(f"  - Items: {len(order_data.get('items', []))}")
    
    items = order_data.get('items', [])
    for item in items:
        print(f"    • {item.get('sku')} x{item.get('quantity')}")
    
    response = input("\nProceed with order number change? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled by user")
        return 0
    
    # Step 3: Update in ShipStation
    if not update_order_number(api_key, api_secret, order_data, NEW_ORDER_NUMBER):
        print("\n❌ ShipStation update failed. Aborting.")
        return 1
    
    # Step 4: Update local database
    local_success = update_local_database(old_order_number, NEW_ORDER_NUMBER, SHIPSTATION_ORDER_ID)
    
    print("\n" + "=" * 80)
    if local_success:
        print("✅ Order number change complete!")
    else:
        print("⚠️  Order number changed in ShipStation, but local database sync issue detected")
    print("=" * 80)
    print(f"Order {old_order_number} is now {NEW_ORDER_NUMBER} in ShipStation")
    
    if not local_success:
        print("\n⚠️  Local database was not updated. You may need to:")
        print("   1. Wait for the next status sync to pick up the change")
        print("   2. Manually update the order in the database")
        print("   3. Check if the order exists in orders_inbox or shipped_orders")
    else:
        print("\nNext steps:")
        print("  1. Verify the change in ShipStation dashboard")
        print("  2. Refresh your Orders Inbox page to see the updated order number")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

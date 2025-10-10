#!/usr/bin/env python3
"""
Backfill Script: Fix Corrupted Ship Dates
==========================================

Problem: The manual sync and daily processor were overwriting ship_date with today's date
every time they ran. This caused ~452 old orders (581xxx range) to show ship_date=2025-10-10
instead of their original ship dates.

Solution: Query ShipStation API to get the correct shipDate for each affected order
and update both shipped_orders and shipped_items tables.

Usage: python utils/backfill_ship_dates.py
"""

import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.db_utils import get_connection, transaction
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
import requests

def get_corrupted_orders(conn, target_date='2025-10-10'):
    """Get list of orders with corrupted ship_date"""
    cursor = conn.execute("""
        SELECT order_number, shipstation_order_id
        FROM shipped_orders
        WHERE ship_date = ?
        ORDER BY order_number
    """, (target_date,))
    
    return cursor.fetchall()

def fetch_correct_ship_date_from_shipstation(api_key, api_secret, order_number):
    """Fetch the correct shipDate from ShipStation API for a given order number"""
    headers = get_shipstation_headers(api_key, api_secret)
    
    try:
        # Query by order number
        response = requests.get(
            f'https://ssapi.shipstation.com/orders?orderNumber={order_number}',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            
            if orders:
                # Get first order (should only be one)
                order = orders[0]
                ship_date_str = order.get('shipDate')
                
                if ship_date_str:
                    # Parse shipDate (format: "2025-10-06T00:00:00.0000000")
                    ship_date = ship_date_str[:10]  # Extract YYYY-MM-DD
                    return ship_date
        
        return None
        
    except Exception as e:
        print(f"  ❌ Error fetching order {order_number}: {e}")
        return None

def update_ship_dates(conn, order_number, correct_ship_date):
    """Update ship_date in both shipped_orders and shipped_items"""
    # Update shipped_orders
    conn.execute("""
        UPDATE shipped_orders
        SET ship_date = ?
        WHERE order_number = ?
    """, (correct_ship_date, order_number))
    
    # Update shipped_items
    conn.execute("""
        UPDATE shipped_items
        SET ship_date = ?
        WHERE order_number = ?
    """, (correct_ship_date, order_number))

def main():
    print("="*100)
    print("SHIP DATE BACKFILL SCRIPT")
    print("="*100)
    print("\nThis script will:")
    print("1. Find all orders with corrupted ship_date (2025-10-10)")
    print("2. Query ShipStation API to get correct ship dates")
    print("3. Update both shipped_orders and shipped_items tables")
    print()
    
    # Get API credentials
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            print("❌ ERROR: ShipStation credentials not found")
            return 1
    except Exception as e:
        print(f"❌ ERROR: Could not get ShipStation credentials: {e}")
        return 1
    
    # Get database connection
    conn = get_connection()
    
    # Find corrupted orders
    print("📊 Finding corrupted orders...")
    corrupted_orders = get_corrupted_orders(conn)
    
    if not corrupted_orders:
        print("✅ No corrupted orders found! All ship dates are correct.")
        conn.close()
        return 0
    
    print(f"⚠️  Found {len(corrupted_orders)} orders with incorrect ship_date")
    print()
    
    # Ask for confirmation
    confirm = input(f"Proceed with backfill for {len(corrupted_orders)} orders? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Aborted by user")
        conn.close()
        return 1
    
    print()
    print("="*100)
    print("STARTING BACKFILL")
    print("="*100)
    
    # Process each order
    success_count = 0
    error_count = 0
    
    for i, (order_number, ss_order_id) in enumerate(corrupted_orders, 1):
        print(f"\n[{i}/{len(corrupted_orders)}] Processing order {order_number}...", end=" ")
        
        # Fetch correct ship date from ShipStation
        correct_ship_date = fetch_correct_ship_date_from_shipstation(api_key, api_secret, order_number)
        
        if correct_ship_date:
            # Update database
            try:
                with transaction() as tx_conn:
                    update_ship_dates(tx_conn, order_number, correct_ship_date)
                print(f"✅ Updated to {correct_ship_date}")
                success_count += 1
            except Exception as e:
                print(f"❌ Database error: {e}")
                error_count += 1
        else:
            print(f"⚠️  Could not fetch ship date from ShipStation")
            error_count += 1
        
        # Show progress every 50 orders
        if i % 50 == 0:
            print(f"\n   Progress: {success_count} success, {error_count} errors")
    
    conn.close()
    
    # Summary
    print()
    print("="*100)
    print("BACKFILL COMPLETE")
    print("="*100)
    print(f"✅ Successfully updated: {success_count} orders")
    print(f"❌ Errors: {error_count} orders")
    print()
    
    if success_count > 0:
        print("🎉 Ship dates have been restored! The Order Audit should now show correct results.")
    
    return 0 if error_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())

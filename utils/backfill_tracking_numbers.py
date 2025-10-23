#!/usr/bin/env python3
"""
Backfill tracking numbers for all shipped orders in orders_inbox.

This script fetches tracking numbers from ShipStation for all orders
with status='shipped' that are missing tracking numbers in the database.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.database.db_adapter import get_connection
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

def fetch_all_recent_shipments(api_key: str, api_secret: str, days_back: int = 90) -> dict:
    """
    Fetch all shipments from last N days and organize by order number.
    
    Returns:
        Dict mapping order_number -> list of tracking numbers
    """
    headers = get_shipstation_headers(api_key, api_secret)
    shipments_endpoint = "https://ssapi.shipstation.com/shipments"
    
    # Query for shipments from last N days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    params = {
        'createDateStart': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
        'createDateEnd': end_date.strftime('%Y-%m-%dT%H:%M:%S'),
        'pageSize': 500
    }
    
    print(f"\n📅 Fetching shipments from {start_date.date()} to {end_date.date()} ({days_back} days)")
    print(f"   Query: {params['createDateStart']} to {params['createDateEnd']}")
    
    all_shipments = []
    page = 1
    
    while True:
        params['page'] = page
        print(f"   📄 Fetching page {page}...", end=' ')
        
        response = make_api_request(
            url=shipments_endpoint,
            method='GET',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if not response or response.status_code != 200:
            print(f"❌ Failed (status: {response.status_code if response else 'None'})")
            break
        
        data = response.json()
        shipments = data.get('shipments', [])
        
        if not shipments:
            print("✅ Done (no more pages)")
            break
        
        all_shipments.extend(shipments)
        print(f"✅ {len(shipments)} shipments")
        
        # Check if there are more pages
        total_pages = data.get('pages', 1)
        if page >= total_pages:
            break
        
        page += 1
    
    print(f"\n✅ Retrieved {len(all_shipments)} total shipments")
    
    # Organize by order number
    tracking_by_order = {}
    for shipment in all_shipments:
        order_num = shipment.get('orderNumber')
        tracking_num = shipment.get('trackingNumber')
        
        if order_num and tracking_num:
            if order_num not in tracking_by_order:
                tracking_by_order[order_num] = []
            tracking_by_order[order_num].append(tracking_num)
    
    print(f"📊 Found tracking numbers for {len(tracking_by_order)} unique orders")
    
    return tracking_by_order


def backfill_tracking_numbers(dry_run: bool = True):
    """
    Backfill tracking numbers for shipped orders missing them.
    
    Args:
        dry_run: If True, only show what would be updated without making changes
    """
    print("=" * 80)
    print("🔄 TRACKING NUMBER BACKFILL SCRIPT")
    print("=" * 80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    else:
        print("⚠️  LIVE MODE - Database will be updated")
    
    # Get ShipStation credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        print("❌ ShipStation credentials not found")
        return
    
    # Fetch all recent shipments from ShipStation
    tracking_by_order = fetch_all_recent_shipments(api_key, api_secret, days_back=90)
    
    # Connect to database
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Find shipped orders without tracking numbers
        cursor.execute("""
            SELECT order_number, status, updated_at
            FROM orders_inbox
            WHERE status = 'shipped'
              AND (tracking_number IS NULL OR tracking_number = '')
            ORDER BY order_number
        """)
        
        orders_needing_tracking = cursor.fetchall()
        print(f"\n📋 Found {len(orders_needing_tracking)} shipped orders without tracking numbers")
        
        if not orders_needing_tracking:
            print("✅ All shipped orders already have tracking numbers!")
            return
        
        # Match and update
        updates_made = 0
        not_found = 0
        
        print("\n🔄 Processing updates:")
        print("-" * 80)
        
        for row in orders_needing_tracking:
            order_number = row[0]
            
            if order_number in tracking_by_order:
                tracking_numbers = tracking_by_order[order_number]
                # Join multiple tracking numbers with comma
                tracking_str = ', '.join(tracking_numbers)
                
                print(f"✅ Order {order_number}: {tracking_str}")
                
                if not dry_run:
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET tracking_number = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE order_number = %s
                    """, (tracking_str, order_number))
                
                updates_made += 1
            else:
                print(f"⚠️  Order {order_number}: No shipment found in ShipStation")
                not_found += 1
        
        if not dry_run:
            conn.commit()
            print("\n✅ Database changes committed")
        else:
            print("\n🔍 DRY RUN - No changes made to database")
        
        print("\n" + "=" * 80)
        print("📊 BACKFILL SUMMARY:")
        print(f"   ✅ Tracking numbers found: {updates_made}")
        print(f"   ⚠️  Not found in ShipStation: {not_found}")
        print(f"   📝 Total shipped orders processed: {len(orders_needing_tracking)}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during backfill: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill tracking numbers for shipped orders')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute the backfill (default is dry-run)')
    
    args = parser.parse_args()
    
    backfill_tracking_numbers(dry_run=not args.execute)
    
    if not args.execute:
        print("\n💡 To execute this backfill, run: python utils/backfill_tracking_numbers.py --execute")

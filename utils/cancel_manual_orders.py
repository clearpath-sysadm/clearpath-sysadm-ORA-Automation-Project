#!/usr/bin/env python3
"""
Utility to cancel specific manual orders from ShipStation
Used for remediation of incorrectly numbered manual orders

Usage:
    python utils/cancel_manual_orders.py --order-ids 223387873,223387885,223387942,223770760
"""
import os
import sys
from pathlib import Path
import argparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from config.settings import settings
from utils.api_utils import make_api_request
from src.services.database.pg_utils import execute_query, transaction


def delete_shipstation_order(api_key, api_secret, order_id):
    """
    Delete an order from ShipStation by order ID
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        order_id: ShipStation order ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    headers = get_shipstation_headers(api_key, api_secret)
    
    # DELETE order by ID
    url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
    
    print(f"🗑️  Deleting order ID {order_id}...")
    
    response = make_api_request(
        url=url,
        method='DELETE',
        headers=headers,
        timeout=30
    )
    
    if response and response.status_code == 200:
        print(f"✅ Successfully deleted order ID {order_id}")
        return True
    else:
        status = response.status_code if response else 'No response'
        print(f"❌ Failed to delete order {order_id}: HTTP {status}")
        if response and response.text:
            print(f"   Error: {response.text}")
        return False


def update_local_database(order_id):
    """
    Update local database to mark order as cancelled
    
    Args:
        order_id: ShipStation order ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Update orders_inbox
            cursor.execute("""
                UPDATE orders_inbox
                SET status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE shipstation_order_id = %s
            """, (str(order_id),))
            
            updated = cursor.rowcount
            
            if updated > 0:
                print(f"✅ Updated local database: {updated} record(s) marked as cancelled")
                return True
            else:
                print(f"⚠️  No local records found for order ID {order_id}")
                return False
                
    except Exception as e:
        print(f"❌ Error updating local database: {e}")
        return False


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Cancel manual orders in ShipStation')
    parser.add_argument('--order-ids', required=True, 
                       help='Comma-separated list of ShipStation order IDs to cancel')
    parser.add_argument('--skip-local-update', action='store_true',
                       help='Skip updating local database (ShipStation only)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    # Parse order IDs
    order_ids = [int(oid.strip()) for oid in args.order_ids.split(',')]
    
    print("=" * 80)
    print("Manual Orders Cancellation Utility")
    print("=" * 80)
    print(f"Orders to cancel: {len(order_ids)}")
    for oid in order_ids:
        print(f"  - {oid}")
    print("=" * 80)
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        print("❌ Failed to retrieve ShipStation credentials")
        return 1
    
    # Confirm with user (unless dry-run)
    if not args.dry_run:
        print("\n⚠️  WARNING: This will DELETE these orders from ShipStation!")
        response = input("Proceed with cancellation? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Operation cancelled by user")
            return 0
    
    # Process each order
    success_count = 0
    failed_count = 0
    
    for order_id in order_ids:
        print(f"\n--- Processing Order ID {order_id} ---")
        
        if args.dry_run:
            print(f"[DRY RUN] Would delete order {order_id}")
            success_count += 1
        else:
            # Delete from ShipStation
            if delete_shipstation_order(api_key, api_secret, order_id):
                success_count += 1
                
                # Update local database
                if not args.skip_local_update:
                    update_local_database(order_id)
            else:
                failed_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{len(order_ids)}")
    print(f"❌ Failed: {failed_count}/{len(order_ids)}")
    print("=" * 80)
    
    if args.dry_run:
        print("\nThis was a DRY RUN. Run without --dry-run to execute.")
    
    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
One-time script to update historical lot numbers in ShipStation.
Changes: 17612 - 250237 → 17612 - 250300 (for awaiting_shipment orders only)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request
import logging
from datetime import datetime
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"

OLD_LOT = "17612 - 250237"
NEW_LOT = "17612 - 250300"
TARGET_STATUS = "awaiting_shipment"

def get_awaiting_shipment_orders():
    """Fetch all awaiting_shipment orders from ShipStation"""
    api_key, api_secret = get_shipstation_credentials()
    headers = get_shipstation_headers(api_key, api_secret)
    
    logger.info(f"🔍 Fetching {TARGET_STATUS} orders from ShipStation...")
    
    orders = []
    page = 1
    
    while True:
        params = {
            'orderStatus': TARGET_STATUS,
            'pageSize': 500,
            'page': page
        }
        
        response = make_api_request(
            method='GET',
            url=f"{SHIPSTATION_BASE_URL}/orders",
            headers=headers,
            params=params
        )
        
        if not response or 'orders' not in response:
            break
            
        page_orders = response['orders']
        orders.extend(page_orders)
        
        logger.info(f"   📄 Page {page}: {len(page_orders)} orders")
        
        if len(page_orders) < 500:
            break
            
        page += 1
    
    logger.info(f"✅ Retrieved {len(orders)} total {TARGET_STATUS} orders")
    return orders

def find_orders_with_old_lot(orders):
    """Filter orders that contain the old lot number"""
    matching_orders = []
    
    for order in orders:
        order_id = order.get('orderId')
        order_number = order.get('orderNumber')
        items = order.get('items', [])
        
        # Check if any item has the old lot number
        has_old_lot = False
        for item in items:
            sku = item.get('sku', '')
            if sku == OLD_LOT:
                has_old_lot = True
                break
        
        if has_old_lot:
            matching_orders.append({
                'orderId': order_id,
                'orderNumber': order_number,
                'orderStatus': order.get('orderStatus'),
                'items': items
            })
    
    return matching_orders

def update_order_lot(headers, order_info, dry_run=True):
    """Update a single order's lot number"""
    order_id = order_info['orderId']
    order_number = order_info['orderNumber']
    items = order_info['items']
    
    # Create updated items list
    updated_items = []
    changes_made = 0
    
    for item in items:
        sku = item.get('sku', '')
        
        if sku == OLD_LOT:
            # Update the SKU
            updated_item = item.copy()
            updated_item['sku'] = NEW_LOT
            updated_items.append(updated_item)
            changes_made += 1
            logger.info(f"   🔄 Item: {sku} → {NEW_LOT} (qty: {item.get('quantity')})")
        else:
            # Keep unchanged
            updated_items.append(item)
    
    if changes_made == 0:
        return False
    
    # Prepare update payload
    update_payload = {
        'orderId': order_id,
        'items': updated_items
    }
    
    if dry_run:
        logger.info(f"   [DRY RUN] Would update order {order_number} ({changes_made} items)")
        return True
    else:
        # Actually update the order
        try:
            response = make_api_request(
                method='POST',
                url=f"{SHIPSTATION_BASE_URL}/orders/createorder",
                headers=headers,
                data=update_payload
            )
            logger.info(f"   ✅ Updated order {order_number} ({changes_made} items)")
            return True
        except Exception as e:
            logger.error(f"   ❌ Failed to update order {order_number}: {e}")
            return False

def main(dry_run=True):
    """Main execution"""
    logger.info("=" * 80)
    logger.info("🚀 SHIPSTATION LOT NUMBER FIX - STARTING")
    logger.info(f"   Target: {OLD_LOT} → {NEW_LOT}")
    logger.info(f"   Status Filter: {TARGET_STATUS}")
    logger.info(f"   Mode: {'DRY RUN (preview only)' if dry_run else 'EXECUTE (will modify ShipStation)'}")
    logger.info("=" * 80)
    
    # Step 1: Get all awaiting_shipment orders
    orders = get_awaiting_shipment_orders()
    
    # Step 2: Filter to orders with old lot
    matching_orders = find_orders_with_old_lot(orders)
    logger.info(f"\n📦 Found {len(matching_orders)} orders with lot {OLD_LOT}")
    
    if not matching_orders:
        logger.info("✅ No orders need updating")
        return
    
    # Step 3: Show what will be updated
    logger.info(f"\n{'='*80}")
    logger.info("📋 ORDERS TO UPDATE:")
    logger.info(f"{'='*80}")
    
    for i, order_info in enumerate(matching_orders, 1):
        logger.info(f"\n{i}. Order: {order_info['orderNumber']} (ID: {order_info['orderId']})")
        logger.info(f"   Status: {order_info['orderStatus']}")
        
        old_lot_items = [item for item in order_info['items'] if item.get('sku') == OLD_LOT]
        for item in old_lot_items:
            logger.info(f"   - SKU: {item.get('sku')} | Qty: {item.get('quantity')} | Name: {item.get('name')}")
    
    # Step 4: Update orders
    api_key, api_secret = get_shipstation_credentials()
    headers = get_shipstation_headers(api_key, api_secret)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"{'📝 DRY RUN - PREVIEW CHANGES' if dry_run else '🔧 EXECUTING UPDATES'}")
    logger.info(f"{'='*80}\n")
    
    updated_count = 0
    for order_info in matching_orders:
        logger.info(f"Order {order_info['orderNumber']}:")
        if update_order_lot(headers, order_info, dry_run=dry_run):
            updated_count += 1
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("📊 SUMMARY:")
    logger.info(f"   Total {TARGET_STATUS} orders: {len(orders)}")
    logger.info(f"   Orders with {OLD_LOT}: {len(matching_orders)}")
    logger.info(f"   {'Would update' if dry_run else 'Updated'}: {updated_count}")
    logger.info(f"{'='*80}")
    
    if dry_run:
        logger.info("\n⚠️  This was a DRY RUN - no changes were made to ShipStation")
        logger.info("   To execute the updates, run: python utils/fix_historical_lot_numbers.py --execute")
    else:
        logger.info("\n✅ Updates completed successfully")

if __name__ == "__main__":
    # Check for --execute flag
    execute_mode = '--execute' in sys.argv
    main(dry_run=not execute_mode)

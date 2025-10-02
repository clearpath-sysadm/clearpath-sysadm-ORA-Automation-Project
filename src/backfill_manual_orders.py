#!/usr/bin/env python3
"""
Manual Orders Backfill Script

One-time script to backfill manual ShipStation orders from a specific date.
Use this to import historical manual orders that were created before the sync started.
"""

import sys
import os
import logging
import datetime
from typing import List, Dict, Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.manual_shipstation_sync import (
    get_shipstation_credentials,
    fetch_shipstation_orders_since_watermark,
    is_order_from_local_system,
    has_key_product_skus,
    import_manual_order
)
from utils.logging_config import setup_logging

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'manual_backfill.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def backfill_manual_orders(start_date: str = '2025-09-19'):
    """
    Backfill manual orders from ShipStation starting from a specific date.
    
    Args:
        start_date: Date string in format 'YYYY-MM-DD'
    """
    logger.info("=== Starting Manual Orders Backfill ===")
    logger.info(f"Fetching orders from {start_date} onward...")
    
    # Get ShipStation credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.critical("Failed to get ShipStation credentials")
        return
    
    # Convert date to ISO format
    start_datetime = f"{start_date}T00:00:00Z"
    
    # Fetch all orders since start date
    logger.info(f"Querying ShipStation for orders modified since {start_datetime}")
    orders = fetch_shipstation_orders_since_watermark(api_key, api_secret, start_datetime)
    
    if not orders:
        logger.warning("No orders found in ShipStation for the specified date range")
        return
    
    logger.info(f"Retrieved {len(orders)} total orders from ShipStation")
    
    # Filter to manual orders with key products
    manual_orders = []
    for order in orders:
        order_id = order.get('orderId') or order.get('orderKey')
        order_number = order.get('orderNumber', 'UNKNOWN')
        
        # Skip if order came from our local system
        if is_order_from_local_system(str(order_id)):
            logger.debug(f"Skipping order {order_number} - originated from local system")
            continue
        
        # Skip if order doesn't contain key product SKUs
        if not has_key_product_skus(order):
            logger.debug(f"Skipping order {order_number} - no Key Products")
            continue
        
        manual_orders.append(order)
        logger.info(f"Found manual order: {order_number} (ShipStation ID: {order_id})")
    
    if not manual_orders:
        logger.info("No manual orders with Key Products found")
        return
    
    logger.info(f"Found {len(manual_orders)} manual orders to import")
    
    # Import manual orders
    imported = 0
    failed = 0
    
    for order in manual_orders:
        order_number = order.get('orderNumber', 'UNKNOWN')
        try:
            if import_manual_order(order):
                imported += 1
                logger.info(f"✅ Successfully imported order {order_number}")
            else:
                failed += 1
                logger.warning(f"❌ Failed to import order {order_number}")
        except Exception as e:
            failed += 1
            logger.error(f"❌ Error importing order {order_number}: {e}", exc_info=True)
    
    logger.info("=== Backfill Complete ===")
    logger.info(f"Imported: {imported}, Failed: {failed}, Total: {len(manual_orders)}")
    
    print("\n" + "="*60)
    print("BACKFILL RESULTS")
    print("="*60)
    print(f"✅ Orders imported: {imported}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total processed: {len(manual_orders)}")
    print("="*60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill manual ShipStation orders')
    parser.add_argument(
        '--start-date',
        default='2025-09-19',
        help='Start date in YYYY-MM-DD format (default: 2025-09-19)'
    )
    
    args = parser.parse_args()
    backfill_manual_orders(start_date=args.start_date)

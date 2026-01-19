#!/usr/bin/env python3
"""
ShipStation Backfill - Dry Run

Compares ShipStation shipped orders against local database to identify
orders that are missing. Does NOT make any changes.

Usage:
    python src/shipstation_backfill_dry_run.py --start-date 2026-01-01 --end-date 2026-01-19
    python src/shipstation_backfill_dry_run.py --days 7  # Last 7 days
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import SHIPSTATION_SHIPMENTS_ENDPOINT
from src.services.database import execute_query
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    fetch_shipstation_shipments
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']


def get_local_shipped_orders(start_date: str, end_date: str) -> set:
    """Get order numbers from shipped_orders within date range"""
    rows = execute_query("""
        SELECT DISTINCT order_number 
        FROM shipped_orders 
        WHERE ship_date >= %s AND ship_date <= %s
    """, (start_date, end_date))
    return {row[0] for row in rows} if rows else set()


def get_local_inbox_orders(start_date: str, end_date: str) -> set:
    """Get order numbers from orders_inbox within date range"""
    rows = execute_query("""
        SELECT DISTINCT order_number 
        FROM orders_inbox 
        WHERE order_date >= %s AND order_date <= %s
    """, (start_date, end_date))
    return {row[0] for row in rows} if rows else set()


def extract_order_number(shipstation_order: Dict) -> str:
    """Extract the order number from ShipStation order data"""
    return shipstation_order.get('orderNumber', '')


def has_key_products(items: List[Dict]) -> bool:
    """Check if any items contain key product SKUs"""
    for item in items:
        sku = item.get('sku', '')
        if any(key_sku in sku for key_sku in KEY_PRODUCT_SKUS):
            return True
    return False


def fetch_all_shipments(api_key: str, api_secret: str, start_date: str, end_date: str) -> List[Dict]:
    """Fetch all shipments from ShipStation for date range"""
    logger.info(f"Fetching shipments from {start_date} to {end_date}...")
    
    shipments = fetch_shipstation_shipments(
        api_key=api_key,
        api_secret=api_secret,
        shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,
        start_date=start_date,
        end_date=end_date,
        shipment_status="shipped"
    )
    
    logger.info(f"Fetched {len(shipments)} total shipments from ShipStation")
    return shipments


def analyze_gap(
    shipments: List[Dict],
    local_shipped: set,
    local_inbox: set
) -> Dict[str, Any]:
    """
    Analyze what's missing between ShipStation and local DB
    
    Returns dict with:
    - missing_from_shipped: Orders in ShipStation but not in shipped_orders
    - missing_from_inbox: Orders in ShipStation but not in orders_inbox
    - details: Per-order details for missing orders
    """
    
    missing_from_shipped = []
    missing_from_inbox = []
    in_inbox_not_shipped = []
    already_synced = []
    no_key_products = []
    
    seen_orders = set()
    
    for shipment in shipments:
        order_number = extract_order_number(shipment)
        
        if not order_number or order_number in seen_orders:
            continue
        seen_orders.add(order_number)
        
        items = shipment.get('shipmentItems', [])
        ship_date = shipment.get('shipDate', '')[:10] if shipment.get('shipDate') else ''
        
        has_key = has_key_products(items)
        
        order_info = {
            'order_number': order_number,
            'ship_date': ship_date,
            'item_count': len(items),
            'has_key_products': has_key,
            'items': [{'sku': i.get('sku', ''), 'qty': i.get('quantity', 0)} for i in items]
        }
        
        if not has_key:
            no_key_products.append(order_info)
            continue
        
        in_shipped = order_number in local_shipped
        in_inbox = order_number in local_inbox
        
        if in_shipped:
            already_synced.append(order_info)
        elif in_inbox:
            in_inbox_not_shipped.append(order_info)
            missing_from_shipped.append(order_info)
        else:
            missing_from_inbox.append(order_info)
            missing_from_shipped.append(order_info)
    
    return {
        'shipstation_total': len(seen_orders),
        'no_key_products': len(no_key_products),
        'already_synced': len(already_synced),
        'in_inbox_not_shipped': len(in_inbox_not_shipped),
        'missing_from_inbox': len(missing_from_inbox),
        'missing_from_shipped': len(missing_from_shipped),
        'details': {
            'missing_from_inbox': missing_from_inbox,
            'in_inbox_not_shipped': in_inbox_not_shipped,
            'no_key_products_orders': no_key_products[:10]
        }
    }


def print_report(results: Dict[str, Any], start_date: str, end_date: str):
    """Print a formatted dry run report"""
    
    print("\n" + "="*70)
    print("SHIPSTATION BACKFILL - DRY RUN REPORT")
    print("="*70)
    print(f"Date Range: {start_date} to {end_date}")
    print("-"*70)
    
    print(f"\n📦 ShipStation Orders (unique):    {results['shipstation_total']}")
    print(f"   └─ Without Key Products:        {results['no_key_products']} (skipped)")
    print(f"   └─ Already Synced:              {results['already_synced']} ✓")
    print(f"   └─ In Inbox, Not Shipped:       {results['in_inbox_not_shipped']}")
    print(f"   └─ Missing from Inbox:          {results['missing_from_inbox']}")
    
    print(f"\n📊 SYNC NEEDED:")
    print(f"   Orders missing from shipped_orders: {results['missing_from_shipped']}")
    
    if results['details']['missing_from_inbox']:
        print(f"\n🔴 ORDERS MISSING FROM orders_inbox (need backfill):")
        for order in results['details']['missing_from_inbox'][:20]:
            items_str = ', '.join([f"{i['sku']}x{i['qty']}" for i in order['items'][:3]])
            print(f"   - {order['order_number']} (shipped {order['ship_date']}) - {items_str}")
        if len(results['details']['missing_from_inbox']) > 20:
            print(f"   ... and {len(results['details']['missing_from_inbox']) - 20} more")
    
    if results['details']['in_inbox_not_shipped']:
        print(f"\n🟡 ORDERS IN INBOX BUT NOT SHIPPED (need status update):")
        for order in results['details']['in_inbox_not_shipped'][:10]:
            print(f"   - {order['order_number']} (shipped {order['ship_date']})")
        if len(results['details']['in_inbox_not_shipped']) > 10:
            print(f"   ... and {len(results['details']['in_inbox_not_shipped']) - 10} more")
    
    print("\n" + "="*70)
    
    if results['missing_from_shipped'] == 0:
        print("✅ LOCAL DATABASE IS IN SYNC WITH SHIPSTATION")
    else:
        print(f"⚠️  RUN SYNC SCRIPT TO BACKFILL {results['missing_from_shipped']} ORDERS")
    
    print("="*70 + "\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='ShipStation Backfill Dry Run')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, help='Number of days to look back (alternative to date range)')
    
    args = parser.parse_args()
    
    if args.days:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        print("Error: Provide either --days or both --start-date and --end-date")
        sys.exit(1)
    
    logger.info(f"Starting dry run for {start_date} to {end_date}")
    
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("Failed to get ShipStation credentials")
        sys.exit(1)
    
    local_shipped = get_local_shipped_orders(start_date, end_date)
    logger.info(f"Found {len(local_shipped)} orders in local shipped_orders")
    
    local_inbox = get_local_inbox_orders(start_date, end_date)
    logger.info(f"Found {len(local_inbox)} orders in local orders_inbox")
    
    shipments = fetch_all_shipments(api_key, api_secret, start_date, end_date)
    
    results = analyze_gap(shipments, local_shipped, local_inbox)
    
    print_report(results, start_date, end_date)
    
    return results


if __name__ == '__main__':
    main()

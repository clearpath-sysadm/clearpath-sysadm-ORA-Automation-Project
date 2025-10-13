#!/usr/bin/env python3
"""
ShipStation Duplicate Identifier
Scans ShipStation for duplicate order+SKU combinations and generates reports

Usage:
    python utils/identify_shipstation_duplicates.py --mode report
    python utils/identify_shipstation_duplicates.py --mode summary
"""

import os
import sys
import csv
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from config.settings import settings
from utils.api_utils import make_api_request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_all_shipstation_orders(api_key, api_secret, days_back=180):
    """
    Fetch all orders from ShipStation for the specified date range
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        days_back: Number of days to look back (default 180 = ~6 months)
        
    Returns:
        List of order dictionaries from ShipStation
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    logger.info(f"Fetching ShipStation orders from {start_date.date()} to {end_date.date()}")
    
    all_orders = []
    page = 1
    total_pages = None
    
    while True:
        params = {
            'createDateStart': start_date.strftime('%Y-%m-%dT00:00:00Z'),
            'createDateEnd': end_date.strftime('%Y-%m-%dT23:59:59Z'),
            'page': page,
            'pageSize': 500
        }
        
        headers = get_shipstation_headers(api_key, api_secret)
        response = make_api_request(
            url=settings.SHIPSTATION_ORDERS_ENDPOINT,
            method='GET',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            all_orders.extend(orders)
            
            if total_pages is None:
                total_pages = data.get('pages', 1)
            
            logger.info(f"Fetched page {page}/{total_pages}, found {len(orders)} orders")
            
            if page >= total_pages:
                break
                
            page += 1
        else:
            logger.error(f"Failed to fetch orders (page {page}): {response.status_code}")
            break
    
    logger.info(f"Total orders fetched: {len(all_orders)}")
    return all_orders


def identify_duplicates(orders):
    """
    Identify duplicate order+SKU combinations
    
    Args:
        orders: List of ShipStation order dictionaries
        
    Returns:
        Dictionary of duplicates grouped by (order_number, base_sku)
    """
    # Build map of (order_number, base_sku) -> list of orders
    order_sku_map = defaultdict(list)
    
    for order in orders:
        order_number = order.get('orderNumber', '').strip().upper()
        order_id = order.get('orderId')
        order_key = order.get('orderKey')
        create_date = order.get('createDate')
        order_status = order.get('orderStatus')
        items = order.get('items', [])
        
        # Skip if no items (shouldn't happen but safety check)
        if not items:
            logger.warning(f"Order {order_number} has no items - skipping")
            continue
        
        # Extract base SKUs (first 5 characters)
        for item in items:
            sku = item.get('sku', '')
            if sku:
                base_sku = sku[:5]  # First 5 digits
                
                key = (order_number, base_sku)
                order_sku_map[key].append({
                    'order_number': order_number,
                    'base_sku': base_sku,
                    'full_sku': sku,
                    'shipstation_order_id': order_id or order_key,
                    'create_date': create_date,
                    'order_status': order_status,
                    'quantity': item.get('quantity', 0),
                    'item_name': item.get('name', '')
                })
    
    # Filter to only duplicates (count > 1)
    duplicates = {k: v for k, v in order_sku_map.items() if len(v) > 1}
    
    return duplicates


def generate_report(duplicates, output_dir='reports'):
    """
    Generate CSV report of duplicates
    
    Args:
        duplicates: Dictionary from identify_duplicates()
        output_dir: Directory to save report (default: reports/)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'shipstation_duplicates_{timestamp}.csv'
    
    with open(report_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Order Number',
            'Base SKU',
            'Full SKU',
            'ShipStation Order ID',
            'Create Date',
            'Order Status',
            'Quantity',
            'Item Name',
            'Duplicate Count',
            'Duplicate Group'
        ])
        
        for (order_num, base_sku), items in sorted(duplicates.items()):
            duplicate_count = len(items)
            group_id = f"{order_num}_{base_sku}"
            
            # Sort by create_date to show chronological order
            items_sorted = sorted(items, key=lambda x: x['create_date'] or '')
            
            for item in items_sorted:
                writer.writerow([
                    item['order_number'],
                    item['base_sku'],
                    item['full_sku'],
                    item['shipstation_order_id'],
                    item['create_date'],
                    item['order_status'],
                    item['quantity'],
                    item['item_name'],
                    duplicate_count,
                    group_id
                ])
    
    logger.info(f"Report saved to: {report_path}")
    return report_path


def print_summary(duplicates):
    """Print console summary of duplicates"""
    
    print("\n" + "="*80)
    print("SHIPSTATION DUPLICATE DETECTION SUMMARY")
    print("="*80 + "\n")
    
    if not duplicates:
        print("✅ NO DUPLICATES FOUND\n")
        return
    
    total_duplicate_combinations = len(duplicates)
    total_duplicate_orders = sum(len(items) for items in duplicates.values())
    
    print(f"❌ DUPLICATES FOUND")
    print(f"   Duplicate (Order+SKU) Combinations: {total_duplicate_combinations}")
    print(f"   Total Duplicate Orders: {total_duplicate_orders}")
    print(f"   Redundant Orders (to clean up): {total_duplicate_orders - total_duplicate_combinations}\n")
    
    print("TOP 10 DUPLICATE GROUPS:")
    print("-" * 80)
    
    # Sort by most duplicates first
    sorted_duplicates = sorted(
        duplicates.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]
    
    for (order_num, base_sku), items in sorted_duplicates:
        print(f"\nOrder: {order_num} | SKU: {base_sku} | Count: {len(items)}")
        
        # Show details of each duplicate
        items_sorted = sorted(items, key=lambda x: x['create_date'] or '')
        for idx, item in enumerate(items_sorted, 1):
            status_icon = "✓" if idx == 1 else "✗"
            print(f"  {status_icon} [{idx}] {item['full_sku']} | "
                  f"ID: {item['shipstation_order_id']} | "
                  f"Status: {item['order_status']} | "
                  f"Created: {item['create_date']}")
    
    print("\n" + "="*80 + "\n")
    
    # Group by status
    status_counts = defaultdict(int)
    for items in duplicates.values():
        for item in items:
            status_counts[item['order_status']] += 1
    
    print("DUPLICATES BY STATUS:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Identify duplicate orders in ShipStation'
    )
    parser.add_argument(
        '--mode',
        choices=['report', 'summary', 'both'],
        default='both',
        help='Output mode: report=CSV only, summary=console only, both=CSV+console'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=180,
        help='Number of days to look back (default: 180)'
    )
    
    args = parser.parse_args()
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("ShipStation credentials not found")
        return 1
    
    # Fetch all orders
    logger.info("Starting duplicate detection...")
    orders = fetch_all_shipstation_orders(api_key, api_secret, args.days_back)
    
    if not orders:
        logger.error("No orders found")
        return 1
    
    # Identify duplicates
    duplicates = identify_duplicates(orders)
    
    # Generate outputs based on mode
    if args.mode in ['report', 'both']:
        report_path = generate_report(duplicates)
        logger.info(f"Report generated: {report_path}")
    
    if args.mode in ['summary', 'both']:
        print_summary(duplicates)
    
    # Return exit code
    return 0 if not duplicates else 1


if __name__ == '__main__':
    sys.exit(main())

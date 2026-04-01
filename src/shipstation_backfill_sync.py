#!/usr/bin/env python3
"""
ShipStation Backfill - Sync Script

Syncs missing shipped orders from ShipStation to local database.
Creates orders in orders_inbox and records shipments in shipped_orders.

Usage:
    python src/shipstation_backfill_sync.py --start-date 2026-01-01 --end-date 2026-01-19
    python src/shipstation_backfill_sync.py --days 7  # Last 7 days
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
from src.services.database.pg_utils import transaction
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


def get_local_inbox_orders(start_date: str, end_date: str) -> Dict[str, int]:
    """Get order numbers and IDs from orders_inbox within date range"""
    rows = execute_query("""
        SELECT order_number, id 
        FROM orders_inbox 
        WHERE order_date >= %s AND order_date <= %s
    """, (start_date, end_date))
    return {row[0]: row[1] for row in rows} if rows else {}


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


def filter_key_items(items: List[Dict]) -> List[Dict]:
    """Filter items to only key product SKUs"""
    return [
        item for item in items
        if any(key_sku in item.get('sku', '') for key_sku in KEY_PRODUCT_SKUS)
    ]


def extract_base_sku(sku: str) -> str:
    """
    Extract base SKU from ShipStation SKU format.
    ShipStation SKUs may be formatted as 'BASE_SKU-LOT' (e.g., '17612-250372').
    Returns just the base SKU portion.
    """
    if not sku:
        return sku
    
    for key_sku in KEY_PRODUCT_SKUS:
        if key_sku in sku:
            return key_sku
    
    if '-' in sku:
        return sku.split('-')[0]
    
    return sku


def get_active_sku_lot(base_sku: str) -> str:
    """Get active lot number for a base SKU"""
    rows = execute_query("""
        SELECT l.lot_number
        FROM lots l
        JOIN skus s ON s.sku_id = l.sku_id
        WHERE s.sku_code = %s AND l.status = 'active'
        ORDER BY l.lot_id DESC LIMIT 1
    """, (base_sku,))
    return rows[0][0] if rows else None


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


def create_order_in_inbox(conn, shipment: Dict) -> int:
    """Create an order in orders_inbox from ShipStation shipment data"""
    cursor = conn.cursor()
    
    order_number = shipment.get('orderNumber', '')
    ship_date = shipment.get('shipDate', '')[:10] if shipment.get('shipDate') else datetime.now().strftime('%Y-%m-%d')
    customer_email = shipment.get('shipTo', {}).get('email', '')
    shipstation_order_id = str(shipment.get('orderId', ''))
    
    ship_to = shipment.get('shipTo', {})
    
    cursor.execute("""
        INSERT INTO orders_inbox (
            order_number, order_date, customer_email, status,
            shipstation_order_id, source_system,
            ship_name, ship_company, ship_street1, ship_street2,
            ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
            shipping_carrier_code, shipping_service_code, tracking_number,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, 'shipped',
            %s, 'shipstation_backfill',
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            NOW(), NOW()
        )
        ON CONFLICT (order_number) DO UPDATE SET
            status = 'shipped',
            shipstation_order_id = EXCLUDED.shipstation_order_id,
            updated_at = NOW()
        RETURNING id
    """, (
        order_number,
        ship_date,
        customer_email,
        shipstation_order_id,
        ship_to.get('name', ''),
        ship_to.get('company', ''),
        ship_to.get('street1', ''),
        ship_to.get('street2', ''),
        ship_to.get('city', ''),
        ship_to.get('state', ''),
        ship_to.get('postalCode', ''),
        ship_to.get('country', ''),
        ship_to.get('phone', ''),
        shipment.get('carrierCode', ''),
        shipment.get('serviceCode', ''),
        shipment.get('trackingNumber', '')
    ))
    
    result = cursor.fetchone()
    return result[0] if result else None


def create_order_items(conn, order_inbox_id: int, items: List[Dict]):
    """Create order items in order_items_inbox"""
    cursor = conn.cursor()
    
    for item in items:
        raw_sku = item.get('sku', '')
        base_sku = extract_base_sku(raw_sku)
        quantity = item.get('quantity', 1)
        unit_price_cents = int(float(item.get('unitPrice', 0)) * 100)
        
        lot = get_active_sku_lot(base_sku)
        sku_lot = f"{base_sku}-{lot}" if lot else None
        
        cursor.execute("""
            INSERT INTO order_items_inbox (order_inbox_id, sku, sku_lot, quantity, unit_price_cents)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (order_inbox_id, sku) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                sku_lot = EXCLUDED.sku_lot
        """, (order_inbox_id, base_sku, sku_lot, quantity, unit_price_cents))


def create_shipped_order(conn, shipment: Dict, total_items: int):
    """Create record in shipped_orders"""
    cursor = conn.cursor()
    
    order_number = shipment.get('orderNumber', '')
    ship_date = shipment.get('shipDate', '')[:10] if shipment.get('shipDate') else datetime.now().strftime('%Y-%m-%d')
    customer_email = shipment.get('shipTo', {}).get('email', '')
    shipstation_order_id = str(shipment.get('orderId', ''))
    
    cursor.execute("""
        INSERT INTO shipped_orders (
            ship_date, order_number, customer_email, total_items,
            shipstation_order_id, shipping_carrier_code, shipping_service_code,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (order_number) DO NOTHING
    """, (
        ship_date,
        order_number,
        customer_email,
        total_items,
        shipstation_order_id,
        shipment.get('carrierCode', ''),
        shipment.get('serviceCode', '')
    ))


def create_shipped_items(conn, shipment: Dict):
    """Create records in shipped_items"""
    cursor = conn.cursor()
    
    order_number = shipment.get('orderNumber', '')
    ship_date = shipment.get('shipDate', '')[:10] if shipment.get('shipDate') else datetime.now().strftime('%Y-%m-%d')
    tracking_number = shipment.get('trackingNumber', '')
    
    items = filter_key_items(shipment.get('shipmentItems', []))
    
    for item in items:
        raw_sku = item.get('sku', '')
        base_sku = extract_base_sku(raw_sku)
        quantity = item.get('quantity', 1)
        lot = get_active_sku_lot(base_sku)
        sku_lot = f"{base_sku}-{lot}" if lot else base_sku
        
        cursor.execute("""
            INSERT INTO shipped_items (
                ship_date, sku_lot, base_sku, quantity_shipped,
                order_number, tracking_number, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (
            ship_date,
            sku_lot,
            base_sku,
            quantity,
            order_number,
            tracking_number
        ))


def sync_shipment(shipment: Dict, inbox_orders: Dict[str, int]) -> Dict[str, Any]:
    """
    Sync a single shipment to local database.
    Returns dict with status and details.
    """
    order_number = shipment.get('orderNumber', '')
    items = filter_key_items(shipment.get('shipmentItems', []))
    total_items = sum(i.get('quantity', 1) for i in items)
    
    result = {
        'order_number': order_number,
        'status': 'unknown',
        'items_count': len(items),
        'units_count': total_items
    }
    
    try:
        with transaction() as conn:
            if order_number in inbox_orders:
                order_inbox_id = inbox_orders[order_number]
                result['status'] = 'updated_existing'
            else:
                order_inbox_id = create_order_in_inbox(conn, shipment)
                create_order_items(conn, order_inbox_id, items)
                result['status'] = 'created_new'
            
            create_shipped_order(conn, shipment, total_items)
            create_shipped_items(conn, shipment)
        
        return result
        
    except Exception as e:
        logger.error(f"Error syncing order {order_number}: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
        return result


def run_sync(start_date: str, end_date: str) -> Dict[str, Any]:
    """Run the full sync process"""
    
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("Failed to get ShipStation credentials")
        return {'error': 'Failed to get ShipStation credentials'}
    
    local_shipped = get_local_shipped_orders(start_date, end_date)
    logger.info(f"Found {len(local_shipped)} orders in local shipped_orders")
    
    inbox_orders = get_local_inbox_orders(start_date, end_date)
    logger.info(f"Found {len(inbox_orders)} orders in local orders_inbox")
    
    shipments = fetch_all_shipments(api_key, api_secret, start_date, end_date)
    
    metrics = {
        'total_shipments': 0,
        'skipped_no_key_products': 0,
        'already_synced': 0,
        'created_new': 0,
        'updated_existing': 0,
        'errors': 0,
        'total_units_synced': 0
    }
    
    seen_orders = set()
    
    for shipment in shipments:
        order_number = extract_order_number(shipment)
        
        if not order_number or order_number in seen_orders:
            continue
        seen_orders.add(order_number)
        
        metrics['total_shipments'] += 1
        
        items = shipment.get('shipmentItems', [])
        if not has_key_products(items):
            metrics['skipped_no_key_products'] += 1
            continue
        
        if order_number in local_shipped:
            metrics['already_synced'] += 1
            continue
        
        result = sync_shipment(shipment, inbox_orders)
        
        if result['status'] == 'created_new':
            metrics['created_new'] += 1
            metrics['total_units_synced'] += result['units_count']
            logger.info(f"✅ Created order {order_number} - {result['units_count']} units")
        elif result['status'] == 'updated_existing':
            metrics['updated_existing'] += 1
            metrics['total_units_synced'] += result['units_count']
            logger.info(f"✅ Updated order {order_number} - {result['units_count']} units")
        elif result['status'] == 'error':
            metrics['errors'] += 1
            logger.error(f"❌ Error with order {order_number}: {result.get('error', 'Unknown')}")
    
    return metrics


def print_results(metrics: Dict[str, Any], start_date: str, end_date: str):
    """Print sync results"""
    
    print("\n" + "="*70)
    print("SHIPSTATION BACKFILL - SYNC RESULTS")
    print("="*70)
    print(f"Date Range: {start_date} to {end_date}")
    print("-"*70)
    
    print(f"\n📦 Total ShipStation Orders:       {metrics['total_shipments']}")
    print(f"   └─ Skipped (no key products):   {metrics['skipped_no_key_products']}")
    print(f"   └─ Already Synced:              {metrics['already_synced']}")
    print(f"   └─ Created New:                 {metrics['created_new']}")
    print(f"   └─ Updated Existing:            {metrics['updated_existing']}")
    print(f"   └─ Errors:                      {metrics['errors']}")
    
    print(f"\n📊 SYNC SUMMARY:")
    print(f"   Total Units Synced:             {metrics['total_units_synced']}")
    
    print("\n" + "="*70)
    
    if metrics['errors'] == 0:
        print("✅ SYNC COMPLETED SUCCESSFULLY")
    else:
        print(f"⚠️  SYNC COMPLETED WITH {metrics['errors']} ERRORS")
    
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='ShipStation Backfill Sync')
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
    
    print(f"\n🚀 Starting sync for {start_date} to {end_date}\n")
    
    metrics = run_sync(start_date, end_date)
    
    print_results(metrics, start_date, end_date)
    
    return metrics


if __name__ == '__main__':
    main()

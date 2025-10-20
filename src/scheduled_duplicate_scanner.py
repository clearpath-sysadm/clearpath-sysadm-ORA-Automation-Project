#!/usr/bin/env python3
"""
Scheduled ShipStation Duplicate Scanner
Monitors ShipStation for duplicate order numbers and creates alerts
Runs every 15 minutes to catch duplicates quickly
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.pg_utils import get_connection, is_workflow_enabled, update_workflow_last_run
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from config.settings import settings
from utils.api_utils import make_api_request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 900  # 15 minutes

def normalize_sku(sku):
    """Extract base SKU from lot number format (e.g., '17612 - 250300' -> '17612')"""
    if not sku:
        return sku
    
    if ' - ' in sku:
        return sku.split(' - ')[0].strip()
    return sku

def fetch_recent_shipstation_orders(api_key, api_secret, days_back=30):
    """
    Fetch recent orders from ShipStation for duplicate detection
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        days_back: Number of days to look back (default 30)
        
    Returns:
        List of order dictionaries from ShipStation
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    logger.info(f"🔍 Scanning ShipStation orders from {start_date.date()} to {end_date.date()}")
    
    all_orders = []
    page = 1
    
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
        
        if response and response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            all_orders.extend(orders)
            
            total_pages = data.get('pages', 1)
            logger.debug(f"Fetched page {page}/{total_pages}, found {len(orders)} orders")
            
            if page >= total_pages:
                break
            page += 1
        else:
            logger.error(f"Failed to fetch ShipStation orders: {response.status_code if response else 'No response'}")
            break
    
    logger.info(f"✅ Fetched {len(all_orders)} total orders from ShipStation")
    return all_orders

def identify_duplicates(orders):
    """
    Identify duplicate order numbers in ShipStation
    
    Returns:
        dict: {order_number: [list of order details]}
    """
    order_map = defaultdict(list)
    
    for order in orders:
        order_number = order.get('orderNumber', '')
        if not order_number:
            continue
        
        order_map[order_number].append({
            'shipstation_id': order.get('orderId'),
            'order_status': order.get('orderStatus'),
            'create_date': order.get('createDate'),
            'customer_name': order.get('shipTo', {}).get('name', 'N/A'),
            'customer_company': order.get('shipTo', {}).get('company', ''),
            'order_total': order.get('orderTotal', 0)
        })
    
    # Filter to only duplicates (count > 1)
    duplicates = {k: v for k, v in order_map.items() if len(v) > 1}
    
    return duplicates

def update_duplicate_alerts(duplicates):
    """
    Update the duplicate_order_alerts table with current duplicates
    
    Args:
        duplicates: dict of {order_number: [list of duplicate records]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get currently active alerts
        cursor.execute("""
            SELECT order_number, shipstation_ids
            FROM duplicate_order_alerts
            WHERE status = 'active'
        """)
        
        existing_alerts = {row[0]: row[1] for row in cursor.fetchall()}
        
        new_count = 0
        updated_count = 0
        resolved_count = 0
        
        # Process current duplicates
        for order_number, dup_list in duplicates.items():
            shipstation_ids = json.dumps([d['shipstation_id'] for d in dup_list])
            details = json.dumps(dup_list)
            
            if order_number in existing_alerts:
                # Update existing alert
                cursor.execute("""
                    UPDATE duplicate_order_alerts
                    SET duplicate_count = %s,
                        shipstation_ids = %s,
                        details = %s,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE order_number = %s AND status = 'active'
                """, (len(dup_list), shipstation_ids, details, order_number))
                updated_count += 1
            else:
                # Create new alert
                cursor.execute("""
                    INSERT INTO duplicate_order_alerts 
                        (order_number, duplicate_count, shipstation_ids, details, status)
                    VALUES (%s, %s, %s, %s, 'active')
                    ON CONFLICT (order_number, status) DO UPDATE
                    SET duplicate_count = EXCLUDED.duplicate_count,
                        shipstation_ids = EXCLUDED.shipstation_ids,
                        details = EXCLUDED.details,
                        last_seen = CURRENT_TIMESTAMP
                """, (order_number, len(dup_list), shipstation_ids, details))
                new_count += 1
        
        # Auto-resolve alerts that are no longer duplicates
        current_duplicate_orders = set(duplicates.keys())
        for order_number in existing_alerts.keys():
            if order_number not in current_duplicate_orders:
                cursor.execute("""
                    UPDATE duplicate_order_alerts
                    SET status = 'resolved',
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = 'auto',
                        notes = 'Auto-resolved: No longer duplicate in ShipStation'
                    WHERE order_number = %s AND status = 'active'
                """, (order_number,))
                resolved_count += 1
        
        conn.commit()
        
        logger.info(f"📊 Alert summary: {new_count} new, {updated_count} updated, {resolved_count} auto-resolved")
        
        return len(duplicates)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating duplicate alerts: {e}", exc_info=True)
        return 0
    finally:
        conn.close()

def scan_for_duplicates():
    """Main scanning function - detects and stores duplicate alerts"""
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error('ShipStation API credentials not found')
            return
        
        # Fetch recent orders
        orders = fetch_recent_shipstation_orders(api_key, api_secret, days_back=30)
        
        if not orders:
            logger.warning('No orders fetched from ShipStation')
            return
        
        # Identify duplicates
        duplicates = identify_duplicates(orders)
        
        if duplicates:
            logger.warning(f"⚠️  Found {len(duplicates)} duplicate order numbers in ShipStation!")
            for order_num, dup_list in duplicates.items():
                logger.warning(f"  Order {order_num}: {len(dup_list)} records")
        else:
            logger.info("✅ No duplicate orders found in ShipStation")
        
        # Update alerts database
        active_count = update_duplicate_alerts(duplicates)
        
        logger.info(f"🎯 Active duplicate alerts: {active_count}")
        
    except Exception as e:
        logger.error(f"Error during duplicate scan: {e}", exc_info=True)

def run_scheduled_scanner():
    """Main loop - runs every 15 minutes"""
    logger.info(f"🚀 Duplicate Scanner started (scanning every {SCAN_INTERVAL_SECONDS // 60} minutes)")
    
    while True:
        try:
            # Check workflow control
            if not is_workflow_enabled('duplicate-scanner'):
                logger.debug("Workflow disabled - sleeping 60s")
                time.sleep(60)
                continue
            
            # Run scan
            scan_for_duplicates()
            
            # Update workflow timestamp
            update_workflow_last_run('duplicate-scanner')
            
            # Sleep until next scan
            logger.info(f"😴 Next scan in {SCAN_INTERVAL_SECONDS // 60} minutes")
            time.sleep(SCAN_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Duplicate scanner stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Scanner error: {e}", exc_info=True)
            time.sleep(60)

if __name__ == '__main__':
    run_scheduled_scanner()

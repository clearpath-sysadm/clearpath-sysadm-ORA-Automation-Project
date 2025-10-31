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

def fetch_recent_shipstation_orders(api_key, api_secret, days_back=90):
    """
    Fetch recent orders from ShipStation for duplicate detection
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        days_back: Number of days to look back (default 90 for comprehensive coverage)
        
    Returns:
        Tuple of (list of orders, scan_successful boolean)
        scan_successful is False if any API errors or incomplete pagination
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    logger.info(f"🔍 Scanning ShipStation orders from {start_date.date()} to {end_date.date()}")
    
    all_orders = []
    page = 1
    scan_successful = True
    
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
            logger.error(f"❌ Failed to fetch ShipStation orders: {response.status_code if response else 'No response'}")
            scan_successful = False
            break
    
    if scan_successful and all_orders:
        logger.info(f"✅ Scan successful: Fetched {len(all_orders)} total orders from ShipStation")
    elif not scan_successful:
        logger.error(f"⚠️  Scan FAILED: API error during fetch - will NOT auto-resolve existing alerts")
    else:
        logger.warning(f"⚠️  Scan returned 0 orders - possible API issue - will NOT auto-resolve existing alerts")
        scan_successful = False
    
    return all_orders, scan_successful

def identify_duplicates(orders):
    """
    Identify duplicate orders in ShipStation
    
    DUPLICATE DEFINITION: Two or more orders with the same order_number AND base_sku
    
    INCLUDES: All order statuses (including cancelled orders)
    
    Returns:
        dict: {(order_number, base_sku): [list of order details]}
    """
    # Group by (order_number, base_sku) - each item in an order creates a separate entry
    order_sku_map = defaultdict(list)
    
    for order in orders:
        order_number = order.get('orderNumber', '')
        if not order_number:
            continue
        
        # Extract all items from the order
        items = order.get('items', [])
        
        # Process each item separately to detect SKU-level duplicates
        for item in items:
            sku = item.get('sku', '')
            if not sku:
                continue
            
            # Extract base SKU (remove lot number suffix like " - 250300")
            base_sku = normalize_sku(sku)
            
            # Key is (order_number, base_sku) tuple
            key = (order_number, base_sku)
            
            order_sku_map[key].append({
                'shipstation_id': order.get('orderId'),
                'order_number': order_number,
                'base_sku': base_sku,
                'full_sku': sku,
                'quantity': item.get('quantity', 0),
                'order_status': order.get('orderStatus'),
                'create_date': order.get('createDate'),
                'customer_name': order.get('shipTo', {}).get('name', 'N/A'),
                'customer_company': order.get('shipTo', {}).get('company', ''),
                'order_total': order.get('orderTotal', 0)
            })
    
    # Filter to only duplicates (count > 1 for same order_number + base_sku)
    duplicates = {k: v for k, v in order_sku_map.items() if len(v) > 1}
    
    return duplicates

def identify_order_number_collisions(orders):
    """
    Identify ORDER NUMBER COLLISIONS in ShipStation
    
    COLLISION DEFINITION: Same order_number appears with DIFFERENT ShipStation IDs
    (regardless of SKU differences)
    
    This catches cases where:
    - Same order number was manually created multiple times
    - Order number reused for different customers
    - Data corruption or external system issues
    
    Returns:
        dict: {order_number: [list of order details with different ShipStation IDs]}
    """
    # Group by order_number only (not SKU)
    order_map = defaultdict(lambda: defaultdict(dict))
    
    for order in orders:
        order_number = order.get('orderNumber', '')
        shipstation_id = order.get('orderId')
        
        if not order_number or not shipstation_id:
            continue
        
        # Store unique ShipStation IDs per order number
        if shipstation_id not in order_map[order_number]:
            ship_to = order.get('shipTo') or {}
            
            # Collect all items for this ShipStation order
            items = []
            for item in order.get('items', []):
                sku = item.get('sku', '')
                if sku:
                    base_sku = normalize_sku(sku)
                    items.append({
                        'base_sku': base_sku,
                        'full_sku': sku,
                        'quantity': item.get('quantity', 0)
                    })
            
            order_map[order_number][shipstation_id] = {
                'shipstation_id': shipstation_id,
                'order_number': order_number,
                'order_status': order.get('orderStatus'),
                'create_date': order.get('createDate'),
                'customer_name': ship_to.get('name', 'N/A'),
                'customer_company': ship_to.get('company', ''),
                'order_total': order.get('orderTotal', 0),
                'items': items
            }
    
    # Filter to only collisions (same order_number with multiple ShipStation IDs)
    collisions = {}
    for order_number, shipstation_dict in order_map.items():
        if len(shipstation_dict) > 1:
            # Convert to list of order details
            collisions[order_number] = list(shipstation_dict.values())
    
    return collisions

def check_and_auto_resolve_deleted_duplicates(cursor, current_duplicates):
    """
    Auto-resolve duplicate alerts when remaining records (after deletions) no longer constitute duplicates.
    
    BUSINESS RULE:
    An alert should only auto-resolve if AFTER user deletions, the remaining active 
    (non-deleted) ShipStation records no longer represent a duplicate/mismatch issue.
    
    This means:
    1. If ALL records are deleted → Auto-resolve
    2. If some records remain → Check if they still appear as duplicates in current scan
       - If YES (still in current_duplicates dict) → Keep alert active
       - If NO (no longer duplicates) → Auto-resolve
    
    Args:
        cursor: Database cursor
        current_duplicates: dict of {(order_number, base_sku): [list of current duplicate records]}
    
    Returns:
        int: Number of alerts auto-resolved
    """
    # Get all active alerts (their IDs were just updated by update_duplicate_alerts)
    cursor.execute("""
        SELECT id, order_number, base_sku, shipstation_ids
        FROM duplicate_order_alerts
        WHERE status = 'active'
    """)
    
    active_alerts = cursor.fetchall()
    auto_resolved_count = 0
    
    for alert_id, order_number, base_sku, shipstation_ids_json in active_alerts:
        try:
            # Parse the FRESHLY-UPDATED ShipStation IDs from database
            shipstation_ids = json.loads(shipstation_ids_json) if shipstation_ids_json else []
            
            if not shipstation_ids:
                continue
            
            # Get which of these IDs have been marked as deleted by user
            placeholders = ','.join(['%s'] * len(shipstation_ids))
            cursor.execute(f"""
                SELECT shipstation_order_id
                FROM deleted_shipstation_orders
                WHERE shipstation_order_id IN ({placeholders})
            """, shipstation_ids)
            
            deleted_ids = {row[0] for row in cursor.fetchall()}
            
            # Calculate REMAINING (non-deleted) ShipStation IDs
            remaining_ids = [sid for sid in shipstation_ids if sid not in deleted_ids]
            
            # If ALL duplicates are deleted, auto-resolve
            if len(remaining_ids) == 0:
                cursor.execute("""
                    UPDATE duplicate_order_alerts
                    SET status = 'resolved',
                        resolved_at = CURRENT_TIMESTAMP,
                        resolution_notes = 'Auto-resolved: All duplicate ShipStation records deleted by user'
                    WHERE id = %s
                """, (alert_id,))
                
                auto_resolved_count += 1
                logger.info(f"✅ Auto-resolved alert {alert_id} for Order #{order_number} + SKU {base_sku} (all {len(shipstation_ids)} duplicates deleted)")
                continue
            
            # Check if remaining records still appear as duplicates in current scan
            # This validates that the remaining non-deleted records are clean
            alert_key = (order_number, base_sku)
            
            if alert_key not in current_duplicates:
                # This alert no longer appears in the current scan - handled by main auto-resolution
                continue
            
            # Get the current duplicate ShipStation IDs from the scan
            current_dup_ids = {d['shipstation_id'] for d in current_duplicates[alert_key]}
            
            # Check if ANY of the remaining (non-deleted) IDs still appear in current duplicates
            remaining_still_duplicated = any(rid in current_dup_ids for rid in remaining_ids)
            
            if not remaining_still_duplicated:
                # Remaining records are no longer showing as duplicates in scan
                # This means after deletions, the issue is resolved
                cursor.execute("""
                    UPDATE duplicate_order_alerts
                    SET status = 'resolved',
                        resolved_at = CURRENT_TIMESTAMP,
                        resolution_notes = 'Auto-resolved: Remaining records after deletion no longer duplicates'
                    WHERE id = %s
                """, (alert_id,))
                
                auto_resolved_count += 1
                logger.info(f"✅ Auto-resolved alert {alert_id} for Order #{order_number} + SKU {base_sku} (remaining {len(remaining_ids)} record(s) no longer duplicated)")
        
        except Exception as e:
            logger.error(f"Error checking deleted status for alert {alert_id}: {e}")
            continue
    
    return auto_resolved_count

def update_duplicate_alerts(duplicates):
    """
    Update the duplicate_order_alerts table with current duplicates
    
    Args:
        duplicates: dict of {(order_number, base_sku): [list of duplicate records]}
    
    Note:
        Auto-resolution now enabled for deleted duplicates ONLY.
        When ALL ShipStation IDs for an alert are marked as deleted, 
        the alert is automatically resolved to reduce manual work.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get currently active alerts
        cursor.execute("""
            SELECT order_number, base_sku, shipstation_ids
            FROM duplicate_order_alerts
            WHERE status = 'active'
        """)
        
        existing_alerts = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        # Get recently manually-resolved alerts (within last 30 days) to prevent re-creation
        cursor.execute("""
            SELECT order_number, base_sku, resolved_at
            FROM duplicate_order_alerts
            WHERE status = 'resolved'
            AND resolution_notes LIKE '%manually resolved%'
            AND resolved_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
        """)
        
        manually_resolved = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        new_count = 0
        updated_count = 0
        resolved_count = 0
        skipped_count = 0
        
        # Process current duplicates
        for (order_number, base_sku), dup_list in duplicates.items():
            shipstation_ids = json.dumps([d['shipstation_id'] for d in dup_list])
            details = json.dumps(dup_list)
            
            key = (order_number, base_sku)
            
            if key in existing_alerts:
                # Update existing alert
                cursor.execute("""
                    UPDATE duplicate_order_alerts
                    SET duplicate_count = %s,
                        shipstation_ids = %s,
                        details = %s,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE order_number = %s AND base_sku = %s AND status = 'active'
                """, (len(dup_list), shipstation_ids, details, order_number, base_sku))
                updated_count += 1
            elif key in manually_resolved:
                # Skip re-creating alerts that were manually resolved within last 30 days
                resolved_date = manually_resolved[key]
                logger.info(f"⏭️ Skipping Order #{order_number} + SKU {base_sku} - manually resolved on {resolved_date}")
                skipped_count += 1
            else:
                # Create new alert (simple INSERT since we already checked it doesn't exist)
                cursor.execute("""
                    INSERT INTO duplicate_order_alerts 
                        (order_number, base_sku, duplicate_count, shipstation_ids, details, status)
                    VALUES (%s, %s, %s, %s, %s, 'active')
                """, (order_number, base_sku, len(dup_list), shipstation_ids, details))
                new_count += 1
        
        # Auto-resolve alerts that NO LONGER appear in current scan (no longer duplicates)
        no_longer_duplicates = 0
        for (order_number, base_sku) in existing_alerts.keys():
            if (order_number, base_sku) not in duplicates:
                cursor.execute("""
                    UPDATE duplicate_order_alerts
                    SET status = 'resolved',
                        resolved_at = CURRENT_TIMESTAMP,
                        resolution_notes = 'Auto-resolved: No longer appears as duplicate in ShipStation scan'
                    WHERE order_number = %s AND base_sku = %s AND status = 'active'
                """, (order_number, base_sku))
                no_longer_duplicates += 1
                logger.info(f"✅ Auto-resolved alert for Order #{order_number} + SKU {base_sku} (no longer a duplicate)")
        
        # Auto-resolve alerts where remaining records (after deletions) no longer constitute duplicates
        # Called AFTER alerts are updated with fresh scan data, so IDs in DB are current
        auto_resolved_deleted = check_and_auto_resolve_deleted_duplicates(cursor, duplicates)
        
        total_auto_resolved = no_longer_duplicates + auto_resolved_deleted
        
        if total_auto_resolved > 0:
            logger.info(f"✅ Total auto-resolved: {total_auto_resolved} alerts ({no_longer_duplicates} no longer duplicates, {auto_resolved_deleted} all deleted)")
        
        if skipped_count > 0:
            logger.info(f"⏭️ Skipped {skipped_count} manually resolved alert(s)")
        
        logger.info(f"📊 Alert summary: {new_count} new, {updated_count} updated, {total_auto_resolved} auto-resolved, {skipped_count} skipped")
        
        conn.commit()
        
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
            logger.error('❌ ShipStation API credentials not found - cannot scan')
            return False
        
        # Fetch recent orders (90-day lookback for comprehensive coverage)
        orders, scan_successful = fetch_recent_shipstation_orders(api_key, api_secret, days_back=90)
        
        # SAFETY: If scan failed, skip alert updates entirely to preserve existing alerts
        if not scan_successful:
            logger.error('❌ Scan failed - preserving existing alerts without updates')
            return False
        
        if not orders:
            logger.warning('⚠️  Scan returned 0 orders - skipping alert updates to preserve existing alerts')
            return False
        
        # Identify duplicates (same order number + same SKU)
        duplicates = identify_duplicates(orders)
        
        if duplicates:
            logger.warning(f"⚠️  Found {len(duplicates)} duplicate order+SKU combinations in ShipStation!")
            for (order_num, base_sku), dup_list in list(duplicates.items())[:10]:  # Log first 10
                logger.warning(f"  Order #{order_num} + SKU {base_sku}: {len(dup_list)} records")
            if len(duplicates) > 10:
                logger.warning(f"  ... and {len(duplicates) - 10} more duplicates")
        else:
            logger.info("✅ No duplicate orders found in ShipStation")
        
        # Identify order number collisions (same order number with different ShipStation IDs)
        collisions = identify_order_number_collisions(orders)
        
        if collisions:
            logger.warning(f"🚨 Found {len(collisions)} ORDER NUMBER COLLISIONS in ShipStation!")
            for order_num, collision_list in list(collisions.items())[:10]:  # Log first 10
                shipstation_ids = [c['shipstation_id'] for c in collision_list]
                logger.warning(f"  Order #{order_num}: {len(collision_list)} different ShipStation IDs: {shipstation_ids}")
            if len(collisions) > 10:
                logger.warning(f"  ... and {len(collisions) - 10} more collisions")
        else:
            logger.info("✅ No order number collisions found")
        
        # Update alerts database
        active_count = update_duplicate_alerts(duplicates)
        
        logger.info(f"🎯 Active duplicate alerts: {active_count}")
        logger.info(f"🚨 Order number collisions detected: {len(collisions)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during duplicate scan: {e}", exc_info=True)
        return False

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
            scan_succeeded = scan_for_duplicates()
            
            # SAFETY: Only update workflow timestamp on successful scans
            # This allows monitoring systems to detect scan failures
            if scan_succeeded:
                update_workflow_last_run('duplicate-scanner')
            else:
                logger.error("❌ Scan failed - workflow timestamp NOT updated (monitoring will detect failure)")
            
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

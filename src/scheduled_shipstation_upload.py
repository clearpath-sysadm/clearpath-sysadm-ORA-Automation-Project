#!/usr/bin/env python3
"""
Scheduled ShipStation Upload
Runs every 5 minutes to automatically upload pending orders to ShipStation
"""
import os
import sys
import time
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.db_utils import get_connection, transaction_with_retry
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    send_all_orders_to_shipstation,
    fetch_shipstation_orders_by_order_numbers
)
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

UPLOAD_INTERVAL_SECONDS = 300  # 5 minutes

def normalize_sku(sku):
    """
    FIX 1: Normalize SKU format to prevent duplicates from spacing inconsistencies
    
    Standardizes SKU format by:
    - Removing extra whitespace
    - Standardizing dash spacing to " - " (space-dash-space)
    - Handling both "17612-250237" and "17612 - 250237" formats
    
    Args:
        sku (str): Raw SKU string from database
        
    Returns:
        str: Normalized SKU in format "BASE - LOT" or "BASE" if no lot
    """
    if not sku:
        return ''
    
    sku = sku.strip()
    
    if '-' in sku:
        parts = sku.split('-')
        if len(parts) == 2:
            base = parts[0].strip()
            lot = parts[1].strip()
            return f"{base} - {lot}"
    
    return sku

def upload_pending_orders():
    """
    Upload pending orders from orders_inbox to ShipStation
    This is the same logic as the /api/upload_orders_to_shipstation endpoint
    
    RACE CONDITION FIX: Uses atomic claiming with run-specific identifier to prevent
    duplicate uploads when multiple upload runs execute concurrently.
    """
    # Generate unique run identifier for this upload batch (outside try block for exception handler)
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error('ShipStation API credentials not found')
            return 0
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # STEP 1: ATOMICALLY CLAIM PENDING ORDERS WITH RUN IDENTIFIER
        
        # Use BEGIN IMMEDIATE to get exclusive lock immediately
        cursor.execute("BEGIN IMMEDIATE")
        
        # Fetch pending order IDs that need upload
        cursor.execute("""
            SELECT id
            FROM orders_inbox
            WHERE status = 'pending'
              AND order_number NOT IN (SELECT order_number FROM shipped_orders)
        """)
        
        pending_ids = [row[0] for row in cursor.fetchall()]
        
        if not pending_ids:
            conn.commit()
            conn.close()
            logger.info('No pending orders to upload')
            return 0
        
        # Mark ONLY these specific orders as 'uploaded' with our run_id  
        # This prevents other concurrent runs from picking up our orders
        placeholders = ','.join('?' * len(pending_ids))
        cursor.execute(f"""
            UPDATE orders_inbox
            SET status = 'uploaded',
                failure_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """, [run_id] + pending_ids)
        
        claimed_count = cursor.rowcount
        conn.commit()
        
        logger.info(f'Claimed {claimed_count} pending orders for upload (run_id: {run_id})')
        
        # STEP 2: FETCH ONLY THE ORDERS WE JUST CLAIMED
        # Fetch SKU-Lot mappings
        cursor.execute("""
            SELECT sku, lot
            FROM sku_lot 
            WHERE active = 1
        """)
        sku_lot_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch Product Name mappings
        cursor.execute("""
            SELECT sku, value
            FROM configuration_params
            WHERE category = 'Product Names'
        """)
        product_name_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch ONLY the orders we claimed (identified by our run_id)
        cursor.execute(f"""
            SELECT id, order_number, order_date, customer_email, total_amount_cents,
                   ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                   bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
            FROM orders_inbox 
            WHERE status = 'uploaded'
              AND failure_reason = ?
        """, (run_id,))
        
        pending_orders = cursor.fetchall()
        
        # Build ShipStation order payloads (ONE ORDER PER SKU)
        shipstation_orders = []
        order_sku_map = []
        
        for order_row in pending_orders:
            (order_id, order_number, order_date, customer_email, total_amount_cents,
             ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
             bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone) = order_row
            
            # Get order items
            cursor.execute("""
                SELECT sku, quantity, unit_price_cents
                FROM order_items_inbox
                WHERE order_inbox_id = ?
            """, (order_id,))
            items = cursor.fetchall()
            
            # FIX 2: CONSOLIDATE items by base SKU to prevent duplicates
            # Group items by normalized base SKU and sum quantities
            consolidated_items = defaultdict(lambda: {'qty': 0, 'price': 0, 'original_sku': ''})
            
            for sku, qty, unit_price_cents in items:
                # Normalize the SKU to handle spacing inconsistencies
                normalized_sku = normalize_sku(sku)
                # Extract base SKU (without lot number)
                base_sku = normalized_sku.split(' - ')[0].strip()
                
                # Accumulate quantities for same base SKU
                consolidated_items[base_sku]['qty'] += qty
                # Keep first price found (should be same for same SKU)
                if consolidated_items[base_sku]['price'] == 0 and unit_price_cents:
                    consolidated_items[base_sku]['price'] = unit_price_cents
                # Keep original SKU for tracking
                if not consolidated_items[base_sku]['original_sku']:
                    consolidated_items[base_sku]['original_sku'] = sku
            
            # FIX: Create ONE ShipStation order with ALL SKUs as line items
            if consolidated_items:
                # Build line items array with ALL SKUs
                line_items = []
                total_amount = 0
                all_skus = []
                
                for base_sku, item_data in consolidated_items.items():
                    qty = item_data['qty']
                    unit_price_cents = item_data['price']
                    
                    # Get lot number from sku_lot mapping
                    lot_number = sku_lot_map.get(base_sku, '')
                    sku_with_lot = f"{base_sku} - {lot_number}" if lot_number else base_sku
                    product_name = product_name_map.get(base_sku, f'Product {base_sku}')
                    
                    line_items.append({
                        'sku': sku_with_lot,
                        'name': product_name,
                        'quantity': qty,
                        'unitPrice': (unit_price_cents / 100) if unit_price_cents else 0
                    })
                    
                    total_amount += (unit_price_cents * qty / 100) if unit_price_cents else 0
                    all_skus.append(base_sku)
                
                # Create SINGLE ShipStation order with ALL line items
                shipstation_order = {
                    'orderNumber': order_number,
                    'orderDate': order_date,
                    'orderStatus': 'awaiting_shipment',
                    'customerEmail': customer_email or '',
                    'billTo': {
                        'name': bill_name or '',
                        'company': bill_company or '',
                        'street1': bill_street1 or '',
                        'city': bill_city or '',
                        'state': bill_state or '',
                        'postalCode': bill_postal_code or '',
                        'country': bill_country or 'US',
                        'phone': bill_phone or ''
                    },
                    'shipTo': {
                        'name': ship_name or '',
                        'company': ship_company or '',
                        'street1': ship_street1 or '',
                        'city': ship_city or '',
                        'state': ship_state or '',
                        'postalCode': ship_postal_code or '',
                        'country': ship_country or 'US',
                        'phone': ship_phone or ''
                    },
                    'items': line_items,  # ALL SKUs in single order
                    'amountPaid': total_amount,
                    'taxAmount': 0,
                    'shippingAmount': 0
                }
                
                shipstation_orders.append(shipstation_order)
                order_sku_map.append({
                    'order_inbox_id': order_id,
                    'sku': '|'.join(all_skus),  # Track all SKUs for this order
                    'order_number': order_number,
                    'sku_with_lot': '|'.join([item['sku'] for item in line_items])
                })
        
        # FIX 3: IN-BATCH DUPLICATE PREVENTION
        # Remove duplicates within the current batch (should be rare now - one order per order_number)
        seen_in_batch = set()
        deduplicated_orders = []
        deduplicated_sku_map = []
        
        for idx, order in enumerate(shipstation_orders):
            order_num = order['orderNumber'].upper()
            
            if order_num not in seen_in_batch:
                seen_in_batch.add(order_num)
                deduplicated_orders.append(order)
                deduplicated_sku_map.append(order_sku_map[idx])
            else:
                logger.warning(f"Skipped in-batch duplicate: Order {order_num}")
        
        # Replace with deduplicated lists
        shipstation_orders = deduplicated_orders
        order_sku_map = deduplicated_sku_map
        
        logger.info(f"After in-batch deduplication: {len(shipstation_orders)} unique orders")
        
        # Check for duplicates in ShipStation
        unique_order_numbers = list(set([o['orderNumber'] for o in shipstation_orders]))
        
        # STEP 1: Safe error handling for API duplicate check
        try:
            existing_orders = fetch_shipstation_orders_by_order_numbers(
                api_key,
                api_secret,
                settings.SHIPSTATION_ORDERS_ENDPOINT,
                unique_order_numbers
            )
            api_check_failed = False
        except Exception as e:
            logger.error(f"ShipStation API duplicate check failed: {e}")
            existing_orders = []  # Safe default: treat as no existing orders
            api_check_failed = True
        
        # STEP 2: ABORT if API check failed to prevent duplicate uploads
        if api_check_failed:
            logger.error("ABORT: Cannot verify duplicates - reverting orders to prevent duplicate uploads")
            
            # Revert claimed orders back to 'pending' for retry in next cycle
            # Use run_id match only (no status filter) to catch orders regardless of current state
            cursor.execute("""
                UPDATE orders_inbox
                SET status = 'pending',
                    failure_reason = 'API duplicate check failed - will retry next cycle',
                    updated_at = CURRENT_TIMESTAMP
                WHERE failure_reason = ?
            """, (run_id,))
            
            reverted = cursor.rowcount
            conn.commit()
            # Note: Keep connection open - function will exit cleanly with return 0
            
            logger.info(f'Aborted upload: Reverted {reverted} orders from run {run_id} back to pending due to API failure')
            return 0
        
        # FIX 4: Create map of existing orders by order_number
        existing_order_map = {}
        for o in existing_orders:
            order_num = o.get('orderNumber', '').strip().upper()
            order_id = o.get('orderId')
            order_key = o.get('orderKey')
            
            existing_order_map[order_num] = {
                'orderId': order_id,
                'orderKey': order_key
            }
        
        # Filter out duplicates
        new_orders = []
        new_order_sku_map = []
        skipped_count = 0
        
        for idx, order in enumerate(shipstation_orders):
            order_num_upper = order['orderNumber'].strip().upper()
            order_sku_info = order_sku_map[idx]
            
            if order_num_upper in existing_order_map:
                # Already exists in ShipStation - update status from 'processing' to 'awaiting_shipment'
                existing = existing_order_map[order_num_upper]
                skipped_count += 1
                shipstation_id = existing['orderId'] or existing['orderKey']
                
                # Track all SKUs for this order
                all_skus = order_sku_info['sku'].split('|')
                for sku in all_skus:
                    cursor.execute("""
                        INSERT OR IGNORE INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                        VALUES (?, ?, ?)
                    """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                
                # Update from 'processing' to 'awaiting_shipment' (clear run_id)
                cursor.execute("""
                    UPDATE orders_inbox
                    SET status = 'awaiting_shipment',
                        shipstation_order_id = ?,
                        failure_reason = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (shipstation_id, order_sku_info['order_inbox_id']))
            else:
                # New order - needs upload
                new_orders.append(order)
                new_order_sku_map.append(order_sku_info)
        
        if not new_orders:
            conn.commit()
            conn.close()
            logger.info(f'All {len(shipstation_orders)} orders already exist in ShipStation (skipped: {skipped_count})')
            return 0
        
        # Upload to ShipStation
        logger.info(f'Uploading {len(new_orders)} new orders to ShipStation')
        
        upload_results = send_all_orders_to_shipstation(
            new_orders,
            api_key,
            api_secret,
            settings.SHIPSTATION_CREATE_ORDERS_ENDPOINT
        )
        
        # Update database with results
        uploaded_count = 0
        failed_count = 0
        
        for idx, result in enumerate(upload_results):
            order_key = result.get('orderKey', '')
            order_id = result.get('orderId')
            success = result.get('success', False)
            error_msg = result.get('errorMessage')
            
            if idx < len(new_order_sku_map):
                order_sku_info = new_order_sku_map[idx]
                
                if success:
                    shipstation_id = order_id or order_key
                    
                    # Track all SKUs for this order
                    all_skus = order_sku_info['sku'].split('|')
                    for sku in all_skus:
                        cursor.execute("""
                            INSERT OR IGNORE INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                            VALUES (?, ?, ?)
                        """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                    
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET shipstation_order_id = ?
                        WHERE id = ? AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
                    """, (shipstation_id, order_sku_info['order_inbox_id']))
                    
                    uploaded_count += 1
                else:
                    failed_count += 1
                    error_details = error_msg or result.get('message') or 'Unknown error'
                    logger.error(f"Upload failed for order {order_sku_info['order_number']}: {error_details}")
                    
                    # Revert failed orders back to 'pending' for retry
                    cursor.execute("""
                        UPDATE orders_inbox 
                        SET status = 'pending',
                            failure_reason = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (error_details, order_sku_info['order_inbox_id']))
        
        # Update successfully uploaded orders from THIS RUN ONLY (clear run_id from failure_reason)
        cursor.execute("""
            UPDATE orders_inbox
            SET status = 'awaiting_shipment',
                failure_reason = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'processing'
              AND failure_reason = ?
              AND id IN (
                SELECT DISTINCT order_inbox_id 
                FROM shipstation_order_line_items
            )
        """, (run_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f'Upload complete: {uploaded_count} uploaded, {failed_count} failed, {skipped_count} skipped')
        
        # Auto-refresh ShipStation metrics to prevent stale cache
        if uploaded_count > 0:
            try:
                from src.services.shipstation.metrics_refresher import refresh_shipstation_metrics
                refresh_shipstation_metrics()
                logger.info("ShipStation metrics refreshed after upload")
            except Exception as refresh_error:
                logger.warning(f"Failed to refresh ShipStation metrics: {refresh_error}")
            
            # Run duplicate detection after successful upload
            try:
                from src.services.shipping_validator import detect_duplicate_order_sku
                duplicate_results = detect_duplicate_order_sku()
                if duplicate_results.get('violations_created', 0) > 0:
                    logger.warning(f"Duplicate detection: {duplicate_results['violations_created']} violations created for {duplicate_results['total_duplicates']} duplicate combinations")
                else:
                    logger.info("Duplicate detection: No duplicates found")
            except Exception as duplicate_error:
                logger.warning(f"Failed to run duplicate detection: {duplicate_error}")
        
        return uploaded_count
        
    except Exception as e:
        logger.error(f'Error uploading orders (run_id: {run_id}): {str(e)}', exc_info=True)
        
        # SAFETY: Revert ONLY THIS RUN's orders back to 'pending'
        # DO NOT touch other concurrent runs' claimed orders
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders_inbox
                SET status = 'pending',
                    failure_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'processing'
                  AND failure_reason = ?
            """, (run_id,))
            reverted = cursor.rowcount
            conn.commit()
            conn.close()
            if reverted > 0:
                logger.info(f'Reverted {reverted} orders from run {run_id} back to pending')
        except Exception as revert_error:
            logger.error(f'Failed to revert run {run_id} orders: {str(revert_error)}')
        
        return 0

def run_scheduled_upload():
    """Main loop - runs every 5 minutes"""
    logger.info(f"Starting scheduled ShipStation upload (every {UPLOAD_INTERVAL_SECONDS}s)")
    
    while True:
        try:
            logger.info("Running scheduled upload...")
            
            uploaded = upload_pending_orders()
            
            if uploaded > 0:
                logger.info(f"Successfully uploaded {uploaded} orders to ShipStation")
            
            logger.info(f"Next upload in {UPLOAD_INTERVAL_SECONDS} seconds")
            time.sleep(UPLOAD_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Scheduled upload stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduled upload: {str(e)}")
            time.sleep(UPLOAD_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_scheduled_upload()

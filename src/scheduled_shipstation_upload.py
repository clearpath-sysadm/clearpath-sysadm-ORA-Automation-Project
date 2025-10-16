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

from src.services.database.pg_utils import get_connection, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
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

UPLOAD_INTERVAL_SECONDS = 300  # 5 minutes (used when fast polling disabled)

# ============================================
# OPTIMIZED POLLING - Phase 1 Implementation
# ============================================

# Feature flag cache (reduce DB queries)
_flag_cache = {}
_flag_cache_time = None

def get_feature_flag(key, default='false'):
    """Cached feature flag check (60 sec TTL)"""
    global _flag_cache, _flag_cache_time
    
    # Cache for 60 seconds
    if _flag_cache_time and (datetime.now() - _flag_cache_time).seconds < 60:
        return _flag_cache.get(key, default)
    
    # Refresh cache using existing get_connection
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT parameter_name, value 
            FROM configuration_params 
            WHERE category = 'Polling'
        """)
        _flag_cache = {row[0]: row[1] for row in cursor.fetchall()}
        _flag_cache_time = datetime.now()
        return _flag_cache.get(key, default)
    finally:
        conn.close()

def has_pending_orders_fast():
    """
    EFFICIENT: Use EXISTS instead of COUNT
    Returns (has_orders: bool, count: int, duration_ms: int)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        start = time.time()
        
        # CORRECTED: Use 'awaiting_shipment' not 'Pending'
        # EXISTS is faster than COUNT for large tables
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM orders_inbox 
                WHERE status = 'awaiting_shipment'
                LIMIT 1
            )
        """)
        has_orders = cursor.fetchone()[0]
        
        # If orders exist, get actual count for logging
        count = 0
        if has_orders:
            cursor.execute("""
                SELECT COUNT(*) FROM orders_inbox 
                WHERE status = 'awaiting_shipment'
            """)
            count = cursor.fetchone()[0]
        
        duration_ms = int((time.time() - start) * 1000)
        
        # Structured log for monitoring
        logger.info(f"METRICS: workflow=upload exists={has_orders} count={count} duration_ms={duration_ms} action={'process' if has_orders else 'skip'}")
        
        return has_orders, count, duration_ms
        
    except Exception as e:
        logger.error(f"Error checking pending orders: {e}")
        return True, 0, 0  # Default to processing on error (safe fallback)
    finally:
        conn.close()

def update_polling_state(count):
    """Update polling state for monitoring"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE polling_state 
            SET last_upload_count = %s,
                last_upload_check = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (count,))
        conn.commit()
    except Exception as e:
        logger.debug(f"Failed to update polling state: {e}")
        # Don't fail workflow on metrics update
    finally:
        conn.close()

# ============================================
# END OPTIMIZED POLLING
# ============================================

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
        
        # PostgreSQL: Use SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        # - FOR UPDATE locks the selected rows
        # - SKIP LOCKED makes concurrent queries skip already-locked rows
        # This ensures only one process can claim each pending order
        
        # Fetch pending order IDs that need upload (with row-level locking)
        cursor.execute("""
            SELECT id
            FROM orders_inbox
            WHERE status = 'awaiting_shipment'
              AND order_number NOT IN (SELECT order_number FROM shipped_orders)
            FOR UPDATE SKIP LOCKED
        """)
        
        pending_ids = [row[0] for row in cursor.fetchall()]
        
        if not pending_ids:
            conn.commit()
            conn.close()
            logger.info('No pending orders to upload')
            return 0
        
        # Mark ONLY these specific orders as 'uploaded' with our run_id  
        # This prevents other concurrent runs from picking up our orders
        placeholders = ','.join(['%s'] * len(pending_ids))
        cursor.execute(f"""
            UPDATE orders_inbox
            SET status = 'uploaded',
                failure_reason = %s,
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
        
        # DEFENSIVE CHECK: Warn if no active lots found
        if not sku_lot_map:
            logger.warning('⚠️ No active lot numbers found in sku_lot table! Orders will upload without lot numbers.')
        else:
            logger.info(f'✅ Loaded {len(sku_lot_map)} active lot mappings: {sku_lot_map}')
        
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
              AND failure_reason = %s
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
                WHERE order_inbox_id = %s
            """, (order_id,))
            items = cursor.fetchall()
            
            # CONSOLIDATE items by FULL SKU (with lot) to preserve lot-level granularity
            # CRITICAL: Must preserve lot information to prevent inventory tracking failures
            consolidated_items = defaultdict(lambda: {'qty': 0, 'price': 0, 'original_sku': ''})
            
            for sku, qty, unit_price_cents in items:
                # Normalize the SKU to handle spacing inconsistencies (preserves lot number)
                normalized_sku = normalize_sku(sku)  # "17612 - 250237" format
                
                # FIX: If SKU doesn't have a lot number, append active lot from sku_lot_map
                if ' - ' not in normalized_sku and normalized_sku in sku_lot_map:
                    normalized_sku = f"{normalized_sku} - {sku_lot_map[normalized_sku]}"
                
                # Accumulate quantities for same FULL SKU (base + lot)
                consolidated_items[normalized_sku]['qty'] += qty
                # Keep first price found (should be same for same SKU)
                if consolidated_items[normalized_sku]['price'] == 0 and unit_price_cents:
                    consolidated_items[normalized_sku]['price'] = unit_price_cents
                # Keep original SKU for tracking
                if not consolidated_items[normalized_sku]['original_sku']:
                    consolidated_items[normalized_sku]['original_sku'] = sku
            
            # FIX: Create ONE ShipStation order with ALL SKUs as line items
            if consolidated_items:
                # Build line items array with ALL SKUs
                line_items = []
                total_amount = 0
                all_skus = []
                
                for full_sku, item_data in consolidated_items.items():
                    qty = item_data['qty']
                    unit_price_cents = item_data['price']
                    
                    # Extract base_sku ONLY for product_name lookup (keep full SKU for shipment)
                    base_sku = full_sku.split(' - ')[0].strip() if ' - ' in full_sku else full_sku
                    product_name = product_name_map.get(base_sku, f'Product {base_sku}')
                    
                    line_items.append({
                        'sku': full_sku,  # Use FULL SKU with lot (already normalized)
                        'name': product_name,
                        'quantity': qty,
                        'unitPrice': (unit_price_cents / 100) if unit_price_cents else 0
                    })
                    
                    total_amount += (unit_price_cents * qty / 100) if unit_price_cents else 0
                    all_skus.append(base_sku)
                
                # Create SINGLE ShipStation order with ALL line items
                shipstation_order = {
                    'orderNumber': order_number,
                    'orderDate': order_date.isoformat() if order_date else None,
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
                WHERE failure_reason = %s
            """, (run_id,))
            
            reverted = cursor.rowcount
            conn.commit()
            # Note: Keep connection open - function will exit cleanly with return 0
            
            logger.info(f'Aborted upload: Reverted {reverted} orders from run {run_id} back to pending due to API failure')
            return 0
        
        # FIX 4: Create map of existing orders by order_number with base SKUs (5-digit)
        existing_order_map = {}
        for o in existing_orders:
            order_num = o.get('orderNumber', '').strip().upper()
            order_id = o.get('orderId')
            order_key = o.get('orderKey')
            
            # Extract base SKUs (first 5 chars) from line items
            base_skus = set()
            items = o.get('items', [])
            for item in items:
                item_sku = item.get('sku', '')
                if item_sku:
                    base_sku = item_sku[:5]  # First 5 digits only
                    base_skus.add(base_sku)
            
            # Verification logging: Warn if no items in response
            if len(items) == 0:
                logger.warning(f"Order {order_num} has no items in ShipStation API response - potential API issue")
            else:
                logger.debug(f"Order {order_num}: {len(items)} items, base SKUs: {base_skus}")
            
            existing_order_map[order_num] = {
                'orderId': order_id,
                'orderKey': order_key,
                'base_skus': base_skus  # NEW: Set of 5-digit base SKUs
            }
        
        # Filter out duplicates based on (order_number + base_sku) combination
        new_orders = []
        new_order_sku_map = []
        skipped_count = 0
        
        for idx, order in enumerate(shipstation_orders):
            order_num_upper = order['orderNumber'].strip().upper()
            order_sku_info = order_sku_map[idx]
            
            # Extract base SKUs from this new order (first 5 chars)
            new_order_base_skus = set()
            for item in order['items']:
                item_sku = item.get('sku', '')
                if item_sku:
                    base_sku = item_sku[:5]  # First 5 digits only
                    new_order_base_skus.add(base_sku)
            
            # Check if order_number exists in ShipStation
            if order_num_upper in existing_order_map:
                existing = existing_order_map[order_num_upper]
                existing_base_skus = existing.get('base_skus', set())
                
                # Check if ANY base SKU overlaps (order + SKU combination exists)
                if new_order_base_skus.intersection(existing_base_skus):
                    # DUPLICATE: Same order number + same base SKU exists
                    skipped_count += 1
                    shipstation_id = existing['orderId'] or existing['orderKey']
                    
                    logger.warning(f"Skipped duplicate: Order {order_num_upper} + SKU(s) {new_order_base_skus} already exists in ShipStation")
                    
                    # Track all SKUs for this order
                    all_skus = order_sku_info['sku'].split('|')
                    for sku in all_skus:
                        cursor.execute("""
                            INSERT INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (order_inbox_id, sku) DO NOTHING
                        """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                    
                    # Update from 'processing' to 'awaiting_shipment' (clear run_id)
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET status = 'awaiting_shipment',
                            shipstation_order_id = %s,
                            failure_reason = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (shipstation_id, order_sku_info['order_inbox_id']))
                else:
                    # DIFFERENT SKUs - allow upload (rare edge case: same order, different products)
                    logger.info(f"Order {order_num_upper} exists but with different SKUs ({existing_base_skus} vs {new_order_base_skus}) - allowing upload")
                    new_orders.append(order)
                    new_order_sku_map.append(order_sku_info)
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
                            INSERT INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (order_inbox_id, sku) DO NOTHING
                        """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                    
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET shipstation_order_id = %s
                        WHERE id = %s AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
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
                            failure_reason = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (error_details, order_sku_info['order_inbox_id']))
        
        # Update successfully uploaded orders from THIS RUN ONLY (clear run_id from failure_reason)
        cursor.execute("""
            UPDATE orders_inbox
            SET status = 'awaiting_shipment',
                failure_reason = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'processing'
              AND failure_reason = %s
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
                  AND failure_reason = %s
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
    """Main loop with efficient change detection (Phase 1 optimized polling)"""
    
    # Get config
    enabled = get_feature_flag('fast_polling_enabled', 'true') == 'true'
    interval = int(get_feature_flag('fast_polling_interval', '300'))
    
    logger.info(f"🚀 Upload workflow started (fast_polling={enabled}, interval={interval}s)")
    
    last_count = 0
    error_count = 0
    
    while True:
        try:
            # Check workflow control
            if not is_workflow_enabled('shipstation-upload'):
                logger.debug("Workflow disabled - sleeping 60s")
                time.sleep(60)
                continue
            
            # Preflight check (if fast polling enabled)
            if enabled:
                has_orders, count, duration = has_pending_orders_fast()
                
                if not has_orders:
                    # Throttle logging - only log state changes
                    if last_count > 0:
                        logger.info("✅ Upload queue empty")
                        update_polling_state(0)
                    last_count = 0
                    time.sleep(interval)
                    continue
                
                # Log only if count changed
                if count != last_count:
                    logger.info(f"📤 Processing {count} pending orders")
                
                update_polling_state(count)
                last_count = count
            
            # Run existing upload logic (all safeguards preserved)
            uploaded_count = upload_pending_orders()
            
            # ONLY update timestamp when we actually uploaded something
            if uploaded_count > 0:
                update_workflow_last_run('shipstation-upload')
            
            error_count = 0
            
            time.sleep(interval if enabled else UPLOAD_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Scheduled upload stopped by user")
            break
        except Exception as e:
            error_count += 1
            logger.error(f"❌ Upload error: {e}", exc_info=True)
            
            # Exponential backoff with max 5 min
            backoff = min(60 * error_count, 300)
            logger.info(f"Backing off {backoff}s after error #{error_count}")
            time.sleep(backoff)

if __name__ == '__main__':
    run_scheduled_upload()

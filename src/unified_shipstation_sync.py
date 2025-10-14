#!/usr/bin/env python3
"""
Unified ShipStation Sync Service

Consolidates manual order sync and status sync into a single watermark-based workflow.
Runs every 5 minutes to efficiently sync both new manual orders and status updates.

Key Features:
- Single watermark-based incremental sync (no duplicate API calls)
- Detects NEW manual orders and imports them
- Updates status for EXISTING orders (shipped, cancelled, etc.)
- Captures carrier/service information for shipping validation
- Comprehensive logging at every decision point
- Idempotent and transactionally safe
"""

import sys
import os
import logging
import datetime
import time
from typing import List, Dict, Any, Tuple

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import SHIPSTATION_ORDERS_ENDPOINT
from utils.logging_config import setup_logging
from src.services.database.db_utils import execute_query, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

# Logging setup with comprehensive output
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'unified_shipstation_sync.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)

# Configuration
KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']
SYNC_INTERVAL_SECONDS = 300  # 5 minutes
WORKFLOW_NAME = 'unified-shipstation-sync'


def get_last_sync_timestamp() -> str:
    """
    Get the last sync timestamp from watermark table.
    If no watermark exists, defaults to 14 days ago (per architect recommendation).
    """
    try:
        rows = execute_query("""
            SELECT last_sync_timestamp 
            FROM sync_watermark 
            WHERE workflow_name = ?
        """, (WORKFLOW_NAME,))
        
        if rows and rows[0]:
            timestamp = rows[0][0]
            logger.info(f"📍 Retrieved watermark: {timestamp}")
            return timestamp
        else:
            # Default to 14 days ago (architect recommendation for seeding)
            default_timestamp = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%SZ')
            logger.warning(f"⚠️ No watermark found - seeding with 14-day lookback: {default_timestamp}")
            return default_timestamp
            
    except Exception as e:
        logger.error(f"❌ Error getting watermark: {e}", exc_info=True)
        # Fallback to 14 days
        return (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%SZ')


def update_sync_watermark(new_timestamp: str, conn):
    """
    Update the watermark with the latest sync timestamp.
    CRITICAL: Must be called within same transaction as order processing (per architect).
    
    Args:
        new_timestamp: New watermark timestamp
        conn: Database connection (transaction context)
    """
    try:
        conn.execute("""
            INSERT INTO sync_watermark (workflow_name, last_sync_timestamp)
            VALUES (?, ?)
            ON CONFLICT(workflow_name) DO UPDATE SET
                last_sync_timestamp = excluded.last_sync_timestamp,
                updated_at = CURRENT_TIMESTAMP
        """, (WORKFLOW_NAME, new_timestamp))
        logger.info(f"✅ Updated watermark to: {new_timestamp}")
    except Exception as e:
        logger.error(f"❌ Error updating watermark: {e}", exc_info=True)
        raise  # Re-raise to rollback transaction


def fetch_shipstation_orders_since_watermark(api_key: str, api_secret: str, modify_date_start: str) -> List[Dict[Any, Any]]:
    """
    Fetch orders from ShipStation modified since the watermark timestamp.
    Uses pagination to retrieve all matching orders.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    
    params = {
        'modifyDateStart': modify_date_start,
        'page': 1,
        'pageSize': 500
    }
    
    try:
        logger.info(f"🔄 Fetching ShipStation orders modified since {modify_date_start}")
        fetch_start = datetime.datetime.now()
        
        while True:
            response = make_api_request(
                url=SHIPSTATION_ORDERS_ENDPOINT,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response and response.status_code == 200:
                data = response.json()
                orders_on_page = data.get('orders', [])
                all_orders.extend(orders_on_page)
                
                total_pages = data.get('pages', 1)
                current_page = data.get('page', 1)
                
                logger.info(f"📄 Page {current_page}/{total_pages}: {len(orders_on_page)} orders")
                
                if current_page >= total_pages:
                    break
                else:
                    params['page'] += 1
            else:
                logger.error(f"❌ API fetch failed. Status: {response.status_code if response else 'N/A'}")
                break
        
        fetch_elapsed = (datetime.datetime.now() - fetch_start).total_seconds()
        logger.info(f"✅ Retrieved {len(all_orders)} total orders from ShipStation in {fetch_elapsed:.1f}s")
        return all_orders
                
    except Exception as e:
        logger.error(f"❌ Error fetching orders: {e}", exc_info=True)
        return []


def is_order_from_local_system(shipstation_order_id: str) -> bool:
    """
    Check if an order originated from our local system by looking in shipstation_order_line_items.
    Returns True if order was uploaded by us, False if it's a manual ShipStation order.
    """
    try:
        rows = execute_query("""
            SELECT 1 FROM shipstation_order_line_items
            WHERE shipstation_order_id = ?
            LIMIT 1
        """, (str(shipstation_order_id),))
        
        return len(rows) > 0
        
    except Exception as e:
        logger.error(f"❌ Error checking order origin: {e}", exc_info=True)
        return False


def has_key_product_skus(order: Dict[Any, Any]) -> bool:
    """Check if order contains any key product SKUs"""
    items = order.get('items', [])
    for item in items:
        sku = str(item.get('sku', '')).strip()
        for key_sku in KEY_PRODUCT_SKUS:
            if sku.startswith(key_sku):
                return True
    return False


def order_exists_locally(order_number: str, conn) -> Tuple[bool, int]:
    """
    Check if order already exists in local database.
    Returns (exists, order_id) tuple.
    
    Args:
        order_number: Order number to check
        conn: Database connection (transaction context)
    """
    try:
        rows = conn.execute("""
            SELECT id FROM orders_inbox WHERE order_number = ?
        """, (order_number,)).fetchall()
        
        if rows and rows[0]:
            return True, rows[0][0]
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Error checking order existence: {e}", exc_info=True)
        return False, None


def extract_carrier_service_info(order: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Extract carrier and service information from ShipStation order.
    Returns dict with carrier_code, carrier_id, service_code, service_name, tracking_number.
    """
    carrier_code = order.get('carrierCode')
    service_code = order.get('serviceCode')
    tracking_number = order.get('trackingNumber')
    
    # Try multiple locations for carrier_id (ShipStation structure varies)
    carrier_id = None
    advanced_options = order.get('advancedOptions', {})
    if advanced_options and isinstance(advanced_options, dict):
        carrier_id = (advanced_options.get('billToMyOtherAccount') or 
                     advanced_options.get('carrierId'))
    if not carrier_id:
        carrier_id = order.get('carrierId')
    
    # Map service codes to human-readable names
    service_name = None
    if service_code:
        service_name_map = {
            'fedex_2day': 'FedEx 2Day',
            'fedex_international_ground': 'FedEx International Ground',
            'fedex_ground': 'FedEx Ground',
            'fedex_home_delivery': 'FedEx Home Delivery',
            'fedex_express_saver': 'FedEx Express Saver',
            'fedex_standard_overnight': 'FedEx Standard Overnight'
        }
        service_name = service_name_map.get(service_code, service_code.replace('_', ' ').title())
    
    return {
        'carrier_code': carrier_code,
        'carrier_id': carrier_id,
        'service_code': service_code,
        'service_name': service_name,
        'tracking_number': tracking_number
    }


def import_new_manual_order(order: Dict[Any, Any], conn) -> bool:
    """
    Import a NEW manual ShipStation order into the local database.
    Creates entries in orders_inbox, order_items_inbox, and potentially shipped_orders/shipped_items.
    
    Args:
        order: ShipStation order dict
        conn: Database connection (transaction context)
    
    Returns:
        True if successfully imported, False otherwise
    """
    try:
        order_id = order.get('orderId') or order.get('orderKey')
        order_number = order.get('orderNumber', '').strip()
        order_status = order.get('orderStatus', '').lower()
        customer_email = order.get('customerEmail', '')
        
        if not order_number:
            logger.warning(f"⚠️ Skipping order without order_number: {order_id}")
            return False
        
        # Extract carrier/service info
        carrier_info = extract_carrier_service_info(order)
        
        # Extract shipping address
        ship_to = order.get('shipTo') or {}
        ship_name = (ship_to.get('name') or '').strip() or None
        ship_company = (ship_to.get('company') or '').strip() or None
        ship_street1 = (ship_to.get('street1') or '').strip() or None
        ship_city = (ship_to.get('city') or '').strip() or None
        ship_state = (ship_to.get('state') or '').strip() or None
        ship_postal_code = (ship_to.get('postalCode') or '').strip() or None
        ship_country = (ship_to.get('country') or '').strip() or None
        ship_phone = (ship_to.get('phone') or '').strip() or None
        
        # Extract billing address
        bill_to = order.get('billTo') or {}
        bill_name = (bill_to.get('name') or '').strip() or None
        bill_company = (bill_to.get('company') or '').strip() or None
        bill_street1 = (bill_to.get('street1') or '').strip() or None
        bill_city = (bill_to.get('city') or '').strip() or None
        bill_state = (bill_to.get('state') or '').strip() or None
        bill_postal_code = (bill_to.get('postalCode') or '').strip() or None
        bill_country = (bill_to.get('country') or '').strip() or None
        bill_phone = (bill_to.get('phone') or '').strip() or None
        
        # Map ShipStation status to database status
        status_mapping = {
            'awaiting_payment': 'awaiting_payment',
            'awaiting_shipment': 'pending',
            'shipped': 'shipped',
            'on_hold': 'on_hold',
            'cancelled': 'cancelled'
        }
        db_status = status_mapping.get(order_status, 'synced_manual')
        
        # Parse order date
        order_date_str = order.get('orderDate', '')
        try:
            order_date = datetime.datetime.strptime(order_date_str[:10], '%Y-%m-%d').date()
        except:
            order_date = datetime.date.today()
        
        # Get order items
        items = order.get('items', [])
        total_items = sum(item.get('quantity', 0) for item in items)
        
        # Calculate total amount (in cents)
        total_amount = order.get('orderTotal', 0)
        total_amount_cents = int(float(total_amount) * 100) if total_amount else 0
        
        # Insert new order
        logger.info(f"📥 Importing NEW manual order: {order_number} (status: {db_status}, items: {total_items})")
        
        cursor = conn.execute("""
            INSERT INTO orders_inbox (
                order_number, order_date, customer_email, status, shipstation_order_id,
                total_items, total_amount_cents,
                ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone,
                shipping_carrier_code, shipping_carrier_id, shipping_service_code, shipping_service_name,
                source_system
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ShipStation Manual')
        """, (
            order_number, order_date, customer_email, db_status, str(order_id), total_items, total_amount_cents,
            ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
            bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone,
            carrier_info['carrier_code'], carrier_info['carrier_id'], 
            carrier_info['service_code'], carrier_info['service_name']
        ))
        order_inbox_id = cursor.lastrowid
        
        # Insert items into order_items_inbox
        for item in items:
            sku_raw = str(item.get('sku', '')).strip()
            quantity = item.get('quantity', 0)
            unit_price = item.get('unitPrice', 0)
            unit_price_cents = int(float(unit_price) * 100) if unit_price else 0
            
            if sku_raw and quantity > 0:
                # Parse SKU - LOT format (e.g., "17612 - 250237")
                if ' - ' in sku_raw:
                    sku_parts = sku_raw.split(' - ')
                    base_sku = sku_parts[0].strip()
                    sku_lot = sku_raw  # Store full "17612 - 250237" format
                else:
                    base_sku = sku_raw
                    sku_lot = None
                
                conn.execute("""
                    INSERT INTO order_items_inbox (
                        order_inbox_id, sku, sku_lot, quantity, unit_price_cents
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (order_inbox_id, base_sku, sku_lot, quantity, unit_price_cents))
                
                logger.debug(f"  ➕ Item: {sku_raw} x{quantity}")
        
        # If order is shipped, also create entries in shipped_orders and shipped_items
        if order_status == 'shipped':
            ship_date_str = order.get('shipDate', order_date_str)
            try:
                ship_date = datetime.datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
            except:
                ship_date = order_date
            
            conn.execute("""
                INSERT INTO shipped_orders (ship_date, order_number, shipstation_order_id)
                VALUES (?, ?, ?)
            """, (ship_date, order_number, str(order_id)))
            
            # Insert into shipped_items
            for item in items:
                sku = str(item.get('sku', '')).strip()
                quantity = item.get('quantity', 0)
                
                if sku and quantity > 0:
                    # Parse SKU - LOT format
                    if ' - ' in sku:
                        sku_parts = sku.split(' - ')
                        base_sku = sku_parts[0].strip()
                        sku_lot = sku  # Store full format
                    else:
                        base_sku = sku
                        sku_lot = sku
                    
                    conn.execute("""
                        INSERT INTO shipped_items (
                            ship_date, sku_lot, base_sku, quantity_shipped, order_number
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (ship_date, sku_lot, base_sku, quantity, order_number))
            
            logger.info(f"✅ Imported SHIPPED manual order: {order_number} (ship_date: {ship_date})")
        else:
            logger.info(f"✅ Imported AWAITING manual order: {order_number}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error importing order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
        return False


def update_existing_order_status(order: Dict[Any, Any], local_order_id: int, conn) -> bool:
    """
    Update status for an EXISTING order in the database.
    Updates carrier/service info and tracking number.
    
    Args:
        order: ShipStation order dict
        local_order_id: Local database order ID
        conn: Database connection (transaction context)
    
    Returns:
        True if successfully updated, False otherwise
    """
    try:
        order_number = order.get('orderNumber', '').strip()
        order_status = order.get('orderStatus', '').lower()
        
        # Extract carrier/service info
        carrier_info = extract_carrier_service_info(order)
        
        # Map ShipStation status to database status
        status_mapping = {
            'awaiting_payment': 'awaiting_payment',
            'awaiting_shipment': 'awaiting_shipment',
            'shipped': 'shipped',
            'on_hold': 'on_hold',
            'cancelled': 'cancelled'
        }
        db_status = status_mapping.get(order_status, order_status)
        
        logger.info(f"🔄 Updating EXISTING order: {order_number} → status: {db_status}, carrier: {carrier_info['carrier_code']}, service: {carrier_info['service_code']}")
        
        # Update order in orders_inbox
        conn.execute("""
            UPDATE orders_inbox
            SET status = ?,
                shipping_carrier_code = ?,
                shipping_carrier_id = ?,
                shipping_service_code = ?,
                shipping_service_name = ?,
                tracking_number = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            db_status,
            carrier_info['carrier_code'],
            carrier_info['carrier_id'],
            carrier_info['service_code'],
            carrier_info['service_name'],
            carrier_info['tracking_number'],
            local_order_id
        ))
        
        logger.info(f"✅ Updated order {order_number} status to '{db_status}'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
        return False


def run_unified_sync():
    """
    Main unified sync function.
    Processes orders from ShipStation watermark:
    - NEW manual orders → import
    - EXISTING orders → update status
    """
    if not is_workflow_enabled(WORKFLOW_NAME):
        logger.info(f"⏸️ Workflow '{WORKFLOW_NAME}' is DISABLED - skipping execution")
        return
    
    update_workflow_last_run(WORKFLOW_NAME)
    logger.info("=" * 80)
    logger.info("🚀 UNIFIED SHIPSTATION SYNC STARTED")
    logger.info("=" * 80)
    
    sync_start = datetime.datetime.now()
    
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.critical("❌ Failed to get ShipStation credentials")
            return
        
        # Get last sync watermark
        last_sync = get_last_sync_timestamp()
        
        # Fetch orders modified since watermark
        orders = fetch_shipstation_orders_since_watermark(api_key, api_secret, last_sync)
        
        if not orders:
            logger.info("📭 No orders found since last sync")
            
            # Advance watermark to avoid reprocessing same empty window (per architect)
            new_watermark = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            with transaction_with_retry() as conn:
                update_sync_watermark(new_watermark, conn)
            
            elapsed = (datetime.datetime.now() - sync_start).total_seconds()
            logger.info(f"✅ Sync completed in {elapsed:.1f}s (no orders to process)")
            return
        
        logger.info(f"📦 Processing {len(orders)} orders from ShipStation")
        
        # Counters for comprehensive logging
        stats = {
            'new_manual_imported': 0,
            'existing_updated': 0,
            'skipped_local_origin': 0,
            'skipped_no_key_skus': 0,
            'skipped_not_manual': 0,
            'errors': 0
        }
        
        max_modify_date = None
        
        # Process all orders in a single transaction (per architect)
        with transaction_with_retry() as conn:
            for order in orders:
                try:
                    order_id = order.get('orderId') or order.get('orderKey')
                    order_number = order.get('orderNumber', '').strip()
                    
                    if not order_number:
                        logger.debug(f"⏭️ Skipping order without number: {order_id}")
                        continue
                    
                    # Track latest modifyDate for watermark update
                    modify_date_str = order.get('modifyDate', '')
                    if modify_date_str:
                        if max_modify_date is None or modify_date_str > max_modify_date:
                            max_modify_date = modify_date_str
                    
                    # Decision tree: NEW manual order or EXISTING order update?
                    
                    # Check if order exists locally
                    exists, local_order_id = order_exists_locally(order_number, conn)
                    
                    if exists:
                        # EXISTING ORDER → Update status
                        logger.debug(f"🔍 Order {order_number} exists locally (id: {local_order_id})")
                        if update_existing_order_status(order, local_order_id, conn):
                            stats['existing_updated'] += 1
                        else:
                            stats['errors'] += 1
                    else:
                        # POTENTIALLY NEW MANUAL ORDER → Apply filters
                        
                        # Filter 1: Must start with "10" (manual orders only)
                        if not order_number.startswith('10'):
                            logger.debug(f"⏭️ Skipping {order_number} - not manual (doesn't start with '10')")
                            stats['skipped_not_manual'] += 1
                            continue
                        
                        # Filter 2: Must NOT be from local system
                        if is_order_from_local_system(str(order_id)):
                            logger.debug(f"⏭️ Skipping {order_number} - originated from local system")
                            stats['skipped_local_origin'] += 1
                            continue
                        
                        # Filter 3: Must contain key product SKUs
                        if not has_key_product_skus(order):
                            logger.debug(f"⏭️ Skipping {order_number} - no key product SKUs")
                            stats['skipped_no_key_skus'] += 1
                            continue
                        
                        # All filters passed → Import as NEW manual order
                        if import_new_manual_order(order, conn):
                            stats['new_manual_imported'] += 1
                        else:
                            stats['errors'] += 1
                
                except Exception as e:
                    logger.error(f"❌ Error processing order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
                    stats['errors'] += 1
            
            # CRITICAL: Only update watermark if NO errors occurred (per architect)
            # This prevents data loss - failed orders will be reprocessed on next run
            if stats['errors'] == 0:
                if max_modify_date:
                    update_sync_watermark(max_modify_date, conn)
                    logger.info(f"✅ Watermark advanced (no errors)")
                else:
                    # No valid modifyDate found, advance to now
                    new_watermark = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                    update_sync_watermark(new_watermark, conn)
                    logger.info(f"✅ Watermark advanced to current time (no errors)")
            else:
                logger.warning(f"⚠️ Watermark NOT advanced due to {stats['errors']} errors - will retry on next run")
                # Rollback transaction to avoid partial commits
                raise Exception(f"Processing failed with {stats['errors']} errors - aborting transaction")
        
        # Comprehensive summary logging
        elapsed = (datetime.datetime.now() - sync_start).total_seconds()
        logger.info("=" * 80)
        logger.info("📊 SYNC SUMMARY:")
        logger.info(f"   ✅ New manual orders imported: {stats['new_manual_imported']}")
        logger.info(f"   🔄 Existing orders updated: {stats['existing_updated']}")
        logger.info(f"   ⏭️ Skipped (not manual): {stats['skipped_not_manual']}")
        logger.info(f"   ⏭️ Skipped (local origin): {stats['skipped_local_origin']}")
        logger.info(f"   ⏭️ Skipped (no key SKUs): {stats['skipped_no_key_skus']}")
        logger.info(f"   ❌ Errors: {stats['errors']}")
        logger.info(f"   ⏱️ Duration: {elapsed:.1f}s")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ FATAL ERROR in unified sync: {e}", exc_info=True)
        raise


def main():
    """Main loop - runs every 5 minutes"""
    logger.info(f"🚀 Starting Unified ShipStation Sync (every {SYNC_INTERVAL_SECONDS}s)")
    
    while True:
        try:
            run_unified_sync()
            logger.info(f"😴 Next sync in {SYNC_INTERVAL_SECONDS} seconds")
            time.sleep(SYNC_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("⛔ Unified sync stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Error in sync loop: {e}", exc_info=True)
            logger.info(f"🔁 Retrying in {SYNC_INTERVAL_SECONDS} seconds")
            time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()

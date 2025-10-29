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
from src.services.database import execute_query, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from src.services.shipstation.tracking_service import (
    is_business_hours,
    should_track_order,
    fetch_tracking_status,
    update_order_tracking_status,
    map_carrier_to_code
)
from src.services.ghost_order_backfill import backfill_ghost_orders
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
            WHERE workflow_name = %s
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
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_watermark (workflow_name, last_sync_timestamp)
            VALUES (%s, %s)
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
            WHERE shipstation_order_id = %s
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


def fetch_shipments_batch(api_key: str, api_secret: str, start_date: str, end_date: str) -> List[Dict[Any, Any]]:
    """
    Fetch shipments from ShipStation for a date range.
    Uses the /shipments endpoint which contains tracking numbers.
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        start_date: Start date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        end_date: End date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
    
    Returns:
        List of shipment dictionaries
    """
    try:
        from src.services.shipstation.api_client import get_shipstation_headers
        
        headers = get_shipstation_headers(api_key, api_secret)
        shipments_endpoint = "https://ssapi.shipstation.com/shipments"
        
        params = {
            'createDateStart': start_date,
            'createDateEnd': end_date,
            'pageSize': 500  # Max allowed by API
        }
        
        all_shipments = []
        page = 1
        
        while True:
            params['page'] = page
            
            logger.debug(f"🚢 Fetching shipments page {page} (date range: {start_date} to {end_date})")
            
            response = make_api_request(
                url=shipments_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if not response or response.status_code != 200:
                logger.warning(f"⚠️ No response from shipments endpoint (page {page})")
                break
            
            # Parse JSON response
            data = response.json()
            shipments = data.get('shipments', [])
            
            if not shipments:
                logger.debug(f"📭 No more shipments on page {page}")
                break
            
            all_shipments.extend(shipments)
            logger.debug(f"📦 Retrieved {len(shipments)} shipments from page {page}")
            
            # Check if there are more pages
            total_pages = data.get('pages', 1)
            if page >= total_pages:
                break
            
            page += 1
        
        logger.info(f"✅ Retrieved {len(all_shipments)} total shipments")
        return all_shipments
        
    except Exception as e:
        logger.error(f"❌ Error fetching shipments: {e}", exc_info=True)
        return []


def update_tracking_numbers(shipments: List[Dict[Any, Any]], conn) -> int:
    """
    Update tracking numbers in orders_inbox based on shipment data.
    Matches shipments to orders by order_number.
    
    Args:
        shipments: List of shipment dictionaries from ShipStation
        conn: Database connection (transaction context)
    
    Returns:
        Number of orders updated with tracking numbers
    """
    if not shipments:
        return 0
    
    try:
        cursor = conn.cursor()
        updated_count = 0
        
        for shipment in shipments:
            order_number = shipment.get('orderNumber', '').strip()
            tracking_number = shipment.get('trackingNumber', '').strip()
            
            if not order_number or not tracking_number:
                continue
            
            # Update tracking number for this order
            # SAFETY: Only update orders with synced ShipStation ID
            cursor.execute("""
                UPDATE orders_inbox
                SET tracking_number = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_number = %s
                  AND (tracking_number IS NULL OR tracking_number = '')
                  AND shipstation_order_id IS NOT NULL
            """, (tracking_number, order_number))
            
            if cursor.rowcount > 0:
                updated_count += 1
                logger.debug(f"📍 Updated tracking for order {order_number}: {tracking_number}")
        
        if updated_count > 0:
            logger.info(f"✅ Updated {updated_count} orders with tracking numbers")
        
        return updated_count
        
    except Exception as e:
        logger.error(f"❌ Error updating tracking numbers: {e}", exc_info=True)
        return 0


def order_exists_locally(order_number: str, conn) -> Tuple[bool, int, str]:
    """
    Check if order already exists in local database.
    Returns (exists, order_id, shipstation_order_id) tuple.
    
    Args:
        order_number: Order number to check
        conn: Database connection (transaction context)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, shipstation_order_id FROM orders_inbox WHERE order_number = %s
        """, (order_number,))
        rows = cursor.fetchall()
        
        if rows and rows[0]:
            return True, rows[0][0], rows[0][1]
        return False, None, None
        
    except Exception as e:
        logger.error(f"❌ Error checking order existence: {e}", exc_info=True)
        return False, None, None


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


def check_order_conflict_in_shipstation(order_number: str, current_order_id: str, api_key: str, api_secret: str) -> Tuple[bool, Any]:
    """
    Query ShipStation to check if this order number already exists with a different ShipStation ID.
    
    Returns:
        Tuple of (has_conflict, original_order_data)
    """
    try:
        from src.services.shipstation.api_client import get_shipstation_headers
        
        headers = get_shipstation_headers(api_key, api_secret)
        
        # Query ShipStation for orders with this order number
        response = make_api_request(
            url=SHIPSTATION_ORDERS_ENDPOINT,
            method='GET',
            headers=headers,
            params={'orderNumber': order_number},
            timeout=30
        )
        
        if not response or 'orders' not in response:
            logger.warning(f"⚠️ Failed to query ShipStation for order number {order_number}")
            return False, None
        
        orders = response.get('orders', [])
        
        # Check if there are other orders with the same order number but different ShipStation ID
        for existing_order in orders:
            existing_id = str(existing_order.get('orderId', ''))
            existing_status = existing_order.get('orderStatus', '').lower()
            
            # Found a different order with same number (includes cancelled orders)
            if existing_id != str(current_order_id):
                logger.warning(f"⚠️ CONFLICT: Order {order_number} already exists in ShipStation (ID: {existing_id}, status: {existing_status})")
                return True, existing_order
        
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Error checking for order conflicts in ShipStation: {e}", exc_info=True)
        return False, None


def import_new_manual_order(order: Dict[Any, Any], conn, api_key: str, api_secret: str) -> bool:
    """
    Import a NEW manual ShipStation order into the local database.
    Creates entries in orders_inbox, order_items_inbox, and potentially shipped_orders/shipped_items.
    
    CONFLICT DETECTION: Queries ShipStation directly to check if order_number already exists
    with a different ShipStation ID (indicates duplicate manual order creation).
    
    Args:
        order: ShipStation order dict
        conn: Database connection (transaction context)
        api_key: ShipStation API key
        api_secret: ShipStation API secret
    
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
        
        # CONFLICT DETECTION: Query ShipStation to check if this order number already exists
        has_conflict, original_order = check_order_conflict_in_shipstation(order_number, order_id, api_key, api_secret)
        
        if has_conflict and original_order:
            # Order number already exists in ShipStation (shipped) - create conflict alert
            ship_date_str = original_order.get('shipDate', '')
            try:
                original_ship_date = datetime.datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date() if ship_date_str else None
            except:
                original_ship_date = None
            
            ship_to = order.get('shipTo') or {}
            customer_name = (ship_to.get('name') or '').strip() or None
            
            # Extract item details from both orders
            import json
            
            # Original order items
            original_ship_to = original_order.get('shipTo') or {}
            original_company = (original_ship_to.get('company') or '').strip() or None
            original_items = []
            for item in original_order.get('items', []):
                sku = item.get('sku', '')
                qty = item.get('quantity', 0)
                original_items.append({'sku': sku, 'quantity': qty})
            
            # Duplicate order items
            duplicate_ship_to = order.get('shipTo') or {}
            duplicate_company = (duplicate_ship_to.get('company') or '').strip() or None
            duplicate_items = []
            for item in order.get('items', []):
                sku = item.get('sku', '')
                qty = item.get('quantity', 0)
                duplicate_items.append({'sku': sku, 'quantity': qty})
            
            logger.warning(f"⚠️ CONFLICT DETECTED: Order {order_number} already exists in ShipStation as shipped")
            
            # Check if conflict already exists to avoid duplicates
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM manual_order_conflicts 
                WHERE shipstation_order_id = %s AND resolution_status = 'pending'
            """, (str(order_id),))
            
            if not cursor.fetchone():
                # Create new conflict alert with detailed information
                cursor.execute("""
                    INSERT INTO manual_order_conflicts (
                        conflicting_order_number, shipstation_order_id, customer_name, original_ship_date,
                        original_company, original_items, duplicate_company, duplicate_items
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (order_number, str(order_id), customer_name, original_ship_date,
                      original_company, json.dumps(original_items), duplicate_company, json.dumps(duplicate_items)))
                logger.info(f"🚨 Created conflict alert for order {order_number}")
            else:
                logger.debug(f"  Conflict alert already exists for order {order_number}")
            
            return False  # Do not import the order
        
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
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders_inbox (
                order_number, order_date, customer_email, status, shipstation_order_id,
                total_items, total_amount_cents,
                ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone,
                shipping_carrier_code, shipping_carrier_id, shipping_service_code, shipping_service_name,
                source_system
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ShipStation Manual')
            RETURNING id
        """, (
            order_number, order_date, customer_email, db_status, str(order_id), total_items, total_amount_cents,
            ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
            bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone,
            carrier_info['carrier_code'], carrier_info['carrier_id'], 
            carrier_info['service_code'], carrier_info['service_name']
        ))
        order_inbox_id = cursor.fetchone()[0]
        
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
                
                cursor.execute("""
                    INSERT INTO order_items_inbox (
                        order_inbox_id, sku, sku_lot, quantity, unit_price_cents
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (order_inbox_id, base_sku, sku_lot, quantity, unit_price_cents))
                
                logger.debug(f"  ➕ Item: {sku_raw} x{quantity}")
        
        # If order is shipped, also create entries in shipped_orders and shipped_items
        if order_status == 'shipped':
            ship_date_str = order.get('shipDate', order_date_str)
            try:
                ship_date = datetime.datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
            except:
                ship_date = order_date
            
            cursor.execute("""
                INSERT INTO shipped_orders (ship_date, order_number, shipstation_order_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (order_number) DO UPDATE 
                SET ship_date = EXCLUDED.ship_date,
                    shipstation_order_id = EXCLUDED.shipstation_order_id
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
                    
                    cursor.execute("""
                        INSERT INTO shipped_items (
                            ship_date, sku_lot, base_sku, quantity_shipped, order_number
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (order_number, base_sku, sku_lot) DO UPDATE
                        SET quantity_shipped = EXCLUDED.quantity_shipped,
                            ship_date = EXCLUDED.ship_date
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
    Updates carrier/service info, tracking number, AND order items (edge case fix).
    
    Edge Case: Orders created before items are added (e.g., from XML without items).
    This function keeps trying to update items until they appear in ShipStation.
    
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
        
        # Get order items from ShipStation
        items = order.get('items', [])
        total_items = sum(item.get('quantity', 0) for item in items)
        
        logger.info(f"🔄 Updating EXISTING order: {order_number} → status: {db_status}, items: {total_items}, carrier: {carrier_info['carrier_code']}, service: {carrier_info['service_code']}")
        
        # Update order in orders_inbox
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders_inbox
            SET status = %s,
                shipping_carrier_code = %s,
                shipping_carrier_id = %s,
                shipping_service_code = %s,
                shipping_service_name = %s,
                tracking_number = %s,
                total_items = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            db_status,
            carrier_info['carrier_code'],
            carrier_info['carrier_id'],
            carrier_info['service_code'],
            carrier_info['service_name'],
            carrier_info['tracking_number'],
            total_items,
            local_order_id
        ))
        
        # EDGE CASE FIX: Update/add order items if they exist in ShipStation
        # This handles the case where orders are created before items are added
        if items:
            # Check if order already has items
            cursor.execute("""
                SELECT COUNT(*) FROM order_items_inbox WHERE order_inbox_id = %s
            """, (local_order_id,))
            existing_items_count = cursor.fetchone()[0]
            
            if existing_items_count == 0:
                logger.info(f"📦 Adding {len(items)} items to order {order_number} (was empty)")
                
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
                        
                        cursor.execute("""
                            INSERT INTO order_items_inbox (
                                order_inbox_id, sku, sku_lot, quantity, unit_price_cents
                            )
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (order_inbox_id, sku) DO UPDATE
                            SET quantity = EXCLUDED.quantity,
                                sku_lot = EXCLUDED.sku_lot,
                                unit_price_cents = EXCLUDED.unit_price_cents
                        """, (local_order_id, base_sku, sku_lot, quantity, unit_price_cents))
                        
                        logger.debug(f"  ➕ Item: {sku_raw} x{quantity}")
        
        logger.info(f"✅ Updated order {order_number} status to '{db_status}'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
        return False


def sync_tracking_statuses(conn, api_key: str, api_secret: str) -> int:
    """
    Fetch and update tracking statuses for active (non-delivered) orders.
    Only runs during business hours (6 AM Pacific to 5 PM Eastern).
    
    Args:
        conn: Database connection (transaction context)
        api_key: ShipStation API key
        api_secret: ShipStation API secret
    
    Returns:
        int: Number of tracking statuses updated
    """
    cursor = conn.cursor()
    
    # Get orders that need tracking status updates
    # Rules:
    # - Has tracking number
    # - Status NOT 'delivered' (or NULL)
    # - Last checked > 5 minutes ago (or never checked)
    cursor.execute("""
        SELECT 
            order_number, 
            tracking_number, 
            shipping_carrier_code, 
            tracking_status,
            tracking_last_checked
        FROM orders_inbox
        WHERE tracking_number IS NOT NULL
          AND tracking_number != ''
          AND (tracking_status IS NULL OR tracking_status != 'DE')
          AND (tracking_last_checked IS NULL 
               OR tracking_last_checked < NOW() - INTERVAL '5 minutes')
        ORDER BY tracking_last_checked NULLS FIRST
        LIMIT 50
    """)
    
    orders_to_check = cursor.fetchall()
    
    if not orders_to_check:
        logger.debug("📭 No orders need tracking status updates")
        return 0
    
    logger.info(f"🔍 Checking tracking status for {len(orders_to_check)} orders...")
    
    updated = 0
    for order_number, tracking_number, carrier, current_status, last_checked in orders_to_check:
        try:
            # Handle multiple tracking numbers (comma-separated)
            tracking_nums = [t.strip() for t in tracking_number.split(',')]
            primary_tracking = tracking_nums[0]
            
            # Map carrier to code
            carrier_code = map_carrier_to_code(carrier) if carrier else 'fedex'
            
            # Fetch status from ShipStation
            tracking_data = fetch_tracking_status(primary_tracking, carrier_code, api_key, api_secret)
            
            if tracking_data.get('success'):
                # Update database
                update_order_tracking_status(order_number, tracking_data, conn)
                updated += 1
                
                # Log status changes
                new_status = tracking_data.get('status_code')
                if new_status != current_status:
                    logger.info(f"📊 Order {order_number}: {current_status or 'NEW'} → {new_status}")
                    
                    # Alert on exceptions
                    if new_status == 'EX':
                        exception_desc = tracking_data.get('exception_description', 'Unknown exception')
                        logger.warning(f"⚠️ EXCEPTION for order {order_number}: {exception_desc}")
            else:
                error_msg = tracking_data.get('error', 'Unknown error')
                logger.warning(f"⚠️ Failed to fetch tracking for {order_number}: {error_msg}")
                
                # Still update last_checked timestamp even on failure
                # SAFETY: Only update orders with synced ShipStation ID
                cursor.execute("""
                    UPDATE orders_inbox
                    SET tracking_last_checked = NOW()
                    WHERE order_number = %s
                      AND shipstation_order_id IS NOT NULL
                """, (order_number,))
                
        except Exception as e:
            logger.error(f"❌ Failed to update tracking for {order_number}: {e}", exc_info=True)
            
            # CRITICAL: Update last_checked even on exception to prevent retry storm
            # SAFETY: Only update orders with synced ShipStation ID
            try:
                cursor.execute("""
                    UPDATE orders_inbox
                    SET tracking_last_checked = NOW()
                    WHERE order_number = %s
                      AND shipstation_order_id IS NOT NULL
                """, (order_number,))
            except:
                pass  # If this fails, let it fail silently to avoid cascading errors
            continue
    
    logger.info(f"✅ Updated tracking status for {updated}/{len(orders_to_check)} orders")
    return updated


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
            cursor = conn.cursor()
            
            for idx, order in enumerate(orders):
                savepoint_name = f"sp_order_{idx}"
                
                try:
                    # PostgreSQL SAVEPOINT: Isolate this order's operations
                    # If this order fails, we can rollback to this point without aborting the whole transaction
                    cursor.execute(f"SAVEPOINT {savepoint_name}")
                    
                    order_id = order.get('orderId') or order.get('orderKey')
                    order_number = order.get('orderNumber', '').strip()
                    
                    if not order_number:
                        logger.debug(f"⏭️ Skipping order without number: {order_id}")
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                        continue
                    
                    # Track latest modifyDate for watermark update
                    modify_date_str = order.get('modifyDate', '')
                    if modify_date_str:
                        if max_modify_date is None or modify_date_str > max_modify_date:
                            max_modify_date = modify_date_str
                    
                    # Decision tree: NEW manual order, EXISTING order update, or CONFLICT?
                    
                    # Check if order exists locally
                    exists, local_order_id, local_shipstation_id = order_exists_locally(order_number, conn)
                    
                    if exists:
                        # Order number exists - but is it the SAME ShipStation order?
                        current_shipstation_id = str(order_id)
                        
                        if local_shipstation_id and str(local_shipstation_id) == current_shipstation_id:
                            # SAME ORDER (same number + same ShipStation ID) → Update status
                            logger.debug(f"🔍 Order {order_number} exists locally (id: {local_order_id})")
                            if update_existing_order_status(order, local_order_id, conn):
                                stats['existing_updated'] += 1
                            else:
                                stats['errors'] += 1
                        else:
                            # CONFLICT! Same order number but DIFFERENT ShipStation ID
                            logger.warning(f"⚠️ MANUAL ORDER CONFLICT: Order {order_number} exists with different ShipStation ID")
                            logger.warning(f"   Local ShipStation ID: {local_shipstation_id}, New ShipStation ID: {current_shipstation_id}")
                            
                            # Create manual order conflict alert
                            cursor = conn.cursor()
                            
                            # Get original order details from local database
                            cursor.execute("""
                                SELECT ship_name, created_at 
                                FROM orders_inbox 
                                WHERE id = %s
                            """, (local_order_id,))
                            original_data = cursor.fetchone()
                            original_ship_name = original_data[0] if original_data else None
                            original_created_at = original_data[1] if original_data else None
                            
                            # Get items from both orders
                            import json
                            
                            # Original order items (from local DB)
                            cursor.execute("""
                                SELECT sku, quantity 
                                FROM order_items_inbox 
                                WHERE order_inbox_id = %s
                            """, (local_order_id,))
                            original_items = []
                            for item_row in cursor.fetchall():
                                original_items.append({'sku': item_row[0], 'quantity': item_row[1]})
                            
                            # New/duplicate order items (from ShipStation)
                            ship_to = order.get('shipTo') or {}
                            duplicate_ship_name = (ship_to.get('name') or '').strip() or None
                            duplicate_company = (ship_to.get('company') or '').strip() or None
                            duplicate_items = []
                            for item in order.get('items', []):
                                sku = item.get('sku', '')
                                qty = item.get('quantity', 0)
                                duplicate_items.append({'sku': sku, 'quantity': qty})
                            
                            # Check if conflict already exists
                            cursor.execute("""
                                SELECT id FROM manual_order_conflicts 
                                WHERE shipstation_order_id = %s AND resolution_status = 'pending'
                            """, (current_shipstation_id,))
                            
                            if not cursor.fetchone():
                                # Create new conflict alert
                                cursor.execute("""
                                    INSERT INTO manual_order_conflicts (
                                        conflicting_order_number, shipstation_order_id, customer_name, original_ship_date,
                                        original_company, original_items, duplicate_company, duplicate_items
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                """, (order_number, current_shipstation_id, duplicate_ship_name, original_created_at,
                                      None, json.dumps(original_items), duplicate_company, json.dumps(duplicate_items)))
                                logger.info(f"🚨 Created manual order conflict alert for order {order_number}")
                            else:
                                logger.debug(f"  Conflict alert already exists for order {order_number}")
                            
                            # Don't import or update this order
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                            continue
                    else:
                        # POTENTIALLY NEW MANUAL ORDER → Apply filters
                        
                        # Filter 1: Must start with "10" (manual orders only)
                        if not order_number.startswith('10'):
                            logger.debug(f"⏭️ Skipping {order_number} - not manual (doesn't start with '10')")
                            stats['skipped_not_manual'] += 1
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                            continue
                        
                        # Filter 2: Must NOT be from local system
                        if is_order_from_local_system(str(order_id)):
                            logger.debug(f"⏭️ Skipping {order_number} - originated from local system")
                            stats['skipped_local_origin'] += 1
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                            continue
                        
                        # Filter 3: Must contain key product SKUs
                        if not has_key_product_skus(order):
                            logger.debug(f"⏭️ Skipping {order_number} - no key product SKUs")
                            stats['skipped_no_key_skus'] += 1
                            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                            continue
                        
                        # All filters passed → Import as NEW manual order
                        if import_new_manual_order(order, conn, api_key, api_secret):
                            stats['new_manual_imported'] += 1
                        else:
                            stats['errors'] += 1
                    
                    # Success - release the savepoint
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                
                except Exception as e:
                    # PostgreSQL: Rollback to savepoint to keep transaction alive
                    try:
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    except:
                        pass  # If rollback fails, transaction will abort anyway
                    
                    logger.error(f"❌ Error processing order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
                    stats['errors'] += 1
            
            cursor.close()
            
            # Fetch and update tracking numbers (uses /shipments endpoint)
            # This runs AFTER order processing, within the same transaction
            try:
                logger.info("🚢 Fetching shipments to update tracking numbers...")
                
                # Use the same date range as order fetch (last_sync to now)
                shipments = fetch_shipments_batch(
                    api_key=api_key,
                    api_secret=api_secret,
                    start_date=last_sync,
                    end_date=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                )
                
                if shipments:
                    tracking_updates = update_tracking_numbers(shipments, conn)
                    stats['tracking_updates'] = tracking_updates
                else:
                    logger.info("📭 No shipments found for tracking number updates")
                    stats['tracking_updates'] = 0
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch/update tracking numbers (non-fatal): {e}")
                stats['tracking_updates'] = 0
            
            # Fetch and update tracking statuses (only during business hours)
            # This runs AFTER tracking number updates, within the same transaction
            try:
                if is_business_hours():
                    logger.info("🔍 Checking tracking statuses (business hours active)...")
                    tracking_status_updates = sync_tracking_statuses(conn, api_key, api_secret)
                    stats['tracking_status_updates'] = tracking_status_updates
                else:
                    logger.info("⏰ Outside business hours - skipping tracking status updates")
                    stats['tracking_status_updates'] = 0
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to update tracking statuses (non-fatal): {e}")
                stats['tracking_status_updates'] = 0
            
            # Backfill ghost orders (orders with 0 items)
            # This runs AFTER all sync processing, BEFORE watermark update
            # Uses per-order transactions for fault tolerance
            try:
                logger.info("👻 Checking for ghost orders (0 items)...")
                ghost_metrics = backfill_ghost_orders(conn, api_key, api_secret)
                stats['ghost_backfilled'] = ghost_metrics.get('backfilled', 0)
                stats['ghost_work_in_progress'] = ghost_metrics.get('work_in_progress', 0)
                stats['ghost_errors'] = ghost_metrics.get('errors', 0)
                
                if ghost_metrics.get('rate_limited'):
                    logger.warning("⚠️ Backfill hit rate limit - remaining orders will retry next cycle")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to backfill ghost orders (non-fatal): {e}")
                stats['ghost_backfilled'] = 0
                stats['ghost_work_in_progress'] = 0
                stats['ghost_errors'] = 0
            
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
        logger.info(f"   📍 Tracking numbers updated: {stats.get('tracking_updates', 0)}")
        logger.info(f"   🔍 Tracking statuses updated: {stats.get('tracking_status_updates', 0)}")
        logger.info(f"   👻 Ghost orders backfilled: {stats.get('ghost_backfilled', 0)}")
        logger.info(f"   ⏳ Ghost orders (WIP): {stats.get('ghost_work_in_progress', 0)}")
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

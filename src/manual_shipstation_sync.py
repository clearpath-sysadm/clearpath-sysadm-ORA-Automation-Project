# filename: src/manual_shipstation_sync.py
"""
Manual ShipStation Order Sync Service

Syncs manual orders created in ShipStation back to the local database for inventory tracking.
Runs hourly to detect and import orders that were created directly in ShipStation
(not originated from XML imports).

Key Features:
- Detects manual orders by absence in shipstation_order_line_items table
- Uses watermark-based incremental sync for efficiency
- Handles both awaiting_shipment and shipped orders
- Updates inventory for shipped orders
- Respects rate limits with exponential backoff
"""

import sys
import os
import logging
import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import SHIPSTATION_ORDERS_ENDPOINT
from utils.logging_config import setup_logging
from src.services.database.db_utils import execute_query, transaction
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

# Logging setup
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'manual_shipstation_sync.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)

# Key Product SKUs - only process these
KEY_PRODUCT_SKUS = ['17612', '17904', '17914', '18675', '18795']


def get_last_sync_timestamp() -> str:
    """Get the last sync timestamp from watermark table"""
    try:
        rows = execute_query("""
            SELECT last_sync_timestamp 
            FROM sync_watermark 
            WHERE workflow_name = 'manual_shipstation_sync'
        """)
        
        if rows and rows[0]:
            timestamp = rows[0][0]
            logger.info(f"Retrieved last sync timestamp: {timestamp}")
            return timestamp
        else:
            # Default to 30 days ago if no watermark exists
            default_timestamp = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            logger.warning(f"No watermark found, using default: {default_timestamp}")
            return default_timestamp
            
    except Exception as e:
        logger.error(f"Error getting last sync timestamp: {e}", exc_info=True)
        return (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')


def update_sync_watermark(new_timestamp: str):
    """Update the watermark with the latest sync timestamp"""
    try:
        with transaction() as conn:
            conn.execute("""
                INSERT INTO sync_watermark (workflow_name, last_sync_timestamp)
                VALUES ('manual_shipstation_sync', ?)
                ON CONFLICT(workflow_name) DO UPDATE SET
                    last_sync_timestamp = excluded.last_sync_timestamp,
                    updated_at = CURRENT_TIMESTAMP
            """, (new_timestamp,))
        logger.info(f"Updated sync watermark to: {new_timestamp}")
    except Exception as e:
        logger.error(f"Error updating sync watermark: {e}", exc_info=True)


def fetch_shipstation_orders_since_watermark(api_key: str, api_secret: str, modify_date_start: str) -> List[Dict[Any, Any]]:
    """
    Fetch orders from ShipStation modified since the watermark timestamp.
    Uses pagination to retrieve all matching orders.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    
    params = {
        'modifyDateStart': modify_date_start,
        'orderStatus': 'awaiting_shipment,shipped',
        'page': 1,
        'pageSize': 500
    }
    
    try:
        logger.info(f"Fetching ShipStation orders modified since {modify_date_start}")
        
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
                
                logger.info(f"Fetched page {current_page}/{total_pages}, {len(orders_on_page)} orders on this page")
                
                if current_page >= total_pages:
                    break
                else:
                    params['page'] += 1
            else:
                logger.error(f"Failed to fetch orders. Status: {response.status_code if response else 'N/A'}")
                break
                
    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
    
    logger.info(f"Retrieved {len(all_orders)} total orders from ShipStation")
    return all_orders


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
        logger.error(f"Error checking order origin: {e}", exc_info=True)
        return False


def has_key_product_skus(order: Dict[Any, Any]) -> bool:
    """Check if order contains any key product SKUs"""
    items = order.get('items', [])
    for item in items:
        sku = str(item.get('sku', '')).strip()
        # Check if SKU starts with any key product SKU (handles format like "17612 - 250237")
        for key_sku in KEY_PRODUCT_SKUS:
            if sku.startswith(key_sku):
                return True
    return False


def import_manual_order(order: Dict[Any, Any]) -> bool:
    """
    Import a manual ShipStation order into the local database.
    Creates entries in orders_inbox, order_items_inbox, and potentially shipped_orders/shipped_items.
    Returns True if successfully imported, False otherwise.
    """
    try:
        order_id = order.get('orderId') or order.get('orderKey')
        order_number = order.get('orderNumber', '').strip()
        order_status = order.get('orderStatus', '').lower()
        customer_email = order.get('customerEmail', '')
        
        if not order_number:
            logger.warning(f"Skipping order without order_number: {order_id}")
            return False
        
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
        
        with transaction() as conn:
            # Check if order already exists
            existing = conn.execute("""
                SELECT id FROM orders_inbox WHERE order_number = ?
            """, (order_number,)).fetchone()
            
            if existing:
                # Update existing order
                conn.execute("""
                    UPDATE orders_inbox
                    SET status = 'synced_manual',
                        shipstation_order_id = ?,
                        customer_email = ?,
                        total_items = ?,
                        total_amount_cents = ?,
                        source_system = 'ShipStation Manual',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE order_number = ?
                """, (str(order_id), customer_email, total_items, total_amount_cents, order_number))
                order_inbox_id = existing[0]
            else:
                # Insert new order
                cursor = conn.execute("""
                    INSERT INTO orders_inbox (
                        order_number, order_date, customer_email, status, shipstation_order_id,
                        total_items, total_amount_cents, source_system
                    )
                    VALUES (?, ?, ?, 'synced_manual', ?, ?, ?, 'ShipStation Manual')
                """, (
                    order_number, order_date, customer_email, str(order_id), total_items, total_amount_cents
                ))
                order_inbox_id = cursor.lastrowid
            
            # Delete existing items and re-insert (simpler than UPSERT without unique constraint)
            conn.execute("DELETE FROM order_items_inbox WHERE order_inbox_id = ?", (order_inbox_id,))
            
            # Insert items into order_items_inbox
            for item in items:
                sku = str(item.get('sku', '')).strip()
                quantity = item.get('quantity', 0)
                unit_price = item.get('unitPrice', 0)
                unit_price_cents = int(float(unit_price) * 100) if unit_price else 0
                
                if sku and quantity > 0:
                    conn.execute("""
                        INSERT INTO order_items_inbox (
                            order_inbox_id, sku, quantity, unit_price_cents
                        )
                        VALUES (?, ?, ?, ?)
                    """, (order_inbox_id, sku, quantity, unit_price_cents))
            
            # If order is shipped, also create entries in shipped_orders and shipped_items
            if order_status == 'shipped':
                ship_date_str = order.get('shipDate', order_date_str)
                try:
                    ship_date = datetime.datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
                except:
                    ship_date = order_date
                
                # Check if shipped order exists
                shipped_exists = conn.execute("""
                    SELECT 1 FROM shipped_orders WHERE order_number = ?
                """, (order_number,)).fetchone()
                
                if shipped_exists:
                    conn.execute("""
                        UPDATE shipped_orders
                        SET ship_date = ?, shipstation_order_id = ?
                        WHERE order_number = ?
                    """, (ship_date, str(order_id), order_number))
                else:
                    conn.execute("""
                        INSERT INTO shipped_orders (ship_date, order_number, shipstation_order_id, source_system)
                        VALUES (?, ?, ?, 'ShipStation Manual')
                    """, (ship_date, order_number, str(order_id)))
                
                # Delete existing shipped items and re-insert
                conn.execute("DELETE FROM shipped_items WHERE order_number = ?", (order_number,))
                
                # Insert into shipped_items
                for item in items:
                    sku = str(item.get('sku', '')).strip()
                    quantity = item.get('quantity', 0)
                    
                    if sku and quantity > 0:
                        # Parse SKU - LOT format (e.g., "17612 - 250237")
                        if ' - ' in sku:
                            sku_parts = sku.split(' - ')
                            base_sku = sku_parts[0].strip()
                            lot = sku_parts[1].strip()
                            sku_lot = f"{base_sku}-{lot}"
                        else:
                            base_sku = sku
                            sku_lot = sku
                        
                        conn.execute("""
                            INSERT INTO shipped_items (
                                ship_date, sku_lot, base_sku, quantity_shipped, order_number
                            )
                            VALUES (?, ?, ?, ?, ?)
                        """, (ship_date, sku_lot, base_sku, quantity, order_number))
                
                logger.info(f"Imported shipped order {order_number} (ShipStation ID: {order_id})")
            else:
                logger.info(f"Imported awaiting order {order_number} (ShipStation ID: {order_id})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error importing order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
        return False


def run_manual_order_sync():
    """
    Main sync function that pulls manual orders from ShipStation and imports them.
    """
    logger.info("=== Starting Manual ShipStation Order Sync ===")
    
    workflow_start_time = datetime.datetime.now()
    
    try:
        # Initialize workflow tracking
        with transaction() as conn:
            conn.execute("""
                INSERT INTO workflows (name, display_name, status, last_run_at)
                VALUES ('manual_shipstation_sync', 'Manual ShipStation Sync', 'running', CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    status = 'running',
                    last_run_at = CURRENT_TIMESTAMP
            """)
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.critical("Failed to get ShipStation credentials")
            return "Failed to get credentials", 500
        
        # Get last sync watermark
        last_sync = get_last_sync_timestamp()
        
        # Fetch orders modified since watermark
        orders = fetch_shipstation_orders_since_watermark(api_key, api_secret, last_sync)
        
        if not orders:
            logger.info("No orders found since last sync")
            
            # Advance watermark to avoid reprocessing same empty window
            new_watermark = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            update_sync_watermark(new_watermark)
            
            # Update workflow status
            with transaction() as conn:
                conn.execute("""
                    UPDATE workflows 
                    SET status = 'completed',
                        records_processed = 0,
                        duration_seconds = ?
                    WHERE name = 'manual_shipstation_sync'
                """, (int((datetime.datetime.now() - workflow_start_time).total_seconds()),))
            
            return "No orders to sync", 200
        
        # Filter to manual orders (not originated from our system) and containing key products
        manual_orders = []
        for order in orders:
            order_id = order.get('orderId') or order.get('orderKey')
            
            # Skip if order came from our system
            if is_order_from_local_system(str(order_id)):
                logger.debug(f"Skipping order {order.get('orderNumber')} - originated from local system")
                continue
            
            # Skip if order doesn't contain key product SKUs
            if not has_key_product_skus(order):
                logger.debug(f"Skipping order {order.get('orderNumber')} - no key product SKUs")
                continue
            
            manual_orders.append(order)
        
        logger.info(f"Found {len(manual_orders)} manual orders to import (out of {len(orders)} total)")
        
        # Import each manual order and track success/failure
        imported_count = 0
        failed_count = 0
        max_modify_date = None
        
        for order in manual_orders:
            try:
                if import_manual_order(order):
                    imported_count += 1
                    # Track the latest modifyDate from successfully imported orders
                    modify_date_str = order.get('modifyDate', '')
                    if modify_date_str:
                        if max_modify_date is None or modify_date_str > max_modify_date:
                            max_modify_date = modify_date_str
                else:
                    failed_count += 1
                    logger.warning(f"Failed to import order {order.get('orderNumber', 'UNKNOWN')}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Exception importing order {order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
        
        logger.info(f"Successfully imported {imported_count} manual orders, {failed_count} failed")
        
        # Only update watermark if we successfully imported orders
        # Use the max modifyDate from successful imports, or current time if no imports
        if imported_count > 0 and max_modify_date:
            update_sync_watermark(max_modify_date)
            logger.info(f"Updated watermark to max successful modifyDate: {max_modify_date}")
        elif imported_count == 0 and failed_count == 0:
            # No orders to process - advance watermark to now to avoid reprocessing same empty set
            new_watermark = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            update_sync_watermark(new_watermark)
            logger.info(f"No orders to import - advanced watermark to: {new_watermark}")
        else:
            # Some orders failed - DO NOT advance watermark so we retry on next run
            logger.warning(f"Watermark NOT advanced due to {failed_count} failures - will retry on next run")
        
        # Update workflow status
        duration = (datetime.datetime.now() - workflow_start_time).total_seconds()
        with transaction() as conn:
            conn.execute("""
                UPDATE workflows 
                SET status = 'completed',
                    records_processed = ?,
                    duration_seconds = ?
                WHERE name = 'manual_shipstation_sync'
            """, (imported_count, int(duration)))
        
        logger.info(f"=== Manual Order Sync Completed in {duration:.2f}s ===")
        return f"Successfully synced {imported_count} manual orders", 200
        
    except Exception as e:
        logger.error(f"Fatal error in manual order sync: {e}", exc_info=True)
        
        # Update workflow status to failed
        try:
            with transaction() as conn:
                conn.execute("""
                    UPDATE workflows 
                    SET status = 'failed'
                    WHERE name = 'manual_shipstation_sync'
                """)
        except:
            pass
        
        return f"Sync failed: {str(e)}", 500


if __name__ == "__main__":
    run_manual_order_sync()

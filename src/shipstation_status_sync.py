#!/usr/bin/env python3
"""
ShipStation Status Sync Service

Syncs status updates for orders that were uploaded to ShipStation from the local system.
Checks orders awaiting shipment for status changes (shipped, cancelled, etc.) and updates local database.

Key Features:
- Queries orders with status='awaiting_shipment' that have shipstation_order_id
- Fetches current status from ShipStation by order ID
- Updates local status and moves shipped orders to shipped_orders/shipped_items tables
- Handles cancelled, on_hold, and other status transitions
- Runs hourly via scheduled workflow
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
log_file = os.path.join(log_dir, 'shipstation_status_sync.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def get_orders_needing_status_check() -> List[Dict[str, Any]]:
    """
    Get all orders from local DB that need status checking.
    Returns orders with shipstation_order_id that need sync (uploaded, awaiting_shipment, pending).
    """
    try:
        rows = execute_query("""
            SELECT 
                id,
                order_number,
                shipstation_order_id,
                status,
                order_date
            FROM orders_inbox
            WHERE shipstation_order_id IS NOT NULL
              AND shipstation_order_id != ''
              AND status IN ('uploaded', 'awaiting_shipment', 'pending')
            ORDER BY order_date DESC
        """)
        
        orders = []
        for row in rows:
            orders.append({
                'id': row[0],
                'order_number': row[1],
                'shipstation_order_id': row[2],
                'local_status': row[3],
                'order_date': row[4]
            })
        
        logger.info(f"Found {len(orders)} orders needing status check")
        return orders
        
    except Exception as e:
        logger.error(f"Error getting orders for status check: {e}", exc_info=True)
        return []


def fetch_orders_batch_from_shipstation(api_key: str, api_secret: str, shipstation_order_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch multiple orders from ShipStation in a single batch call.
    Returns dict mapping shipstation_order_id -> order data.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    
    if not shipstation_order_ids:
        return {}
    
    # Build orderIds comma-separated list for batch query
    order_ids_str = ','.join(str(oid) for oid in shipstation_order_ids)
    
    params = {
        'orderIds': order_ids_str,
        'page': 1,
        'pageSize': 500  # Fetch up to 500 orders at once
    }
    
    try:
        response = make_api_request(
            url=SHIPSTATION_ORDERS_ENDPOINT,
            method='GET',
            headers=headers,
            params=params,
            timeout=60
        )
        
        if response and response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            
            # Build lookup map: shipstation_order_id -> order data
            orders_map = {}
            for order in orders:
                order_id = str(order.get('orderId', ''))
                if order_id:
                    orders_map[order_id] = order
            
            logger.info(f"Batch fetched {len(orders_map)}/{len(shipstation_order_ids)} orders from ShipStation")
            return orders_map
        
        logger.warning(f"Batch fetch failed with status {response.status_code if response else 'None'}")
        return {}
        
    except Exception as e:
        logger.error(f"Error batch fetching orders from ShipStation: {e}", exc_info=True)
        return {}


def update_order_status(local_order: Dict[str, Any], shipstation_order: Dict[str, Any]) -> bool:
    """
    Update local database with current status from ShipStation.
    Handles: shipped → move to shipped_orders, cancelled → update status, etc.
    Also captures carrier/service information for validation.
    """
    try:
        order_id = local_order['id']
        order_number = local_order['order_number']
        local_status = local_order['local_status']
        
        ss_status = shipstation_order.get('orderStatus', '').lower()
        ss_order_id = shipstation_order.get('orderId')
        
        # Extract carrier and service information for validation
        carrier_code = shipstation_order.get('carrierCode')
        service_code = shipstation_order.get('serviceCode')
        
        # Try multiple locations for carrier_id (ShipStation structure varies)
        carrier_id = None
        advanced_options = shipstation_order.get('advancedOptions', {})
        if advanced_options and isinstance(advanced_options, dict):
            # Try billToMyOtherAccount first (FedEx account ID), then carrierId
            carrier_id = (advanced_options.get('billToMyOtherAccount') or 
                         advanced_options.get('carrierId'))
        if not carrier_id:
            carrier_id = shipstation_order.get('carrierId')
        
        # Get human-readable service name if available
        service_name = None
        if service_code:
            # Map common service codes to names
            service_name_map = {
                'fedex_2day': 'FedEx 2Day',
                'fedex_international_ground': 'FedEx International Ground',
                'fedex_ground': 'FedEx Ground',
                'fedex_home_delivery': 'FedEx Home Delivery',
                'fedex_express_saver': 'FedEx Express Saver',
                'fedex_standard_overnight': 'FedEx Standard Overnight'
            }
            service_name = service_name_map.get(service_code, service_code.replace('_', ' ').title())
        
        logger.info(f"Syncing order {order_number}: local='{local_status}' → ShipStation='{ss_status}' (carrier: {carrier_code}, service: {service_code}, carrier_id: {carrier_id})")
        
        with transaction() as conn:
            if ss_status == 'shipped':
                # Order has been shipped - update status in orders_inbox (keep it there)
                conn.execute("""
                    UPDATE orders_inbox
                    SET status = 'shipped',
                        shipping_carrier_code = ?,
                        shipping_carrier_id = ?,
                        shipping_service_code = ?,
                        shipping_service_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (carrier_code, carrier_id, service_code, service_name, order_id))
                
                logger.info(f"✅ Updated order {order_number} status to 'shipped'")
                
            elif ss_status == 'cancelled':
                # Order was cancelled (also capture carrier info even though cancelled)
                conn.execute("""
                    UPDATE orders_inbox
                    SET status = 'cancelled',
                        shipping_carrier_code = ?,
                        shipping_carrier_id = ?,
                        shipping_service_code = ?,
                        shipping_service_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (carrier_code, carrier_id, service_code, service_name, order_id))
                
                logger.info(f"✅ Marked order {order_number} as cancelled")
                
            elif ss_status == 'awaiting_shipment':
                # Still waiting to ship - capture carrier info for validation
                conn.execute("""
                    UPDATE orders_inbox
                    SET status = 'awaiting_shipment',
                        shipping_carrier_code = ?,
                        shipping_carrier_id = ?,
                        shipping_service_code = ?,
                        shipping_service_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (carrier_code, carrier_id, service_code, service_name, order_id))
                
                logger.debug(f"Order {order_number} still awaiting shipment")
                
            elif ss_status in ('on_hold', 'awaiting_payment'):
                # Order is on hold or awaiting payment (also capture carrier info)
                conn.execute("""
                    UPDATE orders_inbox
                    SET status = ?,
                        shipping_carrier_code = ?,
                        shipping_carrier_id = ?,
                        shipping_service_code = ?,
                        shipping_service_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (ss_status, carrier_code, carrier_id, service_code, service_name, order_id))
                
                logger.info(f"✅ Updated order {order_number} to status '{ss_status}'")
            
            else:
                # Unknown status - log it
                logger.warning(f"Unknown ShipStation status '{ss_status}' for order {order_number}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating order {local_order['order_number']}: {e}", exc_info=True)
        return False


def run_status_sync() -> tuple[Dict[str, Any], int]:
    """
    Main function to run status sync.
    Returns (result_dict, status_code) for API compatibility.
    """
    start_time = datetime.datetime.now()
    logger.info("=== Starting ShipStation Status Sync ===")
    
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error("ShipStation credentials not found")
            return {"error": "Missing credentials"}, 500
        
        # Get orders needing status check
        orders = get_orders_needing_status_check()
        
        if not orders:
            logger.info("No orders need status checking")
            return {"message": "No orders to sync"}, 200
        
        # Batch fetch all orders from ShipStation at once
        shipstation_order_ids = [order['shipstation_order_id'] for order in orders]
        shipstation_orders_map = fetch_orders_batch_from_shipstation(api_key, api_secret, shipstation_order_ids)
        
        # Update each order with data from batch fetch
        updated_count = 0
        shipped_count = 0
        cancelled_count = 0
        error_count = 0
        
        for local_order in orders:
            ss_order_id = local_order['shipstation_order_id']
            shipstation_order = shipstation_orders_map.get(ss_order_id)
            
            if shipstation_order:
                success = update_order_status(local_order, shipstation_order)
                if success:
                    updated_count += 1
                    ss_status = shipstation_order.get('orderStatus', '').lower()
                    if ss_status == 'shipped':
                        shipped_count += 1
                    elif ss_status == 'cancelled':
                        cancelled_count += 1
                else:
                    error_count += 1
            else:
                logger.warning(f"Could not find order {local_order['order_number']} in batch fetch")
                error_count += 1
        
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        
        result = {
            "message": f"Status sync complete: {updated_count} orders updated",
            "checked": len(orders),
            "updated": updated_count,
            "shipped": shipped_count,
            "cancelled": cancelled_count,
            "errors": error_count,
            "elapsed_seconds": round(elapsed, 2)
        }
        
        logger.info(f"=== Status Sync Completed in {elapsed:.2f}s ===")
        logger.info(f"Summary: {updated_count} updated ({shipped_count} shipped, {cancelled_count} cancelled), {error_count} errors")
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error in status sync: {e}", exc_info=True)
        return {"error": str(e)}, 500


if __name__ == '__main__':
    result, status = run_status_sync()
    print(f"Result: {result}")
    print(f"Status: {status}")

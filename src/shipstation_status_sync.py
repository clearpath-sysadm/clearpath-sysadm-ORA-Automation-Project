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
from src.services.database.db_utils import execute_query, transaction, transaction_with_retry
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

# Logging setup
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'shipstation_status_sync.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def fetch_orders_from_shipstation_by_date(api_key: str, api_secret: str, days_back: int = 4) -> List[Dict[str, Any]]:
    """
    Fetch orders from ShipStation modified in the last N days.
    Returns list of order data from ShipStation API.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    
    # Calculate date range (last 4 days)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    params = {
        'modifyDateStart': start_date.strftime('%Y-%m-%dT00:00:00'),
        'modifyDateEnd': end_date.strftime('%Y-%m-%dT23:59:59'),
        'page': 1,
        'pageSize': 500
    }
    
    all_orders = []
    
    try:
        while True:
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
                all_orders.extend(orders)
                
                # Check if there are more pages
                total_pages = data.get('pages', 1)
                current_page = params['page']
                
                if current_page < total_pages:
                    params['page'] += 1
                else:
                    break
            else:
                logger.warning(f"Failed to fetch orders: status {response.status_code if response else 'None'}")
                break
        
        logger.info(f"Fetched {len(all_orders)} orders from ShipStation (last {days_back} days)")
        return all_orders
        
    except Exception as e:
        logger.error(f"Error fetching orders from ShipStation: {e}", exc_info=True)
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


def update_order_status(local_order: Dict[str, Any], shipstation_order: Dict[str, Any], conn=None) -> bool:
    """
    Update local database with current status from ShipStation.
    Handles: shipped → move to shipped_orders, cancelled → update status, etc.
    Also captures carrier/service information for validation.
    
    Args:
        local_order: Local order data from database
        shipstation_order: Order data from ShipStation API
        conn: Optional database connection (for batch operations)
    """
    def _do_update(conn):
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
    
    try:
        # Execute update with provided connection or create new transaction
        if conn is not None:
            return _do_update(conn)
        else:
            with transaction() as new_conn:
                return _do_update(new_conn)
    except Exception as e:
        logger.error(f"Error updating order {local_order['order_number']}: {e}", exc_info=True)
        return False


def sync_order_from_shipstation(shipstation_order: Dict[str, Any], conn=None) -> bool:
    """
    Sync a single order from ShipStation to local database.
    Updates order in orders_inbox with current ShipStation data.
    
    Args:
        shipstation_order: Order data from ShipStation API
        conn: Optional database connection (for batch operations)
    """
    def _do_sync(conn):
        order_id = shipstation_order.get('orderId')
        order_number = shipstation_order.get('orderNumber', '').strip()
        order_status = shipstation_order.get('orderStatus', '').lower()
        
        if not order_number:
            return False
        
        # Extract carrier and service information
        carrier_code = shipstation_order.get('carrierCode')
        service_code = shipstation_order.get('serviceCode')
        
        carrier_id = None
        advanced_options = shipstation_order.get('advancedOptions', {})
        if advanced_options and isinstance(advanced_options, dict):
            carrier_id = (advanced_options.get('billToMyOtherAccount') or 
                         advanced_options.get('carrierId'))
        if not carrier_id:
            carrier_id = shipstation_order.get('carrierId')
        
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
        
        # Check if order exists
        existing = conn.execute("""
            SELECT id FROM orders_inbox WHERE order_number = ?
        """, (order_number,)).fetchone()
        
        if existing:
            # Update existing order with current ShipStation data
            conn.execute("""
                UPDATE orders_inbox
                SET status = ?,
                    shipstation_order_id = ?,
                    shipping_carrier_code = ?,
                    shipping_carrier_id = ?,
                    shipping_service_code = ?,
                    shipping_service_name = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_number = ?
            """, (order_status, str(order_id), carrier_code, carrier_id, 
                  service_code, service_name, order_number))
        
        return True
    
    try:
        # Execute sync with provided connection or create new transaction
        if conn is not None:
            return _do_sync(conn)
        else:
            with transaction() as new_conn:
                return _do_sync(new_conn)
    except Exception as e:
        logger.error(f"Error syncing order {shipstation_order.get('orderNumber', 'UNKNOWN')}: {e}", exc_info=True)
        return False


def batch_update_orders_status(status_buckets: Dict[str, List[tuple]], conn) -> Dict[str, int]:
    """
    Batch update orders by status using executemany for efficiency.
    
    Args:
        status_buckets: Dict mapping status -> list of (order_id, carrier_code, carrier_id, service_code, service_name) tuples
        conn: Database connection
    
    Returns:
        Dict with counts per status
    """
    counts = {}
    
    # Batch update for 'shipped' status
    if 'shipped' in status_buckets and status_buckets['shipped']:
        conn.executemany("""
            UPDATE orders_inbox
            SET status = 'shipped',
                shipping_carrier_code = ?,
                shipping_carrier_id = ?,
                shipping_service_code = ?,
                shipping_service_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [(carrier_code, carrier_id, service_code, service_name, order_id) 
              for order_id, carrier_code, carrier_id, service_code, service_name in status_buckets['shipped']])
        counts['shipped'] = len(status_buckets['shipped'])
        logger.info(f"✅ Batch updated {counts['shipped']} shipped orders")
    
    # Batch update for 'cancelled' status
    if 'cancelled' in status_buckets and status_buckets['cancelled']:
        conn.executemany("""
            UPDATE orders_inbox
            SET status = 'cancelled',
                shipping_carrier_code = ?,
                shipping_carrier_id = ?,
                shipping_service_code = ?,
                shipping_service_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [(carrier_code, carrier_id, service_code, service_name, order_id)
              for order_id, carrier_code, carrier_id, service_code, service_name in status_buckets['cancelled']])
        counts['cancelled'] = len(status_buckets['cancelled'])
        logger.info(f"✅ Batch updated {counts['cancelled']} cancelled orders")
    
    # Batch update for 'awaiting_shipment' status
    if 'awaiting_shipment' in status_buckets and status_buckets['awaiting_shipment']:
        conn.executemany("""
            UPDATE orders_inbox
            SET status = 'awaiting_shipment',
                shipping_carrier_code = ?,
                shipping_carrier_id = ?,
                shipping_service_code = ?,
                shipping_service_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [(carrier_code, carrier_id, service_code, service_name, order_id)
              for order_id, carrier_code, carrier_id, service_code, service_name in status_buckets['awaiting_shipment']])
        counts['awaiting_shipment'] = len(status_buckets['awaiting_shipment'])
        logger.debug(f"Batch updated {counts['awaiting_shipment']} awaiting_shipment orders")
    
    # Batch update for 'on_hold' and 'awaiting_payment' statuses
    for status in ['on_hold', 'awaiting_payment']:
        if status in status_buckets and status_buckets[status]:
            conn.executemany("""
                UPDATE orders_inbox
                SET status = ?,
                    shipping_carrier_code = ?,
                    shipping_carrier_id = ?,
                    shipping_service_code = ?,
                    shipping_service_name = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, [(status, carrier_code, carrier_id, service_code, service_name, order_id)
                  for order_id, carrier_code, carrier_id, service_code, service_name in status_buckets[status]])
            counts[status] = len(status_buckets[status])
            logger.info(f"✅ Batch updated {counts[status]} {status} orders")
    
    return counts


def run_status_sync() -> tuple[Dict[str, Any], int]:
    """
    Main function to sync orders from ShipStation (last 7 days).
    Fetches orders and updates local database with current ShipStation data.
    Uses batched updates for efficiency (instead of individual UPDATE statements).
    """
    start_time = datetime.datetime.now()
    logger.info("=== Starting ShipStation Status Sync (7-day window) ===")
    
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error("ShipStation credentials not found")
            return {"error": "Missing credentials"}, 500
        
        # Fetch orders from ShipStation (last 7 days)
        shipstation_orders = fetch_orders_from_shipstation_by_date(api_key, api_secret, days_back=7)
        
        if not shipstation_orders:
            logger.info("No orders found in ShipStation (last 7 days)")
            return {"message": "No orders to sync"}, 200
        
        # Build lookup of local orders
        local_orders_map = {}
        local_orders = execute_query("""
            SELECT id, order_number, shipstation_order_id, status as local_status
            FROM orders_inbox
            WHERE shipstation_order_id IS NOT NULL
        """)
        
        for order in local_orders:
            ss_id = str(order[2])
            if ss_id:
                local_orders_map[ss_id] = {
                    'id': order[0],
                    'order_number': order[1],
                    'shipstation_order_id': ss_id,
                    'local_status': order[3]
                }
        
        # Group orders by status for batch updates
        status_buckets = {
            'shipped': [],
            'cancelled': [],
            'awaiting_shipment': [],
            'on_hold': [],
            'awaiting_payment': []
        }
        
        skipped_count = 0
        
        for ss_order in shipstation_orders:
            ss_order_id = str(ss_order.get('orderId', ''))
            ss_status = ss_order.get('orderStatus', '').lower()
            
            if ss_order_id not in local_orders_map:
                skipped_count += 1
                continue
            
            local_order = local_orders_map[ss_order_id]
            order_id = local_order['id']
            
            # Extract carrier/service info
            carrier_code = ss_order.get('carrierCode')
            service_code = ss_order.get('serviceCode')
            
            carrier_id = None
            advanced_options = ss_order.get('advancedOptions', {})
            if advanced_options and isinstance(advanced_options, dict):
                carrier_id = (advanced_options.get('billToMyOtherAccount') or 
                             advanced_options.get('carrierId'))
            if not carrier_id:
                carrier_id = ss_order.get('carrierId')
            
            # Map service code to name
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
            
            # Add to appropriate status bucket
            if ss_status in status_buckets:
                status_buckets[ss_status].append((order_id, carrier_code, carrier_id, service_code, service_name))
        
        # Execute batched updates in single transaction
        logger.info(f"Batching updates: {sum(len(v) for v in status_buckets.values())} orders, {skipped_count} skipped")
        
        with transaction_with_retry() as conn:
            batch_counts = batch_update_orders_status(status_buckets, conn)
        
        total_updated = sum(batch_counts.values())
        shipped_count = batch_counts.get('shipped', 0)
        cancelled_count = batch_counts.get('cancelled', 0)
        
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        
        result = {
            "message": f"Status sync complete: {total_updated} orders synced",
            "fetched": len(shipstation_orders),
            "updated": total_updated,
            "shipped": shipped_count,
            "cancelled": cancelled_count,
            "errors": 0,
            "elapsed_seconds": round(elapsed, 2)
        }
        
        logger.info(f"=== Status Sync Completed in {elapsed:.2f}s ===")
        logger.info(f"Summary: {total_updated} synced ({shipped_count} shipped, {cancelled_count} cancelled), 0 errors")
        
        # Auto-refresh ShipStation metrics to prevent stale cache
        if total_updated > 0:
            try:
                from src.services.shipstation.metrics_refresher import refresh_shipstation_metrics
                refresh_shipstation_metrics()
                logger.info("ShipStation metrics refreshed after status sync")
            except Exception as refresh_error:
                logger.warning(f"Failed to refresh ShipStation metrics: {refresh_error}")
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error in status sync: {e}", exc_info=True)
        return {"error": str(e)}, 500


if __name__ == '__main__':
    result, status = run_status_sync()
    print(f"Result: {result}")
    print(f"Status: {status}")

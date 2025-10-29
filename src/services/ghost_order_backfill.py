#!/usr/bin/env python3
"""
Ghost Order Backfill Service

Detects and fixes "ghost orders" - orders that exist in orders_inbox but have
zero items in order_items_inbox. This occurs when orders are manually created
in ShipStation and synced to the local database without their line items.

Key Features:
- Per-order transaction isolation for fault tolerance
- Rate limit detection and immediate stop behavior
- Work-in-progress order detection (0 items in ShipStation)
- Comprehensive error handling and logging
- Idempotent ON CONFLICT handling
"""

import logging
from typing import Dict, Any, List, Tuple
from collections import Counter

from src.services.database.pg_utils import transaction
from src.services.shipstation.api_client import get_shipstation_credentials
from utils.api_utils import make_api_request

logger = logging.getLogger(__name__)


def backfill_ghost_orders(read_conn, api_key: str = None, api_secret: str = None) -> Dict[str, Any]:
    """
    Detect and fix ghost orders by backfilling items from ShipStation.
    
    Uses per-order transaction isolation for fault tolerance.
    Stops immediately on rate limit (429) to preserve API quota.
    
    Args:
        read_conn: Database connection for read-only detection query
        api_key: ShipStation API key (optional, uses environment if not provided)
        api_secret: ShipStation API secret (optional, uses environment if not provided)
    
    Returns:
        dict: Metrics about backfill operation
            - ghost_orders_found: Number of ghost orders detected
            - backfilled: Number successfully backfilled with items
            - cancelled: Number marked as cancelled (404 errors)
            - work_in_progress: Number with 0 items in ShipStation
            - errors: Number of API/database errors
            - rate_limited: Boolean, True if 429 encountered
    
    Transaction Strategy:
        - Detection query uses read_conn (read-only)
        - Each order backfill uses new transaction (write isolation)
        - Failures in one order don't affect others
    """
    # Initialize metrics
    metrics = {
        'ghost_orders_found': 0,
        'backfilled': 0,
        'cancelled': 0,
        'work_in_progress': 0,
        'errors': 0,
        'rate_limited': False
    }
    
    # Get ShipStation credentials
    if not api_key or not api_secret:
        api_key, api_secret = get_shipstation_credentials()
    
    try:
        # Detect ghost orders (read-only query)
        ghost_orders = _detect_ghost_orders(read_conn)
        metrics['ghost_orders_found'] = len(ghost_orders)
        
        if metrics['ghost_orders_found'] == 0:
            logger.info("👻 No ghost orders found - all orders have items")
            return metrics
        
        logger.info(f"👻 Found {metrics['ghost_orders_found']} ghost orders with 0 items")
        
        # Process each ghost order in isolated transaction
        for order_id, order_number, shipstation_order_id in ghost_orders:
            try:
                # Fetch order details from ShipStation
                order_data = _fetch_order_from_shipstation(
                    shipstation_order_id, 
                    api_key, 
                    api_secret
                )
                
                # Check for rate limit
                if order_data.get('rate_limited'):
                    metrics['rate_limited'] = True
                    logger.warning(f"⚠️ Hit rate limit (429) - stopping backfill, will retry next cycle")
                    break
                
                # Check for 404 (order not found)
                if order_data.get('not_found'):
                    _mark_order_cancelled(order_id, order_number, "Order not found in ShipStation (404)")
                    metrics['cancelled'] += 1
                    logger.warning(f"⚠️ Order {order_number} not found in ShipStation (404) - marked as cancelled")
                    continue
                
                # Check for API errors
                if order_data.get('error'):
                    metrics['errors'] += 1
                    logger.error(f"❌ Error fetching order {order_number}: {order_data['error']}")
                    continue
                
                # Extract items
                items = order_data.get('items', [])
                status = order_data.get('status', 'awaiting_shipment')
                
                # Check for work-in-progress (0 items)
                if len(items) == 0:
                    metrics['work_in_progress'] += 1
                    logger.warning(f"⚠️ Order {order_number} has 0 items in ShipStation - may be work-in-progress")
                    continue
                
                # Check for duplicate SKUs (constraint violation risk)
                skus = [item.get('sku', '') for item in items if item.get('sku')]
                sku_counts = Counter(skus)
                duplicates = {sku: count for sku, count in sku_counts.items() if count > 1}
                
                if duplicates:
                    logger.critical(
                        f"🚨 CRITICAL: Order {order_number} has duplicate SKUs - constraint violation risk! "
                        f"Duplicates: {duplicates}"
                    )
                    metrics['errors'] += 1
                    continue
                
                # Backfill items in isolated transaction
                success = _backfill_order_items(
                    order_id, 
                    order_number, 
                    items, 
                    status
                )
                
                if success:
                    metrics['backfilled'] += 1
                    logger.info(
                        f"✅ Backfilled order {order_number}: {len(items)} items, status: {status}"
                    )
                else:
                    metrics['errors'] += 1
                    
            except Exception as e:
                metrics['errors'] += 1
                logger.error(f"❌ Error processing ghost order {order_number}: {e}", exc_info=True)
                continue
        
        # Log summary
        logger.info(
            f"👻 Ghost order backfill complete: {metrics['backfilled']} fixed, "
            f"{metrics['work_in_progress']} WIP, {metrics['errors']} errors"
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Fatal error in ghost order backfill: {e}", exc_info=True)
        metrics['errors'] += 1
        return metrics


def _detect_ghost_orders(conn) -> List[Tuple[int, str, str]]:
    """
    Detect ghost orders (orders with 0 items).
    
    Returns:
        List of tuples: (order_id, order_number, shipstation_order_id)
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.id, o.order_number, o.shipstation_order_id
        FROM orders_inbox o
        LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
        WHERE o.status NOT IN ('shipped', 'cancelled')
          AND o.shipstation_order_id IS NOT NULL
        GROUP BY o.id, o.order_number, o.shipstation_order_id
        HAVING COUNT(oi.id) = 0
    """)
    
    return cursor.fetchall()


def _fetch_order_from_shipstation(
    shipstation_order_id: str, 
    api_key: str, 
    api_secret: str
) -> Dict[str, Any]:
    """
    Fetch order details from ShipStation API.
    
    Returns:
        dict with keys: items, status, rate_limited, not_found, error
    """
    try:
        from src.services.shipstation.api_client import get_shipstation_headers
        
        url = f"https://ssapi.shipstation.com/orders/{shipstation_order_id}"
        headers = get_shipstation_headers(api_key, api_secret)
        
        response = make_api_request(
            url=url,
            method='GET',
            headers=headers,
            timeout=10
        )
        
        if not response:
            return {'error': 'No response from ShipStation API'}
        
        # Handle rate limit (429)
        if response.status_code == 429:
            return {'rate_limited': True}
        
        # Handle not found (404)
        if response.status_code == 404:
            return {'not_found': True}
        
        # Handle server errors (500)
        if response.status_code >= 500:
            return {'error': f'ShipStation server error: {response.status_code}'}
        
        # Handle success (200)
        if response.status_code == 200:
            data = response.json()
            return {
                'items': data.get('items', []),
                'status': data.get('orderStatus', 'awaiting_shipment')
            }
        
        # Handle other errors
        return {'error': f'Unexpected status code: {response.status_code}'}
        
    except Exception as e:
        return {'error': str(e)}


def _backfill_order_items(
    order_id: int, 
    order_number: str, 
    items: List[Dict[str, Any]], 
    status: str
) -> bool:
    """
    Backfill items for a ghost order in isolated transaction.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Insert items with ON CONFLICT handling
            for item in items:
                sku = item.get('sku', '')
                quantity = item.get('quantity', 0)
                unit_price = item.get('unitPrice', 0.0)
                unit_price_cents = int(float(unit_price) * 100)
                
                cursor.execute("""
                    INSERT INTO order_items_inbox 
                    (order_inbox_id, sku, quantity, unit_price_cents)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (order_inbox_id, sku) 
                    DO UPDATE SET 
                        quantity = EXCLUDED.quantity,
                        unit_price_cents = EXCLUDED.unit_price_cents
                """, (order_id, sku, quantity, unit_price_cents))
            
            # Update order metadata
            total_items = len(items)
            cursor.execute("""
                UPDATE orders_inbox
                SET total_items = %s,
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (total_items, status, order_id))
            
            # Transaction auto-commits on context exit
            return True
            
    except Exception as e:
        logger.error(f"❌ Database error backfilling order {order_number}: {e}", exc_info=True)
        return False


def _mark_order_cancelled(order_id: int, order_number: str, reason: str) -> bool:
    """
    Mark a ghost order as cancelled (orphaned order).
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders_inbox
                SET status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (order_id,))
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error marking order {order_number} as cancelled: {e}", exc_info=True)
        return False

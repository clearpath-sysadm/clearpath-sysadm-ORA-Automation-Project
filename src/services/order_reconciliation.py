#!/usr/bin/env python3
"""
Order Reconciliation Service

Syncs orphaned orders in orders_inbox with their actual status in ShipStation.
This catches orders that were uploaded and shipped but never synced back to local DB,
typically due to watermark timing windows.

Usage:
- Called by EOD button to ensure all orders are properly synced
- Returns summary report of reconciled orders
"""

import logging
from typing import Dict, Optional
from requests.exceptions import HTTPError
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

logger = logging.getLogger(__name__)


def _mark_not_found(cursor, order_id, order_number, summary):
    cursor.execute("""
        UPDATE orders_inbox
        SET status = 'not_found',
            failure_reason = 'Order no longer exists in ShipStation',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (order_id,))
    summary['not_found_in_shipstation'] += 1
    summary['updated_to_not_found'] += 1
    summary['details'].append(f"⚠️ Order {order_number}: Not found in ShipStation")
    logger.warning(
        "Order %s no longer exists in ShipStation; marked not_found",
        order_number,
    )


def reconcile_orphaned_orders(
    conn,
    stale_before_hours: Optional[int] = None,
    max_orders: Optional[int] = None,
) -> Dict[str, any]:
    """
    Reconcile orders in orders_inbox with ShipStation to sync status.
    
    Checks all non-shipped/cancelled orders in local DB against ShipStation
    and updates their status to match reality.
    
    Args:
        conn: Database connection (transaction context)
    
    Returns:
        Dict with reconciliation summary:
        {
            'total_checked': int,
            'updated_to_shipped': int,
            'updated_to_cancelled': int,
            'updated_to_not_found': int,
            'updated_other': int,
            'not_found_in_shipstation': int,
            'errors': int,
            'details': List[str]
        }
    """
    cursor = conn.cursor()
    summary = {
        'total_checked': 0,
        'updated_to_shipped': 0,
        'updated_to_cancelled': 0,
        'updated_to_not_found': 0,
        'updated_other': 0,
        'not_found_in_shipstation': 0,
        'errors': 0,
        'details': []
    }
    
    try:
        # Get all orders that aren't shipped/cancelled in local DB
        query = """
            SELECT 
                o.id,
                o.order_number,
                o.status,
                o.shipstation_order_id
            FROM orders_inbox o
            WHERE o.status NOT IN ('shipped', 'cancelled', 'not_found')
        """
        params = []
        if stale_before_hours is not None:
            query += " AND o.updated_at < NOW() - (%s * INTERVAL '1 hour')"
            params.append(stale_before_hours)
        query += " ORDER BY o.updated_at ASC"
        if max_orders is not None:
            query += " LIMIT %s"
            params.append(max_orders)
        cursor.execute(query, tuple(params))
        
        orphaned_orders = cursor.fetchall()
        summary['total_checked'] = len(orphaned_orders)
        
        if not orphaned_orders:
            logger.info("✅ No orphaned orders to reconcile")
            return summary
        
        logger.info(f"🔍 Checking {len(orphaned_orders)} potentially orphaned orders against ShipStation")
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        headers = get_shipstation_headers(api_key, api_secret)
        
        # Check each order in ShipStation
        for order_id, order_number, local_status, ss_order_id in orphaned_orders:
            try:
                # Query ShipStation for this order
                if ss_order_id:
                    # Use ShipStation order ID if available
                    response = make_api_request(
                        url=f"https://ssapi.shipstation.com/orders/{ss_order_id}",
                        method='GET',
                        headers=headers,
                        timeout=10
                    )
                else:
                    # Fallback: search by order number
                    response = make_api_request(
                        url="https://ssapi.shipstation.com/orders",
                        method='GET',
                        headers=headers,
                        params={'orderNumber': order_number},
                        timeout=10
                    )
                
                if response is None or response.status_code == 404:
                    if response is not None and response.status_code == 404:
                        _mark_not_found(
                            cursor, order_id, order_number, summary
                        )
                    else:
                        summary['errors'] += 1
                        logger.error(
                            "No response while reconciling order %s",
                            order_number,
                        )
                    continue
                
                if response.status_code != 200:
                    summary['errors'] += 1
                    logger.error(f"Failed to fetch order {order_number}: Status {response.status_code}")
                    continue
                
                # Parse response
                if ss_order_id:
                    # Single order response
                    ss_order = response.json()
                else:
                    # Search response - get first match
                    data = response.json()
                    orders = data.get('orders', [])
                    if not orders:
                        _mark_not_found(
                            cursor, order_id, order_number, summary
                        )
                        continue
                    ss_order = orders[0]
                
                ss_status = ss_order.get('orderStatus', '').lower()
                status_mapping = {
                    'awaiting_payment': 'awaiting_payment',
                    'awaiting_shipment': 'pending',
                    'shipped': 'shipped',
                    'on_hold': 'on_hold',
                    'cancelled': 'cancelled',
                }
                db_status = status_mapping.get(ss_status)

                if db_status and db_status != local_status:
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET status = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (db_status, order_id))
                    if db_status == 'shipped':
                        summary['updated_to_shipped'] += 1
                    elif db_status == 'cancelled':
                        summary['updated_to_cancelled'] += 1
                    else:
                        summary['updated_other'] += 1
                    summary['details'].append(
                        f"✅ Order {order_number}: Updated to {db_status}"
                    )
                    logger.info(
                        f"✅ Reconciled order {order_number}: {local_status} → {db_status}"
                    )
                else:
                    # A successful lookup confirms the local order is still known
                    # to ShipStation. Refresh its verification timestamp so the
                    # scheduled stale-order sweep does not recheck it every run.
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (order_id,))
                
            except HTTPError as e:
                if getattr(e.response, 'status_code', None) == 404:
                    _mark_not_found(cursor, order_id, order_number, summary)
                else:
                    summary['errors'] += 1
                    logger.error(f"Error reconciling order {order_number}: {e}")
                continue
            except Exception as e:
                summary['errors'] += 1
                logger.error(f"Error reconciling order {order_number}: {e}")
                continue
        
        # Log summary
        logger.info(f"📊 Reconciliation complete: {summary['updated_to_shipped']} shipped, "
                   f"{summary['updated_to_cancelled']} cancelled, "
                   f"{summary['updated_to_not_found']} not-found status updates, "
                   f"{summary['updated_other']} other status updates, "
                   f"{summary['not_found_in_shipstation']} not found, "
                   f"{summary['errors']} errors")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error during order reconciliation: {e}", exc_info=True)
        summary['errors'] += 1
        return summary

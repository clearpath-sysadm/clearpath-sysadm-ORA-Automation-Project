#!/usr/bin/env python3
"""
ShipStation ID Backfill Script

Fetches ShipStation order IDs for historical orders in orders_inbox and shipped_orders
that are missing their shipstation_order_id. Queries ShipStation API by order number
to retrieve the IDs and updates both tables.
"""

import sys
import os
import logging
from typing import Dict, Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import SHIPSTATION_ORDERS_ENDPOINT
from utils.logging_config import setup_logging
from src.services.database.db_utils import execute_query, transaction
from src.services.shipstation.api_client import get_shipstation_credentials, fetch_shipstation_orders_by_order_numbers

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'backfill_shipstation_ids.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def backfill_shipstation_ids(batch_size=50, limit=None):
    """
    Backfill missing ShipStation IDs for shipped orders.
    
    Args:
        batch_size: Number of orders to query at once (default: 50)
        limit: Maximum number of orders to process (None = all)
    
    Returns:
        Dict with backfill results
    """
    try:
        logger.info("=== Starting ShipStation ID Backfill ===")
        
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error("ShipStation credentials not found")
            return {'error': 'Missing credentials'}
        
        query = """
            SELECT DISTINCT oi.order_number
            FROM orders_inbox oi
            WHERE oi.status = 'shipped'
              AND (oi.shipstation_order_id IS NULL OR oi.shipstation_order_id = '')
            ORDER BY oi.order_date DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = execute_query(query)
        order_numbers = [row[0] for row in rows]
        
        if not order_numbers:
            logger.info("No orders need backfill")
            return {
                'message': 'No orders need backfill',
                'processed': 0,
                'updated': 0
            }
        
        logger.info(f"Found {len(order_numbers)} orders needing backfill")
        
        updated_inbox = 0
        updated_shipped = 0
        errors = 0
        
        for i in range(0, len(order_numbers), batch_size):
            batch = order_numbers[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} orders")
            
            try:
                shipstation_orders = fetch_shipstation_orders_by_order_numbers(
                    api_key,
                    api_secret,
                    SHIPSTATION_ORDERS_ENDPOINT,
                    batch
                )
                
                logger.info(f"Found {len(shipstation_orders)} orders in ShipStation")
                
                with transaction() as conn:
                    for ss_order in shipstation_orders:
                        order_number = ss_order.get('orderNumber', '').strip()
                        order_id = ss_order.get('orderId')
                        
                        if not order_number or not order_id:
                            continue
                        
                        cursor = conn.execute("""
                            UPDATE orders_inbox
                            SET shipstation_order_id = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE order_number = ?
                              AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
                        """, (str(order_id), order_number))
                        
                        if cursor.rowcount > 0:
                            updated_inbox += cursor.rowcount
                        
                        cursor = conn.execute("""
                            UPDATE shipped_orders
                            SET shipstation_order_id = ?
                            WHERE order_number = ?
                              AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
                        """, (str(order_id), order_number))
                        
                        if cursor.rowcount > 0:
                            updated_shipped += cursor.rowcount
                
                logger.info(f"Batch complete: updated {updated_inbox} inbox, {updated_shipped} shipped records so far")
                
            except Exception as e:
                logger.error(f"Error processing batch: {e}", exc_info=True)
                errors += len(batch)
        
        result = {
            'message': f'Backfill complete: {updated_inbox} orders updated',
            'processed': len(order_numbers),
            'updated_inbox': updated_inbox,
            'updated_shipped': updated_shipped,
            'errors': errors
        }
        
        logger.info(f"=== Backfill Complete ===")
        logger.info(f"Processed: {result['processed']}, Updated inbox: {updated_inbox}, Updated shipped: {updated_shipped}, Errors: {errors}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}", exc_info=True)
        return {'error': str(e)}


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill ShipStation IDs for historical orders')
    parser.add_argument('--batch-size', type=int, default=50, help='Orders to process per batch (default: 50)')
    parser.add_argument('--limit', type=int, default=None, help='Maximum orders to process (default: all)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without updating')
    
    args = parser.parse_args()
    
    if args.dry_run:
        rows = execute_query("""
            SELECT order_number, order_date, status
            FROM orders_inbox
            WHERE status = 'shipped'
              AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
            ORDER BY order_date DESC
            LIMIT 10
        """)
        
        total_rows = execute_query("""
            SELECT COUNT(*)
            FROM orders_inbox
            WHERE status = 'shipped'
              AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
        """)
        
        total = total_rows[0][0] if total_rows else 0
        
        print(f"\n🔍 DRY RUN - Orders that would be backfilled:")
        print(f"\nSample orders:")
        for order_num, order_date, status in rows:
            print(f"  {order_num}: {order_date} ({status})")
        
        print(f"\nTotal orders to backfill: {total}")
        print("\nRun without --dry-run to perform actual backfill")
    else:
        result = backfill_shipstation_ids(
            batch_size=args.batch_size,
            limit=args.limit
        )
        
        print(f"\n{'='*60}")
        print("BACKFILL RESULTS")
        print(f"{'='*60}")
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Orders processed: {result['processed']}")
            print(f"   Inbox updated: {result['updated_inbox']}")
            print(f"   Shipped updated: {result['updated_shipped']}")
            print(f"   Errors: {result['errors']}")
        print(f"{'='*60}\n")

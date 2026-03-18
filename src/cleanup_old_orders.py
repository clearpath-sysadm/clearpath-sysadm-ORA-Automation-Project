#!/usr/bin/env python3
"""
Orders Inbox Cleanup Script

Automatically deletes orders from orders_inbox that are older than 60 days
from their order_date. This keeps the inbox clean and focused on recent orders.

Shipped orders are kept in the shipped_orders table permanently for historical reporting.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import setup_logging
from src.services.database.pg_utils import execute_query, transaction

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'cleanup_old_orders.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def cleanup_old_orders(days=60):
    """
    Delete orders from orders_inbox older than specified days.
    
    CRITICAL: Only deletes TERMINAL orders (shipped, cancelled).
    Non-terminal orders (pending, awaiting_shipment, uploaded, on_hold, failed) 
    are PRESERVED regardless of age to maintain sync with ShipStation.
    
    Args:
        days: Number of days to retain orders (default: 60)
    
    Returns:
        Dict with cleanup results
    """
    # Terminal statuses - safe to delete after retention period
    TERMINAL_STATUSES = ('shipped', 'cancelled')
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        logger.info(f"Starting cleanup of TERMINAL orders older than {days} days (before {cutoff_date})")
        logger.info(f"Terminal statuses eligible for deletion: {TERMINAL_STATUSES}")
        
        with transaction() as conn:
            cursor = conn.cursor()

            # Count orders eligible for deletion (terminal + old)
            cursor.execute("""
                SELECT COUNT(*) FROM orders_inbox
                WHERE DATE(order_date) < %s
                  AND status IN %s
            """, (cutoff_date, TERMINAL_STATUSES))
            orders_to_delete = cursor.fetchone()[0]
            
            # Also count preserved non-terminal orders for logging
            cursor.execute("""
                SELECT COUNT(*) FROM orders_inbox
                WHERE DATE(order_date) < %s
                  AND status NOT IN %s
            """, (cutoff_date, TERMINAL_STATUSES))
            orders_preserved = cursor.fetchone()[0]
            
            if orders_preserved > 0:
                logger.info(f"⚠️ PRESERVING {orders_preserved} non-terminal orders (still active in ShipStation)")
            
            if orders_to_delete == 0:
                logger.info("No terminal orders to clean up")
                return {
                    'deleted': 0,
                    'preserved': orders_preserved,
                    'cutoff_date': cutoff_date,
                    'message': 'No terminal orders older than retention period'
                }
            
            logger.info(f"Found {orders_to_delete} terminal orders to delete")
            
            cursor = conn.cursor()

            # Delete order items for terminal orders only
            cursor.execute("""
                DELETE FROM order_items_inbox
                WHERE order_inbox_id IN (
                    SELECT id FROM orders_inbox
                    WHERE DATE(order_date) < %s
                      AND status IN %s
                )
            """, (cutoff_date, TERMINAL_STATUSES))
            items_deleted = cursor.rowcount
            logger.info(f"Deleted {items_deleted} order items")
            
            cursor = conn.cursor()

            # Delete ShipStation line items for terminal orders only
            cursor.execute("""
                DELETE FROM shipstation_order_line_items
                WHERE order_inbox_id IN (
                    SELECT id FROM orders_inbox
                    WHERE DATE(order_date) < %s
                      AND status IN %s
                )
            """, (cutoff_date, TERMINAL_STATUSES))
            line_items_deleted = cursor.rowcount
            logger.info(f"Deleted {line_items_deleted} ShipStation line items")
            
            cursor = conn.cursor()

            # Delete terminal orders only
            cursor.execute("""
                DELETE FROM orders_inbox
                WHERE DATE(order_date) < %s
                  AND status IN %s
            """, (cutoff_date, TERMINAL_STATUSES))
            orders_deleted = cursor.rowcount
            logger.info(f"Deleted {orders_deleted} terminal orders from inbox")
        
        result = {
            'deleted': orders_deleted,
            'items_deleted': items_deleted,
            'line_items_deleted': line_items_deleted,
            'cutoff_date': cutoff_date,
            'retention_days': days,
            'message': f'Successfully cleaned up {orders_deleted} orders older than {days} days'
        }
        
        logger.info(f"Cleanup completed: {orders_deleted} orders deleted")
        return result
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        return {
            'error': str(e),
            'deleted': 0
        }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up old orders from orders_inbox')
    parser.add_argument('--days', type=int, default=60, help='Number of days to retain orders (default: 60)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    if args.dry_run:
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        TERMINAL_STATUSES = ('shipped', 'cancelled')

        # Sample of orders that WOULD be deleted (terminal + old)
        rows = execute_query("""
            SELECT order_number, order_date, status
            FROM orders_inbox
            WHERE DATE(order_date) < %s
              AND status IN %s
            ORDER BY order_date
            LIMIT 10
        """, (cutoff_date, TERMINAL_STATUSES))

        # Count orders that WOULD be preserved (non-terminal + old)
        preserved_rows = execute_query("""
            SELECT COUNT(*), status
            FROM orders_inbox
            WHERE DATE(order_date) < %s
              AND status NOT IN %s
            GROUP BY status
            ORDER BY status
        """, (cutoff_date, TERMINAL_STATUSES))

        print(f"\n🔍 DRY RUN - Orders that would be deleted (older than {args.days} days, terminal status only):")
        print(f"Cutoff date: {cutoff_date}")
        print(f"Eligible statuses: {', '.join(TERMINAL_STATUSES)}")
        print(f"\nSample orders to DELETE:")
        for order_num, order_date, status in rows:
            print(f"  {order_num}: {order_date} ({status})")

        count_rows = execute_query("""
            SELECT COUNT(*) FROM orders_inbox
            WHERE DATE(order_date) < %s
              AND status IN %s
        """, (cutoff_date, TERMINAL_STATUSES))

        total = count_rows[0][0] if count_rows else 0
        print(f"\nTotal orders to DELETE: {total}")

        if preserved_rows:
            print(f"\n⚠️  Orders that would be PRESERVED (non-terminal, regardless of age):")
            for count, status in preserved_rows:
                print(f"  {count} order(s) with status '{status}'")

        print("\nRun without --dry-run to perform actual deletion")
    else:
        result = cleanup_old_orders(days=args.days)
        print(f"\n{'='*60}")
        print("CLEANUP RESULTS")
        print(f"{'='*60}")
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Orders deleted: {result['deleted']}")
            print(f"   Items deleted: {result['items_deleted']}")
            print(f"   Line items deleted: {result['line_items_deleted']}")
            print(f"   Cutoff date: {result['cutoff_date']}")
            print(f"   Retention period: {result['retention_days']} days")
        print(f"{'='*60}\n")

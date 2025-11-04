#!/usr/bin/env python3
"""
One-Time Script: Fix Orphaned Orders

This script immediately reconciles the 54+ orders currently stuck in orders_inbox
by checking their status in ShipStation and updating local DB accordingly.

Usage: python fix_orphaned_orders.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.order_reconciliation import reconcile_orphaned_orders
from src.services.database import get_connection
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the reconciliation immediately"""
    logger.info("=" * 80)
    logger.info("ORPHANED ORDERS CLEANUP SCRIPT")
    logger.info("=" * 80)
    
    conn = get_connection()
    try:
        logger.info("🔄 Starting reconciliation...")
        summary = reconcile_orphaned_orders(conn)
        conn.commit()
        
        logger.info("=" * 80)
        logger.info("RECONCILIATION SUMMARY:")
        logger.info(f"  Total orders checked: {summary['total_checked']}")
        logger.info(f"  ✅ Updated to shipped: {summary['updated_to_shipped']}")
        logger.info(f"  ❌ Updated to cancelled: {summary['updated_to_cancelled']}")
        logger.info(f"  ⚠️ Not found in ShipStation: {summary['not_found_in_shipstation']}")
        logger.info(f"  🔥 Errors: {summary['errors']}")
        logger.info("=" * 80)
        
        if summary['details']:
            logger.info("\nDETAILS:")
            for detail in summary['details'][:20]:  # Show first 20
                logger.info(f"  {detail}")
            if len(summary['details']) > 20:
                logger.info(f"  ... and {len(summary['details']) - 20} more")
        
        logger.info("\n✅ Reconciliation complete!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Reconciliation failed: {e}", exc_info=True)
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

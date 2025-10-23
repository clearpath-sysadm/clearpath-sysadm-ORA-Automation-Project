#!/usr/bin/env python3
"""
One-time manual tracking status update script.
Bypasses business hours check to populate tracking statuses immediately.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.database import transaction_with_retry
from src.services.shipstation.tracking_service import fetch_tracking_status, map_carrier_to_code
from src.services.shipstation.api_client import get_shipstation_credentials
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_order_tracking_status(order_number, tracking_data, conn):
    """Update tracking status in database"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders_inbox
        SET tracking_status = %s,
            tracking_status_description = %s,
            exception_description = %s,
            tracking_last_checked = NOW(),
            tracking_last_updated = NOW()
        WHERE order_number = %s
    """, (
        tracking_data.get('status_code'),
        tracking_data.get('status_description'),
        tracking_data.get('exception_description'),
        order_number
    ))

def run_manual_tracking_update():
    """Run tracking status updates for all undelivered orders"""
    logger.info("=" * 80)
    logger.info("🚀 MANUAL TRACKING STATUS UPDATE")
    logger.info("=" * 80)
    
    api_key, api_secret = get_shipstation_credentials()
    
    if not api_key or not api_secret:
        logger.error("❌ ShipStation credentials not found!")
        return
    
    with transaction_with_retry() as conn:
        cursor = conn.cursor()
        
        # Get all orders with tracking numbers that need status updates
        cursor.execute("""
            SELECT 
                order_number, 
                tracking_number, 
                shipping_carrier_code, 
                tracking_status
            FROM orders_inbox
            WHERE tracking_number IS NOT NULL
              AND tracking_number != ''
              AND (tracking_status IS NULL OR tracking_status != 'DE')
            ORDER BY order_number DESC
            LIMIT 50
        """)
        
        orders = cursor.fetchall()
        
        if not orders:
            logger.info("📭 No orders to update")
            return
        
        logger.info(f"🔍 Found {len(orders)} orders to check...")
        
        updated = 0
        failed = 0
        
        for order_number, tracking_number, carrier, current_status in orders:
            try:
                # Handle multiple tracking numbers (use first one)
                tracking_nums = [t.strip() for t in tracking_number.split(',')]
                primary_tracking = tracking_nums[0]
                
                # Map carrier to code
                carrier_code = map_carrier_to_code(carrier) if carrier else 'fedex'
                
                logger.info(f"📦 Checking {order_number}: {primary_tracking}")
                
                # Fetch status from ShipStation
                tracking_data = fetch_tracking_status(primary_tracking, carrier_code, api_key, api_secret)
                
                if tracking_data.get('success'):
                    # Update database
                    update_order_tracking_status(order_number, tracking_data, conn)
                    updated += 1
                    
                    # Log status
                    new_status = tracking_data.get('status_code')
                    status_desc = tracking_data.get('status_description')
                    logger.info(f"   ✅ {order_number}: {new_status} ({status_desc})")
                    
                    # Alert on exceptions
                    if new_status == 'EX':
                        exception_desc = tracking_data.get('exception_description', 'Unknown exception')
                        logger.warning(f"   ⚠️ EXCEPTION: {exception_desc}")
                else:
                    error_msg = tracking_data.get('error', 'Unknown error')
                    logger.warning(f"   ⚠️ Failed: {error_msg}")
                    failed += 1
                    
                    # Still update last_checked timestamp
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET tracking_last_checked = NOW()
                        WHERE order_number = %s
                    """, (order_number,))
                    
            except Exception as e:
                logger.error(f"   ❌ Error for {order_number}: {e}")
                failed += 1
                
                # Update timestamp even on exception
                try:
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET tracking_last_checked = NOW()
                        WHERE order_number = %s
                    """, (order_number,))
                except:
                    pass
        
        logger.info("=" * 80)
        logger.info("📊 MANUAL UPDATE COMPLETE")
        logger.info(f"   ✅ Successfully updated: {updated}")
        logger.info(f"   ⚠️ Failed: {failed}")
        logger.info(f"   📝 Total processed: {len(orders)}")
        logger.info("=" * 80)

if __name__ == "__main__":
    run_manual_tracking_update()

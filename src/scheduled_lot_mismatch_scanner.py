#!/usr/bin/env python3
"""
LOT NUMBER MISMATCH SCANNER
Scans orders in ShipStation for lot number mismatches vs active lots in local database.

Alerts when SKU-Lot in ShipStation ≠ active lot in local db.
Provides UI to update SKU-Lot in ShipStation.

Safety Design: Manual-only resolution to prevent data loss.
"""

import os
import sys
import time
import logging
import datetime
from typing import Dict, List, Any
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.pg_utils import transaction_with_retry, is_workflow_enabled, update_workflow_last_run
from src.services.shipstation.api_client import get_shipstation_credentials
from utils.api_utils import make_api_request

SHIPSTATION_ORDERS_ENDPOINT = 'https://ssapi.shipstation.com/orders'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WORKFLOW_NAME = "lot-mismatch-scanner"


def get_active_lot_mappings(conn) -> Dict[str, str]:
    """
    Get active lot mappings from local database.
    
    Returns:
        Dict mapping sku -> active lot number
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sku, lot
        FROM sku_lot
        WHERE active = 1
    """)
    
    mappings = {}
    for row in cursor.fetchall():
        sku = row[0]
        lot = row[1]
        mappings[sku] = lot
    
    return mappings


def scan_for_lot_mismatches(api_key: str, api_secret: str):
    """
    Scan ShipStation orders for lot number mismatches.
    
    Compares SKU-Lot in ShipStation vs active lots in local db.
    Creates alerts for mismatches.
    """
    logger.info("=" * 80)
    logger.info("🔍 LOT MISMATCH SCANNER STARTED")
    logger.info("=" * 80)
    
    scan_start = datetime.datetime.now()
    
    try:
        with transaction_with_retry() as conn:
            # Get active lot mappings
            active_lots = get_active_lot_mappings(conn)
            logger.info(f"📋 Active lot mappings: {len(active_lots)} SKUs")
            
            # Fetch orders from ShipStation (last 30 days, awaiting shipment)
            # We only care about orders that haven't shipped yet
            lookback_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            params = {
                'orderStatus': 'awaiting_shipment',
                'modifyDateStart': lookback_date,
                'pageSize': 500
            }
            
            logger.info(f"🔄 Fetching orders modified since {lookback_date}")
            
            all_orders = []
            page = 1
            
            while True:
                params['page'] = page
                response = make_api_request(
                    'GET',
                    SHIPSTATION_ORDERS_ENDPOINT,
                    auth=(api_key, api_secret),
                    params=params
                )
                
                if not response or 'orders' not in response:
                    break
                
                orders = response['orders']
                all_orders.extend(orders)
                
                total_pages = response.get('pages', 1)
                logger.info(f"📄 Page {page}/{total_pages}: {len(orders)} orders")
                
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(0.5)  # Rate limiting
            
            logger.info(f"✅ Retrieved {len(all_orders)} total orders from ShipStation")
            
            # Scan for lot mismatches
            mismatches_found = 0
            mismatches_created = 0
            
            cursor = conn.cursor()
            
            for order in all_orders:
                order_number = order.get('orderNumber', '').strip()
                order_id = order.get('orderId')
                order_status = order.get('orderStatus', '').lower()
                items = order.get('items', [])
                
                for item in items:
                    sku_raw = str(item.get('sku', '')).strip()
                    item_id = item.get('orderItemId')
                    
                    if not sku_raw:
                        continue
                    
                    # Parse SKU - LOT format
                    base_sku = None
                    shipstation_lot = None
                    
                    if ' - ' in sku_raw:
                        sku_parts = sku_raw.split(' - ')
                        base_sku = sku_parts[0].strip()
                        shipstation_lot = sku_parts[1].strip() if len(sku_parts) > 1 else None
                    else:
                        base_sku = sku_raw
                        shipstation_lot = None
                    
                    # Check if we have an active lot for this SKU
                    if base_sku not in active_lots:
                        continue
                    
                    active_lot = active_lots[base_sku]
                    
                    # Check for mismatch
                    if shipstation_lot != active_lot:
                        mismatches_found += 1
                        
                        logger.warning(
                            f"⚠️ LOT MISMATCH: Order {order_number}, SKU {base_sku} → "
                            f"ShipStation: {shipstation_lot or 'NONE'}, Active: {active_lot}"
                        )
                        
                        # Create/update alert
                        cursor.execute("""
                            INSERT INTO lot_mismatch_alerts (
                                order_number,
                                base_sku,
                                shipstation_lot,
                                active_lot,
                                shipstation_order_id,
                                shipstation_item_id,
                                order_status,
                                detected_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (order_number, base_sku) DO UPDATE
                            SET shipstation_lot = EXCLUDED.shipstation_lot,
                                active_lot = EXCLUDED.active_lot,
                                order_status = EXCLUDED.order_status,
                                detected_at = CURRENT_TIMESTAMP
                            WHERE lot_mismatch_alerts.resolved_at IS NULL
                        """, (
                            order_number,
                            base_sku,
                            shipstation_lot,
                            active_lot,
                            str(order_id),
                            str(item_id),
                            order_status
                        ))
                        
                        if cursor.rowcount > 0:
                            mismatches_created += 1
            
            # Clear resolved alerts for orders that no longer have mismatches
            # (e.g., lot was updated manually in ShipStation)
            cursor.execute("""
                UPDATE lot_mismatch_alerts
                SET resolved_at = CURRENT_TIMESTAMP,
                    resolved_by = 'auto'
                WHERE resolved_at IS NULL
                  AND detected_at < %s
            """, (scan_start,))
            
            auto_resolved = cursor.rowcount
            
            # Update workflow last run
            update_workflow_last_run(WORKFLOW_NAME, conn)
        
        elapsed = (datetime.datetime.now() - scan_start).total_seconds()
        
        logger.info("=" * 80)
        logger.info("📊 SCAN SUMMARY:")
        logger.info(f"   ⚠️ Lot mismatches found: {mismatches_found}")
        logger.info(f"   ➕ New/updated alerts: {mismatches_created}")
        logger.info(f"   ✅ Auto-resolved: {auto_resolved}")
        logger.info(f"   ⏱️ Duration: {elapsed:.1f}s")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error scanning for lot mismatches: {e}", exc_info=True)


def main():
    """Main loop for lot mismatch scanner."""
    logger.info(f"🚀 Starting Lot Mismatch Scanner (every 900s)")
    
    # Get ShipStation credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.critical("❌ Failed to get ShipStation credentials")
        return
    
    while True:
        try:
            if not is_workflow_enabled(WORKFLOW_NAME):
                logger.info(f"⏸️ Workflow '{WORKFLOW_NAME}' is DISABLED - skipping execution")
            else:
                scan_for_lot_mismatches(api_key, api_secret)
            
            logger.info("😴 Next scan in 900 seconds (15 minutes)")
            time.sleep(900)
            
        except KeyboardInterrupt:
            logger.info("👋 Lot mismatch scanner stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}", exc_info=True)
            logger.info("😴 Retrying in 60 seconds after error")
            time.sleep(60)


if __name__ == "__main__":
    main()

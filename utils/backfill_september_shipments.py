#!/usr/bin/env python3
"""
September 2025 Shipment Data Backfill Script

One-off script to backfill shipment data from ShipStation for September 2025.
This will fetch all shipped orders from September and update the database tables:
- shipped_orders
- shipped_items  
- weekly_shipped_history
"""

import sys
import os
import logging
import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import setup_logging
from src.services.shipstation.api_client import get_shipstation_credentials, fetch_shipstation_shipments
from src.services.data_processing.shipment_processor import process_shipped_items, process_shipped_orders
from src.daily_shipment_processor import (
    save_shipped_orders_to_db,
    save_shipped_items_to_db,
    get_weekly_history_from_db,
    update_weekly_history_incrementally,
    save_weekly_history_to_db
)
from src.services.database.db_utils import execute_query
from config.settings import SHIPSTATION_SHIPMENTS_ENDPOINT

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'september_backfill.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def backfill_september_shipments():
    """
    Backfill shipment data for September 2025 from ShipStation.
    """
    logger.info("=" * 70)
    logger.info("SEPTEMBER 2025 SHIPMENT DATA BACKFILL")
    logger.info("=" * 70)
    
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.critical("Failed to get ShipStation credentials")
            return
        
        # Define September date range
        start_date = '2025-09-01'
        end_date = '2025-09-30'
        
        logger.info(f"Fetching shipment data for date range: {start_date} to {end_date}")
        
        # Fetch shipments from ShipStation API
        shipment_data = fetch_shipstation_shipments(
            api_key=api_key,
            api_secret=api_secret,
            shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,
            start_date=start_date,
            end_date=end_date,
            shipment_status="shipped"
        )
        
        if not shipment_data:
            logger.warning("No shipment data returned from ShipStation API for September")
            return
        
        logger.info(f"Retrieved {len(shipment_data)} total shipments from ShipStation")
        
        # Filter out voided shipments
        non_voided_shipments = [s for s in shipment_data if not s.get('voided', False)]
        logger.info(f"Processing {len(non_voided_shipments)} non-voided shipments")
        
        if not non_voided_shipments:
            logger.info("No non-voided shipments to process")
            return
        
        # Process shipments into DataFrames
        logger.info("Processing shipped items...")
        items_df = process_shipped_items(non_voided_shipments)
        logger.info(f"Processed {len(items_df)} shipped items")
        
        logger.info("Processing shipped orders...")
        orders_df = process_shipped_orders(non_voided_shipments)
        logger.info(f"Processed {len(orders_df)} shipped orders")
        
        # Save to database (UPSERT will handle duplicates)
        logger.info("Saving to database...")
        orders_saved = save_shipped_orders_to_db(orders_df)
        logger.info(f"✅ Saved {orders_saved} orders to shipped_orders table")
        
        items_saved = save_shipped_items_to_db(items_df)
        logger.info(f"✅ Saved {items_saved} items to shipped_items table")
        
        # Update weekly shipped history
        logger.info("Updating weekly shipped history...")
        
        # Get target SKUs from configuration
        target_skus_rows = execute_query("""
            SELECT sku FROM configuration_params
            WHERE category = 'Key Products'
            ORDER BY sku
        """)
        target_skus = [str(row[0]) for row in target_skus_rows] if target_skus_rows else ['17612', '17904', '17914', '18675', '18795']
        
        logger.info(f"Updating history for {len(target_skus)} key SKUs: {target_skus}")
        
        # Get existing history
        existing_history_df = get_weekly_history_from_db(target_skus)
        
        # Update history incrementally with September data
        updated_history_df = update_weekly_history_incrementally(
            items_df.copy(),
            existing_history_df.copy(),
            target_skus,
            non_voided_shipments
        )
        
        # Save updated history
        history_saved = save_weekly_history_to_db(updated_history_df)
        logger.info(f"✅ Saved {history_saved} weekly history records")
        
        logger.info("=" * 70)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"Summary:")
        logger.info(f"  - Orders saved: {orders_saved}")
        logger.info(f"  - Items saved: {items_saved}")
        logger.info(f"  - Date range: {start_date} to {end_date}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    backfill_september_shipments()

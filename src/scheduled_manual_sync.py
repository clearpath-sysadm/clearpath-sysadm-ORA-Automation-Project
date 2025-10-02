#!/usr/bin/env python3
"""
Scheduled Manual ShipStation Sync
Runs every hour to sync manual orders from ShipStation back to local database
"""
import os
import sys
import time
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.manual_shipstation_sync import run_manual_order_sync

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Run every hour (3600 seconds)
SYNC_INTERVAL_SECONDS = 3600

def run_scheduled_sync():
    """Main loop - runs hourly sync"""
    logger.info(f"Starting scheduled manual ShipStation sync (every {SYNC_INTERVAL_SECONDS}s / 1 hour)")
    
    while True:
        try:
            logger.info("Running scheduled manual order sync...")
            
            result, status_code = run_manual_order_sync()
            logger.info(f"Sync complete: {result} (Status: {status_code})")
            
            logger.info(f"Next sync in {SYNC_INTERVAL_SECONDS} seconds (1 hour)")
            time.sleep(SYNC_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Scheduled sync stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduled sync: {str(e)}")
            logger.info(f"Retrying in {SYNC_INTERVAL_SECONDS} seconds")
            time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_scheduled_sync()

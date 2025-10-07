#!/usr/bin/env python3
"""
Scheduled ShipStation Status Sync
Runs every 5 minutes to sync order statuses from ShipStation back to local database
"""
import os
import sys
import time
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.shipstation_status_sync import run_status_sync

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Run every 5 minutes (300 seconds)
SYNC_INTERVAL_SECONDS = 300

def run_scheduled_status_sync():
    """Main loop - runs status sync every 5 minutes"""
    logger.info(f"Starting scheduled ShipStation status sync (every {SYNC_INTERVAL_SECONDS}s / 5 minutes)")
    
    while True:
        try:
            logger.info("Running scheduled status sync...")
            
            result, status_code = run_status_sync()
            logger.info(f"Sync complete: {result} (Status: {status_code})")
            
            logger.info(f"Next sync in {SYNC_INTERVAL_SECONDS} seconds (5 minutes)")
            time.sleep(SYNC_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Scheduled status sync stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduled status sync: {str(e)}")
            logger.info(f"Retrying in {SYNC_INTERVAL_SECONDS} seconds")
            time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_scheduled_status_sync()

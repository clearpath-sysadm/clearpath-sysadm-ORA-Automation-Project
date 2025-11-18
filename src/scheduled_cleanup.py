#!/usr/bin/env python3
"""
Scheduled Orders Cleanup

Runs daily cleanup of old orders from orders_inbox.
Deletes orders older than 60 days from their order_date.
"""

import sys
import os
import time
import logging

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cleanup_old_orders import cleanup_old_orders
from src.services.database.pg_utils import is_workflow_enabled, update_workflow_last_run
from utils.logging_config import setup_logging
from utils.business_hours import is_business_hours, get_sleep_until_business_hours, format_business_hours_status

log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'scheduled_cleanup.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)

CLEANUP_INTERVAL = 86400


def main():
    """Run cleanup on a daily schedule during business hours (Mon-Fri 6 AM - 6 PM CST)"""
    logger.info("Starting scheduled cleanup service (runs daily)")
    logger.info("⏰ Business Hours: Monday-Friday 6 AM - 6 PM CST | Weekends OFF")
    
    while True:
        try:
            # PRIORITY 1: Check business hours BEFORE any database queries
            if not is_business_hours():
                status = format_business_hours_status()
                logger.info(f"{status}")
                sleep_duration = get_sleep_until_business_hours()
                logger.info(f"💤 Database sleeping for {sleep_duration}s to reduce compute time")
                time.sleep(sleep_duration)
                continue
            
            # PRIORITY 2: Check if workflow enabled
            if not is_workflow_enabled('orders-cleanup'):
                logger.info("Workflow 'orders-cleanup' is DISABLED - sleeping 60s")
                time.sleep(60)
                continue
            
            update_workflow_last_run('orders-cleanup')
            logger.info("Running scheduled cleanup...")
            result = cleanup_old_orders(days=60)
            
            if 'error' in result:
                logger.error(f"Cleanup failed: {result['error']}")
            else:
                logger.info(f"Cleanup complete: {result['deleted']} orders deleted")
            
            logger.info(f"Next cleanup in {CLEANUP_INTERVAL} seconds (24 hours)")
            time.sleep(CLEANUP_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}", exc_info=True)
            logger.info("Retrying in 1 hour...")
            time.sleep(3600)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Scheduled XML Import from Google Drive
Runs every 5 minutes to import orders.xml and cleanup old data
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.google_drive.api_client import list_xml_files_from_folder, fetch_xml_from_drive_by_file_id
from src.services.database.db_utils import get_connection
import xml.etree.ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GOOGLE_DRIVE_FOLDER_ID = '1rNudeesa_c6q--KIKUAOLwXta_gyRqAE'
IMPORT_INTERVAL_SECONDS = 300
DATA_RETENTION_DAYS = 60

def cleanup_old_orders():
    """Delete orders older than 2 months from orders_inbox"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            DELETE FROM order_items_inbox 
            WHERE order_inbox_id IN (
                SELECT id FROM orders_inbox WHERE created_at < ?
            )
        """, (cutoff_date,))
        
        cursor.execute("DELETE FROM orders_inbox WHERE created_at < ?", (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} orders older than {DATA_RETENTION_DAYS} days")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old orders: {str(e)}")
        return 0

def import_orders_from_drive():
    """Import orders.xml from Google Drive"""
    try:
        files = list_xml_files_from_folder(GOOGLE_DRIVE_FOLDER_ID)
        
        orders_file = next((f for f in files if f['name'] == 'orders.xml'), None)
        
        if not orders_file:
            logger.warning("orders.xml not found in Google Drive")
            return 0
        
        logger.info(f"Found orders.xml (ID: {orders_file['id']})")
        
        xml_content = fetch_xml_from_drive_by_file_id(orders_file['id'])
        
        root = ET.fromstring(xml_content)
        
        conn = get_connection()
        cursor = conn.cursor()
        orders_imported = 0
        
        for order_elem in root.findall('order'):
            order_id = order_elem.find('orderid')
            order_date = order_elem.find('date2')
            email = order_elem.find('email')
            
            if order_id is not None and order_id.text:
                order_number = order_id.text.strip()
                order_date_str = order_date.text.strip() if order_date is not None and order_date.text else datetime.now().strftime('%Y-%m-%d')
                customer_email = email.text.strip() if email is not None and email.text else None
                
                items = order_elem.findall('.//product')
                total_items = len(items)
                
                cursor.execute("SELECT id FROM orders_inbox WHERE order_number = ?", (order_number,))
                existing = cursor.fetchone()
                
                if not existing:
                    cursor.execute("""
                        INSERT INTO orders_inbox (order_number, order_date, customer_email, status, total_items, source_system)
                        VALUES (?, ?, ?, 'pending', ?, 'X-Cart')
                    """, (order_number, order_date_str, customer_email, total_items))
                    
                    order_inbox_id = cursor.lastrowid
                    
                    for product in items:
                        product_code = product.find('productcode')
                        quantity = product.find('amount')
                        
                        if product_code is not None and product_code.text:
                            sku = product_code.text.strip()
                            qty = int(quantity.text.strip()) if quantity is not None and quantity.text else 1
                            
                            cursor.execute("""
                                INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                                VALUES (?, ?, ?)
                            """, (order_inbox_id, sku, qty))
                    
                    orders_imported += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully imported {orders_imported} new orders from Google Drive")
        return orders_imported
        
    except Exception as e:
        logger.error(f"Error importing from Google Drive: {str(e)}")
        return 0

def run_scheduled_import():
    """Main loop - runs every 5 minutes"""
    logger.info(f"Starting scheduled XML import (every {IMPORT_INTERVAL_SECONDS}s)")
    logger.info(f"Data retention: {DATA_RETENTION_DAYS} days")
    
    while True:
        try:
            logger.info("Running scheduled import...")
            
            imported = import_orders_from_drive()
            logger.info(f"Import complete: {imported} orders imported")
            
            deleted = cleanup_old_orders()
            if deleted > 0:
                logger.info(f"Cleanup complete: {deleted} old orders deleted")
            
            logger.info(f"Next import in {IMPORT_INTERVAL_SECONDS} seconds")
            time.sleep(IMPORT_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Scheduled import stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduled import: {str(e)}")
            time.sleep(IMPORT_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_scheduled_import()

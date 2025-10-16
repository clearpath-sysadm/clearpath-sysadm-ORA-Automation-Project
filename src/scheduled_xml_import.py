#!/usr/bin/env python3
"""
Scheduled XML Import from Google Drive
Optimized polling with feature flags and efficient change detection
"""
import os
import sys
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.google_drive.api_client import list_xml_files_from_folder, fetch_xml_from_drive_by_file_id
from src.services.database import get_connection, transaction_with_retry, is_workflow_enabled, update_workflow_last_run
import defusedxml.ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GOOGLE_DRIVE_FOLDER_ID = '1rNudeesa_c6q--KIKUAOLwXta_gyRqAE'
DATA_RETENTION_DAYS = 60

# ============================================================================
# OPTIMIZED POLLING: Feature Flag Caching (60-second TTL)
# ============================================================================
_feature_flag_cache = {}
_feature_flag_cache_time = None

def get_feature_flag(flag_name, default_value):
    """Get feature flag with 60-second cache (shared with upload workflow)"""
    global _feature_flag_cache, _feature_flag_cache_time
    
    # Return cached value if fresh
    if _feature_flag_cache_time and (datetime.now() - _feature_flag_cache_time).seconds < 60:
        return _feature_flag_cache.get(flag_name, default_value)
    
    # Refresh all flags from database
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT parameter_name, value 
            FROM configuration_params 
            WHERE category = 'Polling'
        """)
        
        _feature_flag_cache = {row[0]: row[1] for row in cursor.fetchall()}
        _feature_flag_cache_time = datetime.now()
        
        return _feature_flag_cache.get(flag_name, default_value)
    except Exception as e:
        logger.debug(f"Failed to fetch feature flags: {e}")
        return default_value
    finally:
        conn.close()

# ============================================================================
# OPTIMIZED POLLING: Change Detection
# ============================================================================
def has_new_xml_files():
    """Check if new XML files exist using robust file signature (IDs + timestamps)"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        start = time.time()
        
        # Get last check signature from polling_state
        cursor.execute("SELECT last_xml_count, last_xml_check FROM polling_state WHERE id = 1")
        result = cursor.fetchone()
        last_signature = result[0] if result else ""
        last_check = result[1] if result else datetime.now() - timedelta(hours=1)
        
        # Get current files from Google Drive
        try:
            files = list_xml_files_from_folder(GOOGLE_DRIVE_FOLDER_ID)
            
            # Create robust signature: sorted concat of file_id:modified_time
            # This detects: new files, deleted files, AND replaced files (same name, different ID/timestamp)
            file_signatures = sorted([f"{f['id']}:{f.get('modifiedTime', '')}" for f in files])
            current_signature = "|".join(file_signatures)
            
        except Exception as e:
            logger.error(f"Error checking Drive files: {e}")
            # Process on error (fail-safe)
            duration_ms = int((time.time() - start) * 1000)
            logger.info(f"METRICS: workflow=xml-import signature=error duration_ms={duration_ms} action=process_error")
            return True, "", duration_ms
        
        duration_ms = int((time.time() - start) * 1000)
        has_changes = current_signature != last_signature
        
        logger.info(f"METRICS: workflow=xml-import files={len(files)} duration_ms={duration_ms} action={'process' if has_changes else 'skip'}")
        
        return has_changes, current_signature, duration_ms
        
    except Exception as e:
        logger.error(f"Error in has_new_xml_files: {e}")
        return True, "", 0  # Process on error (fail-safe)
    finally:
        conn.close()

def update_xml_polling_state(signature):
    """Update XML polling state after successful import"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE polling_state 
            SET last_xml_count = %s,
                last_xml_check = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (signature,))
        conn.commit()
        logger.debug(f"✅ Updated polling state with signature (len={len(signature)})")
    except Exception as e:
        logger.debug(f"Failed to update XML polling state: {e}")
    finally:
        conn.close()

def cleanup_old_orders():
    """Delete orders older than 2 months from orders_inbox"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            DELETE FROM order_items_inbox 
            WHERE order_inbox_id IN (
                SELECT id FROM orders_inbox WHERE created_at < %s
            )
        """, (cutoff_date,))
        
        cursor.execute("DELETE FROM orders_inbox WHERE created_at < %s", (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} orders older than {DATA_RETENTION_DAYS} days")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old orders: {str(e)}")
        return 0
    finally:
        conn.close()

def load_bundle_config(cursor):
    """Load bundle configurations from database"""
    cursor.execute("""
        SELECT bs.bundle_sku, bc.component_sku, bc.multiplier, bc.sequence
        FROM bundle_skus bs
        JOIN bundle_components bc ON bs.id = bc.bundle_sku_id
        WHERE bs.active = 1
        ORDER BY bs.bundle_sku, bc.sequence
    """)
    
    bundle_config = {}
    for row in cursor.fetchall():
        bundle_sku, component_sku, multiplier, sequence = row
        
        if bundle_sku not in bundle_config:
            bundle_config[bundle_sku] = []
        
        bundle_config[bundle_sku].append({
            'component_sku': component_sku,
            'multiplier': multiplier
        })
    
    return bundle_config

def expand_bundle_items(line_items, bundle_config):
    """Expand bundle SKUs into component SKUs"""
    expanded_items = []
    
    for item in line_items:
        sku = item['sku']
        qty = item['quantity']
        
        if sku in bundle_config:
            # This is a bundle - expand it
            for component in bundle_config[sku]:
                expanded_items.append({
                    'sku': component['component_sku'],
                    'quantity': qty * component['multiplier']
                })
        else:
            # Regular SKU - pass through
            expanded_items.append(item)
    
    return expanded_items

def import_orders_from_drive():
    """Import orders.xml from Google Drive with bundle expansion"""
    conn = None
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
        
        # BEGIN transaction to prevent race conditions
        # PostgreSQL doesn't support BEGIN IMMEDIATE - just use BEGIN
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        
        # Load bundle configurations
        bundle_config = load_bundle_config(cursor)
        logger.info(f"Loaded {len(bundle_config)} bundle configurations")
        
        # Load Key Products (SKUs we actually process for this client)
        cursor.execute("""
            SELECT sku FROM configuration_params
            WHERE category = 'Key Products'
        """)
        key_products = {row[0] for row in cursor.fetchall()}
        logger.info(f"Loaded {len(key_products)} Key Products for filtering")
        
        # Helper function to safely extract text
        def get_text(elem, tag, default=''):
            child = elem.find(tag)
            return child.text.strip() if child is not None and child.text else default
        
        orders_imported = 0
        orders_skipped = 0
        
        for order_elem in root.findall('order'):
            order_id = order_elem.find('orderid')
            order_date = order_elem.find('date2')
            email = order_elem.find('email')
            
            if order_id is not None and order_id.text:
                order_number = order_id.text.strip()
                order_date_str = order_date.text.strip() if order_date is not None and order_date.text else datetime.now().strftime('%Y-%m-%d')
                customer_email = email.text.strip() if email is not None and email.text else None
                
                # Parse shipping address (prefix 's_')
                ship_firstname = get_text(order_elem, 's_firstname')
                ship_lastname = get_text(order_elem, 's_lastname')
                ship_name = f"{ship_firstname} {ship_lastname}".strip()
                ship_company = get_text(order_elem, 's_company')
                ship_street1 = get_text(order_elem, 's_address')
                ship_city = get_text(order_elem, 's_city')
                ship_state = get_text(order_elem, 's_state')
                ship_postal_code = get_text(order_elem, 's_zipcode')
                ship_country = get_text(order_elem, 's_country', 'US')
                ship_phone = get_text(order_elem, 's_phone')
                
                # Parse billing address (prefix 'b_')
                bill_firstname = get_text(order_elem, 'b_firstname')
                bill_lastname = get_text(order_elem, 'b_lastname')
                bill_name = f"{bill_firstname} {bill_lastname}".strip()
                bill_company = get_text(order_elem, 'b_company')
                bill_street1 = get_text(order_elem, 'b_address')
                bill_city = get_text(order_elem, 'b_city')
                bill_state = get_text(order_elem, 'b_state')
                bill_postal_code = get_text(order_elem, 'b_zipcode')
                bill_country = get_text(order_elem, 'b_country', 'US')
                bill_phone = get_text(order_elem, 'b_phone')
                
                # Parse line items from order_detail elements
                line_items = []
                
                for detail_elem in order_elem.findall('order_detail'):
                    product_code = detail_elem.find('productid')
                    quantity_elem = detail_elem.find('amount')
                    
                    if product_code is not None and product_code.text:
                        sku = product_code.text.strip()
                        qty = int(quantity_elem.text.strip()) if quantity_elem is not None and quantity_elem.text else 1
                        line_items.append({'sku': sku, 'quantity': qty})
                
                # Expand bundles into component SKUs
                expanded_items = expand_bundle_items(line_items, bundle_config)
                
                # CRITICAL: Filter expanded items to ONLY include Key Products
                filtered_items = [item for item in expanded_items if item['sku'] in key_products]
                
                # Skip order if no Key Products remain after filtering
                if not filtered_items:
                    orders_skipped += 1
                    skipped_skus = {item['sku'] for item in expanded_items}
                    logger.info(f"SKIPPED Order {order_number}: No Key Products found. SKUs: {', '.join(skipped_skus)}")
                    continue
                
                # FIX: Consolidate items by SKU to prevent duplicate rows in database
                # Multiple bundles or items can expand to the same SKU - combine them
                consolidated = defaultdict(int)
                for item in filtered_items:
                    consolidated[item['sku']] += item['quantity']
                
                # Convert back to list format for insertion
                consolidated_items = [{'sku': sku, 'quantity': qty} for sku, qty in consolidated.items()]
                
                # Calculate total quantity from consolidated items (only Key Products)
                total_quantity = sum(item['quantity'] for item in consolidated_items)
                
                # IDEMPOTENT UPSERT: Check if order exists
                cursor.execute("SELECT id FROM orders_inbox WHERE order_number = %s", (order_number,))
                existing = cursor.fetchone()
                
                if existing:
                    # Order exists - DELETE old items and UPDATE order (idempotent reprocessing)
                    order_inbox_id = existing[0]
                    
                    # Delete old items
                    cursor.execute("DELETE FROM order_items_inbox WHERE order_inbox_id = %s", (order_inbox_id,))
                    
                    # Update order metadata
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET order_date = %s, customer_email = %s, total_items = %s,
                            ship_name = %s, ship_company = %s, ship_street1 = %s, ship_city = %s, 
                            ship_state = %s, ship_postal_code = %s, ship_country = %s, ship_phone = %s,
                            bill_name = %s, bill_company = %s, bill_street1 = %s, bill_city = %s, 
                            bill_state = %s, bill_postal_code = %s, bill_country = %s, bill_phone = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        order_date_str, customer_email, total_quantity,
                        ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                        bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone,
                        order_inbox_id
                    ))
                else:
                    # New order - INSERT
                    cursor.execute("""
                        INSERT INTO orders_inbox (
                            order_number, order_date, customer_email, status, total_items, source_system,
                            ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                            bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                        )
                        VALUES (%s, %s, %s, 'pending', %s, 'X-Cart', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        order_number, order_date_str, customer_email, total_quantity,
                        ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                        bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                    ))
                    
                    order_inbox_id = cursor.fetchone()[0]
                    orders_imported += 1
                
                # Insert consolidated line items (duplicates merged, only Key Products)
                for item in consolidated_items:
                    cursor.execute("""
                        INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                        VALUES (%s, %s, %s)
                    """, (order_inbox_id, item['sku'], item['quantity']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully imported {orders_imported} new orders from Google Drive ({orders_skipped} skipped - no Key Products)")
        return orders_imported
        
    except Exception as e:
        logger.error(f"Error importing from Google Drive: {str(e)}")
        # Rollback transaction on any error
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return 0

def run_scheduled_import():
    """Optimized main loop with feature flags and efficient polling"""
    # Get feature flags
    fast_polling_enabled = get_feature_flag('fast_polling_enabled', 'false').lower() == 'true'
    fast_polling_interval = int(get_feature_flag('fast_polling_interval', '15'))
    fallback_interval = int(get_feature_flag('sync_interval', '300'))
    
    interval = fast_polling_interval if fast_polling_enabled else fallback_interval
    
    logger.info(f"🚀 XML import workflow started (fast_polling={fast_polling_enabled}, interval={interval}s)")
    logger.info(f"📁 Data retention: {DATA_RETENTION_DAYS} days")
    
    error_count = 0
    max_errors = 5
    
    while True:
        try:
            # Check if workflow is enabled
            if not is_workflow_enabled('xml-import'):
                logger.info("⏸️ Workflow 'xml-import' is DISABLED - sleeping 60s")
                time.sleep(60)
                continue
            
            # PREFLIGHT CHECK: Do we have new files?
            has_changes, file_signature, check_duration = has_new_xml_files()
            
            if not has_changes:
                # No changes - skip processing
                time.sleep(interval)
                continue
            
            # Changes detected - process files
            logger.info(f"📥 Processing XML files from Drive (signature changed)")
            update_workflow_last_run('xml-import')
            
            imported = import_orders_from_drive()
            
            if imported > 0:
                logger.info(f"✅ Import complete: {imported} orders imported")
            else:
                logger.info(f"ℹ️ Import complete: No new orders")
            
            # Update polling state on success with file signature
            update_xml_polling_state(file_signature)
            
            # Cleanup old orders
            deleted = cleanup_old_orders()
            if deleted > 0:
                logger.info(f"🗑️ Cleanup complete: {deleted} old orders deleted")
            
            # Reset error count on success
            error_count = 0
            
            logger.info(f"😴 Next import check in {interval} seconds")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("⏹️ Scheduled import stopped by user")
            break
        except Exception as e:
            error_count += 1
            logger.error(f"❌ Error in scheduled import (attempt {error_count}/{max_errors}): {str(e)}")
            
            if error_count >= max_errors:
                logger.error(f"🚨 Max errors ({max_errors}) reached - using exponential backoff")
                backoff = min(interval * (2 ** (error_count - max_errors)), 3600)  # Max 1 hour
                logger.info(f"😴 Backing off for {backoff}s due to errors")
                time.sleep(backoff)
            else:
                time.sleep(interval)

if __name__ == '__main__':
    run_scheduled_import()

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
from src.utils.server_logger import get_logger
from src.workflow_heartbeat import heartbeat, HeartbeatPhase
from utils.business_hours import is_business_hours, get_sleep_until_business_hours, format_business_hours_status
import defusedxml.ElementTree as ET

WORKFLOW_NAME = 'xml-import'

server_logger = get_logger()

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
        server_logger.info(f"Connecting to Google Drive folder: {GOOGLE_DRIVE_FOLDER_ID}", source="XML Import")
        files = list_xml_files_from_folder(GOOGLE_DRIVE_FOLDER_ID)
        server_logger.info(f"Found {len(files)} files in Google Drive folder", source="XML Import")
        
        orders_file = next((f for f in files if f['name'] == 'orders.xml'), None)
        
        if not orders_file:
            logger.warning("orders.xml not found in Google Drive")
            server_logger.warning("orders.xml NOT FOUND in Google Drive folder!", source="XML Import")
            return 0
        
        logger.info(f"Found orders.xml (ID: {orders_file['id']})")
        server_logger.info(f"Found orders.xml (ID: {orders_file['id'][:20]}...)", source="XML Import")
        
        xml_content = fetch_xml_from_drive_by_file_id(orders_file['id'])
        server_logger.info(f"Fetched XML content ({len(xml_content)} bytes)", source="XML Import")
        
        root = ET.fromstring(xml_content)
        total_orders_in_xml = len(root.findall('order'))
        server_logger.info(f"Parsed XML: {total_orders_in_xml} orders found in file", source="XML Import")
        
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
        server_logger.info(f"Key Products loaded: {', '.join(sorted(key_products))}", source="XML Import")
        
        # Load active lot numbers for automatic assignment
        cursor.execute("""
            SELECT sku, lot 
            FROM sku_lot 
            WHERE active = 1
        """)
        active_lots = {row[0]: row[1] for row in cursor.fetchall()}
        logger.info(f"Loaded {len(active_lots)} active lot numbers for SKU-Lot assignment")
        
        # Log active lots to server logger for production debugging
        if active_lots:
            lots_summary = ', '.join([f"{sku}={lot}" for sku, lot in list(active_lots.items())[:5]])
            if len(active_lots) > 5:
                lots_summary += f" (+{len(active_lots) - 5} more)"
            server_logger.info(f"Active lots loaded: {lots_summary}", source="XML Import")
        else:
            server_logger.warning("No active lot numbers found in sku_lot table!", source="XML Import")
        
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
                cursor.execute("SELECT id, shipstation_order_id, status FROM orders_inbox WHERE order_number = %s", (order_number,))
                existing = cursor.fetchone()
                
                if existing:
                    order_inbox_id = existing[0]
                    existing_ss_id = existing[1]
                    existing_status = existing[2]
                    
                    # CRITICAL FIX: Skip re-importing orders that have already been uploaded
                    # This prevents clearing shipstation_order_id and re-triggering upload
                    if existing_ss_id and existing_ss_id.strip():
                        logger.info(f"SKIPPED Order {order_number}: Already uploaded to ShipStation (ID: {existing_ss_id})")
                        orders_skipped += 1
                        continue
                    
                    # Order exists but not uploaded yet - DELETE old items and UPDATE order (idempotent reprocessing)
                    # Delete old items
                    cursor.execute("DELETE FROM order_items_inbox WHERE order_inbox_id = %s", (order_inbox_id,))
                    
                    # Update order metadata (preserve status if already set)
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
                    
                    # Log new order to server logger
                    item_count = len(consolidated_items)
                    sku_list = ', '.join([f"{item['sku']} x{item['quantity']}" for item in consolidated_items[:3]])
                    if len(consolidated_items) > 3:
                        sku_list += f" (+{len(consolidated_items) - 3} more)"
                    server_logger.info(f"New order imported: {order_number} - {item_count} items ({sku_list})", source="XML Import")
                
                # Insert consolidated line items (duplicates merged, only Key Products)
                # AUTO-ASSIGN lot numbers from active_lots map
                for item in consolidated_items:
                    sku = item['sku']
                    quantity = item['quantity']
                    
                    # Look up active lot for this SKU
                    lot = active_lots.get(sku)
                    
                    if lot:
                        # Format as "SKU - LOT" for sku_lot field
                        sku_lot = f"{sku} - {lot}"
                        cursor.execute("""
                            INSERT INTO order_items_inbox (order_inbox_id, sku, sku_lot, quantity)
                            VALUES (%s, %s, %s, %s)
                        """, (order_inbox_id, sku, sku_lot, quantity))
                    else:
                        # No active lot found - insert without lot (will need manual assignment)
                        logger.warning(f"No active lot found for SKU {sku} in order {order_number}")
                        cursor.execute("""
                            INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                            VALUES (%s, %s, %s)
                        """, (order_inbox_id, sku, quantity))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully imported {orders_imported} new orders from Google Drive ({orders_skipped} skipped - no Key Products)")
        server_logger.info(f"Import summary: {orders_imported} imported, {orders_skipped} skipped (no Key Products), {total_orders_in_xml} total in XML", source="XML Import")
        return orders_imported
        
    except Exception as e:
        logger.error(f"Error importing from Google Drive: {str(e)}")
        server_logger.error(f"Import FAILED: {str(e)[:200]}", source="XML Import")
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
    logger.info(f"⏰ Business Hours: Monday-Friday 6 AM - 6 PM CST | Weekends OFF")
    
    error_count = 0
    max_errors = 5
    
    while True:
        try:
            # PRIORITY 1: Check business hours BEFORE any database queries
            if not is_business_hours():
                status = format_business_hours_status()
                logger.info(f"{status}")
                server_logger.info(f"XML Import sleeping: {status}", source="XML Import")
                sleep_duration = get_sleep_until_business_hours()
                logger.info(f"💤 Database sleeping for {sleep_duration}s to reduce compute time")
                time.sleep(sleep_duration)
                continue
            
            # PRIORITY 2: Check if workflow is enabled
            if not is_workflow_enabled('xml-import'):
                logger.info("⏸️ Workflow 'xml-import' is DISABLED - sleeping 60s")
                server_logger.warning("XML Import workflow DISABLED", source="XML Import")
                time.sleep(60)
                continue
            
            # PREFLIGHT CHECK: Do we have new files?
            has_changes, file_signature, check_duration = has_new_xml_files()
            
            if not has_changes:
                # No changes - skip processing, log skipped heartbeat
                heartbeat(WORKFLOW_NAME, HeartbeatPhase.SKIPPED, details={'reason': 'no_changes'})
                server_logger.info(f"XML Import: No file changes detected (check took {check_duration}ms)", source="XML Import")
                time.sleep(interval)
                continue
            
            # Changes detected - process files
            heartbeat(WORKFLOW_NAME, HeartbeatPhase.STARTED)
            logger.info(f"📥 Processing XML files from Drive (signature changed)")
            server_logger.info(f"XML Import: File changes detected, processing... (sig_len={len(file_signature)})", source="XML Import")
            
            imported = import_orders_from_drive()
            
            if imported > 0:
                logger.info(f"✅ Import complete: {imported} orders imported")
                server_logger.info(f"XML import: {imported} orders imported", source="Scheduler")
                # ONLY update timestamp when we actually imported something
                update_workflow_last_run('xml-import')
            else:
                logger.info(f"ℹ️ Import complete: No new orders")
                server_logger.info("XML import workflow completed (no new orders)", source="Scheduler")
            
            # Update polling state on success with file signature (for change detection)
            update_xml_polling_state(file_signature)
            
            # Cleanup old orders
            deleted = cleanup_old_orders()
            if deleted > 0:
                logger.info(f"🗑️ Cleanup complete: {deleted} old orders deleted")
            
            # Reset error count on success and log completion
            error_count = 0
            heartbeat(WORKFLOW_NAME, HeartbeatPhase.COMPLETED, records_processed=imported, details={'deleted': deleted})
            
            logger.info(f"😴 Next import check in {interval} seconds")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("⏹️ Scheduled import stopped by user")
            server_logger.info("XML Import: Stopped by user", source="XML Import")
            break
        except Exception as e:
            error_count += 1
            heartbeat(WORKFLOW_NAME, HeartbeatPhase.ERROR, details={'error': str(e)[:200]})
            logger.error(f"❌ Error in scheduled import (attempt {error_count}/{max_errors}): {str(e)}")
            server_logger.error(f"XML Import ERROR: {str(e)[:200]}", source="XML Import")
            
            if error_count >= max_errors:
                logger.error(f"🚨 Max errors ({max_errors}) reached - using exponential backoff")
                backoff = min(interval * (2 ** (error_count - max_errors)), 3600)  # Max 1 hour
                logger.info(f"😴 Backing off for {backoff}s due to errors")
                time.sleep(backoff)
            else:
                time.sleep(interval)

def run_once():
    """Run a single import cycle and exit (for manual triggers)"""
    logger.info(f"🎯 Running one-time XML import (manual trigger mode)")
    logger.info(f"📁 Data retention: {DATA_RETENTION_DAYS} days")
    server_logger.info("XML Import: Manual trigger started (--once mode)", source="XML Import")
    
    try:
        # Skip business hours check for manual triggers
        logger.info("⏩ Skipping business hours check (manual trigger)")
        
        # Check if workflow is enabled
        if not is_workflow_enabled('xml-import'):
            logger.warning("⏸️ Workflow 'xml-import' is DISABLED")
            server_logger.warning("XML Import: Workflow DISABLED, aborting manual run", source="XML Import")
            return 0
        
        # Check for new files
        has_changes, file_signature, check_duration = has_new_xml_files()
        server_logger.info(f"XML Import: File check complete - changes={has_changes}, sig_len={len(file_signature)}, duration={check_duration}ms", source="XML Import")
        
        if not has_changes:
            logger.info("ℹ️ No new XML files detected - nothing to import")
            server_logger.info("XML Import: No file changes detected, nothing to import", source="XML Import")
            return 0
        
        # Process files
        logger.info(f"📥 Processing XML files from Drive (signature changed)")
        server_logger.info(f"XML Import: Processing files from Google Drive", source="XML Import")
        
        imported = import_orders_from_drive()
        
        if imported > 0:
            logger.info(f"✅ Import complete: {imported} orders imported")
            server_logger.info(f"XML Import: {imported} orders imported successfully", source="XML Import")
            update_workflow_last_run('xml-import')
        else:
            logger.info(f"ℹ️ Import complete: No new orders")
            server_logger.info("XML Import: Completed with no new orders", source="XML Import")
        
        # Update polling state
        update_xml_polling_state(file_signature)
        
        # Cleanup old orders
        deleted = cleanup_old_orders()
        if deleted > 0:
            logger.info(f"🗑️ Cleanup complete: {deleted} old orders deleted")
            server_logger.info(f"XML Import: Cleaned up {deleted} old orders", source="XML Import")
        
        logger.info(f"✅ One-time import complete: {imported} orders imported")
        return imported
        
    except Exception as e:
        logger.error(f"❌ Error in one-time import: {str(e)}")
        server_logger.error(f"XML Import ERROR (manual): {str(e)[:200]}", source="XML Import")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == '__main__':
    # Check if running in one-shot mode (for manual triggers)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        run_once()
    else:
        run_scheduled_import()

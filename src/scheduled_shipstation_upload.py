#!/usr/bin/env python3
"""
Scheduled ShipStation Upload
Runs every 5 minutes to automatically upload pending orders to ShipStation
"""
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database.db_utils import get_connection
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    send_all_orders_to_shipstation,
    fetch_shipstation_orders_by_order_numbers
)
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

UPLOAD_INTERVAL_SECONDS = 300  # 5 minutes

def determine_carrier_and_service(ship_state, ship_country, ship_company):
    """
    Determine the correct carrier and service codes based on shipping validation rules.
    
    Rules:
    1. Hawaiian orders (HI) → FedEx 2Day
    2. Canadian orders (CA) → FedEx International Ground
    3. Benco orders → FedEx (will be validated for correct account later)
    4. Default → FedEx Ground or no specification (use ShipStation defaults)
    
    Returns:
        tuple: (carrier_code, service_code, service_name)
    """
    carrier_code = "fedex"  # Default to FedEx for all
    service_code = None
    service_name = None
    
    # Normalize inputs (strip whitespace and convert to uppercase for comparison)
    ship_state_normalized = ship_state.strip().upper() if ship_state else ''
    ship_country_normalized = ship_country.strip().upper() if ship_country else ''
    ship_company_normalized = ship_company.strip().upper() if ship_company else ''
    
    # Rule 1: Hawaiian orders MUST use FedEx 2Day
    if ship_state_normalized == 'HI':
        service_code = "fedex_2day"
        service_name = "FedEx 2Day"
        logger.info(f"Hawaiian order detected (state='{ship_state}') - setting service to FedEx 2Day")
        return carrier_code, service_code, service_name
    
    # Rule 2: Canadian orders MUST use International Ground
    if ship_country_normalized in ['CA', 'CANADA']:
        service_code = "fedex_international_ground"
        service_name = "FedEx International Ground"
        logger.info(f"Canadian order detected (country='{ship_country}') - setting service to FedEx International Ground")
        return carrier_code, service_code, service_name
    
    # Rule 3: Benco orders - use FedEx but will be validated for correct account
    # Note: We can't specify carrier_id in V1 API, so we rely on ShipStation automation rules
    # or post-upload validation to ensure correct Benco account is used
    if 'BENCO' in ship_company_normalized:
        logger.info(f"Benco order detected (company='{ship_company}') - will require account validation")
        # For now, don't specify service to allow ShipStation automation rules
        return carrier_code, None, None
    
    # Default: Let ShipStation use its default settings
    return carrier_code, None, None

def upload_pending_orders():
    """
    Upload pending orders from orders_inbox to ShipStation
    This is the same logic as the /api/upload_orders_to_shipstation endpoint
    """
    try:
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error('ShipStation API credentials not found')
            return 0
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch SKU-Lot mappings
        cursor.execute("""
            SELECT sku, lot
            FROM sku_lot 
            WHERE active = 1
        """)
        sku_lot_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch Product Name mappings
        cursor.execute("""
            SELECT sku, value
            FROM configuration_params
            WHERE category = 'Product Names'
        """)
        product_name_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch pending orders (exclude already shipped)
        cursor.execute("""
            SELECT id, order_number, order_date, customer_email, total_amount_cents,
                   ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                   bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
            FROM orders_inbox 
            WHERE status = 'pending'
              AND order_number NOT IN (SELECT order_number FROM shipped_orders)
        """)
        
        pending_orders = cursor.fetchall()
        
        if not pending_orders:
            logger.info('No pending orders to upload')
            return 0
        
        logger.info(f'Found {len(pending_orders)} pending orders to upload')
        
        # Build ShipStation order payloads (ONE ORDER PER SKU)
        shipstation_orders = []
        order_sku_map = []
        
        for order_row in pending_orders:
            (order_id, order_number, order_date, customer_email, total_amount_cents,
             ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
             bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone) = order_row
            
            # Get order items
            cursor.execute("""
                SELECT sku, quantity, unit_price_cents
                FROM order_items_inbox
                WHERE order_inbox_id = ?
            """, (order_id,))
            items = cursor.fetchall()
            
            # Determine carrier and service codes based on shipping rules
            carrier_code, service_code, service_name = determine_carrier_and_service(
                ship_state, ship_country, ship_company
            )
            
            # Create SEPARATE ShipStation order for EACH SKU
            for sku, qty, unit_price_cents in items:
                lot_number = sku_lot_map.get(sku, '')
                sku_with_lot = f"{sku} - {lot_number}" if lot_number else sku
                product_name = product_name_map.get(sku, f'Product {sku}')
                
                shipstation_order = {
                    'orderNumber': order_number,
                    'orderDate': order_date,
                    'orderStatus': 'awaiting_shipment',
                    'customerEmail': customer_email or '',
                    'billTo': {
                        'name': bill_name or '',
                        'company': bill_company or '',
                        'street1': bill_street1 or '',
                        'city': bill_city or '',
                        'state': bill_state or '',
                        'postalCode': bill_postal_code or '',
                        'country': bill_country or 'US',
                        'phone': bill_phone or ''
                    },
                    'shipTo': {
                        'name': ship_name or '',
                        'company': ship_company or '',
                        'street1': ship_street1 or '',
                        'city': ship_city or '',
                        'state': ship_state or '',
                        'postalCode': ship_postal_code or '',
                        'country': ship_country or 'US',
                        'phone': ship_phone or ''
                    },
                    'items': [{
                        'sku': sku_with_lot,
                        'name': product_name,
                        'quantity': qty,
                        'unitPrice': (unit_price_cents / 100) if unit_price_cents else 0
                    }],
                    'amountPaid': (unit_price_cents * qty / 100) if unit_price_cents else 0,
                    'taxAmount': 0,
                    'shippingAmount': 0
                }
                
                # Add carrier and service codes if determined
                if carrier_code:
                    shipstation_order['carrierCode'] = carrier_code
                if service_code:
                    shipstation_order['serviceCode'] = service_code
                
                shipstation_orders.append(shipstation_order)
                order_sku_map.append({
                    'order_inbox_id': order_id,
                    'sku': sku,
                    'order_number': order_number,
                    'sku_with_lot': sku_with_lot,
                    'carrier_code': carrier_code,
                    'service_code': service_code,
                    'service_name': service_name
                })
        
        # Check for duplicates in ShipStation
        unique_order_numbers = list(set([o['orderNumber'] for o in shipstation_orders]))
        
        existing_orders = fetch_shipstation_orders_by_order_numbers(
            api_key,
            api_secret,
            settings.SHIPSTATION_ORDERS_ENDPOINT,
            unique_order_numbers
        )
        
        # Create map of existing orders
        existing_order_map = {}
        for o in existing_orders:
            order_num = o.get('orderNumber', '').strip().upper()
            order_id = o.get('orderId')
            order_key = o.get('orderKey')
            
            items = o.get('items', [])
            if items and len(items) > 0:
                sku_with_lot = items[0].get('sku', '')
                sku = sku_with_lot.split(' - ')[0].strip() if ' - ' in sku_with_lot else sku_with_lot.strip()
                
                key = f"{order_num}_{sku}"
                existing_order_map[key] = {
                    'orderId': order_id,
                    'orderKey': order_key,
                    'sku': sku
                }
        
        # Filter out duplicates
        new_orders = []
        new_order_sku_map = []
        skipped_count = 0
        
        for idx, order in enumerate(shipstation_orders):
            order_num_upper = order['orderNumber'].strip().upper()
            order_sku_info = order_sku_map[idx]
            sku = order_sku_info['sku']
            
            key = f"{order_num_upper}_{sku}"
            
            if key in existing_order_map:
                # Already exists - mark as awaiting_shipment
                existing = existing_order_map[key]
                skipped_count += 1
                shipstation_id = existing['orderId'] or existing['orderKey']
                
                cursor.execute("""
                    INSERT OR IGNORE INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                    VALUES (?, ?, ?)
                """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                
                cursor.execute("""
                    UPDATE orders_inbox
                    SET status = 'awaiting_shipment',
                        shipstation_order_id = ?,
                        shipping_carrier_code = ?,
                        shipping_service_code = ?,
                        shipping_service_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (shipstation_id, 
                      order_sku_info.get('carrier_code'),
                      order_sku_info.get('service_code'),
                      order_sku_info.get('service_name'),
                      order_sku_info['order_inbox_id']))
            else:
                # New order - needs upload
                new_orders.append(order)
                new_order_sku_map.append(order_sku_info)
        
        if not new_orders:
            conn.commit()
            conn.close()
            logger.info(f'All {len(shipstation_orders)} orders already exist in ShipStation (skipped: {skipped_count})')
            return 0
        
        # Upload to ShipStation
        logger.info(f'Uploading {len(new_orders)} new orders to ShipStation')
        
        upload_results = send_all_orders_to_shipstation(
            new_orders,
            api_key,
            api_secret,
            settings.SHIPSTATION_CREATE_ORDERS_ENDPOINT
        )
        
        # Update database with results
        uploaded_count = 0
        failed_count = 0
        
        for idx, result in enumerate(upload_results):
            order_key = result.get('orderKey', '')
            order_id = result.get('orderId')
            success = result.get('success', False)
            error_msg = result.get('errorMessage')
            
            if idx < len(new_order_sku_map):
                order_sku_info = new_order_sku_map[idx]
                
                if success:
                    shipstation_id = order_id or order_key
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                        VALUES (?, ?, ?)
                    """, (order_sku_info['order_inbox_id'], order_sku_info['sku'], shipstation_id))
                    
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET shipstation_order_id = ?,
                            shipping_carrier_code = ?,
                            shipping_service_code = ?,
                            shipping_service_name = ?
                        WHERE id = ? AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
                    """, (shipstation_id,
                          order_sku_info.get('carrier_code'),
                          order_sku_info.get('service_code'),
                          order_sku_info.get('service_name'),
                          order_sku_info['order_inbox_id']))
                    
                    uploaded_count += 1
                else:
                    failed_count += 1
                    error_details = error_msg or result.get('message') or 'Unknown error'
                    logger.error(f"Upload failed for order {order_sku_info['order_number']}, SKU {order_sku_info['sku']}: {error_details}")
                    
                    cursor.execute("""
                        UPDATE orders_inbox 
                        SET status = 'failed',
                            failure_reason = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (error_details, order_sku_info['order_inbox_id']))
        
        # Update successfully uploaded orders
        cursor.execute("""
            UPDATE orders_inbox
            SET status = 'awaiting_shipment',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT DISTINCT order_inbox_id 
                FROM shipstation_order_line_items
            )
        """)
        
        conn.commit()
        
        # Fetch carrier details for newly uploaded orders to capture carrier_id
        if uploaded_count > 0:
            logger.info(f"Fetching carrier details for {uploaded_count} newly uploaded orders...")
            try:
                # Get unique order numbers that were just uploaded
                uploaded_order_numbers = list(set([info['order_number'] for info in new_order_sku_map[:uploaded_count]]))
                
                # Fetch full order details from ShipStation
                uploaded_orders_details = fetch_shipstation_orders_by_order_numbers(
                    api_key,
                    api_secret,
                    settings.SHIPSTATION_ORDERS_ENDPOINT,
                    uploaded_order_numbers
                )
                
                # Extract and update carrier information
                for order_detail in uploaded_orders_details:
                    order_num = order_detail.get('orderNumber', '').strip().upper()
                    carrier_code = order_detail.get('carrierCode')
                    service_code = order_detail.get('serviceCode')
                    
                    # ShipStation may return carrierId in advancedOptions or other fields
                    # Check multiple possible locations
                    carrier_id = None
                    advanced_options = order_detail.get('advancedOptions', {})
                    if advanced_options:
                        carrier_id = advanced_options.get('carrierId')
                    
                    # If still no carrier_id, try other fields
                    if not carrier_id:
                        carrier_id = order_detail.get('carrierId')
                    
                    # Update database with carrier information
                    if carrier_code or service_code or carrier_id:
                        cursor.execute("""
                            UPDATE orders_inbox
                            SET shipping_carrier_id = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE order_number = ?
                        """, (carrier_id, order_num))
                        
                        if carrier_id:
                            logger.debug(f"Captured carrier_id '{carrier_id}' for order {order_num}")
                
                conn.commit()
                logger.info(f"Carrier details updated for uploaded orders")
                
            except Exception as e:
                logger.error(f"Error fetching carrier details: {e}", exc_info=True)
                # Don't fail the whole upload if carrier fetch fails
        
        conn.close()
        
        logger.info(f'Upload complete: {uploaded_count} uploaded, {failed_count} failed, {skipped_count} skipped')
        return uploaded_count
        
    except Exception as e:
        logger.error(f'Error uploading orders: {str(e)}', exc_info=True)
        return 0

def run_scheduled_upload():
    """Main loop - runs every 5 minutes"""
    logger.info(f"Starting scheduled ShipStation upload (every {UPLOAD_INTERVAL_SECONDS}s)")
    
    while True:
        try:
            logger.info("Running scheduled upload...")
            
            uploaded = upload_pending_orders()
            
            if uploaded > 0:
                logger.info(f"Successfully uploaded {uploaded} orders to ShipStation")
            
            logger.info(f"Next upload in {UPLOAD_INTERVAL_SECONDS} seconds")
            time.sleep(UPLOAD_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("Scheduled upload stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduled upload: {str(e)}")
            time.sleep(UPLOAD_INTERVAL_SECONDS)

if __name__ == '__main__':
    run_scheduled_upload()

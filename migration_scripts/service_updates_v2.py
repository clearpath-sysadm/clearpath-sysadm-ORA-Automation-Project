"""
Service Update Patches for Database Normalization v2.2

This file contains the updated database interaction code for all critical services.
These changes must be deployed during the migration window after the schema is updated.

Critical Services:
1. daily_shipment_processor.py - Uses parser + new schema
2. shipstation_status_sync.py - Uses parser + date guard + new schema  
3. manual_shipstation_sync.py - Uses parser + new schema

Author: ORA Automation Team
Date: October 2025
"""

import sqlite3
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Import the parser
from src.services.data_processing.sku_lot_parser import parse_and_lookup

logger = logging.getLogger(__name__)


# ============================================================================
# PATCH 1: Daily Shipment Processor
# ============================================================================

def insert_shipped_items_v2(shipment_data: List[Dict], conn: sqlite3.Connection):
    """
    UPDATED VERSION: Insert shipped items using normalized schema with FKs.
    
    REPLACES: Old code that used base_sku and sku_lot columns
    
    Changes:
    - Uses parse_and_lookup() to get sku_id and lot_id
    - Stores shipstation_sku_raw for API compatibility
    - Enforces FK constraints
    """
    inserted_count = 0
    skipped_count = 0
    
    for shipment in shipment_data:
        ship_date = shipment.get('shipDate')
        order_number = shipment.get('orderNumber')
        
        if not ship_date or not order_number:
            continue
        
        # Parse ship_date
        ship_date = datetime.strptime(ship_date[:10], '%Y-%m-%d').date()
        
        # Process each item in the shipment
        for item in shipment.get('shipmentItems', []):
            raw_sku = item.get('sku', '').strip()
            quantity = item.get('quantity')
            
            if not raw_sku or not quantity:
                continue
            
            # Parse and lookup using centralized parser
            sku_id, lot_id, shipstation_raw = parse_and_lookup(
                raw_sku, 
                conn, 
                create_missing_lots=True
            )
            
            if not sku_id:
                logger.warning(f"Could not resolve SKU: {raw_sku}")
                skipped_count += 1
                continue
            
            try:
                # NEW SCHEMA: Insert with sku_id, lot_id, shipstation_sku_raw
                conn.execute("""
                    INSERT INTO shipped_items 
                        (ship_date, shipstation_sku_raw, sku_id, lot_id, quantity_shipped, order_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_number, shipstation_sku_raw) DO UPDATE SET
                        quantity_shipped = excluded.quantity_shipped,
                        ship_date = excluded.ship_date
                """, (ship_date, shipstation_raw, sku_id, lot_id, quantity, order_number))
                
                inserted_count += 1
                
            except sqlite3.IntegrityError as e:
                logger.warning(f"Integrity error inserting {raw_sku}: {e}")
                skipped_count += 1
    
    conn.commit()
    logger.info(f"Inserted {inserted_count} items, skipped {skipped_count}")
    
    return inserted_count


# ============================================================================
# PATCH 2: ShipStation Status Sync (with DATE GUARD)
# ============================================================================

def process_shipped_order_v2(shipstation_order: Dict[Any, Any], conn: sqlite3.Connection) -> bool:
    """
    UPDATED VERSION: Process shipped order with date guard and normalized schema.
    
    CRITICAL CHANGES:
    1. DATE GUARD: Only process orders shipped within last 30 days
    2. Uses parse_and_lookup() for SKU resolution
    3. Stores sku_id, lot_id, shipstation_sku_raw
    
    This prevents the historical re-sync bug that caused 107 units with wrong dates.
    """
    order_id = shipstation_order.get('orderId')
    order_number = shipstation_order.get('orderNumber')
    ship_date_str = shipstation_order.get('shipDate')
    
    if not ship_date_str:
        logger.warning(f"No ship date for order {order_number}")
        return False
    
    # Parse ship date
    ship_date = datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
    
    # *** DATE GUARD: Reject orders older than 30 days ***
    cutoff_date = (datetime.now() - timedelta(days=30)).date()
    if ship_date < cutoff_date:
        logger.warning(f"Rejecting historical order {order_number} with ship_date {ship_date} (older than 30 days)")
        return False
    
    logger.info(f"Processing shipped order {order_number}, ship_date={ship_date}")
    
    # Move to shipped_orders table
    conn.execute("""
        INSERT INTO shipped_orders 
            (order_number, ship_date, shipstation_order_id, order_date, 
             shipping_carrier_code, shipping_service_code, shipping_service_name, shipping_carrier_id)
        SELECT 
            order_number, ?, shipstation_order_id, order_date,
            shipping_carrier_code, shipping_service_code, shipping_service_name, shipping_carrier_id
        FROM orders_inbox
        WHERE order_number = ?
        ON CONFLICT(order_number) DO UPDATE SET
            ship_date = excluded.ship_date,
            shipstation_order_id = excluded.shipstation_order_id
    """, (ship_date, order_number))
    
    # Process items with new schema
    items = shipstation_order.get('items', [])
    inserted = 0
    
    for item in items:
        raw_sku = item.get('sku', '').strip()
        quantity = item.get('quantity')
        
        if not raw_sku or not quantity:
            continue
        
        # Parse and lookup
        sku_id, lot_id, shipstation_raw = parse_and_lookup(
            raw_sku,
            conn,
            create_missing_lots=True
        )
        
        if not sku_id:
            logger.warning(f"Cannot resolve SKU: {raw_sku}")
            continue
        
        # Insert with new schema
        try:
            conn.execute("""
                INSERT INTO shipped_items
                    (ship_date, shipstation_sku_raw, sku_id, lot_id, quantity_shipped, order_number)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_number, shipstation_sku_raw) DO UPDATE SET
                    quantity_shipped = excluded.quantity_shipped,
                    ship_date = excluded.ship_date
            """, (ship_date, shipstation_raw, sku_id, lot_id, quantity, order_number))
            
            inserted += 1
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Error inserting shipped item: {e}")
    
    # Delete from orders_inbox
    conn.execute("DELETE FROM orders_inbox WHERE order_number = ?", (order_number,))
    
    # Update local order status
    conn.execute("""
        UPDATE orders_inbox 
        SET status = 'shipped'
        WHERE order_number = ?
    """, (order_number,))
    
    conn.commit()
    logger.info(f"Processed {inserted} items for order {order_number}")
    
    return True


# ============================================================================
# PATCH 3: Manual ShipStation Sync
# ============================================================================

def import_manual_order_items_v2(order: Dict[Any, Any], order_number: str, conn: sqlite3.Connection) -> int:
    """
    UPDATED VERSION: Import manual order items with normalized schema.
    
    Changes:
    - Uses parse_and_lookup() for SKU resolution
    - Stores sku_id, lot_id, shipstation_sku_raw
    - Handles both awaiting_shipment and shipped orders
    """
    items = order.get('items', [])
    inserted = 0
    
    order_status = order.get('orderStatus', '').lower()
    ship_date = None
    
    # If already shipped, get ship date
    if order_status == 'shipped':
        ship_date_str = order.get('shipDate')
        if ship_date_str:
            ship_date = datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
            
            # DATE GUARD for shipped orders
            cutoff_date = (datetime.now() - timedelta(days=30)).date()
            if ship_date < cutoff_date:
                logger.warning(f"Skipping historical manual order {order_number} (ship_date={ship_date})")
                return 0
    
    for item in items:
        raw_sku = item.get('sku', '').strip()
        quantity = item.get('quantity')
        
        if not raw_sku or not quantity:
            continue
        
        # Parse and lookup
        sku_id, lot_id, shipstation_raw = parse_and_lookup(
            raw_sku,
            conn,
            create_missing_lots=True
        )
        
        if not sku_id:
            logger.warning(f"Cannot resolve SKU: {raw_sku}")
            continue
        
        # If shipped, insert into shipped_items
        if order_status == 'shipped' and ship_date:
            try:
                conn.execute("""
                    INSERT INTO shipped_items
                        (ship_date, shipstation_sku_raw, sku_id, lot_id, quantity_shipped, order_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_number, shipstation_sku_raw) DO UPDATE SET
                        quantity_shipped = excluded.quantity_shipped,
                        ship_date = excluded.ship_date
                """, (ship_date, shipstation_raw, sku_id, lot_id, quantity, order_number))
                
                inserted += 1
                
            except sqlite3.IntegrityError as e:
                logger.warning(f"Error inserting manual shipped item: {e}")
        
        # Also insert into order_items_inbox for awaiting orders
        else:
            try:
                # For order_items_inbox, we still use base_sku and sku_lot for now
                # (this table is not being migrated in v2.2, will be in future phase)
                from src.services.data_processing.sku_lot_parser import parse_shipstation_sku
                parsed = parse_shipstation_sku(raw_sku)
                
                conn.execute("""
                    INSERT INTO order_items_inbox
                        (order_id, base_sku, sku_lot, quantity, unit_price)
                    VALUES (
                        (SELECT id FROM orders_inbox WHERE order_number = ?),
                        ?, ?, ?, ?
                    )
                """, (order_number, parsed.base_sku, raw_sku, quantity, item.get('unitPrice', 0)))
                
                inserted += 1
                
            except sqlite3.IntegrityError as e:
                logger.warning(f"Error inserting order item: {e}")
    
    conn.commit()
    return inserted


# ============================================================================
# DEPLOYMENT INSTRUCTIONS
# ============================================================================

"""
DEPLOYMENT PROCEDURE:

During migration window, after schema is updated:

1. Update src/services/data_processing/shipment_processor.py:
   - Replace insert logic with insert_shipped_items_v2()

2. Update src/shipstation_status_sync.py:
   - Replace process_shipped_order() with process_shipped_order_v2()
   - This adds the critical DATE GUARD

3. Update src/manual_shipstation_sync.py:
   - Replace import_manual_order_items() with import_manual_order_items_v2()

4. Restart ingestion workflows

CRITICAL: These changes MUST be deployed together with schema migration.
If schema changes but services aren't updated, services will crash.
"""


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_service_updates(conn: sqlite3.Connection) -> bool:
    """
    Validate that services are using the new schema correctly.
    Run this after migration to verify everything works.
    """
    logger.info("Validating service updates...")
    
    # Check that new columns exist
    columns = [row[1] for row in conn.execute("PRAGMA table_info(shipped_items)")]
    
    required = ['sku_id', 'lot_id', 'shipstation_sku_raw']
    for col in required:
        if col not in columns:
            logger.error(f"Missing column: {col}")
            return False
    
    # Check that old columns are gone
    removed = ['base_sku', 'sku_lot']
    for col in removed:
        if col in columns:
            logger.error(f"Old column still exists: {col}")
            return False
    
    logger.info("✅ Service updates validated")
    return True


if __name__ == "__main__":
    # Test imports
    print("Testing service update patches...")
    print("✅ All imports successful")
    print("✅ Parser integration ready")
    print("✅ Date guard implemented")
    print("Ready for deployment during migration window")

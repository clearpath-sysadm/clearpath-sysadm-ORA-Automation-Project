#!/usr/bin/env python3
"""
Import Initial Lot Inventory from 9/19/2025 Baseline

This utility imports the September 19, 2025 initial inventory baseline
into the lot_inventory table, assigning quantities to the oldest lot
for each SKU (FIFO approach).
"""

import sqlite3
import sys
from datetime import datetime

BASELINE_DATE = '2025-09-19'

def import_initial_lot_inventory():
    """Import initial inventory from configuration_params into lot_inventory"""
    conn = sqlite3.connect('ora.db')
    cursor = conn.cursor()
    
    try:
        print(f"🔄 Importing initial lot inventory from {BASELINE_DATE} baseline...")
        
        # Get initial inventory for all SKUs
        cursor.execute("""
            SELECT sku, CAST(value AS INTEGER) as qty
            FROM configuration_params
            WHERE category = 'InitialInventory' 
              AND parameter_name = 'EOD_Prior_Week'
            ORDER BY sku
        """)
        
        initial_inventory = cursor.fetchall()
        print(f"✅ Found {len(initial_inventory)} SKUs with initial inventory")
        
        imported = 0
        skipped = 0
        
        for sku, initial_qty in initial_inventory:
            # Find the oldest lot for this SKU (FIFO)
            cursor.execute("""
                SELECT lot 
                FROM sku_lot 
                WHERE sku = ? AND active = 1
                ORDER BY lot ASC
                LIMIT 1
            """, (sku,))
            
            lot_result = cursor.fetchone()
            
            if not lot_result:
                print(f"⚠️  No active lot found for SKU {sku}, skipping")
                skipped += 1
                continue
            
            lot = lot_result[0]
            
            # Check if this lot inventory already exists
            cursor.execute("""
                SELECT id FROM lot_inventory 
                WHERE sku = ? AND lot = ?
            """, (sku, lot))
            
            if cursor.fetchone():
                print(f"⏭️  SKU {sku} / Lot {lot} already exists, skipping")
                skipped += 1
                continue
            
            # Insert lot inventory record
            cursor.execute("""
                INSERT INTO lot_inventory 
                (sku, lot, initial_qty, manual_adjustment, received_date, status, notes)
                VALUES (?, ?, ?, 0, ?, 'active', ?)
            """, (
                sku, 
                lot, 
                initial_qty, 
                BASELINE_DATE,
                f'Imported from 9/19/2025 baseline inventory (EOD Prior Week)'
            ))
            
            print(f"✅ Imported SKU {sku} / Lot {lot}: {initial_qty:,} units")
            imported += 1
        
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"🎉 Import complete!")
        print(f"   Imported: {imported} lot records")
        print(f"   Skipped: {skipped} (already exist or no lot mapping)")
        print(f"{'='*60}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during import: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = import_initial_lot_inventory()
    sys.exit(0 if success else 1)

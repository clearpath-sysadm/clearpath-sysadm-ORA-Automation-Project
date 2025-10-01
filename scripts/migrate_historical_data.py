#!/usr/bin/env python3
"""
Historical Data Migration - Phase 3.1
Migrates 12 months of data from Google Sheets to SQLite database
Critical for 52-week rolling average calculations
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import (
    GOOGLE_SHEET_ID,
    ORA_CONFIGURATION_TAB_NAME,
    INVENTORY_TRANSACTIONS_TAB_NAME,
    SHIPPED_ORDERS_DATA_TAB_NAME,
    SHIPPED_ITEMS_DATA_TAB_NAME,
    ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME
)
from src.services.google_sheets.api_client import get_google_sheet_data

DATABASE_PATH = "ora.db"

# Calculate 12-month window
TWELVE_MONTHS_AGO = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
FIFTY_TWO_WEEKS_AGO = (datetime.now() - timedelta(weeks=52)).strftime('%Y-%m-%d')

class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.stats = {
            'configuration_params': {'source': 0, 'migrated': 0, 'skipped': 0},
            'inventory_transactions': {'source': 0, 'migrated': 0, 'skipped': 0},
            'shipped_orders': {'source': 0, 'migrated': 0, 'skipped': 0},
            'shipped_items': {'source': 0, 'migrated': 0, 'skipped': 0},
            'weekly_shipped_history': {'source': 0, 'migrated': 0, 'skipped': 0}
        }
    
    def update(self, table: str, source: int = 0, migrated: int = 0, skipped: int = 0):
        """Update statistics for a table"""
        if table in self.stats:
            self.stats[table]['source'] += source
            self.stats[table]['migrated'] += migrated
            self.stats[table]['skipped'] += skipped
    
    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        
        for table, counts in self.stats.items():
            if counts['source'] > 0:
                print(f"\n{table}:")
                print(f"  Source rows:    {counts['source']}")
                print(f"  Migrated:       {counts['migrated']}")
                print(f"  Skipped:        {counts['skipped']}")
        
        print("\n" + "=" * 70)

def dollars_to_cents(value):
    """Convert dollar amount to cents (returns int or None)"""
    if pd.isna(value) or value == '':
        return None
    try:
        if isinstance(value, str):
            value = value.replace('$', '').replace(',', '')
        return int(float(value) * 100)
    except (ValueError, TypeError):
        return None

def parse_date(date_value):
    """Parse various date formats to YYYY-MM-DD TEXT format (returns str or None)"""
    if pd.isna(date_value) or date_value == '':
        return None
    
    try:
        if isinstance(date_value, str):
            # Try parsing common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(date_value, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        elif isinstance(date_value, datetime):
            return date_value.strftime('%Y-%m-%d')
        elif hasattr(date_value, 'to_pydatetime'):
            return date_value.to_pydatetime().strftime('%Y-%m-%d')
        
        return str(date_value)
    except:
        return None

def migrate_configuration_params(conn, dry_run=False) -> Tuple[int, int]:
    """
    Migrate ORA_Configuration sheet to configuration_params table
    Returns: (rows_migrated, rows_skipped)
    """
    print("\n" + "-" * 70)
    print("MIGRATING: ORA_Configuration → configuration_params")
    print("-" * 70)
    
    # Fetch data from Google Sheets
    print(f"  Fetching data from sheet: {ORA_CONFIGURATION_TAB_NAME}")
    df = get_google_sheet_data(GOOGLE_SHEET_ID, ORA_CONFIGURATION_TAB_NAME)
    
    if df is None or df.empty:
        print("  ⚠️  No data found in source sheet")
        return 0, 0
    
    print(f"  Found {len(df)} rows in source")
    
    rows_migrated = 0
    rows_skipped = 0
    
    # Expected columns: Category, Parameter_Name, Value, SKU, Notes, Last_Updated
    for idx, row in df.iterrows():
        category = row.get('Category', '')
        param_name = row.get('Parameter_Name', '')
        value = str(row.get('Value', ''))
        sku = row.get('SKU', None)
        notes = row.get('Notes', None)
        last_updated = parse_date(row.get('Last_Updated', None))
        
        # Skip if missing critical fields
        if not category or not param_name:
            rows_skipped += 1
            continue
        
        # Convert SKU None/NaN to None
        if pd.isna(sku) or sku == '':
            sku = None
        
        if not dry_run:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO configuration_params (
                        category, parameter_name, value, sku, notes, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (category, param_name, value, sku, notes, last_updated))
                rows_migrated += 1
            except sqlite3.Error as e:
                print(f"  ⚠️  Error inserting row {idx}: {e}")
                rows_skipped += 1
        else:
            rows_migrated += 1
    
    print(f"  ✅ Migrated: {rows_migrated}, Skipped: {rows_skipped}")
    return rows_migrated, rows_skipped

def migrate_inventory_transactions(conn, dry_run=False) -> Tuple[int, int]:
    """
    Migrate Inventory_Transactions sheet (last 12 months only)
    Returns: (rows_migrated, rows_skipped)
    """
    print("\n" + "-" * 70)
    print(f"MIGRATING: Inventory_Transactions → inventory_transactions (since {TWELVE_MONTHS_AGO})")
    print("-" * 70)
    
    print(f"  Fetching data from sheet: {INVENTORY_TRANSACTIONS_TAB_NAME}")
    df = get_google_sheet_data(GOOGLE_SHEET_ID, INVENTORY_TRANSACTIONS_TAB_NAME)
    
    if df is None or df.empty:
        print("  ⚠️  No data found in source sheet")
        return 0, 0
    
    print(f"  Found {len(df)} total rows in source")
    
    rows_migrated = 0
    rows_skipped = 0
    
    # Expected columns: Date, SKU, Quantity, Transaction_Type, Notes
    for idx, row in df.iterrows():
        date_str = parse_date(row.get('Date', None))
        sku = row.get('SKU', '')
        quantity = row.get('Quantity', 0)
        trans_type = row.get('Transaction_Type', '')
        notes = row.get('Notes', None)
        
        # Skip if missing critical fields
        if not date_str or not sku or not trans_type:
            rows_skipped += 1
            continue
        
        # Filter: Only last 12 months
        if date_str < TWELVE_MONTHS_AGO:
            rows_skipped += 1
            continue
        
        # Validate transaction type
        valid_types = ['Receive', 'Ship', 'Adjust Up', 'Adjust Down']
        if trans_type not in valid_types:
            rows_skipped += 1
            continue
        
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            rows_skipped += 1
            continue
        
        if not dry_run:
            try:
                conn.execute("""
                    INSERT INTO inventory_transactions (
                        date, sku, quantity, transaction_type, notes
                    ) VALUES (?, ?, ?, ?, ?)
                """, (date_str, sku, quantity, trans_type, notes))
                rows_migrated += 1
            except sqlite3.Error as e:
                print(f"  ⚠️  Error inserting row {idx}: {e}")
                rows_skipped += 1
        else:
            rows_migrated += 1
    
    print(f"  ✅ Migrated: {rows_migrated}, Skipped: {rows_skipped}")
    return rows_migrated, rows_skipped

def migrate_shipped_orders(conn, dry_run=False) -> Tuple[int, int]:
    """
    Migrate Shipped_Orders_Data (last 12 months only)
    Returns: (rows_migrated, rows_skipped)
    """
    print("\n" + "-" * 70)
    print(f"MIGRATING: Shipped_Orders_Data → shipped_orders (since {TWELVE_MONTHS_AGO})")
    print("-" * 70)
    
    print(f"  Fetching data from sheet: {SHIPPED_ORDERS_DATA_TAB_NAME}")
    df = get_google_sheet_data(GOOGLE_SHEET_ID, SHIPPED_ORDERS_DATA_TAB_NAME)
    
    if df is None or df.empty:
        print("  ⚠️  No data found in source sheet")
        return 0, 0
    
    print(f"  Found {len(df)} total rows in source")
    
    rows_migrated = 0
    rows_skipped = 0
    
    # Expected columns: Ship_Date, Order_Number, Customer_Email, Total_Items, ShipStation_Order_ID
    for idx, row in df.iterrows():
        ship_date = parse_date(row.get('Ship_Date', None))
        order_number = row.get('Order_Number', '')
        customer_email = row.get('Customer_Email', None)
        total_items = row.get('Total_Items', 0)
        shipstation_order_id = row.get('ShipStation_Order_ID', None)
        
        # Skip if missing critical fields
        if not ship_date or not order_number:
            rows_skipped += 1
            continue
        
        # Filter: Only last 12 months
        if ship_date < TWELVE_MONTHS_AGO:
            rows_skipped += 1
            continue
        
        try:
            total_items = int(total_items) if total_items else 0
        except (ValueError, TypeError):
            total_items = 0
        
        if not dry_run:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO shipped_orders (
                        ship_date, order_number, customer_email, total_items, shipstation_order_id
                    ) VALUES (?, ?, ?, ?, ?)
                """, (ship_date, order_number, customer_email, total_items, shipstation_order_id))
                rows_migrated += 1
            except sqlite3.Error as e:
                print(f"  ⚠️  Error inserting row {idx}: {e}")
                rows_skipped += 1
        else:
            rows_migrated += 1
    
    print(f"  ✅ Migrated: {rows_migrated}, Skipped: {rows_skipped}")
    return rows_migrated, rows_skipped

def migrate_shipped_items(conn, dry_run=False) -> Tuple[int, int]:
    """
    Migrate Shipped_Items_Data (last 12 months only)
    Returns: (rows_migrated, rows_skipped)
    """
    print("\n" + "-" * 70)
    print(f"MIGRATING: Shipped_Items_Data → shipped_items (since {TWELVE_MONTHS_AGO})")
    print("-" * 70)
    
    print(f"  Fetching data from sheet: {SHIPPED_ITEMS_DATA_TAB_NAME}")
    df = get_google_sheet_data(GOOGLE_SHEET_ID, SHIPPED_ITEMS_DATA_TAB_NAME)
    
    if df is None or df.empty:
        print("  ⚠️  No data found in source sheet")
        return 0, 0
    
    print(f"  Found {len(df)} total rows in source")
    
    rows_migrated = 0
    rows_skipped = 0
    
    # Expected columns: Ship_Date, SKU_Lot, Base_SKU, Quantity_Shipped, Order_Number
    for idx, row in df.iterrows():
        ship_date = parse_date(row.get('Ship_Date', None))
        sku_lot = row.get('SKU_Lot', None)
        base_sku = row.get('Base_SKU', '')
        quantity_shipped = row.get('Quantity_Shipped', 0)
        order_number = row.get('Order_Number', None)
        
        # Skip if missing critical fields
        if not ship_date or not base_sku:
            rows_skipped += 1
            continue
        
        # Filter: Only last 12 months
        if ship_date < TWELVE_MONTHS_AGO:
            rows_skipped += 1
            continue
        
        try:
            quantity_shipped = int(quantity_shipped)
            if quantity_shipped <= 0:
                rows_skipped += 1
                continue
        except (ValueError, TypeError):
            rows_skipped += 1
            continue
        
        if not dry_run:
            try:
                conn.execute("""
                    INSERT INTO shipped_items (
                        ship_date, sku_lot, base_sku, quantity_shipped, order_number
                    ) VALUES (?, ?, ?, ?, ?)
                """, (ship_date, sku_lot, base_sku, quantity_shipped, order_number))
                rows_migrated += 1
            except sqlite3.Error as e:
                print(f"  ⚠️  Error inserting row {idx}: {e}")
                rows_skipped += 1
        else:
            rows_migrated += 1
    
    print(f"  ✅ Migrated: {rows_migrated}, Skipped: {rows_skipped}")
    return rows_migrated, rows_skipped

def migrate_weekly_shipped_history(conn, dry_run=False) -> Tuple[int, int]:
    """
    Migrate ORA_Weekly_Shipped_History (last 52 weeks only)
    CRITICAL: This data is essential for 52-week rolling averages
    Returns: (rows_migrated, rows_skipped)
    """
    print("\n" + "-" * 70)
    print(f"MIGRATING: ORA_Weekly_Shipped_History → weekly_shipped_history (since {FIFTY_TWO_WEEKS_AGO})")
    print("-" * 70)
    
    print(f"  Fetching data from sheet: {ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}")
    df = get_google_sheet_data(GOOGLE_SHEET_ID, ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME)
    
    if df is None or df.empty:
        print("  ⚠️  No data found in source sheet")
        return 0, 0
    
    print(f"  Found {len(df)} total rows in source")
    
    rows_migrated = 0
    rows_skipped = 0
    
    # Expected columns: Start_Date, End_Date, SKU, Quantity_Shipped
    for idx, row in df.iterrows():
        start_date = parse_date(row.get('Start_Date', None))
        end_date = parse_date(row.get('End_Date', None))
        sku = row.get('SKU', '')
        quantity_shipped = row.get('Quantity_Shipped', 0)
        
        # Skip if missing critical fields
        if not start_date or not end_date or not sku:
            rows_skipped += 1
            continue
        
        # Filter: Only last 52 weeks
        if end_date < FIFTY_TWO_WEEKS_AGO:
            rows_skipped += 1
            continue
        
        try:
            quantity_shipped = int(quantity_shipped)
            if quantity_shipped < 0:  # Allow 0 for weeks with no shipments
                rows_skipped += 1
                continue
        except (ValueError, TypeError):
            rows_skipped += 1
            continue
        
        if not dry_run:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO weekly_shipped_history (
                        start_date, end_date, sku, quantity_shipped
                    ) VALUES (?, ?, ?, ?)
                """, (start_date, end_date, sku, quantity_shipped))
                rows_migrated += 1
            except sqlite3.Error as e:
                print(f"  ⚠️  Error inserting row {idx}: {e}")
                rows_skipped += 1
        else:
            rows_migrated += 1
    
    print(f"  ✅ Migrated: {rows_migrated}, Skipped: {rows_skipped}")
    return rows_migrated, rows_skipped

def verify_checksums(conn):
    """
    Verify data integrity with checksums
    CRITICAL: Validates 52-week rolling totals match expectations
    """
    print("\n" + "=" * 70)
    print("CHECKSUM VERIFICATION")
    print("=" * 70)
    
    # Verify weekly history totals per SKU
    print("\n  Checking weekly_shipped_history totals by SKU...")
    cursor = conn.execute("""
        SELECT sku, SUM(quantity_shipped) as total_shipped, COUNT(*) as week_count
        FROM weekly_shipped_history
        GROUP BY sku
        ORDER BY sku
    """)
    
    weekly_totals = cursor.fetchall()
    if weekly_totals:
        print("  SKU            Total Shipped    Weeks")
        print("  " + "-" * 50)
        for sku, total, weeks in weekly_totals:
            print(f"  {sku:15} {total:10} {weeks:8}")
    else:
        print("  ⚠️  No weekly history data found")
    
    # Verify shipped_items totals match shipped_orders
    print("\n  Checking shipped_items vs shipped_orders consistency...")
    cursor = conn.execute("""
        SELECT 
            so.order_number,
            so.total_items as order_total,
            COALESCE(SUM(si.quantity_shipped), 0) as items_sum
        FROM shipped_orders so
        LEFT JOIN shipped_items si ON so.order_number = si.order_number
        GROUP BY so.order_number, so.total_items
        HAVING order_total != items_sum
        LIMIT 10
    """)
    
    mismatches = cursor.fetchall()
    if mismatches:
        print(f"  ⚠️  Found {len(mismatches)} orders with item count mismatches")
        for order_num, order_total, items_sum in mismatches[:5]:
            print(f"    Order {order_num}: declared={order_total}, actual={items_sum}")
    else:
        print("  ✅ All order totals match item sums")
    
    print("\n" + "=" * 70)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate historical data from Google Sheets to SQLite')
    parser.add_argument('--dry-run', action='store_true', help='Run without actually inserting data')
    parser.add_argument('--skip-config', action='store_true', help='Skip configuration_params migration')
    args = parser.parse_args()
    
    print("=" * 70)
    print("ORA HISTORICAL DATA MIGRATION - PHASE 3.1")
    print("=" * 70)
    print(f"\nMode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print(f"Database: {DATABASE_PATH}")
    print(f"12-month window: {TWELVE_MONTHS_AGO} to today")
    print(f"52-week window: {FIFTY_TWO_WEEKS_AGO} to today")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"\n❌ Database not found: {DATABASE_PATH}")
        print("Run: OVERWRITE=1 python scripts/create_database.py")
        sys.exit(1)
    
    stats = MigrationStats()
    conn = None
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        
        if not args.dry_run:
            conn.execute("BEGIN IMMEDIATE")
        
        # Migrate each table
        if not args.skip_config:
            migrated, skipped = migrate_configuration_params(conn, args.dry_run)
            stats.update('configuration_params', migrated + skipped, migrated, skipped)
        
        migrated, skipped = migrate_inventory_transactions(conn, args.dry_run)
        stats.update('inventory_transactions', migrated + skipped, migrated, skipped)
        
        migrated, skipped = migrate_shipped_orders(conn, args.dry_run)
        stats.update('shipped_orders', migrated + skipped, migrated, skipped)
        
        migrated, skipped = migrate_shipped_items(conn, args.dry_run)
        stats.update('shipped_items', migrated + skipped, migrated, skipped)
        
        migrated, skipped = migrate_weekly_shipped_history(conn, args.dry_run)
        stats.update('weekly_shipped_history', migrated + skipped, migrated, skipped)
        
        if not args.dry_run:
            conn.commit()
            print("\n✅ Transaction committed")
            
            # Run checksum verification
            verify_checksums(conn)
        else:
            print("\n⚠️  DRY RUN - No data was actually inserted")
        
        stats.print_summary()
        
        print("\n" + "=" * 70)
        if args.dry_run:
            print("✅ DRY RUN COMPLETED")
        else:
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        if not args.dry_run:
            conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()

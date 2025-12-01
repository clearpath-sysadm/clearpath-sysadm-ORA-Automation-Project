#!/usr/bin/env python3
"""
Backfill Daily Inventory Snapshots

This script populates the inventory_daily_snapshots table with historical EOD inventory
for each day starting from the baseline date (September 19, 2025) up to today.

Calculation: EOD = Previous Day EOD + Receives + Adjustments - Shipments
"""

import os
import psycopg2
from datetime import datetime, timedelta
from decimal import Decimal

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

# Baseline date - the day our initial inventory counts are valid
BASELINE_DATE = '2025-09-19'

# SKUs we track
SKUS = ['17612', '17904', '17914', '18675', '18795']

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def get_initial_inventory(conn):
    """Get the initial inventory from configuration_params (EOD_Prior_Week)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sku, value::integer 
        FROM configuration_params 
        WHERE category = 'InitialInventory' AND parameter_name = 'EOD_Prior_Week'
    """)
    result = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    return result

def get_transactions_by_date(conn):
    """Get all inventory transactions grouped by date and SKU"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, sku, transaction_type, SUM(quantity) as total_qty
        FROM inventory_transactions
        GROUP BY date, sku, transaction_type
        ORDER BY date, sku
    """)
    
    # Structure: {date: {sku: {'receive': qty, 'adjustment': qty}}}
    transactions = {}
    for row in cursor.fetchall():
        date_str, sku, txn_type, qty = row
        if date_str not in transactions:
            transactions[date_str] = {}
        if sku not in transactions[date_str]:
            transactions[date_str][sku] = {'receive': 0, 'adjustment': 0}
        
        # Map transaction types to categories
        if txn_type.lower() in ['receive', 'received']:
            transactions[date_str][sku]['receive'] += qty
        else:
            # Adjustments can be positive or negative
            transactions[date_str][sku]['adjustment'] += qty
    
    cursor.close()
    return transactions

def get_shipments_by_date(conn):
    """Get all shipments grouped by date and SKU"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ship_date, base_sku, SUM(quantity_shipped) as total_shipped
        FROM shipped_items
        WHERE base_sku IS NOT NULL AND base_sku != ''
        GROUP BY ship_date, base_sku
        ORDER BY ship_date, base_sku
    """)
    
    # Structure: {date: {sku: shipped_qty}}
    shipments = {}
    for row in cursor.fetchall():
        date_str, sku, qty = row
        if date_str not in shipments:
            shipments[date_str] = {}
        shipments[date_str][sku] = qty
    
    cursor.close()
    return shipments

def insert_snapshot(conn, snapshot_date, sku, eod_quantity, source='backfill'):
    """Insert or update a daily snapshot"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory_daily_snapshots (snapshot_date, sku, eod_quantity, source, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (snapshot_date, sku) 
        DO UPDATE SET eod_quantity = EXCLUDED.eod_quantity, source = EXCLUDED.source
    """, (snapshot_date, sku, eod_quantity, source))
    cursor.close()

def backfill_snapshots():
    """Main backfill function"""
    conn = get_connection()
    
    # Get baseline inventory
    initial_inventory = get_initial_inventory(conn)
    print(f"Initial Inventory (as of {BASELINE_DATE}):")
    for sku, qty in sorted(initial_inventory.items()):
        print(f"  {sku}: {qty:,}")
    
    # Get all transactions and shipments
    transactions = get_transactions_by_date(conn)
    shipments = get_shipments_by_date(conn)
    
    print(f"\nFound transactions from {len(transactions)} days")
    print(f"Found shipments from {len(shipments)} days")
    
    # Start with baseline inventory
    current_inventory = {sku: initial_inventory.get(sku, 0) for sku in SKUS}
    
    # Parse dates
    start_date = datetime.strptime(BASELINE_DATE, '%Y-%m-%d').date()
    end_date = datetime.now().date()
    
    # Iterate through each day
    current_date = start_date
    days_processed = 0
    
    print(f"\nProcessing {(end_date - start_date).days + 1} days from {start_date} to {end_date}...")
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # For each SKU, calculate the EOD
        for sku in SKUS:
            # Get transactions for this date/sku
            day_txns = transactions.get(date_str, {}).get(sku, {'receive': 0, 'adjustment': 0})
            receives = day_txns['receive']
            adjustments = day_txns['adjustment']
            
            # Get shipments for this date/sku
            shipped = shipments.get(date_str, {}).get(sku, 0)
            
            # Calculate EOD: Previous EOD + Receives + Adjustments - Shipped
            eod = current_inventory[sku] + receives + adjustments - shipped
            
            # Insert the snapshot
            insert_snapshot(conn, current_date, sku, eod, 'backfill')
            
            # Update current inventory for next day
            current_inventory[sku] = eod
        
        days_processed += 1
        if days_processed % 10 == 0:
            print(f"  Processed {days_processed} days (through {date_str})...")
        
        current_date += timedelta(days=1)
    
    conn.commit()
    
    # Print final inventory
    print(f"\nFinal EOD Inventory (as of {end_date}):")
    for sku, qty in sorted(current_inventory.items()):
        print(f"  {sku}: {qty:,}")
    
    # Compare to inventory_current
    cursor = conn.cursor()
    cursor.execute("SELECT sku, quantity FROM inventory_current ORDER BY sku")
    current_db = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    
    print(f"\nComparison to inventory_current table:")
    print(f"  {'SKU':<8} {'Calculated':<12} {'inventory_current':<18} {'Diff'}")
    print(f"  {'-'*50}")
    for sku in SKUS:
        calc = current_inventory[sku]
        actual = current_db.get(sku, 0)
        diff = calc - actual
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        match = "✓" if diff == 0 else "✗"
        print(f"  {sku:<8} {calc:<12,} {actual:<18,} {diff_str} {match}")
    
    conn.close()
    print(f"\nBackfill complete! Processed {days_processed} days.")

if __name__ == '__main__':
    backfill_snapshots()

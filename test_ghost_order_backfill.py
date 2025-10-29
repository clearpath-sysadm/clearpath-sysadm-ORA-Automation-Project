#!/usr/bin/env python3
"""
Test script for ghost order backfill functionality.
Tests on order 100528 (known ghost order).
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection
from src.services.ghost_order_backfill import backfill_ghost_orders

def main():
    print("=" * 80)
    print("GHOST ORDER BACKFILL TEST")
    print("=" * 80)
    print()
    
    # Check before backfill
    print("BEFORE BACKFILL:")
    print("-" * 80)
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            o.id,
            o.order_number,
            o.shipstation_order_id,
            o.status,
            o.total_items,
            COUNT(oi.id) as item_count
        FROM orders_inbox o
        LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
        WHERE o.order_number = '100528'
        GROUP BY o.id, o.order_number, o.shipstation_order_id, o.status, o.total_items
    """)
    
    row = cursor.fetchone()
    if row:
        print(f"Order 100528:")
        print(f"  ID: {row[0]}")
        print(f"  ShipStation ID: {row[2]}")
        print(f"  Status: {row[3]}")
        print(f"  Total Items (field): {row[4]}")
        print(f"  Actual Item Count: {row[5]}")
    else:
        print("Order 100528 not found!")
        conn.close()
        return
    
    conn.close()
    print()
    
    # Run backfill
    print("RUNNING BACKFILL:")
    print("-" * 80)
    
    conn = get_connection()
    try:
        metrics = backfill_ghost_orders(conn)
        print(f"Ghost Orders Found: {metrics['ghost_orders_found']}")
        print(f"Backfilled: {metrics['backfilled']}")
        print(f"Cancelled: {metrics['cancelled']}")
        print(f"Work in Progress: {metrics['work_in_progress']}")
        print(f"Errors: {metrics['errors']}")
        print(f"Rate Limited: {metrics['rate_limited']}")
    finally:
        conn.close()
    
    print()
    
    # Check after backfill
    print("AFTER BACKFILL:")
    print("-" * 80)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            o.id,
            o.order_number,
            o.status,
            o.total_items,
            COUNT(oi.id) as item_count
        FROM orders_inbox o
        LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
        WHERE o.order_number = '100528'
        GROUP BY o.id, o.order_number, o.status, o.total_items
    """)
    
    row = cursor.fetchone()
    if row:
        print(f"Order 100528:")
        print(f"  Status: {row[2]}")
        print(f"  Total Items (field): {row[3]}")
        print(f"  Actual Item Count: {row[4]}")
        print()
        
        # Show items
        cursor.execute("""
            SELECT sku, quantity, unit_price_cents
            FROM order_items_inbox
            WHERE order_inbox_id = %s
        """, (row[0],))
        
        items = cursor.fetchall()
        if items:
            print(f"  Items ({len(items)}):")
            for sku, qty, price_cents in items:
                print(f"    - SKU: {sku}, Qty: {qty}, Price: ${price_cents/100:.2f}")
        else:
            print("  No items found")
    
    conn.close()
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
ORDER AUDIT TOOL - READ-ONLY
Compares XML orders (normalized/consolidated) with actual shipments.
Detects discrepancies: over-shipments, under-shipments, missing orders.

SAFE: This script only reads data, never modifies the database.
"""

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

def get_db_connection():
    """Get database connection with proper settings."""
    conn = sqlite3.connect('ora.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def normalize_sku(sku: str) -> Tuple[str, str]:
    """
    Extract base SKU and lot from a SKU string.
    Returns: (base_sku, lot_number)
    Examples:
        "17612 - 250300" -> ("17612", "250300")
        "17612-250300" -> ("17612", "250300")
        "17612" -> ("17612", "")
    """
    if not sku:
        return "", ""
    
    sku = sku.strip()
    if '-' in sku:
        parts = sku.split('-', 1)
        base = parts[0].strip()
        lot = parts[1].strip() if len(parts) > 1 else ""
        return base, lot
    return sku, ""

def get_xml_orders(conn) -> Dict[str, Dict[str, int]]:
    """
    Get normalized/consolidated XML orders from order_items_inbox.
    Returns: {order_number: {base_sku: total_quantity}}
    """
    cursor = conn.cursor()
    
    # Get all order items from inbox
    cursor.execute("""
        SELECT oi.order_number, oii.sku, oii.quantity
        FROM order_items_inbox oii
        JOIN orders_inbox oi ON oii.order_inbox_id = oi.id
        ORDER BY oi.order_number, oii.sku
    """)
    
    # Consolidate by order + base SKU (strip lot numbers for comparison)
    xml_orders = defaultdict(lambda: defaultdict(int))
    
    for row in cursor.fetchall():
        order_number = row['order_number']
        sku = row['sku']
        quantity = row['quantity']
        
        # Normalize SKU to base (ignore lot for consolidation)
        base_sku, _ = normalize_sku(sku)
        
        xml_orders[order_number][base_sku] += quantity
    
    return dict(xml_orders)

def get_shipped_orders(conn) -> Dict[str, Dict[str, int]]:
    """
    Get actual shipped orders from shipped_items.
    Returns: {order_number: {base_sku: total_quantity}}
    """
    cursor = conn.cursor()
    
    # Get all shipped items
    cursor.execute("""
        SELECT order_number, base_sku, quantity_shipped
        FROM shipped_items
        WHERE order_number IS NOT NULL
        ORDER BY order_number, base_sku
    """)
    
    # Consolidate by order + base SKU
    shipped_orders = defaultdict(lambda: defaultdict(int))
    
    for row in cursor.fetchall():
        order_number = row['order_number']
        base_sku = row['base_sku']
        quantity = row['quantity_shipped']
        
        shipped_orders[order_number][base_sku] += quantity
    
    return dict(shipped_orders)

def compare_orders(xml_orders: Dict, shipped_orders: Dict) -> Dict:
    """
    Compare XML orders vs shipped orders and find discrepancies.
    
    Returns dict with:
        - perfect_matches: [(order_num, sku, qty)]
        - over_shipped: [(order_num, sku, xml_qty, shipped_qty, diff)]
        - under_shipped: [(order_num, sku, xml_qty, shipped_qty, diff)]
        - missing_shipments: [(order_num, sku, xml_qty)]
        - extra_shipments: [(order_num, sku, shipped_qty)]
        - missing_orders: [order_num]
    """
    results = {
        'perfect_matches': [],
        'over_shipped': [],
        'under_shipped': [],
        'missing_shipments': [],
        'extra_shipments': [],
        'missing_orders': []
    }
    
    all_orders = set(xml_orders.keys()) | set(shipped_orders.keys())
    
    for order_num in sorted(all_orders):
        xml_items = xml_orders.get(order_num, {})
        shipped_items = shipped_orders.get(order_num, {})
        
        # Check if order exists in both
        if not xml_items and shipped_items:
            # Order was shipped but not in XML (manual order?)
            for sku, qty in shipped_items.items():
                results['extra_shipments'].append((order_num, sku, qty))
            continue
        
        if xml_items and not shipped_items:
            # Order in XML but never shipped
            results['missing_orders'].append(order_num)
            for sku, qty in xml_items.items():
                results['missing_shipments'].append((order_num, sku, qty))
            continue
        
        # Compare SKUs within the order
        all_skus = set(xml_items.keys()) | set(shipped_items.keys())
        
        for sku in sorted(all_skus):
            xml_qty = xml_items.get(sku, 0)
            shipped_qty = shipped_items.get(sku, 0)
            
            if xml_qty == 0 and shipped_qty > 0:
                # SKU shipped but not in original order
                results['extra_shipments'].append((order_num, sku, shipped_qty))
            elif xml_qty > 0 and shipped_qty == 0:
                # SKU ordered but not shipped
                results['missing_shipments'].append((order_num, sku, xml_qty))
            elif xml_qty == shipped_qty:
                # Perfect match
                results['perfect_matches'].append((order_num, sku, xml_qty))
            elif shipped_qty > xml_qty:
                # Over-shipped
                diff = shipped_qty - xml_qty
                results['over_shipped'].append((order_num, sku, xml_qty, shipped_qty, diff))
            else:
                # Under-shipped
                diff = xml_qty - shipped_qty
                results['under_shipped'].append((order_num, sku, xml_qty, shipped_qty, diff))
    
    return results

def print_audit_report(results: Dict):
    """Print formatted audit report."""
    print("\n" + "="*80)
    print("ORDER AUDIT REPORT - XML vs Actual Shipments")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Summary
    print("\n📊 SUMMARY")
    print("-" * 80)
    print(f"✅ Perfect Matches:      {len(results['perfect_matches']):,} SKU line items")
    print(f"⚠️  Over-Shipped:         {len(results['over_shipped'])} discrepancies")
    print(f"⚠️  Under-Shipped:        {len(results['under_shipped'])} discrepancies")
    print(f"❌ Missing Shipments:    {len(results['missing_shipments'])} SKUs not shipped")
    print(f"➕ Extra Shipments:      {len(results['extra_shipments'])} SKUs shipped but not in XML")
    print(f"📦 Missing Orders:       {len(results['missing_orders'])} orders never shipped")
    
    # Detailed Discrepancies
    if results['over_shipped']:
        print("\n\n🔴 OVER-SHIPPED (Shipped MORE than ordered)")
        print("-" * 80)
        print(f"{'Order Number':<15} {'SKU':<10} {'Ordered':<10} {'Shipped':<10} {'Excess':<10}")
        print("-" * 80)
        for order_num, sku, xml_qty, shipped_qty, diff in results['over_shipped']:
            print(f"{order_num:<15} {sku:<10} {xml_qty:<10} {shipped_qty:<10} +{diff:<10}")
    
    if results['under_shipped']:
        print("\n\n🟡 UNDER-SHIPPED (Shipped LESS than ordered)")
        print("-" * 80)
        print(f"{'Order Number':<15} {'SKU':<10} {'Ordered':<10} {'Shipped':<10} {'Short':<10}")
        print("-" * 80)
        for order_num, sku, xml_qty, shipped_qty, diff in results['under_shipped']:
            print(f"{order_num:<15} {sku:<10} {xml_qty:<10} {shipped_qty:<10} -{diff:<10}")
    
    if results['missing_shipments']:
        print("\n\n⚫ MISSING SHIPMENTS (Ordered but NOT shipped)")
        print("-" * 80)
        print(f"{'Order Number':<15} {'SKU':<10} {'Ordered Qty':<15}")
        print("-" * 80)
        for order_num, sku, xml_qty in results['missing_shipments'][:20]:  # Show first 20
            print(f"{order_num:<15} {sku:<10} {xml_qty:<15}")
        if len(results['missing_shipments']) > 20:
            print(f"\n... and {len(results['missing_shipments']) - 20} more")
    
    if results['extra_shipments']:
        print("\n\n➕ EXTRA SHIPMENTS (Shipped but NOT in XML - manual orders?)")
        print("-" * 80)
        print(f"{'Order Number':<15} {'SKU':<10} {'Shipped Qty':<15}")
        print("-" * 80)
        for order_num, sku, shipped_qty in results['extra_shipments'][:20]:  # Show first 20
            print(f"{order_num:<15} {sku:<10} {shipped_qty:<15}")
        if len(results['extra_shipments']) > 20:
            print(f"\n... and {len(results['extra_shipments']) - 20} more")
    
    if results['missing_orders']:
        print("\n\n📦 MISSING ORDERS (Never shipped)")
        print("-" * 80)
        for order_num in results['missing_orders'][:20]:  # Show first 20
            print(f"  {order_num}")
        if len(results['missing_orders']) > 20:
            print(f"\n... and {len(results['missing_orders']) - 20} more")
    
    # Success indicator
    total_issues = (
        len(results['over_shipped']) +
        len(results['under_shipped']) +
        len(results['missing_shipments']) +
        len(results['extra_shipments']) +
        len(results['missing_orders'])
    )
    
    print("\n" + "="*80)
    if total_issues == 0:
        print("✅ SUCCESS: All orders match perfectly! No discrepancies found.")
    else:
        print(f"⚠️  ATTENTION: Found {total_issues} total discrepancies requiring review.")
    print("="*80 + "\n")

def main():
    """Main execution."""
    try:
        print("🔍 Starting Order Audit...")
        print("📖 READ-ONLY: This script will not modify any data\n")
        
        conn = get_db_connection()
        
        print("📥 Loading XML orders from order_items_inbox...")
        xml_orders = get_xml_orders(conn)
        xml_count = sum(len(items) for items in xml_orders.values())
        print(f"   Found {len(xml_orders)} orders with {xml_count} SKU line items")
        
        print("\n📤 Loading shipped orders from shipped_items...")
        shipped_orders = get_shipped_orders(conn)
        shipped_count = sum(len(items) for items in shipped_orders.values())
        print(f"   Found {len(shipped_orders)} orders with {shipped_count} SKU line items")
        
        print("\n🔄 Comparing orders...")
        results = compare_orders(xml_orders, shipped_orders)
        
        print_audit_report(results)
        
        conn.close()
        
        # Exit code based on results
        total_issues = (
            len(results['over_shipped']) +
            len(results['under_shipped']) +
            len(results['missing_shipments']) +
            len(results['extra_shipments']) +
            len(results['missing_orders'])
        )
        
        return 0 if total_issues == 0 else 1
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())

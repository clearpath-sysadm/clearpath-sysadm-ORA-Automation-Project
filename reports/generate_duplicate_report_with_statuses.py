#!/usr/bin/env python3
"""
Duplicate Orders Report Generator - Production Script
======================================================
This script generates a comprehensive report of duplicate orders in ShipStation
including their current order statuses, which helps determine which duplicates to delete.

Usage:
    python reports/generate_duplicate_report_with_statuses.py

Output:
    - Console report with all duplicate details
    - CSV export option for further analysis
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/runner/workspace')

from src.services.database.pg_utils import get_connection
from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request
from config.settings import settings


def fetch_order_details_from_shipstation(api_key, api_secret, order_id):
    """Fetch detailed order information from ShipStation by order ID"""
    headers = get_shipstation_headers(api_key, api_secret)
    
    url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
    
    response = make_api_request(
        url=url,
        method='GET',
        headers=headers,
        timeout=30
    )
    
    if response and response.status_code == 200:
        return response.json()
    return None


def parse_shipstation_ids(shipstation_ids_text):
    """Parse the comma-separated ShipStation IDs from database"""
    if not shipstation_ids_text:
        return []
    
    # Handle both comma-separated and array-like formats
    ids_text = shipstation_ids_text.strip('{}').strip()
    ids = [id.strip() for id in ids_text.split(',') if id.strip()]
    
    # Convert to integers
    return [int(id) for id in ids if id.isdigit()]


def main():
    print(f"\n{'='*140}")
    print(f"DUPLICATE ORDERS REPORT - WITH SHIPSTATION STATUSES")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*140}\n")
    
    # Get ShipStation credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        print("ERROR: ShipStation credentials not found")
        print("Make sure SHIPSTATION_API_KEY and SHIPSTATION_API_SECRET are set")
        sys.exit(1)
    
    # Connect to database
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all unresolved duplicate alerts
    cursor.execute("""
        SELECT 
            id,
            order_number,
            base_sku,
            duplicate_count,
            shipstation_ids,
            first_detected,
            last_seen,
            notes
        FROM duplicate_order_alerts
        WHERE status != 'resolved'
        ORDER BY order_number, base_sku
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("✅ NO UNRESOLVED DUPLICATES FOUND")
        print(f"\n{'='*140}\n")
        conn.close()
        return
    
    print(f"🚨 FOUND {len(duplicates)} UNRESOLVED DUPLICATE ALERTS\n")
    print(f"{'='*140}\n")
    
    # Prepare CSV export data
    csv_rows = []
    csv_rows.append([
        "Order Number", "Base SKU", "Duplicate Count", 
        "SS Order ID", "SS Order Key", "Status", "Created Date",
        "Full SKU", "Quantity", "Customer Name", "Ship To Country"
    ])
    
    for idx, (alert_id, order_number, base_sku, dup_count, ss_ids_text, first_detected, last_seen, notes) in enumerate(duplicates, 1):
        print(f"\n{'─'*140}")
        print(f"[{idx}] ORDER #{order_number} + SKU {base_sku}")
        print(f"    Duplicate Count: {dup_count} | First Detected: {first_detected} | Last Seen: {last_seen}")
        if notes:
            print(f"    Notes: {notes}")
        print(f"{'─'*140}\n")
        
        # Parse ShipStation IDs
        ss_ids = parse_shipstation_ids(ss_ids_text)
        
        if not ss_ids:
            print(f"  ⚠️  WARNING: No ShipStation IDs found in database record\n")
            continue
        
        print(f"  SHIPSTATION VERSIONS ({len(ss_ids)} found):")
        print(f"  {'─'*136}\n")
        
        # Fetch details for each ShipStation order
        for version_num, ss_order_id in enumerate(ss_ids, 1):
            order_details = fetch_order_details_from_shipstation(api_key, api_secret, ss_order_id)
            
            if not order_details:
                print(f"    Version {version_num}: ShipStation ID {ss_order_id}")
                print(f"      ❌ ERROR: Could not fetch order details from ShipStation")
                print()
                continue
            
            # Extract key information
            order_key = order_details.get('orderKey', 'N/A')
            order_status = order_details.get('orderStatus', 'unknown')
            create_date = order_details.get('createDate', 'N/A')
            customer_name = f"{order_details.get('billTo', {}).get('name', 'N/A')}"
            ship_country = order_details.get('shipTo', {}).get('country', 'N/A')
            
            items = order_details.get('items', [])
            matching_items = [item for item in items if item.get('sku', '').startswith(base_sku)]
            
            # Display order information
            print(f"    Version {version_num}: ShipStation ID {ss_order_id} | Order Key: {order_key}")
            print(f"      📊 Status: {order_status.upper()}")
            print(f"      📅 Created: {create_date}")
            print(f"      👤 Customer: {customer_name}")
            print(f"      🌍 Ship To: {ship_country}")
            print(f"      📦 Matching Items ({len(matching_items)}):")
            
            for item in matching_items:
                item_sku = item.get('sku', 'N/A')
                quantity = item.get('quantity', 0)
                item_name = item.get('name', 'N/A')
                
                print(f"         - SKU: {item_sku} | Qty: {quantity} | {item_name}")
                
                # Add to CSV export
                csv_rows.append([
                    order_number, base_sku, dup_count,
                    ss_order_id, order_key, order_status, create_date,
                    item_sku, quantity, customer_name, ship_country
                ])
            
            print()
        
        # Check local database
        cursor.execute("""
            SELECT 
                oi.id,
                oi.status,
                oi.shipstation_order_id,
                oi.created_at,
                STRING_AGG(oii.sku || ' (Qty: ' || oii.quantity || ')', ', ') as items
            FROM orders_inbox oi
            LEFT JOIN order_items_inbox oii ON oi.id = oii.order_inbox_id
            WHERE oi.order_number = %s
              AND oii.sku LIKE %s
            GROUP BY oi.id, oi.status, oi.shipstation_order_id, oi.created_at
            ORDER BY oi.created_at DESC
        """, (order_number, f"{base_sku}%"))
        
        local_records = cursor.fetchall()
        
        if local_records:
            print(f"  LOCAL DATABASE RECORDS ({len(local_records)} found):")
            print(f"  {'─'*136}\n")
            
            for local_id, status, ss_id, created, items in local_records:
                print(f"    Local ID: {local_id} | SS Order ID: {ss_id or 'NULL'}")
                print(f"      Status: {status}")
                print(f"      Created: {created}")
                print(f"      Items: {items}")
                print()
    
    conn.close()
    
    print(f"\n{'='*140}")
    print(f"SUMMARY")
    print(f"{'='*140}")
    print(f"Total duplicate alerts: {len(duplicates)}")
    print(f"Total CSV rows (including header): {len(csv_rows)}")
    print(f"{'='*140}\n")
    
    # Ask user if they want to export to CSV
    print("💾 To export this report to CSV, uncomment the export code at the end of this script")
    print("   CSV file will be saved to: /tmp/duplicate_orders_with_statuses.csv\n")
    
    # Uncomment the following lines to export to CSV:
    # import csv
    # with open('/tmp/duplicate_orders_with_statuses.csv', 'w', newline='') as f:
    #     writer = csv.writer(f)
    #     writer.writerows(csv_rows)
    # print("✅ CSV export saved to /tmp/duplicate_orders_with_statuses.csv\n")
    
    print(f"{'='*140}")
    print(f"RECOMMENDED ACTIONS:")
    print(f"{'='*140}")
    print(f"1. For each duplicate, keep the order with status 'shipped' (if it exists)")
    print(f"2. Delete orders with status 'awaiting_shipment' that are duplicates")
    print(f"3. Use the Order Management tool (order-management.html) to delete orders")
    print(f"4. After deletion, the duplicate scanner will mark these as resolved")
    print(f"{'='*140}\n")


if __name__ == "__main__":
    main()

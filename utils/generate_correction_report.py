#!/usr/bin/env python3
"""
Generate CSV report for corrected shipments.
Documents mis-shipped orders and their corrections.
"""

import sqlite3
import csv
from datetime import datetime
import requests
import os

def get_shipstation_credentials():
    api_key = os.getenv('SHIPSTATION_API_KEY')
    api_secret = os.getenv('SHIPSTATION_API_SECRET')
    if not api_key or not api_secret:
        raise ValueError("ShipStation credentials not found")
    return api_key, api_secret

def get_discrepancy_data(date):
    """Get comparison data for a specific date"""
    response = requests.get(f'http://localhost:5000/api/order_comparison?start_date={date}&end_date={date}')
    if response.status_code != 200:
        raise Exception(f"Failed to get comparison data: {response.text}")
    
    data = response.json()
    # Filter for discrepancies only
    return [order for order in data['comparison'] if order['status'] == 'discrepancy']

def get_order_details(order_number):
    """Get full order details from database"""
    conn = sqlite3.connect('ora.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ship_name, ship_company, ship_city, ship_state, customer_email
        FROM orders_inbox 
        WHERE order_number = ?
    """, (order_number,))
    
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def main():
    # Configuration
    report_date = '2025-10-06'  # Yesterday's date
    corrected_order_start = 100518  # First corrected order number
    
    print("="*100)
    print("SHIPMENT CORRECTION REPORT GENERATOR")
    print("="*100)
    print(f"\nGenerating report for date: {report_date}\n")
    
    # Get discrepancy data
    print("Fetching discrepancy data...")
    discrepancies = get_discrepancy_data(report_date)
    print(f"Found {len(discrepancies)} discrepancies\n")
    
    # Define delivery status for specific orders
    delivered_orders = ['688195', '688595']  # Already delivered
    return_to_shipper_orders = ['688005', '688025', '688085', '688245']  # Return to shipper requested
    
    # Prepare CSV data
    csv_data = []
    corrected_order_num = corrected_order_start
    
    for disc in discrepancies:
        order_num = disc['order_number']
        print(f"Processing {order_num}...")
        
        # Determine delivery status
        if order_num in delivered_orders:
            delivery_status = 'Delivered'
        elif order_num in return_to_shipper_orders:
            delivery_status = 'Return to Shipper Requested'
        else:
            delivery_status = 'Unknown'
        
        # Get customer details
        details = get_order_details(order_num)
        
        if details:
            csv_data.append({
                'Date': report_date,
                'Original Order': order_num,
                'Customer Name': details['ship_name'],
                'Company': details['ship_company'] or 'N/A',
                'Location': f"{details['ship_city']}, {details['ship_state']}",
                'Items Shipped (INCORRECT)': disc['ss_sku'],
                'Qty Shipped': disc['ss_qty'],
                'Items Ordered (CORRECT)': disc['xml_sku'],
                'Qty Ordered': disc['xml_qty'],
                'Incorrect Order Status': delivery_status,
                'Corrected Order Number': corrected_order_num,
                'Status': 'Correction Created',
                'Customer Email': details['customer_email'] or 'N/A'
            })
            corrected_order_num += 1
    
    # Write CSV
    filename = f'shipment_corrections_{report_date}.csv'
    
    if csv_data:
        fieldnames = [
            'Date', 'Original Order', 'Customer Name', 'Company', 'Location',
            'Items Shipped (INCORRECT)', 'Qty Shipped',
            'Items Ordered (CORRECT)', 'Qty Ordered',
            'Incorrect Order Status',
            'Corrected Order Number', 'Status', 'Customer Email'
        ]
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\n✅ Report generated: {filename}")
        print(f"   Total corrections: {len(csv_data)}")
        print(f"   Corrected orders: {corrected_order_start} - {corrected_order_num - 1}")
        print("\nReport Summary:")
        print("-" * 80)
        for row in csv_data:
            print(f"  {row['Original Order']} → {row['Corrected Order Number']}: {row['Company']}")
            print(f"    Wrong: {row['Items Shipped (INCORRECT)']} (x{row['Qty Shipped']})")
            print(f"    Right: {row['Items Ordered (CORRECT)']} (x{row['Qty Ordered']})")
            print(f"    Status: {row['Incorrect Order Status']}")
            print()
    else:
        print("❌ No data to report")
    
    print(f"\n📧 Ready to email: {filename}")
    print("This report can be sent to both the client and owner.")

if __name__ == '__main__':
    main()

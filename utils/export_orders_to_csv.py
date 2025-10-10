#!/usr/bin/env python3
"""
Export ShipStation orders to CSV for shipping.
Fetches order data and creates CSV with all shipping details.
"""

import requests
import os
import csv
from datetime import datetime

def get_shipstation_credentials():
    api_key = os.getenv('SHIPSTATION_API_KEY')
    api_secret = os.getenv('SHIPSTATION_API_SECRET')
    if not api_key or not api_secret:
        raise ValueError("ShipStation credentials not found")
    return api_key, api_secret

def fetch_orders_from_shipstation(api_key, api_secret, order_numbers):
    """Fetch orders from ShipStation by order number"""
    all_orders = []
    
    for order_num in order_numbers:
        print(f"Fetching order {order_num} from ShipStation...")
        
        response = requests.get(
            f'https://ssapi.shipstation.com/orders?orderNumber={order_num}',
            auth=(api_key, api_secret)
        )
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            
            # Filter for awaiting_shipment status if there are duplicates
            awaiting_orders = [o for o in orders if o.get('orderStatus') == 'awaiting_shipment']
            
            if awaiting_orders:
                print(f"  Found {len(awaiting_orders)} order(s) awaiting shipment")
                all_orders.extend(awaiting_orders)
            else:
                print(f"  No orders awaiting shipment, found {len(orders)} order(s) total")
                if orders:
                    all_orders.extend(orders)
        else:
            print(f"  ERROR: {response.status_code} - {response.text}")
    
    return all_orders

def export_to_csv(orders, filename):
    """Export orders to CSV with all shipping details"""
    
    if not orders:
        print("No orders to export")
        return
    
    csv_data = []
    
    for order in orders:
        # Get shipping info
        ship_to = order.get('shipTo', {})
        
        # Get items
        items = order.get('items', [])
        
        for item in items:
            csv_data.append({
                'Order Number': order.get('orderNumber'),
                'Order Date': order.get('orderDate', '').split('T')[0],
                'Order Status': order.get('orderStatus'),
                'Customer Name': ship_to.get('name'),
                'Company': ship_to.get('company') or '',
                'Street1': ship_to.get('street1'),
                'Street2': ship_to.get('street2') or '',
                'City': ship_to.get('city'),
                'State': ship_to.get('state'),
                'Postal Code': ship_to.get('postalCode'),
                'Country': ship_to.get('country'),
                'Phone': ship_to.get('phone') or '',
                'Email': order.get('customerEmail') or '',
                'Item SKU': item.get('sku'),
                'Item Name': item.get('name'),
                'Quantity': item.get('quantity'),
                'Carrier Code': order.get('carrierCode') or '',
                'Service Code': order.get('serviceCode') or '',
                'Package Code': order.get('packageCode') or '',
                'Internal Notes': order.get('internalNotes') or ''
            })
    
    # Write to CSV
    fieldnames = [
        'Order Number', 'Order Date', 'Order Status',
        'Customer Name', 'Company', 
        'Street1', 'Street2', 'City', 'State', 'Postal Code', 'Country',
        'Phone', 'Email',
        'Item SKU', 'Item Name', 'Quantity',
        'Carrier Code', 'Service Code', 'Package Code',
        'Internal Notes'
    ]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"\n✅ CSV exported: {filename}")
    print(f"   Total rows: {len(csv_data)}")
    return filename

def main():
    print("="*100)
    print("SHIPSTATION ORDER EXPORT TO CSV")
    print("="*100)
    
    # Orders to fetch
    order_numbers = ['100518', '100519']
    
    print(f"\nFetching orders: {', '.join(order_numbers)}")
    print("(Will select 'awaiting_shipment' status if duplicates exist)\n")
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    
    # Fetch orders
    orders = fetch_orders_from_shipstation(api_key, api_secret, order_numbers)
    
    if orders:
        print(f"\nTotal orders found: {len(orders)}")
        for order in orders:
            print(f"  - {order.get('orderNumber')}: {order.get('orderStatus')} ({len(order.get('items', []))} items)")
        
        # Export to CSV
        filename = f"orders_to_ship_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export_to_csv(orders, filename)
        
        print(f"\n📦 Ready to ship orders from: {filename}")
    else:
        print("\n❌ No orders found")

if __name__ == '__main__':
    main()

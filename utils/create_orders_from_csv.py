#!/usr/bin/env python3
"""
Create new manual orders in ShipStation from CSV file.
Reads order data from CSV and creates orders with new order numbers.
"""

import csv
import requests
import os
from datetime import datetime

def get_shipstation_credentials():
    api_key = os.getenv('SHIPSTATION_API_KEY')
    api_secret = os.getenv('SHIPSTATION_API_SECRET')
    if not api_key or not api_secret:
        raise ValueError("ShipStation credentials not found")
    return api_key, api_secret

def read_csv_orders(filename):
    """Read orders from CSV file"""
    orders = []
    
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            orders.append(row)
    
    return orders

def create_shipstation_order(api_key, api_secret, order_data, new_order_number):
    """Create a new order in ShipStation"""
    
    # Build ShipStation order payload
    payload = {
        "orderNumber": new_order_number,
        "orderDate": datetime.now().isoformat(),
        "orderStatus": "awaiting_shipment",
        "customerEmail": order_data.get('Email') or "noemail@oracare.com",
        "billTo": {
            "name": order_data.get('Customer Name'),
            "company": order_data.get('Company') or None,
            "street1": order_data.get('Street1'),
            "street2": order_data.get('Street2') or None,
            "city": order_data.get('City'),
            "state": order_data.get('State'),
            "postalCode": order_data.get('Postal Code'),
            "country": order_data.get('Country') or "US",
            "phone": order_data.get('Phone') or None
        },
        "shipTo": {
            "name": order_data.get('Customer Name'),
            "company": order_data.get('Company') or None,
            "street1": order_data.get('Street1'),
            "street2": order_data.get('Street2') or None,
            "city": order_data.get('City'),
            "state": order_data.get('State'),
            "postalCode": order_data.get('Postal Code'),
            "country": order_data.get('Country') or "US",
            "phone": order_data.get('Phone') or None
        },
        "items": [{
            "sku": order_data.get('Item SKU'),
            "name": order_data.get('Item Name'),
            "quantity": int(order_data.get('Quantity', 1)),
            "unitPrice": 0.00
        }],
        "carrierCode": order_data.get('Carrier Code') or None,
        "serviceCode": order_data.get('Service Code') or None,
        "packageCode": order_data.get('Package Code') or None,
        "internalNotes": f"Recreated from order {order_data.get('Order Number')} - Client duplicate conflict"
    }
    
    # Remove None values from payload to avoid issues
    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items() if v is not None and v != ''}
        return d
    
    payload = clean_dict(payload)
    
    # Create order in ShipStation
    response = requests.post(
        'https://ssapi.shipstation.com/orders/createorder',
        auth=(api_key, api_secret),
        json=payload
    )
    
    return response

def main():
    print("="*100)
    print("CREATE MANUAL ORDERS FROM CSV")
    print("="*100)
    
    # Configuration
    csv_filename = "orders_to_ship_20251010_170406.csv"
    starting_order_number = 100524
    
    print(f"\nReading orders from: {csv_filename}")
    print(f"Starting order number: {starting_order_number}\n")
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    
    # Read CSV
    orders = read_csv_orders(csv_filename)
    print(f"Found {len(orders)} order(s) in CSV\n")
    
    # Create orders
    results = []
    new_order_num = starting_order_number
    
    for order in orders:
        original_order = order.get('Order Number')
        print(f"Processing original order {original_order}...")
        print("-" * 80)
        
        # Show order details
        customer = order.get('Customer Name')
        company = order.get('Company', '')
        if company:
            print(f"  Customer: {customer} @ {company}")
        else:
            print(f"  Customer: {customer}")
        
        print(f"  Address: {order.get('Street1')}, {order.get('City')}, {order.get('State')}")
        print(f"  Item: {order.get('Item SKU')} x{order.get('Quantity')}")
        print(f"  Shipping: {order.get('Service Code')}")
        
        # Ask for confirmation
        confirm = input(f"\n  Create new order {new_order_num} in ShipStation? (y/n): ")
        if confirm.lower() != 'y':
            print(f"  ⏭️  Skipped")
            results.append({'original': original_order, 'status': 'skipped'})
            continue
        
        # Create order
        try:
            response = create_shipstation_order(api_key, api_secret, order, str(new_order_num))
            
            if response.status_code in [200, 201]:
                ss_data = response.json()
                ss_order_id = ss_data.get('orderId')
                print(f"  ✅ SUCCESS! Created order {new_order_num} (ShipStation ID: {ss_order_id})")
                results.append({
                    'original': original_order,
                    'new_order': new_order_num,
                    'ss_id': ss_order_id,
                    'status': 'success'
                })
                new_order_num += 1
            else:
                print(f"  ❌ FAILED: {response.status_code} - {response.text}")
                results.append({
                    'original': original_order,
                    'status': 'failed',
                    'error': response.text
                })
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({
                'original': original_order,
                'status': 'error',
                'error': str(e)
            })
        
        print()
    
    # Summary
    print("="*100)
    print("SUMMARY")
    print("="*100)
    
    success = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') in ['failed', 'error']]
    skipped = [r for r in results if r.get('status') == 'skipped']
    
    if success:
        print(f"\n✅ Successfully created: {len(success)} order(s)")
        for r in success:
            print(f"   {r['original']} → {r['new_order']} (ShipStation ID: {r['ss_id']})")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)} order(s)")
        for r in failed:
            print(f"   {r['original']}: {r.get('error', 'Unknown error')}")
    
    if skipped:
        print(f"\n⏭️  Skipped: {len(skipped)} order(s)")
        for r in skipped:
            print(f"   {r['original']}")
    
    print("\n✅ Done!")

if __name__ == '__main__':
    main()

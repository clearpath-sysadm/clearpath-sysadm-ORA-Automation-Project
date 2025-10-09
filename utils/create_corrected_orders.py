#!/usr/bin/env python3
"""
Create corrected manual orders in ShipStation for mis-shipped orders.
Pulls XML data from database and creates new ShipStation orders with correct SKUs.
"""

import sqlite3
import requests
import os
import sys
from datetime import datetime

# Orders to correct (from screenshot - DO NOT MODIFY)
ORDERS_TO_CORRECT = ['688005', '688025', '688085', '688195', '688245', '688595']

def get_shipstation_credentials():
    api_key = os.getenv('SHIPSTATION_API_KEY')
    api_secret = os.getenv('SHIPSTATION_API_SECRET')
    if not api_key or not api_secret:
        raise ValueError("ShipStation credentials not found in environment")
    return api_key, api_secret

def get_sku_lot_mapping():
    """Get active SKU-Lot mappings from database"""
    conn = sqlite3.connect('ora.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sku, lot 
        FROM sku_lot 
        WHERE active = 1
    """)
    mapping = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return mapping

def get_order_data(order_number):
    """Get order data from database"""
    conn = sqlite3.connect('ora.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get order header
    cursor.execute("""
        SELECT * FROM orders_inbox WHERE order_number = ?
    """, (order_number,))
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        return None
    
    # Get order items
    cursor.execute("""
        SELECT sku, quantity
        FROM order_items_inbox oii
        JOIN orders_inbox oi ON oii.order_inbox_id = oi.id
        WHERE oi.order_number = ?
        ORDER BY sku
    """, (order_number,))
    items = cursor.fetchall()
    
    conn.close()
    return dict(order), items

def create_shipstation_order(api_key, api_secret, order_data, items, sku_lot_mapping):
    """Create a new order in ShipStation with corrected SKUs"""
    
    # Create unique order number with -FIX suffix
    original_order_num = order_data['order_number']
    new_order_num = f"{original_order_num}-FIX"
    
    # Build order items with lot numbers
    ss_items = []
    for item in items:
        sku = item['sku'] if isinstance(item, dict) else item[0]
        qty = item['quantity'] if isinstance(item, dict) else item[1]
        
        # Apply lot number if available
        if sku in sku_lot_mapping:
            sku_with_lot = f"{sku} - {sku_lot_mapping[sku]}"
        else:
            sku_with_lot = sku
        
        ss_items.append({
            "sku": sku_with_lot,
            "name": f"SKU {sku}",
            "quantity": qty,
            "unitPrice": 0.00
        })
    
    # Build ShipStation order payload
    payload = {
        "orderNumber": new_order_num,
        "orderDate": datetime.now().isoformat(),
        "orderStatus": "awaiting_shipment",
        "customerEmail": order_data.get('customer_email') or "noemail@oracare.com",
        "billTo": {
            "name": order_data.get('bill_name') or order_data.get('ship_name'),
            "street1": order_data.get('bill_street1') or order_data.get('ship_street1'),
            "city": order_data.get('bill_city') or order_data.get('ship_city'),
            "state": order_data.get('bill_state') or order_data.get('ship_state'),
            "postalCode": order_data.get('bill_postal_code') or order_data.get('ship_postal_code'),
            "country": order_data.get('bill_country') or order_data.get('ship_country') or "US"
        },
        "shipTo": {
            "name": order_data['ship_name'],
            "company": order_data.get('ship_company'),
            "street1": order_data['ship_street1'],
            "street2": order_data.get('ship_street2'),
            "city": order_data['ship_city'],
            "state": order_data['ship_state'],
            "postalCode": order_data['ship_postal_code'],
            "country": order_data.get('ship_country') or "US",
            "phone": order_data.get('ship_phone')
        },
        "items": ss_items,
        "internalNotes": f"CORRECTED ORDER - Original: {original_order_num} - Mis-shipped on 10/06/2025"
    }
    
    # Create order in ShipStation
    response = requests.post(
        'https://ssapi.shipstation.com/orders/createorder',
        auth=(api_key, api_secret),
        json=payload
    )
    
    return response, new_order_num

def main():
    print("="*100)
    print("SHIPSTATION ORDER CORRECTION UTILITY")
    print("="*100)
    print(f"\nCreating corrected orders for {len(ORDERS_TO_CORRECT)} mis-shipped orders...")
    print(f"Orders: {', '.join(ORDERS_TO_CORRECT)}\n")
    
    # Get credentials and mappings
    api_key, api_secret = get_shipstation_credentials()
    sku_lot_mapping = get_sku_lot_mapping()
    
    print(f"Active SKU-Lot mappings: {len(sku_lot_mapping)}")
    for sku, lot in sku_lot_mapping.items():
        print(f"  {sku} -> {lot}")
    print()
    
    # Process each order
    results = []
    for order_num in ORDERS_TO_CORRECT:
        print(f"\nProcessing Order {order_num}...")
        print("-" * 80)
        
        # Get order data
        order_data, items = get_order_data(order_num)
        if not order_data:
            print(f"  ❌ Order {order_num} not found in database!")
            results.append({'order': order_num, 'status': 'not_found'})
            continue
        
        # Show order details
        print(f"  Ship To: {order_data['ship_name']}")
        if order_data.get('ship_company'):
            print(f"  Company: {order_data['ship_company']}")
        print(f"  Address: {order_data['ship_street1']}, {order_data['ship_city']}, {order_data['ship_state']}")
        print(f"  Items (CORRECT from XML):")
        for item in items:
            sku = item['sku'] if isinstance(item, dict) else item[0]
            qty = item['quantity'] if isinstance(item, dict) else item[1]
            lot = sku_lot_mapping.get(sku, 'NO LOT')
            print(f"    - {sku} (x{qty}) -> Will ship as: {sku} - {lot}")
        
        # Ask for confirmation
        confirm = input(f"\n  Create corrected order {order_num}-FIX in ShipStation? (y/n): ")
        if confirm.lower() != 'y':
            print(f"  ⏭️  Skipped")
            results.append({'order': order_num, 'status': 'skipped'})
            continue
        
        # Create order
        try:
            response, new_order_num = create_shipstation_order(
                api_key, api_secret, order_data, items, sku_lot_mapping
            )
            
            if response.status_code in [200, 201]:
                ss_data = response.json()
                ss_order_id = ss_data.get('orderId')
                print(f"  ✅ SUCCESS! Created order {new_order_num} (ShipStation ID: {ss_order_id})")
                results.append({
                    'order': order_num,
                    'new_order': new_order_num,
                    'ss_id': ss_order_id,
                    'status': 'success'
                })
            else:
                print(f"  ❌ FAILED: {response.status_code} - {response.text}")
                results.append({
                    'order': order_num,
                    'status': 'failed',
                    'error': response.text
                })
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({
                'order': order_num,
                'status': 'error',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    
    success = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') in ['failed', 'error', 'not_found']]
    skipped = [r for r in results if r.get('status') == 'skipped']
    
    print(f"\n✅ Successful: {len(success)}")
    for r in success:
        print(f"   {r['order']} -> {r['new_order']} (ID: {r['ss_id']})")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for r in failed:
            print(f"   {r['order']}: {r.get('error', 'Unknown error')}")
    
    if skipped:
        print(f"\n⏭️  Skipped: {len(skipped)}")
        for r in skipped:
            print(f"   {r['order']}")
    
    print("\nDone!")

if __name__ == '__main__':
    main()

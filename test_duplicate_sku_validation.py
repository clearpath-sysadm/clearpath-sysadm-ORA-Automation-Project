#!/usr/bin/env python3
"""
Phase 0: Duplicate SKU Validation Test

Tests if any ShipStation orders have duplicate SKUs on multiple line items.
This would violate the order_items_inbox UNIQUE(order_inbox_id, sku) constraint.
"""

import sys
import os
from collections import Counter

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from utils.api_utils import make_api_request

def test_for_duplicate_skus():
    """
    Query recent ShipStation orders and check for duplicate SKUs.
    
    Returns:
        dict: Results of the validation test
    """
    print("=" * 80)
    print("PHASE 0: DUPLICATE SKU VALIDATION TEST")
    print("=" * 80)
    print()
    
    api_key, api_secret = get_shipstation_credentials()
    headers = get_shipstation_headers(api_key, api_secret)
    
    results = {
        'total_orders_checked': 0,
        'orders_with_duplicates': [],
        'duplicate_examples': [],
        'test_passed': False
    }
    
    # Test recent 500 orders across 2 pages
    for page in range(1, 3):
        print(f"Fetching page {page} of ShipStation orders...")
        
        url = 'https://ssapi.shipstation.com/orders'
        params = {
            'pageSize': 500,
            'page': page,
            'sortBy': 'ModifyDate',
            'sortDir': 'DESC'
        }
        
        response = make_api_request(
            url=url,
            method='GET',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if not response or response.status_code != 200:
            print(f"❌ API request failed. Status: {response.status_code if response else 'N/A'}")
            return results
        
        data = response.json()
        orders = data.get('orders', [])
        results['total_orders_checked'] += len(orders)
        
        print(f"   Checking {len(orders)} orders for duplicate SKUs...")
        
        # Check each order for duplicate SKUs
        for order in orders:
            order_number = order.get('orderNumber', 'UNKNOWN')
            items = order.get('items', [])
            
            # Extract SKUs
            skus = [item.get('sku', '') for item in items if item.get('sku')]
            
            # Check for duplicates
            sku_counts = Counter(skus)
            duplicates = {sku: count for sku, count in sku_counts.items() if count > 1}
            
            if duplicates:
                results['orders_with_duplicates'].append(order_number)
                
                # Collect detailed example (limit to first 5)
                if len(results['duplicate_examples']) < 5:
                    item_details = []
                    for item in items:
                        sku = item.get('sku', '')
                        if sku in duplicates:
                            item_details.append({
                                'sku': sku,
                                'quantity': item.get('quantity', 0),
                                'name': item.get('name', ''),
                                'lineItemKey': item.get('lineItemKey', '')
                            })
                    
                    results['duplicate_examples'].append({
                        'order_number': order_number,
                        'shipstation_order_id': order.get('orderId'),
                        'status': order.get('orderStatus'),
                        'duplicate_skus': list(duplicates.keys()),
                        'item_details': item_details
                    })
    
    # Determine test result
    results['test_passed'] = len(results['orders_with_duplicates']) == 0
    
    # Print results
    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print(f"Total Orders Checked: {results['total_orders_checked']}")
    print(f"Orders with Duplicate SKUs: {len(results['orders_with_duplicates'])}")
    print()
    
    if results['test_passed']:
        print("✅ TEST PASSED - No duplicate SKUs found!")
        print()
        print("CONCLUSION: Safe to proceed with Ghost Order Backfill implementation.")
        print("The UNIQUE(order_inbox_id, sku) constraint will not cause data loss.")
    else:
        print("⚠️ TEST FAILED - Duplicate SKUs detected!")
        print()
        print(f"Found {len(results['orders_with_duplicates'])} orders with duplicate SKUs:")
        print()
        
        # Show examples
        for idx, example in enumerate(results['duplicate_examples'], 1):
            print(f"Example {idx}:")
            print(f"  Order Number: {example['order_number']}")
            print(f"  ShipStation ID: {example['shipstation_order_id']}")
            print(f"  Status: {example['status']}")
            print(f"  Duplicate SKUs: {', '.join(example['duplicate_skus'])}")
            print(f"  Items:")
            for item in example['item_details']:
                print(f"    - SKU: {item['sku']}, Qty: {item['quantity']}, Name: {item['name']}")
            print()
        
        if len(results['orders_with_duplicates']) > 5:
            print(f"  ... and {len(results['orders_with_duplicates']) - 5} more orders")
            print()
        
        print("CONCLUSION: BLOCKER - Cannot proceed with current implementation.")
        print("REQUIRED ACTION: Redesign constraint or aggregate quantities before backfill.")
    
    print("=" * 80)
    return results

if __name__ == '__main__':
    try:
        results = test_for_duplicate_skus()
        
        # Exit with appropriate code
        sys.exit(0 if results['test_passed'] else 1)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

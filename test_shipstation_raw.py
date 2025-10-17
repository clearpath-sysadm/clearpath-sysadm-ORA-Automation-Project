#!/usr/bin/env python3
"""
Test script to fetch raw ShipStation data for Oct 6-12, 2025
and analyze for duplicates
"""
import sys
import os
from collections import Counter

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from src.services.shipstation.api_client import get_shipstation_credentials, fetch_shipstation_shipments
from config.settings import SHIPSTATION_SHIPMENTS_ENDPOINT
from src.services.data_processing.shipment_processor import extract_base_sku

# Get credentials
api_key, api_secret = get_shipstation_credentials()
if not api_key or not api_secret:
    print("❌ Failed to get ShipStation credentials")
    sys.exit(1)

print("✅ Got ShipStation credentials")
print(f"📡 Fetching shipments from ShipStation API for Oct 6-12, 2025...\n")

# Fetch shipments for the week
shipments = fetch_shipstation_shipments(
    api_key=api_key,
    api_secret=api_secret,
    shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,
    start_date="2025-10-06",
    end_date="2025-10-12"
)

print(f"\n📦 Total shipments returned from API: {len(shipments)}")

# Analyze for duplicates
order_ids = []
order_numbers = []
order_id_counter = Counter()
order_number_counter = Counter()

# Track items by orderId + SKU
items_by_order_sku = []

for shipment in shipments:
    order_id = shipment.get('orderId')
    order_number = shipment.get('orderNumber')
    
    if order_id:
        order_ids.append(order_id)
        order_id_counter[order_id] += 1
    
    if order_number:
        order_numbers.append(order_number)
        order_number_counter[order_number] += 1
    
    # Track items
    if 'shipmentItems' in shipment:
        for item in shipment['shipmentItems']:
            sku = item.get('sku', '')
            base_sku = extract_base_sku(sku)
            qty = item.get('quantity', 0)
            
            items_by_order_sku.append({
                'orderId': order_id,
                'orderNumber': order_number,
                'base_sku': base_sku,
                'sku_lot': sku,
                'quantity': qty,
                'ship_date': shipment.get('shipDate', '')[:10]
            })

print(f"📊 Unique order IDs: {len(set(order_ids))}")
print(f"📊 Unique order numbers: {len(set(order_numbers))}")

# Check for duplicate orderIds
duplicate_order_ids = {oid: count for oid, count in order_id_counter.items() if count > 1}
if duplicate_order_ids:
    print(f"\n⚠️  DUPLICATE ORDER IDs FOUND IN API RESPONSE:")
    for oid, count in sorted(duplicate_order_ids.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   OrderId {oid}: appears {count} times")
else:
    print(f"\n✅ No duplicate orderIds in API response")

# Check for duplicate order numbers
duplicate_order_numbers = {onum: count for onum, count in order_number_counter.items() if count > 1}
if duplicate_order_numbers:
    print(f"\n⚠️  DUPLICATE ORDER NUMBERS FOUND IN API RESPONSE:")
    for onum, count in sorted(duplicate_order_numbers.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   Order {onum}: appears {count} times")
else:
    print(f"\n✅ No duplicate order numbers in API response")

# Count total units for SKU 17612 WITHOUT deduplication
total_17612_raw = sum(item['quantity'] for item in items_by_order_sku if item['base_sku'] == '17612')
print(f"\n📦 SKU 17612 total from raw API (NO dedup): {total_17612_raw}")

# Count with deduplication by (orderId, base_sku, ship_date)
seen = set()
deduplicated_items = []
for item in items_by_order_sku:
    key = (item['orderId'], item['base_sku'], item['ship_date'])
    if key not in seen:
        seen.add(key)
        deduplicated_items.append(item)

total_17612_deduped = sum(item['quantity'] for item in deduplicated_items if item['base_sku'] == '17612')
print(f"📦 SKU 17612 total with dedup (orderId+SKU+date): {total_17612_deduped}")

print(f"\n🔍 Difference: {total_17612_raw - total_17612_deduped} units overcounted")

# Show all SKUs
print("\n📊 All SKUs breakdown:")
sku_totals_raw = {}
sku_totals_deduped = {}

for item in items_by_order_sku:
    sku = item['base_sku']
    sku_totals_raw[sku] = sku_totals_raw.get(sku, 0) + item['quantity']

for item in deduplicated_items:
    sku = item['base_sku']
    sku_totals_deduped[sku] = sku_totals_deduped.get(sku, 0) + item['quantity']

print("\nSKU       | Raw API | Deduped | Difference")
print("----------|---------|---------|----------")
for sku in sorted(set(list(sku_totals_raw.keys()) + list(sku_totals_deduped.keys()))):
    raw = sku_totals_raw.get(sku, 0)
    dedup = sku_totals_deduped.get(sku, 0)
    diff = raw - dedup
    if sku in ['17612', '17904', '17914', '18795']:  # Key SKUs
        print(f"{sku:9} | {raw:7} | {dedup:7} | {diff:+7}")

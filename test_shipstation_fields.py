#!/usr/bin/env python3
"""
Test script to examine ShipStation API response fields
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from src.services.shipstation.api_client import get_shipstation_credentials, fetch_shipstation_shipments
from config.settings import SHIPSTATION_SHIPMENTS_ENDPOINT
from datetime import datetime, timedelta

# Get credentials
api_key, api_secret = get_shipstation_credentials()

# Fetch last 7 days of shipments
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

print(f"Fetching shipments from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

shipments = fetch_shipstation_shipments(
    api_key=api_key,
    api_secret=api_secret,
    shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d'),
    shipment_status="shipped",
    page=1,
    page_size=5  # Just get a few samples
)

if shipments:
    print(f"\n✅ Got {len(shipments)} sample shipments")
    print("\n" + "="*80)
    print("SAMPLE SHIPMENT FIELDS:")
    print("="*80)
    
    sample = shipments[0]
    print(json.dumps(sample, indent=2, default=str))
    
    print("\n" + "="*80)
    print("KEY FIELDS FOR TRACKING:")
    print("="*80)
    print(f"Order Number: {sample.get('orderNumber')}")
    print(f"Service Code: {sample.get('serviceCode')}")
    print(f"Carrier Code: {sample.get('carrierCode')}")
    print(f"Service Name: {sample.get('serviceName')}")
    print(f"Advanced Options: {sample.get('advancedOptions', {})}")
    
    # Check if we have internal notes or custom fields
    if 'advancedOptions' in sample:
        print(f"\nAdvanced Options keys: {list(sample['advancedOptions'].keys())}")
else:
    print("❌ No shipments returned")

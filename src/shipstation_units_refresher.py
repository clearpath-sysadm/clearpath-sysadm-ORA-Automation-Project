#!/usr/bin/env python3
"""
ShipStation Units Refresher
Automatically refreshes units_to_ship metric every 5 minutes
"""
import os
import sys
import time
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection

ORACARE_STORE_ID = 345611


def refresh_units_to_ship():
    """Fetch units from ShipStation (Oracare store only) and update database"""
    try:
        api_key = os.environ.get('SHIPSTATION_API_KEY')
        api_secret = os.environ.get('SHIPSTATION_API_SECRET')

        if not api_key or not api_secret:
            print(f"[{datetime.now()}] ERROR: ShipStation credentials not found")
            return

        auth = HTTPBasicAuth(api_key, api_secret)
        url = "https://ssapi.shipstation.com/orders"

        total_units = 0
        total_orders = 0
        page = 1

        while True:
            params = {
                'orderStatus': 'awaiting_shipment',
                'storeId': ORACARE_STORE_ID,
                'pageSize': 500,
                'page': page,
            }

            response = requests.get(url, params=params, auth=auth, timeout=30)

            if response.status_code != 200:
                print(f"[{datetime.now()}] ShipStation API error: {response.status_code}")
                return

            data = response.json()
            orders = data.get('orders', [])
            total_orders += len(orders)

            for order in orders:
                for item in order.get('items', []):
                    total_units += item.get('quantity', 0)

            total_pages = data.get('pages', 1)
            if page >= total_pages:
                break
            page += 1

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO shipstation_metrics (metric_name, metric_value, last_updated)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (metric_name)
            DO UPDATE SET metric_value = EXCLUDED.metric_value,
                          last_updated = CURRENT_TIMESTAMP
        """, ('units_to_ship', total_units))

        conn.commit()
        conn.close()

        print(f"[{datetime.now()}] Updated: {total_units} units ({total_orders} orders, Oracare store only)")

    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {str(e)}")


def main():
    """Run refresh loop every 5 minutes"""
    print(f"[{datetime.now()}] ShipStation Units Refresher started (5-minute interval)")

    while True:
        refresh_units_to_ship()
        time.sleep(300)


if __name__ == '__main__':
    main()

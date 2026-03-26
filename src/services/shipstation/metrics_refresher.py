#!/usr/bin/env python3
"""
ShipStation Metrics Refresher
Auto-refreshes ShipStation metrics cache to prevent stale data
"""
import requests
from requests.auth import HTTPBasicAuth
from src.services.shipstation.api_client import get_shipstation_credentials
from src.services.database.pg_utils import get_connection
from config.settings import settings

ORACARE_STORE_ID = 345611


def refresh_shipstation_metrics():
    """
    Refresh ShipStation metrics (units_to_ship) by querying the API
    and updating the cache in the database.

    Filters to Oracare store only (storeId=345611) and paginates through
    all pages so the count is accurate.
    """
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        raise ValueError("ShipStation API credentials not found")

    auth = HTTPBasicAuth(api_key, api_secret)
    url = settings.SHIPSTATION_ORDERS_ENDPOINT

    total_units = 0
    page = 1

    while True:
        params = {
            'orderStatus': 'awaiting_shipment',
            'storeId': ORACARE_STORE_ID,
            'pageSize': 500,
            'page': page,
        }

        response = requests.get(url, auth=auth, params=params, timeout=30)

        if response.status_code != 200:
            raise Exception(f'ShipStation API error: {response.status_code}')

        data = response.json()
        orders = data.get('orders', [])

        total_units += sum(
            item.get('quantity', 0)
            for order in orders
            for item in order.get('items', [])
        )

        total_pages = data.get('pages', 1)
        if page >= total_pages:
            break
        page += 1

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO shipstation_metrics (metric_name, metric_value, last_updated)
        VALUES ('units_to_ship', %s, CURRENT_TIMESTAMP)
        ON CONFLICT (metric_name) DO UPDATE
            SET metric_value = EXCLUDED.metric_value,
                last_updated = EXCLUDED.last_updated
    """, (total_units,))

    conn.commit()
    conn.close()

    return total_units

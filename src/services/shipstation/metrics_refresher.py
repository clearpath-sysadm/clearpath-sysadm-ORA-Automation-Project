#!/usr/bin/env python3
"""
ShipStation Metrics Refresher
Auto-refreshes ShipStation metrics cache to prevent stale data
"""
import requests
from requests.auth import HTTPBasicAuth
from src.services.shipstation.api_client import get_shipstation_credentials
from src.services.database.db_utils import get_connection
from config.settings import settings


def refresh_shipstation_metrics():
    """
    Refresh ShipStation metrics (units_to_ship) by querying the API
    and updating the cache in the database.
    
    This prevents stale cache data and ensures dashboard shows current counts.
    """
    # Get ShipStation credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        raise ValueError("ShipStation API credentials not found")
    
    # Fetch orders with status awaiting_shipment
    url = settings.SHIPSTATION_ORDERS_ENDPOINT
    params = {
        'orderStatus': 'awaiting_shipment',
        'pageSize': 500
    }
    
    response = requests.get(
        url,
        auth=HTTPBasicAuth(api_key, api_secret),
        params=params,
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f'ShipStation API error: {response.status_code}')
    
    data = response.json()
    orders = data.get('orders', [])
    
    # Count total units across all items in all orders
    total_units = sum(
        item.get('quantity', 0)
        for order in orders
        for item in order.get('items', [])
    )
    
    # Update cache in database
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE shipstation_metrics
        SET metric_value = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE metric_name = 'units_to_ship'
    """, (total_units,))
    
    conn.commit()
    conn.close()
    
    return total_units

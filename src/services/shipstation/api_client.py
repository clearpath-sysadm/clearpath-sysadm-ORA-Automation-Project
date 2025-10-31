# filename: src/services/shipstation/api_client.py
"""
This module provides functions for interacting with the ShipStation API.
It handles authentication, API requests, and basic data fetching with
built-in retry logic.
"""
import base64
import requests
import logging
import time
import json
import os
import sys

# Add the project root to the Python path to enable imports from a parent directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# FIX: Import the settings object directly from the config package.
from config import settings
from utils.api_utils import make_api_request
from src.services.secrets import get_secret


# --- Environment Detection ---
ENV = getattr(settings, 'get_environment', lambda: 'unknown')()
IS_LOCAL_ENV = ENV == 'local'
IS_CLOUD_ENV = ENV == 'cloud'

# --- Logging Setup ---
logger = logging.getLogger('shipstation_api_client')
logger.setLevel(logging.DEBUG)
if IS_LOCAL_ENV:
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'shipstation_api_client.log')
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
else:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False
logger.info(f"ShipStation API Client started. Environment: {ENV.upper()}")

def get_shipstation_headers(api_key: str, api_secret: str) -> dict:
    """
    Generates the Authorization header for ShipStation API requests.
    """
    combined_credentials = f"{api_key}:{api_secret}"
    encoded_credentials = base64.b64encode(combined_credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded_credentials}"}

def get_shipstation_credentials():
    """
    Retrieves ShipStation API credentials from Replit environment variables or GCP Secret Manager.
    Prioritizes Replit environment variables for Replit deployment.
    """
    try:
        # First check Replit environment variables (most common in Replit)
        api_key = os.getenv('SHIPSTATION_API_KEY')
        api_secret = os.getenv('SHIPSTATION_API_SECRET')
        
        if api_key and api_secret:
            logger.info("Using ShipStation credentials from Replit environment variables")
            return api_key, api_secret
        
        # Fallback to GCP Secret Manager (for Google Cloud deployments)
        logger.info("Attempting to retrieve ShipStation API Key from GCP Secret Manager...")
        api_key = get_secret(settings.SHIPSTATION_API_KEY_SECRET_ID)
        logger.info("Attempting to retrieve ShipStation API Secret from GCP Secret Manager...")
        api_secret = get_secret(settings.SHIPSTATION_API_SECRET_SECRET_ID)
        
        if not api_key or not api_secret:
            logger.error("Failed to retrieve ShipStation API credentials from all sources.")
            return None, None
        return api_key, api_secret
    except Exception as e:
        logger.error(f"Error retrieving ShipStation credentials: {e}", exc_info=True)
        return None, None

def fetch_shipstation_shipments(
    api_key: str,
    api_secret: str,
    shipments_endpoint: str,
    start_date: str,
    end_date: str,
    shipment_status: str = "shipped",
    page: int = 1,
    page_size: int = 500
) -> list:
    """
    Fetches shipment data from ShipStation within a specified date range.
    Includes shipment items.

    Args:
        api_key (str): The ShipStation API key.
        api_secret (str): The ShipStation API secret.
        shipments_endpoint (str): The ShipStation shipments API endpoint URL.
        start_date (str): The start date for the query in 'YYYY-MM-DD' format.
        end_date (str): The end date for the query in 'YYYY-MM-DD' format.
        shipment_status (str): The status of the shipments to retrieve (e.g., "shipped").
        page (int): The starting page number.
        page_size (int): The number of shipments per page (max 500).

    Returns:
        list: A list of shipment dictionaries from the API response.
    """
    logger.info(f"Starting raw shipment fetch from {start_date} with includeShipmentItems=true and status='{shipment_status}'...")
    all_shipments = []
    headers = get_shipstation_headers(api_key, api_secret)
    
    params = {
        'shipDateStart': start_date,
        'shipDateEnd': end_date,
        'includeShipmentItems': 'true',
        'page': page,
        'pageSize': page_size,
        'shipmentStatus': shipment_status
    }

    while True:
        try:
            response = make_api_request(
                url=shipments_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )

            if response and response.status_code == 200:
                data = response.json()
                shipments_on_page = data.get('shipments', [])
                all_shipments.extend(shipments_on_page)
                
                total_pages = data.get('pages', 1)
                current_page = data.get('page', 1)

                logger.info(f"Fetched page {current_page} of {total_pages}. Total shipments so far: {len(all_shipments)}")

                if current_page >= total_pages:
                    break
                else:
                    params['page'] += 1
            else:
                logger.error(f"Failed to fetch shipments. Status: {response.status_code if response else 'N/A'}, Response: {response.text if response else 'N/A'}")
                break
        except Exception as e:
            logger.error(f"An error occurred while fetching shipments: {e}")
            break
            
    logger.info(f"Finished fetching ShipStation shipments. Total retrieved: {len(all_shipments)}")
    return all_shipments

def send_all_orders_to_shipstation(orders_payload: list, api_key: str, api_secret: str, create_orders_endpoint: str) -> list:
    """
    Sends a list of orders to ShipStation's createorders endpoint.
    
    Args:
        orders_payload: List of order dictionaries formatted for ShipStation API
        api_key: ShipStation API Key
        api_secret: ShipStation API Secret
        create_orders_endpoint: Full URL for ShipStation createorders API endpoint
    
    Returns:
        list: Results from the API including orderKey, success status, and error messages
    """
    headers = get_shipstation_headers(api_key, api_secret)
    headers["Content-Type"] = "application/json"
    
    try:
        logger.debug(f"Sending {len(orders_payload)} orders to ShipStation...")
        
        response = make_api_request(
            url=create_orders_endpoint,
            method='POST',
            data=orders_payload,
            headers=headers,
            timeout=120
        )
        
        if response and response.status_code == 200:
            response_data = response.json()
            logger.info(f"Successfully sent orders to ShipStation")
            return response_data.get('results', [])
        else:
            logger.error(f"Failed to send orders. Status: {response.status_code if response else 'N/A'}")
            return []
            
    except Exception as e:
        logger.error(f"Error sending orders to ShipStation: {e}", exc_info=True)
        return []

def fetch_shipstation_existing_orders_by_date_range(
    api_key: str,
    api_secret: str,
    orders_endpoint: str,
    create_date_start: str,
    create_date_end: str
) -> list:
    """
    Fetches existing orders from ShipStation within a date range to check for duplicates.
    
    Args:
        api_key: ShipStation API Key
        api_secret: ShipStation API Secret  
        orders_endpoint: ShipStation orders API endpoint URL
        create_date_start: Start date in ISO format
        create_date_end: End date in ISO format
    
    Returns:
        list: List of existing orders from ShipStation
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    
    params = {
        'createDateStart': create_date_start,
        'createDateEnd': create_date_end,
        'page': 1,
        'pageSize': 500
    }
    
    try:
        while True:
            response = make_api_request(
                url=orders_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response and response.status_code == 200:
                data = response.json()
                orders_on_page = data.get('orders', [])
                all_orders.extend(orders_on_page)
                
                total_pages = data.get('pages', 1)
                current_page = data.get('page', 1)
                
                logger.info(f"Fetched page {current_page} of {total_pages} for duplicate check")
                
                if current_page >= total_pages:
                    break
                else:
                    params['page'] += 1
            else:
                logger.error(f"Failed to fetch existing orders. Status: {response.status_code if response else 'N/A'}")
                break
                
        logger.info(f"Retrieved {len(all_orders)} existing orders for duplicate checking")
        return all_orders
        
    except Exception as e:
        logger.error(f"Error fetching existing orders: {e}", exc_info=True)
        return []

def fetch_shipstation_orders_by_order_numbers(
    api_key: str,
    api_secret: str,
    orders_endpoint: str,
    order_numbers: list
) -> list:
    """
    Fetches existing orders from ShipStation by specific order numbers.
    Uses a single date-range query for efficiency instead of per-order queries.
    
    Args:
        api_key: ShipStation API Key
        api_secret: ShipStation API Secret
        orders_endpoint: ShipStation orders API endpoint URL
        order_numbers: List of order numbers to query
    
    Returns:
        list: List of existing orders from ShipStation matching the order numbers
    """
    if not order_numbers:
        return []
    
    headers = get_shipstation_headers(api_key, api_secret)
    
    # Use a wide date range to capture all orders (last 6 months)
    # This is more efficient than querying each order individually
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    params = {
        'createDateStart': start_date.strftime('%Y-%m-%dT00:00:00Z'),
        'createDateEnd': end_date.strftime('%Y-%m-%dT23:59:59Z'),
        'page': 1,
        'pageSize': 500
    }
    
    all_orders = []
    order_numbers_upper = set(str(num).strip().upper() for num in order_numbers)
    
    try:
        logger.info(f"Fetching orders from ShipStation (date range query for {len(order_numbers)} order numbers)")
        
        while True:
            response = make_api_request(
                url=orders_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response and response.status_code == 200:
                data = response.json()
                orders_on_page = data.get('orders', [])
                
                # Filter to only orders we care about
                for order in orders_on_page:
                    order_num = order.get('orderNumber', '').strip().upper()
                    if order_num in order_numbers_upper:
                        all_orders.append(order)
                
                total_pages = data.get('pages', 1)
                current_page = data.get('page', 1)
                
                logger.debug(f"Fetched page {current_page}/{total_pages}, found {len([o for o in orders_on_page if o.get('orderNumber', '').strip().upper() in order_numbers_upper])} matching orders")
                
                if current_page >= total_pages:
                    break
                else:
                    params['page'] += 1
            else:
                logger.error(f"Failed to fetch orders. Status: {response.status_code if response else 'N/A'}")
                break
                
    except Exception as e:
        logger.error(f"Error fetching orders by date range: {e}", exc_info=True)
    
    logger.info(f"Retrieved {len(all_orders)} existing orders (filtered from bulk query)")
    return all_orders

def fetch_order_by_id(order_id: int, api_key: str = None, api_secret: str = None) -> dict:
    """
    Fetch a single order from ShipStation by order ID.
    
    Args:
        order_id: The ShipStation order ID to fetch
        api_key: Optional ShipStation API key (will retrieve if not provided)
        api_secret: Optional ShipStation API secret (will retrieve if not provided)
        
    Returns:
        dict: {'success': bool, 'order': dict, 'error': str (optional)}
    """
    try:
        if not api_key or not api_secret:
            api_key, api_secret = get_shipstation_credentials()
            if not api_key or not api_secret:
                return {'success': False, 'error': 'ShipStation credentials not found'}
        
        headers = get_shipstation_headers(api_key, api_secret)
        url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
        
        logger.info(f"Fetching order from ShipStation: Order ID {order_id}")
        
        response = make_api_request(
            url=url,
            method='GET',
            headers=headers,
            timeout=30
        )
        
        if response and response.status_code == 200:
            order = response.json()
            logger.info(f"✅ Successfully fetched order {order_id}: Order #{order.get('orderNumber')}, Status: {order.get('orderStatus')}")
            return {'success': True, 'order': order}
        else:
            error_msg = f"Failed to fetch order {order_id}: HTTP {response.status_code if response else 'No response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        logger.error(f"Error fetching order {order_id} from ShipStation: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

def delete_order_from_shipstation(order_id: int) -> dict:
    """
    Delete an order from ShipStation by order ID.
    
    Args:
        order_id: The ShipStation order ID to delete
        
    Returns:
        dict: {'success': bool, 'message': str, 'error': str (optional)}
    """
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}
        
        headers = get_shipstation_headers(api_key, api_secret)
        url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
        
        logger.info(f"Deleting order from ShipStation: Order ID {order_id}")
        
        response = make_api_request(
            url=url,
            method='DELETE',
            headers=headers,
            timeout=30
        )
        
        if response and response.status_code == 200:
            logger.info(f"✅ Successfully deleted order {order_id} from ShipStation")
            return {'success': True, 'message': f'Order {order_id} deleted successfully'}
        else:
            error_msg = f"Failed to delete order {order_id}: HTTP {response.status_code if response else 'No response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        logger.error(f"Error deleting order {order_id} from ShipStation: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

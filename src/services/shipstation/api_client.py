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
from src.services.gcp.secret_manager import access_secret_version


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
    Retrieves ShipStation API credentials securely from Google Cloud Secret Manager.
    """
    # In src/services/shipstation/api_client.py

# Add this import at the top of the file
from config.settings import SERVICE_ACCOUNT_KEY_PATH 

def get_shipstation_credentials():
    """
    Retrieves ShipStation API credentials securely from Google Cloud Secret Manager.
    """
    # Add this line for debugging
    print(f"DEBUG: Using service account key path: {SERVICE_ACCOUNT_KEY_PATH}")

    try:
        logger.info("Attempting to retrieve ShipStation API Key from Secret Manager...")
        api_key = access_secret_version(
            settings.YOUR_GCP_PROJECT_ID,
            settings.SHIPSTATION_API_KEY_SECRET_ID,
            credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
        )
        logger.info("Attempting to retrieve ShipStation API Secret from Secret Manager...")
        api_secret = access_secret_version(
            settings.YOUR_GCP_PROJECT_ID,
            settings.SHIPSTATION_API_SECRET_SECRET_ID,
            credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
        )
        if not api_key or not api_secret:
            logger.error("Failed to retrieve ShipStation API credentials.")
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

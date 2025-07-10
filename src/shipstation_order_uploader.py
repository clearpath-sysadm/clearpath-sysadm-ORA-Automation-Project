# This script serves as the main entry point for the ShipStation Order Uploader.
# It orchestrates the process of fetching X-Cart XML order data,
# transforming it into ShipStation-compatible payloads, and sending
# these orders to the ShipStation API. It leverages various modules
# for secure credential retrieval, XML parsing, and API interaction.

# --- Functions ---

# def main(): (Implicitly defined within __name__ == "__main__" block)
#   Purpose:
#     Orchestrates the end-to-end process of importing X-Cart orders
#     and creating them in ShipStation. It handles initialization,
#     credential retrieval, data fetching, parsing, and API calls.
#   Inputs:
#     None (operates using global settings and imported module functions).
#   Outputs:
#     None (orchestrates data flow and API interactions; logs outcomes and errors).

import sys
import os
import datetime # Import datetime for date calculations
from dateutil import parser # ADD THIS IMPORT for robust date parsing

# Add the project root to the Python path to enable imports from utils and services
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Standard library imports needed for basic script operation (sys.exit, os.path.exists)
# All other library imports (requests, base64, json, datetime, time, xml.etree.ElementTree, pandas)
# are now encapsulated within their respective service modules.

# Core utility imports
from utils.logging_config import setup_logging
import logging

# Import from centralized configuration settings
from config import settings

# Import necessary service modules
from src.services.gcp.secret_manager import access_secret_version
from src.services.shipstation.api_client import send_all_orders_to_shipstation, fetch_shipstation_existing_orders_by_date_range # Import new function
from src.services.data_parsers.x_cart_parser import parse_x_cart_xml_for_shipstation_payload # Only this is needed for main flow


# --- Setup Logging for this script ---
_log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
_log_file = os.path.join(_log_dir, 'app.log') # Assuming app.log is the desired log file for this script
# Ensure logging is only configured once if this script is run as main.
if not logging.getLogger().handlers:
    setup_logging(log_file_path=_log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


# --- Main execution block ---
if __name__ == "__main__":
    logger.info("Starting ShipStation Order Uploader Script (main orchestrator)...")

    # --- Retrieve API credentials ---
    shipstation_api_key = access_secret_version(
        settings.YOUR_GCP_PROJECT_ID,
        settings.SHIPSTATION_API_KEY_SECRET_ID,
        credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
    )
    shipstation_api_secret = access_secret_version(
        settings.YOUR_GCP_PROJECT_ID,
        settings.SHIPSTATION_API_SECRET_SECRET_ID,
        credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
    )

    if not shipstation_api_key or not shipstation_api_secret:
        logger.critical("Failed to retrieve ShipStation API credentials. Exiting.")
        sys.exit(1) # Use sys.exit(1) for abnormal termination

    logger.info(f"ShipStation API Key retrieved (truncated): {shipstation_api_key[:5]}...")
    logger.info(f"ShipStation API Secret retrieved (truncated): {shipstation_api_secret[:5]}...")

    # --- Parse Data from X-Cart XML ---
    logger.info(f"Loading orders from X-Cart XML file: {settings.X_CART_XML_PATH}...")
    # Using the modularized parser
    all_orders_payload = parse_x_cart_xml_for_shipstation_payload(
        settings.X_CART_XML_PATH, 
        settings.BUNDLE_CONFIG
    )
        
    if not all_orders_payload:
        logger.warning("No valid orders to send to ShipStation after processing XML. Exiting.")
        sys.exit(0) # Use sys.exit(0) for graceful exit with no orders

    logger.info(f"Prepared {len(all_orders_payload)} orders for upload to ShipStation.")

    # --- DUPLICATE ORDER PRE-CHECK LOGIC START ---
    # Extract all orderNumbers and find the earliest orderDate from the payload
    # Normalize order numbers to uppercase and strip whitespace for consistent lookup
    order_numbers_to_check = {order.get('orderNumber').strip().upper() for order in all_orders_payload if order.get('orderNumber')}
    
    earliest_order_date = None
    for order in all_orders_payload:
        order_date_str = order.get('orderDate') # This is from X-Cart XML's <orderDate> or <date2>
        
        if order_date_str:
            try:
                # --- PROPOSED CHANGE START ---
                # Attempt to parse using dateutil.parser.parse for flexibility
                # It can handle 'YYYY-MM-DD HH:MM:SS' and ISO 8601 formats
                current_order_date = parser.parse(order_date_str)
                
                # Ensure the datetime is timezone-aware UTC for consistency with ShipStation
                if current_order_date.tzinfo is None:
                    # If naive, assume it's UTC (as ShipStation expects) and make it timezone-aware
                    current_order_date = current_order_date.replace(tzinfo=datetime.timezone.utc)
                else:
                    # If already timezone-aware, convert to UTC
                    current_order_date = current_order_date.astimezone(datetime.timezone.utc)

                # Handle potential UNIX timestamp from <date> if it's ever used as orderDate
                # This assumes order_date_str might sometimes be a pure integer string for a timestamp
                # Check if it looks like a UNIX timestamp (all digits)
                if isinstance(order_date_str, str) and order_date_str.isdigit() and len(order_date_str) > 8: # Basic check for length
                    try:
                        current_order_date = datetime.datetime.fromtimestamp(int(order_date_str), tz=datetime.timezone.utc)
                    except ValueError:
                        # If it looks like a digit string but isn't a valid timestamp, let parser.parse handle it
                        pass 
                # --- PROPOSED CHANGE END ---
            except (ValueError, TypeError, parser.ParserError): # Catch dateutil specific errors too
                logger.warning(f"Could not parse orderDate '{order_date_str}' for duplicate check. Skipping date for this order.")
                continue # Skip this order's date if parsing fails

            if earliest_order_date is None or current_order_date < earliest_order_date:
                earliest_order_date = current_order_date
    
    # If no valid dates found, default to a reasonable past date to fetch existing orders
    if earliest_order_date is None:
        logger.warning("No valid order dates found in payload. Fetching existing orders from 30 days ago for duplicate check.")
        # Ensure default date is also timezone-aware UTC
        earliest_order_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    
    # Format earliest_order_date to ISO 8601 for ShipStation API
    create_date_start_iso = earliest_order_date.isoformat(timespec='seconds') + 'Z'
    create_date_end_iso = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + 'Z' # Current UTC time

    logger.info(f"Checking for existing orders in ShipStation from {create_date_start_iso} to {create_date_end_iso}...")
    existing_shipstation_orders = fetch_shipstation_existing_orders_by_date_range(
        shipstation_api_key,
        shipstation_api_secret,
        settings.SHIPSTATION_ORDERS_ENDPOINT, # Use the general orders endpoint for fetching
        create_date_start_iso,
        create_date_end_iso
    )

    # Create a set of existing order numbers for efficient lookup
    # Normalize existing order numbers to uppercase and strip whitespace for consistent lookup
    existing_order_numbers_set = {order.get('orderNumber').strip().upper() for order in existing_shipstation_orders if order.get('orderNumber')}
    
    new_orders_payload = []
    skipped_orders_count = 0
    for order in all_orders_payload:
        # Normalize the current order number before checking for duplicates
        order_number = order.get('orderNumber')
        if order_number:
            normalized_order_number = order_number.strip().upper()
        else:
            normalized_order_number = None # Handle cases where orderNumber might be missing
        
        if normalized_order_number and normalized_order_number in existing_order_numbers_set:
            logger.info(f"Skipping duplicate order: {order_number} (normalized: {normalized_order_number}) already exists in ShipStation.")
            skipped_orders_count += 1
        else:
            new_orders_payload.append(order)
    
    if skipped_orders_count > 0:
        logger.info(f"Skipped {skipped_orders_count} duplicate orders.")
    
    if not new_orders_payload:
        logger.warning("No new unique orders to send to ShipStation after duplicate check. Exiting.")
        sys.exit(0)

    logger.info(f"Proceeding with {len(new_orders_payload)} new unique orders for upload.")
    # --- DUPLICATE ORDER PRE-CHECK LOGIC END ---

    # --- Send Orders to ShipStation ---
    # Using the modularized API client
    upload_results = send_all_orders_to_shipstation(
        new_orders_payload, # Pass the filtered payload
        shipstation_api_key,
        shipstation_api_secret,
        settings.SHIPSTATION_CREATE_ORDERS_ENDPOINT
    )

    if upload_results:
        logger.info(f"--- ShipStation Upload Results ---")
        for result in upload_results:
            logger.info(f"OrderKey: {result.get('orderKey')}, Success: {result.get('success')}, ErrorMessage: {result.get('errorMessage')}")
    else:
        logger.warning("No results returned from ShipStation upload or an error occurred during sending.")

    logger.info("Script finished. (Order upload attempt completed)")


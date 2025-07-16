# This script serves as the main entry point for the ShipStation Order Uploader.
# It orchestrates the process of fetching X-Cart XML order data,
# transforming it into ShipStation-compatible payloads, and sending
# these orders to the ShipStation API. It leverages various modules
# for secure credential retrieval, XML parsing, and API interaction.

import sys
import os
import datetime
from dateutil import parser

# Add the project root to the Python path to enable imports from utils and services
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core utility imports
from utils.logging_config import setup_logging
import logging

# Import from centralized configuration settings
from config import settings

# Import necessary service modules
from src.services.gcp.secret_manager import access_secret_version
from src.services.shipstation.api_client import send_all_orders_to_shipstation, fetch_shipstation_existing_orders_by_date_range
from src.services.data_parsers.x_cart_parser import parse_x_cart_xml_for_shipstation_payload
# NEW: Import for Google Drive interaction
from src.services.google_drive.api_client import fetch_xml_content_from_drive


# --- Setup Logging for this script ---
# In a Cloud Function, logs go to stdout/stderr and are picked up by Cloud Logging.
# For local development, you might still want a file log.
_log_file_path = None # Default to no file logging for cloud deployment
# If running locally and you want file logs, uncomment and adjust this line:
# _log_log_file_path = os.path.join(project_root, 'logs', 'shipstation_order_uploader.log')

# Ensure logging is only configured once if this script is run as main.
if not logging.getLogger().handlers:
    setup_logging(log_file_path=_log_file_path, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)




# --- Cloud Function Entry Point (for Deployment) ---
# This function name should be your --entry-point when deploying to Google Cloud Functions.
# For example: gcloud functions deploy shipstation_order_uploader --entry-point shipstation_order_uploader_http_trigger
#
# LOCAL TESTING NOTE: When running locally, this block is typically commented out or
#                     the 'if __name__ == "__main__":' block below is used instead.
#                     For deployment, this block MUST be active.
#
def shipstation_order_uploader_http_trigger(request):
    logger.info({"message": "Cloud Function received HTTP trigger for order uploader.", "trigger_type": "HTTP"})
    try:
        success, message = run_order_uploader_logic()
        if success:
            return message, 200
        else:
            return message, 500
    except Exception as e:
        logger.critical({"message": "Cloud Function execution failed for order uploader", "error": str(e)}, exc_info=True)
        return f"ShipStation Order Uploader script failed: {e}", 500

# --- Core Order Uploader Logic (Reusable Function) ---
def run_order_uploader_logic():
    """
    Contains the core business logic for fetching X-Cart orders,
    processing them, and uploading them to ShipStation.
    This function is designed to be called by both local execution and the Cloud Function entry point.
    """
    logger.info({"message": "Starting core order uploader logic execution."})

    # --- Retrieve API credentials ---
    shipstation_api_key = access_secret_version(
        settings.YOUR_GCP_PROJECT_ID,
        settings.SHIPSTATION_API_KEY_SECRET_ID,
        credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH # Will be None in cloud, path for local
    )
    shipstation_api_secret = access_secret_version(
        settings.YOUR_GCP_PROJECT_ID,
        settings.SHIPSTATION_API_SECRET_SECRET_ID,
        credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH # Will be None in cloud, path for local
    )

    if not shipstation_api_key or not shipstation_api_secret:
        logger.critical({"message": "Failed to retrieve ShipStation API credentials", "action": "exiting", "severity_detail": "critical_failure"})
        # For local run, we might sys.exit. For Cloud Function, we return an error message.
        # This function will return a status and message, which the caller will interpret.
        return False, 'Failed to retrieve ShipStation API credentials'

    logger.info({"message": "ShipStation API credentials retrieved", "api_key_truncated": shipstation_api_key[:5], "api_secret_truncated": shipstation_api_secret[:5]})

    # --- Retrieve Google Sheets Service Account Key for Google Drive Access ---
    google_sheets_service_account_json = access_secret_version(
        settings.YOUR_GCP_PROJECT_ID,
        settings.GOOGLE_SHEETS_SA_KEY_SECRET_ID,
        credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH # Will be None in cloud, path for local
    )

    if not google_sheets_service_account_json:
        logger.critical({"message": "Failed to retrieve Google Sheets service account key for Google Drive access", "action": "exiting", "severity_detail": "critical_failure"})
        return False, 'Failed to retrieve Google Sheets service account key for Google Drive access'

    logger.info({"message": "Google Sheets Service Account Key retrieved for Drive access", "key_truncated": google_sheets_service_account_json[:5]})
    
    # --- DIAGNOSTIC LOG: Check type and beginning of XML content before parsing ---
    logger.debug({
        "message": "Preparing to parse XML content.",
        "content_type": str(type(x_cart_xml_content)),
        "content_start_snippet": x_cart_xml_content[:200] if isinstance(x_cart_xml_content, str) else str(x_cart_xml_content)
    })
    # --- END DIAGNOSTIC LOG ---

    # --- Fetch and Parse Data from X-Cart XML (from Google Drive) ---
    logger.info({"message": "Fetching orders from X-Cart XML on Google Drive", "file_id": settings.X_CART_XML_FILE_ID})
    
    x_cart_xml_content = fetch_xml_content_from_drive(
        settings.X_CART_XML_FILE_ID,
        google_sheets_service_account_json
    )
        
    if not x_cart_xml_content:
        logger.critical({"message": "No XML content retrieved from Google Drive or an error occurred during fetch.", "file_id": settings.X_CART_XML_FILE_ID, "action": "exiting"})
        return False, 'No XML content retrieved from Google Drive'

    logger.info({"message": "XML content fetched successfully from Google Drive", "file_id": settings.X_CART_XML_FILE_ID, "content_length": len(x_cart_xml_content)})

    # Using the modularized parser, now passing content string directly
    all_orders_payload = parse_x_cart_xml_for_shipstation_payload(
        x_cart_xml_content, # Pass the XML content string
        settings.BUNDLE_CONFIG
    )
        
    if not all_orders_payload:
        logger.warning({"message": "No valid orders to send to ShipStation after processing XML", "action": "exiting_gracefully"})
        return True, 'No new unique orders to send to ShipStation after processing XML' # Graceful exit, no orders

    logger.info({"message": "Orders prepared for upload to ShipStation", "count": len(all_orders_payload), "stage": "payload_preparation"})

    # --- DUPLICATE ORDER PRE-CHECK LOGIC START ---
    order_numbers_to_check = {order.get('orderNumber').strip().upper() for order in all_orders_payload if order.get('orderNumber')}
    
    earliest_order_date = None
    for order in all_orders_payload:
        order_date_str = order.get('orderDate')
        
        if order_date_str:
            try:
                current_order_date = parser.parse(order_date_str)
                
                if current_order_date.tzinfo is None:
                    current_order_date = current_order_date.replace(tzinfo=datetime.timezone.utc)
                else:
                    current_order_date = current_order_date.astimezone(datetime.timezone.utc)

                if isinstance(order_date_str, str) and order_date_str.isdigit() and len(order_date_str) > 8:
                    try:
                        current_order_date = datetime.datetime.fromtimestamp(int(order_date_str), tz=datetime.timezone.utc)
                    except ValueError:
                        pass
            except (ValueError, TypeError, parser.ParserError) as e:
                logger.warning({"message": "Could not parse orderDate for duplicate check", "order_date_string": order_date_str, "error": str(e)})
                continue

            if earliest_order_date is None or current_order_date < earliest_order_date:
                earliest_order_date = current_order_date
    
    if earliest_order_date is None:
        logger.warning({"message": "No valid order dates found in payload. Using default past date for duplicate check.", "default_days_ago": 30})
        earliest_order_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    
    create_date_start_iso = earliest_order_date.isoformat(timespec='seconds') + 'Z'
    create_date_end_iso = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + 'Z'

    logger.info({"message": "Checking for existing orders in ShipStation", "date_range_start": create_date_start_iso, "date_range_end": create_date_end_iso})
    existing_shipstation_orders = fetch_shipstation_existing_orders_by_date_range(
        shipstation_api_key,
        shipstation_api_secret,
        settings.SHIPSTATION_ORDERS_ENDPOINT,
        create_date_start_iso,
        create_date_end_iso
    )

    existing_order_numbers_set = {order.get('orderNumber').strip().upper() for order in existing_shipstation_orders if order.get('orderNumber')}
    
    new_orders_payload = []
    skipped_orders_count = 0
    for order in all_orders_payload:
        order_number = order.get('orderNumber')
        if order_number:
            normalized_order_number = order_number.strip().upper()
        else:
            normalized_order_number = None
        
        if normalized_order_number and normalized_order_number in existing_order_numbers_set:
            logger.info({
                "message": "Skipping duplicate order",
                "orderNumber": order_number,
                "normalizedOrderNumber": normalized_order_number,
                "reason": "already exists in ShipStation",
                "action": "skipped_upload"
            })
            skipped_orders_count += 1
        else:
            new_orders_payload.append(order)
    
    if skipped_orders_count > 0:
        logger.info({"message": "Duplicate orders skipped", "count": skipped_orders_count})
    
    if not new_orders_payload:
        logger.warning({"message": "No new unique orders to send to ShipStation after duplicate check", "action": "exiting_gracefully"})
        return True, 'No new unique orders to send to ShipStation' # Graceful exit, no orders

    logger.info({"message": "Proceeding with new unique orders for upload", "count": len(new_orders_payload)})
    # --- DUPLICATE ORDER PRE-CHECK LOGIC END ---

    # --- Send Orders to ShipStation ---
    upload_results = send_all_orders_to_shipstation(
        new_orders_payload,
        shipstation_api_key,
        shipstation_api_secret,
        settings.SHIPSTATION_CREATE_ORDERS_ENDPOINT
    )

    if upload_results:
        logger.info({"message": "ShipStation Upload Results Summary", "total_orders_attempted": len(new_orders_payload)})
        for result in upload_results:
            logger.info({
                "message": "ShipStation single order upload result",
                "orderKey": result.get('orderKey'),
                "success": result.get('success'),
                "errorMessage": result.get('errorMessage'),
                "type": "shipstation_api_response"
            })
    else:
        logger.warning({"message": "No results returned from ShipStation upload or an error occurred during sending", "status": "no_upload_results"})

    logger.info({"message": "ShipStation Order Uploader Script finished", "status": "completed"})
    return True, 'ShipStation Order Uploader script executed successfully!'

# # --- Local Execution Block (for Local Testing) ---
# # This block is for local testing only. It directly calls the core logic.
# # When deploying to a Cloud Function, this block should be commented out,
# # and the 'shipstation_order_uploader_http_trigger' function above should be active.
# if __name__ == "__main__":
#     print("--- Running shipstation_order_uploader_logic locally ---")
#     success, message = run_order_uploader_logic()
#     if success:
#         print(f"Local Test Result: SUCCESS - {message}")
#     else:
#         print(f"Local Test Result: FAILED - {message}")
#     print("--- Local execution finished ---")

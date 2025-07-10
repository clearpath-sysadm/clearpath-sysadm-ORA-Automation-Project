import sys
import os # For path manipulation for logging setup

# Add the project root to the Python path to enable imports from utils and services
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
import base64 
import json
import datetime # Still needed for datetime.datetime.now() for default end_date in fetch_shipstation_shipments if used.
import time # Still needed for time.sleep if any local function has it.
import xml.etree.ElementTree as ET # No longer needed here, moved to x_cart_parser
import pandas as pd # No longer needed here, moved to x_cart_parser

# Import our new API utility for robust requests and logging setup
from utils.api_utils import make_api_request
from utils.logging_config import setup_logging
import logging

# Import the new secret manager service
from src.services.gcp.secret_manager import access_secret_version
# Import the new ShipStation API client service
from src.services.shipstation.api_client import send_all_orders_to_shipstation 
# Import the new X-Cart Parser service
from src.services.data_parsers.x_cart_parser import parse_date, build_address_from_xml, parse_x_cart_xml_for_shipstation_payload # Import these functions


# --- Configuration for ShipStation API ---
YOUR_GCP_PROJECT_ID = "ora-automation-project"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"

# --- ShipStation API Endpoints for Order Creation ---
SHIPSTATION_CREATE_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders/createorders"

# --- Service Account Key Path (Used for Secret Manager Access) ---
# IMPORTANT: This path should point to your *actual* service account JSON key for Secret Manager.
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"


# --- Data Source: X-Cart XML for Test Orders ---
# This path should point to your X-Cart XML test file.
X_CART_XML_PATH = "C:\\Users\\NathanNeely\\Projects\\ORA_Automation\\src\\test_data\\x_cart_orders_bundle_test.xml" # This can also be updated to point to test_data/test_x_cart_orders.xml

# Scopes required for reading and writing to Google Sheets (if used for state management/config)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The Secret ID for your Google Sheets service account JSON key (if needed for state)
GOOGLE_SHEETS_SERVICE_ACCOUNT_SECRET_ID = "google-sheets-service-account-key"


# --- Bundle Product Configuration (Comprehensive, from SQL SPROC) ---
BUNDLE_CONFIG = {
    # -------------------------------------------------------------
    # Single Component Bundles (from main CASE statements for ProductId and Quantity)
    # -------------------------------------------------------------
    "18075": {"component_id": "17913", "multiplier": 1},
    "18225": {"component_id": "17612", "multiplier": 40}, # OraCare Buy 30 Get 8 Free
    "18235": {"component_id": "17612", "multiplier": 15}, # OraCare Buy 12 Get 3 Free
    "18255": {"component_id": "17612", "multiplier": 6},  # OraCare Buy 5 Get 1 Free
    "18345": {"component_id": "17612", "multiplier": 1},  # Autoship; OraCare Health Rinse
    "18355": {"component_id": "17612", "multiplier": 1},  # Free; OraCare Buy 5 Get 1 Free
    "18185": {"component_id": "17612", "multiplier": 41}, # Webinar Special: OraCare Buy 30 Get 11 Free
    "18215": {"component_id": "17612", "multiplier": 16}, # Webinar Special: OraCare Buy 12 Get 4 Free
    "18435": {"component_id": "17612", "multiplier": 1},  # OraCare at Grandfathered $219 price
    "18445": {"component_id": "17612", "multiplier": 1},  # Autoship; FREE Case OraCare Health Rinse
    "18575": {"component_id": "17612", "multiplier": 50}, # 2022 Cyber Monday 30 Get 20 Free
    "18585": {"component_id": "17612", "multiplier": 18}, # 2022 Cyber Monday 12 Get 6 Free
    "18595": {"component_id": "17612", "multiplier": 7},  # 2022 Cyber Monday 5 Get 2 Free
    "18655": {"component_id": "17612", "multiplier": 45}, # 2023 Cyber Monday 30 Get 15 Free
    "18645": {"component_id": "17612", "multiplier": 18}, # 2023 Cyber Monday 12 Get 6 Free
    "18635": {"component_id": "17612", "multiplier": 9},  # 2023 Cyber Monday 6 Get 3 Free
    "18785": {"component_id": "17612", "multiplier": 45}, # 2024 Cyber Monday 30 Get 15 Free
    "18775": {"component_id": "17612", "multiplier": 18}, # 2024 Cyber Monday 12 Get 6 Free
    "18765": {"component_id": "17612", "multiplier": 9},  # 2024 Cyber Monday 6 Get 3 Free
    "18625": {"component_id": "17612", "multiplier": 3},  # Starter Pack = 3 * 17612
    # Maps to 17914
    "18265": {"component_id": "17914", "multiplier": 40}, # PPR Buy 30 Get 10 Free
    "18275": {"component_id": "17914", "multiplier": 15}, # PPR Buy 12 Get 3 Free
    "18285": {"component_id": "17914", "multiplier": 6},  # PPR Buy 5 Get 1 Free
    "18195": {"component_id": "17914", "multiplier": 1},  # Autoship; OraCare PPR
    "18375": {"component_id": "17914", "multiplier": 1},  # Free; OraCare PPR
    "18455": {"component_id": "17914", "multiplier": 1},  # Autoship; FREE OraCare PPR
    "18495": {"component_id": "17914", "multiplier": 16}, # Webinar Special; PPR Buy 12 Get 4 Free
    "18485": {"component_id": "17914", "multiplier": 41}, # Webinar Special; PPR Buy 30 Get 11 Free
    # Maps to 17904
    "18295": {"component_id": "17904", "multiplier": 40}, # Travel Buy 30 Get 10 Free
    "18305": {"component_id": "17904", "multiplier": 15}, # Travel Buy 12 Get 3 Free
    "18425": {"component_id": "17904", "multiplier": 6},  # Travel Buy 5 Get 1 Free
    "18385": {"component_id": "17904", "multiplier": 1},  # Autoship; OraCare Travel
    "18395": {"component_id": "17904", "multiplier": 1},  # Free; OraCare Travel
    "18465": {"component_id": "17904", "multiplier": 1},  # Autoship; FREE OraCare Travel
    "18515": {"component_id": "17904", "multiplier": 16}, # Webinar Special; Travel Buy 12 Get 4
    # Maps to 17975
    "18315": {"component_id": "17975", "multiplier": 40}, # Reassure Buy 30 Get 10 Free
    "18325": {"component_id": "17975", "multiplier": 15}, # Reassure Buy 12 Get 3 Free
    "18335": {"component_id": "17975", "multiplier": 6},  # Reassure Buy 5 Get 1 Free
    "18405": {"component_id": "17975", "multiplier": 1},  # Autoship; OraCare Reassure
    "18415": {"component_id": "17975", "multiplier": 1},  # Free; OraCare Reassure
    "18525": {"component_id": "17975", "multiplier": 41}, # Webinar Special; Reassure Buy 30 Get 11 Free
    "18535": {"component_id": "17975", "multiplier": 16}, # Webinar Special; Reassure Buy 12 Get 4
    # Note: 18405 is duplicated in SPROC for Autoship & Autoship FREE, assuming it maps to 1x component.
    # Maps to 18675 (Ortho Protect)
    "18685": {"component_id": "18675", "multiplier": 40}, # Ortho Protect Buy 30 Get 10 Free
    "18695": {"component_id": "18675", "multiplier": 15}, # Ortho Protect Buy 12 Get 3 Free
    "18705": {"component_id": "18675", "multiplier": 6},  # Ortho Protect Buy 5 Get 1 Free
    "18715": {"component_id": "18675", "multiplier": 41}, # Webinar Special- Buy 30 Get 11 Free
    "18725": {"component_id": "18675", "multiplier": 16}, # Webinar Special- Buy 12 Get 4 Free
    "18735": {"component_id": "18675", "multiplier": 1},  # Autoship- Ortho Protect 1
    "18745": {"component_id": "17612", "multiplier": 1},  # Autoship- Free Ortho Protect 1
    # Multi-Component Bundles
    "18605": [
        {"component_id": "17612", "multiplier": 4},
        {"component_id": "17914", "multiplier": 1},
        {"component_id": "17904", "multiplier": 1},
    ],
    "18615": [
        {"component_id": "17612", "multiplier": 4},
        {"component_id": "17914", "multiplier": 1},
        {"component_id": "17904", "multiplier": 1},
        {"component_id": "17975", "multiplier": 1},
    ]
}


# --- Setup Logging for this script ---
# This ensures that all output from this script goes through our configured logging system.
# The log file will be in C:\Users\NathanNeely\Projects\ORA_Automation\logs\app.log
_log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
_log_file = os.path.join(_log_dir, 'app.log')
setup_logging(log_file_path=_log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


# --- Helper Functions (All XML parsing functions have been migrated) ---


if __name__ == "__main__":
    logger.info("Starting ShipStation Order Uploader Script (Python version)...")

    # --- Retrieve API credentials ---
    shipstation_api_key = access_secret_version(
        YOUR_GCP_PROJECT_ID,
        SHIPSTATION_API_KEY_SECRET_ID,
        credentials_path=SERVICE_ACCOUNT_KEY_PATH
    )
    shipstation_api_secret = access_secret_version(
        YOUR_GCP_PROJECT_ID,
        SHIPSTATION_API_SECRET_SECRET_ID,
        credentials_path=SERVICE_ACCOUNT_KEY_PATH
    )

    if not shipstation_api_key or not shipstation_api_secret:
        logger.critical("Failed to retrieve ShipStation API credentials. Exiting.")
        exit(1) # Use exit(1) for abnormal termination

    logger.info(f"ShipStation API Key retrieved (truncated): {shipstation_api_key[:5]}...")
    logger.info(f"ShipStation API Secret retrieved (truncated): {shipstation_api_secret[:5]}...")

    # --- Parse Data from X-Cart XML ---
    logger.info(f"Loading orders from X-Cart XML file: {X_CART_XML_PATH}...")
    # Now calling the function from the new x_cart_parser module
    all_orders_payload = parse_x_cart_xml_for_shipstation_payload(X_CART_XML_PATH, BUNDLE_CONFIG)
        
    if not all_orders_payload:
        logger.warning("No valid orders to send to ShipStation after processing XML. Exiting.")
        exit(0) # Use exit(0) for graceful exit with no orders

    logger.info(f"Prepared {len(all_orders_payload)} orders for upload to ShipStation.")

    # --- Send Orders to ShipStation ---
    # Now calling the function from the new api_client module
    upload_results = send_all_orders_to_shipstation(
        all_orders_payload,
        shipstation_api_key,
        shipstation_api_secret,
        SHIPSTATION_CREATE_ORDERS_ENDPOINT # Pass the endpoint URL
    )

    if upload_results:
        logger.info(f"--- ShipStation Upload Results ---")
        for result in upload_results:
            logger.info(f"OrderKey: {result.get('orderKey')}, Success: {result.get('success')}, ErrorMessage: {result.get('errorMessage')}")
    else:
        logger.warning("No results returned from ShipStation upload or an error occurred during sending.")

    logger.info("Script finished. (Order upload attempt completed)")

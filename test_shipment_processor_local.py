# test_shipment_processor_live.py
import sys
import os
import logging
import datetime
import pandas as pd

# Add the project root to the Python path to enable imports from services and utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import constants directly from settings.py
from config.settings import (
    YOUR_GCP_PROJECT_ID,
    SHIPSTATION_API_KEY_SECRET_ID,
    SHIPSTATION_API_SECRET_SECRET_ID,
    SERVICE_ACCOUNT_KEY_PATH,
    SHIPSTATION_SHIPMENTS_ENDPOINT,
    GOOGLE_SHEET_ID,
    ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME,
    SHIPPED_ORDERS_DATA_TAB_NAME,
    SHIPSTATION_BASE_URL,
)

# Import necessary modules
from utils.logging_config import setup_logging
from src.services.gcp.secret_manager import access_secret_version
from src.services.data_processing.shipment_processor import (
    process_shipped_items,
    process_shipped_orders,
    aggregate_weekly_shipped_history,
)
from src.services.google_sheets.sheets_api import SheetsApiModule
# FIX: Import the new functions from api_client.py
from src.services.shipstation.api_client import (
    get_shipstation_credentials, # FIX: Import the function from api_client.py
    fetch_shipstation_shipments,
    get_shipstation_headers,
    make_api_request
)

# Setup logging to ensure console output
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')
setup_logging(log_file_path=log_file, log_level=logging.DEBUG, enable_console_logging=True)
logger = logging.getLogger(__name__)

# FIX: Remove the local copies of these functions to rely on the imported versions.
# def get_shipstation_credentials():
#     """
#     Retrieves ShipStation API credentials securely from Google Cloud Secret Manager.
#     """
#     try:
#         logger.info("Attempting to retrieve ShipStation API Key from Secret Manager...")
#         api_key = access_secret_version(
#             YOUR_GCP_PROJECT_ID,
#             SHIPSTATION_API_KEY_SECRET_ID,
#             credentials_path=SERVICE_ACCOUNT_KEY_PATH
#         )
#         logger.info("Attempting to retrieve ShipStation API Secret from Secret Manager...")
#         api_secret = access_secret_version(
#             YOUR_GCP_PROJECT_ID,
#             SHIPSTATION_API_SECRET_SECRET_ID,
#             credentials_path=SERVICE_ACCOUNT_KEY_PATH
#         )
#         if not api_key or not api_secret:
#             logger.error("Failed to retrieve ShipStation API credentials.")
#             return None, None
#         return api_key, api_secret
#     except Exception as e:
#         logger.error(f"Error retrieving ShipStation credentials: {e}", exc_info=True)
#         return None, None

def get_last_processed_dates():
    """
    Reads the last processed dates from the Google Sheets tabs to define the new date range.
    """
    logger.info("Reading last processed dates from Google Sheets...")
    
    # Read the last recorded Stop Date from ORA_Weekly_Shipped_History
    weekly_history_data = SheetsApiModule.get_google_sheet_data(
        GOOGLE_SHEET_ID, ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME, 'B:B', SERVICE_ACCOUNT_KEY_PATH
    )
    last_weekly_stop_date = None
    if weekly_history_data and len(weekly_history_data) > 1:
        last_weekly_stop_date_str = weekly_history_data[-1][0]
        last_weekly_stop_date = datetime.datetime.strptime(last_weekly_stop_date_str, '%m/%d/%Y').date()
        logger.info(f"Last recorded stop date for weekly history: {last_weekly_stop_date}")
    
    # Read the last recorded date from Shipped_Orders_Data (or Shipped_Items_Data)
    orders_data = SheetsApiModule.get_google_sheet_data(
        GOOGLE_SHEET_ID, SHIPPED_ORDERS_DATA_TAB_NAME, 'A:A', SERVICE_ACCOUNT_KEY_PATH
    )
    last_order_date = None
    if orders_data and len(orders_data) > 1:
        last_order_date_str = orders_data[-1][0]
        last_order_date = datetime.datetime.strptime(last_order_date_str, '%m/%d/%Y').date()
        logger.info(f"Last recorded date for monthly data: {last_order_date}")

    return last_weekly_stop_date, last_order_date

def main():
    """
    Main function to test the new shipment_processor functions with live data.
    """
    logger.info("--- Starting live test of shipment_processor.py functions with comprehensive data ---")

    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_key:
        return

    # --- 1. Determine Comprehensive Date Range ---
    last_weekly_stop_date, last_order_date = get_last_processed_dates()

    # Determine the date range needed for all reports
    today = datetime.date.today()
    
    # The last date to pull from ShipStation should be today's date
    end_date = today.strftime('%Y-%m-%d')
    
    # Calculate the earliest possible start date for the master API pull
    # The pull must include the full last month AND the last 52 weeks
    
    # Start date for monthly data: The beginning of the month of the last order date.
    # if last_order_date:
    #     monthly_start_date = last_order_date.replace(day=1)
    # else:
    #     # If no previous monthly data, default to the start of the current month
    monthly_start_date = today.replace(day=1)

    # Start date for weekly data: The start date of the data for the last 52 weeks.
    if last_weekly_stop_date:
        # The pull must include all data from the past 52 weeks, starting from the last date in the weekly report.
        weekly_start_date = last_weekly_stop_date - datetime.timedelta(weeks=51)
    else:
        # If no previous weekly data, pull a full 52 weeks ending today.
        weekly_start_date = today - datetime.timedelta(weeks=52)

    # The overall API pull needs to start from the earliest of these calculated dates
    start_date = min(weekly_start_date, monthly_start_date)

    start_date_str = start_date.strftime('%Y-%m-%d')

    logger.info(f"Using comprehensive date range: {start_date_str} to {end_date}")
    
    # --- 2. Get Live Data from ShipStation API for each specific range ---
    
    live_shipment_data = fetch_shipstation_shipments(
        api_key=api_key,
        api_secret=api_secret,
        shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,
        start_date=start_date_str,
        end_date=end_date,
        shipment_status="shipped"
    )
    
    if not live_shipment_data:
        logger.warning("No live data returned from ShipStation API. Cannot proceed with processing.")
        return

    # FIX: Add a filtering step to remove voided shipments
    non_voided_shipments = [shipment for shipment in live_shipment_data if not shipment.get('voided', False)]
    logger.info(f"Filtered out {len(live_shipment_data) - len(non_voided_shipments)} voided shipments. Processing {len(non_voided_shipments)} non-voided shipments.")


    # --- 3. Process Data for each tab ---
    
    # Process monthly data for Shipped_Items_Data
    logger.info("\n--- Testing process_shipped_items ---")
    items_df = process_shipped_items(non_voided_shipments)
    # FIX: Convert the 'Ship Date' column to datetime before filtering
    items_df['Ship Date'] = pd.to_datetime(items_df['Ship Date'])
    # FIX: Filter by the month of the last recorded date for a full month's data
    if last_order_date:
        items_df = items_df[(items_df['Ship Date'].dt.year == today.year) & (items_df['Ship Date'].dt.month == today.month)]
    else:
        items_df = items_df[(items_df['Ship Date'].dt.year == today.year) & (items_df['Ship Date'].dt.month == today.month)]
    logger.info("Resulting DataFrame for Shipped_Items_Data:")
    logger.info(items_df.to_string())

    # Process monthly data for Shipped_Orders_Data
    logger.info("\n--- Testing process_shipped_orders ---")
    orders_df = process_shipped_orders(non_voided_shipments)
    # FIX: Convert the 'Ship Date' column to datetime before filtering
    orders_df['Ship Date'] = pd.to_datetime(orders_df['Ship Date'])
    # FIX: Filter by the month of the last recorded date for a full month's data
    if last_order_date:
        orders_df = orders_df[(orders_df['Ship Date'].dt.year == today.year) & (orders_df['Ship Date'].dt.month == today.month)]
    else:
        orders_df = orders_df[(orders_df['Ship Date'].dt.year == today.year) & (orders_df['Ship Date'].dt.month == today.month)]
    logger.info("Resulting DataFrame for Shipped_Orders_Data:")
    logger.info(orders_df.to_string())

    # Process weekly data for ORA_Weekly_Shipped_History
    logger.info("\n--- Testing aggregate_weekly_shipped_history ---")
    target_skus = ['17612', '17904', '17914', '18675', '18795']
    weekly_history_df = aggregate_weekly_shipped_history(non_voided_shipments, target_skus)
    logger.info("Resulting DataFrame for ORA_Weekly_Shipped_History:")
    logger.info(weekly_history_df.to_string())

    logger.info("\n--- All live tests finished successfully! ---")

if __name__ == "__main__":
    main()

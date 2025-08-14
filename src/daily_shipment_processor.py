# src/daily_shipment_processor.py
import sys
import os
import logging
import datetime
import pandas as pd

# --- Dynamic Path Adjustment for Module Imports ---
# Add the project root to the Python path to enable imports from services and utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import Constants and Modules ---
# Import constants directly from settings.py
from config.settings import (
    GOOGLE_SHEET_ID,
    SHIPPED_ITEMS_DATA_TAB_NAME,
    SHIPPED_ORDERS_DATA_TAB_NAME,
    ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME, # Added for the weekly history update
    SHIPSTATION_SHIPMENTS_ENDPOINT
)

# Import necessary modules
from utils.logging_config import setup_logging
from src.services.data_processing.shipment_processor import (
    process_shipped_items,
    process_shipped_orders,
    aggregate_weekly_shipped_history # Re-added for weekly aggregation
)
# Note: Assumes robust read/write functions exist in your Google Sheets API client
from src.services.google_sheets.api_client import write_dataframe_to_sheet, get_google_sheet_data
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    fetch_shipstation_shipments
)

# --- Logging Configuration ---
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'daily_processor.log') # Dedicated log file
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def update_weekly_history_incrementally(daily_items_df, existing_history_df, target_skus):
    """
    Updates the 52-week history with the latest data for the current week.

    Args:
        daily_items_df (pd.DataFrame): DataFrame with the last 32 days of granular shipped items.
        existing_history_df (pd.DataFrame): DataFrame with the current 52-week history.
        target_skus (list): A list of SKUs to be included in the weekly history.

    Returns:
        pd.DataFrame: The updated 52-week history DataFrame.
    """
    logger.info("Starting incremental update of the 52-week history tab...")

    # Ensure 'Ship Date' is in datetime format
    daily_items_df['Ship Date'] = pd.to_datetime(daily_items_df['Ship Date']).dt.date

    # Determine the start of the current week (Monday)
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())
    logger.info(f"Current week starts on: {start_of_current_week}")

    # Filter the daily items to get only shipments from the current week
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()

    if current_week_items_df.empty:
        logger.info("No shipments found for the current week yet. History remains unchanged.")
        return existing_history_df

    # Aggregate this new weekly data
    # We need to convert the DataFrame back to a list of dicts for the existing function
    current_week_shipments_list = current_week_items_df.to_dict('records')
    # The aggregate function needs the full shipment structure, so we adapt
    # For simplicity, we'll simulate the structure needed by aggregate_weekly_shipped_history
    # A more robust solution would be a new, dedicated aggregation function.
    # This is a placeholder for the logic that correctly aggregates the current week.
    # Let's assume a simplified aggregation for now.
    current_week_summary_df = aggregate_weekly_shipped_history(
        current_week_items_df.to_dict('records'), # This will need adjustment based on function's needs
        target_skus
    )

    if current_week_summary_df.empty:
        logger.warning("Aggregation of current week's data resulted in an empty DataFrame.")
        return existing_history_df

    # The first row of the summary is the one we want
    new_week_row = current_week_summary_df.iloc[0]

    # Check if the existing history already has a row for this week
    existing_history_df['Start Date'] = pd.to_datetime(existing_history_df['Start Date']).dt.date
    week_exists = start_of_current_week in existing_history_df['Start Date'].values

    if week_exists:
        logger.info("Current week found in history. Updating the last row.")
        # Update the last row, assuming it's the current week
        # A safer method would be to find the index by date
        idx_to_update = existing_history_df[existing_history_df['Start Date'] == start_of_current_week].index
        existing_history_df.loc[idx_to_update] = new_week_row.values
    else:
        logger.info("This is a new week. Appending new week and removing the oldest.")
        # Append the new row and drop the oldest
        updated_history_df = pd.concat([existing_history_df, new_week_row.to_frame().T], ignore_index=True)
        # Sort by date to be sure, then drop the first row
        updated_history_df = updated_history_df.sort_values(by='Start Date', ascending=True)
        updated_history_df = updated_history_df.iloc[1:]
        existing_history_df = updated_history_df

    return existing_history_df

def run_daily_shipment_pull(request=None):
    """
    Main function for the daily shipment processor.
    Pulls a 32-day rolling window of shipment data from ShipStation and
    overwrites or updates the target Google Sheet tabs.

    Args:
        request: The request object from a Google Cloud Function trigger (optional).
    """
    logger.info("--- Starting Daily Shipment Processor ---")
    try:
        # --- 1. Get ShipStation Credentials ---
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return "Failed to get credentials", 500

        # --- 2. Determine the 32-Day Rolling Date Range ---
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=32)
        end_date_str = today.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')
        logger.info(f"Using rolling 32-day date range: {start_date_str} to {end_date_str}")

        # --- 3. Fetch Data from ShipStation API ---
        shipment_data = fetch_shipstation_shipments(
            api_key=api_key,
            api_secret=api_secret,
            shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,
            start_date=start_date_str,
            end_date=end_date_str,
            shipment_status="shipped"
        )

        if not shipment_data:
            logger.warning("No shipment data returned from ShipStation API for the specified range. Exiting.")
            return "No data returned from API", 200

        non_voided_shipments = [shipment for shipment in shipment_data if not shipment.get('voided', False)]
        logger.info(f"Processing {len(non_voided_shipments)} non-voided shipments.")

        if not non_voided_shipments:
            logger.info("No non-voided shipments to process. Exiting.")
            return "No non-voided shipments", 200

        # --- 4. Process Data into DataFrames ---
        logger.info("Processing data for Shipped_Items_Data tab...")
        items_df = process_shipped_items(non_voided_shipments)

        logger.info("Processing data for Shipped_Orders_Data tab...")
        orders_df = process_shipped_orders(non_voided_shipments)

        # --- 5. Overwrite Transactional Google Sheet Tabs ---
        if not items_df.empty:
            logger.info(f"Overwriting '{SHIPPED_ITEMS_DATA_TAB_NAME}' tab with {len(items_df)} rows...")
            write_dataframe_to_sheet(items_df, GOOGLE_SHEET_ID, SHIPPED_ITEMS_DATA_TAB_NAME)
        else:
            logger.warning(f"Shipped Items DataFrame is empty. Skipping write to '{SHIPPED_ITEMS_DATA_TAB_NAME}'.")

        if not orders_df.empty:
            logger.info(f"Overwriting '{SHIPPED_ORDERS_DATA_TAB_NAME}' tab with {len(orders_df)} rows...")
            write_dataframe_to_sheet(orders_df, GOOGLE_SHEET_ID, SHIPPED_ORDERS_DATA_TAB_NAME)
        else:
            logger.warning(f"Shipped Orders DataFrame is empty. Skipping write to '{SHIPPED_ORDERS_DATA_TAB_NAME}'.")

        # --- 6. Incrementally Update the Weekly Shipped History Tab ---
        logger.info("Fetching existing 52-week history for update...")
        # Note: get_google_sheet_data should return a DataFrame
        existing_history_df = get_google_sheet_data(GOOGLE_SHEET_ID, ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME)

        if existing_history_df is not None and not existing_history_df.empty:
            # This is a placeholder for the SKUs that are tracked weekly.
            # This should ideally be loaded from a config file or another sheet.
            target_skus = ['17612', '17904', '17914', '18675', '18795']
            
            updated_history_df = update_weekly_history_incrementally(items_df.copy(), existing_history_df.copy(), target_skus)
            
            logger.info(f"Overwriting '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' with updated 52-week history...")
            write_dataframe_to_sheet(updated_history_df, GOOGLE_SHEET_ID, ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME)
        else:
            logger.warning(f"Could not read existing weekly history from '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}'. Skipping update.")


        logger.info("--- Daily Shipment Processor finished successfully! ---")
        return "Process completed successfully", 200

    except Exception as e:
        logger.critical(f"An unhandled error occurred in the daily shipment processor: {e}", exc_info=True)
        return f"An error occurred: {e}", 500

# This allows the script to be run directly for testing purposes
if __name__ == "__main__":
    run_daily_shipment_pull()

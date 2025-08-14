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


def update_weekly_history_incrementally(daily_items_df, existing_history_df, target_skus, shipment_data):
    # --- Ensure all variables are defined before use ---
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())

    # After filtering for current week, log the DataFrame and unique SKUs
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()
    # Debug print for SKU 17612 quantity in current week
    sku_17612_df = current_week_items_df[current_week_items_df['Base SKU'] == '17612']
    print("\n[DEBUG] Current week total Quantity Shipped for SKU 17612:", sku_17612_df['Quantity Shipped'].sum())
    print("[DEBUG] Current week rows for SKU 17612:")
    print(sku_17612_df)
    logger.info(f"Full current_week_items_df for current week:\n{current_week_items_df}")
    logger.info(f"current_week_items_df shape: {current_week_items_df.shape}")
    logger.info(f"current_week_items_df head:\n{current_week_items_df.head(10)}")
    logger.info(f"Unique 'Base SKU' values in current_week_items_df: {sorted(current_week_items_df['Base SKU'].unique())}")
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

    """
    Updates the 52-week history with the latest data for the current week.

    Args:
        daily_items_df (pd.DataFrame): DataFrame with the last 32 days of granular shipped items.
        existing_history_df (pd.DataFrame): DataFrame with the current 52-week history.
        target_skus (list): A list of SKUs to be included in the weekly history.

    Returns:
        pd.DataFrame: The updated 52-week history DataFrame.
    """


    # Ensure 'Ship Date' is in datetime format
    daily_items_df['Ship Date'] = pd.to_datetime(daily_items_df['Ship Date']).dt.date

    logger.info(f"Current week starts on: {start_of_current_week}")
    logger.info(f"Unique Ship Dates in daily_items_df: {sorted(daily_items_df['Ship Date'].unique())}")
    logger.info(f"Min Ship Date: {daily_items_df['Ship Date'].min()}, Max Ship Date: {daily_items_df['Ship Date'].max()}")

    # Now safe to filter and log current week items
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()
    logger.info(f"current_week_items_df shape: {current_week_items_df.shape}")
    logger.info(f"current_week_items_df head:\n{current_week_items_df.head(10)}")
    logger.info(f"Unique 'Base SKU' values in current_week_items_df: {sorted(current_week_items_df['Base SKU'].unique())}")

    # Determine the start of the current week (Monday)
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())
    logger.info(f"Current week starts on: {start_of_current_week}")
    # Debug: Show unique Ship Dates and min/max
    logger.debug(f"Unique Ship Dates in daily_items_df: {sorted(daily_items_df['Ship Date'].unique())}")
    logger.debug(f"Min Ship Date: {daily_items_df['Ship Date'].min()}, Max Ship Date: {daily_items_df['Ship Date'].max()}")

    # --- DEBUG LOGGING FOR SKU 17612 ---
    logger.debug(f"Today's date: {today}")
    logger.debug("Today's shipments for SKU 17612:")
    logger.debug(daily_items_df[daily_items_df['Base SKU'] == '17612'])
    if not existing_history_df.empty:
        last_row = existing_history_df.tail(1)
        logger.debug("Last row in ORA_Weekly_Shipped_History:")
        logger.debug(last_row)
        if '17612' in existing_history_df.columns:
            logger.debug(f"Value for 17612 in last row: {last_row['17612'].values[0]}")
        logger.debug(f"Last week Start Date: {last_row['Start Date'].values[0]}, Stop Date: {last_row['Stop Date'].values[0]}")
    today_sum = daily_items_df[daily_items_df['Base SKU'] == '17612']['Quantity Shipped'].sum()
    logger.debug(f"Sum of today's shipments for SKU 17612: {today_sum}")

    # Filter the daily items to get only shipments from the current week
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()

    logger.debug("Filtered daily_items_df for current week:")
    logger.debug(current_week_items_df)

    for sku in target_skus:
        sku_filtered = current_week_items_df[current_week_items_df['Base SKU'].astype(str) == str(sku)]
        logger.debug(f"Current week items for SKU {sku}:")
        logger.debug(sku_filtered)

    if current_week_items_df.empty:
        logger.info("No shipments found for the current week yet. History remains unchanged.")
        return existing_history_df

    # Aggregate this new weekly data using the original raw shipment data filtered for the current week
    # This assumes you have access to the original shipment_data (raw API response) in scope
    # You may need to pass shipment_data as an argument to this function if not already available
    def filter_shipments_for_week(shipment_data, start_of_week, end_of_week):
        filtered = []
        for s in shipment_data:
            ship_date = s.get('shipDate')
            if ship_date:
                ship_date_dt = datetime.datetime.strptime(ship_date[:10], '%Y-%m-%d').date()
                if start_of_week <= ship_date_dt <= start_of_week + datetime.timedelta(days=6):
                    filtered.append(s)
        return filtered

    current_week_shipments = filter_shipments_for_week(shipment_data, start_of_current_week, start_of_current_week + datetime.timedelta(days=6))
    current_week_summary_df = aggregate_weekly_shipped_history(
        current_week_shipments,
        target_skus
    )

    # Debug print: show the summary DataFrame and the row to be written
    print("\n[DEBUG] Aggregated weekly summary DataFrame (current_week_summary_df):")
    print(current_week_summary_df)
    if not current_week_summary_df.empty:
        print("[DEBUG] Aggregated values by SKU for the current week:")
        for sku in target_skus:
            print(f"  SKU {sku}: {current_week_summary_df.iloc[0].get(str(sku), 'N/A')}")
        print("[DEBUG] Full row to be written to sheet:")
        print(current_week_summary_df.iloc[0])

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

        # Convert list of lists to DataFrame if needed
        sheet_data = existing_history_df
        if sheet_data and len(sheet_data) > 1:
            existing_history_df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
        else:
            # Define expected columns for the weekly history tab (match actual sheet layout)
            expected_columns = ['Start Date', 'Stop Date', '17612', '17904', '17914', '18675', '18795']
            existing_history_df = pd.DataFrame(columns=expected_columns)

        if not existing_history_df.empty:
            # This is a placeholder for the SKUs that are tracked weekly.
            # This should ideally be loaded from a config file or another sheet.
            target_skus = ['17612', '17904', '17914', '18675', '18795']
            updated_history_df = update_weekly_history_incrementally(items_df.copy(), existing_history_df.copy(), target_skus, shipment_data)
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

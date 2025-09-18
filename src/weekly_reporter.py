import pandas as pd
import datetime
import math
import time
import logging

# Add the project root to the Python path to enable imports from services and config
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the new Google Sheets API client service
from src.services.google_sheets.api_client import get_google_sheet_data, write_dataframe_to_sheet
# Import inventory and average calculations from their new modules
from src.services.reporting_logic.inventory_calculations import calculate_current_inventory
from src.services.reporting_logic.average_calculations import calculate_12_month_rolling_average
# Import report data loader to get key SKUs
from src.services.reporting_logic.report_data_loader import get_key_skus_and_product_names, get_weekly_shipped_history

# Import centralized configuration settings
from config.settings import settings 


# --- Environment Detection ---
try:
    from config import settings
    ENV = getattr(settings, 'get_environment', lambda: 'unknown')()
except ImportError:
    ENV = 'unknown'
IS_LOCAL_ENV = ENV == 'local'
IS_CLOUD_ENV = ENV == 'cloud'

# --- Logging Setup ---
logger = logging.getLogger('weekly_reporter')
logger.setLevel(logging.DEBUG)
if IS_LOCAL_ENV:
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'weekly_reporter.log')
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
else:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False
logger.info(f"Weekly Reporter started. Environment: {ENV.upper()}")


def generate_weekly_inventory_report(google_sheet_id: str, weekly_report_tab_name: str):
    """
    Orchestrates the generation of the Weekly Inventory Report.
    """
    logger.info("--- Starting Weekly Inventory Report Generation ---")

    # 1. Get Key SKUs and Product Names
    key_skus_list, product_names_map = get_key_skus_and_product_names(google_sheet_id)
    if not key_skus_list:
        logger.error("Could not retrieve Key Products. Aborting report generation.")
        return
    # --- NEW DIAGNOSTIC LOGGING ---
    logger.debug(f"Step 1 Complete: Found {len(key_skus_list)} Key SKUs.")

    # 2. Get Historical Shipped Data
    weekly_shipped_history_df = get_weekly_shipped_history(google_sheet_id, key_skus_list)
    # --- NEW DIAGNOSTIC LOGGING ---
    if weekly_shipped_history_df is not None:
        logger.debug(f"Step 2 Complete: Fetched {len(weekly_shipped_history_df)} rows of weekly shipped history.")
    else:
        logger.error("Failed to fetch weekly shipped history. Aborting.")
        return

    # 3. Get Transactional Data for Current Inventory Calculation
    inventory_transactions_df = get_google_sheet_data(google_sheet_id, settings.INVENTORY_TRANSACTIONS_TAB_NAME)
    shipped_items_df = get_google_sheet_data(google_sheet_id, settings.SHIPPED_ITEMS_DATA_TAB_NAME)
    # --- NEW DIAGNOSTIC LOGGING ---
    if inventory_transactions_df is not None and shipped_items_df is not None:
         logger.debug(f"Step 3 Complete: Fetched {len(inventory_transactions_df)} inventory transactions and {len(shipped_items_df)} shipped items.")
    else:
        logger.error("Failed to fetch transaction or shipped item data. Aborting.")
        return

    # 4. Calculate Current Inventory
    from datetime import datetime, timedelta
    current_week_end_date = datetime.now().date()
    current_week_start_date = current_week_end_date - timedelta(days=7)
    current_inventory_df = calculate_current_inventory({}, inventory_transactions_df, shipped_items_df, key_skus_list, current_week_start_date, current_week_end_date)
    # --- NEW DIAGNOSTIC LOGGING ---
    if current_inventory_df is not None:
        logger.debug(f"Step 4 Complete: Calculated current inventory for {len(current_inventory_df)} SKUs.")
    else:
        logger.error("Failed to calculate current inventory. Aborting.")
        return

    # 5. Calculate 12-Month Rolling Average
    rolling_average_df = calculate_12_month_rolling_average(weekly_shipped_history_df)
    # --- NEW DIAGNOSTIC LOGGING ---
    if rolling_average_df is not None:
        logger.debug(f"Step 5 Complete: Calculated rolling average for {len(rolling_average_df)} SKUs.")
    else:
        logger.error("Failed to calculate rolling average. Aborting.")
        return

    # 6. Combine DataFrames and Generate Final Report
    if current_inventory_df.empty:
        logger.warning("Current inventory data is empty. Cannot generate weekly report.")
        return
        
    # Merge current inventory with product names
    weekly_report_df = pd.merge(current_inventory_df, product_names_map, on='SKU', how='left')
    # Merge the result with rolling averages
    weekly_report_df = pd.merge(weekly_report_df, rolling_average_df, on='SKU', how='left')
    
    # Final formatting
    weekly_report_df = weekly_report_df.rename(columns={'Quantity': 'Current Quantity', 'Rolling_Avg': 'Weekly Avg'})
    weekly_report_df['Weekly Avg'] = weekly_report_df['Weekly Avg'].fillna('Insufficient Data')
    
    # --- NEW DIAGNOSTIC LOGGING ---
    logger.debug(f"Step 6 Complete: Final report DataFrame has {len(weekly_report_df)} rows before writing to sheet.")

    # 7. Write to Google Sheet
    if not weekly_report_df.empty:
        logger.info(f"Writing {len(weekly_report_df)} rows to the '{weekly_report_tab_name}' tab.")
        write_dataframe_to_sheet(weekly_report_df, google_sheet_id, weekly_report_tab_name)
    else:
        logger.warning("Final report DataFrame is empty. Nothing to write to the sheet.")

    logger.info("--- Weekly Inventory Report Generation Finished ---")


if __name__ == "__main__":
    generate_weekly_inventory_report(
        google_sheet_id=settings.GOOGLE_SHEET_ID,
        weekly_report_tab_name=settings.WEEKLY_REPORT_OUTPUT_TAB_NAME
    )

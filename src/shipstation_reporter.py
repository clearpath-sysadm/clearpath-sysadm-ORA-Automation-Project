# TESTING DEPLOYMENT 2025-07-10 (2ND ATTEMPT)#
# 3RD ATTEMPT#


import pandas as pd
from datetime import datetime, date # Import date as well for explicit date objects
import os
import sys
import logging

# --- Dynamic Path Adjustment for Module Imports ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# # --- Logging Configuration ---
# from utils.logging_config import setup_logging
# log_dir = os.path.join(project_root, 'logs')
# log_file_path = os.path.join(log_dir, 'app-log-2025-07-09.txt')
# os.makedirs(log_dir, exist_ok=True)
# setup_logging(log_file_path=log_file_path, log_level=logging.DEBUG, enable_console_logging=True)

from config import settings
from src.services.google_sheets.api_client import get_google_sheet_data, write_dataframe_to_sheet
from src.services.reporting_logic import (
    inventory_calculations,
    average_calculations,
    monthly_report_generator,
    report_data_loader
)
from src.services.data_processing import shipment_processor # Import the shipment_processor

#########logger = logging.getLogger(__name__)

# Renamed original main() to run_reporter_logic()
def run_reporter_logic():
    """Contains the core logic of the ShipStation Reporter."""
    #########logger.info("Starting ShipStation Reporter Script (core logic)...")

    # Load all configuration data
    (
        initial_inventory, # EOD_Prior_Week for Weekly Report
        rates,
        pallet_counts,
        key_skus_list,
        current_report_year,
        current_report_month,
        weekly_report_start_date,
        weekly_report_end_date,
        eom_previous_month_data # NEW: Unpack EOM data here for Monthly Report
    ) = report_data_loader.load_all_configuration_data(settings.GOOGLE_SHEET_ID)

    if initial_inventory is None or eom_previous_month_data is None: # Check both initial inventories
        #########logger.critical("Failed to load initial configuration data. Exiting script.")
        return

    # Load raw data for processing
    inventory_transactions_df = report_data_loader.load_inventory_transactions(settings.GOOGLE_SHEET_ID)
    shipped_items_df = report_data_loader.load_shipped_items_data(settings.GOOGLE_SHEET_ID)
    shipped_orders_df = report_data_loader.load_shipped_orders_data(settings.GOOGLE_SHEET_ID)
    weekly_shipped_history_df = report_data_loader.load_weekly_shipped_history(settings.GOOGLE_SHEET_ID)
    product_names_map = report_data_loader.load_product_names_map(settings.GOOGLE_SHEET_ID)

    # Convert SKUs in initial_inventory (for weekly) and eom_previous_month_data (for monthly) to string for consistency
    initial_inventory = {str(k): v for k, v in initial_inventory.items()}
    eom_previous_month_data = {str(k): v for k, v in eom_previous_month_data.items()}


    # --- Monthly Charge Report Generation ---
    #########logger.info("Generating Monthly Charge Report...")
    monthly_report_df, monthly_totals_df = monthly_report_generator.generate_monthly_charge_report(
        rates,
        pallet_counts,
        eom_previous_month_data, # IMPORTANT CHANGE: Pass eom_previous_month_data for monthly report initial inventory
        inventory_transactions_df,
        shipped_items_df,
        shipped_orders_df,
        current_report_year,
        current_report_month,
        key_skus_list
    )

    if monthly_report_df is not None and not monthly_report_df.empty:
        # Ensure monthly_totals_df is not None before attempting to rename
        if monthly_totals_df is not None and not monthly_totals_df.empty:
            final_monthly_df = pd.concat([monthly_report_df, monthly_totals_df.rename(index={0: 'TOTAL'})])
        else:
            final_monthly_df = monthly_report_df # If totals are empty, just use the main report
            #########logger.warning("Monthly totals DataFrame was empty or None. Only main monthly report data will be written.")

        write_dataframe_to_sheet(final_monthly_df, settings.GOOGLE_SHEET_ID, settings.MONTHLY_CHARGE_REPORT_OUTPUT_TAB_NAME)
        #########logger.info("Monthly Charge Report written successfully.")
    else:
        #########logger.error("Monthly Charge Report generation failed.")


    # --- Weekly Inventory Report Generation ---
    #########logger.info("Generating Weekly Inventory Report...")
    
    # Pass the weekly_report_start_date and weekly_report_end_date to calculate_current_inventory
    # Note: This still uses 'initial_inventory' (EOD_Prior_Week) for the weekly report's starting point
        current_inventory_df = inventory_calculations.calculate_current_inventory(
        initial_inventory, # This is EOD_Prior_Week from ORA_Configuration for weekly report
        inventory_transactions_df,
        shipped_items_df,
        key_skus_list,
        weekly_report_start_date,
        weekly_report_end_date
    )
    
    # Ensure weekly_shipped_history_df is not None before proceeding
    if weekly_shipped_history_df is not None:
        rolling_average_df = average_calculations.calculate_12_month_rolling_average(weekly_shipped_history_df)
    else:
        #########logger.warning("weekly_shipped_history_df was None. Skipping 12-Month Rolling Average calculation.")
        rolling_average_df = None # Set to None to prevent subsequent crashes

    
    if current_inventory_df is not None and not current_inventory_df.empty and product_names_map is not None:
        weekly_report_df = pd.merge(current_inventory_df, product_names_map, on='SKU', how='left')
        
        # Ensure '12-Month Rolling Average' column exists before accessing it
        if rolling_average_df is not None and not rolling_average_df.empty:
            weekly_report_df = pd.merge(weekly_report_df, rolling_average_df, on='SKU', how='left')
            weekly_report_df['12-Month Rolling Average'] = weekly_report_df['12-Month Rolling Average'].fillna('Insufficient Data')
        else:
            weekly_report_df['12-Month Rolling Average'] = 'Insufficient Data'

        weekly_report_df = weekly_report_df.rename(columns={'Quantity': 'Current Inventory'})
        
        write_dataframe_to_sheet(weekly_report_df[['SKU', 'Product', 'Current Inventory', '12-Month Rolling Average']], settings.GOOGLE_SHEET_ID, settings.WEEKLY_REPORT_OUTPUT_TAB_NAME)
        #########logger.info("Weekly Inventory Report written successfully.")
    else:
        #########logger.error("Weekly Inventory Report generation failed. Missing current inventory data or product names map.")

    #########logger.info("Script core logic finished successfully.") # Added this line for clarity


# This is the new entry point for the Cloud Function (HTTP trigger)
# def shipstation_reporter_http_trigger(request): # This function name should be your --entry-point
#     """
#     Cloud Function entry point for HTTP trigger.
#     Triggers the ShipStation Reporter logic.
#     """
#     logger.info("Cloud Function received HTTP trigger. Starting reporter logic.")
#     try:
#         run_reporter_logic() # Call your existing logic
#         logger.info("Cloud Function execution completed successfully.")
#         return 'ShipStation Reporter script executed successfully!', 200
#     except Exception as e:
#         logger.critical(f"Cloud Function execution failed: {e}", exc_info=True)
#         return f"ShipStation Reporter script failed: {e}", 500

def shipstation_reporter_http_trigger(request):
    """
    Cloud Function entry point for HTTP trigger.
    Returns a simple success message to pass health check.
    """
    # Ensure your logging setup is robust for Cloud Functions
    # If setup_logging is writing to a local file, it might cause issues.
    # It's better to let Cloud Functions handle logging to stdout/stderr for Cloud Logging.
    # Temporarily comment out your custom logging setup to rule it out.
    # from utils.logging_config import setup_logging
    # log_dir = os.path.join(project_root, 'logs')
    # log_file_path = os.path.join(log_dir, 'app-log-2025-07-09.txt')
    # os.makedirs(log_dir, exist_ok=True)
    # setup_logging(log_file_path=log_file_path, log_level=logging.DEBUG, enable_console_logging=True)
    # Also remove any lines that set up local file logging, like log_file_path = ...

    #########logger.info("Cloud Function received HTTP trigger. Testing basic response for health check.")
    return 'Hello World! Container is up and running.', 200


# Removed the 'if __name__ == "__main__": main()' block as it's not needed for Cloud Functions
# The Cloud Function environment will call shipstation_reporter_http_trigger directly.
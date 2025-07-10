import sys
import os

# Add the project root to the Python path to enable imports from utils and services
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
import base64
import json
import datetime
import time
import pandas as pd
import math
# Removed google.oauth2.service_account and googleapiclient.discovery/errors as they are now encapsulated
# within src.services.google_sheets.sheets_api

# Now these imports should work because 'utils' is in sys.path
from utils.api_utils import make_api_request
from utils.logging_config import setup_logging
import logging

# Import the new secret manager service
from src.services.gcp.secret_manager import access_secret_version
# Import the new ShipStation API client service
from src.services.shipstation.api_client import get_shipstation_headers, fetch_shipstation_shipments
# Import the new Google Sheets API client service
from src.services.google_sheets.sheets_api import get_google_sheet_data, write_google_sheet_data # Import these functions

# Import the data_validator module (ensure this path is correct relative to main script)
import debug.data_validator as data_validator

# Import the weekly_reporter module (this will be refactored later)
import weekly_reporter


# --- Configuration for ShipStation API ---
YOUR_GCP_PROJECT_ID = "ora-automation-project"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"

# --- ShipStation API Endpoints for Reporting Data ---
SHIPSTATION_SHIPMENTS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/shipments"
SHIPSTATION_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders"

# --- Service Account Key Path (Used for Secret Manager and Google Sheets Access) ---
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"

# --- Google Sheets API Configuration ---
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
ORA_PROCESSING_STATE_RANGE = 'ORA_Processing_State'
MONTHLY_CHARGE_REPORT_TAB_NAME = 'Monthly Charge Report'
WEEKLY_REPORT_TAB_NAME = 'Weekly Report'
ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME = 'ORA_Weekly_Shipped_History'
GOLDEN_TEST_DATA_RAW_TAB_NAME = 'Golden_Test_Data_Raw'
INVENTORY_TRANSACTIONS_TAB_NAME = 'Inventory_TRANSACTIONS' # Ensure this matches sheet name exactly
ORA_CONFIGURATION_TAB_NAME = 'ORA_Configuration'

SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Still needed if passed to sheets_api functions directly

# --- Bundle Product Configuration (Comprehensive, from SQL SPROC) ---
BUNDLE_CONFIG = {
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
    "18265": {"component_id": "17914", "multiplier": 40}, # PPR Buy 30 Get 10 Free
    "18275": {"component_id": "17914", "multiplier": 15}, # PPR Buy 12 Get 3 Free
    "18285": {"component_id": "17914", "multiplier": 6},  # PPR Buy 5 Get 1 Free
    "18195": {"component_id": "17914", "multiplier": 1},  # Autoship; OraCare PPR
    "18375": {"component_id": "17914", "multiplier": 1},  # Free; OraCare PPR
    "18455": {"component_id": "17914", "multiplier": 1},  # Autoship; FREE OraCare PPR
    "18495": {"component_id": "17914", "multiplier": 16}, # Webinar Special; PPR Buy 12 Get 4 Free
    "18485": {"component_id": "17914", "multiplier": 41}, # Webinar Special; PPR Buy 30 Get 11 Free
    "18295": {"component_id": "17904", "multiplier": 40}, # Travel Buy 30 Get 10 Free
    "18305": {"component_id": "17904", "multiplier": 15}, # Travel Buy 12 Get 3 Free
    "18425": {"component_id": "17904", "multiplier": 6},  # Travel Buy 5 Get 1 Free
    "18385": {"component_id": "17904", "multiplier": 1},  # Autoship; OraCare Travel
    "18395": {"component_id": "17904", "multiplier": 1},  # Free; OraCare Travel
    "18465": {"component_id": "17904", "multiplier": 1},  # Autoship; FREE OraCare Travel
    "18515": {"component_id": "17904", "multiplier": 16}, # Webinar Special; Travel Buy 12 Get 4
    "18315": {"component_id": "17975", "multiplier": 40}, # Reassure Buy 30 Get 10 Free
    "18325": {"component_id": "17975", "multiplier": 15}, # Reassure Buy 12 Get 3 Free
    "18335": {"component_id": "17975", "multiplier": 6},  # Reassure Buy 5 Get 1 Free
    "18405": {"component_id": "17975", "multiplier": 1},  # Autoship; OraCare Reassure
    "18415": {"component_id": "17975", "multiplier": 1},  # Free; OraCare Reassure
    "18525": {"component_id": "17975", "multiplier": 41}, # Webinar Special; Reassure Buy 30 Get 11 Free
    "18535": {"component_id": "17975", "multiplier": 16}, # Webinar Special; Reassure Buy 12 Get 4
    "18685": {"component_id": "18675", "multiplier": 40}, # Ortho Protect Buy 30 Get 10 Free
    "18695": {"component_id": "18675", "multiplier": 15}, # Ortho Protect Buy 12 Get 3 Free
    "18705": {"component_id": "18675", "multiplier": 6},  # Ortho Protect Buy 5 Get 1 Free
    "18715": {"component_id": "18675", "multiplier": 41}, # Webinar Special- Buy 30 Get 11 Free
    "18725": {"component_id": "18675", "multiplier": 16}, # Webinar Special- Buy 12 Get 4 Free
    "18735": {"component_id": "18675", "multiplier": 1},  # Autoship- Ortho Protect 1
    "18745": {"component_id": "18675", "multiplier": 1},  # Autoship- Free Ortho Protect 1
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
_log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
_log_file = os.path.join(_log_dir, 'app.log')
# Ensure logging is only configured once if this script is run as main.
if not logging.getLogger().handlers:
    setup_logging(log_file_path=_log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


def format_sku_with_lot(sku_id, sku_lot_map):
    """
    Formats a SKU by appending its active lot number if found in the SKU-Lot map.
    """
    if sku_id in sku_lot_map:
        lot_number = sku_lot_map[sku_id]
        formatted_sku = f"{sku_id} - {lot_number}"
        return formatted_sku
    return sku_id


# REMOVED access_secret_version function (now imported from src.services.gcp.secret_manager)
# REMOVED get_shipstation_headers function (now imported from src.services.shipstation.api_client)
# REMOVED fetch_shipstation_shipments function (now imported from src.services.shipstation.api_client)
# REMOVED get_google_sheet_data function (now imported from src.services.google_sheets.sheets_api)
# REMOVED write_google_sheet_data function (now imported from src.services.google_sheets.sheets_api)


def process_shipstation_shipments_to_daily_df(raw_shipments_data, bundle_config):
    """
    Processes raw ShipStation shipments data into a flattened Pandas DataFrame,
    applying bundling logic. SKU-Lot formatting will be applied at report finalization.
    This function is adapted to process data directly from Golden_Test_Data_Raw sheet,
    specifically for 'ShippedItem' transactions to get item quantities.
    Now uses the logging system instead of print().
    """
    processed_items = []
    
    for i, row_dict in enumerate(raw_shipments_data):
        current_order_number = row_dict.get('Order_Number')
        logger.debug(f"Row {i+2} (from sheet): Order_Number before processing: '{current_order_number}' (type: {type(current_order_number)})")

        if row_dict.get('Transaction_Type') != 'ShippedItem':
            continue

        ship_date_str = row_dict.get('Date')
        ship_date = pd.to_datetime(ship_date_str).date() if ship_date_str else None
        
        order_number = row_dict.get('Order_Number')
        order_number = str(order_number).strip() if order_number is not None else ''
        if order_number.upper() == 'NULL' or order_number == '':
            order_number = None
        
        logger.debug(f"Row {i+2} (ShippedItem): Order_Number after processing: '{order_number}' (type: {type(order_number)})")

        original_product_id = str(row_dict.get('SKU_With_Lot')) if row_dict.get('SKU_With_Lot') is not None else None
        original_quantity = row_dict.get('Quantity_Shipped')

        try:
            original_quantity = int(original_quantity) if original_quantity is not None else 0
        except ValueError:
            logger.warning(f"Non-numeric quantity '{row_dict.get('Quantity_Shipped')}' for SKU '{original_product_id}' in Order {order_number}. Defaulting to 0.")
            original_quantity = 0

        item_name = 'N/A' # Default name; will be replaced by actual product names eventually

        if original_product_id is None or original_product_id == '' or original_quantity == 0:
            logger.debug(f"Skipping shipment item with missing SKU ('{original_product_id}') or zero quantity ({original_quantity}) for Order: {order_number}")
            continue

        base_sku = original_product_id.split(' - ')[0] if ' - ' in original_product_id else original_product_id

        if base_sku in BUNDLE_CONFIG: # Using BUNDLE_CONFIG from global scope
            bundle_def = BUNDLE_CONFIG[base_sku]
            if isinstance(bundle_def, dict): # Single component bundle
                component_id = bundle_def.get('component_id')
                multiplier = bundle_def.get('multiplier', 1)
                expanded_quantity = original_quantity * multiplier
                processed_items.append({
                    'Date': ship_date,
                    'OrderNumber': order_number,
                    'BaseSKU': component_id,
                    'QuantityShipped': expanded_quantity,
                    'OriginalSKU': original_product_id,
                    'ItemName': item_name
                })
                logger.debug(f"Expanded bundle {original_product_id} to {expanded_quantity}x {component_id} for Order {order_number}.")
            elif isinstance(bundle_def, list): # Multi-component bundle
                for component_info in bundle_def:
                    component_sku = component_info.get('component_id')
                    multiplier = component_info.get('multiplier', 1)
                    expanded_quantity = original_quantity * multiplier
                    items_list.append({
                        "sku": component_sku,
                        "name": product_name,
                        "quantity": expanded_quantity,
                        "weight": {"value": weight_value, "units": "ounces"},
                        "dimensions": {"height": height, "length": length, "width": width}
                    })
                    logger.debug(f"Expanded multi-component bundle {original_product_id} to {expanded_quantity}x {component_sku} for Order {order_number}.")
        else:
            processed_items.append({
                "Date": ship_date,
                "OrderNumber": order_number,
                "BaseSKU": base_sku,
                "QuantityShipped": original_quantity,
                "OriginalSKU": original_product_id,
                "ItemName": item_name
            })
    
    # Create DataFrame
    shipments_df = pd.DataFrame(processed_items)
    
    # Ensure 'Date' is datetime and sort
    if 'Date' in shipments_df.columns:
        shipments_df['Date'] = pd.to_datetime(shipments_df['Date'])
        shipments_df = shipments_df.sort_values(by='Date').reset_index(drop=True)
    
    return shipments_df


# --- Daily Aggregations and Inventory Calculation Functions ---
def process_daily_aggregations(processed_shipments_df):
    """
    Aggregates processed shipment data to daily shipped quantities per SKU and daily unique order counts.
    Now uses the logging system instead of print().
    """
    daily_shipped_sku_qty = processed_shipments_df.groupby(['Date', 'BaseSKU'])['QuantityShipped'].sum().reset_index()
    daily_shipped_sku_qty.rename(columns={'QuantityShipped': 'TotalQtyShipped', 'BaseSKU': 'SKU'}, inplace=True)
    
    return daily_shipped_sku_qty, pd.DataFrame(columns=['Date', 'CountOfOrders'])

def calculate_daily_inventory(initial_inventory_map, all_skus, all_dates, daily_movements_df):
    """
    Calculates daily Beginning of Day (BOD) and End of Day (EOD) inventory quantities
    for each SKU using a recursive-like approach in Pandas.
    Now uses the logging system instead of print().
    """
    idx = pd.MultiIndex.from_product([pd.to_datetime(all_dates).normalize(), all_skus], names=['Date', 'SKU'])
    daily_inventory_df = pd.DataFrame(index=idx).reset_index()

    daily_movements_df['Date'] = pd.to_datetime(daily_movements_df['Date']).dt.normalize()
    daily_movements_df['SKU'] = daily_movements_df['SKU'].astype(str)

    daily_inventory_df = pd.merge(
        daily_inventory_df,
        daily_movements_df,
        on=['Date', 'SKU'],
        how='left'
    ).fillna({
        'ShippedQty': 0,
        'ReceivedQty': 0,
        'RepackedQty': 0
    })
    
    daily_inventory_df['BOD_Qty'] = 0
    daily_inventory_df['EOD_Qty'] = 0

    daily_inventory_df = daily_inventory_df.sort_values(by=['SKU', 'Date']).reset_index(drop=True)

    for sku in all_skus:
        sku_data = daily_inventory_df[daily_inventory_df['SKU'] == sku].copy()
        
        initial_eod_for_sku = initial_inventory_map.get(sku, 0)

        if not sku_data.empty:
            sku_data.loc[sku_data.index[0], 'BOD_Qty'] = initial_eod_for_sku
            
            sku_data.loc[sku_data.index[0], 'EOD_Qty'] = (
                sku_data.loc[sku_data.index[0], 'BOD_Qty']
                - sku_data.loc[sku_data.index[0], 'ShippedQty']
                + sku_data.loc[sku_data.index[0], 'ReceivedQty']
                + sku_data.loc[sku_data.index[0], 'RepackedQty']
            )

            for i in range(1, len(sku_data)):
                sku_data.loc[sku_data.index[i], 'BOD_Qty'] = sku_data.loc[sku_data.index[i-1], 'EOD_Qty']
                
                sku_data.loc[sku_data.index[i], 'EOD_Qty'] = (
                    sku_data.loc[sku_data.index[i], 'BOD_Qty']
                    - sku_data.loc[sku_data.index[i], 'ShippedQty']
                    + sku_data.loc[sku_data.index[i], 'ReceivedQty']
                    + sku_data.loc[sku_data.index[i], 'RepackedQty']
                )
        
        daily_inventory_df.loc[daily_inventory_df['SKU'] == sku, ['BOD_Qty', 'EOD_Qty']] = sku_data[['BOD_Qty', 'EOD_Qty']].values

    return daily_inventory_df

def calculate_current_inventory(daily_inventory_df, key_skus):
    """
    Extracts the most recent End of Day (EOD) quantity for each key SKU
    from the daily inventory DataFrame.
    Now uses the logging system instead of print().
    """
    current_inventory_data = []
    daily_inventory_df['Date'] = pd.to_datetime(daily_inventory_df['Date'])
    daily_inventory_df_sorted = daily_inventory_df.sort_values(by='Date', ascending=False)

    for sku in key_skus:
        sku_data = daily_inventory_df_sorted[daily_inventory_df_sorted['SKU'] == sku].copy()
        latest_eod = sku_data['EOD_Qty'].iloc[0] if not sku_data.empty else 0
        current_inventory_data.append({
            'SKU': sku,
            'Current Quantity': latest_eod
        })
    
    return pd.DataFrame(current_inventory_data)


def calculate_12_month_rolling_average(weekly_shipped_history_df, key_skus):
    """
    Calculates the 12-month (52-week) rolling average of shipped quantities for each key SKU.
    Handles cases with insufficient historical data.
    Now uses the logging system instead of print().
    """
    logger.info("Calculating 12-Month Rolling Average...")
    rolling_average_data = []
    
    expected_cols = ['WeekEndDate', 'SKU', 'ShippedQuantity']
    for col in expected_cols:
        if col not in weekly_shipped_history_df.columns:
            logger.error(f"Missing expected column '{col}' in weekly_shipped_history_df. Available columns: {weekly_shipped_history_df.columns.tolist()}")
            return pd.DataFrame(columns=['SKU', '12-Month Rolling Average'])

    weekly_shipped_history_df['WeekEndDate'] = pd.to_datetime(weekly_shipped_history_df['WeekEndDate'])
    weekly_shipped_history_df_sorted = weekly_shipped_history_df.sort_values(by='WeekEndDate', ascending=False)

    for sku in key_skus:
        sku_history = weekly_shipped_history_df_sorted[weekly_shipped_history_df_sorted['SKU'] == sku].copy()
        
        if len(sku_history) < 52:
            rolling_average = "Insufficient Data"
        else:
            last_52_weeks = sku_history.head(52)
            total_shipped_last_52_weeks = last_52_weeks['ShippedQuantity'].sum()
            rolling_average = round(total_shipped_last_52_weeks / 52, 2) 

        rolling_average_data.append({
            'SKU': sku,
            '12-Month Rolling Average': rolling_average
        })
    
    return pd.DataFrame(rolling_average_data)


def get_key_skus(spreadsheet_id, config_sheet_name, service_account_file_path):
    """
    Reads the 'ORA_Configuration' Google Sheet to extract the list of "Key Products (SKUs)".
    Assumes the structure: 'ParameterCategory', 'ParameterName', 'SKU', 'Value', etc.
    It looks for 'ParameterCategory' == 'Key Products' and returns SKUs.
    Now uses the logging system instead of print().
    """
    logger.info(f"Attempting to read Key SKUs from '{config_sheet_name}' sheet...")
    raw_config_data = get_google_sheet_data( # Using imported function
        spreadsheet_id,
        f'{config_sheet_name}!A:F', 
        service_account_file_path
    )

    key_skus = []
    if raw_config_data and len(raw_config_data) > 1:
        headers = [h.strip() for h in raw_config_data[0]]
        data_rows = raw_config_data[1:]

        try:
            param_cat_idx = headers.index('ParameterCategory')
            sku_idx = headers.index('SKU')
            product_name_idx = headers.index('ParameterName') # Assuming 'ParameterName' holds product names

            for row in data_rows:
                if len(row) > max(param_cat_idx, sku_idx, product_name_idx):
                    category = row[param_cat_idx].strip()
                    sku = row[sku_idx].strip()
                    product_name = row[product_name_idx].strip()

                    if category == 'Key Products' and sku:
                        key_skus.append((sku, product_name)) # Store as tuple (SKU, Name)
        except ValueError as e:
            logger.error(f"Missing expected column in ORA_Configuration sheet (e.g., 'ParameterCategory', 'SKU', or 'ParameterName'): {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing ORA_Configuration: {e}", exc_info=True)
    else:
        logger.warning("No data or malformed data found in ORA_Configuration sheet.")
    
    # Return unique SKUs and a map of SKU to product name
    unique_key_skus = sorted(list(set([sku for sku, name in key_skus])))
    product_names_map = {sku: name for sku, name in key_skus} # Build the map
    
    logger.info(f"Successfully extracted {len(unique_key_skus)} key SKUs and their names.")
    return unique_key_skus, product_names_map


def get_weekly_shipped_history(spreadsheet_id, sheet_name, service_account_file_path, key_skus_for_report):
    """
    Reads historical weekly aggregated SKU shipment quantities from the specified Google Sheet tab.
    It handles the "Ship Week" date range format and unpivots the data.
    Now uses the logging system instead of print().
    """
    logger.info(f"Attempting to read historical weekly shipped data from '{sheet_name}' sheet...")
    range_name = f'{sheet_name}!A:E' 
    raw_history_data = get_google_sheet_data( # Using imported function
        spreadsheet_id,
        range_name,
        service_account_file_path
    )

    weekly_shipped_df = pd.DataFrame()
    if raw_history_data and len(raw_history_data) > 0: 
        headers = [h.strip() for h in raw_history_data[0]]
        data_rows = raw_history_data[1:]

        if not headers or not data_rows:
            logger.warning(f"No valid headers or data rows found in '{sheet_name}'. Returning empty DataFrame.")
            return pd.DataFrame(columns=['WeekEndDate', 'SKU', 'ShippedQuantity'])

        df_temp = pd.DataFrame(data_rows, columns=headers)

        id_vars = ['Ship Week']
        
        value_vars = [str(col).strip() for col in headers if str(col).strip() in key_skus_for_report]
        
        if not value_vars:
            logger.error(f"No matching SKU columns found in '{sheet_name}' based on key_skus_for_report: {key_skus_for_report}. Available headers: {headers}. Returning empty DataFrame.")
            return pd.DataFrame(columns=['WeekEndDate', 'SKU', 'ShippedQuantity'])

        weekly_shipped_df = pd.melt(
            df_temp,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name='SKU',        
            value_name='ShippedQuantity' 
        )

        weekly_shipped_df.rename(columns={'Ship Week': 'WeekEndDate'}, inplace=True)

        if 'WeekEndDate' in weekly_shipped_df.columns: 
            try:
                weekly_shipped_df['WeekEndDate'] = weekly_shipped_df['WeekEndDate'].apply(
                    lambda x: pd.to_datetime(str(x).split(' - ')[1].strip()) if ' - ' in str(x) else pd.to_datetime(x)
                )
            except Exception as e:
                logger.warning(f"Could not convert 'WeekEndDate' column (date range) to datetime in '{sheet_name}'. Details: {e}", exc_info=True)
                weekly_shipped_df['WeekEndDate'] = pd.NaT 

        if 'SKU' in weekly_shipped_df.columns:
            weekly_shipped_df['SKU'] = weekly_shipped_df['SKU'].astype(str)
        if 'ShippedQuantity' in weekly_shipped_df.columns:
            try:
                weekly_shipped_df['ShippedQuantity'] = pd.to_numeric(weekly_shipped_df['ShippedQuantity'], errors='coerce').fillna(0)
            except Exception as e:
                logger.warning(f"Could not convert 'ShippedQuantity' column to numeric in '{sheet_name}' after melt. Details: {e}", exc_info=True)
                weekly_shipped_df['ShippedQuantity'] = 0 

    else:
        logger.warning(f"No data retrieved from '{sheet_name}' sheet or sheet is empty/malformed.")
    logger.debug(f"Columns of weekly_shipped_df after melt and rename: {weekly_shipped_df.columns.tolist()}")
    return weekly_shipped_df


def generate_monthly_charge_report(
    shipstation_api_key, shipstation_api_secret, service_account_credentials_path, 
    google_sheet_id, monthly_charge_report_tab_name, initial_inventory_map, 
    pallet_counts, rates, raw_golden_test_data_raw, inventory_transactions_raw):
    """
    Orchestrates the generation and writing of the Monthly Charge Report.
    Returns the DailyInventory_DF and DailyShippedSKUQty_DF for use in other reports.
    This version correctly separates processing for ShippedItem (quantities)
    and ShippedOrder (order counts) from Golden_Test_Data_Raw.
    Now uses the logging system instead of print().
    """
    logger.info("Generating Monthly Charge Report...")
    
    if not raw_golden_test_data_raw or len(raw_golden_test_data_raw) < 2:
        logger.warning("No data or malformed data provided for Golden Test Data Raw. Returning empty DataFrames for Monthly Report.")
        return pd.DataFrame(), pd.DataFrame()

    headers_golden_raw = [h.strip() for h in raw_golden_test_data_raw[0]]
    data_rows_golden_raw = raw_golden_test_data_raw[1:]

    shipped_item_data_dicts = []
    for row in data_rows_golden_raw:
        row_dict = dict(zip(headers_golden_raw, row))
        if row_dict.get('Transaction_Type') == 'ShippedItem':
            shipped_item_data_dicts.append(row_dict)
    
    processed_shipped_items_df = process_shipstation_shipments_to_daily_df(
        shipped_item_data_dicts, # Pass only ShippedItem data
        BUNDLE_CONFIG 
    )
    logger.info(f"Processed Shipped Items (from ShippedItem) DataFrame. Shape: {processed_shipped_items_df.shape}")
    logger.debug(f"Head:\n{processed_shipped_items_df.head()}")

    shipped_order_data_dicts = []
    for row in data_rows_golden_raw:
        row_dict = dict(zip(headers_golden_raw, row))
        if row_dict.get('Transaction_Type') == 'ShippedOrder':
            shipped_order_data_dicts.append(row_dict)

    order_count_source_df = pd.DataFrame(shipped_order_data_dicts)

    if not order_count_source_df.empty:
        order_count_source_df['Date'] = pd.to_datetime(order_count_source_df['Date'])
        order_count_source_df['OrderNumber'] = order_count_source_df['Order_Number'].apply( # Corrected to use 'Order_Number' column from raw data
            lambda x: str(x).strip() if x is not None else ''
        ).apply(
            lambda x: None if x.upper() == 'NULL' or x == '' else x
        )
    else:
        order_count_source_df = pd.DataFrame(columns=['Date', 'OrderNumber']) # Changed to 'OrderNumber' for consistency

    logger.info(f"Raw ShippedOrder Data for Order Counting. Shape: {order_count_source_df.shape}")
    logger.debug(f"Head:\n{order_count_source_df.head()}")
    
    all_dates_list = []
    if not processed_shipped_items_df.empty:
        all_dates_list.extend(processed_shipped_items_df['Date'].tolist())
    if not order_count_source_df.empty: # Use order_count_source_df here
        all_dates_list.extend(order_count_source_df['Date'].tolist())

    if all_dates_list:
        report_start_date = pd.to_datetime(all_dates_list).min().date()
        report_end_date = pd.to_datetime(all_dates_list).max().date()
    else:
        report_start_date = datetime.date.today()
        report_end_date = datetime.date.today()

    all_dates = pd.to_datetime(pd.date_range(start=report_start_date, end=report_end_date, freq='D').normalize()) 
    all_skus = list(pallet_counts.keys()) 

    DailyShippedSKUQty_DF = processed_shipped_items_df.groupby(['Date', 'BaseSKU'])['QuantityShipped'].sum().reset_index()
    DailyShippedSKUQty_DF.rename(columns={'QuantityShipped': 'TotalQtyShipped', 'BaseSKU': 'SKU'}, inplace=True) 
    DailyShippedSKUQty_DF['Date'] = pd.to_datetime(DailyShippedSKUQty_DF['Date']).dt.normalize()
    
    # Generate DailyOrderCount_DF from order_count_source_df
    DailyOrderCount_DF = order_count_source_df[order_count_source_df['OrderNumber'].notna()].groupby('Date')['OrderNumber'].nunique().reset_index()
    DailyOrderCount_DF.rename(columns={'OrderNumber': 'CountOfOrders'}, inplace=True) # Ensure consistent column name
    DailyOrderCount_DF['Date'] = pd.to_datetime(DailyOrderCount_DF['Date']).dt.normalize()

    logger.info(f"Daily Aggregated Shipments (from ShippedItem). Shape: {DailyShippedSKUQty_DF.shape}")
    logger.debug(f"Head:\n{DailyShippedSKUQty_DF.head()}")

    logger.info(f"Daily Order Count (from ShippedOrder). Shape: {DailyOrderCount_DF.shape}")
    logger.debug(f"Head:\n{DailyOrderCount_DF.head()}")

    inventory_transactions_df = pd.DataFrame() 
    if inventory_transactions_raw and len(inventory_transactions_raw) > 1:
        headers = [h.strip() for h in inventory_transactions_raw[0]]
        data_rows = inventory_transactions_raw[1:]
        if headers: 
            inventory_transactions_df = pd.DataFrame(data_rows, columns=headers)
            if 'Date' in inventory_transactions_df.columns:
                try:
                    inventory_transactions_df['Date'] = pd.to_datetime(inventory_transactions_df['Date'])
                except Exception as e:
                    logger.warning(f"Could not convert 'Date' column to datetime in Inventory_Transactions. Details: {e}", exc_info=True)
            if 'Quantity' in inventory_transactions_df.columns:
                try:
                    inventory_transactions_df['Quantity'] = pd.to_numeric(inventory_transactions_df['Quantity'])
                except Exception as e:
                    logger.warning(f"Could not convert 'Quantity' column to numeric in Inventory_Transactions. Details: {e}", exc_info=True)
        else:
            logger.error("Inventory_Transactions sheet has no headers.")
    else:
        logger.warning("No data retrieved from Inventory_Transactions sheet or sheet is empty/malformed.")
    logger.info(f"Inventory Transactions Loaded. Shape: {inventory_transactions_df.shape if not inventory_transactions_df.empty else 'empty'}")
    logger.debug(f"Head:\n{inventory_transactions_df.head()}" if not inventory_transactions_df.empty else "Inventory Transactions DataFrame is empty.")


    if 'Date' in inventory_transactions_df.columns:
        inventory_transactions_df['Date'] = pd.to_datetime(inventory_transactions_df['Date']).dt.normalize()
    
    DailyShippedSKUQty_DF['Date'] = pd.to_datetime(DailyShippedSKUQty_DF['Date']).dt.normalize()
    DailyShippedSKUQty_DF['SKU'] = DailyShippedSKUQty_DF['SKU'].astype(str) 

    received_df = inventory_transactions_df[inventory_transactions_df['TransactionType'] == 'Receive'].groupby(['Date', 'SKU'])['Quantity'].sum().reset_index()
    received_df.rename(columns={'Quantity': 'ReceivedQty'}, inplace=True)
    received_df['SKU'] = received_df['SKU'].astype(str) 

    repacked_df = inventory_transactions_df[inventory_transactions_df['TransactionType'] == 'Repack'].groupby(['Date', 'SKU'])['Quantity'].sum().reset_index()
    repacked_df.rename(columns={'Quantity': 'RepackedQty'}, inplace=True)
    repacked_df['SKU'] = repacked_df['SKU'].astype(str) 

    all_date_sku_combinations = pd.MultiIndex.from_product([all_dates, all_skus], names=['Date', 'SKU']).to_frame(index=False)
    all_date_sku_combinations['SKU'] = all_date_sku_combinations['SKU'].astype(str) 

    AllDailySKUMovements_DF = pd.merge(
        all_date_sku_combinations,
        DailyShippedSKUQty_DF, 
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'TotalQtyShipped': 0}) 
    AllDailySKUMovements_DF.rename(columns={'TotalQtyShipped': 'ShippedQty'}, inplace=True) 

    AllDailySKUMovements_DF = pd.merge(
        AllDailySKUMovements_DF,
        received_df,
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'ReceivedQty': 0})

    AllDailySKUMovements_DF = pd.merge(
        AllDailySKUMovements_DF,
        repacked_df,
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'RepackedQty': 0})

    AllDailySKUMovements_DF['ShippedQty'] = AllDailySKUMovements_DF['ShippedQty'].astype(int)
    AllDailySKUMovements_DF['ReceivedQty'] = AllDailySKUMovements_DF['ReceivedQty'].astype(int)
    AllDailySKUMovements_DF['RepackedQty'] = AllDailySKUMovements_DF['RepackedQty'].astype(int)

    logger.info(f"All Daily SKU Movements. Shape: {AllDailySKUMovements_DF.shape}")
    logger.debug(f"Head:\n{AllDailySKUMovements_DF.head()}")

    initial_inventory_for_calc = {
        sku: initial_inventory_map.get(sku, 0) # Use .get() with default to prevent KeyError for missing SKUs
        for sku in all_skus
    }

    DailyInventory_DF = calculate_daily_inventory(
        initial_inventory_for_calc, 
        all_skus, 
        all_dates, 
        AllDailySKUMovements_DF[['Date', 'SKU', 'ShippedQty', 'ReceivedQty', 'RepackedQty']] 
    )

    logger.info(f"Daily Inventory (BOD/EOD). Shape: {DailyInventory_DF.shape}")
    logger.debug(f"Head:\n{DailyInventory_DF.head()}")

    MonthlyChargeReport_DF = pd.merge(
        DailyInventory_DF,
        DailyShippedSKUQty_DF, 
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'TotalQtyShipped': 0}) 

    MonthlyChargeReport_DF = pd.merge(
        MonthlyChargeReport_DF,
        DailyOrderCount_DF, # Use the correctly generated DailyOrderCount_DF
        on='Date',
        how='left'
    ).fillna({'CountOfOrders': 0}) 

    space_rental_rate = rates.get('SpaceRentalRate', 0.0)
    MonthlyChargeReport_DF['PalletsUsed'] = MonthlyChargeReport_DF.apply(
        lambda row: math.ceil(row['EOD_Qty'] / pallet_counts.get(row['SKU'], 1)) if pallet_counts.get(row['SKU'], 1) > 0 else 0,
        axis=1
    )
    MonthlyChargeReport_DF['Space_Rental_Charge_Per_SKU'] = MonthlyChargeReport_DF['PalletsUsed'] * space_rental_rate

    DailySpaceRentalCharge = MonthlyChargeReport_DF.groupby('Date')['Space_Rental_Charge_Per_SKU'].sum().reset_index()
    DailySpaceRentalCharge.rename(columns={'Space_Rental_Charge_Per_SKU': 'Space_Rental_Charge'}, inplace=True)

    FinalDailyReport_DF = pd.merge(
        DailyOrderCount_DF, # Start with DailyOrderCount_DF for final report base
        DailySpaceRentalCharge,
        on='Date',
        how='left'
    ).fillna({'Space_Rental_Charge': 0})

    DailyPackagesShipped = DailyShippedSKUQty_DF.groupby('Date')['TotalQtyShipped'].sum().reset_index()
    DailyPackagesShipped.rename(columns={'TotalQtyShipped': 'TotalPackagesShipped'}, inplace=True)

    FinalDailyReport_DF = pd.merge(
        FinalDailyReport_DF,
        DailyPackagesShipped,
        on='Date',
        how='left'
    ).fillna({'TotalPackagesShipped': 0})

    order_charge_rate = rates.get('OrderCharge', 0.0)
    package_charge_rate = rates.get('PackageCharge', 0.0)

    FinalDailyReport_DF['Orders_Charge'] = FinalDailyReport_DF['CountOfOrders'] * order_charge_rate
    FinalDailyReport_DF['Packages_Charge'] = FinalDailyReport_DF['TotalPackagesShipped'] * package_charge_rate
    FinalDailyReport_DF['Total_Charge'] = (
        FinalDailyReport_DF['Orders_Charge'] + 
        FinalDailyReport_DF['Packages_Charge'] + 
        FinalDailyReport_DF['Space_Rental_Charge']
    )

    financial_columns = ['Orders_Charge', 'Packages_Charge', 'Space_Rental_Charge', 'Total_Charge']
    for col in financial_columns:
        if col in FinalDailyReport_DF.columns:
            FinalDailyReport_DF[col] = FinalDailyReport_DF[col].round(2)

    output_columns = [
        'Date', '# Of Orders', '17612_Shipped', '17904_Shipped', '17914_Shipped', '18675_Shipped',
        'Orders_Charge', 'Packages_Charge', 'Space_Rental_Charge', 'Total_Charge'
    ]

    pivot_shipped_qty = DailyShippedSKUQty_DF.pivot_table(
        index='Date', 
        columns='SKU',
        values='TotalQtyShipped', 
        fill_value=0
    ).reset_index()

    column_rename_map = {f'{sku}': f'{sku}_Shipped' for sku in pallet_counts.keys()} 
    pivot_shipped_qty.rename(columns=column_rename_map, inplace=True)

    MonthlyChargeReport_DF_Final = pd.merge(
        FinalDailyReport_DF,
        pivot_shipped_qty,
        on='Date',
        how='left'
    ).fillna(0) 

    MonthlyChargeReport_DF_Final.rename(columns={'CountOfOrders': '# Of Orders'}, inplace=True)

    for sku_key in pallet_counts.keys():
        col_name = f'{sku_key}_Shipped'
        if col_name not in MonthlyChargeReport_DF_Final.columns:
            MonthlyChargeReport_DF_Final[col_name] = 0
    
    MonthlyChargeReport_DF_Final = MonthlyChargeReport_DF_Final[output_columns]
    
    logger.info(f"Monthly Charge Report (Daily). Shape: {MonthlyChargeReport_DF_Final.shape}")
    logger.debug(f"Head:\n{MonthlyChargeReport_DF_Final.head()}")

    MonthlyTotals_DF = pd.DataFrame([{
        'Date': 'Monthly Totals',
        '# Of Orders': MonthlyChargeReport_DF_Final['# Of Orders'].sum(),
        '17612_Shipped': MonthlyChargeReport_DF_Final['17612_Shipped'].sum() if '17612_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        '17904_Shipped': MonthlyChargeReport_DF_Final['17904_Shipped'].sum() if '17904_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        '17914_Shipped': MonthlyChargeReport_DF_Final['17914_Shipped'].sum() if '17914_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        '18675_Shipped': MonthlyChargeReport_DF_Final['18675_Shipped'].sum() if '18675_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        'Orders_Charge': MonthlyChargeReport_DF_Final['Orders_Charge'].sum().round(2), # Round total
        'Packages_Charge': MonthlyChargeReport_DF_Final['Packages_Charge'].sum().round(2), # Round total
        'Space_Rental_Charge': MonthlyChargeReport_DF_Final['Space_Rental_Charge'].sum().round(2), # Round total
        'Total_Charge': MonthlyChargeReport_DF_Final['Total_Charge'].sum().round(2) # Round total
    }])

    logger.info(f"Monthly Totals. Head:\n{MonthlyTotals_DF.head()}")


    logger.info("Attempting to write Monthly Charge Report to Google Sheets...")
    write_google_sheet_data( # Using imported function
        google_sheet_id,
        monthly_charge_report_tab_name + "!A1", 
        service_account_credentials_path, 
        MonthlyChargeReport_DF_Final 
    )
    start_row_for_totals = len(MonthlyChargeReport_DF_Final) + 3 
    write_google_sheet_data( # Using imported function
        google_sheet_id,
        monthly_charge_report_tab_name + f"!A{start_row_for_totals}", 
        service_account_credentials_path, 
        MonthlyTotals_DF 
    )
    logger.info("Monthly Charge Report writing process complete.")

    return DailyInventory_DF, DailyShippedSKUQty_DF 

def generate_weekly_inventory_report(
    google_sheet_id, weekly_report_tab_name, service_account_file_path, 
    daily_inventory_df, weekly_shipped_history_df, key_skus_for_report, product_names_map): # Added product_names_map
    """
    Orchestrates the generation and writing of the Weekly Inventory Report.
    Combines current inventory and 12-month rolling average.
    Now uses the logging system instead of print().
    """
    logger.info("Generating Weekly Inventory Report...")

    # Step 4: Calculate Current Inventory
    current_inventory_df = calculate_current_inventory(daily_inventory_df, key_skus_for_report)
    logger.info(f"Calculated Current Inventory for Weekly Report. Shape: {current_inventory_df.shape}")
    logger.debug(f"Head:\n{current_inventory_df.head()}")

    # Step 5: Calculate 12-Month Rolling Average
    rolling_average_df = calculate_12_month_rolling_average(weekly_shipped_history_df, key_skus_for_report)
    logger.info(f"Calculated 12-Month Rolling Average for Weekly Report. Shape: {rolling_average_df.shape}")
    logger.debug(f"Head:\n{rolling_average_df.head()}")

    # Merge current inventory and rolling average DataFrames
    weekly_report_df = pd.merge(
        current_inventory_df,
        rolling_average_df,
        on='SKU',
        how='outer'
    )
    
    # Add Product Name column using product_names_map
    weekly_report_df['Product Name'] = weekly_report_df['SKU'].map(product_names_map)
    
    weekly_report_df['Current Quantity'] = weekly_report_df['Current Quantity'].fillna(0).astype(int)
    weekly_report_df['12-Month Rolling Average'] = weekly_report_df['12-Month Rolling Average'].fillna('N/A')

    # Reorder columns to include Product Name
    final_columns = ['SKU', 'Product Name', 'Current Quantity', '12-Month Rolling Average']
    weekly_report_df = weekly_report_df[final_columns]

    logger.info(f"Final Weekly Inventory Report. Shape: {weekly_report_df.shape}")
    logger.debug(f"Head:\n{weekly_report_df.head()}")

    return weekly_report_df


# --- Main execution block ---
if __name__ == "__main__":
    import sys 

    logger.info("Starting ShipStation Reporter Script...")
    # --- HARDCODED CREDENTIALS FOR DEBUGGING ONLY ---
    # In a production environment, these would be retrieved securely (e.g., from Secret Manager)
    # The actual retrieval will now use the imported access_secret_version
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
    # The Google Sheets service account key also needs to be loaded securely.
    # For this testing phase, we'll keep the direct file path for Google Sheets for now,
    # but acknowledge it should ideally come from Secret Manager too.
    google_sheets_service_account_json_content = "DUMMY_GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON" # Placeholder - actual content from Secret Manager

    if not shipstation_api_key or not shipstation_api_secret:
        logger.critical("Failed to retrieve ShipStation API credentials. Aborting script.")
        sys.exit(1)

    logger.info(f"ShipStation API Key retrieved (truncated): {shipstation_api_key[:5]}...")
    logger.info(f"ShipStation API Secret retrieved (truncated): {shipstation_api_secret[:5]}...")
    logger.debug(f"Google Sheets Service Account Key retrieved (truncated): {google_sheets_service_account_json_content[:50]}...") 

    # Ensure the dummy service account key file exists for Google Sheets access during testing
    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        logger.warning(f"Dummy service account key path '{SERVICE_ACCOUNT_KEY_PATH}' does not exist. Creating it for testing.")
        os.makedirs(os.path.dirname(SERVICE_ACCOUNT_KEY_PATH), exist_ok=True)
        # Create a minimal dummy JSON structure for google.oauth2.service_account.Credentials.from_service_account_file
        dummy_content = json.dumps({
            "type": "service_account",
            "project_id": YOUR_GCP_PROJECT_ID,
            "private_key_id": "dummy_private_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nDUmMyKeY\\n-----END PRIVATE KEY-----\\n", 
            "client_email": "dummy-service-account@ora-automation-project.iam.gserviceaccount.com", 
            "client_id": "dummy_client_id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy-service-account%40ora-automation-project.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        })
        with open(SERVICE_ACCOUNT_KEY_PATH, 'w') as f:
            f.write(dummy_content)


    # --- Pre-validation of all Google Sheets data using data_validator ---
    logger.info("Running Data Validation Before Processing ---")
    
    # Updated call to get_key_skus to receive both key_skus and product_names_map
    key_skus_for_report, product_names_map = get_key_skus(GOOGLE_SHEET_ID, ORA_CONFIGURATION_TAB_NAME, SERVICE_ACCOUNT_KEY_PATH)
    config_raw_data = get_google_sheet_data(GOOGLE_SHEET_ID, f'{ORA_CONFIGURATION_TAB_NAME}!A:F', SERVICE_ACCOUNT_KEY_PATH)
    config_success, config_msg = data_validator.validate_ora_configuration(config_raw_data)
    logger.info(f"ORA Configuration Validation: {config_msg}")
    if not config_success:
        logger.critical("ORA Configuration validation failed. Aborting script execution.")
        sys.exit(1) 

    if not key_skus_for_report:
        logger.critical("No Key SKUs extracted from ORA_Configuration. Aborting script.")
        sys.exit(1)
    
    weekly_history_raw_data = get_google_sheet_data(GOOGLE_SHEET_ID, f'{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}!A:E', SERVICE_ACCOUNT_KEY_PATH)
    weekly_history_success, weekly_history_msg = data_validator.validate_weekly_shipped_history(weekly_history_raw_data, key_skus_for_report)
    logger.info(f"Weekly Shipped History Validation: {weekly_history_msg}")
    if not weekly_history_success:
        logger.critical("Weekly Shipped History validation failed. Aborting script execution.")
        sys.exit(1)

    golden_raw_raw_data = get_google_sheet_data(GOOGLE_SHEET_ID, f'{GOLDEN_TEST_DATA_RAW_TAB_NAME}!A:H', SERVICE_ACCOUNT_KEY_PATH)
    golden_raw_success, golden_raw_msg = data_validator.validate_golden_test_data_raw(golden_raw_raw_data)
    logger.info(f"Golden Test Data Raw Validation: {golden_raw_msg}")
    if not golden_raw_success:
        logger.critical("Golden Test Data Raw validation failed. Aborting script execution.")
        sys.exit(1)

    inventory_trans_raw_data = get_google_sheet_data(GOOGLE_SHEET_ID, f'{INVENTORY_TRANSACTIONS_TAB_NAME}!A:D', SERVICE_ACCOUNT_KEY_PATH)
    inventory_trans_success, inventory_trans_msg = data_validator.validate_inventory_transactions(inventory_trans_raw_data)
    logger.info(f"Inventory Transactions Validation: {inventory_trans_msg}")
    if not inventory_trans_success:
        logger.critical("Inventory Transactions validation failed. Aborting script execution.")
        sys.exit(1)

    logger.info("All Data Sources Validated Successfully. Proceeding with Report Generation.")


    # --- Load Data after Validation (using validated raw data) ---
    RATES = {}
    PALLET_COUNTS = {}
    INITIAL_INVENTORY = {} 
    if config_raw_data and len(config_raw_data) > 1:
        headers = [h.strip() for h in config_raw_data[0]]
        data_rows = config_raw_data[1:]

        try:
            param_cat_idx = headers.index('ParameterCategory')
            param_name_idx = headers.index('ParameterName')
            sku_idx = headers.index('SKU')
            value_idx = headers.index('Value')
            
            for row in data_rows:
                if len(row) > max(param_cat_idx, param_name_idx, value_idx, sku_idx):
                    category = row[param_cat_idx].strip()
                    name = row[param_name_idx].strip()
                    value = row[value_idx].strip() 
                    sku = row[sku_idx].strip() if sku_idx != -1 else None

                    if category == 'Rates':
                        try: RATES[name] = float(value)
                        except ValueError: logger.warning(f"Could not convert rate '{value}' for {name} to float.") 
                    elif category == 'PalletConfig':
                        if sku:
                            try: PALLET_COUNTS[sku] = int(value)
                            except ValueError: logger.warning(f"Could not convert pallet count '{value}' for {sku} to int.") 
                    elif category == 'InitialInventory':
                        if sku:
                            try: INITIAL_INVENTORY[sku] = int(value)
                            except ValueError: logger.warning(f"Could not convert initial inventory '{value}' for {sku} to int.") 
        except Exception as e:
            logger.error(f"Data extraction from ORA_Configuration failed after validation: {e}", exc_info=True)
            sys.exit(1)
    
    logger.info(f"Rates: {RATES}")
    logger.info(f"Pallet Counts: {PALLET_COUNTS}")
    logger.info(f"Initial Inventory (EOD_Prior_Week): {INITIAL_INVENTORY}")
    logger.info(f"Key SKUs for Weekly Report (extracted from config): {key_skus_for_report}") 
    
    # Process weekly_shipped_history_df from raw data after validation
    weekly_shipped_history_df = weekly_reporter.get_weekly_shipped_history(GOOGLE_SHEET_ID, ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME, SERVICE_ACCOUNT_KEY_PATH, key_skus_for_report)
    logger.info(f"Weekly Shipped History Data (from Google Sheet). Shape: {weekly_shipped_history_df.shape}")
    logger.debug(f"Head:\n{weekly_shipped_history_df.head()}")
    logger.debug(f"Tail:\n{weekly_shipped_history_df.tail()}")

    # --- Generate Monthly Charge Report ---
    daily_inventory_df, daily_shipped_sku_qty_df = generate_monthly_charge_report(
        shipstation_api_key, 
        shipstation_api_secret, 
        SERVICE_ACCOUNT_KEY_PATH, 
        GOOGLE_SHEET_ID, 
        MONTHLY_CHARGE_REPORT_TAB_NAME, 
        INITIAL_INVENTORY, 
        PALLET_COUNTS, 
        RATES, 
        golden_raw_raw_data, 
        inventory_trans_raw_data 
    )

    logger.info("Confirmation of Monthly Report Outputs for Weekly Report Input:")
    logger.info(f"DailyInventory_DF is now available for further processing. Shape: {daily_inventory_df.shape}")
    logger.debug(f"Head:\n{daily_inventory_df.head()}")
    logger.info(f"DailyShippedSKUQty_DF is also available. Shape: {daily_shipped_sku_qty_df.shape}")
    logger.debug(f"Head:\n{daily_shipped_sku_qty_df.head()}")

    # --- Generate and Write Weekly Inventory Report ---
    weekly_inventory_report_df = weekly_reporter.generate_weekly_inventory_report(
        GOOGLE_SHEET_ID, 
        WEEKLY_REPORT_TAB_NAME, 
        SERVICE_ACCOUNT_KEY_PATH, 
        daily_inventory_df, 
        weekly_shipped_history_df, 
        key_skus_for_report,
        product_names_map # Pass the newly extracted product_names_map
    )
    logger.info(f"Final Weekly Inventory Report. Shape: {weekly_inventory_report_df.shape}")
    logger.debug(f"Head:\n{weekly_inventory_report_df.head()}")

    logger.info("Attempting to write Weekly Inventory Report to Google Sheets...")
    write_google_sheet_data( # Using imported function
        GOOGLE_SHEET_ID,
        WEEKLY_REPORT_TAB_NAME + "!A1", 
        SERVICE_ACCOUNT_KEY_PATH, 
        weekly_inventory_report_df 
    )
    logger.info("Weekly Inventory Report writing process complete.")

    # --- Consolidated Unit Tests ---
    logger.info("Running Consolidated Unit Tests...")

    # Unit Test for calculate_current_inventory
    if not daily_inventory_df.empty:
        # Expected values based on the *actual* output you confirmed were correct
        expected_current_inventory_df_live_test = pd.DataFrame({
            'SKU': ['17612', '17904', '17914', '18675'],
            'Current Quantity': [634, 198, 361, 774] 
        })
        actual_current_inventory_df_test = weekly_reporter.calculate_current_inventory(daily_inventory_df.copy(), key_skus_for_report)
        
        actual_current_inventory_df_test = actual_current_inventory_df_test.sort_values(by='SKU').reset_index(drop=True)
        expected_current_inventory_df_live_test = expected_current_inventory_df_live_test.sort_values(by='SKU').reset_index(drop=True)

        actual_current_inventory_df_test['Current Quantity'] = actual_current_inventory_df_test['Current Quantity'].astype(int) # Ensure type consistency
        expected_current_inventory_df_live_test['Current Quantity'] = expected_current_inventory_df_live_test['Current Quantity'].astype(int) # Ensure type consistency

        if actual_current_inventory_df_test.equals(expected_current_inventory_df_live_test):
            logger.info("Unit Test (calculate_current_inventory - Live Data) PASSED.")
        else:
            logger.error("Unit Test (calculate_current_inventory - Live Data) FAILED.")
            logger.error(f"Expected:\n{expected_current_inventory_df_live_test}")
            logger.error(f"Actual:\n{actual_current_inventory_df_test}")
    else:
        logger.warning("Skipping calculate_current_inventory live data test due to empty daily_inventory_df.")


    # Unit Test for calculate_12_month_rolling_average
    if not weekly_shipped_history_df.empty and key_skus_for_report:
        # Expected values based on the *actual* output you confirmed were correct
        expected_rolling_average_df_live_test = pd.DataFrame({
            'SKU': ['17612', '17904', '17914', '18675'],
            '12-Month Rolling Average': [471.25, 12.54, 28.04, 3.58] 
        })
        actual_rolling_average_df_test = weekly_reporter.calculate_12_month_rolling_average(weekly_shipped_history_df.copy(), key_skus_for_report)

        actual_rolling_average_df_test = actual_rolling_average_df_test.sort_values(by='SKU').reset_index(drop=True)
        expected_rolling_average_df_live_test = expected_rolling_average_df_live_test.sort_values(by='SKU').reset_index(drop=True)

        actual_rolling_average_df_test['12-Month Rolling Average'] = actual_rolling_average_df_test['12-Month Rolling Average'].astype(str)
        expected_rolling_average_df_live_test['12-Month Rolling Average'] = expected_rolling_average_df_live_test['12-Month Rolling Average'].astype(str)

        if actual_rolling_average_df_test.equals(expected_rolling_average_df_live_test):
            logger.info("Unit Test (calculate_12_month_rolling_average - Live Data) PASSED.")
        else:
            logger.error("Unit Test (calculate_12_month_rolling_average - Live Data) FAILED.")
            logger.error(f"Expected:\n{expected_rolling_average_df_live_test}")
            logger.error(f"Actual:\n{actual_rolling_average_df_test}")
    else:
        logger.warning("Skipping calculate_12_month_rolling_average live data test due to empty weekly_shipped_history_df or key_skus_for_report.")


    logger.info("Script finished. (All data loaded from Google Sheets and consolidated unit tests run)")

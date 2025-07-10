import pandas as pd
import datetime
import math
import time 
import logging # Added logging import for consistency

# Add the project root to the Python path to enable imports from services
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the new Google Sheets API client service
from src.services.google_sheets.sheets_api import get_google_sheet_data, write_google_sheet_data

# Setup logging for this module. This assumes setup_logging from utils.logging_config
# has already been called in the main application entry point.
logger = logging.getLogger(__name__)

# --- Configuration (These will eventually move to central config/settings.py) ---
# For now, keep them if used internally for defaults, but they should be passed as args.
# GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo' # To be passed
# SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json" # To be passed
# SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Used internally by sheets_api

# WEEKLY_REPORT_TAB_NAME = 'Weekly Report' # To be passed
# ORA_CONFIGURATION_TAB_NAME = 'ORA_Configuration' # To be passed
# ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME = 'ORA_Weekly_Shipped_History' # To be passed


# --- REMOVED get_google_sheet_data and write_google_sheet_data from here. They are now imported. ---


def calculate_current_inventory(daily_inventory_df: pd.DataFrame, key_skus: list) -> pd.DataFrame:
    """
    Extracts the most recent End of Day (EOD) quantity for each key SKU
    from the daily inventory DataFrame.
    """
    logger.info("Calculating Current Inventory...")
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


def calculate_12_month_rolling_average(weekly_shipped_history_df: pd.DataFrame, key_skus: list) -> pd.DataFrame:
    """
    Calculates the 12-month (52-week) rolling average of shipped quantities for each key SKU.
    Handles cases with insufficient historical data. Rounds numerical averages to the nearest whole number.
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
            # Round to the nearest whole number
            rolling_average = round(total_shipped_last_52_weeks / 52) 

        rolling_average_data.append({
            'SKU': sku,
            '12-Month Rolling Average': rolling_average
        })
    
    return pd.DataFrame(rolling_average_data)


def get_key_skus(spreadsheet_id: str, config_sheet_name: str, service_account_file_path: str) -> tuple[list, dict]:
    """
    Reads the 'ORA_Configuration' Google Sheet to extract the list of "Key Products (SKUs)".
    Assumes the structure: 'ParameterCategory', 'ParameterName', 'SKU', 'Value', etc.
    It looks for 'ParameterCategory' == 'Key Products' and returns SKUs and their product names.
    """
    logger.info(f"Attempting to read Key SKUs from '{config_sheet_name}' sheet...")
    raw_config_data = get_google_sheet_data( # Using imported function
        spreadsheet_id,
        f'{config_sheet_name}!A:F', 
        service_account_file_path
    )

    key_skus = []
    product_names = {} 

    if raw_config_data and len(raw_config_data) > 1:
        headers = [h.strip() for h in raw_config_data[0]]
        data_rows = raw_config_data[1:]

        try:
            param_cat_idx = headers.index('ParameterCategory')
            param_name_idx = headers.index('ParameterName') 
            sku_idx = headers.index('SKU')
            value_idx = headers.index('Value') # Value might be empty for Key Products, but index needed for len check

            for row in data_rows:
                # Ensure row has enough columns to avoid IndexError
                if len(row) > max(param_cat_idx, param_name_idx, sku_idx, value_idx):
                    category = row[param_cat_idx].strip()
                    name = row[param_name_idx].strip()
                    sku = row[sku_idx].strip() if sku_idx < len(row) and row[sku_idx] else None

                    if category == 'Key Products' and sku:
                        key_skus.append(sku)
                        product_names[sku] = name 
        except ValueError as e:
            logger.error(f"Error: Missing expected column in ORA_Configuration sheet (e.g., 'ParameterCategory', 'SKU', or 'ParameterName'): {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing ORA_Configuration: {e}", exc_info=True)
    else:
        logger.warning("No data or malformed data found in ORA_Configuration sheet.")
    
    unique_key_skus = sorted(list(set(key_skus)))
    return unique_key_skus, product_names 


def get_weekly_shipped_history(spreadsheet_id: str, sheet_name: str, service_account_file_path: str, key_skus_for_report: list) -> pd.DataFrame:
    """
    Reads historical weekly aggregated SKU shipment quantities from the specified Google Sheet tab.
    It handles the "Ship Week" date range format and unpivots the data.
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

def generate_weekly_inventory_report(
    google_sheet_id: str, weekly_report_tab_name: str, service_account_file_path: str, 
    daily_inventory_df: pd.DataFrame, weekly_shipped_history_df: pd.DataFrame, 
    key_skus_for_report: list, product_names_map: dict) -> pd.DataFrame:
    """
    Orchestrates the generation and writing of the Weekly Inventory Report.
    Combines current inventory and 12-month rolling average.
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
    
    # Add Product Name column
    weekly_report_df['Product'] = weekly_report_df['SKU'].map(product_names_map).fillna('N/A')

    weekly_report_df['Quantity'] = weekly_report_df['Current Quantity'].fillna(0).astype(int) 
    # Convert rolling average to int, handling "Insufficient Data" strings gracefully
    weekly_report_df['Weekly Avg'] = weekly_report_df['12-Month Rolling Average'].apply( 
        lambda x: int(round(float(x))) if isinstance(x, (int, float)) else x
    ).fillna('N/A')


    # Ensure final column order: SKU, Product, Quantity, Weekly Avg
    final_columns = ['SKU', 'Product', 'Quantity', 'Weekly Avg'] 
    weekly_report_df = weekly_report_df[final_columns]
    
    logger.info(f"Final Weekly Inventory Report. Shape: {weekly_report_df.shape}")
    logger.debug(f"Head:\n{weekly_report_df.head()}")

    logger.info("Attempting to write Weekly Inventory Report to Google Sheets...")
    write_google_sheet_data( # Using imported function
        google_sheet_id, 
        weekly_report_tab_name + "!A1", 
        service_account_file_path,
        weekly_report_df 
    )
    logger.info("Weekly Inventory Report writing process complete.")

    return weekly_report_df


# --- Main execution block for independent debugging of weekly_reporter.py ---
if __name__ == "__main__":
    import os # Added for path manipulation in dummy config
    import sys # Added for sys.exit

    # Simulate logging setup for independent module testing
    # In a full application, setup_logging from utils.logging_config would be used.
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("Starting Weekly Reporter (Independent Debugging) Script...")

    # --- Simulate Configuration (normally from central config and Secret Manager) ---
    DUMMY_GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo' # Replace with your actual Sheet ID
    DUMMY_SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json" # Replace with your actual path

    # Ensure a dummy service account key file exists for local testing of Google Sheet access
    if not os.path.exists(DUMMY_SERVICE_ACCOUNT_KEY_PATH):
        logger.warning(f"Dummy service account key path '{DUMMY_SERVICE_ACCOUNT_KEY_PATH}' does not exist. Creating it for testing.")
        os.makedirs(os.path.dirname(DUMMY_SERVICE_ACCOUNT_KEY_PATH), exist_ok=True)
        # Create a minimal dummy JSON structure for google.oauth2.service_account.Credentials.from_service_account_file
        dummy_content = json.dumps({
            "type": "service_account",
            "project_id": "ora-automation-project", # Use your actual project ID
            "private_key_id": "dummy_private_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nDUmMyKeY\\n-----END PRIVATE KEY-----\\n", 
            "client_email": "dummy-service-account@ora-automation-project.iam.gserviceaccount.com", # Use your actual service account email
            "client_id": "dummy_client_id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy-service-account%40ora-automation-project.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        })
        with open(DUMMY_SERVICE_ACCOUNT_KEY_PATH, 'w') as f:
            f.write(dummy_content)
    
    # 1. Simulate key_skus_for_report and product_names_map (normally from ORA_Configuration)
    # Using real values as per your config sheet
    key_skus_for_test = ['17612', '17904', '17914', '18675'] 
    product_names_test_map = {
        '17612': 'PT Kit',
        '17904': 'Travel Kit',
        '17914': 'PPR Kit',
        '18675': 'Ortho Protect'
    }

    # 2. Simulate daily_inventory_df (normally from generate_monthly_charge_report)
    simulated_daily_inventory_df_realistic = pd.DataFrame({
        'Date': pd.to_datetime(['2025-05-03'] * len(key_skus_for_test)),
        'SKU': key_skus_for_test,
        'ShippedQty': [0] * len(key_skus_for_test), 
        'ReceivedQty': [0] * len(key_skus_for_test),
        'RepackedQty': [0] * len(key_skus_for_test),
        'BOD_Qty': [0] * len(key_skus_for_test),
        'EOD_Qty': [991, 214, 416, 776] 
    })


    # 3. Simulate weekly_shipped_history_df (normally from get_weekly_shipped_history)
    simulated_weekly_shipped_history_df_17612 = pd.DataFrame({
        'WeekEndDate': pd.to_datetime([f'2024-05-12', f'2024-05-19', f'2024-05-26', f'2024-06-02', f'2024-06-09', f'2024-06-16', f'2024-06-23', f'2024-06-30', f'2024-07-07', f'2024-07-14', 
                                     f'2024-07-21', f'2024-07-28', f'2024-08-04', f'2024-08-11', f'2024-08-18', f'2024-08-25', f'2024-09-01', f'2024-09-08', f'2024-09-15', f'2024-09-22', 
                                     f'2024-09-29', f'2024-10-06', f'2024-10-13', f'2024-10-20', f'2024-10-27', f'2024-11-03', f'2024-11-10', f'2024-11-17', f'2024-11-24', f'2024-12-01', 
                                     f'2024-12-08', f'2024-12-15', f'2024-12-22', f'2024-12-29', f'2025-01-05', f'2025-01-12', f'2025-01-19', f'2025-01-26', f'2025-02-02', f'2025-02-09', 
                                     f'2025-02-16', f'2025-02-23', f'2025-03-02', f'2025-03-09', f'2025-03-16', f'2025-03-23', f'2025-03-30', f'2025-04-06', f'2025-04-13', f'2025-04-20', 
                                     f'2025-04-27', f'2025-05-04']), # 52 weeks ending 2025-05-04
        'SKU': ['17612'] * 52,
        'ShippedQuantity': [414, 488, 411, 352, 489, 532, 390, 443, 361, 299, 
                            330, 380, 420, 450, 400, 370, 320, 300, 280, 250, 
                            230, 200, 180, 150, 120, 100, 90, 80, 70, 60,   
                            50, 40, 30, 20, 10, 5, 1, 0, 0, 0,             
                            10, 15, 20, 25, 30, 35, 40, 45, 50, 55,       
                            60, 65]                                     
    }).assign(SKU='17612')

    # For '17904' which should show 'Insufficient Data' (fewer than 52 weeks)
    simulated_weekly_shipped_history_df_17904 = pd.DataFrame({
        'WeekEndDate': pd.to_datetime([f'2025-01-01', f'2025-01-08', f'2025-01-15', f'2025-01-22', f'2025-01-29']), # 5 weeks of data
        'SKU': ['17904'] * 5,
        'ShippedQuantity': [10, 12, 8, 15, 7]
    })

    # For '17914' (exactly 52 weeks, consistent values)
    simulated_weekly_shipped_history_df_17914 = pd.DataFrame({
        'WeekEndDate': pd.to_datetime([f'2024-05-12', f'2024-05-19', f'2024-05-26', f'2024-06-02', f'2024-06-09', f'2024-06-16', f'2024-06-23', f'2024-06-30', f'2024-07-07', f'2024-07-14', 
                                     f'2024-07-21', f'2024-07-28', f'2024-08-04', f'2024-08-11', f'2024-08-18', f'2024-08-25', f'2024-09-01', f'2024-09-08', f'2024-09-15', f'2024-09-22', 
                                     f'2024-09-29', f'2024-10-06', f'2024-10-13', f'2024-10-20', f'2024-10-27', f'2024-11-03', f'2024-11-10', f'2024-11-17', f'2024-11-24', f'2024-12-01', 
                                     f'2024-12-08', f'2024-12-15', f'2024-12-22', f'2024-12-29', f'2025-01-05', f'2025-01-12', f'2025-01-19', f'2025-01-26', f'2025-02-02', f'2025-02-09', 
                                     f'2025-02-16', f'2025-02-23', f'2025-03-02', f'2025-03-09', f'2025-03-16', f'2025-03-23', f'2025-03-30', f'2025-04-06', f'2025-04-13', f'2025-04-20', 
                                     f'2025-04-27', f'2025-05-04']), # 52 weeks ending 2025-05-04
        'SKU': ['17914'] * 52,
        'ShippedQuantity': [75 + i % 5 for i in range(52)] # Varying values for avg
    })

    # For '18675' (just under 52 weeks, to test 'Insufficient Data')
    simulated_weekly_shipped_history_df_18675 = pd.DataFrame({
        'WeekEndDate': pd.to_datetime([f'2024-06-01', f'2024-06-08', f'2024-06-15', f'2024-06-22', f'2024-06-29', 
                                     f'2024-07-06', f'2024-07-13', f'2024-07-20', f'2024-07-27', f'2024-08-03', 
                                     f'2024-08-10', f'2024-08-17', f'2024-08-24', f'2024-08-31', f'2024-09-07', 
                                     f'2024-09-14', f'2024-09-21', f'2024-09-28', f'2024-10-05', f'2024-10-12', 
                                     f'2024-10-19', f'2024-10-26', f'2024-11-02', f'2024-11-09', f'2024-11-16', 
                                     f'2024-11-23', f'2024-11-30', f'2024-12-07', f'2024-12-14', f'2024-12-21', 
                                     f'2024-12-28', f'2025-01-05', f'2025-01-12', f'2025-01-19', f'2025-01-26', 
                                     f'2025-02-02', f'2025-02-09', f'2025-02-16', f'2025-02-23', f'2025-03-02', 
                                     f'2025-03-09', f'2025-03-16', f'2025-03-22', f'2025-03-29', f'2025-04-05', 
                                     f'2025-04-12', f'2025-04-19', f'2025-04-26', f'2025-05-03', f'2025-05-10']), # 50 weeks
        'SKU': ['18675'] * 50,
        'ShippedQuantity': [20 + i % 3 for i in range(50)]
    })

    # Concatenate all simulated history data
    simulated_weekly_shipped_history_df_all_skus = pd.concat([
        simulated_weekly_shipped_history_df_17612, 
        simulated_weekly_shipped_history_df_17904,
        simulated_weekly_shipped_history_df_17914,
        simulated_weekly_shipped_history_df_18675
    ]).reset_index(drop=True)


    # Run the report generation
    weekly_report_result_df = generate_weekly_inventory_report(
        DUMMY_GOOGLE_SHEET_ID, # Pass spreadsheet_id
        'Weekly Report', # Pass weekly_report_tab_name (or from central config later)
        DUMMY_SERVICE_ACCOUNT_KEY_PATH, # Pass service_account_file_path
        simulated_daily_inventory_df_realistic, 
        simulated_weekly_shipped_history_df_all_skus, 
        key_skus_for_test, 
        product_names_test_map 
    )
    
    logger.info("\n--- Independent Weekly Report Run Results ---")
    logger.info(f"Shape: {weekly_report_result_df.shape}")
    logger.info("Head:\n" + str(weekly_report_result_df.head())) # Use str() for explicit conversion

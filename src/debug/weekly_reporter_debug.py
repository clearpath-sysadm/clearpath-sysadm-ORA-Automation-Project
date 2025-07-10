import pandas as pd
import datetime
import math
from google.oauth2 import service_account 
from googleapiclient.discovery import build 
from googleapiclient.errors import HttpError 
import time 

# --- Configuration (Replicated for independent running) ---
# IMPORTANT: These must match your actual Google Sheet ID and service account path
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] 

WEEKLY_REPORT_TAB_NAME = 'Weekly Report'
ORA_CONFIGURATION_TAB_NAME = 'ORA_Configuration'
ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME = 'ORA_Weekly_Shipped_History'

# --- Replicated get_google_sheet_data for independent operation ---
def get_google_sheet_data(spreadsheet_id, range_name, service_account_file_path): 
    """
    Retrieves data from a Google Sheet using a service account file.
    Includes retry logic for HttpError 503 (Service Unavailable).
    This function is a copy from the main script for independent validation.
    """
    max_retries = 15 
    initial_delay = 1  

    for attempt in range(max_retries):
        try:
            creds = service_account.Credentials.from_service_account_file(service_account_file_path, scopes=SCOPES) 
            service = build('sheets', 'v4', credentials=creds)
            
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])

            if not values:
                print(f"No data found in sheet: {range_name}")
                return []
            else:
                return values
        except HttpError as e:
            if e.resp.status == 503:
                print(f"HttpError 503 (Service Unavailable) accessing Google Sheet '{spreadsheet_id}' range '{range_name}'. Retrying in {initial_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(initial_delay)
                initial_delay *= 2 
            else:
                print(f"Error accessing Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
                print(f"Details: {e}")
                return []
        except FileNotFoundError: 
            print(f"Error: Service account file not found at '{service_account_file_path}'. Please check the path.")
            return []
        except Exception as e:
            print(f"Error accessing Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
            print(f"Details: {e}")
            return []
    
    print(f"Failed to retrieve data from Google Sheet '{spreadsheet_id}' range '{range_name}' after {max_retries} retries due to HttpError 503.")
    return []


def write_google_sheet_data(spreadsheet_id, range_name, df_to_write, service_account_file_path): 
    """
    Writes a Pandas DataFrame to a Google Sheet, clearing existing data first.
    Includes retry logic for HttpError 503.
    """
    max_retries = 5
    initial_delay = 1 

    values_to_write = [df_to_write.columns.tolist()] + df_to_write.astype(str).values.tolist()

    for attempt in range(max_retries):
        try:
            creds = service_account.Credentials.from_service_account_file(service_account_file_path, scopes=SCOPES) 
            service = build('sheets', 'v4', credentials=creds)

            clear_request_body = {} 
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                body=clear_request_body
            ).execute()
            print(f"Cleared existing data in {range_name}.")

            body = {
                'values': values_to_write
            }
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW', 
                body=body
            ).execute()
            print(f"{result.get('updatedCells')} cells updated in {range_name}.")
            return True 
        except HttpError as e:
            if e.resp.status == 503:
                print(f"HttpError 503 (Service Unavailable) writing to Google Sheet '{spreadsheet_id}' range '{range_name}'. Retrying in {initial_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(initial_delay)
                initial_delay *= 2
            else:
                print(f"Error writing to Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
                print(f"Details: {e}")
                return False 
        except FileNotFoundError: 
            print(f"Error: Service account file not found at '{service_account_file_path}'. Please check the path.")
            return False
        except Exception as e:
            print(f"Error writing to Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
            print(f"Details: {e}")
            return False
    
    print(f"Failed to write data to Google Sheet '{spreadsheet_id}' range '{range_name}' after {max_retries} retries due to HttpError 503.")
    return []


def calculate_current_inventory(daily_inventory_df, key_skus):
    """
    Extracts the most recent End of Day (EOD) quantity for each key SKU
    from the daily inventory DataFrame.
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
    """
    print("\n--- Calculating 12-Month Rolling Average ---")
    rolling_average_data = []
    
    expected_cols = ['WeekEndDate', 'SKU', 'ShippedQuantity']
    for col in expected_cols:
        if col not in weekly_shipped_history_df.columns:
            print(f"ERROR: Missing expected column '{col}' in weekly_shipped_history_df. Available columns: {weekly_shipped_history_df.columns.tolist()}")
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
    """
    print(f"Attempting to read Key SKUs from '{config_sheet_name}' sheet...")
    raw_config_data = get_google_sheet_data(
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

            for row in data_rows:
                if len(row) > max(param_cat_idx, sku_idx):
                    category = row[param_cat_idx].strip()
                    sku = row[sku_idx].strip()

                    if category == 'Key Products' and sku:
                        key_skus.append(sku)
        except ValueError as e:
            print(f"Error: Missing expected column in ORA_Configuration sheet (e.g., 'ParameterCategory' or 'SKU'): {e}")
        except Exception as e:
            print(f"An unexpected error occurred while parsing ORA_Configuration: {e}")
    else:
        print("No data or malformed data found in ORA_Configuration sheet.")
    
    unique_key_skus = sorted(list(set(key_skus)))
    return unique_key_skus


def get_weekly_shipped_history(spreadsheet_id, sheet_name, service_account_file_path, key_skus_for_report):
    """
    Reads historical weekly aggregated SKU shipment quantities from the specified Google Sheet tab.
    It handles the "Ship Week" date range format and unpivots the data.
    """
    print(f"Attempting to read historical weekly shipped data from '{sheet_name}' sheet...")
    range_name = f'{sheet_name}!A:E' 
    raw_history_data = get_google_sheet_data(
        spreadsheet_id,
        range_name,
        service_account_file_path
    )

    weekly_shipped_df = pd.DataFrame()
    if raw_history_data and len(raw_history_data) > 0: 
        headers = [h.strip() for h in raw_history_data[0]]
        data_rows = raw_history_data[1:]

        if not headers or not data_rows:
            print(f"WARNING: No valid headers or data rows found in '{sheet_name}'. Returning empty DataFrame.")
            return pd.DataFrame(columns=['WeekEndDate', 'SKU', 'ShippedQuantity'])

        df_temp = pd.DataFrame(data_rows, columns=headers)
        print(f"DEBUG: Columns of df_temp before melt: {df_temp.columns.tolist()}")

        id_vars = ['Ship Week']
        
        value_vars = [str(col).strip() for col in headers if str(col).strip() in key_skus_for_report]
        
        if not value_vars:
            print(f"ERROR: No matching SKU columns found in '{sheet_name}' based on key_skus_for_report: {key_skus_for_report}. Available headers: {headers}. Returning empty DataFrame.")
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
                print(f"Warning: Could not convert 'WeekEndDate' column (date range) to datetime in '{sheet_name}'. Details: {e}")
                weekly_shipped_df['WeekEndDate'] = pd.NaT 

        if 'SKU' in weekly_shipped_df.columns:
            weekly_shipped_df['SKU'] = weekly_shipped_df['SKU'].astype(str)
        if 'ShippedQuantity' in weekly_shipped_df.columns:
            try:
                weekly_shipped_df['ShippedQuantity'] = pd.to_numeric(weekly_shipped_df['ShippedQuantity'], errors='coerce').fillna(0)
            except Exception as e:
                print(f"Warning: Could not convert 'ShippedQuantity' column to numeric in '{sheet_name}' after melt. Details: {e}")
                weekly_shipped_df['ShippedQuantity'] = 0 

    else:
        print(f"No data retrieved from '{sheet_name}' sheet or sheet is empty/malformed.")
    print(f"DEBUG: Columns of weekly_shipped_df after melt and rename: {weekly_shipped_df.columns.tolist()}")
    return weekly_shipped_df


def generate_weekly_inventory_report(
    google_sheet_id, weekly_report_tab_name, service_account_file_path, 
    daily_inventory_df, weekly_shipped_history_df, key_skus_for_report):
    """
    Orchestrates the generation and writing of the Weekly Inventory Report.
    Combines current inventory and 12-month rolling average.
    """
    print("\n--- Generating Weekly Inventory Report ---")

    # Step 4: Calculate Current Inventory
    current_inventory_df = calculate_current_inventory(daily_inventory_df, key_skus_for_report)
    print(f"\n--- Calculated Current Inventory for Weekly Report ---")
    print(f"Shape: {current_inventory_df.shape}")
    print("Head:\n", current_inventory_df.head())

    # Step 5: Calculate 12-Month Rolling Average
    rolling_average_df = calculate_12_month_rolling_average(weekly_shipped_history_df, key_skus_for_report)
    print(f"\n--- Calculated 12-Month Rolling Average for Weekly Report ---")
    print(f"Shape: {rolling_average_df.shape}")
    print("Head:\n", rolling_average_df.head())

    # Merge current inventory and rolling average DataFrames
    weekly_report_df = pd.merge(
        current_inventory_df,
        rolling_average_df,
        on='SKU',
        how='outer'
    )
    
    weekly_report_df['Current Quantity'] = weekly_report_df['Current Quantity'].fillna(0).astype(int)
    weekly_report_df['12-Month Rolling Average'] = weekly_report_df['12-Month Rolling Average'].fillna('N/A')

    final_columns = ['SKU', 'Current Quantity', '12-Month Rolling Average']
    weekly_report_df = weekly_report_df[final_columns]

    print(f"\n--- Final Weekly Inventory Report ---")
    print(f"Shape: {weekly_report_df.shape}")
    print("Head:\n", weekly_report_df.head())

    return weekly_report_df


# --- Main execution block for independent debugging of weekly_reporter.py ---
if __name__ == "__main__":
    print("Starting Weekly Reporter (Independent Debugging) Script...")

    # --- Simulate necessary inputs for generate_weekly_inventory_report ---
    # These would normally come from shipstation_reporter.py or be loaded live
    
    # 1. Simulate key_skus_for_report (normally from ORA_Configuration)
    # Using a subset for simplicity in independent testing
    key_skus_for_test = ['17612', '17904', '17914', '18675'] 

    # 2. Simulate daily_inventory_df (normally from generate_monthly_charge_report)
    # This minimal data is enough for calculate_current_inventory
    # Using realistic EODs based on a previous successful full run output (from output_shipstation_reporter.txt)
    simulated_daily_inventory_df_realistic = pd.DataFrame({
        'Date': pd.to_datetime(['2025-05-03'] * len(key_skus_for_test)), # Assuming latest EOD date
        'SKU': key_skus_for_test,
        'ShippedQty': [0] * len(key_skus_for_test), 
        'ReceivedQty': [0] * len(key_skus_for_test),
        'RepackedQty': [0] * len(key_skus_for_test),
        'BOD_Qty': [0] * len(key_skus_for_test),
        'EOD_Qty': [991, 214, 416, 776] # These are the EODs from a successful Monthly Report output
    })


    # 3. Simulate weekly_shipped_history_df (normally from get_weekly_shipped_history)
    # This data needs to be sufficiently long (52+ weeks) for rolling average
    # Using values that approximate your ORA_Weekly_Shipped_History sheet's output
    # (Tail values were used to derive some of these averages)
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
                                     f'2024-12-28', f'2025-01-04', f'2025-01-11', f'2025-01-18', f'2025-01-25', 
                                     f'2025-02-01', f'2025-02-08', f'2025-02-15', f'2025-02-22', f'2025-03-01', 
                                     f'2025-03-08', f'2025-03-15', f'2025-03-22', f'2025-03-29', f'2025-04-05', 
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
        GOOGLE_SHEET_ID, 
        WEEKLY_REPORT_TAB_NAME, 
        SERVICE_ACCOUNT_KEY_PATH, 
        simulated_daily_inventory_df_realistic, 
        simulated_weekly_shipped_history_df_all_skus, 
        key_skus_for_test
    )
    
    print("\n--- Independent Weekly Report Run Results ---")
    print(f"Shape: {weekly_report_result_df.shape}")
    print("Head:\n", weekly_report_result_df.head())

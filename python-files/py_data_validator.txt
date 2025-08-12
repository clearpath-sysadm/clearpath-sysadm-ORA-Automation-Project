import pandas as pd
import datetime
from google.oauth2 import service_account 
from googleapiclient.discovery import build 
from googleapiclient.errors import HttpError 
import time 
import json 

# --- Configuration for Google Sheets API (Replicated for independent running) ---
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] 

# --- Sheet Names and Ranges (Replicated for independent running) ---
ORA_CONFIGURATION_TAB_NAME = 'ORA_Configuration'
ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME = 'ORA_Weekly_Shipped_History'
GOLDEN_TEST_DATA_RAW_TAB_NAME = 'Golden_Test_Data_Raw'
INVENTORY_TRANSACTIONS_TAB_NAME = 'Inventory_Transactions'

# --- Replicated get_google_sheet_data for independent operation ---
def get_google_sheet_data_for_validator(spreadsheet_id, range_name, service_account_file_path): 
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

# --- Validation Functions ---

def validate_ora_configuration(raw_config_data):
    """
    Validates the raw data from the ORA_Configuration sheet.
    Checks for essential headers and attempts to parse key sections.
    Returns (True, message) on success or (False, error_message).
    """
    print(f"\n--- Validating '{ORA_CONFIGURATION_TAB_NAME}' ---")
    if not raw_config_data or len(raw_config_data) < 2:
        return False, f"Error: No data or insufficient rows in '{ORA_CONFIGURATION_TAB_NAME}'."

    headers = [h.strip() for h in raw_config_data[0]]
    data_rows = raw_config_data[1:]
    
    expected_headers = ['ParameterCategory', 'ParameterName', 'SKU', 'Value', 'Unit/Description', 'Notes']
    for header in expected_headers:
        if header not in headers:
            return False, f"Error: Missing expected header '{header}' in '{ORA_CONFIGURATION_TAB_NAME}'. Found: {headers}"

    rates_found = False
    pallet_config_found = False
    initial_inventory_found = False
    key_products_found = False
    
    test_skus_extracted = [] 

    try:
        param_cat_idx = headers.index('ParameterCategory')
        param_name_idx = headers.index('ParameterName')
        sku_idx = headers.index('SKU')
        value_idx = headers.index('Value')

        for i, row in enumerate(data_rows):
            if len(row) <= max(param_cat_idx, param_name_idx, sku_idx, value_idx):
                print(f"DEBUG: Skipping row {i+2} due to insufficient columns. Row: {row}")
                continue 

            category = row[param_cat_idx].strip()
            print(f"DEBUG: Row {i+2} - ParameterCategory found: '{category}' (len={len(category)}). Expected: 'Key Products'")

            name = row[param_name_idx].strip()
            value = row[value_idx].strip() 
            sku = row[sku_idx].strip() if sku_idx < len(row) and row[sku_idx] else None

            if category == 'Rates':
                try: float(value); rates_found = True
                except ValueError: return False, f"Error: Value '{value}' for Rate '{name}' (row {i+2}) in '{ORA_CONFIGURATION_TAB_NAME}' is not a valid number."
            elif category == 'PalletConfig':
                if sku:
                    try: int(value); pallet_config_found = True
                    except ValueError: return False, f"Error: Value '{value}' for PalletConfig SKU '{sku}' (row {i+2}) in '{ORA_CONFIGURATION_TAB_NAME}' is not a valid integer."
            elif category == 'InitialInventory':
                if sku:
                    try: int(value); initial_inventory_found = True
                    except ValueError: return False, f"Error: Value '{value}' for InitialInventory SKU '{sku}' (row {i+2}) in '{ORA_CONFIGURATION_TAB_NAME}' is not a valid integer."
            elif category == 'Key Products': 
                if sku:
                    key_products_found = True
                    test_skus_extracted.append(sku)
    except Exception as e:
        return False, f"Error processing rows in '{ORA_CONFIGURATION_TAB_NAME}': {e}"
    
    if not rates_found: print(f"Warning: No 'Rates' configuration found in '{ORA_CONFIGURATION_TAB_NAME}'.")
    if not pallet_config_found: print(f"Warning: No 'PalletConfig' found in '{ORA_CONFIGURATION_TAB_NAME}'.")
    if not initial_inventory_found: print(f"Warning: No 'InitialInventory' found in '{ORA_CONFIGURATION_TAB_NAME}'.")
    if not key_products_found: return False, f"Error: No 'Key Products' found in '{ORA_CONFIGURATION_TAB_NAME}'. This is essential for SKU filtering."
    
    return True, f"'{ORA_CONFIGURATION_TAB_NAME}' validated successfully. Extracted Key SKUs: {test_skus_extracted}"


def validate_weekly_shipped_history(raw_history_data, key_skus_from_config):
    """
    Validates the raw data from the ORA_Weekly_Shipped_History sheet.
    Checks for 'Ship Week' column, SKU columns (matching key_skus), and data types.
    Also validates the 'Ship Week' date range format.
    Returns (True, message) on success or (False, error_message).
    """
    print(f"\n--- Validating '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' ---")
    if not raw_history_data or len(raw_history_data) < 2:
        return False, f"Error: No data or insufficient rows in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}'."

    headers = [str(h).strip() for h in raw_history_data[0]] 
    data_rows = raw_history_data[1:]

    if 'Ship Week' not in headers:
        return False, f"Error: Missing 'Ship Week' header in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}'. Found: {headers}"
    
    key_skus_set = set(key_skus_from_config)
    sku_headers = [h for h in headers if h in key_skus_set]
    
    if not sku_headers:
        return False, f"Error: No matching SKU columns found in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' headers based on key SKUs: {key_skus_from_config}. Found headers: {headers}"

    try:
        df_temp = pd.DataFrame(data_rows, columns=headers)
        df_temp.rename(columns={'Ship Week': 'Ship Week'}, inplace=True) 
        
        test_melt_df = pd.melt(
            df_temp,
            id_vars=['Ship Week'], 
            value_vars=sku_headers, 
            var_name='SKU',
            value_name='ShippedQuantity'
        )

        if 'Ship Week' not in test_melt_df.columns:
            return False, f"Error: 'Ship Week' column not retained after melt in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}'."

        for i, val in enumerate(test_melt_df['Ship Week']):
            val_str = str(val).strip()
            if ' - ' in val_str:
                try:
                    pd.to_datetime(val_str.split(' - ')[1].strip())
                except Exception:
                    return False, f"Error: 'Ship Week' value '{val}' (row {i+2}) in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' is not in 'MM/DD/YYYY - MM/DD/YYYY' format or end date is unparseable."
            else:
                try: 
                    pd.to_datetime(val_str)
                except Exception:
                    return False, f"Error: 'Ship Week' value '{val}' (row {i+2}) in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' is not a valid date format."

        if 'SKU' not in test_melt_df.columns:
            return False, f"Error: 'SKU' column not created after melt in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}'."
        if 'ShippedQuantity' not in test_melt_df.columns:
            return False, f"Error: 'ShippedQuantity' column not created after melt in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}'."
        
        try:
            pd.to_numeric(test_melt_df['ShippedQuantity'], errors='raise')
        except Exception:
            return False, f"Error: 'ShippedQuantity' column in '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' contains non-numeric values."

    except Exception as e:
        return False, f"Error during pre-processing (melting/type conversion check) of '{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}': {e}"

    return True, f"'{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}' validated successfully. SKU columns found: {sku_headers}"


def validate_golden_test_data_raw(raw_data):
    """
    Validates the raw data from the Golden_Test_Data_Raw sheet.
    Checks for expected headers and 'Transaction_Type' consistency.
    Includes specific checks for Order_Number presence based on Transaction_Type.
    Returns (True, message) on success or (False, error_message).
    """
    print(f"\n--- Validating '{GOLDEN_TEST_DATA_RAW_TAB_NAME}' ---")
    if not raw_data or len(raw_data) < 2:
        return False, f"Error: No data or insufficient rows in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}'."

    headers = [h.strip() for h in raw_data[0]]
    data_rows = raw_data[1:]

    expected_headers = ['Date', 'SKU_With_Lot', 'Quantity_Shipped', 'Order_Number', 
                        'Inventory_SKU', 'Quantity_Received', 'Quantity_Repacked', 'Transaction_Type']
    for header in expected_headers:
        if header not in headers:
            return False, f"Error: Missing expected header '{header}' in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}'. Found: {headers}"
    
    shipped_item_order_numbers = []
    shipped_order_order_numbers = [] # New list to collect ShippedOrder order numbers

    try:
        date_idx = headers.index('Date')
        qty_shipped_idx = headers.index('Quantity_Shipped')
        qty_received_idx = headers.index('Quantity_Received')
        qty_repacked_idx = headers.index('Quantity_Repacked')
        trans_type_idx = headers.index('Transaction_Type')
        order_num_idx = headers.index('Order_Number') 

        for i, row in enumerate(data_rows):
            if len(row) <= max(date_idx, qty_shipped_idx, qty_received_idx, qty_repacked_idx, trans_type_idx, order_num_idx):
                continue

            trans_type = row[trans_type_idx].strip()
            order_num_val = str(row[order_num_idx]).strip()
            
            # Check date parsing
            try: pd.to_datetime(row[date_idx])
            except Exception: return False, f"Error: Date '{row[date_idx]}' (row {i+2}) in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}' is not a valid date format."

            if trans_type == 'ShippedItem':
                # Warning for ShippedItem if Order_Number is present but should be NULL/ignored for order counting
                if order_num_val and order_num_val.upper() != 'NULL':
                    print(f"WARNING: Order_Number '{order_num_val}' for ShippedItem (row {i+2}) found in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}'. This order number may be ignored if only 'ShippedOrder' types are used for order counting.")
                # We still expect quantities to be numeric for ShippedItem
                try: int(row[qty_shipped_idx])
                except ValueError: return False, f"Error: Quantity_Shipped '{row[qty_shipped_idx]}' (row {i+2}) for 'ShippedItem' in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}' is not numeric."
            
            elif trans_type == 'ShippedOrder': # New check for ShippedOrder
                if order_num_val.upper() == 'NULL' or order_num_val == '':
                    return False, f"Error: Order_Number for 'ShippedOrder' (row {i+2}) is missing or 'NULL' in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}'. This is required for order counting."
                else:
                    shipped_order_order_numbers.append(order_num_val) # Collect valid ShippedOrder order numbers
                # Quantity_Shipped might also be relevant for ShippedOrder, but current spec only calls for Order_Number here.
                # If ShippedOrder also implies a quantity, add a check similar to ShippedItem.
            
            elif trans_type == 'Receive':
                try: int(row[qty_received_idx])
                except ValueError: return False, f"Error: Quantity_Received '{row[qty_received_idx]}' (row {i+2}) for 'Receive' in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}' is not numeric."
            elif trans_type in ['RepackedInv', 'Repack']: 
                try: int(row[qty_repacked_idx])
                except ValueError: return False, f"Error: Quantity_Repacked '{row[qty_repacked_idx]}' (row {i+2}) for 'Repack' in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}' is not numeric."
            else:
                 print(f"WARNING: Unexpected Transaction_Type '{trans_type}' (row {i+2}) in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}'.")

    except Exception as e:
        return False, f"Error processing rows in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}': {e}"

    if not shipped_order_order_numbers:
        return False, f"Error: No valid Order_Numbers found for 'ShippedOrder' transactions in '{GOLDEN_TEST_DATA_RAW_TAB_NAME}'. This will result in zero orders counted in reports."

    return True, f"'{GOLDEN_TEST_DATA_RAW_TAB_NAME}' validated successfully. Found {len(shipped_order_order_numbers)} valid 'ShippedOrder' Order_Numbers."


def validate_inventory_transactions(raw_data):
    """
    Validates the raw data from the Inventory_Transactions sheet.
    Checks for essential headers and data types.
    Returns (True, message) on success or (False, error_message).
    """
    print(f"\n--- Validating '{INVENTORY_TRANSACTIONS_TAB_NAME}' ---")
    if not raw_data or len(raw_data) < 2:
        return False, f"Error: No data or insufficient rows in '{INVENTORY_TRANSACTIONS_TAB_NAME}'."

    headers = [h.strip() for h in raw_data[0]]
    data_rows = raw_data[1:]

    expected_headers = ['Date', 'SKU', 'Quantity', 'TransactionType']
    for header in expected_headers:
        if header not in headers:
            return False, f"Error: Missing expected header '{header}' in '{INVENTORY_TRANSACTIONS_TAB_NAME}'. Found: {headers}"

    try:
        date_idx = headers.index('Date')
        sku_idx = headers.index('SKU')
        qty_idx = headers.index('Quantity')
        trans_type_idx = headers.index('TransactionType')

        for i, row in enumerate(data_rows):
            if len(row) <= max(date_idx, sku_idx, qty_idx, trans_type_idx):
                continue
            
            # Date validation
            try: pd.to_datetime(row[date_idx])
            except Exception: return False, f"Error: Date '{row[date_idx]}' (row {i+2}) in '{INVENTORY_TRANSACTIONS_TAB_NAME}' is not a valid date format."
            
            # Quantity validation
            try: float(row[qty_idx]) 
            except ValueError: return False, f"Error: Quantity '{row[qty_idx]}' (row {i+2}) in '{INVENTORY_TRANSACTIONS_TAB_NAME}' is not numeric."

            valid_transaction_types = ['Receive', 'Repack'] 
            if row[trans_type_idx].strip() not in valid_transaction_types:
                 print(f"Warning: Unexpected TransactionType '{row[trans_type_idx].strip()}' (row {i+2}) in '{INVENTORY_TRANSACTIONS_TAB_NAME}'.")

    except Exception as e:
        return False, f"Error processing rows in '{INVENTORY_TRANSACTIONS_TAB_NAME}': {e}"

    return True, f"'{INVENTORY_TRANSACTIONS_TAB_NAME}' validated successfully."


# --- Main execution block for independent debugging ---
if __name__ == "__main__":
    print("Starting Data Validator Script...")

    # Fetch configuration first to get key SKUs
    config_success, config_msg = validate_ora_configuration(
        get_google_sheet_data_for_validator(GOOGLE_SHEET_ID, f'{ORA_CONFIGURATION_TAB_NAME}!A:F', SERVICE_ACCOUNT_KEY_PATH)
    )
    print(config_msg)
    if not config_success:
        print("ORA Configuration validation failed. Aborting further validation.")
        # Exit removed as per user instruction to avoid exiting the whole script
    
    # Extract key SKUs from the validated config data for subsequent validations
    raw_config_data = get_google_sheet_data_for_validator(GOOGLE_SHEET_ID, f'{ORA_CONFIGURATION_TAB_NAME}!A:F', SERVICE_ACCOUNT_KEY_PATH)
    key_skus_from_config = []
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
                        key_skus_from_config.append(sku)
        except Exception as e:
            print(f"Error extracting key SKUs during validation: {e}")
    key_skus_from_config = sorted(list(set(key_skus_from_config)))
    print(f"Key SKUs extracted for validation: {key_skus_from_config}")


    # Validate ORA_Weekly_Shipped_History
    weekly_history_success, weekly_history_msg = validate_weekly_shipped_history(
        get_google_sheet_data_for_validator(GOOGLE_SHEET_ID, f'{ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME}!A:E', SERVICE_ACCOUNT_KEY_PATH),
        key_skus_from_config
    )
    print(weekly_history_msg)


    # Validate Golden_Test_Data_Raw
    golden_raw_success, golden_raw_msg = validate_golden_test_data_raw(
        get_google_sheet_data_for_validator(GOOGLE_SHEET_ID, f'{GOLDEN_TEST_DATA_RAW_TAB_NAME}!A:H', SERVICE_ACCOUNT_KEY_PATH)
    )
    print(golden_raw_msg)


    # Validate Inventory_Transactions
    inventory_trans_success, inventory_trans_msg = validate_inventory_transactions(
        get_google_sheet_data_for_validator(GOOGLE_SHEET_ID, f'{INVENTORY_TRANSACTIONS_TAB_NAME}!A:D', SERVICE_ACCOUNT_KEY_PATH)
    )
    print(inventory_trans_msg)

    print("\nData Validator Script Finished.")

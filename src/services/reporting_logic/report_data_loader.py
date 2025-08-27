import pandas as pd
import logging
from config.settings import settings
from src.services.google_sheets.api_client import get_google_sheet_data
from datetime import datetime # Import datetime for parsing dates
import os # Ensure os is imported here as well for consistency
from utils.google_sheets_utils import safe_sheet_to_dataframe

logger = logging.getLogger(__name__)

def load_all_configuration_data(sheet_id: str) -> tuple | None:
    """
    Loads all necessary configuration and raw data from Google Sheets for reporting.
    """
    logger.info("Loading all configuration data...")
    raw_config_data = get_google_sheet_data(sheet_id, settings.ORA_CONFIGURATION_TAB_NAME)
    
    # --- FIX: Convert raw_config_data (list of lists) to DataFrame immediately ---
    if raw_config_data is None or (isinstance(raw_config_data, list) and not raw_config_data):
        logger.warning("No data or malformed data found in 'ORA_Configuration' worksheet. Returning default empty configuration.")
        return {}, {}, {}, [], 0, 0, datetime.now().date(), datetime.now().date(), {}
    

    # Use safe_sheet_to_dataframe for robust DataFrame construction
    config_df = safe_sheet_to_dataframe(raw_config_data)
    if config_df is None:
        logger.error(f"safe_sheet_to_dataframe returned None for ORA_Configuration. Returning empty configuration.")
        return {}, {}, {}, [], 0, 0, datetime.now().date(), datetime.now().date(), {}

    # Check if DataFrame is empty after conversion
    if config_df.empty:
        logger.warning("ORA_Configuration DataFrame is empty after conversion. Returning default empty configuration.")
        return {}, {}, {}, [], 0, 0, datetime.now().date(), datetime.now().date(), {}


    try:
        # --- FIX: Strip whitespace from column names for robustness (now on a DataFrame) ---
        config_df.columns = config_df.columns.str.strip()

        rates_df = config_df[config_df['ParameterCategory'] == 'Rates']
        rates = dict(zip(rates_df['ParameterName'], pd.to_numeric(rates_df['Value'])))

        pallet_df = config_df[config_df['ParameterCategory'] == 'PalletConfig']
        pallet_counts = dict(zip(pallet_df['SKU'].astype(str).str.strip(), pd.to_numeric(pallet_df['Value'])))

        initial_inv_df = config_df[config_df['ParameterCategory'] == 'InitialInventory']
        initial_inventory = dict(zip(initial_inv_df['SKU'].astype(str).str.strip(), pd.to_numeric(initial_inv_df['Value'])))
        
        eom_previous_month_df = config_df[config_df['ParameterCategory'] == 'Inventory'].copy()
        eom_previous_month_data = dict(zip(eom_previous_month_df['SKU'].astype(str).str.strip(), pd.to_numeric(eom_previous_month_df['Value'])))

        reporting_df = config_df[config_df['ParameterCategory'] == 'Reporting']
        year = int(reporting_df.loc[reporting_df['ParameterName'] == 'CurrentMonthlyReportYear', 'Value'].iloc[0])
        month = int(reporting_df.loc[reporting_df['ParameterName'] == 'CurrentMonthlyReportMonth', 'Value'].iloc[0])
        
        start_date_str = reporting_df.loc[reporting_df['ParameterName'] == 'CurrentWeeklyReportStartDate', 'Value'].iloc[0]
        end_date_str = reporting_df.loc[reporting_df['ParameterName'] == 'CurrentWeeklyReportEndDate', 'Value'].iloc[0]
        weekly_report_start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
        weekly_report_end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()

        key_products_df = config_df[config_df['ParameterCategory'] == 'Key Products'].copy()
        key_skus_list = key_products_df['SKU'].astype(str).str.strip().tolist()
        
        logger.info("Successfully loaded all configuration data.")
        return initial_inventory, rates, pallet_counts, key_skus_list, year, month, weekly_report_start_date, weekly_report_end_date, eom_previous_month_data

    except Exception as e:
        logger.error(f"Error processing ORA_Configuration data: {e}", exc_info=True)
        # Return default empty values to prevent TypeError on unpacking
        return {}, {}, {}, [], 0, 0, datetime.now().date(), datetime.now().date(), {}


def load_inventory_transactions(sheet_id: str) -> pd.DataFrame | None:
    """Loads and processes inventory transactions."""
    logger.info("Loading inventory transactions...")
    raw_transactions_data = get_google_sheet_data(sheet_id, settings.INVENTORY_TRANSACTIONS_TAB_NAME)
    
    # --- FIX: Convert raw_transactions_data (list of lists) to DataFrame immediately ---
    if raw_transactions_data is None or (isinstance(raw_transactions_data, list) and not raw_transactions_data):
        logger.warning("No data or malformed data found in 'Inventory_Transactions' worksheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])
    

    # Use safe_sheet_to_dataframe for robust DataFrame construction
    transactions_df = safe_sheet_to_dataframe(raw_transactions_data)

    if transactions_df.empty:
        logger.warning("Inventory_Transactions DataFrame is empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])


    transactions_df.columns = transactions_df.columns.str.strip()

    logger.debug(f"Inventory_Transactions dtypes BEFORE date conversion:\n{transactions_df.dtypes.to_string()}")
    logger.debug(f"Inventory_Transactions 'Date' column head BEFORE conversion:\n{transactions_df['Date'].head().to_string()}")

    if 'Date' in transactions_df.columns:
        transactions_df['Date'] = pd.to_datetime(transactions_df['Date'], errors='coerce')
        transactions_df.dropna(subset=['Date'], inplace=True) 
        
        logger.debug(f"Inventory_Transactions 'Date' column head AFTER conversion and dropna:\n{transactions_df['Date'].head().to_string()}")
        if transactions_df['Date'].empty:
            logger.warning("All dates in Inventory_Transactions became NaT or were empty after conversion. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])
        transactions_df['Date'] = transactions_df['Date'].dt.date # Convert to datetime.date objects for comparison
    else:
        logger.error("Missing 'Date' column in Inventory_Transactions. Cannot process transactions.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])

    transactions_df['Quantity'] = pd.to_numeric(transactions_df['Quantity'], errors='coerce').fillna(0)
    transactions_df['SKU'] = transactions_df['SKU'].astype(str).str.strip() # Ensure SKU is stripped

    logger.info(f"Successfully loaded {len(transactions_df)} inventory transactions.")
    return transactions_df

def load_shipped_items_data(sheet_id: str) -> pd.DataFrame | None:
    """Loads and processes shipped items data."""
    logger.info("Loading shipped items data...")
    raw_shipped_items_data = get_google_sheet_data(sheet_id, settings.SHIPPED_ITEMS_DATA_TAB_NAME)
    
    # --- FIX: Convert raw_shipped_items_data (list of lists) to DataFrame immediately ---
    if raw_shipped_items_data is None or (isinstance(raw_shipped_items_data, list) and not raw_shipped_items_data):
        logger.warning("No data or malformed data found in 'Shipped_Items_Data' worksheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU_Lot', 'Quantity Shipped', 'Base SKU', 'SKU'])
    

    # Use safe_sheet_to_dataframe for robust DataFrame construction
    shipped_items_df = safe_sheet_to_dataframe(raw_shipped_items_data)

    if shipped_items_df.empty:
        logger.warning("Shipped_Items_Data DataFrame is empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU_Lot', 'Quantity Shipped', 'Base SKU', 'SKU'])


    shipped_items_df.columns = shipped_items_df.columns.str.strip()

    qty_col_found = False
    for original_col in shipped_items_df.columns:
        if original_col.strip().lower() == 'quantity shipped':
            shipped_items_df['Quantity_Shipped'] = pd.to_numeric(shipped_items_df[original_col], errors='coerce').fillna(0)
            qty_col_found = True
            break
    if not qty_col_found:
        logger.error("Missing 'Quantity Shipped' column (or its variations) in Shipped_Items_Data. Cannot process shipment quantities.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    date_col_found = False
    for original_col in shipped_items_df.columns:
        stripped_original_col = original_col.strip().lower()
        if stripped_original_col == 'ship date' or stripped_original_col == 'date':
            shipped_items_df['Date'] = pd.to_datetime(shipped_items_df[original_col], errors='coerce')
            date_col_found = True
            break
    if not date_col_found:
        logger.error("Missing 'Ship Date' or 'Date' column (or its variations) in Shipped_Items_Data. Cannot process shipment dates.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    shipped_items_df.dropna(subset=['Date'], inplace=True)
    
    logger.debug(f"Shipped_Items_Data 'Date' column head AFTER conversion and dropna:\n{shipped_items_df['Date'].head().to_string()}")
    if shipped_items_df['Date'].empty:
        logger.warning("All dates in Shipped_Items_Data became NaT or were empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    logger.debug(f"Shipped_Items_Data dtypes BEFORE SKU/Quantity processing:\n{shipped_items_df.dtypes.to_string()}")
    logger.debug(f"Shipped_Items_Data head BEFORE SKU/Quantity processing:\n{shipped_items_df.head().to_string()}")
    logger.debug(f"Shipped_Items_Data value counts for 'SKU' column (if exists, from raw data usually):\n{shipped_items_df.get('SKU', pd.Series(dtype='object')).value_counts(dropna=False).to_string()}")
    logger.debug(f"Shipped_Items_Data value counts for 'SKU_Lot' column (if exists):\n{shipped_items_df.get('SKU_Lot', pd.Series(dtype='object')).value_counts(dropna=False).to_string()}")
    logger.debug(f"Shipped_Items_Data value counts for 'Base SKU' column (if exists):\n{shipped_items_df.get('Base SKU', pd.Series(dtype='object')).value_counts(dropna=False).to_string()}")

    if 'Base SKU' in shipped_items_df.columns:
        shipped_items_df.rename(columns={'Base SKU': 'SKU'}, inplace=True)
    elif 'BaseSKU_from_sheet' in shipped_items_df.columns:
        shipped_items_df.rename(columns={'BaseSKU_from_sheet': 'SKU'}, inplace=True)
    elif 'SKU_Lot' in shipped_items_df.columns:
        shipped_items_df['SKU'] = shipped_items_df['SKU_Lot'].astype(str).apply(lambda x: x.split(' - ')[0].strip()) # Ensure strip after split
        logger.warning("Derived 'SKU' from 'SKU_Lot' column in Shipped_Items_Data.")
    else:
        logger.error("Could not find a suitable 'SKU' column in Shipped_Items_Data (looked for 'Base SKU', 'BaseSKU_from_sheet', or 'SKU_Lot').")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])
    
    shipped_items_df['SKU'] = shipped_items_df['SKU'].astype(str).str.strip() # Ensure final SKU column is string and stripped
    shipped_items_df['Date'] = shipped_items_df['Date'].dt.date
    logger.info(f"Successfully loaded {len(shipped_items_df)} shipped items.")
    return shipped_items_df

def load_shipped_orders_data(sheet_id: str) -> pd.DataFrame | None:
    """Loads and processes shipped orders data."""
    logger.info("Loading shipped orders data...")
    raw_shipped_orders_data = get_google_sheet_data(sheet_id, settings.SHIPPED_ORDERS_DATA_TAB_NAME)
    
    # --- FIX: Convert raw_shipped_orders_data (list of lists) to DataFrame immediately ---
    if raw_shipped_orders_data is None or (isinstance(raw_shipped_orders_data, list) and not raw_shipped_orders_data):
        logger.warning("No data or malformed data found in 'Shipped_Orders_Data' worksheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'OrderNumber'])


    # Use safe_sheet_to_dataframe for robust DataFrame construction
    shipped_orders_df = safe_sheet_to_dataframe(raw_shipped_orders_data)

    if shipped_orders_df.empty:
        logger.warning("Shipped_Orders_Data DataFrame is empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'OrderNumber'])


    shipped_orders_df.columns = shipped_orders_df.columns.str.strip()

    if 'Ship Date' in shipped_orders_df.columns:
        shipped_orders_df['Date'] = pd.to_datetime(shipped_orders_df['Ship Date'], errors='coerce')
    elif 'Date' in shipped_orders_df.columns:
        shipped_orders_df['Date'] = pd.to_datetime(shipped_orders_df['Date'], errors='coerce')
    else:
        logger.error("Missing 'Ship Date' or 'Date' column in Shipped_Orders_Data. Cannot process order dates.")
        return pd.DataFrame(columns=['Date', 'OrderNumber'])
    
    shipped_orders_df.dropna(subset=['Date'], inplace=True)
    if shipped_orders_df['Date'].empty:
        logger.warning("All dates in Shipped_Orders_Data became NaT or were empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'OrderNumber'])

    shipped_orders_df['Date'] = shipped_orders_df['Date'].dt.date
    logger.info(f"Successfully loaded {len(shipped_orders_df)} shipped orders.")
    return shipped_orders_df

def load_weekly_shipped_history(sheet_id: str) -> pd.DataFrame | None:
    """Loads the weekly shipped history from Google Sheets."""
    logger.info("Loading weekly shipped history...")
    raw_data = get_google_sheet_data(sheet_id, settings.ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME) 
    if raw_data is not None:
        logging.debug(f"Raw data from ORA_Weekly_Shipped_History (first 5 rows):\n{raw_data[:5]}")
        # Continue with the rest of your logic that uses raw_data
    else:
        # Handle the error case gracefully, for example, by logging a warning.
        logging.warning("Failed to retrieve weekly shipped history data. The function returned None.")

    # Initialize df to ensure it's always defined before its first use outside the initial raw_data processing blocks.
    # This empty DataFrame will be returned if raw_data is invalid or empty after processing.
    df = pd.DataFrame(columns=['Date', 'SKU', 'ShippedQuantity']) 

    # --- FIX: Convert raw_data (list of lists) to DataFrame immediately ---
    # This block ensures raw_data is processed, or df remains an empty DataFrame
    if raw_data is None or (isinstance(raw_data, list) and not raw_data):
        logger.warning("No data or malformed data found in 'ORA_Weekly_Shipped_History' sheet. Returning empty DataFrame.")
        return df # Return the already initialized df
    

    # Use safe_sheet_to_dataframe for robust DataFrame construction
    df = safe_sheet_to_dataframe(raw_data)

    # This 'if df.empty:' check is now safe because df is guaranteed to be defined.
    # The warning message is also updated per prior request.
    if df.empty: 
        logger.warning("ORA_Weekly_Shipped_History DataFrame is empty after conversion. Returning empty DataFrame.")
        return df # Return the defined df

    df.columns = df.columns.str.strip() # Strip whitespace from column names

    # --- UPDATED: Use 'Start Date' and 'Stop Date' as id_vars ---
    id_vars = ['Start Date', 'Stop Date'] 
    
    if not all(col in df.columns for col in id_vars):
        logger.error(f"Missing expected ID columns '{id_vars}' in 'ORA_Weekly_Shipped_History' data. Available columns: {df.columns.tolist()}")
        # This return should also be df for consistency if it's meant to be empty.
        return df # Changed to return df for consistency

    value_vars = [col for col in df.columns if col not in id_vars]
    
    if not value_vars:
        logger.warning(f"No SKU columns found in 'ORA_Weekly_Shipped_History' to melt. Available columns: {df.columns.tolist()}")
        # This return should also be df for consistency if it's meant to be empty.
        return df # Changed to return df for consistency

    # Perform the melt operation
    long_df = pd.melt(df, id_vars=id_vars, value_vars=value_vars, var_name='SKU', value_name='ShippedQuantity')


    # --- UPDATED: Directly convert 'Stop Date' to 'Date' column ---
    # Convert new 'Start Date' and 'Stop Date' columns to datetime objects
    long_df['Start_Date_Parsed'] = pd.to_datetime(long_df['Start Date'], errors='coerce').dt.date
    long_df['Stop_Date_Parsed'] = pd.to_datetime(long_df['Stop Date'], errors='coerce').dt.date

    # Rename 'Stop_Date_Parsed' to 'Date' for consistency with downstream functions
    long_df.rename(columns={'Stop_Date_Parsed': 'Date'}, inplace=True)
    
    initial_rows = len(long_df)
    # Drop rows where either Start Date or Stop Date failed to parse
    rows_to_drop_filter = long_df['Start_Date_Parsed'].isna() | long_df['Date'].isna()
    logging.debug(f"DataFrame before dropping NaT dates:\n{long_df[rows_to_drop_filter].to_string()}")
    rows_to_drop = long_df[rows_to_drop_filter].copy() # Capture rows before dropping
    long_df.dropna(subset=['Start_Date_Parsed', 'Date'], inplace=True)
    
    if len(long_df) < initial_rows:
        logger.warning(f"Dropped {initial_rows - len(long_df)} rows from ORA_Weekly_Shipped_History due to unparsable Start/Stop Dates.")
        # New debug line to display the entire dropped rows' data
        logger.debug(f"Details of dropped rows:\n{rows_to_drop.to_string()}")
        # Existing debug lines for problematic raw dates (optional to keep, as the full row provides more info)
        logger.debug(f"Problematic raw Start Dates: {rows_to_drop['Start Date'].unique().tolist()}")
        logger.debug(f"Problematic raw Stop Dates: {rows_to_drop['Stop Date'].unique().tolist()}")


    if long_df.empty:
        logger.warning("ORA_Weekly_Shipped_History became empty after date parsing and dropping invalid dates. Cannot calculate rolling average.")
        # This return should also be df for consistency if it's meant to be empty.
        return df # Changed to return df for consistency

    long_df['ShippedQuantity'] = pd.to_numeric(long_df['ShippedQuantity'].replace('', 0)).fillna(0)
    long_df['SKU'] = long_df['SKU'].astype(str).str.strip()

    if not all(col in long_df.columns for col in ['Date', 'SKU', 'ShippedQuantity']):
        logger.error(f"Final DataFrame from ORA_Weekly_Shipped_History is missing essential columns after processing. Columns: {long_df.columns.tolist()}")
        # This return should also be df for consistency if it's meant to be empty.
        return df # Changed to return df for consistency

    logger.info(f"Successfully loaded and unpivoted weekly shipped history. Resulting DataFrame shape: {long_df.shape}")
    logger.debug(f"Weekly shipped history final DataFrame head:\n{long_df.head().to_string()}")
    logger.debug(f"Weekly shipped history final DataFrame dtypes:\n{long_df.dtypes.to_string()}")
    
    return long_df

def load_product_names_map(sheet_id: str) -> pd.DataFrame | None:
    """
    Loads SKU to Product name mapping from a Google Sheet.
    Returns a DataFrame with 'SKU' and 'Product' columns.
    """
    logger.info("Loading product names map...")
    try:
        raw_data = get_google_sheet_data(sheet_id, settings.ORA_CONFIGURATION_TAB_NAME)
        logger.debug(f"Raw data from ORA_Configuration for product names: {raw_data[:2] if isinstance(raw_data, list) else type(raw_data)}")

        # --- FIX: Convert raw_data (list of lists) to DataFrame immediately ---
        if raw_data is None or (isinstance(raw_data, list) and not raw_data):
            logger.warning("No data or malformed data found in 'ORA_Configuration' worksheet for product names map. Returning empty DataFrame.")
            return pd.DataFrame(columns=['SKU', 'Product'])

        # Use safe_sheet_to_dataframe for robust DataFrame construction
        df = safe_sheet_to_dataframe(raw_data)

        if df.empty:
            logger.warning("ORA_Configuration DataFrame is empty after conversion. Returning empty DataFrame.")
            return pd.DataFrame(columns=['SKU', 'Product'])

        df.columns = df.columns.str.strip()

        logger.debug(f"DataFrame columns from ORA_Configuration after strip(): {df.columns.tolist()}")
        logger.debug(f"DataFrame head from ORA_Configuration for product names:\n{df.head().to_string()}")

        key_products_df = df[df['ParameterCategory'] == 'Key Products'].copy()

        if 'SKU' in key_products_df.columns and 'ParameterName' in key_products_df.columns:
            df_filtered = key_products_df[['SKU', 'ParameterName']].copy()
            df_filtered.rename(columns={'ParameterName': 'Product'}, inplace=True)
            df_filtered['SKU'] = df_filtered['SKU'].astype(str).str.strip() # Ensure SKU is string type and stripped
            logger.info(f"Successfully loaded product names map from ORA_Configuration. Shape: {df_filtered.shape}")
            return df_filtered # Return DataFrame
        else:
            logger.error(f"Missing expected 'SKU' or 'ParameterName' columns in 'ORA_Configuration' for 'Key Products' category. Found columns in filtered data: {key_products_df.columns.tolist()}")
            return pd.DataFrame(columns=['SKU', 'Product']) # Return empty DataFrame on error

    except Exception as e:
        logger.error(f"Error loading product names map: {e}", exc_info=True)
        return None

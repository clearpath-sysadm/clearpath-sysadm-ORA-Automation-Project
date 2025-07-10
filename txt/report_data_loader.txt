import pandas as pd
import logging
from config.settings import settings
from src.services.google_sheets.api_client import get_google_sheet_data
from datetime import datetime # Import datetime for parsing dates
import os # Ensure os is imported here as well for consistency

logger = logging.getLogger(__name__)

def load_all_configuration_data(sheet_id: str) -> tuple | None:
    """
    Loads all necessary configuration and raw data from Google Sheets for reporting.
    """
    logger.info("Loading all configuration data...")
    config_df = get_google_sheet_data(sheet_id, settings.ORA_CONFIGURATION_TAB_NAME)
    # --- FIX: Robustly check for empty/invalid config_df immediately ---
    if config_df is None or (isinstance(config_df, pd.DataFrame) and config_df.empty) or (isinstance(config_df, list) and not config_df):
        logger.warning("No data or malformed data found in 'ORA_Configuration' worksheet. Returning None.")
        return None

    try:
        # --- FIX: Strip whitespace from column names for robustness ---
        config_df.columns = config_df.columns.str.strip()

        rates_df = config_df[config_df['ParameterCategory'] == 'Rates']
        rates = dict(zip(rates_df['ParameterName'], pd.to_numeric(rates_df['Value'])))

        pallet_df = config_df[config_df['ParameterCategory'] == 'PalletConfig']
        pallet_counts = dict(zip(pallet_df['SKU'].astype(str), pd.to_numeric(pallet_df['Value'])))

        initial_inv_df = config_df[config_df['ParameterCategory'] == 'InitialInventory']
        initial_inventory = dict(zip(initial_inv_df['SKU'].astype(str), pd.to_numeric(initial_inv_df['Value'])))
        
        # Load EomPreviousMonth data
        eom_previous_month_df = config_df[config_df['ParameterCategory'] == 'Inventory'].copy()
        # Ensure SKU is string and Value is numeric for EomPreviousMonth values
        eom_previous_month_data = dict(zip(eom_previous_month_df['SKU'].astype(str), pd.to_numeric(eom_previous_month_df['Value'])))

        # Ensure current_report_year and current_report_month are always returned
        reporting_df = config_df[config_df['ParameterCategory'] == 'Reporting']
        year = int(reporting_df.loc[reporting_df['ParameterName'] == 'CurrentMonthlyReportYear', 'Value'].iloc[0])
        month = int(reporting_df.loc[reporting_df['ParameterName'] == 'CurrentMonthlyReportMonth', 'Value'].iloc[0])
        
        # Get weekly report dates
        start_date_str = reporting_df.loc[reporting_df['ParameterName'] == 'CurrentWeeklyReportStartDate', 'Value'].iloc[0]
        end_date_str = reporting_df.loc[reporting_df['ParameterName'] == 'CurrentWeeklyReportEndDate', 'Value'].iloc[0]
        weekly_report_start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
        weekly_report_end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()

        # --- OLD: key_skus_list was also providing product names in the original sheet, but was causing issues.
        # This list determines which SKUs are tracked in the monthly report columns.
        key_products_df = config_df[config_df['ParameterCategory'] == 'Key Products'].copy()
        key_skus_list = key_products_df['SKU'].astype(str).tolist()
        
        logger.info("Successfully loaded all configuration data.")
        return initial_inventory, rates, pallet_counts, key_skus_list, year, month, weekly_report_start_date, weekly_report_end_date, eom_previous_month_data

    except Exception as e:
        logger.error(f"Error loading all configuration data: {e}", exc_info=True)
        return None

def load_inventory_transactions(sheet_id: str) -> pd.DataFrame | None:
    """Loads and processes inventory transactions."""
    logger.info("Loading inventory transactions...")
    transactions_df = get_google_sheet_data(sheet_id, settings.INVENTORY_TRANSACTIONS_TAB_NAME)
    # --- FIX: Robustly check for empty/invalid raw_data immediately ---
    if transactions_df is None or (isinstance(transactions_df, pd.DataFrame) and transactions_df.empty) or (isinstance(transactions_df, list) and not transactions_df):
        logger.warning("No data or malformed data found in 'Inventory_Transactions' worksheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])

    # --- FIX: Strip whitespace from column names for robustness ---
    transactions_df.columns = transactions_df.columns.str.strip()

    # --- Robust Date Conversion for Inventory Transactions ---
    logger.debug(f"Inventory_Transactions dtypes BEFORE date conversion:\n{transactions_df.dtypes.to_string()}")
    logger.debug(f"Inventory_Transactions 'Date' column head BEFORE conversion:\n{transactions_df['Date'].head().to_string()}")

    if 'Date' in transactions_df.columns:
        transactions_df['Date'] = pd.to_datetime(transactions_df['Date'], errors='coerce')
        # Drop rows where Date conversion failed (NaT)
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
    
    logger.info(f"Successfully loaded {len(transactions_df)} inventory transactions.")
    return transactions_df

def load_shipped_items_data(sheet_id: str) -> pd.DataFrame | None:
    """Loads and processes shipped items data."""
    logger.info("Loading shipped items data...")
    shipped_items_df = get_google_sheet_data(sheet_id, settings.SHIPPED_ITEMS_DATA_TAB_NAME)
    # --- FIX: Robustly check for empty/invalid raw_data immediately ---
    if shipped_items_df is None or (isinstance(shipped_items_df, pd.DataFrame) and shipped_items_df.empty) or (isinstance(shipped_items_df, list) and not shipped_items_df):
        logger.warning("No data or malformed data found in 'Shipped_Items_Data' worksheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU_Lot', 'Quantity Shipped', 'Base SKU', 'SKU']) # Added 'Base SKU' to column list for robustness

    # --- FIX: Strip whitespace from column names for robustness ---
    shipped_items_df.columns = shipped_items_df.columns.str.strip()

    # --- FIX: Ultra-robust column matching for Quantity and Date ---
    # Convert all column names to stripped lowercase for robust comparison
    stripped_cols = [col.strip().lower() for col in shipped_items_df.columns]

    # Find the Quantity Shipped column
    qty_col_found = False
    for original_col in shipped_items_df.columns:
        if original_col.strip().lower() == 'quantity shipped': # Compare stripped/lowercased version
            shipped_items_df['Quantity_Shipped'] = pd.to_numeric(shipped_items_df[original_col], errors='coerce').fillna(0)
            qty_col_found = True
            break
    if not qty_col_found:
        logger.error("Missing 'Quantity Shipped' column (or its variations) in Shipped_Items_Data. Cannot process shipment quantities.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    # Find the Date column
    date_col_found = False
    for original_col in shipped_items_df.columns:
        stripped_original_col = original_col.strip().lower()
        if stripped_original_col == 'ship date' or stripped_original_col == 'date': # Check for both 'Ship Date' and 'Date'
            shipped_items_df['Date'] = pd.to_datetime(shipped_items_df[original_col], errors='coerce')
            date_col_found = True
            break
    if not date_col_found:
        logger.error("Missing 'Ship Date' or 'Date' column (or its variations) in Shipped_Items_Data. Cannot process shipment dates.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    # Drop rows where Date conversion failed (NaT)
    shipped_items_df.dropna(subset=['Date'], inplace=True)
    
    logger.debug(f"Shipped_Items_Data 'Date' column head AFTER conversion and dropna:\n{shipped_items_df['Date'].head().to_string()}")
    if shipped_items_df['Date'].empty:
        logger.warning("All dates in Shipped_Items_Data became NaT or were empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    # Add this debug block BEFORE the SKU derivation logic
    logger.debug(f"Shipped_Items_Data dtypes BEFORE SKU/Quantity processing:\n{shipped_items_df.dtypes.to_string()}")
    logger.debug(f"Shipped_Items_Data head BEFORE SKU/Quantity processing:\n{shipped_items_df.head().to_string()}")
    logger.debug(f"Shipped_Items_Data value counts for 'SKU' column (if exists, from raw data usually):\n{shipped_items_df.get('SKU', pd.Series(dtype='object')).value_counts(dropna=False).to_string()}")
    logger.debug(f"Shipped_Items_Data value counts for 'SKU_Lot' column (if exists):\n{shipped_items_df.get('SKU_Lot', pd.Series(dtype='object')).value_counts(dropna=False).to_string()}")
    logger.debug(f"Shipped_Items_Data value counts for 'Base SKU' column (if exists):\n{shipped_items_df.get('Base SKU', pd.Series(dtype='object')).value_counts(dropna=False).to_string()}")

    # Attempt to derive 'SKU' if 'Base SKU' exists, otherwise use 'SKU_Lot' if that's the real SKU
    if 'Base SKU' in shipped_items_df.columns: # This refers to 'Base SKU' directly from the sheet
        shipped_items_df.rename(columns={'Base SKU': 'SKU'}, inplace=True) # Standardize to 'SKU'
    elif 'BaseSKU_from_sheet' in shipped_items_df.columns: # This was a specific internal column name if a sheet had it
        shipped_items_df.rename(columns={'BaseSKU_from_sheet': 'SKU'}, inplace=True)
    elif 'SKU_Lot' in shipped_items_df.columns:
        # Fallback if no specific Base SKU column, extract SKU from SKU_Lot if formatted "SKU - Lot"
        shipped_items_df['SKU'] = shipped_items_df['SKU_Lot'].apply(lambda x: str(x).split(' - ')[0])
        logger.warning("Derived 'SKU' from 'SKU_Lot' column in Shipped_Items_Data.")
    else:
        logger.error("Could not find a suitable 'SKU' column in Shipped_Items_Data (looked for 'Base SKU', 'BaseSKU_from_sheet', or 'SKU_Lot').")
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped']) # Return empty if critical column missing
    
    # Ensure final SKU column is string type for consistency
    shipped_items_df['SKU'] = shipped_items_df['SKU'].astype(str)

# Add this debug block AFTER the SKU derivation logic
    logger.debug(f"Shipped_Items_Data dtypes AFTER SKU derivation:\n{shipped_items_df.dtypes.to_string()}")
    logger.debug(f"Shipped_Items_Data head AFTER SKU derivation:\n{shipped_items_df.head().to_string()}")
    logger.debug(f"Shipped_Items_Data 'SKU' column value counts AFTER derivation:\n{shipped_items_df['SKU'].value_counts(dropna=False).to_string()}")
    logger.debug(f"Shipped_Items_Data missing values in 'SKU' column AFTER derivation:\n{shipped_items_df['SKU'].isnull().sum()}")

    shipped_items_df['Date'] = shipped_items_df['Date'].dt.date # Convert to datetime.date objects for comparison
    logger.info(f"Successfully loaded {len(shipped_items_df)} shipped items.")
    return shipped_items_df

def load_shipped_orders_data(sheet_id: str) -> pd.DataFrame | None:
    """Loads and processes shipped orders data."""
    logger.info("Loading shipped orders data...")
    shipped_orders_df = get_google_sheet_data(sheet_id, settings.SHIPPED_ORDERS_DATA_TAB_NAME)
    # --- FIX: Robustly check for empty/invalid raw_data immediately ---
    if shipped_orders_df is None or (isinstance(shipped_orders_df, pd.DataFrame) and shipped_orders_df.empty) or (isinstance(shipped_orders_df, list) and not shipped_orders_df):
        logger.warning("No data or malformed data found in 'Shipped_Orders_Data' worksheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'OrderNumber'])

    # --- FIX: Strip whitespace from column names for robustness ---
    shipped_orders_df.columns = shipped_orders_df.columns.str.strip()

    # --- FIX: Handle 'Ship Date' -> 'Date' for orders ---
    if 'Ship Date' in shipped_orders_df.columns:
        shipped_orders_df['Date'] = pd.to_datetime(shipped_orders_df['Ship Date'], errors='coerce')
    elif 'Date' in shipped_orders_df.columns:
        shipped_orders_df['Date'] = pd.to_datetime(shipped_orders_df['Date'], errors='coerce')
    else:
        logger.error("Missing 'Ship Date' or 'Date' column in Shipped_Orders_Data. Cannot process order dates.")
        return pd.DataFrame(columns=['Date', 'OrderNumber']) # Return empty if critical column missing
    
    shipped_orders_df.dropna(subset=['Date'], inplace=True) # Drop rows where date conversion failed (NaT)
    if shipped_orders_df['Date'].empty:
        logger.warning("All dates in Shipped_Orders_Data became NaT or were empty after conversion. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'OrderNumber'])

    shipped_orders_df['Date'] = shipped_orders_df['Date'].dt.date # Convert to datetime.date objects for consistency
    logger.info(f"Successfully loaded {len(shipped_orders_df)} shipped orders.")
    return shipped_orders_df

def load_weekly_shipped_history(sheet_id: str) -> pd.DataFrame | None:
    """Loads the weekly shipped history from Google Sheets."""
    logger.info("Loading weekly shipped history...")
    raw_data = get_google_sheet_data(sheet_id, settings.ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME) 
    
    # --- FIX for KeyError: 0 and DateParseError ---
    # Robustly handle raw_data being list of lists or DataFrame
    if isinstance(raw_data, list) and len(raw_data) > 1:
        headers = raw_data[0]
        data = raw_data[1:]
        df = pd.DataFrame(data, columns=headers)
    elif isinstance(raw_data, pd.DataFrame):
        df = raw_data # raw_data is already a DataFrame
    # --- FIX: Handle raw_data being False or other non-iterable types ---
    elif isinstance(raw_data, bool) and not raw_data: # Explicitly check for False returned by get_google_sheet_data
        logger.warning("get_google_sheet_data returned False for 'ORA_Weekly_Shipped_History' sheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'ShippedQuantity'])
    else:
        logger.warning("No data or malformed data found in 'ORA_Weekly_Shipped_History' sheet. Returning empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'SKU', 'ShippedQuantity'])

    # --- FIX: Strip whitespace from column names for robustness ---
    df.columns = df.columns.str.strip()

    # --- Apply previous melting and date parsing logic ---
    id_vars = ['Ship Week'] 
    value_vars = [col for col in df.columns if col not in id_vars]
    
    if id_vars[0] not in df.columns:
        logger.error(f"Missing expected ID column '{id_vars[0]}' in 'ORA_Weekly_Shipped_History' data after initial load.")
        return pd.DataFrame(columns=['Date', 'SKU', 'ShippedQuantity']) # Return empty on critical column missing

    long_df = pd.melt(df, id_vars=id_vars, value_vars=value_vars, var_name='SKU', value_name='ShippedQuantity')

    long_df.rename(columns={'Ship Week': 'Date'}, inplace=True) # Rename Ship Week to Date
    long_df['ShippedQuantity'] = pd.to_numeric(long_df['ShippedQuantity'].replace('', 0)).fillna(0)
    
    # Extract the end date from the 'Date' (originally 'Ship Week') string
    long_df['Date'] = pd.to_datetime(long_df['Date'].astype(str).str.split(' - ').str[1], errors='coerce')
    
    long_df.dropna(subset=['Date'], inplace=True)
    long_df['SKU'] = long_df['SKU'].astype(str) # Ensure SKU is string type

    logger.info(f"Successfully loaded and unpivoted weekly shipped history. Resulting DataFrame shape: {long_df.shape}")
    return long_df

def load_product_names_map(sheet_id: str) -> pd.DataFrame | None:
    """
    Loads SKU to Product name mapping from a Google Sheet.
    Assumes a sheet named 'SKU_Lot' with columns 'SKU' and 'Product Name'.
    """
    logger.info("Loading product names map...")
    try:
        raw_data = get_google_sheet_data(sheet_id, settings.ORA_CONFIGURATION_TAB_NAME) # Changed to ORA_CONFIGURATION_TAB_NAME
        
        # --- NEW DEBUG ---
        logger.debug(f"Raw data from ORA_Configuration for product names: {raw_data[:2] if isinstance(raw_data, list) else type(raw_data)}")
        # --- END NEW DEBUG ---

        if raw_data is None or (isinstance(raw_data, pd.DataFrame) and raw_data.empty) or (isinstance(raw_data, list) and not raw_data) or isinstance(raw_data, bool):
            logger.warning("No data or malformed data found in 'ORA_Configuration' worksheet for product names map. Returning empty DataFrame.")
            return pd.DataFrame(columns=['SKU', 'Product'])

        if isinstance(raw_data, list) and len(raw_data) > 0:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
        elif isinstance(raw_data, pd.DataFrame):
            df = raw_data
        else:
            logger.warning("Raw data for ORA_Configuration is malformed. Returning empty DataFrame.")
            return pd.DataFrame(columns=['SKU', 'Product'])
        
        df.columns = df.columns.str.strip()

        # --- NEW DEBUG ---
        logger.debug(f"DataFrame columns from ORA_Configuration after strip(): {df.columns.tolist()}")
        logger.debug(f"DataFrame head from ORA_Configuration for product names:\n{df.head().to_string()}")
        # --- END NEW DEBUG ---

        # Ensure 'ParameterCategory' is 'Key Products', then map 'SKU' to 'ParameterName' as 'Product'
        key_products_df = df[df['ParameterCategory'] == 'Key Products'].copy()

        if 'SKU' in key_products_df.columns and 'ParameterName' in key_products_df.columns:
            df_filtered = key_products_df[['SKU', 'ParameterName']].copy()
            df_filtered.rename(columns={'ParameterName': 'Product'}, inplace=True)
            df_filtered['SKU'] = df_filtered['SKU'].astype(str) # Ensure SKU is string type
            logger.info(f"Successfully loaded product names map from ORA_Configuration. Shape: {df_filtered.shape}")
            return df_filtered
        else:
            logger.error(f"Missing expected 'SKU' or 'ParameterName' columns in 'ORA_Configuration' for 'Key Products' category. Found columns in filtered data: {key_products_df.columns.tolist()}")
            return pd.DataFrame(columns=['SKU', 'Product'])

    except Exception as e:
        logger.error(f"Error loading product names map: {e}", exc_info=True)
        return None
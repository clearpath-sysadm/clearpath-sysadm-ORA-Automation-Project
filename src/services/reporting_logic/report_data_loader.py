import pandas as pd
import logging
from config.settings import settings
from src.services.google_sheets.api_client import get_google_sheet_data
from datetime import datetime

logger = logging.getLogger(__name__)

def _convert_raw_to_dataframe(raw_data: list, sheet_name: str, expected_columns: list = None) -> pd.DataFrame | None:
    """
    Helper function to convert raw list-of-lists data from Google Sheets into a Pandas DataFrame.
    Handles cases where data is empty or malformed.
    """
    if not raw_data or len(raw_data) < 1:
        logger.warning({"message": "No raw data found or data is empty.", "sheet_name": sheet_name})
        if expected_columns:
            return pd.DataFrame(columns=expected_columns)
        return pd.DataFrame() # Return empty DataFrame if no expected columns

    headers = raw_data[0]
    data_rows = raw_data[1:]

    # Ensure headers are strings and strip whitespace
    headers = [str(h).strip() for h in headers]

    df = pd.DataFrame(data_rows, columns=headers)
    df.columns = df.columns.str.strip() # Strip column names again after DataFrame creation

    # Optional: Check for expected columns if provided
    if expected_columns:
        # Check for case-insensitive and stripped matches
        df_columns_lower_stripped = [col.lower().strip() for col in df.columns]
        missing_cols = []
        for expected_col in expected_columns:
            if expected_col.lower().strip() not in df_columns_lower_stripped:
                missing_cols.append(expected_col)

        if missing_cols:
            logger.error({
                "message": "Missing expected columns in sheet data.",
                "sheet_name": sheet_name,
                "missing_columns": missing_cols,
                "available_columns": df.columns.tolist()
            })
            # Return empty DataFrame with expected columns if critical ones are missing
            return pd.DataFrame(columns=expected_columns)
            
    logger.debug({"message": "Successfully converted raw data to DataFrame.", "sheet_name": sheet_name, "shape": str(df.shape)})
    return df


def load_all_configuration_data(sheet_id: str) -> tuple | None:
    """
    Loads all necessary configuration and raw data from Google Sheets for reporting.
    """
    logger.info({"message": "Loading all configuration data from ORA_Configuration sheet."})
    
    raw_config_data = get_google_sheet_data(sheet_id, settings.ORA_CONFIGURATION_TAB_NAME)
    
    # Log raw data after fetching
    logger.debug({"message": "Raw data received from Google Sheet", "sheet": settings.ORA_CONFIGURATION_TAB_NAME, "raw_data_head": raw_config_data[:5] if isinstance(raw_config_data, list) else str(raw_config_data)})

    config_df = _convert_raw_to_dataframe(raw_config_data, settings.ORA_CONFIGURATION_TAB_NAME)

    if config_df is None or config_df.empty:
        logger.critical({"message": "No data or malformed data found in 'ORA_Configuration' worksheet after conversion. Cannot load configuration.", "sheet_id": sheet_id})
        return None # Critical failure, return None as this data is essential

    try:
        # Rates
        rates_df = config_df[config_df['ParameterCategory'] == 'Rates'].copy()
        rates = dict(zip(rates_df['ParameterName'], pd.to_numeric(rates_df['Value'], errors='coerce').fillna(0)))

        # Pallet Config
        pallet_df = config_df[config_df['ParameterCategory'] == 'PalletConfig'].copy()
        pallet_counts = dict(zip(pallet_df['SKU'].astype(str), pd.to_numeric(pallet_df['Value'], errors='coerce').fillna(0)))

        # Initial Inventory (for Weekly Report - EOD_Prior_Week)
        initial_inv_df = config_df[config_df['ParameterCategory'] == 'InitialInventory'].copy()
        initial_inventory = dict(zip(initial_inv_df['SKU'].astype(str), pd.to_numeric(initial_inv_df['Value'], errors='coerce').fillna(0)))
        
        # EomPreviousMonth data (for Monthly Report)
        eom_previous_month_df = config_df[config_df['ParameterCategory'] == 'Inventory'].copy()
        eom_previous_month_data = dict(zip(eom_previous_month_df['SKU'].astype(str), pd.to_numeric(eom_previous_month_df['Value'], errors='coerce').fillna(0)))

        # Reporting Dates
        reporting_df = config_df[config_df['ParameterCategory'] == 'Reporting'].copy()
        
        current_report_year = int(reporting_df.loc[reporting_df['ParameterName'] == 'CurrentMonthlyReportYear', 'Value'].iloc[0])
        current_report_month = int(reporting_df.loc[reporting_df['ParameterName'] == 'CurrentMonthlyReportMonth', 'Value'].iloc[0])
        
        start_date_str = reporting_df.loc[reporting_df['ParameterName'] == 'CurrentWeeklyReportStartDate', 'Value'].iloc[0]
        end_date_str = reporting_df.loc[reporting_df['ParameterName'] == 'CurrentWeeklyReportEndDate', 'Value'].iloc[0]
        
        weekly_report_start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
        weekly_report_end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()

        # Key SKUs List
        key_products_df = config_df[config_df['ParameterCategory'] == 'Key Products'].copy()
        key_skus_list = key_products_df['SKU'].astype(str).tolist()
        
        logger.info({"message": "Successfully loaded all configuration data.", "config_items_count": len(config_df)})
        return (initial_inventory, rates, pallet_counts, key_skus_list,
                current_report_year, current_report_month,
                weekly_report_start_date, weekly_report_end_date,
                eom_previous_month_data)

    except Exception as e:
        logger.critical({"message": "Error processing configuration data from ORA_Configuration.", "error": str(e)}, exc_info=True)
        return None # Critical failure if config processing fails

def load_inventory_transactions(sheet_id: str) -> pd.DataFrame:
    """Loads and processes inventory transactions."""
    logger.info({"message": "Loading inventory transactions from Google Sheet."})
    
    raw_transactions_data = get_google_sheet_data(sheet_id, settings.INVENTORY_TRANSACTIONS_TAB_NAME)
    
    # Log raw data after fetching
    logger.debug({"message": "Raw data received from Google Sheet", "sheet": settings.INVENTORY_TRANSACTIONS_TAB_NAME, "raw_data_head": raw_transactions_data[:5] if isinstance(raw_transactions_data, list) else str(raw_transactions_data)})

    transactions_df = _convert_raw_to_dataframe(raw_transactions_data, settings.INVENTORY_TRANSACTIONS_TAB_NAME, 
                                                expected_columns=['Date', 'SKU', 'Quantity', 'TransactionType'])

    if transactions_df is None or transactions_df.empty:
        logger.warning({"message": "No data or malformed data found in 'Inventory_Transactions' worksheet after conversion. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])

    # Robust Date Conversion for Inventory Transactions
    if 'Date' in transactions_df.columns:
        transactions_df['Date'] = pd.to_datetime(transactions_df['Date'], errors='coerce')
        transactions_df.dropna(subset=['Date'], inplace=True) 
        
        if transactions_df['Date'].empty:
            logger.warning({"message": "All dates in Inventory_Transactions became NaT or were empty after conversion. Returning empty DataFrame."})
            return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])
        transactions_df['Date'] = transactions_df['Date'].dt.date # Convert to datetime.date objects for comparison
    else:
        logger.error({"message": "Missing 'Date' column in Inventory_Transactions. Cannot process transactions.", "available_columns": transactions_df.columns.tolist()})
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType'])

    transactions_df['Quantity'] = pd.to_numeric(transactions_df['Quantity'], errors='coerce').fillna(0)
    
    logger.info({"message": "Successfully loaded inventory transactions.", "rows_count": len(transactions_df)})
    return transactions_df

def load_shipped_items_data(sheet_id: str) -> pd.DataFrame:
    """Loads and processes shipped items data."""
    logger.info({"message": "Loading shipped items data from Google Sheet."})
    
    raw_shipped_items_data = get_google_sheet_data(sheet_id, settings.SHIPPED_ITEMS_DATA_TAB_NAME)
    
    # Log raw data after fetching
    logger.debug({"message": "Raw data received from Google Sheet", "sheet": settings.SHIPPED_ITEMS_DATA_TAB_NAME, "raw_data_head": raw_shipped_items_data[:5] if isinstance(raw_shipped_items_data, list) else str(raw_shipped_items_data)})

    # CORRECTED: Adjust expected_columns to match actual sheet headers
    shipped_items_df = _convert_raw_to_dataframe(raw_shipped_items_data, settings.SHIPPED_ITEMS_DATA_TAB_NAME,
                                                 expected_columns=['Ship Date', 'SKU - Lot', 'Quantity Shipped', 'Base SKU'])

    if shipped_items_df is None or shipped_items_df.empty:
        logger.warning({"message": "No data or malformed data found in 'Shipped_Items_Data' worksheet after conversion. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'SKU_Lot', 'Quantity Shipped', 'Base SKU', 'SKU']) # Keep original return columns for consistency downstream

    # --- FIX: Ultra-robust column matching for Quantity and Date ---
    # Standardize column names for internal use after conversion
    # Ensure 'Ship Date' becomes 'Date' and 'SKU - Lot' becomes 'SKU_Lot'
    # 'Quantity Shipped' becomes 'Quantity_Shipped'
    column_mapping = {
        'Ship Date': 'Date',
        'SKU - Lot': 'SKU_Lot',
        'Quantity Shipped': 'Quantity_Shipped',
        'Base SKU': 'Base SKU' # Keep as is or rename to 'SKU' later
    }
    shipped_items_df.rename(columns=column_mapping, inplace=True)
    
    # Check for presence of critical columns after renaming
    if 'Quantity_Shipped' not in shipped_items_df.columns:
        logger.error({"message": "Missing 'Quantity_Shipped' column after renaming in Shipped_Items_Data. Cannot process shipment quantities.", "available_columns": shipped_items_df.columns.tolist()})
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])
    
    if 'Date' not in shipped_items_df.columns:
        logger.error({"message": "Missing 'Date' column after renaming in Shipped_Items_Data. Cannot process shipment dates.", "available_columns": shipped_items_df.columns.tolist()})
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    shipped_items_df['Quantity_Shipped'] = pd.to_numeric(shipped_items_df['Quantity_Shipped'], errors='coerce').fillna(0)
    shipped_items_df['Date'] = pd.to_datetime(shipped_items_df['Date'], errors='coerce')

    shipped_items_df.dropna(subset=['Date'], inplace=True)
    
    if shipped_items_df['Date'].empty:
        logger.warning({"message": "All dates in Shipped_Items_Data became NaT or were empty after conversion. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])

    # Attempt to derive 'SKU' if 'Base SKU' exists, otherwise use 'SKU_Lot' if that's the real SKU
    if 'Base SKU' in shipped_items_df.columns:
        shipped_items_df.rename(columns={'Base SKU': 'SKU'}, inplace=True)
    elif 'SKU_Lot' in shipped_items_df.columns: # Use SKU_Lot if Base SKU is not present
        shipped_items_df['SKU'] = shipped_items_df['SKU_Lot'].apply(lambda x: str(x).split(' - ')[0])
        logger.warning({"message": "Derived 'SKU' from 'SKU_Lot' column in Shipped_Items_Data."})
    else:
        logger.error({"message": "Could not find a suitable 'SKU' column in Shipped_Items_Data (looked for 'Base SKU' or 'SKU_Lot')."})
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity_Shipped'])
    
    shipped_items_df['SKU'] = shipped_items_df['SKU'].astype(str)

    shipped_items_df['Date'] = shipped_items_df['Date'].dt.date
    logger.info({"message": "Successfully loaded shipped items.", "rows_count": len(shipped_items_df)})
    return shipped_items_df

def load_shipped_orders_data(sheet_id: str) -> pd.DataFrame:
    """Loads and processes shipped orders data."""
    logger.info({"message": "Loading shipped orders data from Google Sheet."})
    
    raw_shipped_orders_data = get_google_sheet_data(sheet_id, settings.SHIPPED_ORDERS_DATA_TAB_NAME)
    
    # Log raw data after fetching
    logger.debug({"message": "Raw data received from Google Sheet", "sheet": settings.SHIPPED_ORDERS_DATA_TAB_NAME, "raw_data_head": raw_shipped_orders_data[:5] if isinstance(raw_shipped_orders_data, list) else str(raw_shipped_orders_data)})

    # CORRECTED: Adjust expected_columns to match actual sheet headers
    shipped_orders_df = _convert_raw_to_dataframe(raw_shipped_orders_data, settings.SHIPPED_ORDERS_DATA_TAB_NAME,
                                                  expected_columns=['Ship Date', 'OrderNumber'])

    if shipped_orders_df is None or shipped_orders_df.empty:
        logger.warning({"message": "No data or malformed data found in 'Shipped_Orders_Data' worksheet after conversion. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'OrderNumber'])

    # Standardize 'Ship Date' to 'Date'
    column_mapping = {
        'Ship Date': 'Date'
    }
    shipped_orders_df.rename(columns=column_mapping, inplace=True)

    # Check for presence of critical 'Date' column after renaming
    if 'Date' not in shipped_orders_df.columns:
        logger.error({"message": "Missing 'Date' column after renaming in Shipped_Orders_Data. Cannot process order dates.", "available_columns": shipped_orders_df.columns.tolist()})
        return pd.DataFrame(columns=['Date', 'OrderNumber'])
    
    shipped_orders_df['Date'] = pd.to_datetime(shipped_orders_df['Date'], errors='coerce')
    shipped_orders_df.dropna(subset=['Date'], inplace=True)

    if shipped_orders_df['Date'].empty:
        logger.warning({"message": "All dates in Shipped_Orders_Data became NaT or were empty after conversion. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'OrderNumber'])

    shipped_orders_df['Date'] = shipped_orders_df['Date'].dt.date
    logger.info({"message": "Successfully loaded shipped orders.", "rows_count": len(shipped_orders_df)})
    return shipped_orders_df

def load_weekly_shipped_history(sheet_id: str) -> pd.DataFrame:
    """Loads the weekly shipped history from Google Sheets."""
    logger.info({"message": "Loading weekly shipped history from Google Sheet."})
    
    raw_data = get_google_sheet_data(sheet_id, settings.ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME) 
    
    # Log raw data after fetching
    logger.debug({"message": "Raw data received from Google Sheet", "sheet": settings.ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME, "raw_data_head": raw_data[:5] if isinstance(raw_data, list) else str(raw_data)})

    # Convert raw list data to DataFrame
    # CORRECTED: Adjust expected_columns to match actual sheet headers
    df = _convert_raw_to_dataframe(raw_data, settings.ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME,
                                   expected_columns=['Ship Week', 'SKU', 'Quantity Shipped']) # Changed 'ShippedQuantity' to 'Quantity Shipped'

    if df is None or df.empty:
        logger.warning({"message": "No data or malformed data found in 'ORA_Weekly_Shipped_History' sheet after conversion. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'SKU', 'ShippedQuantity']) # Keep original return columns for consistency downstream

    id_vars = ['Ship Week'] 
    value_vars = [col for col in df.columns if col not in id_vars]
    
    if not value_vars:
        logger.warning({"message": "No SKU columns found in 'ORA_Weekly_Shipped_History' for unpivoting. Returning empty DataFrame."})
        return pd.DataFrame(columns=['Date', 'SKU', 'ShippedQuantity'])

    # Use 'Quantity Shipped' as the value column for melt
    long_df = pd.melt(df, id_vars=id_vars, value_vars=value_vars, var_name='SKU', value_name='ShippedQuantity')

    long_df.rename(columns={'Ship Week': 'Date'}, inplace=True)
    long_df['ShippedQuantity'] = pd.to_numeric(long_df['ShippedQuantity'].replace('', 0)).fillna(0)
    
    long_df['Date'] = pd.to_datetime(long_df['Date'].astype(str).str.split(' - ').str[1], errors='coerce')
    
    long_df.dropna(subset=['Date'], inplace=True)
    long_df['SKU'] = long_df['SKU'].astype(str)

    logger.info({"message": "Successfully loaded and unpivoted weekly shipped history.", "shape": str(long_df.shape)})
    return long_df

def load_product_names_map(sheet_id: str) -> pd.DataFrame:
    """
    Loads SKU to Product name mapping from a Google Sheet.
    Assumes a sheet named 'ORA_Configuration' with ParameterCategory 'Key Products'.
    """
    logger.info({"message": "Loading product names map from Google Sheet."})
    try:
        raw_data = get_google_sheet_data(sheet_id, settings.ORA_CONFIGURATION_TAB_NAME)
        
        # Log raw data after fetching
        logger.debug({"message": "Raw data received from Google Sheet", "sheet": settings.ORA_CONFIGURATION_TAB_NAME, "raw_data_head": raw_data[:5] if isinstance(raw_data, list) else str(raw_data)})

        # Convert raw list data to DataFrame
        df = _convert_raw_to_dataframe(raw_data, settings.ORA_CONFIGURATION_TAB_NAME)

        if df is None or df.empty:
            logger.warning({"message": "No data or malformed data found in 'ORA_Configuration' worksheet for product names map after conversion. Returning empty DataFrame."})
            return pd.DataFrame(columns=['SKU', 'Product'])
        
        # Ensure 'ParameterCategory' is 'Key Products', then map 'SKU' to 'ParameterName' as 'Product'
        if 'ParameterCategory' not in df.columns:
            logger.error({"message": "Missing 'ParameterCategory' column in ORA_Configuration for product names map. Cannot filter 'Key Products'.", "available_columns": df.columns.tolist()})
            return pd.DataFrame(columns=['SKU', 'Product'])

        key_products_df = df[df['ParameterCategory'] == 'Key Products'].copy()

        if 'SKU' in key_products_df.columns and 'ParameterName' in key_products_df.columns:
            df_filtered = key_products_df[['SKU', 'ParameterName']].copy()
            df_filtered.rename(columns={'ParameterName': 'Product'}, inplace=True)
            df_filtered['SKU'] = df_filtered['SKU'].astype(str)
            logger.info({"message": "Successfully loaded product names map from ORA_Configuration.", "shape": str(df_filtered.shape)})
            return df_filtered
        else:
            logger.error({"message": "Missing expected 'SKU' or 'ParameterName' columns in 'ORA_Configuration' for 'Key Products' category. Found columns in filtered data:", "available_columns": key_products_df.columns.tolist()})
            return pd.DataFrame(columns=['SKU', 'Product'])

    except Exception as e:
        logger.error({"message": "Error loading product names map.", "error": str(e)}, exc_info=True)
        return pd.DataFrame(columns=['SKU', 'Product'])


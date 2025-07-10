# filename: shipment_processor.py
"""
This module handles the processing and transformation of raw shipment data
retrieved from data sources like Google Sheets or APIs. It cleans the data,
renames columns, and extracts key information like the base SKU.
"""

import pandas as pd
import logging

def extract_base_sku(sku_lot: str) -> str:
    """Extracts the base SKU from a combined 'SKU - Lot' string."""
    if not isinstance(sku_lot, str):
        return ''
    return sku_lot.split('-')[0].strip()

def process_shipped_items(raw_shipped_items_data: list) -> pd.DataFrame:
    """
    Processes raw shipped items data into a clean DataFrame.
    """
    if not raw_shipped_items_data or len(raw_shipped_items_data) <= 1:
        logging.warning("No raw shipped items data provided to process.")
        return pd.DataFrame()

    headers = [h.strip() for h in raw_shipped_items_data[0]]
    data_rows = raw_shipped_items_data[1:]
    
    df = pd.DataFrame(data_rows, columns=headers)

    expected_cols_mapping = {
        'Ship Date': 'OrderDate',
        'SKU - Lot': 'SKU_Lot',
        'Quantity Shipped': 'Quantity',
        'Base SKU': 'BaseSKU_from_sheet'
    }
    
    # Rename columns that exist
    df.rename(columns={k: v for k, v in expected_cols_mapping.items() if k in df.columns}, inplace=True)

    # Ensure essential columns exist after renaming
    if 'SKU_Lot' not in df.columns or 'Quantity' not in df.columns or 'OrderDate' not in df.columns:
        logging.error("Essential columns are missing from the shipped items data after processing.")
        return pd.DataFrame()

    # Determine the final SKU
    if 'BaseSKU_from_sheet' in df.columns and not df['BaseSKU_from_sheet'].isnull().all():
        df['SKU'] = df['BaseSKU_from_sheet']
        logging.info("Using 'Base SKU' column from sheet for SKU identification.")
    else:
        df['SKU'] = df['SKU_Lot'].apply(extract_base_sku)
        logging.info("Extracting 'Base SKU' from 'SKU - Lot' in Python.")
    
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0).astype(int)
    df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce').dt.date
    
    # Drop rows where essential data is missing after conversion
    df.dropna(subset=['OrderDate', 'SKU', 'Quantity'], inplace=True)
    
    # --- PROPOSED ADDITION START ---
    # Rename columns to match what downstream reporting modules expect
    df.rename(columns={'OrderDate': 'Date', 'Quantity': 'Quantity_Shipped'}, inplace=True)
    # --- PROPOSED ADDITION END ---

    return df

def process_shipped_orders(raw_shipped_orders_data: list) -> pd.DataFrame:
    """
    Processes raw shipped orders data into a clean DataFrame.
    """
    if not raw_shipped_orders_data or len(raw_shipped_orders_data) <= 1:
        logging.warning("No raw shipped orders data provided to process.")
        return pd.DataFrame()

    headers = [h.strip() for h in raw_shipped_orders_data[0]]
    data_rows = raw_shipped_orders_data[1:]
    
    df = pd.DataFrame(data_rows, columns=headers)

    expected_cols_mapping = {'Ship Date': 'OrderDate', 'Order Number': 'OrderNumber'}

    df.rename(columns={k: v for k, v in expected_cols_mapping.items() if k in df.columns}, inplace=True)

    if 'OrderDate' not in df.columns or 'OrderNumber' not in df.columns:
        logging.error("Essential columns are missing from the shipped orders data after processing.")
        return pd.DataFrame()

    df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce').dt.date
    df.dropna(subset=['OrderDate', 'OrderNumber'], inplace=True)

    # --- PROPOSED ADDITION START ---
    # Rename 'OrderDate' to 'Date' to match downstream expectations
    df.rename(columns={'OrderDate': 'Date'}, inplace=True)
    # --- PROPOSED ADDITION END ---

    return df
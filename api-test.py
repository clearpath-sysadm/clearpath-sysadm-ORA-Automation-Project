# filename: src/services/data_processing/shipment_processor.py
"""
This module handles the processing and transformation of raw shipment data
retrieved from data sources like Google Sheets or APIs. It cleans the data,
renames columns, and extracts key information like the base SKU.
"""

import pandas as pd
import logging
import datetime

# FIX: Removed logging setup. This module relies on the main script for logging configuration.
logger = logging.getLogger(__name__)

def extract_base_sku(sku_lot: str) -> str:
    """Extracts the base SKU from a combined 'SKU - Lot' string."""
    if not isinstance(sku_lot, str):
        return ''
    return sku_lot.split('-')[0].strip()

def process_shipments_for_items(raw_shipment_data: list) -> pd.DataFrame:
    """
    Processes raw shipment data into a DataFrame suitable for the
    'Shipped_Items_Data' tab.

    Args:
        raw_shipment_data (list): Raw list of dictionaries from the ShipStation API
                                  'GET /shipments' endpoint.

    Returns:
        pd.DataFrame: A DataFrame with columns 'Ship Date', 'SKU - Lot',
                      'Quantity Shipped', and 'Base SKU'.
    """
    logger.info("Processing raw shipment data for Shipped_Items_Data tab...")
    
    # FIX: Filter out cancelled shipments before processing
    shipped_data = [s for s in raw_shipment_data if s.get('shipmentStatus') == 'shipped']
    
    extracted_data = []

    for shipment in shipped_data:
        ship_date = shipment.get('shipDate')
        if not ship_date:
            continue

        ship_date = datetime.datetime.strptime(ship_date[:10], '%Y-%m-%d').date()

        if 'shipmentItems' in shipment and shipment['shipmentItems']:
            for item in shipment['shipmentItems']:
                sku_lot = item.get('sku', '')
                quantity = item.get('quantity')
                base_sku = extract_base_sku(sku_lot)

                extracted_data.append({
                    'Ship Date': ship_date,
                    'SKU - Lot': sku_lot,
                    'Quantity Shipped': quantity,
                    'Base SKU': base_sku
                })

    df = pd.DataFrame(extracted_data)
    
    if not df.empty:
        df = df[['Ship Date', 'SKU - Lot', 'Quantity Shipped', 'Base SKU']]

    logger.info(f"Finished processing. Resulting DataFrame has {len(df)} rows.")
    return df

def process_shipments_for_orders(raw_shipment_data: list) -> pd.DataFrame:
    """
    Processes raw shipment data into a DataFrame suitable for the
    'Shipped_Orders_Data' tab, ensuring unique orders.

    Args:
        raw_shipment_data (list): Raw list of dictionaries from the ShipStation API
                                  'GET /shipments' endpoint.

    Returns:
        pd.DataFrame: A DataFrame with unique 'Ship Date' and 'OrderNumber'.
    """
    logger.info("Processing raw shipment data for Shipped_Orders_Data tab...")
    
    # FIX: Filter out cancelled shipments before processing
    shipped_data = [s for s in raw_shipment_data if s.get('shipmentStatus') == 'shipped']
    
    extracted_data = []
    
    for shipment in shipped_data:
        order_number = shipment.get('orderNumber')
        ship_date = shipment.get('shipDate')

        if order_number and ship_date:
            ship_date = datetime.datetime.strptime(ship_date[:10], '%Y-%m-%d').date()
            extracted_data.append({
                'Ship Date': ship_date,
                'OrderNumber': order_number
            })

    df = pd.DataFrame(extracted_data)

    if not df.empty:
        df.drop_duplicates(subset=['OrderNumber'], inplace=True)
        df.sort_values(by='Ship Date', inplace=True)
    
    logger.info(f"Finished processing. Resulting DataFrame has {len(df)} unique order rows.")
    return df


def aggregate_weekly_shipped_history(raw_shipment_data: list, target_skus: list) -> pd.DataFrame:
    """
    Aggregates quantities of specific Base SKUs into weekly totals for the
    'ORA_Weekly_Shipped_History' tab.

    Args:
        raw_shipment_data (list): Raw list of dictionaries from the ShipStation API
                                  'GET /shipments' endpoint.
        target_skus (list): A list of Base SKU strings to track.

    Returns:
        pd.DataFrame: A DataFrame with weekly aggregated data for each target SKU.
    """
    logger.info(f"Aggregating weekly shipment history for SKUs: {target_skus}...")
    
    # FIX: Filter out cancelled shipments before processing
    shipped_data = [s for s in raw_shipment_data if s.get('shipmentStatus') == 'shipped']
    
    extracted_data = []
    
    for shipment in shipped_data:
        ship_date = shipment.get('shipDate')
        if not ship_date:
            continue
        ship_date = datetime.datetime.strptime(ship_date[:10], '%Y-%m-%d').date()

        if 'shipmentItems' in shipment and shipment['shipmentItems']:
            for item in shipment['shipmentItems']:
                sku_lot = item.get('sku', '')
                base_sku = extract_base_sku(sku_lot)
                quantity = item.get('quantity')

                if base_sku in target_skus and quantity is not None:
                    extracted_data.append({
                        'Ship Date': ship_date,
                        'Base SKU': base_sku,
                        'Quantity': pd.to_numeric(quantity, errors='coerce')
                    })
    
    if not extracted_data:
        logger.warning("No data found for target SKUs within the raw shipment data.")
        return pd.DataFrame(columns=['Start Date', 'Stop Date'] + target_skus)

    df = pd.DataFrame(extracted_data)
    df.dropna(subset=['Quantity'], inplace=True)
    
    df['WeekYear'] = df['Ship Date'].apply(lambda d: d.isocalendar()[0])
    df['WeekNumber'] = df['Ship Date'].apply(lambda d: d.isocalendar()[1])
    
    df['DayOfWeek'] = df['Ship Date'].apply(lambda d: d.weekday())
    df['AdjustedDate'] = df['Ship Date'] - pd.to_timedelta(df['DayOfWeek'].apply(lambda x: (x + 2) % 7), unit='d')
    df['Start Date'] = df['AdjustedDate']
    df['Stop Date'] = df['Start Date'] + pd.to_timedelta(6, unit='d')

    aggregated_df = df.groupby(['Start Date', 'Stop Date', 'Base SKU'])['Quantity'].sum().reset_index()

    pivot_df = aggregated_df.pivot_table(
        index=['Start Date', 'Stop Date'],
        columns='Base SKU',
        values='Quantity',
        fill_value=0
    ).reset_index()

    for sku in target_skus:
        if sku not in pivot_df.columns:
            pivot_df[sku] = 0

    final_columns = ['Start Date', 'Stop Date'] + target_skus
    pivot_df = pivot_df[final_columns]
    pivot_df.sort_values(by='Start Date', inplace=True)

    logger.info(f"Aggregation complete. Final report has {len(pivot_df)} weekly rows.")
    return pivot_df

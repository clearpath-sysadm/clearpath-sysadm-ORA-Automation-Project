# filename: average_calculations.py
"""
This module is responsible for performing more complex, multi-row calculations,
specifically focusing on rolling averages for the ORA Project reports.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta

def calculate_12_month_rolling_average(weekly_shipped_history_df):
    """
    Calculates the 12-month (52-week) rolling average of shipped quantities for each SKU
    based on historical data.

    Args:
        weekly_shipped_history_df (pd.DataFrame): A DataFrame containing the historical
                                                  weekly shipment data. Expected columns
                                                  are 'Date', 'SKU', 'ShippedQuantity'.

    Returns:
        pd.DataFrame: A DataFrame with 'SKU' and 'Rolling_Average_12_Month'.
    """
    logging.info("Calculating 12-Month Rolling Average...")
    if weekly_shipped_history_df is None or weekly_shipped_history_df.empty:
        logging.warning("Weekly shipped history DataFrame is empty. Cannot calculate rolling average.")
        return pd.DataFrame(columns=['SKU', 'Rolling_Average_12_Month'])

    # --- Start of Corrected Logic ---
    # Create a copy to avoid modifying the original DataFrame
    df = weekly_shipped_history_df.copy()

    # Ensure the 'Date' column is in a proper datetime format for comparison
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)

    # Use the actual current date to define the end of the 52-week window
    end_date = pd.to_datetime(datetime.now())
    start_date = end_date - timedelta(weeks=52)
    # --- End of Corrected Logic ---

    logging.debug(f"Calculating rolling average for 52 weeks prior to {end_date.strftime('%Y-%m-%d')}")

    # Filter the DataFrame to include only records within the last 52 weeks
    recent_shipments = df[df['Date'].between(start_date, end_date)]
    logging.debug(f"Found {len(recent_shipments)} shipment records in the last 52 weeks.")

    if recent_shipments.empty:
        logging.warning("No shipment data found in the last 52 weeks to calculate rolling average.")
        # If no recent data, return 0 averages for all SKUs found in the original history
        all_skus = df['SKU'].unique()
        return pd.DataFrame({'SKU': all_skus, 'Rolling_Average_12_Month': 0})

    # Group the recent shipment data by SKU and sum the quantities
    total_shipped_by_sku = recent_shipments.groupby('SKU')['ShippedQuantity'].sum()

    # Calculate the average by dividing the total quantity by 52 weeks
    rolling_average = (total_shipped_by_sku / 52).round(0).astype(int)

    # Convert the resulting pandas Series to a DataFrame for easier merging later
    rolling_average_df = rolling_average.reset_index()
    rolling_average_df.rename(columns={'ShippedQuantity': '12-Month Rolling Average'}, inplace=True)

    logging.info("Successfully calculated 12-month rolling average.")
    logging.debug(f"Final rolling average DataFrame shape: {rolling_average_df.shape}")
    logging.debug(f"Final rolling average DataFrame shape: {rolling_average_df.shape}")
    logging.debug(f"Final rolling average DataFrame columns: {rolling_average_df.columns.tolist()}") # Add this for verification
    
    return rolling_average_df
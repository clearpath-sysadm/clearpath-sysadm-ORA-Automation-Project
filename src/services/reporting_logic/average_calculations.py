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
    based on historical data, using the 52 most recent data points.

    Args:
        weekly_shipped_history_df (pd.DataFrame): A DataFrame containing the historical
                                                  weekly shipment data. Expected columns
                                                  are 'Date', 'SKU', 'ShippedQuantity'.

    Returns:
        pd.DataFrame: A DataFrame with 'SKU' and '12-Month Rolling Average'.
    """
    logging.info("Calculating 12-Month Rolling Average using most recent 52 entries...")
    
    # Debug log: Input DataFrame row count
    logging.debug(f"Input weekly_shipped_history_df has {len(weekly_shipped_history_df)} rows.")

    if weekly_shipped_history_df is None or weekly_shipped_history_df.empty:
        logging.warning("Weekly shipped history DataFrame is empty. Cannot calculate rolling average.")
        return pd.DataFrame(columns=['SKU', '12-Month Rolling Average'])

    df = weekly_shipped_history_df.copy()

    # Ensure the 'Date' column is in a proper datetime format for sorting
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)

    # Sort data by SKU and then by Date in descending order to get most recent entries first
    df_sorted = df.sort_values(by=['SKU', 'Date'], ascending=[True, False])

    # Group by SKU and take the sum of the most recent 52 quantities
    # If an SKU has less than 52 entries, it will sum whatever is available for that SKU.
    # The division by 52 (next step) implicitly treats missing weeks as zeros for the average period.
    
    # Store intermediate results to log
    intermediate_sums = {}
    
    def get_sum_and_log(x):
        recent_entries = x['ShippedQuantity'].head(52)
        current_sum = recent_entries.sum()
        actual_count = len(recent_entries)
        
        # Debug log: Sum and actual count per SKU
        logging.debug(f"SKU {x.name}: Sum of {actual_count} recent entries = {current_sum}.")
        
        if actual_count < 52:
            logging.debug(f"SKU {x.name}: Warning, only {actual_count} entries found for 52-week average.") # Debug log for less than 52 entries
            
        intermediate_sums[x.name] = current_sum # Store sum for later
        return current_sum

    total_shipped_by_sku_recent_52 = df_sorted.groupby('SKU').apply(get_sum_and_log)

    # Calculate the average by dividing the total quantity by 52 weeks
    # This aligns with the "divide by 52" part of the desired logic
    unrounded_rolling_average = total_shipped_by_sku_recent_52 / 52
    
    # Debug log: Unrounded average
    logging.debug(f"Unrounded rolling averages: {unrounded_rolling_average.to_dict()}.")

    rolling_average = unrounded_rolling_average.round(0).astype(int)

    # Convert the resulting pandas Series to a DataFrame
    rolling_average_df = rolling_average.reset_index()
    rolling_average_df.rename(columns={0: '12-Month Rolling Average'}, inplace=True) 

    logging.info("Successfully calculated 12-month rolling average based on 52 most recent quantities.")
    logging.debug(f"Final rolling average DataFrame shape: {rolling_average_df.shape}")
    logging.debug(f"Final rolling average DataFrame columns: {rolling_average_df.columns.tolist()}")
    
    return rolling_average_df

# filename: average_calculations.py
"""
This module is responsible for performing more complex, multi-row calculations,
specifically focusing on rolling averages for the ORA Project reports.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from src.services.reporting_logic.week_utils import get_current_week_boundaries

def calculate_12_month_rolling_average(weekly_shipped_history_df):
    """
    Calculates the 12-month (52-week) rolling average of shipped quantities for each SKU
    based on historical data, using the 52 most recent COMPLETE weeks only.
    
    IMPORTANT: Defensively filters out the current/incomplete week to ensure accurate averages.
    Friday is the last shipping day, so weeks are complete once Friday has passed.

    Args:
        weekly_shipped_history_df (pd.DataFrame): A DataFrame containing the historical
                                                  weekly shipment data. Expected columns
                                                  are 'Date', 'SKU', 'ShippedQuantity'.

    Returns:
        pd.DataFrame: A DataFrame with 'SKU' and '12-Month Rolling Average'.
    """
    logging.info("Calculating 12-Month Rolling Average using most recent 52 COMPLETE weeks...")
    
    # Debug log: Input DataFrame row count
    logging.debug(f"Input weekly_shipped_history_df has {len(weekly_shipped_history_df)} rows.")

    if weekly_shipped_history_df is None or weekly_shipped_history_df.empty:
        logging.warning("Weekly shipped history DataFrame is empty. Cannot calculate rolling average.")
        return pd.DataFrame(columns=['SKU', '12-Month Rolling Average'])

    df = weekly_shipped_history_df.copy()
    
    # Ensure 'Date' and 'ShippedQuantity' columns are in proper formats
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    # Convert ShippedQuantity to numeric, coercing errors to NaN.
    # This handles cases where quantity values might be strings (e.g., '-')
    df['ShippedQuantity'] = pd.to_numeric(df['ShippedQuantity'], errors='coerce')
    
    # Drop rows where 'Date' or 'ShippedQuantity' are NaN after conversion
    df.dropna(subset=['Date', 'ShippedQuantity'], inplace=True)
    
    # DEFENSIVE FILTERING: Remove any incomplete weeks
    # Get current week boundaries to filter out partial weeks
    current_monday, _ = get_current_week_boundaries()
    
    # Filter out rows from the current/incomplete week
    rows_before = len(df)
    df = df[df['Date'] < pd.Timestamp(current_monday)]
    rows_after = len(df)
    
    if rows_before > rows_after:
        logging.info(f"Filtered out {rows_before - rows_after} row(s) from incomplete week(s) (>= {current_monday})")
    
    if df.empty:
        logging.warning("After filtering incomplete weeks, no data remains. Cannot calculate rolling average.")
        return pd.DataFrame(columns=['SKU', '12-Month Rolling Average'])

    # Sort data by SKU and then by Date in descending order to get most recent entries first
    df_sorted = df.sort_values(by=['SKU', 'Date'], ascending=[True, False])

    # Group by SKU and take the sum of the most recent 52 quantities
    # If an SKU has less than 52 entries, it will sum whatever is available for that SKU.
    
    # Store intermediate results to log (for the get_sum_and_log function)
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

    # Updated: Add include_groups=False to address FutureWarning
    total_shipped_by_sku_recent_52 = df_sorted.groupby('SKU').apply(get_sum_and_log, include_groups=False)

    # Calculate the average by dividing the total quantity by 52 weeks
    # This aligns with the "divide by 52" part of the desired logic
    unrounded_rolling_average = total_shipped_by_sku_recent_52 / 52
    
    # Debug log: Unrounded average
    logging.debug(f"Unrounded rolling averages: {unrounded_rolling_average.to_dict()}.")

    rolling_average = unrounded_rolling_average.round(0).astype(int)

    # Convert the resulting pandas Series to a DataFrame
    rolling_average_df = rolling_average.reset_index()
    # Updated: Rename the column that results from the apply operation.
    # The name of the series from .apply is typically derived from the input or is a default.
    # Using the name attribute of the series itself is more robust.
    rolling_average_df.rename(columns={rolling_average_df.columns[1]: '12-Month Rolling Average'}, inplace=True) 

    logging.info("Successfully calculated 12-month rolling average based on 52 most recent quantities.")
    logging.debug(f"Final rolling average DataFrame shape: {rolling_average_df.shape}")
    logging.debug(f"Final rolling average DataFrame columns: {rolling_average_df.columns.tolist()}")
    
    return rolling_average_df

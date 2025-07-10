# filename: weekly_report_generator.py
"""
This module contains functions for generating the Weekly Inventory Report.
It's designed to be part of the ORA (Order & Reporting Automation) Project's
reporting logic pipeline.
"""
import pandas as pd
import logging

# No __main__ block or embedded supporting modules in this final modular file.
# This module relies on being imported by an orchestrator like shipstation_reporter.py
# which handles the import of inventory_calculations, average_calculations, etc.
# from their proper locations.

def generate_weekly_inventory_report(current_inventory_df: pd.DataFrame, rolling_average_df: pd.DataFrame, product_names_map: dict) -> pd.DataFrame:
    """
    Generates the weekly inventory report by combining current inventory with rolling averages.
    """
    logging.info("Generating Weekly Inventory Report...")
    
    if current_inventory_df.empty or rolling_average_df.empty or not product_names_map:
        logging.warning("Missing required input data (current_inventory_df, rolling_average_df, or product_names_map) for Weekly Inventory Report generation. Returning empty DataFrame.")
        return pd.DataFrame(columns=['SKU', 'Product', 'Current_Inventory', '12-Month Rolling Average'])

    # Merge current inventory and rolling average
    weekly_report_df = pd.merge(
        current_inventory_df,
        rolling_average_df,
        on='SKU',
        how='outer'
    )

    # Add product names
    weekly_report_df['Product'] = weekly_report_df['SKU'].map(product_names_map).fillna('N/A')

    # Ensure 'Current_Inventory' and '12-Month Rolling Average' are handled gracefully
    weekly_report_df['Current_Inventory'] = weekly_report_df['Current_Inventory'].fillna(0).astype(int)
    weekly_report_df['12-Month Rolling Average'] = weekly_report_df['12-Month Rolling Average'].apply( 
        lambda x: int(x) if isinstance(x, (int, float)) else x
    ).fillna('N/A')

    # Select and reorder final columns.
    final_columns = ['SKU', 'Product', 'Current_Inventory', '12-Month Rolling Average'] 
    weekly_report_df = weekly_report_df[final_columns]
    
    logging.info(f"Weekly Inventory Report prepared. Shape: {weekly_report_df.shape}")
    logging.debug(f"Weekly Report head:\n{weekly_report_df.head()}")
    
    return weekly_report_df

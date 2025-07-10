import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def calculate_daily_inventory(initial_inventory: dict, transactions_df: pd.DataFrame, all_dates_for_report: pd.DatetimeIndex) -> pd.DataFrame | None:
    """
    Calculates the daily Beginning of Day (BOD) and End of Day (EOD) inventory.
    This version correctly uses a starting inventory dictionary.
    """
    try:
        logger.info("--- Starting daily inventory calculation (BOD/EOD) ---")
        
        # Log initial inventory and all dates for report
        logger.info(f"Initial Inventory (head): {list(initial_inventory.items())[:5]}...")
        logger.info(f"Number of dates in report period: {len(all_dates_for_report)}")
        logger.info(f"First 5 dates: {all_dates_for_report[:5]}")
        
        if transactions_df.empty:
            logger.warning("Transactions DataFrame is empty. Inventory will not change from initial values.")
        else:
            logger.info(f"Transactions DataFrame shape: {transactions_df.shape}")
            logger.info(f"Transactions DataFrame head:\n{transactions_df.head().to_string()}")
            # Date column is already guaranteed to be datetime.date objects by report_data_loader.py
            # This block was causing a TypeError due to redundant processing.
            # if not transactions_df['Date'].empty and not isinstance(transactions_df['Date'].iloc[0], datetime.date):
            #    transactions_df['Date'] = transactions_df['Date'].apply(lambda x: x.date() if isinstance(x, datetime) else x)


        # --- FIX: Standardize all SKUs to strings ---
        # Convert all SKU keys from initial_inventory to strings
        initial_inventory_str_keys = {str(k): v for k, v in initial_inventory.items()}
        # Convert all SKUs from transactions_df to strings
        transactions_skus_str = transactions_df['SKU'].astype(str).unique()
        all_skus = set(initial_inventory_str_keys.keys()) | set(transactions_skus_str)
        
        inventory_records = []
        
        # Initialize current_inventory with string keys and default 0, then update with initial values
        current_inventory = {sku: 0 for sku in all_skus} 
        current_inventory.update(initial_inventory_str_keys) 
        
        logger.debug(f"Initial state of current_inventory before daily loop: {current_inventory}")

        for i, report_date in enumerate(all_dates_for_report):
            logger.debug(f"--- Processing date: {report_date} (Day {i+1} of {len(all_dates_for_report)}) ---")
            
            bod_inventory = current_inventory.copy() # Captures the inventory from the end of the previous day
            logger.debug(f"BOD_Inventory (copy of current_inventory) for {report_date}: {bod_inventory}")

            # report_date will already be datetime.date from all_dates_for_report
            report_date_as_date = report_date 

            # Ensure comparison is with string SKUs in daily_transactions
            daily_transactions = transactions_df[transactions_df['Date'] == report_date_as_date].copy()
            daily_transactions['SKU'] = daily_transactions['SKU'].astype(str) # Ensure SKU in daily_transactions is string

            # Log daily transactions being processed
            if not daily_transactions.empty:
                logger.info(f"Processing daily transactions for {report_date}: {daily_transactions.shape[0]} transactions found.")
                # logger.debug(f"Daily transactions details:\n{daily_transactions.to_string()}") # Use debug for verbose output

            for sku in all_skus: # 'sku' here will be a string
                bod_qty = bod_inventory.get(sku, 0) # This will now correctly pull from the robust current_inventory with string keys
                
                # Sum transactions for the day
                # Ensure TransactionType is correctly matched (e.g. 'Ship' vs 'ship')
                shipped_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'ship'), 'Quantity'].sum()
                received_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'receive'), 'Quantity'].sum()
                repack_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'repack'), 'Quantity'].sum()
                
                eod_qty = bod_qty + received_qty - shipped_qty + repack_qty
                current_inventory[sku] = eod_qty 
                
                # Log daily inventory changes for each SKU
                if (bod_qty != eod_qty) or (shipped_qty > 0) or (received_qty > 0) or (repack_qty > 0) or (sku in initial_inventory_str_keys.keys()):
                    logger.info(f"Date: {report_date}, SKU: {sku}, BOD: {bod_qty}, Received: {received_qty}, Shipped: {shipped_qty}, Repack: {repack_qty}, EOD: {eod_qty}")
                # else:
                #     logger.debug(f"Date: {report_date}, SKU: {sku}, EOD: {eod_qty} (No change)") # Use debug for non-changing inventory
                
                inventory_records.append({
                    'Date': report_date,
                    'SKU': sku,
                    'BOD_Inventory': bod_qty,
                    'EOD_Inventory': eod_qty
                })
            logger.debug(f"current_inventory (after processing {report_date}): {current_inventory}") # Log current_inventory at end of day
        
        # --- FIX FOR DUPLICATE (DATE, SKU) ENTRIES AND STATIC EOD ---
        final_df = pd.DataFrame(inventory_records)
        if not final_df.empty:
            # Ensure unique (Date, SKU) pairs, keeping the one that should have correct EOD
            # This requires sorting to ensure the dynamically calculated one is chosen
            final_df = final_df.sort_values(by=['Date', 'SKU', 'EOD_Inventory'], ascending=[True, True, False]) # Sort to prioritize non-zero/higher EODs if duplicates exist
            final_df = final_df.drop_duplicates(subset=['Date', 'SKU'], keep='first') # Keep the first, which should now be the most accurate after sorting
            
            logger.info(f"Final daily_inventory_df to be returned from calculate_daily_inventory (head):\n{final_df.head().to_string()}")
            logger.info(f"Final daily_inventory_df to be returned from calculate_daily_inventory (tail):\n{final_df.tail().to_string()}")
        else:
            logger.warning("No daily inventory records generated.")
        
        logger.info(f"Daily inventory calculation complete. Shape: {final_df.shape}")
        return final_df

    except Exception as e:
        logger.error(f"Error calculating daily inventory: {e}", exc_info=True)
        return None


def calculate_current_inventory(initial_inventory: dict, inventory_transactions_df: pd.DataFrame, shipped_items_df: pd.DataFrame, key_skus: list, current_week_start_date: datetime.date, current_week_end_date: datetime.date) -> pd.DataFrame:
    """
    Calculates the current inventory by applying initial values (EOD Prior Week) and
    transactions specifically within the current week.
    """
    try:
        logger.info(f"Calculating current inventory for week {current_week_start_date} to {current_week_end_date}...")
        
        # --- FIX: Standardize initial_inventory keys to strings here as well ---
        current_inventory = {str(k): v for k, v in initial_inventory.items()}
        logger.debug(f"Initial inventory for current calculation: {current_inventory}")

        # Filter transactions to only include those within the current week
        # Ensure 'Date' column is datetime.date for comparison
        # This line is redundant if report_data_loader.py already ensures datetime.date objects
        # inventory_transactions_df['Date'] = inventory_transactions_df['Date'].apply(lambda x: x if isinstance(x, datetime.date) else x.date())
        # shipped_items_df['Date'] = shipped_items_df['Date'].apply(lambda x: x if isinstance(x, datetime.date) else x.date())

        weekly_transactions_df = inventory_transactions_df[
            (inventory_transactions_df['Date'] >= current_week_start_date) & 
            (inventory_transactions_df['Date'] <= current_week_end_date)
        ].copy()
        
        weekly_shipped_items_df = shipped_items_df[
            (shipped_items_df['Date'] >= current_week_start_date) & 
            (shipped_items_df['Date'] <= current_week_end_date)
        ].copy()

        logger.debug(f"Weekly transactions shape: {weekly_transactions_df.shape}")
        logger.debug(f"Weekly shipped items shape: {weekly_shipped_items_df.shape}")

        # Combine all relevant weekly transactions
        weekly_shipped_items_df['SKU'] = weekly_shipped_items_df['SKU'].astype(str)
        weekly_shipped_items_df.rename(columns={'Quantity_Shipped': 'Quantity'}, inplace=True)
        weekly_shipped_items_df['TransactionType'] = 'Ship'
        
        all_weekly_transactions = pd.concat([weekly_transactions_df[['SKU', 'Quantity', 'TransactionType']], weekly_shipped_items_df[['SKU', 'Quantity', 'TransactionType']]], ignore_index=True)
        all_weekly_transactions['Quantity'] = pd.to_numeric(all_weekly_transactions['Quantity'], errors='coerce').fillna(0)
        
        logger.debug(f"All weekly transactions head:\n{all_weekly_transactions.head().to_string()}")
        logger.debug(f"All weekly transactions tail:\n{all_weekly_transactions.tail().to_string()}")
        logger.debug(f"All weekly transactions shape: {all_weekly_transactions.shape}")


        # Apply weekly transactions to the initial inventory (EOD Prior Week)
        for _, row in all_weekly_transactions.iterrows():
            sku = str(row['SKU']) # Ensure SKU is string for dictionary lookup
            qty = row['Quantity']
            if row['TransactionType'].lower() == 'ship':
                current_inventory[sku] = current_inventory.get(sku, 0) - qty
            else: # Receive, Repack
                current_inventory[sku] = current_inventory.get(sku, 0) + qty
        
        # Format for output
        final_df = pd.DataFrame(list(current_inventory.items()), columns=['SKU', 'Quantity'])
        # Ensure key_skus are strings for filtering
        final_df = final_df[final_df['SKU'].isin([str(s) for s in key_skus])]

        logger.info(f"Current inventory calculation complete. Shape: {final_df.shape}")
        return final_df

    except Exception as e:
        logger.error(f"Error calculating current inventory: {e}", exc_info=True)
        return pd.DataFrame(columns=['SKU', 'Quantity']) # Return empty DataFrame on error
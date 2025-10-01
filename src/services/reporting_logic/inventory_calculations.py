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
                bod_qty = bod_inventory.get(sku, 0) 
                
                # Sum transactions for the day
                # Ensure TransactionType is correctly matched (e.g. 'Ship' vs 'ship')
                shipped_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'ship'), 'Quantity'].sum()
                received_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'receive'), 'Quantity'].sum()
                repack_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'repack'), 'Quantity'].sum()
                
                # --- NEW: Handle Adjust Up and Adjust Down transaction types ---
                # Adjusted to compare against "adjust up" and "adjust down" (without underscore)
                adjust_up_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'adjust up'), 'Quantity'].sum()
                adjust_down_qty = daily_transactions.loc[(daily_transactions['SKU'] == sku) & (daily_transactions['TransactionType'].astype(str).str.lower() == 'adjust down'), 'Quantity'].sum()

                eod_qty = bod_qty + received_qty - shipped_qty + repack_qty + adjust_up_qty - adjust_down_qty
                current_inventory[sku] = eod_qty 
                
                # Log daily inventory changes for each SKU
                if (bod_qty != eod_qty) or (shipped_qty > 0) or (received_qty > 0) or (repack_qty > 0) or (adjust_up_qty > 0) or (adjust_down_qty > 0) or (sku in initial_inventory_str_keys.keys()):
                    logger.info(f"Date: {report_date}, SKU: {sku}, BOD: {bod_qty}, Received: {received_qty}, Shipped: {shipped_qty}, Repack: {repack_qty}, Adjust Up: {adjust_up_qty}, Adjust Down: {adjust_down_qty}, EOD: {eod_qty}")
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
    Calculates the current inventory by applying initial values (as of 9/19/2025) and transactions AFTER that baseline date.
    Initial inventory (9/19/2025) + receives/repacks/adjustments AFTER 9/19 - shipments AFTER 9/19 = Current inventory
    """
    try:
        # Baseline date when InitialInventory was set
        baseline_date = datetime.strptime('2025-09-19', '%Y-%m-%d').date()
        logger.info(f"Calculating current inventory from baseline date: {baseline_date}")
        
        # Standardize initial_inventory keys to strings
        current_inventory = {str(k): v for k, v in initial_inventory.items()}
        logger.info(f"Initial inventory (as of {baseline_date}) loaded for {len(current_inventory)} SKUs")
        logger.debug(f"Initial inventory: {current_inventory}")

        # Process ONLY inventory transactions AFTER the baseline date
        all_transactions_df = inventory_transactions_df[
            inventory_transactions_df['Date'] > baseline_date
        ].copy()
        logger.info(f"Processing {len(all_transactions_df)} inventory transactions after {baseline_date}")

        # Process ONLY shipped items AFTER the baseline date
        all_shipped_items_df = shipped_items_df[
            shipped_items_df['Date'] > baseline_date
        ].copy()
        logger.info(f"Processing {len(all_shipped_items_df)} shipped items after {baseline_date}")

        # Prepare shipped items as transactions
        all_shipped_items_df['SKU'] = all_shipped_items_df['SKU'].astype(str)
        all_shipped_items_df.rename(columns={'Quantity_Shipped': 'Quantity'}, inplace=True)
        all_shipped_items_df['TransactionType'] = 'Ship'
        
        # Combine all transactions
        all_combined_transactions = pd.concat(
            [all_transactions_df[['SKU', 'Quantity', 'TransactionType']], 
             all_shipped_items_df[['SKU', 'Quantity', 'TransactionType']]], 
            ignore_index=True
        )
        all_combined_transactions['Quantity'] = pd.to_numeric(all_combined_transactions['Quantity'], errors='coerce').fillna(0)
        
        logger.info(f"Total combined transactions: {len(all_combined_transactions)}")

        # Apply ALL transactions to the initial inventory
        for _, row in all_combined_transactions.iterrows():
            sku = str(row['SKU'])
            qty = row['Quantity']
            transaction_type = row['TransactionType'].lower()

            if transaction_type == 'ship':
                current_inventory[sku] = current_inventory.get(sku, 0) - qty
            elif transaction_type == 'adjust down':
                current_inventory[sku] = current_inventory.get(sku, 0) - qty
            elif transaction_type in ['receive', 'repack', 'adjust up']:
                current_inventory[sku] = current_inventory.get(sku, 0) + qty
            else:
                logger.warning(f"Unknown transaction type '{transaction_type}' for SKU '{sku}'. Quantity not applied.")
        
        # Format for output
        final_df = pd.DataFrame(list(current_inventory.items()), columns=['SKU', 'Quantity'])
        # Ensure key_skus are strings for filtering
        final_df = final_df[final_df['SKU'].isin([str(s) for s in key_skus])]

        logger.info(f"Current inventory calculation complete. Shape: {final_df.shape}")
        logger.info(f"Final inventory by SKU:\n{final_df.to_string()}")
        return final_df

    except Exception as e:
        logger.error(f"Error calculating current inventory: {e}", exc_info=True)
        return pd.DataFrame(columns=['SKU', 'Quantity'])

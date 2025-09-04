import pandas as pd
import logging
import os
from datetime import datetime, timedelta
import math
from . import inventory_calculations

log_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..')
log_dir = os.path.join(log_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'monthly_report_generator.log')

logger = logging.getLogger('monthly_report_generator')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.propagate = False

def generate_monthly_charge_report(
    rates: dict,
    pallet_counts: dict,
    start_of_month_inventory: dict,
    inventory_transactions_df: pd.DataFrame,
    shipped_items_df: pd.DataFrame,
    shipped_orders_df: pd.DataFrame,
    year: int,
    month: int,
    key_skus_list: list
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """
    Generates the main DataFrame for the Monthly Charge Report.
    This version has the correct function signature and logic.
    """
    try:
    # Moved EOM inventory values section to end of log output
        logger.info(f"Generating Monthly Charge Report for {year}-{month}...")
        start_date = datetime(year, month, 1).date()
        end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        # --- LOGGING: Shipped Items DataFrame after loading ---
        logger.debug(f"Shipped Items DataFrame after loading: shape={shipped_items_df.shape}, columns={list(shipped_items_df.columns)}")
        logger.debug(f"Shipped Items DataFrame head:\n{shipped_items_df.head()}\n")
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D').date
        
        # Ensure 'Date' columns are datetime.date objects for proper filtering
        inventory_transactions_df['Date'] = pd.to_datetime(inventory_transactions_df['Date']).dt.date
        shipped_items_df['Date'] = pd.to_datetime(shipped_items_df['Date']).dt.date 
        shipped_orders_df['Date'] = pd.to_datetime(shipped_orders_df['Date']).dt.date 
        
        # Filter shipments to only include those within the report month
        # Log inventory transaction summary for the month
        month_transactions = inventory_transactions_df[
            (inventory_transactions_df['Date'] >= start_date) & (inventory_transactions_df['Date'] <= end_date)
        ]
        logger.info(f"Total inventory transactions for month: {len(month_transactions)}")
        if 'TransactionType' in month_transactions.columns:
            logger.info("Inventory transactions by type:")
            logger.info(month_transactions['TransactionType'].value_counts().to_string())
            logger.info("Sum of quantities by type:")
            logger.info(month_transactions.groupby('TransactionType')['Quantity'].sum().to_string())
            if 'SKU' in month_transactions.columns:
                logger.info("Sum of quantities by TransactionType and SKU:")
                logger.info(month_transactions.groupby(['TransactionType', 'SKU'])['Quantity'].sum().to_string())

        # Log detailed inventory transactions for audit
        logger.info("===== Detailed Inventory Transactions for Month =====")
        if not month_transactions.empty:
            for idx, row in month_transactions.iterrows():
                logger.info(f"Date: {row['Date']} | SKU: {row['SKU']} | Type: {row['TransactionType']} | Qty: {row['Quantity']}")
        else:
            logger.info("No inventory transactions for this month.")
        logger.info("===== End of Detailed Inventory Transactions =====\n")
        # --- LOGGING: Shipped Items DataFrame after date conversion ---
        logger.debug(f"Shipped Items DataFrame after date conversion: shape={shipped_items_df.shape}, columns={list(shipped_items_df.columns)}")
        logger.debug(f"Shipped Items DataFrame head:\n{shipped_items_df.head()}\n")
        shipped_items_df_filtered = shipped_items_df[(shipped_items_df['Date'] >= start_date) & (shipped_items_df['Date'] <= end_date)].copy()
        shipped_orders_df_filtered = shipped_orders_df[(shipped_orders_df['Date'] >= start_date) & (shipped_orders_df['Date'] <= end_date)].copy()

        logger.debug(f"shipped_items_df_filtered head: \n{shipped_items_df_filtered.head().to_string()}")
        logger.debug(f"shipped_items_df_filtered tail: \n{shipped_items_df_filtered.tail().to_string()}")
        logger.debug(f"shipped_items_df_filtered shape: {shipped_items_df_filtered.shape}")

        logger.debug(f"shipped_orders_df_filtered head: \n{shipped_orders_df_filtered.head().to_string()}")
        logger.debug(f"shipped_orders_df_filtered tail: \n{shipped_orders_df_filtered.tail().to_string()}")
        logger.debug(f"shipped_orders_df_filtered shape: {shipped_orders_df_filtered.shape}")
        
        # Consolidate all relevant transactions into a single DataFrame for daily calculation
        shipped_transactions_for_daily_calc = shipped_items_df_filtered[['Date', 'SKU', 'Quantity_Shipped']].copy()
        shipped_transactions_for_daily_calc.rename(columns={'Quantity_Shipped': 'Quantity'}, inplace=True)
        shipped_transactions_for_daily_calc['TransactionType'] = 'Ship'
        
        all_daily_transactions = pd.concat([inventory_transactions_df, shipped_transactions_for_daily_calc], ignore_index=True)
        all_daily_transactions['Quantity'] = pd.to_numeric(all_daily_transactions['Quantity'], errors='coerce').fillna(0)

        # Calculate daily inventory (BOD/EOD) for each SKU
        daily_inventory_df = inventory_calculations.calculate_daily_inventory(
            start_of_month_inventory,
            all_daily_transactions,
            all_dates
        )

        logger.info("--- Inspecting daily_inventory_df after calculation ---")
        if daily_inventory_df is not None and not daily_inventory_df.empty:
            logger.info(f"daily_inventory_df head:\n{daily_inventory_df.head().to_string()}")
            logger.info(f"daily_inventory_df tail:\n{daily_inventory_df.tail().to_string()}")
            logger.info(f"daily_inventory_df shape: {daily_inventory_df.shape}")
            
            if 'EOD_Inventory' in daily_inventory_df.columns:
                logger.info("EOD_Inventory description across all SKUs:\n" + daily_inventory_df['EOD_Inventory'].describe().to_string())
                if '17612' in daily_inventory_df['SKU'].unique():
                    logger.info(f"Daily EOD_Inventory for SKU 17612:\n{daily_inventory_df[daily_inventory_df['SKU'] == '17612'][['Date', 'EOD_Inventory']].to_string()}")
                if '17904' in daily_inventory_df['SKU'].unique():
                    logger.info(f"Daily EOD_Inventory for SKU 17904:\n{daily_inventory_df[daily_inventory_df['SKU'] == '17904'][['Date', 'EOD_Inventory']].to_string()}")
            else:
                logger.warning("daily_inventory_df is missing 'EOD_Inventory' column after daily inventory calculation.")
        else:
            logger.error("daily_inventory_df is None or empty after daily inventory calculation. Cannot proceed with report generation.")
            return None, None
        
        # Prepare the report DataFrame with all dates
        report_df = pd.DataFrame({'Date': all_dates})
        report_df['Date'] = pd.to_datetime(report_df['Date'])

        # Calculate daily order and package charges
        daily_orders = shipped_orders_df_filtered.groupby('Date')['OrderNumber'].nunique().rename('Num_Orders')
        daily_packages = shipped_items_df_filtered.groupby('Date')['Quantity_Shipped'].sum().rename('Num_Packages')

        logger.info("Daily Unique SKUs Shipped (count > 0):")
        if not shipped_items_df_filtered.empty:
            daily_unique_skus_shipped = shipped_items_df_filtered.pivot_table(
                index='Date', 
                columns='SKU', 
                values='Quantity_Shipped', 
                aggfunc='sum'
            )
            daily_unique_skus_shipped_count = (daily_unique_skus_shipped > 0).sum(axis=1)
            logger.info(daily_unique_skus_shipped_count.to_string())
        else:
            logger.info("No shipped items data to calculate daily unique SKUs shipped.")


        report_df = report_df.set_index('Date')
        report_df = report_df.join(daily_orders).fillna(0)
        report_df = report_df.join(daily_packages).fillna(0)
        
        report_df['Orders Charge'] = report_df['Num_Orders'] * rates.get('OrderCharge', 0)
        report_df['Packages Charge'] = report_df['Num_Packages'] * rates.get('PackageCharge', 0)
        
        # Calculate daily space rental charge
        daily_inventory_df['PalletsUsed'] = daily_inventory_df.apply(\
            lambda row: math.ceil(row['EOD_Inventory'] / pallet_counts.get(row['SKU'], 1)) if pallet_counts.get(row['SKU']) else 0,\
            axis=1\
        )

        logger.info("--- Inspecting PalletsUsed before summing ---")
        if not daily_inventory_df.empty and 'PalletsUsed' in daily_inventory_df.columns:
            logger.info("PalletsUsed description across all SKUs:\n" + daily_inventory_df['PalletsUsed'].describe().to_string())
            if '17612' in daily_inventory_df['SKU'].unique():
                logger.info(f"Daily PalletsUsed for SKU 17612:\n{daily_inventory_df[daily_inventory_df['SKU'] == '17612'][['Date', 'PalletsUsed']].to_string()}")
            
            total_daily_pallets_sum = daily_inventory_df.groupby('Date')['PalletsUsed'].sum()
            logger.info(f"Summed PalletsUsed per Date (head):\n{total_daily_pallets_sum.head().to_string()}")
            logger.info(f"Summed PalletsUsed per Date (tail):\n{total_daily_pallets_sum.tail().to_string()}")
        else:
            logger.warning("daily_inventory_df is empty or missing 'PalletsUsed' column before space charge calculation.")

        logger.info(f"Pallet counts used: {pallet_counts}")
        logger.info(f"Rates dictionary used: {rates}")

        daily_space_charge = daily_inventory_df.groupby('Date')['PalletsUsed'].sum() * rates.get('SpaceRentalRate', 0)
        report_df = report_df.join(daily_space_charge.rename('Space Rental Charge')).fillna(0)
        
        logger.info("--- Final Space Rental Charge in Report DataFrame ---")
        #logger.info(f"Space Rental Charge column (head):\n{report_df['Space Rental Charge'].head().to_string()}")
        #logger.info(f"Space Rental Charge column (tail):\n{report_df['Space Rental Charge'].tail().to_string()}")

        logger.info("--- Full Space Rental Charge column for audit ---")
        logger.info(report_df['Space Rental Charge'].to_string())

        report_df['Total Charge'] = report_df['Orders Charge'] + report_df['Packages Charge'] + report_df['Space Rental Charge']
        
        # Add shipped columns for key SKUs
        daily_shipped_pivot = shipped_items_df_filtered.pivot_table(index='Date', columns='SKU', values='Quantity_Shipped', aggfunc='sum').fillna(0)
        
        logger.debug(f"Key SKUs list: {key_skus_list}")
        logger.debug(f"Daily Shipped Pivot table shape: {daily_shipped_pivot.shape}")
        logger.debug(f"Daily Shipped Pivot table columns: {daily_shipped_pivot.columns.tolist()}")
        logger.debug(f"Daily Shipped Pivot table head:\n{daily_shipped_pivot.head().to_string()}")
        logger.debug(f"Daily Shipped Pivot table info:\n{daily_shipped_pivot.info()}")

        # Ensure pivot columns are string type for consistent matching
        daily_shipped_pivot.columns = daily_shipped_pivot.columns.astype(str)
        logger.debug(f"Daily Shipped Pivot table columns AFTER string conversion: {daily_shipped_pivot.columns.tolist()}")


        for sku in key_skus_list:
            sku_column_name = f'{sku}_Shipped'
            if sku in daily_shipped_pivot.columns:
                report_df[sku_column_name] = daily_shipped_pivot[sku]
                logger.debug(f"Populated '{sku_column_name}' from pivot for SKU '{sku}'. Head:\n{report_df[sku_column_name].head().to_string()}")
                logger.debug(f"Non-zero count for '{sku_column_name}': {(report_df[sku_column_name] != 0).sum()}")
            else:
                report_df[sku_column_name] = 0
                logger.warning(f"SKU '{sku}' not found in daily_shipped_pivot columns. '{sku_column_name}' column set to 0.")
                logger.debug(f"Set '{sku_column_name}' to 0. Head:\n{report_df[sku_column_name].head().to_string()}")

        # Fill NaN values in Shipped columns with 0 after they are all added
        for sku in key_skus_list:
            report_df[f'{sku}_Shipped'] = report_df[f'{sku}_Shipped'].fillna(0)
            logger.debug(f"Applied fillna(0) to '{sku}_Shipped'. Head:\n{report_df[f'{sku}_Shipped'].head().to_string()}")

        logger.debug("Report DataFrame after adding SKU_Shipped columns (head):")
        logger.debug(report_df.head().to_string())
        logger.debug("Report DataFrame after adding SKU_Shipped columns (columns and dtypes):")
        logger.debug(report_df.info())
        logger.debug("Report DataFrame after adding SKU_Shipped columns (tail):")
        logger.debug(report_df.tail().to_string())


        # Calculate totals
        totals = report_df.sum(numeric_only=True).to_frame().T
        totals['Date'] = 'TOTAL'
        
        final_report_df = pd.concat([report_df.reset_index(), totals], ignore_index=True)
        
        # --- NEW CHANGE: Define desired column order and rename headers ---
        desired_column_order_and_names = {
            'Date': 'Date',
            'Num_Orders': '# Of Orders',
            '17612_Shipped': '17612',  # Renaming SKU columns
            '17904_Shipped': '17904',
            '17914_Shipped': '17914',
            '18675_Shipped': '18675',
            '18795_Shipped': '18795', # Now explicitly included and will be formatted
            'Orders Charge': 'Orders',
            'Packages Charge': 'Packages',
            'Space Rental Charge': 'Space Rental',
            'Total Charge': 'Total'
        }

        # --- IMPORTANT: Apply the reordering and renaming ---
        # Filter and reorder columns based on desired_column_order_and_names keys
        reordered_columns = [col for col in desired_column_order_and_names.keys() if col in final_report_df.columns]
        final_report_df = final_report_df[reordered_columns]

        # Rename columns to final display names
        final_report_df = final_report_df.rename(columns=desired_column_order_and_names)

        # --- Apply final formatting for display ---
        # 1. Format Date column
        final_report_df['Date'] = final_report_df['Date'].apply(lambda x: x.strftime('%#m/%#d/%Y') if isinstance(x, datetime) else x)

        # 2. Format SKU columns (0 to '-')
        # Correctly iterate through the *renamed* SKU columns in the final DataFrame
        # Ensure all relevant SKUs from key_skus_list are included here
        final_sku_cols = [str(sku) for sku in key_skus_list if str(sku) in final_report_df.columns]
        # Adding 18795 explicitly if it's not already covered by key_skus_list (e.g. if it's not in the config list)
        if '18795' not in final_sku_cols and '18795' in final_report_df.columns:
            final_sku_cols.append('18795')
            
        for col in final_sku_cols:
            # Ensure the column is numeric before trying to replace 0 with '-'
            final_report_df[col] = pd.to_numeric(final_report_df[col], errors='coerce').fillna(0)
            final_report_df[col] = final_report_df[col].astype(str).replace('0.0', '-').replace('0', '-') # Replace both '0.0' and '0'


        # 3. Format Charge columns ($XX.YY)
        charge_cols_to_format = ['Orders', 'Packages', 'Space Rental', 'Total']
        for col in charge_cols_to_format:
            if col in final_report_df.columns: # Ensure column exists
                # Convert to numeric first, coerce errors to NaN, then fillna(0)
                final_report_df[col] = pd.to_numeric(final_report_df[col], errors='coerce').fillna(0) 

                final_report_df[col] = final_report_df[col].apply(
                    lambda x: f"${x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
                )


        logger.debug("Final Report DataFrame AFTER all formatting (head):")
        logger.debug(final_report_df.head().to_string())
        logger.debug("Final Report DataFrame AFTER all formatting (columns and dtypes):")
        logger.debug(final_report_df.info())
        logger.debug("Final Report DataFrame AFTER all formatting (tail):")
        logger.debug(final_report_df.tail().to_string())

            # Log inventory transaction summary for the month at the end for easy access
        logger.info("\n===== Inventory Transaction Summary for Month =====")
        month_transactions = inventory_transactions_df[
                (inventory_transactions_df['Date'] >= start_date) & (inventory_transactions_df['Date'] <= end_date)
            ]
        logger.info(f"Total inventory transactions for month: {len(month_transactions)}")
        if 'TransactionType' in month_transactions.columns:
                logger.info("Inventory transactions by type:")
                logger.info(month_transactions['TransactionType'].value_counts().to_string())
                logger.info("Sum of quantities by type:")
                logger.info(month_transactions.groupby('TransactionType')['Quantity'].sum().to_string())
                if 'SKU' in month_transactions.columns:
                    logger.info("Sum of quantities by TransactionType and SKU:")
                    logger.info(month_transactions.groupby(['TransactionType', 'SKU'])['Quantity'].sum().to_string())
        logger.info("===== End of Inventory Transaction Summary =====\n")

            # Log previous EOM inventory values from Configuration tab at the end for easy access
        logger.info("===== Previous End of Month (EOM) Inventory Values from Configuration Tab =====")
        for sku, qty in start_of_month_inventory.items():
                logger.info(f"SKU: {sku} | EOM Inventory: {qty}")
        logger.info("===== End of Previous EOM Inventory Values =====\n")

        # Log summary calculation for each SKU
        logger.info("===== Monthly Inventory Movement Summary by SKU =====")
        for sku in start_of_month_inventory.keys():
            bom = start_of_month_inventory.get(sku, 0)
            received = 0
            shipped = 0
            repacked = 0
            if not inventory_transactions_df.empty:
                received = inventory_transactions_df[(inventory_transactions_df['SKU'] == sku) & (inventory_transactions_df['TransactionType'] == 'Receive') & (inventory_transactions_df['Date'] >= start_date) & (inventory_transactions_df['Date'] <= end_date)]['Quantity'].sum()
                repacked = inventory_transactions_df[(inventory_transactions_df['SKU'] == sku) & (inventory_transactions_df['TransactionType'] == 'Repack') & (inventory_transactions_df['Date'] >= start_date) & (inventory_transactions_df['Date'] <= end_date)]['Quantity'].sum()
            if not shipped_items_df.empty:
                shipped = shipped_items_df[(shipped_items_df['SKU'] == sku) & (shipped_items_df['Date'] >= start_date) & (shipped_items_df['Date'] <= end_date)]['Quantity_Shipped'].sum()
            eom_calc = bom + received + repacked - shipped
            # Get actual EOM from daily_inventory_df
            actual_eom = None
            if 'daily_inventory_df' in locals() and daily_inventory_df is not None and not daily_inventory_df.empty:
                eom_row = daily_inventory_df[(daily_inventory_df['SKU'] == sku) & (daily_inventory_df['Date'] == end_date)]
                if not eom_row.empty and 'EOD_Inventory' in eom_row.columns:
                    actual_eom = int(eom_row['EOD_Inventory'].iloc[0])
            logger.info(f"SKU: {sku} | BOM: {bom} | Received: {received} | Repacked: {repacked} | Shipped: {shipped} | Calculated EOM: {eom_calc} | Actual EOM: {actual_eom}")
        logger.info("===== End of Monthly Inventory Movement Summary =====\n")

        # Log Previous End of Month (EOM) inventory values from Configuration tab at the end
        logger.info("===== Previous End of Month (EOM) Inventory Values from Configuration tab =====")
        for sku, qty in start_of_month_inventory.items():
            pallet_size = pallet_counts.get(sku, '-')  # Cases per pallet
            # Calculate pallets used (inventory pallet count, including partials)
            pallets_used = '-'
            try:
                if isinstance(pallet_size, (int, float)) and pallet_size > 0:
                    pallets_used = int(math.ceil(qty / pallet_size))
            except Exception:
                pass
            logger.info(f"SKU: {sku} | EOM Inventory: {qty} | Pallet Size: {pallet_size} | Pallets Used: {pallets_used}")
        logger.info("===== End of Previous EOM Inventory Values =====\n")

        logger.info("Monthly Charge Report generated successfully.")
        return final_report_df, None
    except Exception as e:
        logger.error(f"Error generating monthly charge report: {e}", exc_info=True)
        return None, None
# src/daily_shipment_processor.py
import sys
import os
import logging
import datetime
import pandas as pd

# --- Dynamic Path Adjustment for Module Imports ---
# Add the project root to the Python path to enable imports from services and utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import Constants and Modules ---

# Import constants and environment detection from settings.py
from config.settings import (
    SHIPSTATION_SHIPMENTS_ENDPOINT,
    IS_CLOUD_ENV, IS_LOCAL_ENV, SERVICE_ACCOUNT_KEY_PATH
)

# Import necessary modules
from utils.logging_config import setup_logging
from src.services.data_processing.shipment_processor import (     
    process_shipped_items,
    process_shipped_orders,
    aggregate_weekly_shipped_history # Re-added for weekly aggregation
)
# Import database utilities for SQLite operations
from src.services.database.db_utils import execute_query, transaction
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    fetch_shipstation_shipments
)



# --- Environment-Aware Logging Configuration ---
if IS_LOCAL_ENV:
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'daily_processor.log')
    setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
elif IS_CLOUD_ENV:
    # In cloud, log to stdout/stderr only (Google Cloud Logging will pick up)
    setup_logging(log_file_path=None, log_level=logging.INFO, enable_console_logging=True)
else:
    # Fallback: log to console only
    setup_logging(log_file_path=None, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)

# --- DEBUG: Print and log service account key path, existence, environment, project ID, and secret names ---
print(f"[DEBUG] SERVICE_ACCOUNT_KEY_PATH: {SERVICE_ACCOUNT_KEY_PATH}")
print(f"[DEBUG] SERVICE_ACCOUNT_KEY_PATH exists: {os.path.exists(SERVICE_ACCOUNT_KEY_PATH) if SERVICE_ACCOUNT_KEY_PATH else 'None'}")
print(f"[DEBUG] IS_LOCAL_ENV: {IS_LOCAL_ENV}")
print(f"[DEBUG] IS_CLOUD_ENV: {IS_CLOUD_ENV}")
import config.settings as _settings
print(f"[DEBUG] YOUR_GCP_PROJECT_ID: {_settings.YOUR_GCP_PROJECT_ID}")
print(f"[DEBUG] SHIPSTATION_API_KEY_SECRET_ID: {_settings.SHIPSTATION_API_KEY_SECRET_ID}")
print(f"[DEBUG] SHIPSTATION_API_SECRET_SECRET_ID: {_settings.SHIPSTATION_API_SECRET_SECRET_ID}")
logger.info(f"[DEBUG] SERVICE_ACCOUNT_KEY_PATH: {SERVICE_ACCOUNT_KEY_PATH}")
logger.info(f"[DEBUG] SERVICE_ACCOUNT_KEY_PATH exists: {os.path.exists(SERVICE_ACCOUNT_KEY_PATH) if SERVICE_ACCOUNT_KEY_PATH else 'None'}")
logger.info(f"[DEBUG] IS_LOCAL_ENV: {IS_LOCAL_ENV}")
logger.info(f"[DEBUG] IS_CLOUD_ENV: {IS_CLOUD_ENV}")
logger.info(f"[DEBUG] YOUR_GCP_PROJECT_ID: {_settings.YOUR_GCP_PROJECT_ID}")
logger.info(f"[DEBUG] SHIPSTATION_API_KEY_SECRET_ID: {_settings.SHIPSTATION_API_KEY_SECRET_ID}")
logger.info(f"[DEBUG] SHIPSTATION_API_SECRET_SECRET_ID: {_settings.SHIPSTATION_API_SECRET_SECRET_ID}")


def update_weekly_history_incrementally(daily_items_df, existing_history_df, target_skus, shipment_data):
    # --- Ensure all variables are defined before use ---
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())

    # After filtering for current week, log the DataFrame and unique SKUs
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()
    # Debug print for SKU 17612 quantity in current week
    sku_17612_df = current_week_items_df[current_week_items_df['Base SKU'] == '17612']
    print("\n[DEBUG] Current week total Quantity Shipped for SKU 17612:", sku_17612_df['Quantity Shipped'].sum())
    print("[DEBUG] Current week rows for SKU 17612:")
    print(sku_17612_df)
    logger.info(f"Full current_week_items_df for current week:\n{current_week_items_df}")
    logger.info(f"current_week_items_df shape: {current_week_items_df.shape}")
    logger.info(f"current_week_items_df head:\n{current_week_items_df.head(10)}")
    logger.info(f"Unique 'Base SKU' values in current_week_items_df: {sorted(current_week_items_df['Base SKU'].unique())}")
    """
    Updates the 52-week history with the latest data for the current week.

    Args:
        daily_items_df (pd.DataFrame): DataFrame with the last 32 days of granular shipped items.
        existing_history_df (pd.DataFrame): DataFrame with the current 52-week history.
        target_skus (list): A list of SKUs to be included in the weekly history.

    Returns:
        pd.DataFrame: The updated 52-week history DataFrame.      
    """
    logger.info("Starting incremental update of the 52-week history tab...")

    """
    Updates the 52-week history with the latest data for the current week.

    Args:
        daily_items_df (pd.DataFrame): DataFrame with the last 32 days of granular shipped items.
        existing_history_df (pd.DataFrame): DataFrame with the current 52-week history.
        target_skus (list): A list of SKUs to be included in the weekly history.

    Returns:
        pd.DataFrame: The updated 52-week history DataFrame.      
    """


    # Ensure 'Ship Date' is in datetime format
    daily_items_df['Ship Date'] = pd.to_datetime(daily_items_df['Ship Date']).dt.date

    logger.info(f"Current week starts on: {start_of_current_week}")
    logger.info(f"Unique Ship Dates in daily_items_df: {sorted(daily_items_df['Ship Date'].unique())}")
    logger.info(f"Min Ship Date: {daily_items_df['Ship Date'].min()}, Max Ship Date: {daily_items_df['Ship Date'].max()}")

    # Now safe to filter and log current week items
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()
    logger.info(f"current_week_items_df shape: {current_week_items_df.shape}")
    logger.info(f"current_week_items_df head:\n{current_week_items_df.head(10)}")
    logger.info(f"Unique 'Base SKU' values in current_week_items_df: {sorted(current_week_items_df['Base SKU'].unique())}")

    # Determine the start of the current week (Monday)
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())
    logger.info(f"Current week starts on: {start_of_current_week}")
    # Debug: Show unique Ship Dates and min/max
    logger.debug(f"Unique Ship Dates in daily_items_df: {sorted(daily_items_df['Ship Date'].unique())}")
    logger.debug(f"Min Ship Date: {daily_items_df['Ship Date'].min()}, Max Ship Date: {daily_items_df['Ship Date'].max()}")

    # --- DEBUG LOGGING FOR SKU 17612 ---
    logger.debug(f"Today's date: {today}")
    logger.debug("Today's shipments for SKU 17612:")
    logger.debug(daily_items_df[daily_items_df['Base SKU'] == '17612'])
    if not existing_history_df.empty:
        last_row = existing_history_df.tail(1)
        logger.debug("Last row in ORA_Weekly_Shipped_History:")   
        logger.debug(last_row)
        if '17612' in existing_history_df.columns:
            logger.debug(f"Value for 17612 in last row: {last_row['17612'].values[0]}")
        logger.debug(f"Last week Start Date: {last_row['Start Date'].values[0]}, Stop Date: {last_row['Stop Date'].values[0]}")     
    today_sum = daily_items_df[daily_items_df['Base SKU'] == '17612']['Quantity Shipped'].sum()
    logger.debug(f"Sum of today's shipments for SKU 17612: {today_sum}")

    # Filter the daily items to get only shipments from the current week
    current_week_items_df = daily_items_df[daily_items_df['Ship Date'] >= start_of_current_week].copy()

    logger.debug("Filtered daily_items_df for current week:")     
    logger.debug(current_week_items_df)

    for sku in target_skus:
        sku_filtered = current_week_items_df[current_week_items_df['Base SKU'].astype(str) == str(sku)]
        logger.debug(f"Current week items for SKU {sku}:")        
        logger.debug(sku_filtered)

    if current_week_items_df.empty:
        logger.info("No shipments found for the current week yet. History remains unchanged.")
        return existing_history_df

    # Aggregate this new weekly data using the original raw shipment data filtered for the current week
    # This assumes you have access to the original shipment_data (raw API response) in scope
    # You may need to pass shipment_data as an argument to this function if not already available
    def filter_shipments_for_week(shipment_data, start_of_week, end_of_week):
        filtered = []
        for s in shipment_data:
            ship_date = s.get('shipDate')
            if ship_date:
                ship_date_dt = datetime.datetime.strptime(ship_date[:10], '%Y-%m-%d').date()
                if start_of_week <= ship_date_dt <= start_of_week + datetime.timedelta(days=6):
                    filtered.append(s)
        return filtered

    current_week_shipments = filter_shipments_for_week(shipment_data, start_of_current_week, start_of_current_week + datetime.timedelta(days=6))
    current_week_summary_df = aggregate_weekly_shipped_history(   
        current_week_shipments,
        target_skus
    )

    # Debug print: show the summary DataFrame and the row to be written
    print("\n[DEBUG] Aggregated weekly summary DataFrame (current_week_summary_df):")
    print(current_week_summary_df)
    if not current_week_summary_df.empty:
        print("[DEBUG] Aggregated values by SKU for the current week:")
        for sku in target_skus:
            print(f"  SKU {sku}: {current_week_summary_df.iloc[0].get(str(sku), 'N/A')}")
        print("[DEBUG] Full row to be written to sheet:")
        print(current_week_summary_df.iloc[0])

    if current_week_summary_df.empty:
        logger.warning("Aggregation of current week's data resulted in an empty DataFrame.")
        return existing_history_df

    # The first row of the summary is the one we want
    new_week_row = current_week_summary_df.iloc[0]

    # Check if the existing history already has a row for this week
    existing_history_df['Start Date'] = pd.to_datetime(existing_history_df['Start Date']).dt.date
    week_exists = start_of_current_week in existing_history_df['Start Date'].values

    if week_exists:
        logger.info("Current week found in history. Updating the last row.")
        # Update the last row, assuming it's the current week     
        # A safer method would be to find the index by date       
        idx_to_update = existing_history_df[existing_history_df['Start Date'] == start_of_current_week].index
        existing_history_df.loc[idx_to_update] = new_week_row.values
    else:
        logger.info("This is a new week. Appending new week and removing the oldest.")
        # Append the new row and drop the oldest
        updated_history_df = pd.concat([existing_history_df, new_week_row.to_frame().T], ignore_index=True)
        # Sort by date to be sure, then drop the first row        
        updated_history_df = updated_history_df.sort_values(by='Start Date', ascending=True)
        updated_history_df = updated_history_df.iloc[1:]
        existing_history_df = updated_history_df


    # --- DEDUPLICATION STEP: Ensure only one entry per week (by Start Date and Stop Date), keeping the most recent ---
    # Sort by Start Date and Stop Date to ensure consistent ordering
    existing_history_df = existing_history_df.sort_values(by=["Start Date", "Stop Date", "Ship Date" if "Ship Date" in existing_history_df.columns else "Start Date"], ascending=True)
    # Drop duplicates, keeping the last (most recent) entry for each week
    before_dedup = len(existing_history_df)
    existing_history_df = existing_history_df.drop_duplicates(subset=["Start Date", "Stop Date"], keep="last").reset_index(drop=True)
    after_dedup = len(existing_history_df)
    logger.info(f"Deduplication complete: {before_dedup - after_dedup} duplicate week(s) removed. {after_dedup} unique weeks remain.")

    # --- ENFORCE 52 WEEKS: Trim to most recent 52 weeks (by Start Date) ---
    if len(existing_history_df) > 52:
        logger.info(f"History has {len(existing_history_df)} weeks. Trimming to the most recent 52 weeks.")
        existing_history_df = existing_history_df.sort_values(by="Start Date", ascending=True).iloc[-52:].reset_index(drop=True)    
    elif len(existing_history_df) < 52:
        logger.warning(f"History has only {len(existing_history_df)} weeks. (No padding implemented.)")

    logger.info(f"History now contains {len(existing_history_df)} weeks after enforcing 52-week rule.")

    # --- ENSURE CURRENT WEEK IS PRESENT AND CORRECT ---
    # (This logic is already handled above: update or append current week)

    # --- FINAL VALIDATION: Ensure all requirements are met ---   
    # 1. No duplicate weeks
    num_dupes = existing_history_df.duplicated(subset=["Start Date", "Stop Date"]).sum()
    # 2. Exactly 52 weeks
    num_weeks = len(existing_history_df)
    # 3. Most recent week is current week
    most_recent_start = existing_history_df['Start Date'].max()   
    expected_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())

    logger.info(f"Validation: {num_dupes} duplicate week(s) found. {num_weeks} total weeks. Most recent week: {most_recent_start}, Expected: {expected_start}.")

    assert num_dupes == 0, "Duplicate weeks found after deduplication!"
    # Allow fewer than 52 weeks during database initialization
    if num_weeks < 52:
        logger.warning(f"Weekly history has only {num_weeks} weeks (< 52). This is expected during initial data population.")
    elif num_weeks > 52:
        logger.error(f"Weekly history has {num_weeks} weeks (> 52). This should not happen after 52-week enforcement.")
    
    assert most_recent_start == expected_start, f"Most recent week ({most_recent_start}) is not the current week ({expected_start})"

    logger.info("Weekly history update successful: deduplication, week count validation, and current week validation all passed.")    

    return existing_history_df


def save_shipped_orders_to_db(orders_df):
    """Save shipped orders to database with UPSERT by order_number
    
    Schema: shipped_orders(ship_date, order_number UNIQUE, customer_email, total_items, shipstation_order_id)
    Input DataFrame columns: Ship Date, OrderNumber
    """
    if orders_df.empty:
        logger.warning("No orders to save to database")
        return 0
    
    logger.info(f"Saving {len(orders_df)} shipped orders to database...")
    records_saved = 0
    
    with transaction() as conn:
        for _, row in orders_df.iterrows():
            ship_date = row.get('Ship Date')
            order_number = row.get('OrderNumber')
            
            if not order_number or not ship_date:
                logger.warning(f"Skipping row with missing order_number or ship_date: {row}")
                continue
            
            conn.execute("""
                INSERT INTO shipped_orders (ship_date, order_number)
                VALUES (?, ?)
                ON CONFLICT(order_number) DO UPDATE SET
                    ship_date = excluded.ship_date
            """, (str(ship_date), str(order_number)))
            records_saved += 1
    
    logger.info(f"Successfully saved {records_saved} shipped orders to database")
    return records_saved


def save_shipped_items_to_db(items_df):
    """Save shipped items to database with UPSERT
    
    Schema: shipped_items(ship_date, sku_lot, base_sku, quantity_shipped, order_number)
    UNIQUE(order_number, base_sku, sku_lot)
    Input DataFrame columns: Ship Date, SKU - Lot, Base SKU, Quantity Shipped, OrderNumber
    """
    if items_df.empty:
        logger.warning("No items to save to database")
        return 0
    
    logger.info(f"Saving {len(items_df)} shipped items to database...")
    records_saved = 0
    
    with transaction() as conn:
        for _, row in items_df.iterrows():
            ship_date = row.get('Ship Date')
            sku_lot = row.get('SKU - Lot', '')
            base_sku = row.get('Base SKU')
            quantity = row.get('Quantity Shipped')
            order_number = row.get('OrderNumber')
            
            if not ship_date or not base_sku or not quantity:
                logger.warning(f"Skipping row with missing required fields: {row}")
                continue
            
            # Ensure sku_lot is never None/NaN - coalesce to empty string
            sku_lot = str(sku_lot) if sku_lot and str(sku_lot) != 'nan' else ''
            
            conn.execute("""
                INSERT INTO shipped_items (
                    ship_date, sku_lot, base_sku, quantity_shipped, order_number
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(order_number, base_sku, sku_lot) DO UPDATE SET
                    ship_date = excluded.ship_date,
                    quantity_shipped = excluded.quantity_shipped
            """, (str(ship_date), sku_lot, str(base_sku), int(quantity), str(order_number) if order_number else None))
            records_saved += 1
    
    logger.info(f"Successfully saved {records_saved} shipped items to database")
    return records_saved


def save_weekly_history_to_db(history_df):
    """Save weekly shipped history to database with UPSERT"""
    if history_df.empty:
        logger.warning("No weekly history to save to database")
        return 0
    
    logger.info(f"Saving {len(history_df)} weeks of history to database...")
    records_saved = 0
    
    # Get SKU columns (all columns except Start Date, Stop Date, Ship Date)
    date_columns = ['Start Date', 'Stop Date', 'Ship Date']
    sku_columns = [col for col in history_df.columns if col not in date_columns]
    
    with transaction() as conn:
        for _, row in history_df.iterrows():
            start_date = row.get('Start Date')
            end_date = row.get('Stop Date')
            
            # Insert/update a row for each SKU in this week
            for sku in sku_columns:
                quantity = row.get(sku, 0)
                # Skip if quantity is not a number or is 0
                try:
                    quantity = int(float(quantity)) if quantity and str(quantity).strip() else 0
                except (ValueError, TypeError):
                    quantity = 0
                
                if quantity > 0:
                    conn.execute("""
                        INSERT INTO weekly_shipped_history (
                            start_date, end_date, sku, quantity_shipped
                        ) VALUES (?, ?, ?, ?)
                        ON CONFLICT(start_date, end_date, sku) DO UPDATE SET
                            quantity_shipped = excluded.quantity_shipped
                    """, (str(start_date), str(end_date), sku, quantity))
                    records_saved += 1
    
    logger.info(f"Successfully saved {records_saved} weekly history records to database")
    return records_saved


def get_weekly_history_from_db(target_skus):
    """Get weekly shipped history from database for specified SKUs"""
    logger.info("Loading weekly shipped history from database...")
    
    try:
        # Get all weekly history for target SKUs
        rows = execute_query("""
            SELECT start_date, end_date, sku, quantity_shipped
            FROM weekly_shipped_history
            WHERE sku IN ({})
            ORDER BY start_date, sku
        """.format(','.join('?' * len(target_skus))), tuple(target_skus))
        
        if not rows:
            logger.warning("No weekly history found in database")
            # Return empty DataFrame with expected structure
            expected_columns = ['Start Date', 'Stop Date'] + target_skus
            return pd.DataFrame(columns=expected_columns)
        
        # Convert to wide format (one row per week, one column per SKU)
        df = pd.DataFrame(rows, columns=['Start Date', 'Stop Date', 'SKU', 'Quantity Shipped'])
        df['Start Date'] = pd.to_datetime(df['Start Date']).dt.date
        df['Stop Date'] = pd.to_datetime(df['Stop Date']).dt.date
        
        # Pivot to wide format
        history_df = df.pivot_table(
            index=['Start Date', 'Stop Date'],
            columns='SKU',
            values='Quantity Shipped',
            fill_value=0
        ).reset_index()
        
        # Ensure all target SKUs are present as columns
        for sku in target_skus:
            if sku not in history_df.columns:
                history_df[sku] = 0
        
        # Reorder columns
        column_order = ['Start Date', 'Stop Date'] + target_skus
        history_df = history_df[column_order]
        
        logger.info(f"Loaded {len(history_df)} weeks of history from database")
        return history_df
        
    except Exception as e:
        logger.error(f"Error loading weekly history from database: {e}", exc_info=True)
        expected_columns = ['Start Date', 'Stop Date'] + target_skus
        return pd.DataFrame(columns=expected_columns)


def run_daily_shipment_pull(request=None):
    """
    Main function for the daily shipment processor.
    Pulls a 32-day rolling window of shipment data from ShipStation and
    saves to SQLite database tables: shipped_orders, shipped_items, weekly_shipped_history.

    Args:
        request: The request object from a Google Cloud Function trigger (optional).
    """

    logger.info("--- Starting Daily Shipment Processor ---")
    
    # Initialize workflow tracking
    workflow_start_time = datetime.datetime.now()
    try:
        # Create or update workflow record
        with transaction() as conn:
            conn.execute("""
                INSERT INTO workflows (name, display_name, status, last_run_at)
                VALUES ('daily_shipment_processor', 'Daily Shipment Processor', 'running', CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    status = 'running',
                    last_run_at = CURRENT_TIMESTAMP
            """)
        
    except Exception as e:
        logger.error(f"Failed to initialize workflow tracking: {e}")
    
    try:
        # --- 1. Get ShipStation Credentials (Environment-Aware) ---
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.critical("Failed to get ShipStation credentials.")
            return "Failed to get credentials", 500

        # --- 2. Determine the 32-Day Rolling Date Range ---
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=40)
        end_date_str = today.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')
        logger.info(f"Using rolling 32-day date range: {start_date_str} to {end_date_str}")
        logger.info(f"Environment: {'CLOUD' if IS_CLOUD_ENV else 'LOCAL' if IS_LOCAL_ENV else 'UNKNOWN'}")
        logger.info(f"Service Account Key Path: {SERVICE_ACCOUNT_KEY_PATH}")

        # --- 3. Fetch Data from ShipStation API ---
        shipment_data = fetch_shipstation_shipments(
            api_key=api_key,
            api_secret=api_secret,
            shipments_endpoint=SHIPSTATION_SHIPMENTS_ENDPOINT,    
            start_date=start_date_str,
            end_date=end_date_str,
            shipment_status="shipped"
        )

        if not shipment_data:
            logger.warning("No shipment data returned from ShipStation API for the specified range. Exiting.")
            return "No data returned from API", 200

        non_voided_shipments = [shipment for shipment in shipment_data if not shipment.get('voided', False)]
        logger.info(f"Processing {len(non_voided_shipments)} non-voided shipments.")

        if not non_voided_shipments:
            logger.info("No non-voided shipments to process. Exiting.")
            return "No non-voided shipments", 200

        # --- 4. Process Data into DataFrames ---
        logger.info("Processing data for Shipped_Items_Data tab...")
        items_df = process_shipped_items(non_voided_shipments)    

        logger.info("Processing data for Shipped_Orders_Data table...")
        orders_df = process_shipped_orders(non_voided_shipments)  

        # --- 5. Save to Database Tables ---
        # Save orders first, then items (respects foreign key constraint)
        orders_saved = save_shipped_orders_to_db(orders_df)
        items_saved = save_shipped_items_to_db(items_df)

        # --- 6. Incrementally Update the Weekly Shipped History ---
        logger.info("Fetching existing 52-week history from database...")
        
        # Get target SKUs from configuration_params
        target_skus_rows = execute_query("""
            SELECT sku FROM configuration_params
            WHERE category = 'Key Products'
            ORDER BY sku
        """)
        target_skus = [str(row[0]) for row in target_skus_rows] if target_skus_rows else ['17612', '17904', '17914', '18675', '18795']
        
        existing_history_df = get_weekly_history_from_db(target_skus)
        updated_history_df = update_weekly_history_incrementally(items_df.copy(), existing_history_df.copy(), target_skus, shipment_data)
        
        history_saved = save_weekly_history_to_db(updated_history_df)
        
        # --- 7. Update Workflow Status ---
        total_records = items_saved + orders_saved + history_saved
        duration = (datetime.datetime.now() - workflow_start_time).total_seconds()
        
        with transaction() as conn:
            conn.execute("""
                UPDATE workflows 
                SET status = 'completed',
                    records_processed = ?,
                    duration_seconds = CAST(? AS INTEGER)
                WHERE name = 'daily_shipment_processor'
            """, (total_records, duration))
        
        logger.info(f"--- Daily Shipment Processor finished successfully! ---")
        logger.info(f"Total records processed: {total_records} (items: {items_saved}, orders: {orders_saved}, history: {history_saved})")
        return "Process completed successfully", 200

    except Exception as e:
        logger.critical(f"An unhandled error occurred in the daily shipment processor: {e}", exc_info=True)
        
        # Update workflow status to failed
        try:
            with transaction() as conn:
                conn.execute("""
                    UPDATE workflows 
                    SET status = 'failed',
                        error_message = ?
                    WHERE name = 'daily_shipment_processor'
                """, (str(e)[:500],))
        except Exception as workflow_err:
            logger.error(f"Failed to update workflow status: {workflow_err}")
        
        return f"An error occurred: {e}", 500

# This allows the script to be run directly for testing purposes
if __name__ == "__main__":
    run_daily_shipment_pull()

# Google Cloud Function entry point
def daily_shipment_processor_http_trigger(request):
    """
    Google Cloud Function HTTP trigger for daily-weekly-history-update.
    Mirrors the pattern used in the shipstation reporter module.
    """
    return run_daily_shipment_pull(request)
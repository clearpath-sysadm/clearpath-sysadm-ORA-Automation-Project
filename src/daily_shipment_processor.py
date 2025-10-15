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
from src.services.database.pg_utils import execute_query, transaction
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    fetch_shipstation_shipments
)
# Import week utilities for handling complete vs partial weeks
from src.services.reporting_logic.week_utils import (
    get_current_week_boundaries,
    is_week_complete,
    get_prior_complete_week_boundaries
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
    """
    Updates the 52-week history with COMPLETE weeks only (excludes current/partial week).
    
    IMPORTANT: Only processes weeks where Sunday has passed. The current/partial week
    is excluded to prevent artificially lowering the 52-week rolling average.

    Args:
        daily_items_df (pd.DataFrame): DataFrame with the last 32 days of granular shipped items.
        existing_history_df (pd.DataFrame): DataFrame with the current 52-week history.
        target_skus (list): A list of SKUs to be included in the weekly history.
        shipment_data: Raw shipment data from ShipStation API.

    Returns:
        pd.DataFrame: The updated 52-week history DataFrame (only complete weeks).      
    """
    logger.info("Starting incremental update of the 52-week history (COMPLETE weeks only)...")
    
    # Get current and prior week boundaries
    current_monday, current_sunday = get_current_week_boundaries()
    prior_monday, prior_sunday = get_prior_complete_week_boundaries()
    today = datetime.date.today()
    
    logger.info(f"Today: {today}")
    
    # Determine which week to process based on completeness
    # If current week is complete (today is Saturday/Sunday after Friday), process current week
    # Otherwise, process prior week
    if is_week_complete(current_sunday):
        processed_week_start = current_monday
        processed_week_end = current_sunday
        logger.info(f"Current week is COMPLETE (Friday has passed). Processing current week: {current_monday} to {current_sunday}")
    else:
        processed_week_start = prior_monday
        processed_week_end = prior_sunday
        logger.info(f"Current week is INCOMPLETE. Processing prior complete week: {prior_monday} to {prior_sunday}")
    
    # Ensure 'Ship Date' is in datetime format
    daily_items_df['Ship Date'] = pd.to_datetime(daily_items_df['Ship Date']).dt.date
    
    logger.info(f"Ship dates range: {daily_items_df['Ship Date'].min()} to {daily_items_df['Ship Date'].max()}")
    
    # Filter for the processed week (prior complete week) only
    processed_week_items_df = daily_items_df[
        (daily_items_df['Ship Date'] >= processed_week_start) &
        (daily_items_df['Ship Date'] <= processed_week_end)
    ].copy()
    
    logger.info(f"Found {len(processed_week_items_df)} shipment items for processed week {processed_week_start} to {processed_week_end}")
    
    if processed_week_items_df.empty:
        logger.info(f"No shipments found for the processed week ({processed_week_start} to {processed_week_end}). "
                   "Purging any incomplete weeks and returning existing history.")
        # Purge any incomplete weeks (>= next Monday) from existing history
        next_monday = current_monday + datetime.timedelta(days=7)
        existing_history_df['Start Date'] = pd.to_datetime(existing_history_df['Start Date']).dt.date
        existing_history_df = existing_history_df[existing_history_df['Start Date'] < next_monday].reset_index(drop=True)
        return existing_history_df
    
    # Helper function to filter raw shipment data for a specific week
    def filter_shipments_for_week(shipment_data, start_date, end_date):
        filtered = []
        for s in shipment_data:
            ship_date_str = s.get('shipDate')
            if ship_date_str:
                ship_date = datetime.datetime.strptime(ship_date_str[:10], '%Y-%m-%d').date()
                if start_date <= ship_date <= end_date:
                    filtered.append(s)
        return filtered
    
    # Get shipments for the processed week
    processed_week_shipments = filter_shipments_for_week(
        shipment_data, processed_week_start, processed_week_end
    )
    
    # Aggregate the processed week's data
    processed_week_summary_df = aggregate_weekly_shipped_history(
        processed_week_shipments,
        target_skus
    )
    
    if processed_week_summary_df.empty:
        logger.warning(f"Aggregation of processed week ({processed_week_start} to {processed_week_end}) resulted in empty DataFrame.")
        # Still purge incomplete weeks before returning
        next_monday = current_monday + datetime.timedelta(days=7)
        existing_history_df['Start Date'] = pd.to_datetime(existing_history_df['Start Date']).dt.date
        existing_history_df = existing_history_df[existing_history_df['Start Date'] < next_monday].reset_index(drop=True)
        return existing_history_df
    
    # Get the aggregated row
    new_week_row = processed_week_summary_df.iloc[0]
    
    logger.info(f"Aggregated data for week {processed_week_start} to {processed_week_end}")
    
    # Ensure Start Date column is datetime for comparison
    existing_history_df['Start Date'] = pd.to_datetime(existing_history_df['Start Date']).dt.date
    
    # Check if this week already exists in history
    week_exists = processed_week_start in existing_history_df['Start Date'].values
    
    if week_exists:
        logger.info(f"Week {processed_week_start} already exists in history. Updating it.")
        idx_to_update = existing_history_df[existing_history_df['Start Date'] == processed_week_start].index
        existing_history_df.loc[idx_to_update] = new_week_row.values
    else:
        logger.info(f"Week {processed_week_start} is new. Appending to history.")
        updated_history_df = pd.concat([existing_history_df, new_week_row.to_frame().T], ignore_index=True)
        updated_history_df = updated_history_df.sort_values(by='Start Date', ascending=True)
        # If we now have more than 52 weeks, drop the oldest
        if len(updated_history_df) > 52:
            updated_history_df = updated_history_df.iloc[-52:]
        existing_history_df = updated_history_df
    
    # PURGE any incomplete future weeks (rows with Start Date >= next Monday)
    # This allows completed weeks (e.g., on Saturday/Sunday) to remain in history
    next_monday = current_monday + datetime.timedelta(days=7)
    before_purge = len(existing_history_df)
    existing_history_df = existing_history_df[existing_history_df['Start Date'] < next_monday].reset_index(drop=True)
    after_purge = len(existing_history_df)
    if before_purge > after_purge:
        logger.info(f"Purged {before_purge - after_purge} incomplete week(s) (Start Date >= {next_monday})")
    
    # Deduplication: Ensure only one entry per week
    existing_history_df = existing_history_df.sort_values(by=["Start Date", "Stop Date"], ascending=True)
    before_dedup = len(existing_history_df)
    existing_history_df = existing_history_df.drop_duplicates(subset=["Start Date", "Stop Date"], keep="last").reset_index(drop=True)
    after_dedup = len(existing_history_df)
    if before_dedup > after_dedup:
        logger.info(f"Deduplication removed {before_dedup - after_dedup} duplicate(s). {after_dedup} unique weeks remain.")
    
    # Enforce 52-week limit
    if len(existing_history_df) > 52:
        logger.info(f"History has {len(existing_history_df)} weeks. Trimming to most recent 52.")
        existing_history_df = existing_history_df.sort_values(by="Start Date", ascending=True).iloc[-52:].reset_index(drop=True)
    
    logger.info(f"Final history contains {len(existing_history_df)} weeks")
    
    # Validation
    num_dupes = existing_history_df.duplicated(subset=["Start Date", "Stop Date"]).sum()
    num_weeks = len(existing_history_df)
    most_recent_start = existing_history_df['Start Date'].max() if not existing_history_df.empty else None
    
    logger.info(f"Validation: {num_dupes} duplicates, {num_weeks} total weeks, most recent week: {most_recent_start}")
    
    assert num_dupes == 0, "Duplicate weeks found after deduplication!"
    
    if num_weeks < 52:
        logger.warning(f"History has only {num_weeks} weeks (< 52). Expected during initial data population.")
    elif num_weeks > 52:
        logger.error(f"History has {num_weeks} weeks (> 52). This should not happen after enforcement!")
    
    # Most recent week should be the processed week (prior complete week), NOT current week
    if most_recent_start and most_recent_start != processed_week_start:
        logger.warning(f"Most recent week ({most_recent_start}) is not the processed week ({processed_week_start}). "
                      "This may be normal if processed week had no shipments.")
    
    logger.info("Weekly history update successful (COMPLETE weeks only, partial week excluded).")
    
    return existing_history_df


def save_shipped_orders_to_db(orders_df):
    """Save shipped orders to database with UPSERT by order_number
    
    Schema: shipped_orders(ship_date, order_number UNIQUE, customer_email, total_items, shipstation_order_id)
    Input DataFrame columns: Ship Date, OrderNumber, ShipStationOrderId
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
            shipstation_order_id = row.get('ShipStationOrderId', '')
            
            if not order_number or not ship_date:
                logger.warning(f"Skipping row with missing order_number or ship_date: {row}")
                continue
            
            shipstation_order_id = str(shipstation_order_id) if shipstation_order_id and str(shipstation_order_id) != 'nan' else None
            
            cursor = conn.cursor()

            
            cursor.execute("""
                INSERT INTO shipped_orders (ship_date, order_number, shipstation_order_id)
                VALUES (%s, %s, %s)
                ON CONFLICT(order_number) DO UPDATE SET
                    ship_date = excluded.ship_date,
                    shipstation_order_id = excluded.shipstation_order_id
            """, (str(ship_date), str(order_number), shipstation_order_id))
            records_saved += 1
    
    logger.info(f"Successfully saved {records_saved} shipped orders to database")
    return records_saved


def save_shipped_items_to_db(items_df):
    """Save shipped items to database with UPSERT
    
    Schema: shipped_items(ship_date, sku_lot, base_sku, quantity_shipped, order_number, tracking_number)
    UNIQUE(order_number, base_sku, sku_lot)
    Input DataFrame columns: Ship Date, SKU - Lot, Base SKU, Quantity Shipped, OrderNumber, TrackingNumber
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
            tracking_number = row.get('TrackingNumber', '')
            
            if not ship_date or not base_sku or not quantity:
                logger.warning(f"Skipping row with missing required fields: {row}")
                continue
            
            # Ensure sku_lot is never None/NaN - coalesce to empty string
            sku_lot = str(sku_lot) if sku_lot and str(sku_lot) != 'nan' else ''
            tracking_number = str(tracking_number) if tracking_number and str(tracking_number) != 'nan' else ''
            
            cursor = conn.cursor()

            
            cursor.execute("""
                INSERT INTO shipped_items (
                    ship_date, sku_lot, base_sku, quantity_shipped, order_number, tracking_number
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(order_number, base_sku, sku_lot) DO UPDATE SET
                    ship_date = excluded.ship_date,
                    quantity_shipped = excluded.quantity_shipped,
                    tracking_number = excluded.tracking_number
            """, (str(ship_date), sku_lot, str(base_sku), int(quantity), str(order_number) if order_number else None, tracking_number))
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
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO weekly_shipped_history (
                            start_date, end_date, sku, quantity_shipped
                        ) VALUES (%s, %s, %s, %s)
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
            cursor = conn.cursor()

            cursor.execute("""
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
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE workflows 
                SET status = 'completed',
                    records_processed = %s,
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
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE workflows 
                    SET status = 'failed',
                        error_message = %s
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
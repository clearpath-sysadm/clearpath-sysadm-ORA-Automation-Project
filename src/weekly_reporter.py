import pandas as pd
import datetime
import logging
import os
import sys

# Add the project root to the Python path to enable imports from services and config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import database utilities
from src.services.database.pg_utils import execute_query, upsert, transaction, is_workflow_enabled, update_workflow_last_run

# Import inventory and average calculations from their modules
from src.services.reporting_logic.inventory_calculations import calculate_current_inventory
from src.services.reporting_logic.average_calculations import calculate_12_month_rolling_average

# Import centralized configuration settings
from config.settings import settings

# --- Environment Detection ---
ENV = getattr(settings, 'get_environment', lambda: 'unknown')()
IS_LOCAL_ENV = ENV == 'local'
IS_CLOUD_ENV = ENV == 'cloud'

# --- Logging Setup ---
logger = logging.getLogger('weekly_reporter')
logger.setLevel(logging.DEBUG)
if IS_LOCAL_ENV:
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'weekly_reporter.log')
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
else:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False
logger.info(f"Weekly Reporter started. Environment: {ENV.upper()}")


def get_key_skus_from_db():
    """Get key SKUs and product names from configuration_params table"""
    logger.info("Loading key SKUs from database...")
    try:
        rows = execute_query("""
            SELECT sku, value as product_name
            FROM configuration_params
            WHERE category = 'Key Products'
            ORDER BY sku
        """)
        
        if not rows:
            logger.error("No key SKUs found in database")
            return [], pd.DataFrame()
        
        key_skus_list = [row[0] for row in rows]
        product_names_map = pd.DataFrame(rows, columns=['SKU', 'Product Name'])
        
        logger.info(f"Loaded {len(key_skus_list)} key SKUs from database")
        return key_skus_list, product_names_map
    except Exception as e:
        logger.error(f"Error loading key SKUs from database: {e}", exc_info=True)
        return [], pd.DataFrame()


def get_initial_inventory_from_db():
    """Get initial inventory from configuration_params table"""
    logger.info("Loading initial inventory from database...")
    try:
        rows = execute_query("""
            SELECT sku, CAST(value AS INTEGER) as quantity
            FROM configuration_params
            WHERE category = 'InitialInventory'
        """)
        
        if not rows:
            logger.warning("No initial inventory found in database")
            return {}
        
        # Convert to dict, using latest value for duplicate SKUs
        initial_inventory = {}
        for sku, qty in rows:
            initial_inventory[str(sku)] = qty
        
        logger.info(f"Loaded initial inventory for {len(initial_inventory)} SKUs")
        return initial_inventory
    except Exception as e:
        logger.error(f"Error loading initial inventory: {e}", exc_info=True)
        return {}


def get_weekly_shipped_history_from_db(key_skus_list):
    """Get 52-week shipped history from database"""
    logger.info("Loading weekly shipped history from database...")
    try:
        # Get all 52-week shipped history (already contains rolling 52 weeks)
        rows = execute_query("""
            SELECT start_date, end_date, sku, quantity_shipped
            FROM weekly_shipped_history
            ORDER BY start_date DESC, sku
        """)
        
        if not rows:
            logger.warning("No weekly shipped history found in database")
            return pd.DataFrame(columns=['Start Date', 'End Date', 'SKU', 'Quantity Shipped'])
        
        df = pd.DataFrame(rows, columns=['Start Date', 'End Date', 'SKU', 'Quantity Shipped'])
        logger.info(f"Loaded {len(df)} rows of weekly shipped history from database")
        return df
    except Exception as e:
        logger.error(f"Error loading weekly shipped history: {e}", exc_info=True)
        return pd.DataFrame(columns=['Start Date', 'End Date', 'SKU', 'Quantity Shipped'])


def get_inventory_transactions_from_db():
    """Get inventory transactions from database"""
    logger.info("Loading inventory transactions from database...")
    try:
        rows = execute_query("""
            SELECT date, sku, quantity, transaction_type, notes
            FROM inventory_transactions
            ORDER BY date DESC
        """)
        
        if not rows:
            logger.warning("No inventory transactions found in database")
            return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType', 'Notes'])
        
        df = pd.DataFrame(rows, columns=['Date', 'SKU', 'Quantity', 'TransactionType', 'Notes'])
        # Convert string dates to datetime then to date objects for compatibility
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        logger.info(f"Loaded {len(df)} inventory transactions from database")
        return df
    except Exception as e:
        logger.error(f"Error loading inventory transactions: {e}", exc_info=True)
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'TransactionType', 'Notes'])


def get_shipped_items_from_db():
    """Get shipped items from database"""
    logger.info("Loading shipped items from database...")
    try:
        rows = execute_query("""
            SELECT ship_date, base_sku, quantity_shipped, sku_lot
            FROM shipped_items
            ORDER BY ship_date DESC
        """)
        
        if not rows:
            logger.warning("No shipped items found in database (expected if not yet populated from ShipStation)")
            # Return empty DataFrame with columns matching what calculate_current_inventory expects
            return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'SKU - Lot'])
        
        df = pd.DataFrame(rows, columns=['Ship Date', 'Base SKU', 'Quantity Shipped', 'SKU - Lot'])
        # Convert string dates to datetime then to date objects for compatibility
        df['Ship Date'] = pd.to_datetime(df['Ship Date']).dt.date
        # Rename columns to match expected format
        df = df.rename(columns={'Ship Date': 'Date', 'Base SKU': 'SKU', 'Quantity Shipped': 'Quantity'})
        logger.info(f"Loaded {len(df)} shipped items from database")
        return df
    except Exception as e:
        logger.error(f"Error loading shipped items: {e}", exc_info=True)
        return pd.DataFrame(columns=['Date', 'SKU', 'Quantity', 'SKU - Lot'])


def save_inventory_to_db(inventory_df, rolling_average_df, product_names_map):
    """Save calculated inventory and KPIs to database"""
    logger.info("Saving inventory calculations to database...")
    
    try:
        with transaction() as conn:
            # Track workflow status
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE workflows 
                SET status = 'running',
                    last_run_at = CURRENT_TIMESTAMP
                WHERE name = 'weekly_reporter'
            """)
            
            # Merge inventory with product names and rolling averages
            combined_df = pd.merge(inventory_df, product_names_map, left_on='SKU', right_on='SKU', how='left')
            combined_df = pd.merge(combined_df, rolling_average_df, on='SKU', how='left')
            
            records_processed = 0
            
            # UPSERT each row to inventory_current table
            for _, row in combined_df.iterrows():
                sku = str(row['SKU'])
                product_name = str(row.get('Product Name', 'Unknown'))
                current_quantity = int(row['Quantity']) if pd.notna(row['Quantity']) else 0
                rolling_avg = row.get('12-Month Rolling Average', None)
                
                # Convert rolling average to cents if it exists
                weekly_avg_cents = None
                if pd.notna(rolling_avg) and rolling_avg != 'Insufficient Data':
                    try:
                        weekly_avg_cents = int(float(rolling_avg) * 100)
                    except (ValueError, TypeError):
                        weekly_avg_cents = None
                
                # Determine alert level based on inventory
                alert_level = 'normal'
                if current_quantity == 0:
                    alert_level = 'critical'
                elif current_quantity < 50:  # Default reorder point
                    alert_level = 'low'
                
                cursor = conn.cursor()

                
                cursor.execute("""
                    INSERT INTO inventory_current 
                        (sku, product_name, current_quantity, weekly_avg_cents, alert_level, last_updated)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(sku) DO UPDATE SET
                        product_name = excluded.product_name,
                        current_quantity = excluded.current_quantity,
                        weekly_avg_cents = excluded.weekly_avg_cents,
                        alert_level = excluded.alert_level,
                        last_updated = CURRENT_TIMESTAMP
                """, (sku, product_name, current_quantity, weekly_avg_cents, alert_level))
                
                records_processed += 1
            
            # Update workflow status to completed
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE workflows 
                SET status = 'completed',
                    records_processed = %s,
                    duration_seconds = CAST((julianday('now') - julianday(last_run_at)) * 86400 AS INTEGER)
                WHERE name = 'weekly_reporter'
            """, (records_processed,))
            
            logger.info(f"Successfully saved {records_processed} inventory records to database")
            
    except Exception as e:
        logger.error(f"Error saving to database: {e}", exc_info=True)
        # Update workflow status to failed
        try:
            with transaction() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE workflows 
                    SET status = 'failed',
                        details = %s
                    WHERE name = 'weekly_reporter'
                """, (str(e),))
        except:
            pass
        raise


def generate_weekly_inventory_report():
    """
    Orchestrates the generation of the Weekly Inventory Report using SQLite database.
    """
    if not is_workflow_enabled('weekly-reporter'):
        logger.info("Workflow 'weekly-reporter' is DISABLED - skipping execution")
        return
    
    update_workflow_last_run('weekly-reporter')
    logger.info("--- Starting Weekly Inventory Report Generation ---")

    # 1. Get Key SKUs and Product Names from database
    key_skus_list, product_names_map = get_key_skus_from_db()
    if not key_skus_list:
        logger.error("Could not retrieve Key Products. Aborting report generation.")
        return
    logger.debug(f"Step 1 Complete: Found {len(key_skus_list)} Key SKUs.")

    # 2. Get Historical Shipped Data from database
    weekly_shipped_history_df = get_weekly_shipped_history_from_db(key_skus_list)
    if weekly_shipped_history_df is None or weekly_shipped_history_df.empty:
        logger.error("Failed to fetch weekly shipped history. Aborting.")
        return
    # Rename columns to match what calculate_12_month_rolling_average expects
    weekly_shipped_history_df = weekly_shipped_history_df.rename(columns={
        'Start Date': 'Date',
        'Quantity Shipped': 'ShippedQuantity'
    })
    logger.debug(f"Step 2 Complete: Fetched {len(weekly_shipped_history_df)} rows of weekly shipped history.")

    # 3. Get Transactional Data for Current Inventory Calculation from database
    inventory_transactions_df = get_inventory_transactions_from_db()
    shipped_items_df = get_shipped_items_from_db()
    logger.debug(f"Step 3 Complete: Fetched {len(inventory_transactions_df)} inventory transactions and {len(shipped_items_df)} shipped items.")

    # 4. Get initial inventory and calculate current inventory
    initial_inventory = get_initial_inventory_from_db()
    from datetime import datetime, timedelta
    current_week_end_date = datetime.now().date()
    current_week_start_date = current_week_end_date - timedelta(days=7)
    current_inventory_df = calculate_current_inventory(
        initial_inventory, 
        inventory_transactions_df, 
        shipped_items_df, 
        key_skus_list, 
        current_week_start_date, 
        current_week_end_date
    )
    if current_inventory_df is None or current_inventory_df.empty:
        logger.error("Failed to calculate current inventory. Aborting.")
        return
    logger.debug(f"Step 4 Complete: Calculated current inventory for {len(current_inventory_df)} SKUs.")

    # 5. Calculate 12-Month Rolling Average
    rolling_average_df = calculate_12_month_rolling_average(weekly_shipped_history_df)
    if rolling_average_df is None:
        logger.error("Failed to calculate rolling average. Aborting.")
        return
    logger.debug(f"Step 5 Complete: Calculated rolling average for {len(rolling_average_df)} SKUs.")

    # 6. Save Results to Database (replaces Google Sheets write)
    if current_inventory_df.empty:
        logger.warning("Current inventory data is empty. Cannot save to database.")
        return
    
    save_inventory_to_db(current_inventory_df, rolling_average_df, product_names_map)
    logger.debug(f"Step 6 Complete: Saved inventory data to database.")

    logger.info("--- Weekly Inventory Report Generation Finished ---")


if __name__ == "__main__":
    generate_weekly_inventory_report()

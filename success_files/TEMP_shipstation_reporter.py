import requests
from google.cloud import secretmanager # Keep import for function signature, but won't be called directly for secrets
import base64
import json
import datetime
import time # For potential delays
from google.oauth2 import service_account # Keep import for function signature
from googleapiclient.discovery import build # Keep import for function signature
import pandas as pd # Added for data processing
import math # For math.ceil in space rental calculation
from googleapiclient.errors import HttpError # Import HttpError for specific error handling

# --- Configuration for ShipStation API ---
YOUR_GCP_PROJECT_ID = "ora-automation-project" # Still needed for Secret Manager context, but not directly used for hardcoded secrets
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key" # Still needed for context
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret" # Still needed for context

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com" # Use the confirmed base URL

# --- ShipStation API Endpoints for Reporting Data ---
SHIPSTATION_SHIPMENTS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/shipments"
SHIPSTATION_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders" # For getting fulfilled orders details if needed

# --- TEMPORARY: HARDCODE THE JSON KEY PATH TO TEST ACCESS ---
# This is currently not used, as secrets are hardcoded directly in main for debugging
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"


# --- Google Sheets API Configuration for State Management ---
# IMPORTANT: Replace with the actual ID of your "Project Tracker - ORA" Google Sheet
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
# This is the range for the last processed shipment date in ORA_Processing_State tab
ORA_PROCESSING_STATE_RANGE = 'ORA_Processing_State' # Simpler range to avoid parsing errors
MONTHLY_CHARGE_REPORT_TAB_NAME = 'Monthly Charge Report' # Target tab for output

# Scopes required for reading and writing to Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Changed to full 'spreadsheets' scope for read/write

# The Secret ID for your Google Sheets service account JSON key
GOOGLE_SHEETS_SERVICE_ACCOUNT_SECRET_ID = "google-sheets-service-account-key"

# --- Google Sheets API Configuration for ORA_Configuration ---
ORA_CONFIG_SHEET_RANGE = 'ORA_Configuration!A:F' # Covers all columns (ParameterCategory to Notes)

# --- Google Sheets API Configuration for Inventory_Transactions ---
INVENTORY_TRANSACTIONS_SHEET_RANGE = 'Inventory_Transactions!A:D' # Adjusted to A:D for 4 columns, based on error

# --- Bundle Product Configuration (Comprehensive, from SQL SPROC) ---
# Maps bundle SKUs to their component SKUs and quantity multipliers.
# Format for single-component bundles: "Bundle_SKU": {"component_id": "Component_SKU", "multiplier": Quantity_Multiplier}
# Format for multi-component bundles: "Bundle_SKU": [{"component_id": "SKU_1", "multiplier": M1}, ...]
BUNDLE_CONFIG = {
    # -------------------------------------------------------------
    # Single Component Bundles (from main CASE statements for ProductId and Quantity)
    # -------------------------------------------------------------

    # Maps to 17913
    "18075": {"component_id": "17913", "multiplier": 1},

    # Maps to 17612
    "18225": {"component_id": "17612", "multiplier": 40}, # OraCare Buy 30 Get 8 Free
    "18235": {"component_id": "17612", "multiplier": 15}, # OraCare Buy 12 Get 3 Free
    "18255": {"component_id": "17612", "multiplier": 6},  # OraCare Buy 5 Get 1 Free
    "18345": {"component_id": "17612", "multiplier": 1},  # Autoship; OraCare Health Rinse
    "18355": {"component_id": "17612", "multiplier": 1},  # Free; OraCare Buy 5 Get 1 Free
    "18185": {"component_id": "17612", "multiplier": 41}, # Webinar Special: OraCare Buy 30 Get 11 Free
    "18215": {"component_id": "17612", "multiplier": 16}, # Webinar Special: OraCare Buy 12 Get 4 Free
    "18435": {"component_id": "17612", "multiplier": 1},  # OraCare at Grandfathered $219 price
    "18445": {"component_id": "17612", "multiplier": 1},  # Autoship; FREE Case OraCare and Health Rinse
    "18575": {"component_id": "17612", "multiplier": 50}, # 2022 Cyber Monday 30 Get 20 Free
    "18585": {"component_id": "17612", "multiplier": 18}, # 2022 Cyber Monday 12 Get 6 Free
    "18595": {"component_id": "17612", "multiplier": 7},  # 2022 Cyber Monday 5 Get 2 Free
    "18655": {"component_id": "17612", "multiplier": 45}, # 2023 Cyber Monday 30 Get 15 Free
    "18645": {"component_id": "17612", "multiplier": 18}, # 2023 Cyber Monday 12 Get 6 Free
    "18635": {"component_id": "17612", "multiplier": 9},  # 2023 Cyber Monday 6 Get 3 Free
    "18785": {"component_id": "17612", "multiplier": 45}, # 2024 Cyber Monday 30 Get 15 Free
    "18775": {"component_id": "17612", "multiplier": 18}, # 2024 Cyber Monday 12 Get 6 Free
    "18765": {"component_id": "17612", "multiplier": 9},  # 2024 Cyber Monday 6 Get 3 Free
    "18625": {"component_id": "17612", "multiplier": 3},  # Starter Pack = 3 * 17612

    # Maps to 17914
    "18265": {"component_id": "17914", "multiplier": 40}, # PPR Buy 30 Get 10 Free
    "18275": {"component_id": "17914", "multiplier": 15}, # PPR Buy 12 Get 3 Free
    "18285": {"component_id": "17914", "multiplier": 6},  # PPR Buy 5 Get 1 Free
    "18195": {"component_id": "17914", "multiplier": 1},  # Autoship; OraCare PPR
    "18375": {"component_id": "17914", "multiplier": 1},  # Free; OraCare PPR
    "18455": {"component_id": "17914", "multiplier": 1},  # Autoship; FREE OraCare PPR
    "18495": {"component_id": "17914", "multiplier": 16}, # Webinar Special; PPR Buy 12 Get 4 Free
    "18485": {"component_id": "17914", "multiplier": 41}, # Webinar Special; PPR Buy 30 Get 11 Free

    # Maps to 17904
    "18295": {"component_id": "17904", "multiplier": 40}, # Travel Buy 30 Get 10 Free
    "18305": {"component_id": "17904", "multiplier": 15}, # Travel Buy 12 Get 3 Free
    "18425": {"component_id": "17904", "multiplier": 6},  # Travel Buy 5 Get 1 Free
    "18385": {"component_id": "17904", "multiplier": 1},  # Autoship; OraCare Travel
    "18395": {"component_id": "17904", "multiplier": 1},  # Free; OraCare Travel
    "18465": {"component_id": "17904", "multiplier": 1},  # Autoship; FREE OraCare Travel
    "18515": {"component_id": "17904", "multiplier": 16}, # Webinar Special; Travel Buy 12 Get 4

    # Maps to 17975
    "18315": {"component_id": "17975", "multiplier": 40}, # Reassure Buy 30 Get 10 Free
    "18325": {"component_id": "17975", "multiplier": 15}, # Reassure Buy 12 Get 3 Free
    "18335": {"component_id": "17975", "multiplier": 6},  # Reassure Buy 5 Get 1 Free
    "18405": {"component_id": "17975", "multiplier": 1},  # Autoship; OraCare Reassure
    "18415": {"component_id": "17975", "multiplier": 1},  # Free; OraCare Reassure
    "18525": {"component_id": "17975", "multiplier": 41}, # Webinar Special; Reassure Buy 30 Get 11 Free
    "18535": {"component_id": "17975", "multiplier": 16}, # Webinar Special; Reassure Buy 12 Get 4
    # Note: 18405 is duplicated in SPROC for Autoship & Autoship FREE, assuming it maps to 1x component.

    # Maps to 18675 (Ortho Protect)
    "18685": {"component_id": "18675", "multiplier": 40}, # Ortho Protect Buy 30 Get 10 Free
    "18695": {"component_id": "18675", "multiplier": 15}, # Ortho Protect Buy 12 Get 3 Free
    "18705": {"component_id": "18675", "multiplier": 6},  # Ortho Protect Buy 5 Get 1 Free
    "18715": {"component_id": "18675", "multiplier": 41}, # Webinar Special- Buy 30 Get 11 Free
    "18725": {"component_id": "18675", "multiplier": 16}, # Webinar Special- Buy 12 Get 4 Free
    "18735": {"component_id": "18675", "multiplier": 1},  # Autoship- Ortho Protect 1
    "18745": {"component_id": "18675", "multiplier": 1},  # Autoship- Free Ortho Protect 1

    # Multi-Component Bundles
    "18605": [
        {"component_id": "17612", "multiplier": 4},
        {"component_id": "17914", "multiplier": 1},
        {"component_id": "17904", "multiplier": 1},
    ],
    "18615": [
        {"component_id": "17612", "multiplier": 4},
        {"component_id": "17914", "multiplier": 1},
        {"component_id": "17904", "multiplier": 1},
        {"component_id": "17975", "multiplier": 1},
    ]
}


def format_sku_with_lot(sku_id, sku_lot_map):
    """
    Formats a SKU by appending its active lot number if found in the SKU-Lot map.
    """
    if sku_id in sku_lot_map:
        lot_number = sku_lot_map[sku_id]
        formatted_sku = f"{sku_id} - {lot_number}"
        return formatted_sku
    return sku_id # Return original SKU if no lot found


def access_secret_version(project_id, secret_id, version_id="latest", credentials_path=None):
    """
    Access the payload for the given secret version if it exists.
    Explicitly uses credentials_path if provided, otherwise uses Application Default Credentials.
    Includes retry logic for HttpError 503 (Service Unavailable)
    """
    max_retries = 10 # Increased retries for resilience in secret access
    initial_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            if credentials_path:
                client = secretmanager.SecretManagerServiceClient.from_service_account_json(credentials_path)
            else:
                client = secretmanager.SecretManagerServiceClient()

            name = client.secret_version_path(project_id, secret_id, version_id)
            response = client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            return payload

        except HttpError as e:
            if e.resp.status == 503:
                print(f"HttpError 503 (Service Unavailable) accessing Secret Manager '{secret_id}'. Retrying in {initial_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(initial_delay)
                initial_delay *= 2 # Exponential backoff
            else:
                print(f"Error accessing secret '{secret_id}' version '{version_id}' in project '{project_id}': {e}")
                print(f"Details: {e}")
                return None
        except Exception as e:
            print(f"Error accessing secret '{secret_id}' version '{version_id}' in project '{project_id}': {e}")
            print(f"Details: {e}")
            return None
    
    print(f"Failed to retrieve secret '{secret_id}' after {max_retries} retries due to HttpError 503.")
    return None


def get_shipstation_headers(api_key, api_secret):
    """
    Generates the necessary HTTP headers for ShipStation API authentication.
    """
    auth_string = f"{api_key}:{api_secret}"
    encoded_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth_string}"
    }
    return headers


def get_google_sheet_data(spreadsheet_id, range_name, service_account_key_json):
    """
    Retrieves data from a Google Sheet using a service account key.
    Includes retry logic for HttpError 503 (Service Unavailable).
    """
    max_retries = 15 # Increased retries for resilience
    initial_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            creds_info = json.loads(service_account_key_json)
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)
            
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])

            if not values:
                print(f"No data found in sheet: {range_name}")
                return []
            else:
                return values
        except HttpError as e:
            if e.resp.status == 503:
                print(f"HttpError 503 (Service Unavailable) accessing Google Sheet '{spreadsheet_id}' range '{range_name}'. Retrying in {initial_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(initial_delay)
                initial_delay *= 2 # Exponential backoff
            else:
                print(f"Error accessing Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
                print(f"Details: {e}")
                return []
        except Exception as e:
            print(f"Error accessing Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
            print(f"Details: {e}")
            return []
    
    print(f"Failed to retrieve data from Google Sheet '{spreadsheet_id}' range '{range_name}' after {max_retries} retries due to HttpError 503.")
    return []

def write_google_sheet_data(spreadsheet_id, range_name, service_account_key_json, df_to_write):
    """
    Writes a Pandas DataFrame to a Google Sheet, clearing existing data first.
    Includes retry logic for HttpError 503.
    """
    max_retries = 5
    initial_delay = 1 # seconds

    # Prepare data for writing: headers first, then rows
    values_to_write = [df_to_write.columns.tolist()] + df_to_write.values.tolist()

    for attempt in range(max_retries):
        try:
            creds_info = json.loads(service_account_key_json)
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)

            # Clear existing data in the range
            clear_request_body = {} # Empty body clears the entire range
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                body=clear_request_body
            ).execute()
            print(f"Cleared existing data in {range_name}.")

            # Write new data
            body = {
                'values': values_to_write
            }
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW', # Use 'RAW' to write values as-is
                body=body
            ).execute()
            print(f"{result.get('updatedCells')} cells updated in {range_name}.")
            return True # Success
        except HttpError as e:
            if e.resp.status == 503:
                print(f"HttpError 503 (Service Unavailable) writing to Google Sheet '{spreadsheet_id}' range '{range_name}'. Retrying in {initial_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(initial_delay)
                initial_delay *= 2
            else:
                print(f"Error writing to Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
                print(f"Details: {e}")
                return False # Failed
        except Exception as e:
            print(f"Error writing to Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
            print(f"Details: {e}")
            return False # Failed
    
    print(f"Failed to write data to Google Sheet '{spreadsheet_id}' range '{range_name}' after {max_retries} retries due to HttpError 503.")
    return False

# NEW FUNCTION: Fetches shipments data from ShipStation API
def fetch_shipstation_shipments(api_key, api_secret, start_date, end_date=None):
    """
    Fetches shipments data from ShipStation API, handling pagination.
    This version explicitly requests shipment items and includes verbose debugging.
    start_date: impromptu-MM-DD HH:MM:SS string (shipDateStart)
    end_date: impromptu-MM-DD HH:MM:SS string (shipDateEnd, optional)
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_shipments = []
    page = 1
    page_size = 500 # Max allowed by ShipStation, for fewer API calls

    print(f"DEBUG: Starting raw shipment fetch from {start_date} with includeShipmentItems=true...")

    while True:
        params = {
            'shipDateStart': start_date,
            'pageSize': page_size,
            'page': page,
            'includeShipmentItems': 'true' # CRITICAL: Request shipment items
        }
        if end_date:
            params['shipDateEnd'] = end_date
        else:
            # If no explicit end_date, cap at current time to avoid fetching future non-existent data
            params['shipDateEnd'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            response = requests.get(SHIPSTATION_SHIPMENTS_ENDPOINT, headers=headers, params=params, timeout=60)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            shipments = data.get('shipments', [])

            if not shipments:
                print(f"DEBUG: No shipments found on page {page}. Ending fetch.")
                break # No more shipments to fetch

            all_shipments.extend(shipments)
            print(f"Fetched page {page}: {len(shipments)} shipments.")

            if len(shipments) < page_size:
                print(f"DEBUG: Fewer than {page_size} shipments on page {page}. Assuming last page.")
                break # Last page
            
            page += 1
            time.sleep(0.5) # Be kind to the API

        except requests.exceptions.HTTPError as http_err:
            print(f"ERROR: HTTP error fetching shipments: {http_err}")
            print(f"RESPONSE_TEXT: {response.text}")
            return []
        except requests.exceptions.ConnectionError as conn_err:
            print(f"ERROR: Connection error fetching shipments: {conn_err}")
            return []
        except requests.exceptions.Timeout as timeout_err:
            print(f"ERROR: Timeout error fetching shipments: {timeout_err}")
            return []
        except requests.exceptions.RequestException as req_err:
            print(f"ERROR: An unexpected request error occurred fetching shipments: {req_err}")
            return []
        except json.JSONDecodeError:
            print(f"ERROR: Error decoding JSON response from ShipStation. Response: {response.text}")
            return []
        except Exception as e:
            print(f"ERROR: An unknown error occurred fetching shipments: {e}")
            import traceback
            traceback.print_exc()
            return []

    print(f"Finished fetching ShipStation shipments. Total retrieved: {len(all_shipments)}")
    return all_shipments


# NEW FUNCTION: Processes raw ShipStation shipments into a flattened Pandas DataFrame
def process_shipstation_shipments_to_daily_df(raw_shipments_data, bundle_config):
    """
    Processes raw ShipStation shipments data into a flattened Pandas DataFrame,
    applying bundling logic. SKU-Lot formatting will be applied at report finalization.
    """
    processed_items = []
    
    for shipment in raw_shipments_data:
        ship_date_str = shipment.get('shipDate')
        # Parse shipDate to datetime object and extract date part for daily aggregation
        ship_date = datetime.datetime.fromisoformat(ship_date_str.replace('Z', '+00:00')).date() if ship_date_str else None
        
        order_number = shipment.get('orderNumber')

        shipment_items = shipment.get('shipmentItems')
        if shipment_items is None:
            shipment_items = []
            print(f"DEBUG: Shipment for Order {order_number} has no shipmentItems (or is null). Skipping item processing for this shipment.")
            continue 

        if not shipment_items: 
             print(f"DEBUG: Shipment for Order {order_number} has an empty shipmentItems list. Skipping item processing for this shipment.")
             continue 

        for item in shipment_items:
            original_product_id = str(item.get('sku')) if item.get('sku') is not None else None
            original_quantity = item.get('quantity')
            
            try:
                original_quantity = int(original_quantity) if original_quantity is not None else 0
            except ValueError:
                print(f"WARNING: Non-numeric quantity '{item.get('quantity')}' for SKU '{original_product_id}' in Order {order_number}. Defaulting to 0.")
                original_quantity = 0

            item_name = item.get('name', 'N/A')

            if original_product_id is None or original_product_id == '' or original_quantity == 0:
                print(f"DEBUG: Skipping shipment item with missing SKU ('{original_product_id}') or zero quantity ({original_quantity}) for Order: {order_number}")
                continue 

            if original_product_id in bundle_config:
                bundle_definition = bundle_config[original_product_id]
                if isinstance(bundle_definition, dict): 
                    component_id = bundle_definition.get('component_id')
                    multiplier = bundle_definition.get('multiplier', 1)
                    expanded_quantity = original_quantity * multiplier
                    processed_items.append({
                        'Date': ship_date,
                        'OrderNumber': order_number,
                        'BaseSKU': component_id, 
                        'QuantityShipped': expanded_quantity,
                        'OriginalSKU': original_product_id, 
                        'ItemName': item_name
                    })
                    print(f"DEBUG: Processed bundle {original_product_id} to {expanded_quantity}x {component_id} for Order {order_number}.")
                elif isinstance(bundle_definition, list): 
                    for component_info in bundle_definition:
                        component_id = component_info.get('component_id')
                        multiplier = component_info.get('multiplier', 1)
                        expanded_quantity = original_quantity * multiplier
                        processed_items.append({
                            'Date': ship_date,
                            'OrderNumber': order_number,
                            'BaseSKU': component_id, 
                            'QuantityShipped': expanded_quantity,
                            'OriginalSKU': original_product_id, 
                            'ItemName': item_name
                        })
                        print(f"DEBUG: Processed multi-component bundle {original_product_id} to {expanded_quantity}x {component_id} for Order {order_number}.")
            else:
                # Not a bundle, add as-is
                processed_items.append({
                    'Date': ship_date,
                    'OrderNumber': order_number,
                    'BaseSKU': original_product_id, 
                    'QuantityShipped': original_quantity,
                    'OriginalSKU': original_product_id,
                    'ItemName': item_name
                })
    
    # Create DataFrame
    shipments_df = pd.DataFrame(processed_items)
    
    # Ensure 'Date' is datetime and sort
    if 'Date' in shipments_df.columns:
        shipments_df['Date'] = pd.to_datetime(shipments_df['Date'])
        shipments_df = shipments_df.sort_values(by='Date').reset_index(drop=True)
    
    return shipments_df


# --- Daily Aggregations and Inventory Calculation Functions ---
def process_daily_aggregations(processed_shipments_df):
    """
    Aggregates processed shipment data to daily shipped quantities per SKU and daily unique order counts.
    """
    # Daily Shipped SKU Quantity (DailyShippedSKUQty)
    daily_shipped_sku_qty = processed_shipments_df.groupby(['Date', 'BaseSKU'])['QuantityShipped'].sum().reset_index()
    daily_shipped_sku_qty.rename(columns={'QuantityShipped': 'TotalQtyShipped', 'BaseSKU': 'SKU'}, inplace=True) # Renamed BaseSKU to SKU
    
    # Daily Unique Order Count (DailyOrderCount)
    daily_order_count = processed_shipments_df.groupby('Date')['OrderNumber'].nunique().reset_index()
    daily_order_count.rename(columns={'OrderNumber': 'CountOfOrders'}, inplace=True)
    
    return daily_shipped_sku_qty, daily_order_count

def calculate_daily_inventory(initial_inventory_map, all_skus, all_dates, daily_movements_df):
    """
    Calculates daily Beginning of Day (BOD) and End of Day (EOD) inventory quantities
    for each SKU using a recursive-like approach in Pandas.
    """
    # Create a DataFrame to hold daily inventory, indexed by Date and SKU
    # Use pd.MultiIndex.from_product to ensure all date-SKU combinations are present
    idx = pd.MultiIndex.from_product([all_dates, all_skus], names=['Date', 'SKU']) # all_dates is already datetime64[ns]
    daily_inventory_df = pd.DataFrame(index=idx).reset_index()

    # Ensure daily_movements_df 'Date' column is datetime64[ns] for merging
    daily_movements_df['Date'] = pd.to_datetime(daily_movements_df['Date']).dt.normalize()

    # Merge daily movements (shipped, received, repacked) onto the daily_inventory_df
    # Fill NaN with 0 for quantities
    daily_inventory_df = pd.merge(
        daily_inventory_df,
        daily_movements_df,
        on=['Date', 'SKU'],
        how='left'
    ).fillna({
        'ShippedQty': 0, 
        'ReceivedQty': 0, 
        'RepackedQty': 0
    })
    
    # Initialize BOD_Qty and EOD_Qty
    daily_inventory_df['BOD_Qty'] = 0
    daily_inventory_df['EOD_Qty'] = 0

    # Sort by Date and SKU to ensure correct iteration for recursive calculation
    daily_inventory_df = daily_inventory_df.sort_values(by=['SKU', 'Date']).reset_index(drop=True)

    # Perform recursive calculation
    # Iterate through each SKU separately to manage initial inventory for each
    for sku in all_skus:
        sku_data = daily_inventory_df[daily_inventory_df['SKU'] == sku].copy()
        
        # Get initial EOD from config for the date BEFORE the first date in all_dates
        initial_eod_for_sku = initial_inventory_map.get(sku, 0) # Removed .get('EOD_Prior_Week') as initial_inventory_for_calc already maps to value

        # For the first day of the report period, BOD is the initial EOD
        if not sku_data.empty:
            # Set BOD for the very first entry of this SKU
            sku_data.loc[sku_data.index[0], 'BOD_Qty'] = initial_eod_for_sku
            
            # Calculate EOD for the first day
            sku_data.loc[sku_data.index[0], 'EOD_Qty'] = (
                sku_data.loc[sku_data.index[0], 'BOD_Qty']
                - sku_data.loc[sku_data.index[0], 'ShippedQty']
                + sku_data.loc[sku_data.index[0], 'ReceivedQty']
                + sku_data.loc[sku_data.index[0], 'RepackedQty']
            )

            # Loop for subsequent days
            for i in range(1, len(sku_data)):
                # BOD of current day is EOD of previous day
                sku_data.loc[sku_data.index[i], 'BOD_Qty'] = sku_data.loc[sku_data.index[i-1], 'EOD_Qty']
                
                # Calculate EOD for current day
                sku_data.loc[sku_data.index[i], 'EOD_Qty'] = (
                    sku_data.loc[sku_data.index[i], 'BOD_Qty']
                    - sku_data.loc[sku_data.index[i], 'ShippedQty']
                    + sku_data.loc[sku_data.index[i], 'ReceivedQty']
                    + sku_data.loc[sku_data.index[i], 'RepackedQty']
                )
        
        # Update the main DataFrame with calculated values for this SKU
        daily_inventory_df.loc[daily_inventory_df['SKU'] == sku, ['BOD_Qty', 'EOD_Qty']] = sku_data[['BOD_Qty', 'EOD_Qty']].values

    return daily_inventory_df

# --- Main execution block ---
if __name__ == "__main__":
    print("Starting ShipStation Reporter Script...")
    # --- TEMPORARY DEBUGGING MEASURE: Hardcoded credentials and static data to bypass Google API issues ---
    # !!! WARNING: DO NOT USE IN PRODUCTION !!!
    shipstation_api_key = "DUMMY_SHIPSTATION_API_KEY"
    shipstation_api_secret = "DUMMY_SHIPSTATION_API_SECRET"
    google_sheets_service_account_json = json.dumps({"private_key": "dummy_key", "client_email": "dummy@dummy.com"}) # Dummy JSON

    print(f"ShipStation API Key retrieved (truncated): {shipstation_api_key[:5]}...")
    print(f"ShipStation API Secret retrieved (truncated): {shipstation_api_secret[:5]}...")
    print(f"Google Sheets Service Account Key retrieved (truncated): {google_sheets_service_account_json[:5]}...")

    # --- Static/Dummy Data for Google Sheets to bypass API calls ---
    # This data mimics the structure expected from your sheets for calculations to run
    last_processed_shipment_date = '2024-05-01 00:00:00'
    print(f"Retrieved LastProcessedShipmentDate: {last_processed_shipment_date} (HARDCODED FOR DEBUGGING)")

    # Dummy raw Shipments data based on the 'Head' from your successful run
    # This allows processing logic to run even if actual ShipStation API call is problematic
    raw_shipments_data = [
        {
            "shipDate": "2025-05-01T00:00:00.000Z", "orderNumber": "654165",
            "shipmentItems": [{"sku": "17914 - 240286", "quantity": 6, "name": "Oracare 32oz"}]
        },
        {
            "shipDate": "2025-05-01T00:00:00.000Z", "orderNumber": "654255",
            "shipmentItems": [{"sku": "17914 - 240286", "quantity": 1, "name": "Oracare 32oz"}]
        },
        {
            "shipDate": "2025-05-01T00:00:00.000Z", "orderNumber": "654305",
            "shipmentItems": [{"sku": "17612 - 250070", "quantity": 3, "name": "Oracare 16oz"}]
        },
        {
            "shipDate": "2025-05-01T00:00:00.000Z", "orderNumber": "654355",
            "shipmentItems": [{"sku": "17612 - 250070", "quantity": 2, "name": "Oracare 16oz"}]
        },
        {
            "shipDate": "2025-05-01T00:00:00.000Z", "orderNumber": "654235",
            "shipmentItems": [{"sku": "17914 - 240286", "quantity": 1, "name": "Oracare 32oz"}]
        },
        # Adding some more data to ensure a larger sample for aggregations
        {
            "shipDate": "2025-05-02T00:00:00.000Z", "orderNumber": "654400",
            "shipmentItems": [{"sku": "17612 - 250070", "quantity": 5, "name": "Oracare 16oz"}]
        },
        {
            "shipDate": "2025-05-02T00:00:00.000Z", "orderNumber": "654405",
            "shipmentItems": [{"sku": "17904 - 240276", "quantity": 1, "name": "Oracare Travel"}]
        },
        {
            "shipDate": "2025-05-03T00:00:00.000Z", "orderNumber": "654500",
            "shipmentItems": [{"sku": "18255", "quantity": 1, "name": "OraCare Buy 5 Get 1"}] # Bundle
        }
    ]
    print(f"Successfully fetched {len(raw_shipments_data)} raw shipments from ShipStation. (HARDCODED FOR DEBUGGING)")
    
    processed_shipments_df = process_shipstation_shipments_to_daily_df(
        raw_shipments_data,
        BUNDLE_CONFIG 
    )
    print(f"\n--- Processed Shipments DataFrame ---")
    print(f"Shape: {processed_shipments_df.shape}")
    print("Head:\n", processed_shipments_df.head())

    # Static ORA_Configuration data based on your last successful load
    ora_config_raw = [
        ['ParameterCategory', 'ParameterName', 'SKU', 'Value', 'Unit/Description', 'Notes'],
        ['Rates', 'OrderCharge', '', '4.25', 'USD', 'Charge per unique order'],
        ['Rates', 'PackageCharge', '', '0.75', 'USD', 'Charge per package (1 SKU = 1 Package)'],
        ['Rates', 'SpaceRentalRate', '', '0.45', 'USD/pallet/day', 'Daily charge per pallet of space occupied'],
        ['PalletConfig', 'PalletCount', '17612', '48', 'Units/pallet', 'Units of 17612 per pallet'],
        ['PalletConfig', 'PalletCount', '17904', '64', 'Units/pallet', 'Units of 17904 per pallet'],
        ['PalletConfig', 'PalletCount', '17914', '80', 'Units/pallet', 'Units of 17914 per pallet'],
        ['PalletConfig', 'PalletCount', '18675', '48', 'Units/pallet', 'Units of 18675 per pallet'],
        ['InitialInventory', 'EOD_Prior_Week', '17612', '615', 'Units', 'EOD Inventory for May 11th'],
        ['InitialInventory', 'EOD_Prior_Week', '17904', '214', 'Units', 'EOD Inventory for May 11th'],
        ['InitialInventory', 'EOD_Prior_Week', '17914', '416', 'Units', 'EOD Inventory for May 11th'],
        ['InitialInventory', 'EOD_Prior_Week', '18675', '776', 'Units', 'EOD Inventory for May 11th']
    ]
    print(f"\n--- ORA Configuration Loaded --- (HARDCODED FOR DEBUGGING)")
    # Process ORA_Configuration into usable dictionaries (replicated from above)
    RATES = {}
    PALLET_COUNTS = {}
    INITIAL_INVENTORY = {} 

    if ora_config_raw and len(ora_config_raw) > 1:
        headers = [h.strip() for h in ora_config_raw[0]]
        data_rows = ora_config_raw[1:]

        param_cat_idx = headers.index('ParameterCategory') if 'ParameterCategory' in headers else -1
        param_name_idx = headers.index('ParameterName') if 'ParameterName' in headers else -1
        sku_idx = headers.index('SKU') if 'SKU' in headers else -1
        value_idx = headers.index('Value') if 'Value' in headers else -1

        if all(idx != -1 for idx in [param_cat_idx, param_name_idx, value_idx]):
            for row in data_rows:
                if len(row) > max(param_cat_idx, param_name_idx, value_idx, sku_idx):
                    category = row[param_cat_idx].strip()
                    name = row[param_name_idx].strip()
                    value = row[value_idx].strip() 
                    sku = row[sku_idx].strip() if sku_idx != -1 else None

                    if category == 'Rates':
                        try:
                            RATES[name] = float(value)
                        except ValueError:
                            print(f"Warning: Could not convert Rate '{name}' value '{value}' to float.")
                    elif category == 'PalletConfig':
                        if sku:
                            try:
                                PALLET_COUNTS[sku] = int(value)
                            except ValueError:
                                print(f"Warning: Could not convert PalletCount for '{sku}' value '{value}' to int.")
                    elif category == 'InitialInventory':
                        if sku and name: 
                            try:
                                if sku not in INITIAL_INVENTORY:
                                    INITIAL_INVENTORY[sku] = {}
                                INITIAL_INVENTORY[sku][name] = int(value)
                            except ValueError:
                                print(f"Warning: Could not convert InitialInventory for '{sku}' '{name}' value '{value}' to int.")
        else:
            print("Error: Missing one or more expected columns in ORA_Configuration sheet for parsing (ParameterCategory, ParameterName, Value, SKU).")
    else:
        print("No data retrieved from ORA_Configuration sheet or sheet is empty/malformed.")
    
    print(f"Rates: {RATES}")
    print(f"Pallet Counts: {PALLET_COUNTS}")
    print(f"Initial Inventory (EOD_Prior_Week): {INITIAL_INVENTORY}")

    # Static Inventory_Transactions data based on your last successful load
    inventory_transactions_raw = [
        ['Date', 'SKU', 'Quantity', 'TransactionType'],
        ['2025-05-16', '17612', '528', 'Receive'],
        ['2025-05-20', '17612', '576', 'Receive'],
        ['2025-05-25', '17612', '576', 'Receive'],
        ['2025-05-02', '17612', '382', 'Receive'],
        ['2025-05-12', '17612', '5', 'Repack'],
        ['2025-05-10', '17904', '10', 'Receive'], # Added for more varied data
        ['2025-05-15', '18675', '20', 'Repack']  # Added for more varied data
    ]
    print(f"\n--- Inventory Transactions Loaded --- (HARDCODED FOR DEBUGGING)")

    inventory_transactions_df = pd.DataFrame() 

    if inventory_transactions_raw:
        headers = [h.strip() for h in inventory_transactions_raw[0]]
        data_rows = inventory_transactions_raw[1:]
        
        if headers: 
            inventory_transactions_df = pd.DataFrame(data_rows, columns=headers)
            if 'Date' in inventory_transactions_df.columns:
                try:
                    inventory_transactions_df['Date'] = pd.to_datetime(inventory_transactions_df['Date'])
                except Exception as e:
                    print(f"Warning: Could not convert 'Date' column to datetime in Inventory_Transactions. Details: {e}")
            if 'Quantity' in inventory_transactions_df.columns:
                try:
                    inventory_transactions_df['Quantity'] = pd.to_numeric(inventory_transactions_df['Quantity'])
                except Exception as e:
                    print(f"Warning: Could not convert 'Quantity' column to numeric in Inventory_Transactions. Details: {e}")
            
            print(f"Shape: {inventory_transactions_df.shape}")
            print("Head:\n", inventory_transactions_df.head())
        else:
            print("Error: Inventory_Transactions sheet has no headers.")
    else:
        print("No data retrieved from Inventory_Transactions sheet or sheet is empty/malformed.")

    # --- Calculations for Monthly Charge Report ---

    # Define the reporting period based on initial_inventory (EOD_Prior_Week)
    # Find the earliest date in your processed_shipments_df as the start of the report period
    report_start_date = processed_shipments_df['Date'].min() if not processed_shipments_df.empty else datetime.date.today()
    report_end_date = processed_shipments_df['Date'].max() if not processed_shipments_df.empty else datetime.date.today()

    # Generate all dates in the reporting period
    all_dates = pd.to_datetime(pd.date_range(start=report_start_date, end=report_end_date, freq='D')).normalize() # Ensure datetime64[ns]
    all_skus = list(PALLET_COUNTS.keys()) # Get all relevant SKUs from Pallet Counts

    # 1. Daily Aggregations (replicates SQL DailyShippedSKUQty_Golden and DailyOrderCount_Golden)
    DailyShippedSKUQty_DF, DailyOrderCount_DF = process_daily_aggregations(processed_shipments_df)
    
    print(f"\n--- Daily Aggregated Shipments ---")
    print(f"Shape: {DailyShippedSKUQty_DF.shape}")
    print("Head:\n", DailyShippedSKUQty_DF.head())

    print(f"\n--- Daily Order Count ---")
    print(f"Shape: {DailyOrderCount_DF.shape}")
    print("Head:\n", DailyOrderCount_DF.head())

    # 2. Daily Inventory Movements (replicates SQL DailyInventoryMovements_Golden)
    # Combine shipped quantities from DailyShippedSKUQty_DF with received/repacked from inventory_transactions_df
    # Ensure all_dates and inventory_transactions_df dates are consistent (datetime.date objects)
    # Check if 'Date' column exists before trying to access .dt.date
    if 'Date' in inventory_transactions_df.columns:
        inventory_transactions_df['Date'] = pd.to_datetime(inventory_transactions_df['Date']).dt.normalize() # Ensure datetime64[ns]
    
    # Ensure DailyShippedSKUQty_DF['Date'] is also datetime64[ns] (it should be if process_daily_aggregations is correct)
    DailyShippedSKUQty_DF['Date'] = pd.to_datetime(DailyShippedSKUQty_DF['Date']).dt.normalize()
    DailyShippedSKUQty_DF['SKU'] = DailyShippedSKUQty_DF['SKU'].astype(str) # Ensure SKU is string for merge

    # Aggregate received and repacked quantities per SKU per day from inventory_transactions_df
    received_df = inventory_transactions_df[inventory_transactions_df['TransactionType'] == 'Receive'].groupby(['Date', 'SKU'])['Quantity'].sum().reset_index()
    received_df.rename(columns={'Quantity': 'ReceivedQty'}, inplace=True)
    received_df['SKU'] = received_df['SKU'].astype(str) # Ensure SKU is string for merge

    repacked_df = inventory_transactions_df[inventory_transactions_df['TransactionType'] == 'Repack'].groupby(['Date', 'SKU'])['Quantity'].sum().reset_index()
    repacked_df.rename(columns={'Quantity': 'RepackedQty'}, inplace=True)
    repacked_df['SKU'] = repacked_df['SKU'].astype(str) # Ensure SKU is string for merge

    # Initialize AllDailySKUMovements_DF with all date-SKU combinations and default to 0
    all_date_sku_combinations = pd.MultiIndex.from_product([all_dates, all_skus], names=['Date', 'SKU']).to_frame(index=False)
    all_date_sku_combinations['SKU'] = all_date_sku_combinations['SKU'].astype(str) # Ensure SKU is string for merge

    AllDailySKUMovements_DF = pd.merge(
        all_date_sku_combinations,
        DailyShippedSKUQty_DF.rename(columns={'TotalQtyShipped': 'ShippedQty', 'BaseSKU': 'SKU'}), # Use BaseSKU rename for merge
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'ShippedQty': 0}) # Fill NaN with 0 for shipped

    AllDailySKUMovements_DF = pd.merge(
        AllDailySKUMovements_DF,
        received_df,
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'ReceivedQty': 0})

    AllDailySKUMovements_DF = pd.merge(
        AllDailySKUMovements_DF,
        repacked_df,
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'RepackedQty': 0})

    # Ensure all quantities are integers
    AllDailySKUMovements_DF['ShippedQty'] = AllDailySKUMovements_DF['ShippedQty'].astype(int)
    AllDailySKUMovements_DF['ReceivedQty'] = AllDailySKUMovements_DF['ReceivedQty'].astype(int)
    AllDailySKUMovements_DF['RepackedQty'] = AllDailySKUMovements_DF['RepackedQty'].astype(int)

    print(f"\n--- All Daily SKU Movements ---")
    print(f"Shape: {AllDailySKUMovements_DF.shape}")
    print("Head:\n", AllDailySKUMovements_DF.head())

    # 3. Daily Inventory (BOD and EOD) Calculation
    # Need to prepare initial_inventory_map into a consistent format for the function
    # Example: {'17612': {'EOD_Prior_Week': 615}} -> {'17612': 615}
    initial_inventory_for_calc = {
        sku: data.get('EOD_Prior_Week', 0) # Assuming 'EOD_Prior_Week' is the key for the initial quantity
        for sku, data in INITIAL_INVENTORY.items()
    }

    DailyInventory_DF = calculate_daily_inventory(
        initial_inventory_for_calc, 
        all_skus, 
        all_dates, 
        AllDailySKUMovements_DF[['Date', 'SKU', 'ShippedQty', 'ReceivedQty', 'RepackedQty']] # Pass relevant columns
    )

    print(f"\n--- Daily Inventory (BOD/EOD) ---")
    print(f"Shape: {DailyInventory_DF.shape}")
    print("Head:\n", DailyInventory_DF.head())

    # --- Final Monthly Charge Report Aggregation ---
    # Merge Daily Inventory, Daily Shipped SKU Quantity, and Daily Order Count
    # Start with DailyInventory_DF as base, as it has all dates and SKUs
    MonthlyChargeReport_DF = pd.merge(
        DailyInventory_DF,
        DailyShippedSKUQty_DF, # This now has 'SKU' and 'Date' after renaming in process_daily_aggregations
        on=['Date', 'SKU'],
        how='left'
    ).fillna({'TotalQtyShipped': 0}) # Fill shipped with 0 for days with no shipments

    MonthlyChargeReport_DF = pd.merge(
        MonthlyChargeReport_DF,
        DailyOrderCount_DF,
        on='Date',
        how='left'
    ).fillna({'CountOfOrders': 0}) # Fill order count with 0 for days with no orders

    # Calculate Space Rental Charge
    # Handle division by zero for pallet counts that might be 0
    MonthlyChargeReport_DF['PalletsUsed'] = MonthlyChargeReport_DF.apply(
        lambda row: math.ceil(row['EOD_Qty'] / PALLET_COUNTS.get(row['SKU'], 1)) if PALLET_COUNTS.get(row['SKU'], 1) > 0 else 0,
        axis=1
    )
    # Ensure SpaceRentalRate is correctly retrieved from RATES
    space_rental_rate = RATES.get('SpaceRentalRate', 0.0)
    MonthlyChargeReport_DF['Space_Rental_Charge_Per_SKU'] = MonthlyChargeReport_DF['PalletsUsed'] * space_rental_rate

    # Aggregate Space Rental Charge per day across all SKUs
    DailySpaceRentalCharge = MonthlyChargeReport_DF.groupby('Date')['Space_Rental_Charge_Per_SKU'].sum().reset_index()
    DailySpaceRentalCharge.rename(columns={'Space_Rental_Charge_Per_SKU': 'Space_Rental_Charge'}, inplace=True)

    # Merge all daily charges into one DataFrame
    FinalDailyReport_DF = pd.merge(
        DailyOrderCount_DF,
        DailySpaceRentalCharge,
        on='Date',
        how='left'
    ).fillna({'Space_Rental_Charge': 0})

    # Calculate Total Packages Shipped per day
    DailyPackagesShipped = DailyShippedSKUQty_DF.groupby('Date')['TotalQtyShipped'].sum().reset_index()
    DailyPackagesShipped.rename(columns={'TotalQtyShipped': 'TotalPackagesShipped'}, inplace=True)

    FinalDailyReport_DF = pd.merge(
        FinalDailyReport_DF,
        DailyPackagesShipped,
        on='Date',
        how='left'
    ).fillna({'TotalPackagesShipped': 0})

    # Calculate Charges
    order_charge_rate = RATES.get('OrderCharge', 0.0)
    package_charge_rate = RATES.get('PackageCharge', 0.0)

    FinalDailyReport_DF['Orders_Charge'] = FinalDailyReport_DF['CountOfOrders'] * order_charge_rate
    FinalDailyReport_DF['Packages_Charge'] = FinalDailyReport_DF['TotalPackagesShipped'] * package_charge_rate
    FinalDailyReport_DF['Total_Charge'] = (
        FinalDailyReport_DF['Orders_Charge'] + 
        FinalDailyReport_DF['Packages_Charge'] + 
        FinalDailyReport_DF['Space_Rental_Charge']
    )

    # Reformat to desired output columns and order
    output_columns = [
        'Date', '# Of Orders', '17612_Shipped', '17904_Shipped', '17914_Shipped', '18675_Shipped',
        'Orders_Charge', 'Packages_Charge', 'Space_Rental_Charge', 'Total_Charge'
    ]

    # Dynamically pivot shipped quantities for SKU columns
    # Need to handle cases where a SKU might not have shipments on a given day
    pivot_shipped_qty = DailyShippedSKUQty_DF.pivot_table(
        index='Date', 
        columns='SKU', # Changed from BaseSKU to SKU because it's renamed in process_daily_aggregations
        values='TotalQtyShipped', 
        fill_value=0
    ).reset_index()

    # Rename columns to match desired output format
    column_rename_map = {f'{sku}': f'{sku}_Shipped' for sku in PALLET_COUNTS.keys()}
    pivot_shipped_qty.rename(columns=column_rename_map, inplace=True)

    # Merge pivoted shipments back to FinalDailyReport_DF
    MonthlyChargeReport_DF_Final = pd.merge(
        FinalDailyReport_DF,
        pivot_shipped_qty,
        on='Date',
        how='left'
    ).fillna(0) # Fill any missing SKU_Shipped values with 0

    # Rename CountOfOrders to '# Of Orders'
    MonthlyChargeReport_DF_Final.rename(columns={'CountOfOrders': '# Of Orders'}, inplace=True)

    # Ensure all target SKU_Shipped columns exist, even if no data for them
    for sku_key in PALLET_COUNTS.keys():
        col_name = f'{sku_key}_Shipped'
        if col_name not in MonthlyChargeReport_DF_Final.columns:
            MonthlyChargeReport_DF_Final[col_name] = 0
    
    # Select and order final columns
    MonthlyChargeReport_DF_Final = MonthlyChargeReport_DF_Final[output_columns]
    
    print(f"\n--- Monthly Charge Report (Daily) ---")
    print(f"Shape: {MonthlyChargeReport_DF_Final.shape}")
    print("Head:\n", MonthlyChargeReport_DF_Final.head())

    # Monthly Totals Row
    MonthlyTotals_DF = pd.DataFrame([{
        'Date': 'Monthly Totals',
        '# Of Orders': MonthlyChargeReport_DF_Final['# Of Orders'].sum(),
        '17612_Shipped': MonthlyChargeReport_DF_Final['17612_Shipped'].sum() if '17612_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        '17904_Shipped': MonthlyChargeReport_DF_Final['17904_Shipped'].sum() if '17904_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        '17914_Shipped': MonthlyChargeReport_DF_Final['17914_Shipped'].sum() if '17914_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        '18675_Shipped': MonthlyChargeReport_DF_Final['18675_Shipped'].sum() if '18675_Shipped' in MonthlyChargeReport_DF_Final.columns else 0,
        'Orders_Charge': MonthlyChargeReport_DF_Final['Orders_Charge'].sum(),
        'Packages_Charge': MonthlyChargeReport_DF_Final['Packages_Charge'].sum(),
        'Space_Rental_Charge': MonthlyChargeReport_DF_Final['Space_Rental_Charge'].sum(),
        'Total_Charge': MonthlyChargeReport_DF_Final['Total_Charge'].sum()
    }])

    print(f"\n--- Monthly Totals ---")
    print("Head:\n", MonthlyTotals_DF.head())


    # --- Write to Google Sheets ---
    # This will be done in a separate function when re-enabling Google API calls
    # For now, just print the final DataFrame
    print("\nAttempting to write Monthly Charge Report to Google Sheets...")
    # This part remains commented out/placeholder until Google API is fully functional
    # and credentials are moved out of hardcoding.
    # write_google_sheet_data(
    #     GOOGLE_SHEET_ID,
    #     MONTHLY_CHARGE_REPORT_TAB_NAME + "!A1", # Start writing from A1
    #     google_sheets_service_account_json,
    #     MonthlyChargeReport_DF_Final # Pass the DataFrame to be written
    # )
    # print("Monthly Charge Report writing process complete.")

    print("Script finished. (Raw data and configuration loaded)")

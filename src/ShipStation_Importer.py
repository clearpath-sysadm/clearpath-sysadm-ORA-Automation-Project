import requests
from google.cloud import secretmanager
import base64
import json
import datetime
import time # For potential delays
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd # Added for data processing

# --- Configuration for ShipStation API ---
YOUR_GCP_PROJECT_ID = "ora-automation-project"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com" # Use the confirmed base URL

# --- ShipStation API Endpoints for Reporting Data ---
SHIPSTATION_SHIPMENTS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/shipments"
SHIPSTATION_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders" # For getting fulfilled orders details if needed

# --- TEMPORARY: HARDCODE THE JSON KEY PATH TO TEST ACCESS ---
# IMPORTANT: THIS IS A TEMPORARY MEASURE TO DEBUG.
# REPLACE 'ora-automation-project-2345f75740f8.json' with your *exact* JSON key filename
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"


# --- Google Sheets API Configuration for State Management ---
# IMPORTANT: Replace with the actual ID of your "Project Tracker - ORA" Google Sheet
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
# This is the range for the last processed shipment date in ORA_Processing_State tab
ORA_PROCESSING_STATE_RANGE = 'ORA_Processing_State' # Simpler range to avoid parsing errors

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
    "18445": {"component_id": "17612", "multiplier": 1},  # Autoship; FREE Case OraCare Health Rinse
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
    """
    try:
        if credentials_path:
            client = secretmanager.SecretManagerServiceClient.from_service_account_json(credentials_path)
        else:
            client = secretmanager.SecretManagerServiceClient()

        name = client.secret_version_path(project_id, secret_id, version_id)
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return payload

    except Exception as e:
        print(f"Error accessing secret '{secret_id}' version '{version_id}' in project '{project_id}': {e}")
        print(f"Details: {e}")
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
    """
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
    except Exception as e:
        print(f"Error accessing Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
        print(f"Details: {e}")
        return []

# NEW FUNCTION: Fetches shipments data from ShipStation API
def fetch_shipstation_shipments(api_key, api_secret, start_date, end_date=None):
    """
    Fetches shipments data from ShipStation API, handling pagination.
    start_date: impromptu-MM-DD HH:MM:SS string (shipDateStart)
    end_date: impromptu-MM-DD HH:MM:SS string (shipDateEnd, optional)
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_shipments = []
    page = 1
    page_size = 500 # Max allowed by ShipStation, for fewer API calls

    print(f"Fetching ShipStation shipments from {start_date}...")

    while True:
        params = {
            'shipDateStart': start_date,
            'pageSize': page_size,
            'page': page
        }
        if end_date:
            params['shipDateEnd'] = end_date

        try:
            response = requests.get(SHIPSTATION_SHIPMENTS_ENDPOINT, headers=headers, params=params, timeout=60)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            shipments = data.get('shipments', [])

            if not shipments:
                break # No more shipments to fetch

            all_shipments.extend(shipments)
            print(f"Fetched page {page}: {len(shipments)} shipments.")

            if len(shipments) < page_size:
                break # Last page
            
            page += 1
            time.sleep(0.5) # Be kind to the API, especially with multiple pages

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error fetching shipments: {http_err}")
            print(f"ShipStation API Response (Error): {response.text}")
            return []
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error fetching shipments: {conn_err}")
            return []
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error fetching shipments: {timeout_err}")
            return []
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected request error occurred fetching shipments: {req_err}")
            return []
        except json.JSONDecodeError:
            print(f"Error decoding JSON response from ShipStation. Response: {response.text}")
            return []
        except Exception as e:
            print(f"An unknown error occurred fetching shipments: {e}")
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
        # For simplicity, not extracting all original ShipStation fields, focusing on needed for report
        # carrier_code = shipment.get('carrierCode')
        # service_code = shipment.get('serviceCode')
        # tracking_number = shipment.get('trackingNumber')

        # Ensure shipmentItems is a list, even if None
        shipment_items = shipment.get('shipmentItems')
        if shipment_items is None:
            shipment_items = []

        for item in shipment_items:
            original_product_id = str(item.get('sku')) # Ensure SKU is string for consistency
            original_quantity = item.get('quantity', 0)
            item_name = item.get('name', 'N/A')

            # Apply bundling logic
            if original_product_id in bundle_config:
                bundle_definition = bundle_config[original_product_id]
                if isinstance(bundle_definition, dict): # Single-component bundle
                    component_id = bundle_definition.get('component_id')
                    multiplier = bundle_definition.get('multiplier', 1)
                    expanded_quantity = original_quantity * multiplier
                    processed_items.append({
                        'Date': ship_date,
                        'OrderNumber': order_number,
                        'BaseSKU': component_id, # Use component SKU
                        'QuantityShipped': expanded_quantity,
                        'OriginalSKU': original_product_id, # Keep original bundle SKU for traceability
                        'ItemName': item_name
                    })
                    # print(f"DEBUG: Processed bundle {original_product_id} to {expanded_quantity}x {component_id}") # Keep for debugging
                elif isinstance(bundle_definition, list): # Multi-component bundle
                    for component_info in bundle_definition:
                        component_id = component_info.get('component_id')
                        multiplier = component_info.get('multiplier', 1)
                        expanded_quantity = original_quantity * multiplier
                        processed_items.append({
                            'Date': ship_date,
                            'OrderNumber': order_number,
                            'BaseSKU': component_id, # Use component SKU
                            'QuantityShipped': expanded_quantity,
                            'OriginalSKU': original_product_id, # Keep original bundle SKU for traceability
                            'ItemName': item_name
                        })
                        # print(f"DEBUG: Processed multi-component bundle {original_product_id} to {expanded_quantity}x {component_id}") # Keep for debugging
            else:
                # Not a bundle, add as-is
                processed_items.append({
                    'Date': ship_date,
                    'OrderNumber': order_number,
                    'BaseSKU': original_product_id, # Use original SKU
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


if __name__ == "__main__":
    print("Starting ShipStation Reporter Script...")
    # Retrieve ShipStation API credentials
    shipstation_api_key = access_secret_version(
        YOUR_GCP_PROJECT_ID,
        SHIPSTATION_API_KEY_SECRET_ID,
        credentials_path=SERVICE_ACCOUNT_KEY_PATH
    )
    shipstation_api_secret = access_secret_version(
        YOUR_GCP_PROJECT_ID,
        SHIPSTATION_API_SECRET_SECRET_ID,
        credentials_path=SERVICE_ACCOUNT_KEY_PATH
    )

    if not shipstation_api_key or not shipstation_api_secret:
        print("Failed to retrieve ShipStation API credentials. Exiting.")
        exit()

    print(f"ShipStation API Key retrieved (truncated): {shipstation_api_key[:5]}...")
    print(f"ShipStation API Secret retrieved (truncated): {shipstation_api_secret[:5]}...")

    # --- Retrieve Google Sheets Service Account Key ---
    google_sheets_service_account_json = access_secret_version(
        YOUR_GCP_PROJECT_ID,
        GOOGLE_SHEETS_SERVICE_ACCOUNT_SECRET_ID,
        credentials_path=SERVICE_ACCOUNT_KEY_PATH # Reuse the same path as ShipStation secrets
    )

    if not google_sheets_service_account_json:
        print("Failed to retrieve Google Sheets service account key. Exiting.")
        exit()
    else:
        print(f"Google Sheets Service Account Key retrieved (truncated): {google_sheets_service_account_json[:5]}...")

    # --- Get Last Processed Shipment Date from ORA_Processing_State ---
    last_processed_state_data = get_google_sheet_data(
        GOOGLE_SHEET_ID,
        ORA_PROCESSING_STATE_RANGE,
        google_sheets_service_account_json
    )

    last_processed_shipment_date = None
    if last_processed_state_data and len(last_processed_state_data) > 1: # Check for headers and at least one data row
        # Assuming 'Key' is in A1 and 'Value' in B1
        # We search for 'LastProcessedShipmentDate' in column A and get its value from column B
        for row in last_processed_state_data:
            if len(row) >= 2 and row[0].strip() == 'LastProcessedShipmentDate':
                last_processed_shipment_date = row[1].strip()
                break
        
        if last_processed_shipment_date:
            print(f"Retrieved LastProcessedShipmentDate: {last_processed_shipment_date}")
        else:
            # Fallback if key not found, e.g., use a very old date or initial cutoff
            print("LastProcessedShipmentDate not found in ORA_Processing_State. Using initial cutoff date.")
            # Use the initial cutoff date from the Comprehensive Specs document (e.g., May 1, 2024)
            last_processed_shipment_date = '2024-05-01 00:00:00' 
    else:
        print("ORA_Processing_State sheet is empty or malformed. Using initial cutoff date.")
        last_processed_shipment_date = '2024-05-01 00:00:00' # Initial cutoff
    
    # --- Fetch ShipStation Shipments Data ---
    # Set the end_date to current time for the report, or leave None for all up to now
    current_time_for_end_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Changed from fetch_shipstation_orders to fetch_shipstation_shipments and added back date constraints
    raw_shipments_data = fetch_shipstation_shipments(
        shipstation_api_key,
        shipstation_api_secret,
        last_processed_shipment_date, # Start date from Google Sheet state
        current_time_for_end_date # End date as current time
    )

    if raw_shipments_data:
        print(f"Successfully fetched {len(raw_shipments_data)} raw shipments from ShipStation.")
        
        # Process ShipStation shipments into a DataFrame, applying bundling
        processed_shipments_df = process_shipstation_shipments_to_daily_df(
            raw_shipments_data,
            BUNDLE_CONFIG # Pass the BUNDLE_CONFIG
        )
        print(f"\n--- Processed Shipments DataFrame ---")
        print(f"Shape: {processed_shipments_df.shape}")
        print("Head:\n", processed_shipments_df.head())

    else:
        print("No raw shipments fetched from ShipStation or an error occurred.")

    # --- Load ORA_Configuration Data ---
    ora_config_raw = get_google_sheet_data(
        GOOGLE_SHEET_ID,
        ORA_CONFIG_SHEET_RANGE,
        google_sheets_service_account_json
    )

    # Process ORA_Configuration into usable dictionaries
    RATES = {}
    PALLET_COUNTS = {}
    INITIAL_INVENTORY = {} # For initial EOD quantities for a specific date

    if ora_config_raw and len(ora_config_raw) > 1:
        headers = [h.strip() for h in ora_config_raw[0]]
        data_rows = ora_config_raw[1:]

        # Dynamically find column indices
        param_cat_idx = headers.index('ParameterCategory') if 'ParameterCategory' in headers else -1
        param_name_idx = headers.index('ParameterName') if 'ParameterName' in headers else -1
        sku_idx = headers.index('SKU') if 'SKU' in headers else -1
        value_idx = headers.index('Value') if 'Value' in headers else -1

        if all(idx != -1 for idx in [param_cat_idx, param_name_idx, value_idx]):
            for row in data_rows:
                # Corrected: Use value_idx for 'value' instead of row[0]
                if len(row) > max(param_cat_idx, param_name_idx, value_idx, sku_idx):
                    category = row[param_cat_idx].strip()
                    name = row[param_name_idx].strip()
                    value = row[value_idx].strip() # Corrected: Use value_idx for value
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
                        if sku and name: # Name will be the EOD date identifier like 'EOD_Prior_Week'
                            try:
                                # Store as {SKU: {Date_Identifier: Quantity}}
                                if sku not in INITIAL_INVENTORY:
                                    INITIAL_INVENTORY[sku] = {}
                                INITIAL_INVENTORY[sku][name] = int(value)
                            except ValueError:
                                print(f"Warning: Could not convert InitialInventory for '{sku}' '{name}' value '{value}' to int.")
        else:
            print("Error: Missing one or more expected columns in ORA_Configuration sheet for parsing (ParameterCategory, ParameterName, Value, SKU).")
    else:
        print("No data retrieved from ORA_Configuration sheet or sheet is empty/malformed.")
    
    print(f"\n--- ORA Configuration Loaded ---")
    print(f"Rates: {RATES}")
    print(f"Pallet Counts: {PALLET_COUNTS}")
    print(f"Initial Inventory (EOD_Prior_Week): {INITIAL_INVENTORY}")

    # --- Load Inventory_Transactions Data ---
    inventory_transactions_raw = get_google_sheet_data(
        GOOGLE_SHEET_ID,
        INVENTORY_TRANSACTIONS_SHEET_RANGE,
        google_sheets_service_account_json
    )

    inventory_transactions_df = pd.DataFrame() # Initialize empty DataFrame

    if inventory_transactions_raw:
        headers = [h.strip() for h in inventory_transactions_raw[0]]
        data_rows = inventory_transactions_raw[1:]
        
        if headers: # Ensure headers exist
            inventory_transactions_df = pd.DataFrame(data_rows, columns=headers)
            # Convert 'Date' column to datetime objects
            if 'Date' in inventory_transactions_df.columns:
                try:
                    inventory_transactions_df['Date'] = pd.to_datetime(inventory_transactions_df['Date'])
                except Exception as e:
                    print(f"Warning: Could not convert 'Date' column to datetime in Inventory_Transactions. Details: {e}")
            # Convert 'Quantity' column to numeric
            if 'Quantity' in inventory_transactions_df.columns:
                try:
                    inventory_transactions_df['Quantity'] = pd.to_numeric(inventory_transactions_df['Quantity'])
                except Exception as e:
                    print(f"Warning: Could not convert 'Quantity' column to numeric in Inventory_Transactions. Details: {e}")
            
            print(f"\n--- Inventory Transactions Loaded ---")
            print(f"Shape: {inventory_transactions_df.shape}")
            print("Head:\n", inventory_transactions_df.head())
        else:
            print("Error: Inventory_Transactions sheet has no headers.")
    else:
        print("No data retrieved from Inventory_Transactions sheet or sheet is empty/malformed.")

    print("Script finished. (Raw data and configuration loaded)")

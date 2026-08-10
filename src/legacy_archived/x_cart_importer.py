import defusedxml.ElementTree as ET
import os
import datetime
import requests
from google.cloud import secretmanager
import base64
import json
import time # Import time for optional sleep
from google.oauth2 import service_account
from googleapiclient.discovery import build # New import for Google Sheets API

# --- Configuration ---
# Set this to your single-order test file for safe initial testing
X_CART_XML_SAMPLE_FILE = 'x_cart_orders_bundle_test.xml'

# --- Configuration for ShipStatyou see a view right now that Iion API ---
YOUR_GCP_PROJECT_ID = "ora-automation-project"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"

# Corrected Base URL and Endpoint based on original PowerShell script
SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"
SHIPSTATION_CREATE_ORDER_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders/createorders"

# --- Google Sheets API Configuration for SKU-Lot Data ---
# IMPORTANT: Replace with the actual ID of your "Project Tracker - ORA" Google Sheet.
# You find this ID in the Google Sheet's URL (between /d/ and /edit).
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo' # ENSURE THIS IS YOUR CORRECT ID
SKU_LOT_SHEET_RANGE = 'SKU_Lot!A:C' # A:C covers SKU, Lot, Active columns

# Scopes required for reading from Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The Secret ID for your Google Sheets service account JSON key.
GOOGLE_SHEETS_SERVICE_ACCOUNT_SECRET_ID = "google-sheets-service-account-key"

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
    "18355": {"component_id": "17612", "multiplier": 1},  # Free; OraCare Health Rinse
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

    # -------------------------------------------------------------
    # Multi-Component Bundles (from INSERT statements in SPROC)
    # These bundles expand into multiple DIFFERENT SKUs.
    # -------------------------------------------------------------

    # 18605: 4x 17612, 1x 17914, 1x 17904
    # "4 cases of 32 ozOraCare Health Rinse, 1 case of 64 oz PPR, 1 case of 2 oz Travel"
    "18605": [
        {"component_id": "17612", "multiplier": 4},
        {"component_id": "17914", "multiplier": 1},
        {"component_id": "17904", "multiplier": 1},
    ],

    # 18615: 4x 17612, 1x 17914, 1x 17904, 1x 17975
    # "4 cases of 32 ozOraCare Health Rinse, 1 case Reassure, 1 case of 64 oz PPR, 1 case of 2 oz Travel"
    "18615": [
        {"component_id": "17612", "multiplier": 4},
        {"component_id": "17914", "multiplier": 1},
        {"component_id": "17904", "multiplier": 1},
        {"component_id": "17975", "multiplier": 1},
    ]
}


def _get_text_safe(element, tag_name, default=''):
    """
    Helper function to safely get text from a sub-element.
    Returns default if the element or its text is None.
    """
    found_element = element.find(tag_name)
    if found_element is not None and found_element.text is not None:
        return found_element.text.strip()
    return default

# New helper function for SKU-Lot formatting
def format_sku_with_lot(sku_id, sku_lot_map):
    """
    Formats a SKU by appending its active lot number if found in the SKU-Lot map.
    """
    if sku_id in sku_lot_map:
        lot_number = sku_lot_map[sku_id]
        formatted_sku = f"{sku_id} - {lot_number}"
        print(f"DEBUG: Formatting SKU {sku_id} with lot {lot_number}. Result: {formatted_sku}")
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

# Add this function after access_secret_version
def get_google_sheet_data(spreadsheet_id, range_name, service_account_key_json):
    """
    Retrieves data from a Google Sheet using a service account key.
    """
    try:
        # Load credentials from the service account key JSON content
        creds_info = json.loads(service_account_key_json)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

        # Build the Google Sheets service object
        service = build('sheets', 'v4', credentials=creds)
        
        # Call the Sheets API
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

def parse_x_cart_orders(xml_file_path):
    """
    Parses the X-Cart XML data from a given file path and extracts structured order information.
    Returns a list of dictionaries, where each dictionary represents an order.
    """
    orders_data = []
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot() # <DentistSelectOrders>

        for order_elem in root.findall('order'):
            order = {}

            # Extract order-level fields
            order['order_id'] = _get_text_safe(order_elem, 'orderid')
            order['date_timestamp'] = _get_text_safe(order_elem, 'date')
            order['date_human_readable'] = _get_text_safe(order_elem, 'date2')
            order['dentist_code'] = _get_text_safe(order_elem, 'dentistcode')
            order['shipping_method'] = _get_text_safe(order_elem, 'shipping')
            order['company_name'] = _get_text_safe(order_elem, 'company')
            order['email'] = _get_text_safe(order_elem, 'email')

            # Shipping Address
            order['shipping_address'] = {
                'first_name': _get_text_safe(order_elem, 's_firstname'),
                'last_name': _get_text_safe(order_elem, 's_lastname'),
                'company': _get_text_safe(order_elem, 's_company'),
                'address1': _get_text_safe(order_elem, 's_address'),
                'city': _get_text_safe(order_elem, 's_city'),
                'state': _get_text_safe(order_elem, 's_state'),
                'zipcode': _get_text_safe(order_elem, 's_zipcode'),
                'country': _get_text_safe(order_elem, 's_country'),
                'phone': _get_text_safe(order_elem, 's_phone')
            }

            # Billing Address
            order['billing_address'] = {
                'first_name': _get_text_safe(order_elem, 'b_firstname'),
                'last_name': _get_text_safe(order_elem, 'b_lastname'),
                'company': _get_text_safe(order_elem, 'b_company'),
                'address1': _get_text_safe(order_elem, 'b_address'),
                'city': _get_text_safe(order_elem, 'b_city'),
                'state': _get_text_safe(order_elem, 'b_state'),
                'zipcode': _get_text_safe(order_elem, 'b_zipcode'),
                'country': _get_text_safe(order_elem, 'b_country'),
                'phone': _get_text_safe(order_elem, 'b_phone')
            }

            try:
                order['shipping_cost'] = float(_get_text_safe(order_elem, 'shipping_cost', '0.0'))
            except ValueError:
                order['shipping_cost'] = 0.0
                print(f"Warning: Could not convert shipping_cost to float for Order ID: {order['order_id']}")

            order['customer_id'] = _get_text_safe(order_elem, 'customerid')

            # Extract line items
            line_items = []
            for detail_elem in order_elem.findall('order_detail'):
                item = {
                    'product_name': _get_text_safe(detail_elem, 'product'),
                    'product_id': _get_text_safe(detail_elem, 'productid')
                }
                try:
                    item['quantity'] = int(_get_text_safe(detail_elem, 'amount', '0'))
                except ValueError:
                    item['quantity'] = 0
                    print(f"Warning: Could not convert item quantity to int for Order ID: {order['order_id']} Product ID: {item['product_id']}")
                line_items.append(item)

            order['line_items'] = line_items
            orders_data.append(order)

    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}")

    return orders_data

def create_shipstation_order_payload(x_cart_order, sku_lot_map): # sku_lot_map added here
    """
    Transforms a parsed X-Cart order dictionary into a ShipStation Create Order API payload.
    Applies product bundling logic based on BUNDLE_CONFIG and SKU-Lot formatting.
    """
    order_number = x_cart_order.get('order_id')
    
    order_date = datetime.datetime.fromtimestamp(
        int(x_cart_order.get('date_timestamp'))
    ).isoformat() if x_cart_order.get('date_timestamp') else datetime.datetime.now().isoformat()

    shipping_address = x_cart_order.get('shipping_address', {})
    billing_address = x_cart_order.get('billing_address', {})

    shipstation_items = []
    for item in x_cart_order.get('line_items', []):
        original_product_id = item.get('product_id')
        original_quantity = item.get('quantity')

        # Check if the current item is a bundle defined in BUNDLE_CONFIG
        if original_product_id in BUNDLE_CONFIG:
            bundle_definition = BUNDLE_CONFIG[original_product_id]

            # Handle single-component bundles (e.g., "18255": {"component_id": "17612", "multiplier": 6})
            if isinstance(bundle_definition, dict):
                component_id = bundle_definition.get('component_id')
                multiplier = bundle_definition.get('multiplier', 1)
                expanded_quantity = original_quantity * multiplier
                shipstation_items.append({
                    "sku": format_sku_with_lot(component_id, sku_lot_map), # Apply formatting to component SKU
                    "name": f"{item.get('product_name')} (Component: {component_id})", # Add note for clarity
                    "quantity": expanded_quantity,
                    "unitPrice": 0.0 # Default to 0.0 as price is not in X-Cart XML
                })
                print(f"DEBUG: Expanded bundle {original_product_id} to {expanded_quantity}x {component_id}")

            # Handle multi-component bundles (e.g., "18605": [{"component_id": "SKU1", "multiplier": M1}, ...])
            elif isinstance(bundle_definition, list):
                for component_info in bundle_definition:
                    component_id = component_info.get('component_id')
                    multiplier = component_info.get('multiplier', 1)
                    expanded_quantity = original_quantity * multiplier
                    shipstation_items.append({
                        "sku": format_sku_with_lot(component_id, sku_lot_map), # Apply formatting to component SKU
                        "name": f"{item.get('product_name')} (Component: {component_id})", # Add note for clarity
                        "quantity": expanded_quantity,
                        "unitPrice": 0.0 # Default to 0.0 as price is not in X-Cart XML
                    })
                    print(f"DEBUG: Expanded multi-component bundle {original_product_id} to {expanded_quantity}x {component_id}")
        else:
            # If it's not a bundle, apply SKU-Lot formatting and add the item as-is
            shipstation_items.append({
                "sku": format_sku_with_lot(original_product_id, sku_lot_map), # Apply formatting
                "name": item.get('product_name'),
                "quantity": original_quantity,
                "unitPrice": 0.0 # Default to 0.0 as price is not in X-Cart XML
            })
    payload = {
        "orderNumber": order_number,
        "orderDate": order_date,
        "customerEmail": x_cart_order.get('email'),
        "customerUsername": x_cart_order.get('customer_id'),
        "orderStatus": "awaiting_shipment",
        "amountPaid": 0.0, # Not available from X-Cart XML
        "shippingAmount": x_cart_order.get('shipping_cost'),
        "internalNotes": f"X-Cart Dentist Code: {x_cart_order.get('dentist_code', 'N/A')}",
        "requestedShippingService": x_cart_order.get('shipping_method'),

        "shipTo": {
            "name": f"{shipping_address.get('first_name')} {shipping_address.get('last_name')}".strip(),
            "company": shipping_address.get('company'),
            "street1": shipping_address.get('address1'),
            "city": shipping_address.get('city'),
            "state": shipping_address.get('state'),
            "postalCode": shipping_address.get('zipcode'),
            "country": shipping_address.get('country'),
            "phone": shipping_address.get('phone')
        },
        "billTo": {
            "name": f"{billing_address.get('first_name')} {billing_address.get('last_name')}".strip(),
            "company": billing_address.get('company'),
            "street1": billing_address.get('address1'),
            "city": billing_address.get('city'),
            "state": billing_address.get('state'),
            "postalCode": billing_address.get('zipcode'),
            "country": billing_address.get('country'),
            "phone": billing_address.get('phone')
        },
        "items": shipstation_items
    }
    return payload

def send_order_to_shipstation(payload, api_key, api_secret):
    """
    Sends a single ShipStation order payload to the ShipStation API.
    Returns True on success, False on failure.
    """
    # ShipStation API requires Base64 encoded API Key:API Secret for Basic Authentication
    auth_string = f"{api_key}:{api_secret}"
    encoded_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth_string}"
    }

    print(f"Attempting to send order {payload.get('orderNumber')} to ShipStation...")
    try:
        # CRITICAL FIX: Send payload as a JSON array (even if it's just one item)
        response = requests.post(SHIPSTATION_CREATE_ORDER_ENDPOINT, headers=headers, json=[payload], timeout=30)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        # If successful, parse the response
        shipstation_response = response.json()
        print(f"Successfully sent order {payload.get('orderNumber')} to ShipStation. ShipStation Order ID: {shipstation_response.get('orderId')}")
        # You might want to log the full response for auditing
        return True
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while sending order {payload.get('orderNumber')}: {http_err}")
        print(f"ShipStation API Response (Error): {response.text}")
        return False
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred while sending order {payload.get('orderNumber')}: {conn_err}")
        return False
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred while sending order {payload.get('orderNumber')}: {timeout_err}")
        return False
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred while sending order {payload.get('orderNumber')}: {req_err}")
        return False
    except json.JSONDecodeError:
        print(f"Error decoding JSON response from ShipStation for order {payload.get('orderNumber')}. Response: {response.text}")
        return False
    except Exception as e:
        print(f"An unknown error occurred while sending order {payload.get('orderNumber')}: {e}")
        return False

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)
    xml_full_path = os.path.join(script_dir, X_CART_XML_SAMPLE_FILE)

    print(f"Attempting to parse XML from: {xml_full_path}")
    parsed_orders = parse_x_cart_orders(xml_full_path)

    # --- TEMPORARY: HARDCODE THE JSON KEY PATH TO TEST ACCESS ---
    # IMPORTANT: THIS IS A TEMPORARY MEASURE TO DEBUG.
    # REPLACE 'ora-automation-project-2345f75740f8.json' with your *exact* JSON key filename
    SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"
    # The 'r' before the string means it's a raw string, preventing backslashes from being escape characters.

    # Retrieve ShipStation API credentials using the hardcoded path
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
        print("Failed to retrieve ShipStation API credentials. Cannot proceed with import.")
        exit()

    print(f"ShipStation API Key retrieved (truncated): {shipstation_api_key[:5]}...")
    print(f"ShipStation API Secret retrieved (truncated): {shipstation_api_secret[:5]}...")

    # --- Retrieve Google Sheets Service Account Key ---
    # Using the hardcoded path for consistency with other secret retrieval for now
    google_sheets_service_account_json = access_secret_version(
        YOUR_GCP_PROJECT_ID,
        GOOGLE_SHEETS_SERVICE_ACCOUNT_SECRET_ID,
        credentials_path=SERVICE_ACCOUNT_KEY_PATH # Reuse the same path as ShipStation secrets
    )

    if not google_sheets_service_account_json:
        print("Failed to retrieve Google Sheets service account key. Cannot proceed with SKU-Lot lookup.")
        exit()
    else:
        print(f"Google Sheets Service Account Key retrieved (truncated): {google_sheets_service_account_json[:5]}...")


    # --- Get SKU-Lot data from Google Sheet ---
    sku_lot_data_raw = get_google_sheet_data(
        GOOGLE_SHEET_ID,
        SKU_LOT_SHEET_RANGE,
        google_sheets_service_account_json
    )

    # Process raw data into a usable dictionary
    SKU_LOT_MAP = {}
    if sku_lot_data_raw:
        headers = sku_lot_data_raw[0]
        data_rows = sku_lot_data_raw[1:] # Skip header row

        # Find column indices dynamically to be robust to column order changes
        sku_col_idx = -1
        lot_col_idx = -1
        active_col_idx = -1
        for i, header in enumerate(headers):
            if header.strip().lower() == 'sku':
                sku_col_idx = i
            elif header.strip().lower() == 'lot':
                lot_col_idx = i
            elif header.strip().lower() == 'active':
                active_col_idx = i

        if sku_col_idx != -1 and lot_col_idx != -1 and active_col_idx != -1:
            for row in data_rows:
                # Ensure row has enough columns before accessing
                if len(row) > max(sku_col_idx, lot_col_idx, active_col_idx):
                    sku = row[sku_col_idx].strip()
                    lot = row[lot_col_idx].strip()
                    active_status = row[active_col_idx].strip().lower() # Convert to lowercase for comparison

                    if active_status == 'true': # Assuming 'TRUE' is string from Sheet
                        if sku not in SKU_LOT_MAP: # Ensure we only pick one active lot per SKU
                            SKU_LOT_MAP[sku] = lot
                        else:
                            print(f"Warning: Multiple active lots found for SKU '{sku}'. Using the first one found.")
                else:
                    print(f"Warning: Skipping row due to insufficient columns: {row}")
        else:
            print(f"Error: Missing one or more expected columns (SKU, Lot, Active) in SKU_Lot Google Sheet. Headers found: {headers}")
    else:
        print("No SKU-Lot data retrieved from Google Sheet or an error occurred.")
    
    print(f"\n--- SKU-Lot Map Loaded ({len(SKU_LOT_MAP)} active SKUs) ---")
    print(SKU_LOT_MAP) # For debugging, print the loaded map

    if parsed_orders:
        print(f"\n--- Successfully Parsed {len(parsed_orders)} Orders ---")
        print(f"Attempting to import {len(parsed_orders)} order(s) into ShipStation...")
        
# Initialize counters for import summary
        successful_imports_count = 0
        failed_imports_count = 0
        skipped_imports_count = 0 # New counter for skipped orders

        for x_cart_order in parsed_orders:
            order_id = x_cart_order.get('order_id', 'UNKNOWN_ORDER_ID')
            print(f"\nProcessing Order ID: {order_id}")

            # --- Validation Step: Check for Missing SKU-Lot Entries ---
            # We need to determine the final SKUs after bundling first, then check their lots
            # For a robust check, we'll temporarily create the payload to get the final SKUs
            # without actually sending it, just to validate the items.

            # Create a dummy payload to check the final SKUs (without lot numbers for this check)
            # This temporarily calls create_shipstation_order_payload without the SKU_LOT_MAP to get raw SKUs
            temp_payload_for_validation = create_shipstation_order_payload(x_cart_order, {}) # Pass empty map

            skus_to_check = []
            for item in temp_payload_for_validation.get('items', []):
                # Extract the base SKU without lot (if any) for checking against SKU_LOT_MAP
                base_sku = item.get('sku').split(' - ')[0].split('-')[0] # Handles both "SKU - Lot" and "SKU-Lot" and just "SKU"
                skus_to_check.append(base_sku)

            all_skus_have_active_lot = True
            missing_lot_skus = []
            for sku in skus_to_check:
                if sku not in SKU_LOT_MAP:
                    all_skus_have_active_lot = False
                    missing_lot_skus.append(sku)

            if not all_skus_have_active_lot:
                print(f"SKIPPING Order {order_id}: One or more SKUs are missing active lot numbers in SKU_Lot tab: {', '.join(missing_lot_skus)}")
                skipped_imports_count += 1
                continue # Skip to the next order if validation fails
            # --- End Validation Step ---

            # If validation passes, proceed with creating the actual payload with lot numbers
            shipstation_payload = create_shipstation_order_payload(x_cart_order, SKU_LOT_MAP) 

            if send_order_to_shipstation(shipstation_payload, shipstation_api_key, shipstation_api_secret):
                successful_imports_count += 1
            else:
                failed_imports_count += 1

            # Optional: Add a small delay between API calls to respect rate limits
            # time.sleep(0.5) # Wait 0.5 seconds between requests if needed in production

        print(f"\n--- ShipStation Import Summary ---")
        print(f"Total Orders Attempted: {len(parsed_orders)}")
        print(f"Successfully Imported: {successful_imports_count}")
        print(f"Failed Imports: {failed_imports_count}")
        print(f"Skipped Due to Missing Lot: {skipped_imports_count}") # New summary line
    else:
        print("No orders parsed from XML or an error occurred during parsing/")
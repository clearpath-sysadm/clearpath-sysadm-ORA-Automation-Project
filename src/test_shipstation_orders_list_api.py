import requests
from google.cloud import secretmanager
import base64
import json
import datetime
import time # For potential delays

# --- Configuration for ShipStation API ---
YOUR_GCP_PROJECT_ID = "ora-automation-project"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"

SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"
SHIPSTATION_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders" # Target the orders endpoint

# --- TEMPORARY: HARDCODE THE JSON KEY PATH TO TEST ACCESS ---
# IMPORTANT: This is a temporary measure for local debugging.
# REPLACE 'ora-automation-project-2345f75740f8.json' with your *exact* JSON key filename
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"


# --- Helper Functions (from previous versions) ---

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

def fetch_shipstation_orders_raw(api_key, api_secret, start_date, end_date=None):
    """
    Fetches orders data from ShipStation API, handling pagination and filtering by modified date and status.
    This version includes verbose debugging for orderItems.
    start_date: impromptu-MM-DD HH:MM:SS string (modifyDateStart)
    end_date: impromptu-MM-DD HH:MM:SS string (modifyDateEnd, optional)
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    page = 1
    page_size = 500 # Max allowed by ShipStation, for fewer API calls

    print(f"DEBUG: Starting raw order fetch from {start_date} with status 'shipped'...")

    while True:
        params = {
            'modifyDateStart': start_date, # Using modifyDateStart as per your previous request
            'orderStatus': 'shipped',     # Filtering by shipped status
            'pageSize': page_size,
            'page': page
        }
        if end_date:
            params['modifyDateEnd'] = end_date
        else:
            # If no explicit end_date, cap at current time to avoid fetching future non-existent data
            params['modifyDateEnd'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            response = requests.get(SHIPSTATION_ORDERS_ENDPOINT, headers=headers, params=params, timeout=60)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            orders = data.get('orders', [])

            # --- DEBUGGING OUTPUT FOR ORDER ITEMS ---
            if page == 1 and orders:
                print(f"DEBUG: Inspecting raw 'orderItems' for first 5 orders on page {page}:")
                for i, o in enumerate(orders[:5]):
                    print(f"  Order {i+1} (ID: {o.get('orderId')}, Order #: {o.get('orderNumber')}):")
                    if 'orderItems' in o:
                        print(f"    orderItems: {json.dumps(o['orderItems'], indent=2)}")
                    else:
                        print("    orderItems: [KEY NOT PRESENT IN RESPONSE]")
            # --- END DEBUGGING OUTPUT ---

            if not orders:
                print(f"DEBUG: No orders found on page {page}. Ending fetch.")
                break # No more orders to fetch

            all_orders.extend(orders)
            print(f"Fetched page {page}: {len(orders)} orders.")

            if len(orders) < page_size:
                print(f"DEBUG: Fewer than {page_size} orders on page {page}. Assuming last page.")
                break # Last page
            
            page += 1
            time.sleep(0.5) # Be kind to the API

        except requests.exceptions.HTTPError as http_err:
            print(f"ERROR: HTTP error fetching orders: {http_err}")
            print(f"RESPONSE_TEXT: {response.text}")
            return []
        except requests.exceptions.ConnectionError as conn_err:
            print(f"ERROR: Connection error fetching orders: {conn_err}")
            return []
        except requests.exceptions.Timeout as timeout_err:
            print(f"ERROR: Timeout error fetching orders: {timeout_err}")
            return []
        except requests.exceptions.RequestException as req_err:
            print(f"ERROR: An unexpected request error occurred fetching orders: {req_err}")
            return []
        except json.JSONDecodeError:
            print(f"ERROR: Error decoding JSON response from ShipStation. Response: {response.text}")
            return []
        except Exception as e:
            print(f"ERROR: An unknown error occurred fetching orders: {e}")
            import traceback
            traceback.print_exc()
            return []

    print(f"Finished fetching ShipStation orders. Total retrieved: {len(all_orders)}")
    return all_orders


if __name__ == "__main__":
    print("Starting ShipStation Orders List API Test Script...")

    # --- Retrieve API credentials ---
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

    # --- Fetch ShipStation Orders Data for diagnostic purposes ---
    # Using a specific start date for June 2025.
    specific_start_date = '2025-06-01 00:00:00' 
    current_time_for_end_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    raw_orders_output = fetch_shipstation_orders_raw(
        shipstation_api_key,
        shipstation_api_secret,
        specific_start_date,
        current_time_for_end_date
    )

    if raw_orders_output:
        print(f"\n--- Raw Orders Data Fetch Completed ---")
        print(f"Total orders retrieved: {len(raw_orders_output)}")
        # The primary goal is the DEBUG output during fetch.
    else:
        print("No raw orders retrieved or an error occurred during the fetch operation.")

    print("Script finished.")

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
SHIPSTATION_SHIPMENTS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/shipments"

# --- TEMPORARY: HARDCODE THE JSON KEY PATH TO TEST ACCESS ---
# IMPORTANT: THIS IS A TEMPORARY MEASURE FOR LOCAL DEBUGGING.
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

def fetch_shipstation_shipments_raw(api_key, api_secret, start_date, end_date=None):
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

            # --- DEBUGGING OUTPUT FOR FULL SHIPMENT OBJECT ---
            if page == 1 and shipments:
                print(f"DEBUG: Displaying full JSON for first 5 shipments on page {page}:")
                for i, s in enumerate(shipments[:5]):
                    print(f"  --- Shipment {i+1} (ID: {s.get('shipmentId')}, Order #: {s.get('orderNumber')}) ---")
                    # Check if 'shipmentItems' key is present and print its content
                    if 'shipmentItems' in s:
                        print(f"    shipmentItems: {json.dumps(s['shipmentItems'], indent=2)}")
                    else:
                        print("    shipmentItems: [KEY NOT PRESENT IN RESPONSE - UNEXPECTED WITH includeShipmentItems=true]")
                    print(json.dumps(s, indent=2)) # Print the entire shipment object (including shipmentItems if present)
                    print("-" * 50) # Separator for readability
            # --- END DEBUGGING OUTPUT ---

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


if __name__ == "__main__":
    print("Starting ShipStation Shipments API Test Script...")

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

    # --- Fetch ShipStation Shipments Data for diagnostic purposes ---
    # Using a very old start date to try and capture ANY shipments with items.
    diagnostic_start_date = '2010-01-01 00:00:00' 
    current_time_for_end_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    raw_shipments_output = fetch_shipstation_shipments_raw(
        shipstation_api_key,
        shipstation_api_secret,
        diagnostic_start_date,
        current_time_for_end_date
    )

    if raw_shipments_output:
        print(f"\n--- Raw Shipments Data Fetch Completed ---")
        print(f"Total shipments retrieved: {len(raw_shipments_output)}")
        # You can add further processing or inspection here if needed,
        # but the primary goal is the DEBUG output during fetch.
    else:
        print("No raw shipments retrieved or an error occurred during the fetch operation.")

    print("Script finished.")

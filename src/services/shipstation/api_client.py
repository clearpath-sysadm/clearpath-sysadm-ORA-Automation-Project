import base64
import json
import requests
import datetime
import time
import logging

# Import the API utility for robust requests with retry logic
from utils.api_utils import make_api_request

# Setup logging for this module. This assumes setup_logging from utils.logging_config
# has already been called in the main application entry point.
logger = logging.getLogger(__name__)

def get_shipstation_headers(api_key: str, api_secret: str) -> dict:
    """
    Generates the necessary HTTP headers for ShipStation API authentication.

    Args:
        api_key (str): The ShipStation API Key.
        api_secret (str): The ShipStation API Secret.

    Returns:
        dict: A dictionary containing the 'Content-Type' and 'Authorization' headers.
    """
    auth_string = f"{api_key}:{api_secret}"
    # Encode the authentication string to Base64
    encoded_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth_string}"
    }
    return headers

def send_all_orders_to_shipstation(orders_payload: list[dict], api_key: str, api_secret: str, create_orders_endpoint: str) -> list[dict]:
    """
    Sends a list of orders to ShipStation's createorders endpoint using make_api_request.

    Args:
        orders_payload (list[dict]): A list of dictionaries, where each dictionary represents an order
                                     formatted for the ShipStation createorders API.
        api_key (str): The ShipStation API Key.
        api_secret (str): The ShipStation API Secret.
        create_orders_endpoint (str): The full URL for the ShipStation createorders API endpoint.

    Returns:
        list[dict]: A list of dictionaries containing the results of the upload, typically
                    including 'orderKey', 'success', and 'errorMessage' for each order.
                    Returns an empty list if an error occurs.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    
    # Log a truncated version of the payload for debugging, if needed.
    # json.dumps is used to format the payload for logging readability.
    try:
        json_body = json.dumps(orders_payload, indent=2) 
        logger.debug(f"Sending payload to ShipStation API. First 500 chars: {json_body[:500]}...")
    except TypeError: # Handle cases where payload might not be JSON serializable
        logger.debug(f"Could not dump payload to JSON for debugging log (not JSON serializable).")

    try:
        # Use our robust make_api_request utility with retry logic.
        # The 'data' parameter is passed as a dict, and make_api_request handles converting it to JSON.
        response = make_api_request(
            url=create_orders_endpoint,
            method='POST',
            data=orders_payload, # make_api_request will handle json=data conversion
            headers=headers,
            timeout=120 # Set a generous timeout for potentially large uploads
        )
        
        # make_api_request already calls raise_for_status() for HTTP errors and logs them.
        response_data = response.json()
        logger.info("All orders sent successfully to ShipStation.")
        logger.debug(f"ShipStation API response (first 500 chars): {json.dumps(response_data, indent=2)[:500]}...")
        
        # The ShipStation API typically returns results in a 'results' array.
        return response_data.get('results', []) 

    except requests.exceptions.RequestException as req_err:
        # make_api_request handles logging most HTTP and connection errors.
        # This catch is for any specific additional handling needed by this function.
        logger.error(f"Failed to send orders to ShipStation after retries: {req_err}", exc_info=True)
        return []
    except json.JSONDecodeError:
        # Handle cases where the response from ShipStation is not valid JSON.
        logger.error(
            f"Error decoding JSON response from ShipStation. "
            f"Response: {response.text if 'response' in locals() else 'N/A'}", 
            exc_info=True
        )
        return []
    except Exception as e:
        # Catch any other unexpected errors during the process.
        logger.critical(f"An unexpected error occurred sending orders to ShipStation: {e}", exc_info=True)
        return []

def fetch_shipstation_shipments(api_key: str, api_secret: str, shipments_endpoint: str, start_date: str, end_date: str = None) -> list[dict]:
    """
    Fetches shipments data from ShipStation API, handling pagination.
    Uses make_api_request for API calls and our logging system.

    Args:
        api_key (str): The ShipStation API Key.
        api_secret (str): The ShipStation API Secret.
        shipments_endpoint (str): The full URL for the ShipStation shipments API endpoint.
        start_date (str): The start date for filtering shipments (e.g., 'YYYY-MM-DD HH:MM:SS').
                          Corresponds to ShipStation's 'shipDateStart' parameter.
        end_date (str, optional): The end date for filtering shipments (e.g., 'YYYY-MM-DD HH:MM:SS').
                                  Corresponds to ShipStation's 'shipDateEnd' parameter.
                                  If None, defaults to the current UTC time.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a shipment
                    fetched from ShipStation. Returns an empty list if an error occurs.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_shipments = []
    page = 1
    page_size = 500 # Max allowed by ShipStation API, optimizes for fewer calls

    logger.debug(f"Starting raw shipment fetch from {start_date} with includeShipmentItems=true...")

    while True:
        params = {
            'shipDateStart': start_date,
            'pageSize': page_size,
            'page': page,
            'includeShipmentItems': 'true' # Important to get item-level details
        }
        if end_date:
            params['shipDateEnd'] = end_date
        else:
            # If no end_date provided, fetch up to the current UTC time.
            params['shipDateEnd'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + 'Z'

        try:
            # Use make_api_request with retry logic for robustness.
            response = make_api_request(
                url=shipments_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=60 # Timeout for each API call
            )
            
            data = response.json()
            shipments = data.get('shipments', [])

            if not shipments:
                logger.debug(f"No shipments found on page {page}. Ending fetch.")
                break # No more shipments to fetch on this page or subsequent pages

            all_shipments.extend(shipments)
            logger.info(f"Fetched page {page}: {len(shipments)} shipments.")

            if len(shipments) < page_size:
                logger.debug(f"Fewer than {page_size} shipments on page {page}. Assuming last page.")
                break # Reached the last page of results
            
            page += 1
            time.sleep(0.5) # Be respectful to the API, introduce a small delay between paginated calls

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Failed to fetch ShipStation shipments after retries (Page {page}): {req_err}", exc_info=True)
            return []
        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON response from ShipStation. Response (Page {page}): "
                f"{response.text if 'response' in locals() else 'N/A'}", 
                exc_info=True
            )
            return []
        except Exception as e:
            logger.critical(f"An unexpected error occurred fetching ShipStation shipments (Page {page}): {e}", exc_info=True)
            return []

    logger.info(f"Finished fetching ShipStation shipments. Total retrieved: {len(all_shipments)}")
    return all_shipments

# --- NEW FUNCTION FOR DUPLICATE CHECKING ---
def fetch_shipstation_existing_orders_by_date_range(api_key: str, api_secret: str, orders_endpoint: str, create_date_start: str, create_date_end: str = None) -> list[dict]:
    """
    Fetches existing ShipStation orders within a specified creation date range, handling pagination.
    This is used to pre-check for duplicates before uploading new orders.

    Args:
        api_key (str): The ShipStation API Key.
        api_secret (str): The ShipStation API Secret.
        orders_endpoint (str): The full URL for the ShipStation orders API endpoint (e.g., 'https://ssapi.shipstation.com/orders').
        create_date_start (str): The start date for filtering orders by creation date (ISO 8601 format).
        create_date_end (str, optional): The end date for filtering orders by creation date (ISO 8601 format).
                                         If None, defaults to the current UTC timestamp.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents an order
                    fetched from ShipStation. Returns an empty list if an error occurs.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    page = 1
    page_size = 500  # Max allowed by ShipStation API

    logger.debug(f"Starting ShipStation existing orders fetch from {create_date_start} to {create_date_end or 'current UTC'}...")

    while True:
        params = {
            'createDateStart': create_date_start,
            'pageSize': page_size,
            'page': page
        }
        if create_date_end:
            params['createDateEnd'] = create_date_end
        else:
            params['createDateEnd'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + 'Z'

        try:
            response = make_api_request(
                url=orders_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=60
            )
            
            data = response.json()
            orders = data.get('orders', []) # ShipStation returns orders in an 'orders' array

            if not orders:
                logger.debug(f"No orders found on page {page}. Ending fetch.")
                break

            all_orders.extend(orders)
            logger.info(f"Fetched page {page}: {len(orders)} existing orders.")

            if len(orders) < page_size:
                logger.debug(f"Fewer than {page_size} orders on page {page}. Assuming last page.")
                break
            
            page += 1
            time.sleep(0.5) # Be respectful to the API

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Failed to fetch existing ShipStation orders after retries (Page {page}): {req_err}", exc_info=True)
            return []
        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON response from ShipStation. Response (Page {page}): "
                f"{response.text if 'response' in locals() else 'N/A'}", 
                exc_info=True
            )
            return []
        except Exception as e:
            logger.critical(f"An unexpected error occurred fetching existing ShipStation orders (Page {page}): {e}", exc_info=True)
            return []

    logger.info(f"Finished fetching existing ShipStation orders. Total retrieved: {len(all_orders)}")
    return all_orders


# This block is for independent testing of the module.
if __name__ == "__main__":
    # Simulate logging setup for independent module testing
    # In a real application, ensure your main script calls setup_logging once.
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # --- DUMMY CREDENTIALS AND ENDPOINTS FOR TESTING ONLY ---
    # Replace with actual values for real testing, or rely on environment variables/config
    DUMMY_API_KEY = "YOUR_DUMMY_SHIPSTATION_API_KEY"
    DUMMY_API_SECRET = "YOUR_DUMMY_SHIPSTATION_API_SECRET"
    DUMMY_SHIPMENTS_ENDPOINT = "https://ssapi.shipstation.com/shipments" # Use real endpoint for testing
    DUMMY_CREATE_ORDERS_ENDPOINT = "https://ssapi.shipstation.com/orders/createorders" # Use real endpoint
    DUMMY_ORDERS_ENDPOINT = "https://ssapi.shipstation.com/orders" # New: for fetching existing orders

    logger.info("Starting independent test of ShipStation API Client module...")

    # Test get_shipstation_headers
    headers = get_shipstation_headers(DUMMY_API_KEY, DUMMY_API_SECRET)
    logger.info(f"Generated headers (truncated Authorization): {headers.get('Authorization', '')[:30]}...")

    # Test fetch_shipstation_shipments (requires a valid API key/secret and actual data)
    # Using a past date range for demonstration. Adjust as needed.
    test_start_date_shipments = "2024-01-01 00:00:00"
    test_end_date_shipments = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    logger.info(f"Attempting to fetch shipments from {test_start_date_shipments} to {test_end_date_shipments}...")
    # NOTE: This call will likely fail without a valid, real ShipStation API key and secret.
    # This is for demonstration of the function call structure.
    # shipments = fetch_shipstation_shipments(DUMMY_API_KEY, DUMMY_API_SECRET, DUMMY_SHIPMENTS_ENDPOINT, test_start_date_shipments, test_end_date_shipments)
    # if shipments:
    #     logger.info(f"Fetched {len(shipments)} shipments. First shipment: {json.dumps(shipments[0], indent=2)[:200]}...")
    # else:
    #     logger.warning("No shipments fetched or an error occurred during fetch.")

    # --- NEW TEST FOR fetch_shipstation_existing_orders_by_date_range ---
    test_create_date_start = "2024-06-01T00:00:00Z" # Example: Start of last month
    test_create_date_end = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + 'Z'

    logger.info(f"Attempting to fetch existing orders from {test_create_date_start} to {test_create_date_end}...")
    # NOTE: This call will also likely fail without a valid, real ShipStation API key and secret.
    # existing_orders = fetch_shipstation_existing_orders_by_date_range(DUMMY_API_KEY, DUMMY_API_SECRET, DUMMY_ORDERS_ENDPOINT, test_create_date_start, test_create_date_end)
    # if existing_orders:
    #     logger.info(f"Fetched {len(existing_orders)} existing orders. First order: {json.dumps(existing_orders[0], indent=2)[:200]}...")
    # else:
    #     logger.warning("No existing orders fetched or an error occurred during fetch.")


    # Test send_all_orders_to_shipstation (requires a valid API key/secret and endpoint)
    # This is a minimal dummy payload for demonstration.
    dummy_orders_payload = [
        {
            "orderNumber": "TEST-ORDER-001",
            "orderKey": "TEST-ORDER-001",
            "orderDate": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds') + 'Z',
            "customerEmail": "test@example.com",
            "billTo": {"name": "Test Customer", "street1": "123 Test St", "city": "Testville", "state": "TX", "postalCode": "77001", "country": "US"},
            "shipTo": {"name": "Test Customer", "street1": "123 Test St", "city": "Testville", "state": "TX", "postalCode": "77001", "country": "US"},
            "items": [
                {"sku": "SKU-001", "name": "Test Product 1", "quantity": 1, "weight": {"value": 10, "units": "ounces"}}
            ]
        }
    ]
    logger.info("Attempting to send a dummy order...")
    # NOTE: This call will likely fail without a valid, real ShipStation API key and secret.
    # upload_results = send_all_orders_to_shipstation(dummy_orders_payload, DUMMY_API_KEY, DUMMY_API_SECRET, DUMMY_CREATE_ORDERS_ENDPOINT)
    # if upload_results:
    #     logger.info(f"Upload results: {json.dumps(upload_results, indent=2)}")
    # else:
    #     logger.warning("No upload results or an error occurred during sending.")

    logger.info("Independent test of ShipStation API Client module finished.")



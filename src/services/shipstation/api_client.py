# filename: src/services/shipstation/api_client.py
"""
This module provides functions for interacting with the ShipStation API.
It handles authentication, API requests, and basic data fetching with
built-in retry logic.
"""
import base64
import requests
import logging
import time
import json
import os
import sys
from datetime import datetime, timezone

# Add the project root to the Python path to enable imports from a parent directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# FIX: Import the settings object directly from the config package.
from config import settings
from utils.api_utils import make_api_request
from src.services.secrets import get_secret


# --- Environment Detection ---
ENV = getattr(settings, 'get_environment', lambda: 'unknown')()
IS_LOCAL_ENV = ENV == 'local'
IS_CLOUD_ENV = ENV == 'cloud'

# --- Logging Setup ---
logger = logging.getLogger('shipstation_api_client')
logger.setLevel(logging.DEBUG)
if IS_LOCAL_ENV:
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'shipstation_api_client.log')
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
else:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False
logger.info(f"ShipStation API Client started. Environment: {ENV.upper()}")

def get_shipstation_headers(api_key: str, api_secret: str) -> dict:
    """
    Generates the Authorization header for ShipStation API requests.
    """
    combined_credentials = f"{api_key}:{api_secret}"
    encoded_credentials = base64.b64encode(combined_credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded_credentials}"}

def get_shipstation_credentials():
    """
    Retrieves ShipStation API credentials from Replit environment variables or GCP Secret Manager.
    Prioritizes Replit environment variables for Replit deployment.
    """
    try:
        # First check Replit environment variables (most common in Replit)
        api_key = os.getenv('SHIPSTATION_API_KEY')
        api_secret = os.getenv('SHIPSTATION_API_SECRET')
        
        if api_key and api_secret:
            logger.info("Using ShipStation credentials from Replit environment variables")
            return api_key, api_secret
        
        # Fallback to GCP Secret Manager (for Google Cloud deployments)
        logger.info("Attempting to retrieve ShipStation API Key from GCP Secret Manager...")
        api_key = get_secret(settings.SHIPSTATION_API_KEY_SECRET_ID)
        logger.info("Attempting to retrieve ShipStation API Secret from GCP Secret Manager...")
        api_secret = get_secret(settings.SHIPSTATION_API_SECRET_SECRET_ID)
        
        if not api_key or not api_secret:
            logger.error("Failed to retrieve ShipStation API credentials from all sources.")
            return None, None
        return api_key, api_secret
    except Exception as e:
        logger.error(f"Error retrieving ShipStation credentials: {e}", exc_info=True)
        return None, None

def fetch_shipstation_shipments(
    api_key: str,
    api_secret: str,
    shipments_endpoint: str,
    start_date: str,
    end_date: str,
    shipment_status: str = "shipped",
    page: int = 1,
    page_size: int = 500
) -> list:
    """
    Fetches shipment data from ShipStation within a specified date range.
    Includes shipment items.

    Args:
        api_key (str): The ShipStation API key.
        api_secret (str): The ShipStation API secret.
        shipments_endpoint (str): The ShipStation shipments API endpoint URL.
        start_date (str): The start date for the query in 'YYYY-MM-DD' format.
        end_date (str): The end date for the query in 'YYYY-MM-DD' format.
        shipment_status (str): The status of the shipments to retrieve (e.g., "shipped").
        page (int): The starting page number.
        page_size (int): The number of shipments per page (max 500).

    Returns:
        list: A list of shipment dictionaries from the API response.
    """
    logger.info(f"Starting raw shipment fetch from {start_date} with includeShipmentItems=true and status='{shipment_status}'...")
    all_shipments = []
    headers = get_shipstation_headers(api_key, api_secret)
    
    params = {
        'shipDateStart': start_date,
        'shipDateEnd': end_date,
        'includeShipmentItems': 'true',
        'page': page,
        'pageSize': page_size,
        'shipmentStatus': shipment_status
    }

    while True:
        try:
            response = make_api_request(
                url=shipments_endpoint,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )

            if response and response.status_code == 200:
                data = response.json()
                shipments_on_page = data.get('shipments', [])
                all_shipments.extend(shipments_on_page)
                
                total_pages = data.get('pages', 1)
                current_page = data.get('page', 1)

                logger.info(f"Fetched page {current_page} of {total_pages}. Total shipments so far: {len(all_shipments)}")

                if current_page >= total_pages:
                    break
                else:
                    params['page'] += 1
            else:
                logger.error(f"Failed to fetch shipments. Status: {response.status_code if response else 'N/A'}, Response: {response.text if response else 'N/A'}")
                break
        except Exception as e:
            logger.error(f"An error occurred while fetching shipments: {e}")
            break
            
    logger.info(f"Finished fetching ShipStation shipments. Total retrieved: {len(all_shipments)}")
    return all_shipments

def send_all_orders_to_shipstation(orders_payload: list, api_key: str, api_secret: str, create_orders_endpoint: str) -> list:
    """
    Sends a list of orders to ShipStation's createorders endpoint.

    DISABLED: BigCommerce now pushes orders directly to ShipStation.
    Remove the RuntimeError below to re-enable.
    """
    raise RuntimeError(
        "send_all_orders_to_shipstation is disabled. "
        "BigCommerce pushes orders directly to ShipStation. "
        "Remove this guard in src/services/shipstation/api_client.py to re-enable."
    )
    headers = get_shipstation_headers(api_key, api_secret)
    headers["Content-Type"] = "application/json"
    
    try:
        logger.debug(f"Sending {len(orders_payload)} orders to ShipStation...")
        
        response = make_api_request(
            url=create_orders_endpoint,
            method='POST',
            data=orders_payload,
            headers=headers,
            timeout=120
        )
        
        if response and response.status_code == 200:
            response_data = response.json()
            logger.info(f"Successfully sent orders to ShipStation")
            return response_data.get('results', [])
        else:
            logger.error(f"Failed to send orders. Status: {response.status_code if response else 'N/A'}")
            return []
            
    except Exception as e:
        logger.error(f"Error sending orders to ShipStation: {e}", exc_info=True)
        return []

def fetch_shipstation_orders_by_order_numbers(
    api_key: str,
    api_secret: str,
    orders_endpoint: str,
    order_numbers: list
) -> list:
    """
    Fetches existing orders from ShipStation by specific order numbers.
    Uses direct per-order lookups (?orderNumber=X) instead of a bulk date-range
    scan. This is O(n) in the number of orders we care about, not O(total orders
    in ShipStation), so it stays fast regardless of how many orders ShipStation
    holds (e.g. after a BigCommerce store migration).

    Args:
        api_key: ShipStation API Key
        api_secret: ShipStation API Secret
        orders_endpoint: ShipStation orders API endpoint URL
        order_numbers: List of order numbers to query

    Returns:
        list: List of existing orders from ShipStation matching the order numbers
    """
    if not order_numbers:
        return []

    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []

    logger.info(f"Fetching orders from ShipStation (per-order lookup for {len(order_numbers)} order numbers)")

    for order_number in order_numbers:
        try:
            response = make_api_request(
                url=orders_endpoint,
                method='GET',
                headers=headers,
                params={'orderNumber': str(order_number), 'pageSize': 500},
                timeout=30
            )

            if response and response.status_code == 200:
                data = response.json()
                orders_on_page = data.get('orders', [])
                all_orders.extend(orders_on_page)
                logger.debug(f"Order {order_number}: found {len(orders_on_page)} match(es) in ShipStation")
            else:
                logger.error(f"Failed to fetch order {order_number}. Status: {response.status_code if response else 'N/A'}")

        except Exception as e:
            logger.error(f"Error fetching order {order_number} from ShipStation: {e}", exc_info=True)

        time.sleep(0.5)

    logger.info(f"Retrieved {len(all_orders)} existing orders (per-order lookup)")
    return all_orders

def fetch_order_by_id(order_id: int, api_key: str = None, api_secret: str = None) -> dict:
    """
    Fetch a single order from ShipStation by order ID.
    
    Args:
        order_id: The ShipStation order ID to fetch
        api_key: Optional ShipStation API key (will retrieve if not provided)
        api_secret: Optional ShipStation API secret (will retrieve if not provided)
        
    Returns:
        dict: {'success': bool, 'order': dict, 'error': str (optional)}
    """
    try:
        if not api_key or not api_secret:
            api_key, api_secret = get_shipstation_credentials()
            if not api_key or not api_secret:
                return {'success': False, 'error': 'ShipStation credentials not found'}
        
        headers = get_shipstation_headers(api_key, api_secret)
        url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
        
        logger.info(f"Fetching order from ShipStation: Order ID {order_id}")
        
        response = make_api_request(
            url=url,
            method='GET',
            headers=headers,
            timeout=30
        )
        
        if response and response.status_code == 200:
            order = response.json()
            logger.info(f"✅ Successfully fetched order {order_id}: Order #{order.get('orderNumber')}, Status: {order.get('orderStatus')}")
            return {'success': True, 'order': order}
        else:
            error_msg = f"Failed to fetch order {order_id}: HTTP {response.status_code if response else 'No response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        logger.error(f"Error fetching order {order_id} from ShipStation: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

def update_order_custom_fields(
    order_id: int,
    field1_value: str,
    field2_value: str = None,
    *,
    field3_value: str = None,
    skip_cf1: bool = False,
    carrier_code: str = None,
    service_code: str = None,
    package_code: str = None,
    weight_oz: float = None,
    dim_length: float = None,
    dim_width: float = None,
    dim_height: float = None,
    bill_to_party: str = None,
    bill_to_account: int = None,
) -> dict:
    """
    Update customField1 (and optionally customField2/3) in ShipStation advancedOptions,
    and optionally set the full shipping profile in the same POST.

    field1_value should be the full 'SKU - LOT' string (e.g. '17612 - 250237').
    field2_value is only set when preserving a pre-existing customField1 value.
    field3_value when set writes customField3 (e.g. promo-hold audit stamps).

    Shipping profile kwargs (all optional):
        carrier_code    — e.g. 'fedex'
        service_code    — e.g. 'fedex_ground', 'fedex_2day'
        package_code    — e.g. 'package'  (goes in advancedOptions)
        weight_oz       — per-unit weight in ounces (top-level weight field)
        dim_length/width/height — dimensions in inches (top-level dimensions field)
        bill_to_party   — e.g. 'my_other_account' (goes in advancedOptions)
        bill_to_account — ShipStation shippingProviderId as int (goes in advancedOptions)

    When weight_oz or any dim_* is None, that top-level field is left untouched.
    When package_code is None, advancedOptions.packageCode is left untouched.

    Returns dict with 'success' bool and 'error' on failure.
    """
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        fetch_result = fetch_order_by_id(order_id, api_key, api_secret)
        if not fetch_result.get('success'):
            return {'success': False, 'error': fetch_result.get('error', 'Failed to fetch order')}

        order_data = fetch_result['order']
        if order_data.get('advancedOptions') is None:
            order_data['advancedOptions'] = {}

        if not skip_cf1:
            order_data['advancedOptions']['customField1'] = field1_value
        if field2_value is not None:
            order_data['advancedOptions']['customField2'] = field2_value
        if field3_value is not None:
            order_data['advancedOptions']['customField3'] = field3_value

        if carrier_code is not None:
            order_data['carrierCode'] = carrier_code
        if service_code is not None:
            order_data['serviceCode'] = service_code

        if package_code is not None:
            order_data['packageCode'] = package_code
        if bill_to_party is not None:
            order_data['advancedOptions']['billToParty'] = bill_to_party
        if bill_to_account is not None:
            order_data['advancedOptions']['billToMyOtherAccount'] = bill_to_account

        if weight_oz is not None:
            order_data['weight'] = {'value': weight_oz, 'units': 'ounces'}

        if dim_length is not None and dim_width is not None and dim_height is not None:
            order_data['dimensions'] = {
                'units': 'inches',
                'length': dim_length,
                'width': dim_width,
                'height': dim_height,
            }

        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'

        response = make_api_request(
            url='https://ssapi.shipstation.com/orders/createorder',
            method='POST',
            headers=headers,
            data=order_data,
            timeout=30
        )

        if response and response.status_code == 200:
            if skip_cf1:
                logger.info(f"Updated shipping profile for order {order_id} (CF1 intentionally skipped — Lot Override)")
            else:
                logger.info(f"Updated customField1 for order {order_id}: '{field1_value}'")
            return {'success': True}
        else:
            error_msg = f"ShipStation API error {response.status_code if response else 'no response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error updating custom fields for order {order_id}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


_PROMO_HOLD_TAG_ID_CACHE: dict = {}
_PROMO_HOLD_TAG_NAME = 'Promo Hold'
_PROMO_HOLD_TAG_COLOR = '#E80505'


def _get_promo_hold_tag_id() -> int | None:
    """
    Lazily resolve the ShipStation tag ID for 'Promo Hold', creating it if
    it does not exist.  Result is cached in the module-level dict so subsequent
    calls in the same process are free.

    Returns the tag ID (int) or None on any API failure.
    """
    if 'id' in _PROMO_HOLD_TAG_ID_CACHE:
        return _PROMO_HOLD_TAG_ID_CACHE['id']

    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            logger.error('_get_promo_hold_tag_id: ShipStation credentials not found')
            return None

        headers = get_shipstation_headers(api_key, api_secret)

        resp = make_api_request(
            url='https://ssapi.shipstation.com/accounts/listtags',
            method='GET',
            headers=headers,
            timeout=30,
        )
        if not resp or resp.status_code != 200:
            logger.error(
                f'_get_promo_hold_tag_id: GET /accounts/listtags failed '
                f'{resp.status_code if resp else "no response"}'
            )
            return None

        for tag in resp.json():
            if tag.get('name') == _PROMO_HOLD_TAG_NAME:
                tag_id = tag['tagId']
                _PROMO_HOLD_TAG_ID_CACHE['id'] = tag_id
                logger.info(f'_get_promo_hold_tag_id: found existing tag id={tag_id}')
                return tag_id

        create_headers = {**headers, 'Content-Type': 'application/json'}
        create_resp = make_api_request(
            url='https://ssapi.shipstation.com/accounts/addtag',
            method='POST',
            headers=create_headers,
            data={'name': _PROMO_HOLD_TAG_NAME, 'color': _PROMO_HOLD_TAG_COLOR},
            timeout=30,
        )
        if not create_resp or create_resp.status_code not in (200, 201):
            logger.error(
                f'_get_promo_hold_tag_id: POST /accounts/addtag failed '
                f'{create_resp.status_code if create_resp else "no response"}'
            )
            return None

        tag_id = create_resp.json().get('tagId')
        if tag_id:
            _PROMO_HOLD_TAG_ID_CACHE['id'] = tag_id
            logger.info(f'_get_promo_hold_tag_id: created new tag id={tag_id}')
        return tag_id

    except Exception as exc:
        logger.error(f'_get_promo_hold_tag_id: unexpected error: {exc}', exc_info=True)
        return None


def apply_promo_hold_tag(order_id: int) -> dict:
    """
    Apply the 'Promo Hold' ShipStation tag to an order.

    Uses POST /orders/addtag. Non-fatal on failure — logs a warning but does
    not raise so the caller can still proceed with other failure-path actions.

    Returns dict with 'success' bool and 'error' on failure.
    """
    tag_id = _get_promo_hold_tag_id()
    if tag_id is None:
        msg = 'apply_promo_hold_tag: could not resolve PROMO HOLD tag ID'
        logger.warning(msg)
        return {'success': False, 'error': msg}

    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'

        resp = make_api_request(
            url='https://ssapi.shipstation.com/orders/addtag',
            method='POST',
            headers=headers,
            data={'orderId': order_id, 'tagId': tag_id},
            timeout=30,
        )
        if resp and resp.status_code in (200, 204):
            logger.info(f'apply_promo_hold_tag: tagged order {order_id}')
            return {'success': True}

        status = resp.status_code if resp else 'no response'
        body = resp.text[:200] if resp else ''
        error_msg = f'POST /orders/addtag failed {status}: {body}'
        logger.warning(f'apply_promo_hold_tag: {error_msg}')
        return {'success': False, 'error': error_msg}

    except Exception as exc:
        logger.error(f'apply_promo_hold_tag: error for order {order_id}: {exc}', exc_info=True)
        return {'success': False, 'error': str(exc)}


def remove_promo_hold_tag(order_id: int) -> dict:
    """
    Remove the 'Promo Hold' ShipStation tag from an order.

    Uses POST /orders/removetag. Non-fatal — a missing tag (204 / 200) is
    treated as success since the desired end state (tag absent) is reached.

    Returns dict with 'success' bool and 'error' on failure.
    """
    tag_id = _get_promo_hold_tag_id()
    if tag_id is None:
        msg = 'remove_promo_hold_tag: could not resolve PROMO HOLD tag ID'
        logger.warning(msg)
        return {'success': False, 'error': msg}

    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'

        resp = make_api_request(
            url='https://ssapi.shipstation.com/orders/removetag',
            method='POST',
            headers=headers,
            data={'orderId': order_id, 'tagId': tag_id},
            timeout=30,
        )
        if resp and resp.status_code in (200, 204):
            logger.info(f'remove_promo_hold_tag: tag removed from order {order_id}')
            return {'success': True}

        status = resp.status_code if resp else 'no response'
        body = resp.text[:200] if resp else ''
        error_msg = f'POST /orders/removetag failed {status}: {body}'
        logger.warning(f'remove_promo_hold_tag: {error_msg}')
        return {'success': False, 'error': error_msg}

    except Exception as exc:
        logger.error(f'remove_promo_hold_tag: error for order {order_id}: {exc}', exc_info=True)
        return {'success': False, 'error': str(exc)}


def update_order_package_v2(
    order_id: int,
    package_id: str,
    weight_oz: float,
    length: float,
    width: float,
    height: float,
    num_packages: int = 1,
) -> dict:
    """
    Set the package configuration on a ShipStation V2 shipment.

    Constructs shipment_id as 'se-{order_id}' — no extra lookup required.

    Auth: PRODUCTION_KEY env var as 'API-Key' header (V2-specific credential).

    V2 PUT is a full replacement, not a partial update. Required flow:
      1. GET the current shipment to retrieve ship_from, ship_to, carrier_id, etc.
      2. Build packages array based on num_packages:
         - num_packages == 1: [{package_id, weight}]
           Dimensions must NOT be sent; custom package preset defines its own dims
           and the V2 API rejects dimensions when package_id is specified.
         - num_packages > 1: [{package_code:'package', weight, dimensions}] × N
           ShipStation silently discards custom package_id for multi-package entries,
           so we use the generic package code with explicit dimensions to preserve
           the correct box size for each package.
      3. PUT back the full modified shipment.

    V2 weight unit is 'ounce' (not 'ounces' as used by V1).

    Returns dict with 'success' bool and 'error' on failure.
    """
    num_packages = max(1, int(num_packages or 1))

    try:
        api_key = os.getenv('PRODUCTION_KEY')
        if not api_key:
            return {'success': False, 'error': 'PRODUCTION_KEY environment variable not set'}

        shipment_id = f"se-{order_id}"
        url = f"https://api.shipstation.com/v2/shipments/{shipment_id}"

        headers = {
            'API-Key': api_key,
            'Content-Type': 'application/json',
        }

        # Step 1: GET current shipment data (required for PUT — it's a full replacement)
        get_response = make_api_request(
            url=url,
            method='GET',
            headers=headers,
            timeout=30,
        )
        if not get_response or get_response.status_code != 200:
            status = get_response.status_code if get_response else 'no response'
            body = get_response.text[:200] if get_response else ''
            return {'success': False, 'error': f"V2 GET failed {status}: {body}"}

        shipment = get_response.json()

        # Step 2: Build packages array
        if num_packages == 1:
            # Single package: use named custom preset — dimensions omitted because
            # the preset already defines them and the API rejects sending both.
            shipment['packages'] = [
                {
                    'package_id': package_id,
                    'weight': {'value': weight_oz, 'unit': 'ounce'},
                }
            ]
        else:
            # Multi-package: ShipStation silently discards custom package_id when
            # it appears more than once in the array, converting to the generic
            # carrier package type. Use package_code='package' + explicit dimensions
            # to preserve the correct box size per package.
            single_pkg = {
                'package_code': 'package',
                'weight': {'value': weight_oz, 'unit': 'ounce'},
                'dimensions': {
                    'unit': 'inch',
                    'length': length,
                    'width': width,
                    'height': height,
                },
            }
            shipment['packages'] = [single_pkg] * num_packages

        # ShipStation V2 rejects PUTs where ship_date is in the past.  Always
        # reset to today so old orders (created before today) don't receive 400.
        shipment['ship_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00Z')

        # Step 3: PUT back the full modified shipment
        put_response = make_api_request(
            url=url,
            method='PUT',
            headers=headers,
            data=shipment,
            timeout=30,
        )

        if put_response and put_response.status_code in (200, 204):
            logger.info(
                f"V2: set {num_packages}×package_id={package_id} on shipment {shipment_id}"
            )
            return {'success': True}
        else:
            status = put_response.status_code if put_response else 'no response'
            body = put_response.text[:300] if put_response else ''
            error_msg = f"ShipStation V2 PUT error {status}: {body}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error setting V2 package for order {order_id}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def list_carriers() -> dict:
    """
    Fetch the list of connected carriers from ShipStation.
    GET /carriers

    Returns dict with 'success' bool, 'carriers' list, and 'error' on failure.
    """
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        headers = get_shipstation_headers(api_key, api_secret)
        response = make_api_request(
            url='https://ssapi.shipstation.com/carriers',
            method='GET',
            headers=headers,
            timeout=30
        )

        if response and response.status_code == 200:
            carriers = response.json()
            return {'success': True, 'carriers': carriers}
        else:
            error_msg = f"ShipStation API error {response.status_code if response else 'no response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error fetching carriers: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def list_packages(carrier_code: str) -> dict:
    """
    Fetch the list of packages available for a given carrier.
    GET /carriers/listpackages?carrierCode=<carrier_code>

    Returns dict with 'success' bool, 'packages' list, and 'error' on failure.
    """
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        headers = get_shipstation_headers(api_key, api_secret)
        response = make_api_request(
            url='https://ssapi.shipstation.com/carriers/listpackages',
            method='GET',
            headers=headers,
            params={'carrierCode': carrier_code},
            timeout=30
        )

        if response and response.status_code == 200:
            packages = response.json()
            return {'success': True, 'packages': packages}
        else:
            error_msg = f"ShipStation API error {response.status_code if response else 'no response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error fetching packages for carrier {carrier_code!r}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def register_order_notify_webhook(target_url: str) -> dict:
    """
    Register an ORDER_NOTIFY webhook with ShipStation pointing at target_url.

    target_url must include the SHIPSTATION_WEBHOOK_TOKEN in the path.
    ShipStation does not return a signing secret — security is the token in the URL.

    Returns dict with 'success' bool, 'already_exists' bool, and 'error' on failure.
    """
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        headers = get_shipstation_headers(api_key, api_secret)

        # Check for existing ORDER_NOTIFY webhook at this URL
        list_response = make_api_request(
            url='https://ssapi.shipstation.com/webhooks',
            method='GET',
            headers=headers,
            timeout=30
        )

        if list_response and list_response.status_code == 200:
            existing = list_response.json()
            for webhook in existing.get('webhooks', []):
                if webhook.get('HookType') != 'ORDER_NOTIFY':
                    continue
                webhook_url = webhook.get('Url', '')
                webhook_id = webhook.get('WebHookID')
                if webhook_url == target_url:
                    logger.info(f"ORDER_NOTIFY webhook already registered: {target_url}")
                    return {'success': True, 'already_exists': True}
                # Stale webhook pointing to a different (dead) URL — delete it
                if webhook_id:
                    del_headers = {**headers, 'Content-Type': 'application/json'}
                    del_response = make_api_request(
                        url=f'https://ssapi.shipstation.com/webhooks/{webhook_id}',
                        method='DELETE',
                        headers=del_headers,
                        timeout=30
                    )
                    if del_response and del_response.status_code in (200, 204):
                        logger.info(f"Deleted stale ORDER_NOTIFY webhook {webhook_id} → {webhook_url}")
                    else:
                        status = del_response.status_code if del_response else 'no response'
                        logger.warning(f"Failed to delete stale webhook {webhook_id}: HTTP {status}")

        # Register new webhook
        payload = {
            'event': 'ORDER_NOTIFY',
            'target_url': target_url,
            'store_id': None,
            'friendly_name': 'lot-tagger'
        }
        headers['Content-Type'] = 'application/json'
        reg_response = make_api_request(
            url='https://ssapi.shipstation.com/webhooks/subscribe',
            method='POST',
            headers=headers,
            data=payload,
            timeout=30
        )

        if reg_response and reg_response.status_code in (200, 201):
            logger.info(f"Registered ORDER_NOTIFY webhook: {target_url}")
            return {'success': True, 'already_exists': False}
        else:
            error_msg = f"Webhook registration failed: HTTP {reg_response.status_code if reg_response else 'no response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error registering ShipStation webhook: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def delete_order_from_shipstation(order_id: int, fetch_details_first: bool = True) -> dict:
    """
    DEPRECATED — do not call this function.

    All order removals must go through cancel_order_in_shipstation() so that
    orders remain visible in ShipStation with a CF3 audit stamp.

    The two X-Cart-era endpoints in app.py (~6748 bulk_dedup, ~6874
    confirm_delete) bypass this function via raw make_api_request DELETE calls
    and are NOT protected by this guard.
    """
    import traceback
    logger.error(
        "delete_order_from_shipstation called — this function is DEPRECATED. "
        "Use cancel_order_in_shipstation() instead. "
        f"Caller: {''.join(traceback.format_stack(limit=4))}"
    )
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}
        
        # Fetch order details before deletion for audit trail
        order_details = None
        customer_data = {}
        order_number = None
        
        if fetch_details_first:
            fetch_result = fetch_order_by_id(order_id, api_key, api_secret)
            if fetch_result.get('success') and fetch_result.get('order'):
                order_details = fetch_result['order']
                order_number = order_details.get('orderNumber')
                
                # Extract customer data for audit
                bill_to = order_details.get('billTo') or {}
                ship_to = order_details.get('shipTo') or {}
                items = order_details.get('items', [])
                
                customer_data = {
                    'customer_name': bill_to.get('name') or ship_to.get('name'),
                    'customer_email': order_details.get('customerEmail'),
                    'customer_company': bill_to.get('company') or ship_to.get('company'),
                    'ship_to_name': ship_to.get('name'),
                    'ship_to_city': ship_to.get('city'),
                    'ship_to_state': ship_to.get('state'),
                    'order_total_cents': int(float(order_details.get('orderTotal', 0)) * 100) if order_details.get('orderTotal') else None,
                    'order_date': order_details.get('orderDate', '')[:10] if order_details.get('orderDate') else None,
                    'items_json': [{'sku': item.get('sku'), 'quantity': item.get('quantity'), 'name': item.get('name')} for item in items]
                }
                
                logger.info(f"📋 Captured order details before deletion: Order #{order_number}, Customer: {customer_data.get('customer_name')}")
        
        headers = get_shipstation_headers(api_key, api_secret)
        url = f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}"
        
        logger.info(f"Deleting order from ShipStation: Order ID {order_id}")
        
        response = make_api_request(
            url=url,
            method='DELETE',
            headers=headers,
            timeout=30
        )
        
        if response and response.status_code == 200:
            logger.info(f"✅ Successfully deleted order {order_id} from ShipStation")
            return {
                'success': True, 
                'message': f'Order {order_id} deleted successfully',
                'order_number': order_number,
                'customer_data': customer_data
            }
        else:
            error_msg = f"Failed to delete order {order_id}: HTTP {response.status_code if response else 'No response'}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'order_number': order_number, 'customer_data': customer_data}
            
    except Exception as e:
        logger.error(f"Error deleting order {order_id} from ShipStation: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def cancel_order_in_shipstation(
    order_id: int,
    order_data: dict = None,
    custom_field3: str = None,
) -> dict:
    """
    Cancel a ShipStation order by setting its orderStatus to 'cancelled'.

    ShipStation's createorder endpoint requires the full order payload on update
    (a minimal {orderId, orderStatus} body returns 400). Either the full order
    dict can be passed in directly (preferred, avoids an extra API call) or it
    will be fetched automatically.

    Args:
        order_id:      ShipStation order ID to cancel
        order_data:    Full ShipStation order dict (optional — fetched if omitted)
        custom_field3: Optional string written to advancedOptions.customField3 in
                       the same POST so cancellation + audit stamp are one API call.
                       E.g. 'orphan:verify-failed 2026-04-15'

    Returns:
        {
            'success': bool,
            'order_number': str | None,   # populated when order_data was fetched internally
            'customer_data': dict | None, # populated when order_data was fetched internally
            'error': str                  # present on failure only
        }
    """
    _READONLY_KEYS = frozenset({
        'createDate', 'modifyDate', 'userId',
        'externallyFulfilled', 'externallyFulfilledBy',
        'externallyFulfilledById', 'externallyFulfilledByName',
        'labelMessages',
    })

    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found',
                    'order_number': None, 'customer_data': None}

        order_number = None
        customer_data = None

        if order_data is None:
            fetch_result = fetch_order_by_id(order_id, api_key, api_secret)
            if not fetch_result.get('success') or not fetch_result.get('order'):
                return {'success': False,
                        'error': f"Could not fetch order {order_id} for cancellation: "
                                 f"{fetch_result.get('error', 'unknown')}",
                        'order_number': None, 'customer_data': None}
            order_data = fetch_result['order']
            order_number = order_data.get('orderNumber')
            bill_to = order_data.get('billTo') or {}
            ship_to = order_data.get('shipTo') or {}
            items   = order_data.get('items', [])
            customer_data = {
                'customer_name':    bill_to.get('name') or ship_to.get('name'),
                'customer_email':   order_data.get('customerEmail'),
                'customer_company': bill_to.get('company') or ship_to.get('company'),
                'ship_to_name':     ship_to.get('name'),
                'ship_to_city':     ship_to.get('city'),
                'ship_to_state':    ship_to.get('state'),
                'order_total_cents': (
                    int(float(order_data.get('orderTotal', 0)) * 100)
                    if order_data.get('orderTotal') else None
                ),
                'order_date': (
                    order_data.get('orderDate', '')[:10]
                    if order_data.get('orderDate') else None
                ),
                'items_json': [
                    {'sku': i.get('sku'), 'quantity': i.get('quantity'), 'name': i.get('name')}
                    for i in items
                ],
            }

        import copy
        payload = copy.deepcopy(order_data)
        payload['orderStatus'] = 'cancelled'
        for key in _READONLY_KEYS:
            payload.pop(key, None)

        for item in payload.get('items', []):
            for k in ('createDate', 'modifyDate'):
                item.pop(k, None)

        if custom_field3 is not None:
            payload.setdefault('advancedOptions', {})['customField3'] = custom_field3

        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'

        logger.info(f"Cancelling order in ShipStation: Order ID {order_id}"
                    + (f" (CF3: {custom_field3!r})" if custom_field3 else ""))

        response = make_api_request(
            url='https://ssapi.shipstation.com/orders/createorder',
            method='POST',
            headers=headers,
            data=payload,
            timeout=30,
        )

        if response and response.status_code == 200:
            logger.info(f"✅ Successfully cancelled order {order_id} in ShipStation")
            return {'success': True, 'order_number': order_number, 'customer_data': customer_data}
        else:
            error_msg = (
                f"Failed to cancel order {order_id}: HTTP "
                f"{response.status_code if response else 'no response'} — "
                f"{response.text[:200] if response else ''}"
            )
            logger.error(error_msg)
            return {'success': False, 'error': error_msg,
                    'order_number': order_number, 'customer_data': customer_data}

    except Exception as e:
        logger.error(f"Error cancelling order {order_id} in ShipStation: {e}", exc_info=True)
        return {'success': False, 'error': str(e), 'order_number': None, 'customer_data': None}


def create_replacement_order(original_order: dict, promo_sku: str, base_sku: str) -> dict:
    """
    Create a new ShipStation order that is identical to original_order except
    the specific promo SKU line item(s) are replaced with the base SKU.
    All other line items are left unchanged.

    Key payload mutations (required so ShipStation creates a NEW order):
      - orderId  removed — omitting forces creation instead of update
      - orderKey removed — omitting prevents ShipStation matching on the
                           BigCommerce idempotency key and updating the original

    The user-facing orderNumber is preserved unchanged.

    Args:
        original_order: Full ShipStation order dict
        promo_sku:      The promotional SKU to replace
        base_sku:       The base fulfillment SKU to use instead

    Returns:
        {'success': bool, 'order': dict, 'error': str (optional)}
    """
    try:
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return {'success': False, 'error': 'ShipStation credentials not found'}

        import copy
        payload = copy.deepcopy(original_order)

        payload.pop('orderId', None)
        payload.pop('orderKey', None)

        _STRIP_ITEM_KEYS = frozenset({'orderItemId', 'createDate', 'modifyDate'})
        new_items = []
        for item in payload.get('items', []):
            new_item = dict(item)
            for k in _STRIP_ITEM_KEYS:
                new_item.pop(k, None)
            if str(new_item.get('sku') or '').strip() == promo_sku:
                new_item['sku'] = base_sku
                if str(new_item.get('fulfillmentSku') or '').strip() == promo_sku:
                    new_item['fulfillmentSku'] = base_sku
            new_items.append(new_item)
        payload['items'] = new_items

        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'

        response = make_api_request(
            url='https://ssapi.shipstation.com/orders/createorder',
            method='POST',
            headers=headers,
            data=payload,
            timeout=30,
        )

        if response and response.status_code == 200:
            new_order = response.json()
            logger.info(
                f"Created replacement order #{new_order.get('orderNumber')} "
                f"(SS ID: {new_order.get('orderId')}) with base SKU {base_sku}"
            )
            return {'success': True, 'order': new_order}
        else:
            error_msg = (
                f"ShipStation createorder failed: HTTP "
                f"{response.status_code if response else 'no response'} — "
                f"{response.text[:200] if response else ''}"
            )
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error creating replacement order: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def v2_get_pending_axiom_shipments() -> dict:
    """
    Fetch all pending shipments for the Axiom warehouse from ShipStation V2.

    Paginates automatically if the result set exceeds 500 entries.
    Auth: PRODUCTION_KEY as 'API-Key' header (V2-specific credential).

    Returns dict with 'success' bool, 'shipment_ids' list, and 'error' on failure.
    """
    from config.settings import settings
    try:
        api_key = os.getenv('PRODUCTION_KEY')
        if not api_key:
            return {'success': False, 'error': 'PRODUCTION_KEY environment variable not set'}

        headers = {
            'API-Key': api_key,
            'Content-Type': 'application/json',
        }

        shipment_ids = []
        skipped = 0
        page = 1

        while True:
            response = make_api_request(
                url='https://api.shipstation.com/v2/shipments',
                method='GET',
                headers=headers,
                params={
                    'shipment_status': 'pending',
                    'page_size': 500,
                    'page': page,
                },
                timeout=30,
            )

            if not response or response.status_code != 200:
                status = response.status_code if response else 'no response'
                body = response.text[:200] if response else ''
                return {'success': False, 'error': f"V2 GET /shipments failed {status}: {body}"}

            data = response.json()
            batch = data.get('shipments', [])
            page_axiom = 0
            for shipment in batch:
                sid = shipment.get('shipment_id')
                wh = shipment.get('warehouse_id')
                if not sid:
                    continue
                # Client-side filter: only include shipments from the Axiom warehouse.
                # The warehouse_id query param is not reliably honored by the V2 API.
                if wh != settings.AXIOM_WAREHOUSE_ID:
                    skipped += 1
                    logger.debug(f"Skipping shipment {sid} — warehouse {wh} is not Axiom")
                    continue
                shipment_ids.append(sid)
                page_axiom += 1

            total_pages = data.get('pages', 1)
            logger.info(
                f"V2 shipments page {page}/{total_pages}: "
                f"{page_axiom} Axiom, {len(batch) - page_axiom} non-Axiom (skipped)"
            )

            if page >= total_pages:
                break
            page += 1

        logger.info(
            f"V2 pending Axiom shipments: {len(shipment_ids)} included, "
            f"{skipped} non-Axiom skipped"
        )
        return {'success': True, 'shipment_ids': shipment_ids}

    except Exception as e:
        logger.error(f"Error fetching V2 pending Axiom shipments: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def v2_create_batch(shipment_ids: list) -> dict:
    """
    Create a ShipStation V2 batch from a list of shipment IDs.

    POST /v2/batches
    Auth: PRODUCTION_KEY as 'API-Key' header.

    Returns dict with 'success' bool, 'batch_id' str, and 'error' on failure.
    """
    from config.settings import settings
    try:
        api_key = os.getenv('PRODUCTION_KEY')
        if not api_key:
            return {'success': False, 'error': 'PRODUCTION_KEY environment variable not set'}

        headers = {
            'API-Key': api_key,
            'Content-Type': 'application/json',
        }

        payload = {
            'shipment_ids': shipment_ids,
            'warehouse_id': settings.AXIOM_WAREHOUSE_ID,
        }

        response = make_api_request(
            url='https://api.shipstation.com/v2/batches',
            method='POST',
            headers=headers,
            data=payload,
            timeout=30,
        )

        if response and response.status_code in (200, 201):
            data = response.json()
            batch_id = data.get('batch_id') or data.get('id')
            logger.info(f"V2 batch created: {batch_id} ({len(shipment_ids)} shipments)")
            return {'success': True, 'batch_id': batch_id, 'response': data}
        else:
            status = response.status_code if response else 'no response'
            body = response.text[:300] if response else ''
            error_msg = f"V2 POST /batches failed {status}: {body}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error creating V2 batch: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def v2_process_batch_labels(batch_id: str, ship_date: str) -> dict:
    """
    Trigger label processing for a ShipStation V2 batch.

    POST /v2/batches/{batch_id}/process/labels
    Auth: PRODUCTION_KEY as 'API-Key' header.

    Args:
        batch_id: The batch ID returned by v2_create_batch.
        ship_date: ISO date string (YYYY-MM-DD) — typically today.

    Returns dict with 'success' bool and 'error' on failure.
    """
    try:
        api_key = os.getenv('PRODUCTION_KEY')
        if not api_key:
            return {'success': False, 'error': 'PRODUCTION_KEY environment variable not set'}

        headers = {
            'API-Key': api_key,
            'Content-Type': 'application/json',
        }

        payload = {'ship_date': ship_date}

        response = make_api_request(
            url=f'https://api.shipstation.com/v2/batches/{batch_id}/process/labels',
            method='POST',
            headers=headers,
            data=payload,
            timeout=30,
        )

        if response and response.status_code in (200, 204):
            logger.info(f"V2 batch {batch_id} label processing triggered (ship_date={ship_date})")
            return {'success': True}
        else:
            status = response.status_code if response else 'no response'
            body = response.text[:300] if response else ''
            error_msg = f"V2 POST /batches/{batch_id}/process/labels failed {status}: {body}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"Error processing V2 batch {batch_id} labels: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

# filename: src/services/shipstation/tracking_service.py
"""
This module provides ShipStation tracking status functionality.
Fetches real-time delivery status during business hours (6 AM Pacific to 5 PM Eastern).

Tracking Status Codes:
- UN: Unknown (label created, not scanned yet)
- AC: Accepted (carrier has package)
- IT: In Transit (moving to destination)
- EX: Exception (delivery problem - ALERT)
- DE: Delivered (final state - stop tracking)
"""
import logging
import os
import sys
from datetime import datetime
import pytz
import requests

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.shipstation.api_client import get_shipstation_headers
from utils.api_utils import make_api_request

# --- Logging Setup ---
logger = logging.getLogger('shipstation_tracking')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

# --- Constants ---
SHIPSTATION_SHIPMENTS_ENDPOINT = "https://ssapi.shipstation.com/shipments"

# Status codes
STATUS_UNKNOWN = 'UN'
STATUS_ACCEPTED = 'AC'
STATUS_IN_TRANSIT = 'IT'
STATUS_EXCEPTION = 'EX'
STATUS_DELIVERED = 'DE'

# Final statuses (stop tracking)
FINAL_STATUSES = [STATUS_DELIVERED]

# Active statuses (keep tracking)
ACTIVE_STATUSES = [STATUS_UNKNOWN, STATUS_ACCEPTED, STATUS_IN_TRANSIT, STATUS_EXCEPTION]


def is_business_hours() -> bool:
    """
    Check if current time is during business hours.
    Business hours: 6 AM Pacific to 5 PM Eastern
    - Pacific: 6 AM - 2 PM
    - Central: 8 AM - 4 PM
    - Eastern: 9 AM - 5 PM
    
    Returns:
        bool: True if within business hours, False otherwise
    """
    try:
        # Check against Pacific time (must be after 6 AM)
        pacific = pytz.timezone('America/Los_Angeles')
        now_pacific = datetime.now(pacific)
        pacific_hour = now_pacific.hour
        
        # Check against Eastern time (must be before 5 PM)
        eastern = pytz.timezone('America/New_York')
        now_eastern = datetime.now(eastern)
        eastern_hour = now_eastern.hour
        
        # Must be after 6 AM Pacific AND before 5 PM Eastern
        is_open = pacific_hour >= 6 and eastern_hour < 17
        
        if not is_open:
            logger.debug(f"Outside business hours: Pacific={pacific_hour}:00, Eastern={eastern_hour}:00")
        
        return is_open
        
    except Exception as e:
        logger.error(f"Error checking business hours: {e}")
        return False


def map_carrier_to_code(carrier_name: str) -> str:
    """
    Map ShipStation carrier name to carrier code for tracking API.
    
    Args:
        carrier_name: Carrier name from ShipStation (e.g., "FedEx")
    
    Returns:
        str: Carrier code (e.g., "fedex")
    """
    carrier_mapping = {
        'fedex': 'fedex',
        'ups': 'ups',
        'usps': 'usps',
        'dhl': 'dhl_express',
        'ontrac': 'ontrac',
        'lasership': 'lasership',
    }
    
    carrier_lower = carrier_name.lower() if carrier_name else ''
    
    # Try exact match
    for key, code in carrier_mapping.items():
        if key in carrier_lower:
            return code
    
    # Default to fedex (most common)
    return 'fedex'


def fetch_tracking_status(tracking_number: str, carrier_code: str, api_key: str, api_secret: str) -> dict:
    """
    Fetch tracking status from ShipStation /shipments API.
    
    Uses ShipStation's native shipments endpoint with Basic-auth credentials.
    Queries by tracking number and extracts trackingStatus field.
    
    Args:
        tracking_number: Tracking number to look up
        carrier_code: Carrier code (not used with ShipStation API, kept for compatibility)
        api_key: ShipStation API key
        api_secret: ShipStation API secret
    
    Returns:
        dict: {
            'status_code': 'IT',  # Our standardized code (UN, AC, IT, EX, DE)
            'status_description': 'In Transit',
            'exception_description': None or str,
            'success': True or False,
            'error': None or str
        }
    """
    try:
        # Build ShipStation shipments URL with tracking number filter
        # Format: https://ssapi.shipstation.com/shipments?trackingNumber=xxx
        headers = get_shipstation_headers(api_key, api_secret)
        
        params = {
            'trackingNumber': tracking_number,
            'page': 1,
            'pageSize': 1  # Only need first result
        }
        
        logger.debug(f"Fetching tracking status for {tracking_number} from ShipStation")
        
        response = make_api_request(
            url=SHIPSTATION_SHIPMENTS_ENDPOINT,
            method='GET',
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response and response.status_code == 200:
            data = response.json()
            shipments = data.get('shipments', [])
            
            if not shipments:
                # No shipments found - tracking not yet in system
                logger.warning(f"⚠️ Tracking {tracking_number}: Not found in ShipStation (not scanned yet)")
                return {
                    'status_code': STATUS_UNKNOWN,
                    'status_description': 'Not Scanned',
                    'exception_description': None,
                    'success': True,
                    'error': None
                }
            
            # Get first shipment (should be only one matching tracking number)
            shipment = shipments[0]
            shipstation_status = shipment.get('trackingStatus', '').lower()
            
            # Map ShipStation status to our standardized codes
            status_code, status_description = map_shipstation_status_to_code(shipstation_status)
            
            # Check for exception description (if status indicates problem)
            exception_description = None
            if status_code == STATUS_EXCEPTION:
                # ShipStation may provide additional details in void status or notes
                exception_description = shipment.get('voidStatus') or 'Delivery exception'
            
            logger.info(f"✅ Tracking {tracking_number}: {status_code} ({status_description}) [ShipStation: {shipstation_status}]")
            
            return {
                'status_code': status_code,
                'status_description': status_description,
                'exception_description': exception_description,
                'success': True,
                'error': None
            }
            
        elif response and response.status_code == 429:
            # Rate limit exceeded
            logger.error(f"🚨 Rate limit exceeded for ShipStation API")
            return {
                'status_code': None,
                'status_description': None,
                'exception_description': None,
                'success': False,
                'error': 'Rate limit exceeded'
            }
        else:
            error_msg = f"Failed to fetch tracking: Status {response.status_code if response else 'None'}"
            logger.error(f"❌ {error_msg}")
            return {
                'status_code': None,
                'status_description': None,
                'exception_description': None,
                'success': False,
                'error': error_msg
            }
            
    except Exception as e:
        logger.error(f"❌ Error fetching tracking status for {tracking_number}: {e}", exc_info=True)
        return {
            'status_code': None,
            'status_description': None,
            'exception_description': None,
            'success': False,
            'error': str(e)
        }


def map_shipstation_status_to_code(shipstation_status: str) -> tuple:
    """
    Map ShipStation tracking status to our standardized status codes.
    
    ShipStation statuses include: pending, shipped, delivered, cancelled, voided, etc.
    Our codes: UN (Unknown), AC (Accepted), IT (In Transit), EX (Exception), DE (Delivered)
    
    Args:
        shipstation_status: Status string from ShipStation (e.g., 'delivered', 'shipped')
    
    Returns:
        tuple: (status_code, status_description)
    """
    status = shipstation_status.lower().strip()
    
    # Mapping based on ShipStation documentation
    status_map = {
        'delivered': (STATUS_DELIVERED, 'Delivered'),
        'shipped': (STATUS_IN_TRANSIT, 'In Transit'),
        'pending': (STATUS_ACCEPTED, 'Accepted'),
        'cancelled': (STATUS_EXCEPTION, 'Cancelled'),
        'voided': (STATUS_EXCEPTION, 'Voided'),
        'returned': (STATUS_EXCEPTION, 'Returned'),
        'exception': (STATUS_EXCEPTION, 'Exception'),
        '': (STATUS_UNKNOWN, 'Unknown'),
    }
    
    # Try exact match first
    if status in status_map:
        return status_map[status]
    
    # Try partial matches
    if 'deliver' in status:
        return (STATUS_DELIVERED, 'Delivered')
    elif 'ship' in status or 'transit' in status:
        return (STATUS_IN_TRANSIT, 'In Transit')
    elif 'pend' in status or 'accept' in status:
        return (STATUS_ACCEPTED, 'Accepted')
    elif 'cancel' in status or 'void' in status or 'return' in status or 'exception' in status:
        return (STATUS_EXCEPTION, 'Exception')
    
    # Default to unknown
    logger.warning(f"Unknown ShipStation status '{shipstation_status}' - defaulting to UN")
    return (STATUS_UNKNOWN, 'Unknown')


def should_track_order(order: dict) -> bool:
    """
    Determine if an order should be tracked.
    
    Rules:
    - Must have tracking number
    - Status must not be 'delivered' (DE)
    - Must be during business hours (6 AM Pacific to 5 PM Eastern)
    - Must not have been checked in last 5 minutes
    
    Args:
        order: Order dictionary with tracking_number, tracking_status, tracking_last_checked
    
    Returns:
        bool: True if order should be tracked, False otherwise
    """
    # Must have tracking number
    tracking_number = order.get('tracking_number')
    if not tracking_number or tracking_number.strip() == '':
        return False
    
    # Don't track delivered orders
    tracking_status = order.get('tracking_status')
    if tracking_status in FINAL_STATUSES:
        return False
    
    # Only track during business hours
    if not is_business_hours():
        return False
    
    # Check if we've checked recently (within 5 minutes)
    tracking_last_checked = order.get('tracking_last_checked')
    if tracking_last_checked:
        try:
            # Handle both datetime objects and strings
            if isinstance(tracking_last_checked, str):
                from dateutil import parser
                tracking_last_checked = parser.parse(tracking_last_checked)
            
            # Add timezone if naive
            if tracking_last_checked.tzinfo is None:
                tracking_last_checked = pytz.UTC.localize(tracking_last_checked)
            
            time_since_check = datetime.now(pytz.UTC) - tracking_last_checked
            if time_since_check.total_seconds() < 300:  # 5 minutes
                return False
        except Exception as e:
            logger.warning(f"Error parsing tracking_last_checked: {e}")
            # If we can't parse, go ahead and check (fail safe)
    
    return True


def update_order_tracking_status(order_number: str, tracking_data: dict, conn):
    """
    Update order tracking status in database.
    
    SAFETY: Only updates orders that have a ShipStation ID synced.
    Orders without ShipStation IDs (NULL) are blocked from updates to prevent data integrity issues.
    
    Args:
        order_number: Order number to update
        tracking_data: Dictionary with status_code, status_description, exception_description
        conn: Database connection
    """
    try:
        cursor = conn.cursor()
        
        status_code = tracking_data.get('status_code')
        status_description = tracking_data.get('status_description')
        exception_description = tracking_data.get('exception_description')
        
        # SAFETY CHECK: Only update if shipstation_order_id IS NOT NULL
        # This prevents updates on orders that haven't been synced to ShipStation yet
        cursor.execute("""
            UPDATE orders_inbox
            SET tracking_status = %s,
                tracking_status_description = %s,
                exception_description = %s,
                tracking_last_checked = NOW(),
                tracking_last_updated = CASE 
                    WHEN tracking_status IS DISTINCT FROM %s THEN NOW()
                    ELSE tracking_last_updated
                END
            WHERE order_number = %s
              AND shipstation_order_id IS NOT NULL
        """, (status_code, status_description, exception_description, status_code, order_number))
        
        if cursor.rowcount == 0:
            logger.warning(f"⚠️ Skipped tracking update for order {order_number} - ShipStation ID not synced yet (NULL)")
        
        conn.commit()
        cursor.close()
        
        logger.debug(f"Updated tracking status for order {order_number}")
        
    except Exception as e:
        logger.error(f"Error updating tracking status for {order_number}: {e}", exc_info=True)
        conn.rollback()
        raise


def get_tracking_status_icon(status_code: str) -> str:
    """
    Get emoji icon for tracking status code.
    
    Args:
        status_code: Status code (UN, AC, IT, EX, DE)
    
    Returns:
        str: Emoji icon
    """
    icons = {
        STATUS_DELIVERED: '✅',  # Delivered
        STATUS_IN_TRANSIT: '🚚',  # In Transit
        STATUS_EXCEPTION: '⚠️',  # Exception
        STATUS_ACCEPTED: '📋',  # Accepted
        STATUS_UNKNOWN: '❓'   # Unknown
    }
    return icons.get(status_code, '📦')

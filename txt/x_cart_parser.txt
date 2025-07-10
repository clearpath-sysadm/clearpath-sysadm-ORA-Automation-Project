import xml.etree.ElementTree as ET
import datetime
import pandas as pd
import logging
import os

# Import the actual Google Sheets API client function
from src.services.google_sheets.api_client import get_google_sheet_data
# Import the central settings
from config.settings import settings

logger = logging.getLogger(__name__)

def _get_active_sku_lot_map():
    """
    Fetches the SKU to Lot mapping from Google Sheets and returns a dictionary
    containing ONLY the active mappings.
    """
    try:
        logger.debug("Fetching and filtering SKU-Lot map from Google Sheets...")
        
        sku_lot_df = get_google_sheet_data(
            sheet_id=settings.GOOGLE_SHEET_ID, 
            worksheet_name=settings.SKU_LOT_TAB_NAME
        )
        
        if sku_lot_df is None or sku_lot_df.empty:
            logger.warning("SKU_Lot sheet is empty or could not be read. No lot codes will be applied.")
            return {}

        required_cols = ['SKU', 'Lot', 'Active']
        if not all(col in sku_lot_df.columns for col in required_cols):
            logger.error(f"SKU_Lot sheet is missing one of the required columns: {required_cols}")
            return {}

        # Ensure the SKU column from Google Sheets is a clean string
        sku_lot_df['SKU'] = sku_lot_df['SKU'].astype(str).str.strip()

        active_sku_lot_df = sku_lot_df[sku_lot_df['Active'].astype(str).str.upper() == 'TRUE'].copy()
        active_lot_map = pd.Series(active_sku_lot_df.Lot.values, index=active_sku_lot_df.SKU).to_dict()
        
        logger.info(f"Successfully created active SKU-Lot map with {len(active_lot_map)} entries.")
        return active_lot_map
    except Exception as e:
        logger.error(f"Failed to get or process SKU_Lot map from Google Sheets: {e}", exc_info=True)
        return {}

def parse_date(date_string: str) -> str | None:
    """Parses multiple date formats from an XML string into an ISO 8601 formatted string."""
    if date_string is None: return None
    formats_to_try = [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y %I:%M:%S %p'
    ]
    for fmt in formats_to_try:
        try:
            dt_obj = datetime.datetime.strptime(date_string, fmt)
            return dt_obj.astimezone(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        except (ValueError, Exception):
            continue
    logger.warning(f"Unable to parse date: '{date_string}' with known formats. Returning None.")
    return None

def build_address_from_xml(order_element: ET.Element, address_prefix: str) -> dict:
    """Builds an address dictionary from an XML element using the given prefix."""
    firstname = order_element.findtext(f'{address_prefix}firstname') or ""
    lastname = order_element.findtext(f'{address_prefix}lastname') or ""
    address = {
        "name": (firstname + " " + lastname).strip(),
        "company": order_element.findtext(f'{address_prefix}company') or "",
        "street1": order_element.findtext(f'{address_prefix}address') or "",
        "city": order_element.findtext(f'{address_prefix}city') or "",
        "state": order_element.findtext(f'{address_prefix}state') or "",
        "postalCode": order_element.findtext(f'{address_prefix}zipcode') or "",
        "country": order_element.findtext(f'{address_prefix}country') or "",
        "phone": order_element.findtext(f'{address_prefix}phone') or ""
    }
    if address["street1"]:
        address["street1"] = address["street1"].encode('ascii', 'ignore').decode('ascii').strip()
    return address

def parse_x_cart_xml_for_shipstation_payload(xml_file_path: str, bundle_config: dict) -> list[dict]:
    """Parses an X-Cart XML file, applies SKU-Lot and bundling logic, and prepares payloads for ShipStation."""
    orders_payload = []
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        active_lot_map = _get_active_sku_lot_map()

        for order_element in root.findall('order'):
            order_data = {
                'orderKey': order_element.findtext('orderid'),
                'orderNumber': order_element.findtext('orderid'),
                'orderDate': parse_date(order_element.findtext('date2')),
                'orderStatus': 'awaiting_shipment',
                'customerEmail': order_element.findtext('email'),
                'requestedShippingService': order_element.findtext('shipping'),
                'billTo': build_address_from_xml(order_element, "b_"),
                'shipTo': build_address_from_xml(order_element, "s_"),
                'items': []
            }

            items_list = []
            for order_detail_element in order_element.findall('order_detail'):
                original_sku_raw = order_detail_element.findtext('productid')
                if not original_sku_raw: continue
                cleaned_sku = str(original_sku_raw).strip()

                original_quantity = int(order_detail_element.findtext('amount') or '0')
                if original_quantity == 0: continue
                
                sku_after_lot_logic = f"{cleaned_sku} - {active_lot_map[cleaned_sku]}" if cleaned_sku in active_lot_map else cleaned_sku

                if sku_after_lot_logic in bundle_config:
                    for component in bundle_config[sku_after_lot_logic]:
                        # --- THIS IS THE DEFINITIVE FIX ---
                        # Perform the SKU-Lot lookup on the COMPONENT SKU as well.
                        component_sku = str(component['component_id']).strip()
                        final_component_sku = f"{component_sku} - {active_lot_map[component_sku]}" if component_sku in active_lot_map else component_sku
                        
                        items_list.append({
                            "sku": final_component_sku,
                            "name": f"Component of {sku_after_lot_logic}",
                            "quantity": original_quantity * component['multiplier'],
                        })
                else:
                    items_list.append({
                        "sku": sku_after_lot_logic,
                        "name": order_detail_element.findtext('product'),
                        "quantity": original_quantity,
                    })
            
            order_data['items'] = items_list
            orders_payload.append(order_data)

    except Exception as e:
        logger.critical(f"An unexpected error occurred during XML processing: {e}", exc_info=True)
        return []
        
    return orders_payload

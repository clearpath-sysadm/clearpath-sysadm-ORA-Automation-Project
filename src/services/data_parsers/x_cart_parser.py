import xml.etree.ElementTree as ET
import datetime
import pandas as pd
import logging
from typing import Union

# Import the actual Google Sheets API client function (now self-authenticating)
from src.services.google_sheets.api_client import get_google_sheet_data
# Import the central settings
from config.settings import settings

logger = logging.getLogger(__name__)

def _get_active_sku_lot_map():
    """
    Fetches the SKU to Lot mapping from Google Sheets and returns a dictionary
    containing ONLY the active mappings.
    This function now relies on src.services.google_sheets.api_client.get_google_sheet_data
    to handle its own authentication, so no key is passed here.
    """
    try:
        logger.debug({"message": "Fetching and filtering SKU-Lot map from Google Sheets..."})
        
        # get_google_sheet_data returns a list of lists (raw values)
        raw_sku_lot_data = get_google_sheet_data(
            sheet_id=settings.GOOGLE_SHEET_ID, 
            worksheet_name=settings.SKU_LOT_TAB_NAME
        )
        
        if not raw_sku_lot_data or len(raw_sku_lot_data) < 1:
            logger.warning({"message": "SKU_Lot sheet is empty or could not be read. No lot codes will be applied."})
            return {}

        # Convert raw list of lists to Pandas DataFrame
        # Assume the first row contains headers
        headers = raw_sku_lot_data[0]
        data_rows = raw_sku_lot_data[1:]
        
        sku_lot_df = pd.DataFrame(data_rows, columns=headers)

        # Now, sku_lot_df is a DataFrame, so .empty and .columns will work
        if sku_lot_df.empty: # Re-check after DataFrame conversion, though unlikely if raw_data was not empty
            logger.warning({"message": "SKU_Lot DataFrame is empty after conversion. No lot codes will be applied."})
            return {}


        required_cols = ['SKU', 'Lot', 'Active']
        if not all(col in sku_lot_df.columns for col in required_cols):
            logger.error({"message": "SKU_Lot sheet is missing required columns", "required_columns": required_cols, "available_columns": sku_lot_df.columns.tolist()})
            return {}

        # Ensure the SKU column from Google Sheets is a clean string
        sku_lot_df['SKU'] = sku_lot_df['SKU'].astype(str).str.strip()

        active_sku_lot_df = sku_lot_df[sku_lot_df['Active'].astype(str).str.upper() == 'TRUE'].copy()
        active_lot_map = pd.Series(active_sku_lot_df.Lot.values, index=active_sku_lot_df.SKU).to_dict()
        
        logger.info({"message": "Successfully created active SKU-Lot map", "entry_count": len(active_lot_map)})
        return active_lot_map
    except Exception as e:
        logger.error({"message": "Failed to get or process SKU_Lot map from Google Sheets", "error": str(e)}, exc_info=True)
        return {}

def parse_date(date_string: str) -> str | None:
    """
    Parses multiple date formats from an XML string into an ISO 8601 formatted UTC string.
    """
    if date_string is None:
        logger.debug({"message": "Input date_string is None, returning None for date parsing."})
        return None

    formats_to_try = [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y %I:%M:%S %p'
    ]
    
    for fmt in formats_to_try:
        try:
            dt_obj = datetime.datetime.strptime(date_string, fmt)
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
            else:
                dt_obj = dt_obj.astimezone(datetime.timezone.utc)

            return dt_obj.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        except (ValueError, Exception):
            continue
    
    logger.warning({"message": "Unable to parse date with known formats", "date_string": date_string})
    return None

def build_address_from_xml(order_element: ET.Element, address_prefix: str) -> dict:
    """
    Builds an address dictionary from an XML element using the given prefix.
    """
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
    
    logger.debug({"message": "Address built from XML", "prefix": address_prefix, "name": address["name"], "city": address["city"]})
    return address

def parse_x_cart_xml_for_shipstation_payload(xml_content_string: str, bundle_config: dict) -> list[dict]:
    """
    Parses an X-Cart XML content string, applies SKU-Lot and bundling logic,
    and prepares payloads for ShipStation.
    """
    orders_payload = []
    try:
        root = ET.fromstring(xml_content_string)
        logger.info({"message": "XML content parsed successfully from string.", "root_tag": root.tag})

        active_lot_map = _get_active_sku_lot_map()

        for order_element in root.findall('order'):
            order_id = order_element.findtext('orderid')
            if not order_id:
                logger.warning({"message": "Skipping order due to missing orderid", "xml_snippet": ET.tostring(order_element, encoding='unicode')[:200]})
                continue

            order_data = {
                'orderKey': order_id,
                'orderNumber': order_id,
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
                if not original_sku_raw:
                    logger.warning({"message": "Skipping item due to missing productid", "order_id": order_id, "item_xml_snippet": ET.tostring(order_detail_element, encoding='unicode')[:100]})
                    continue
                
                cleaned_sku = str(original_sku_raw).strip()

                original_quantity_str = order_detail_element.findtext('amount')
                try:
                    original_quantity = int(original_quantity_str or '0')
                except ValueError:
                    logger.error({"message": "Invalid quantity for item, defaulting to 0", "order_id": order_id, "sku": cleaned_sku, "quantity_raw": original_quantity_str})
                    original_quantity = 0
                
                if original_quantity <= 0:
                    logger.warning({"message": "Skipping item due to zero or negative quantity", "order_id": order_id, "sku": cleaned_sku, "quantity": original_quantity})
                    continue
                
                sku_after_lot_logic = f"{cleaned_sku} - {active_lot_map[cleaned_sku]}" if cleaned_sku in active_lot_map else cleaned_sku

                if sku_after_lot_logic in settings.BUNDLE_CONFIG:
                    logger.debug({"message": "Applying bundle logic", "order_id": order_id, "bundle_sku": sku_after_lot_logic})
                    bundle_definition = settings.BUNDLE_CONFIG[sku_after_lot_logic]
                    
                    if isinstance(bundle_definition, dict):
                        bundle_definition = [bundle_definition]

                    for component in bundle_definition:
                        component_sku_raw = component.get('component_id')
                        if not component_sku_raw:
                            logger.warning({"message": "Bundle component missing component_id", "order_id": order_id, "bundle_sku": sku_after_lot_logic, "component_info": component})
                            continue

                        component_sku = str(component_sku_raw).strip()
                        
                        # CORRECTED: Ensure final_component_sku is correctly determined if no lot is found
                        final_component_sku = f"{component_sku} - {active_lot_map[component_sku]}" if component_sku in active_lot_map else component_sku
                        
                        items_list.append({
                            "sku": final_component_sku,
                            "name": f"Component of {sku_after_lot_logic}",
                            "quantity": original_quantity * component.get('multiplier', 1),
                        })
                else:
                    items_list.append({
                        "sku": sku_after_lot_logic,
                        "name": order_detail_element.findtext('product') or "N/A",
                        "quantity": original_quantity,
                    })
            
            order_data['items'] = items_list
            orders_payload.append(order_data)
            logger.debug({"message": "Order processed and added to payload", "order_id": order_id, "item_count": len(items_list)})

    except ET.ParseError as pe:
        logger.critical({"message": "XML parsing error", "error": str(pe), "xml_content_start": xml_content_string[:500]}, exc_info=True)
        return []
    except Exception as e:
        logger.critical({"message": "An unexpected error occurred during XML processing", "error": str(e)}, exc_info=True)
        return []
        
    logger.info({"message": "Finished parsing X-Cart XML", "total_orders_parsed": len(orders_payload)})
    return orders_payload


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
    Fetches the SKU to Lot mapping from Google Sheets, converts it to a DataFrame,
    and returns a dictionary containing ONLY the active mappings.
    """
    try:
        logger.debug("Fetching and filtering SKU-Lot map from Google Sheets...")
        
        # Call get_google_sheet_data which returns list | None
        raw_sku_lot_data = get_google_sheet_data(
            sheet_id=settings.GOOGLE_SHEET_ID, 
            worksheet_name=settings.SKU_LOT_TAB_NAME
        )
        
        # --- NEW LOGIC: Convert to DataFrame here ---
        if not raw_sku_lot_data: # Handles None or empty list
            logger.warning("SKU_Lot sheet is empty or could not be read. No lot codes will be applied.")
            return {}

        # Assume first row is header, rest is data
        header = raw_sku_lot_data[0]
        data = raw_sku_lot_data[1:]
        
        sku_lot_df = pd.DataFrame(data, columns=header)
        # --- END NEW LOGIC ---

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

def _get_key_products_list() -> list[str]:
    """
    Fetches the list of 'Key Products' SKUs from the ORA_CONFIGURATION Google Sheet.
    """
    try:
        logger.debug("Fetching 'Key Products' list from Google Sheets...")
        raw_config_data = get_google_sheet_data(
            sheet_id=settings.GOOGLE_SHEET_ID, 
            worksheet_name=settings.ORA_CONFIGURATION_TAB_NAME
        )

        if not raw_config_data:
            logger.warning("ORA_Configuration sheet is empty or could not be read. No key product filtering will be applied.")
            return []

        header = raw_config_data[0]
        data = raw_config_data[1:]
        config_df = pd.DataFrame(data, columns=header)

        required_cols = ['ParameterCategory', 'SKU']
        if not all(col in config_df.columns for col in required_cols):
            logger.error(f"ORA_Configuration sheet is missing one of the required columns: {required_cols}")
            return []

        key_products_df = config_df[config_df['ParameterCategory'].astype(str).str.strip() == 'Key Products'].copy()
        key_product_skus = key_products_df['SKU'].astype(str).str.strip().tolist()
        
        logger.info(f"Successfully loaded {len(key_product_skus)} key product SKUs.")
        return key_product_skus
    except Exception as e:
        logger.error(f"Failed to get or process Key Products list from Google Sheets: {e}", exc_info=True)
        return []

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

def parse_x_cart_xml_for_shipstation_payload(xml_content: str, bundle_config: dict) -> list[dict]:
    """
    Parses X-Cart XML content (as a string), applies SKU-Lot and bundling logic,
    and prepares payloads for ShipStation.
    Items are skipped if their SKU is not found in the active SKU-Lot map
    or if bundle components are not defined in the active SKU-Lot map.
    Orders are skipped if any of their final SKUs (after bundling/lot) are not
    found in the 'Key Products' list.
    Finally, identical base SKUs are consolidated into single line items.
    """
    orders_payload = []
    try:
        root = ET.fromstring(xml_content) 
        active_lot_map = _get_active_sku_lot_map()
        key_product_skus = _get_key_products_list() # Fetch key products once

        for order_element in root.findall('order'):
            order_id = order_element.findtext('orderid')
            order_contains_non_key_product = False
            
            # Initialize a temporary dictionary to hold consolidated items for the current order
            consolidated_shipstation_items = {} 

            order_data = {
                'orderKey': order_id,
                'orderNumber': order_id,
                'orderDate': parse_date(order_element.findtext('date2')),
                'orderStatus': 'awaiting_shipment',
                'customerEmail': order_element.findtext('email'),
                'requestedShippingService': order_element.findtext('shipping'),
                'billTo': build_address_from_xml(order_element, "b_"),
                'shipTo': build_address_from_xml(order_element, "s_"),
                'items': [] # This will be populated from consolidated_shipstation_items
            }

            for order_detail_element in order_element.findall('order_detail'):
                original_sku_raw = order_detail_element.findtext('productid')
                if not original_sku_raw: 
                    logger.warning(f"Skipping item due to missing productid for order {order_id}")
                    order_contains_non_key_product = True # Mark order to be skipped
                    break # Skip processing further items for this order
                
                cleaned_sku = str(original_sku_raw).strip()
                original_quantity = int(order_detail_element.findtext('amount') or '0')
                if original_quantity == 0: 
                    logger.warning(f"Skipping item {cleaned_sku} for order {order_id} due to zero quantity.")
                    continue

                if cleaned_sku in bundle_config:
                    # It's a bundle, iterate its components
                    for component in bundle_config[cleaned_sku]:
                        component_id = str(component['component_id']).strip()
                        
                        # Validate component SKU against active_lot_map and key_product_skus
                        if component_id not in active_lot_map:
                            logger.warning({
                                "message": "Skipping bundle component as its SKU is not defined in active lot map.",
                                "order_id": order_id,
                                "bundle_sku": cleaned_sku,
                                "component_sku": component_id
                            })
                            order_contains_non_key_product = True # Mark order to be skipped
                            break # No need to process other components if one is bad
                        
                        if component_id not in key_product_skus:
                             logger.info({
                                "message": "Skipping bundle component as it is not a Key Product.",
                                "order_id": order_id,
                                "bundle_sku": cleaned_sku,
                                "component_sku": component_id
                            })
                             order_contains_non_key_product = True # Mark order to be skipped
                             break # No need to process other components if one is not a key product
                        
                        # Apply SKU-Lot logic to the component SKU
                        final_component_sku = f"{component_id} - {active_lot_map[component_id]}"
                        
                        # CONSOLIDATION LOGIC FOR BUNDLE COMPONENTS
                        if final_component_sku in consolidated_shipstation_items:
                            consolidated_shipstation_items[final_component_sku]['quantity'] += (original_quantity * component['multiplier'])
                        else:
                            consolidated_shipstation_items[final_component_sku] = {
                                "sku": final_component_sku,
                                "name": f"Component of {order_detail_element.findtext('product')}", 
                                "quantity": original_quantity * component['multiplier'],
                            }
                    if order_contains_non_key_product:
                        break # Skip remaining items for this order if a bundle component was invalid
                else:
                    # It's a regular product, check if it's in active_lot_map and key_product_skus
                    if cleaned_sku not in active_lot_map:
                        logger.warning({
                            "message": "Skipping regular item as its SKU is not defined in active lot map.",
                            "order_id": order_id,
                            "sku": cleaned_sku,
                            "product_name": order_detail_element.findtext('product')
                        })
                        order_contains_non_key_product = True # Mark order to be skipped
                        continue # Skip this item entirely
                    
                    if cleaned_sku not in key_product_skus:
                        logger.info({
                            "message": "Skipping regular item as it is not a Key Product.",
                            "order_id": order_id,
                            "sku": cleaned_sku,
                            "product_name": order_detail_element.findtext('product')
                        })
                        order_contains_non_key_product = True # Mark order to be skipped
                        continue # Skip this item entirely
                    
                    # Apply lot logic for regular product
                    sku_with_lot = f"{cleaned_sku} - {active_lot_map[cleaned_sku]}"
                    
                    # CONSOLIDATION LOGIC FOR REGULAR ITEMS
                    if sku_with_lot in consolidated_shipstation_items:
                        consolidated_shipstation_items[sku_with_lot]['quantity'] += original_quantity
                    else:
                        consolidated_shipstation_items[sku_with_lot] = {
                            "sku": sku_with_lot,
                            "name": order_detail_element.findtext('product'),
                            "quantity": original_quantity,
                        }
            
            # After processing all order_detail_elements for the current order:
            if order_contains_non_key_product:
                logger.info({
                    "message": "Skipping entire order due to missing active lot number or non-Key Product.",
                    "order_id": order_id
                })
                continue # Skip this entire order

            # Convert the consolidated_shipstation_items dictionary back into a list
            order_data['items'] = list(consolidated_shipstation_items.values())
            
            orders_payload.append(order_data)
            logger.info(f"Successfully processed order {order_id} and added to payload.")

    except Exception as e:
        logger.critical(f"An unexpected error occurred during XML processing: {e}", exc_info=True)
        return []
        
    return orders_payload

import xml.etree.ElementTree as ET
from xml.dom import minidom # For pretty printing XML
import datetime
import os

# --- Comprehensive BUNDLE_CONFIG (copied from x_cart_importer.py for reference) ---
BUNDLE_CONFIG = {
    # Single Component Bundles
    "18075": {"component_id": "17913", "multiplier": 1},
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

def generate_bundle_test_xml(output_file='x_cart_orders_bundle_test.xml'):
    """
    Generates an XML file containing a separate order for each bundle SKU
    defined in BUNDLE_CONFIG, for testing bundling logic.
    """
    root = ET.Element("DentistSelectOrders")
    base_order_id = 100000 # Starting point for test order IDs
    
    for bundle_sku, bundle_info in BUNDLE_CONFIG.items():
        # Create a unique order ID for each bundle test
        current_time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        order_id = f"BUNDLE-TEST-{bundle_sku}-{current_time_str}-{base_order_id}"
        base_order_id += 1 # Increment for next order

        # Get current date/time for order date fields
        current_timestamp = int(datetime.datetime.now().timestamp())
        current_datetime_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        order_elem = ET.SubElement(root, "order")
        
        # Add common order details (from user's example)
        ET.SubElement(order_elem, "orderid").text = order_id
        ET.SubElement(order_elem, "date").text = str(current_timestamp)
        ET.SubElement(order_elem, "date2").text = current_datetime_str
        ET.SubElement(order_elem, "dentistcode").text = "BUNDLE-TEST"
        ET.SubElement(order_elem, "shipping").text = "Standard Flat Rate Ground"
        ET.SubElement(order_elem, "company").text = f"BUNDLE Test Co. {bundle_sku}"
        ET.SubElement(order_elem, "email").text = "bundle.test@example.com"
        ET.SubElement(order_elem, "s_firstname").text = "TEST"
        ET.SubElement(order_elem, "s_lastname").text = "DO NOT SHIP" # Critical safety flag
        ET.SubElement(order_elem, "s_company").text = f"TEST COMPANY {bundle_sku}"
        ET.SubElement(order_elem, "s_address").text = "123 Test Lane"
        ET.SubElement(order_elem, "s_city").text = "Testville"
        ET.SubElement(order_elem, "s_state").text = "MN"
        ET.SubElement(order_elem, "s_zipcode").text = "55125"
        ET.SubElement(order_elem, "s_country").text = "US"
        ET.SubElement(order_elem, "s_phone").text = "(555) 555-5555"
        
        # Billing details (can be same as shipping for simplicity in test)
        ET.SubElement(order_elem, "b_firstname").text = "TEST"
        ET.SubElement(order_elem, "b_lastname").text = "DO NOT SHIP"
        ET.SubElement(order_elem, "b_company").text = f"TEST BILLING {bundle_sku}"
        ET.SubElement(order_elem, "b_address").text = "123 Test Lane"
        ET.SubElement(order_elem, "b_city").text = "Testville"
        ET.SubElement(order_elem, "b_state").text = "MN"
        ET.SubElement(order_elem, "b_zipcode").text = "55125"
        ET.SubElement(order_elem, "b_country").text = "US"
        ET.SubElement(order_elem, "b_phone").text = "(555) 555-5555"
        
        ET.SubElement(order_elem, "shipping_cost").text = "0.00" # Set to 0 for test clarity
        ET.SubElement(order_elem, "customerid").text = f"TEST-CUST-{bundle_sku}"

        # Add the bundle item as a single order_detail
        order_detail_elem = ET.SubElement(order_elem, "order_detail")
        ET.SubElement(order_detail_elem, "orderid").text = order_id # Matching parent orderid
        ET.SubElement(order_detail_elem, "amount").text = "1" # Always 1 unit of the bundle itself
        ET.SubElement(order_detail_elem, "product").text = f"Bundle Test Product: {bundle_sku}"
        ET.SubElement(order_detail_elem, "productid").text = bundle_sku # This is the bundle SKU being tested

    # Pretty print the XML
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

    # Save to file
    script_dir = os.path.dirname(__file__)
    output_full_path = os.path.join(script_dir, output_file)

    with open(output_full_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml_as_string)
    
    print(f"Generated test XML with {len(BUNDLE_CONFIG)} bundle orders to: {output_full_path}")


if __name__ == "__main__":
    # Ensure this script is run from the same directory as x_cart_importer.py
    # This will create 'x_cart_orders_bundle_test.xml' in your src directory
    generate_bundle_test_xml()
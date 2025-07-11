# filename: settings.py
"""
Centralized configuration settings for the ORA Project.
This module consolidates all application-wide settings.
"""
import os

# --- Project Root Path ---
# Defines the base directory of the project for relative pathing if needed.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# --- Google Cloud Project Configuration ---
YOUR_GCP_PROJECT_ID = "ora-automation-project"

# Correct, absolute path to the service account key file, located
# in a 'config' folder outside the main project directory.
# SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\config\ora-automation-project-2345f75740f8.json" # LOCAL DEVELOPMENT
SERVICE_ACCOUNT_KEY_PATH = None # FOR PRODUCTION

# --- ShipStation API Configuration ---
SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"
SHIPSTATION_CREATE_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders/createorders"
SHIPSTATION_SHIPMENTS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/shipments"
SHIPSTATION_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders"


# --- Google Sheets API Configuration ---
GOOGLE_SHEET_ID = "1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo"
# --- THIS IS THE FIX ---
# Updated to match the exact name of the secret in your GCP Secret Manager screenshot.
GOOGLE_SHEETS_SA_KEY_SECRET_ID = "google-sheets-service-account-key" 
ORA_PROCESSING_STATE_TAB_NAME = 'ORA_Processing_State'
MONTHLY_CHARGE_REPORT_OUTPUT_TAB_NAME = 'Monthly Charge Report'
WEEKLY_REPORT_OUTPUT_TAB_NAME = 'Weekly Report'
ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME = 'ORA_Weekly_Shipped_History'
GOLDEN_TEST_DATA_RAW_TAB_NAME = 'Golden_Test_Data_Raw'
INVENTORY_TRANSACTIONS_TAB_NAME = 'Inventory_Transactions'
ORA_CONFIGURATION_TAB_NAME = 'ORA_Configuration'
SKU_LOT_TAB_NAME = 'SKU_Lot'
SHIPPED_ITEMS_DATA_TAB_NAME = "Shipped_Items_Data"
SHIPPED_ORDERS_DATA_TAB_NAME = "Shipped_Orders_Data"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


# --- Product Bundle Configuration ---
BUNDLE_CONFIG = {
    "18075": [{"component_id": "17612", "multiplier": 1}],
    "18225": [{"component_id": "17612", "multiplier": 40}],
    "18235": [{"component_id": "17612", "multiplier": 15}],
    "18255": [{"component_id": "17612", "multiplier": 6}],
    "18345": [{"component_id": "17612", "multiplier": 1}],
    "18355": [{"component_id": "17612", "multiplier": 1}],
    "18185": [{"component_id": "17612", "multiplier": 41}],
    "18215": [{"component_id": "17612", "multiplier": 16}],
    "18435": [{"component_id": "17612", "multiplier": 1}],
    "18445": [{"component_id": "17612", "multiplier": 1}],
    "18575": [{"component_id": "17612", "multiplier": 50}],
    "18585": [{"component_id": "17612", "multiplier": 18}],
    "18595": [{"component_id": "17612", "multiplier": 7}],
    "18655": [{"component_id": "17612", "multiplier": 45}],
    "18645": [{"component_id": "17612", "multiplier": 18}],
    "18635": [{"component_id": "17612", "multiplier": 9}],
    "18785": [{"component_id": "17612", "multiplier": 45}],
    "18775": [{"component_id": "17612", "multiplier": 18}],
    "18765": [{"component_id": "17612", "multiplier": 9}],
    "18625": [{"component_id": "17612", "multiplier": 3}],
    "18265": [{"component_id": "17914", "multiplier": 40}],
    "18275": [{"component_id": "17914", "multiplier": 15}],
    "18285": [{"component_id": "17914", "multiplier": 6}],
    "18195": [{"component_id": "17914", "multiplier": 1}],
    "18375": [{"component_id": "17914", "multiplier": 1}],
    "18455": [{"component_id": "17914", "multiplier": 1}],
    "18495": [{"component_id": "17914", "multiplier": 16}],
    "18485": [{"component_id": "17914", "multiplier": 41}],
    "18295": [{"component_id": "17904", "multiplier": 40}],
    "18305": [{"component_id": "17904", "multiplier": 15}],
    "18425": [{"component_id": "17904", "multiplier": 6}],
    "18385": [{"component_id": "17904", "multiplier": 1}],
    "18395": [{"component_id": "17904", "multiplier": 1}],
    "18465": [{"component_id": "17904", "multiplier": 1}],
    "18515": [{"component_id": "17904", "multiplier": 16}],
    "18315": [{"component_id": "17975", "multiplier": 40}],
    "18325": [{"component_id": "17975", "multiplier": 15}],
    "18335": [{"component_id": "17975", "multiplier": 6}],
    "18405": [{"component_id": "17975", "multiplier": 1}],
    "18415": [{"component_id": "17975", "multiplier": 1}],
    "18525": [{"component_id": "17975", "multiplier": 41}],
    "18535": [{"component_id": "17975", "multiplier": 16}],
    "18685": [{"component_id": "18675", "multiplier": 40}],
    "18695": [{"component_id": "18675", "multiplier": 15}],
    "18705": [{"component_id": "18675", "multiplier": 6}],
    "18715": [{"component_id": "18675", "multiplier": 41}],
    "18725": [{"component_id": "18675", "multiplier": 16}],
    "18735": [{"component_id": "18675", "multiplier": 1}],
    "18745": [{"component_id": "18675", "multiplier": 1}],
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


# --- X-Cart XML Data Path ---
X_CART_XML_PATH = os.path.join(PROJECT_ROOT, "src", "test_data", "x_cart_orders_uat_test.xml")


# --- Settings Class ---
class Settings:
    def __init__(self):
        self.PROJECT_ROOT = PROJECT_ROOT
        self.YOUR_GCP_PROJECT_ID = YOUR_GCP_PROJECT_ID
        self.SERVICE_ACCOUNT_KEY_PATH = SERVICE_ACCOUNT_KEY_PATH
        self.SHIPSTATION_BASE_URL = SHIPSTATION_BASE_URL
        self.SHIPSTATION_API_KEY_SECRET_ID = SHIPSTATION_API_KEY_SECRET_ID
        self.SHIPSTATION_API_SECRET_SECRET_ID = SHIPSTATION_API_SECRET_SECRET_ID
        self.SHIPSTATION_CREATE_ORDERS_ENDPOINT = SHIPSTATION_CREATE_ORDERS_ENDPOINT
        self.SHIPSTATION_SHIPMENTS_ENDPOINT = SHIPSTATION_SHIPMENTS_ENDPOINT
        self.SHIPSTATION_ORDERS_ENDPOINT = SHIPSTATION_ORDERS_ENDPOINT
        self.GOOGLE_SHEET_ID = GOOGLE_SHEET_ID
        self.GOOGLE_SHEETS_SA_KEY_SECRET_ID = GOOGLE_SHEETS_SA_KEY_SECRET_ID
        self.ORA_PROCESSING_STATE_TAB_NAME = ORA_PROCESSING_STATE_TAB_NAME
        self.MONTHLY_CHARGE_REPORT_OUTPUT_TAB_NAME = MONTHLY_CHARGE_REPORT_OUTPUT_TAB_NAME
        self.WEEKLY_REPORT_OUTPUT_TAB_NAME = WEEKLY_REPORT_OUTPUT_TAB_NAME
        self.ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME = ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME
        self.GOLDEN_TEST_DATA_RAW_TAB_NAME = GOLDEN_TEST_DATA_RAW_TAB_NAME
        self.INVENTORY_TRANSACTIONS_TAB_NAME = INVENTORY_TRANSACTIONS_TAB_NAME
        self.ORA_CONFIGURATION_TAB_NAME = ORA_CONFIGURATION_TAB_NAME
        self.SKU_LOT_TAB_NAME = SKU_LOT_TAB_NAME
        self.SHIPPED_ITEMS_DATA_TAB_NAME = SHIPPED_ITEMS_DATA_TAB_NAME
        self.SHIPPED_ORDERS_DATA_TAB_NAME = SHIPPED_ORDERS_DATA_TAB_NAME
        self.SCOPES = SCOPES
        self.BUNDLE_CONFIG = BUNDLE_CONFIG
        self.X_CART_XML_PATH = X_CART_XML_PATH

# Initialize a global settings object for easy import
settings = Settings()

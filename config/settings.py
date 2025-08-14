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
YOUR_GCP_PROJECT_ID = "ora-automation-project-dev"

# SERVICE_ACCOUNT_KEY_PATH:
# For local development: Point to the absolute path of your Google Service Account JSON key file.
# This file is used by the 'google-cloud-secret-manager' client library for local authentication
# when retrieving secrets, and by 'googleapiclient' for Sheets/Drive API access.
# For cloud deployment (Google Cloud Functions): This should be None. GCFs use their
#                                             assigned service account automatically for GCP services,
#                                             and secrets are fetched via Secret Manager using ADC.
# Uncomment the appropriate line based on your environment.
# LOCAL DEVELOPMENT VERSION:
# SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\NathanNeely\Projects\config\ora-automation-project-2345f75740f8.json"

_SERVICE_ACCOUNT_BASE_PATH = r"C:\Users\NathanNeely\Projects\config"
_SERVICE_ACCOUNT_FILENAME = "ora-automation-project-dev-25acb5551197.json"
SERVICE_ACCOUNT_KEY_PATH = os.path.join(_SERVICE_ACCOUNT_BASE_PATH, _SERVICE_ACCOUNT_FILENAME)


# CLOUD DEPLOYMENT VERSION:
# SERVICE_ACCOUNT_KEY_PATH = None


# --- ShipStation API Configuration ---
SHIPSTATION_BASE_URL = "https://ssapi.shipstation.com"
SHIPSTATION_API_KEY_SECRET_ID = "shipstation-api-key"
SHIPSTATION_API_SECRET_SECRET_ID = "shipstation-api-secret"
SHIPSTATION_CREATE_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders/createorders"
SHIPSTATION_SHIPMENTS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/shipments"
SHIPSTATION_ORDERS_ENDPOINT = f"{SHIPSTATION_BASE_URL}/orders"


# --- Google Sheets & Drive API Configuration ---
GOOGLE_SHEET_ID = "1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo"
# GOOGLE_SHEETS_SA_KEY_SECRET_ID:
# The Secret Manager ID for your Google Sheets service account JSON key.
# This secret should contain the *content* of the JSON key, not its path.
# Used for both local (via secret_manager.access_secret_version) and cloud environments
# to authenticate with Google Sheets and Google Drive APIs.
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

# SCOPES: Comprehensive list of Google API scopes required for the service account.
# 'https://www.googleapis.com/auth/spreadsheets' for Sheets read/write.
# 'https://www.googleapis.com/auth/drive.readonly' for Drive file content read.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']


# --- Product Bundle Configuration ---
# This configuration is static and does not change based on environment.
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


# --- X-Cart XML Data Source Configuration ---
# X_CART_XML_PATH: Local file path for X-Cart XML.
# This variable is ONLY used during local development/testing of the uploader
# when reading from a local XML file.
# LOCAL DEVELOPMENT VERSION:
X_CART_XML_PATH = os.path.join(PROJECT_ROOT, "src", "test_data", "x_cart_orders_uat_test.xml")
# CLOUD DEPLOYMENT VERSION (This variable is not used in cloud, can be commented out or set to None):
# X_CART_XML_PATH = None

# X_CART_XML_FILE_ID: Google Drive File ID for the X-Cart XML.
# This variable will be used when the script is deployed to Google Cloud Functions
# to fetch the XML data directly from Google Drive.
# You MUST replace 'your_google_drive_file_id_here' with the actual ID.
# X_CART_XML_FILE_ID = "1rNudeesa_c6q--KIKUAOLwXta_gyRqAE" # Updated with provided File ID
X_CART_XML_FILE_ID = "1mBbpzIp_tq3t5GeUzLKwoeFmoAQ_ViqY" # Updated with new File ID



# --- Notification & Reporting Configuration ---
# DAILY_SUMMARY_RECIPIENTS: List of email addresses for the daily order import summary digest email.
# These are the recipients for the high-level operational summary.
DAILY_SUMMARY_RECIPIENTS = ["nathan@clearpathai.co"]

# NOTIFICATION_RECIPIENTS: List of email addresses for critical error notifications.
# These recipients will receive immediate alerts for significant issues (e.g., via Cloud Logging alerts).
# This list can be the same as or different from DAILY_SUMMARY_RECIPIENTS based on who needs immediate technical alerts.
NOTIFICATION_RECIPIENTS = ["nathan@clearpathai.co"]

# EMAIL_SERVICE_API_KEY_SECRET_ID:
# The Secret Manager ID for the API key of your chosen third-party email service (e.g., SendGrid).
# This key is used by the notification_manager to send emails.
# IMPORTANT: You need to create a secret in Google Cloud Secret Manager.
# 1. Go to Google Cloud Console -> Secret Manager.
# 2. Click "Create Secret".
# 3. Give it a name (e.g., "sendgrid-api-key" or "ora-email-api-key").
# 4. In the "Secret value" field, paste your actual SendGrid API Key (or other email service API key).
# 5. Click "Create Secret".
# 6. Use the name you gave it as the value for this variable below.
EMAIL_SERVICE_API_KEY_SECRET_ID = "sendgrid-api-key" # Example Secret Manager ID for SendGrid API Key


# --- Settings Class ---
# This class encapsulates all the above constants, making them accessible
# as attributes (e.g., settings.YOUR_GCP_PROJECT_ID) throughout the application.
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
        self.X_CART_XML_FILE_ID = X_CART_XML_FILE_ID
        self.DAILY_SUMMARY_RECIPIENTS = DAILY_SUMMARY_RECIPIENTS
        self.NOTIFICATION_RECIPIENTS = NOTIFICATION_RECIPIENTS
        self.EMAIL_SERVICE_API_KEY_SECRET_ID = EMAIL_SERVICE_API_KEY_SECRET_ID


# Initialize a global settings object for easy import
settings = Settings()

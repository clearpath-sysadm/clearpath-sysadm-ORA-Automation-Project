# filename: src/services/google_sheets/api_client.py
"""
This module provides functions for reading from and writing to Google Sheets
using the Google Sheets API. Supports both Replit Connector OAuth2 and service account auth.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
from google.oauth2 import service_account, credentials as oauth2_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import central settings and unified secrets module
from config import settings
from src.services.secrets import get_secret

logger = logging.getLogger(__name__)

# Ensure this logger outputs DEBUG logs regardless of root logger config
logger.setLevel(logging.DEBUG)

# Cache for credentials to avoid repeated Secret Manager access and credential building
_cached_credentials = None

# Cache for Replit Connector tokens (in-memory only, never persisted)
_connector_token_cache = {
    'access_token': None,
    'expires_at': None
}

def _get_replit_connector_token():
    """
    Fetches OAuth2 access token from Replit Connectors API.
    Implements in-memory caching with 60s expiry skew.
    
    Returns:
        tuple: (access_token, expires_at_datetime) or (None, None) if unavailable
    """
    global _connector_token_cache
    
    # Check if cached token is still valid (with 60s buffer)
    if _connector_token_cache['access_token'] and _connector_token_cache['expires_at']:
        now = datetime.now(timezone.utc)
        if _connector_token_cache['expires_at'] > now + timedelta(seconds=60):
            logger.debug("Using cached Replit Connector token")
            return _connector_token_cache['access_token'], _connector_token_cache['expires_at']
    
    # Determine X-REPLIT-TOKEN from environment
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
    
    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        logger.warning("No REPL_IDENTITY or WEB_REPL_RENEWAL found - Replit Connector unavailable")
        return None, None
    
    # Fetch token from Replit Connectors API
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME', 'connectors.replit.com')
    url = f"https://{hostname}/api/v2/connection"
    params = {
        'include_secrets': 'true',
        'connector_names': 'google-sheet'
    }
    headers = {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': x_replit_token
    }
    
    try:
        logger.debug(f"Fetching token from Replit Connectors API: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        if not items:
            logger.warning("No Google Sheets connections found in Replit Connectors")
            return None, None
        
        # Use first connection or specified connection ID
        connection = items[0]
        if settings.CONNECTORS_GOOGLE_SHEET_CONNECTION_ID:
            for conn in items:
                if conn.get('id') == settings.CONNECTORS_GOOGLE_SHEET_CONNECTION_ID:
                    connection = conn
                    break
        
        # Extract access token and expiry
        conn_settings = connection.get('settings', {})
        access_token = conn_settings.get('access_token')
        expires_at_str = conn_settings.get('expires_at')
        
        if not access_token:
            logger.error("No access_token found in Replit Connector response")
            return None, None
        
        # Parse expiry (ISO 8601 format)
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Could not parse expires_at: {expires_at_str}")
        
        # Cache the token
        _connector_token_cache['access_token'] = access_token
        _connector_token_cache['expires_at'] = expires_at
        
        logger.info("Successfully fetched token from Replit Connector")
        return access_token, expires_at
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch token from Replit Connectors: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error fetching Replit Connector token: {e}", exc_info=True)
        return None, None


def _get_sheets_credentials():
    """
    Helper function to get authenticated Google Sheets credentials.
    Implements auto auth strategy: prefer Replit Connector, fallback to service account.
    
    Returns:
        google.auth.credentials.Credentials: Authenticated credentials
    """
    global _cached_credentials
    
    auth_mode = settings.GS_AUTH_MODE
    
    # Try Replit Connector if mode is 'auto' or 'connector'
    if auth_mode in ['auto', 'connector']:
        access_token, expires_at = _get_replit_connector_token()
        
        if access_token:
            logger.info("Using Replit Connector OAuth2 credentials")
            creds = oauth2_credentials.Credentials(
                token=access_token,
                expiry=expires_at
            )
            return creds
        elif auth_mode == 'connector':
            raise RuntimeError("GS_AUTH_MODE set to 'connector' but Replit Connector unavailable")
        else:
            logger.info("Replit Connector unavailable, falling back to service account")
    
    # Use service account credentials (cached)
    if _cached_credentials and auth_mode != 'connector':
        logger.debug("Using cached service account credentials")
        return _cached_credentials

    try:
        logger.debug("Attempting to retrieve Google Sheets service account key")
        service_account_key_json = get_secret(settings.GOOGLE_SHEETS_SA_KEY_SECRET_ID)

        if not service_account_key_json:
            logger.critical(f"Failed to retrieve Google Sheets service account key: {settings.GOOGLE_SHEETS_SA_KEY_SECRET_ID}")
            raise ValueError("Google Sheets service account key not available.")

        creds_info = json.loads(service_account_key_json)
        
        # Build credentials with all necessary scopes from settings
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=settings.SCOPES)
        
        _cached_credentials = creds
        logger.info("Google Sheets service account credentials successfully retrieved and cached")
        return creds

    except json.JSONDecodeError as e:
        logger.critical(f"Failed to parse Google Sheets service account JSON key: {e}", exc_info=True)
        raise ValueError("Invalid Google Sheets service account JSON format.") from e
    except Exception as e:
        logger.critical(f"Unexpected error getting Google Sheets credentials: {e}", exc_info=True)
        raise RuntimeError("Could not establish Google Sheets credentials.") from e

def get_google_sheet_data(sheet_id: str, worksheet_name: str) -> list | None:
    """
    Retrieves data from a Google Sheet using a service account.

    Args:
        sheet_id (str): The ID of the Google Sheet.
        worksheet_name (str): The name of the specific worksheet (tab) to read from.

    Returns:
        list | None: A list of lists representing the sheet data, or None if an error occurs.
    """
    # Development mode bypass - return fixture data
    if settings.DEV_FAKE_SHEETS:
        logger.info(f"🔧 DEV BYPASS ACTIVE - Google Sheets: Loading fixture for '{worksheet_name}'")
        import json
        import os
        
        # Map worksheet names to fixture files
        fixture_map = {
            "ORA_Configuration": "ora_configuration.json",
            "ORA_Weekly_Shipped_History": "ora_weekly_shipped_history.json", 
            "Inventory_Transactions": "inventory_transactions.json",
            "Shipped_Items_Data": "shipped_items_data.json",
            "Shipped_Orders_Data": "shipped_orders_data.json"
        }
        
        fixture_file = fixture_map.get(worksheet_name)
        if fixture_file:
            fixture_path = os.path.join(settings.DEV_FIXTURES_PATH, fixture_file)
            try:
                with open(fixture_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data)} rows from fixture '{fixture_file}'")
                return data
            except FileNotFoundError:
                logger.warning(f"Fixture file not found: {fixture_path}")
                return [["Column1", "Column2"], ["No", "Data"]]
        
        # Fallback empty data
        logger.warning(f"No fixture available for worksheet '{worksheet_name}', returning empty data")
        return [["Column1", "Column2"], ["Sample", "Data"]]
    
    try:
        creds = _get_sheets_credentials()
        service = build('sheets', 'v4', credentials=creds)
        
        range_name = f"'{worksheet_name}'!A:ZZ" # Fetch all data from the sheet
        
        logger.debug({"message": "Fetching data from Google Sheet", "sheet_id": sheet_id, "worksheet": worksheet_name, "range": range_name})
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            logger.warning({"message": "No data found in Google Sheet or worksheet is empty.", "sheet_id": sheet_id, "worksheet": worksheet_name})
            return [] # Return empty list if no values
        else:
            logger.info({"message": "Successfully retrieved data from Google Sheet.", "sheet_id": sheet_id, "worksheet": worksheet_name, "rows_count": len(values)})
            return values
    except HttpError as e:
        logger.error({
            "message": "Google Sheets API HTTP error during data retrieval.",
            "sheet_id": sheet_id,
            "worksheet": worksheet_name,
            "error_code": e.resp.status,
            "error_details": e.content.decode('utf-8'),
            "function": "get_google_sheet_data"
        }, exc_info=True)
        return None
    except Exception as e:
        logger.error({
            "message": "An unexpected error occurred while retrieving data from Google Sheet.",
            "sheet_id": sheet_id,
            "worksheet": worksheet_name,
            "error": str(e),
            "function": "get_google_sheet_data"
        }, exc_info=True)
        return None

def write_dataframe_to_sheet(df: pd.DataFrame, sheet_id: str, worksheet_name: str, header_row: bool = True):
    # Only clear rows after 53 for the Weekly History tab
    from config.settings import ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME
    if worksheet_name == ORA_WEEKLY_SHIPPED_HISTORY_TAB_NAME:
        try:
            clear_range = f"'{worksheet_name}'!A54:ZZ"
            service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=clear_range
            ).execute()
            logger.info({"message": "Cleared all rows after row 53 (row 54 and beyond)", "sheet_id": sheet_id, "worksheet": worksheet_name})
        except Exception as e:
            logger.error({"message": "Failed to clear rows after row 53.", "sheet_id": sheet_id, "worksheet": worksheet_name, "error": str(e)})
    """
    Writes a Pandas DataFrame to a Google Sheet, clearing existing content first.
    Applies cell alignment formatting: header row centered, data rows right-justified.

    Args:
        df (pd.DataFrame): The DataFrame to write.
        sheet_id (str): The ID of the Google Sheet.
        worksheet_name (str): The name of the specific worksheet (tab) to write to.
        header_row (bool): If True, the DataFrame's columns will be written as the first row.
    """

    if df.empty:
        logger.warning({"message": "DataFrame is empty, nothing to write to Google Sheet.", "sheet_id": sheet_id, "worksheet": worksheet_name})
        return

    # Debug: Log DataFrame dtypes and a sample of the data before upload
    logger.debug({
        "message": "DataFrame dtypes before upload",
        "dtypes": df.dtypes.astype(str).to_dict()
    })
    logger.debug({
        "message": "Sample data before upload",
        "sample": df.head(3).to_dict(orient='list')
    })

    # Robustly convert all values to native Python types for JSON serialization
    import numpy as np
    def make_serializable(val):
        if isinstance(val, (np.generic,)):
            return val.item()
        if hasattr(val, 'isoformat'):
            return val.isoformat()
        if isinstance(val, (list, tuple)):
            return [make_serializable(v) for v in val]
        if isinstance(val, dict):
            return {k: make_serializable(v) for k, v in val.items()}
        return val

    df = df.applymap(make_serializable)

    try:
        creds = _get_sheets_credentials()
        service = build('sheets', 'v4', credentials=creds)

        # Prepare data for writing
        values_to_write = [df.columns.tolist()] if header_row else []
        values_to_write.extend(df.values.tolist())

        body = {
            'values': values_to_write
        }
        range_name = f"'{worksheet_name}'!A1" # Start writing from A1


        # 2. Write new data
        logger.debug({"message": "Writing new data to Google Sheet.", "sheet_id": sheet_id, "worksheet": worksheet_name, "rows_to_write": len(values_to_write)})
        result = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='RAW', # RAW means no parsing, USER_ENTERED means parsing (e.g. "1/2" becomes date)
            body=body
        ).execute()
        logger.info({"message": "Data successfully written to Google Sheet.", "sheet_id": sheet_id, "worksheet": worksheet_name, "updated_cells": result.get('updatedCells')})

        # 3. Apply formatting (header centered, data rows right-justified)
        requests = []
        # Header row formatting (centered)
        if header_row and values_to_write:
            # Dynamically get sheetId from the spreadsheet metadata
            spreadsheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheet_id_for_formatting = None
            for sheet_prop in spreadsheet_metadata.get('sheets', []):
                if sheet_prop.get('properties', {}).get('title') == worksheet_name:
                    sheet_id_for_formatting = sheet_prop.get('properties', {}).get('sheetId')
                    break
            
            if sheet_id_for_formatting is None:
                logger.warning({"message": "Could not find sheetId for formatting. Skipping header formatting.", "sheet_id": sheet_id, "worksheet": worksheet_name})
            else:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id_for_formatting,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(df.columns)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "horizontalAlignment": "CENTER"
                            }
                        },
                        "fields": "userEnteredFormat.horizontalAlignment"
                    }
                })
        
        # Data rows formatting (right-justified)
        if len(values_to_write) > (1 if header_row else 0):
            # Dynamically get sheetId from the spreadsheet metadata
            spreadsheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheet_id_for_formatting = None
            for sheet_prop in spreadsheet_metadata.get('sheets', []):
                if sheet_prop.get('properties', {}).get('title') == worksheet_name:
                    sheet_id_for_formatting = sheet_prop.get('properties', {}).get('sheetId')
                    break
            
            if sheet_id_for_formatting is None:
                logger.warning({"message": "Could not find sheetId for formatting. Skipping data row formatting.", "sheet_id": sheet_id, "worksheet": worksheet_name})
            else:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id_for_formatting,
                            "startRowIndex": (1 if header_row else 0),
                            "endRowIndex": len(values_to_write),
                            "startColumnIndex": 0,
                            "endColumnIndex": len(df.columns)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "horizontalAlignment": "RIGHT"
                            }
                        },
                        "fields": "userEnteredFormat.horizontalAlignment"
                    }
                })
        
        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()
            logger.info({"message": "Google Sheet formatting applied successfully.", "sheet_id": sheet_id, "worksheet": worksheet_name})
            

    except HttpError as e:
        logger.error({
            "message": "Google Sheets API HTTP error during data write or formatting.",
            "sheet_id": sheet_id,
            "worksheet": worksheet_name,
            "error_code": e.resp.status,
            "error_details": e.content.decode('utf-8'),
            "function": "write_dataframe_to_sheet"
        }, exc_info=True)
    except Exception as e:
        logger.error({
            "message": "An unexpected error occurred while writing data to Google Sheet.",
            "sheet_id": sheet_id,
            "worksheet": worksheet_name,
            "error": str(e),
            "function": "write_dataframe_to_sheet"
        }, exc_info=True)



# filename: src/services/google_sheets/api_client.py
"""
This module provides functions for reading from and writing to Google Sheets
using the Google Sheets API. It handles authentication internally via Secret Manager.
"""
import json
import logging
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import central settings and secret manager client
from config import settings
from src.services.gcp.secret_manager import access_secret_version

logger = logging.getLogger(__name__)

# Ensure this logger outputs DEBUG logs regardless of root logger config
logger.setLevel(logging.DEBUG)

# Cache for credentials to avoid repeated Secret Manager access and credential building
_cached_credentials = None

def _get_sheets_credentials():
    """
    Helper function to get authenticated Google Sheets credentials.
    Retrieves the service account key from Secret Manager and caches it.
    """
    global _cached_credentials
    if _cached_credentials:
        logger.debug({"message": "Using cached Google Sheets credentials."})
        return _cached_credentials

    try:
        logger.debug({"message": "Attempting to retrieve Google Sheets service account key from Secret Manager."})
        service_account_key_json = access_secret_version(
            settings.YOUR_GCP_PROJECT_ID,
            settings.GOOGLE_SHEETS_SA_KEY_SECRET_ID,
            credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH # For local testing
        )

        if not service_account_key_json:
            logger.critical({"message": "Failed to retrieve Google Sheets service account key from Secret Manager.", "secret_id": settings.GOOGLE_SHEETS_SA_KEY_SECRET_ID})
            raise ValueError("Google Sheets service account key not available.")

        creds_info = json.loads(service_account_key_json)
        
        # Build credentials with all necessary scopes from settings
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=settings.SCOPES)
        
        _cached_credentials = creds # Cache the credentials
        logger.info({"message": "Google Sheets credentials successfully retrieved and cached."})
        return creds

    except json.JSONDecodeError as e:
        logger.critical({"message": "Failed to parse Google Sheets service account JSON key.", "error": str(e)}, exc_info=True)
        raise ValueError("Invalid Google Sheets service account JSON format.") from e
    except Exception as e:
        logger.critical({"message": "An unexpected error occurred while getting Google Sheets credentials.", "error": str(e)}, exc_info=True)
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
    # ...existing code for writing and formatting...

    # 4. Clear all rows after row 53 (i.e., row 54 and beyond) using values().clear
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

            # 4. Clear all rows after row 53 (i.e., row 54 and beyond) using values().clear
    try:
        clear_range = f"'{worksheet_name}'!A54:ZZ"
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=clear_range
        ).execute()
        logger.info({"message": "Cleared all rows after row 53 (row 54 and beyond)", "sheet_id": sheet_id, "worksheet": worksheet_name})
    except Exception as e:
        logger.error({"message": "Failed to clear rows after row 53.", "sheet_id": sheet_id, "worksheet": worksheet_name, "error": str(e)})


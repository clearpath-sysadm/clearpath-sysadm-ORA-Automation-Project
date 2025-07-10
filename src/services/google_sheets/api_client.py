import logging
import pandas as pd
import json
import gspread
from gspread_dataframe import set_with_dataframe
from src.services.gcp.secret_manager import access_secret_version
from config.settings import settings

logger = logging.getLogger(__name__)

def _get_gspread_client():
    """
    Authenticates with Google Sheets API using service account credentials
    fetched from Secret Manager and returns an authorized gspread client.
    """
    try:
        logger.debug("Authenticating with Google Sheets API...")
        sa_key_json_str = access_secret_version(
            project_id=settings.YOUR_GCP_PROJECT_ID,
            secret_id=settings.GOOGLE_SHEETS_SA_KEY_SECRET_ID,
            credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
        )
        if not sa_key_json_str:
            logger.error("Failed to retrieve Google Sheets service account key from Secret Manager.")
            return None
        
        sa_info = json.loads(sa_key_json_str)

        # --- THIS IS THE FIX ---
        # The service_account_from_dict function returns an already authorized client.
        # Calling gspread.authorize() on it is redundant and causes the TypeError.
        client = gspread.service_account_from_dict(sa_info)
        
        logger.info("Successfully authenticated with Google Sheets API.")
        return client

    except Exception as e:
        logger.critical(f"An error occurred during Google Sheets authentication: {e}", exc_info=True)
        return None

def get_google_sheet_data(sheet_id: str, worksheet_name: str) -> pd.DataFrame | None:
    """
    Fetches all data from a specified worksheet using the Google Sheet ID.
    """
    client = _get_gspread_client()
    if not client:
        return None
    try:
        logger.debug(f"Opening Google Sheet by ID: '{sheet_id}'.")
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        logger.debug(f"Reading data from worksheet: '{worksheet_name}'.")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        logger.info(f"Successfully fetched {len(df)} rows from worksheet '{worksheet_name}'.")
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Google Sheet with ID '{sheet_id}' not found or access denied.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{worksheet_name}' not found in the specified Google Sheet.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching data from Google Sheets: {e}", exc_info=True)
        return None

def write_dataframe_to_sheet(df: pd.DataFrame, sheet_id: str, worksheet_name: str):
    """
    Writes a pandas DataFrame to a specified worksheet using the Google Sheet ID.
    """
    client = _get_gspread_client()
    if not client:
        logger.error("Cannot write to sheet, gspread client not available.")
        return
    try:
        logger.debug(f"Opening Google Sheet by ID '{sheet_id}' to write to worksheet '{worksheet_name}'.")
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        logger.info(f"Successfully wrote {len(df)} rows to worksheet '{worksheet_name}'.")
    except Exception as e:
        logger.error(f"An error occurred while writing data to Google Sheets: {e}", exc_info=True)

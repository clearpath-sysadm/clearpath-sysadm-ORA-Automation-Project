# filename: sheets_api.py
"""
Module for interacting with Google Sheets API.
Provides functions to read and write data from specified sheets.
"""
import gspread
from google.oauth2 import service_account
import logging

# Assume logging is configured globally by the main orchestrating script (e.g., shipstation_reporter.py)

class SheetsApiModule:
    @staticmethod
    def get_google_sheet_data(sheet_id, sheet_name, range_name, service_account_key_path):
        """
        Retrieves data from a specified Google Sheet.
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_key_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            client = gspread.authorize(credentials)
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.worksheet(sheet_name)
            data = worksheet.get(range_name)
            logging.info(f"Successfully retrieved data from Google Sheet ID: {sheet_id}, Sheet: {sheet_name}, Range: {range_name}")
            return data
        except Exception as e:
            logging.error(f"Error retrieving data from Google Sheet ID: {sheet_id}, Sheet: {sheet_name}, Range: {range_name}. Error: {e}")
            return []

    @staticmethod
    def write_google_sheet_data(sheet_id, sheet_name, range_name, data, service_account_key_path):
        """
        Writes data to a specified Google Sheet.
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_key_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            client = gspread.authorize(credentials)
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.worksheet(sheet_name)
            worksheet.update(values=data, range_name=range_name)
            logging.info(f"Successfully wrote data to Google Sheet ID: {sheet_id}, Sheet: {sheet_name}, Range: {range_name}")
            return True
        except Exception as e:
            logging.error(f"Error writing data to Google Sheet ID: {sheet_id}, Sheet: {sheet_name}, Range: {range_name}. Error: {e}")
            return False

sheets_api = SheetsApiModule()

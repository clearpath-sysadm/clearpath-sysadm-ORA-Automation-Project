import pandas as pd
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time # For time.sleep in retry logic

# --- Configuration for this standalone test ---
# IMPORTANT: Replace with the actual ID of your "Project Tracker - ORA" Google Sheet
GOOGLE_SHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
MONTHLY_CHARGE_REPORT_TAB_NAME = 'Monthly Charge Report'

# Scopes required for writing to Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# --- CRITICAL: Path to your Google Service Account JSON file ---
# IMPORTANT: REPLACE THIS WITH THE ACTUAL, ABSOLUTE PATH TO YOUR DOWNLOADED SERVICE ACCOUNT JSON FILE
# Example: SERVICE_ACCOUNT_FILE_PATH = r"C:\Users\YourUser\Downloads\your-service-account-key.json"
SERVICE_ACCOUNT_FILE_PATH = r"C:\Users\NathanNeely\Projects\ORA_Automation\config\ora-automation-project-2345f75740f8.json"


# --- Write Google Sheet Data Function (Copied and adapted from shipstation_reporter.py) ---
def write_google_sheet_data(spreadsheet_id, tab_name, service_account_file_path, df_to_write):
    """
    Writes a Pandas DataFrame to a Google Sheet, clearing existing data first.
    Includes retry logic for HttpError 503.
    """
    max_retries = 5
    initial_delay = 1 # seconds

    # Prepare data for writing: headers first, then rows
    values_to_write = [df_to_write.columns.tolist()] + df_to_write.values.tolist()
    
    # Explicitly convert numpy types to native Python types if present (e.g., np.int64 to int, np.float64 to float)
    clean_values_to_write = []
    for row in values_to_write:
        cleaned_row = []
        for item in row:
            if pd.isna(item): # Handle NaN values which JSON doesn't like directly
                cleaned_row.append("")
            elif isinstance(item, (int, float, str, bool)): # Already native types
                cleaned_row.append(item)
            elif hasattr(item, 'item'): # For numpy types like np.int64, np.float64
                cleaned_row.append(item.item())
            else:
                cleaned_row.append(str(item)) # Fallback for other complex types
        clean_values_to_write.append(cleaned_row)


    # Define the range to write, starting from A1 of the specified tab
    range_name = f"{tab_name}!A1"

    for attempt in range(max_retries):
        try:
            # Authenticate using the service account file directly
            creds = service_account.Credentials.from_service_account_file(service_account_file_path, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)

            # Clear existing data in the range
            clear_request_body = {} # Empty body clears the entire range
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                body=clear_request_body
            ).execute()
            print(f"Cleared existing data in {range_name}.")

            # Write new data
            body = {
                'values': clean_values_to_write
            }
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW', # Use 'RAW' to write values as-is
                body=body
            ).execute()
            print(f"{result.get('updatedCells')} cells updated in {range_name}.")
            return True # Success
        except HttpError as e:
            if e.resp.status == 503:
                print(f"HttpError 503 (Service Unavailable) writing to Google Sheet '{spreadsheet_id}' range '{range_name}'. Retrying in {initial_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(initial_delay)
                initial_delay *= 2 # Exponential backoff
            else:
                print(f"Error writing to Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
                print(f"Details: {e}")
                return False # Failed
        except FileNotFoundError:
            print(f"Error: Service account file not found at '{service_account_file_path}'. Please check the path.")
            return False
        except Exception as e:
            print(f"Error writing to Google Sheet '{spreadsheet_id}' range '{range_name}': {e}")
            print(f"Details: {e}")
            return False
    
    print(f"Failed to write data to Google Sheet '{spreadsheet_id}' range '{range_name}' after {max_retries} retries due to HttpError 503.")
    return False

# --- Main execution for the test script ---
if __name__ == "__main__":
    print("Starting Google Sheets Write Test Script...")

    # Create a DataFrame with just the word "test"
    test_df = pd.DataFrame([["test"]], columns=["Message"])

    print(f"Attempting to write '{test_df.iloc[0,0]}' to Google Sheet '{GOOGLE_SHEET_ID}' tab '{MONTHLY_CHARGE_REPORT_TAB_NAME}' using file '{SERVICE_ACCOUNT_FILE_PATH}'...")
    
    success = write_google_sheet_data(
        GOOGLE_SHEET_ID,
        MONTHLY_CHARGE_REPORT_TAB_NAME,
        SERVICE_ACCOUNT_FILE_PATH, # Pass the file path directly
        test_df
    )

    if success:
        print("Successfully wrote 'test' to the Google Sheet. Please check the tab manually.")
    else:
        print("Failed to write 'test' to the Google Sheet. Check console output for errors.")

    print("Test script finished.")

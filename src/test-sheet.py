from google.oauth2 import service_account
from googleapiclient.discovery import build

# Update these paths/IDs as needed
SERVICE_ACCOUNT_FILE = r'C:\Users\NathanNeely\Projects\config\ora-automation-project-dev-25acb5551197.json'
SPREADSHEET_ID = '1SMewCScZp0U4QtdXMp8ZhT3oxefzKHu-Hq2BAXtCeoo'
RANGE_NAME = 'A1:B2'  # Change as needed

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def main():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    print(values)

if __name__ == '__main__':
    main()
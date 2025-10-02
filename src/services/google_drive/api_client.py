# filename: src/services/google_drive/api_client.py
"""
This module provides functions for interacting with the Google Drive API,
specifically for fetching file content.
"""
import json
import logging
import os
import requests
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from io import BytesIO
from googleapiclient.http import MediaIoBaseDownload

# Import central settings
from config import settings

# Initialize logger for this module
logger = logging.getLogger(__name__)

def get_replit_google_drive_access_token():
    """Get Google Drive access token from Replit connection"""
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    x_replit_token = os.environ.get('REPL_IDENTITY')
    
    if x_replit_token:
        x_replit_token = 'repl ' + x_replit_token
    elif os.environ.get('WEB_REPL_RENEWAL'):
        x_replit_token = 'depl ' + os.environ.get('WEB_REPL_RENEWAL')
    else:
        raise Exception('X_REPLIT_TOKEN not found for repl/depl')
    
    url = f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-drive'
    headers = {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': x_replit_token
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    connection_settings = data.get('items', [{}])[0]
    
    # Try multiple paths for access token (connector API can return it in different places)
    settings = connection_settings.get('settings', {})
    access_token = settings.get('access_token')
    
    if not access_token:
        # Try OAuth credentials path
        access_token = settings.get('oauth', {}).get('credentials', {}).get('access_token')
    
    if not access_token:
        raise Exception('Google Drive not connected')
    
    logger.info("Successfully retrieved Google Drive access token from Replit connector")
    return access_token

def list_xml_files_from_folder(folder_id: str):
    """List all XML files from a Google Drive folder using Replit connection"""
    try:
        access_token = get_replit_google_drive_access_token()
        
        credentials = Credentials(token=access_token)
        service = build('drive', 'v3', credentials=credentials)
        
        # Query for XML files in the folder
        query = f"'{folder_id}' in parents and (mimeType='text/xml' or mimeType='application/xml' or name contains '.xml') and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, modifiedTime, size)"
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"Found {len(files)} XML files in Google Drive folder {folder_id}")
        
        return files
        
    except Exception as e:
        logger.error(f"Error listing files from Google Drive: {str(e)}")
        raise

def fetch_xml_from_drive_by_file_id(file_id: str) -> str:
    """Fetch XML content from Google Drive using Replit connection"""
    try:
        access_token = get_replit_google_drive_access_token()
        
        credentials = Credentials(token=access_token)
        service = build('drive', 'v3', credentials=credentials)
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
        logger.info(f"Fetching file: {file_metadata.get('name')}")
        
        # Download file content
        request = service.files().get_media(fileId=file_id)
        file_content_stream = BytesIO()
        downloader = MediaIoBaseDownload(file_content_stream, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")
        
        xml_content_bytes = file_content_stream.getvalue()
        xml_string = xml_content_bytes.decode('iso-8859-1')
        
        logger.info(f"Successfully fetched XML content from file {file_id}")
        return xml_string
        
    except Exception as e:
        logger.error(f"Error fetching XML from Google Drive: {str(e)}")
        raise

def fetch_xml_content_from_drive(file_id: str, service_account_key_json: str) -> str | None:
    """
    Securely retrieves and decodes XML content from a specified Google Drive file ID in-memory.

    Args:
        file_id (str): The Google Drive File ID of the XML file to fetch.
        service_account_key_json (str): The JSON content of the Google Service Account key
                                        as a string, used for authentication.

    Returns:
        str | None: The decoded XML content as a string if successful, None otherwise.
    """
    if not file_id:
        logger.error({"message": "Google Drive File ID is missing.", "function": "fetch_xml_content_from_drive"})
        return None
    if not service_account_key_json:
        logger.critical({"message": "Google Service Account JSON key is missing for Drive access.", "function": "fetch_xml_content_from_drive"})
        return None

    try:
        creds_info = json.loads(service_account_key_json)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=settings.SCOPES)
        service = build('drive', 'v3', credentials=creds)
        logger.debug({"message": "Google Drive API service client built successfully.", "function": "fetch_xml_content_from_drive"})

        # First, get file metadata to confirm it's a non-native file and get its actual mimeType
        # This helps in debugging if alt='media' behaves unexpectedly
        file_metadata = service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
        file_name = file_metadata.get('name')
        file_mime_type = file_metadata.get('mimeType')
        file_size = file_metadata.get('size') # Size in bytes

        logger.info({
            "message": "Confirmed file metadata from Google Drive.",
            "file_id": file_id,
            "file_name": file_name,
            "file_mime_type": file_mime_type,
            "file_size_bytes": file_size
        })

        if file_mime_type != 'text/xml':
            logger.warning({
                "message": "File is not of expected text/xml MIME type. Attempting to fetch anyway, but may cause parsing issues.",
                "file_id": file_id,
                "actual_mime_type": file_mime_type
            })
        
        # Request the media content
        request = service.files().get_media(fileId=file_id) # Use get_media() directly for raw content
        
        file_content_stream = BytesIO()
        downloader = MediaIoBaseDownload(file_content_stream, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                logger.debug({"message": "Downloading chunk from Google Drive", "status_progress": status.progress(), "file_id": file_id})
        
        xml_content_bytes = file_content_stream.getvalue()
        
        logger.info({"message": "File content fetched from Google Drive.", "file_id": file_id, "content_length_bytes": len(xml_content_bytes), "function": "fetch_xml_content_from_drive"})

        if isinstance(xml_content_bytes, bytes):
            if not xml_content_bytes: # Check if content is empty after fetch
                logger.warning({"message": "Fetched XML content is empty.", "file_id": file_id, "function": "fetch_xml_content_from_drive"})
                return None
            
            # --- NEW LOGGING ADDED HERE ---
            logger.debug({
                "message": "Raw XML bytes snippet before decoding.",
                "file_id": file_id,
                "raw_bytes_start_hex": xml_content_bytes[:50].hex(), # Log hex to reveal non-printable chars
                "raw_bytes_end_hex": xml_content_bytes[-50:].hex()
            })
            # --- END NEW LOGGING ---

            # Decode using 'iso-8859-1' to match the XML declaration
            xml_string = xml_content_bytes.decode('iso-8859-1')

            # --- NEW LOGGING ADDED HERE ---
            logger.debug({
                "message": "Decoded XML string snippet.",
                "file_id": file_id,
                "decoded_string_start": xml_string[:200], # Log first 200 chars
                "decoded_string_end": xml_string[-200:] # Log last 200 chars
            })
            # --- END NEW LOGGING ---
            
            logger.info({"message": "XML content successfully fetched and decoded from Google Drive.", "file_id": file_id, "function": "fetch_xml_content_from_drive"})
            return xml_string
        else:
            logger.critical({
                "message": "Fetched content is not bytes; expected XML bytes but received unexpected type.",
                "file_id": file_id,
                "received_type": str(type(xml_content_bytes)),
                "received_content_start": str(xml_content_bytes)[:200],
                "function": "fetch_xml_content_from_drive"
            })
            return None

    except HttpError as e:
        logger.error({
            "message": "Google Drive API HTTP error during file fetch.",
            "file_id": file_id,
            "error_code": e.resp.status,
            "error_details": e.content.decode('utf-8') if e.content else "No error details",
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None
    except json.JSONDecodeError as e:
        logger.critical({
            "message": "Failed to parse service account JSON key.",
            "error": str(e),
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None
    except UnicodeDecodeError as e:
        logger.error({
            "message": "Failed to decode XML content to UTF-8. Content might be corrupted or in a different encoding.",
            "file_id": file_id,
            "error": str(e),
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None
    except Exception as e:
        logger.critical({
            "message": "An unexpected error occurred while fetching XML from Google Drive.",
            "file_id": file_id,
            "error": str(e),
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None

